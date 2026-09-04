import os
import io
import re
import uuid
import base64
import contextlib
from pathlib import Path
from typing import Union, List, Optional, Tuple, Sequence

EXPORT_CONTEXT = {"export_dir": None, "media_counter": 0}

def format_inline_markdown(text: str) -> str:
    """太字、イタリック、箇条書き、改行などを安全・軽量にHTMLタグへ変換する"""
    text = text.strip()
    if not text:
        return ""

    # ::: point ... ::: の変換
    def replace_point(match):
        inner = match.group(1).strip()
        formatted = format_inline_markdown(inner)
        return f'<div class="point-box">\n{formatted}\n</div>'

    text = re.sub(r":::\s*point\s*\n(.*?)\n:::", replace_point, text, flags=re.DOTALL)

    # ::: memo ... ::: の変換
    def replace_memo(match):
        inner = match.group(1).strip()
        formatted = format_inline_markdown(inner)
        return f'<div class="layout-memo">\n{formatted}\n</div>'

    text = re.sub(r":::\s*memo\s*\n(.*?)\n:::", replace_memo, text, flags=re.DOTALL)

    # 単独の残余コロン記法を除去
    text = re.sub(r"^:::\s*card(?:\(([^)\n]+)\)|:([^\n]+))?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::\s*point\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::\s*memo\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::\s*$", "", text, flags=re.MULTILINE).strip()

    # 太字 **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # イタリック *text*
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    # マークダウン表 (| a | b |) の変換
    def parse_tables(raw_text: str) -> str:
        lines = raw_text.split("\n")
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if "|" in stripped and i + 1 < len(lines):
                next_stripped = lines[i+1].strip()
                sep_cells = [c.strip() for c in next_stripped.split("|")]
                sep_cells = [c for c in sep_cells if c]
                is_sep = len(sep_cells) > 0 and all(re.match(r"^:?-+:?$", c) for c in sep_cells)
                
                if is_sep:
                    alignments = []
                    for sc in sep_cells:
                        if sc.startswith(":") and sc.endswith(":"):
                            alignments.append(' style="text-align: center;"')
                        elif sc.endswith(":"):
                            alignments.append(' style="text-align: right;"')
                        elif sc.startswith(":"):
                            alignments.append(' style="text-align: left;"')
                        else:
                            alignments.append('')

                    header_raw = [c.strip() for c in stripped.split("|")]
                    if stripped.startswith("|"):
                        header_raw = header_raw[1:]
                    if stripped.endswith("|"):
                        header_raw = header_raw[:-1]

                    table_html = ['<table class="slide-table">', '  <thead>', '    <tr>']
                    for idx, hc in enumerate(header_raw):
                        align = alignments[idx] if idx < len(alignments) else ''
                        table_html.append(f'      <th{align}>{hc}</th>')
                    table_html.extend(['    </tr>', '  </thead>', '  <tbody>'])

                    i += 2
                    while i < len(lines):
                        row_line = lines[i].strip()
                        if not row_line or "|" not in row_line:
                            break
                        row_raw = [c.strip() for c in row_line.split("|")]
                        if row_line.startswith("|"):
                            row_raw = row_raw[1:]
                        if row_line.endswith("|"):
                            row_raw = row_raw[:-1]
                        
                        table_html.append('    <tr>')
                        for idx, rc in enumerate(row_raw):
                            align = alignments[idx] if idx < len(alignments) else ''
                            table_html.append(f'      <td{align}>{rc}</td>')
                        table_html.append('    </tr>')
                        i += 1
                    
                    table_html.extend(['  </tbody>', '</table>'])
                    new_lines.append("\n".join(table_html))
                    continue

            new_lines.append(line)
            i += 1

        return "\n".join(new_lines)

    text = parse_tables(text)

    lines = text.split("\n")
    out_chunks = []
    current_list = []

    def flush_list():
        if not current_list:
            return
        out_chunks.append("<ul>")
        for item in current_list:
            content = item['header']
            if item['body']:
                body_html = "<br>".join(item['body'])
                content = f"{content}<br><span class=\"list-body\">{body_html}</span>"
            if item.get('subitems'):
                sub_html = "<ul>" + "".join(f"<li>{s}</li>" for s in item['subitems']) + "</ul>"
                content = f"{content}\n{sub_html}"
            out_chunks.append(f"  <li>{content}</li>")
        out_chunks.append("</ul>")
        current_list.clear()

    block_html_prefixes = ("<div", "</div", "<table", "</table", "<thead", "</thead", "<tbody", "</tbody", "<tr", "</tr", "<th", "</th", "<td", "</td")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # すでにブロックHTMLの場合はそのまま出力
        if any(stripped.startswith(prefix) for prefix in block_html_prefixes):
            flush_list()
            out_chunks.append(stripped)
            continue

        # インデント文字数の計算（タブはスペース4つ換算）
        expanded_line = line.expandtabs(4)
        indent = len(expanded_line) - len(expanded_line.lstrip(' '))

        # 箇条書き (- item または * item)
        match_bullet = re.match(r'^(\s*)[-*]\s+(.*)$', line)
        if match_bullet:
            bullet_indent = len(match_bullet.group(1).expandtabs(4))
            bullet_text = match_bullet.group(2).strip()

            if bullet_indent >= 2 and current_list:
                # ネストされたサブ箇条書き
                current_list[-1].setdefault('subitems', []).append(bullet_text)
            else:
                # 第一レベルの箇条書き
                current_list.append({'header': bullet_text, 'body': [], 'subitems': []})
        else:
            # 箇条書き記号がない行
            if current_list and indent >= 2:
                # インデントされている場合 -> 直前の箇条書き項目の内部要素（本文）
                current_list[-1]['body'].append(stripped)
            else:
                # インデントがない場合 -> リストを終了し、独立した段落 <p>
                flush_list()
                out_chunks.append(f"<p>{stripped}</p>")

    flush_list()

    return "\n".join(out_chunks)


def to_graph_html(obj) -> str:
    """
    あらゆる可視化オブジェクト（Plotly, Matplotlib, Bokeh, Altair, Pandas, HTMLファイルパス等）を
    Reveal.js用HTMLスニペットに統一変換する
    """
    if obj is None:
        return ""

    # すでに HTML 文字列または Graph オブジェクトの場合
    if hasattr(obj, "to_html") and not isinstance(obj, str) and hasattr(obj, "html_snippet"):
        return obj.html_snippet

    mod = getattr(obj.__class__, "__module__", "")

    # 1. Plotly Figure
    if "plotly" in mod and hasattr(obj, "to_html"):
        div_id = "chart_" + uuid.uuid4().hex[:8]
        try:
            return obj.to_html(
                full_html=False,
                include_plotlyjs=False,
                div_id=div_id,
                default_height="100%",
                default_width="100%",
                config={"responsive": True}
            )
        except Exception:
            try:
                return obj.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)
            except Exception:
                pass

    # 2. Matplotlib / Seaborn Figure
    if hasattr(obj, "savefig"):
        try:
            buf = io.BytesIO()
            obj.savefig(buf, format="png", bbox_inches="tight", transparent=True)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f'<img src="data:image/png;base64,{b64}" style="max-height: 100%; max-width: 100%; object-fit: contain;">'
        except Exception:
            pass

    # 3. Bokeh
    if "bokeh" in mod:
        try:
            from bokeh.embed import components
            script, div = components(obj)
            return f"{div}\n{script}"
        except Exception:
            pass

    # 4. 一般的な _repr_html_ プロトコル (Altair, Pandas, HoloViews, Folium等)
    if hasattr(obj, "_repr_html_"):
        try:
            return obj._repr_html_()
        except Exception:
            pass

    return f"<div class='graph-object'>{str(obj)}</div>"


FRAGMENT_ANIMATION_ALIASES = {
    "semi-out": "semi-fade-out",
    "highlight": "highlight-red",
}

def wrap_with_fragment(html: str, step: Optional[Union[int, str]] = None, animation: Optional[str] = "fade-in") -> str:
    """要素のHTMLをreveal.jsのfragment divでラップする"""
    if step is None or not html:
        return html
    anim = (animation or "fade-in").strip()
    anim = FRAGMENT_ANIMATION_ALIASES.get(anim, anim)
    cls = "fragment" if anim in ("fade-in", "") else f"fragment {anim}"
    return f'<div class="{cls}" data-fragment-index="{step}">\n{html}\n</div>'


def get_element_step(el: "Element") -> Optional[Union[int, str]]:
    """要素のステップ番号を安全に取得する"""
    return getattr(el, "_step", None)


class StepProperty:
    """代入（card.step = 1）もコンテキストマネージャ呼び出し（with s.step():）も両方受け付けるハイブリッドプロパティ"""
    def __get__(self, instance, owner):
        if instance is None:
            return self

        class _CallableStep:
            def __call__(_self, step: Optional[Union[int, str]] = None, animation: str = "fade-in"):
                return instance._step_context(step, animation)

            def __enter__(_self):
                _self._ctx = instance._step_context()
                return _self._ctx.__enter__()

            def __exit__(_self, exc_type, exc_val, exc_tb):
                return _self._ctx.__exit__(exc_type, exc_val, exc_tb)

            def __eq__(_self, other):
                return instance._step == other

            def __repr__(_self):
                return f"<StepProperty: {instance._step}>"

        return _CallableStep()

    def __set__(self, instance, value):
        if instance is not None:
            instance._step = value


class Element:
    """すべての要素の基底クラス"""
    def __init__(self, step: Optional[Union[int, str]] = None, animation: Optional[str] = None):
        self._step = step
        self.animation = animation

    @property
    def step(self) -> Optional[Union[int, str]]:
        return self._step

    @step.setter
    def step(self, value: Optional[Union[int, str]]):
        self._step = value

    def to_html(self, embed: bool = True) -> str:
        raise NotImplementedError

    def has_chart(self) -> bool:
        return False


class Container(Element):
    """子要素を持つことができる領域（コンテナ）の基底クラス"""
    step = StepProperty()

    def __init__(
        self,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional["Container"] = None
    ):
        super().__init__(step=step, animation=animation)
        self.elements: List[Element] = []
        self.parent = parent
        self._current_step: Optional[Union[int, str]] = None
        self._current_animation: Optional[str] = None
        self._step_counter: int = 0

    def get_root_container(self) -> "Container":
        curr = self
        while curr.parent is not None:
            curr = curr.parent
        return curr

    @contextlib.contextmanager
    def _step_context(self, step: Optional[Union[int, str]] = None, animation: str = "fade-in"):
        """
        reveal.js のステップアニメーション用コンテキストマネージャ内部実装。
        with container.step(): 内で追加された要素に自動でステップ番号とアニメーションを付与する。
        """
        root = self.get_root_container()
        prev_step = self._current_step
        prev_anim = self._current_animation

        if step is None:
            root._step_counter += 1
            cur_step = root._step_counter
        else:
            cur_step = step
            if isinstance(step, int):
                root._step_counter = max(root._step_counter, step)

        self._current_step = cur_step
        self._current_animation = animation
        try:
            yield cur_step
        finally:
            self._current_step = prev_step
            self._current_animation = prev_anim

    def _resolve_step_and_animation(
        self,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ) -> Tuple[Optional[Union[int, str]], str]:
        if step is not None:
            eff_step = step
        else:
            curr = self
            eff_step = None
            while curr is not None:
                if curr._current_step is not None:
                    eff_step = curr._current_step
                    break
                curr = curr.parent

        if animation is not None:
            eff_anim = animation
        else:
            curr = self
            eff_anim = None
            while curr is not None:
                if curr._current_animation is not None:
                    eff_anim = curr._current_animation
                    break
                curr = curr.parent

        return eff_step, (eff_anim or "fade-in")

    def add(self, element: Element, step: Optional[Union[int, str]] = None, animation: Optional[str] = None) -> Element:
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        if eff_step is not None and get_element_step(element) is None:
            element.step = eff_step
            element.animation = eff_anim
        if isinstance(element, Container):
            element.parent = self
        self.elements.append(element)
        return element

    def add_markdown(
        self,
        text: str,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ) -> "Markdown":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        md = Markdown(text, step=eff_step, animation=eff_anim)
        self.elements.append(md)
        return md

    def add_card(
        self,
        color: str = None,
        bg: str = None,
        height: str = None,
        border: str = None,
        border_color: str = None,
        text_color: str = None,
        style: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        **kwargs
    ) -> "Card":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        card = Card(
            color=color,
            bg=bg,
            height=height,
            border=border,
            border_color=border_color,
            text_color=text_color,
            style=style,
            step=eff_step,
            animation=eff_anim,
            parent=self,
            **kwargs
        )
        self.elements.append(card)
        return card

    @property
    def card(self) -> "Card":
        """コンテナ内の直近の Card を取得する。存在しない場合は自動生成して追加する。"""
        for el in reversed(self.elements):
            if isinstance(el, Card):
                return el
        return self.add_card()

    @card.setter
    def card(self, card_obj: "Card"):
        if isinstance(card_obj, Container):
            card_obj.parent = self
        self.elements.append(card_obj)

    def add_grid(
        self,
        col: Union[int, Sequence[int], str] = 2,
        row: Union[int, Sequence[int], str] = 1,
        gap: str = "16px",
        height: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ) -> "Grid":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        grid = Grid(col=col, row=row, gap=gap, height=height, step=eff_step, animation=eff_anim, parent=self)
        self.elements.append(grid)
        return grid

    def add_graph(self, obj, step: Optional[Union[int, str]] = None, animation: Optional[str] = None) -> "Graph":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        graph = Graph(obj, step=eff_step, animation=eff_anim)
        self.elements.append(graph)
        return graph

    def add_chart(self, obj, step: Optional[Union[int, str]] = None, animation: Optional[str] = None) -> "Graph":
        """add_graph のエイリアス"""
        return self.add_graph(obj, step=step, animation=animation)

    def add_table(self, obj, step: Optional[Union[int, str]] = None, animation: Optional[str] = None) -> "Table":
        """Pandas DataFrame等を埋め込む（テーブル専用CSSが適用される）"""
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        table = Table(obj, step=eff_step, animation=eff_anim)
        self.elements.append(table)
        return table

    def add_html(
        self,
        path_or_html: str,
        iframe: bool = False,
        height: str = "100%",
        width: str = "100%",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ) -> "HTMLEmbed":
        """
        外部のHTMLファイルパス、または生HTMLタグを追加する
        iframe=False (デフォルト): <body>の中身を抽出・Plotlyの正規化を行い直接DOMとして埋め込む
        iframe=True: 独立したiframeとして読み込む（CSSのコンフリクトを避けたい場合）
        """
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        html_obj = HTMLEmbed(path_or_html, iframe=iframe, height=height, width=width, step=eff_step, animation=eff_anim)
        self.elements.append(html_obj)
        return html_obj

    def add_image(
        self,
        src: str = None,
        img_path: str = None,
        height: str = None,
        caption: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ) -> "Image":
        actual_src = img_path if img_path is not None else src
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        img = Image(src=actual_src, height=height, caption=caption, step=eff_step, animation=eff_anim)
        self.elements.append(img)
        return img

    def add_memo(self, text: str = "", step: Optional[Union[int, str]] = None, animation: Optional[str] = None) -> "Memo":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        memo = Memo(text, step=eff_step, animation=eff_anim, parent=self)
        self.elements.append(memo)
        return memo

    def add_point(self, text: str = "", step: Optional[Union[int, str]] = None, animation: Optional[str] = None) -> "Point":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        point = Point(text, step=eff_step, animation=eff_anim, parent=self)
        self.elements.append(point)
        return point

    def set_markdown(
        self,
        text: str = "",
        x: Union[int, float, str] = 0,
        y: Union[int, float, str] = 0,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        **kwargs
    ) -> "StampMarkdown":
        """
        スライド上の指定座標 (x, y) にテキスト・マークダウンを絶対配置（スタンプ）する。
        レイアウトの流れを崩さず、グラフや表の上に「↓ココ」「注目！」などの注釈をハンコのように押すことができます。
        """
        if "str" in kwargs and not text:
            text = kwargs.pop("str")
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        stamp = StampMarkdown(text=text, x=x, y=y, step=eff_step, animation=eff_anim, **kwargs)
        self.elements.append(stamp)
        return stamp

    def set_stamp(self, *args, **kwargs) -> "StampMarkdown":
        """set_markdown のエイリアス。レイアウト完了後に絶対座標に配置します。"""
        return self.set_markdown(*args, **kwargs)

    # 後方互換性プロパティ
    @property
    def markdown(self) -> str:
        return ""

    @markdown.setter
    def markdown(self, text: str):
        self.add_markdown(text)

    @property
    def chart(self):
        return None

    @chart.setter
    def chart(self, fig):
        self.add_graph(fig)

    @property
    def graph(self):
        return None

    @graph.setter
    def graph(self, fig):
        self.add_graph(fig)

    def to_html(self, embed: bool = True) -> str:
        parts = []
        for el in self.elements:
            html = el.to_html(embed=embed)
            if not html:
                continue
            step_val = get_element_step(el)
            # GridCell, StampMarkdown は自身の to_html 内で fragment を処理するため二重ラップしない
            if step_val is not None and not isinstance(el, (GridCell, StampMarkdown)):
                html = wrap_with_fragment(html, step_val, getattr(el, "animation", "fade-in"))
            parts.append(html)
        return "\n".join(parts)

    def has_chart(self) -> bool:
        return any(el.has_chart() for el in self.elements)


class Markdown(Element):
    def __init__(self, text: str, step: Optional[Union[int, str]] = None, animation: Optional[str] = None):
        super().__init__(step=step, animation=animation)
        self.text = text

    def to_html(self, embed: bool = True) -> str:
        return format_inline_markdown(self.text)


class StampMarkdown(Element):
    """
    スライド上の指定座標 (x, y) に絶対配置（スタンプ）するテキスト・マークダウン要素。
    既存のレイアウト（グラフや表など）の流れを崩さず、上からハンコを押すように注釈や矢印を配置できます。
    """
    def __init__(
        self,
        text: str = "",
        x: Union[int, float, str] = 0,
        y: Union[int, float, str] = 0,
        color: Optional[str] = None,
        font_size: Optional[str] = None,
        font_weight: Optional[str] = None,
        bg_color: Optional[str] = None,
        background: Optional[str] = None,
        border: Optional[str] = None,
        border_radius: Optional[str] = None,
        padding: Optional[str] = None,
        rotate: Optional[Union[int, float, str]] = None,
        z_index: int = 100,
        pointer_events: str = "none",
        css_class: str = "",
        class_name: str = "",
        style: Optional[str] = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(step=step, animation=animation)
        self.text = text
        self.x = f"{x}px" if isinstance(x, (int, float)) else str(x)
        self.y = f"{y}px" if isinstance(y, (int, float)) else str(y)
        self.color = color
        self.font_size = font_size
        self.font_weight = font_weight
        self.bg_color = bg_color or background
        self.border = border
        self.border_radius = border_radius
        self.padding = padding
        self.rotate = rotate
        self.z_index = z_index
        self.pointer_events = pointer_events
        self.css_class = css_class or class_name
        self.custom_style = style
        self.extra_kwargs = kwargs

    def to_html(self, embed: bool = True) -> str:
        if not self.text:
            return ""

        styles = [
            "position: absolute",
            f"left: {self.x}",
            f"top: {self.y}",
            f"z-index: {self.z_index}",
            f"pointer-events: {self.pointer_events}",
        ]

        if self.color:
            styles.append(f"color: {self.color}")
        if self.font_size:
            styles.append(f"font-size: {self.font_size}")
        if self.font_weight:
            styles.append(f"font-weight: {self.font_weight}")
        if self.bg_color:
            styles.append(f"background: {self.bg_color}")
        if self.border:
            styles.append(f"border: {self.border}")
        if self.border_radius:
            styles.append(f"border-radius: {self.border_radius}")
        if self.padding:
            styles.append(f"padding: {self.padding}")
        if self.rotate is not None:
            rot_val = f"{self.rotate}deg" if isinstance(self.rotate, (int, float)) else str(self.rotate)
            styles.append(f"transform: rotate({rot_val})")
        if self.custom_style:
            styles.append(self.custom_style.strip().rstrip(";"))

        style_str = "; ".join(styles)
        classes = ["slide-stamp"]
        if self.step is not None:
            classes.append("fragment")
            anim = (self.animation or "fade-in").strip()
            anim = FRAGMENT_ANIMATION_ALIASES.get(anim, anim)
            if anim and anim != "fade-in":
                classes.append(anim)
        if self.css_class:
            classes.append(self.css_class)
        class_attr = " ".join(classes)
        frag_attr = f' data-fragment-index="{self.step}"' if self.step is not None else ""

        inner_html = format_inline_markdown(self.text)
        return f'<div class="{class_attr}" style="{style_str}"{frag_attr}>{inner_html}</div>'

    def has_chart(self) -> bool:
        return False


class Graph(Element):
    """Plotly, Matplotlib, Bokeh, Pandas 等を統一的にラップしてHTML化する要素"""
    def __init__(self, obj, step: Optional[Union[int, str]] = None, animation: Optional[str] = None):
        super().__init__(step=step, animation=animation)
        self.raw_obj = obj
        self.html_snippet = to_graph_html(obj)

    def to_html(self, embed: bool = True) -> str:
        if not self.html_snippet:
            return ""
        return f'<div class="included-chart-container">\n{self.html_snippet}\n</div>'

    def has_chart(self) -> bool:
        return True

# エイリアス
Chart = Graph


class Table(Element):
    """Pandas DataFrame 等を統一的にラップしてテーブルとしてHTML化する要素"""
    def __init__(self, obj, step: Optional[Union[int, str]] = None, animation: Optional[str] = None):
        super().__init__(step=step, animation=animation)
        self.raw_obj = obj
        self.html_snippet = to_graph_html(obj)

    def to_html(self, embed: bool = True) -> str:
        if not self.html_snippet:
            return ""
        return f'<div class="slide-table">\n{self.html_snippet}\n</div>'

    def has_chart(self) -> bool:
        return False


class HTMLEmbed(Element):
    """外部HTMLファイルパスまたは生HTML文字列を埋め込む要素"""
    def __init__(
        self,
        path_or_html: str,
        iframe: bool = False,
        height: str = "100%",
        width: str = "100%",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ):
        super().__init__(step=step, animation=animation)
        self.path_or_html = path_or_html
        self.iframe = iframe
        self.height = height
        self.width = width
        
    def to_html(self, embed: bool = True) -> str:
        if not self.path_or_html:
            return ""
            
        stripped = self.path_or_html.strip()
        
        # iframe モードの場合 (パス指定前提)
        if self.iframe:
            # 生HTMLタグが渡された場合はiframeでは厳しいのでそのまま出力する
            if stripped.startswith("<"):
                return stripped
            # style="border:none;" などで見栄えを良くする
            return f'<iframe src="{stripped}" width="{self.width}" height="{self.height}" style="border:none; overflow:hidden;" scrolling="no"></iframe>'
            
        # iframe=False (embed) モードの場合
        # ファイルパスの判定
        if os.path.exists(stripped) and stripped.lower().endswith(".html"):
            try:
                with open(stripped, "r", encoding="utf-8") as f:
                    content = f.read()

                from .utils import normalize_embedded_html
                return normalize_embedded_html(content, width=self.width, height=self.height)
            except Exception as e:
                return f"<div>Error loading HTML file: {stripped} ({e})</div>"
                
        # ファイルパスでない場合は生HTMLとして扱う
        return stripped
        
    def has_chart(self) -> bool:
        # iframeやembedの中にPlotlyが含まれている可能性があるため一応Trueにしておく
        return True


class Image(Element):
    """画像要素（ローカルファイルやPILイメージを自動でBase64エンコードして完全自己完結化）"""
    def __init__(
        self,
        src=None,
        img_path=None,
        height: str = None,
        caption: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None
    ):
        super().__init__(step=step, animation=animation)
        self.src = img_path if img_path is not None else src
        self.height = height
        self.caption = caption

    def to_html(self, embed: bool = True) -> str:
        if self.src is None:
            return ""

        src_uri = ""
        export_dir = EXPORT_CONTEXT.get("export_dir")
        media_dir = None
        if export_dir and not embed:
            media_dir = Path(export_dir) / "media"
            media_dir.mkdir(parents=True, exist_ok=True)

        # 1. PIL Image または save メソッドを持つオブジェクト
        if hasattr(self.src, "save") and callable(self.src.save):
            try:
                fmt = getattr(self.src, "format", None) or "PNG"
                if media_dir:
                    EXPORT_CONTEXT["media_counter"] += 1
                    c = EXPORT_CONTEXT["media_counter"]
                    filename = f"image_{c}.{fmt.lower()}"
                    out_path = media_dir / filename
                    self.src.save(out_path, format=fmt)
                    src_uri = f"media/{filename}"
                else:
                    buf = io.BytesIO()
                    self.src.save(buf, format=fmt)
                    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    src_uri = f"data:image/{fmt.lower()};base64,{b64}"
            except Exception:
                src_uri = ""
        # 2. ローカルファイルパスまたは文字列
        elif isinstance(self.src, (str, Path)):
            src_str = str(self.src).strip()
            if os.path.exists(src_str):
                p = Path(src_str)
                if media_dir:
                    import shutil
                    filename = p.name
                    out_path = media_dir / filename
                    if out_path.exists():
                        EXPORT_CONTEXT["media_counter"] += 1
                        filename = f"{p.stem}_{EXPORT_CONTEXT['media_counter']}{p.suffix}"
                        out_path = media_dir / filename
                    shutil.copy2(p, out_path)
                    src_uri = f"media/{filename}"
                elif embed:
                    try:
                        ext = p.suffix.lower().lstrip(".")
                        mime = f"image/{ext}" if ext != "svg" else "image/svg+xml"
                        with open(p, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                            src_uri = f"data:{mime};base64,{b64}"
                    except Exception:
                        src_uri = src_str
                else:
                    src_uri = src_str
            else:
                src_uri = src_str
        else:
            src_uri = str(self.src)

        if not src_uri:
            return ""

        style_parts = [
            "max-width: 100%;",
            "max-height: 100%;",
            "object-fit: contain;",
        ]
        if self.height:
            h = self.height if (self.height.endswith("px") or self.height.endswith("%") or self.height.endswith("vh")) else f"{self.height}px"
            style_parts.append(f"height: {h};")
            style_parts.append(f"max-height: {h};")
        else:
            style_parts.append("width: 100%;")
            style_parts.append("height: 100%;")

        style_attr = f' style="{" ".join(style_parts)}"'
        caption_html = f'<figcaption>{self.caption}</figcaption>' if self.caption else ""
        return f'<figure class="slide-image">\n  <img src="{src_uri}"{style_attr}>\n  {caption_html}\n</figure>'


def _is_dark_color(c: str) -> bool:
    if not isinstance(c, str):
        return False
    c_clean = c.strip().lstrip("#")
    if len(c_clean) == 3:
        c_clean = "".join([ch * 2 for ch in c_clean])
    if len(c_clean) == 6:
        try:
            r = int(c_clean[0:2], 16)
            g = int(c_clean[2:4], 16)
            b = int(c_clean[4:6], 16)
            return (r * 299 + g * 587 + b * 114) / 1000 < 128
        except ValueError:
            return False
    return False


CARD_PALETTE_MAP = {
    # Yellow / Accent
    "yellow": "card-yellow",
    "soft_yellow": "card-soft-yellow",
    "soft-yellow": "card-soft-yellow",
    "yellow_soft": "card-soft-yellow",
    "yellow-soft": "card-soft-yellow",
    "accent_soft": "card-soft-yellow",
    "accent-soft": "card-soft-yellow",
    "accent_light": "card-yellow",
    "accent-light": "card-yellow",
    "accent": "card-yellow",
    "primary_accent": "card-yellow",
    "primary-accent": "card-yellow",

    # Blue / Sub Accent
    "blue": "card-blue",
    "soft_blue": "card-soft-blue",
    "soft-blue": "card-soft-blue",
    "blue_soft": "card-soft-blue",
    "blue-soft": "card-soft-blue",
    "sub_accent": "card-blue",
    "sub-accent": "card-blue",
    "sub_accent_light": "card-soft-blue",
    "sub-accent-light": "card-soft-blue",
    "accent_blue": "card-blue",
    "accent-blue": "card-blue",
    "accent_blue_soft": "card-soft-blue",
    "accent-blue-soft": "card-soft-blue",
    "accent_blue_light": "card-soft-blue",
    "accent-blue-light": "card-soft-blue",

    # Red
    "red": "card-red",
    "soft_red": "card-soft-red",
    "soft-red": "card-soft-red",
    "red_soft": "card-soft-red",
    "red-soft": "card-soft-red",
    "color_red": "card-red",
    "color-red": "card-red",
    "color_red_soft": "card-soft-red",
    "color-red-soft": "card-soft-red",

    # Green
    "green": "card-green",
    "soft_green": "card-soft-green",
    "soft-green": "card-soft-green",
    "green_soft": "card-soft-green",
    "green-soft": "card-soft-green",
    "color_green": "card-green",
    "color-green": "card-green",
    "color_green_soft": "card-soft-green",
    "color-green-soft": "card-soft-green",

    # Gold / Amber
    "gold": "card-gold",
    "soft_gold": "card-soft-gold",
    "soft-gold": "card-soft-gold",
    "gold_soft": "card-soft-gold",
    "gold-soft": "card-soft-gold",
    "color_gold": "card-gold",
    "color-gold": "card-gold",
    "color_gold_soft": "card-soft-gold",
    "color-gold-soft": "card-soft-gold",
    "accent_dark": "card-gold",
    "accent-dark": "card-gold",

    # Gray / Slate
    "gray": "card-gray",
    "grey": "card-gray",
    "slate": "card-gray",
    "light": "card-gray",

    # Purple
    "purple": "card-purple",
    "violet": "card-purple",

    # Dark / Black
    "dark": "card-dark",
    "black": "card-dark",
    "bg_dark": "card-dark",
    "bg-dark": "card-dark",
}


class Card(Container):
    def __init__(
        self,
        color: str = None,
        bg: str = None,
        height: str = None,
        border: str = None,
        border_color: str = None,
        text_color: str = None,
        style: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional[Container] = None,
        **kwargs
    ):
        super().__init__(step=step, animation=animation, parent=parent)
        self.color = color.lower() if color else None
        self.bg = bg
        self.height = height
        self.border = border
        self.border_color = border_color
        self.text_color = text_color
        self.custom_style = style
        self.extra_kwargs = kwargs

    def to_html(self, embed: bool = True) -> str:
        cls_parts = ["card"]
        styles = []

        target_color = (self.bg or self.color or "").strip()
        if target_color and target_color != "none":
            norm_key = target_color.lower().replace("-", "_")
            if norm_key in CARD_PALETTE_MAP:
                cls_parts.append(CARD_PALETTE_MAP[norm_key])
            elif target_color.startswith("var(") or target_color.startswith("--"):
                c_val = target_color if target_color.startswith("var(") else f"var({target_color})"
                styles.append(f"background: {c_val};")
            elif target_color.startswith("#") or target_color.startswith("rgb") or target_color.startswith("hsl"):
                # 任意のCSSカラー指定（HEXカラー #001122 や rgba など）
                styles.append(f"background: {target_color};")
                # 暗い背景色の場合は自動で白文字＆透過ボーダーに調整して可読性を維持
                if _is_dark_color(target_color) and not self.text_color:
                    styles.append("color: #f8fafc;")
                    if not self.border and not self.border_color:
                        styles.append("border-color: rgba(255, 255, 255, 0.18);")
            else:
                # 未知の名前でも CSS変数 var(--...) として解決を試みる（例: laser_color -> var(--laser-color)）
                css_var = target_color.replace("_", "-")
                styles.append(f"background: var(--{css_var}, {target_color});")
                cls_parts.append(f"card-{css_var}")

        if self.text_color:
            styles.append(f"color: {self.text_color};")
        if self.border:
            styles.append(f"border: {self.border};")
        elif self.border_color:
            styles.append(f"border-color: {self.border_color};")

        if self.height:
            h = self.height if (self.height.endswith("px") or self.height.endswith("%") or self.height.endswith("vh")) else f"{self.height}px"
            styles.append(f"height: {h}; min-height: {h};")

        if self.custom_style:
            styles.append(self.custom_style.strip().rstrip(";"))

        style_attr = f' style="{" ".join(styles)}"' if styles else ""
        inner_html = super().to_html(embed=embed)
        return f'<div class="{" ".join(cls_parts)}"{style_attr}>\n{inner_html}\n</div>'


class Memo(Container):
    def __init__(
        self,
        text: str = "",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional[Container] = None
    ):
        super().__init__(step=step, animation=animation, parent=parent)
        self.text = text

    def to_html(self, embed: bool = True) -> str:
        parts = []
        if self.text:
            parts.append(format_inline_markdown(self.text))
        inner = super().to_html(embed=embed)
        if inner:
            parts.append(inner)
        return f'<div class="layout-memo">\n' + "\n".join(parts) + '\n</div>'


class Point(Container):
    """ポイント強調ボックス (.point-box) 要素。内部に Grid や Image などを自由にネスト可能"""
    def __init__(
        self,
        text: str = "",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional[Container] = None
    ):
        super().__init__(step=step, animation=animation, parent=parent)
        self.text = text

    def to_html(self, embed: bool = True) -> str:
        parts = []
        if self.text:
            parts.append(format_inline_markdown(self.text))
        inner = super().to_html(embed=embed)
        if inner:
            parts.append(inner)
        return f'<div class="point-box">\n' + "\n".join(parts) + '\n</div>'


class GridCell(Container):
    def __init__(
        self,
        name: str = "",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional[Container] = None
    ):
        super().__init__(step=step, animation=animation, parent=parent)
        self.name = name

    def to_html(self, embed: bool = True) -> str:
        inner_html = super().to_html(embed=embed)
        cls_parts = ["grid-cell"]
        frag_attrs = ""
        step_val = get_element_step(self)
        if step_val is not None:
            cls_parts.append("fragment")
            anim = (self.animation or "fade-in").strip()
            anim = FRAGMENT_ANIMATION_ALIASES.get(anim, anim)
            if anim and anim != "fade-in":
                cls_parts.append(anim)
            frag_attrs = f' data-fragment-index="{step_val}"'
        return f'<div class="{" ".join(cls_parts)}"{frag_attrs}>\n{inner_html}\n</div>'


class Grid(Element):
    def __init__(
        self,
        col: Union[int, Sequence[int], str] = 2,
        row: Union[int, Sequence[int], str] = 1,
        gap: str = "16px",
        height: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional[Container] = None
    ):
        super().__init__(step=step, animation=animation)
        self.col = col
        self.row = row
        self.gap = gap
        self.height = height
        self.parent = parent

        # 列数 (num_cols) の解決
        if isinstance(col, (list, tuple)):
            self.num_cols = len(col)
        elif str(col).isdigit():
            self.num_cols = int(col)
        elif ":" in str(col):
            self.num_cols = len(str(col).split(":"))
        else:
            self.num_cols = 2

        # 行数 (num_rows) の解決
        if isinstance(row, (list, tuple)):
            self.num_rows = len(row)
        elif str(row).isdigit():
            self.num_rows = int(row)
        elif ":" in str(row):
            self.num_rows = len(str(row).split(":"))
        else:
            self.num_rows = 1

        total_cells = max(self.num_cols * self.num_rows, 1)
        self.cells: List[GridCell] = [GridCell(f"cell_{i}", parent=self.parent or self) for i in range(total_cells)]

    def __getitem__(self, key: Union[int, Tuple[int, int]]) -> GridCell:
        """NumPyライクな行列アクセス: g[row, col] または 1次元 g[idx]"""
        if isinstance(key, tuple) and len(key) == 2:
            r, c = key
            if not (0 <= r < self.num_rows):
                raise IndexError(f"Grid 行インデックス範囲外: {r} (有効範囲: 0 ~ {self.num_rows - 1})")
            if not (0 <= c < self.num_cols):
                raise IndexError(f"Grid 列インデックス範囲外: {c} (有効範囲: 0 ~ {self.num_cols - 1})")
            return self.cells[r * self.num_cols + c]
        elif isinstance(key, int):
            return self.cells[key]
        raise TypeError(f"無効なインデックス形式です: {key} (int または tuple[int, int] が必要です)")

    def __len__(self) -> int:
        return len(self.cells)

    def __iter__(self):
        return iter(self.cells)

    # 後方互換性
    @property
    def left(self) -> GridCell:
        return self.cells[0]

    @property
    def right(self) -> GridCell:
        return self.cells[self.num_cols - 1]

    @property
    def center(self) -> GridCell:
        if self.num_cols >= 3:
            return self.cells[1]
        return self.cells[0]

    def to_html(self, embed: bool = True) -> str:
        # 列スタイル
        if isinstance(self.col, (list, tuple)):
            col_style = " ".join([f"{c}fr" for c in self.col])
        elif ":" in str(self.col):
            parts = [c.strip() for c in str(self.col).split(":") if c.strip()]
            col_style = " ".join([f"{p}fr" for p in parts])
        elif str(self.col).isdigit():
            col_style = f"repeat({self.col}, minmax(0, 1fr))"
        else:
            col_style = "repeat(2, minmax(0, 1fr))"

        # 行スタイル
        if isinstance(self.row, (list, tuple)):
            row_style = " ".join([f"{r}fr" for r in self.row])
        elif ":" in str(self.row):
            parts = [r.strip() for r in str(self.row).split(":") if r.strip()]
            row_style = " ".join([f"{p}fr" for p in parts])
        elif str(self.row).isdigit():
            row_style = f"repeat({self.row}, minmax(0, 1fr))"
        else:
            row_style = "repeat(1, minmax(0, 1fr))"

        style_parts = [
            f"grid-template-columns: {col_style}",
            f"grid-template-rows: {row_style}",
            f"gap: {self.gap}",
        ]
        if self.height:
            h = self.height if (self.height.endswith("px") or self.height.endswith("%")) else f"{self.height}px"
            style_parts.append(f"height: {h}")
            style_parts.append(f"flex: 0 0 {h}")

        grid_style = f'style="{"; ".join(style_parts)};"'
        cells_html = "\n".join([cell.to_html(embed=embed) for cell in self.cells])
        return f'<div class="custom-grid" {grid_style}>\n{cells_html}\n</div>'

    def has_chart(self) -> bool:
        return any(cell.has_chart() for cell in self.cells)

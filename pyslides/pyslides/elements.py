import os
import io
import re
import uuid
import base64
import contextlib
from pathlib import Path
from typing import Union, List, Optional, Tuple, Sequence

EXPORT_CONTEXT = {"export_dir": None, "media_counter": 0}

def format_inline_markdown(text: str, step: bool = False, step_effect: str = "fade-in") -> str:
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

    frag_cls = "fragment" if step_effect in ("fade-in", "") else f"fragment {step_effect}"

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
            li_cls = f' class="{frag_cls}"' if step else ""
            out_chunks.append(f"  <li{li_cls}>{content}</li>")
        out_chunks.append("</ul>")
        current_list.clear()

    block_html_prefixes = ("<div", "</div", "<table", "</table", "<thead", "</thead", "<tbody", "</tbody", "<tr", "</tr", "<th", "</th", "<td", "</td")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if any(stripped.startswith(prefix) for prefix in block_html_prefixes):
            flush_list()
            out_chunks.append(stripped)
            continue

        expanded_line = line.expandtabs(4)
        indent = len(expanded_line) - len(expanded_line.lstrip(' '))

        match_bullet = re.match(r'^(\s*)[-*]\s+(.*)$', line)
        if match_bullet:
            bullet_indent = len(match_bullet.group(1).expandtabs(4))
            bullet_text = match_bullet.group(2).strip()

            if bullet_indent >= 2 and current_list:
                current_list[-1].setdefault('subitems', []).append(bullet_text)
            else:
                current_list.append({'header': bullet_text, 'body': [], 'subitems': []})
        else:
            if current_list and indent >= 2:
                current_list[-1]['body'].append(stripped)
            else:
                flush_list()
                p_cls = f' class="{frag_cls}"' if step else ""
                out_chunks.append(f"<p{p_cls}>{stripped}</p>")

    flush_list()
    return "\n".join(out_chunks)


def to_graph_html(obj) -> str:
    """あらゆる可視化オブジェクトを Reveal.js 用 HTML スニペットに統一変換する"""
    if obj is None:
        return ""

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

    # 5. 文字列パス（外部HTMLファイル等の場合）
    if isinstance(obj, str):
        from .utils import normalize_embedded_html
        content = obj.strip()
        if content.endswith(".html") or content.endswith(".htm") or os.path.exists(content):
            try:
                with open(content, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass
        return normalize_embedded_html(content)

    return f"<div>{html_escape(str(obj))}</div>"


def html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


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
    idx_attr = f' data-fragment-index="{step}"' if str(step) not in ("", "+", "None") else ""
    return f'<div class="{cls}"{idx_attr}>\n{html}\n</div>'


def get_element_step(el: "Element") -> Optional[Union[int, str]]:
    """要素のステップ番号を安全に取得する"""
    val = getattr(el, "_step", None)
    if val is not None:
        return val
    if getattr(el, "fragment", False):
        idx = getattr(el, "fragment_index", None)
        return idx if idx is not None else "+"
    return None


class StepProperty:
    """個別要素指定（card.step = 1）とコンテキストマネージャ（with s.step():）を受け付けるハイブリッドプロパティ"""
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
    def __init__(
        self,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        if fragment and not animation and isinstance(fragment, str) and fragment != "fade-in":
            animation = fragment
        if fragment_index is not None and step is None:
            step = fragment_index
        elif fragment and step is None:
            step = "+"

        self._step = step
        self.animation = animation
        self.fragment = fragment
        self.fragment_index = fragment_index

    @property
    def step(self) -> Optional[Union[int, str]]:
        return self._step

    @step.setter
    def step(self, value: Optional[Union[int, str]]):
        self._step = value

    def as_fragment(self, effect: str = "fade-in", index: int = None) -> "Element":
        """メソッドチェーン用: 要素をフラグメントアニメーション化する"""
        self.animation = effect
        self.fragment = effect
        if index is not None:
            self._step = index
            self.fragment_index = index
        elif self._step is None:
            self._step = "+"
        return self

    def wrap_fragment(self, inner_html: str) -> str:
        """フラグメントアニメーション用のdivラッパーを適用する"""
        step_val = get_element_step(self)
        if step_val is None:
            return inner_html
        return wrap_with_fragment(inner_html, step_val, self.animation or "fade-in")

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
        parent: Optional["Container"] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
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
        """reveal.js のステップアニメーション用コンテキストマネージャ"""
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
    ) -> Tuple[Optional[Union[int, str]], Optional[str]]:
        eff_step = self._current_step if step is None else step
        eff_anim = self._current_animation if animation is None else animation
        return eff_step, eff_anim

    def add_markdown(
        self,
        text: str,
        step: Optional[Union[bool, int, str]] = None,
        step_effect: str = "fade-in",
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Markdown":
        eff_step, eff_anim = self._resolve_step_and_animation(
            step if isinstance(step, (int, str)) and not isinstance(step, bool) else None,
            animation
        )
        if step is True and eff_step is None:
            eff_step = "+"

        md = Markdown(
            text,
            step=eff_step,
            step_effect=step_effect or eff_anim or "fade-in",
            animation=eff_anim,
            fragment=fragment,
            fragment_index=fragment_index
        )
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
        fragment: Union[bool, str] = False,
        fragment_index: int = None,
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
            fragment=fragment,
            fragment_index=fragment_index,
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
        self.elements.append(card_obj)

    def add_grid(
        self,
        col: Union[int, Sequence[int], str] = 2,
        row: Union[int, Sequence[int], str] = 1,
        gap: str = "16px",
        height: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Grid":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        grid = Grid(
            col=col,
            row=row,
            gap=gap,
            height=height,
            step=eff_step,
            animation=eff_anim,
            parent=self,
            fragment=fragment,
            fragment_index=fragment_index
        )
        self.elements.append(grid)
        return grid

    def add_graph(
        self,
        obj,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Graph":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        graph = Graph(obj, step=eff_step, animation=eff_anim, fragment=fragment, fragment_index=fragment_index)
        self.elements.append(graph)
        return graph

    def add_chart(
        self,
        obj,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Graph":
        return self.add_graph(obj, step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)

    def add_table(
        self,
        obj,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Table":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        table = Table(obj, step=eff_step, animation=eff_anim, fragment=fragment, fragment_index=fragment_index)
        self.elements.append(table)
        return table

    def add_html(
        self,
        path_or_str: str,
        iframe: bool = False,
        height: str = "100%",
        width: str = "100%",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "HTML":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        html = HTML(
            path_or_str,
            iframe=iframe,
            height=height,
            width=width,
            step=eff_step,
            animation=eff_anim,
            fragment=fragment,
            fragment_index=fragment_index
        )
        self.elements.append(html)
        return html

    def add_image(
        self,
        src: Union[str, bytes, Path, "PIL.Image.Image"] = None,
        img_path=None,
        height: str = None,
        caption: str = None,
        fit: str = None,
        scale: float = None,
        width: str = None,
        align: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Image":
        actual_src = src if src is not None else img_path
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        img = Image(
            actual_src,
            height=height,
            caption=caption,
            fit=fit,
            scale=scale,
            width=width,
            align=align,
            step=eff_step,
            animation=eff_anim,
            fragment=fragment,
            fragment_index=fragment_index
        )
        self.elements.append(img)
        return img

    def add_memo(
        self,
        text: str = "",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Memo":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        memo = Memo(
            text,
            step=eff_step,
            animation=eff_anim,
            parent=self,
            fragment=fragment,
            fragment_index=fragment_index
        )
        self.elements.append(memo)
        return memo

    def add_point(
        self,
        text: str = "",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ) -> "Point":
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        point = Point(
            text,
            step=eff_step,
            animation=eff_anim,
            parent=self,
            fragment=fragment,
            fragment_index=fragment_index
        )
        self.elements.append(point)
        return point

    def set_markdown(
        self,
        text: str = "",
        x: Union[int, float, str] = 0,
        y: Union[int, float, str] = 0,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None,
        **kwargs
    ) -> "StampMarkdown":
        if "str" in kwargs and not text:
            text = kwargs.pop("str")
        eff_step, eff_anim = self._resolve_step_and_animation(step, animation)
        stamp = StampMarkdown(
            text=text,
            x=x,
            y=y,
            step=eff_step,
            animation=eff_anim,
            fragment=fragment,
            fragment_index=fragment_index,
            **kwargs
        )
        self.elements.append(stamp)
        return stamp

    def set_stamp(self, *args, **kwargs) -> "StampMarkdown":
        return self.set_markdown(*args, **kwargs)

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
            if step_val is not None and not isinstance(el, (GridCell, StampMarkdown)):
                html = wrap_with_fragment(html, step_val, getattr(el, "animation", "fade-in"))
            parts.append(html)
        return "\n".join(parts)

    def has_chart(self) -> bool:
        return any(el.has_chart() for el in self.elements)


class Markdown(Element):
    def __init__(
        self,
        text: str,
        step: Optional[Union[int, str]] = None,
        step_effect: str = "fade-in",
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
        self.text = text
        self.step_effect = step_effect

    def to_html(self, embed: bool = True) -> str:
        has_step = (self.step is not None) or bool(self.fragment)
        return format_inline_markdown(self.text, step=has_step, step_effect=self.step_effect)


class StampMarkdown(Element):
    """絶対配置 (x, y) されるマークダウン・テキストスタンプ"""
    def __init__(
        self,
        text: str = "",
        x: Union[int, float, str] = 0,
        y: Union[int, float, str] = 0,
        bg_color: Optional[str] = None,
        color: Optional[str] = None,
        padding: str = "4px 8px",
        border_radius: str = "4px",
        font_size: str = "1em",
        font_weight: str = "bold",
        border: Optional[str] = None,
        css_class: str = "",
        class_name: str = "",
        style: Optional[str] = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None,
        **kwargs
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
        self.text = text
        self.x = f"{x}px" if isinstance(x, (int, float)) else str(x)
        self.y = f"{y}px" if isinstance(y, (int, float)) else str(y)
        self.bg_color = bg_color
        self.color = color
        self.padding = padding
        self.border_radius = border_radius
        self.font_size = font_size
        self.font_weight = font_weight
        self.border = border
        self.css_class = css_class or class_name
        self.style = style
        self.extra_kwargs = kwargs

    def to_html(self, embed: bool = True) -> str:
        styles = [
            "position: absolute;",
            f"left: {self.x};",
            f"top: {self.y};",
            "z-index: 100;",
            "box-sizing: border-box;",
        ]
        if self.bg_color:
            styles.append(f"background-color: {self.bg_color};")
        if self.color:
            styles.append(f"color: {self.color};")
        if self.padding:
            styles.append(f"padding: {self.padding};")
        if self.border_radius:
            styles.append(f"border-radius: {self.border_radius};")
        if self.font_size:
            styles.append(f"font-size: {self.font_size};")
        if self.font_weight:
            styles.append(f"font-weight: {self.font_weight};")
        if self.border:
            styles.append(f"border: {self.border};")
        if self.style:
            styles.append(self.style.rstrip("; ") + ";")

        for k, v in self.extra_kwargs.items():
            css_prop = k.replace("_", "-")
            styles.append(f"{css_prop}: {v};")

        style_str = " ".join(styles)
        cls_parts = ["slide-stamp"]
        if self.css_class:
            cls_parts.append(self.css_class)

        step_val = get_element_step(self)
        frag_attr = ""
        if step_val is not None:
            cls_parts.append("fragment")
            anim = (self.animation or "fade-in").strip()
            anim = FRAGMENT_ANIMATION_ALIASES.get(anim, anim)
            if anim and anim != "fade-in":
                cls_parts.append(anim)
            frag_attr = f' data-fragment-index="{step_val}"'

        inner_html = format_inline_markdown(self.text)
        return f'<div class="{" ".join(cls_parts)}" style="{style_str}"{frag_attr}>{inner_html}</div>'


class Graph(Element):
    def __init__(
        self,
        obj,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
        self.raw_obj = obj
        self.html_snippet = to_graph_html(obj)

    def to_html(self, embed: bool = True) -> str:
        if not self.html_snippet:
            return ""
        return f'<div class="included-chart-container">\n{self.html_snippet}\n</div>'

    def has_chart(self) -> bool:
        return True


Chart = Graph


class Table(Element):
    def __init__(
        self,
        obj,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
        self.obj = obj

    def to_html(self, embed: bool = True) -> str:
        if hasattr(self.obj, "to_html"):
            return self.obj.to_html(classes="slide-table", border=0)
        return str(self.obj)


class HTML(Element):
    def __init__(
        self,
        path_or_str: str,
        iframe: bool = False,
        height: str = "100%",
        width: str = "100%",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
        self.path_or_str = path_or_str
        self.iframe = iframe
        self.height = height
        self.width = width
        self._has_chart = None

    def to_html(self, embed: bool = True) -> str:
        content = self.path_or_str.strip()
        if content.endswith(".html") or content.endswith(".htm") or os.path.exists(content):
            try:
                with open(content, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass

        c_lower = content.lower()
        if "plotly" in c_lower or "chart" in c_lower or "plotly-graph-div" in content or "js-plotly-plot" in content:
            self._has_chart = True

        if self.iframe:
            from .utils import normalize_embedded_html
            b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            data_uri = f"data:text/html;base64,{b64}"
            return f'<iframe src="{data_uri}" style="width: {self.width}; height: {self.height}; border: none;" allowfullscreen></iframe>'

        from .utils import normalize_embedded_html
        return normalize_embedded_html(content, width=self.width, height=self.height)

    def has_chart(self) -> bool:
        if self._has_chart is not None:
            return self._has_chart
        p_str = self.path_or_str.strip()
        if "plotly" in p_str.lower() or "chart" in p_str.lower():
            self._has_chart = True
            return True
        if p_str.endswith((".html", ".htm")) or os.path.exists(p_str):
            try:
                with open(p_str, "r", encoding="utf-8") as f:
                    sample = f.read(5000)
                    sample_lower = sample.lower()
                    if "plotly" in sample_lower or "chart" in sample_lower or "plotly-graph-div" in sample:
                        self._has_chart = True
                        return True
            except Exception:
                pass
        self._has_chart = False
        return False


class Image(Element):
    def __init__(
        self,
        src: Union[str, bytes, Path, "PIL.Image.Image"] = None,
        img_path=None,
        height: str = None,
        caption: str = None,
        fit: str = None,
        scale: float = None,
        width: str = None,
        align: str = None,
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
        self.src = src if src is not None else img_path
        self.height = height
        self.caption = caption
        self.fit = fit
        self.scale = scale
        self.width = width
        self.align = align

    def to_html(self, embed: bool = True) -> str:
        if self.src is None:
            return ""

        src_uri = ""
        media_dir = None
        if EXPORT_CONTEXT.get("export_dir"):
            media_dir = Path(EXPORT_CONTEXT["export_dir"]) / "media"
            media_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(self.src, str):
            src_str = self.src
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
        elif isinstance(self.src, bytes):
            if media_dir:
                EXPORT_CONTEXT["media_counter"] += 1
                filename = f"image_{EXPORT_CONTEXT['media_counter']}.png"
                with open(media_dir / filename, "wb") as f:
                    f.write(self.src)
                src_uri = f"media/{filename}"
            else:
                b64 = base64.b64encode(self.src).decode("utf-8")
                src_uri = f"data:image/png;base64,{b64}"
        elif isinstance(self.src, Path):
            p = self.src
            if p.exists():
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
                        src_uri = str(p)
                else:
                    src_uri = str(p)
            else:
                src_uri = str(p)
        elif hasattr(self.src, "save"):
            buf = io.BytesIO()
            self.src.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            if media_dir:
                EXPORT_CONTEXT["media_counter"] += 1
                filename = f"image_{EXPORT_CONTEXT['media_counter']}.png"
                with open(media_dir / filename, "wb") as f:
                    f.write(img_bytes)
                src_uri = f"media/{filename}"
            else:
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                src_uri = f"data:image/png;base64,{b64}"
        else:
            src_uri = str(self.src)

        style_parts = []
        if self.fit:
            style_parts.append(f"object-fit: {self.fit} !important;")
        if self.height:
            style_parts.append(f"height: {self.height} !important;")
        if self.width:
            style_parts.append(f"width: {self.width} !important;")
        if self.scale:
            style_parts.append(f"transform: scale({self.scale});")
        if self.align:
            if self.align == "center":
                style_parts.append("margin-left: auto !important; margin-right: auto !important;")
            elif self.align == "left":
                style_parts.append("margin-right: auto !important; margin-left: 0 !important;")
            elif self.align == "right":
                style_parts.append("margin-left: auto !important; margin-right: 0 !important;")

        style_attr = f' style="{" ".join(style_parts)}"' if style_parts else ""
        caption_html = f'<figcaption>{self.caption}</figcaption>' if self.caption else ""
        return f'<figure class="slide-image">\n  <img src="{src_uri}"{style_attr}>\n  {caption_html}\n</figure>'


def _is_dark_color(c: str) -> bool:
    if not c or not c.startswith("#") or len(c) < 7:
        return False
    try:
        r = int(c[1:3], 16)
        g = int(c[3:5], 16)
        b = int(c[5:7], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return lum < 128
    except Exception:
        return False


class Card(Container):
    """スタイリングされたカードコンテナ要素"""
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
        fragment: Union[bool, str] = False,
        fragment_index: int = None,
        **kwargs
    ):
        super().__init__(step=step, animation=animation, parent=parent, fragment=fragment, fragment_index=fragment_index)
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

        if self.color:
            c = self.color.replace("_", "-")
            cls_parts.append(f"card-{c}")

        if self.bg:
            styles.append(f"background: {self.bg} !important;")
            if not self.text_color and _is_dark_color(self.bg):
                styles.append("color: #f8fafc !important;")

        if self.border:
            styles.append(f"border: {self.border} !important;")
        elif self.border_color:
            styles.append(f"border-color: {self.border_color} !important;")

        if self.text_color:
            styles.append(f"color: {self.text_color} !important;")

        if self.height:
            styles.append(f"height: {self.height} !important;")
            styles.append("min-height: 0 !important;")

        if self.custom_style:
            styles.append(self.custom_style.rstrip("; ") + ";")

        for k, v in self.extra_kwargs.items():
            css_prop = k.replace("_", "-")
            styles.append(f"{css_prop}: {v};")

        style_attr = f' style="{" ".join(styles)}"' if styles else ""
        inner_html = super().to_html(embed=embed)
        return f'<div class="{" ".join(cls_parts)}"{style_attr}>\n{inner_html}\n</div>'


class Memo(Container):
    def __init__(
        self,
        text: str = "",
        step: Optional[Union[int, str]] = None,
        animation: Optional[str] = None,
        parent: Optional[Container] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, parent=parent, fragment=fragment, fragment_index=fragment_index)
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
        parent: Optional[Container] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, parent=parent, fragment=fragment, fragment_index=fragment_index)
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
        parent: Optional[Container] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, parent=parent, fragment=fragment, fragment_index=fragment_index)
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
            idx_attr = f' data-fragment-index="{step_val}"' if str(step_val) not in ("", "+", "None") else ""
            frag_attrs = idx_attr
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
        parent: Optional[Container] = None,
        fragment: Union[bool, str] = False,
        fragment_index: int = None
    ):
        super().__init__(step=step, animation=animation, fragment=fragment, fragment_index=fragment_index)
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

    @property
    def left(self) -> GridCell:
        return self.cells[0]

    @property
    def right(self) -> GridCell:
        return self.cells[1] if len(self.cells) > 1 else self.cells[0]

    def to_html(self, embed: bool = True) -> str:
        style_parts = []

        if isinstance(self.col, (list, tuple)):
            cols_val = " ".join([f"{c}fr" if isinstance(c, (int, float)) else str(c) for c in self.col])
        elif ":" in str(self.col):
            cols_val = " ".join([f"{part}fr" for part in str(self.col).split(":")])
        elif str(self.col).isdigit():
            cols_val = f"repeat({self.col}, 1fr)"
        else:
            cols_val = str(self.col)
        style_parts.append(f"grid-template-columns: {cols_val}")

        if isinstance(self.row, (list, tuple)):
            rows_val = " ".join([f"{r}fr" if isinstance(r, (int, float)) else str(r) for r in self.row])
        elif ":" in str(self.row):
            rows_val = " ".join([f"{part}fr" for part in str(self.row).split(":")])
        elif str(self.row).isdigit():
            rows_val = f"repeat({self.row}, 1fr)"
        else:
            rows_val = str(self.row)
        style_parts.append(f"grid-template-rows: {rows_val}")

        if self.gap:
            style_parts.append(f"gap: {self.gap}")

        if self.height:
            style_parts.append(f"height: {self.height} !important")
            style_parts.append("min-height: 0 !important")

        grid_style = f'style="{"; ".join(style_parts)};"'
        cells_html = "\n".join([cell.to_html(embed=embed) for cell in self.cells])
        return f'<div class="custom-grid" {grid_style}>\n{cells_html}\n</div>'

    def has_chart(self) -> bool:
        return any(cell.has_chart() for cell in self.cells)

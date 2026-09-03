import os
import io
import re
import uuid
import base64
from pathlib import Path
from typing import Union, List, Optional, Tuple, Sequence

def format_inline_markdown(text: str) -> str:
    """太字、イタリック、箇条書き、改行などを安全・軽量にHTMLタグへ変換する"""
    text = text.strip()
    if not text:
        return ""

    # ::: card(color) や ::: memo のような過去の記法が混ざっていた場合の除去／置換
    text = re.sub(r"^:::\s*card(?:\(([^)\n]+)\)|:([^\n]+))?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::\s*memo\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::\s*$", "", text, flags=re.MULTILINE).strip()

    # 太字 **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # イタリック *text*
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    lines = text.split("\n")
    out_chunks = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        # 箇条書き (- item または * item)
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                out_chunks.append("<ul>")
                in_list = True
            item_text = stripped[2:].strip()
            out_chunks.append(f"  <li>{item_text}</li>")
        else:
            if in_list:
                out_chunks.append("</ul>")
                in_list = False
            if stripped:
                out_chunks.append(f"<p>{stripped}</p>")

    if in_list:
        out_chunks.append("</ul>")

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

    # 5. 文字列の場合 (HTMLファイルパス or 生HTMLタグ)
    if isinstance(obj, str):
        stripped = obj.strip()
        # ファイルパスの判定
        if os.path.exists(stripped) and stripped.lower().endswith(".html"):
            try:
                with open(stripped, "r", encoding="utf-8") as f:
                    content = f.read()
                    # bodyタグの内側があれば抽出
                    body_m = re.search(r"<body[^>]*>(.*?)</body>", content, flags=re.DOTALL | re.IGNORECASE)
                    return body_m.group(1).strip() if body_m else content.strip()
            except Exception:
                pass
        # 生HTMLタグ
        if stripped.startswith("<"):
            return stripped

    return f"<div class='graph-object'>{str(obj)}</div>"


class Element:
    """すべての要素の基底クラス"""
    def to_html(self, embed: bool = True) -> str:
        raise NotImplementedError

    def has_chart(self) -> bool:
        return False


class Container(Element):
    """子要素を持つことができる領域（コンテナ）の基底クラス"""
    def __init__(self):
        self.elements: List[Element] = []

    def add(self, element: Element) -> Element:
        self.elements.append(element)
        return element

    def add_markdown(self, text: str) -> "Markdown":
        md = Markdown(text)
        self.elements.append(md)
        return md

    def add_card(self, color: str = None, bg: str = None, height: str = None) -> "Card":
        card = Card(color=color, bg=bg, height=height)
        self.elements.append(card)
        return card

    def add_grid(
        self,
        col: Union[int, Sequence[int], str] = 2,
        row: Union[int, Sequence[int], str] = 1,
        gap: str = "16px",
        height: str = None
    ) -> "Grid":
        grid = Grid(col=col, row=row, gap=gap, height=height)
        self.elements.append(grid)
        return grid

    def add_graph(self, obj) -> "Graph":
        graph = Graph(obj)
        self.elements.append(graph)
        return graph

    def add_chart(self, obj) -> "Graph":
        """add_graph のエイリアス"""
        return self.add_graph(obj)

    def add_image(self, src: str = None, img_path: str = None, height: str = None, caption: str = None) -> "Image":
        actual_src = img_path if img_path is not None else src
        img = Image(src=actual_src, height=height, caption=caption)
        self.elements.append(img)
        return img

    def add_memo(self, text: str) -> "Memo":
        memo = Memo(text)
        self.elements.append(memo)
        return memo

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
        parts = [el.to_html(embed=embed) for el in self.elements]
        return "\n".join(filter(None, parts))

    def has_chart(self) -> bool:
        return any(el.has_chart() for el in self.elements)


class Markdown(Element):
    def __init__(self, text: str):
        self.text = text

    def to_html(self, embed: bool = True) -> str:
        return format_inline_markdown(self.text)


class Graph(Element):
    """Plotly, Matplotlib, Bokeh, Pandas 等を統一的にラップしてHTML化する要素"""
    def __init__(self, obj):
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


class Image(Element):
    """画像要素（ローカルファイルなら自動でBase64エンコードして完全自己完結化）"""
    def __init__(self, src: str = None, img_path: str = None, height: str = None, caption: str = None):
        self.src = img_path if img_path is not None else src
        self.height = height
        self.caption = caption

    def to_html(self, embed: bool = True) -> str:
        if not self.src:
            return ""

        src_uri = self.src
        # ローカルファイルのBase64エンコード
        if embed and os.path.exists(self.src):
            try:
                p = Path(self.src)
                ext = p.suffix.lower().lstrip(".")
                mime = f"image/{ext}" if ext != "svg" else "image/svg+xml"
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    src_uri = f"data:{mime};base64,{b64}"
            except Exception:
                src_uri = self.src

        style_parts = []
        if self.height:
            h = self.height if (self.height.endswith("px") or self.height.endswith("%")) else f"{self.height}px"
            style_parts.append(f"max-height: {h};")
            style_parts.append(f"height: {h};")
        style_parts.append("object-fit: contain;")
        style_attr = f' style="{" ".join(style_parts)}"' if style_parts else ""

        caption_html = f'<figcaption>{self.caption}</figcaption>' if self.caption else ""
        return f'<figure class="slide-image">\n  <img src="{src_uri}"{style_attr}>\n  {caption_html}\n</figure>'


class Card(Container):
    def __init__(self, color: str = None, bg: str = None, height: str = None):
        super().__init__()
        self.color = color.lower() if color else None
        self.bg = bg
        self.height = height

    def to_html(self, embed: bool = True) -> str:
        cls_parts = ["card"]
        if self.color:
            cls_parts.append(f"card-{self.color}")
        
        styles = []
        if self.bg:
            styles.append(f"background: {self.bg};")
        if self.height:
            h = self.height if (self.height.endswith("px") or self.height.endswith("%")) else f"{self.height}px"
            styles.append(f"height: {h}; min-height: {h};")
            
        style_attr = f' style="{" ".join(styles)}"' if styles else ""
        inner_html = super().to_html(embed=embed)
        return f'<div class="{" ".join(cls_parts)}"{style_attr}>\n{inner_html}\n</div>'


class Memo(Element):
    def __init__(self, text: str):
        self.text = text

    def to_html(self, embed: bool = True) -> str:
        formatted = format_inline_markdown(self.text)
        return f'<div class="layout-memo">\n{formatted}\n</div>'


class GridCell(Container):
    def __init__(self, name: str = ""):
        super().__init__()
        self.name = name

    def to_html(self, embed: bool = True) -> str:
        inner_html = super().to_html(embed=embed)
        return f'<div class="grid-cell">\n{inner_html}\n</div>'


class Grid(Element):
    def __init__(
        self,
        col: Union[int, Sequence[int], str] = 2,
        row: Union[int, Sequence[int], str] = 1,
        gap: str = "16px",
        height: str = None
    ):
        self.col = col
        self.row = row
        self.gap = gap
        self.height = height

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
        self.cells: List[GridCell] = [GridCell(f"cell_{i}") for i in range(total_cells)]

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

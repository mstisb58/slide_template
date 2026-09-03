"""
設定およびHTMLテンプレート定義
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SLIDES_MD = BASE_DIR / "slide.md"
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_CSS_DIR = ASSETS_DIR / "css"
ASSETS_JS_DIR = ASSETS_DIR / "js"
EMBED_HTML = BASE_DIR / "slide_embed.html"
REFERED_HTML = BASE_DIR / "slide_refered.html"


TEMPLATE_PATH = ASSETS_DIR / "templates" / "base.html"

# 旧 HTML_TEMPLATE 定数は廃止し、外部ファイルから読み込むように変更
# （ただし他のモジュールとの互換性のため property のように振る舞う関数、または builder 側で直接読み込むよう修正します。
# 今回は builder.py が HTML_TEMPLATE という変数を import しているため、実行時に読み込んだ文字列を代入します）
with open(TEMPLATE_PATH, "r", encoding="utf-8") as _f:
    HTML_TEMPLATE = _f.read()


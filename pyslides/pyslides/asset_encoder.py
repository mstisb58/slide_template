import os
import re
import base64
from pathlib import Path

def find_assets_dir() -> Path:
    """assets ディレクトリを探索（プロジェクトルート優先、次にパッケージ内）"""
    cur = Path(__file__).resolve().parent
    # 1. プロジェクトルート (2階層上または3階層上)
    for p in [cur.parent.parent, cur.parent, cur]:
        candidate = p / "assets"
        if candidate.exists() and (candidate / "css" / "theme-custom.css").exists():
            return candidate
    # 2. パッケージ内 assets
    pkg_assets = cur / "assets"
    if pkg_assets.exists():
        return pkg_assets
    raise FileNotFoundError("pyslides: assets ディレクトリが見つかりません。")

def get_inlined_assets(assets_dir: Path) -> dict:
    """全CSS、ロゴBase64、JSスクリプトを辞書形式でインライン化してキャッシュ"""
    css_dir = assets_dir / "css"
    js_dir = assets_dir / "js"

    # 1. ロゴSVGのBase64データURI作成
    logo_path = css_dir / "logo.svg"
    logo_data_uri = ""
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            logo_data_uri = f"data:image/svg+xml;base64,{b64}"

    # 2. CSSのインライン化
    css_files = [
        css_dir / "reveal.min.css",
        css_dir / "katex.min.css",
        css_dir / "highlight-dark.min.css",
        css_dir / "theme-custom.css",
    ]
    css_blocks = []
    for cf in css_files:
        if cf.exists():
            with open(cf, "r", encoding="utf-8") as f:
                content = f.read()
                # CSS内の url("./logo.svg") を Base64 に置換
                if logo_data_uri:
                    content = re.sub(r'url\(["\']?\./logo\.svg["\']?\)', f'url("{logo_data_uri}")', content)
                css_blocks.append(content)

    inlined_css = "\n\n".join(css_blocks)

    # 3. JSの読み込み
    def read_js_content(p: Path) -> str:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    return {
        "css": inlined_css,
        "plotly_js": read_js_content(js_dir / "plotly.min.js"),
        "katex_js": read_js_content(js_dir / "katex.min.js"),
        "katex_auto_js": read_js_content(js_dir / "katex-auto.min.js"),
        "highlight_js": read_js_content(js_dir / "highlight.min.js"),
        "reveal_js": read_js_content(js_dir / "reveal.min.js"),
        "custom_reveal_js": read_js_content(js_dir / "custom-reveal.js"),
    }

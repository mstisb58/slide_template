import os
import re
import base64
from pathlib import Path
from typing import Optional

def get_pkg_assets_dir() -> Path:
    """パッケージ内部にバンドルされたアセットディレクトリ"""
    return Path(__file__).resolve().parent / "assets"

def find_user_assets_dir() -> Optional[Path]:
    """カレントディレクトリ (ノートブック作業フォルダ) またはプロジェクトルートの assets/css ディレクトリを探索"""
    cwd = Path.cwd()
    if (cwd / "assets" / "css").exists():
        return cwd / "assets"
    if (cwd / "css").exists():
        return cwd

    cur = Path(__file__).resolve().parent
    for p in [cur.parent.parent, cur.parent, cur]:
        candidate = p / "assets"
        if candidate.exists() and (candidate / "css").exists():
            return candidate
    return None

def find_assets_dir() -> Path:
    """後方互換用: assets ディレクトリを返す（ユーザー側優先、なければパッケージ内）"""
    user_adir = find_user_assets_dir()
    if user_adir:
        return user_adir
    return get_pkg_assets_dir()

def find_default_theme_css() -> Optional[Path]:
    """利用するデフォルトのテーマCSSを特定する（kracie_template16-9.css 優先、次に theme-custom.css）"""
    user_adir = find_user_assets_dir()
    if user_adir:
        css_dir = user_adir / "css" if (user_adir / "css").exists() else user_adir
        for name in ["kracie_template16-9.css", "theme-custom.css"]:
            target = css_dir / name
            if target.exists():
                return target
        # 任意の非min CSSファイルがあれば採用
        for cf in css_dir.glob("*.css"):
            if not cf.name.endswith(".min.css"):
                return cf

    # パッケージ内 fallback
    pkg_theme = get_pkg_assets_dir() / "css" / "theme-custom.css"
    if pkg_theme.exists():
        return pkg_theme
    return None

def get_inlined_assets(assets_dir: Optional[Path] = None) -> dict:
    """全CSS、ロゴBase64、JSスクリプトを辞書形式でインライン化してキャッシュ"""
    pkg_dir = get_pkg_assets_dir()
    user_dir = find_user_assets_dir()

    # 1. ロゴSVGの探索（ユーザー側 assets/css/logo.svg 優先、なければパッケージ内）
    logo_data_uri = ""
    logo_paths = []
    if user_dir:
        logo_paths.append(user_dir / "css" / "logo.svg")
        logo_paths.append(user_dir / "logo.svg")
    logo_paths.append(pkg_dir / "css" / "logo.svg")

    for lp in logo_paths:
        if lp.exists():
            try:
                with open(lp, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    logo_data_uri = f"data:image/svg+xml;base64,{b64}"
                    break
            except Exception:
                pass

    # 2. CSSのインライン化
    # システム標準（reveal, katex, highlight）は常にパッケージ内から安全に読み込む
    pkg_css = pkg_dir / "css"
    css_files = [
        pkg_css / "reveal.min.css",
        pkg_css / "katex.min.css",
        pkg_css / "highlight-dark.min.css",
    ]

    # デフォルトのテーマCSS（kracie_template16-9.css 等）を追加
    theme_css = find_default_theme_css()
    if theme_css and theme_css.exists():
        css_files.append(theme_css)

    css_blocks = []
    for cf in css_files:
        if cf.exists():
            with open(cf, "r", encoding="utf-8") as f:
                content = f.read()
                # CSS内の url("./logo.svg") や url("logo.svg") を Base64 に置換
                if logo_data_uri:
                    content = re.sub(r'url\(["\']?\.?/?logo\.svg["\']?\)', f'url("{logo_data_uri}")', content)
                css_blocks.append(content)

    inlined_css = "\n\n".join(css_blocks)

    # 3. JSの読み込み（常にパッケージ内から読み込む）
    pkg_js = pkg_dir / "js"
    def read_js_content(p: Path) -> str:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    return {
        "css": inlined_css,
        "logo_data_uri": logo_data_uri,
        "theme_css_path": str(theme_css) if theme_css else "",
        "plotly_js": read_js_content(pkg_js / "plotly.min.js"),
        "katex_js": read_js_content(pkg_js / "katex.min.js"),
        "katex_auto_js": read_js_content(pkg_js / "katex-auto.min.js"),
        "highlight_js": read_js_content(pkg_js / "highlight.min.js"),
        "reveal_js": read_js_content(pkg_js / "reveal.min.js"),
        "custom_reveal_js": read_js_content(pkg_js / "custom-reveal.js"),
    }

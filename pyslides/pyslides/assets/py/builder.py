"""
HTMLスライド生成（参照型・埋込型）ビルダーモジュール
"""
import re
from pathlib import Path
from .config import (
    BASE_DIR,
    SLIDES_MD,
    ASSETS_CSS_DIR,
    ASSETS_JS_DIR,
    EMBED_HTML,
    REFERED_HTML,
    HTML_TEMPLATE
)
from .markdown_parser import markdown_to_html, split_slides
from .asset_encoder import to_data_uri, embed_css_urls, resolve_includes, embed_images_in_html


def generate_slides_html(md_text: str) -> str:
    """
    Markdownテキストを解析し、Reveal.js用の <section> HTML構造を生成。
    """
    slides_structure = split_slides(md_text)
    slides_html_list = []

    for item in slides_structure:
        if isinstance(item, list):
            # 縦送りスライド (<section> の中に <section> が並ぶ)
            v_html_list = []
            for v_md in item:
                content = markdown_to_html(v_md)
                v_html_list.append(f"  <section>\n{content}\n  </section>")
            slides_html_list.append("<section>\n" + "\n".join(v_html_list) + "\n</section>")
        else:
            # 単一スライド
            is_title = item.strip().startswith("::: title") or item.strip().startswith(":::title")
            sec_class = ' class="title-section"' if is_title else ''
            content = markdown_to_html(item)
            slides_html_list.append(f"<section{sec_class}>\n{content}\n</section>")

    return "\n".join(slides_html_list)


def build_refered_html(slides_html: str) -> str:
    """
    [参照型] assets/ フォルダのファイルを相対パスでリンクする軽量HTMLを生成。
    """
    html = HTML_TEMPLATE

    import time
    ts = int(time.time())

    # CSS リンク (キャッシュバスター付き)
    css_tags = [
        f'<link rel="stylesheet" href="./assets/css/reveal.min.css?v={ts}">',
        f'<link rel="stylesheet" href="./assets/css/katex.min.css?v={ts}">',
        f'<link rel="stylesheet" href="./assets/css/highlight-dark.min.css?v={ts}">',
        f'<link rel="stylesheet" href="./assets/css/theme-custom.css?v={ts}">'
    ]
    html = html.replace("<!-- CSS_PLACEHOLDER -->", "\n  ".join(css_tags))


    # JS スクリプトタグ
    html = html.replace("<!-- PLOTLY_PLACEHOLDER -->", '<script src="./assets/js/plotly.min.js"></script>')
    html = html.replace("<!-- KATEX_JS_PLACEHOLDER -->", '<script src="./assets/js/katex.min.js"></script>\n  <script src="./assets/js/katex-auto.min.js"></script>')
    html = html.replace("<!-- HIGHLIGHT_JS_PLACEHOLDER -->", '<script src="./assets/js/highlight.min.js"></script>')
    html = html.replace("<!-- REVEAL_JS_PLACEHOLDER -->", '<script src="./assets/js/reveal.min.js"></script>')
    html = html.replace("<!-- CUSTOM_JS_PLACEHOLDER -->", '<script src="./assets/js/custom-reveal.js"></script>')

    # スライド内容
    html = html.replace("<!-- SLIDES_PLACEHOLDER -->", slides_html)

    # 外部ファイルのインクルード解決
    html = resolve_includes(html, BASE_DIR)

    return html


def build_embed_html(slides_html: str) -> str:
    """
    [埋込型] CSS, JS, 画像, グラフをすべてインライン＆Base64埋め込みした完全自己完結HTMLを生成。
    """
    html = HTML_TEMPLATE

    # 1. CSSのインライン化
    css_files = [
        ASSETS_CSS_DIR / "reveal.min.css",
        ASSETS_CSS_DIR / "katex.min.css",
        ASSETS_CSS_DIR / "highlight-dark.min.css",
        ASSETS_CSS_DIR / "theme-custom.css"
    ]

    css_inlined = []
    for css_f in css_files:
        if css_f.exists():
            with open(css_f, "r", encoding="utf-8") as f:
                content = f.read()
                content = embed_css_urls(content, ASSETS_CSS_DIR)
                css_inlined.append(f"<style>\n{content}\n</style>")

    html = html.replace("<!-- CSS_PLACEHOLDER -->", "\n".join(css_inlined))

    # 2. JSのインライン化
    def read_js(path: Path) -> str:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f"<script>\n{f.read()}\n</script>"
        return ""

    html = html.replace("<!-- PLOTLY_PLACEHOLDER -->", read_js(ASSETS_JS_DIR / "plotly.min.js"))
    katex_scripts = [read_js(ASSETS_JS_DIR / "katex.min.js"), read_js(ASSETS_JS_DIR / "katex-auto.min.js")]
    html = html.replace("<!-- KATEX_JS_PLACEHOLDER -->", "\n".join(katex_scripts))
    html = html.replace("<!-- HIGHLIGHT_JS_PLACEHOLDER -->", read_js(ASSETS_JS_DIR / "highlight.min.js"))
    html = html.replace("<!-- REVEAL_JS_PLACEHOLDER -->", read_js(ASSETS_JS_DIR / "reveal.min.js"))
    html = html.replace("<!-- CUSTOM_JS_PLACEHOLDER -->", read_js(ASSETS_JS_DIR / "custom-reveal.js"))

    # 3. 外部ファイルのインクルード解決 (埋込型はBase64 Data URI)
    slides_resolved = resolve_includes(slides_html, BASE_DIR, is_embed=True)


    # 4. スライド内の画像（<img src="...">）をBase64データURIに変換
    slides_resolved = embed_images_in_html(slides_resolved, BASE_DIR)

    # 5. スライド内容の埋め込み
    html = html.replace("<!-- SLIDES_PLACEHOLDER -->", slides_resolved)

    return html


def build_all(output_dir: Path = None, verbose: bool = True) -> tuple[Path, Path]:
    """
    slide.md から slide_refered.html と slide_embed.html の両方をビルド
    """
    if not SLIDES_MD.exists():
        raise FileNotFoundError(f"{SLIDES_MD} が見つかりません。")

    with open(SLIDES_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    slides_html = generate_slides_html(md_text)

    # 参照型HTML
    refered_content = build_refered_html(slides_html)
    with open(REFERED_HTML, "w", encoding="utf-8") as f:
        f.write(refered_content)

    # 埋込型HTML
    embed_content = build_embed_html(slides_html)
    with open(EMBED_HTML, "w", encoding="utf-8") as f:
        f.write(embed_content)

    if verbose:
        print("=" * 50)
        print("✔ スライドのビルドが完了しました！ (ロゴ/数式/ハイライト/動画/表/3Dグラフ対応)")
        print(f"  [参照型・確認用] {REFERED_HTML.name}")
        print(f"  [埋込型・配布用] {EMBED_HTML.name}")
        print("=" * 50)

    return REFERED_HTML, EMBED_HTML

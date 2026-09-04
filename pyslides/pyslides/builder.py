import os
import re
import base64
from pathlib import Path
from .asset_encoder import find_assets_dir, get_inlined_assets

def build_full_html(
    slides_section_html: str,
    title: str = "Presentation",
    single_slide: bool = False,
    is_title_slide: bool = False,
    has_chart: bool = True,
    custom_style_paths: list = None,
    export_mode: str = "inline",
    export_dir: Path = None,
    subset_font_css: str = ""
) -> str:
    """
    1280x720 の黄金比デザインシステム、ロゴ、全CSS/JSを完全インライン化、
    またはZIPエクスポート用にファイル分離したHTMLを構築。
    """
    assets_dir = find_assets_dir()
    assets = get_inlined_assets(assets_dir)
    logo_data_uri = assets.get("logo_data_uri", "")

    # ユーザー指定の追加スタイルがあれば追加（複数対応）
    extra_css = ""
    if custom_style_paths:
        for css_path in custom_style_paths:
            if css_path and os.path.exists(css_path):
                with open(css_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # カスタムCSSのディレクトリに logo.svg があれば優先してBase64化
                custom_logo_path = Path(css_path).parent / "logo.svg"
                current_logo_uri = logo_data_uri
                if custom_logo_path.exists():
                    try:
                        with open(custom_logo_path, "rb") as lf:
                            b64 = base64.b64encode(lf.read()).decode("utf-8")
                            current_logo_uri = f"data:image/svg+xml;base64,{b64}"
                    except Exception:
                        pass

                if current_logo_uri:
                    content = re.sub(r'url\(["\']?\.?/?logo\.svg["\']?\)', f'url("{current_logo_uri}")', content)

                extra_css += f"\n/* Custom Style: {os.path.basename(css_path)} */\n{content}\n"

    body_class = "is-title-slide" if (single_slide and is_title_slide) else ""

    # JS制御: ベースは常に custom_reveal_js を使用
    base_js = assets['custom_reveal_js']
    if single_slide:
        # プレビュー特有の上書き設定（コントロール表示、クリック送り）
        preview_override = """
        Reveal.configure({
            hash: false,
            slideNumber: false,
            controls: true,
            progress: false,
            keyboard: true,
            touch: true,
            center: false
        });

        // プレビュー画面内をクリックすると自動フォーカス＆次へ進む（アニメーション確認用）
        document.addEventListener('click', function(e) {
            if (!e.target.closest('button, a, .control-btn, input, select, textarea, .js-plotly-plot')) {
                window.focus();
                Reveal.next();
            }
        });
        """
        runtime_js = f"{base_js}\n{preview_override}"
    else:
        runtime_js = base_js

    if export_mode == "zip" and export_dir:
        # ZIPモード: アセットをファイルに書き出し、相対パスで参照
        assets_out = Path(export_dir) / "assets"
        (assets_out / "css").mkdir(parents=True, exist_ok=True)
        (assets_out / "js").mkdir(parents=True, exist_ok=True)
        
        css_content = f"{assets['css']}\n{extra_css}"
        with open(assets_out / "css" / "style.css", "w", encoding="utf-8") as f:
            f.write(css_content)
        style_html = '<link rel="stylesheet" href="assets/css/style.css">'
        
        with open(assets_out / "js" / "reveal.min.js", "w", encoding="utf-8") as f:
            f.write(assets["reveal_js"])
        reveal_html = '<script src="assets/js/reveal.min.js"></script>'
        
        with open(assets_out / "js" / "runtime.js", "w", encoding="utf-8") as f:
            f.write(runtime_js)
        runtime_html = '<script src="assets/js/runtime.js"></script>'
        
        if has_chart:
            with open(assets_out / "js" / "plotly.min.js", "w", encoding="utf-8") as f:
                f.write(assets["plotly_js"])
            plotly_html = '<script src="assets/js/plotly.min.js"></script>'
        else:
            plotly_html = ""

        with open(assets_out / "js" / "katex.min.js", "w", encoding="utf-8") as f:
            f.write(assets["katex_js"])
        with open(assets_out / "js" / "katex-auto.min.js", "w", encoding="utf-8") as f:
            f.write(assets["katex_auto_js"])
        katex_html = '<script src="assets/js/katex.min.js"></script>\n<script src="assets/js/katex-auto.min.js"></script>'
        
        with open(assets_out / "js" / "highlight.min.js", "w", encoding="utf-8") as f:
            f.write(assets["highlight_js"])
        highlight_html = '<script src="assets/js/highlight.min.js"></script>'
    
    else:
        # インラインモード
        style_html = f"<style>\n{assets['css']}\n{extra_css}\n</style>"
        reveal_html = f"<script>\n{assets['reveal_js']}\n</script>"
        runtime_html = f"<script>\n{runtime_js}\n</script>"
        
        if not has_chart:
            plotly_html = ""
        elif single_slide:
            plotly_html = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
        else:
            plotly_html = f"<script>\n{assets['plotly_js']}\n</script>"

        if single_slide:
            katex_html = """  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>"""
            highlight_html = '  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>'
        else:
            katex_html = f"  <script>\n{assets['katex_js']}\n{assets['katex_auto_js']}\n  </script>"
            highlight_html = f"  <script>\n{assets['highlight_js']}\n  </script>"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{title}</title>
  {subset_font_css}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700&family=BIZ+UDPMincho:wght@400;700&family=Noto+Sans+JP:wght@100..900&family=Inter:wght@100..900&display=swap" rel="stylesheet">
  {style_html}
  {plotly_html}
{katex_html}
{highlight_html}
</head>
<body class="{body_class}">
  <div class="reveal">
    <div class="slides">
      <div class="slide-fixed-logo"></div>
{slides_section_html}
    </div>
  </div>
  {reveal_html}
  {runtime_html}
</body>
</html>"""
    return html

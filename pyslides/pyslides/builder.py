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
    custom_style_paths: list = None
) -> str:
    """
    1280x720 の黄金比デザインシステム、ロゴ、全CSS/JSを完全インライン化したHTMLを構築。
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

    # Plotlyスクリプトの解決（プレビュー時は4.8MBの巨大インラインを避けCDNを使用）
    if not has_chart:
        plotly_script = ""
    elif single_slide:
        plotly_script = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
    else:
        plotly_script = f"<script>\n{assets['plotly_js']}\n</script>"

    # KaTeX / Highlight.jsの解決（プレビュー時は400KB以上の巨大インラインJSを避けCDNを使用）
    if single_slide:
        katex_script = """  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>"""
        highlight_script = '  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>'
    else:
        katex_script = f"  <script>\n{assets['katex_js']}\n{assets['katex_auto_js']}\n  </script>"
        highlight_script = f"  <script>\n{assets['highlight_js']}\n  </script>"

    # JS制御: ベースは常に custom_reveal_js を使用し、プレビュー時のみ追加設定を差し込む
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

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{title}</title>
  <style>
{assets['css']}
{extra_css}
  </style>
  {plotly_script}
{katex_script}
{highlight_script}
</head>
<body class="{body_class}">
  <div class="reveal">
    <div class="slides">
      <div class="slide-fixed-logo"></div>
{slides_section_html}
    </div>
  </div>
  <script>
{assets['reveal_js']}
  </script>
  <script>
{runtime_js}
  </script>
</body>
</html>"""
    return html

import os
from pathlib import Path
from .asset_encoder import find_assets_dir, get_inlined_assets

def build_full_html(
    slides_section_html: str,
    title: str = "Presentation",
    single_slide: bool = False,
    is_title_slide: bool = False,
    has_chart: bool = True,
    custom_style_path: str = None
) -> str:
    """
    1280x720 の黄金比デザインシステム、ロゴ、全CSS/JSを完全インライン化したHTMLを構築。
    """
    assets_dir = find_assets_dir()
    assets = get_inlined_assets(assets_dir)

    # ユーザー指定の追加スタイルがあれば追加
    extra_css = ""
    if custom_style_path and os.path.exists(custom_style_path):
        with open(custom_style_path, "r", encoding="utf-8") as f:
            extra_css = f"\n/* User Custom Style */\n{f.read()}"

    body_class = "is-title-slide" if (single_slide and is_title_slide) else ""

    # Plotlyスクリプトの解決（プレビュー時は4.8MBの巨大インラインを避けCDNを使用）
    if not has_chart:
        plotly_script = ""
    elif single_slide:
        plotly_script = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
    else:
        plotly_script = f"<script>\n{assets['plotly_js']}\n</script>"

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
  <script>
{assets['katex_js']}
{assets['katex_auto_js']}
  </script>
  <script>
{assets['highlight_js']}
  </script>
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

import re

def normalize_embedded_html(content: str, width: str = "100%", height: str = "100%") -> str:
    """
    埋め込み用HTML (Plotly等) の正規化を行う。
    - 不要な外枠(DOCTYPE, html/head/body, meta) の削除
    - 重複する Plotly CDN スクリプトの削除
    - 描画用スクリプトを遅延実行用に変更 (class="plotly-delayed-script")
    - 最外枠の固定幅/高さ指定を解除し、親要素に追従するように修正
    - .included-chart-container でラップする
    """
    # 1. 不要なタグを除去
    content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</?(?:html|head|body)[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<meta[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<script\s+[^>]*src=["\'][^"\']*plotly[^"\']*["\'][^>]*>\s*</script>', '', content, flags=re.IGNORECASE)

    # 2. Plotlyの描画スクリプトをスライド表示時まで遅延実行させるため、型を text/plain に変更
    content = re.sub(
        r'<script(?:\s+type=["\']text/javascript["\'])?>',
        '<script type="text/plain" class="plotly-delayed-script">',
        content,
        flags=re.IGNORECASE
    )

    # 3. 一番外側のPlotly固定幅ラッパーdiv（height:...; width:...;）を100%に正規化
    content = re.sub(
        r'<div\s+style="[^"]*?(?:height:\s*\d+px|width:\s*\d+px)[^"]*">',
        '<div style="width:100%; height:100%; position:relative;">',
        content,
        count=1,
        flags=re.IGNORECASE
    )

    # 4. included-chart-container でラップ
    w = width if (width.endswith("%") or width.endswith("px")) else f"{width}px"
    h = height if (height.endswith("%") or height.endswith("px")) else f"{height}px"
    style_attr = f'style="width: {w}; height: {h}; overflow: hidden; position: relative; margin: 0 auto;"'
    
    return f'<div class="included-chart-container" {style_attr}>\n{content.strip()}\n</div>'

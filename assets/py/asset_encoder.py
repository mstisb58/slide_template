"""
アセットエンコード（Base64化・インクルード解決）モジュール
"""
import base64
import mimetypes
import os
import re
from pathlib import Path


def to_data_uri(file_path: Path) -> str:
    """
    ファイルをBase64 Data URIに変換
    """
    if not file_path.exists():
        print(f"[Warning] ファイルが見つかりません: {file_path}")
        return ""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        if file_path.suffix == ".svg":
            mime_type = "image/svg+xml"
        elif file_path.suffix in [".woff", ".woff2"]:
            mime_type = f"font/{file_path.suffix[1:]}"
        else:
            mime_type = "application/octet-stream"

    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def embed_css_urls(css_content: str, base_dir: Path) -> str:
    """
    CSS内の url(...) をすべて Base64 データURI に置換
    """
    def replace_url(match):
        rel_path = match.group(1).strip("'\"")
        if rel_path.startswith("data:") or rel_path.startswith("http"):
            return match.group(0)
        target = (base_dir / rel_path).resolve()
        if target.exists():
            return f"url('{to_data_uri(target)}')"
        return match.group(0)

    return re.sub(r'url\((.*?)\)', replace_url, css_content)


def resolve_includes(html_content: str, base_dir: Path, is_embed: bool = False) -> str:
    """
    ::include(path/to/file.html[:subparam]):: 構文を検出し、
    不要な外枠タグのみを除去して親の最新 plotly.min.js で直接描画するコンテナとして展開。
    """
    def replace_include(match):
        raw_path = match.group(1).strip()
        opt = match.group(2) if match.lastindex >= 2 and match.group(2) else None
        
        rel_path = raw_path.strip().replace("\\", "/")
        target_file = base_dir / rel_path
        if target_file.exists():
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 1. 不要な外枠タグ・ヘッダー・CDNスクリプトを除去
            content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'</?(?:html|head|body)[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<meta[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<script\s+[^>]*src=["\'][^"\']*plotly[^"\']*["\'][^>]*>\s*</script>', '', content, flags=re.IGNORECASE)

            # [追加] Plotlyの描画スクリプトをスライド表示時まで遅延実行させるため、型を text/plain に変更
            content = re.sub(
                r'<script(?:\s+type=["\']text/javascript["\'])?>',
                '<script type="text/plain" class="plotly-delayed-script">',
                content,
                flags=re.IGNORECASE
            )

            # 2. 一番外側のPlotly固定幅ラッパーdiv（height:...; width:...;）を100%に正規化
            content = re.sub(r'<div\s+style="[^"]*?(?:height:\s*\d+px|width:\s*\d+px)[^"]*">', '<div style="width:100%; height:100%; position:relative;">', content, count=1, flags=re.IGNORECASE)

            # (旧処理) 3. Plotly layout JSON 内の固定幅・高さを削除する処理は、SyntaxErrorの原因になるため削除しました。
            # サイズは config.py の initPlotlyOnSlide 側で動的に relayout することで上書きします。

            h_val = "100%"
            if opt:
                h = opt.replace("h=", "").replace("height=", "").strip()
                if h.isdigit():
                    h += "px"
                h_val = h

            style_attr = f'style="width: 100%; height: {h_val}; overflow: hidden; position: relative;"'
            return f'<div class="included-chart-container" {style_attr}>\n{content.strip()}\n</div>'
        else:
            return f'<div style="color:red; border:1px solid red; padding:10px;">[Include Error] ファイルが見つかりません: {rel_path}</div>'

    return re.sub(r"::include\(([^:\)]+)(?::([^\)]+))?\)::", replace_include, html_content)










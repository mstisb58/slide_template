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
        raw_inside = match.group(1).strip()
        parts = [p.strip() for p in raw_inside.split(",") if p.strip()]
        if not parts:
            return ""

        # 第1引数はファイルパス（クォート除去）
        raw_path = parts[0].strip().strip("'\"")

        opt_parts = []
        for extra in parts[1:]:
            opt_parts.extend([e.strip() for e in re.split(r"[,:]+", extra) if e.strip()])

        # 旧コロン区切り (例: "path.html:40%") のフォールバック対応
        if ":" in raw_path and not (raw_path.startswith("http://") or raw_path.startswith("https://")):
            sub_parts = raw_path.split(":")
            raw_path = sub_parts[0].strip().strip("'\"")
            opt_parts.extend(sub_parts[1:])

        rel_path = raw_path.strip().replace("\\", "/")
        target_file = base_dir / rel_path
        if target_file.exists():
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()

            w_val = "100%"
            h_val = "100%"
            for p in opt_parts:
                p = p.strip()
                if not p: continue
                if p.startswith("w=") or p.startswith("width="):
                    w = p.replace("width=", "").replace("w=", "").strip().strip("'\"")
                    if w.isdigit(): w += "px"
                    w_val = w
                elif p.startswith("h=") or p.startswith("height="):
                    h = p.replace("height=", "").replace("h=", "").strip().strip("'\"")
                    if h.isdigit(): h += "px"
                    h_val = h
                elif p.endswith("%"):
                    h_val = p
                elif p.endswith("px") or p.isdigit():
                    h = p if p.endswith("px") else p + "px"
                    h_val = h

            try:
                from pyslides.pyslides.utils import normalize_embedded_html
            except ImportError:
                import sys
                sys.path.insert(0, str(base_dir))
                from pyslides.pyslides.utils import normalize_embedded_html
                
            return normalize_embedded_html(content, width=w_val, height=h_val)
        else:
            return f'<div style="color:red; border:1px solid red; padding:10px;">[Include Error] ファイルが見つかりません: {rel_path}</div>'

    return re.sub(r"::include\(([^)\n]+)\)::", replace_include, html_content)


def embed_images_in_html(html_content: str, base_dir: Path) -> str:
    """
    HTML内の <img src="..."> をBase64 Data URIに置換して自己完結させる。
    """
    def replace_img_src(match):
        prefix = match.group(1)
        src = match.group(2)
        suffix = match.group(3)
        if src.startswith("data:") or src.startswith("http"):
            return match.group(0)
        img_path = base_dir / src
        if img_path.exists():
            data_uri = to_data_uri(img_path)
            return f'{prefix}{data_uri}{suffix}'
        return match.group(0)

    return re.sub(r'(<img\s+[^>]*src=["\'])(.*?)(["\'][^>]*>)', replace_img_src, html_content, flags=re.IGNORECASE)







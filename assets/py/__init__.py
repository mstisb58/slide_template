"""
スライド生成パッケージ (assets.py)
"""
from .builder import build_all, build_refered_html, build_embed_html
from .markdown_parser import markdown_to_html, split_slides
from .config import BASE_DIR, SLIDES_MD, REFERED_HTML, EMBED_HTML

__all__ = [
    "build_all",
    "build_refered_html",
    "build_embed_html",
    "markdown_to_html",
    "split_slides",
    "BASE_DIR",
    "SLIDES_MD",
    "REFERED_HTML",
    "EMBED_HTML",
]

import os
import sys
import uuid
import json
from pathlib import Path
from typing import Union, List, Optional

from .slide import Slide
from .elements import Chart

class Deck:
    def __init__(
        self,
        slides_or_title: Union[list, tuple, str] = None,
        title: str = "Presentation",
        theme: str = "default",
        agenda_items: list = None,
        slides: list = None
    ):
        # 第1引数がリストやタプルの場合はスライド群として扱う
        if isinstance(slides_or_title, (list, tuple)):
            initial_slides = list(slides_or_title)
        elif slides is not None:
            initial_slides = list(slides)
        else:
            initial_slides = []
            if isinstance(slides_or_title, str):
                title = slides_or_title

        self.title = title
        self.theme = theme
        self.agenda_items = agenda_items or []
        self._slides = []
        self.join(initial_slides)
        self._assets_dir = Path(__file__).parent / "assets"
        
    @property
    def slides(self) -> list:
        return self._slides

    @slides.setter
    def slides(self, new_slides: list):
        self.join(new_slides)

    def join(self, slides: list) -> "Deck":
        """スライドのリストを結合・設定する。順番の入れ替えやカットにも使用可能。"""
        self._slides = list(slides)
        for s in self._slides:
            s.deck = self
        return self

    def append(self, slide: Slide) -> "Deck":
        """単一のスライドを末尾に追加"""
        slide.deck = self
        self._slides.append(slide)
        return self

    def add_slide(self, slide: Slide) -> "Deck":
        """append のエイリアス"""
        return self.append(slide)

    def extend(self, slides: list) -> "Deck":
        """複数のスライドを末尾に追加"""
        for s in slides:
            s.deck = self
            self._slides.append(s)
        return self
        
    def to_html(self, output_path: str, embed: bool = True, font_embed: bool = False, font_path: str = None):
        from .renderer import render_slide_html
        from .builder import build_full_html
        
        sections = []
        any_charts = False
        for i, slide in enumerate(self._slides):
            sec_html, is_title, has_chart = render_slide_html(slide, embed=embed)
            if has_chart:
                any_charts = True
            if i == 0 and is_title:
                is_first_title = True
            else:
                is_first_title = False
            sections.append(sec_html)
            
        slides_str = "\n".join(sections)
        
        # SlideFactoryからスタイルリストを収集 (重複排除しつつ順序を維持)
        style_paths = []
        for slide in self._slides:
            if hasattr(slide, 'factory') and slide.factory and slide.factory.style:
                if slide.factory.style not in style_paths:
                    style_paths.append(slide.factory.style)

        subset_font_css = ""
        if font_embed:
            if not font_path:
                from .font_subsetter import find_default_font_path
                font_path = find_default_font_path()
                if not font_path:
                    print("Warning: font_embed=True was specified, but font_path is missing and no default system font could be found. Skipping font subsetting.")
                else:
                    print(f"Auto-discovered system font for subsetting: {font_path}")
            
            if font_path:
                from .font_subsetter import generate_subset
                b64_font = generate_subset(font_path, slides_str, output_path=None)
                if b64_font:
                    subset_font_css = f"""<style>
@font-face {{
    font-family: 'SubsetFont';
    src: url('{b64_font}') format('woff2');
    font-display: swap;
}}
:root {{
    --font-main: 'SubsetFont', "BIZ UDPGothic", -apple-system, sans-serif !important;
}}
</style>"""
        
        final_html = build_full_html(
            slides_section_html=slides_str,
            title=self.title,
            single_slide=False,
            is_title_slide=(len(self._slides) > 0 and self._slides[0].template == "title"),
            has_chart=any_charts,
            custom_style_paths=style_paths,
            export_mode="inline",
            subset_font_css=subset_font_css
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"Presentation saved to {output_path}")

    def show(self, height=540):
        """Preview the entire presentation deck with all slides and animations in Jupyter Notebook (1920x1080, 16:9 Full HD)"""
        from IPython.display import display, IFrame
        import base64
        from .renderer import render_slide_html
        from .builder import build_full_html

        sections = []
        is_first_title = False
        any_charts = False
        for i, slide in enumerate(self._slides):
            sec_html, is_title, has_chart = render_slide_html(slide)
            if has_chart:
                any_charts = True
            if i == 0 and is_title:
                is_first_title = True
            sections.append(sec_html)
            
        slides_str = "\n".join(sections)
        
        # SlideFactoryからスタイルリストを収集 (重複排除しつつ順序を維持)
        style_paths = []
        for slide in self._slides:
            if hasattr(slide, 'factory') and slide.factory and slide.factory.style:
                if slide.factory.style not in style_paths:
                    style_paths.append(slide.factory.style)
                    
        preview_html = build_full_html(
            slides_section_html=slides_str,
            title=self.title or "Presentation Deck Preview",
            single_slide=True,
            is_title_slide=is_first_title,
            has_chart=any_charts,
            custom_style_paths=style_paths
        )

        import os
        from IPython.display import display, IFrame
        
        # URL長制限やIPythonのセキュリティ制限（srcdocブロック）を回避するため、
        # カレントディレクトリに一時的なHTMLファイルを作成して IFrame で読み込む
        temp_file = "preview_temp.html"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(preview_html)
            
        display(IFrame(src=f"./{temp_file}", width="100%", height=height))

    def to_zip(self, zip_path: str, font_embed: bool = False, font_path: str = None):
        """
        プレゼンテーション一式を ZIP ファイルとしてエクスポートします。
        HTML 単体ではなく、画像や CSS/JS などの依存ファイルが 'assets/' や 'media/' ディレクトリとして構造化された状態で ZIP に含まれます。
        font_embed=True を指定すると、フォントのサブセット化を実行し同梱します。
        """
        import tempfile
        import shutil
        from pathlib import Path
        from .elements import EXPORT_CONTEXT
        from .renderer import render_slide_html
        from .builder import build_full_html
        
        if not zip_path.endswith('.zip'):
            zip_path += '.zip'
            
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            EXPORT_CONTEXT["export_dir"] = str(tmp_path)
            EXPORT_CONTEXT["media_counter"] = 0
            
            sections = []
            any_charts = False
            for i, slide in enumerate(self._slides):
                sec_html, is_title, has_chart = render_slide_html(slide, embed=False)
                if has_chart:
                    any_charts = True
                sections.append(sec_html)
                
            slides_str = "\n".join(sections)
            
            style_paths = []
            for slide in self._slides:
                if hasattr(slide, 'factory') and slide.factory and slide.factory.style:
                    if slide.factory.style not in style_paths:
                        style_paths.append(slide.factory.style)
                        
            subset_font_css = ""
            if font_embed:
                if not font_path:
                    from .font_subsetter import find_default_font_path
                    font_path = find_default_font_path()
                    if not font_path:
                        print("Warning: font_embed=True was specified, but no system font could be found. Skipping font subsetting.")
                    else:
                        print(f"Auto-discovered system font for subsetting: {font_path}")
                
                if font_path:
                    from .font_subsetter import generate_subset
                    font_out_path = str(tmp_path / "assets" / "fonts" / "subset.woff2")
                    saved_path = generate_subset(font_path, slides_str, output_path=font_out_path)
                    if saved_path:
                        subset_font_css = f"""<style>
@font-face {{
    font-family: 'SubsetFont';
    src: url('assets/fonts/subset.woff2') format('woff2');
    font-display: swap;
}}
:root {{
    --font-main: 'SubsetFont', "BIZ UDPGothic", -apple-system, sans-serif !important;
}}
</style>"""

            final_html = build_full_html(
                slides_section_html=slides_str,
                title=self.title or "Presentation",
                single_slide=False,
                is_title_slide=(len(self._slides) > 0 and self._slides[0].template == "title"),
                has_chart=any_charts,
                custom_style_paths=style_paths,
                export_mode="zip",
                export_dir=tmp_path,
                subset_font_css=subset_font_css
            )
            
            with open(tmp_path / "index.html", "w", encoding="utf-8") as f:
                f.write(final_html)
                
            zip_base_name = str(Path(zip_path).with_suffix(''))
            shutil.make_archive(zip_base_name, 'zip', tmpdir)
            
            EXPORT_CONTEXT["export_dir"] = None
            
        print(f"Presentation successfully exported to {zip_path}")

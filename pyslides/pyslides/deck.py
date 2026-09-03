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
        style: str = None,
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
        self.style = style
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

    def extend(self, slides: list) -> "Deck":
        """複数のスライドを末尾に追加"""
        for s in slides:
            s.deck = self
            self._slides.append(s)
        return self

    def add_slide(self, template: str = "default", **kwargs) -> Slide:
        """後方互換性：新しいスライドを直接生成して追加"""
        slide = Slide(template=template, deck=self, **kwargs)
        self._slides.append(slide)
        return slide
        
    def to_html(self, output_path: str, embed: bool = True):
        from .renderer import render_slide_html
        from .builder import build_full_html
        
        sections = []
        any_charts = False
        for i, slide in enumerate(self._slides):
            sec_html, is_title, has_chart = render_slide_html(slide)
            if has_chart:
                any_charts = True
            if i == 0 and is_title:
                is_first_title = True
            else:
                is_first_title = False
            sections.append(sec_html)
            
        slides_str = "\n".join(sections)
        final_html = build_full_html(
            slides_section_html=slides_str,
            title=self.title,
            single_slide=False,
            is_title_slide=(len(self._slides) > 0 and self._slides[0].template == "title"),
            has_chart=any_charts,
            custom_style_path=self.style
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"Presentation saved to {output_path}")

    def show(self, height=540):
        """Preview the entire presentation deck with all slides and animations in Jupyter Notebook"""
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
        preview_html = build_full_html(
            slides_section_html=slides_str,
            title=self.title or "Presentation Deck Preview",
            single_slide=True,
            is_title_slide=is_first_title,
            has_chart=any_charts,
            custom_style_path=self.style
        )

        b64_html = base64.b64encode(preview_html.encode('utf-8')).decode('utf-8')
        data_url = f"data:text/html;base64,{b64_html}"
        display(IFrame(src=data_url, width="100%", height=height))

import os
import sys
import uuid
import json
from pathlib import Path

from .slide import Slide
from .elements import Chart

class Deck:
    def __init__(self, title: str = "Presentation", theme: str = "default", style: str = None):
        self.title = title
        self.theme = theme
        self.style = style
        self.slides = []
        self._assets_dir = Path(__file__).parent / "assets"
        
    def add_slide(self, template: str = "default", **kwargs) -> Slide:
        slide = Slide(template=template, deck=self, **kwargs)
        self.slides.append(slide)
        return slide
        
    def to_html(self, output_path: str, embed: bool = True):
        # 1. 既存の markdown_parser.py へのパスを通し、パース関数をインポート
        sys.path.insert(0, str(self._assets_dir / "py"))
        try:
            from markdown_parser import markdown_to_html
        except ImportError:
            raise ImportError(f"Cannot import markdown_parser from {self._assets_dir / 'py'}")
            
        # 2. 全スライドのコンテンツを構築
        html_slides = []
        charts_map = {} # id -> Chart object
        
        for slide in self.slides:
            # Gather all markdown lines for this slide
            md_lines = []
            
            if slide.template != "default":
                md_lines.append(f"::: layout({slide.template})")
                
            if slide.template == "title":
                if slide.title: md_lines.append(f'# {slide.title}')
                if slide.author: md_lines.append(slide.author)
            elif slide.template == "agenda":
                if slide.title: md_lines.append(f'# {slide.title}')
                
            for el in slide.elements:
                if hasattr(el, 'to_markdown'):
                    md_lines.append(el.to_markdown())
                elif isinstance(el, Chart):
                    md_lines.append(f"{{{{CHART:{el.id}}}}}")
                    charts_map[el.id] = el
                else: # Markdown element
                    md_lines.append(getattr(el, 'text', ''))
                    
            if slide.template != "default":
                md_lines.append(":::")
                
            md_content = "\n".join(md_lines)
            
            # 3. markdown_parser で HTML変換
            slide_html = markdown_to_html(md_content)
            
            # 4. チャートのプレースホルダーを実際の Plotly <div> に置換
            for chart_id, chart_obj in charts_map.items():
                token = f"{{{{CHART:{chart_id}}}}}"
                if token in slide_html:
                    slide_html = slide_html.replace(token, chart_obj.to_html(embed=embed))
            
            html_slides.append(slide_html)
            
        # 5. Base HTML テンプレートへの流し込み
        # ここでは Reveal.js のスケルトンHTMLを生成
        
        # もし embed=True なら、CSS の内容を読み込んで <style> タグに入れる
        css_content = ""
        if self.style and os.path.exists(self.style):
            with open(self.style, "r", encoding="utf-8") as f:
                css_content = f"<style>\n{f.read()}\n</style>"
        else:
            # Default fallback for 16:9 layout if no style is provided
            pass
            
        if not embed and self.style:
            # External reference (Assuming it's in the correct relative path)
            css_content = f'<link rel="stylesheet" href="{self.style}">'
            
        # 最終的な Reveal.js のスライド群の構成
        slides_html_str = ""
        for s in html_slides:
            slides_html_str += f"<section>\n{s}\n</section>\n"
            
        # グラフを使う場合は Plotly.js を読み込む必要がある
        plotly_js = ""
        if charts_map:
            plotly_js = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
            
        final_html = f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reset.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/theme/white.css">
    {css_content}
    {plotly_js}
</head>
<body>
    <div class="reveal">
        <div class="slides">
            {slides_html_str}
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.js"></script>
    <script>
        Reveal.initialize({{
            hash: true,
            slideNumber: true,
            width: 1920,
            height: 1080,
            margin: 0.04,
            minScale: 0.2,
            maxScale: 2.0
        }});
    </script>
</body>
</html>
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"Presentation saved to {output_path}")

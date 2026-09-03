from .elements import Element, Markdown, Chart

class GridArea:
    def __init__(self, name: str):
        self.name = name
        self.elements = []
        
    @property
    def markdown(self):
        return ""
        
    @markdown.setter
    def markdown(self, text: str):
        self.elements.append(Markdown(text))
        
    @property
    def chart(self):
        return None
        
    @chart.setter
    def chart(self, fig):
        self.elements.append(Chart(fig))

class Grid:
    def __init__(self, col: str = None, row: str = None):
        self.col = col
        self.row = row
        # Common layout areas
        self.left = GridArea("left")
        self.right = GridArea("right")
        self.top = GridArea("top")
        self.bottom = GridArea("bottom")
        self.center = GridArea("center")
        
    def to_markdown(self) -> str:
        """
        現在のMarkdown Parserの構文に合わせて変換する。
        ::: grid(col=...)
        [left contents]
        :: split
        [right contents]
        :::
        というような形を生成する。
        """
        # Collect non-empty areas
        areas = []
        for a in [self.left, self.right, self.top, self.bottom, self.center]:
            if a.elements:
                areas.append(a)
                
        if not areas:
            return ""
            
        params = []
        if self.col: params.append(f"col={self.col}")
        if self.row: params.append(f"row={self.row}")
        
        param_str = f"({','.join(params)})" if params else ""
        lines = [f"::: grid{param_str}"]
        
        for i, area in enumerate(areas):
            if i > 0:
                lines.append(":: split")
            for el in area.elements:
                # Assuming element to_html() or text representation can be used directly
                # However for Chart, the Markdown parser doesn't know about it. 
                # We need a special token to inject the chart later.
                if isinstance(el, Chart):
                    # Placeholder for parser
                    lines.append(f"{{{{CHART:{el.id}}}}}")
                elif isinstance(el, Markdown):
                    lines.append(el.text)
                    
        lines.append(":::")
        return "\n".join(lines)

class Slide:
    def __init__(self, template: str = "default", deck=None, title: str = "", author: str = "", **kwargs):
        self.template = template
        self.deck = deck
        self.attributes = {"title": title, "author": author, **kwargs}
        self.elements = []
        self._grid = None
        
    @property
    def title(self):
        return self.attributes.get("title", "")
        
    @title.setter
    def title(self, value):
        self.attributes["title"] = value

    @property
    def author(self):
        return self.attributes.get("author", "")
        
    @author.setter
    def author(self, value):
        self.attributes["author"] = value
        
    def grid(self, col: str = None, row: str = None) -> Grid:
        self._grid = Grid(col=col, row=row)
        self.elements.append(self._grid)
        return self._grid
        
    @property
    def markdown(self):
        return ""
        
    @markdown.setter
    def markdown(self, text: str):
        self.elements.append(Markdown(text))
        
    @property
    def chart(self):
        return None
        
    @chart.setter
    def chart(self, fig):
        self.elements.append(Chart(fig))
        
    def show(self, height=600):
        """Preview this slide in Jupyter Notebook"""
        from IPython.display import display, IFrame
        import os
        import sys
        import base64
        from .elements import Chart
        
        # Gather markdown lines
        md_lines = []
        if self.template != "default":
            md_lines.append(f"::: layout({self.template})")
            
        if self.template == "title":
            if self.title: md_lines.append(f'# {self.title}')
            if self.author: md_lines.append(self.author)
        elif self.template == "agenda":
            if self.title: md_lines.append(f'# {self.title}')
            
        charts_map = {}
        for el in self.elements:
            if hasattr(el, 'to_markdown'):
                md_lines.append(el.to_markdown())
            elif isinstance(el, Chart):
                md_lines.append(f"{{{{CHART:{el.id}}}}}")
                charts_map[el.id] = el
            else:
                md_lines.append(getattr(el, 'text', ''))
                
        if self.template != "default":
            md_lines.append(":::")
                
        md_content = "\n".join(md_lines)
        
        # Parse markdown
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        if os.path.join(assets_dir, "py") not in sys.path:
            sys.path.insert(0, os.path.join(assets_dir, "py"))
            
        try:
            from markdown_parser import markdown_to_html
            slide_html = markdown_to_html(md_content)
        except ImportError:
            slide_html = f"<pre>{md_content}</pre>"
            
        # Replace Charts
        for chart_id, chart_obj in charts_map.items():
            token = f"{{{{CHART:{chart_id}}}}}"
            if token in slide_html:
                slide_html = slide_html.replace(token, chart_obj.to_html(embed=True))
                
        # Generate preview HTML
        css_content = ""
        if self.deck and self.deck.style and os.path.exists(self.deck.style):
            with open(self.deck.style, "r", encoding="utf-8") as f:
                css_content = f.read()
                
        plotly_js = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>' if charts_map else ""
        
        preview_html = f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reset.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/theme/white.css">
    <style>{css_content}</style>
    {plotly_js}
</head>
<body>
    <div class="reveal">
        <div class="slides">
            <section>{slide_html}</section>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.js"></script>
    <script>
        Reveal.initialize({{
            hash: false,
            slideNumber: false,
            width: 1920,
            height: 1080,
            margin: 0.04,
            minScale: 0.2,
            maxScale: 2.0
        }});
    </script>
</body>
</html>"""

        b64_html = base64.b64encode(preview_html.encode('utf-8')).decode('utf-8')
        data_url = f"data:text/html;base64,{b64_html}"
        display(IFrame(src=data_url, width="100%", height=height))

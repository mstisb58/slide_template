import uuid

class Element:
    def to_html(self, embed: bool) -> str:
        raise NotImplementedError

class Markdown(Element):
    def __init__(self, text: str):
        self.text = text
    
    def to_html(self, embed: bool) -> str:
        return self.text

class Chart(Element):
    def __init__(self, fig):
        """
        :param fig: plotly.graph_objects.Figure
        """
        self.fig = fig
        self.id = "chart_" + uuid.uuid4().hex[:8]
    
    def to_html(self, embed: bool) -> str:
        if self.fig is None:
            return ""
        
        try:
            return self.fig.to_html(full_html=False, include_plotlyjs=False, div_id=self.id)
        except AttributeError:
            return f"<div class='error'>Invalid Chart Object</div>"

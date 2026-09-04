from typing import Union, Tuple, List, Optional
from .elements import Container, Element, Markdown, Chart, Grid, Card, Image, Memo

HighlightStep = Union[str, int, List[int], Tuple[int, ...]]
HighlightOrder = Tuple[HighlightStep, ...]

class HighlightProperty:
    """代入（s.highlight = ...）もメソッド呼び出し（s.highlight("all", 0)）も両方受け付けるハイブリッドプロパティ"""
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        class _CallableHighlight(tuple):
            def __call__(_self, *args):
                if len(args) == 1 and isinstance(args[0], (list, tuple)):
                    instance.highlight_order = tuple(args[0])
                else:
                    instance.highlight_order = tuple(args)
                return instance

        return _CallableHighlight(instance.highlight_order)

    def __set__(self, instance, value):
        if instance is not None:
            if isinstance(value, (list, tuple)):
                instance.highlight_order = tuple(value)
            else:
                instance.highlight_order = (value,)

class Slide(Container):
    def __init__(
        self,
        template: str = "default",
        factory=None,
        title: str = "",
        author: str = "",
        date: str = "",
        subtitle: str = "",
        **kwargs
    ):
        super().__init__()
        self.template = template
        self.factory = factory
        self.deck = None
        self.attributes = {
            "title": title,
            "author": author,
            "date": date,
            "subtitle": subtitle,
            **kwargs
        }

    def __getattr__(self, name):
        # self.__dict__ を直接参照して __getattr__ の無限再帰を完全に防止
        attrs = self.__dict__.get("attributes")
        if attrs is not None and isinstance(attrs, dict) and name in attrs:
            return attrs[name]
        raise AttributeError(f"'Slide' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in ("template", "factory", "deck", "attributes", "elements"):
            super().__setattr__(name, value)
        else:
            attrs = self.__dict__.get("attributes")
            if attrs is not None and isinstance(attrs, dict):
                attrs[name] = value
            super().__setattr__(name, value)

    def __copy__(self):
        import copy
        new_slide = Slide(
            template=self.template,
            factory=self.factory,
            **copy.copy(self.attributes)
        )
        new_slide.elements = copy.copy(self.elements)
        return new_slide

    def __deepcopy__(self, memo):
        import copy
        new_slide = Slide(
            template=self.template,
            factory=self.factory,
            **copy.deepcopy(self.attributes, memo)
        )
        new_slide.elements = copy.deepcopy(self.elements, memo)
        return new_slide

    # 属性アクセサ
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

    @property
    def date(self):
        return self.attributes.get("date", "")

    @date.setter
    def date(self, value):
        self.attributes["date"] = value

    @property
    def subtitle(self):
        return self.attributes.get("subtitle", "")

    @subtitle.setter
    def subtitle(self, value):
        self.attributes["subtitle"] = value

    @property
    def items(self):
        return self.attributes.get("items", self.attributes.get("item", []))

    @items.setter
    def items(self, value):
        self.attributes["items"] = value
        self.attributes["item"] = value

    @property
    def item(self):
        return self.items

    @item.setter
    def item(self, value):
        self.items = value

    @property
    def highlight_order(self) -> HighlightOrder:
        val = self.attributes.get("highlight_order", self.attributes.get("highlight", self.attributes.get("hilight", None)))
        if val is None:
            return ("none",)
        if isinstance(val, (str, int)):
            return (val,)
        if isinstance(val, list):
            return tuple(val)
        return val

    @highlight_order.setter
    def highlight_order(self, value: Union[HighlightOrder, HighlightStep, list]):
        self.attributes["highlight_order"] = value
        self.attributes["highlight"] = value
        self.attributes["hilight"] = value

    highlight = HighlightProperty()
    hilight = HighlightProperty()

    # エイリアス: s.grid(...) -> s.add_grid(...)
    def grid(self, col: Union[int, str] = 2, row: Union[int, str] = 1, gap: str = "16px", height: str = None) -> Grid:
        return self.add_grid(col=col, row=row, gap=gap, height=height)

    def show(self, height=520):
        """Preview this slide in Jupyter Notebook with 1280x720 Golden Ratio Design System"""
        from IPython.display import display, IFrame
        import base64
        from .renderer import render_slide_html
        from .builder import build_full_html

        slide_sec_html, is_title, has_chart = render_slide_html(self)
        custom_style = self.factory.style if self.factory else None
        
        preview_html = build_full_html(
            slides_section_html=slide_sec_html,
            title=self.title or "Slide Preview",
            single_slide=True,
            is_title_slide=is_title,
            has_chart=has_chart,
            custom_style_paths=[custom_style] if custom_style else []
        )

        b64_html = base64.b64encode(preview_html.encode('utf-8')).decode('utf-8')
        data_url = f"data:text/html;base64,{b64_html}"
        if len(data_url) < 2000000:
            display(IFrame(src=data_url, width="100%", height=height))
        else:
            import html
            from IPython.display import HTML
            escaped = html.escape(preview_html, quote=True)
            display(HTML(f'<iframe srcdoc="{escaped}" width="100%" height="{height}" frameborder="0" allowfullscreen style="border:none; width:100%; height:{height}px;"></iframe>'))

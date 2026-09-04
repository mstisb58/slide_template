from typing import Optional
from .slide import Slide

class SlideFactory:
    """
    個別スライドのファクトリクラス。
    共通のスタイルや初期設定を保持し、Slide インスタンスを生成する。
    """
    def __init__(self, style: Optional[str] = None, theme_name: Optional[str] = None):
        self.style = style
        self.theme_name = theme_name

    def create_slide(self, template: str = "default", **kwargs) -> Slide:
        """
        新しいスライドを生成する。
        """
        return Slide(template=template, factory=self, **kwargs)

    def create_section(self, parent: Slide, template: Optional[str] = None, name: Optional[str] = None, **kwargs) -> Slide:
        """
        セクション（縦方向スライド/サブスライド）を生成し、親スライドに紐づける。
        template や title はデフォルトで親のものを引き継ぐ。
        """
        if template is None:
            template = parent.template
            
        if "title" not in kwargs and hasattr(parent, "title"):
            kwargs["title"] = parent.title
            
        sub = self.create_slide(template=template, **kwargs)
        parent.sections.append(sub)
        if name:
            setattr(parent, name, sub)
        return sub

    def create_subslide(self, parent: Slide, template: Optional[str] = None, name: Optional[str] = None, **kwargs) -> Slide:
        """create_section のエイリアス"""
        return self.create_section(parent, template=template, name=name, **kwargs)


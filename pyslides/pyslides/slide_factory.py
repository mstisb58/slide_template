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

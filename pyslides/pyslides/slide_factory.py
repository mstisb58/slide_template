from typing import Optional
from .slide import Slide

class SlideFactory:
    """
    個別スライドのファクトリクラス。
    共通のスタイルや初期設定を保持し、Slide インスタンスを生成する。
    """
    def __init__(self, style: Optional[str] = None, theme_name: Optional[str] = None):
        if style:
            from pathlib import Path
            from .asset_encoder import find_user_assets_dir
            style_p = Path(style)
            if not style_p.exists():
                user_adir = find_user_assets_dir()
                if user_adir:
                    candidate = user_adir / "css" / style
                    if candidate.exists():
                        style = str(candidate)
                    elif (user_adir / "css" / f"{style}.css").exists():
                        style = str(user_adir / "css" / f"{style}.css")
        self.style = style
        self.theme_name = theme_name or "kracie"

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

    @property
    def theme_info(self):
        """
        適用中のテーマやCSSの仕様情報（フォント、カラーパレット、見出しサイズ等）を
        確認できる ThemeInfo オブジェクトを返す。
        Jupyter Notebook 上ではリッチなカード・テーブルでプレビュー表示されます。
        """
        from .theme_info import ThemeInfo
        return ThemeInfo(css_path=self.style, theme_name=self.theme_name)

    @property
    def theme(self):
        """theme_info のエイリアス"""
        return self.theme_info

    @property
    def style_info(self):
        """theme_info のエイリアス"""
        return self.theme_info

    @property
    def design_system(self):
        """theme_info のエイリアス"""
        return self.theme_info

    @property
    def font(self):
        """theme_info のエイリアス"""
        return self.theme_info



import os
import sys
from pathlib import Path

def _render_single_slide_html(slide, assets_dir: Path = None, embed: bool = True) -> tuple[str, bool, bool]:
    """単一スライドの HTML (<section>...)、タイトルフラグ、チャート含有フラグを返す。直接HTMLを構築する。"""
    
    # 1. コンテナツリーを再帰的にHTML化
    parsed_elements_html = slide.to_html(embed=embed)
    has_chart = slide.has_chart()

    # 2. HTMLの直接組み立て
    content_html = []
    
    # 2.5 テーマごとのスコーピング用クラス
    theme_cls = ""
    if hasattr(slide, 'factory') and slide.factory and getattr(slide.factory, 'theme_name', None):
        theme_cls = f' {slide.factory.theme_name}'
        
    sec_cls_attr = f' class="{theme_cls.strip()}"' if theme_cls.strip() else ""
    
    # --- タイトルスライド ---
    if slide.template == "title":
        date_str = getattr(slide, "date", "") or slide.attributes.get("date", "")
        if date_str:
            content_html.append(f'<div class="title-date">{date_str}</div>')
            
        content_html.append('<div class="title-body">')
        if slide.title:
            content_html.append(f'<h1>{slide.title}</h1>')
            
        subtitle = getattr(slide, "subtitle", "") or slide.attributes.get("subtitle", "")
        if subtitle:
            content_html.append(f'<div class="title-subtitle">{subtitle}</div>')
        content_html.append('</div>')
        
        author = getattr(slide, "author", "") or slide.attributes.get("author", "")
        if author:
            author_lines = "<br>".join([line.strip() for line in str(author).split("\n") if line.strip()])
            content_html.append(f'<div class="title-author">{author_lines}</div>')
            
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
            
        inner_html = "\n".join(content_html)
        return f'<section class="title-section{theme_cls}">\n<div class="title-slide">\n{inner_html}\n</div>\n</section>', True, has_chart

    # --- アジェンダスライド ---
    elif slide.template == "agenda":
        if slide.title:
            content_html.append(f'<h2>{slide.title}</h2>')
            
        raw_items = getattr(slide, "items", None) or getattr(slide, "item", None) or slide.attributes.get("items", slide.attributes.get("item", None))
        deck_obj = getattr(slide, "deck", None)
        if not raw_items and deck_obj and getattr(deck_obj, "agenda_items", None):
            raw_items = deck_obj.agenda_items
        raw_items = raw_items or []

        item_pairs = []  # [(key, label), ...]
        if isinstance(raw_items, dict):
            for k, v in raw_items.items():
                item_pairs.append((str(k), str(v)))
        elif isinstance(raw_items, (list, tuple)):
            for idx, val in enumerate(raw_items):
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    item_pairs.append((str(val[0]), str(val[1])))
                else:
                    item_pairs.append((f"{idx + 1:02d}", str(val)))

        hl = getattr(slide, "highlight_order", None)
        if hl is None:
            hl = getattr(slide, "highlight", None)
        if hl is None:
            hl = getattr(slide, "hilight", None)
        if hl is None:
            hl = slide.attributes.get("highlight_order", slide.attributes.get("highlight", slide.attributes.get("hilight", None)))

        def resolve_index(target):
            target_str = str(target).strip()
            # 1. 完全一致（キー文字列、大文字小文字区別なし）
            for i, (k, _) in enumerate(item_pairs):
                if k == target_str or k.lower() == target_str.lower():
                    return i
            # 2. 数字キー互換（"1" と "01" 等）
            if target_str.isdigit():
                target_int = int(target_str)
                for i, (k, _) in enumerate(item_pairs):
                    if k.isdigit() and int(k) == target_int:
                        return i
            # 3. インデックス指定
            if isinstance(target, int) and 0 <= target < len(item_pairs):
                return target
            return None

        def resolve_step(v):
            if isinstance(v, str):
                v_clean = v.lower().strip()
                if v_clean == "all":
                    return "all"
                elif v_clean == "none":
                    return "none"
                elif v_clean in ("gray", "grey"):
                    return "gray"
                else:
                    idx = resolve_index(v)
                    return [idx] if idx is not None else []
            elif isinstance(v, (list, tuple)):
                indices = []
                for sub_v in v:
                    idx = resolve_index(sub_v)
                    if idx is not None:
                        indices.append(idx)
                return indices
            elif isinstance(v, int):
                idx = resolve_index(v)
                return [idx] if idx is not None else []
            return []

        steps = []
        if hl is not None:
            if not isinstance(hl, (list, tuple)):
                hl = [hl]
                    
            for v in hl:
                steps.append(resolve_step(v))

        if not steps and item_pairs:
            steps = ["none"]

        first_step = steps[0] if steps else "none"
        import json
        steps_json = json.dumps(steps)

        container_class = "agenda-list" + (" is-step" if len(steps) > 1 else "")
        content_html.append(f'<div class="{container_class}" data-agenda-steps=\'{steps_json}\'>')
        active_cls = "active-fixed" if len(steps) == 1 else "is-active"

        for idx, (key_label, item_text) in enumerate(item_pairs):
            if first_step == "none":
                cls = "agenda-item"
            elif first_step in ("gray", "grey"):
                cls = "agenda-item dimmed"
            elif first_step == "all":
                cls = f"agenda-item {active_cls}"
            elif isinstance(first_step, list):
                cls = f"agenda-item {active_cls}" if idx in first_step else "agenda-item dimmed"
            else:
                cls = f"agenda-item {active_cls}" if idx == first_step else "agenda-item dimmed"

            content_html.append(f'  <div class="{cls}" data-agenda-index="{idx}" data-agenda-key="{key_label}">')
            content_html.append(f'    <span class="agenda-num">{key_label}</span>')
            content_html.append(f'    <span>{item_text}</span></div>')
        content_html.append('</div>')

        for s_idx in range(1, len(steps)):
            content_html.append(f'<div class="agenda-step-trigger fragment fade-in-highlight" data-fragment-index="{s_idx}"></div>')

        if parsed_elements_html:
            content_html.append(parsed_elements_html)
            
        return f'<section class="agenda-section{theme_cls}">\n' + "\n".join(content_html) + "\n</section>", False, has_chart

    # --- 3. 標準スライド (normal): タイトル(h2)を内蔵 ---
    elif slide.template == "normal":
        sec_cls = f'normal-section normal{theme_cls}'
        if slide.title:
            content_html.append(f'<h2>{slide.title}</h2>')
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
        return f'<section class="{sec_cls}">\n' + "\n".join(content_html) + "\n</section>", False, has_chart

    # --- 4. デフォルトスライド (default): タイトルすらない完全白紙マスタ（ロゴと帯のみ） ---
    elif slide.template == "default":
        sec_cls = f'default-section default{theme_cls}'
        # タイトル(h2)は内蔵しない
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
        return f'<section class="{sec_cls}">\n' + "\n".join(content_html) + "\n</section>", False, has_chart

    else:
        sec_cls = f'{slide.template}-section {slide.template}{theme_cls}'
        if slide.title:
            content_html.append(f'<h2>{slide.title}</h2>')
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
        return f'<section class="{sec_cls}">\n' + "\n".join(content_html) + "\n</section>", False, has_chart

def render_slide_html(slide, assets_dir: Path = None, embed: bool = True) -> tuple[str, bool, bool]:
    parent_html, is_title, has_chart = _render_single_slide_html(slide, assets_dir)
    
    sections = getattr(slide, 'sections', None) or getattr(slide, 'subslides', [])
    if not sections:
        return parent_html, is_title, has_chart
        
    html_parts = ["<section>"]
    html_parts.append(parent_html)
    
    for sub in sections:
        sub_html, _, sub_has_chart = render_slide_html(sub, assets_dir)
        html_parts.append(sub_html)
        if sub_has_chart:
            has_chart = True
            
    html_parts.append("</section>")
    return "\n".join(html_parts), is_title, has_chart

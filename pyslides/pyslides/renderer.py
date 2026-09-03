import os
import sys
from pathlib import Path

def render_slide_html(slide, assets_dir: Path = None) -> tuple[str, bool, bool]:
    """単一スライドの HTML (<section>...)、タイトルフラグ、チャート含有フラグを返す。直接HTMLを構築する。"""
    
    # 1. コンテナツリーを再帰的にHTML化
    parsed_elements_html = slide.to_html(embed=True)
    has_chart = slide.has_chart()

    # 2. HTMLの直接組み立て
    content_html = []
    
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
            content_html.append(f'<div class="subtitle">{subtitle}</div>')
        content_html.append('</div>')
        
        author = getattr(slide, "author", "") or slide.attributes.get("author", "")
        if author:
            author_lines = "<br>".join([line.strip() for line in str(author).split("\n") if line.strip()])
            content_html.append(f'<div class="title-author">{author_lines}</div>')
            
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
            
        inner_html = "\n".join(content_html)
        return f'<section class="title-section">\n<div class="title-slide">\n{inner_html}\n</div>\n</section>', True, has_chart

    # --- アジェンダスライド ---
    elif slide.template == "agenda":
        if slide.title:
            content_html.append(f'<h2>{slide.title}</h2>')
            
        items = getattr(slide, "items", None) or getattr(slide, "item", None) or slide.attributes.get("items", slide.attributes.get("item", None))
        if not items and slide.deck and getattr(slide.deck, "agenda_items", None):
            items = slide.deck.agenda_items
        items = items or []

        hl = getattr(slide, "highlight_order", None)
        if hl is None:
            hl = getattr(slide, "highlight", None)
        if hl is None:
            hl = getattr(slide, "hilight", None)
        if hl is None:
            hl = slide.attributes.get("highlight_order", slide.attributes.get("highlight", slide.attributes.get("hilight", None)))

        steps = []
        if hl is not None:
            if not isinstance(hl, (list, tuple)):
                hl = [hl]
                    
            for v in hl:
                if isinstance(v, str):
                    v = v.lower().strip()
                    if v == "all":
                        steps.append([i for i in range(len(items))])
                    elif v == "none":
                        steps.append([])
                    else:
                        import re
                        m = re.search(r"\d+", v)
                        if m:
                            steps.append([int(m.group(0))])
                elif isinstance(v, (list, tuple)):
                    step_indices = [int(x) for x in v]
                    steps.append(step_indices)
                else:
                    steps.append([int(v)])

        if not steps and items:
            steps = [[i] for i in range(len(items))]

        initial_actives = set(steps[0]) if steps else set()
        import json
        steps_json = json.dumps(steps)

        container_class = "agenda-list" + (" is-step" if len(steps) > 1 else "")
        content_html.append(f'<div class="{container_class}" data-agenda-steps=\'{steps_json}\'>')
        for idx, item_text in enumerate(items):
            active_cls = "active-fixed" if len(steps) == 1 else "is-active"
            cls = f"agenda-item {active_cls}" if idx in initial_actives else "agenda-item dimmed"
            content_html.append(f'  <div class="{cls}" data-agenda-index="{idx}">')
            content_html.append(f'    <span class="agenda-num">{idx + 1:02d}</span>')
            content_html.append(f'    <span>{item_text}</span></div>')
        content_html.append('</div>')

        for s_idx in range(1, len(steps)):
            content_html.append(f'<div class="agenda-step-trigger fragment fade-in-highlight" data-fragment-index="{s_idx}"></div>')

        if parsed_elements_html:
            content_html.append(parsed_elements_html)
            
        return f"<section>\n" + "\n".join(content_html) + "\n</section>", False, has_chart

    # --- その他のレイアウト (chart-focus, compare-3 など) ---
    elif slide.template != "default":
        if slide.title:
            content_html.append(f'<h2>{slide.title}</h2>')
        
        content_html.append(f'<div class="custom-grid {slide.template}">')
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
        content_html.append('</div>')
        return f"<section>\n" + "\n".join(content_html) + "\n</section>", False, has_chart

    # --- デフォルト (通常スライド) ---
    else:
        if slide.title:
            content_html.append(f'<h2>{slide.title}</h2>')
        if parsed_elements_html:
            content_html.append(parsed_elements_html)
        return f"<section>\n" + "\n".join(content_html) + "\n</section>", False, has_chart

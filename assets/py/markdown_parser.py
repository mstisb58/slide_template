"""
Markdownパースおよびカスタム記法変換モジュール
"""
import re


def process_custom_containers(text: str) -> str:
    """
    ::: title, ::: agenda, ::: point, ::: grid-*, ::: card, ::: images-*, ::: step などの独自記法を展開
    """
    # 1. ::: agenda[:option] (目次 ＆ 自由なステップハイライト設定)
    def replace_agenda(match):
        spec = (match.group(1) or "").strip().lower()
        items_raw = match.group(2).strip().split("\n")

        # 項目リストの抽出
        valid_items = []
        for item in items_raw:
            cleaned = re.sub(r"^\d+\.\s*", "", item.strip())
            if cleaned:
                valid_items.append(cleaned)

        total_items = len(valid_items)

        # パース: どの項目をどの順番でハイライトするか
        fragment_order = {}  # {item_index (1-indexed): fragment_index (1-indexed)}
        fixed_active = None
        is_step = False

        if not spec or spec == "auto" or spec == "all" or spec == "step":
            # デフォルト: 全項目を 1 -> 2 -> ... -> N で順番にハイライト
            is_step = True
            for i in range(1, total_items + 1):
                fragment_order[i] = i
        elif spec == "none" or spec == "off":
            # ステップアニメーションなし (最初から全員通常表示)
            is_step = False
        elif spec.startswith("fixed:"):
            # 特定項目を固定ハイライト
            try:
                fixed_active = int(spec.split(":")[1])
            except ValueError:
                fixed_active = None
        elif "," in spec or "->" in spec:
            # カンマまたは矢印区切りのシーケンス (例: 1,3 または 1->2->3)
            is_step = True
            parts = re.split(r"[,->]+", spec)
            step_idx = 1
            for p in parts:
                p = p.strip()
                if p.isdigit():
                    idx = int(p)
                    if 1 <= idx <= total_items:
                        fragment_order[idx] = step_idx
                        step_idx += 1
        elif spec.isdigit():
            # 単一の番号指定 (例: ::: agenda:2 -> 2番目だけをハイライト)
            is_step = True
            target = int(spec)
            if 1 <= target <= total_items:
                fragment_order[target] = 1
        else:
            is_step = True
            for i in range(1, total_items + 1):
                fragment_order[i] = i

        container_classes = ["agenda-list"]
        if is_step:
            container_classes.append("is-step")

        agenda_html = [f'<div class="{" ".join(container_classes)}">']

        for idx, item_text in enumerate(valid_items, start=1):
            item_classes = ["agenda-item"]
            attrs = []

            if is_step and idx in fragment_order:
                item_classes.append("fragment")
                attrs.append(f'data-fragment-index="{fragment_order[idx]}"')

            if fixed_active == idx:
                item_classes.append("is-active")

            attr_str = (" " + " ".join(attrs)) if attrs else ""
            agenda_html.append(f'  <div class="{" ".join(item_classes)}"{attr_str}><span class="agenda-num">{idx:02d}</span> <span>{item_text}</span></div>')

        agenda_html.append('</div>')
        return "\n".join(agenda_html)

    text = re.sub(r":::\s*agenda(?::([a-zA-Z0-9_,:-]+))?\s*\n(.*?)\n:::", replace_agenda, text, flags=re.DOTALL)

    # 2. ::: point (強調ボックス: 内部にgridや画像をネスト可能)
    text = re.sub(r":::\s*point\s*", r'<div class="point-box">\n', text)

    # 2.5. ::: images-2, ::: images-3 (画像横並びレイアウト: 高さ自由指定 ::: images-2:260 または ::: images-2:h=260px に対応)
    def replace_images_2(match):
        opt = match.group(1)
        content = match.group(2)
        style = ""
        if opt:
            h = opt.replace("h=", "").replace("height=", "").strip()
            if h.isdigit():
                h += "px"
            style = f' style="--img-max-h: {h};"'
        return f'<div class="images-2"{style}>\n{content}\n</div>'

    def replace_images_3(match):
        opt = match.group(1)
        content = match.group(2)
        style = ""
        if opt:
            h = opt.replace("h=", "").replace("height=", "").strip()
            if h.isdigit():
                h += "px"
            style = f' style="--img-max-h: {h};"'
        return f'<div class="images-3"{style}>\n{content}\n</div>'

    text = re.sub(r":::\s*images-2(?::([^\n]+))?\s*\n(.*?)\n:::", replace_images_2, text, flags=re.DOTALL)
    text = re.sub(r":::\s*images-3(?::([^\n]+))?\s*\n(.*?)\n:::", replace_images_3, text, flags=re.DOTALL)

    # 3. ::: title (表紙レイアウト: 左上日付、中央タイトル、下部サブタイトル、右下発表者名)
    def replace_title(match):
        lines = [l.strip() for l in match.group(1).strip().split("\n") if l.strip() and not l.strip().startswith("<!--")]
        date_lines = []
        title_line = ""
        sub_lines = []
        author_line = ""

        mode = "title"
        for line in lines:
            if re.match(r"^20\d{2}[/-]?\d{1,2}[/-]?\d{1,2}$", line) or "年" in line:
                date_lines.append(line)
            elif line.startswith("# ") or line.startswith("## "):
                title_line = re.sub(r"^#+\s*", "", line)
                mode = "sub"
            elif mode == "sub" and not author_line and (len(lines) > 2 and line == lines[-1]):
                author_line = line
            elif mode == "sub":
                sub_lines.append(line)
            else:
                author_line = line

        html = ['<div class="title-slide">']
        if date_lines:
            html.append(f'  <div class="title-date">{"<br>".join(date_lines)}</div>')
        html.append('  <div class="title-body">')
        if title_line:
            html.append(f'    <h1>{title_line}</h1>')
        for sub in sub_lines:
            html.append(f'    <p class="title-subtitle">{sub}</p>')
        html.append('  </div>')

        if author_line:
            html.append(f'  <div class="title-author">{author_line}</div>')
        html.append('</div>')
        return "\n".join(html)

    text = re.sub(r":::\s*title\s*\n(.*?)\n:::", replace_title, text, flags=re.DOTALL)

    # 4. ::: fragment (段階表示)
    text = re.sub(r":::\s*fragment\s*\n(.*?)\n:::", r'<div class="fragment">\n\1\n</div>', text, flags=re.DOTALL)

    # 5. ::: step (内部の箇条書きを自動で1行ずつフェードイン)
    def replace_step(match):
        content = match.group(1).strip().split("\n")
        res = []
        for line in content:
            s = line.strip()
            if s.startswith("- ") or s.startswith("* "):
                res.append(f'<li class="fragment">{s[2:]}</li>')
            else:
                res.append(f'<div class="fragment">{line}</div>')
        return '<ul style="margin-left:24px;">\n' + "\n".join(res) + "\n</ul>"

    text = re.sub(r":::\s*step\s*\n(.*?)\n:::", replace_step, text, flags=re.DOTALL)

    # 6. 2カラムレイアウト (::: grid-2, ::: grid-2:1, ::: grid-1:2, ::: grid-3:1) - splitとペアで完全タグ生成
    def replace_2col_grid(match):
        raw_spec = match.group(1) or "2"
        left_content = match.group(2).strip()
        right_content = match.group(3).strip()

        # "2:1" や "2:1:350" や "2-1" などをパース
        parts = raw_spec.replace('-', ':').split(':')
        ratio_parts = []
        height_val = "360px"

        for p in parts:
            p_clean = p.strip()
            if not p_clean:
                continue
            if p_clean.endswith("px") or p_clean.endswith("%") or p_clean.startswith("h="):
                h = p_clean.replace("h=", "").replace("height=", "").strip()
                if h.isdigit():
                    h += "px"
                height_val = h
            elif len(ratio_parts) < 2 and p_clean.isdigit() and int(p_clean) > 0:
                ratio_parts.append(p_clean)

        ratio_cls = "-".join(ratio_parts) if ratio_parts else "2"
        col_style = 'style="min-width: 0; max-width: 100%; overflow: hidden; box-sizing: border-box; height: 100%;"'
        return f'<div class="grid-{ratio_cls}" style="--grid-h: {height_val}; height: {height_val};">\n<div {col_style}>\n{left_content}\n</div>\n<div {col_style}>\n{right_content}\n</div>\n</div>'


    # 3カラムグリッド (::: grid-3 / ::: grid3 / ::: grid-3:280 / ::: grid-3:60%) - split 2つ対応
    def replace_3col_split_grid(match):
        opt = match.group(1)
        col1 = match.group(2).strip()
        col2 = match.group(3).strip()
        col3 = match.group(4).strip()

        h_val = "300px"
        if opt:
            h = opt.replace("h=", "").replace("height=", "").strip()
            if h.isdigit():
                h += "px"
            h_val = h

        grid_style = f'style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; width: 100%; max-width: 100%; box-sizing: border-box; --grid-h: {h_val}; height: {h_val};"'
        col_style = 'style="min-width: 0; max-width: 100%; overflow: hidden; box-sizing: border-box; height: 100%;"'
        return f'<div class="grid-3" {grid_style}>\n<div {col_style}>\n{col1}\n</div>\n<div {col_style}>\n{col2}\n</div>\n<div {col_style}>\n{col3}\n</div>\n</div>'


    text = re.sub(r":::\s*grid-?3(?::([^\n]+))?\s*\n(.*?)\n:::\s*split\s*\n(.*?)\n:::\s*split\s*\n(.*?)(?:\n\s*:::|\n(?=---)|\Z)", replace_3col_split_grid, text, flags=re.DOTALL)
    text = re.sub(r":::\s*grid-?([0-9:-]+)\s*\n(.*?)\n:::\s*split\s*\n(.*?)(?:\n\s*:::|\n(?=---)|\Z)", replace_2col_grid, text, flags=re.DOTALL)
    text = re.sub(r":::\s*grid-?2\s*\n(.*?)\n:::\s*split\s*\n(.*?)(?:\n\s*:::|\n(?=---)|\Z)", lambda m: f'<div class="grid-2">\n<div>\n{m.group(1).strip()}\n</div>\n<div>\n{m.group(2).strip()}\n</div>\n</div>', text, flags=re.DOTALL)

    # 6.5. 3カラムグリッド開始タグ (単独使用時)
    def replace_grid_3_start(m):
        opt = m.group(1)
        style = ""
        if opt:
            h = opt.replace("h=", "").replace("height=", "").strip()
            if h.isdigit():
                h += "px"
            style = f' style="--grid-h: {h}; height: {h};"'
        return f'<div class="grid-3"{style}>\n'

    text = re.sub(r":::\s*grid-?3(?::([^\n]+))?\s*", replace_grid_3_start, text)



    # 7. カードの色バリエーション (::: card:blue, ::: card:red, ::: card:yellow, ::: card:bg="#...")
    def replace_card(m):
        variant = m.group(1)
        if not variant:
            return '<div class="card">\n'
        v = variant.strip().lower()
        if v.startswith('bg='):
            color_val = variant.strip()[3:].strip(' "\'')
            return f'<div class="card" style="background: {color_val};">\n'
        return f'<div class="card card-{v}">\n'

    text = re.sub(r":::\s*card(?::([^\n]+))?\s*", replace_card, text)
    text = re.sub(r"^:::\s*$", r'</div>', text, flags=re.MULTILINE)
    text = re.sub(r":::\s*", r'</div>\n', text)

    return text




def parse_markdown_table(lines: list, start_idx: int) -> tuple[str, int]:
    """
    MarkdownテーブルをHTMLテーブルに変換
    """
    table_lines = []
    idx = start_idx
    while idx < len(lines) and "|" in lines[idx]:
        table_lines.append(lines[idx].strip())
        idx += 1

    if len(table_lines) < 2:
        return "<p>" + lines[start_idx] + "</p>", start_idx + 1

    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    
    html = ['<table>', '  <thead>', '    <tr>']
    for h in headers:
        html.append(f'      <th>{h}</th>')
    html.extend(['    </tr>', '  </thead>', '  <tbody>'])

    for row in table_lines[2:]:
        cols = [c.strip() for c in row.strip("|").split("|")]
        html.append('    <tr>')
        for c in cols:
            html.append(f'      <td>{parse_inline_markdown(c)}</td>')
        html.append('    </tr>')

    html.extend(['  </tbody>', '</table>'])
    return "\n".join(html), idx


def markdown_to_html(md_text: str) -> str:
    """
    Markdownテキストを行単位でパースしてHTMLに変換。
    """
    md_text = process_custom_containers(md_text)

    lines = md_text.strip().split("\n")
    html_lines = []
    in_list = False
    list_type = "ul"
    in_code_block = False
    code_block_lines = []
    code_lang = ""

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # コードブロック
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_block_lines = []
            else:
                in_code_block = False
                code_content = "\n".join(code_block_lines)
                code_content = code_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<pre><code class="language-{code_lang}">{code_content}</code></pre>')
            idx += 1
            continue

        if in_code_block:
            code_block_lines.append(line)
            idx += 1
            continue

        # リストの終了判定
        is_list_item = stripped.startswith("- ") or stripped.startswith("* ") or re.match(r"^\d+\.\s", stripped)
        if in_list and not is_list_item:
            html_lines.append(f"</{list_type}>")
            in_list = False

        # 空行
        if not stripped:
            idx += 1
            continue

        # HTMLタグ直書き行
        if stripped.startswith("<") and stripped.endswith(">") and not stripped.startswith("<!--"):
            html_lines.append(line)
            idx += 1
            continue

        # 単独の画像記法 ![alt](url)
        if re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped):
            html_lines.append(parse_inline_markdown(stripped))
            idx += 1
            continue

        # インクルード記法 ::include(...)::
        if stripped.startswith("::include(") and stripped.endswith(")::"):
            html_lines.append(stripped)
            idx += 1
            continue

        # Markdownテーブル
        if "|" in stripped and idx + 1 < len(lines) and re.match(r"^\|?\s*[-:]+[-| :]*$", lines[idx+1].strip()):
            tbl_html, idx = parse_markdown_table(lines, idx)
            html_lines.append(tbl_html)
            continue

        # 数式ブロック $$ ... $$
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            html_lines.append(f'<div class="math-display">{stripped}</div>')
            idx += 1
            continue

        # 見出し
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
            idx += 1
            continue
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
            idx += 1
            continue
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
            idx += 1
            continue

        # 箇条書きリスト
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list or list_type != "ul":
                if in_list: html_lines.append(f"</{list_type}>")
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            content = parse_inline_markdown(stripped[2:])
            html_lines.append(f"  <li>{content}</li>")
            idx += 1
            continue

        # 番号付きリスト
        m_num = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m_num:
            if not in_list or list_type != "ol":
                if in_list: html_lines.append(f"</{list_type}>")
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            content = parse_inline_markdown(m_num.group(2))
            html_lines.append(f"  <li>{content}</li>")
            idx += 1
            continue

        # 引用ブロック
        if stripped.startswith("> "):
            content = parse_inline_markdown(stripped[2:])
            html_lines.append(f"<blockquote>{content}</blockquote>")
            idx += 1
            continue

        # 通常の段落
        content = parse_inline_markdown(line)
        html_lines.append(f"<p>{content}</p>")
        idx += 1


    if in_list:
        html_lines.append(f"</{list_type}>")

    return "\n".join(html_lines)


def parse_inline_markdown(text: str) -> str:
    """
    インラインMarkdown記法（太字、斜体、画像、リンク、インラインコード等）を変換
    """
    # インラインコード
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # 太字
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # 斜体
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    # 画像: ![alt](url)
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img src="\2" alt="\1" class="slide-img">', text)
    # リンク: [text](url)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" target="_blank">\1</a>', text)
    return text


def split_slides(md_text: str) -> list:
    """
    --- (横送り) と -- (縦送り) でスライドをネスト構造に分割。
    """
    h_slides_raw = re.split(r"\n---\n", md_text)
    slides_structure = []

    for h_raw in h_slides_raw:
        if not h_raw.strip():
            continue
        v_slides_raw = re.split(r"\n--\n", h_raw)
        v_list = [v.strip() for v in v_slides_raw if v.strip()]
        if len(v_list) == 1:
            slides_structure.append(v_list[0])
        else:
            slides_structure.append(v_list)

    return slides_structure

"""
Markdownパースおよびカスタム記法変換モジュール
"""
import re


def _parse_paren_args(raw: str) -> tuple[list[str], dict[str, str]]:
    """
    カッコ内の引数文字列 (例: 'col=2:1, row=1, h=250px') を
    位置引数リストとキーワード引数辞書に分解する。
    """
    if not raw:
        return [], {}

    s = raw.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()

    parts = [p.strip() for p in s.split(",") if p.strip()]
    positional = []
    kwargs = {}

    for p in parts:
        p_clean = p.strip("'\"")
        if "=" in p:
            k, v = p.split("=", 1)
            kwargs[k.strip().lower()] = v.strip().strip("'\"")
        else:
            positional.append(p_clean)

    return positional, kwargs


def _parse_agenda(text: str) -> str:
    def replace_agenda(match):
        raw_opt = match.group(1) or match.group(2) or ""
        items_raw = match.group(3).strip().split("\n")

        valid_items = []
        for item in items_raw:
            cleaned = re.sub(r"^\d+\.\s*", "", item.strip())
            if cleaned:
                valid_items.append(cleaned)

        total_items = len(valid_items)
        steps = []
        
        # JSON形式の拡張設定をチェック
        raw_opt_clean = raw_opt.strip("'\" \t\r\n")
        if raw_opt_clean.startswith("{") and raw_opt_clean.endswith("}"):
            try:
                import json
                data = json.loads(raw_opt_clean)
                steps = data.get("steps", [])
            except Exception:
                pass
        else:
            # 従来の文字列形式 (1->5, fixed=1, 等) の互換処理
            pos, kwargs = _parse_paren_args(raw_opt)
            spec = (pos[0] if pos else kwargs.get("highlight", "")).strip().lower()
            
            if not spec or spec in ("auto", "all", "step"):
                steps = [[i] for i in range(total_items)]
            elif spec in ("none", "off"):
                steps = []
            elif spec.startswith("fixed"):
                target_num = spec.replace("fixed", "").replace(":", "").replace("=", "").strip()
                if target_num.isdigit():
                    v = int(target_num)
                    steps = [[v - 1 if v > 0 else 0]]
            elif "," in spec or "->" in spec:
                parts = re.split(r"[,->]+", spec)
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        idx = int(p)
                        if 1 <= idx <= total_items:
                            steps.append([idx - 1])
            elif spec.isdigit():
                target = int(spec)
                if 1 <= target <= total_items:
                    steps.append([target - 1])

        # stepsが空でアイテムがある場合はデフォルトで順次ハイライト
        if not steps and valid_items:
            steps = [[i] for i in range(total_items)]

        initial_actives = set(steps[0]) if steps else set()
        
        import json
        steps_json = json.dumps(steps)
        agenda_html = [f'<div class="agenda-list" data-agenda-steps=\'{steps_json}\'>']
        
        for idx, item_text in enumerate(valid_items):
            cls = "agenda-item is-active" if idx in initial_actives else "agenda-item dimmed"
            agenda_html.append(f'  <div class="{cls}" data-agenda-index="{idx}">')
            agenda_html.append(f'    <span class="agenda-num">{idx + 1:02d}</span>')
            agenda_html.append(f'    <span>{item_text}</span></div>')
        agenda_html.append('</div>')

        # ステップトリガー
        for s_idx in range(1, len(steps)):
            agenda_html.append(f'<div class="agenda-step-trigger fragment" data-fragment-index="{s_idx}"></div>')

        return "\n".join(agenda_html)

    return re.sub(r":::\s*agenda(?:\(([^)\n]*)\)|:([^\n]+))?\s*\n(.*?)\n:::", replace_agenda, text, flags=re.DOTALL)


def _parse_images(text: str) -> str:
    def replace_images(match):
        raw_args = match.group(1) or match.group(3) or ""
        num_str = match.group(2)
        pos, kwargs = _parse_paren_args(raw_args)

        count = 2
        if num_str in ("2", "3"):
            count = int(num_str)
        elif pos and pos[0] in ("2", "3"):
            count = int(pos[0])

        h_val = kwargs.get("h") or kwargs.get("height") or (pos[1] if len(pos) > 1 else (pos[0] if pos and pos[0] not in ("2", "3") else "340px"))
        if h_val.isdigit():
            h_val += "px"

        content = match.group(4).strip()
        style = f' style="--img-max-h: {h_val};"'
        return f'<div class="images-{count}"{style}>\n{content}\n</div>'

    return re.sub(r":::\s*images(?:\(([^)\n]+)\)|-([23])(?::([^\n]+))?)\s*\n(.*?)\n:::", replace_images, text, flags=re.DOTALL)


def _parse_title(text: str) -> str:
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

    return re.sub(r":::\s*title\s*\n(.*?)\n:::", replace_title, text, flags=re.DOTALL)


def _parse_step(text: str) -> str:
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
    return re.sub(r":::\s*step\s*\n(.*?)\n:::", replace_step, text, flags=re.DOTALL)


def _parse_grid(text: str) -> str:
    """
    汎用 N×M グリッドシステム
    ::: grid(col=3, row=2, h=480px)
    ::: split で各セルを区切る。
    厳格に row のみ受け付け、タイポ (raw など) は認識しない。
    """
    lines = text.split("\n")
    out_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("::: grid(") or stripped.startswith(":::grid("):
            # カッコ内の引数を解析
            raw_args = stripped[stripped.index("(") + 1 : stripped.rindex(")")].strip()
            pos, kwargs = _parse_paren_args(raw_args)

            # 列数 / 比率 (col): 均等 (例: 2, 3) または 比率 (例: 2:1, 1:2:1)
            raw_col = kwargs.get("col") or (pos[0] if pos else "2")
            if ":" in str(raw_col):
                col_parts = [c.strip() for c in str(raw_col).split(":") if c.strip()]
                col_style = " ".join([f"{c}fr" for c in col_parts])
            elif str(raw_col).isdigit():
                col_style = f"repeat({raw_col}, minmax(0, 1fr))"
            else:
                col_style = "repeat(2, minmax(0, 1fr))"

            # 行数 / 比率 (row): 厳格に row のみ。均等 (例: 1, 2) または 比率 (例: 2:1, 1:2)
            raw_row = kwargs.get("row") or (pos[1] if len(pos) > 1 else "1")
            if ":" in str(raw_row):
                row_parts = [r.strip() for r in str(raw_row).split(":") if r.strip()]
                row_style = " ".join([f"{r}fr" for r in row_parts])
            elif str(raw_row).isdigit():
                row_style = f"repeat({raw_row}, minmax(0, 1fr))"
            else:
                row_style = "repeat(1, minmax(0, 1fr))"

            # 高さ (h または height) - 指定がなければ自動で下までめいっぱい伸びる
            h_val = kwargs.get("h") or kwargs.get("height")
            if not h_val:
                for p in pos:
                    if p.endswith("px") or p.endswith("%"):
                        h_val = p
                        break
            if h_val and h_val.isdigit():
                h_val += "px"

            gap_val = kwargs.get("gap", "16px")
            if gap_val.isdigit():
                gap_val += "px"

            # 閉じタグ ::: までの深さを追跡
            depth = 1
            block_lines = []
            i += 1

            while i < len(lines):
                cur_line = lines[i]
                cur_strip = cur_line.strip()

                if cur_strip.startswith("::: grid") or cur_strip.startswith("::: card") or cur_strip.startswith("::: point"):
                    depth += 1
                    block_lines.append(cur_line)
                elif cur_strip == ":::":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                    else:
                        block_lines.append(cur_line)
                else:
                    block_lines.append(cur_line)
                i += 1

            # block_lines を :: split または ::: split でセル分割
            cells = [[]]
            for bl in block_lines:
                bs = bl.strip()
                if bs in (":: split", "::split", "::: split", ":::split"):
                    cells.append([])
                else:
                    cells[-1].append(bl)

            cell_htmls = []
            for c in cells:
                cell_content = "\n".join(c).strip()
                cell_htmls.append(f'<div class="grid-cell">\n{cell_content}\n</div>')

            style_parts = [
                f"grid-template-columns: {col_style}",
                f"grid-template-rows: {row_style}",
                f"gap: {gap_val}",
            ]
            if h_val:
                style_parts.append(f"height: {h_val}")
                style_parts.append(f"flex: 0 0 {h_val}")
            
            grid_style = f'style="{"; ".join(style_parts)};"'

            out_lines.append(f'<div class="custom-grid" {grid_style}>\n' + "\n".join(cell_htmls) + '\n</div>')
        else:
            out_lines.append(line)
            i += 1

    return "\n".join(out_lines)


def _parse_card(text: str) -> str:
    def replace_card(m):
        raw_args = m.group(1) or m.group(2) or ""
        if not raw_args:
            return '<div class="card">\n'

        pos, kwargs = _parse_paren_args(raw_args)

        color = ""
        styles = []

        for p in pos:
            p_lower = p.lower()
            if p_lower in ("yellow", "red", "blue", "gold", "green"):
                color = p_lower
            elif p_lower.startswith("bg="):
                styles.append(f"background: {p[3:].strip(' \"\'')};")
            elif p_lower.endswith("px") or p_lower.endswith("%") or p_lower.isdigit():
                h = p_lower if (p_lower.endswith("px") or p_lower.endswith("%")) else p_lower + "px"
                styles.append(f"height: {h}; min-height: {h};")

        if "color" in kwargs:
            color = kwargs["color"].lower()
        if "bg" in kwargs:
            styles.append(f"background: {kwargs['bg']};")
        if "h" in kwargs or "height" in kwargs:
            h = kwargs.get("h") or kwargs.get("height")
        cls = f"card card-{color}" if color else "card"
        style_attr = f' style="{" ".join(styles)}"' if styles else ""
        return f'<div class="{cls}"{style_attr}>\n'

    return re.sub(r":::\s*card(?:\(([^)\n]+)\)|:([^\n]+))?\s*", replace_card, text)


def _parse_layouts(text: str) -> str:
    """
    PowerPoint風マスタースライド レイアウトテンプレートの堅牢な行ベースパース
    ネストする ::: memo や ::: card の深さ (depth) を正しく追跡してパースする。
    """
    text = re.sub(r":::\s*layout\s*\(title\)\s*", "::: title\n", text)
    text = re.sub(r":::\s*layout:title\s*", "::: title\n", text)
    text = re.sub(r":::\s*layout\s*\(agenda(?:,\s*([^)\n]+))?\)\s*", r"::: agenda(\1)\n", text)
    text = re.sub(r":::\s*layout:agenda(?::([^\n]+))?\s*", r"::: agenda:\1\n", text)

    lines = text.split("\n")
    out_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("::: layout") or stripped.startswith(":::layout"):
            raw_args = stripped.replace("::: layout", "").replace(":::layout", "").strip()
            pos, kwargs = _parse_paren_args(raw_args)

            layout_type = pos[0].lower() if pos else "compare-3"
            layout_h = kwargs.get("h") or kwargs.get("height")
            if layout_h and layout_h.isdigit():
                layout_h += "px"
            layout_style = f' style="height: {layout_h}; max-height: {layout_h};"' if layout_h else ""

            # ネスト深度を追跡して外側のブロックを抽出
            depth = 1
            block_lines = []
            i += 1

            while i < len(lines):
                cur_line = lines[i]
                cur_strip = cur_line.strip()

                if cur_strip.startswith("::: memo") or cur_strip.startswith("::: card") or cur_strip.startswith("::: point"):
                    depth += 1
                    block_lines.append(cur_line)
                elif cur_strip == ":::":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                    else:
                        block_lines.append(cur_line)
                else:
                    block_lines.append(cur_line)
                i += 1

            # block_lines から memo (::: memo ... :::) を分離抽出
            memo_lines = []
            non_memo_lines = []
            in_memo = False
            for bl in block_lines:
                bs = bl.strip()
                if bs.startswith("::: memo") or bs == ":::memo":
                    in_memo = True
                    continue
                elif in_memo and bs == ":::":
                    in_memo = False
                    continue
                if in_memo:
                    memo_lines.append(bl)
                else:
                    non_memo_lines.append(bl)

            memo_html = f'<div class="layout-memo">\n' + "\n".join(memo_lines) + '\n</div>' if memo_lines else ""

            # レイアウト別の組み立て
            if layout_type == "chart-focus":
                header_lines = []
                chart_lines = []
                in_header = True
                for nl in non_memo_lines:
                    ns = nl.strip()
                    if in_header:
                        if ns.startswith("::include(") or ns.startswith("![") or ns.startswith("<img") or ns.startswith("<div"):
                            in_header = False
                            chart_lines.append(nl)
                        else:
                            header_lines.append(nl)
                    else:
                        chart_lines.append(nl)

                h_text = "\n".join(header_lines).strip()
                c_text = "\n".join(chart_lines).strip()
                out_lines.append(f'<div class="slide-layout layout-chart-focus"{layout_style}>\n<div class="layout-header">\n{h_text}\n</div>\n<div class="layout-chart-area">\n{c_text}\n</div>\n{memo_html}\n</div>')

            elif layout_type == "chart-split":
                # ::: split で左右分割
                left_lines = []
                right_lines = []
                target_col = left_lines
                for nl in non_memo_lines:
                    ns = nl.strip()
                    if ns in (":: split", "::split", "::: split", ":::split"):
                        target_col = right_lines
                    else:
                        target_col.append(nl)

                # left_lines からヘッダーを分離
                header_lines = []
                chart_lines = []
                in_header = True
                for ll in left_lines:
                    ls = ll.strip()
                    if in_header:
                        if ls.startswith("::include(") or ls.startswith("![") or ls.startswith("<img") or ls.startswith("<div") or ls.startswith("|"):
                            in_header = False
                            chart_lines.append(ll)
                        else:
                            header_lines.append(ll)
                    else:
                        chart_lines.append(ll)

                h_text = "\n".join(header_lines).strip()
                left_text = "\n".join(chart_lines).strip()
                right_text = "\n".join(right_lines).strip()
                out_lines.append(f'<div class="slide-layout layout-chart-split"{layout_style}>\n<div class="layout-header">\n{h_text}\n</div>\n<div class="layout-split-area">\n<div class="layout-left-col">\n{left_text}\n</div>\n<div class="layout-right-col">\n{right_text}\n</div>\n</div>\n{memo_html}\n</div>')

            elif layout_type == "compare-3":
                # :: split または ::: split で最大3カラムに分割
                cols = [[]]
                for nl in non_memo_lines:
                    ns = nl.strip()
                    if ns in (":: split", "::split", "::: split", ":::split"):
                        cols.append([])
                    else:
                        cols[-1].append(nl)

                # 第1カラムからヘッダーを分離
                first_col = cols[0]
                header_lines = []
                col1_lines = []
                in_header = True
                for fl in first_col:
                    fs = fl.strip()
                    if in_header:
                        if fs.startswith("::include(") or fs.startswith("![") or fs.startswith("<img") or fs.startswith("<div") or fs.startswith("|") or fs.startswith(":::"):
                            in_header = False
                            col1_lines.append(fl)
                        else:
                            header_lines.append(fl)
                    else:
                        col1_lines.append(fl)

                h_text = "\n".join(header_lines).strip()
                clean_cols = ["\n".join(col1_lines).strip()]
                for other_c in cols[1:3]:
                    clean_cols.append("\n".join(other_c).strip())
                while len(clean_cols) < 3:
                    clean_cols.append("")

                cols_html = "\n".join([f'<div class="layout-compare-col">\n{cc}\n</div>' for cc in clean_cols])
                out_lines.append(f'<div class="slide-layout layout-compare-3"{layout_style}>\n<div class="layout-header">\n{h_text}\n</div>\n<div class="layout-compare-area">\n{cols_html}\n</div>\n{memo_html}\n</div>')

            elif layout_type == "summary":
                # ::: card を抽出
                card_list = []
                cur_card = []
                in_card = False
                header_lines = []

                for nl in non_memo_lines:
                    ns = nl.strip()
                    if ns.startswith("::: card") or ns == ":::card":
                        in_card = True
                        cur_card = []
                        continue
                    elif in_card and ns == ":::":
                        in_card = False
                        card_list.append("\n".join(cur_card).strip())
                        continue

                    if in_card:
                        cur_card.append(nl)
                    else:
                        header_lines.append(nl)

                h_lines = []
                lead_lines = []
                for hl in header_lines:
                    hs = hl.strip()
                    if hs.startswith("#"):
                        h_lines.append(hl)
                    elif hs:
                        lead_lines.append(hl)

                h_text = "\n".join(h_lines).strip()
                lead_html = f'<div class="layout-lead">{"<br>".join(lead_lines)}</div>' if lead_lines else ""
                cards_html = "\n".join([f'<div class="summary-card">\n{cd}\n</div>' for cd in card_list])
                cards_area = f'<div class="layout-cards-area">\n{cards_html}\n</div>' if card_list else ""

                out_lines.append(f'<div class="slide-layout layout-summary"{layout_style}>\n<div class="layout-header">\n{h_text}\n</div>\n{lead_html}\n{cards_area}\n</div>')
            else:
                out_lines.append("\n".join(block_lines))
        else:
            out_lines.append(line)
            i += 1

    return "\n".join(out_lines)


def _parse_memo(text: str) -> str:
    """
    どのスライドでも単独で使える ::: memo ... ::: 記法
    """
    return re.sub(r":::\s*memo\s*\n(.*?)\n:::", r'<div class="layout-memo">\n\1\n</div>', text, flags=re.DOTALL)


def process_custom_containers(text: str) -> str:
    """
    ::: title, ::: agenda, ::: layout:*, ::: point, ::: grid, ::: card, ::: step, ::: memo などの独自記法を展開
    """
    text = _parse_layouts(text)
    text = _parse_agenda(text)
    text = re.sub(r":::\s*point\s*", r'<div class="point-box">\n', text)
    text = _parse_images(text)
    text = _parse_title(text)
    text = re.sub(r":::\s*fragment\s*\n(.*?)\n:::", r'<div class="fragment">\n\1\n</div>', text, flags=re.DOTALL)
    text = _parse_step(text)
    text = _parse_grid(text)
    text = _parse_card(text)
    text = _parse_memo(text)

    # 閉じタグの処理
    text = re.sub(r"^:::\s*$", r'</div>', text, flags=re.MULTILINE)
    text = re.sub(r":::\s*", r'</div>\n', text)
    return text


def parse_markdown_table(lines: list, start_idx: int) -> tuple[str, int]:
    table_lines = []
    idx = start_idx
    while idx < len(lines) and "|" in lines[idx]:
        table_lines.append(lines[idx].strip())
        idx += 1

    if len(table_lines) < 2:
        return "<p>" + lines[start_idx] + "</p>", start_idx + 1

    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    html = ['<table>', '  <thead>', '    <tr>']
    for h in headers: html.append(f'      <th>{h}</th>')
    html.extend(['    </tr>', '  </thead>', '  <tbody>'])

    for row in table_lines[2:]:
        cols = [c.strip() for c in row.strip("|").split("|")]
        html.append('    <tr>')
        for c in cols: html.append(f'      <td>{parse_inline_markdown(c)}</td>')
        html.append('    </tr>')
    html.extend(['  </tbody>', '</table>'])
    return "\n".join(html), idx


def markdown_to_html(md_text: str) -> str:
    md_text = process_custom_containers(md_text)
    lines = md_text.strip().split("\n")
    html_lines = []
    in_list, list_type = False, "ul"
    in_code_block, code_block_lines, code_lang = False, [], ""
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block, code_lang, code_block_lines = True, stripped[3:].strip(), []
            else:
                in_code_block = False
                code_content = "\n".join(code_block_lines).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<pre><code class="language-{code_lang}">{code_content}</code></pre>')
            idx += 1
            continue
        if in_code_block:
            code_block_lines.append(line)
            idx += 1
            continue

        # リスト項目の継続行（インデントされた付帯説明行）の判定
        is_indented_continuation = in_list and (line.startswith("  ") or line.startswith("\t")) and bool(stripped)
        is_list_item = stripped.startswith("- ") or stripped.startswith("* ") or bool(re.match(r"^\d+\.\s", stripped))

        if in_list and not (is_list_item or is_indented_continuation):
            html_lines.append(f"</{list_type}>")
            in_list = False

        if not stripped:
            idx += 1
            continue

        if is_indented_continuation:
            # 直前の <li> の中に付帯説明として収める
            sub_html = parse_inline_markdown(stripped)
            if html_lines and html_lines[-1].endswith("</li>"):
                last = html_lines.pop()
                content = last[:-5]  # remove </li>
                if '<div class="list-subtext">' in content:
                    content = content[:-6] + f" {sub_html}</div>"
                else:
                    content = content + f'<div class="list-subtext">{sub_html}</div>'
                html_lines.append(content + "</li>")
            idx += 1
            continue

        if stripped.startswith("<") and stripped.endswith(">") and not stripped.startswith("<!--"):
            html_lines.append(line)
            idx += 1
            continue

        if re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped):
            html_lines.append(parse_inline_markdown(stripped))
            idx += 1
            continue

        if stripped.startswith("::include(") and stripped.endswith(")::"):
            html_lines.append(stripped)
            idx += 1
            continue

        if "|" in stripped and idx + 1 < len(lines) and re.match(r"^\|?\s*[-:]+[-| :]*$", lines[idx+1].strip()):
            tbl_html, idx = parse_markdown_table(lines, idx)
            html_lines.append(tbl_html)
            continue

        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            html_lines.append(f'<div class="math-display">{stripped}</div>')
            idx += 1
            continue

        if stripped.startswith("# "): html_lines.append(f"<h1>{stripped[2:]}</h1>"); idx += 1; continue
        elif stripped.startswith("## "): html_lines.append(f"<h2>{stripped[3:]}</h2>"); idx += 1; continue
        elif stripped.startswith("### "): html_lines.append(f"<h3>{stripped[4:]}</h3>"); idx += 1; continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list or list_type != "ul":
                if in_list: html_lines.append(f"</{list_type}>")
                html_lines.append("<ul>")
                in_list, list_type = True, "ul"
            html_lines.append(f"  <li>{parse_inline_markdown(stripped[2:])}</li>")
            idx += 1
            continue

        m_num = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m_num:
            if not in_list or list_type != "ol":
                if in_list: html_lines.append(f"</{list_type}>")
                html_lines.append("<ol>")
                in_list, list_type = True, "ol"
            html_lines.append(f"  <li>{parse_inline_markdown(m_num.group(2))}</li>")
            idx += 1
            continue

        if stripped.startswith("> "):
            html_lines.append(f"<blockquote>{parse_inline_markdown(stripped[2:])}</blockquote>")
            idx += 1
            continue

        html_lines.append(f"<p>{parse_inline_markdown(line)}</p>")
        idx += 1

    if in_list:
        html_lines.append(f"</{list_type}>")

    return "\n".join(html_lines)


def parse_inline_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img src="\2" alt="\1" class="slide-img">', text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" target="_blank">\1</a>', text)
    return text


def split_slides(md_text: str) -> list:
    h_slides_raw = re.split(r"\n---\n", md_text)
    slides_structure = []

    for h_raw in h_slides_raw:
        if not h_raw.strip(): continue
        v_slides_raw = re.split(r"\n--\n", h_raw)
        v_list = [v.strip() for v in v_slides_raw if v.strip()]
        if len(v_list) == 1:
            slides_structure.append(v_list[0])
        else:
            slides_structure.append(v_list)

    return slides_structure

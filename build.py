import argparse
import base64
import mimetypes
import os
import re
import sys
import webbrowser
from pathlib import Path

# Windows環境でのUTF-8出力対応
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
SLIDES_MD = BASE_DIR / "slide.md"
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_CSS_DIR = ASSETS_DIR / "css"
ASSETS_JS_DIR = ASSETS_DIR / "js"
EMBED_HTML = BASE_DIR / "slide_embed.html"
REFERED_HTML = BASE_DIR / "slide_refered.html"


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Presentation</title>
  <!-- CSS_PLACEHOLDER -->
  <!-- PLOTLY_PLACEHOLDER -->
  <!-- KATEX_JS_PLACEHOLDER -->
  <!-- HIGHLIGHT_JS_PLACEHOLDER -->
</head>
  <!-- コントロールボタンバー (左下) -->
  <div class="slide-controls-bar">
    <button class="control-btn" id="btn-overview" onclick="toggleTileModal();" title="全スライド一覧 (ESC / O)">
      📑 タイル一覧
    </button>
    <button class="control-btn" id="btn-fullscreen" onclick="toggleFullscreen();" title="全画面表示 (F / F11)">
      ⛶ 全画面
    </button>
  </div>

  <!-- タイル一覧モーダル -->
  <div id="slide-tile-modal">
    <div class="tile-header">
      <h2>📑 全スライド一覧</h2>
      <button class="tile-close-btn" onclick="toggleTileModal();">閉じる (ESC)</button>
    </div>
    <div class="tile-grid" id="tile-grid-container"></div>
  </div>

  <div class="reveal">
    <div class="slides">
      <!-- 全スライド共通のロゴ (1280x720スライド用紙の内側に完全固定) -->
      <div class="slide-fixed-logo"></div>
<!-- SLIDES_PLACEHOLDER -->
    </div>
  </div>


  <!-- REVEAL_JS_PLACEHOLDER -->
  <script>
    // Reveal.jsの初期化
    Reveal.initialize({
      hash: true,
      slideNumber: 'c/t',
      showSlideNumber: 'all',
      transition: 'slide',
      center: false,
      width: 1280,
      height: 720,
      margin: 0,
      minScale: 0.1,
      maxScale: 4.0
    });


    // 1. 全画面表示 (Fullscreen)
    function toggleFullscreen() {
      if (!document.fullscreenElement) {
        const docEl = document.documentElement;
        if (docEl.requestFullscreen) {
          docEl.requestFullscreen().catch(err => {
            console.log('Fullscreen note:', err.message);
          });
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        }
      }
    }

    // 2. タイル一覧モーダル
    function toggleTileModal() {
      const modal = document.getElementById('slide-tile-modal');
      const isActive = modal.classList.toggle('active');
      if (isActive) {
        buildTileGrid();
      }
    }

    function buildTileGrid() {
      const container = document.getElementById('tile-grid-container');
      container.innerHTML = '';
      const indices = Reveal.getIndices();

      const horizontalSections = document.querySelectorAll('.reveal .slides > section');
      let slideCounter = 1;

      horizontalSections.forEach((hSec, hIdx) => {
        const verticalSections = hSec.querySelectorAll('section');
        if (verticalSections.length > 0) {
          verticalSections.forEach((vSec, vIdx) => {
            createTileItem(container, vSec, hIdx, vIdx, `${slideCounter} (縦 ${vIdx + 1})`, hIdx === indices.h && vIdx === indices.v);
            slideCounter++;
          });
        } else {
          createTileItem(container, hSec, hIdx, 0, `${slideCounter}`, hIdx === indices.h && indices.v === 0);
          slideCounter++;
        }
      });
    }

    function createTileItem(container, secEl, h, v, label, isCurrent) {
      const tile = document.createElement('div');
      tile.className = 'slide-tile-item' + (isCurrent ? ' current' : '');

      const heading = secEl.querySelector('h1, h2, h3');
      let titleText = 'スライド ' + label;
      if (heading && heading.textContent) {
        titleText = heading.textContent.replace(/#/g, '').trim();
      }

      const snippetEl = secEl.querySelector('p, li, .agenda-item, td');
      const snippetText = snippetEl && snippetEl.textContent ? snippetEl.textContent.trim().slice(0, 60) : '';

      tile.innerHTML = `
        <div>
          <div class="tile-badge">Slide #${label} ${isCurrent ? ' (現在地)' : ''}</div>
          <div class="tile-title">${titleText}</div>
          <div class="tile-snippet">${snippetText}</div>
        </div>
      `;

      tile.onclick = function() {
        Reveal.slide(h, v);
        toggleTileModal();
      };

      container.appendChild(tile);
    }

    // キーボードショートカット
    window.addEventListener('keydown', function(e) {
      // ESCまたはOキー: タイル一覧の開閉
      if (e.key === 'Escape' || e.key === 'o' || e.key === 'O') {
        const modal = document.getElementById('slide-tile-modal');
        if (modal && modal.classList.contains('active')) {
          toggleTileModal();
          e.preventDefault();
          e.stopPropagation();
        }
      }
    });

    // Reveal.jsにFキーの全画面バインドを登録 (ブラウザ権限エラーを防止)
    Reveal.addKeyBinding({ keyCode: 70, key: 'F', description: 'Toggle Fullscreen' }, function() {
      toggleFullscreen();
    });


    // シンタックスハイライト & 数式レンダリング
    function initEnhancements() {
      if (typeof hljs !== 'undefined') {
        hljs.highlightAll();
      }
      if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(document.body, {
          delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false}
          ],
          throwOnError: false
        });
      }
    }

    // スライド切り替えイベント
    function triggerPlotlyResize() {
      if (typeof Plotly !== 'undefined') {
        window.dispatchEvent(new Event('resize'));
        document.querySelectorAll('.js-plotly-plot, [id^="chart-"], [id^="plotly-"]').forEach(function(el) {
          try { Plotly.Plots.resize(el); } catch(e) {}
        });
      }
    }

    function updateSlideState() {
      const indices = Reveal.getIndices();
      const isTitle = (indices.h === 0 && indices.v === 0);
      document.body.classList.toggle('is-title-slide', isTitle);
    }

    Reveal.on('ready', function() {
      initEnhancements();
      updateSlideState();
      setTimeout(triggerPlotlyResize, 200);
    });

    Reveal.on('slidechanged', function() {
      updateSlideState();
      setTimeout(triggerPlotlyResize, 100);
    });
  </script>
</body>

</html>
"""


def process_custom_containers(text: str) -> str:
    """
    ::: title, ::: agenda, ::: point, ::: grid-2, ::: grid-3, ::: card, ::: notes, ::: step, ::: fragment などの展開
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
        elif spec == "none" or spec == "static":
            # アニメーションなし（最初から全体通常表示）
            is_step = False
        elif spec.startswith("fixed:") or spec.startswith("only:"):
            # 最初から特定の番号が固定ハイライト（ステップなし）
            num_str = spec.split(":")[-1]
            if num_str.isdigit():
                fixed_active = int(num_str)
        else:
            # 自由指定: 例 "3", "1,3", "1-3", "2,4"
            is_step = True
            step_counter = 1
            parts = spec.split(",")
            for part in parts:
                part = part.strip()
                if "-" in part:
                    # 範囲指定: 1-3
                    rng = part.split("-")
                    if len(rng) == 2 and rng[0].isdigit() and rng[1].isdigit():
                        start, end = int(rng[0]), int(rng[1])
                        for num in range(start, end + 1):
                            if 1 <= num <= total_items and num not in fragment_order:
                                fragment_order[num] = step_counter
                                step_counter += 1
                elif part.isdigit():
                    num = int(part)
                    if 1 <= num <= total_items and num not in fragment_order:
                        fragment_order[num] = step_counter
                        step_counter += 1

        classes = ["agenda-list"]
        if is_step:
            classes.append("is-step")

        agenda_html = [f'<div class="{" ".join(classes)}">']
        for idx, item_text in enumerate(valid_items, 1):
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



    # 2. ::: point (強調ボックス: スペースなしの :::point にも対応)
    text = re.sub(r":::\s*point\s*\n(.*?)\n:::", r'<div class="point-box">\n\1\n</div>', text, flags=re.DOTALL)

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


        # # の位置を探す
        h_idx = -1
        for i, l in enumerate(lines):
            if l.startswith("#"):
                h_idx = i
                title_line = re.sub(r"^#+\s*", "", l)
                break

        if h_idx != -1:
            date_lines = lines[:h_idx]
            after_lines = lines[h_idx + 1:]
            if len(after_lines) == 1:
                # 1行だけなら発表者名
                author_line = after_lines[0]
            elif len(after_lines) > 1:
                sub_lines = after_lines[:-1]
                author_line = after_lines[-1]
        else:
            # # がない場合のフォールバック
            if len(lines) == 1:
                title_line = lines[0]
            elif len(lines) >= 2:
                title_line = lines[0]
                sub_lines = lines[1:-1]
                author_line = lines[-1]

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



    # 5. ::: fragment (段階表示)
    text = re.sub(r":::\s*fragment\s*\n(.*?)\n:::", r'<div class="fragment">\n\1\n</div>', text, flags=re.DOTALL)

    # 6. ::: step (内部の箇条書きを自動で1行ずつフェードイン)
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

    # 7. ::: grid-2, ::: grid-3, ::: card (色指定対応), ::: split, ::: 終了
    text = re.sub(r":::\s*grid-2\s*", r'<div class="grid-2">\n<div>\n', text)
    text = re.sub(r":::\s*grid-3\s*", r'<div class="grid-3">\n', text)

    # カードの色バリエーション (::: card:blue, ::: card:red, ::: card:yellow, ::: card:bg="#...")
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
    text = re.sub(r":::\s*split\s*", r'</div>\n<div>\n', text)
    text = re.sub(r":::\s*\n", r'</div>\n', text)


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
            html.append(f'      <td>{c}</td>')
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
    in_code = False
    code_lang = ""
    code_buffer = []
    in_raw_html = False

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # テーブル検出
        if not in_code and not in_raw_html and stripped.startswith("|") and idx + 1 < len(lines) and "|---" in lines[idx + 1]:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            table_html, new_idx = parse_markdown_table(lines, idx)
            html_lines.append(table_html)
            idx = new_idx
            continue

        # 生HTMLブロック
        if stripped.startswith("<script") or stripped.startswith("<style") or stripped.startswith("<!--") or stripped.startswith("<aside"):
            in_raw_html = True
        
        if in_raw_html:
            html_lines.append(line)
            if stripped.endswith("</script>") or stripped.endswith("</style>") or stripped.endswith("-->") or stripped.endswith("</aside>"):
                in_raw_html = False
            idx += 1
            continue

        # コードブロック
        if stripped.startswith("```"):
            if in_code:
                code_content = "\n".join(code_buffer)
                cls = f' class="language-{code_lang}"' if code_lang else ''
                html_lines.append(f'<pre><code{cls}>{code_content}</code></pre>')
                in_code = False
                code_buffer = []
                code_lang = ""
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                in_code = True
                code_lang = stripped[3:].strip()
            idx += 1
            continue

        if in_code:
            code_buffer.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            idx += 1
            continue

        # リストの終了
        if in_list and not (stripped.startswith("- ") or stripped.startswith("* ")):
            html_lines.append("</ul>")
            in_list = False

        # 空行
        if not stripped:
            idx += 1
            continue

        # 既に完全なHTMLタグ
        if stripped.startswith("<") and not stripped.startswith("<http"):
            if in_list and not (stripped.startswith("<li") or stripped.startswith("</li")):
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(line)
            idx += 1
            continue


        # 見出し
        if stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        # リスト
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        # 引用
        elif stripped.startswith("> "):
            html_lines.append(f"<blockquote>{stripped[2:]}</blockquote>")
        # 通常テキスト / 段落
        else:
            html_lines.append(f"<p>{line}</p>")

        idx += 1

    if in_list:
        html_lines.append("</ul>")
    if in_code:
        html_lines.append("</code></pre>")

    result = "\n".join(html_lines)
    result = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", result)
    result = re.sub(r"`(.*?)`", r"<code>\1</code>", result)
    return result


def process_includes_and_images(md_text: str, is_embed: bool) -> str:
    # 1. ::include(path):: で外部HTMLを展開
    def replace_include(match):
        rel_path = match.group(1).strip()
        target = BASE_DIR / rel_path
        if target.exists():
            return target.read_text(encoding="utf-8")
        return f"<div style='color:red;'>[Not Found: {rel_path}]</div>"

    text = re.sub(r"::include\(([^)]+)\)::", replace_include, md_text)

    # 2. ::video(path):: で動画を簡単に配置
    def replace_video(match):
        rel_path = match.group(1).strip()
        if is_embed:
            vid_path = BASE_DIR / rel_path
            if vid_path.exists():
                mime, _ = mimetypes.guess_type(vid_path)
                mime = mime or "video/mp4"
                b64 = base64.b64encode(vid_path.read_bytes()).decode("utf-8")
                return f'<video class="slide-video" autoplay loop muted playsinline src="data:{mime};base64,{b64}"></video>'
        return f'<video class="slide-video" autoplay loop muted playsinline src="{rel_path}"></video>'

    text = re.sub(r"::video\(([^)]+)\)::", replace_video, text)

    # 3. 画像の処理
    if is_embed:
        def replace_img_embed(match):
            alt, rel_path = match.group(1), match.group(2).strip()
            img_path = BASE_DIR / rel_path
            if img_path.exists():
                mime, _ = mimetypes.guess_type(img_path)
                mime = mime or "image/png"
                b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
                return f'<img class="slide-img" alt="{alt}" src="data:{mime};base64,{b64}" />'
            return match.group(0)

        text = re.sub(r"!\[(.*?)\]\((.*?)\)", replace_img_embed, text)
    else:
        def replace_img_refered(match):
            alt, rel_path = match.group(1), match.group(2).strip()
            return f'<img class="slide-img" alt="{alt}" src="{rel_path}" />'

        text = re.sub(r"!\[(.*?)\]\((.*?)\)", replace_img_refered, text)

    return text


def parse_slides(raw_text: str) -> str:
    horizontal_slides = raw_text.split("\n---\n")
    sections_html = []

    for h_slide in horizontal_slides:
        if "\n--\n" in h_slide:
            vertical_slides = h_slide.split("\n--\n")
            inner_sections = []
            for v_slide in vertical_slides:
                html = markdown_to_html(v_slide)
                cls = ' class="title-section"' if '<div class="title-slide">' in html else ''
                inner_sections.append(f"<section{cls}>\n{html}\n</section>")
            sections_html.append("<section>\n" + "\n".join(inner_sections) + "\n</section>")
        else:
            html = markdown_to_html(h_slide)
            cls = ' class="title-section"' if '<div class="title-slide">' in html else ''
            sections_html.append(f"<section{cls}>\n{html}\n</section>")

    return "\n".join(sections_html)



def build(open_target=None):
    raw_md = SLIDES_MD.read_text(encoding="utf-8")

    # =========================================================================
    # 1. slide_refered.html の生成 (相対パス参照型)
    # =========================================================================
    refered_content = process_includes_and_images(raw_md, is_embed=False)
    
    refered_css = """  <link rel="stylesheet" href="./assets/css/reveal.min.css">
  <link rel="stylesheet" href="./assets/css/katex.min.css">
  <link rel="stylesheet" href="./assets/css/highlight-dark.min.css">
  <link rel="stylesheet" href="./assets/css/theme-custom.css">"""
    
    refered_plotly = '<script src="./assets/js/plotly.min.js"></script>'
    refered_katex = '<script src="./assets/js/katex.min.js"></script>\n  <script src="./assets/js/katex-auto.min.js"></script>'
    refered_hljs = '<script src="./assets/js/highlight.min.js"></script>'
    refered_reveal_js = '<script src="./assets/js/reveal.min.js"></script>'

    refered_html = HTML_TEMPLATE.replace("<!-- CSS_PLACEHOLDER -->", refered_css)
    refered_html = refered_html.replace("<!-- PLOTLY_PLACEHOLDER -->", refered_plotly)
    refered_html = refered_html.replace("<!-- KATEX_JS_PLACEHOLDER -->", refered_katex)
    refered_html = refered_html.replace("<!-- HIGHLIGHT_JS_PLACEHOLDER -->", refered_hljs)
    refered_html = refered_html.replace("<!-- REVEAL_JS_PLACEHOLDER -->", refered_reveal_js)
    refered_html = refered_html.replace("<!-- SLIDES_PLACEHOLDER -->", parse_slides(refered_content))

    REFERED_HTML.write_text(refered_html, encoding="utf-8")

    # =========================================================================
    # 2. slide_embed.html の生成 (完全埋込型・単一ファイル)
    # =========================================================================
    embed_content = process_includes_and_images(raw_md, is_embed=True)

    reveal_css = (ASSETS_CSS_DIR / "reveal.min.css").read_text(encoding="utf-8") if (ASSETS_CSS_DIR / "reveal.min.css").exists() else ""
    katex_css = (ASSETS_CSS_DIR / "katex.min.css").read_text(encoding="utf-8") if (ASSETS_CSS_DIR / "katex.min.css").exists() else ""
    hljs_css = (ASSETS_CSS_DIR / "highlight-dark.min.css").read_text(encoding="utf-8") if (ASSETS_CSS_DIR / "highlight-dark.min.css").exists() else ""
    
    custom_css = ""
    if (ASSETS_CSS_DIR / "theme-custom.css").exists():
        custom_css = (ASSETS_CSS_DIR / "theme-custom.css").read_text(encoding="utf-8")
        # CSS内の url("./logo.svg") や url("./logo.png") を Base64化
        def replace_css_url(match):
            rel_img = match.group(1).strip().strip("'\"")
            img_file = (ASSETS_CSS_DIR / rel_img).resolve()
            if img_file.exists():
                mime, _ = mimetypes.guess_type(img_file)
                if img_file.suffix.lower() == ".svg":
                    mime = "image/svg+xml"
                mime = mime or "image/png"
                b64 = base64.b64encode(img_file.read_bytes()).decode("utf-8")
                return f'url("data:{mime};base64,{b64}")'
            return match.group(0)

        custom_css = re.sub(r'url\((.*?)\)', replace_css_url, custom_css)

    bundle_css = f"<style>\n{reveal_css}\n{katex_css}\n{hljs_css}\n{custom_css}\n  </style>"

    plotly_js = f"<script>\n{(ASSETS_JS_DIR / 'plotly.min.js').read_text(encoding='utf-8')}\n  </script>"
    
    katex_js = ""
    if (ASSETS_JS_DIR / "katex.min.js").exists() and (ASSETS_JS_DIR / "katex-auto.min.js").exists():
        katex_js = f"<script>\n{(ASSETS_JS_DIR / 'katex.min.js').read_text(encoding='utf-8')}\n{(ASSETS_JS_DIR / 'katex-auto.min.js').read_text(encoding='utf-8')}\n  </script>"

    hljs_js = ""
    if (ASSETS_JS_DIR / "highlight.min.js").exists():
        hljs_js = f"<script>\n{(ASSETS_JS_DIR / 'highlight.min.js').read_text(encoding='utf-8')}\n  </script>"

    reveal_js = f"<script>\n{(ASSETS_JS_DIR / 'reveal.min.js').read_text(encoding='utf-8')}\n  </script>"

    embed_html = HTML_TEMPLATE.replace("<!-- CSS_PLACEHOLDER -->", bundle_css)
    embed_html = embed_html.replace("<!-- PLOTLY_PLACEHOLDER -->", plotly_js)
    embed_html = embed_html.replace("<!-- KATEX_JS_PLACEHOLDER -->", katex_js)
    embed_html = embed_html.replace("<!-- HIGHLIGHT_JS_PLACEHOLDER -->", hljs_js)
    embed_html = embed_html.replace("<!-- REVEAL_JS_PLACEHOLDER -->", reveal_js)
    embed_html = embed_html.replace("<!-- SLIDES_PLACEHOLDER -->", parse_slides(embed_content))

    EMBED_HTML.write_text(embed_html, encoding="utf-8")

    print("==================================================")
    print("✔ スライドのビルドが完了しました！ (ロゴ/数式/ハイライト/動画/表/3Dグラフ対応)")
    print(f"  [参照型・確認用] {REFERED_HTML.name}")
    print(f"  [埋込型・配布用] {EMBED_HTML.name}")
    print("==================================================")



    if open_target == "embed":
        webbrowser.open(EMBED_HTML.as_uri())
    elif open_target == "refered":
        webbrowser.open(REFERED_HTML.as_uri())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slide Builder")
    parser.add_argument("--open", "-o", choices=["embed", "refered"], default=None, help="ビルド後に自動でブラウザで開くファイル")
    args = parser.parse_args()

    build(open_target=args.open)

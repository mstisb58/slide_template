# 🛠️ 開発者向け仕様書・カスタマイズマニュアル (MANUAL.md)

このドキュメントは、**`build.py` の変換パイプライン、拡張構文の正規表現ロジック、CSS・JSの構造、およびシステムの拡張方法** を解説した開発者向け仕様書です。

---

## 1. システムアーキテクチャ概要

本システムは、Markdown (`slide.md`) から **Python標準ライブラリのみ** でHTMLを生成し、Reveal.js、Plotly.js、KaTeX、Highlight.js を統合してリッチなプレゼンテーションを実現しています。

```
[ slide.md ]
    │
    ▼ (1) process_includes_and_images()  : ::include(...), ::video(...) 展開 & 画像/動画のBase64化(embed時)
    ▼ (2) process_custom_containers()    : ::: 構文 (title, agenda, step, notes, point, grid) の正規表現置換
    ▼ (3) markdown_to_html()             : テーブル、コード、見出し、リスト、太字の行単位パース
    ▼ (4) parse_slides()                 : --- (横) および -- (縦) で <section> 分割
    │
    ├─► [ slide_refered.html ] (相対パス参照型 / 開発用)
    └─► [ slide_embed.html ]   (全JS/CSS/画像を内包 / 完全配布用)
```

---

## 2. `build.py` 内部ロジック仕様

### ① 外部インクルード & メディア処理 (`process_includes_and_images`)
- `::include(relative_path)::` : 指定されたHTMLファイルの中身を読み込んでそのまま展開。
- `::video(relative_path)::` : `<video class="slide-video" autoplay loop muted playsinline src="..."></video>` に展開。
- **embed（埋込）時**: 画像（PNG/JPG/SVG/WebP）および動画（MP4/WebM）を検出し、Base64エンコードした `data:{mime};base64,...` 文字列に自動置換して完全埋め込み化。
- **refered（参照）時**: 相対パスのまま出力。

### ② カスタムコンテナ構文 (`process_custom_containers`)
正規表現（`re.sub`）により、以下のMarkdown拡張記法をHTMLタグへ変換しています：

| Markdown記法 | 変換後HTML | 役割 |
|---|---|---|
| `::: title` ～ `:::` | `<div class="title-slide"> ... </div>` | 表紙中央揃えレイアウト |
| `::: point` ～ `:::` | `<div class="point-box"> ... </div>` | 左線付きの強調ボックス |
| `::: step` ～ `:::` | 内部の各行を `<li class="fragment">` に自動変換 | クリックごとの段階フェードイン |
| `::: fragment` ～ `:::` | `<div class="fragment"> ... </div>` | 要素全体の段階表示 |
| `::: grid-2` | `<div class="grid-2"><div>` | 左右2分割（左カラム開始） |
| `::: split` | `</div><div>` | 左カラム終了 ➜ 右カラム開始 |
| `:::` | `</div>` | コンテナの終了 |
| `::: grid-3` | `<div class="grid-3">` | 3列グリッド |
| `::: card` | `<div class="card">` | カード枠 |

### ③ テーブルパーサー (`parse_markdown_table`)
- `| A | B |` および `|---|---|` を検出し、セマンティックな `<table><thead><tr><th>...</th></tr></thead><tbody>...</tbody></table>` を生成。

### ④ コードブロック ＆ 数式
- ````python ... ```` ➜ `<pre><code class="language-python">...</code></pre>` を生成し、初期化時に `hljs.highlightAll()` でカラー化。
- `$E=mc^2$` や `$$ ... $$` ➜ 初期化時に `renderMathInElement()` でKaTeXにより数式レンダリング。

### ⑤ スライド分割 (`parse_slides`)
- `\n---\n` で水平スライドを分割。
- 水平スライド内に `\n--\n` がある場合、親 `<section>` 内に子 `<section>` をネストして **垂直スタック（縦送りスライド）** を構成。

---

## 3. CSS・デザイン構造 (`assets/theme-custom.css`)

### ① デザイントークン (`:root`)
カラーパレットはすべて先頭の CSS 変数で一元管理されています。

```css
:root {
  --bg-main: #0f172a;           /* 背景色 */
  --text-main: #f8fafc;         /* メインテキスト色 */
  --text-sub: #94a3b8;          /* 補足テキスト色 */
  --accent: #38bdf8;            /* アクセントカラー (水色) */
  --accent-secondary: #818cf8;  /* サブアクセント (薄紫) */
  --border-color: rgba(255, 255, 255, 0.12); /* 枠線色 */
  --card-bg: rgba(255, 255, 255, 0.04);      /* カード背景色 */
}
```

---

## 4. JavaScript 連携機能

1. **タイル一覧モーダル (`toggleTileModal()`)**
   - DOM内のスライドを走査し、見出し・概要文を抽出してグリッドタイルを自動生成。
   - クリックで `Reveal.slide(h, v)` によりジャンプ。`ESC` / `O` キーでトグル。
2. **Plotly 自動リサイズ (`triggerPlotlyResize()`)**
   - スライド遷移イベント（`slidechanged`）時に `Plotly.Plots.resize()` を発火。
3. **KaTeX ＆ Highlight.js 初期化 (`initEnhancements()`)**
   - スライド読み込み時に数式レンダリングとコードハイライトを一括適用。

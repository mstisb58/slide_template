# pyslides

**pyslides** は、Python のオブジェクト指向 API を用いてモダンで美しい Reveal.js ベースの HTML スライドを直接生成する Python ライブラリです。

Jupyter Notebook / IPython 上での**インタラクティブな単体スライド・全体スライドのプレビュー**に対応しており、データサイエンスや研究発表、テクニカルプレゼンテーションをノートブック上で快適に作成・編集・検証できます。

---

## 主な特徴

- 🚀 **Python to Slide ダイレクト生成**: Markdown を経由せず、Python オブジェクトから直接 HTML タグ（`<section>`）を構築。高速で拡張性に優れています。
- 🧩 **独立型スライド設計**: 各スライド（`Slide`）を単体で独立して作成・プレビューでき、最後に `deck.join([s1, s2, s3])` で自由に順序入れ替え・カットが可能。
- 📊 **Plotly 完全対応**: Plotly で作成したインタラクティブなグラフをそのままスライド内に埋め込み可能。
- 🎯 **直感的なアジェンダ制御**: 目次スライドのステップ送りアニメーション（特定項目のハイライト／ダークアウト）をタプルで直感的に指定可能。
- 📐 **1280×720 固定デザインシステム**: アスペクト比 16:9 の黄金比デザインシステムを採用。フォント・行間・余白が美しく調整されています。
- 📦 **完全自己完結型 HTML**: 全 CSS、JavaScript、SVG ロゴを 1 つの HTML ファイルにインライン化して出力可能（配布が容易）。

---

## インストール・セットアップ

プロジェクトディレクトリ内でローカルパッケージとして読み込みます：

```bash
# uv をお使いの場合
uv add --editable ./pyslides
```

または Python スクリプト・ノートブックから：

```python
import sys
sys.path.insert(0, "pyslides")
from pyslides import Slide, Deck, Chart
```

---

## クイックスタート

### 1. テンプレートファクトリの準備

まず、CSSテーマとデザイン属性を管理する `SlideFactory` を作成します。スライドはこのファクトリから生成します。

```python
import sys
sys.path.insert(0, "pyslides")
from pyslides import Deck, SlideFactory

# テーマごとのファクトリを作成
factory = SlideFactory(style="assets/css/theme-custom.css", theme_name="kracie")
```

### 2. スライドを個別に作成し、要素を拡張する

```python
# --- スライド1: タイトル ---
s1 = factory.create_slide(template="title", title="NIR-HSIを用いた毛髪診断システムの開発")
s1.author = "礒辺 真人\nクラシエ薬品株式会社"
s1.show()  # Jupyter Notebook上で単体プレビュー！

# --- スライド2: アジェンダ（目次） ---
s2 = factory.create_slide(
    template="agenda",
    title="目次",
    # 辞書の key が左の丸（バッジ）に表示され、highlight の指定キーにもなります
    item={
        "01": "背景と課題",
        "02": "漢方体質アンケート",
        "03": "毛髪と漢方体質",
        "04": "今後の展望"
    },
    # キー（"01"など）やキーワード（"none", "gray", "all"）で指定可能
    # リストで渡すとステップアニメーション（例: 通常表示 → 01をハイライト）
    highlight=["none", "01"]
)
s2.show()

# --- スライド3: Pythonネイティブなグリッド＆カード構成 ---
s3 = factory.create_slide(title="背景：漢方体質とは？気血水の基本概念")
s3.add_markdown("漢方医学では、人体は**「気」「血」「水」**の3要素がバランスよく巡ることで健康が保たれると考えられている。")

# 3分割グリッドを作成
s3_g = s3.add_grid(col=3)

# セル0: yellowカードを作成し、カード内に要素を追加
s3_g[0].add_card(color="yellow")
s3_g[0].card.add_markdown("""
**気：生命エネルギー・代謝**
自律神経系や代謝を司る活力
- **気虚**: エネルギー不足・疲労・胃腸虚弱
- **気滞**: 気の滞り・抑うつ・膨満感
- **気逆**: 気の逆流・のぼせ・動悸
""")
# 必要に応じてカード内に画像も追加可能: s3_g[0].card.add_image(pil_img)
# カードの下に注釈を追加することも可能: s3_g[0].add_markdown("カード下の注釈")

# セル1: redカード
s3_g[1].add_card(color="red")
s3_g[1].card.add_markdown("""
**血：血液・ホルモン・栄養**
全身に酸素や栄養を届ける働き
- **血虚**: 栄養不足・肌荒れ・貧血
- **瘀血**: 血行不良・冷えのぼせ
""")

# セル2: blueカード
s3_g[2].add_card(color="blue")
s3_g[2].card.add_markdown("""
**水：体液・リンパ・水分代謝**
血液以外の水分や分泌液
- **水滞 / 水毒**: 水分代謝異常・むくみ・めまい・頭重感
""")

# スライド最下部にメモ（注釈ボックス）を追加
s3.add_memo("**日本独自の発展（古方派）**：中国の思弁的な理論に対し、日本の江戸時代（吉益東洞ら）の実証的な漢方医学において、病態をシンプルに捉える指標として発展・体系化。")

s3.show()
```

---

### 3. スライドを束ねて全体出力・プレビューする

作成したスライドは、リストで `Deck` に渡すだけで順序の入れ替えや不要スライドのカットが自由自在に行えます。

```python
from pyslides import Deck

# Deckを作成し、スライドを結合
deck = Deck(title="毛髪診断システム発表資料")
deck.join([s1, s2, s3])

# 全体プレゼンテーションをノートブック内でプレビュー
deck.show()

# 1枚の完全完結型 HTML ファイルとして出力
deck.to_html("dist/presentation.html")
```

---

## 主要 API リファレンス

### `add_graph(obj)` / `add_chart(obj)`
あらゆる可視化オブジェクト（Plotly, Matplotlib, Bokeh, Altair, Pandas, 外部HTMLファイル等）を統一的にスライドまたはセル内に埋め込みます。

```python
# 1. Plotly フィギュアの追加
fig = go.Figure(...)
g[1].add_graph(fig)

# 2. Matplotlib / Seaborn の追加 (自動でPNG画像化して埋め込み)
fig, ax = plt.subplots(...)
g[0].add_graph(fig)

# 3. 外部HTMLファイルパスの追加
g[0].add_graph("charts/sample_3d.html")
```

### `add_image(src=None, img_path=None, height=None, caption=None)`
画像要素をスライドまたはセル内に配置します。ローカル画像ファイル（PNG, JPEG, SVG, WebP）が指定された場合は、自動で Base64 Data URI に変換されて完全自己完結します。

```python
# 相対パスでの追加 (Base64自動エンコード)
g[0].add_image("graph/cube.png", height="280px")
# キーワード引数での指定
g[1].add_image(img_path="graph/taishitu.png", caption="漢方体質分類図")
```

### `SlideFactory(style, theme_name)`
デザインテーマを管理し、スライドを生成するファクトリクラスです。

- **メソッド**:
  - `create_slide(template="default", **kwargs)`: 指定されたテンプレートと属性を持つ `Slide` インスタンスを生成します。

### スライド拡張 API (`Slide` / `Container`)
`SlideFactory` で作成されたスライドには、後から動的に様々な要素を追加できます。

- `add_markdown(text)`: マークダウン形式のテキストを追加
- `add_grid(col=2, row=1)`: グリッドコンテナを追加し、要素を分割配置
- `add_chart(fig)` / `add_graph(fig)`: Plotly等のグラフオブジェクトを追加
- `add_image(path)`: 組み込みの画像を追加

```python
# タイトルスライドであっても後から自由に要素を足すことが可能
g = s1.add_grid(col=2)
g[0].add_markdown("左カラム")
g[1].add_markdown("右カラム")
```

### `Deck(slides=None, title="...", style=None)`
プレゼンテーション全体を統括・出力するコンテナクラス。

- **プロパティ / メソッド**:
  - `slides`: 登録されているスライドのリスト（代入による一括更新・順序変更が可能）
  - `join(slides: list)`: スライドのリストを結合・設定
  - `append(slide: Slide)`: スライドを末尾に追加
  - `extend(slides: list)`: 複数のスライドを末尾に追加
  - `show(height=540)`: ノートブック上で全スライドをプレビュー表示（キーボード・クリック送り対応）
  - `to_html(output_path: str)`: 完全自己完結型の HTML ファイルを出力

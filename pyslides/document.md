# pyslides 技術資料 (document.md)

本ドキュメントは、Python 製スライド生成ライブラリ **`pyslides`** の内部アーキテクチャ、モジュール設計、および主要機能の技術的メカニズムについて解説する技術資料です。

---

## 1. 設計思想とアーキテクチャの進化

### 背景と課題（Markdownパーサー依存からの脱却）
初期のプロトタイプでは、Python のオブジェクトを一度 `::: agenda` や `::: title` のような Markdown 独自記法に変換し、それを既存の `markdown_parser.py` で正規表現を用いて HTML にパースし直す構造（Markdown ジェネレーター）をとっていました。

しかしこの方式には以下の根本的な欠点がありました：
1. **二重処理によるパフォーマンス低下**: Python オブジェクト ➜ Markdown 文字列 ➜ 正規表現パース ➜ HTML という無駄な中継が発生。
2. **コードの複雑化・肥大化**: Python 側とパーサー側の双方が同一の構文ルールを二重に管理する必要があり、メンテナンス性が悪化。
3. **データ損失のリスク**: 複雑なステップ情報（例: 複数ハイライトの入れ子リスト）を文字列経由で受け渡すためエスケープやパースの破損が生じやすい。

### 「Python to Slide」ダイレクト HTML 生成
現在の `pyslides` は、**「Python オブジェクトからダイレクトに Reveal.js 用の HTML (`<section>`) を構築する」** ピュアなジェネレーターとして再構築されています。
外部の Markdown パーサーへの依存は完全に排除され、最小限のコード量で最大の実行速度と堅牢性を達成しています。

---

## 2. パッケージ構成とモジュール責務

`pyslides` パッケージは単一責任の原則（Single Responsibility Principle）に基づき、明確に責務が分離されています。

```
pyslides/
├── pyproject.toml
├── README.md               # ユーザー向け説明書
├── document.md             # 本技術資料
└── pyslides/               # パッケージ本体
    ├── __init__.py         # 公開APIのエクスポート
    ├── deck.py             # プレゼンテーション全体の統括（コンテナ）
    ├── slide.py            # 単一スライドの表現・型定義
    ├── elements.py         # チャートやグリッド等の構成要素
    ├── renderer.py         # Slideオブジェクト ➔ <section> HTML の直接生成
    ├── builder.py          # 全体HTML枠組み（<head>, <body>, Reveal初期化）の構築
    ├── asset_encoder.py    # CSS/JS/画像アセットの探索・インライン化
    └── assets/             # 静的ファイル（Static Assets）
        ├── css/            # reveal.min.css, theme-custom.css, logo.svg 等
        └── js/             # reveal.min.js, plotly.min.js, custom-reveal.js 等
```

### 各モジュールの役割

| モジュール | 責務 |
| :--- | :--- |
| **`slide.py`** | 1枚のスライドの状態（テンプレート名、タイトル、項目リスト、ハイライト順序、要素群）を保持。静的型付け（`HighlightOrder`）を提供。 |
| **`deck.py`** | 複数の `Slide` をリストとして束ねるコンテナ。スライドの追加・順序入れ替え（`join`）、全体表示（`show`）、ファイル出力（`to_html`）を担当。 |
| **`renderer.py`** | 1枚の `Slide` インスタンスを入力とし、Reveal.js が解釈可能な単一の `<section>` HTML 文字列を出力する純粋関数群。 |
| **`builder.py`** | 複数の `<section>` 文字列を受け取り、CSS・JS・メタタグを埋め込んだ完全な HTML ドキュメントを構築する。プレビュー用と配布用で出力を最適化。 |
| **`asset_encoder.py`** | ディレクトリを探索して静的アセットを収集し、CSS 内のローカル URL（`logo.svg`）を Base64 Data URI に置換して自己完結させる。 |
| **`custom-reveal.js`** | Reveal.js 本体には備わっていない独自機能（アジェンダの動的ハイライト、Plotly の自動リサイズ等）を担うフロントエンド拡張スクリプト。 |

---

## 3. 主要機能の実装メカニズム

### (1) アジェンダのステップ遷移アニメーションとハイライト仕様

目次スライド（`template="agenda"`）において、`item` を辞書（`{"01": "背景", ...}`）で渡すことで、**左側の丸バッジ（`.agenda-num`）の文字列と、`highlight` の指定キーを完全に連動**させることができます（`"A"`, `"B"` や `"い"`, `"ろ"` など任意のキーが利用可能）。従来のリスト（`["背景", ...]`）を渡した場合は自動で `"01"`, `"02"`... が割り振られます。

- **`"none"`（デフォルト）**: すべて通常状態（ハイライトもトーンダウンもない、標準の白カード）。
- **`"gray"`**: すべてトーンダウン（全項目が `.dimmed` のグレーアウト状態）。
- **`"all"`**: すべてハイライト（全項目が `.is-active` / `.active-fixed` の光っている状態）。
- **キー指定（例: `"01"` や `["01", "03"]`, `"A"`）**: 指定したキーの項目のみハイライトし、それ以外の項目はトーンダウン。
- **ステップ指定（例: `["none", "01"]` や `["all", "02"]`）**: 
  Reveal.js のフラグメントと連動し、ページ送り（クリック / スペース / 矢印キー）に合わせて段階的にハイライト状態が切り替わります。

1. **Python (`renderer.py`) による出力**:
   ```html
   <div class="agenda-list is-step" data-agenda-steps='["none", [0]]'>
     <div class="agenda-item" data-agenda-index="0" data-agenda-key="01">
       <span class="agenda-num">01</span>
       <span>背景</span>
     </div>
     ...
   </div>
   ```
2. **JavaScript (`custom-reveal.js`) による動的制御**:
   - `Reveal.on('fragmentshown')` および `fragmenthidden` を監視。
   - 現在アクティブになっている `.agenda-step-trigger` の個数からステップ値（`"none"`, `"gray"`, `"all"`, または `[インデックス]`）を取得。
   - `"none"`: 全項目の `.is-active`, `.dimmed` を除去。
   - `"gray"`: 全項目に `.dimmed` を付与。
   - `"all"`: 全項目に `.is-active` を付与。
   - `[インデックス]`: 該当インデックスに `.is-active`、他には `.dimmed` を付与。

### (2) Plotly グラフの描画崩れ防止

Plotly は非表示要素（`display: none` または画面外のスライド）内で初期化されると、親コンテナのサイズを正しく取得できず、グラフが極小化したり潰れたりする問題があります。

- **解決策**:
  - `custom-reveal.js` 内で `Reveal.on('slidechanged')` を購読。
  - スライドが画面上に現れたタイミングで、当該スライド内の `.js-plotly-plot` 要素に対して `Plotly.Plots.resize()` を強制発火させます。

### (3) Jupyter Notebook 上での動的プレビュー

ノートブックの出力セル（IFrame）内で Reveal.js のスライドを確実に動作させるため、以下の工夫を行っています：

1. **Base64 Data URI**:
   - 生成した HTML を `data:text/html;base64,...` 形式にエンコードして `IPython.display.IFrame` に渡すことで、外部 Web サーバーを起動することなく即座にレンダリング。
2. **プレビュー専用 JS 制御**:
   - IFrame 内をクリックした際に自動で `window.focus()` を呼び、キーボードイベント（矢印キーや Space キーでのスライド送り）を確実に IFrame が拾えるようにイベントリスナーを注入。
   - 背景クリックでのページ送りにも対応。
3. **Plotly スクリプトの CDN 最適化**:
   - 単体スライドプレビュー時、4MB を超える Plotly 本体 JS を毎セル Base64 化するとノートブックが極端に重くなるため、プレビュー時のみ Plotly CDN を利用し、ファイル出力時（`to_html`）には完全ローカルインライン化を行います。

### (4) グリッド＆カードの Python ネイティブコンポーザビリティ

以前の Markdown 独自記法（`::: card(...)` や `::: grid`）によるパース処理を廃止し、**コンテナツリー構造による完全な Python オブジェクト操作**を実現しています。

- **`GridCell.add_card(color="...")`**: セル内にカード要素を生成。
- **`GridCell.card` プロパティ**: セル内のカードを直接参照可能（`s_g[0].card.add_markdown(...)`）。
- **`Card.add_image(pil_img)`**: PIL の Image オブジェクトを直接渡せば、自動でインメモリ Base64 エンコードされて `<img src="data:image/png;base64,...">` として埋め込まれます。
- **多段構成**: カードの外（下）に `s_g[0].add_markdown(...)` で注釈を付けたり、スライド全体に `s.add_memo(...)` を配置するなど、直感的な Python コードのネストで自由自在なレイアウトを構築できます。

### (5) フラグメントアニメーション（Reveal.js Fragments）の統合アーキテクチャ

すべての要素の基底クラスである `Element` にフラグメント制御（`fragment`, `fragment_index`, `as_fragment()`, `wrap_fragment()`）を統合しました。

1. **インテリジェントなルートタグ注入 (`wrap_fragment`)**:
   - 余計な外枠 `<div>` の二重ラップを回避するため、`Card`, `GridCell`, `Image`, `Table`, `Graph` などの単一外枠要素では、ルートタグ（`<div class="card...">` など）の `class` 属性に正規表現で直接 `fragment {effect}` を追記し、`data-fragment-index` を付与します。
   - これにより、CSS グリッドレイアウトや Flexbox の親子関係（`.custom-grid > .grid-cell > .card`）の崩れを完全に防ぎます。
2. **Markdown 箇条書き・段落のステップ分割 (`step=True`)**:
   - `format_inline_markdown` 内で、`step=True` が指定された場合、各リスト項目 `<li>` や独立段落 `<p>` に動的に `class="fragment {step_effect}"` を付与します。
   - `step="fade-up"` のようにエフェクト名文字列をそのまま渡すことも可能です。
3. **柔軟な Python API**:
   - コンストラクタ / `add_*` メソッドの引数（`fragment="fade-up"`, `fragment_index=1`）と、メソッドチェーン（`s.add_card(...).as_fragment("fade-up")`）の両方をサポートしています。

---

## 4. デザインシステム仕様

- **基本解像度**: `1280px × 720px`（16:9 黄金比デザインシステム）
- **フォントスタック**: モダンサンセリフ + 和文ゴシック（游ゴシック / ヒラギノ角ゴ / メイリオ）
- **ブランド統一性**:
  - タイトルスライド以外の上部に自動で固定ロゴ（`.slide-fixed-logo`）を表示。
  - SVG ロゴを Base64 化して CSS 内に埋め込むことで、画像のリンク切れを完全に防止。

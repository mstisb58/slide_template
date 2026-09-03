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

### (1) アジェンダのステップ遷移アニメーション

目次スライドにおいて、クリックやキー操作で特定項目を順番にハイライトする機能は、**カスタムデータ属性と Reveal.js のフラグメントイベントの連動**により実現されています。

1. **Python (`renderer.py`) による出力**:
   ```html
   <div class="agenda-list is-step" data-agenda-steps='[[0, 1, 2, 3], [0], [1], [3]]'>
     <div class="agenda-item is-active" data-agenda-index="0">...</div>
     <div class="agenda-item is-active" data-agenda-index="1">...</div>
     ...
   </div>
   <!-- ステップ数に応じた透明なトリガーフラグメント -->
   <div class="agenda-step-trigger fragment fade-in-highlight" data-fragment-index="1"></div>
   <div class="agenda-step-trigger fragment fade-in-highlight" data-fragment-index="2"></div>
   ```
2. **JavaScript (`custom-reveal.js`) による動的制御**:
   - `Reveal.on('fragmentshown')` および `fragmenthidden` を監視。
   - 現在アクティブになっている `.agenda-step-trigger` の個数を数え、対応するステップ配列（例: `[1]`）を取得。
   - インデックスに含まれる項目に `.is-active` を付与し、それ以外に `.dimmed` を付与。

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

---

## 4. デザインシステム仕様

- **基本解像度**: `1280px × 720px`（16:9 黄金比デザインシステム）
- **フォントスタック**: モダンサンセリフ + 和文ゴシック（游ゴシック / ヒラギノ角ゴ / メイリオ）
- **ブランド統一性**:
  - タイトルスライド以外の上部に自動で固定ロゴ（`.slide-fixed-logo`）を表示。
  - SVG ロゴを Base64 化して CSS 内に埋め込むことで、画像のリンク切れを完全に防止。

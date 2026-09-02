# 🛠️ 開発者向け仕様書・アーキテクチャマニュアル (MANUAL.md)

このドキュメントは、**本スライドシステムの内部構造、Reveal.jsとの役割分担、モジュール分割（`assets/py/`）、および拡張方法** を解説した開発者向け仕様書です。

---

## 1. システム概要 ＆ Reveal.js との役割分担

本システムは、世界標準のスライドフレームワーク **Reveal.js** をコアエンジンとして活用しつつ、その上に **「Markdown直感記法」「Base64完全インライン化」「Plotly 3Dグラフ自動連携」「5色デザインシステム」** を独自に構築したハイブリッドアーキテクチャです。

### 役割分担一覧

| 機能領域 | 担当レイヤー | 詳細 |
|---|---|---|
| **スライド実行基盤** | **Reveal.js** (オープンソース) | 2次元ページ遷移（横・縦）、キーボード・タッチ操作、16:9比率維持（スケーリング）、ハッシュURLルーティング |
| **Markdown変換エンジン** | **自作** (`markdown_parser.py`) | `::: agenda`, `::: grid-2:1`, `::: card:blue`, `::: images-2:250`, `::: point`, `::: step` などの独自コンテナ解析 |
| **単一ファイル配布パイプライン** | **自作** (`asset_encoder.py`) | 全CSS/JS/画像/SVGロゴ/グラフをBase64データURIに変換し、1枚の完全自己完結HTML（`slide_embed.html`）を生成 |
| **デザインシステム** | **自作** (`theme-custom.css`) | 5色黄金比パレット（コーポレートイエロー × ロイヤルブルー）、スライド用紙内側ロゴ固定、タイル一覧モーダル |
| **外部グラフ連携** | **自作** (`builder.py`) | `::include(charts/*.html)::` によるPlotlyの自動リサイズ・展開 |

---

## 2. ディレクトリ構成 ＆ モジュール責務

```text
slide_template/
├── build.py                  # ルートのエントリポイント (CLI引数処理)
├── slide.md                  # スライド原稿 (Markdown)
├── slide_refered.html        # [出力] 開発・確認用HTML (相対パス参照)
├── slide_embed.html          # [出力] 配布・本番用HTML (完全インライン自己完結)
│
├── assets/
│   ├── css/                  # CSSスタイルシート
│   │   ├── reveal.min.css    # Reveal.js 基盤CSS
│   │   ├── theme-custom.css  # ★ 独自デザインシステム (5色パレット・レイアウト)
│   │   └── ...
│   ├── js/                   # JSライブラリ群
│   │   ├── reveal.min.js     # Reveal.js 本体
│   │   ├── plotly.min.js     # 3D/2D インタラクティブグラフ描画
│   │   └── ...
│   └── py/                   # ★ ビルドシステム本体 (Pythonモジュール)
│       ├── __init__.py       # パッケージ定義
│       ├── config.py         # パス定数・HTML雛形テンプレート
│       ├── markdown_parser.py# 独自記法・Markdownパーサー・スライド分割
│       ├── asset_encoder.py  # Base64エンコード・CSS内URL置換・インクルード解決
│       └── builder.py        # 参照型＆埋込型HTMLビルダー
│
├── charts/                   # 外部PlotlyグラフHTML (sample_2d.html, sample_3d.html)
└── graph/                    # スライド用画像ファイル (PNG, JPG, SVG)
```

---

## 3. モジュール別ロジック仕様

### ① `assets/py/markdown_parser.py`
Markdownテキストを行単位・ブロック単位で解析し、Reveal.js用HTMLに変換します。

- **`split_slides(md_text)`**:
  - `\n---\n` ➜ 水平スライド（親 `<section>`）
  - `\n--\n` ➜ 垂直スタック（親 `<section>` 内の子 `<section>`）
- **`process_custom_containers(text)`**:
  - `::: agenda[:option]` ➜ 目次生成 ＆ `fragment` による自由なハイライトシーケンス制御
  - `::: grid-([0-9:-]+)` ➜ `grid-2`, `grid-2-1` (左2/3:右1/3), `grid-1-2` (左1/3:右2/3) への展開
  - `::: card(?::([a-zA-Z0-9_-]+))?` ➜ `card`, `card-blue`, `card-red`, `card-yellow`, `card-gold` への展開
  - `::: images-([23])(?::([^\n]+))?` ➜ 2枚/3枚の横並び配置 ＆ `--img-max-h` による高さ統一
  - `::: point` ➜ `point-box`（内部にgridや画像のネストが可能）
  - `::: step` ➜ 内部リストを `<li class="fragment">` に自動変換
- **`markdown_to_html(md_text)`**:
  - テーブル（`|...|`）、コードブロック（```` ``` ````）、数式（`$$...$$`）、見出し（`#`, `##`, `###`）を行単位でパース。

---

### ② `assets/py/asset_encoder.py`
完全自己完結HTML（`slide_embed.html`）を生成するためのエンコーダー。

- **`to_data_uri(file_path)`**:
  - 画像やフォントファイルをバイナリ読み込みし、MIMEタイプ付きの `data:{mime};base64,...` 文字列を生成。
- **`embed_css_urls(css_content, base_dir)`**:
  - CSS内部の `url("./logo.svg")` などを正規表現で走査し、Base64データURIに置換。
- **`resolve_includes(html_content, base_dir)`**:
  - `::include(path/to/chart.html)::` を検出し、外部HTMLの中身を自動抽出して `<div class="included-chart-container">` 内に展開。

---

### ③ `assets/py/builder.py`
- **`build_refered_html(slides_html)`**:
  - 相対パス（`./assets/...`）でCSS/JSを読み込む高速HTMLを生成。
- **`build_embed_html(slides_html)`**:
  - 全CSS・JSを `<style>` / `<script>` でインライン展開し、全画像・グラフをBase64化して埋め込み。
- **`build_all()`**:
  - 上記の2系統を同時にビルドして出力。

---

## 4. 拡張・カスタマイズ方法

### 💡 新しい独自記法（`::: xxx`）を追加したい場合
[assets/py/markdown_parser.py](file:///c:/Users/isobe/project/html/slide_template/assets/py/markdown_parser.py) の `process_custom_containers()` 内に正規表現ルールを追加し、[assets/css/theme-custom.css](file:///c:/Users/isobe/project/html/slide_template/assets/css/theme-custom.css) にスタイルを追記します。

### 💡 カラーパレットを変更したい場合
[assets/css/theme-custom.css](file:///c:/Users/isobe/project/html/slide_template/assets/css/theme-custom.css) の `:root` 内の変数（`--accent`, `--accent-blue` など）を編集するだけで、全スライドに一括適用されます。

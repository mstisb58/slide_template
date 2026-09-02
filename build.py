#!/usr/bin/env python3
"""
スライドビルド実行スクリプト (エントリポイント)

使い方:
  uv run build.py           # 通常ビルド
  uv run build.py --open    # ビルド後にブラウザで自動プレビュー
"""
import argparse
import sys
import webbrowser
from pathlib import Path

# Windows環境でのUTF-8出力対応
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# assets/py モジュールの読み込み
from assets.py import build_all, REFERED_HTML, EMBED_HTML


def main():
    parser = argparse.ArgumentParser(description="Markdown to Interactive HTML Slide Builder")
    parser.add_argument("--open", "-o", action="store_true", help="ビルド完了後にブラウザで自動オープン")
    parser.add_argument("--embed-only", action="store_true", help="配布用埋込HTMLのみ生成")
    args = parser.parse_args()

    try:
        refered_path, embed_path = build_all()
        if args.open:
            webbrowser.open(refered_path.as_uri())
    except Exception as e:
        print(f"❌ ビルドエラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

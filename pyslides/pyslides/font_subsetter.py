import os
import re
import html
import base64
import tempfile
from pathlib import Path
from fontTools.subset import main as fonttools_subset
from fontTools.ttLib import TTFont, TTCollection


def _get_system_font_dir() -> Path:
    """OS別のシステムフォントディレクトリを返す"""
    import platform
    system = platform.system()
    if system == 'Windows':
        return Path('C:/Windows/Fonts')
    elif system == 'Darwin':
        return Path('/System/Library/Fonts')
    elif system == 'Linux':
        return Path('/usr/share/fonts')
    return None


def _get_font_family_names(font_path: str) -> list:
    """
    フォントファイル（.ttf / .ttc）に含まれるフォントファミリー名を全て返す。
    TTCの場合は [(font_index, family_name), ...] のリストを返す。
    """
    results = []
    p = Path(font_path)
    ext = p.suffix.lower()

    try:
        if ext == '.ttc':
            tc = TTCollection(str(font_path))
            for i, font in enumerate(tc.fonts):
                name_table = font['name']
                for record in name_table.names:
                    if record.nameID == 1:  # Family name
                        try:
                            name = record.toUnicode()
                            results.append((i, name))
                        except Exception:
                            pass
        else:
            font = TTFont(str(font_path))
            name_table = font['name']
            for record in name_table.names:
                if record.nameID == 1:
                    try:
                        name = record.toUnicode()
                        results.append((0, name))
                    except Exception:
                        pass
    except Exception:
        pass

    return results


def find_font_for_css(css_paths: list) -> tuple:
    """
    CSSファイルから --font-main の最初のフォント名を読み取り、
    システムフォントディレクトリからそのフォントの実体ファイルを探す。

    Returns:
        (font_file_path: str, font_number: int, font_family_name: str)
        見つからない場合は (None, None, None)
    """
    # 1. CSSから --font-main のフォント名を抽出
    target_font_name = None
    for css_path in (css_paths or []):
        if not css_path or not os.path.exists(css_path):
            continue
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        m = re.search(r'--font-main\s*:\s*(.+?)\s*;', css_content)
        if m:
            font_list_str = m.group(1)
            # カンマで分割し、最初のクォートされたフォント名を取得
            for part in font_list_str.split(','):
                part = part.strip().strip('"').strip("'")
                # システムフォント指定（-apple-system等）やジェネリックファミリー（sans-serif等）はスキップ
                if part.startswith('-') or part in ('sans-serif', 'serif', 'monospace', 'cursive', 'system-ui'):
                    continue
                target_font_name = part
                break
        if target_font_name:
            break

    if not target_font_name:
        return (None, None, None)

    # 2. システムフォントディレクトリを走査して、フォントの中身を読みフォント名が一致するものを探す
    font_dir = _get_system_font_dir()
    if not font_dir or not font_dir.exists():
        return (None, None, None)

    for font_file in sorted(font_dir.glob('*.tt[cf]')):
        family_entries = _get_font_family_names(str(font_file))
        for font_number, family_name in family_entries:
            if family_name == target_font_name:
                return (str(font_file), font_number, family_name)

    return (None, None, None)


def extract_unique_chars(html_str: str) -> str:
    """
    HTML文字列からテキスト部分だけを抽出し、ユニークな文字の文字列を返す。
    """
    # scriptとstyleの中身を除外
    html_str = re.sub(r'<(script|style).*?>.*?</\1>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', '', html_str)
    # 実体参照(&nbsp;など)をデコード
    text = html.unescape(text)
    text = re.sub(r'[\r\n\t]+', '', text)

    # 常に含めるべき基本文字群
    basic_chars = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~　"

    unique_chars = "".join(sorted(set(text + basic_chars)))
    return unique_chars


def generate_subset(font_path: str, font_number: int, html_str: str, output_path: str = None) -> str:
    """
    指定されたHTML内に含まれる文字だけを抽出して、WOFF2形式のサブセットフォントを生成する。
    output_path が指定されていればそこに保存し、そのパスを返す。
    指定されていなければ、一時ファイルに生成してBase64文字列（data URI）を返す。
    """
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")

    chars = extract_unique_chars(html_str)

    is_base64_mode = False
    if output_path is None:
        is_base64_mode = True
        fd, output_path = tempfile.mkstemp(suffix=".woff2")
        os.close(fd)
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    args = [
        str(font_path),
        f"--text={chars}",
        "--flavor=woff2",
        f"--output-file={output_path}",
        "--layout-features=*",
        "--desubroutinize",
        f"--font-number={font_number}"
    ]

    try:
        fonttools_subset(args)
    except Exception as e:
        if is_base64_mode and os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError(f"Font subsetting failed: {e}") from e

    if is_base64_mode:
        with open(output_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(output_path)
        return f"data:font/woff2;base64,{b64}"
    else:
        return output_path

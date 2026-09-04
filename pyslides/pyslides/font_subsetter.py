import os
import re
import html
import base64
import tempfile
from pathlib import Path
from fontTools.subset import main as fonttools_subset

def find_default_font_path() -> str:
    """
    システムにインストールされている標準的な日本語ゴシックフォントのパスを自動探索して返す。
    見つからなかった場合は None を返す。
    """
    import platform
    system = platform.system()
    
    candidates = []
    if system == 'Windows':
        font_dir = Path('C:/Windows/Fonts')
        candidates = [
            font_dir / 'BIZ-UDPGothic.ttc',
            font_dir / 'bizudpgothic.ttc',
            font_dir / 'BIZ-UDGothicR.ttc',
            font_dir / 'yuGothR.ttc',      # 游ゴシック Regular
            font_dir / 'msgothic.ttc',     # MSゴシック
            font_dir / 'meiryo.ttc'        # メイリオ
        ]
    elif system == 'Darwin': # Mac
        candidates = [
            Path('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'),
            Path('/System/Library/Fonts/Hiragino Sans W3.ttc'),
            Path('/Library/Fonts/BIZUDPGothic-Regular.ttf')
        ]
    elif system == 'Linux':
        candidates = [
            Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
            Path('/usr/share/fonts/noto/NotoSansCJK-Regular.ttc'),
            Path('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf')
        ]
        
    for p in candidates:
        if p.exists():
            return str(p)
            
    return None

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
    # 全ての空白文字を除去（空白文字はフォント側のスペースグリフで持っていることが多いが、
    # 念のため半角・全角スペースは残すか？いや、空白文字自体はASCIIなどで常に含まれるようにする）
    text = re.sub(r'[\r\n\t]+', '', text)
    
    # 常に含めるべき基本文字群 (ASCII記号, 数字, アルファベット)
    basic_chars = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~　"
    
    unique_chars = "".join(sorted(set(text + basic_chars)))
    return unique_chars

def generate_subset(font_path: str, html_str: str, output_path: str = None) -> str:
    """
    指定されたHTML内に含まれる文字だけを抽出して、WOFF2形式のサブセットフォントを生成する。
    output_path が指定されていればそこに保存し、そのパスを返す。
    指定されていなければ、一時ファイルに生成してBase64文字列（data URI）を返す。
    """
    if not os.path.exists(font_path):
        print(f"Warning: Font file not found at {font_path}")
        return ""
        
    chars = extract_unique_chars(html_str)
    
    # fontTools.subset はコマンドライン引数のようにリストを渡す
    # args: font_file --text="chars" --flavor=woff2
    
    # 一時ファイルに出力するかどうか
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
        "--obfuscate_names",
        "--font-number=0"
    ]
    
    try:
        fonttools_subset(args)
    except Exception as e:
        print(f"Error during font subsetting: {e}")
        if is_base64_mode and os.path.exists(output_path):
            os.remove(output_path)
        return ""
        
    if is_base64_mode:
        with open(output_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(output_path)
        return f"data:font/woff2;base64,{b64}"
    else:
        return output_path

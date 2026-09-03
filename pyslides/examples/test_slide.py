import os
import sys

# pyslidesパッケージをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import plotly.express as px
from pyslides import Deck

def main():
    # 1. デッキの初期化
    deck = Deck(title="Pyslides Demo", theme="kracie")

    # 2. タイトルスライド
    s1 = deck.add_slide(template="title", title="pyslidesの紹介", author="AI Assistant")

    # 3. Plotly 動的グラフ生成
    df = px.data.iris()
    fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species",
                     size='petal_length', hover_data=['petal_width'])
                     
    # レイアウト微調整 (スライドに合うように)
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 4. コンテンツスライド (Grid分割とグラフ埋め込み)
    s2 = deck.add_slide(template="default")
    g = s2.grid(col="2:3")
    g.left.markdown = """
    ## Plotly グラフの直接埋め込み
    
    - ファイル保存は不要です
    - メモリ上の `fig` オブジェクトを代入するだけ
    - グリッドの比率指定も `col="2:3"` のように可能
    """
    
    # グラフを左側、いや右側にセット
    g.right.chart = fig

    # 5. HTML出力
    output_path = os.path.join(os.path.dirname(__file__), "presentation.html")
    deck.to_html(output_path, embed=True)
    
if __name__ == "__main__":
    main()

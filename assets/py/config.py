"""
設定およびHTMLテンプレート定義
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
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
<body>
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

    // スライド切り替えイベント (Plotly遅延実行 & リサイズ)
    function initPlotlyOnSlide(scopeEl) {
      if (!scopeEl) return;
      const root = scopeEl || document;

      // 1. 初回表示時のみ: 遅延されていたPlotlyスクリプトを実行
      const delayedScripts = root.querySelectorAll('script.plotly-delayed-script');
      delayedScripts.forEach(scriptEl => {
        // 新しいscriptタグを作って実行
        const newScript = document.createElement('script');
        newScript.type = 'text/javascript';
        newScript.textContent = scriptEl.textContent;
        // DOMに挿入して実行させる
        scriptEl.parentNode.insertBefore(newScript, scriptEl.nextSibling);
        // 二重実行防止
        scriptEl.classList.remove('plotly-delayed-script');
        scriptEl.classList.add('plotly-delayed-script-done');
      });

      // 2. 既に描画済みのグラフがあればリサイズ処理
      if (typeof Plotly !== 'undefined') {
        root.querySelectorAll('.plotly-graph-div, .js-plotly-plot, [id^="chart-"]').forEach(function(el) {
          try {
            var container = el.closest('.included-chart-container') || el.parentElement;
            var w = container ? container.clientWidth : 0;
            var h = container ? container.clientHeight : 0;
            // コンテナがまだ非表示(サイズ0)の場合は何もしない
            if (w === 0 || h === 0) return;

            var update = { autosize: true, width: w, height: h };

            if (!el._fullLayout || !el._fullLayout.scene) {
              update.margin = { l: 35, r: 15, t: 35, b: 30 };
              update.font = { size: 9 };
              update.titlefont = { size: 11 };
            }
            Plotly.relayout(el, update);
            Plotly.Plots.resize(el);
          } catch(e) {
            try { Plotly.Plots.resize(el); } catch(e2) {}
          }
        });
      }
    }


    function updateSlideState() {
      const indices = Reveal.getIndices();
      const isTitle = (indices.h === 0 && indices.v === 0);
      document.body.classList.toggle('is-title-slide', isTitle);
    }

    Reveal.on('ready', function(event) {
      initEnhancements();
      updateSlideState();
      setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 100);
      setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 500); // 念のため
    });

    Reveal.on('slidechanged', function(event) {
      updateSlideState();
      // スライドが表示され、DOMのサイズ計算が終わるのを少し待ってから実行
      setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 100);
      setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 500);
    });
  </script>
</body>

</html>
"""


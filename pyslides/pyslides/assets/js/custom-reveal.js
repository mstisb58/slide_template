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
    const newScript = document.createElement('script');
    newScript.type = 'text/javascript';
    newScript.textContent = scriptEl.textContent;
    scriptEl.parentNode.insertBefore(newScript, scriptEl.nextSibling);
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

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

function resizePlotlyElement(el) {
  try {
    var container = el.closest('.included-chart-container') || el.parentElement;
    var w = container ? container.clientWidth : 0;
    var h = container ? container.clientHeight : 0;
    if (w === 0 || h === 0) return;

    var update = { autosize: true, width: w, height: h };

    if (!el._fullLayout || !el._fullLayout.scene) {
      update.margin = { l: 55, r: 25, t: 42, b: 42 };
      update['xaxis.automargin'] = true;
      update['yaxis.automargin'] = true;
      update.font = { size: 9 };
      update.titlefont = { size: 11 };
    }
    Plotly.relayout(el, update);
    Plotly.Plots.resize(el);
  } catch(e) {
    try { Plotly.Plots.resize(el); } catch(e2) {}
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

  // 2. 描画済みのグラフのリサイズ & ResizeObserver設定
  if (typeof Plotly !== 'undefined') {
    root.querySelectorAll('.plotly-graph-div, .js-plotly-plot, [id^="chart-"]').forEach(function(el) {
      resizePlotlyElement(el);

      var container = el.closest('.included-chart-container') || el.parentElement;
      if (container && typeof ResizeObserver !== 'undefined' && !container._plotlyObserver) {
        container._plotlyObserver = new ResizeObserver(function() {
          resizePlotlyElement(el);
        });
        container._plotlyObserver.observe(container);
      }
    });
  }
}

function updateSlideState(currentSlide) {
  var slide = currentSlide || Reveal.getCurrentSlide();
  var isTitle = false;
  if (slide) {
    isTitle = slide.classList.contains('title-section') || !!slide.querySelector('.title-slide');
  } else {
    var firstSection = document.querySelector('.reveal .slides > section');
    if (firstSection) {
      isTitle = firstSection.classList.contains('title-section') || !!firstSection.querySelector('.title-slide');
    }
  }
  document.body.classList.toggle('is-title-slide', isTitle);
}

function updateAgendaSteps(scopeEl) {
  var root = scopeEl || document;
  var container = root.querySelector('.agenda-list[data-agenda-steps]');
  if (!container) return;
  var raw = container.getAttribute('data-agenda-steps');
  if (!raw) return;
  try {
    var steps = JSON.parse(raw);
    if (!steps || !steps.length) return;
    var section = container.closest('section');
    if (!section) return;
    var visibleTriggers = section.querySelectorAll('.agenda-step-trigger.visible');
    var stepIdx = visibleTriggers.length;
    if (stepIdx >= steps.length) stepIdx = steps.length - 1;
    var step = steps[stepIdx];
    var items = container.querySelectorAll('.agenda-item');

    if (step === 'none') {
      items.forEach(function(item) {
        item.classList.remove('is-active', 'active-fixed', 'dimmed');
      });
    } else if (step === 'gray' || step === 'grey') {
      items.forEach(function(item) {
        item.classList.remove('is-active', 'active-fixed');
        item.classList.add('dimmed');
      });
    } else if (step === 'all') {
      items.forEach(function(item) {
        item.classList.add('is-active');
        item.classList.remove('dimmed');
      });
    } else {
      var activeIndices = Array.isArray(step) ? step : [step];
      items.forEach(function(item, idx) {
        if (activeIndices.indexOf(idx) !== -1) {
          item.classList.add('is-active');
          item.classList.remove('dimmed');
        } else {
          item.classList.remove('is-active', 'active-fixed');
          item.classList.add('dimmed');
        }
      });
    }
  } catch(e) {}
}

Reveal.on('ready', function(event) {
  initEnhancements();
  updateSlideState(event.currentSlide);
  updateAgendaSteps(event.currentSlide);
  setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 100);
  setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 500); // 念のため
});

Reveal.on('slidechanged', function(event) {
  updateSlideState(event.currentSlide);
  updateAgendaSteps(event.currentSlide);
  setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 100);
  setTimeout(function() { initPlotlyOnSlide(event.currentSlide); }, 500);
});

Reveal.on('fragmentshown', function(event) {
  updateAgendaSteps(Reveal.getCurrentSlide());
});

Reveal.on('fragmenthidden', function(event) {
  updateAgendaSteps(Reveal.getCurrentSlide());
});

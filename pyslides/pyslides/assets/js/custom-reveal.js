// Reveal.jsの初期化 (1920x1080 16:9 Full HD 最適化)
Reveal.initialize({
  hash: true,
  slideNumber: 'c/t',
  showSlideNumber: 'all',
  transition: 'slide',
  center: false,
  width: 1920,
  height: 1080,
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

// --- レーザーポインター機能 (Zoom/画面共有用 DOMポインター & クリック波紋) ---
(function() {
  let isLaserActive = false;
  let laserPointerEl = null;

  function initLaserPointer() {
    // 1. ポインター要素の生成
    if (!laserPointerEl) {
      laserPointerEl = document.createElement('div');
      laserPointerEl.className = 'laser-pointer';
      document.body.appendChild(laserPointerEl);
    }

    // 2. コントロールバーの初期化・F, L, O ボタンの追加
    let controlsBar = document.querySelector('.slide-controls-bar');
    if (!controlsBar) {
      controlsBar = document.createElement('div');
      controlsBar.className = 'slide-controls-bar';
      document.body.appendChild(controlsBar);
    }
    controlsBar.innerHTML = '';

    // F (全画面表示)
    const btnF = document.createElement('button');
    btnF.className = 'control-btn';
    btnF.id = 'btn-fullscreen';
    btnF.title = '全画面表示 (F)';
    btnF.textContent = 'F';
    btnF.onclick = toggleFullscreen;
    controlsBar.appendChild(btnF);

    // L (レーザーポインター)
    const btnL = document.createElement('button');
    btnL.className = 'control-btn';
    btnL.id = 'btn-laser';
    btnL.title = 'レーザーポインター (L)';
    btnL.textContent = 'L';
    btnL.onclick = toggleLaserPointer;
    controlsBar.appendChild(btnL);

    // O (タイル一覧/概要)
    const btnO = document.createElement('button');
    btnO.className = 'control-btn';
    btnO.id = 'btn-overview';
    btnO.title = 'タイル一覧 (O / ESC)';
    btnO.textContent = 'O';
    btnO.onclick = function() {
      if (typeof Reveal !== 'undefined' && Reveal.toggleOverview) {
        Reveal.toggleOverview();
      }
    };
    controlsBar.appendChild(btnO);

    // 状態変更時のスタイル同期
    if (typeof Reveal !== 'undefined' && Reveal.on) {
      Reveal.on('overviewshown', function() { btnO.classList.add('is-active'); });
      Reveal.on('overviewhidden', function() { btnO.classList.remove('is-active'); });
    }
    document.addEventListener('fullscreenchange', function() {
      if (document.fullscreenElement) {
        btnF.classList.add('is-active');
      } else {
        btnF.classList.remove('is-active');
      }
    });


    // 3. マウス追従
    window.addEventListener('mousemove', function(e) {
      if (!isLaserActive || !laserPointerEl) return;
      laserPointerEl.style.left = e.clientX + 'px';
      laserPointerEl.style.top = e.clientY + 'px';
    });

    // 画面外に出たときの処理
    document.addEventListener('mouseleave', function() {
      if (laserPointerEl) laserPointerEl.style.opacity = '0';
    });
    document.addEventListener('mouseenter', function() {
      if (laserPointerEl && isLaserActive) laserPointerEl.style.opacity = '1';
    });

    // 4. クリック時の波紋（Ripple）エフェクト
    window.addEventListener('mousedown', function(e) {
      if (!isLaserActive) return;
      if (e.target.closest && e.target.closest('.control-btn')) return;

      createLaserRipple(e.clientX, e.clientY);
    });
  }

  function createLaserRipple(x, y) {
    const ripple = document.createElement('div');
    ripple.className = 'laser-ripple';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    document.body.appendChild(ripple);
    setTimeout(function() {
      if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
    }, 500);
  }

  function toggleLaserPointer() {
    isLaserActive = !isLaserActive;
    document.body.classList.toggle('laser-pointer-active', isLaserActive);

    const btn = document.getElementById('btn-laser');
    if (btn) {
      btn.classList.toggle('laser-active', isLaserActive);
    }

    if (!isLaserActive && laserPointerEl) {
      laserPointerEl.style.opacity = '0';
    } else if (isLaserActive && laserPointerEl) {
      laserPointerEl.style.opacity = '1';
    }
  }

  window.toggleLaserPointer = toggleLaserPointer;

  // Reveal.js キーバインド登録 (L キー)
  if (typeof Reveal !== 'undefined' && Reveal.addKeyBinding) {
    Reveal.addKeyBinding({ keyCode: 76, key: 'L', description: 'Toggle Laser Pointer' }, function() {
      toggleLaserPointer();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLaserPointer);
  } else {
    initLaserPointer();
  }
})();


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

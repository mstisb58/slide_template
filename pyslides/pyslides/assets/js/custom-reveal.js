// Reveal.jsの初期化 (1920x1080 16:9 Full HD 最適化)
Reveal.initialize({
  hash: true,
  slideNumber: 'c/t',
  showSlideNumber: 'all',
  transition: 'slide',
  navigationMode: 'linear',
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
      if (typeof toggleSlideSorter === 'function') {
        toggleSlideSorter();
      } else if (typeof Reveal !== 'undefined' && Reveal.toggleOverview) {
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
  var target = event.fragment || Reveal.getCurrentSlide();
  setTimeout(function() {
    initPlotlyOnSlide(target);
  }, 20);
  setTimeout(function() {
    initPlotlyOnSlide(target);
    if (typeof Plotly !== 'undefined') {
      target.querySelectorAll('.plotly-graph-div, .js-plotly-plot, [id^="chart-"]').forEach(function(el) {
        resizePlotlyElement(el);
        try { Plotly.relayout(el, {autosize: true}); } catch(e) {}
      });
    }
  }, 120);
});

Reveal.on('fragmenthidden', function(event) {
  updateAgendaSteps(Reveal.getCurrentSlide());
});

// ==========================================================================
// PowerPoint スタイル・スライド一覧（タイル・ソーター）モード
// ==========================================================================
(function() {
  let sorterModal = null;
  let isSorterOpen = false;
  let selectedCardIndex = 0;

  function isInputFocused(e) {
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : '';
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target && e.target.isContentEditable);
  }

  function getSlideTitle(sec, index) {
    if (!sec) return 'スライド ' + (index + 1);
    const h1 = sec.querySelector('h1');
    if (h1 && h1.textContent.trim()) return h1.textContent.trim();
    const h2 = sec.querySelector('h2');
    if (h2 && h2.textContent.trim()) return h2.textContent.trim();
    const h3 = sec.querySelector('h3');
    if (h3 && h3.textContent.trim()) return h3.textContent.trim();
    const titleTopic = sec.querySelector('.title-topic');
    if (titleTopic && titleTopic.textContent.trim()) return titleTopic.textContent.trim();
    const agendaTitle = sec.querySelector('.agenda-title');
    if (agendaTitle && agendaTitle.textContent.trim()) return agendaTitle.textContent.trim();
    return 'スライド ' + (index + 1);
  }

  function getFlatSlideList() {
    // Reveal.jsの全実体スライド（stackコンテナを除外した個別section）
    return Array.from(document.querySelectorAll('.reveal .slides section:not(.stack)'));
  }

  function getSlideCoordinates(sec) {
    if (typeof Reveal !== 'undefined' && Reveal.getIndices) {
      const idx = Reveal.getIndices(sec);
      if (idx && typeof idx.h === 'number') {
        return { h: idx.h, v: idx.v || 0 };
      }
    }
    // Fallback: DOM構造から h, v を算出
    if (sec.parentElement && sec.parentElement.tagName === 'SECTION') {
      const parentStack = sec.parentElement;
      const h = Array.from(parentStack.parentElement.children).indexOf(parentStack);
      const v = Array.from(parentStack.children).indexOf(sec);
      return { h: Math.max(0, h), v: Math.max(0, v) };
    }
    const h = Array.from(sec.parentElement.children).indexOf(sec);
    return { h: Math.max(0, h), v: 0 };
  }

  function createSorterModal() {
    if (sorterModal) return sorterModal;

    sorterModal = document.createElement('div');
    sorterModal.id = 'slide-sorter-modal';
    sorterModal.className = 'slide-sorter-modal';
    sorterModal.style.display = 'none';

    sorterModal.innerHTML = `
      <div class="slide-sorter-header">
        <div class="slide-sorter-header-left">
          <span class="slide-sorter-icon">🗂️</span>
          <h3 class="slide-sorter-heading">スライド一覧 (Slide Sorter)</h3>
          <span class="slide-sorter-badge-total" id="sorter-total-count">0 枚</span>
        </div>
        <div class="slide-sorter-header-right">
          <span class="slide-sorter-keyboard-hint">↑ ↓ ← → で選択 / Enter またはクリックで移動 / Esc・O で閉じる</span>
          <button class="slide-sorter-btn-close" id="sorter-btn-close" title="閉じる (Esc)">✕</button>
        </div>
      </div>
      <div class="slide-sorter-body" id="sorter-body">
        <div class="slide-sorter-grid" id="sorter-grid"></div>
      </div>
    `;

    document.body.appendChild(sorterModal);

    // 閉じるボタン
    const btnClose = sorterModal.querySelector('#sorter-btn-close');
    if (btnClose) {
      btnClose.addEventListener('click', function(e) {
        e.stopPropagation();
        closeSlideSorter();
      });
    }

    // モーダル背景クリック時（グリッドやカード以外）に閉じる
    sorterModal.addEventListener('click', function(e) {
      if (e.target === sorterModal || e.target.id === 'sorter-body') {
        closeSlideSorter();
      }
    });

    window.addEventListener('resize', function() {
      if (isSorterOpen) {
        updateCardScales();
      }
    });

    return sorterModal;
  }

  function updateCardScales() {
    if (!sorterModal) return;
    const cards = sorterModal.querySelectorAll('.slide-sorter-card');
    cards.forEach(card => {
      const preview = card.querySelector('.slide-sorter-card-preview');
      const canvas = card.querySelector('.slide-sorter-canvas');
      if (preview && canvas) {
        const previewWidth = preview.clientWidth;
        if (previewWidth > 0) {
          const scale = previewWidth / 1920;
          canvas.style.transform = `scale(${scale})`;
        }
      }
    });
  }

  function buildGrid() {
    createSorterModal();
    const grid = sorterModal.querySelector('#sorter-grid');
    const totalBadge = sorterModal.querySelector('#sorter-total-count');
    grid.innerHTML = '';

    const slides = getFlatSlideList();
    if (totalBadge) {
      totalBadge.textContent = slides.length + ' 枚';
    }

    const currentSlide = (typeof Reveal !== 'undefined' && Reveal.getCurrentSlide) ? Reveal.getCurrentSlide() : null;
    let currentIdx = -1;

    slides.forEach((sec, idx) => {
      const coords = getSlideCoordinates(sec);
      const isCurrent = (sec === currentSlide);
      if (isCurrent) currentIdx = idx;

      const title = getSlideTitle(sec, idx);

      const card = document.createElement('div');
      card.className = 'slide-sorter-card' + (isCurrent ? ' is-current-slide' : '');
      card.setAttribute('tabindex', '0');
      card.setAttribute('data-index', idx);
      card.setAttribute('data-h', coords.h);
      card.setAttribute('data-v', coords.v);

      const preview = document.createElement('div');
      preview.className = 'slide-sorter-card-preview';

      // 16:9キャンバスラッパー (スライド紙面を100%遮らず表示)
      const wrapper = document.createElement('div');
      wrapper.className = 'slide-sorter-canvas-wrapper';

      const canvas = document.createElement('div');
      canvas.className = 'slide-sorter-canvas reveal';

      const slidesWrap = document.createElement('div');
      slidesWrap.className = 'slides';

      // タイトルスライド以外は固定ロゴを表示
      const isTitle = sec.classList.contains('title-section') || !!sec.querySelector('.title-slide');
      if (!isTitle) {
        const logo = document.createElement('div');
        logo.className = 'slide-fixed-logo';
        slidesWrap.appendChild(logo);
      }

      // スライド本体のディープクローン
      const clone = sec.cloneNode(true);
      clone.classList.remove('future', 'past', 'stack');
      clone.classList.add('present');
      clone.style.display = '';
      clone.style.transform = 'none';

      // タイル一覧内では全フラグメントを表示状態にする（全体を俯瞰できるように）
      clone.querySelectorAll('.fragment').forEach(f => {
        f.classList.add('visible');
        f.classList.remove('current-fragment');
        f.style.opacity = '1';
        f.style.visibility = 'visible';
        f.style.transform = 'none';
      });

      // アジェンダアイテムも全表示
      clone.querySelectorAll('.agenda-item').forEach(item => {
        item.classList.add('is-active');
        item.classList.remove('dimmed');
      });

      slidesWrap.appendChild(clone);
      canvas.appendChild(slidesWrap);
      wrapper.appendChild(canvas);
      preview.appendChild(wrapper);
      card.appendChild(preview);

      // フッター（スライド番号・タイトル・現在タグ）
      const footer = document.createElement('div');
      footer.className = 'slide-sorter-card-footer';

      const numSpan = document.createElement('span');
      numSpan.className = 'slide-sorter-card-number';
      numSpan.textContent = (idx + 1);
      footer.appendChild(numSpan);

      const titleSpan = document.createElement('span');
      titleSpan.className = 'slide-sorter-card-title';
      titleSpan.textContent = title;
      titleSpan.title = title;
      footer.appendChild(titleSpan);

      if (isCurrent) {
        const curBadge = document.createElement('span');
        curBadge.className = 'slide-sorter-card-current-badge';
        curBadge.textContent = '現在';
        footer.appendChild(curBadge);
      }

      card.appendChild(footer);

      // クリックイベントで該当スライドへ遷移
      card.addEventListener('click', function() {
        navigateToSlide(coords.h, coords.v);
      });

      card.addEventListener('focus', function() {
        setSelectedCard(idx, false);
      });

      grid.appendChild(card);
    });

    selectedCardIndex = currentIdx >= 0 ? currentIdx : 0;
  }

  function setSelectedCard(idx, shouldFocus = true) {
    if (!sorterModal) return;
    const cards = sorterModal.querySelectorAll('.slide-sorter-card');
    if (idx < 0 || idx >= cards.length) return;

    cards.forEach((c, i) => {
      c.classList.toggle('is-selected', i === idx);
    });

    selectedCardIndex = idx;
    if (shouldFocus && cards[idx]) {
      cards[idx].focus();
      cards[idx].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function navigateToSlide(h, v) {
    closeSlideSorter();
    if (typeof Reveal !== 'undefined' && Reveal.slide) {
      Reveal.slide(h, v, 0);
    }
  }

  function openSlideSorter() {
    if (isSorterOpen) return;
    buildGrid();
    sorterModal.style.display = 'flex';
    isSorterOpen = true;

    // コントロールボタンのアクティブ化
    const btnO = document.getElementById('btn-overview');
    if (btnO) btnO.classList.add('is-active');

    // スケール計算 & 現在のスライドカードへスクロール
    requestAnimationFrame(() => {
      updateCardScales();
      const cards = sorterModal.querySelectorAll('.slide-sorter-card');
      if (cards[selectedCardIndex]) {
        setSelectedCard(selectedCardIndex, true);
        cards[selectedCardIndex].scrollIntoView({ behavior: 'auto', block: 'center' });
      }
    });

    // Revealのカスタムイベント発火
    if (typeof Reveal !== 'undefined' && Reveal.dispatchEvent) {
      try {
        Reveal.dispatchEvent({ type: 'overviewshown' });
      } catch(e) {}
    }
  }

  function closeSlideSorter() {
    if (!isSorterOpen || !sorterModal) return;
    sorterModal.style.display = 'none';
    isSorterOpen = false;

    // コントロールボタンの解除
    const btnO = document.getElementById('btn-overview');
    if (btnO) btnO.classList.remove('is-active');

    // Revealにフォーカス復帰
    if (typeof Reveal !== 'undefined' && Reveal.focus) {
      Reveal.focus();
    }

    if (typeof Reveal !== 'undefined' && Reveal.dispatchEvent) {
      try {
        Reveal.dispatchEvent({ type: 'overviewhidden' });
      } catch(e) {}
    }
  }

  function toggleSlideSorter() {
    if (isSorterOpen) {
      closeSlideSorter();
    } else {
      openSlideSorter();
    }
  }

  function handleSorterKeyboard(e) {
    if (!isSorterOpen || !sorterModal) return;

    if (e.key === 'Escape' || e.key === 'o' || e.key === 'O') {
      e.preventDefault();
      e.stopPropagation();
      closeSlideSorter();
      return;
    }

    const cards = Array.from(sorterModal.querySelectorAll('.slide-sorter-card'));
    if (cards.length === 0) return;

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      const currentCard = cards[selectedCardIndex];
      if (currentCard) {
        const h = parseInt(currentCard.getAttribute('data-h') || '0', 10);
        const v = parseInt(currentCard.getAttribute('data-v') || '0', 10);
        navigateToSlide(h, v);
      }
      return;
    }

    // 列数の計算（1行目のカード数）
    let cols = 1;
    if (cards.length > 1) {
      const firstTop = cards[0].offsetTop;
      for (let i = 1; i < cards.length; i++) {
        if (cards[i].offsetTop === firstTop) {
          cols++;
        } else {
          break;
        }
      }
    }

    let targetIdx = selectedCardIndex;

    if (e.key === 'ArrowRight') {
      e.preventDefault();
      e.stopPropagation();
      targetIdx = Math.min(cards.length - 1, selectedCardIndex + 1);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      e.stopPropagation();
      targetIdx = Math.max(0, selectedCardIndex - 1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      e.stopPropagation();
      targetIdx = Math.min(cards.length - 1, selectedCardIndex + cols);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      e.stopPropagation();
      targetIdx = Math.max(0, selectedCardIndex - cols);
    }

    if (targetIdx !== selectedCardIndex) {
      setSelectedCard(targetIdx, true);
    }
  }

  // グローバルキーリスナー（キャプチャフェーズで 'O', 'ESC', 矢印キーを確実にキャッチ）
  window.addEventListener('keydown', function(e) {
    if (isSorterOpen) {
      handleSorterKeyboard(e);
      return;
    }

    // ソーターが閉じていて入力フィールドにいないとき
    if ((e.key === 'o' || e.key === 'O') && !isInputFocused(e)) {
      e.preventDefault();
      e.stopPropagation();
      openSlideSorter();
    }
  }, true);

  // Reveal.jsの標準 overview メソッドの差し替え
  function hookRevealOverview() {
    if (typeof Reveal === 'undefined') return;

    if (Reveal.overview) {
      Reveal.overview.toggle = function() { toggleSlideSorter(); };
      Reveal.overview.activate = function() { openSlideSorter(); };
      Reveal.overview.deactivate = function() { closeSlideSorter(); };
      Reveal.overview.isActive = function() { return isSorterOpen; };
    }
    Reveal.toggleOverview = function() { toggleSlideSorter(); };
  }

  if (typeof Reveal !== 'undefined' && Reveal.on) {
    Reveal.on('ready', hookRevealOverview);
  } else {
    document.addEventListener('DOMContentLoaded', hookRevealOverview);
  }

  // グローバル露出
  window.toggleSlideSorter = toggleSlideSorter;
  window.openSlideSorter = openSlideSorter;
  window.closeSlideSorter = closeSlideSorter;
})();

(function() {
  'use strict';

  const slides = document.querySelectorAll('.slide');
  const totalSlides = slides.length;
  const progressBar = document.getElementById('progressBar');
  const navCurrent = document.getElementById('navCurrent');
  const navTotal = document.getElementById('navTotal');
  const btnPrev = document.getElementById('btnPrev');
  const btnNext = document.getElementById('btnNext');

  let currentIndex = 0;
  let chartsInitialized = new Set();

  navTotal.textContent = String(totalSlides).padStart(2, '0');

  function showSlide(idx) {
    if (idx < 0 || idx >= totalSlides) return;
    slides.forEach((s, i) => {
      s.classList.remove('is-active', 'is-prev');
      if (i === idx) s.classList.add('is-active');
      else if (i < idx) s.classList.add('is-prev');
    });
    currentIndex = idx;
    const pct = ((idx + 1) / totalSlides) * 100;
    progressBar.style.width = pct + '%';
    navCurrent.textContent = String(idx + 1).padStart(2, '0');
    btnPrev.disabled = idx === 0;
    btnNext.disabled = idx === totalSlides - 1;

    // Trigger counter animations on entering slide
    animateCountersInSlide(slides[idx]);
    // Init charts on demand
    initChartsInSlide(slides[idx]);
  }

  function animateCounter(el) {
    if (el.dataset.animated === 'true') {
      // re-animate on revisit
    }
    const target = parseFloat(el.dataset.counter);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const duration = 1600;
    const startTime = performance.now();
    el.dataset.animated = 'true';

    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutExpo
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = target * eased;
      let display;
      if (decimals > 0) {
        display = current.toFixed(decimals);
      } else {
        display = Math.floor(current).toLocaleString('it-IT');
      }
      el.textContent = prefix + display + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function animateCountersInSlide(slide) {
    const counters = slide.querySelectorAll('[data-counter]');
    counters.forEach(c => {
      // reset and animate fresh each time
      c.dataset.animated = 'false';
      animateCounter(c);
    });
  }

  function initChartsInSlide(slide) {
    const canvases = slide.querySelectorAll('canvas');
    canvases.forEach(canvas => {
      if (chartsInitialized.has(canvas.id)) return;
      if (typeof window.buildChart === 'function') {
        chartsInitialized.add(canvas.id);
        window.buildChart(canvas);
      }
    });
  }

  // Navigation events
  btnPrev.addEventListener('click', () => showSlide(currentIndex - 1));
  btnNext.addEventListener('click', () => showSlide(currentIndex + 1));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
      e.preventDefault();
      showSlide(currentIndex + 1);
    } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
      e.preventDefault();
      showSlide(currentIndex - 1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      showSlide(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      showSlide(totalSlides - 1);
    } else if (e.key === 'f' || e.key === 'F') {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen?.();
      } else {
        document.exitFullscreen?.();
      }
    }
  });

  // Touch swipe
  let touchStartX = 0;
  let touchEndX = 0;
  document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });
  document.addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    const dx = touchEndX - touchStartX;
    if (Math.abs(dx) > 60) {
      if (dx < 0) showSlide(currentIndex + 1);
      else showSlide(currentIndex - 1);
    }
  }, { passive: true });

  // Accordion handler for holdings rows with data-desc
  document.addEventListener('click', (e) => {
    const row = e.target.closest('.holdings-row[data-desc]');
    if (!row) return;
    e.stopPropagation();
    row.classList.toggle('is-expanded');
    const detail = row.nextElementSibling;
    if (detail && detail.classList.contains('holdings-detail')) {
      detail.classList.toggle('is-open');
    }
  });

  // Initialize first slide (counters + charts)
  setTimeout(() => { showSlide(0); }, 60);

  // Click on slide area to advance (optional)
  // (disabled to avoid conflict with future interactive elements)
})();

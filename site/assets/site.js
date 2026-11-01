(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var BASE = window.BASE || '';
  var today = new Date();
  var iso = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');

  /* ---------- navigation ---------- */
  var menuBtn = $('.menu-toggle');
  var nav = $('#mainnav');
  menuBtn.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', open);
  });
  $$('.sub-toggle').forEach(function (b) {
    b.addEventListener('click', function () {
      var open = b.getAttribute('aria-expanded') !== 'true';
      $$('.sub-toggle').forEach(function (o) { o.setAttribute('aria-expanded', 'false'); });
      b.setAttribute('aria-expanded', open);
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-sub')) $$('.sub-toggle').forEach(function (o) { o.setAttribute('aria-expanded', 'false'); });
  });

  /* ---------- search ---------- */
  var sBtn = $('.search-toggle');
  var sBox = $('#search');
  var q = $('#q');
  var results = $('#results');
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function closeSearch() { sBox.hidden = true; sBtn.setAttribute('aria-expanded', 'false'); }
  sBtn.addEventListener('click', function () {
    var open = sBox.hidden;
    sBox.hidden = !open;
    sBtn.setAttribute('aria-expanded', open);
    if (open) q.focus();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!sBox.hidden) { closeSearch(); sBtn.focus(); }
    $$('.sub-toggle').forEach(function (o) { o.setAttribute('aria-expanded', 'false'); });
  });
  q.addEventListener('input', function () {
    var term = q.value.trim().toLowerCase();
    if (term.length < 2) { results.innerHTML = ''; return; }
    var hits = window.SEARCH.map(function (p) {
      var t = p.t.toLowerCase().indexOf(term);
      var x = p.x.toLowerCase().indexOf(term);
      return { p: p, t: t, x: x, score: (t >= 0 ? 2 : 0) + (x >= 0 ? 1 : 0) };
    }).filter(function (h) { return h.score; }).sort(function (a, b) { return b.score - a.score; }).slice(0, 8);
    if (!hits.length) {
      results.innerHTML = '<li><a href="' + BASE + 'kontakta-oss/index.html"><strong>Inga träffar på “' + esc(q.value) + '”</strong><span>Prova ett annat ord eller kontakta oss.</span></a></li>';
      return;
    }
    results.innerHTML = hits.map(function (h) {
      var start = Math.max(0, h.x - 40);
      var snip = h.x >= 0 ? h.p.x.slice(start, h.x) + '\u0001' + h.p.x.slice(h.x, h.x + term.length) + '\u0002' + h.p.x.slice(h.x + term.length, h.x + 90) : '';
      snip = esc(snip).replace('\u0001', '<mark>').replace('\u0002', '</mark>');
      return '<li><a href="' + BASE + (h.p.u ? h.p.u + '/' : '') + 'index.html"><strong>' + esc(h.p.t) + '</strong><span>' + (start ? '…' : '') + snip + '</span></a></li>';
    }).join('');
  });

  /* ---------- calendar ---------- */
  var nextIdx = window.EVENTS.findIndex(function (e) { return e.e >= iso; });
  $$('.cal-row').forEach(function (row) {
    if (row.dataset.end < iso) row.classList.add('past');
  });
  var firstUpcoming = $$('.cal-row').filter(function (r) { return r.dataset.end >= iso; }).sort(function (a, b) {
    return a.dataset.start < b.dataset.start ? -1 : 1;
  })[0];
  if (firstUpcoming) firstUpcoming.classList.add('now');
  var nextList = $('#next-events');
  if (nextList && nextIdx >= 0) {
    var upcoming = window.EVENTS.filter(function (e) { return e.e >= iso; }).sort(function (a, b) {
      return a.s < b.s ? -1 : a.s > b.s ? 1 : 0;
    }).slice(0, 3);
    nextList.innerHTML = upcoming.map(function (e) {
      return '<li><span class="when">' + esc(e.d) + '</span><span>' + esc(e.t) + '</span></li>';
    }).join('');
  }
  $$('[data-until]').forEach(function (el) { if (el.dataset.until < iso) el.hidden = true; });
  var wd = today.getDay();
  if (wd >= 1 && wd <= 5) {
    var dayRow = $('.menu tr[data-day="' + (wd - 1) + '"]');
    if (dayRow) dayRow.classList.add('today');
  }

  /* ---------- quotes ---------- */
  var qBox = $('[data-quotes]');
  if (qBox) {
    var qs = $$('.quote', qBox);
    var qi = 0;
    $$('[data-q]', qBox).forEach(function (b) {
      b.addEventListener('click', function () {
        qs[qi].classList.remove('on');
        qs[qi].hidden = true;
        qi = (qi + Number(b.dataset.q) + qs.length) % qs.length;
        qs[qi].hidden = false;
        qs[qi].classList.add('on');
        $('#quote-count').textContent = (qi + 1) + ' / ' + qs.length;
      });
    });
  }

  /* ---------- staff filter ---------- */
  var staffQ = $('#staff-q');
  if (staffQ) {
    var people = $$('.person');
    staffQ.addEventListener('input', function () {
      var t = staffQ.value.trim().toLowerCase();
      var any = false;
      people.forEach(function (p) {
        var show = p.dataset.search.indexOf(t) >= 0;
        p.hidden = !show;
        any = any || show;
      });
      $('#staff-empty').hidden = any;
    });
  }

  /* ---------- demo forms ---------- */
  $$('.demo-form').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var s = $('.form-status', f);
      s.hidden = false;
      s.scrollIntoView({ block: 'nearest', behavior: calm ? 'auto' : 'smooth' });
    });
  });

  /* ---------- hill the children run on ---------- */
  function hillY(t) { // 0..1 along the page width, returns 0..100 in hill units from the top
    return 62 - 20 * Math.sin(t * Math.PI * 1.15 + 0.55) - 7 * Math.sin(t * Math.PI * 3.1 + 1.2);
  }
  var hill = $('[data-hill]');
  var runners = [];
  if (hill) {
    var d = 'M0 100';
    for (var i = 0; i <= 80; i++) d += ' L' + (i * 12.5) + ' ' + hillY(i / 80).toFixed(2);
    d += ' L1000 100Z';
    $('[data-hill-path]').setAttribute('d', d);
    runners = $$('[data-runner]').map(function (el, n) {
      return { el: el, t: 0.42 - n * 0.14, v: 0.042 };
    });
  }
  function placeRunners(dt, now) {
    var w = hill.clientWidth;
    var h = hill.clientHeight;
    runners.forEach(function (r) {
      r.t += r.v * dt;
      if (r.t > 1.12) r.t = -0.12;
      var y = hillY(Math.max(0, Math.min(1, r.t)));
      var y2 = hillY(Math.max(0, Math.min(1, r.t + 0.01)));
      var slope = Math.atan2((y2 - y) * h / 100, 0.01 * w) * 180 / Math.PI;
      r.el.style.transform = 'translate3d(' + (r.t * w).toFixed(1) + 'px,' + (y * h / 100 - h + 2).toFixed(1) + 'px,0) rotate(' + slope.toFixed(1) + 'deg)';
    });
  }

  /* ---------- flocks ---------- */
  var flocks = $$('.flock').map(function (box) {
    var isHero = !!box.closest('.hero');
    var birds = $$('.fly', box).map(function (el, n) {
      var cfg = isHero
        ? [[.30, .13, 96, .78], [.20, .20, 76, .66], [.11, .09, 62, .86], [-.05, .27, 54, .7], [.56, .23, 68, .74]][n]
        : [[.62, .16, 72, .74], [.44, .26, 56, .66], [.26, .12, 46, .84], [.08, .3, 40, .7]][n];
      var small = window.innerWidth < 620;
      el.style.setProperty('--w', cfg[2] * (small ? .62 : 1) + 'px');
      el.style.setProperty('--flap', cfg[3] + 's');
      $$('.wing', el).forEach(function (w) { w.style.animationDelay = (-n * .23) + 's'; });
      return { el: el, x: cfg[0], y: cfg[1], w: cfg[2], n: n };
    });
    return { box: box, birds: birds, travel: 0.022 };
  });

  function placeBirds(f, dt, now, lift) {
    var W = f.box.clientWidth;
    var H = f.box.clientHeight;
    f.birds.forEach(function (b) {
      b.x += f.travel * dt * (1 + b.n * .05);
      if (b.x > 1.15) b.x = -0.15;
      var bobY = Math.sin(now / 1100 + b.n * 1.7) * 7;
      var px = b.x * W;
      var sky = window.innerWidth < 620 ? 88 / .27 : H; // phones keep the birds in the sky above the text
      var py = b.y * sky + bobY - lift * (1 + b.n * .12);
      b.el.style.opacity = 1;
      b.el.style.transform = 'translate3d(' + px.toFixed(1) + 'px,' + py.toFixed(1) + 'px,0) rotate(' + (Math.cos(now / 1100 + b.n * 1.7) * -2.5).toFixed(2) + 'deg)';
    });
  }

  /* ---------- scroll: photos, progress bird, header ---------- */
  var parallax = $$('[data-parallax]').map(function (el) {
    return { el: el, img: el.querySelector('img'), k: Number(el.dataset.parallax) };
  }).filter(function (p) { return p.img; });
  var heroImg = $('[data-hero-img]');
  var heroBox = $('.hero, .page-hero');
  var passers = calm ? [] : $$('.sec.band').map(function (sec) {
    var el = document.createElement('div');
    el.className = 'sec-bird';
    el.setAttribute('aria-hidden', 'true');
    el.appendChild($('.scrollbird .bird').cloneNode(true));
    sec.appendChild(el);
    return { sec: sec, el: el };
  });
  var drift = $('[data-drift]');
  var head = $('.site-head');
  var scrollbird = $('.scrollbird');
  var scrollY = window.scrollY;
  var vh = window.innerHeight;

  function updateScroll() {
    var y = window.scrollY;
    scrollY = y;
    document.body.classList.toggle('scrolled', y > 70);
    var max = document.documentElement.scrollHeight - vh;
    scrollbird.style.setProperty('--p', (max > 40 ? Math.min(100, y / max * 100) : 0).toFixed(2) + '%');
    if (calm) return;
    if (heroImg && y < vh * 1.3) heroImg.style.transform = 'translate3d(0,' + (y * .22).toFixed(1) + 'px,0) scale(' + (1 + y * .00009).toFixed(4) + ')';
    parallax.forEach(function (p) {
      var r = p.el.getBoundingClientRect();
      if (r.bottom < -80 || r.top > vh + 80) return;
      var travel = r.height * 0.17; // stays inside the image's 18% overscan
      var progress = Math.max(0, Math.min(1, (r.top + r.height) / (vh + r.height))); // 1 entering at the bottom, 0 leaving at the top
      p.img.style.transform = 'translate3d(0,' + (-travel * (1 - progress)).toFixed(1) + 'px,0)';
    });
    passers.forEach(function (p) {
      var r = p.sec.getBoundingClientRect();
      if (r.bottom < 0 || r.top > vh) return;
      var pr = 1 - r.bottom / (vh + r.height); // crosses the band once while it scrolls past
      p.el.style.transform = 'translate3d(' + ((pr * 1.2 - .1) * r.width).toFixed(1) + 'px,' + (Math.sin(pr * 9) * 5).toFixed(1) + 'px,0)';
    });
    if (drift) {
      var dr = drift.getBoundingClientRect();
      if (dr.bottom > -100 && dr.top < vh + 100) {
        var over = Math.max(0, drift.scrollWidth - drift.parentElement.clientWidth);
        var pr = 1 - (dr.top + dr.height) / (vh + dr.height);
        drift.style.transform = 'translate3d(' + (-over * Math.max(0, Math.min(1, pr))).toFixed(1) + 'px,0,0)';
      }
    }
  }

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { ticking = false; updateScroll(); });
  }, { passive: true });
  window.addEventListener('resize', function () { vh = window.innerHeight; updateScroll(); });
  updateScroll();

  /* gentle arrival for photo frames; everything is visible without JS */
  if (!calm && 'IntersectionObserver' in window) {
    var targets = $$('.teaser, .sec-media, .poster-frame, .poster-inline .frame, .cal-row, .person, .doc-row');
    var seen = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); seen.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    targets.forEach(function (t) {
      var r = t.getBoundingClientRect();
      if (r.top < vh * .92) return;
      t.classList.add('rise');
      if (t.matches('.cal-row, .person, .doc-row')) t.style.transitionDelay = (Array.prototype.indexOf.call(t.parentNode.children, t) % 4) * 60 + 'ms';
      seen.observe(t);
    });
  }

  /* ---------- animation loop, only while something is on screen ---------- */
  if (calm) {
    flocks.forEach(function (f) {
      f.birds.forEach(function (b) {
        b.el.style.opacity = 1;
        b.el.style.transform = 'translate3d(' + ((.25 + b.n * .17) * f.box.clientWidth) + 'px,' + (b.y * f.box.clientHeight) + 'px,0)';
      });
    });
    if (hill) placeRunners(0, 0);
    return;
  }
  var visible = !heroBox;
  if (heroBox && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(heroBox);
  } else visible = true;

  var last = performance.now();
  function frame(now) {
    var dt = Math.min(.05, (now - last) / 1000);
    last = now;
    if (visible && !document.hidden) {
      flocks.forEach(function (f) {
        var r = f.box.getBoundingClientRect();
        if (r.bottom < 0 || r.top > vh) return;
        placeBirds(f, dt, now, scrollY * .25);
      });
      if (hill) placeRunners(dt, now);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

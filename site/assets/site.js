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
  var sScrim = $('.search-scrim');
  var q = $('#q');
  var results = $('#results');
  var sCount = $('#search-count');
  var sQuick = $('#search-quick');
  var sClear = $('.search-clear');
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function norm(s) { return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); } // "sjukanmalan" also finds "sjukanmälan"
  function setSearch(open) {
    sBox.hidden = !open;
    sScrim.hidden = !open;
    sBtn.setAttribute('aria-expanded', open);
    if (open) { q.focus(); q.select(); }
  }
  sBtn.addEventListener('click', function () { setSearch(sBox.hidden); });
  sScrim.addEventListener('click', function () { setSearch(false); });
  sClear.addEventListener('click', function () { q.value = ''; runSearch(); q.focus(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (!sBox.hidden) { setSearch(false); sBtn.focus(); }
      $$('.sub-toggle').forEach(function (o) { o.setAttribute('aria-expanded', 'false'); });
      return;
    }
    var typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) { e.preventDefault(); setSearch(true); return; }
    if (sBox.hidden) return;
    var links = $$('a', results);
    var at = links.indexOf(document.activeElement);
    if (e.key === 'ArrowDown' && links.length) { e.preventDefault(); links[Math.min(at + 1, links.length - 1)].focus(); }
    if (e.key === 'ArrowUp' && at >= 0) { e.preventDefault(); if (at === 0) q.focus(); else links[at - 1].focus(); }
    if (e.key === 'Enter' && document.activeElement === q && links.length) { e.preventDefault(); links[0].click(); }
  });

  /* one flat list: pages, their sections, staff and calendar events */
  var items = null;
  function pageUrl(u, hash) { return BASE + (u ? u + '/' : '') + 'index.html' + (hash ? '#' + hash : ''); }
  function buildItems() {
    items = [];
    function add(kind, title, text, url, crumb) { items.push({ kind: kind, title: title, text: text, url: url, crumb: crumb || '', nt: norm(title), nx: norm(text) }); }
    window.SEARCH.forEach(function (p) {
      add('page', p.t, p.x, pageUrl(p.u));
      (p.s || []).forEach(function (s) { add('page', s.h, s.x, pageUrl(p.u, s.id), p.t); });
    });
    (window.PEOPLE || []).forEach(function (p) {
      add('person', p.n, p.r + (p.m ? ' ' + p.m : ''), pageUrl('om-oss/medarbetare') + '?q=' + encodeURIComponent(p.n));
    });
    var events = window.EVENTS.filter(function (e) { return e.e >= iso; }).concat(window.EVENTS.filter(function (e) { return e.e < iso; }));
    events.forEach(function (e) { add('event', e.t, e.d, pageUrl('kalendarium')); });
  }
  function words(item) {
    if (!item.words) {
      item.words = {};
      (item.nt + ' ' + item.nx).split(/[^a-z0-9]+/).forEach(function (w) { if (w.length > 3) item.words[w] = 1; });
    }
    return Object.keys(item.words);
  }
  function near(a, b, max) { // edit distance within max, for misspellings
    if (Math.abs(a.length - b.length) > max) return false;
    var row = [];
    for (var j = 0; j <= b.length; j++) row[j] = j;
    for (var i = 1; i <= a.length; i++) {
      var prev = row[0], best = row[0] = i;
      for (var k = 1; k <= b.length; k++) {
        var cur = row[k];
        row[k] = Math.min(row[k] + 1, row[k - 1] + 1, prev + (a[i - 1] === b[k - 1] ? 0 : 1));
        prev = cur;
        if (row[k] < best) best = row[k];
      }
      if (best > max) return false;
    }
    return row[b.length] <= max;
  }
  function scoreExact(item, terms) {
    var total = 0;
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i], at = item.nt.indexOf(t), s = 0;
      if (item.nt === t) s = 12;
      else if (at === 0) s = 9;
      else if (at > 0) s = 6;
      else if ((' ' + item.nx).indexOf(' ' + t) >= 0) s = 3; // the start of a word beats the middle of one
      else if (item.nx.indexOf(t) >= 0) s = 1;
      if (!s) return 0;
      total += s;
    }
    return total + (item.crumb ? 0 : .5);
  }
  function fuzzyTerms(item, terms) { // returns the words actually found, so they can be highlighted
    var found = [];
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i], max = t.length >= 7 ? 2 : 1, hit = null;
      if (t.length < 4) { if (item.nt.indexOf(t) < 0 && item.nx.indexOf(t) < 0) return null; found.push(t); continue; }
      var list = words(item);
      for (var w = 0; w < list.length && !hit; w++) if (near(t, list[w], max)) hit = list[w];
      if (!hit) return null;
      found.push(hit);
    }
    return found;
  }
  function mark(text, ntext, terms) {
    var ranges = [];
    terms.forEach(function (t) {
      for (var at = ntext.indexOf(t); at >= 0 && t; at = ntext.indexOf(t, at + t.length)) ranges.push([at, at + t.length]);
    });
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var out = '', pos = 0;
    ranges.forEach(function (r) {
      if (r[0] < pos) return;
      out += esc(text.slice(pos, r[0])) + '<mark>' + esc(text.slice(r[0], r[1])) + '</mark>';
      pos = r[1];
    });
    return out + esc(text.slice(pos));
  }
  function snippet(item, terms) {
    var at = -1;
    terms.forEach(function (t) { var a = item.nx.indexOf(t); if (a >= 0 && (at < 0 || a < at)) at = a; });
    if (at < 0) return esc(item.text.slice(0, 110)) + (item.text.length > 110 ? '…' : '');
    var from = Math.max(0, item.text.lastIndexOf(' ', Math.max(0, at - 42)));
    var to = Math.min(item.text.length, at + 96);
    return (from ? '…' : '') + mark(item.text.slice(from, to), item.nx.slice(from, to), terms) + (to < item.text.length ? '…' : '');
  }
  var GROUPS = [['page', 'Sidor', 7], ['person', 'Medarbetare', 4], ['event', 'Kalendarium', 4]];
  function runSearch() {
    var raw = q.value.trim();
    sClear.hidden = !q.value;
    var terms = norm(raw).split(/\s+/).filter(Boolean);
    sQuick.hidden = raw.length >= 2;
    if (raw.length < 2) { results.innerHTML = ''; sCount.textContent = ''; return; }
    if (!items) buildItems();
    var hits = items.map(function (it) { return { it: it, s: scoreExact(it, terms), terms: terms }; }).filter(function (h) { return h.s; });
    var fuzzy = false;
    if (!hits.length) {
      fuzzy = true;
      items.forEach(function (it) {
        var f = fuzzyTerms(it, terms);
        if (f) hits.push({ it: it, s: it.nt.indexOf(f[0]) >= 0 ? 2 : 1, terms: f });
      });
    }
    hits.sort(function (a, b) { return b.s - a.s; });
    if (!hits.length) {
      sCount.textContent = 'Inga träffar';
      sQuick.hidden = false;
      results.innerHTML = '<li class="no-hit"><strong>Inga träffar på “' + esc(raw) + '”</strong><span>Prova ett annat ord, välj en genväg nedan eller <a href="' + pageUrl('kontakta-oss') + '">kontakta oss</a>.</span></li>';
      return;
    }
    var html = '', shown = 0;
    var best = function (g) { var top = hits.filter(function (h) { return h.it.kind === g[0]; })[0]; return top ? top.s : 0; };
    GROUPS.slice().sort(function (a, b) { return best(b) - best(a); }).forEach(function (g) { // the strongest kind of hit comes first, so Enter opens it
      var list = hits.filter(function (h) { return h.it.kind === g[0]; });
      if (!list.length) return;
      html += '<li class="hit-group"><h3>' + g[1] + ' <span>' + list.length + '</span></h3><ul>';
      list.slice(0, g[2]).forEach(function (h) {
        var it = h.it;
        shown++;
        html += '<li class="hit-' + it.kind + '"><a href="' + it.url + '"><strong>' + (it.crumb ? '<em>' + esc(it.crumb) + ' /</em> ' : '') + mark(it.title, it.nt, h.terms) + '</strong><span>' + (it.kind === 'event' ? esc(it.text) : snippet(it, h.terms)) + '</span></a></li>';
      });
      html += '</ul></li>';
    });
    results.innerHTML = html;
    sCount.textContent = (fuzzy ? 'Inga exakta träffar, visar det närmaste: ' : '') + hits.length + (hits.length === 1 ? ' träff' : ' träffar');
  }
  var searchTimer = 0;
  q.addEventListener('input', function () { clearTimeout(searchTimer); searchTimer = setTimeout(runSearch, 70); });

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
    var preset = new URLSearchParams(location.search).get('q'); // arriving from a search hit
    if (preset) { staffQ.value = preset; staffQ.dispatchEvent(new Event('input')); }
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

  /* ---------- hill and the girls running on it ---------- */
  function hillY(t) { // 0..1 along the page width, returns 0..100 in hill units from the top
    return 62 - 20 * Math.sin(t * Math.PI * 1.15 + 0.55) - 7 * Math.sin(t * Math.PI * 3.1 + 1.2);
  }
  var hill = $('[data-hill]');
  var kids = null;
  if (hill) {
    var d = 'M0 100';
    for (var i = 0; i <= 80; i++) d += ' L' + (i * 12.5) + ' ' + hillY(i / 80).toFixed(2);
    d += ' L1000 100Z';
    $('[data-hill-path]').setAttribute('d', d);
    kids = {
      cv: $('.kids', hill),
      girls: [
        { t: .46, size: 1, phase: 0, hair: 'pony', hairC: '#6b3f22', dress: '#d9736f', hem: '#f3c3b6', sock: '#f6efe4', shoe: '#5b3a28', skin: '#f2c9a8' },
        { t: .33, size: .9, phase: 2.1, hair: 'braids', hairC: '#c79a4b', dress: '#6f7c4d', hem: '#d9dcae', sock: '#e9e2cf', shoe: '#463325', skin: '#f6d6ba' },
        { t: .21, size: .82, phase: 4.2, hair: 'bob', hairC: '#3e2a1b', dress: '#d8a24a', hem: '#f6e2a9', sock: '#f6efe4', shoe: '#7a3f35', skin: '#d9a57f' }
      ]
    };
  }
  function shade(hex, k) { // k<1 darkens the far limbs so the figure has depth
    var n = parseInt(hex.slice(1), 16);
    return 'rgb(' + [n >> 16, n >> 8 & 255, n & 255].map(function (c) { return Math.round(c * k); }).join(',') + ')';
  }
  function limb(c, ax, ay, bx, by, cx, cy, w1, w2, col) {
    c.strokeStyle = col; c.lineCap = 'round'; c.lineJoin = 'round';
    c.lineWidth = w1; c.beginPath(); c.moveTo(ax, ay); c.lineTo(bx, by); c.stroke();
    c.lineWidth = w2; c.beginPath(); c.moveTo(bx, by); c.lineTo(cx, cy); c.stroke();
  }
  function ik(ax, ay, tx, ty, l1, l2, bend) { // two-bone solve, returns the joint between them
    var dx = tx - ax, dy = ty - ay, len = Math.min(Math.hypot(dx, dy), l1 + l2 - .01) || .01;
    var a = (l1 * l1 - l2 * l2 + len * len) / (2 * len), h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
    var ux = dx / Math.hypot(dx, dy || .01), uy = dy / Math.hypot(dx, dy || .01);
    return { x: ax + ux * a - uy * h * bend, y: ay + uy * a + ux * h * bend, ex: ax + ux * (l1 + l2 > len ? len : l1 + l2), ey: ay + uy * len };
  }
  function drawGirl(c, g, W, H, top, dt) {
    var S = (W < 620 ? 56 : 86) * g.size, u = S / 100;
    function ground(x) { return top + hillY(Math.max(0, Math.min(1, x / W))) * H / 100; }
    var x = g.t * W;
    var slope = (ground(x + 8) - ground(x - 8)) / 16; // positive runs downhill
    var stride = 21 * u, speed = S * 1.3 * (1 + slope * .45 + Math.sin(g.phase * .03) * .1);
    if (dt) {
      g.t += speed * dt / W;
      g.phase += speed * dt * Math.PI / (2 * stride);
      if (g.t > 1.08) { g.t = -.08; g.chain = null; }
      x = g.t * W;
    }
    var p = g.phase, lean = .2 + Math.atan(slope) * .5;
    var hipY = ground(x) - (45 + Math.cos(2 * p) * 2.6) * u, hipX = x;
    var shX = hipX + Math.sin(lean) * 27 * u, shY = hipY - Math.cos(lean) * 27 * u;
    var headX = shX + Math.sin(lean) * 11 * u + 1.5 * u, headY = shY - 11 * u + Math.sin(2 * p + .6) * .7 * u;

    /* shadow stays on the ground and tightens as she lifts off */
    c.fillStyle = 'rgba(63,49,0,.2)';
    c.beginPath(); c.ellipse(x, ground(x) + 1.5 * u, (15 - Math.cos(2 * p) * 2) * u, 2.2 * u, Math.atan(slope), 0, 7); c.fill();

    function leg(q, tone) {
      var q2 = (q % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI);
      var swing = q2 > Math.PI, s = Math.sin(q2);
      var fx = hipX + stride * Math.cos(q2) + (swing ? -s * -5 * u : 0);
      var lift = swing ? -s * 15 * u : 0;
      var fy = ground(fx) - 5 * u - lift;
      var knee = ik(hipX, hipY, fx, fy, 24 * u, 22 * u, -1);
      limb(c, hipX, hipY, knee.x, knee.y, fx, fy, 6 * u, 4.6 * u, shade(tone ? g.sock : g.skin, tone ? .82 : 1));
      if (!tone) limb(c, knee.x, knee.y, (knee.x + fx) / 2, (knee.y + fy) / 2, fx, fy, 4.6 * u, 4.8 * u, g.sock);
      var pitch = swing ? .7 * -s : (q2 > 2.2 ? .35 : -.05); // heel rises as the foot leaves the ground
      c.strokeStyle = shade(g.shoe, tone ? .8 : 1); c.lineWidth = 4.6 * u; c.lineCap = 'round';
      c.beginPath(); c.moveTo(fx - 1 * u, fy + 1.5 * u); c.lineTo(fx + Math.cos(pitch) * 6.5 * u, fy + 1.5 * u + Math.sin(pitch) * 6.5 * u); c.stroke();
    }
    function arm(q, far) {
      var a = lean - Math.sin(q) * 1 + .12;
      var ex = shX + Math.sin(a) * 13 * u, ey = shY + Math.cos(a) * 13 * u + 1.5 * u;
      var f = a + 1.55 + Math.sin(q) * .25;
      limb(c, shX, shY + 1.5 * u, ex, ey, ex + Math.sin(f) * 12 * u, ey + Math.cos(f) * 12 * u, 4.2 * u, 3.6 * u, shade(far ? shade(g.dress, 1) && g.skin : g.skin, far ? .84 : 1));
    }
    function hairChain(key, ax, ay, n, seg, w) {
      var ch = g.chain && g.chain[key];
      if (!ch) {
        ch = []; for (var k = 0; k <= n; k++) ch.push({ x: ax - k * seg, y: ay + k * seg * .3, ox: ax - k * seg, oy: ay + k * seg * .3 });
        g.chain = g.chain || {}; g.chain[key] = ch;
      }
      ch[0].x = ax; ch[0].y = ay;
      if (dt) {
        for (var a = 1; a <= n; a++) {
          var pt = ch[a], vx = (pt.x - pt.ox) * .86, vy = (pt.y - pt.oy) * .86;
          pt.ox = pt.x; pt.oy = pt.y; pt.x += vx; pt.y += vy + 900 * u * dt * dt;
        }
        for (var it = 0; it < 3; it++) for (var b = 1; b <= n; b++) {
          var A = ch[b - 1], B = ch[b], dx = B.x - A.x, dy = B.y - A.y, l = Math.hypot(dx, dy) || 1, e = (l - seg) / l;
          B.x -= dx * e; B.y -= dy * e;
        }
      }
      c.strokeStyle = g.hairC; c.lineCap = 'round';
      for (var m = 1; m <= n; m++) {
        c.lineWidth = w * (1 - (m - 1) / (n + 1.5));
        c.beginPath(); c.moveTo(ch[m - 1].x, ch[m - 1].y); c.lineTo(ch[m].x, ch[m].y); c.stroke();
      }
    }

    arm(p + Math.PI, true);
    leg(p + Math.PI, true);
    leg(p, false);

    /* dress: narrow at the shoulders, flares and trails behind her at the hem */
    var hemY = hipY + 15 * u, wave = Math.sin(p * 2) * 1.6 * u, trail = 5 * u + Math.sin(p * 2 + 1) * 1.8 * u;
    var fr = hipX + 10 * u, bk = hipX - 11 * u - trail;
    c.fillStyle = g.dress;
    c.beginPath();
    c.moveTo(shX + 5.5 * u, shY - 1 * u);
    c.quadraticCurveTo(hipX + 6.5 * u, hipY - 12 * u, fr, hemY + wave);
    c.quadraticCurveTo((fr + bk) / 2, hemY + 4 * u - wave, bk, hemY - 2 * u - wave);
    c.quadraticCurveTo(hipX - 7 * u, hipY - 12 * u, shX - 6 * u, shY - 1 * u);
    c.closePath(); c.fill();
    c.strokeStyle = g.hem; c.lineWidth = 2.2 * u; c.lineCap = 'round';
    c.beginPath(); c.moveTo(fr - .5 * u, hemY + wave - 1 * u);
    c.quadraticCurveTo((fr + bk) / 2, hemY + 3 * u - wave, bk + .5 * u, hemY - 3 * u - wave); c.stroke();

    /* hair behind the head moves on its own, a beat after the body */
    if (g.hair === 'pony') hairChain('a', headX - 7 * u, headY - 5 * u, 5, 5 * u, 5 * u);
    if (g.hair === 'braids') { hairChain('a', headX - 7 * u, headY + 2 * u, 5, 4.6 * u, 3.8 * u); hairChain('b', headX - 4 * u, headY + 4 * u, 5, 4.3 * u, 3.4 * u); }
    if (g.hair === 'bob') hairChain('a', headX - 7 * u, headY + 1 * u, 2, 5 * u, 7 * u);

    c.fillStyle = g.skin; c.fillRect(shX - 1.8 * u, shY - 6 * u, 3.6 * u, 7 * u);
    c.beginPath(); c.arc(headX, headY, 10 * u, 0, 7); c.fill();
    c.fillStyle = g.hairC;
    c.beginPath(); c.arc(headX, headY, 10.6 * u, Math.PI * .72, Math.PI * 1.88); c.quadraticCurveTo(headX + 1 * u, headY - 4 * u, headX - 8 * u, headY + 6 * u); c.closePath(); c.fill();
    c.fillStyle = 'rgba(217,100,90,.4)';
    c.beginPath(); c.arc(headX + 5.5 * u, headY + 3 * u, 2.2 * u, 0, 7); c.fill();
    c.fillStyle = '#3a2614';
    c.beginPath(); c.arc(headX + 5 * u, headY - .6 * u, Math.max(.7, 1.1 * u), 0, 7); c.fill();

    arm(p, false);
  }
  function drawKids(dt) {
    var w = hill.clientWidth, h = hill.clientHeight, extra = 110, dpr = Math.min(2, window.devicePixelRatio || 1), cv = kids.cv;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round((h + extra) * dpr)) {
      cv.width = Math.round(w * dpr); cv.height = Math.round((h + extra) * dpr);
      cv.style.height = (h + extra) + 'px';
    }
    var c = cv.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h + extra);
    kids.girls.forEach(function (g) { drawGirl(c, g, w, h, extra, dt); });
  }

  /* ---------- white blossoms hanging in the top right corner ---------- */
  var blossomBox = $('[data-blossoms]');
  var strands = [];
  var gust = 0;
  if (blossomBox) {
    var seed = 7;
    var rnd = function () { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    var flower = function (x, y, r, rot) {
      return '<use href="#bl" transform="translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ') rotate(' + rot.toFixed(0) + ') scale(' + r.toFixed(2) + ')"/>';
    };
    var petals = '';
    for (var pi = 0; pi < 5; pi++) {
      var ang = pi * 72;
      petals += '<g transform="rotate(' + ang + ')"><path d="M0 -1C6 -4 8 -12 3.500 -16.500 1.800 -17.800 -1.800 -17.800 -3.500 -16.500 -8 -12 -6 -4 0 -1z" fill="#3f3100" opacity=".16" transform="translate(.8 1.400)"/><path d="M0 -1C6 -4 8 -12 3.500 -16.500 1.800 -17.800 -1.800 -17.800 -3.500 -16.500 -8 -12 -6 -4 0 -1z" fill="#fffdf9"/><path d="M0 -3C1.500 -7 1 -11 0 -14" fill="none" stroke="#f3cfc8" stroke-width=".8"/></g>';
    }
    var stamens = '<circle r="2.600" fill="#c9cf8d"/>';
    for (var si = 0; si < 7; si++) stamens += '<circle cx="' + (Math.cos(si * .9) * 5.200).toFixed(1) + '" cy="' + (Math.sin(si * .9) * 5.200).toFixed(1) + '" r=".7" fill="#d9b35a"/>';
    var leaf = 'M0 0C5 -5 13 -5 18 0 13 5 5 5 0 0z';
    var svg = '<svg viewBox="0 0 420 300" aria-hidden="true"><defs><g id="bl">' + petals + stamens + '</g></defs>';
    [[96, 42], [158, 74], [216, 58], [268, 112], [318, 186], [364, 132], [404, 226]].forEach(function (st) {
      var sx = st[0], len = st[1], dx = (rnd() - .5) * 18, g = '';
      g += '<path d="M' + sx + ' -8Q' + (sx + dx * 1.6) + ' ' + len * .5 + ' ' + (sx + dx) + ' ' + len + '" fill="none" stroke="#5f6645" stroke-width="1.500" stroke-linecap="round"/>';
      var n = Math.max(2, Math.round(len / 27));
      for (var k = 0; k <= n; k++) {
        var f = k / n, y = 6 + f * (len - 6), x = sx + dx * f * (2 - f) * .9 + (k % 2 ? 10 : -10) * (1 - f * .55);
        if (k % 3 === 1) g += '<path d="' + leaf + '" fill="#79805a" transform="translate(' + (sx + dx * f) + ' ' + y + ') rotate(' + (k % 2 ? 40 : 140) + ') scale(.95)"/>';
        g += flower(x, y, (.92 - f * .56) * (.8 + rnd() * .3), rnd() * 360);
      }
      strands.push({ x: sx, html: g });
    });
    strands.forEach(function (st, n) {
      svg += '<g class="gust" data-x="' + st.x + '"><g class="strand" style="transform-origin:' + st.x + 'px 0;animation-duration:' + (4.200 + (n * 1.3) % 2.700).toFixed(1) + 's;animation-delay:-' + (n * .9).toFixed(1) + 's">' + st.html + '</g></g>';
    });
    svg += '</svg>';
    for (var fp = 0; fp < 3; fp++) svg += '<span class="fall-petal" style="right:' + (4 + fp * 9) + '%;animation-delay:-' + (fp * 5.100).toFixed(1) + 's;animation-duration:' + (12 + fp * 1.700).toFixed(1) + 's"></span>';
    blossomBox.innerHTML = svg;
    strands = $$('.gust', blossomBox);
  }
  function blowBlossoms() {
    if (Math.abs(gust) < .02) return;
    gust *= .93;
    strands.forEach(function (s, n) {
      s.setAttribute('transform', 'rotate(' + (gust * (1 + n % 3 * .3)).toFixed(2) + ' ' + s.dataset.x + ' 0)');
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
    if (strands.length) gust = Math.max(-5, Math.min(5, gust + (y - scrollY) * .04));
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
    if (hill) drawKids(0);
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
      if (hill) drawKids(dt);
      blowBlossoms();
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

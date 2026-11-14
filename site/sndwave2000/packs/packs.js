/* The SNDWAVE2000 Sound Pack Explorer (/sndwave2000/packs/). Data: packs.json (one entry per pack) and data/ID.json
   (its presets), made by tools/sndrec-demo/sndwave_site.py. #ID opens a pack. Art is shown pixel for pixel through
   /sndrec/pxfit.js: the box at full, 1/2 or 1/3 size, whichever is the largest that fits at a whole scale. Previews
   load only when played. */
(function () {
  'use strict';
  var PLAY = document.documentElement.getAttribute('data-play') === 'live';
  if (!PLAY) [].forEach.call(document.querySelectorAll('a.playlink'), function (a) { a.href = '/sndrec.html#b16try'; });
  var grid = document.getElementById('grid'), packEl = document.getElementById('pack'), player = document.getElementById('player');
  var gq = document.getElementById('gq'), results = document.getElementById('results');
  var PACKS = [], BY = {}, DATA = {}, playing = null;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function num(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function load(id) {
    if (!DATA[id]) DATA[id] = fetch('data/' + id + '.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    return DATA[id];
  }
  function px(img) { if (window.pxfit) pxfit.fit(img); }
  // the largest of the box's sizes that fits the column at a whole scale (k >= 1), else the smallest
  function boxSrc(p, availCss) {
    var dpr = window.devicePixelRatio || 1, dev = availCss * dpr, a = p.art;
    var c = [['box.png', a.box], ['half.png', a.half], ['thumb.png', a.thumb]];
    for (var i = 0; i < c.length; i++) if (c[i][1][0] <= dev) return c[i];
    return c[2];
  }
  function img(src, wh, alt) { var i = new Image(wh[0], wh[1]); i.src = src; i.alt = alt || ''; i.setAttribute('data-px', wh[0] + 'x' + wh[1]); return i; }

  // ---- the shelf of packs
  function card(p) {
    var a = el('a', 'card'); a.href = '#' + p.id;
    var box = el('span', 'pxbox pximg'); box.appendChild(img(p.id + '/thumb.png', p.art.thumb, ''));
    a.appendChild(box);
    var cats = Object.keys(p.cats).sort(function (x, y) { return p.cats[y] - p.cats[x]; });
    a.appendChild(el('b', null, esc(p.title)));
    a.appendChild(el('span', 'mk', esc(p.maker.name) + '<br>' + esc(p.label) + ' &middot; ' + esc(p.year)));
    a.appendChild(el('span', 'ct', p.n + ' presets' + (p.fav ? ' &middot; <span class="star" aria-label="favourites">&#9733;</span> ' + p.fav : '') +
      '<br><i>' + esc(cats.slice(0, 5).join(', ')) + (cats.length > 5 ? ' &hellip;' : '') + '</i>'));
    return a;
  }

  // ---- one pack
  function fileLinks(p) {
    var f = p.files, r = '';
    if (f.pdf) r += '<a class="btn def" href="' + p.id + '/' + esc(f.pdf.name) + '" target="_blank" rel="noopener">Manual (PDF' + (f.pdf.pages ? ', ' + f.pdf.pages + ' pages' : '') + ', ' + f.pdf.kb + ' KB)</a>';
    if (f.hlp) r += '<a class="btn" href="' + p.id + '/' + esc(f.hlp.name) + '" download>Help file (' + esc(f.hlp.name) + ', ' + f.hlp.kb + ' KB)</a>';
    if (f.readme) r += '<a class="btn" href="' + p.id + '/' + esc(f.readme.name) + '" target="_blank" rel="noopener">README.TXT</a>';
    return r;
  }
  function openPack(id) {
    var p = BY[id];
    if (!p) { packEl.hidden = true; packEl.innerHTML = ''; stop(); return; }
    stop();
    packEl.hidden = false;
    packEl.innerHTML = '';
    packEl.style.setProperty('--pk', p.accent || 'var(--bk-accent)');
    var head = el('div', 'phead');
    head.innerHTML = '<a class="back" href="#">&larr; All sound packs</a>' +
      '<p class="kicker">' + esc(p.label) + ' &middot; ' + esc(p.year) + ' &middot; ' + esc(p.maker.name) + '</p>' +
      '<h2 class="ptitle">' + (p.art.icon32 ? '<img class="pix" src="' + p.id + '/icon32.png" width="32" height="32" alt="">' : '') + esc(p.title) + '</h2>' +
      (p.subtitle ? '<p class="tagline">' + esc(p.subtitle) + '</p>' : '');
    packEl.appendChild(head);
    var body = el('div', 'pbody'), art = el('div', 'part'), txt = el('div', 'ptext');
    body.appendChild(art); body.appendChild(txt); packEl.appendChild(body);
    var bb = el('div', 'pxbox pximg'); art.appendChild(bb);
    var avail = art.clientWidth || 360, b = boxSrc(p, avail);
    bb.appendChild(img(p.id + '/' + b[0], b[1], 'The ' + p.title + ' box'));
    px(bb.firstChild);
    if (p.art.disc) {
      var db = el('div', 'pxbox pximg disc'); art.appendChild(db);
      db.appendChild(img(p.id + '/disc.png', p.art.disc, 'The ' + p.title + ' disc'));
      px(db.firstChild);
    }
    var t = '';
    if (p.blurb) t += '<p class="blurb">' + esc(p.blurb) + '</p>';
    (p.intro || []).forEach(function (s) { t += '<p>' + esc(s) + '</p>'; });
    t += '<p class="files">' + fileLinks(p) + '</p>';
    if (p.note && p.note.length) t += '<blockquote class="mnote"><p class="kicker">From the maker</p>' + p.note.map(function (s) { return '<p>' + esc(s) + '</p>'; }).join('') + '</blockquote>';
    var m = p.maker;
    t += '<div class="maker"><p class="kicker">The company</p><address>' + (m.contact || [m.name, m.place]).map(esc).join('<br>') + '</address>' +
      (m.kind ? '<p class="note">' + esc(m.kind) + '. ' + esc(m.place) + '.</p>' : '') +
      (m.people && m.people.length ? '<ul class="people">' + m.people.map(function (x) { return '<li><b>' + esc(x[0]) + '</b>, ' + esc(x[1]) + '</li>'; }).join('') + '</ul>' : '') +
      (p.copyright ? '<p class="note">' + esc(p.copyright) + '</p>' : '') + '</div>';
    txt.innerHTML = t;
    // the presets, in a window of their own
    var w = el('div', 'win plist');
    w.innerHTML = '<div class="cap"><span class="box"></span><span class="t">' + esc(p.label) + ' - Presets</span></div><div class="body">' +
      '<div class="chips" role="group" aria-label="Category"></div>' +
      '<div class="find"><label><input type="checkbox" class="favonly"> Favourites only</label><input type="search" class="pq" placeholder="Find in this pack" aria-label="Find in this pack" autocomplete="off"><span class="count" aria-live="polite"></span></div>' +
      '<ul class="rows"><li class="loading">Loading the presets&hellip;</li></ul></div>';
    packEl.appendChild(w);
    load(id).then(function (d) { presets(w, p, d.presets); }, function () { w.querySelector('.rows').innerHTML = '<li class="loading">The presets did not load. Try again later.</li>'; });
  }
  function presets(w, p, all) {
    var chips = w.querySelector('.chips'), rows = w.querySelector('.rows'), count = w.querySelector('.count'), fav = w.querySelector('.favonly'), q = w.querySelector('.pq');
    var cat = 'All', order = Object.keys(p.cats).sort();
    function draw() {
      var s = q.value.trim().toLowerCase();
      var list = all.filter(function (x) {
        return (cat === 'All' || x.c === cat) && (!fav.checked || x.fav) &&
          (!s || (x.n + ' ' + x.c + ' ' + x.d + ' ' + (x.r.one || '')).toLowerCase().indexOf(s) >= 0);
      });
      rows.innerHTML = '';
      var last = null;
      list.forEach(function (x) {
        if (cat === 'All' && x.c !== last) { rows.appendChild(el('li', 'cath', esc(x.c))); last = x.c; }
        rows.appendChild(row(x, p));
      });
      if (!list.length) rows.appendChild(el('li', 'loading', 'No presets match.'));
      count.textContent = list.length + ' of ' + all.length;
    }
    all.sort(function (a, b) { return a.c < b.c ? -1 : a.c > b.c ? 1 : a.n < b.n ? -1 : 1; });
    var opts = [['All', all.length]].concat(order.map(function (c) { return [c, p.cats[c]]; }));
    chips.innerHTML = '';
    opts.forEach(function (o) {
      var b = el('button', 'chip', esc(o[0]) + ' <span>' + o[1] + '</span>'); b.type = 'button'; b.setAttribute('aria-pressed', String(o[0] === cat));
      b.addEventListener('click', function () { cat = o[0]; [].forEach.call(chips.children, function (c) { c.setAttribute('aria-pressed', String(c === b)); }); draw(); });
      chips.appendChild(b);
    });
    fav.addEventListener('change', draw); q.addEventListener('input', draw);
    draw();
  }
  function audioOf(x) {
    if (x.a) return x.a;
    if (x.ogg && player.canPlayType('audio/ogg; codecs="opus"')) return 'audio/' + x.s + '.ogg';
    if (x.mp3) return 'audio/' + x.s + '.mp3';
    return null;
  }
  var ICON_PLAY = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 1.5v11l9-5.5z" fill="currentColor"/></svg>';
  var ICON_STOP = '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2.5" y="2.5" width="9" height="9" fill="currentColor"/></svg>';
  function row(x, p) {
    var li = el('li', 'prow'), src = audioOf(x);
    var b = el('button', 'btn play', ICON_PLAY); b.type = 'button';
    if (src) { b.setAttribute('aria-label', 'Play ' + x.n); b.addEventListener('click', function () { toggle(li, b, src); }); }
    else { b.disabled = true; b.title = 'Preview coming with the 1.3.0 renders'; b.setAttribute('aria-label', 'No preview yet for ' + x.n); }
    li.appendChild(b);
    var m = el('div', 'pm');
    var rec = x.r || {}, lines = rec.kit ? rec.kit.layers.concat(rec.kit.pads, rec.kit.env ? [rec.kit.env] : []) : (rec.lines || []);
    var one = rec.one && rec.one.length <= 96 && !rec.kit;
    m.innerHTML = '<div class="pn"><b>' + esc(x.n) + '</b>' + (x.fav ? ' <span class="star" title="An owner\'s favourite" aria-label="favourite">&#9733;</span>' : '') +
      (x.rt ? ' <span class="rt" title="The owner\'s rating">' + x.rt + '/10</span>' : '') +
      '<span class="pc">' + esc(x.c) + (x.ph ? ' &middot; plays ' + esc(x.ph) : '') + (x.xp ? ' &middot; uses XP sounds' : '') + (x.fl && x.fl.length ? ' &middot; <span class="flag">' + esc(x.fl.join(', ')) + '</span>' : '') + '</span></div>' +
      (one ? '<code class="rone">' + esc(rec.one) + '</code>' : '<pre class="rlines">' + esc(lines.join('\n')) + '</pre>');
    var cp = el('div', 'cp');
    var c1 = el('button', 'btn small', 'Copy DNA'); c1.type = 'button'; c1.addEventListener('click', function () { copy(x.d, c1); });
    var c2 = el('button', 'btn small', 'Copy recipe'); c2.type = 'button'; c2.addEventListener('click', function () { copy(lines.join('\n') || rec.one || '', c2); });
    cp.appendChild(c1); cp.appendChild(c2); m.appendChild(cp);
    li.appendChild(m);
    return li;
  }
  function copy(text, b) {
    var done = function () { var t = b.textContent; b.textContent = 'Copied'; setTimeout(function () { b.textContent = t; }, 1200); };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
    function fallback() { var a = el('textarea'); a.value = text; a.style.position = 'fixed'; a.style.opacity = '0'; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); done(); } catch (e) {} a.remove(); }
  }
  function stop() {
    if (!playing) return;
    player.pause(); playing.li.classList.remove('on'); playing.b.innerHTML = ICON_PLAY; playing = null;
  }
  function toggle(li, b, src) {
    if (playing && playing.li === li) { stop(); return; }
    stop();
    playing = {li: li, b: b};
    li.classList.add('on'); b.innerHTML = ICON_STOP;
    player.src = src; player.currentTime = 0;
    var pr = player.play(); if (pr && pr.catch) pr.catch(function () { stop(); });
  }
  player.addEventListener('ended', stop);
  player.addEventListener('error', function () { if (playing) { playing.b.disabled = true; playing.b.title = 'The preview did not load'; stop(); } });

  // ---- find in every pack (loads the packs' data the first time)
  var allLoaded = null, gt = 0;
  function gfind() {
    var s = gq.value.trim().toLowerCase();
    if (s.length < 2) { results.hidden = true; results.innerHTML = ''; return; }
    if (!allLoaded) allLoaded = Promise.all(PACKS.map(function (p) { return load(p.id).then(function (d) { return [p, d.presets]; }); }));
    allLoaded.then(function (all) {
      if (gq.value.trim().toLowerCase() !== s) return;
      var hits = [];
      all.forEach(function (pd) { pd[1].forEach(function (x) { if ((x.n + ' ' + x.c + ' ' + x.d + ' ' + (x.r.one || '')).toLowerCase().indexOf(s) >= 0) hits.push([pd[0], x]); }); });
      results.hidden = false;
      results.innerHTML = '<p class="note">' + hits.length + ' preset' + (hits.length === 1 ? '' : 's') + (hits.length > 60 ? ', the first 60 shown' : '') + '</p>';
      var ul = el('ul', 'rows');
      hits.slice(0, 60).forEach(function (h) { var li = row(h[1], h[0]); li.querySelector('.pc').insertAdjacentHTML('afterbegin', '<a href="#' + h[0].id + '">' + esc(h[0].title) + '</a> &middot; '); ul.appendChild(li); });
      results.appendChild(ul);
    });
  }
  gq.addEventListener('input', function () { clearTimeout(gt); gt = setTimeout(gfind, 180); });

  function route(scroll) {
    var id = location.hash.slice(1);
    openPack(id);
    if (scroll && BY[id]) packEl.scrollIntoView({block: 'start'});
  }
  fetch('packs.json').then(function (r) { return r.json(); }).then(function (d) {
    PACKS = d.packs;
    PACKS.forEach(function (p) { BY[p.id] = p; grid.appendChild(card(p)); });
    [].forEach.call(grid.querySelectorAll('[data-px]'), px);
    document.getElementById('status').textContent = PACKS.length + ' packs, ' + num(d.total) + ' presets. ' +
      (d.previews ? 'Every preview was rendered by the real Windows 3.11 machine.' : 'The previews for 1.3.0 are being rendered on the release build; until then the owner\'s top picks play the demos already made.');
    route(!!location.hash);
    document.querySelector('main').classList.remove('wait');
    window.addEventListener('hashchange', function () { route(true); });
  }, function () { grid.innerHTML = '<p>The sound packs did not load. Try again later.</p>'; document.querySelector('main').classList.remove('wait'); });
})();

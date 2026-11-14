/* The SNDWAVE2000 Sound Pack Explorer (/sndwave2000/packs/): a Windows 3.1 media player for every preset, the open
   pack's box, manual and maker below it, and the shelf of packs. Data: packs.json and data/ID.json, made by
   tools/sndrec-demo/sndwave_site.py. #ID or #ID/SLUG opens a pack (and a preset).

   The player plays one preview at a time (loaded only when played; the next one is prefetched) and goes on to the next
   preset with a preview at the end of each, into the next pack after the last. Each preset's picture is a detail of
   its pack's printed art (front, back or disc label, at the art's own pixel size, never scaled), chosen by a hash of
   the preset's slug, dithered to 16 colours (Floyd-Steinberg, its own palette by median cut) with the category's
   glyph in the corner; it and the Sound Recorder wave view are shown on whole device pixels through /sndrec/pxfit.js. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var audio = $('player'), listEl = $('mp-list'), packSel = $('mp-pack'), q = $('mp-q'), favCb = $('mp-fav'), shufCb = $('mp-shuf');
  var playBtn = $('mp-play'), seek = $('mp-seek'), tEl = $('mp-time'), lenEl = $('mp-len'), statusEl = $('mp-status'), countEl = $('mp-count');
  var artC = $('mp-art'), scopeC = $('mp-scope'), packEl = $('pack'), grid = $('grid');
  var PACKS = [], BY = {}, DATA = {}, ORDER = [];   // ORDER: pack ids in the combo's (alphabetical) order
  var cur = {pack: null, items: [], sel: -1}, playingX = null, playingPack = null, hist = [], wantPlay = false;
  var ALL = '*all';

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function num(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function load(id) {
    if (!DATA[id]) DATA[id] = fetch('data/' + id + '.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { d.presets.forEach(function (x) { x.pk = id; }); d.presets.sort(byCat); return d.presets; });
    return DATA[id];
  }
  function byCat(a, b) { return a.c < b.c ? -1 : a.c > b.c ? 1 : a.n < b.n ? -1 : a.n > b.n ? 1 : 0; }
  function audioOf(x) {
    if (x.a) return x.a;
    if (x.ogg && audio.canPlayType('audio/ogg; codecs="opus"')) return 'audio/' + x.s + '.ogg';
    if (x.mp3) return 'audio/' + x.s + '.mp3';
    return null;
  }
  function recipeLines(x) {
    var r = x.r || {};
    return r.kit ? r.kit.layers.concat(r.kit.pads, r.kit.env ? [r.kit.env] : []) : (r.lines && r.lines.length ? r.lines : [r.one || '']);
  }
  function fmt(t) {
    if (!isFinite(t) || t < 0) t = 0;
    var m = Math.floor(t / 60), s = t - m * 60;
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s.toFixed(1);
  }
  function copy(text, b) {
    var done = function () { var t = b.textContent; b.textContent = 'Copied'; setTimeout(function () { b.textContent = t; }, 1200); };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
    function fallback() { var a = el('textarea'); a.value = text; a.style.position = 'fixed'; a.style.opacity = '0'; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); done(); } catch (e) {} a.remove(); }
  }

  // ---------------------------------------------------------------- the preset's picture
  var srcCache = {};
  function srcPixels(pid, k) {   // the whole art image, as pixels (same origin)
    var key = pid + '/' + k;
    if (!srcCache[key]) srcCache[key] = new Promise(function (ok, no) {
      var im = new Image(); im.onload = function () {
        var c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
        var x = c.getContext('2d'); x.fillStyle = '#f6f3ea'; x.fillRect(0, 0, c.width, c.height); x.drawImage(im, 0, 0);
        ok({w: c.width, h: c.height, d: x.getImageData(0, 0, c.width, c.height).data});
      }; im.onerror = no; im.src = pid + '/' + k + '.png';
    });
    return srcCache[key];
  }
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function rng(seed) { return function () { seed = (seed + 0x6D2B79F5) | 0; var t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  var AW = 240, AH = 180;
  function crop(S, r) {   // the most detailed of six seeded 240 x 180 windows
    var best = null, bs = -1;
    for (var i = 0; i < 6; i++) {
      var x0 = Math.floor(r() * Math.max(1, S.w - AW)), y0 = Math.floor(r() * Math.max(1, S.h - AH)), e = 0;
      for (var y = y0 + 2; y < y0 + AH - 2; y += 6) for (var x = x0 + 2; x < x0 + AW - 2; x += 6) {
        var o = (y * S.w + x) * 4, o2 = o + 12;
        e += Math.abs(S.d[o] - S.d[o2]) + Math.abs(S.d[o + 1] - S.d[o2 + 1]) + Math.abs(S.d[o + 2] - S.d[o2 + 2]);
      }
      if (e > bs) { bs = e; best = [x0, y0]; }
    }
    return best;
  }
  function palette(px, n) {   // median cut
    var boxes = [px];
    while (boxes.length < n) {
      var bi = -1, bw = -1, ch = 0;
      boxes.forEach(function (b, i) {
        if (b.length < 2) return;
        for (var c = 0; c < 3; c++) { var lo = 255, hi = 0; for (var j = 0; j < b.length; j++) { var v = b[j][c]; if (v < lo) lo = v; if (v > hi) hi = v; } if (hi - lo > bw) { bw = hi - lo; bi = i; ch = c; } }
      });
      if (bi < 0 || bw <= 0) break;
      var b = boxes[bi].sort(function (p, q) { return p[ch] - q[ch]; }), m = b.length >> 1;
      boxes.splice(bi, 1, b.slice(0, m), b.slice(m));
    }
    return boxes.map(function (b) { var s = [0, 0, 0]; b.forEach(function (p) { s[0] += p[0]; s[1] += p[1]; s[2] += p[2]; }); return s.map(function (v) { return Math.round(v / b.length); }); });
  }
  // 12 x 12 category glyphs ('#' ink)
  var GLYPH = {
    note: ['....####....', '....#..##...', '....#...##..', '....#....#..', '....#.......', '....#.......', '....#.......', '.####.......', '#####.......', '#####.......', '.###........', '............'],
    keys: ['############', '#.#.##.#.#.#', '#.#.##.#.#.#', '#.#.##.#.#.#', '#.#.##.#.#.#', '#.#.##.#.#.#', '#..#..#..#.#', '#..#..#..#.#', '#..#..#..#.#', '#..#..#..#.#', '############', '............'],
    drum: ['..########..', '.#........#.', '#..........#', '.#........#.', '#.########.#', '#.#..#..#..#', '#..#.#.#...#', '#...#.#....#', '#..#.#.#...#', '.#........#.', '..########..', '............'],
    bell: ['.....##.....', '....####....', '...######...', '...######...', '..########..', '..########..', '..########..', '.##########.', '############', '.....##.....', '.....##.....', '............'],
    wave: ['............', '............', '..##........', '.#..#.......', '#....#....#.', '......#..#..', '.......##...', '............', '############', '............', '............', '............'],
    bolt: ['......###...', '.....###....', '....###.....', '...###......', '..#######...', '.....###....', '....###.....', '...###......', '..##........', '.#..........', '............', '............'],
    voice: ['...######...', '..#......#..', '.#..#..#..#.', '.#........#.', '.#..####..#.', '..#......#..', '...######...', '.....##.....', '...######...', '..#......#..', '............', '............'],
    bass: ['..##........', '.#..#.......', '....#..#....', '....#.......', '...#...#....', '..#.........', '.#..........', '#...........', '............', '############', '............', '............']};
  function glyphFor(c) {
    c = (c || '').toLowerCase();
    if (/bass|sub/.test(c)) return GLYPH.bass;
    if (/key|piano|organ/.test(c)) return GLYPH.keys;
    if (/perc|kit|drum|beat|break|machine|electromech/.test(c)) return GLYPH.drum;
    if (/bell|mallet|chime/.test(c)) return GLYPH.bell;
    if (/pad|texture|drone|ambient|string/.test(c)) return GLYPH.wave;
    if (/fx|stab|noise|collage/.test(c)) return GLYPH.bolt;
    if (/vocal|choir|voice/.test(c)) return GLYPH.voice;
    return GLYPH.note;
  }
  var artNative = document.createElement('canvas'); artNative.width = AW; artNative.height = AH;
  var artToken = 0;
  function drawArt(x) {
    var p = BY[x.pk], tok = ++artToken, keys = ['front', 'back', 'disc'].filter(function (k) { return p.art[k]; });
    if (!keys.length) keys = ['box'];
    var r = rng(hash(x.s)), k = keys[Math.floor(r() * keys.length)];
    artC.setAttribute('aria-label', x.n + ': a detail of the ' + p.title + ' ' + (k === 'disc' ? 'disc label' : k + ' of the box') + ', dithered to 16 colours');
    srcPixels(p.id, k).then(function (S) {
      if (tok !== artToken) return;
      var o = crop(S, r), w = Math.min(AW, S.w), h = Math.min(AH, S.h);
      var ctx = artNative.getContext('2d'), id = ctx.createImageData(AW, AH), d = id.data, px = [];
      var f = new Float32Array(AW * AH * 3);
      for (var y = 0; y < AH; y++) for (var xx = 0; xx < AW; xx++) {
        var sx = o[0] + (xx % w), sy = o[1] + (y % h), so = (sy * S.w + sx) * 4, i = (y * AW + xx) * 3;
        f[i] = S.d[so]; f[i + 1] = S.d[so + 1]; f[i + 2] = S.d[so + 2];
        if (((y * AW + xx) & 3) === 0) px.push([S.d[so], S.d[so + 1], S.d[so + 2]]);
      }
      var pal = palette(px, 16);
      for (y = 0; y < AH; y++) for (xx = 0; xx < AW; xx++) {   // Floyd-Steinberg
        i = (y * AW + xx) * 3;
        var R = f[i], G = f[i + 1], B = f[i + 2], bj = 0, bd = 1e9;
        for (var j = 0; j < pal.length; j++) { var dr = R - pal[j][0], dg = G - pal[j][1], db = B - pal[j][2], dd = dr * dr * 3 + dg * dg * 4 + db * db * 2; if (dd < bd) { bd = dd; bj = j; } }
        var c = pal[bj], er = [R - c[0], G - c[1], B - c[2]], o4 = (y * AW + xx) * 4;
        d[o4] = c[0]; d[o4 + 1] = c[1]; d[o4 + 2] = c[2]; d[o4 + 3] = 255;
        for (var ch = 0; ch < 3; ch++) {
          if (xx + 1 < AW) f[i + 3 + ch] += er[ch] * 7 / 16;
          if (y + 1 < AH) {
            if (xx > 0) f[i + AW * 3 - 3 + ch] += er[ch] * 3 / 16;
            f[i + AW * 3 + ch] += er[ch] * 5 / 16;
            if (xx + 1 < AW) f[i + AW * 3 + 3 + ch] += er[ch] / 16;
          }
        }
      }
      ctx.putImageData(id, 0, 0);
      // the category glyph on a raised grey tile, bottom left
      var G2 = glyphFor(x.c), gx = 4, gy = AH - 22;
      ctx.fillStyle = '#000'; ctx.fillRect(gx, gy, 18, 18);
      ctx.fillStyle = '#c0c0c0'; ctx.fillRect(gx + 1, gy + 1, 16, 16);
      ctx.fillStyle = '#fff'; ctx.fillRect(gx + 1, gy + 1, 15, 1); ctx.fillRect(gx + 1, gy + 1, 1, 15);
      ctx.fillStyle = '#808080'; ctx.fillRect(gx + 2, gy + 16, 15, 1); ctx.fillRect(gx + 16, gy + 2, 1, 15);
      ctx.fillStyle = '#000';
      for (y = 0; y < 12; y++) for (xx = 0; xx < 12; xx++) if (G2[y][xx] === '#') ctx.fillRect(gx + 3 + xx, gy + 3 + y, 1, 1);
      if (x.fav) {   // a favourite: a small star tile, bottom right
        var sx2 = AW - 22;
        ctx.fillStyle = '#000'; ctx.fillRect(sx2, gy, 18, 18); ctx.fillStyle = '#8a1c1c'; ctx.fillRect(sx2 + 1, gy + 1, 16, 16);
        var ST = ['.....##.....', '.....##.....', '....####....', '############', '.##########.', '..########..', '...######...', '...##..##...', '..##....##..', '.##......##.'];
        ctx.fillStyle = '#f6f3ea';
        for (y = 0; y < ST.length; y++) for (xx = 0; xx < 12; xx++) if (ST[y][xx] === '#') ctx.fillRect(sx2 + 3 + xx, gy + 4 + y, 1, 1);
      }
      window.pxfit && pxfit.draw(artC);
    }, function () {});
  }

  // ---------------------------------------------------------------- the Sound Recorder wave view
  var sctx = scopeC._n = document.createElement('canvas'); sctx.width = 96; sctx.height = 32;
  var actx = null, analyser = null, abuf = null;
  function scopeInit() {
    if (actx || !(window.AudioContext || window.webkitAudioContext)) return;
    try {
      actx = new (window.AudioContext || window.webkitAudioContext)();
      var srcN = actx.createMediaElementSource(audio); analyser = actx.createAnalyser(); analyser.fftSize = 512;
      srcN.connect(analyser); analyser.connect(actx.destination); abuf = new Uint8Array(analyser.fftSize);
    } catch (e) { actx = null; analyser = null; }
  }
  function scopeDraw() {
    var c = sctx.getContext('2d');
    c.fillStyle = '#000'; c.fillRect(0, 0, 96, 32);
    c.fillStyle = '#008000'; c.fillRect(0, 16, 96, 1);
    if (analyser && !audio.paused) {
      analyser.getByteTimeDomainData(abuf);
      c.fillStyle = '#00ff00';
      for (var x = 0; x < 96; x++) {
        var lo = 255, hi = 0;
        for (var j = Math.floor(x * abuf.length / 96); j < Math.floor((x + 1) * abuf.length / 96); j++) { if (abuf[j] < lo) lo = abuf[j]; if (abuf[j] > hi) hi = abuf[j]; }
        var a = Math.round(16 + (lo - 128) / 128 * 15), b = Math.round(16 + (hi - 128) / 128 * 15);
        c.fillRect(x, Math.min(a, b, 16), 1, Math.max(1, Math.abs(Math.max(b, 16) - Math.min(a, 16)) + 1));
      }
    }
    window.pxfit && pxfit.draw(scopeC);
  }

  // ---------------------------------------------------------------- the list
  function visible(x) {
    var s = q.value.trim().toLowerCase();
    return (!favCb.checked || x.fav) && (!s || (x.n + ' ' + x.c + ' ' + x.d + ' ' + ((x.r && x.r.one) || '') + ' ' + (cur.pack === ALL ? BY[x.pk].title : '')).toLowerCase().indexOf(s) >= 0);
  }
  function renderList() {
    listEl.innerHTML = '';
    cur.items = cur.all.filter(visible);
    var last = null, frag = document.createDocumentFragment(), nPlay = 0;
    cur.items.forEach(function (x, i) {
      var head = cur.pack === ALL ? BY[x.pk].title : x.c;
      if (head !== last) { frag.appendChild(el('div', 'mp-cat', esc(head))); last = head; }
      var ok = !!audioOf(x); if (ok) nPlay++;
      var it = el('div', 'mp-it' + (ok ? '' : ' na') + (x === playingX ? ' on' : ''),
        '<span class="pl" aria-hidden="true"></span><span class="nm">' + esc(x.n) + '</span>' + (x.fav ? '<span class="st" aria-label="favourite">&#9733;</span>' : '') +
        (x.rt ? '<span class="rt">' + x.rt + '</span>' : '') + (ok ? '' : '<span class="soon">preview coming</span>'));
      it.id = 'mp-i' + i; it.setAttribute('role', 'option'); it.setAttribute('aria-selected', 'false'); it.dataset.i = i;
      frag.appendChild(it);
    });
    listEl.appendChild(frag);
    if (!cur.items.length) listEl.appendChild(el('div', 'mp-cat', 'No presets match.'));
    countEl.textContent = cur.items.length + ' presets, ' + nPlay + ' with previews';
    var i = playingX ? cur.items.indexOf(playingX) : -1;
    if (i < 0) for (var j = 0; j < cur.items.length; j++) if (audioOf(cur.items[j])) { i = j; break; }   // else the first with a preview
    select(i >= 0 ? i : (cur.items.length ? 0 : -1), false);
  }
  function select(i, show) {
    var old = listEl.querySelector('.mp-it[aria-selected="true"]'); if (old) old.setAttribute('aria-selected', 'false');
    cur.sel = i;
    if (i < 0) { listEl.removeAttribute('aria-activedescendant'); return; }
    var it = $('mp-i' + i); it.setAttribute('aria-selected', 'true'); listEl.setAttribute('aria-activedescendant', it.id);
    var top = it.offsetTop - listEl.offsetTop, lh = listEl.clientHeight;
    if (top < listEl.scrollTop + 18) listEl.scrollTop = Math.max(0, top - 18); else if (top + it.offsetHeight > listEl.scrollTop + lh) listEl.scrollTop = top + it.offsetHeight - lh;
    if (show !== false && (!playingX || audio.paused)) nowShow(cur.items[i]);
  }
  listEl.addEventListener('click', function (e) {
    var it = e.target.closest('.mp-it'); if (!it) return;
    var i = +it.dataset.i; select(i, false); var x = cur.items[i];
    if (audioOf(x)) play(x, true); else { nowShow(x); status('Preview coming for ' + x.n + ': it is being rendered on the release build.'); }
  });

  // ---------------------------------------------------------------- now playing
  var shown = null;
  function nowShow(x) {
    if (!x) return;
    shown = x;
    var p = BY[x.pk], f = p.files;
    $('mp-now').innerHTML = '<b class="nm">' + esc(x.n) + (x.fav ? ' <span class="st" title="An owner\'s favourite">&#9733;</span>' : '') + (x.rt ? ' <span class="rt" title="The owner\'s rating">' + x.rt + '/10</span>' : '') + '</b>' +
      '<span>' + esc(x.c) + (x.ph ? ', plays ' + esc(x.ph) : '') + '</span>' +
      '<span><a href="#' + p.id + '" class="pk">' + esc(p.title) + '</a></span><span class="mk">' + esc(p.maker.name) + '</span>';
    $('mp-recipe').textContent = recipeLines(x).join('\n');
    $('mp-links').innerHTML = (f.pdf ? '<a href="' + p.id + '/' + esc(f.pdf.name) + '" target="_blank" rel="noopener">Manual</a>' : '') +
      (f.hlp ? '<a href="' + p.id + '/' + esc(f.hlp.name) + '" download>Help</a>' : '') + (f.iso ? '<a href="' + p.id + '/' + esc(f.iso.name) + '" download>Disc image</a>' : '') + '<a href="#pack" class="about">About this pack</a>';
    $('mp-title').textContent = 'SNDWAVE2000 Media Player - ' + x.n.toUpperCase();
    drawArt(x);
    if (!audioOf(x)) { tEl.textContent = '--:--.-'; lenEl.textContent = 'preview coming'; }
    else if (x !== playingX) { tEl.textContent = fmt(0); lenEl.textContent = fmt(x.sec || 0); }
  }
  $('mp-cdna').addEventListener('click', function () { if (shown) copy(shown.d, this); });
  $('mp-crec').addEventListener('click', function () { if (shown) copy(recipeLines(shown).join('\n'), this); });
  function status(t) { statusEl.textContent = t; }
  function setHash(h) { try { window.history.replaceState(null, '', '#' + h); } catch (e) {} }

  // ---------------------------------------------------------------- playing
  function setPlayingUi(on) {
    playBtn.classList.toggle('on', on); playBtn.setAttribute('aria-label', on ? 'Pause' : 'Play');
    [].forEach.call(listEl.querySelectorAll('.mp-it.on'), function (e) { e.classList.remove('on'); });
    var i = playingX ? cur.items.indexOf(playingX) : -1; if (i >= 0) $('mp-i' + i).classList.add('on');
  }
  function play(x, user) {
    var url = audioOf(x); if (!url) return;
    scopeInit(); if (actx && actx.state === 'suspended') actx.resume();
    if (playingX && playingX !== x) hist.push(playingX);
    playingX = x; playingPack = x.pk; wantPlay = true;
    nowShow(x);
    audio.src = url; audio.currentTime = 0;
    var pr = audio.play(); if (pr && pr.catch) pr.catch(function () { wantPlay = false; setPlayingUi(false); status('Press Play to start.'); });
    setPlayingUi(true);
    status('Playing ' + x.n + ' (' + BY[x.pk].title + ')');
    setHash(x.pk + '/' + x.s);
    nextOf(x).then(function (n) { if (n) { var u = audioOf(n); if (u) fetch(u).catch(function () {}); } });   // prefetch the next
    if (!raf) raf = requestAnimationFrame(tick);
  }
  function stop() { audio.pause(); try { audio.currentTime = 0; } catch (e) {} wantPlay = false; setPlayingUi(false); tick(); status('Stopped.'); }
  // the next preset with a preview: on in this list, then on into the following packs (or, shuffled, any pack)
  function playable(arr) { return arr.filter(function (x) { return audioOf(x) && (!favCb.checked || x.fav); }); }
  function nextOf(x) {
    if (shufCb.checked) return Promise.all(ORDER.map(load)).then(function (all) {
      var pool = playable([].concat.apply([], all)).filter(function (y) { return y !== x; });
      return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
    });
    var i0 = ORDER.indexOf(x.pk);
    return load(x.pk).then(function (arr) {
      var own = playable(arr), k = own.indexOf(x);
      if (k >= 0 && k + 1 < own.length) return own[k + 1];
      var step = function (n) {
        if (n > ORDER.length) return null;
        return load(ORDER[(i0 + n) % ORDER.length]).then(function (a) { var pl = playable(a); return pl.length ? pl[0] : step(n + 1); });
      };
      return step(1);
    });
  }
  function prevOf(x) {
    if (hist.length) return Promise.resolve(hist.pop());
    var i0 = ORDER.indexOf(x.pk);
    return load(x.pk).then(function (arr) {
      var own = playable(arr), k = own.indexOf(x);
      if (k > 0) return own[k - 1];
      var step = function (n) {
        if (n > ORDER.length) return null;
        return load(ORDER[(i0 - n + ORDER.length * 2) % ORDER.length]).then(function (a) { var pl = playable(a); return pl.length ? pl[pl.length - 1] : step(n + 1); });
      };
      return step(1);
    });
  }
  function goto(x) {   // show x's pack in the list (if it is not the one shown) and play it
    if (!x) return;
    if (cur.pack !== ALL && cur.pack !== x.pk) { packSel.value = x.pk; openPack(x.pk).then(function () { play(x); }); }
    else { play(x); var i = cur.items.indexOf(x); if (i >= 0) select(i, false); }
  }
  function forward() {
    var base = playingX || cur.items[cur.sel]; if (!base) return;
    var h = hist.length; nextOf(base).then(function (n) { if (n) { goto(n); if (hist.length > h + 1) hist.length = h + 1; } });
  }
  function back() {
    if (playingX && audio.currentTime > 3) { audio.currentTime = 0; return; }
    var base = playingX || cur.items[cur.sel]; if (!base) return;
    prevOf(base).then(function (p) { if (p) { goto(p); hist.pop(); } });
  }
  function toggle() {
    if (playingX && audio.src && !audio.ended && audio.paused && audio.currentTime > 0) { scopeInit(); if (actx && actx.state === 'suspended') actx.resume(); audio.play(); wantPlay = true; setPlayingUi(true); status('Playing ' + playingX.n); if (!raf) raf = requestAnimationFrame(tick); return; }
    if (!audio.paused) { audio.pause(); wantPlay = false; setPlayingUi(false); status('Paused.'); return; }
    var x = cur.items[cur.sel];
    if (x && audioOf(x)) play(x, true);
    else if (x) nextOf(x).then(function (n) { if (n) goto(n); });
  }
  playBtn.addEventListener('click', toggle);
  $('mp-stop').addEventListener('click', stop);
  $('mp-next').addEventListener('click', forward);
  $('mp-prev').addEventListener('click', back);
  audio.addEventListener('ended', function () { setPlayingUi(false); if (wantPlay) forward(); });
  audio.addEventListener('error', function () {
    if (!playingX) return;
    status('The preview for ' + playingX.n + ' did not load.');
    if (wantPlay) setTimeout(forward, 600);
  });
  var seeking = false;
  seek.addEventListener('input', function () { seeking = true; if (isFinite(audio.duration)) { audio.currentTime = seek.value * audio.duration; tick(); } });
  seek.addEventListener('change', function () { seeking = false; });
  var raf = 0;
  function tick() {
    raf = 0;
    var d = audio.duration;
    if (playingX && shown === playingX) { tEl.textContent = fmt(audio.currentTime); lenEl.textContent = fmt(isFinite(d) ? d : (playingX.sec || 0)); }
    if (!seeking) seek.value = isFinite(d) && d > 0 ? audio.currentTime / d : 0;
    scopeDraw();
    if (!audio.paused) raf = requestAnimationFrame(tick);
  }
  // keys: Space play / pause, Up / Down the list, Left / Right back / forward
  document.addEventListener('keydown', function (e) {
    var t = e.target, tag = t && t.tagName;
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (tag === 'INPUT' && t.type !== 'checkbox' || tag === 'SELECT' || tag === 'TEXTAREA' || t.isContentEditable) return;
    if ((tag === 'A' || tag === 'BUTTON') && (e.key === ' ' || e.key === 'Enter')) return;   // the control's own action
    var mpTop = $('mp').getBoundingClientRect();
    if (mpTop.bottom < 0 || mpTop.top > window.innerHeight) return;   // only while the player is on screen
    if (e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); toggle(); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      var i = Math.max(0, Math.min(cur.items.length - 1, cur.sel + (e.key === 'ArrowDown' ? 1 : -1)));
      select(i, true);
      var x = cur.items[i]; if (x && !audio.paused && audioOf(x)) play(x, true);
    }
    else if (e.key === 'ArrowRight') { e.preventDefault(); forward(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); back(); }
    else if (e.key === 'Enter' && t === listEl) { var y = cur.items[cur.sel]; if (y && audioOf(y)) play(y, true); }
  });
  q.addEventListener('input', renderList);
  favCb.addEventListener('change', renderList);
  shufCb.addEventListener('change', function () { hist = []; status(shufCb.checked ? 'Shuffle: the next preview comes from any pack.' : 'In order: the next preview follows the list, then the next pack.'); });

  // ---------------------------------------------------------------- packs
  function openPack(id) {
    cur.pack = id;
    var pr = id === ALL ? Promise.all(ORDER.map(load)).then(function (a) { return [].concat.apply([], a); }) : load(id);
    q.setAttribute('aria-label', id === ALL ? 'Find a preset in every pack' : 'Find a preset in this pack');
    if (id !== ALL) about(id);
    return pr.then(function (arr) { if (cur.pack !== id) return; cur.all = arr; renderList(); if (!playingX || audio.paused) nowShow(cur.items[cur.sel]); },
      function () { listEl.innerHTML = '<div class="mp-cat">The presets did not load. Try again later.</div>'; });
  }
  packSel.addEventListener('change', function () { hist = []; openPack(packSel.value); if (packSel.value !== ALL) setHash(packSel.value); });

  // the open pack, below the player: its art at native size, its story, its maker and its files
  function about(id) {
    var p = BY[id];
    packEl.hidden = false; packEl.innerHTML = '';
    packEl.style.setProperty('--pk', p.accent || 'var(--bk-accent)');
    var head = el('div', 'phead');
    head.innerHTML = '<p class="kicker">' + esc(p.label) + ' &middot; ' + esc(p.year) + ' &middot; ' + esc(p.maker.name) + '</p>' +
      '<h2 class="ptitle">' + (p.art.icon32 ? '<img class="pix" src="' + p.id + '/icon32.png" width="32" height="32" alt="">' : '') + esc(p.title) + '</h2>' +
      (p.subtitle ? '<p class="tagline">' + esc(p.subtitle) + '</p>' : '');
    packEl.appendChild(head);
    var VIEWS = [['box', 'Box'], ['front', 'Front'], ['back', 'Back'], ['spine', 'Spine'], ['disc3d', 'Disc and inlay'], ['disc', 'Disc label']]
      .filter(function (v) { return p.art[v[0]]; });
    var viewer = el('div', 'viewer'), vt = el('div', 'chips vtabs'), frame = el('div', 'vframe'), pic = new Image(), cap = el('p', 'note vcap');
    vt.setAttribute('role', 'group'); vt.setAttribute('aria-label', 'Show');
    frame.appendChild(pic); viewer.appendChild(vt); viewer.appendChild(frame); viewer.appendChild(cap);
    function align() {
      var dpr = window.devicePixelRatio || 1; pic.style.margin = '0';
      var r = pic.getBoundingClientRect(), fx = (r.left * dpr) % 1, fy = ((r.top + window.scrollY) * dpr) % 1;
      pic.style.margin = (fy > 1e-3 ? (1 - fy) / dpr : 0) + 'px 0 0 ' + (fx > 1e-3 ? (1 - fx) / dpr : 0) + 'px';
    }
    function show(k) {
      var wh = p.art[k], dpr = window.devicePixelRatio || 1;
      pic.alt = 'The ' + p.title + ' ' + (k === 'disc3d' ? 'disc on its inlay' : k === 'disc' ? 'disc label' : k);
      pic.src = p.id + '/' + k + '.png'; pic.loading = 'lazy';
      pic.style.width = (wh[0] / dpr) + 'px'; pic.style.height = (wh[1] / dpr) + 'px';
      frame.style.height = Math.min(wh[1] / dpr, Math.max(320, window.innerHeight * 0.8)) + 'px';
      cap.textContent = wh[0] + ' x ' + wh[1] + ' pixels, shown pixel for pixel' + (wh[0] / dpr > frame.clientWidth + 1 ? '; scroll to see all of it' : '') + '.';
      [].forEach.call(vt.children, function (c) { c.setAttribute('aria-pressed', String(c.getAttribute('data-k') === k)); });
      align();
    }
    VIEWS.forEach(function (v) { var b = el('button', 'chip', v[1]); b.type = 'button'; b.setAttribute('data-k', v[0]); b.addEventListener('click', function () { show(v[0]); }); vt.appendChild(b); });
    var body = el('div', 'pbody'), txt = el('div', 'ptext'), side = el('div', 'pside');
    body.appendChild(viewer); body.appendChild(txt); body.appendChild(side); packEl.appendChild(body);
    show(VIEWS[0][0]);
    var f = p.files, t = '';
    if (p.blurb) t += '<p class="blurb">' + esc(p.blurb) + '</p>';
    (p.intro || []).forEach(function (s) { t += '<p>' + esc(s) + '</p>'; });
    var facts = [p.edition, p.package && {bigbox: 'big box', jewel: 'jewel case', dvd: 'DVD case', mailer: 'mailer'}[p.package], p.price, p.starburst].filter(Boolean);
    if (facts.length) t += '<p class="facts">' + facts.map(esc).join(' &middot; ') + '</p>';
    t += '<p class="files">' + (f.pdf ? '<a class="btn def" href="' + p.id + '/' + esc(f.pdf.name) + '" target="_blank" rel="noopener">Manual (PDF' + (f.pdf.pages ? ', ' + f.pdf.pages + ' pages' : '') + ', ' + f.pdf.kb + ' KB)</a>' : '') +
      (f.hlp ? '<a class="btn" href="' + p.id + '/' + esc(f.hlp.name) + '" download>Help file (' + esc(f.hlp.name) + ', ' + f.hlp.kb + ' KB)</a>' : '') +
      (f.readme ? '<a class="btn" href="' + p.id + '/' + esc(f.readme.name) + '" target="_blank" rel="noopener">README.TXT</a>' : '') +
      (f.iso ? '<a class="btn" href="' + p.id + '/' + esc(f.iso.name) + '" download>Disc image (' + esc(f.iso.name) + ', ' + (f.iso.kb >= 1024 ? (f.iso.kb / 1024).toFixed(1) + ' MB' : f.iso.kb + ' KB') + ')</a>' : '') + '</p>' +
      (f.iso ? '<p class="note">The disc is already in SNDWAVE2000 1.3.0 (Library tab, drive P:). The image is for another machine, or to keep.</p>' : '');
    if (p.credits && p.credits.length) t += '<div class="credits"><p class="kicker">Sound credits</p><ul>' + p.credits.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul></div>';
    if (p.note && p.note.length) t += '<blockquote class="mnote"><p class="kicker">From the maker</p>' + p.note.map(function (s) { return '<p>' + esc(s) + '</p>'; }).join('') + '</blockquote>';
    txt.innerHTML = t;
    var m = p.maker;
    side.innerHTML = '<div class="maker"><p class="kicker">The company</p><address>' + (m.contact || [m.name, m.place]).map(esc).join('<br>') + '</address>' +
      (m.kind ? '<p class="note">' + esc(m.kind) + '. ' + esc(m.place) + '.</p>' : '') +
      (m.people && m.people.length ? '<ul class="people">' + m.people.map(function (x) { return '<li><b>' + esc(x[0]) + '</b>, ' + esc(x[1]) + '</li>'; }).join('') + '</ul>' : '') +
      (p.copyright ? '<p class="note">' + esc(p.copyright) + '</p>' : '') + '</div>';
  }

  // the shelf
  function card(p) {
    var a = el('a', 'card'); a.href = '#' + p.id;
    var box = el('span', 'pxbox pximg'), im = new Image(p.art.thumb[0], p.art.thumb[1]);
    im.src = p.id + '/thumb.png'; im.alt = ''; im.setAttribute('data-px', p.art.thumb[0] + 'x' + p.art.thumb[1]);
    box.appendChild(im); a.appendChild(box);
    var cats = Object.keys(p.cats).sort(function (x, y) { return p.cats[y] - p.cats[x]; });
    a.appendChild(el('b', null, esc(p.title)));
    a.appendChild(el('span', 'mk', esc(p.maker.name) + '<br>' + esc(p.label) + ' &middot; ' + esc(p.year)));
    a.appendChild(el('span', 'ct', p.n + ' presets' + (p.fav ? ' &middot; <span class="star" aria-label="favourites">&#9733;</span> ' + p.fav : '') +
      '<br><i>' + esc(cats.slice(0, 5).join(', ')) + (cats.length > 5 ? ' &hellip;' : '') + '</i>'));
    return a;
  }

  // #ID or #ID/SLUG
  function route(fromHashChange) {
    var h = decodeURIComponent(location.hash.slice(1)), parts = h.split('/'), id = parts[0], slug = parts[1];
    if (id === 'pack') return;
    if (!BY[id]) return false;
    if (playingX && playingX.pk === id && (!slug || playingX.s === slug)) return true;
    packSel.value = id;
    openPack(id).then(function () {
      if (slug) { var i = -1; cur.items.forEach(function (x, j) { if (x.s === slug) i = j; }); if (i >= 0) { select(i, true); } }
    });
    if (fromHashChange) $('mp').scrollIntoView({block: 'start', behavior: 'smooth'});
    return true;
  }
  fetch('packs.json').then(function (r) { return r.json(); }).then(function (d) {
    PACKS = d.packs;
    PACKS.forEach(function (p) { BY[p.id] = p; });
    ORDER = PACKS.slice().sort(function (a, b) { return a.title.toLowerCase() < b.title.toLowerCase() ? -1 : 1; }).map(function (p) { return p.id; });
    packSel.innerHTML = ORDER.map(function (id) { var p = BY[id]; return '<option value="' + id + '">' + esc(p.title) + ' (' + p.n + ')</option>'; }).join('') +
      '<option value="' + ALL + '">All packs (' + num(d.total) + ')</option>';
    PACKS.forEach(function (p) { grid.appendChild(card(p)); });
    [].forEach.call(grid.querySelectorAll('[data-px]'), function (i) { pxfit.fit(i); });
    $('status').textContent = PACKS.length + ' packs, ' + num(d.total) + ' presets. ' +
      (d.previews ? 'Every preview was rendered by the real Windows 3.11 machine.' : 'Every disc ships with SNDWAVE2000 1.3.0. Previews of every preset are being rendered on the release build; until then the owner\'s top picks play the demos already made, and the rest say "preview coming".');
    if (!route(false)) {   // first visit: the pack with the most previews
      var best = PACKS.slice().sort(function (a, b) { return (b.picks || 0) - (a.picks || 0) || b.fav - a.fav; })[0];
      packSel.value = best.id; openPack(best.id);
    }
    status('Ready. Choose a preset, or press Play.');
    document.querySelector('main').classList.remove('wait');
    window.addEventListener('hashchange', function () { route(true); });
  }, function () { status('The sound packs did not load. Try again later.'); document.querySelector('main').classList.remove('wait'); });

  // pixel-exact canvases: the art and the wave view
  artC.pxSource = artNative; scopeC.pxSource = sctx;
  if (window.pxfit) { pxfit.fit(artC); pxfit.fit(scopeC); }
  scopeDraw();
})();

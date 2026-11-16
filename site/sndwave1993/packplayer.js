/* The sound packs on the home page (/sndwave1993/#packs): a compact player. The stage is the pack's booklet page for
   the playing item's category (384 x 288, whole device pixels through /sndrec/pxfit.js; the playing preset's line
   inverted on a listing page); the controls sit over it. Beside it (below on phones), the pack's presets or songs.
   One click plays; at the end of a clip the next plays, on into the next pack; the next clip is prefetched.
   Keys (with the player focused): Space play / pause, Up / Down items, Left / Right packs. Swipe the art for packs.
   Data: packs/packs.json, packs/data/ID.json, packs/ID/booklet/booklet.json (tools/sndrec-demo/sndwave_site.py).
   The full player stays at /sndwave1993/packs/. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var root = $('pp'); if (!root) return;
  var audio = $('pp-audio'), list = $('pp-list'), art = $('pp-art'), seek = $('pp-seek'), playBtn = $('pp-play');
  var B = 'packs/', PACKS = [], BY = {}, DATA = {}, BOOK = {}, IMG = {};
  var cur = {i: 0, mode: 'p', items: [], sel: -1}, playing = null, wantPlay = false;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function fmt(t) { if (!isFinite(t) || t < 0) t = 0; var m = Math.floor(t / 60), s = Math.floor(t - m * 60); return m + ':' + (s < 10 ? '0' : '') + s; }
  function data(id) {
    if (!DATA[id]) DATA[id] = fetch(B + 'data/' + id + '.json').then(function (r) { return r.json(); }).then(function (d) { d.presets.forEach(function (x) { x.pk = id; }); return d.presets; });
    return DATA[id];
  }
  function booklet(id) {
    if (!BOOK[id]) BOOK[id] = BY[id].booklet ? fetch(B + id + '/' + BY[id].booklet).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }) : Promise.resolve(null);
    return BOOK[id];
  }
  function img(url) {
    if (!IMG[url]) IMG[url] = new Promise(function (ok, no) { var im = new Image(); im.onload = function () { ok(im); }; im.onerror = no; im.src = url; });
    return IMG[url];
  }
  function audioOf(x) {
    if (x.k === 'song') return (x.au.ogg && audio.canPlayType('audio/ogg; codecs="opus"')) ? B + x.au.ogg : (x.au.mp3 ? B + x.au.mp3 : null);
    if (x.a) return x.a;
    var v = x.v ? '?v=' + x.v : '';
    if (x.ogg && audio.canPlayType('audio/ogg; codecs="opus"')) return B + 'audio/' + x.s + '.ogg' + v;
    if (x.mp3) return B + 'audio/' + x.s + '.mp3' + v;
    return null;
  }

  // ---- the stage: the booklet page (the cover for a song, or before anything plays)
  var native = document.createElement('canvas'); native.width = 384; native.height = 288;
  art.pxSource = native; if (window.pxfit) pxfit.fit(art);
  var tok = 0;
  function drawArt(id, x) {
    var t = ++tok;
    booklet(id).then(function (bk) {
      if (t !== tok) return;
      var file = 'cover.png', pg = null;
      if (bk) {
        if (x && x.k !== 'song' && bk.by_category[x.c]) file = bk.by_category[x.c];
        bk.pages.forEach(function (q) { if (q.file === file) pg = q; });
      }
      var url = bk ? B + id + '/booklet/' + file : B + id + '/thumb.png';
      img(url).then(function (im) {
        if (t !== tok) return;
        var c = native.getContext('2d'); c.fillStyle = '#101018'; c.fillRect(0, 0, 384, 288);
        c.drawImage(im, Math.floor((384 - im.width) / 2), Math.floor((288 - im.height) / 2));
        var row = null; if (pg && x) (pg.rows || []).forEach(function (r) { if (r.name === x.n) row = r; });
        if (row) { var R = row.rect, d = c.getImageData(R[0], R[1], R[2], R[3]); for (var i = 0; i < d.data.length; i += 4) { d.data[i] = 255 - d.data[i]; d.data[i + 1] = 255 - d.data[i + 1]; d.data[i + 2] = 255 - d.data[i + 2]; } c.putImageData(d, R[0], R[1]); }
        art.setAttribute('aria-label', 'The ' + BY[id].title + ' booklet' + (pg && pg.category ? ', ' + pg.category + ' page' : ', cover'));
        if (window.pxfit) pxfit.draw(art);
      });
    });
  }

  // ---- the list
  function render() {
    list.innerHTML = '';
    var p = BY[PACKS[cur.i].id];
    cur.items = cur.all.filter(function (x) { return cur.mode === 's' ? x.k === 'song' : x.k !== 'song'; });
    var frag = document.createDocumentFragment();
    cur.items.forEach(function (x, i) {
      var r = document.createElement('div'); r.className = 'pp-it' + (x === playing ? ' on' : ''); r.id = 'pp-i' + i; r.setAttribute('role', 'option'); r.dataset.i = i;
      r.innerHTML = '<span class="pl" aria-hidden="true"></span><span class="nm">' + esc(x.n) + '</span>' + (x.fav ? '<span class="st">&#9733;</span>' : '') +
        '<span class="c">' + esc(x.k === 'song' ? (x.song.length || '') : x.c) + '</span>';
      frag.appendChild(r);
    });
    list.appendChild(frag);
    list.setAttribute('aria-label', (cur.mode === 's' ? 'Songs' : 'Presets') + ' in ' + p.title);
    var i = playing ? cur.items.indexOf(playing) : -1; select(i >= 0 ? i : 0, false);
  }
  function select(i, scroll) {
    var o = list.querySelector('.pp-it[aria-selected="true"]'); if (o) o.setAttribute('aria-selected', 'false');
    cur.sel = i; var r = $('pp-i' + i); if (!r) return;
    r.setAttribute('aria-selected', 'true'); list.setAttribute('aria-activedescendant', r.id);
    if (scroll !== false) { var top = r.offsetTop - list.offsetTop; if (top < list.scrollTop) list.scrollTop = top; else if (top + r.offsetHeight > list.scrollTop + list.clientHeight) list.scrollTop = top + r.offsetHeight - list.clientHeight; }
  }
  list.addEventListener('click', function (e) { var r = e.target.closest('.pp-it'); if (!r) return; var i = +r.dataset.i; select(i, false); play(cur.items[i]); });

  // ---- packs
  function showPack(i, then) {
    var n = PACKS.length; cur.i = (i + n) % n; var p = PACKS[cur.i], f = p.files || {};
    $('pp-pack').textContent = p.title; $('pp-maker').textContent = p.maker.name;
    $('pp-np').textContent = p.n; $('pp-ns').textContent = p.songs || 0; $('pp-ts').disabled = !p.songs;
    $('pp-links').innerHTML = (f.pdf ? '<a href="' + B + p.id + '/' + esc(f.pdf.name) + '" target="_blank" rel="noopener">Manual</a>' : '') +
      (f.hlp ? '<a href="' + B + p.id + '/' + esc(f.hlp.name) + '" download>Help</a>' : '') +
      (f.iso ? '<a href="' + B + p.id + '/' + esc(f.iso.name) + '" download>Disc</a>' : '') + '<a href="' + B + '#' + p.id + '">Open full player</a>';
    if (cur.mode === 's' && !p.songs) setMode('p', true);
    if (!playing || playing.pk !== p.id) drawArt(p.id, null);
    list.innerHTML = '';
    return data(p.id).then(function (arr) { if (PACKS[cur.i].id !== p.id) return; cur.all = arr; render(); if (then) then(); });
  }
  function setMode(m, quiet) {
    cur.mode = m; $('pp-tp').setAttribute('aria-pressed', String(m === 'p')); $('pp-ts').setAttribute('aria-pressed', String(m === 's'));
    if (!quiet && cur.all) render();
  }
  $('pp-tp').addEventListener('click', function () { setMode('p'); });
  $('pp-ts').addEventListener('click', function () { setMode('s'); });
  $('pp-prevpack').addEventListener('click', function () { showPack(cur.i - 1); });
  $('pp-nextpack').addEventListener('click', function () { showPack(cur.i + 1); });
  $('pp-fold').addEventListener('click', function () { var open = root.classList.toggle('folded'); this.setAttribute('aria-expanded', String(!open)); });

  // ---- playing
  function setUi(on) { playBtn.classList.toggle('on', on); playBtn.setAttribute('aria-label', on ? 'Pause' : 'Play');
    [].forEach.call(list.querySelectorAll('.pp-it.on'), function (e) { e.classList.remove('on'); });
    var i = playing ? cur.items.indexOf(playing) : -1; if (i >= 0) $('pp-i' + i).classList.add('on'); }
  function play(x) {
    var u = audioOf(x); if (!u) return;
    playing = x; wantPlay = true; audio.src = u; audio.currentTime = 0;
    var pr = audio.play(); if (pr && pr.catch) pr.catch(function () { wantPlay = false; setUi(false); });
    setUi(true); drawArt(x.pk, x);
    list.setAttribute('aria-label', 'Playing ' + x.n);
    var n = nextIn(cur.items, x); if (n) { var nu = audioOf(n); if (nu) fetch(nu).catch(function () {}); }   // prefetch
    if (!raf) raf = requestAnimationFrame(tick);
  }
  function nextIn(items, x) { var k = items.indexOf(x); return k >= 0 && k + 1 < items.length ? items[k + 1] : null; }
  function step(d) {
    var i = cur.sel + d;
    if (i >= cur.items.length) { showPack(cur.i + 1, function () { select(0); if (wantPlay) play(cur.items[0]); }); return; }
    if (i < 0) { showPack(cur.i - 1, function () { select(cur.items.length - 1); if (wantPlay) play(cur.items[cur.items.length - 1]); }); return; }
    select(i); if (wantPlay || !audio.paused) play(cur.items[i]);
  }
  function toggle() {
    if (!audio.paused) { audio.pause(); wantPlay = false; setUi(false); return; }
    if (playing && audio.currentTime > 0 && !audio.ended && cur.items[cur.sel] === playing) { audio.play(); wantPlay = true; setUi(true); if (!raf) raf = requestAnimationFrame(tick); return; }
    var x = cur.items[cur.sel]; if (x) play(x);
  }
  playBtn.addEventListener('click', toggle);
  $('pp-prev').addEventListener('click', function () { if (audio.currentTime > 3 && !audio.paused) { audio.currentTime = 0; return; } step(-1); });
  $('pp-next').addEventListener('click', function () { step(1); });
  audio.addEventListener('ended', function () { setUi(false); if (wantPlay) step(1); });
  audio.addEventListener('error', function () { if (wantPlay) setTimeout(function () { step(1); }, 500); });
  var seeking = false, raf = 0;
  seek.addEventListener('input', function () { seeking = true; if (isFinite(audio.duration)) audio.currentTime = seek.value * audio.duration; });
  seek.addEventListener('change', function () { seeking = false; });
  function tick() {
    raf = 0; var d = audio.duration;
    if (!seeking) seek.value = isFinite(d) && d > 0 ? audio.currentTime / d : 0;
    $('pp-time').textContent = fmt(audio.currentTime) + (isFinite(d) ? ' / ' + fmt(d) : '');
    if (!audio.paused) raf = requestAnimationFrame(tick);
  }
  root.addEventListener('keydown', function (e) {
    var t = e.target; if (t.tagName === 'INPUT' && t.type === 'range' && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) return;
    if ((t.tagName === 'BUTTON' || t.tagName === 'A') && (e.key === ' ' || e.key === 'Enter')) return;
    if (e.key === ' ') { e.preventDefault(); toggle(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); step(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); showPack(cur.i + 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); showPack(cur.i - 1); }
    else if (e.key === 'Enter' && t === list) { e.preventDefault(); var x = cur.items[cur.sel]; if (x) play(x); }
  });
  // swipe the art for the next or previous pack
  var down = null, stage = $('pp-stage');
  stage.addEventListener('pointerdown', function (e) { if (e.target.closest('.pp-bar')) return; down = {x: e.clientX, y: e.clientY}; });
  stage.addEventListener('pointerup', function (e) { if (!down) return; var dx = e.clientX - down.x, dy = e.clientY - down.y; down = null; if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) showPack(cur.i + (dx < 0 ? 1 : -1)); });

  fetch(B + 'packs.json').then(function (r) { return r.json(); }).then(function (d) {
    PACKS = d.packs.slice().sort(function (a, b) { return a.title.toLowerCase() < b.title.toLowerCase() ? -1 : 1; });
    PACKS.forEach(function (p) { BY[p.id] = p; });
    var start = 0; PACKS.forEach(function (p, i) { if (p.id === 'rainyl') start = i; });
    showPack(start);
  });
})();

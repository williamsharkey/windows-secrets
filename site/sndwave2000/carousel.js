/* The sound packs on the home page (/sndwave2000/#packs): a carousel of the packs' boxes (box_small, at whole device
   pixels), the selected pack's description, counts and files, and the media player (/sndwave2000/packs/?embed=1) in
   a Windows 3.1 window over the page. Data: packs/packs.json (tools/sndrec-demo/sndwave_site.py). The full player
   stays at /sndwave2000/packs/. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var root = $('spx'); if (!root) return;
  var view = root.querySelector('.spx-view'), track = root.querySelector('.spx-track');
  var dlg = $('spx-dlg'), frame = $('spx-frame');
  var PACKS = [], cur = 0, slots = [], SW = 256;   // slot width, CSS px
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function num(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  // each image pixel is k x k device pixels (k = the whole part of the device pixel ratio, at least 1)
  function sizeImg(im, w, h) { var dpr = window.devicePixelRatio || 1, k = Math.max(1, Math.floor(dpr + 1e-6)); im.style.width = (w * k / dpr) + 'px'; im.style.height = (h * k / dpr) + 'px'; }
  function load(i) {   // the box art loads only near the current pack
    var s = slots[i]; if (!s || s.loaded) return;
    s.loaded = true; s.img.src = 'packs/' + PACKS[i].id + '/thumb.png';
  }
  var dragX = 0;
  function place(anim) {
    if (slots[0]) SW = slots[0].el.offsetWidth || SW;   // the slot width from the stylesheet (narrower on phones)
    var dpr = window.devicePixelRatio || 1, x = view.clientWidth / 2 - (cur * SW + SW / 2) + dragX;
    x = Math.round(x * dpr) / dpr;   // on whole device pixels
    track.style.transition = anim ? 'transform .22s ease-out' : 'none';
    track.style.transform = 'translateX(' + x + 'px)';
  }
  function show(i, anim) {
    var n = PACKS.length; i = (i + n) % n; cur = i;
    slots.forEach(function (s, j) { s.el.classList.toggle('on', j === i); s.el.setAttribute('aria-current', j === i ? 'true' : 'false'); s.el.tabIndex = -1; });
    for (var d = -2; d <= 2; d++) load((i + d + n) % n);
    place(anim !== false);
    var p = PACKS[i], f = p.files || {}, cats = Object.keys(p.cats).sort(function (a, b) { return p.cats[b] - p.cats[a]; });
    $('spx-title').textContent = p.title;
    $('spx-maker').textContent = [p.maker.name, p.label, p.year].filter(Boolean).join(' · ');
    $('spx-desc').textContent = p.blurb || p.subtitle || '';
    $('spx-facts').innerHTML = num(p.n) + ' presets' + (p.songs ? ' &middot; ' + p.songs + (p.songs === 1 ? ' song' : ' songs') : '') +
      (p.fav ? ' &middot; <span class="star" aria-label="owner\'s favourites">&#9733;</span> ' + p.fav : '') + ' &middot; ' + esc(cats.slice(0, 6).join(', ')) + (cats.length > 6 ? ' &hellip;' : '');
    $('spx-links').innerHTML = (f.pdf ? '<a href="packs/' + p.id + '/' + esc(f.pdf.name) + '" target="_blank" rel="noopener">Manual</a>' : '') +
      (f.hlp ? '<a href="packs/' + p.id + '/' + esc(f.hlp.name) + '" download>Help</a>' : '') +
      (f.iso ? '<a href="packs/' + p.id + '/' + esc(f.iso.name) + '" download>Disc image</a>' : '');
    $('spx-open').href = 'packs/#' + p.id;
    $('spx-status').textContent = 'Disc ' + (i + 1) + ' of ' + n + ': ' + p.title;
  }
  root.querySelector('.spx-prev').addEventListener('click', function () { show(cur - 1); });
  root.querySelector('.spx-next').addEventListener('click', function () { show(cur + 1); });
  view.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(cur - 1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); show(cur + 1); }
    else if (e.key === 'Enter') { e.preventDefault(); openPlayer(); }
  });
  // swipe (and drag with a mouse): the track follows, then snaps to the nearest pack
  var down = null, dragged = false;
  view.addEventListener('pointerdown', function (e) { down = {x: e.clientX, y: e.clientY, id: e.pointerId, moved: false}; });
  view.addEventListener('pointermove', function (e) {
    if (!down || e.pointerId !== down.id) return;
    var dx = e.clientX - down.x;
    if (!down.moved && Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(e.clientY - down.y)) { down.moved = true; try { view.setPointerCapture(e.pointerId); } catch (x) {} }
    if (down.moved) { dragX = dx; place(false); }
  });
  function up(e) {
    if (!down || e.pointerId !== down.id) return;
    var moved = down.moved, dx = dragX; down = null; dragX = 0; dragged = moved;
    if (moved) { var steps = Math.round(-dx / SW) || (Math.abs(dx) > 40 ? (dx < 0 ? 1 : -1) : 0); show(cur + steps); }
  }
  view.addEventListener('pointerup', up); view.addEventListener('pointercancel', up);
  view.addEventListener('click', function (e) {   // a click on a neighbour goes to it; on the current box, plays the pack
    if (dragged) { dragged = false; return; }   // the click that ends a swipe
    var s = e.target.closest && e.target.closest('.spx-slot'); if (!s) return;
    var i = +s.dataset.i; if (i === cur) openPlayer(); else show(i);
  });
  window.addEventListener('resize', function () { slots.forEach(function (s, i) { sizeImg(s.img, PACKS[i].art.thumb[0], PACKS[i].art.thumb[1]); }); place(false); });

  // the player, in a window over the page
  var lastFocus = null;
  function openPlayer() {
    var p = PACKS[cur]; if (!p) return;
    lastFocus = document.activeElement;
    frame.style.height = ''; frame.src = 'packs/?embed=1&autoplay=1&p=' + encodeURIComponent(p.id) + '#' + p.id;
    $('spx-dtitle').textContent = 'SNDWAVE2000 Media Player - ' + p.title;
    dlg.hidden = false; document.documentElement.classList.add('spx-open');
    dlg.querySelector('.spx-close').focus();
  }
  function closePlayer() {
    if (dlg.hidden) return;
    frame.src = 'about:blank';   // stops the sound
    dlg.hidden = true; document.documentElement.classList.remove('spx-open');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  $('spx-play').addEventListener('click', openPlayer);
  window.addEventListener('message', function (e) {   // the player says how tall it is; the window fits it
    if (e.origin !== location.origin || !e.data || !e.data.spxHeight) return;
    if (window.innerWidth > 700) frame.style.height = Math.min(e.data.spxHeight, window.innerHeight - 80) + 'px';
  });
  dlg.querySelector('.spx-close').addEventListener('click', closePlayer);
  dlg.addEventListener('click', function (e) { if (e.target === dlg) closePlayer(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePlayer(); });

  fetch('packs/packs.json').then(function (r) { return r.json(); }).then(function (d) {
    PACKS = d.packs.slice().sort(function (a, b) { return a.title.toLowerCase() < b.title.toLowerCase() ? -1 : 1; });
    PACKS.forEach(function (p, i) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'spx-slot'; b.dataset.i = i;
      b.setAttribute('aria-label', p.title + ', ' + p.maker.name);
      var im = new Image(); im.alt = ''; im.width = p.art.thumb[0]; im.height = p.art.thumb[1]; im.draggable = false; sizeImg(im, p.art.thumb[0], p.art.thumb[1]);
      b.appendChild(im); track.appendChild(b); slots.push({el: b, img: im, loaded: false});
    });
    $('spx-count').textContent = PACKS.length + ' discs, ' + num(d.total) + ' presets';
    var start = 0; PACKS.forEach(function (p, i) { if (p.id === 'workgrp' && !start) start = i; });
    PACKS.forEach(function (p, i) { if (p.id === 'rainyl') start = i; });   // the newest disc first, when it is out
    show(start, false);
  }, function () { $('spx-status').textContent = 'The sound packs did not load.'; });
})();

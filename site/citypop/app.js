/* CITYPOP DEPROGRAMMED: the player, its Windows 3.1 windows, and the night they sit in.
   Every window is placed on whole device pixels; every canvas is backed at device resolution and drawn in device pixels. */
(() => {
'use strict';
const BUILD = '20261114g';             // cache key for the scene and life modules; bump on each UI deploy
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const store = {
  get(k, d) { try { const v = localStorage.getItem('cpd:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('cpd:' + k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  del(k) { try { localStorage.removeItem('cpd:' + k); } catch (e) { /* ignore */ } },
};
const mqReduced = matchMedia('(prefers-reduced-motion: reduce)');
const prefs = Object.assign({ tod: 'album', motion: false, remember: true, vol: 80, repeat: false, scale: 'auto' }, store.get('prefs', {}));
const savePrefs = () => store.set('prefs', prefs);
const reduced = () => mqReduced.matches || prefs.motion;
let DPR = window.devicePixelRatio || 1;
let S = 1;                                               // UI scale: 1 or 2 whole device pixels per CSS pixel of the windows
const RR = () => DPR * S;                                // device pixels per CSS pixel inside the desktop
const snap = (v) => Math.round(v * RR()) / RR();         // a CSS length that lands on a device pixel
const VW = () => innerWidth / S, VH = () => innerHeight / S;   // the viewport, in the desktop's own CSS pixels
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fmt = (s) => { s = Math.max(0, s | 0); return String((s / 60) | 0).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
const BAY = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
const rgb = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

/* ================================================================== device-pixel textures for the CSS */
function texture(w, h, fn) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d'), id = x.createImageData(w, h);
  for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) { const p = fn(i, y); const o = (y * w + i) * 4; id.data[o] = p[0]; id.data[o + 1] = p[1]; id.data[o + 2] = p[2]; id.data[o + 3] = p[3] == null ? 255 : p[3]; }
  x.putImageData(id, 0, 0);
  return 'url(' + c.toDataURL() + ')';
}
function paintTextures() {
  const R = document.documentElement.style, d = RR();
  // the active caption: magenta at the top settling into deep purple, ordered-dithered one device pixel at a time
  const th = Math.round(20 * d), top = rgb('#6a2a7a'), mid = rgb('#4b2472'), bot = rgb('#2c1c5a');
  R.setProperty('--title-img', texture(4, th, (x, y) => {
    const t = y / (th - 1), b = BAY[(y & 3) * 4 + (x & 3)];
    const [c0, c1, f] = t < 0.45 ? [top, mid, t / 0.45] : [mid, bot, (t - 0.45) / 0.55];
    return f > b ? c1 : c0;
  }));
  R.setProperty('--title-sz', `${4 / d}px 20px`);
  // the sizing border: a sparse grain of warm and dark device pixels over the plum brown
  R.setProperty('--frame-img', texture(4, 4, (x, y) => {
    const b = BAY[y * 4 + x];
    return b < 0.2 ? [0, 0, 0, 70] : b > 0.88 ? [210, 150, 120, 34] : [0, 0, 0, 0];
  }));
  R.setProperty('--frame-sz', `${4 / d}px`);
  R.setProperty('--dlg-img', texture(4, 4, (x, y) => (BAY[y * 4 + x] < 0.25 ? [0, 0, 0, 60] : [0, 0, 0, 0])));
  // the scroll-bar track: Windows' 50% checkerboard, at device pixels
  const a = rgb('#2b2545'), b = rgb('#110e24');
  R.setProperty('--track-img', texture(2, 2, (x, y) => ((x + y) & 1 ? a : b)));
  R.setProperty('--track-sz', `${2 / d}px`);
}
paintTextures();

/* ================================================================== a canvas backed at device resolution */
const views = [];
const SOFT = !/[?&]gpucanvas/.test(location.search);   // small canvases redrawn often are cheaper on the CPU than as GPU command streams
function view(cv, draw) {
  const v = { cv, ctx: cv.getContext('2d', SOFT ? { willReadFrequently: true } : undefined), w: 0, h: 0, cw: 0, ch: 0, k: DPR, draw };
  const ro = new ResizeObserver((es) => {
    for (const e of es) {
      let w, h;
      if (e.devicePixelContentBoxSize && e.devicePixelContentBoxSize[0]) { w = e.devicePixelContentBoxSize[0].inlineSize; h = e.devicePixelContentBoxSize[0].blockSize; }
      else { w = Math.round(e.contentRect.width * DPR); h = Math.round(e.contentRect.height * DPR); }
      v.cw = e.contentRect.width; v.ch = e.contentRect.height;
      if (w > 0 && h > 0 && (w !== v.w || h !== v.h)) { v.w = cv.width = w; v.h = cv.height = h; v.k = v.cw ? w / v.cw : DPR; v.draw(v, true); }
    }
  });
  try { ro.observe(cv, { box: 'device-pixel-content-box' }); } catch (e) { ro.observe(cv); }
  views.push(v);
  return v;
}
const redrawAll = () => views.forEach((v) => v.w && v.draw(v, true));

/* ================================================================== menus */
let openDD = null;
function closeMenu() { if (!openDD) return; openDD.dd.remove(); openDD.anchor.classList.remove('open'); const a = openDD.anchor; openDD = null; return a; }
function openMenu(anchor, items) {
  if (openDD && openDD.anchor === anchor) { closeMenu(); return; }
  closeMenu();
  const dd = document.createElement('div'); dd.className = 'dd'; dd.setAttribute('role', 'menu');
  for (const it of items) {
    if (it === '-') { dd.appendChild(document.createElement('hr')); continue; }
    const el = document.createElement(it.href ? 'a' : 'button');
    el.setAttribute('role', 'menuitem');
    if (it.href) { el.href = it.href; if (it.download) el.setAttribute('download', it.download); if (it.blank) el.target = '_blank'; }
    if (it.disabled) el.disabled = true;
    if (it.checked) el.classList.add('ck');
    el.innerHTML = it.label + (it.key ? `<span class="k">${it.key}</span>` : '');
    el.onclick = () => { closeMenu(); if (it.action) it.action(); };
    dd.appendChild(el);
  }
  $('#menus').appendChild(dd);
  const r = anchor.getBoundingClientRect();
  const rl = r.left / S, rt = r.top / S, rb = r.bottom / S;
  const x = clamp(rl, 0, VW() - dd.offsetWidth - 2), y = rb + dd.offsetHeight > VH() ? Math.max(0, rt - dd.offsetHeight) : rb;
  dd.style.left = snap(x) + 'px'; dd.style.top = snap(y) + 'px';
  anchor.classList.add('open');
  openDD = { dd, anchor };
  const first = dd.querySelector('button:not([disabled]), a'); if (first) first.focus({ preventScroll: true });
  dd.addEventListener('keydown', (e) => {
    const els = $$('button:not([disabled]), a', dd), i = els.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') { e.preventDefault(); els[(i + 1) % els.length].focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); els[(i - 1 + els.length) % els.length].focus(); }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); const a = closeMenu(); if (a) a.focus(); }
  });
}
addEventListener('pointerdown', (e) => { if (openDD && !openDD.dd.contains(e.target) && !openDD.anchor.contains(e.target)) closeMenu(); }, true);

/* ================================================================== the window manager */
const WINS = ['player', 'rec', 'ev', 'clock', 'notes', 'desktop', 'about', 'resume'];
const W = {};          // id -> {el, x, y, w, h, min}
let zTop = 10, wm = false;
WINS.forEach((id) => { W[id] = { id, el: $('#' + id), min: false }; });
const isWM = () => VW() >= 960 && VH() >= 580;
function uiScale() {
  if (prefs.scale === '1' || prefs.scale === '2') return +prefs.scale;
  return DPR < 1.5 && innerWidth >= 2200 && innerHeight >= 1160 ? 2 : 1;   // a big screen at one device pixel per CSS pixel: double
}
function applyScale() {
  const s = uiScale();
  if (s === S && document.body.dataset.scale === String(s)) return;
  S = s; document.body.dataset.scale = s;
  [$('#desk'), $('#menus'), $('#unhide')].forEach((el) => { el.style.zoom = s === 1 ? '' : s; });
  paintTextures(); closeMenu();
}

function defaults() {
  const vw = VW(), vh = VH(), top = 20, L = 20, gap = 12, foot = 76;
  const pw = 460, cw = vw >= 1700 ? 420 : 372, cx = L + pw + gap;
  const ph = Math.min(vh - top - foot, vw >= 1700 ? 820 : 700);
  if (wm) W.rec.el.style.width = cw + 'px';
  const recH = W.rec.el.offsetHeight || 180;
  const rest = vh - top - foot - recH - gap * 2;
  const evH = Math.max(200, Math.round(rest * 0.56)), nH = Math.max(140, rest - evH);
  const ck = vw >= 1700 ? 184 : 168;
  return {
    player: { x: L, y: top, w: pw, h: ph },
    rec: { x: cx, y: top, w: cw },
    ev: { x: cx, y: top + recH + gap, w: cw, h: evH },
    notes: { x: cx, y: top + recH + gap + evH + gap, w: cw, h: nH },
    clock: { x: vw - L - ck, y: top, w: ck, h: ck + 10 },
    desktop: { w: 300 }, about: { w: 320 },
  };
}
function place(id, g) {
  const o = W[id], el = o.el;
  Object.assign(o, g);
  if (!wm) return;
  const w = o.w ? Math.round(o.w) : el.offsetWidth;
  const h = o.h ? Math.round(o.h) : el.offsetHeight;
  if (o.x == null) { o.x = (VW() - w) / 2; o.y = Math.max(20, (VH() - (h || 300)) / 2 - 40); }
  o.x = clamp(o.x, 60 - w, VW() - 60); o.y = clamp(o.y, 0, VH() - 24);
  el.style.left = snap(o.x) + 'px'; el.style.top = snap(o.y) + 'px';
  if (o.w) el.style.width = o.w + 'px';
  if (o.h) el.style.height = o.h + 'px';
}
function saveLayout() {
  if (!prefs.remember || !wm) return;
  const L = {};
  ['player', 'rec', 'ev', 'clock', 'notes'].forEach((id) => { const o = W[id]; L[id] = { x: Math.round(o.x), y: Math.round(o.y), min: o.min }; });
  store.set('layout', { vw: innerWidth, vh: innerHeight, s: S, L });
}
function layout(reset) {
  applyScale();
  wm = isWM();
  document.body.classList.toggle('wm', wm);
  if (!wm) { WINS.forEach((id) => { const el = W[id].el; el.style.left = el.style.top = el.style.width = el.style.height = ''; }); occlude(); return; }
  const D = defaults();
  let saved = !reset && prefs.remember ? store.get('layout', null) : null;
  if (saved && (saved.s || 1) !== S) saved = null;
  ['rec', 'player', 'ev', 'notes', 'clock'].forEach((id) => {
    const g = Object.assign({}, D[id]);
    if (saved && saved.L && saved.L[id]) { g.x = saved.L[id].x; g.y = saved.L[id].y; setMin(id, !!saved.L[id].min, true); }
    else if (reset) setMin(id, false, true);
    place(id, g);
  });
  icons();
  occlude();
}
function focusWin(id) {
  const o = W[id];
  WINS.forEach((k) => W[k].el.classList.toggle('on', k === id));
  if (wm) o.el.style.zIndex = ++zTop;
}
function setMin(id, on, quiet) {
  const o = W[id]; o.min = on; o.el.classList.toggle('min', on);
  if (!quiet) { icons(); saveLayout(); occlude(); if (!on) { focusWin(id); kick(); } }
}
function restore(id) {
  const o = W[id];
  if (o.el.hidden) { o.el.hidden = false; place(id, { x: null }); }
  setMin(id, false);
  focusWin(id);
}
// drag by the caption
WINS.forEach((id) => {
  const o = W[id], el = o.el, tb = $('.tb', el);
  el.addEventListener('pointerdown', () => focusWin(id), true);
  tb.addEventListener('pointerdown', (e) => {
    if (!wm || e.button !== 0 || e.target.closest('button')) return;
    e.preventDefault();
    const sx = e.clientX, sy = e.clientY, ox = o.x, oy = o.y;
    tb.setPointerCapture(e.pointerId);
    const mv = (ev) => { o.x = ox + (ev.clientX - sx) / S; o.y = oy + (ev.clientY - sy) / S; place(id, {}); };
    const up = () => { tb.removeEventListener('pointermove', mv); tb.removeEventListener('pointerup', up); tb.removeEventListener('pointercancel', up); saveLayout(); occlude(); };
    tb.addEventListener('pointermove', mv); tb.addEventListener('pointerup', up); tb.addEventListener('pointercancel', up);
  });
  const mn = $('.mn', el);
  if (mn) mn.onclick = () => setMin(id, true);
  const sys = $('.sys', el);
  const close = () => { if (el.classList.contains('dlg')) closeDialog(id); else setMin(id, true); };
  sys.onclick = () => openMenu(sys, [
    { label: '<u>R</u>estore', disabled: true }, { label: '<u>M</u>ove', disabled: !wm, action: () => {} }, { label: '<u>S</u>ize', disabled: true },
    { label: 'Mi<u>n</u>imize', disabled: !!el.classList.contains('dlg'), action: () => setMin(id, true) }, { label: 'Ma<u>x</u>imize', disabled: true },
    '-', { label: '<u>C</u>lose', key: 'Alt+F4', action: close },
    '-', { label: 'Hide All <u>W</u>indows', key: 'H', action: watch },
  ]);
  sys.ondblclick = close;
});

/* ------------------------------------------------------------------ Program Manager icons */
const ICONS = [['player', 'Media Player'], ['rec', 'Sound Recorder'], ['ev', 'Event List'], ['clock', 'Clock'], ['notes', 'LINERS.TXT'], ['desktop', 'Desktop']];
const iconViews = [];
function buildIcons() {
  const nav = $('#icons');
  for (const [id, label] of ICONS) {
    const b = document.createElement('button'); b.className = 'ic'; b.dataset.id = id; b.title = label;
    b.innerHTML = `<canvas aria-hidden="true"></canvas><span>${label}</span>`;
    b.onclick = () => (id === 'desktop' ? openDesktop() : restore(id));
    nav.appendChild(b);
    iconViews.push(view($('canvas', b), (v) => paintIcon(v, id)));
  }
  $$('#icons .ic').forEach((b) => b.setAttribute('aria-label', 'Open ' + b.title));
}
function icons() { $$('#icons .ic').forEach((b) => { const o = W[b.dataset.id]; b.classList.toggle('open', o && !o.min && !o.el.hidden); }); }

/* icons, drawn on a 32 x 32 grid at device pixels; where there are two or more device pixels per grid cell,
   the fine lines (glints, grilles, hands) are a single device pixel */
function paintIcon(v, kind) {
  const { ctx: c, w } = v, k = w / 32, px = 1 / k;   // px = one device pixel in grid units
  c.setTransform(k, 0, 0, k, 0, 0); c.clearRect(0, 0, 32, 32); c.imageSmoothingEnabled = false;
  const R = (x, y, ww, hh, col) => { c.fillStyle = col; c.fillRect(x, y, ww, hh); };
  const box = (x, y, ww, hh, fill) => { R(x, y, ww, hh, '#000'); R(x + 1, y + 1, ww - 2, hh - 2, fill); };
  if (kind === 'player' || kind === 'about') {
    // a compact disc in front of a film-strip
    R(2, 6, 24, 18, '#000'); R(3, 7, 22, 16, '#2b2148');
    for (let i = 0; i < 6; i++) { const x = 4 + Math.round(i * 3.5); R(x, 8, 2, 2, '#8a7fbf'); R(x, 20, 2, 2, '#8a7fbf'); }
    R(4, 11, 20, 8, '#120f26'); R(5, 12, 8, 6, '#4a2470'); R(14, 12, 9, 6, '#6a2a74');
    c.beginPath(); c.arc(21, 19, 10, 0, Math.PI * 2); c.fillStyle = '#000'; c.fill();
    const g = c.createLinearGradient(12, 10, 30, 28); g.addColorStop(0, '#f0d6a0'); g.addColorStop(0.35, '#d8d0f0'); g.addColorStop(0.6, '#b0507e'); g.addColorStop(1, '#5a3a8c');
    c.beginPath(); c.arc(21, 19, 9, 0, Math.PI * 2); c.fillStyle = g; c.fill();
    c.strokeStyle = 'rgba(255,255,255,.35)'; c.lineWidth = px; for (const r of [4.5, 6, 7.5]) { c.beginPath(); c.arc(21, 19, r, 3.6, 4.9); c.stroke(); }
    c.beginPath(); c.arc(21, 19, 2.6, 0, Math.PI * 2); c.fillStyle = '#000'; c.fill();
    c.beginPath(); c.arc(21, 19, 1.4, 0, Math.PI * 2); c.fillStyle = '#07081a'; c.fill();
  } else if (kind === 'rec') {
    // a microphone on a stand
    R(12, 2, 9, 15, '#000'); R(13, 3, 7, 13, '#6b5f9e'); R(13, 3, 2, 13, '#a99dcb');
    for (let y = 5; y < 15; y += 2) R(15, y, 5, px, '#262241');
    R(10, 13, 1, 5, '#000'); R(22, 13, 1, 5, '#000'); R(10, 18, 13, 1, '#000'); R(16, 18, 1, 7, '#000'); if (k >= 2) R(17 - px, 18, px, 7, '#8a7fbf');
    R(9, 25, 15, 3, '#000'); R(10, 25, 13, 2, '#4b4275'); R(10, 25, 13, px, '#a99dcb');
    R(4, 28, 3, 1, '#7fe08a'); R(26, 28, 3, 1, '#7fe08a');
    for (let i = 0; i < 5; i++) R(2 + i, 22 - Math.round(Math.sin(i * 1.3) * 3), 1, 1, '#7fe08a');
  } else if (kind === 'ev') {
    // a sheet of the event list, rows in the channel colours, a folded corner
    c.fillStyle = '#000'; c.beginPath(); c.moveTo(5, 2); c.lineTo(22, 2); c.lineTo(28, 8); c.lineTo(28, 30); c.lineTo(5, 30); c.closePath(); c.fill();
    c.fillStyle = '#e9e2f7'; c.beginPath(); c.moveTo(6, 3); c.lineTo(21, 3); c.lineTo(27, 9); c.lineTo(27, 29); c.lineTo(6, 29); c.closePath(); c.fill();
    c.fillStyle = '#a99dcb'; c.beginPath(); c.moveTo(21, 3); c.lineTo(21, 9); c.lineTo(27, 9); c.closePath(); c.fill();
    const col = ['#9ad0ff', '#f0b0d8', '#f0d6a0', '#b8f0c0', '#d0a8ff', '#ffb89a', '#8fe0e0', '#f0b0d8', '#9ad0ff'];
    R(7, 21, 20, 1, 'rgba(140,52,120,.45)');
    for (let i = 0; i < 9; i++) { const y = 11 + i * 2; R(8, y, 2, 1, col[i]); R(11, y, 4 + ((i * 7) % 9), 1, '#3a3360'); }
  } else if (kind === 'clock') {
    c.beginPath(); c.arc(16, 16, 14, 0, Math.PI * 2); c.fillStyle = '#000'; c.fill();
    c.beginPath(); c.arc(16, 16, 13, 0, Math.PI * 2); c.fillStyle = '#29243f'; c.fill();
    c.beginPath(); c.arc(16, 16, 11.5, 0, Math.PI * 2); c.fillStyle = '#131127'; c.fill();
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; R(Math.round(16 + Math.sin(a) * 9.5) - 1, Math.round(16 - Math.cos(a) * 9.5) - 1, i % 3 ? 1 : 2, i % 3 ? 1 : 2, i % 3 ? '#8a7fbf' : '#f0d6a0'); }
    c.strokeStyle = '#e9e2f7'; c.lineCap = 'square'; c.lineWidth = 2; c.beginPath(); c.moveTo(16, 16); c.lineTo(16 + 5, 16 - 3); c.stroke();
    c.lineWidth = 1.2; c.beginPath(); c.moveTo(16, 16); c.lineTo(16 - 1, 16 - 8); c.stroke();
    c.strokeStyle = '#f0a0c8'; c.lineWidth = px; c.beginPath(); c.moveTo(16, 16); c.lineTo(16 - 6, 16 + 6); c.stroke();
  } else if (kind === 'notes') {
    // a notepad, spiral bound
    box(5, 4, 22, 26, '#e9e2f7'); R(6, 5, 20, 4, '#4b2472');
    for (let i = 0; i < 6; i++) { R(7 + i * 3, 2, 1, 5, '#000'); R(7 + i * 3 + px, 2, px, 4, '#a99dcb'); }
    for (let y = 12; y < 28; y += 3) R(8, y, y === 24 ? 9 : 16, 1, '#8a7fbf');
  } else if (kind === 'desktop') {
    // a monitor with the night in it
    box(3, 4, 26, 20, '#29243f'); R(5, 6, 22, 15, '#000');
    const g = c.createLinearGradient(0, 7, 0, 20); g.addColorStop(0, '#0d1030'); g.addColorStop(0.6, '#33226a'); g.addColorStop(1, '#8c3478');
    c.fillStyle = g; c.fillRect(6, 7, 20, 13);
    c.beginPath(); c.arc(21, 10, 2, 0, Math.PI * 2); c.fillStyle = '#f0d6a0'; c.fill();
    R(7, 15, 4, 5, '#07081a'); R(11, 13, 3, 7, '#07081a'); R(15, 16, 5, 4, '#07081a'); R(8, 16, 1, 1, '#f0d6a0'); R(12, 15, 1, 1, '#f0d6a0');
    R(13, 24, 6, 3, '#000'); R(9, 27, 14, 3, '#000'); R(10, 27, 12, 2, '#4b4275');
  }
  c.setTransform(1, 0, 0, 1, 0, 0);
}

/* ================================================================== scroll bars for Notepad and the track list */
function scroller(sv) {
  const vp = $('.vp', sv), sb = $('.sb', sv);
  sb.innerHTML = '<span class="ar u"></span><span class="tr"><span class="th"></span></span><span class="ar d"></span>';
  const tr = $('.tr', sb), th = $('.th', sb);
  const sync = () => {
    const max = vp.scrollHeight - vp.clientHeight, span = tr.clientHeight - 16;
    sb.classList.toggle('off', max <= 1);
    th.style.top = snap(max > 0 ? vp.scrollTop / max * Math.max(0, span) : 0) + 'px';
  };
  vp.addEventListener('scroll', sync, { passive: true });
  const ro = new ResizeObserver(sync); ro.observe(vp); if (vp.firstElementChild) ro.observe(vp.firstElementChild);
  const repeat = (fn) => (e) => {
    e.preventDefault(); fn(e);
    let t = setTimeout(function again() { fn(e); t = setTimeout(again, 45); }, 380);
    const stop = () => { clearTimeout(t); removeEventListener('pointerup', stop); removeEventListener('pointercancel', stop); };
    addEventListener('pointerup', stop); addEventListener('pointercancel', stop);
  };
  $('.ar.u', sb).addEventListener('pointerdown', repeat(() => { vp.scrollTop -= 18; }));
  $('.ar.d', sb).addEventListener('pointerdown', repeat(() => { vp.scrollTop += 18; }));
  tr.addEventListener('pointerdown', repeat((e) => {
    if (e.target === th) return;
    const r = th.getBoundingClientRect();
    if (e.clientY < r.top) vp.scrollTop -= vp.clientHeight - 18; else if (e.clientY > r.bottom) vp.scrollTop += vp.clientHeight - 18;
  }));
  th.addEventListener('pointerdown', (e) => {
    e.preventDefault(); e.stopPropagation();
    const sy = e.clientY, st = vp.scrollTop, max = vp.scrollHeight - vp.clientHeight, span = tr.clientHeight - 16;
    th.setPointerCapture(e.pointerId);
    const mv = (ev) => { vp.scrollTop = st + (ev.clientY - sy) / S / Math.max(1, span) * max; };
    const up = () => { th.removeEventListener('pointermove', mv); th.removeEventListener('pointerup', up); };
    th.addEventListener('pointermove', mv); th.addEventListener('pointerup', up);
  });
  return { sync };
}
const npScroll = scroller($('#npbox'));
const lbScroll = scroller($('#listbox'));

/* ================================================================== trackbars: position and volume */
function trackbar(cv, o) {
  const tb = { v: 0, drag: false, lastSig: '' };
  const vw = view(cv, (v) => { tb.lastSig = ''; draw(v); });
  const geom = (v) => { const k = v.k, m = Math.round((o.small ? 7 : 8) * k); return { k, x0: m, x1: v.w - m - 1 }; };
  function draw(v) {
    if (!v.w) return;
    const { ctx: c, w, h } = v, { k, x0, x1 } = geom(v), L = Math.max(1, Math.round(k)), one = 1;
    const tx = Math.round(x0 + tb.v * (x1 - x0));
    const sig = tx + '|' + (o.ticks ? o.ticks().length : 0) + '|' + w;
    if (sig === tb.lastSig) return; tb.lastSig = sig;
    c.fillStyle = '#29243f'; c.fillRect(0, 0, w, h);
    // the sunken channel
    const cy = Math.round((o.small ? 6 : 7) * k), ch = Math.round(5 * k);
    c.fillStyle = '#0e0b20'; c.fillRect(x0 - L, cy - L, x1 - x0 + 2 * L, L); c.fillRect(x0 - L, cy - L, L, ch + 2 * L);
    c.fillStyle = '#7869ab'; c.fillRect(x0 - L, cy + ch, x1 - x0 + 2 * L, L); c.fillRect(x1 + 1, cy - L, L, ch + 2 * L);
    c.fillStyle = '#000'; c.fillRect(x0, cy, x1 - x0 + 1, ch);
    // the played part: a magenta dither, one device pixel at a time
    if (tx > x0) {
      if (!tb.pat) { const p = document.createElement('canvas'); p.width = p.height = 2; const q = p.getContext('2d'); q.fillStyle = '#5a2470'; q.fillRect(0, 0, 2, 2); q.fillStyle = '#8c3478'; q.fillRect(0, 0, 1, 1); q.fillRect(1, 1, 1, 1); tb.pat = c.createPattern(p, 'repeat'); }
      c.fillStyle = tb.pat; c.fillRect(x0 + one, cy + one, tx - x0 - one, ch - 2 * one);
      c.fillStyle = '#b0507e'; c.fillRect(x0 + one, cy + one, tx - x0 - one, 1);
    }
    // the scale
    if (o.ticks) {
      const ty = cy + ch + L + Math.round(4 * k);
      c.font = `${Math.round(9 * k)}px "CP Sans", "DejaVu Sans", sans-serif`; c.textBaseline = 'top'; c.textAlign = 'center';
      let lastLab = -1e9;
      for (const t of o.ticks()) {
        const x = Math.round(x0 + t.at * (x1 - x0));
        c.fillStyle = t.major ? '#a99dcb' : '#5a5084';
        c.fillRect(x, ty, one * (t.major && k >= 2 ? 1 : 1), Math.round((t.major ? 5 : 3) * k));
        if (t.label && !o.small) {
          const tw = c.measureText(t.label).width;
          const lx = Math.round(clamp(x, tw / 2 + 1, w - tw / 2 - 1));
          if (lx - tw / 2 > lastLab + 4 * k) { c.fillStyle = '#8f84b6'; c.fillText(t.label, lx, ty + Math.round(6 * k)); lastLab = lx + tw / 2; }
        }
      }
    }
    // the thumb: a raised slab with a groove down the middle
    const tw = Math.round((o.small ? 9 : 11) * k) | 1, thh = Math.round((o.small ? 16 : 19) * k), ty0 = cy + Math.round(ch / 2) - Math.round(thh / 2);
    const x = tx - (tw >> 1);
    c.fillStyle = '#000'; c.fillRect(x - L, ty0 - L, tw + 2 * L, thh + 2 * L);
    c.fillStyle = '#29243f'; c.fillRect(x, ty0, tw, thh);
    c.fillStyle = '#7869ab'; c.fillRect(x, ty0, tw, L); c.fillRect(x, ty0, L, thh);
    c.fillStyle = '#0e0b20'; c.fillRect(x, ty0 + thh - 2 * L, tw, 2 * L); c.fillRect(x + tw - 2 * L, ty0, 2 * L, thh);
    c.fillStyle = '#0e0b20'; c.fillRect(tx - (k >= 2 ? 1 : 0), ty0 + 3 * L, 1, thh - 6 * L);
    c.fillStyle = '#a99dcb'; c.fillRect(tx + (k >= 2 ? 0 : 1), ty0 + 3 * L, 1, thh - 6 * L);
  }
  const valAt = (e) => { const r = cv.getBoundingClientRect(), { k, x0, x1 } = geom(vw); return clamp(((e.clientX - r.left) * (vw.w / r.width) - x0) / (x1 - x0), 0, 1); };
  cv.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    e.preventDefault(); cv.focus({ preventScroll: true }); cv.setPointerCapture(e.pointerId);
    tb.drag = true; tb.set(valAt(e)); if (o.input) o.input(tb.v);
    const mv = (ev) => { tb.set(valAt(ev)); if (o.input) o.input(tb.v); };
    const up = () => { tb.drag = false; cv.removeEventListener('pointermove', mv); cv.removeEventListener('pointerup', up); cv.removeEventListener('pointercancel', up); if (o.change) o.change(tb.v); };
    cv.addEventListener('pointermove', mv); cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  });
  cv.addEventListener('keydown', (e) => {
    const st = o.step || 0.05;
    let nv = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') nv = tb.v + st; else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') nv = tb.v - st;
    else if (e.key === 'Home') nv = 0; else if (e.key === 'End') nv = 1; else if (e.key === 'PageUp') nv = tb.v + st * 4; else if (e.key === 'PageDown') nv = tb.v - st * 4;
    if (nv == null) return;
    e.preventDefault(); e.stopPropagation(); tb.set(clamp(nv, 0, 1)); if (o.change) o.change(tb.v);
  });
  let aria = '';
  tb.set = (v) => {
    tb.v = clamp(v, 0, 1);
    const txt = o.text ? o.text(tb.v) : String(Math.round(tb.v * 100));
    if (txt !== aria) { aria = txt; cv.setAttribute('aria-valuenow', Math.round(tb.v * 100)); if (o.text) cv.setAttribute('aria-valuetext', txt); }
    draw(vw);
  };
  tb.redraw = () => { tb.lastSig = ''; draw(vw); };
  return tb;
}

/* ================================================================== the player */
const A = [new Audio(), new Audio()];     // two decks: the next track waits loaded in the other one
A.forEach((a) => { a.preload = 'auto'; a.crossOrigin = 'anonymous'; });
let cur = 0, deck = 0, album = null, ac = null, an = null, an2 = null, gain = null, fader = null, loadedNext = -1, stopped = true;
const evdata = {};
const opus = A[0].canPlayType('audio/ogg; codecs=opus') !== '';
const src = (t) => (opus ? t.opus : t.mp3);
const list = $('#list');
const T = () => (album ? album.tracks[cur] : null);
const durOf = (a) => (isFinite(a.duration) && a.duration > 0 ? a.duration : (T() && T().seconds) || 0);

function webaudio() {
  if (ac) return;
  try {
    ac = new (window.AudioContext || window.webkitAudioContext)();
    gain = ac.createGain(); fader = ac.createGain(); fader.connect(gain); an = ac.createAnalyser(); an.fftSize = 2048; an.smoothingTimeConstant = 0;
    an2 = ac.createAnalyser(); an2.fftSize = 1024;
    A.forEach((a) => { a.volume = 1; ac.createMediaElementSource(a).connect(fader); });
    gain.connect(an); gain.connect(an2); gain.connect(ac.destination);
    gain.gain.value = (prefs.vol / 100) ** 2;
    if (lifeCtl && lifeCtl.setAnalyser) try { lifeCtl.setAnalyser(an2); } catch (e) { /* life optional */ }
  } catch (e) { ac = null; }
}
function setVol(v, save = true) {
  v = clamp(Math.round(v), 0, 100); prefs.vol = v;
  if (gain) gain.gain.value = (v / 100) ** 2; else A.forEach((a) => { a.volume = (v / 100) ** 2; });
  volBar.set(v / 100);
  if (save) savePrefs();
}

/* titles, variations and keys, for the list */
function parseTitle(t) {
  const m = t.title.match(/^(?:Var\.\s*([IVXLC]+)|(Theme)|(Finale))\s*:?\s*(.*)$/);
  if (!m) return { v: '', name: t.title };
  return { v: m[1] || (m[2] ? 'Th.' : 'Fin.'), name: m[4] || t.title };
}
function keyOf(t) {
  let k = t.key;
  if (!k && t.note) { const m = t.note.match(/\bin ([A-G](?:-flat|-sharp)?(?: (?:major|minor))?)\b/); if (m) k = m[1]; }
  return k || '';
}
const keyShort = (k) => k.replace(/-flat/g, '♭').replace(/-sharp/g, '♯').replace(/ major/g, '').replace(/ minor/g, 'm').replace(/,? then /g, '→').replace(/,? and /g, '/');
function meterOf(t) { if (t.meter) return +t.meter; return /waltz|3\/4/i.test((t.variation || '') + ' ' + (t.note || '')) ? 3 : 4; }
const ready = (i) => album && album.tracks[i] && !album.tracks[i].pending;

function renderList() {
  const d = album, frag = document.createDocumentFragment();
  d.tracks.forEach((t, i) => {
    const li = document.createElement('li'); li.tabIndex = 0;
    const p = parseTitle(t), k = keyOf(t);
    li.innerHTML = '<span class="n"></span><span class="v"></span><span class="t"></span><span class="k"></span><span class="b"></span><span class="d"></span>';
    const s = li.children;
    s[0].textContent = String(t.n).padStart(2, '0'); s[1].textContent = p.v; s[2].textContent = p.name;
    s[3].textContent = t.pending ? '' : keyShort(k); s[3].title = k;
    s[4].textContent = t.pending || !t.bpm ? '' : Math.round(t.bpm);
    s[5].textContent = t.pending ? '--:--' : fmt(t.seconds);
    li.title = t.pending ? t.title + ' — in the mastering room.' : t.title + (t.variation ? ' — ' + t.variation : '');
    if (t.pending) { li.classList.add('wait'); li.setAttribute('aria-disabled', 'true'); }
    li.classList.toggle('on', i === cur);
    li.onclick = () => play(i);
    li.ondblclick = () => play(i);
    li.onkeydown = (e) => {
      if (e.key === 'Enter') play(i);
      else if (e.key === 'ArrowDown' && li.nextElementSibling) { e.preventDefault(); e.stopPropagation(); li.nextElementSibling.focus(); }
      else if (e.key === 'ArrowUp' && li.previousElementSibling) { e.preventDefault(); e.stopPropagation(); li.previousElementSibling.focus(); }
    };
    frag.appendChild(li);
  });
  list.replaceChildren(frag);
  const nready = d.tracks.filter((t) => !t.pending).length;
  $('#stat2').textContent = nready < d.tracks.length ? `${nready} of ${d.tracks.length} tracks ready` : `${d.tracks.length} tracks`;
  lbScroll.sync();
}
function show(i) {
  const t = album.tracks[i];
  [...list.children].forEach((li, k) => { li.classList.toggle('on', k === i); li.setAttribute('aria-current', k === i ? 'true' : 'false'); });
  const li = list.children[i]; if (li) { const vp = li.parentElement.parentElement; if (li.offsetTop < vp.scrollTop || li.offsetTop + 18 > vp.scrollTop + vp.clientHeight) vp.scrollTop = li.offsetTop - 36; }
  const p = parseTitle(t);
  $('#ttitle').textContent = t.title;
  $('#tvar').textContent = t.pending ? 'In the mastering room. It will be here shortly; the player skips it until then.' : (t.variation ? t.variation.charAt(0).toUpperCase() + t.variation.slice(1) + '. ' : '') + (t.note || '');
  $('#tvar').title = t.note || '';
  const nn = String(t.n).padStart(2, '0');
  $('#rectitle').textContent = 'Sound Recorder - TRACK' + nn + '.WAV';
  $('#rlen').textContent = (t.seconds || 0).toFixed(2) + ' sec.';
  $('#evname').textContent = 'TRACK' + nn + '.MID';
  document.title = (p.name || t.title) + ' — CITYPOP DEPROGRAMMED';
  if ('mediaSession' in navigator) {
    try { navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: 'Algorithmic Industries', album: 'CITYPOP DEPROGRAMMED', artwork: [{ src: 'art/cover-640.png', sizes: '640x640', type: 'image/png' }] }); } catch (e) { /* old browsers */ }
  }
  posBar.redraw();
  loadEvents(i);
  lcdDirty = true; evDirty = true; kick();
}
function loadEvents(i) {
  const t = album.tracks[i];
  if (evdata[i] || !t.events || t.pending) return;
  evdata[i] = 'loading';
  fetch(t.events).then((r) => r.json()).then((d) => { evdata[i] = d; d.key = t.events; if (i === cur) { evDirty = true; evStatus(); kick(); } }).catch(() => { evdata[i] = null; });
}
function prepare(i) {   // the next track into the idle deck
  if (!album || i < 0 || i >= album.tracks.length || loadedNext === i || !ready(i)) return;
  const a = A[1 - deck]; a.src = src(album.tracks[i]); a.preload = 'auto'; a.load(); loadedNext = i; loadEvents(i);
}
function play(i, from = 0) {
  if (!album) return;
  if (!leaving) unfade();
  if (!ready(i)) { cur = i; show(i); return; }
  webaudio(); if (ac && ac.state === 'suspended') ac.resume();
  const t = album.tracks[i];
  let a;
  if (loadedNext === i) { deck = 1 - deck; a = A[deck]; } else { a = A[deck]; a.src = src(t); }
  A[1 - deck].pause();
  loadedNext = -1; cur = i; stopped = false; advancing = false;
  try { a.currentTime = from; } catch (e) { /* not seekable yet */ }
  a.play().catch(() => {});
  show(i); playing(true);
  if (lifeCtl && lifeCtl.onTrack) try { lifeCtl.onTrack(t.n, { bpm: t.bpm, title: t.title }); } catch (e) { /* optional */ }
  pushTime(); saveNow();
}
let isPlaying = false, lifeDriven = false;
function driveLife() {   // while the music plays, life draws inside the UI's frames instead of its own
  const want = !!(lifeCtl && lifeCtl.drive && lifeCtl.frame && isPlaying && !document.hidden && !prefs.motion && busy());
  if (want === lifeDriven) return;
  lifeDriven = want;
  try { lifeCtl.drive(want); } catch (e) { lifeDriven = false; }
}
function playing(on) {
  isPlaying = on; driveLife();
  $('#playicon').setAttribute('d', on ? 'M4 3h3v10H4zM9 3h3v10H9z' : 'M5 3h1v10H5zM6 4h1v8H6zM7 5h1v6H7zM8 6h1v4H8zM9 7h1v2H9z');
  $('#play').setAttribute('aria-label', on ? 'Pause' : 'Play');
  $('#stat').textContent = on ? 'Playing' : stopped ? 'Stopped' : 'Paused';
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = on ? 'playing' : 'paused';
  lcdDirty = true; evDirty = true; kick();
}
function toggle() {
  const a = A[deck];
  if (!a.src) return play(cur);
  if (a.paused) { webaudio(); if (ac) ac.resume(); unfade(); stopped = false; a.play().catch(() => {}); playing(true); } else { a.pause(); playing(false); saveNow(); }
}
function stop() { const a = A[deck]; a.pause(); try { a.currentTime = 0; } catch (e) { /* ignore */ } stopped = true; playing(false); saveNow(); }
function nextReady(i, d) {   // the next track out of the mastering room; continuous play never stops on one that isn't
  const n = album.tracks.length;
  for (let k = 1; k <= n; k++) { const j = ((i + d * k) % n + n) % n; if (ready(j)) return j; }
  return i;
}
function step(d) { if (album) play(prefs.repeat && d === 0 ? cur : nextReady(cur, d)); }
let advancing = false;
function advance() { if (advancing) return; advancing = true; if (prefs.repeat) play(cur); else step(1); }
A.forEach((a, k) => {
  a.addEventListener('ended', () => { if (k === deck) advance(); });     // continuous play, round the album
  a.addEventListener('timeupdate', () => {
    if (k !== deck || !album) return;
    const t = album.tracks[cur];
    if (a.currentTime > 20 || a.currentTime > t.seconds * 0.5) prepare(prefs.repeat ? -1 : nextReady(cur, 1));
  });
  a.addEventListener('waiting', () => { if (k === deck) $('#stat').textContent = 'Loading…'; });
  a.addEventListener('playing', () => { if (k === deck) $('#stat').textContent = 'Playing'; });
  a.addEventListener('pause', () => { if (k === deck && isPlaying && !a.ended && !advancing) playing(false); });
  a.addEventListener('loadedmetadata', () => { if (k === deck) { posBar.redraw(); lcdDirty = true; kick(); } });
});

/* ------------------------------------------------------------------ remembering the place: back three seconds and a two-second fade-in on return; a one-second fade-out on leaving by a link */
function saveNow() {
  if (!album || !album.tracks[cur]) return;
  const a = A[deck];
  let t = a.currentTime || 0;
  if (cued && !isPlaying && cued.i === cur && Math.abs(t - cued.from) < 0.25) t = cued.t;   // reloading while paused does not creep back three seconds a time
  store.set('now', { n: album.tracks[cur].n, t: Math.round(t * 10) / 10, playing: isPlaying && !a.paused, at: Date.now() });
}
setInterval(() => { if (isPlaying) saveNow(); }, 1000);
addEventListener('pagehide', saveNow);
document.addEventListener('visibilitychange', () => { if (document.hidden) saveNow(); });
A.forEach((a) => a.addEventListener('seeked', () => { if (a === A[deck]) saveNow(); }));
function fadeTo(target, secs, cb) {   // an equal-power curve on the fader, ahead of the volume
  if (!ac || !fader) { if (cb) setTimeout(cb, secs * 1000); return; }
  const g = fader.gain, now = ac.currentTime, from = g.value, N = 64, curve = new Float32Array(N);
  for (let i = 0; i < N; i++) { const x = i / (N - 1); curve[i] = target > from ? from + (target - from) * Math.sin(x * Math.PI / 2) : target + (from - target) * Math.cos(x * Math.PI / 2); }
  g.cancelScheduledValues(now);
  try { g.setValueCurveAtTime(curve, now, secs); } catch (e) { g.value = target; }
  if (cb) setTimeout(cb, secs * 1000 + 40);
}
function unfade() { if (fader) { fader.gain.cancelScheduledValues(0); fader.gain.value = 1; } }
let cued = null;
function cue(i, from, t) {   // the track in the deck, paused at a place
  cued = { i, from, t: t == null ? from : t };
  webaudio();   // the graph must exist before the deck loads, or Chrome's element stalls once it is routed later
  const a = A[deck];
  a.src = src(album.tracks[i]); a.preload = 'auto'; loadedNext = -1;
  const go = () => { try { a.currentTime = from; } catch (e) { /* not yet */ } evSnap = true; kick(); };
  if (a.readyState >= 1) go(); else a.addEventListener('loadedmetadata', go, { once: true });
  try { a.currentTime = from; } catch (e) { /* before metadata */ }
  stopped = false; playing(false);
}
function resumeAt(from) {
  webaudio(); if (ac && ac.state !== 'running') ac.resume().catch(() => {});
  if (fader) { fader.gain.cancelScheduledValues(0); fader.gain.value = 0; }
  const a = A[deck];
  if (!a.src) a.src = src(T());
  try { a.currentTime = from; } catch (e) { /* before metadata: the default start position */ }
  stopped = false; advancing = false;
  a.play().then(() => fadeTo(1, 2)).catch(() => unfade());
  playing(true);
}
async function comeBack(r) {
  cue(cur, r.from, r.t);
  if (!r.playing) return;
  // try to carry on unasked; most browsers want a click or a key first
  webaudio();
  let ok = false;
  try {
    if (fader) fader.gain.value = 0;
    await A[deck].play();
    if (ac && ac.state !== 'running') await Promise.race([ac.resume(), new Promise((res) => setTimeout(res, 500))]);
    ok = !ac || ac.state === 'running';
  } catch (e) { ok = false; }
  if (ok) { stopped = false; playing(true); fadeTo(1, 2); return; }
  A[deck].pause(); unfade(); playing(false);
  askResume(r.from);
}
function askResume(from) {
  const t = T();
  $('#resumetext').textContent = `Resume Track ${String(t.n).padStart(2, '0')} at ${fmt(from).replace(/^0/, '')}?`;
  if (!resIcon) resIcon = view($('#resicon'), (v) => paintIcon(v, 'player'));
  openDialog('resume');
  const done = () => { closeDialog('resume'); removeEventListener('pointerdown', onPtr, true); removeEventListener('keydown', onKey, true); };
  const go = () => { done(); resumeAt(from); };
  // OK, Enter or Space, or a click on the night itself resumes; a click on a control means the listener wants something else
  const onPtr = (e) => {
    if (e.target.closest('#rcancel')) { done(); return; }
    if (e.target.closest('#rok') || !e.target.closest('button, a, li, input, label, canvas[role=slider], .dd, .sb, .hsb, .tb, .vp')) { e.preventDefault(); go(); }
    else done();
  };
  const onKey = (e) => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(); return; }
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); go(); return; }
    if (!['Shift', 'Control', 'Alt', 'Meta', 'Tab'].includes(e.key)) done();
  };
  addEventListener('pointerdown', onPtr, true); addEventListener('keydown', onKey, true);
}
let resIcon = null, leaving = false;
document.addEventListener('click', (e) => {   // leaving by a link: a one-second fade, then go
  const l = e.target.closest('a[href]');
  if (!l || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  if (l.hasAttribute('download') || (l.target && l.target !== '_self') || !isPlaying || !fader || leaving) return;
  const u = new URL(l.href, location.href);
  if (u.origin === location.origin && u.pathname === location.pathname && u.hash) return;
  e.preventDefault(); leaving = true; saveNow();
  fadeTo(0, 1, () => { location.href = l.href; });
});
addEventListener('pageshow', (e) => {   // back from the page the link led to (the back/forward cache): carry on, faded in
  if (!e.persisted || !leaving) return;
  leaving = false;
  const a = A[deck]; resumeAt(Math.max(0, (a.currentTime || 0) - 3));
});

/* ------------------------------------------------------------------ the transport */
const posBar = trackbar($('#pos'), {
  ticks() {
    const t = T(); if (!t) return [];
    const dur = durOf(A[deck]) || 1, out = [];
    for (let s = 0; s <= dur + 0.01; s += 10) out.push({ at: s / dur, major: s % 60 === 0, label: s % 60 === 0 ? (s / 60) + ':00' : (s % 30 === 0 && dur < 200 ? fmt(s).slice(1) : '') });
    return out;
  },
  step: 0.02,
  text: (v) => fmt(v * durOf(A[deck])),
  input() { lcdDirty = true; kick(); },
  change(v) { const a = A[deck]; if (a.src && durOf(a)) { a.currentTime = v * durOf(a); evSnap = true; } else if (!a.src) play(cur, v * (T().seconds || 0)); kick(); },
});
const volBar = trackbar($('#vol'), {
  small: true, step: 0.05,
  ticks() { const o = []; for (let i = 0; i <= 10; i++) o.push({ at: i / 10, major: i % 5 === 0 }); return o; },
  text: (v) => Math.round(v * 100) + '%',
  input(v) { setVol(v * 100, false); }, change(v) { setVol(v * 100); },
});
setVol(prefs.vol, false);
$('#play').onclick = toggle; $('#stop').onclick = stop;
$('#next').onclick = () => step(1);
$('#prev').onclick = () => { const a = A[deck]; if (a.currentTime > 4) { a.currentTime = 0; evSnap = true; } else step(-1); };
$('#rplay').onclick = () => { if (A[deck].paused) toggle(); };
$('#rstop').onclick = () => { if (!A[deck].paused) toggle(); };
$('#rrew').onclick = () => { const a = A[deck]; if (a.src) { a.currentTime = 0; evSnap = true; kick(); } };
$('#rff').onclick = () => step(1);
$('#rrec').onclick = () => { $('#stat').textContent = 'Sound Recorder is in playback mode.'; };
// the Sound Recorder's scroll bar seeks too
(() => {
  const hsb = $('#rscroll'), tr = $('.tr', hsb);
  const seek = (e) => { const a = A[deck], r = tr.getBoundingClientRect(); if (durOf(a)) { a.currentTime = clamp(((e.clientX - r.left) / S - 8) / (r.width / S - 17), 0, 1) * durOf(a); evSnap = true; kick(); } };
  tr.addEventListener('pointerdown', (e) => { e.preventDefault(); tr.setPointerCapture(e.pointerId); seek(e); const mv = (ev) => seek(ev); tr.addEventListener('pointermove', mv); tr.addEventListener('pointerup', () => tr.removeEventListener('pointermove', mv), { once: true }); });
  $('.ar.l', hsb).onclick = () => { const a = A[deck]; a.currentTime = Math.max(0, a.currentTime - 5); evSnap = true; kick(); };
  $('.ar.r', hsb).onclick = () => { const a = A[deck]; if (durOf(a)) a.currentTime = Math.min(durOf(a) - 0.5, a.currentTime + 5); evSnap = true; kick(); };
})();

/* ------------------------------------------------------------------ the menus of the Media Player */
const menus = {
  file() {
    const t = T();
    return [
      { label: 'Save Track as MP3…', href: t && !t.pending ? t.mp3 : undefined, download: t ? `CITYPOP DEPROGRAMMED ${String(t.n).padStart(2, '0')} ${t.title.replace(/[:/\\?*"<>|]/g, '')}.mp3` : '', disabled: !t || t.pending },
      { label: 'Cover Art (640 px)', href: 'art/cover-640.png', blank: true },
      { label: 'SOURCES.TXT', href: 'SOURCES.TXT', blank: true },
      '-', { label: 'SNDWAVE2000 Home', href: '/sndwave2000/' },
    ];
  },
  device() {
    return [
      { label: '<u>C</u>ontinuous Play', checked: !prefs.repeat, action: () => { prefs.repeat = false; savePrefs(); } },
      { label: '<u>R</u>epeat Track', checked: prefs.repeat, action: () => { prefs.repeat = true; savePrefs(); loadedNext = -1; } },
      '-', { label: '<u>D</u>esktop…', action: openDesktop },
      { label: '<u>H</u>ide Windows', key: 'H', action: watch },
    ];
  },
  help() { return [{ label: '<u>K</u>eys…', action: openAbout }, { label: '<u>A</u>bout Media Player…', action: openAbout }]; },
};
$$('#player .menu [data-menu]').forEach((b) => { b.onclick = () => openMenu(b, menus[b.dataset.menu]()); });

/* ------------------------------------------------------------------ hide the windows: the night alone */
let idleT = 0;
function watch() {
  closeMenu();
  const on = document.body.classList.toggle('watch');
  $('#unhide').hidden = !on;
  if (on) $('#unhide').focus(); else $('#hide').focus();
  occlude(); driveLife(); kick();
}
$('#hide').onclick = watch; $('#unhide').onclick = watch;
addEventListener('pointermove', () => {
  if (!document.body.classList.contains('watch')) return;
  document.body.classList.remove('idle'); clearTimeout(idleT); idleT = setTimeout(() => document.body.classList.add('idle'), 2600);
}, { passive: true });

/* ------------------------------------------------------------------ dialogs: Desktop (time of night) and About */
let dlgSaved = null;
function openDialog(id) {
  const o = W[id]; o.el.hidden = false; o.min = false;
  if (wm) place(id, { x: null, y: null, w: o.w || (id === 'desktop' ? 300 : 320) });
  focusWin(id); icons();
  const f = $('.push.def', o.el); if (f) f.focus();
}
function closeDialog(id) { W[id].el.hidden = true; icons(); }
function openDesktop() {
  dlgSaved = { tod: prefs.tod, motion: prefs.motion, remember: prefs.remember, scale: prefs.scale };
  $$('#desktop input[name=scale]').forEach((r) => { r.checked = r.value === String(prefs.scale); });
  $$('#desktop input[name=tod]').forEach((r) => { r.checked = r.value === String(prefs.tod); });
  $('#optmotion').checked = prefs.motion; $('#optremember').checked = prefs.remember;
  openDialog('desktop');
}
function openAbout() { openDialog('about'); }
$$('#desktop input[name=tod]').forEach((r) => { r.onchange = () => { prefs.tod = r.value; pushTime(true); }; });
$('#optmotion').onchange = (e) => { prefs.motion = e.target.checked; applyMotion(); };
$$('#desktop input[name=scale]').forEach((r) => { r.onchange = () => { prefs.scale = r.value; layout(false); focusWin('desktop'); place('desktop', { x: null, y: null }); }; });
$('#optremember').onchange = (e) => { prefs.remember = e.target.checked; };
$('#optreset').onclick = () => { store.del('layout'); layout(true); };
$('#dok').onclick = () => { savePrefs(); if (prefs.remember) saveLayout(); else store.del('layout'); closeDialog('desktop'); };
$('#dcancel').onclick = () => { const sc = prefs.scale !== dlgSaved.scale; Object.assign(prefs, dlgSaved); applyMotion(); pushTime(true); closeDialog('desktop'); if (sc) layout(false); };
$('#aok').onclick = () => closeDialog('about');

/* ------------------------------------------------------------------ keys */
addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) { if (e.altKey && e.key === 'F4') { /* let the browser have it */ } return; }
  const tag = e.target.tagName, onSlider = e.target.getAttribute && e.target.getAttribute('role') === 'slider';
  if (tag === 'INPUT' && e.target.type !== 'radio' && e.target.type !== 'checkbox') return;
  const a = A[deck], k = e.key;
  if (k === 'Escape') {
    if (openDD) return;
    if (!W.desktop.el.hidden) { $('#dcancel').onclick(); return; }
    if (!W.about.el.hidden) { closeDialog('about'); return; }
    if (document.body.classList.contains('watch')) watch();
    return;
  }
  if (k === ' ' || k === 'k') { if (tag === 'BUTTON' && k === ' ') return; e.preventDefault(); toggle(); }
  else if (k === 'n' || k === 'N') step(1);
  else if (k === 'p' || k === 'P') step(-1);
  else if (k === 's' || k === 'S') stop();
  else if (k === 'h' || k === 'H') watch();
  else if (onSlider) return;
  else if (k === 'ArrowRight' && !e.target.closest('.list')) { if (durOf(a)) { a.currentTime = Math.min(durOf(a) - 0.5, a.currentTime + 10); evSnap = true; kick(); } }
  else if (k === 'ArrowLeft' && !e.target.closest('.list')) { a.currentTime = Math.max(0, a.currentTime - 10); evSnap = true; kick(); }
  else if (k === 'ArrowUp' && !e.target.closest('.list, .vp')) { e.preventDefault(); setVol(prefs.vol + 5); }
  else if (k === 'ArrowDown' && !e.target.closest('.list, .vp')) { e.preventDefault(); setVol(prefs.vol - 5); }
  else { const n = '1234567890-='.indexOf(k); if (n >= 0 && album && n < album.tracks.length) play(n); }
});
if ('mediaSession' in navigator) {
  try {
    navigator.mediaSession.setActionHandler('play', () => { if (A[deck].paused) toggle(); });
    navigator.mediaSession.setActionHandler('pause', () => { if (!A[deck].paused) toggle(); });
    navigator.mediaSession.setActionHandler('nexttrack', () => step(1));
    navigator.mediaSession.setActionHandler('previoustrack', () => step(-1));
  } catch (e) { /* unsupported action */ }
}

/* ================================================================== the LCD: seven segments, ghosts of the unlit ones */
const SEG = { 0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc', 5: 'afgcd', 6: 'afgedc', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg', '-': 'g', ' ': '' };
function seg7(c, x, y, dw, dh, t, ch, on, ghost) {
  const hh = (dh - t) >> 1, S = {
    a: [x + 1, y, dw - 2, t], d: [x + 1, y + dh - t, dw - 2, t], g: [x + 1, y + hh, dw - 2, t],
    f: [x, y + 1, t, hh], b: [x + dw - t, y + 1, t, hh], e: [x, y + hh + t - 1, t, dh - hh - t], c: [x + dw - t, y + hh + t - 1, t, dh - hh - t],
  };
  const lit = SEG[ch] || '';
  for (const s in S) {
    const [sx, sy, sw, sh] = S[s], isOn = lit.includes(s);
    c.fillStyle = isOn ? on : ghost;
    // a segment with its ends bevelled off: three stacked rectangles, whole device pixels
    if (sw > sh) { c.fillRect(sx + 1, sy, sw - 2, sh); c.fillRect(sx, sy + 1, sw, sh - 2); }
    else { c.fillRect(sx, sy + 1, sw, sh - 2); c.fillRect(sx + 1, sy, sw - 2, sh); }
  }
}
let lcdDirty = true, lcdSig = '';
const lcd = view($('#lcd'), (v) => { lcdSig = ''; drawLCD(v); });
function drawLCD(v) {
  if (!v.w) return;
  const t = T(), a = A[deck];
  const pos = posBar.drag ? posBar.v * durOf(a) : (a.currentTime || 0);
  const sig = [Math.floor(pos), cur, isPlaying, stopped, v.w, t && t.pending, album ? 1 : 0, fontsOK].join('|');
  if (sig === lcdSig) return; lcdSig = sig;
  const { ctx: c, w, h, k } = v;
  c.fillStyle = '#07060f'; c.fillRect(0, 0, w, h);
  // fine scanlines, one device pixel each, every third device row
  if (k >= 2) { c.fillStyle = 'rgba(240,214,160,.025)'; for (let y = 0; y < h; y += 3) c.fillRect(0, y, w, 1); }
  const on = '#f0d6a0', ghost = 'rgba(240,214,160,.075)';
  const dh = Math.round(24 * k), dw = Math.round(13 * k), th = Math.max(2, Math.round(2.6 * k)), gap = Math.round(4 * k);
  const y = Math.round((h - dh) / 2) + Math.round(2 * k);
  // the track number, smaller
  const sdh = Math.round(16 * k), sdw = Math.round(9 * k), sth = Math.max(2, Math.round(2 * k));
  let x = Math.round(8 * k);
  c.font = `${Math.round(8 * k)}px "CP Sans", "DejaVu Sans", sans-serif`; c.textBaseline = 'top'; c.fillStyle = 'rgba(240,214,160,.55)';
  c.fillText('TRACK', x, Math.round(4 * k));
  const tn = t ? String(t.n).padStart(2, '0') : '--';
  for (const ch of tn) { seg7(c, x, y + dh - sdh, sdw, sdh, sth, ch === '-' ? '-' : ch, on, ghost); x += sdw + Math.round(3 * k); }
  x += Math.round(10 * k);
  // the time: mm:ss
  c.fillStyle = 'rgba(240,214,160,.55)'; c.fillText(stopped && !isPlaying ? 'STOP' : isPlaying ? 'PLAY' : 'PAUSE', x, Math.round(4 * k));
  c.save();
  const ts = fmt(pos);
  for (const ch of ts) {
    if (ch === ':') {
      const s = Math.max(2, Math.round(2.6 * k)); c.fillStyle = on;
      c.fillRect(x + Math.round(1 * k), y + Math.round(dh * 0.28), s, s); c.fillRect(x + Math.round(1 * k), y + Math.round(dh * 0.68), s, s);
      x += s + Math.round(4 * k); continue;
    }
    seg7(c, x, y, dw, dh, th, ch, on, ghost); x += dw + gap;
  }
  c.restore();
  // the right column: length, tempo, key
  if (t) {
    const rx = w - Math.round(8 * k);
    c.textAlign = 'right'; c.fillStyle = 'rgba(240,214,160,.85)';
    c.font = `${Math.round(10 * k)}px "CP Mono", "DejaVu Sans Mono", monospace`;
    c.fillText('/ ' + fmt(durOf(a)), rx, Math.round(5 * k));
    c.fillStyle = 'rgba(240,214,160,.55)'; c.font = `${Math.round(9 * k)}px "CP Sans", "DejaVu Sans", sans-serif`;
    if (!t.pending) {
      c.fillText((t.bpm ? Math.round(t.bpm) + ' BPM  ' : '') + meterOf(t) + '/4', rx, Math.round(18 * k));
      c.fillText(keyShort(keyOf(t)).toUpperCase().replace('♭', '♭'), rx, Math.round(29 * k));
    } else c.fillText('MASTERING', rx, Math.round(18 * k));
    c.textAlign = 'left';
  }
}

/* ================================================================== Sound Recorder's wave */
let fbuf = null;
const wave = view($('#wave'), (v) => drawWave(v, true));
let waveFlat = false;
function drawWave(v, force) {
  if (!v.w) return;
  const { ctx: c, w, h } = v, live = an && isPlaying;
  if (!live && waveFlat && !force) return;
  c.fillStyle = '#000'; c.fillRect(0, 0, w, h);
  const mid = h >> 1;
  c.fillStyle = '#163d1e'; c.fillRect(0, mid, w, 1);
  waveFlat = !live;
  if (!live) return;
  if (!fbuf) fbuf = new Float32Array(an.fftSize);
  an.getFloatTimeDomainData(fbuf);
  const N = fbuf.length, amp = (h / 2 - 1) * 1.7;   // a little display gain: the quiet passages still draw
  for (let x = 0; x < w; x++) {
    const i0 = Math.floor(x * N / w), i1 = Math.max(i0 + 1, Math.floor((x + 1) * N / w));
    let lo = 1, hi = -1, sum = 0;
    for (let i = i0; i < i1; i++) { const s = fbuf[i]; if (s < lo) lo = s; if (s > hi) hi = s; sum += s < 0 ? -s : s; }
    const y0 = Math.round(mid - clamp(hi, -1, 1) * amp), y1 = Math.round(mid - clamp(lo, -1, 1) * amp);
    c.fillStyle = '#3c9a4a'; c.fillRect(x, Math.min(y0, mid), 1, Math.max(1, Math.max(y1, mid) - Math.min(y0, mid) + 1));
    const r = Math.round(sum / (i1 - i0) * amp);
    if (r > 0) { c.fillStyle = '#9ff0a8'; c.fillRect(x, mid - r, 1, 2 * r + 1); }
  }
}

/* ================================================================== the Event List: a tracker that scrolls with the music */
const CH = ['#9ad0ff', '#f0b0d8', '#f0d6a0', '#b8f0c0', '#d0a8ff', '#ffb89a', '#8fe0e0', '#e8e0f6', '#f8e08a', '#c0a0e0', '#a0c8a8', '#f0a0a0', '#a0b0ff', '#ffd0f0', '#d8c098', '#90d0b8'];
const NOTE = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-'];
const nn = (n) => NOTE[n % 12] + ((n / 12 | 0) - 1);
const COLX = [2, 54, 124, 206, 248, 294];   // matches the header cells (52, 70, 82, 42, 46)
let evDirty = true, evSnap = true, evDisp = 0, evLast = 0, beatIdx = -1;
const evv = view($('#evc'), () => { evDirty = true; drawEv(performance.now()); });
const evSb = $('#evsb'); evSb.innerHTML = '<span class="tr"><span class="th"></span></span>';
const evTh = $('.th', evSb), evTr = $('.tr', evSb);
const beatLeds = $$('#beats i');
new ResizeObserver((es) => { evTrH = es[0].contentRect.height; dom.evth = ''; }).observe(evTr);
// each row is typeset once into its own little bitmap; a frame is then a stack of blits
const rowCache = new Map();
let rowKey = '';
function evRow(d, i, e, bar, bt, col, w, rh, k, X, pad, base) {
  const key = d.key + '|' + w + '|' + rh + '|' + fontsOK;
  if (key !== rowKey) { rowCache.clear(); rowKey = key; }
  let r = rowCache.get(i);
  if (r) return r;
  if (rowCache.size > 400) rowCache.delete(rowCache.keys().next().value);
  r = document.createElement('canvas'); r.width = w; r.height = rh;
  const c = r.getContext('2d');
  c.font = `${Math.round(11 * k)}px "CP Mono", "DejaVu Sans Mono", monospace`; c.textBaseline = 'alphabetic';
  c.fillStyle = bt === 1 ? '#d8d0f0' : '#7d71a8';
  c.fillText(String(bar).padStart(3, '0') + ':' + bt, X[0] + pad, base);
  const tt = e[0] / 1000;
  c.fillStyle = '#8f84b6';
  c.fillText(String((tt / 60) | 0).padStart(2, '0') + ':' + (tt % 60).toFixed(3).padStart(6, '0'), X[1] + pad, base);
  c.fillStyle = col; c.fillRect(X[2] + pad, Math.round(3 * k), Math.round(3 * k), rh - Math.round(6 * k));
  c.fillText(d.parts[e[1]].slice(0, 8), X[2] + pad + Math.round(7 * k), base);
  c.fillStyle = '#e9e2f7'; c.fillText(nn(e[2]), X[3] + pad, base);
  c.fillStyle = '#a99dcb'; c.fillText(String(e[3]).padStart(3), X[4] + pad, base);
  const vb = Math.round(e[3] / 127 * 14 * k), vx = X[4] + pad + Math.round(22 * k), vy = Math.round(6 * k), vh = Math.max(2, Math.round(3 * k));
  c.fillStyle = '#3a3360'; c.fillRect(vx, vy, Math.round(14 * k), vh);
  c.fillStyle = col; c.fillRect(vx, vy, vb, vh);
  c.fillStyle = '#8f84b6'; c.fillText((e[4] / 1000).toFixed(2).padStart(5), X[5] + pad, base);
  rowCache.set(i, r);
  return r;
}
function lowerBound(ev, ms) { let lo = 0, hi = ev.length; while (lo < hi) { const m = (lo + hi) >> 1; if (ev[m][0] <= ms) lo = m + 1; else hi = m; } return lo; }
function evStatus() {
  const d = evdata[cur];
  $('#evstat').textContent = d && d.ev ? `${d.ev.length.toLocaleString('en')} events, ${d.parts.length} parts` : T() && T().pending ? 'In the mastering room' : 'No events';
}
let leadT = 0;
function leadPart(d, ms) {   // the part carrying the tune just now: the busiest pitched voice of the last four seconds
  const lo = lowerBound(d.ev, ms - 4000), hi = lowerBound(d.ev, ms), score = {};
  for (let i = lo; i < hi; i++) { const e = d.ev[i], p = d.parts[e[1]]; if (/^(kit|perc|rain|vinyl|room|street|cafe|spoon|steam|train|city|fx|noise)/.test(p) || e[2] < 55 || e[4] > 6000) continue; score[p] = (score[p] || 0) + 1 + e[2] / 128; }
  let best = '', bs = 0; for (const p in score) if (score[p] > bs) { bs = score[p]; best = p; }
  return best;
}
function drawEv(now) {
  const v = evv; if (!v.w) return;
  const d = evdata[cur], t = T(), a = A[deck];
  const ms = (a.currentTime || 0) * 1000;
  const { ctx: c, w, h, k } = v, rh = Math.round(15 * k), one = 1;
  const dt = Math.min(0.25, (now - evLast) / 1000); evLast = now;
  if (!d || !d.ev) {
    if (!evDirty) return; evDirty = false;
    c.fillStyle = '#08070f'; c.fillRect(0, 0, w, h);
    c.font = `${Math.round(11 * k)}px "CP Mono", "DejaVu Sans Mono", monospace`; c.fillStyle = '#6c6294'; c.textBaseline = 'alphabetic';
    c.fillText(t && t.pending ? '(in the mastering room)' : d === 'loading' ? 'Loading…' : '(press Play)', Math.round(8 * k), Math.round(18 * k));
    return;
  }
  const ev = d.ev, lo = lowerBound(ev, ms);
  let target;
  if (lo <= 0) target = -1 + (ev.length ? clamp(ms / Math.max(1, ev[0][0]), 0, 1) : 0);
  else if (lo >= ev.length) target = ev.length - 1;
  else target = lo - 1 + clamp((ms - ev[lo - 1][0]) / Math.max(1, ev[lo][0] - ev[lo - 1][0]), 0, 1);
  if (evSnap || Math.abs(target - evDisp) > 60 || reduced()) { evDisp = target; evSnap = false; }
  else evDisp += (target - evDisp) * (1 - Math.exp(-dt * 12));
  const bpm = (t && t.bpm) || 120, beatMs = 60000 / bpm, meter = meterOf(t || {});
  const bNow = Math.floor(ms / beatMs);
  c.fillStyle = '#08070f'; c.fillRect(0, 0, w, h);
  const y0 = Math.round(h * 0.62);               // the now line
  const first = Math.floor(evDisp - y0 / rh) - 1, last = Math.ceil(evDisp + (h - y0) / rh) + 1;
  const fs = Math.round(11 * k);
  c.font = `${fs}px "CP Mono", "DejaVu Sans Mono", monospace`; c.textBaseline = 'alphabetic';
  const X = COLX.map((x) => Math.round(x * k)), pad = Math.round(4 * k), base = Math.round(11 * k);
  let prevBar = null;
  for (let i = Math.max(0, first); i <= Math.min(ev.length - 1, last); i++) {
    const e = ev[i], y = Math.round(y0 + (i - evDisp) * rh) - rh;
    const b = Math.floor(e[0] / beatMs), bar = Math.floor(b / meter) + 1, bt = (b % meter) + 1;
    const past = e[0] <= ms;
    if (b === bNow && past) { c.fillStyle = 'rgba(140,52,120,.20)'; c.fillRect(0, y, w, rh); }
    if (prevBar !== null && bar !== prevBar) { c.fillStyle = '#2a2448'; c.fillRect(0, y, w, one); }
    prevBar = bar;
    const age = ms - e[0];
    const col = CH[e[1] % CH.length];
    c.globalAlpha = past ? (age < 140 ? 1 : 0.86) : 0.38;
    c.drawImage(evRow(d, i, e, bar, bt, col, w, rh, k, X, pad, base), 0, y);
    // a note that is still sounding keeps a thin light under its row
    if (past && age < e[4]) { c.fillStyle = col; c.globalAlpha = 0.5; c.fillRect(X[1], y + rh - one, Math.round((1 - age / e[4]) * (w - X[1])), one); }
    c.globalAlpha = 1;
  }
  // the now line and the columns
  c.fillStyle = 'rgba(240,214,160,.55)'; c.fillRect(0, y0, w, one);
  c.fillStyle = 'rgba(240,214,160,.10)'; c.fillRect(0, y0 - rh, w, rh);
  c.fillStyle = '#15122a'; for (let j = 1; j < X.length; j++) c.fillRect(X[j], 0, one, h);
  // the static scroll bar: where in the song we are
  const dur = durOf(a) || 1, span = evTrH - 16;
  const tp = snap(clamp(ms / 1000 / dur, 0, 1) * Math.max(0, span)) + 'px';
  if (tp !== dom.evth) { dom.evth = tp; evTh.style.top = tp; }
  // the four (or three) beat lights
  if (bNow !== beatIdx) {
    beatIdx = bNow;
    const bi = isPlaying ? bNow % meter : -1;
    beatLeds.forEach((el, j) => { el.style.display = j < meter ? '' : 'none'; el.classList.toggle('on', j === bi); el.classList.toggle('one', j === 0); });
    if (isPlaying && lifeCtl && lifeCtl.onBeat) try { lifeCtl.onBeat(bi, meter); } catch (e) { /* optional */ }
  }
  if (now - leadT > 1000) { leadT = now; const p = leadPart(d, ms); $('#evpart').textContent = p ? 'Lead: ' + p : ''; }
  evDirty = false;
}

/* ================================================================== the Clock, as Windows 3.1 drew it, at device resolution */
const clk = view($('#clk'), (v) => drawClock(v));
function drawClock(v) {
  if (!v.w) return;
  const { ctx: c, w, h, k } = v, now = new Date();
  const cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - Math.round(8 * k);
  c.fillStyle = '#131127'; c.fillRect(0, 0, w, h);
  // the faint face
  const g = c.createRadialGradient(cx, cy - R * 0.3, R * 0.1, cx, cy, R * 1.1); g.addColorStop(0, 'rgba(75,36,114,.30)'); g.addColorStop(1, 'rgba(75,36,114,0)');
  c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R * 1.05, 0, Math.PI * 2); c.fill();
  const L = Math.max(1, Math.round(k));
  for (let i = 0; i < 60; i++) {
    const an = i / 60 * Math.PI * 2, x = Math.round(cx + Math.sin(an) * R), y = Math.round(cy - Math.cos(an) * R);
    if (i % 5) { c.fillStyle = '#6c6294'; c.fillRect(x - (L >> 1), y - (L >> 1), L, L); continue; }
    // the hour marks are little raised squares, as on the Windows 3.1 clock
    const s = Math.round((i % 15 ? 4 : 5) * k) | 1, x0 = x - (s >> 1), y0 = y - (s >> 1);
    c.fillStyle = '#000'; c.fillRect(x0 - 1, y0 - 1, s + 2, s + 2);
    c.fillStyle = i === 0 ? '#8c3478' : '#4b4275'; c.fillRect(x0, y0, s, s);
    c.fillStyle = i === 0 ? '#f0a0c8' : '#a99dcb'; c.fillRect(x0, y0, s, 1); c.fillRect(x0, y0, 1, s);
    c.fillStyle = '#0e0b20'; c.fillRect(x0, y0 + s - 1, s, 1); c.fillRect(x0 + s - 1, y0, 1, s);
  }
  const hand = (frac, len, back, wid, fill) => {
    const an = frac * Math.PI * 2, sx = Math.sin(an), cy2 = -Math.cos(an), px = -cy2, py = sx;
    c.beginPath();
    c.moveTo(cx + sx * len, cy + cy2 * len);
    c.lineTo(cx + px * wid + sx * len * 0.18, cy + py * wid + cy2 * len * 0.18);
    c.lineTo(cx - sx * back, cy - cy2 * back);
    c.lineTo(cx - px * wid + sx * len * 0.18, cy - py * wid + cy2 * len * 0.18);
    c.closePath();
    c.fillStyle = fill; c.fill(); c.lineWidth = 1; c.strokeStyle = '#000'; c.stroke();
  };
  const hr = now.getHours() % 12, mi = now.getMinutes(), se = now.getSeconds();
  hand((hr + mi / 60) / 12, R * 0.55, R * 0.1, R * 0.075, '#d8d0f0');
  hand((mi + se / 60) / 60, R * 0.82, R * 0.1, R * 0.06, '#e9e2f7');
  if (!reduced()) {
    const an = se / 60 * Math.PI * 2;
    c.strokeStyle = '#f0a0c8'; c.lineWidth = Math.max(1, Math.round(k * 0.75)); c.beginPath();
    c.moveTo(cx - Math.sin(an) * R * 0.15, cy + Math.cos(an) * R * 0.15); c.lineTo(cx + Math.sin(an) * R * 0.88, cy - Math.cos(an) * R * 0.88); c.stroke();
  }
  const s = Math.round(3 * k) | 1; c.fillStyle = '#000'; c.fillRect(Math.round(cx) - (s >> 1) - 1, Math.round(cy) - (s >> 1) - 1, s + 2, s + 2); c.fillStyle = '#f0d6a0'; c.fillRect(Math.round(cx) - (s >> 1), Math.round(cy) - (s >> 1), s, s);
  $('#clktitle').textContent = 'Clock - ' + (now.getMonth() + 1) + '/' + now.getDate();
}
function clockLoop() {
  if (!document.hidden && !loopOn && !W.clock.min && !document.body.classList.contains('watch')) drawClock(clk);   // while playing, the frame loop draws it
  setTimeout(clockLoop, 1000 - (Date.now() % 1000) + 5);
}

/* ================================================================== the frame loop: ~30 fps while playing, nothing while paused or hidden */
const inView = { ev: true, rec: true };
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((es) => { for (const e of es) inView[e.target.id] = e.isIntersecting; kick(); });
  io.observe(W.ev.el); io.observe(W.rec.el);
}
// only the tracker and the wave need ~6 frames a second, and only while one of them can be seen
const busy = () => !document.body.classList.contains('watch') && ((!W.ev.min && inView.ev) || (!W.rec.min && inView.rec));
let loopOn = false, lastSec = 0, lastPush = 0, rTrW = 0, evTrH = 0;
const FR = +(new URLSearchParams(location.search).get('fr') || 166);   // ms between frames: every compositor frame costs, so the tracker, wave, LCD and clock share ~8 a second
const dom = {}, rposEl = $('#rpos'), rThEl = $('#rscroll .th');
new ResizeObserver((es) => { for (const e of es) { if (e.target.closest('#rscroll')) rTrW = e.contentRect.width; else evTrH = e.contentRect.height; dom.rth = dom.evth = ''; } }).observe($('#rscroll .tr'));
function kick() { if (!loopOn && !document.hidden) { loopOn = true; requestAnimationFrame(frame); } }
function frame(now) {
  loopOn = false;
  if (document.hidden || !album) return;
  const a = A[deck], live = isPlaying && !a.paused;
  // near-gapless: hand over to the waiting deck a few milliseconds before the end
  if (live && isFinite(a.duration) && a.duration - a.currentTime < 0.045 && loadedNext >= 0 && A[1 - deck].readyState >= 3) advance();
  const shown = !document.body.classList.contains('watch');
  if (shown) {
    if (!posBar.drag) { const dur = durOf(a) || 1; posBar.set((a.currentTime || 0) / dur); }
    if (!W.player.min) drawLCD(lcd);
    if (!W.rec.min) {
      drawWave(wave);
      const ps = (a.currentTime || 0).toFixed(1) + '0 sec.';
      if (ps !== dom.rpos) { dom.rpos = ps; rposEl.textContent = ps; }
      const dur = durOf(a) || 1, l = snap(clamp((a.currentTime || 0) / dur, 0, 1) * Math.max(0, rTrW - 17)) + 'px';
      if (l !== dom.rth) { dom.rth = l; rThEl.style.left = l; }
    }
    if (!W.ev.min && (live || evDirty || evSnap)) { if (evSnap) evDirty = true; drawEv(now); }
    const sec = (Date.now() / 1000) | 0;
    if (live && sec !== lastSec && !W.clock.min) { lastSec = sec; drawClock(clk); }
  } else if (live && evdata[cur] && evdata[cur].ev) {   // the night still hears the beat
    const t = T(), bpm = (t && t.bpm) || 120, b = Math.floor(a.currentTime * 1000 / (60000 / bpm));
    if (b !== beatIdx) { beatIdx = b; if (lifeCtl && lifeCtl.onBeat) try { lifeCtl.onBeat(b % meterOf(t), meterOf(t)); } catch (e) { /* optional */ } }
  }
  if (now - lastPush > 10000) { lastPush = now; pushTime(); }
  if (lifeDriven && lifeCtl) try { lifeCtl.frame(now); } catch (e) { /* optional */ }
  if (live) {
    driveLife();
    loopOn = true; setTimeout(() => requestAnimationFrame(frame), reduced() ? 500 : busy() ? FR : 1000);   // 1 fps when nothing moving is in view
  }
}
document.addEventListener('visibilitychange', () => {
  driveLife();
  if (!document.hidden) { evSnap = true; kick(); }
  if (sceneCtl) try { document.hidden ? sceneCtl.pause() : sceneCtl.resume(); } catch (e) { /* optional */ }
  if (lifeCtl && !prefs.motion) try { document.hidden ? lifeCtl.pause() : lifeCtl.resume(); } catch (e) { /* optional */ }
});
A.forEach((a) => { a.addEventListener('play', kick); a.addEventListener('seeked', () => { evSnap = true; kick(); }); });

/* ================================================================== the time of night, for the scene and life */
function todHours() {
  if (prefs.tod === 'album') {
    const n = album ? album.tracks.length : 12, a = A[deck], f = durOf(a) ? a.currentTime / durOf(a) : 0;
    return 19.5 + clamp((cur + f) / n, 0, 1) * 10;
  }
  if (prefs.tod === 'clock') { const d = new Date(); let h = d.getHours() + d.getMinutes() / 60; if (h < 12) h += 24; return clamp(h, 19.5, 29.5); }
  return +prefs.tod || 24;
}
let lastTod = -1;
function pushTime(force) {
  const h = Math.round(todHours() * 100) / 100;
  if (!force && Math.abs(h - lastTod) < 0.01) return;
  lastTod = h;
  if (sceneCtl && sceneCtl.setTime) try { sceneCtl.setTime(h); } catch (e) { /* optional */ }
  if (lifeCtl && lifeCtl.setTime) try { lifeCtl.setTime(h); } catch (e) { /* optional */ }
}
function occlude() {
  const rects = [];
  if (wm && !document.body.classList.contains('watch')) {
    for (const id of WINS) { const o = W[id]; if (o.min || o.el.hidden) continue; const r = o.el.getBoundingClientRect(); rects.push({ x: r.left, y: r.top, w: r.width, h: r.height }); }
  }
  if (lifeCtl && lifeCtl.setOccluders) try { lifeCtl.setOccluders(rects); } catch (e) { /* optional */ }
  if (sceneCtl && sceneCtl.occluders) try { sceneCtl.occluders(rects); } catch (e) { /* optional */ }
}
function applyMotion() {
  if (lifeCtl) try { prefs.motion ? lifeCtl.pause() : lifeCtl.resume(); } catch (e) { /* optional */ }
  driveLife();
  night.still = reduced();
  drawClock(clk);
}

/* ================================================================== the scene and the life in it (lazy), with the old 320 x 200 night as the fallback */
let sceneCtl = null, lifeCtl = null;
const night = { cv: $('#night'), stop: false, still: reduced() };
function loadScript(s) { return new Promise((res, rej) => { const el = document.createElement('script'); el.src = s; el.async = true; el.onload = res; el.onerror = rej; document.head.appendChild(el); }); }
async function mountModules() {
  const q = new URLSearchParams(location.search);
  if (q.has('noscene')) return;
  try { await loadScript('scene/scene.js?v=' + BUILD); } catch (e) { /* no scene module yet */ }
  const CS = window.CityScene || window.Scene;
  if (CS && CS.start) {
    try {
      sceneCtl = CS.start($('#scene'), { dpr: DPR, reduced: reduced(), time: todHours() });
      Promise.resolve(sceneCtl && sceneCtl.ready).then(() => {
        night.cv.style.opacity = '0'; setTimeout(() => { night.stop = true; night.cv.remove(); }, 1700);
      }).catch(() => {});
      occlude();
    } catch (e) { console.warn('scene', e); sceneCtl = null; }
  }
  if (q.has('nolife')) return;
  try { await loadScript('life/life.js?v=' + BUILD); } catch (e) { /* no life module yet */ }
  const CL = window.CityLife || window.Life;
  if (CL && CL.start) {
    try {
      lifeCtl = CL.start($('#life'), { dpr: DPR, reduced: reduced(), scene: sceneCtl, analyser: an2 || null, seed: (Date.now() / 86400000) | 0 });
      if (an2 && lifeCtl.setAnalyser) lifeCtl.setAnalyser(an2);
      if (prefs.motion) lifeCtl.pause();
      const t = T(); if (t && isPlaying && lifeCtl.onTrack) lifeCtl.onTrack(t.n, { bpm: t.bpm, title: t.title });
      occlude(); pushTime(true); driveLife();
    } catch (e) { console.warn('life', e); lifeCtl = null; }
  }
  pushTime(true);
}
window.cpd = { get scene() { return sceneCtl; }, get life() { return lifeCtl; }, get analyser() { return an2; }, get fader() { return fader; }, get deck() { return A[deck]; }, get playing() { return isPlaying; }, todHours };

const PAL = ['#07081a', '#0d1030', '#171a46', '#23215a', '#33226a', '#4a2470', '#6a2a74', '#8c3478', '#b0507e',
  '#2a1a1c', '#3e2824', '#5a3a2c', '#c89058', '#f0d6a0', '#d8d0f0', '#9a90c8'];
const hexToU32 = (h) => { const [r, g, b] = rgb(h); return ((255 << 24) | (b << 16) | (g << 8) | r) >>> 0; };
const PU = PAL.map(hexToU32);
async function startNight() {
  const [img, meta] = await Promise.all([
    new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = 'art/scene.png'; }),
    fetch('art/scene.json').then((r) => r.json())]);
  if (night.stop) return;
  const Wd = meta.w, Ht = meta.h;
  const off = document.createElement('canvas'); off.width = Wd; off.height = Ht;
  const oc = off.getContext('2d', { willReadFrequently: true });
  oc.drawImage(img, 0, 0);
  const base = oc.getImageData(0, 0, Wd, Ht), baseU = new Uint32Array(base.data.buffer.slice(0));
  const frameD = oc.createImageData(Wd, Ht), fu = new Uint32Array(frameD.data.buffer);
  const idx = new Uint8Array(Wd * Ht), lut = new Map(PU.map((u, i) => [u, i]));
  for (let i = 0; i < Wd * Ht; i++) idx[i] = lut.has(baseU[i] >>> 0) ? lut.get(baseU[i] >>> 0) : 0;
  const wins = meta.windows.map((w) => ({ x: w[0], y: w[1], w: w[2], h: w[3], lit: w[4], to: w[4], k: w[4] ? 1 : 0 }));
  const ripples = [];
  const ctx = night.cv.getContext('2d');
  let scale = 1, ox = 0, oy = 0;
  function fit() {
    const cw = Math.round(innerWidth * DPR), ch = Math.round(innerHeight * DPR);
    night.cv.width = cw; night.cv.height = ch; night.cv.style.width = cw / DPR + 'px'; night.cv.style.height = ch / DPR + 'px';
    scale = Math.max(1, Math.ceil(Math.max(cw / Wd, ch / Ht)));      // whole device pixels per scene pixel, covering
    ox = Math.floor((cw - Wd * scale) * (wm ? 0.75 : 0.5)); oy = Math.floor((ch - Ht * scale) * 0.62);
    ctx.imageSmoothingEnabled = false;
  }
  fit(); addEventListener('resize', fit);
  const mix = (x, y, c, a) => { if (x >= 0 && y >= 0 && x < Wd && y < Ht && a > BAY[(y & 3) * 4 + (x & 3)]) fu[y * Wd + x] = PU[c]; };
  const t0 = performance.now(); let last = 0;
  function draw(now) {
    const t = (now - t0) / 1000, dt = Math.min(0.2, t - last); last = t;
    fu.set(baseU);
    const [h0, h1] = meta.haze;
    for (let y = h0; y < h1; y++) {
      const band = Math.sin((y - h0) / (h1 - h0) * Math.PI);
      for (let x = 0; x < Wd; x++) {
        const v = 0.5 + 0.5 * Math.sin(x * 0.045 + t * 0.07 + Math.sin(y * 0.13 + t * 0.05) * 1.6);
        if (band * v * 0.16 > BAY[(y & 3) * 4 + (x & 3)]) { const i = idx[y * Wd + x]; if (i <= 6) fu[y * Wd + x] = PU[i + 1 <= 6 ? i + 1 : 15]; }
      }
    }
    for (const s of meta.stars) { const v = 0.5 + 0.5 * Math.sin(t * (0.6 + s[2] * 0.9) + s[2] * 40); if (v > 0.35) fu[s[1] * Wd + s[0]] = PU[v > 0.85 ? 14 : v > 0.6 ? 15 : 4]; }
    if (Math.random() < dt / 3.5) { const w = wins[(Math.random() * wins.length) | 0]; w.to = w.to ? 0 : 1; }
    for (const w of wins) {
      if (w.k !== w.to) w.k += Math.sign(w.to - w.k) * Math.min(Math.abs(w.to - w.k), dt / 2.5);
      if ((w.lit && w.k < 0.999) || (!w.lit && w.k > 0.001)) for (let y = w.y; y < w.y + w.h; y++) for (let x = w.x; x < w.x + w.w; x++) fu[y * Wd + x] = PU[w.k > BAY[(y & 3) * 4 + (x & 3)] ? 12 : 1];
    }
    if (!night.still && Math.random() < dt / 2.6) { const p = meta.puddles[(Math.random() * meta.puddles.length) | 0]; ripples.push({ x: p[0] + (Math.random() - 0.5) * p[2], y: p[1], rx: p[2], ry: p[3], r: 0 }); }
    for (let i = ripples.length - 1; i >= 0; i--) {
      const r = ripples[i]; r.r += dt * 5; const al = 1 - r.r / (r.rx * 0.8);
      if (al <= 0) { ripples.splice(i, 1); continue; }
      const ry = Math.max(0.6, r.r * r.ry / r.rx);
      for (let q = 0; q < 40; q++) { const th = q / 40 * Math.PI * 2, x = Math.round(r.x + Math.cos(th) * r.r), y = Math.round(r.y + Math.sin(th) * ry); const ii = idx[y * Wd + x]; if ((ii >= 2 && ii <= 6) || ii === 15) mix(x, y, 14, al * 0.8); }
    }
    oc.putImageData(frameD, 0, 0);
    ctx.drawImage(off, 0, 0, Wd, Ht, ox, oy, Wd * scale, Ht * scale);
  }
  let timer = 0;
  function loop() { if (night.stop) return; if (document.hidden) { timer = 0; return; } draw(performance.now()); timer = setTimeout(() => requestAnimationFrame(loop), night.still ? 1000 : 200); }
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !timer && !night.stop) loop(); });
  loop();
}

/* ================================================================== start */
buildIcons();
layout(false);
focusWin('player');
if (/[?&]watch\b/.test(location.search)) watch();   // a link straight to the night alone
let rsT = 0;
addEventListener('resize', () => { clearTimeout(rsT); rsT = setTimeout(() => { layout(false); if (sceneCtl && sceneCtl.resize) try { sceneCtl.resize(); } catch (e) { /* optional */ } if (lifeCtl && lifeCtl.resize) try { lifeCtl.resize(); } catch (e) { /* optional */ } }, 120); });
(function watchDPR() {
  const m = matchMedia(`(resolution: ${DPR}dppx)`);
  const on = () => { m.removeEventListener('change', on); DPR = window.devicePixelRatio || 1; paintTextures(); layout(false); redrawAll(); watchDPR(); };
  m.addEventListener('change', on);
})();
if (document.fonts) document.fonts.ready.then(() => { fontsOK = 1; redrawAll(); posBar.redraw(); volBar.redraw(); });
var fontsOK = 0;   // eslint-disable-line no-var
clockLoop();
if (!/[?&]nonight/.test(location.search)) startNight().catch(() => {});

function loadAlbum(first) {
  return fetch('album.json' + (first ? '' : '?t=' + Date.now()), { cache: first ? 'default' : 'no-store' }).then((r) => r.json()).then((d) => {
    if (!first && album) {
      // a track out of the mastering room, or a re-render: take the new list, keep what is playing
      const playingSrc = A[deck].src;
      album = d;
      if (loadedNext >= 0 && A[1 - deck].src && !A[1 - deck].src.endsWith(src(d.tracks[loadedNext]).replace(/^.*\//, ''))) loadedNext = -1;
      renderList(); show(cur);
      if (playingSrc) $$('#list li')[cur].classList.add('on');
      return;
    }
    album = d;
    renderList();
    const h = location.hash.match(/^#(\d+)/);
    let back = null;
    if (h) cur = clamp(+h[1] - 1, 0, d.tracks.length - 1);
    else {   // where the listener was when the page last closed
      const st = store.get('now', null), i = st && st.n ? d.tracks.findIndex((t) => t.n === st.n) : -1;
      if (i >= 0 && ready(i)) { cur = i; if (st.t > 0) back = { from: Math.max(0, st.t - 3), t: st.t, playing: !!st.playing }; }
    }
    if (!ready(cur)) cur = nextReady(cur, 1);
    show(cur); evStatus();
    if (back) comeBack(back);
    // the heavy art waits until the page is up and the music can play
    const go = () => mountModules();
    if ('requestIdleCallback' in window) requestIdleCallback(go, { timeout: 1200 }); else setTimeout(go, 300);
  });
}
loadAlbum(true).catch(() => { $('#ttitle').textContent = 'The track list did not load. Reload the page.'; });
setInterval(() => { if (!document.hidden && album) loadAlbum(false).then(evStatus).catch(() => {}); }, 4 * 60 * 1000);
})();

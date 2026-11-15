/* CITYPOP DEPROGRAMMED: the life in the night.
   Hundreds of small, slow, device-pixel things on overlay canvases above the scene's layers.
   One scheduler; each thing is a pure function of (seed, time, hour of night) and says when it next changes;
   only the rectangles that changed are cleared and redrawn. See LIFE-API.md. */
(() => {
'use strict';

/* ------------------------------------------------------------------ hashing: everything is f(seed, id, slot) */
let SEED = 1990;
function hash(a, b, c) {
  let h = Math.imul((a | 0) ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul((b | 0) + 0x632be59b, 0xc2b2ae35) ^ Math.imul((c | 0) + 0x27d4eb2f + SEED, 0x165667b1);
  h ^= h >>> 15; h = Math.imul(h, 0x2c1b3c6d); h ^= h >>> 12; h = Math.imul(h, 0x297a2d39); h ^= h >>> 15;
  return (h >>> 0) / 4294967296;
}
const TAU = Math.PI * 2;
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, u) => a + (b - a) * u;
const smooth = (a, b, x) => { const u = clamp((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u); };
// a smooth value noise in time, 0..1, period-free
function vnoise(id, t) { const i = Math.floor(t), f = t - i, u = f * f * (3 - 2 * f); return lerp(hash(id, i, 7), hash(id, i + 1, 7), u); }

/* an event in slot n of length P: present with probability prob, lasting dur, placed inside the slot.
   returns {on, u (0..1 through it), next (time the answer can next change)} */
function slotEv(id, T, P, prob, dur) {
  const n = Math.floor(T / P);
  if (hash(id, n, 1) < prob) {
    const t0 = n * P + hash(id, n, 2) * Math.max(0, P - dur);
    if (T < t0) return { on: false, next: t0, n };
    if (T < t0 + dur) return { on: true, u: (T - t0) / dur, t0, n, next: t0 + dur };
  }
  return { on: false, next: (n + 1) * P, n };
}

/* ------------------------------------------------------------------ colour */
const C = {
  warm: ['#f4c27a', '#eab06a', '#ffd796', '#e09a5c', '#f7cf8e'],
  warmDim: '#b47848', cool: ['#a7b8ff', '#c9d5ff', '#8d9cf2', '#b6c6ff'], pink: '#ff86c0', pinkHot: '#ffc2e0',
  moon: '#ece8ff', star: ['#f6f2ff', '#d6deff', '#ffeed6', '#e6e0ff'], red: '#ff5248', redDim: '#a8302c',
  green: '#7dffb0', amber: '#ffb648', white: '#fffaf0', dark: '#120e20', darker: '#0b0918', plum: '#5c3c7c',
  plumHi: '#8e6cb0', mist: '#b8a6d8', wet: '#c8bcf0', sodium: '#ffc070',
};
function rgba(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }

/* ------------------------------------------------------------------ sprite & glow caches (device pixels) */
const cache = new Map();
function glow(col, r, k = 1) {  // soft radial glow of radius r device px
  r = Math.max(1, Math.round(r)); const key = 'g' + col + r + k;
  let cv = cache.get(key); if (cv) return cv;
  cv = document.createElement('canvas'); cv.width = cv.height = r * 2 + 1;
  const g = cv.getContext('2d'), gr = g.createRadialGradient(r + 0.5, r + 0.5, 0, r + 0.5, r + 0.5, r);
  gr.addColorStop(0, rgba(col, 0.55 * k)); gr.addColorStop(0.35, rgba(col, 0.18 * k)); gr.addColorStop(1, rgba(col, 0));
  g.fillStyle = gr; g.fillRect(0, 0, r * 2 + 1, r * 2 + 1); cache.set(key, cv); return cv;
}
// pixel sprite from rows of chars; pal maps char -> colour; each char is u x u device px
function sprite(name, rows, pal, u) {
  const key = 's' + name + u; let cv = cache.get(key); if (cv) return cv;
  cv = document.createElement('canvas'); cv.width = rows[0].length * u; cv.height = rows.length * u;
  const g = cv.getContext('2d');
  rows.forEach((row, y) => { for (let x = 0; x < row.length; x++) { const c = pal[row[x]]; if (c) { g.fillStyle = c; g.fillRect(x * u, y * u, u, u); } } });
  cache.set(key, cv); return cv;
}
// a soft blob cloud / mist strip rendered once
function softStrip(key, w, h, col, a, seed, lumps) {
  const k = 'm' + key + w + 'x' + h; let cv = cache.get(k); if (cv) return cv;
  cv = document.createElement('canvas'); cv.width = w; cv.height = h; const g = cv.getContext('2d');
  for (let i = 0; i < lumps; i++) {
    const x = hash(seed, i, 31) * w, y = h * (0.3 + 0.4 * hash(seed, i, 32)), rx = w * (0.06 + 0.16 * hash(seed, i, 33)), ry = h * (0.18 + 0.3 * hash(seed, i, 34));
    const gr = g.createRadialGradient(x, y, 0, x, y, rx);
    gr.addColorStop(0, rgba(col, a)); gr.addColorStop(1, rgba(col, 0));
    g.save(); g.translate(x, y); g.scale(1, ry / rx); g.translate(-x, -y); g.fillStyle = gr; g.beginPath(); g.arc(x, y, rx, 0, TAU); g.fill(); g.restore();
  }
  // fade the strip's ends
  g.globalCompositeOperation = 'destination-in';
  const e = g.createLinearGradient(0, 0, w, 0); e.addColorStop(0, 'rgba(0,0,0,0)'); e.addColorStop(0.15, '#000'); e.addColorStop(0.85, '#000'); e.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = e; g.fillRect(0, 0, w, h);
  const v = g.createLinearGradient(0, 0, 0, h); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(0.35, '#000'); v.addColorStop(0.65, '#000'); v.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = v; g.fillRect(0, 0, w, h);
  cache.set(k, cv); return cv;
}

/* ------------------------------------------------------------------ sprites (original pixel art) */
const SPR = {
  catSleep: ['............', '............', '..h.h.......', '.kkkhhhhh...', 'kkkkkkkkkkkk', '.kkkkkkkkkkk'],
  catBreath: ['............', '............', '..h.h.......', '.kkkhhhhhh..', 'kkkkkkkkkkkk', '.kkkkkkkkkkk'],
  catUp: ['.h.h........', '.kkk........', '.eke........', '.kkkkhhhh...', 'kkkkkkkkkkk.', '.kkkkkkkkkkk'],
  catUpBlink: ['.h.h........', '.kkk........', '.kkk........', '.kkkkhhhh...', 'kkkkkkkkkkk.', '.kkkkkkkkkkk'],
  catStretch: ['............', '............', 'h.h.........', 'kkk.....hhh.', 'ekkkkkkkkkkk', 'k.k.kkkk.k.k'],
  catTail: ['.h.h.......k', '.kkk......k.', '.eke.......', '.kkkkhhhh...', 'kkkkkkkkkkk.', '.kkkkkkkkkk.'],
  walkA: ['...qqq...', '.ppppppp.', 'ppppppppp', '....s....', '....s....', '...kkk...', '..kkkk...', '...kkk...', '...kkk...', '...k.k...', '..k...k..'],
  walkB: ['...qqq...', '.ppppppp.', 'ppppppppp', '....s....', '....s....', '...kkk...', '...kkkk..', '...kkk...', '...kkk...', '...kk....', '...k.k...'],
  lantern: ['..b..', '.bbb.', 'rwwwr', 'rwywr', 'rwywr', 'rwwwr', '.rrr.', '..b..'],
  boat: ['....m.....', '....k.....', '...kkk....', 'kkkkkkkkkk', '.kkkkkkkk.'],
  ferry: ['..........kkkkkkkk..........', '...kkkkkkwkwkwkwkwkkkkkk....', 'kkkwkwkwkwkwkwkwkwkwkwkwkkkk', '.kkkkkkkkkkkkkkkkkkkkkkkkkk.'],
  bird1: ['k...k', '.k.k.', '..k..'], bird2: ['.....', 'kk.kk', '..k..'],
  furin: ['.s.', 'ggg', 'g.g', '.p.', '.p.'],
  scooter: ['.kk..', 'kkkkk', 'k...k'],
};
const SPAL = {
  cat: { k: '#151020', h: '#4a3c68', e: '#c8e870' },
  walk: { p: '#4c3068', q: '#7a5aa0', k: '#1a1424', s: '#2a2034' },
  lantern: { b: '#2a1a1c', r: '#b4482c', w: '#ffaa58', y: '#ffe2a6' },
  boat: { k: '#0e0c1a', m: '#ffe0a0' }, ferry: { k: '#100e1e', w: '#ffd890' },
  bird: { k: '#2a2238' }, furin: { s: '#3a3048', g: '#bfe4ff', p: '#e8a0b8' }, scooter: { k: '#141020' },
};

/* ------------------------------------------------------------------ the old 320x200 scene, as a scene2-style anchor map */
function adaptOld(m) {
  const S = (i, k) => hash(4242, i, k);
  const L = 'mid';
  const a = {
    w: m.w, h: m.h, design: 320,
    windowDark: '#0d1030',
    windows: m.windows.map((w, i) => ({ x: w[0], y: w[1], w: w[2], h: w[3], lit: w[4], baked: w[4], layer: L,
      room: S(i, 1) < 0.14 ? 'tv' : S(i, 1) < 0.24 ? 'desk' : 'plain', curtain: S(i, 2) < 0.3 ? 1 : 0, hue: S(i, 3) < 0.05 ? 'pink' : 'warm' })),
    stars: { regions: [{ x: 0, y: 0, w: 320, h: 58 }], points: m.stars.map((s) => [s[0], s[1], s[2]]) },
    moon: { x: m.moon[0], y: m.moon[1], r: m.moon[2], halo: m.moon[2] * 2.6 },
    bridge: { lights: m.lamps.map((l) => [l[0], l[1]]), towers: [[55, 79], [130, 79]], deck: [20, 92, 162], layer: 'far' },
    water: [{ x: 0, y: m.water[0], w: 320, h: m.water[1] - m.water[0] }], moonPath: { x: m.moon[0], y0: m.water[0] + 1, y1: m.water[1] - 1, w: 16 },
    train: { path: [[-30, m.rail], [350, m.rail]], layer: L },
    boats: [{ path: [[340, 113], [-20, 115]] }, { path: [[-20, 119], [340, 118]] }], ferry: { path: [[-40, 121], [360, 120]] },
    far: [[170, 96], [182, 94], [196, 97], [238, 95], [251, 97], [262, 96], [290, 98], [301, 97], [313, 99], [8, 97], [150, 98], [226, 96], [276, 97]],
    lighthouse: { x: 316, y: 98 }, antenna: { x: 268, y: 86 }, buoys: [{ x: 95, y: 117, c: 'g' }, { x: 248, y: 115, c: 'r' }],
    signal: { x: 300, y: 99 }, fisher: { x: 150, y: 111 },
    puddles: m.puddles.map((p) => ({ x: p[0] - p[2] / 2, y: p[1] - p[3] / 2, w: p[2], h: p[3], src: [], layer: 'near' })),
    lamps: [{ x: m.streetlamp[0], y: m.streetlamp[1], r: 7, kind: 'street', layer: L }, { x: 291, y: 160, r: 3, kind: 'porch', layer: L }, { x: 22, y: 150, r: 3, kind: 'porch', layer: L }],
    signs: m.signs.map((s) => ({ x: s[0], y: s[1], w: s[2], h: s[3], layer: L })),
    vending: { x: 302, y: 182, w: 5, h: 8, layer: 'near' }, shop: { x: 228, y: 189, w: 18, h: 7, layer: 'near' },
    shrine: { x: 44, y: 116, hang: [44, 113] }, cat: { x: 236, y: 125, w: 8, h: 4, layer: L },
    bikes: [{ x: 214, y: 186, w: 5, h: 3 }, { x: 108, y: 188, w: 5, h: 3 }],
    bench: { x: 196, y: 192, w: 9, h: 2, layer: 'near' }, crossing: { x: 128, y: 120 }, ped: { x: 120, y: 182 },
    laundry: [{ x: 252, y: 150, w: 10, h: 3, layer: L }, { x: 60, y: 160, w: 8, h: 3, layer: L }],
    vents: [{ x: 270, y: 129 }, { x: 28, y: 131 }, { x: 120, y: 140 }],
    ac: [[60, 142], [120, 150], [256, 160], [300, 140], [16, 170], [86, 181], [276, 178]].map((p) => ({ x: p[0], y: p[1] })),
    eaves: [{ x0: 112, x1: 130, y: 160 }, { x0: 182, x1: 205, y: 172 }, { x0: 100, x1: 128, y: 186 }],
    drips: [{ x: 132, y: 150 }, { x: 186, y: 162 }, { x: 118, y: 178 }],
    wires: [{ pts: [[0, 60], [80, 63], [160, 72], [240, 73], [320, 72]] }, { pts: [[0, 66], [100, 69], [160, 80], [240, 82], [320, 82]] }],
    furin: [{ x: 207, y: 168 }], phone: [{ x: 258, y: 168 }, { x: 34, y: 150 }],
    stairs: [{ pts: [[159, 130], [160, 200]], w0: 40, w1: 110 }],
    streets: [{ pts: [[330, 124], [-10, 124]] }],
    regions: { sky: { x: 0, y: 0, w: 320, h: 80 }, haze: [{ y0: 55, y1: 100 }, { y0: 100, y1: 128 }], ghost: [{ x: 120, y: 132, w: 90, h: 64 }, { x: 0, y: 128, w: 110, h: 50 }] },
    layers: null,
  };
  return a;
}

/* ------------------------------------------------------------------ scene2.json anchors -> the shapes life reads */
function normalize(a) {
  if (!a || a._norm) return a;
  const o = Object.assign({}, a); o._norm = true;
  // anything the art hides behind something nearer is marked visible:0 by the scene; drop it everywhere
  const vis = (x) => !(x && typeof x === 'object' && !Array.isArray(x) && (x.visible === 0 || x.visible === false));
  for (const k of Object.keys(o)) if (Array.isArray(o[k]) && k !== 'windows') o[k] = o[k].filter(vis);
  const rect = (r) => (Array.isArray(r) ? { x: r[0], y: r[1], w: r[2], h: r[3] } : r);
  if (Array.isArray(o.windows) && o.windows.length && Array.isArray(o.windows[0])) {
    const f = o.windowsFields || ['x', 'y', 'w', 'h', 'lit', 'baked', 'hue', 'curtain', 'room', 'layer', 'dark'];
    o.windows = o.windows.map((w) => { const r = {}; f.forEach((k, i) => { r[k] = w[i]; }); return r; });
  }
  if (o.stars) o.stars = { regions: (o.stars.regions || []).map(rect), points: (o.stars.points || []).map((p) => Array.isArray(p) ? p : [p.x, p.y, p.mag, p.col]) };
  if (o.water && o.water[0] && o.water[0].moonPath && !o.moonPath) o.moonPath = o.water[0].moonPath;
  if (o.regions) {
    const r = Object.assign({}, o.regions);
    if (r.sky) r.sky = rect(r.sky);
    if (r.haze) r.haze = r.haze.map((h) => (Array.isArray(h) ? { y0: h[0], y1: h[1] } : h));
    r.ghost = (r.ghost || r.motes || r.fireflies || []).map(rect);
    o.regions = r;
  }
  if (o.vents) {
    const bells = o.vents.filter((v) => v.kind === 'windbell');
    if (bells.length) o.furin = (o.furin || []).concat(bells);
    o.fans = o.vents.filter((v) => v.kind === 'fan');
    // a few of the fans are water heaters breathing steam; the rest only hum
    o.vents = o.vents.filter((v, i) => v.kind === 'steam' || (v.kind === 'fan' && hash(i, 3, 9100) < 0.12) || !v.kind);
  }
  if (o.paths) {
    if (!o.stairs) o.stairs = o.paths.filter((p) => p.kind === 'lane');
    if (!o.streets) o.streets = o.paths.filter((p) => p.kind === 'road');
  }
  if (o.stairs) o.stairs = o.stairs.map((st) => Object.assign({ w0: st.w || 20 }, st));
  if (o.ferry && o.ferry.path && !o.ferry.pts) o.ferry = Object.assign({}, o.ferry);
  if (o.shrine && o.shrine.lantern && !o.shrine.hang) o.shrine = Object.assign({}, o.shrine, { hang: [o.shrine.lantern[0], o.shrine.lantern[1] - 16] });
  if (o.shrine && o.shrine.lantern) o.shrine = Object.assign({}, o.shrine, { x: o.shrine.lantern[0], y: o.shrine.lantern[1] });
  return o;
}
// a point at fraction u along a polyline, by length
function along(pts, u) {
  if (pts.length < 2) return pts[0];
  let L = 0; const seg = [];
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); L += d; }
  let t = clamp(u, 0, 1) * L;
  for (let i = 0; i < seg.length; i++) { if (t <= seg[i] || i === seg.length - 1) { const f = seg[i] ? clamp(t / seg[i], 0, 1) : 0; return [lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)]; } t -= seg[i]; }
  return pts[pts.length - 1];
}

/* ------------------------------------------------------------------ the engine */
function create(opts) {
  opts = opts || {};
  const reduced = !!opts.reduced || matchMedia('(prefers-reduced-motion: reduce)').matches;
  let qs = null; try { qs = new URLSearchParams(location.search); } catch (e) { /* none */ }
  const timeScale = opts.timeScale || (qs && +qs.get('lifespeed')) || 1;     // ?lifespeed=20 to watch a night go by
  const ONLY = opts.only || (qs && qs.get('lifeonly') ? qs.get('lifeonly').split(',') : null);
  const SKIP = qs && qs.get('lifeskip') ? qs.get('lifeskip').split(',') : null;
  const t0wall = performance.now(), base = (opts.epoch != null ? opts.epoch : 0) || (qs && +qs.get('lifeepoch')) || (Date.now() / 1000 - 1.7e9);
  const now = () => base + (performance.now() - t0wall) / 1000 * timeScale;

  let scene = opts.scene || null, A = null, view = null, U = 1;
  let hours = opts.hours || 26;         // 19.5 evening .. 24 midnight .. 29.5 first light
  let analyser = opts.analyser || null, bins = null, bass = 0, level = 0, lvlSlow = 0, lastOnset = 0;
  const onsets = [];                   // music-made ripple seeds {t, k}
  let occl = [], paused = false, timer = 0, raf = 0, dead = false;
  const surfaces = new Map(); let top = null;
  let actors = [], kinds = new Set();
  const stat = { frames: 0, paints: 0, px: 0, since: performance.now(), fps: 0, pps: 0, pxs: 0 };

  // a palette colour of the scene as the current mood shows it (scene.moodColor), cached per tenth of an hour
  const moodCache = new Map();
  function moodRGB(layer, rgb) {
    if (!scene || typeof scene.moodColor !== 'function') return null;
    const k = layer + rgb.join() + Math.round(hours * 10);
    let c = moodCache.get(k);
    if (c === undefined) { try { c = scene.moodColor(layer, rgb) || null; } catch (e) { c = null; } if (moodCache.size > 4000) moodCache.clear(); moodCache.set(k, c); }
    return c;
  }
  /* night curves */
  const deep = () => smooth(19.5, 26.5, hours) * (1 - smooth(27.5, 29.6, hours));     // 0 evening, 1 deepest
  const dawn = () => smooth(28, 29.6, hours);
  const wet = () => 1 - 0.75 * smooth(19.5, 29, hours);                                  // drying through the night
  const litFrac = () => 0.62 - 0.46 * deep() + 0.12 * dawn();

  /* -------- surfaces */
  function topCanvas() {
    if (top) return top;
    let cv = opts.canvas;
    if (!cv) {
      cv = document.createElement('canvas'); cv.setAttribute('aria-hidden', 'true');
      cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;image-rendering:pixelated';
      (opts.container || document.body).appendChild(cv); opts._own = cv;
    }
    top = mkSurf(cv, 'top'); return top;
  }
  // each canvas repaints at most at its own rate: the far and slow layers less often, so fewer canvases change per frame
  const RATE = { sky: 4, far: 4, mid: 4, near: 4, fg: 4, top: 4 };
  function mkSurf(cv, name) { return { cv, ctx: cv.getContext('2d'), name, tiles: null, tw: 0, th: 0, any: false, urgent: false, last: 0, rate: RATE[name] || 6 }; }
  function surf(layer) {
    if (scene && typeof scene.overlay === 'function' && layer && layer !== 'top') {
      let s = surfaces.get(layer);
      if (!s) { let cv = null; try { cv = scene.overlay(layer); } catch (e) { cv = null; } s = cv ? mkSurf(cv, layer) : topCanvas(); if (!s.tiles) sizeSurf(s); surfaces.set(layer, s); }
      return s;
    }
    return topCanvas();
  }
  const TILE = 16;
  function sizeSurf(s) {
    if (s === top && !(scene && scene.overlay && false)) {
      const dpr = opts.dpr || window.devicePixelRatio || 1, el = s.cv.parentElement && s.cv.parentElement !== document.body ? s.cv.parentElement : null;
      const cw = Math.round((el ? el.clientWidth : innerWidth) * dpr) || Math.round(innerWidth * dpr), ch = Math.round((el ? el.clientHeight : innerHeight) * dpr) || Math.round(innerHeight * dpr);
      if (s.cv.width !== cw || s.cv.height !== ch) { s.cv.width = cw; s.cv.height = ch; }
    }
    s.tw = Math.ceil(s.cv.width / TILE); s.th = Math.ceil(s.cv.height / TILE); s.tiles = new Uint8Array(s.tw * s.th);
    s.ctx.imageSmoothingEnabled = false;
  }

  /* -------- view: art px -> device px */
  function computeView() {
    if (scene && typeof scene.view === 'function') { view = Object.assign({ parallax: {} }, scene.view()); }
    else {
      const s = topCanvas(); sizeSurf(s);
      const cw = s.cv.width, ch = s.cv.height, W = A.w, H = A.h;
      const scale = A.design === 320 ? Math.max(1, Math.ceil(Math.max(cw / W, ch / H))) : Math.max(cw / W, ch / H);
      view = { w: W, h: H, scale, ox: Math.floor((cw - W * scale) / 2), oy: Math.floor((ch - H * scale) * 0.62), parallax: {} };
    }
    // the design unit: one sprite pixel is U device pixels; the 2560-wide art is drawn 1:1 at its design size
    U = Math.max(1, Math.round(view.scale * (A.design === 320 ? 320 / 2560 : 1)));
  }
  function P(x, y, layer) { const p = (view.parallax && view.parallax[layer]) || [0, 0]; return [Math.round((x + p[0]) * view.scale + view.ox), Math.round((y + p[1]) * view.scale + view.oy)]; }
  const Ls = (v) => Math.max(1, Math.round(v * view.scale));     // an art length in device px
  // art units of the design: the 320 stub is 8x coarser than the 2560 art
  const D = (v) => v * 2560 / A.w;

  /* -------- dirty tiles */
  function dirty(s, x, y, w, h) {
    if (w <= 0 || h <= 0 || !s.tiles) return;
    for (const o of occl) if (x >= o.x && y >= o.y && x + w <= o.x + o.w && y + h <= o.y + o.h) return;
    const x0 = clamp(Math.floor(x / TILE), 0, s.tw - 1), x1 = clamp(Math.floor((x + w - 1) / TILE), 0, s.tw - 1);
    const y0 = clamp(Math.floor(y / TILE), 0, s.th - 1), y1 = clamp(Math.floor((y + h - 1) / TILE), 0, s.th - 1);
    if (x + w < 0 || y + h < 0 || x >= s.cv.width || y >= s.cv.height) return;
    for (let ty = y0; ty <= y1; ty++) s.tiles.fill(1, ty * s.tw + x0, ty * s.tw + x1 + 1);
    s.any = true;
  }
  function flush(s) {
    if (!s.any || !s.tiles) return; s.any = false;
    const g = s.ctx, list = s.list;
    // runs of dirty tiles per row, merged down while identical
    const rects = [];
    let open = new Map();
    for (let ty = 0; ty <= s.th; ty++) {
      const runs = new Map();
      if (ty < s.th) {
        let tx = 0; const row = ty * s.tw;
        while (tx < s.tw) { if (s.tiles[row + tx]) { const a = tx; while (tx < s.tw && s.tiles[row + tx]) tx++; runs.set(a * 65536 + tx, 1); } else tx++; }
      }
      const next = new Map();
      for (const [k, r] of open) { if (runs.has(k)) { r.h++; next.set(k, r); runs.delete(k); } else rects.push(r); }
      for (const k of runs.keys()) next.set(k, { x: Math.floor(k / 65536), y: ty, w: (k & 65535) - Math.floor(k / 65536), h: 1 });
      open = next;
    }
    s.tiles.fill(0);
    for (const r of rects) {
      const x = r.x * TILE, y = r.y * TILE, w = r.w * TILE, h = r.h * TILE;
      g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.clearRect(x, y, w, h);
      for (const a of list) {
        if (a.bx + a.bw <= x || a.by + a.bh <= y || a.bx >= x + w || a.by >= y + h || a.hide || a.occluded) continue;
        g.globalAlpha = 1; a.draw(g);
      }
      g.restore(); stat.px += w * h;
    }
  }
  function fullRedraw() {
    for (const s of allSurfs()) {
      s.tiles && s.tiles.fill(0); s.any = false;
      s.ctx.clearRect(0, 0, s.cv.width, s.cv.height);
      for (const a of s.list) if (!a.hide && !a.occluded) { s.ctx.globalAlpha = 1; a.draw(s.ctx); }
      s.ctx.globalAlpha = 1;
    }
  }
  function allSurfs() { const set = new Set(surfaces.values()); if (top) set.add(top); return [...set]; }
  function markOccluded(a) {
    a.occluded = false;
    for (const o of occl) if (a.bx >= o.x && a.by >= o.y && a.bx + a.bw <= o.x + o.w && a.by + a.bh <= o.y + o.h) { a.occluded = true; break; }
  }

  /* -------- actors
     an actor: {s, kind, bx,by,bw,bh, wake, key, upd(T) -> key (sets a.wake, may move the box), draw(g)} */
  let nid = 0;
  function actor(kind, layer, o) {
    const a = Object.assign({ s: surf(layer), kind, id: ++nid * 7919 + kind.length, bx: 0, by: 0, bw: 0, bh: 0, wake: 0, key: undefined, hide: false }, o);
    if (ONLY && !ONLY.includes(kind)) return a;
    if (SKIP && SKIP.includes(kind)) return a;      // diagnostics: only some kinds (opts.only, or ?lifeonly=star,window)
    kinds.add(kind); actors.push(a); return a;
  }
  const FR = 1 / 30, FR15 = 1 / 15, FR8 = 1 / 8, BEAT_IDLE = 3, BEAT_MUSIC = 6, BEAT_FAST = 8;
  const box = (a, x, y, w, h) => { a.bx = x; a.by = y; a.bw = w; a.bh = h; };

  /* ================================================================== the things */
  function build() {
    actors = []; kinds = new Set(); nid = 0;
    const T = now();
    sky(); water(); bridge(); town(); street(); presence(); air();
    // per-surface lists
    for (const s of allSurfs()) s.list = [];
    for (const a of actors) { if (!a.s.list) a.s.list = []; }
    for (const s of allSurfs()) { s.list = []; sizeSurf(s); }
    for (const a of actors) a.s.list.push(a);
    for (const a of actors) { a.key = a.upd(T); markOccluded(a); }
    fullRedraw();
  }

  /* ---------------------------------------------------------------- sky */
  function sky() {
    const st = A.stars || { points: [] }, reg = (A.regions && A.regions.sky) || { x: 0, y: 0, w: A.w, h: A.h * 0.4 };
    // stars: each twinkles at its own rate; the damp air dims them in slow passing veils
    (st.points || []).forEach((p, i) => {
      const [X, Y] = P(p[0], p[1], 'sky'), mag = p[2] == null ? 0.5 : p[2];
      const col = p[3] === 'blue' ? C.star[1] : p[3] === 'warm' ? C.star[2] : p[3] === 'white' ? C.star[0] : C.star[(hash(i, 5, 3) * 4) | 0], rate = 0.35 + hash(i, 6, 3) * 1.2, big = mag > 0.82, s = big ? 2 * U : U;
      const a = actor('star', 'sky', { i, lv: 0 });
      const r = big ? 2 * U + U : U;
      box(a, X - r, Y - r, s + 2 * r, s + 2 * r);
      a.upd = (T) => {
        const veil = 0.55 + 0.45 * vnoise(9000 + ((p[0] / (A.w / 6)) | 0), T / 37);           // moisture drifting by
        const tw = 0.5 + 0.5 * Math.sin(T * rate * TAU / 3 + i) * (0.6 + 0.4 * vnoise(i, T * rate));
        const k = (1 - 0.85 * dawn()) * veil * (0.35 + 0.65 * tw) * (0.4 + 0.6 * mag);
        a.lv = Math.round(k * 10); a.wake = T + (reduced ? 30 : 0.12 + 0.3 * hash(i, 8, 3));
        return a.lv;
      };
      a.draw = (g) => {
        if (a.lv <= 0) return;
        g.globalAlpha = a.lv / 10; g.fillStyle = col; g.fillRect(X, Y, s, s);
        if (big && a.lv >= 6) { g.globalAlpha = (a.lv - 5) / 14; g.fillRect(X - U, Y + s / 2 - (U >> 1), U, U); g.fillRect(X + s, Y + s / 2 - (U >> 1), U, U); g.fillRect(X + s / 2 - (U >> 1), Y - U, U, U); g.fillRect(X + s / 2 - (U >> 1), Y + s, U, U); }
      };
    });
    if (reduced) return;
    const [sx0, sy0] = P(reg.x, reg.y, 'sky'), [sx1, sy1] = P(reg.x + reg.w, reg.y + reg.h, 'sky');
    // a satellite, slow and steady, now and then
    {
      const a = actor('satellite', 'sky', { on: false, fast: true });
      a.upd = (T) => {
        const e = slotEv(101, T, 260, 0.75, 95);
        if (!e.on) { a.on = false; a.wake = e.next; box(a, 0, 0, 0, 0); return 'off'; }
        const ya = lerp(sy0, sy1, 0.1 + 0.4 * hash(101, e.n, 4)), yb = lerp(sy0, sy1, 0.05 + 0.5 * hash(101, e.n, 5));
        const dir = hash(101, e.n, 6) < 0.5;
        const x = Math.round(lerp(dir ? sx0 : sx1, dir ? sx1 : sx0, e.u)), y = Math.round(lerp(ya, yb, e.u));
        a.on = true; a.x = x; a.y = y; a.lv = Math.round(10 * Math.sin(e.u * Math.PI) ** 0.5 * (0.7 + 0.3 * vnoise(102, T / 4)));
        box(a, x, y, U, U); a.wake = T + Math.max(FR, 95 / Math.max(1, sx1 - sx0)); return x * 1e5 + y * 16 + a.lv;
      };
      a.draw = (g) => { if (!a.on) return; g.globalAlpha = 0.25 + a.lv / 16; g.fillStyle = '#e4e8ff'; g.fillRect(a.x, a.y, U, U); };
    }
    // a meteor, very rarely: a fine streak and gone
    {
      const a = actor('meteor', 'sky', {fast: true });
      a.upd = (T) => {
        const e = slotEv(103, T, 540, 0.55, 0.9);
        if (!e.on) { a.on = false; a.wake = e.next; box(a, 0, 0, 0, 0); return 'off'; }
        const x0 = lerp(sx0, sx1, hash(103, e.n, 4)), y0 = lerp(sy0, sy1, 0.05 + 0.3 * hash(103, e.n, 5)), len = 120 * U * (0.6 + 0.6 * hash(103, e.n, 6));
        const dx = hash(103, e.n, 7) < 0.5 ? -1 : 1;
        a.on = true; a.pts = [];
        const head = e.u * len, tail = Math.max(0, head - 50 * U);
        for (let d = tail; d <= head; d += U) a.pts.push([Math.round(x0 + dx * d * 0.85), Math.round(y0 + d * 0.5), (d - tail) / (head - tail + 1) * (1 - e.u * 0.7)]);
        const xs = a.pts.map((p) => p[0]), ys = a.pts.map((p) => p[1]);
        box(a, Math.min(...xs), Math.min(...ys), Math.max(...xs) - Math.min(...xs) + U, Math.max(...ys) - Math.min(...ys) + U);
        a.wake = T + FR; return e.u;
      };
      a.draw = (g) => { if (!a.on) return; g.fillStyle = '#f4f0ff'; for (const p of a.pts) { g.globalAlpha = p[2] * 0.8; g.fillRect(p[0], p[1], U, U); } };
    }
    // a high, late aircraft: a white strobe and a dim red, crossing slowly
    {
      const a = actor('aircraft', 'sky', {});
      a.upd = (T) => {
        const e = slotEv(104, T, 480, 0.5 * (1 - deep() * 0.6), 150);
        if (!e.on) { a.on = false; a.wake = e.next; box(a, 0, 0, 0, 0); return 'off'; }
        const y = Math.round(lerp(sy0, sy1, 0.15 + 0.3 * hash(104, e.n, 4))), dir = hash(104, e.n, 5) < 0.5;
        const x = Math.round(lerp(dir ? sx0 - 20 : sx1 + 20, dir ? sx1 + 20 : sx0 - 20, e.u));
        const ph = (T - e.t0) % 1.4; a.on = true; a.x = x; a.y = y; a.strobe = ph < 0.07; a.red = ((T - e.t0) % 2.2) < 1.1;
        box(a, x - U, y - U, 4 * U, 3 * U); a.wake = T + (a.strobe ? 0.07 : Math.min(0.2, 1.4 - ph)); return x * 100 + (a.strobe ? 1 : 0) + (a.red ? 2 : 0);
      };
      a.draw = (g) => {
        if (!a.on) return;
        g.globalAlpha = 0.5; g.fillStyle = a.red ? C.red : C.redDim; g.fillRect(a.x + 2 * U, a.y, U, U);
        if (a.strobe) { g.globalAlpha = 0.95; g.fillStyle = C.white; g.fillRect(a.x, a.y, U, U); g.globalAlpha = 0.3; g.fillRect(a.x - U, a.y, 3 * U, U); g.fillRect(a.x, a.y - U, U, 3 * U); }
      };
    }
    // the moon's halo breathes: a soft ring that swells and settles, with the bass a breath deeper
    if (A.moon) {
      const m = A.moon, [X, Y] = P(m.x, m.y, 'sky'), R = Ls(m.r), H = Ls(m.halo || m.r * 2.6);
      const a = actor('moonhalo', 'sky', { lv: 0 });
      box(a, X - H - 2, Y - H - 2, 2 * H + 4, 2 * H + 4);
      a.upd = (T) => {
        const v = 0.5 + 0.5 * Math.sin(T * TAU / 23) * 0.7 + 0.3 * (vnoise(105, T / 9) - 0.5);
        a.lv = Math.round((v + bass * 0.6) * 24); a.wake = T + 0.5; return a.lv;
      };
      a.draw = (g) => {
        const gr = g.createRadialGradient(X, Y, R * 0.9, X, Y, H);
        const k = 0.05 + a.lv / 24 * 0.06;
        gr.addColorStop(0, rgba(C.moon, k)); gr.addColorStop(0.4, rgba('#d8b8f0', k * 0.45)); gr.addColorStop(1, rgba('#b080d0', 0));
        g.fillStyle = gr; g.beginPath(); g.arc(X, Y, H, 0, TAU); g.fill();
      };
      // a faint ring of moisture, the 22-degree halo, only in the damp hours
      const b = actor('moonring', 'sky', {}); const RR = Ls(m.r * 5.2);
      box(b, X - RR - 2, Y - RR - 2, 2 * RR + 4, 2 * RR + 4);
      b.upd = (T) => { b.lv = Math.round(wet() * (0.5 + 0.5 * vnoise(106, T / 40)) * 8); b.wake = T + 4; return b.lv; };
      b.draw = (g) => { if (b.lv < 2) return; g.globalAlpha = b.lv / 8 * 0.03; g.strokeStyle = '#e8dcff'; g.lineWidth = Math.max(U, Ls(m.r * 0.7)); g.beginPath(); g.arc(X, Y, RR, 0, TAU); g.stroke(); };
    }
    // thin clouds drifting across, very slowly, thinner as the night dries
    for (let i = 0; i < 4; i++) {
      const w = Math.round((sx1 - sx0) * (0.25 + 0.2 * hash(i, 1, 107))), h = Math.round((sy1 - sy0) * (0.1 + 0.1 * hash(i, 2, 107)));
      const y = Math.round(lerp(sy0, sy1, 0.15 + 0.7 * hash(i, 3, 107))), v = (2 + 3 * hash(i, 4, 107)) * U / 10;   // device px per second
      const strip = softStrip('cloud' + i, w, h, i % 2 ? '#7a5c98' : '#5a4680', 0.13, 300 + i, 34);
      const span = sx1 - sx0 + w, a = actor('cloud', 'sky', {});
      a.upd = (T) => {
        const x = sx0 - w + Math.floor(((T * v + hash(i, 5, 107) * span) % span));
        a.x = x; a.lv = Math.round((0.35 + 0.65 * wet()) * 10); box(a, x, y, w, h); a.wake = T + 1 / v; return x * 100 + a.lv;
      };
      a.draw = (g) => { g.globalAlpha = a.lv / 10; g.drawImage(strip, a.x, y); };
    }
    // dawn: a few birds cross, and the last stars go out
    {
      for (let i = 0; i < 3; i++) {
        const a = actor('bird', 'sky', {}); const b1 = sprite('bird1', SPR.bird1, SPAL.bird, U), b2 = sprite('bird2', SPR.bird2, SPAL.bird, U);
        a.upd = (T) => {
          const e = slotEv(110 + i, T, 70, dawn() > 0.3 ? 0.6 : 0, 40);
          if (!e.on) { a.on = false; a.wake = Math.min(e.next, T + 20); box(a, 0, 0, 0, 0); return 'off'; }
          const x = Math.round(lerp(sx1 + 10, sx0 - 10, e.u)), y = Math.round(lerp(sy0, sy1, 0.5 + 0.3 * hash(i, e.n, 111)) + Math.sin(e.u * 7) * 3 * U);
          a.on = true; a.x = x; a.y = y; a.f = ((T * 3) | 0) % 2; box(a, x, y, 5 * U, 3 * U); a.wake = T + FR15; return x * 1e4 + y * 2 + a.f;
        };
        a.draw = (g) => { if (a.on) { g.globalAlpha = 0.8; g.drawImage(a.f ? b1 : b2, a.x, a.y); } };
      }
    }
  }

  /* ---------------------------------------------------------------- water */
  function water() {
    const W0 = (A.water && A.water[0]) || null; if (!W0) return;
    const L = 'far';
    const [wx0, wy0] = P(W0.x, W0.y, L), [wx1, wy1] = P(W0.x + W0.w, W0.y + W0.h, L);
    // the moon's path: glints coming and going on the swell, wider toward us
    if (A.moonPath) {
      const mp = A.moonPath, n = reduced ? 0 : (A.design === 320 ? 56 : 110);
      for (let i = 0; i < n; i++) {
        const a = actor('glint', L, {});
        const P0 = 0.6 + hash(i, 1, 120) * 1.6;
        a.upd = (T) => {
          const k = Math.floor(T / P0 + hash(i, 2, 120)), f = (T / P0 + hash(i, 2, 120)) - k;
          const v = hash(i, k, 121), yy = mp.y0 + (mp.y1 - mp.y0) * Math.pow(v, 0.8);
          const dz = (yy - mp.y0) / (mp.y1 - mp.y0), spread = (mp.w0 != null ? lerp(mp.w0, mp.w1, dz) : mp.w * (0.3 + 0.9 * dz)) / 2;
          const xx = mp.x + (hash(i, k, 122) * 2 - 1) * spread * (0.4 + 0.6 * hash(i, k, 123));
          const [X, Y] = P(xx, yy, L), len = U * (1 + ((hash(i, k, 124) * 3 * (0.5 + v) * (A.design === 320 ? 1 : 1 + 2 * dz)) | 0));
          const on = f > 0.2 && f < 0.75; a.lv = on ? (f < 0.35 || f > 0.6 ? 1 : 2) : 0;
          a.X = X; a.Y = Y; a.len = len; box(a, X, Y, len, U);
          a.wake = T + P0 * (f < 0.2 ? 0.2 - f : f < 0.35 ? 0.35 - f : f < 0.6 ? 0.6 - f : f < 0.75 ? 0.75 - f : 1 - f) + 0.001;
          return k * 4 + a.lv;
        };
        a.draw = (g) => { if (!a.lv) return; g.globalAlpha = a.lv === 2 ? 0.85 : 0.4; g.fillStyle = C.moon; g.fillRect(a.X, a.Y, a.len, U); };
      }
    }
    // the swell: long faint lines of light drifting along the strait
    for (let i = 0; i < (reduced ? 0 : (A.design === 320 ? 34 : 70)); i++) {
      const a = actor('swell', L, {});
      const wh = A.train && A.design !== 320 ? Math.max(40, A.train.path[0][1] - 70 - W0.y) : W0.h, yy = W0.y + wh * (0.02 + 0.96 * Math.pow(hash(i, 1, 130), 1.4)), [, Y] = P(0, yy, L), len = Math.round((wx1 - wx0) * (0.01 + 0.03 * hash(i, 2, 130)) * (0.5 + (yy - W0.y) / wh));
      const v = (0.4 + hash(i, 3, 130)) * U * 0.6 * (hash(i, 4, 130) < 0.5 ? -1 : 1), col = hash(i, 5, 130) < 0.3 ? '#c8a0e0' : '#8e88d8';
      const span = wx1 - wx0 + len;
      a.upd = (T) => {
        const x = wx0 - len + (((T * v + hash(i, 6, 130) * span) % span) + span) % span;
        a.X = Math.floor(x); a.lv = Math.round(4 + 4 * vnoise(i + 1300, T / 6)); box(a, a.X, Y, len, U);
        a.wake = T + Math.min(1 / Math.abs(v), 1.5); return a.X * 10 + a.lv;
      };
      a.draw = (g) => { g.globalAlpha = a.lv / 8 * 0.22; g.fillStyle = col; g.fillRect(a.X, Y, len, U); };
    }
    if (reduced) return;
    // perspective: how big a thing at art-y looks, relative to the dock (1 at the near shore, small at the horizon)
    const hy = (A.camera && A.camera.hy) || (A.water && A.water[0] ? A.water[0].y : 0), nearY = A.train ? A.train.path[0][1] : A.h;
    const persp = (y) => (A.design === 320 ? 1 : clamp((y - hy) / Math.max(1, nearY - hy), 0.08, 1.5));
    const unitAt = (y, base) => Math.max(U, Math.round(U * base * persp(y)));
    // small boats with a masthead light, crossing over minutes; their light trembles on the water below
    (A.boats || []).forEach((b, i) => {
      const pts = b.path || [[b.x - 30, b.y], [b.x + 30, b.y]], BL = b.layer || L;
      if (b.kind === 'squid') {
        // squid boats far out: a row of bright lamps (baked), breathing, their long reflections shivering
        const [X, Y] = P(b.x, b.y, BL), w = Math.max(3 * U, Ls(b.w || 13)), a = actor('squidboat', BL, {});
        box(a, X - 2 * U, Y - 3 * U, w + 4 * U, 16 * U);
        a.upd = (T) => { a.k = Math.floor(T * 2.2 + i); a.dx = Math.round(Math.sin(T / 9 + i * 2) * 1.2) * U; a.wake = T + 1 / 2.2; return a.k * 10 + a.dx; };
        a.draw = (g) => {
          g.fillStyle = '#e8fff0';
          for (let x = 0; x < w; x += 2 * U) { g.globalAlpha = 0.35 + 0.5 * hash(a.k, x, 142); g.fillRect(X + x, Y - U, U, U); }
          g.fillStyle = '#c8e8ff';
          for (let j = 1; j < 12; j++) { if (hash(a.k, j, 143) < 0.35) continue; g.globalAlpha = 0.28 * (1 - j / 13); g.fillRect(X + (w >> 1) + a.dx + Math.round((hash(a.k, j, 144) - 0.5) * 3) * U, Y + j * U, U, U); }
        };
        return;
      }
      if (A.design !== 320) {
        // this boat is painted at anchor: only its lamp's light trembling on the water is ours
        const [X, Y] = P(b.x + (b.w || 20) / 2, b.y, BL), m = actor('mooredlight', BL, {}); box(m, X - 3 * U, Y + U, 7 * U, 10 * U);
        m.upd = (T) => { m.k = Math.floor(T * 2.5 + i); m.wake = T + 0.4; return m.k; };
        m.draw = (g) => { g.fillStyle = C.amber; for (let j = 0; j < 9; j += 2) { if (hash(m.k, j, 145) < 0.3) continue; g.globalAlpha = 0.35 * (1 - j / 10); g.fillRect(X + Math.round((hash(m.k, j, 146) - 0.5) * 4) * U, Y + 2 * U + j * U, U * (j > 4 ? 2 : 1), U); } };
        if (i !== 0) return;
      }
      // a small boat crossing (in the high-res art, on its own lane nearer the shore than the moored one)
      const lane = A.design === 320 ? pts : pts.map((q) => [q[0] + (q === pts[0] ? -500 : 300), q[1] + 70]);
      const a = actor('boat', BL, {}), r = actor('boatlight', BL, {});
      a.upd = (T) => {
        const e = slotEv(140 + i, T, 360 + 80 * i, 0.7, 260);
        if (!e.on) { a.on = r.on = false; a.wake = e.next; box(a, 0, 0, 0, 0); return 'off'; }
        const dir = hash(140 + i, e.n, 3) < 0.5, q = along(lane, dir ? e.u : 1 - e.u), [X, Y] = P(q[0], q[1], BL), su = unitAt(q[1], 1.6);
        a.on = true; a.su = su; a.dir = dir; a.X = X - 5 * su; a.Y = Y - 5 * su; box(a, a.X - 4 * su, a.Y - 5 * su, 18 * su, 10 * su);
        a.wake = T + 0.25; return a.X * 10 + a.Y * 1e5 + su;
      };
      a.draw = (g) => {
        if (!a.on) return; const su = a.su;
        g.drawImage(sprite('boat' + su, SPR.boat, SPAL.boat, su), a.X, a.Y);
        g.globalAlpha = 0.3; g.drawImage(glow(C.amber, 4 * su), a.X + 4 * su - 4 * su, a.Y - 4 * su);
        g.globalAlpha = 0.9; g.fillStyle = a.dir ? C.green : C.red; g.fillRect(a.X + (a.dir ? 8 : 1) * su, a.Y + 3 * su, su, su);
      };
      r.upd = (T) => {
        if (!a.on) { r.on = false; r.wake = a.wake; box(r, 0, 0, 0, 0); return 'off'; }
        const su = a.su; r.on = true; r.su = su; r.X = a.X + 4 * su; r.Y = a.Y + 6 * su; r.k = Math.floor(T * 3); box(r, r.X - 2 * su, r.Y, 5 * su, 9 * su); r.wake = T + 1 / 3; return r.X * 100 + r.k + r.Y * 1e6;
      };
      r.draw = (g) => {
        if (!r.on) return; const su = r.su; g.fillStyle = C.amber;
        for (let j = 0; j < 8; j += 2) { g.globalAlpha = 0.45 * (1 - j / 9); const o = Math.round((hash(r.k, j, 141) - 0.5) * 3) * su; g.fillRect(r.X + o - (j > 3 ? su : 0), r.Y + j * su, su * (j > 3 ? 3 : 1), su); }
      };
    });
    // the late ferry: leaves its dock, a row of warm windows, out across the strait (and, another time, back)
    if (A.ferry && (A.ferry.path || []).length > 1) {
      const pts = A.ferry.path, FL = A.ferry.layer || L, a = actor('ferry', FL, {}), r = actor('ferrylight', FL, {});
      a.upd = (T) => {
        const e = slotEv(150, T, 900, deep() > 0.85 ? 0.35 : 0.85, 520);
        if (!e.on) { a.on = r.on = false; a.wake = e.next; box(a, 0, 0, 0, 0); return 'off'; }
        const out = hash(150, e.n, 3) < 0.6, u = out ? e.u : 1 - e.u, q = along(pts, smooth(0, 1, u)), [X, Y] = P(q[0], q[1], FL), su = unitAt(q[1], 1.5);
        a.on = true; a.su = su; a.X = X - 14 * su; a.Y = Y - 4 * su; a.al = Math.round(Math.min(1, (1 - u) * 6 + 0.25, A.design === 320 ? 1 : Math.max(0, (u - 0.04) * 12)) * 8) / 8; if (a.al <= 0) { box(a, 0, 0, 0, 0); a.on = false; a.wake = T + 0.5; return 'dock'; } box(a, a.X - 2 * su, a.Y - 3 * su, 32 * su, 8 * su); a.wake = T + 0.3; return a.X * 10 + a.Y * 1e5 + su + a.al;
      };
      a.draw = (g) => {
        if (!a.on) return; const su = a.su; g.globalAlpha = a.al; g.drawImage(sprite('ferry' + su, SPR.ferry, SPAL.ferry, su), a.X, a.Y);
        g.fillStyle = C.green; g.globalAlpha = 0.8 * a.al; g.fillRect(a.X + 27 * su, a.Y + su, su, su); g.fillStyle = C.white; g.fillRect(a.X + 13 * su, a.Y - 2 * su, su, su);
      };
      r.upd = (T) => {
        if (!a.on) { r.on = false; r.wake = a.wake; box(r, 0, 0, 0, 0); return 'off'; }
        r.on = true; r.su = a.su; r.al = a.al; r.X = a.X; r.Y = a.Y + 5 * a.su; r.k = Math.floor(T * 2.5); box(r, r.X, r.Y, 28 * a.su, 7 * a.su); r.wake = T + 0.4; return r.X * 100 + r.k + r.Y * 1e6;
      };
      r.draw = (g) => {
        if (!r.on) return; const su = r.su; g.fillStyle = '#ffd890';
        for (let x = 3; x < 25; x += 2) for (let j = 0; j < 6; j += 2) { if (hash(r.k, x * 8 + j, 151) < 0.45) continue; g.globalAlpha = 0.3 * r.al * (1 - j / 7); g.fillRect(r.X + x * su + Math.round((hash(r.k, x + j, 152) - 0.5) * 2) * su, r.Y + j * su, su, su); }
      };
    }
    // buoys: a green and a red, each with its own patient count
    (A.buoys || []).forEach((b, i) => {
      const [X, Y] = P(b.x, b.y, L), col = b.c === 'r' ? C.red : C.green, per = b.c === 'r' ? 5 : 4, a = actor('buoy', L, {});
      box(a, X - 3 * U, Y - 3 * U, 7 * U, 10 * U);
      a.upd = (T) => { const ph = (T + i * 1.7) % per; a.lv = ph < 0.6 ? 2 : ph < 0.9 ? 1 : 0; a.wake = T + (ph < 0.6 ? 0.6 - ph : ph < 0.9 ? 0.9 - ph : per - ph); return a.lv; };
      a.draw = (g) => {
        g.globalAlpha = 0.5; g.fillStyle = '#1a1626'; g.fillRect(X, Y + U, U, 2 * U);
        if (!a.lv) { g.globalAlpha = 0.25; g.fillStyle = col; g.fillRect(X, Y, U, U); return; }
        g.globalAlpha = a.lv === 2 ? 0.95 : 0.4; g.fillStyle = col; g.fillRect(X, Y, U, U);
        g.globalAlpha = a.lv === 2 ? 0.4 : 0.15; g.drawImage(glow(col, 3 * U), X - 3 * U, Y - 3 * U);
        g.globalAlpha = a.lv === 2 ? 0.35 : 0.1; g.fillRect(X, Y + 4 * U, U, U); g.fillRect(X, Y + 6 * U, U, U);
      };
    });
    // the far shore: house lights, an antenna's red, a lighthouse's slow pair, a traffic light changing for no one
    (A.far || []).forEach((p, i) => {
      const [X, Y] = P(p[0], p[1], L), a = actor('farlight', L, {}), col = hash(i, 1, 160) < 0.2 ? '#cfd6ff' : C.warm[i % 5];
      box(a, X, Y, U, U);
      a.upd = (T) => {
        const e = slotEv(1600 + i, T, 400, litFrac() * 1.2, 400);
        const keep = hash(i, 9, 161) < 0.4;   // some burn all night
        a.lv = keep || e.on ? Math.round(5 + 4 * vnoise(1600 + i, T / 3)) : 0; a.wake = T + 1.5; return a.lv;
      };
      a.draw = (g) => { if (a.lv) { g.globalAlpha = a.lv / 10; g.fillStyle = col; g.fillRect(X, Y, U, U); } };
    });
    if (A.antenna) {
      const [X, Y] = P(A.antenna.x, A.antenna.y, L), a = actor('antenna', L, {}); box(a, X - 3 * U, Y - 3 * U, 7 * U, 7 * U);
      a.upd = (T) => { const ph = T % 3.1, v = ph < 1.5 ? Math.sin(ph / 1.5 * Math.PI) : 0; a.lv = Math.round(v * 6); a.wake = T + (ph < 1.5 ? 0.12 : 3.1 - ph); return a.lv; };
      a.draw = (g) => { if (!a.lv) return; g.globalAlpha = a.lv / 6; g.fillStyle = C.red; g.fillRect(X, Y, U, U); g.globalAlpha = a.lv / 6 * 0.3; g.drawImage(glow(C.red, 3 * U), X - 3 * U, Y - 3 * U); };
    }
    if (A.lighthouse) {
      const [X, Y] = P(A.lighthouse.x, A.lighthouse.y, L), a = actor('lighthouse', L, {}); box(a, X - 5 * U, Y - 5 * U, 11 * U, 11 * U);
      a.upd = (T) => { const ph = T % 12; const on = (ph < 0.5) || (ph > 1.4 && ph < 1.9); a.lv = on ? 1 : 0; a.wake = T + (ph < 0.5 ? 0.5 - ph : ph < 1.4 ? 1.4 - ph : ph < 1.9 ? 1.9 - ph : 12 - ph); return a.lv; };
      a.draw = (g) => { g.globalAlpha = a.lv ? 0.9 : 0.15; g.fillStyle = '#fff4d8'; g.fillRect(X, Y, U, U); if (a.lv) { g.globalAlpha = 0.35; g.drawImage(glow('#fff0c8', 5 * U), X - 5 * U, Y - 5 * U); } };
    }
    if (A.signal) {
      const [X, Y] = P(A.signal.x, A.signal.y, L), a = actor('farsignal', L, {}); box(a, X - U, Y - U, 3 * U, 7 * U);
      a.upd = (T) => { const ph = T % 48; a.c = ph < 26 ? C.green : ph < 30 ? C.amber : C.red; a.wake = T + (ph < 26 ? 26 - ph : ph < 30 ? 30 - ph : 48 - ph); return a.c; };
      a.draw = (g) => { g.fillStyle = a.c; g.globalAlpha = 0.85; g.fillRect(X, Y, U, U); g.globalAlpha = 0.2; g.fillRect(X, Y + 3 * U, U, U); g.globalAlpha = 0.1; g.fillRect(X, Y + 5 * U, U, U); };
    }
    // a fishing boat at anchor, its lantern bobbing on the slow swell
    if (A.fisher) {
      const [X, Y] = P(A.fisher.x, A.fisher.y, L), a = actor('fisher', L, {}); box(a, X - 4 * U, Y - 5 * U, 9 * U, 13 * U);
      a.upd = (T) => { a.dy = Math.round(Math.sin(T * TAU / 5.5)) * U; a.k = Math.floor(T * 1.5); a.wake = T + 1 / 1.5; return a.dy * 1000 + a.k; };
      a.draw = (g) => {
        const y = Y + a.dy; g.fillStyle = '#0e0c1a'; g.globalAlpha = 0.9; g.fillRect(X - 3 * U, y, 7 * U, U); g.fillRect(X - 2 * U, y + U, 5 * U, U);
        g.fillStyle = '#ffcf80'; g.fillRect(X + U, y - 3 * U, U, U); g.globalAlpha = 0.3; g.drawImage(glow(C.amber, 3 * U), X - 2 * U, y - 6 * U);
        for (let j = 0; j < 4; j++) { g.globalAlpha = 0.3 - j * 0.06; g.fillRect(X + U + Math.round((hash(a.k, j, 170) - 0.5) * 2) * U, y + (3 + j * 1.5 | 0) * U, U, U); }
      };
    }
  }

  /* ---------------------------------------------------------------- the bridge */
  function bridge() {
    const B = A.bridge; if (!B) return; const L = B.layer || 'far';
    // deck lights: a slow wave of brightness walking the span, one sodium lamp that hesitates
    const n = (B.lights || []).length;
    (B.lights || []).forEach((p, i) => {
      const [X, Y] = P(p[0], p[1], L), a = actor('bridgelight', L, {}), weak = hash(i, 1, 180) < 0.08;
      box(a, X - 2 * U, Y - 2 * U, 5 * U, 5 * U);
      a.upd = (T) => {
        let v = 0.72 + 0.2 * Math.sin(TAU * (T / 40 - i / Math.max(1, n) * 1.5)) + 0.08 * bass;
        if (weak) { const e = slotEv(1800 + i, T, 90, 0.5, 6); if (e.on) v *= 0.35 + 0.65 * Math.abs(Math.cos(e.u * 9)); }
        a.lv = Math.round(v * 10); a.wake = T + (reduced ? 20 : weak ? 0.2 : 0.8); return a.lv;
      };
      a.draw = (g) => { g.globalAlpha = a.lv / 10; g.fillStyle = C.sodium; g.fillRect(X, Y, U, U); g.globalAlpha = a.lv / 10 * 0.35; g.drawImage(glow(C.sodium, 2 * U), X - 2 * U, Y - 2 * U); };
    });
    // the tower tops: aviation red, breathing together
    (B.towers || []).forEach((p, i) => {
      const crane = p.kind === 'crane', [X, Y] = P(p[0] != null ? p[0] : p.x, p[1] != null ? p[1] : p.y, L), a = actor(crane ? 'cranelight' : 'towerlight', L, {});
      const per = crane ? 3.3 + i * 0.37 : 2.4, off = crane ? i * 0.9 : 0;
      box(a, X - 4 * U, Y - 4 * U, 9 * U, 9 * U);
      a.upd = (T) => { const ph = (T + off) % per, on = per / 2, v = ph < on ? Math.sin(ph / on * Math.PI) : 0; a.lv = Math.round(v * 8); a.wake = T + (reduced ? 30 : ph < on ? 0.1 : per - ph); return a.lv; };
      a.draw = (g) => { g.globalAlpha = 0.25 + a.lv / 8 * 0.7; g.fillStyle = C.red; g.fillRect(X, Y, U, U); if (a.lv) { g.globalAlpha = a.lv / 8 * 0.4; g.drawImage(glow(C.red, 4 * U), X - 4 * U, Y - 4 * U); } };
    });
  }

  /* ---------------------------------------------------------------- the town */
  function town() {
    const dark = A.windowDark || null;
    (A.windows || []).forEach((w, i) => {
      if (w.visible === 0 || w.visible === false) return;      // hidden behind something nearer in the art
      const L = w.layer || 'mid', [X, Y] = P(w.x, w.y, L), [X1, Y1] = P(w.x + w.w, w.y + w.h, L), ww = Math.max(U, X1 - X), hh = Math.max(U, Y1 - Y);
      const room = w.room || (hash(i, 1, 200) < 0.12 ? 'tv' : hash(i, 1, 200) < 0.2 ? 'desk' : 'plain');
      const hue = w.hue === 'tv' ? 'plain' : w.hue || 'warm', tv = room === 'tv' || w.hue === 'tv';
      const per = 120 + 520 * hash(i, 2, 200), bias = w.lit ? 0.35 : -0.1, baked = !!w.baked;
      const darkCol0 = w.dark ? `rgb(${w.dark[0]},${w.dark[1]},${w.dark[2]})` : dark || C.darker;
      let darkCol = darkCol0;
      // room light: warm lamps mostly; a few cool kitchens, a pink one; values sit in the scene's night, never pastel
      const ROOM = { warm: [['#f0b060', '#c88444'], ['#eaa458', '#b8763c'], ['#f4c070', '#cc8c4c'], ['#e89c5c', '#b06c3c']], cool: [['#a8b4e8', '#7a84c0']], pink: [['#e07aa8', '#a84c80']] };
      const rc = (ROOM[hue] || ROOM.warm)[i % (ROOM[hue] || ROOM.warm).length], big = ww >= 5 * U && hh >= 5 * U;
      const a = actor('window', L, { i }); box(a, X, Y, ww, hh);
      const canSil = ww >= 3 * U && hh >= 3 * U, canCurt = w.curtain && ww >= 3 * U;
      const litAt = (T) => {     // lit or not in this slot, from the hour, the window's habit and the seed
        const n = Math.floor(T / per), p = clamp(litFrac() + bias, 0.03, 0.97);
        return hash(i, n, 201) < p;
      };
      a.upd = (T) => {
        const n = Math.floor(T / per), f = T - n * per, on = litAt(T), was = litAt(n * per - 1);
        const FADE = 2.5; let k = on ? 1 : 0;
        if (on !== was && f < FADE && !reduced) k = on ? f / FADE : 1 - f / FADE;
        a.k = Math.round(k * 8) / 8; let wake = (on !== was && f < FADE && !reduced) ? T + FADE / 8 : n * per + per;
        a.tv = 0; a.sil = -1; a.cur = 0; a.desk = 0;
        if (a.k > 0 && !reduced) {
          if (tv) { const c = Math.floor(T / (0.35 + 0.9 * hash(i, Math.floor(T / 7), 202))); a.tv = 1 + ((hash(i, c, 203) * 5) | 0); wake = Math.min(wake, T + 0.35); }
          if (canSil) { const e = slotEv(2000 + i, T, 240, 0.18, 6); if (e.on) { a.sil = e.u; wake = Math.min(wake, T + 0.2); } else wake = Math.min(wake, e.next); }
          if (canCurt) { a.cur = Math.round((Math.sin(T * TAU / (6 + 3 * hash(i, 3, 200))) * 0.5 + 0.5) * (wet() * 0.5 + 0.5) * 1.6); wake = Math.min(wake, T + 0.7); }
          if (room === 'desk') { a.desk = deep() > 0.4 ? 1 : 0; }
        }
        a.wake = wake;
        return a.k * 1000 + a.tv * 10 + (a.sil < 0 ? 0 : 1 + Math.round(a.sil * 20)) * 100000 + a.cur + a.desk * 7;
      };
      a.draw = (g) => {
        const lit = a.k;
        if (w.dark) darkCol = moodRGB(L, w.dark) || darkCol0;
        if (baked) {      // the art has it lit: we may only darken it, or add a delta
          if (lit >= 1 && !a.tv && a.sil < 0) return;
          if (lit < 1) { g.globalAlpha = (1 - lit) * 0.9 * (scene && scene.moodColor ? 1 : 1 - 0.8 * smooth(26.5, 28.5, hours)); g.fillStyle = darkCol; g.fillRect(X, Y, ww, hh); g.globalAlpha = 1; }
        } else if (dark && lit < 1) { g.fillStyle = darkCol; g.fillRect(X, Y, ww, hh); }
        if (lit <= 0) return;
        if (!baked) {
          if (a.tv) {           // a dark room lit only by the set: deep blue, its brightness jumping with the cuts
            g.globalAlpha = lit * (0.32 + a.tv * 0.07); g.fillStyle = a.tv === 5 ? '#8a9ae8' : '#5a68c0'; g.fillRect(X, Y, ww, hh);
          } else if (a.desk) {  // a desk lamp in a dark room: a dim warm room and one bright corner
            g.globalAlpha = lit * 0.55; g.fillStyle = '#7a4e34'; g.fillRect(X, Y, ww, hh);
            const lx = X + Math.max(0, ww - 3 * U), ly = Y + Math.max(0, hh - 3 * U);
            g.globalAlpha = lit * 0.9; g.fillStyle = '#ffe2a8'; g.fillRect(lx, ly, Math.min(ww, 2 * U), Math.min(hh, 2 * U));
            if (big) { g.globalAlpha = lit * 0.35; g.fillStyle = '#d89a5c'; g.fillRect(Math.max(X, lx - 2 * U), Math.max(Y, ly - 2 * U), Math.min(ww, 5 * U), Math.min(hh, 4 * U)); }
          } else {              // a lamp-lit room: darker at the top, brighter where the lamp is
            g.globalAlpha = lit * 0.82; g.fillStyle = rc[1]; g.fillRect(X, Y, ww, hh);
            const top = big ? Math.round(hh * 0.35) : 0; g.globalAlpha = lit * 0.85; g.fillStyle = rc[0]; g.fillRect(X, Y + top, ww, hh - top);
          }
          if (big) {            // the frame and glazing bars, in the wall's dark, so it reads as a window
            g.globalAlpha = lit * 0.75; g.fillStyle = darkCol;
            g.fillRect(X + (ww >> 1), Y, U, hh); if (hh >= 8 * U) g.fillRect(X, Y + Math.round(hh * 0.45), ww, U);
          }
        } else if (a.tv) { g.globalAlpha = lit * (0.12 + a.tv * 0.04); g.fillStyle = '#7080e0'; g.fillRect(X, Y, ww, hh); }
        if (a.cur) { g.globalAlpha = lit * 0.45; g.fillStyle = '#e6c49c'; g.fillRect(X, Y, Math.min(ww, Math.round(ww * 0.3) + U * a.cur), hh); }
        if (a.sil >= 0) {
          const sw = Math.max(U, Math.round(ww * 0.35)), sx = Math.round(X - sw + (ww + sw) * a.sil);
          const x0 = Math.max(X, sx), x1 = Math.min(X + ww, sx + sw);
          if (x1 > x0) { g.globalAlpha = 0.75 * lit; g.fillStyle = '#2a1c2a'; g.fillRect(x0, Y + Math.round(hh * 0.25), x1 - x0, hh - Math.round(hh * 0.25)); }
        }
      };
    });

    // neon signs: steady hum, and once in a while a stutter
    (A.signs || []).forEach((s, i) => {
      const L = s.layer || 'mid', [X, Y] = P(s.x, s.y, L), [X1, Y1] = P(s.x + s.w, s.y + s.h, L), a = actor(s.neon === false ? 'signlight' : 'neon', L, {});
      const tube = s.neon === false ? '#fff0d8' : C.pinkHot, halo = s.neon === false ? '#ffe0b0' : C.pink;
      const gw = Math.max(X1 - X, Y1 - Y); box(a, X - gw, Y - gw / 2 | 0, X1 - X + 2 * gw, Y1 - Y + gw);
      a.upd = (T) => {
        let v = 0.82 + 0.1 * vnoise(2100 + i, T * 0.8) + 0.06 * bass;
        const e = reduced || s.neon === false ? { on: false, next: T + 60 } : slotEv(2100 + i, T, 70, 0.35, 1.4);
        if (e.on) v *= hash(i, Math.floor(e.u * 14), 2101) < 0.45 ? 0.25 : 1;
        a.lv = Math.round(v * 12); a.wake = Math.min(e.on ? T + 0.1 : e.next, T + (reduced ? 30 : 0.5)); return a.lv;
      };
      a.draw = (g) => {
        g.globalAlpha = a.lv / 12 * (s.neon === false ? 0.08 : 0.18); g.fillStyle = halo; g.fillRect(X - U, Y - U, X1 - X + 2 * U, Y1 - Y + 2 * U);
        g.globalAlpha = a.lv / 12 * (s.neon === false ? 0.3 : 0.75); g.fillStyle = tube; g.fillRect(X + ((X1 - X) >> 1) - (U >> 1), Y + U, U, Math.max(U, Y1 - Y - 2 * U));
      };
    });

    // lamps: the bulb breathes with the bass; moths keep company with the street lamps
    (A.lamps || []).forEach((l, i) => {
      const L = l.layer || 'mid', bulb = l.bulb, [X, Y] = bulb ? P(bulb[0], bulb[1], L) : P(l.x, l.y, L), BW = bulb ? Math.max(U, Ls(bulb[2])) : U, BH = bulb ? Math.max(U, Ls(bulb[3])) : U;
      const R = Math.max(3 * U, Math.round(Ls(l.r || 4) * (bulb ? 0.35 : 1))), gk = bulb ? 0.22 : 0.4, a = actor('lamp', L, {});
      const col = l.kind === 'vending' ? '#d8f0ff' : l.kind === 'lantern' ? '#ffb060' : C.sodium;
      box(a, X - R, Y - R, 2 * R + 1, 2 * R + 1);
      a.upd = (T) => { a.lv = Math.round((0.75 + 0.1 * vnoise(2200 + i, T / 5) + 0.15 * bass) * 20); a.wake = T + (reduced ? 30 : 0.25); return a.lv; };
      a.draw = (g) => { g.globalAlpha = a.lv / 20 * gk; g.drawImage(glow(col, R), X + (BW >> 1) - R, Y + (BH >> 1) - R); g.globalAlpha = a.lv / 20 * 0.9; g.fillStyle = '#fff6e0'; g.fillRect(X, Y, BW, BH); };
      if (reduced || l.kind === 'vending') return;
      const nm = l.kind === 'street' ? 3 : l.kind === 'porch' && hash(i, 1, 2290) < 0.6 ? 0 : 1;
      for (let j = 0; j < nm; j++) {
        const m = actor('moth', L, {}), ph = hash(i, j, 2300) * 100;
        m.upd = (T) => {
          const e = slotEv(2300 + i * 7 + j, T, 150, 0.7 - 0.3 * dawn(), 110);
          if (!e.on) { m.on = false; m.wake = e.next; box(m, 0, 0, 0, 0); return 'off'; }
          const tt = T * (1.3 + j * 0.4) + ph, r = R * 0.55;
          const x = Math.round(X + Math.sin(tt * 1.7) * r * (0.6 + 0.4 * Math.sin(tt * 0.31))), y = Math.round(Y - R * 0.15 + Math.cos(tt * 2.3) * r * 0.5);
          m.on = true; m.X = x; m.Y = y; m.fl = ((T * 8) | 0) % 2; box(m, x - U, y, 3 * U, U); m.wake = T + FR15; return x * 1e4 + y * 2 + m.fl;
        };
        m.draw = (g) => { if (!m.on) return; g.globalAlpha = 0.7; g.fillStyle = '#efe6d8'; g.fillRect(m.X, m.Y, U, U); if (m.fl) { g.globalAlpha = 0.35; g.fillRect(m.X - U, m.Y, U, U); g.fillRect(m.X + U, m.Y, U, U); } };
      }
    });

    // the vending machine: a cold steady glow, the selection lamps stepping, the compressor's sigh
    if (A.vending) {
      const v = A.vending, L = v.layer || 'near', pr = v.panel || [v.x, v.y, v.w, v.h * 0.55], [X, Y] = P(pr[0], pr[1], L), [X1, Y1] = P(pr[0] + pr[2], pr[1] + pr[3], L), w = X1 - X, h = Math.round((Y1 - Y) / 0.55);
      const a = actor('vending', L, {}); box(a, X - 2 * U, Y - 2 * U, w + 4 * U, h + 4 * U);
      a.upd = (T) => {
        let v2 = 0.9 + 0.05 * Math.sin(T * 0.9);
        const e = reduced ? { on: false, next: T + 60 } : slotEv(2400, T, 95, 0.6, 3);
        if (e.on) v2 *= 0.8 + 0.2 * (hash(2400, Math.floor(e.u * 10), 1) < 0.6 ? 1 : 0);
        a.lv = Math.round(v2 * 16); a.sel = reduced ? 0 : Math.floor(T / 1.6) % 6; a.wake = T + (e.on ? 0.15 : 0.4); return a.lv * 10 + a.sel;
      };
      a.draw = (g) => {
        if (a.lv < 14) { g.globalAlpha = (14 - a.lv) / 14 * 1.6; g.fillStyle = '#20223a'; g.fillRect(X, Y, w, Math.round(h * 0.55)); }
        else { g.globalAlpha = (a.lv - 13) / 4 * 0.12; g.fillStyle = '#eef6ff'; g.fillRect(X, Y, w, Math.round(h * 0.55)); }
        const rowY = Y + Math.round(h * 0.6);
        for (let k = 0; k < 6; k++) { const bx = X + U + Math.round(k * (w - 2 * U) / 6); g.globalAlpha = k === a.sel ? 0.9 : 0.25; g.fillStyle = k === a.sel ? '#ff9a60' : '#9fd0ff'; g.fillRect(bx, rowY, U, U); }
      };
    }

    // laundry: shirts and a towel, swaying in the same breeze as the lantern
    (A.laundry || []).forEach((l, i) => {
      const L = l.layer || 'mid', [X, Y] = P(l.x, l.y, L), [X1] = P(l.x + l.w, l.y, L), w = X1 - X;
      const items = [], cols = ['#9a8aa8', '#7a6a98', '#a08080', '#8898b0', '#b0a0a0'];
      for (let k = 0, x = U; x < w - 2 * U && k < 6; k++) { const iw = (2 + ((hash(i, k, 2500) * 3) | 0)) * U, ih = (3 + ((hash(i, k, 2501) * 4) | 0)) * U; items.push({ x, w: iw, h: ih, c: cols[(i + k) % 5] }); x += iw + U; }
      const a = actor('laundry', L, {}); box(a, X - 2 * U, Y - U, w + 4 * U, 9 * U);
      a.upd = (T) => {
        const g0 = breeze(T); a.off = items.map((it, k) => Math.round(Math.sin(T * TAU / (4 + k * 0.7) + k) * g0 * 1.4) * U);
        a.wake = T + (reduced ? 60 : 0.3); return a.off.join();
      };
      a.draw = (g) => {
        g.globalAlpha = 0.5; g.fillStyle = '#3a3048'; g.fillRect(X, Y, w, U);
        items.forEach((it, k) => { g.globalAlpha = 0.85; g.fillStyle = it.c; g.fillRect(X + it.x, Y + U, it.w, U); g.fillRect(X + it.x + a.off[k], Y + 2 * U, it.w, it.h - U); g.globalAlpha = 0.2; g.fillStyle = '#ffffff'; g.fillRect(X + it.x + a.off[k], Y + 2 * U, U, it.h - U); });
      };
    });

    // steam from vents and a bathhouse flue: puffs that rise, widen, and thin away
    (A.vents || []).forEach((v, i) => {
      if (reduced) return;
      const L = v.layer || 'mid', [X, Y] = P(v.x, v.y, L);
      for (let j = 0; j < 4; j++) {
        const a = actor('steam', L, {}), per = 5 + 2 * hash(i, j, 2600);
        a.upd = (T) => {
          const tt = T / per + j / 4, k = Math.floor(tt), u = tt - k, r = Math.round((2 + 6 * u) * U);
          a.X = Math.round(X + (hash(i, k * 4 + j, 2601) - 0.5) * 4 * U + breeze(T) * 10 * U * u); a.Y = Math.round(Y - u * 26 * U); a.r = r;
          a.lv = Math.round(Math.sin(u * Math.PI) * 8 * (0.5 + 0.5 * wet())); box(a, a.X - r, a.Y - r, 2 * r + 1, 2 * r + 1); a.wake = T + 0.18; return a.X * 1e5 + a.Y * 10 + a.lv;
        };
        a.draw = (g) => { if (a.lv <= 0) return; g.globalAlpha = a.lv / 8 * 0.35; g.drawImage(glow('#c8b8e0', a.r), a.X - a.r, a.Y - a.r); };
      }
    });

    // the cat: asleep on the wall, breathing; now and then it wakes, looks about, stretches, and settles again
    if (A.cat && A.cat.head) {
      const c = A.cat, L = c.layer || 'mid', [HX, HY] = P(c.head[0], c.head[1], L), [TX, TY] = P(c.tail[0], c.tail[1], L), cu = Math.max(U, Ls(1));
      const a = actor('cat', L, {}); box(a, Math.min(HX, TX) - 8 * cu, Math.min(HY, TY) - 8 * cu, Math.abs(HX - TX) + 16 * cu, Math.abs(HY - TY) + 12 * cu);
      a.upd = (T) => {
        const e = reduced ? { on: false, next: T + 300 } : slotEv(2700, T, 240, 0.8, 30);
        const tw = slotEv(2701, T, 40, 0.6, 0.5);      // an ear twitch, asleep
        a.eyes = 0; a.tail = 0; a.ear = tw.on ? 1 : 0; let wake = Math.min(e.next, tw.on ? tw.next : tw.next);
        if (e.on) {
          const t = e.u * 30; a.ear = 1;
          a.eyes = t < 1 || t > 27 ? 0 : (((t * 1.7) | 0) % 9 === 4 ? 0 : 1 + ((t / 6) | 0) % 2);   // open, a slow blink, looking left/right
          a.tail = t > 8 && t < 22 ? 1 + (((t * 1.5) | 0) % 3) : 0; wake = T + 0.2;
        }
        a.wake = wake; return a.eyes * 100 + a.tail * 10 + a.ear;
      };
      a.draw = (g) => {
        if (a.ear) { g.globalAlpha = 0.9; g.fillStyle = '#1a1220'; g.fillRect(HX - 2 * cu, HY - 6 * cu, cu, 2 * cu); g.fillRect(HX + 2 * cu, HY - 6 * cu, cu, 2 * cu); }
        if (a.eyes) { const dx = a.eyes === 2 ? -cu : 0; g.globalAlpha = 0.95; g.fillStyle = '#d8f080'; g.fillRect(HX - 2 * cu + dx, HY - 2 * cu, cu, cu); g.fillRect(HX + cu + dx, HY - 2 * cu, cu, cu); g.globalAlpha = 0.25; g.drawImage(glow('#d8f080', 3 * cu), HX - 3 * cu, HY - 5 * cu); }
        if (a.tail) { g.globalAlpha = 0.95; g.fillStyle = '#2a1c22'; const k = a.tail; for (let j = 0; j < 5; j++) g.fillRect(TX - j * cu, TY - Math.round(Math.sin(j / 4 * Math.PI * 0.5) * k * 1.5) * cu - j * cu, cu, cu); }
      };
    } else if (A.cat) {
      const c = A.cat, L = c.layer || 'mid', [X, Y] = P(c.x, c.y, L), [X1] = P(c.x + c.w, c.y, L);
      const cu = Math.max(U, Math.round((X1 - X) / 12)), a = actor('cat', L, {});
      const fr = {}; for (const k of ['catSleep', 'catBreath', 'catUp', 'catUpBlink', 'catStretch', 'catTail']) fr[k] = sprite(k, SPR[k], SPAL.cat, cu);
      box(a, X, Y + Ls(c.h) - 6 * cu, 12 * cu, 6 * cu);
      a.upd = (T) => {
        const e = reduced ? { on: false, next: T + 300 } : slotEv(2700, T, 280, 0.8, 26);
        let f = ((T / 3.2) | 0) % 2 ? 'catBreath' : 'catSleep', wake = Math.min(e.next, T + 3.2 - (T % 3.2));
        if (e.on) {
          const s = e.u * 26;
          f = s < 2 ? 'catUp' : s < 9 ? (((s * 2) | 0) % 9 === 0 ? 'catUpBlink' : ((s | 0) % 4 === 3 ? 'catTail' : 'catUp')) : s < 13 ? 'catStretch' : s < 22 ? (((s * 3) | 0) % 11 === 0 ? 'catUpBlink' : 'catUp') : 'catSleep';
          wake = T + 0.25;
        }
        a.f = f; a.wake = wake; return f;
      };
      a.draw = (g) => { g.drawImage(fr[a.f], a.bx, a.by); };
    }

    // AC units: condensate gathers, falls, ticks on the ground
    (A.ac || []).forEach((p, i) => { if (!reduced) dropper('acdrip', p.x, p.y, p.layer || 'mid', 3000 + i, 8 + 12 * hash(i, 1, 3000), 10 + 22 * hash(i, 2, 3000), '#aab8e0'); });

    // a wind chime under the eaves: the paper strip turns, the glass catches the lamp
    (A.furin || []).forEach((f, i) => {
      const L = f.layer || 'mid', [X, Y] = P(f.x, f.y, L), spr = sprite('furin', SPR.furin, SPAL.furin, U), a = actor('furin', L, {});
      box(a, X - 3 * U, Y, 9 * U, 6 * U);
      a.upd = (T) => { const b = breeze(T); a.dx = Math.round(Math.sin(T * TAU / 2.3) * b * 1.6) * U; a.gl = b > 0.6 && hash(i, Math.floor(T * 2), 3100) < 0.3; a.wake = T + (reduced ? 60 : 0.25); return a.dx * 10 + (a.gl ? 1 : 0); };
      a.draw = (g) => { g.drawImage(spr, X - U, Y); g.globalAlpha = 0.8; g.fillStyle = '#e8a0b8'; g.fillRect(X + a.dx, Y + 4 * U, U, 2 * U); if (a.gl) { g.globalAlpha = 0.9; g.fillStyle = '#ffffff'; g.fillRect(X - U, Y + U, U, U); } };
    });

    // someone awake on a balcony: a phone's small cool glow for a while
    (A.phone || []).forEach((p, i) => {
      if (reduced) return;
      const L = p.layer || 'mid', [X, Y] = P(p.x, p.y, L), a = actor('phone', L, {}); box(a, X - 3 * U, Y - 3 * U, 7 * U, 7 * U);
      a.upd = (T) => { const e = slotEv(3200 + i, T, 380, 0.5 * (0.4 + deep()), 60); if (!e.on) { a.lv = 0; a.wake = e.next; return 0; } a.lv = Math.round((0.6 + 0.4 * hash(i, Math.floor(T / 2.5), 3201)) * Math.min(1, e.u * 20, (1 - e.u) * 20) * 6); a.wake = T + 0.5; return a.lv; };
      a.draw = (g) => { if (!a.lv) return; g.globalAlpha = a.lv / 6 * 0.5; g.drawImage(glow('#b8d0ff', 3 * U), X - 3 * U, Y - 3 * U); g.globalAlpha = a.lv / 6; g.fillStyle = '#dce8ff'; g.fillRect(X, Y, U, U); };
    });

    // roofs still wet: moon glints on tiles, fewer as the night dries
    for (let i = 0; i < (reduced ? 0 : 40) && A.windows && A.windows.length; i++) {
      const w = A.windows[(hash(i, 1, 3300) * A.windows.length) | 0], L = w.layer || 'mid';
      const [X, Y] = P(w.x + hash(i, 2, 3300) * w.w * 3 - w.w, w.y - D(4) * (0.5 + hash(i, 3, 3300)) / 8 * (A.w / 320 === 1 ? 1 : 1) - (A.design === 320 ? 2 : 6), L);
      const a = actor('rooftile', L, {}); box(a, X, Y, U, U); const per = 3 + 6 * hash(i, 4, 3300);
      a.upd = (T) => { const k = Math.floor(T / per), f = T / per - k; a.on = hash(i, k, 3301) < 0.55 * wet() && f > 0.3 && f < 0.5; a.wake = T + per * (f < 0.3 ? 0.3 - f : f < 0.5 ? 0.5 - f : 1.3 - f); return a.on ? 1 : 0; };
      a.draw = (g) => { if (a.on) { g.globalAlpha = 0.55; g.fillStyle = C.wet; g.fillRect(X, Y, U, U); } };
    }

    // potted plants on the steps and sills: a wet leaf catching the light now and then, nodding in the breeze
    (A.plants || []).forEach((pl, i) => {
      if (reduced) return;
      const L = pl.layer || 'mid', [X, Y] = P(pl.x, pl.y, L), a = actor('dew', L, {}), per = 5 + 9 * hash(i, 1, 5100);
      box(a, X - 3 * U, Y - 4 * U, 7 * U, 6 * U);
      a.upd = (T) => {
        const k = Math.floor(T / per + hash(i, 2, 5100)), f = T / per + hash(i, 2, 5100) - k, on = hash(i, k, 5101) < 0.35 * (0.4 + 0.6 * wet()) && f > 0.2 && f < 0.45;
        const b = breeze(T); a.dx = b > 0.55 ? Math.round(Math.sin(T * 2.1 + i)) * U : 0;
        a.on = on; a.ox = Math.round((hash(i, k, 5102) - 0.5) * 4) * U; a.oy = -Math.round(hash(i, k, 5103) * 3) * U;
        a.wake = T + (on ? 0.3 : Math.min(0.6, per * (f < 0.2 ? 0.2 - f : 1.2 - f))); return (on ? 1 : 0) + a.dx * 10 + a.ox * 100 + a.oy * 1e4;
      };
      a.draw = (g) => { if (!a.on) return; g.globalAlpha = 0.75; g.fillStyle = '#e4f0ff'; g.fillRect(X + a.ox + a.dx, Y + a.oy, U, U); };
    });
    // trees: their leaves turn and shine a little when the breeze comes, and drip after
    (A.trees || []).forEach((t, i) => {
      if (reduced) return;
      const L = t.layer || 'mid', [X, Y] = P(t.x, t.y, L), R = Math.max(3 * U, Ls(t.r || 10));
      for (let j = 0; j < 4; j++) {
        const a = actor('leaf', L, {}), ang = hash(i, j, 5200) * TAU, rr = R * (0.3 + 0.6 * hash(i, j, 5201));
        const lx = Math.round(X + Math.cos(ang) * rr), ly = Math.round(Y + Math.sin(ang) * rr * 0.8);
        box(a, lx - U, ly - U, 3 * U, 3 * U);
        a.upd = (T) => { const b = breeze(T); a.lv = b > 0.5 ? Math.round(clamp((b - 0.5) * 2 * (0.5 + 0.5 * Math.sin(T * 3.3 + j * 2 + i)), 0, 1) * 4) : 0; a.wake = T + (b > 0.45 ? 0.25 : 1.5); return a.lv; };
        a.draw = (g) => { if (!a.lv) return; g.globalAlpha = a.lv / 4 * 0.5; g.fillStyle = '#9fb8d8'; g.fillRect(lx, ly, U, U); };
      }
      dropper('treedrip', t.x + (hash(i, 1, 5202) - 0.5) * (t.r || 10), t.y + (t.r || 10) * 0.6, L, 5300 + i, 9 + 10 * hash(i, 2, 5202), Math.max(8, (t.r || 10) * 0.9), '#c8d8f8');
    });
    // utility poles: a bead of rain on an insulator arm; at first light a small bird perches
    (A.poles || []).forEach((po, i) => {
      const L = po.layer || 'mid', arms = po.arms || [[po.x, po.y]];
      if (!reduced) { const q = arms[(hash(i, 1, 5400) * arms.length) | 0]; dropper('armdrip', q[0], q[1] + 1, L, 5400 + i, 10 + 14 * hash(i, 2, 5400), 14 + 10 * hash(i, 3, 5400), '#d0d8f8'); }
      const q = arms[(hash(i, 4, 5400) * arms.length) | 0], [X, Y] = P(q[0], q[1], L), a = actor('perch', L, {}), bu = Math.max(U, Ls(1));
      box(a, X - 3 * bu, Y - 4 * bu, 7 * bu, 4 * bu);
      a.upd = (T) => { const e = slotEv(5450 + i, T, 120, dawn() > 0.2 ? 0.7 : 0.05, 70); a.on = e.on; a.f = e.on ? (((T * 0.7) | 0) % 5 === 0 ? 1 : 0) : 0; a.wake = e.on ? T + 0.5 : Math.min(e.next, T + 20); return (a.on ? 1 : 0) + a.f * 2; };
      a.draw = (g) => { if (!a.on) return; g.globalAlpha = 0.95; g.fillStyle = '#1c1624'; g.fillRect(X - bu, Y - 2 * bu, 3 * bu, 2 * bu); g.fillRect(X + (a.f ? 2 : 1) * bu, Y - 3 * bu, bu, bu); g.fillRect(X - 2 * bu, Y - bu, bu, bu); };
    });
    // the pagoda on the far hill keeps a small lamp at its foot
    if (A.shrine_pagoda) {
      const sp = A.shrine_pagoda, [X, Y] = P(sp.x, (sp.base || sp.y) - 6, 'far'), a = actor('pagodalamp', 'far', {});
      box(a, X - 6 * U, Y - 6 * U, 13 * U, 13 * U);
      a.upd = (T) => { a.lv = Math.round((0.7 + 0.3 * vnoise(5500, T * 1.5)) * 6); a.wake = T + (reduced ? 60 : 0.35); return a.lv; };
      a.draw = (g) => { g.globalAlpha = a.lv / 6 * 0.3; g.drawImage(glow('#ffb860', 6 * U), X - 6 * U, Y - 6 * U); g.globalAlpha = a.lv / 6 * 0.8; g.fillStyle = '#ffd8a0'; g.fillRect(X, Y, U, U); };
    }
  }

  // a breeze shared by everything that sways: mostly still, sometimes a long soft gust
  function breeze(T) { const e = slotEv(77, T, 75, 0.7, 14); const g = e.on ? Math.sin(e.u * Math.PI) : 0; return 0.25 + 0.15 * vnoise(78, T / 8) + 0.6 * g; }

  // a drip site: a bead swells, lets go, falls, and ticks (or rings a puddle below)
  function dropper(kind, x, y, L, id, per, fall, col) {
    const [X, Y] = P(x, y, L), F = Math.round(Ls(fall / (A.design === 320 ? 8 : 1) * (A.design === 320 ? 1 : 1)));
    const a = actor(kind, L, {}); box(a, X - 2 * U, Y, 5 * U, F + 3 * U);
    const p = per / (0.4 + 0.6 * wet());
    a.upd = (T) => {
      const pp = per / (0.4 + 0.6 * wet()), k = Math.floor(T / pp + hash(id, 0, 9)), f = (T / pp + hash(id, 0, 9)) - k, s = f * pp;
      // 0..pp-1.2: swelling bead; then a 0.5 s fall; then a tiny splash
      const sw = pp - 1.2;
      if (s < sw) { a.st = 0; a.sz = s > sw * 0.6 ? 1 : 0; a.wake = T + (s < sw * 0.6 ? sw * 0.6 - s : sw - s); }
      else if (s < sw + 0.5) { const u = (s - sw) / 0.5; a.st = 1; a.dy = Math.round(F * u * u); a.wake = T + FR; }
      else if (s < sw + 0.75) { a.st = 2; a.wake = T + 0.25 - (s - sw - 0.5) + 0.001; }
      else { a.st = 3; a.wake = T + (pp - s); }
      return a.st * 1e4 + (a.st === 1 ? a.dy : a.sz) + k * 1e5;
    };
    a.draw = (g) => {
      g.fillStyle = col;
      if (a.st === 0) { g.globalAlpha = a.sz ? 0.85 : 0.45; g.fillRect(X, Y, U, U); if (a.sz) { g.globalAlpha = 0.3; g.fillRect(X, Y + U, U, U); } }
      else if (a.st === 1) { g.globalAlpha = 0.8; g.fillRect(X, Y + a.dy, U, U); g.globalAlpha = 0.3; g.fillRect(X, Y + a.dy - 3 * U, U, 3 * U); g.globalAlpha = 0.12; g.fillRect(X, Y + a.dy - 6 * U, U, 3 * U); }
      else if (a.st === 2) { g.globalAlpha = 0.5; g.fillRect(X - U, Y + F, U, U); g.fillRect(X + U, Y + F, U, U); g.globalAlpha = 0.3; g.fillRect(X - 2 * U, Y + F + U, U, U); g.fillRect(X + 2 * U, Y + F + U, U, U); }
    };
    return a;
  }

  /* ---------------------------------------------------------------- the street */
  function street() {
    // drips: eaves and leaf tips
    if (!reduced) {
      (A.eaves || []).forEach((e, i) => { if (A.design !== 320 && hash(i, 0, 3399) > 0.62) return; const n = A.design === 320 ? Math.max(1, Math.round((e.x1 - e.x0) / 6)) : 1 + (hash(i, 1, 3399) < 0.25 ? 1 : 0); for (let j = 0; j < n; j++) dropper('eavedrip', e.x0 + (e.x1 - e.x0) * (j + 0.5) / n, e.y, e.layer || 'mid', 3400 + i * 16 + j, 5 + 9 * hash(i, j, 3400), A.design === 320 ? 6 : 40, '#c0c8f0'); });
      (A.drips || []).forEach((d, i) => (A.design === 320 || hash(i, 0, 3499) < 0.6) && dropper('leafdrip', d.x, d.y, d.layer || 'near', 3500 + i, 6 + 12 * hash(i, 1, 3500), A.design === 320 ? 8 : 60, '#d0e0ff'));
      // raindrops beading on the wires, sliding to the low point, letting go
      (A.wires || []).forEach((w, i) => {
        const pts = w.pts, L = w.layer || 'sky';
        for (let j = 0; j < 3; j++) {
          const a = actor('wirebead', L, {}), per = 14 + 16 * hash(i, j, 3600), seg = (hash(i, j, 3601) * (pts.length - 1)) | 0;
          let k0 = seg, dir = pts[Math.min(pts.length - 1, seg + 1)][1] >= pts[seg][1] ? 1 : -1; const sub = [pts[k0]];
          for (let k = k0 + dir; k >= 0 && k < pts.length && sub.length < 8; k += dir) { if (pts[k][1] < sub[sub.length - 1][1] - 0.01) break; sub.push(pts[k]); }
          if (sub.length < 2) sub.push([pts[k0][0] + 1, pts[k0][1]]);
          const st = sub[0], en = sub[sub.length - 1];
          a.upd = (T) => {
            const f = (T / per + hash(i, j, 3602)) % 1;
            if (f > 0.85) { a.on = false; box(a, 0, 0, 0, 0); a.wake = T + (1 - f) * per; return 'off'; }
            const u = smooth(0, 0.8, f), q = along(sub, u * 0.95), [X, Y] = P(q[0], q[1] + 0.2, L);
            a.on = true; a.X = X; a.Y = Y + U; a.lv = f > 0.8 ? 2 : 1; box(a, X, Y + U, U, U); a.wake = T + 0.3; return X * 1e4 + Y * 2 + a.lv;
          };
          a.draw = (g) => { if (a.on) { g.globalAlpha = a.lv === 2 ? 0.9 : 0.55; g.fillStyle = '#dfe4ff'; g.fillRect(a.X, a.Y, U, U); } };
        }
      });
    }
    // puddles: rings from the drips (fewer as the night dries) and from the music; the moon trembles in one of them
    (A.puddles || []).forEach((p, i) => {
      const L = p.layer || 'near', [X, Y] = P(p.x, p.y, L), [X1, Y1] = P(p.x + p.w, p.y + p.h, L), w = X1 - X, h = Math.max(U, Y1 - Y);
      if (!reduced) for (let j = 0; j < 3; j++) {
        const a = actor('ripple', L, {}); box(a, X - U, Y - U, w + 2 * U, h + 2 * U);
        a.upd = (T) => {
          // the music's ripple, if one is fresh for this puddle and this ring
          let src = null;
          for (const o of onsets) if (o.p === i && o.j === j && T - o.t < 3) src = { t0: o.t, x: o.x, y: o.y };
          if (!src) {
            const per = (6 + 8 * hash(i, j, 3700)) / (0.3 + 0.7 * wet()), k = Math.floor(T / per + hash(i, j, 3701)), t0 = (k - hash(i, j, 3701)) * per;
            if (T - t0 < 3) src = { t0, x: 0.15 + 0.7 * hash(i * 9 + j, k, 3702), y: 0.3 + 0.4 * hash(i * 9 + j, k, 3703) };
            else { a.on = false; a.wake = t0 + per; return 'off'; }
          }
          const u = (T - src.t0) / 3; a.on = true; a.cx = X + w * src.x; a.cy = Y + h * src.y;
          a.rx = Math.max(U, u * w * 0.35); a.ry = Math.max(U * 0.5, a.rx * h / w * 1.1); a.lv = Math.round((1 - u) * 6); a.wake = T + FR8; return Math.round(a.rx) * 10 + a.lv;
        };
        a.draw = (g) => {
          if (!a.on || a.lv <= 0) return;
          g.fillStyle = C.wet; g.globalAlpha = a.lv / 6 * 0.55;
          const n = Math.max(10, Math.round(a.rx * 0.9));
          for (let k = 0; k < n; k++) { const th = k / n * TAU; const x = Math.round((a.cx + Math.cos(th) * a.rx) / U) * U, y = Math.round((a.cy + Math.sin(th) * a.ry) / U) * U; if (x >= X && x < X + w && y >= Y && y < Y + h) g.fillRect(x, y, U, U); }
        };
      }
      if (i === 0 || (p.src && p.src.length)) {
        // a reflected light (the moon in the first puddle, the lamps it lists in the others) shivering
        const a = actor('reflection', L, {}), sx = X + Math.round(w * (0.3 + 0.4 * hash(i, 1, 3800))), sy = Y + Math.round(h * 0.4);
        box(a, sx - 4 * U, sy - U, 9 * U, 3 * U);
        a.upd = (T) => { a.dx = Math.round(Math.sin(T * 1.3 + i) * vnoise(3800 + i, T / 2) * 2) * U; a.lv = Math.round((0.6 + 0.4 * vnoise(3801 + i, T / 3)) * 5); a.wake = T + (reduced ? 60 : 0.35); return a.dx * 10 + a.lv; };
        a.draw = (g) => { g.globalAlpha = a.lv / 5 * 0.5; g.fillStyle = i === 0 ? C.moon : C.sodium; g.fillRect(sx + a.dx - U, sy, 3 * U, U); g.globalAlpha *= 0.5; g.fillRect(sx - a.dx, sy + U, U, U); };
      }
    });
    // the shrine lantern: hung on its cord, swaying in the breeze, candle-warm
    if (A.shrine) {
      const s = A.shrine, L = s.layer || 'mid', hp = s.hang || [s.x, s.y - 4], [HX, HY] = P(hp[0], hp[1], L), [, LY] = P(s.x, s.y, L);
      const lu = Math.max(U, A.design === 320 ? Math.round(Ls(1) / 2) : Ls(2)), spr = sprite('lantern' + lu, SPR.lantern, SPAL.lantern, lu), a = actor('lantern', L, {});
      const len = Math.max(2 * U, LY - HY);
      box(a, HX - 8 * lu, HY, 16 * lu, len + 9 * lu + 8 * lu);
      a.upd = (T) => {
        const ang = (Math.sin(T * TAU / 6.3) * 0.5 + Math.sin(T * TAU / 2.9) * 0.2) * breeze(T) * 0.09;
        a.dx = Math.round(Math.sin(ang) * (len + 4 * lu)); a.fl = Math.round((0.8 + 0.2 * vnoise(3900, T * 3)) * 4); a.wake = T + (reduced ? 60 : 0.2); return a.dx * 10 + a.fl;
      };
      a.draw = (g) => {
        g.globalAlpha = 0.6; g.fillStyle = '#2a1a1c';
        for (let k = 0; k < len; k += U) g.fillRect(HX + Math.round(a.dx * k / len), HY + k, U, U);
        const lx = HX + a.dx - 2 * lu, ly = HY + len;
        g.globalAlpha = 0.35 + a.fl * 0.06; g.drawImage(glow('#ffa040', 8 * lu), lx + 2 * lu - 8 * lu, ly + 4 * lu - 8 * lu);
        g.globalAlpha = 0.8 + a.fl * 0.05; g.drawImage(spr, lx, ly);
      };
    }
    if (reduced) return;
    // the night train along the shore: lit windows sliding past, a headlight, the crossing bells' lamps
    if (A.train) {
      const tp = A.train.path, L = A.train.layer || 'mid', [AX, AY] = P(tp[0][0], tp[0][1], L), [BX, BY] = P(tp[tp.length - 1][0], tp[tp.length - 1][1], L);
      const carW = A.train.car ? Ls(A.train.car) : 46 * U, TH = A.train.h ? Math.max(3 * U, Ls(A.train.h)) : 5 * U, wh = Math.max(U, Math.round(TH * 0.3)), a = actor('train', L, { fast: true });
      const trainAt = (T) => {
        const per = 300, prob = hours > 25.3 && hours < 28.6 ? 0.2 : 0.6; const e = slotEv(4000, T, per, prob, 120);
        if (!e.on) return { on: false, next: e.next };
        const cars = 3 + ((hash(4000, e.n, 4) * 4) | 0), dir = hash(4000, e.n, 5) < 0.5, len = cars * carW;
        const x = dir ? lerp(AX - len, BX, e.u) : lerp(BX, AX - len, e.u);
        return { on: true, x: Math.round(x), cars, dir, n: e.n, next: e.next };
      };
      a.upd = (T) => {
        const s = trainAt(T); a.tr = s;
        if (!s.on) { box(a, 0, 0, 0, 0); a.wake = s.next; return 'off'; }
        const y = Math.round(lerp(AY, BY, 0.5)); a.y = y;
        box(a, s.x - 8 * U, y - TH - 4 * U, s.cars * carW + 16 * U, TH + 10 * U); a.wake = T + 120 / Math.max(1, Math.abs(BX - AX) + s.cars * carW); return s.x;
      };
      a.draw = (g) => {
        const s = a.tr; if (!s || !s.on) return; const y = a.y;
        for (let c = 0; c < s.cars; c++) {
          const x = s.x + c * carW;
          g.globalAlpha = 0.95; g.fillStyle = '#100c1c'; g.fillRect(x + U, y - TH, carW - 2 * U, TH);
          g.globalAlpha = 0.5; g.fillStyle = '#3a3050'; g.fillRect(x + U, y - TH, carW - 2 * U, U);      // the roof catches the moon
          g.fillStyle = '#ffe6b0'; const step = Math.max(3 * U, wh * 2);
          for (let k = 3 * U; k < carW - 4 * U - wh; k += step) { if (hash(s.n, c * 97 + k, 4001) < 0.15) continue; g.globalAlpha = 0.85; g.fillRect(x + k, y - TH + Math.round(TH * 0.3), wh + U, wh); }
          g.globalAlpha = 0.18; g.fillStyle = '#ffe0a0'; g.fillRect(x + 2 * U, y + U, carW - 4 * U, U);       // the lit windows on the wet ballast
        }
        const hx = s.dir ? s.x + s.cars * carW - U : s.x; g.globalAlpha = 0.9; g.fillStyle = C.white; g.fillRect(hx, y - 2 * U, U, U);
        g.globalAlpha = 0.35; g.drawImage(glow('#fff4d0', 6 * U), hx - 6 * U, y - 8 * U);
        const tx = s.dir ? s.x : s.x + s.cars * carW - U; g.globalAlpha = 0.8; g.fillStyle = C.red; g.fillRect(tx, y - 2 * U, U, U);
      };
      // its reflection, if water lies below the line
      const W0 = A.water && A.water[0];
      if (W0) {
        const r = actor('trainreflect', 'far', {fast: true }), [, WY0] = P(0, W0.y, 'far'), [, WY1] = P(0, W0.y + W0.h, 'far');
        r.upd = (T) => {
          const s = trainAt(T); r.tr = s; if (!s.on) { box(r, 0, 0, 0, 0); r.wake = s.next; return 'off'; }
          r.y = Math.round(Math.min(WY1 - 4 * U, lerp(AY, BY, 0.5) + 3 * U)); if (r.y < WY0) { box(r, 0, 0, 0, 0); r.wake = s.next; return 'off'; }
          r.k = Math.floor(T * 4); box(r, s.x, r.y, s.cars * carW, 4 * U); r.wake = T + Math.min(0.25, 120 / Math.max(1, Math.abs(BX - AX) + s.cars * carW)); return s.x * 10 + r.k % 10;
        };
        r.draw = (g) => {
          const s = r.tr; if (!s || !s.on) return; g.fillStyle = '#ffe0a0';
          for (let c = 0; c < s.cars; c++) for (let k = 3 * U; k < carW - 5 * U; k += 4 * U) { if (hash(s.n, c * 40 + k, 4001) < 0.15) continue; g.globalAlpha = 0.22; g.fillRect(s.x + c * carW + k + Math.round((hash(r.k, k + c, 4002) - 0.5) * 2) * U, r.y + ((hash(r.k, k, 4003) * 3) | 0) * U, 2 * U, U); }
        };
      }
      // the level crossing's two lamps, alternating while a train is near
      if (A.crossing) {
        const CL = A.crossing.layer || L, lp = (A.crossing.lamps || [[A.crossing.x, A.crossing.y], [A.crossing.x + 4 / view.scale, A.crossing.y]]).map((q) => P(q[0], q[1], CL));
        const [X, Y] = lp[0], c = actor('crossing', CL, {}), x0 = Math.min(lp[0][0], lp[1][0]), x1 = Math.max(lp[0][0], lp[1][0]);
        box(c, x0 - 4 * U, Math.min(lp[0][1], lp[1][1]) - 4 * U, x1 - x0 + 9 * U, Math.abs(lp[0][1] - lp[1][1]) + 9 * U);
        c.upd = (T) => {
          const s = trainAt(T); const near = s.on && X > s.x - 140 * U && X < s.x + s.cars * carW + 140 * U;
          // also ring a little before it arrives
          const soon = trainAt(T + 5), on = near || (soon.on && X > soon.x - 140 * U && X < soon.x + soon.cars * carW + 140 * U);
          c.ph = on ? (((T / 0.55) | 0) % 2) + 1 : 0; c.wake = T + (on ? 0.55 - (T % 0.55) : 1); return c.ph;
        };
        c.draw = (g) => {
          for (const k of [0, 1]) { const on = c.ph === k + 1, [lx, ly] = lp[k]; if (!on) continue; g.globalAlpha = 0.95; g.fillStyle = C.red; g.fillRect(lx, ly, 2 * U, 2 * U); g.globalAlpha = 0.35; g.drawImage(glow(C.red, 4 * U), lx + U - 4 * U, ly + U - 4 * U); }
        };
      }
    }
    // a pedestrian signal down the lane, keeping its own time
    if (A.ped) {
      const L = A.ped.layer || 'near', rr = A.ped.red, gr = A.ped.green, [X, Y] = P(A.ped.x, A.ped.y, L), a = actor('pedsignal', L, {});
      const [RX, RY] = rr ? P(rr[0], rr[1], L) : [X, Y], [GX, GY] = gr ? P(gr[0], gr[1], L) : [X, Y + 2 * U], PS = rr ? Math.max(U, Ls(rr[2])) : U;
      box(a, Math.min(RX, GX) - 3 * U, Math.min(RY, GY) - 3 * U, PS + 6 * U, Math.abs(GY - RY) + PS + 6 * U);
      a.upd = (T) => { const ph = T % 60; a.st = ph < 34 ? 'r' : ph < 52 ? 'g' : (((ph * 3) | 0) % 2 ? 'g' : 'o'); a.wake = T + (ph < 34 ? 34 - ph : ph < 52 ? 52 - ph : 1 / 3 - (ph % (1 / 3)) + 0.001); return a.st; };
      a.draw = (g) => {
        if (a.st === 'r') { g.globalAlpha = 0.8; g.fillStyle = C.red; g.fillRect(RX, RY, PS, PS); g.globalAlpha = 0.25; g.drawImage(glow(C.red, 3 * U), RX - 3 * U, RY - 3 * U); }
        if (a.st === 'g') { g.globalAlpha = 0.85; g.fillStyle = '#80ffd0'; g.fillRect(GX, GY, PS, PS); g.globalAlpha = 0.25; g.drawImage(glow('#80ffd0', 3 * U), GX - 3 * U, GY - 3 * U); }
      };
    }
    // a scooter's tail-light far along the shore road
    (A.streets || []).forEach((st, i) => {
      const pts = st.pts, L = st.layer || 'mid', [AX, AY] = P(pts[0][0], pts[0][1], L), [BX, BY] = P(pts[pts.length - 1][0], pts[pts.length - 1][1], L);
      const a = actor('scooter', L, {});
      a.upd = (T) => {
        const e = slotEv(4100 + i, T, 210, 0.55, 55); if (!e.on) { a.on = false; box(a, 0, 0, 0, 0); a.wake = e.next; return 'off'; }
        const dir = hash(4100, e.n, 1) < 0.5, u = dir ? e.u : 1 - e.u; a.on = true; a.dir = dir;
        a.X = Math.round(lerp(AX, BX, u)); a.Y = Math.round(lerp(AY, BY, u)); box(a, a.X - 4 * U, a.Y - 4 * U, 9 * U, 7 * U); a.wake = T + FR15; return a.X * 1e4 + a.Y;
      };
      a.draw = (g) => {
        if (!a.on) return; const back = a.dir ? -U : U;
        g.globalAlpha = 0.9; g.fillStyle = C.red; g.fillRect(a.X - back, a.Y - U, U, U); g.globalAlpha = 0.25; g.fillRect(a.X - back, a.Y + U, U, U);
        g.globalAlpha = 0.7; g.fillStyle = '#fff2d0'; g.fillRect(a.X + back * 2, a.Y - U, U, U); g.globalAlpha = 0.18; g.drawImage(glow('#fff2d0', 3 * U), a.X + back * 3 - 3 * U, a.Y - 4 * U);
      };
    });
    // bicycles left out: a spoke or a bell catches a light, once in a while
    (A.bikes || []).forEach((b, i) => {
      const L = b.layer || 'near', [X, Y] = P(b.x + b.w * hash(i, 1, 4200), b.y + b.h * 0.3, L), a = actor('bikeglint', L, {}); box(a, X - U, Y - U, 3 * U, 3 * U);
      a.upd = (T) => { const e = slotEv(4200 + i, T, 40, 0.6, 0.8); a.on = e.on; a.lv = e.on ? (e.u < 0.3 || e.u > 0.7 ? 1 : 2) : 0; a.wake = e.on ? T + 0.1 : e.next; return a.lv; };
      a.draw = (g) => { if (!a.lv) return; g.fillStyle = '#ffffff'; g.globalAlpha = a.lv === 2 ? 0.9 : 0.4; g.fillRect(X, Y, U, U); if (a.lv === 2) { g.globalAlpha = 0.3; g.fillRect(X - U, Y, U, U); g.fillRect(X + U, Y, U, U); g.fillRect(X, Y - U, U, U); g.fillRect(X, Y + U, U, U); } };
    });
  }

  /* ---------------------------------------------------------------- presence: someone was just here */
  function presence() {
    // the corner shop, open and empty: its tubes hum, one hesitates, nobody at the till
    if (A.shop) {
      const s = A.shop, L = s.layer || 'near', [X, Y] = P(s.x, s.y, L), [X1, Y1] = P(s.x + s.w, s.y + s.h, L), w = X1 - X, h = Y1 - Y, a = actor('shop', L, {});
      box(a, X - 4 * U, Y - 2 * U, w + 8 * U, h + 8 * U);
      a.upd = (T) => {
        let v = 1; const e = reduced ? { on: false, next: T + 60 } : slotEv(4300, T, 130, 0.5, 2.2);
        if (e.on) v = hash(4300, Math.floor(e.u * 16), 2) < 0.5 ? 0.4 : 1;
        a.lv = v; a.wake = e.on ? T + 0.12 : Math.min(e.next, T + 30); return v;
      };
      a.draw = (g) => {
        g.globalAlpha = 0.22; g.fillStyle = '#e8f4ff'; g.fillRect(X, Y, w, h);
        const n = Math.max(1, Math.round(w / (8 * U)));
        for (let k = 0; k < n; k++) { g.globalAlpha = k === 1 % n ? 0.85 * a.lv : 0.85; g.fillStyle = '#f4fbff'; g.fillRect(X + Math.round((k + 0.2) * w / n), Y + U, Math.round(w / n * 0.6), U); }
        g.globalAlpha = 0.12; g.fillStyle = '#d0e8ff'; g.fillRect(X, Y + h, w, 3 * U); g.globalAlpha = 0.06; g.fillRect(X - 2 * U, Y + h + 3 * U, w + 4 * U, 3 * U);   // its light lying on the wet street
      };
    }
    // the bench: someone sat here a while ago; a warmth lifts off it and goes
    if (A.bench && !reduced) {
      const b = A.bench, L = b.layer || 'near', [X, Y] = P(b.x, b.y, L), [X1] = P(b.x + b.w, b.y, L), w = X1 - X;
      for (let j = 0; j < 4; j++) {
        const a = actor('warmth', L, {});
        a.upd = (T) => {
          const e = slotEv(4400, T, 360, 0.6, 60);
          if (!e.on) { a.on = false; box(a, 0, 0, 0, 0); a.wake = e.next; return 'off'; }
          const per = 7, f = ((T - e.t0) / per + j / 4) % 1, k = Math.floor((T - e.t0) / per + j / 4);
          a.on = true; a.X = Math.round(X + w * hash(j, k, 4401)); a.Y = Math.round(Y - f * 14 * U); a.lv = Math.round(Math.sin(f * Math.PI) * (1 - e.u) * 6);
          box(a, a.X, a.Y, U, U); a.wake = T + 0.25; return a.X * 1e4 + a.Y * 10 + a.lv;
        };
        a.draw = (g) => { if (a.on && a.lv > 0) { g.globalAlpha = a.lv / 6 * 0.45; g.fillStyle = '#ffc890'; g.fillRect(a.X, a.Y, U, U); } };
      }
    }
    // the late walker on the stair lane, under an umbrella; their footprints shine a while and dry
    if (A.stairs && A.stairs.length && !reduced) {
      const st = A.stairs[0], pts = st.pts, L = st.layer || 'near';
      const walkAt = (T) => slotEv(4500, T, 260, 0.6, 70);
      const down = pts[0][1] < pts[pts.length - 1][1], posAt = (u) => along(pts, down ? u : 1 - u);     // always going down the steps
      const hy = (A.camera && A.camera.hy) || 0, sizeAt = (y, rows) => A.design === 320 ? null : Math.max(U, Math.round(0.026 * (y - hy) * view.scale / rows));
      const off = (u, n) => (hash(4500, n, 3) - 0.5) * (st.w0 || 20) * 0.3 + Math.sin(u * 5) * (st.w0 || 20) * 0.04;
      const a = actor('walker', L, {});
      a.upd = (T) => {
        const e = walkAt(T); if (!e.on) { a.on = false; box(a, 0, 0, 0, 0); a.wake = e.next; return 'off'; }
        const u = e.u, [x, y] = posAt(u), [X, Y] = P(x + off(u, e.n), y, L);
        const su = sizeAt(y, 11) || Math.max(U, Math.round(U * (1 + u * 2)));
        a.on = true; a.su = su; a.f = ((T / 0.45) | 0) % 2; a.X = X - 4 * su; a.Y = Y - 11 * su; a.al = Math.min(1, u * 8, (1 - u) * 8) * 0.75;
        a.al = Math.round(a.al * 8) / 8; box(a, a.X, a.Y, 9 * su, 11 * su); a.wake = T + 0.15; return a.X * 1e4 + a.Y * 4 + a.f * 2 + a.al;
      };
      a.draw = (g) => { if (!a.on) return; g.globalAlpha = a.al; g.drawImage(sprite((a.f ? 'walkA' : 'walkB'), a.f ? SPR.walkA : SPR.walkB, SPAL.walk, a.su), a.X, a.Y); };
      // footprints: appear as the walker passes, drying over three minutes
      for (let j = 0; j < 14; j++) {
        const f = actor('footprint', L, {}), uj = (j + 0.5) / 14;
        f.upd = (T) => {
          // the latest walk whose walker has passed this step
          let e = walkAt(T), tPass = -1;
          if (e.on && e.u > uj) tPass = e.t0 + uj * 70;
          if (tPass < 0) { const p = walkAt(T - 260); if (p.on || p.n !== undefined) { const n = Math.floor(T / 260); for (let m = n; m >= n - 1; m--) { if (hash(4500, m, 1) < 0.6) { const t0 = m * 260 + hash(4500, m, 2) * (260 - 70); if (T > t0 + uj * 70) { tPass = t0 + uj * 70; e = { n: m }; break; } } } } }
          const age = tPass < 0 ? 1e9 : T - tPass;
          if (age > 180) { f.on = false; box(f, 0, 0, 0, 0); f.wake = e.on && e.u <= uj ? e.t0 + uj * 70 : Math.min(walkAt(T).next, T + 30); return 'off'; }
          const [x, y] = posAt(uj), [X, Y] = P(x + off(uj, e.n) + ((j % 2) ? 1 : -1) * (A.design === 320 ? 0.6 : 4), y, L);
          f.on = true; f.X = X; f.Y = Y; f.lv = Math.round((1 - age / 180) * 6); f.su = Math.max(U, Math.round((sizeAt(y, 11) || U * (1 + uj * 1.5)) * 0.8)); box(f, X, Y, f.su, 2 * f.su); f.wake = T + 3; return f.lv;
        };
        f.draw = (g) => { if (f.on && f.lv > 0) { g.globalAlpha = f.lv / 6 * 0.3; g.fillStyle = C.wet; g.fillRect(f.X, f.Y, f.su, 2 * f.su); } };
      }
    }
  }

  /* ---------------------------------------------------------------- the air: mist and the quiet company in it */
  function air() {
    if (reduced) return;
    const L = 'top';
    // mist banks over the water and the low town, drifting, thinning toward dawn
    ((A.regions && A.regions.haze) || []).forEach((hz, i) => {
      const [, Y0] = P(0, hz.y0, 'mid'), [, Y1] = P(0, hz.y1, 'mid'), [X0] = P(0, 0, 'mid'), [X1] = P(A.w, 0, 'mid');
      for (let j = 0; j < 2; j++) {
        const w = Math.round((X1 - X0) * (0.5 + 0.3 * hash(i, j, 4600))), h = Math.max(4, Y1 - Y0), strip = softStrip('mist' + i + j, w, h, '#a898d0', 0.1, 500 + i * 3 + j, 34);
        const v = (1 + 1.5 * hash(i, j, 4601)) * U / 10 * (j ? -1 : 1), span = X1 - X0 + w, a = actor('mist', L, {});
        a.upd = (T) => {
          const x = X0 - w + Math.floor((((T * v + hash(i, j, 4602) * span) % span) + span) % span);
          a.X = x; a.lv = Math.round((0.45 + 0.55 * wet()) * (0.7 + 0.3 * vnoise(4600 + i * 2 + j, T / 30)) * 10); box(a, x, Y0, w, h); a.wake = T + Math.max(0.5, 1 / Math.abs(v)); return x * 100 + a.lv;
        };
        a.draw = (g) => { g.globalAlpha = a.lv / 10; g.drawImage(strip, a.X, Y0); };
      }
    });
    // motes: a few faint warm lights drifting in the open, as if someone just walked through
    ((A.regions && A.regions.ghost) || []).forEach((r, i) => {
      const [X0, Y0] = P(r.x, r.y, 'mid'), [X1, Y1] = P(r.x + r.w, r.y + r.h, 'mid');
      for (let j = 0; j < 7; j++) {
        const a = actor('mote', L, {}), id = 4700 + i * 16 + j, life = 24 + 20 * hash(i, j, 4700);
        a.upd = (T) => {
          const k = Math.floor(T / life + hash(i, j, 4701)), f = T / life + hash(i, j, 4701) - k;
          const x = lerp(X0, X1, hash(id, k, 1)) + (vnoise(id, T / 9) - 0.5) * 40 * U + f * 12 * U, y = lerp(Y0, Y1, hash(id, k, 2)) - f * 18 * U + (vnoise(id + 50, T / 7) - 0.5) * 16 * U;
          a.X = Math.round(x / U) * U; a.Y = Math.round(y / U) * U; a.lv = Math.round(Math.sin(f * Math.PI) ** 2 * 6 * (0.8 + 0.4 * deep()));
          a.c = hash(id, k, 3) < 0.6 ? '#ffd8a8' : '#d8d0ff'; box(a, a.X - U, a.Y - U, 3 * U, 3 * U); a.wake = T + 0.2; return a.X * 1e5 + a.Y * 10 + a.lv;
        };
        a.draw = (g) => { if (a.lv <= 0) return; g.fillStyle = a.c; g.globalAlpha = a.lv / 6 * 0.35; g.fillRect(a.X, a.Y, U, U); g.globalAlpha = a.lv / 6 * 0.1; g.fillRect(a.X - U, a.Y, U, U); g.fillRect(a.X + U, a.Y, U, U); g.fillRect(a.X, a.Y - U, U, U); g.fillRect(a.X, a.Y + U, U, U); };
      }
    });
  }

  /* ================================================================== the loop */
  function listen(T) {
    if (!analyser) return;
    if (!bins) bins = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(bins);
    let b = 0, l = 0; for (let k = 1; k < 8; k++) b += bins[k]; for (let k = 1; k < 128; k++) l += bins[k];
    b /= 7 * 255; l /= 127 * 255;
    bass = bass * 0.7 + b * 0.3;
    if (l > 0.02 && l > lvlSlow * 1.35 + 0.015 && T - lastOnset > 0.7 && A.puddles && A.puddles.length) {
      lastOnset = T; const p = (hash(T * 10 | 0, 1, 5000) * A.puddles.length) | 0;
      onsets.push({ t: T, p, j: (hash(T * 10 | 0, 2, 5000) * 3) | 0, x: 0.2 + 0.6 * hash(T * 10 | 0, 3, 5000), y: 0.3 + 0.4 * hash(T * 10 | 0, 4, 5000) });
      while (onsets.length > 6) onsets.shift();
      for (const a of actors) if (a.kind === 'ripple') a.wake = Math.min(a.wake, T);
    }
    lvlSlow = lvlSlow * 0.9 + l * 0.1; level = l;
    if (l < 0.004) bass *= 0.5;
  }
  let lastListen = 0, lastBeatT = -1e9;
  function tick() {
    raf = 0; if (paused || dead) return;
    const T = now(); let next = Infinity, nextFast = Infinity;
    if (analyser && T - lastListen > 0.1) { lastListen = T; listen(T); }
    for (const a of actors) {
      if (a.wake <= T) {
        const ox = a.bx, oy = a.by, ow = a.bw, oh = a.bh, k = a.upd(T);
        if (k !== a.key) {
          a.key = k; if (ow) dirty(a.s, ox, oy, ow, oh); markOccluded(a); if (a.fast) a.s.urgent = true;
          if (!a.occluded && a.bw) dirty(a.s, a.bx, a.by, a.bw, a.bh);
        }
        if (!(a.wake > T)) a.wake = T + 1;     // never spin
      }
      if (a.fast) { if (a.wake < nextFast) nextFast = a.wake; } else if (a.wake < next) next = a.wake;
    }
    let flushed = 0;
    for (const s of allSurfs()) {
      if (!s.any) continue; flushed = 1;
      if (s.urgent || T - s.last >= 1 / s.rate - 0.02) { flush(s); s.last = T; s.urgent = false; }
      else next = Math.min(next, s.last + 1 / s.rate);
    }
    stat.frames++; stat.paints += flushed;
    const el = performance.now() - stat.since; if (el > 2000) { stat.fps = stat.frames * 1000 / el; stat.pps = stat.paints * 1000 / el; stat.paints = 0; stat.pxs = stat.px * 1000 / el; stat.frames = 0; stat.px = 0; stat.since = performance.now(); }
    if (analyser) next = Math.min(next, T + 0.1);
    // frames fall on a shared grid: ambient things on a 3 fps beat (6 while music plays), fast movers (a train, a satellite) on 8 fps,
    // so the two never interleave into more frames than the faster beat
    // while music plays the page is repainting anyway, so life can afford a quicker beat
    const music = (analyser && level > 0.01) || now() - lastBeatT < 2.5, BEAT = music ? BEAT_MUSIC : BEAT_IDLE;
    for (const s of allSurfs()) s.rate = BEAT;
    next = Math.ceil(Math.max(next, T + 0.001) * BEAT) / BEAT;
    if (nextFast < Infinity) next = Math.min(next, Math.ceil(Math.max(nextFast, T + 0.001) * BEAT_FAST) / BEAT_FAST);
    schedule((next - now()) / timeScale);
  }
  function schedule(dt) {
    if (paused || dead) return;
    clearTimeout(timer);
    const ms = Math.max(1000 / 30, Math.min(60000, dt * 1000 - 4));
    timer = setTimeout(() => { timer = 0; if (!raf) raf = requestAnimationFrame(tick); }, ms);
  }
  function wakeAll() { const T = now(); for (const a of actors) a.wake = Math.min(a.wake, T); }

  const onVis = () => { if (document.hidden) ctl.pause(true); else ctl.resume(true); };
  let userPaused = false;
  const ctl = {
    setAnalyser(n) { analyser = n || null; bins = null; schedule(0); },
    pause(auto) { if (!auto) userPaused = true; paused = true; clearTimeout(timer); timer = 0; if (raf) cancelAnimationFrame(raf); raf = 0; },
    resume(auto) { if (!auto) userPaused = false; if (dead || (auto && userPaused) || document.hidden) return; paused = false; wakeAll(); schedule(0); },
    resize() { if (dead) return; computeView(); build(); schedule(0); },
    setTime(h) {
      if (typeof h === 'number' && isFinite(h) && Math.abs(h - hours) > 0.01) {
        const big = Math.round(h * 10) !== Math.round(hours * 10); hours = clamp(h, 18, 31); wakeAll();
        if (big && A) fullRedraw(); schedule(0);
      }
    },
    time() { return hours; },
    onTrack(n, info) { /* a fresh track: a ripple in the nearest puddle, a breath of the moon */ const T = now(); if (A.puddles && A.puddles.length) { onsets.push({ t: T, p: 0, j: 0, x: 0.5, y: 0.5 }); wakeAll(); schedule(0); } },
    onBeat() { lastBeatT = now(); if (!analyser) { bass = Math.min(1, bass + 0.25); setTimeout(() => { bass *= 0.5; }, 200); } },
    setOccluders(list) {
      const dpr = opts.dpr || window.devicePixelRatio || 1;
      occl = (list || []).map((r) => ({ x: Math.round(r.x * dpr), y: Math.round(r.y * dpr), w: Math.round(r.w * dpr), h: Math.round(r.h * dpr) }));
      for (const a of actors) markOccluded(a); fullRedraw();
    },
    stats() { return { fps: +stat.fps.toFixed(1), paintsPerSec: +stat.pps.toFixed(1), actors: actors.length, kinds: kinds.size, kindList: [...kinds], drawnPxPerSec: Math.round(stat.pxs), U, hours }; },
    destroy() { dead = true; ctl.pause(); removeEventListener('resize', onResize); document.removeEventListener('visibilitychange', onVis); for (const s of allSurfs()) s.ctx.clearRect(0, 0, s.cv.width, s.cv.height); if (opts._own) opts._own.remove(); },
    get ready() { return !!A; },
  };
  let rz = 0; const onResize = () => { clearTimeout(rz); rz = setTimeout(() => ctl.resize(), 150); };

  async function init() {
    if (scene && scene.ready && typeof scene.ready.then === 'function') { try { await scene.ready; } catch (e) { scene = null; } }
    if (scene && !scene.anchors) scene = null;      // no scene after all: the old night, on our own canvas
    if (scene && scene.anchors) {
      const v = typeof scene.view === 'function' ? scene.view() : {};
      A = normalize(Object.assign({ w: v.w || 2560, h: v.h || 1440 }, scene.anchors));
    }
    else if (opts.anchors) A = normalize(opts.anchors);
    else { const r = await fetch(opts.oldScene || 'art/scene.json'); A = adaptOld(await r.json()); }
    if (A.seed != null) SEED = A.seed | 0; if (opts.seed != null) SEED = opts.seed | 0;
    // the scene's transform changes on resize and, eased in a few steps, on pointer parallax: rebuild once it settles
    let chT = 0; if (scene && typeof scene.onChange === 'function') scene.onChange(() => { clearTimeout(chT); chT = setTimeout(() => ctl.resize(), 120); });
    if (scene && typeof scene.onMood === 'function' && opts.followSceneMood) scene.onMood((t) => ctl.setTime(19.5 + 10 * t));
    computeView(); build();
    addEventListener('resize', onResize); document.addEventListener('visibilitychange', onVis);
    if (!document.hidden) schedule(0); else paused = true;
  }
  ctl.ready_promise = init().catch((e) => { console.warn('life:', e); });
  return ctl;
}

const Life = {
  // CityLife.start(container, {dpr, reduced, scene, analyser, seed, hours})
  start(container, opts) { return create(Object.assign({}, opts, { container })); },
  // Life.mount(canvas, scene, {analyser, ...})
  mount(canvas, scene, opts) { return create(Object.assign({}, opts, { canvas, scene })); },
  version: 1,
};
window.CityLife = Life; window.Life = Life;
})();

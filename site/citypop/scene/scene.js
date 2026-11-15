/* CITYPOP DEPROGRAMMED: the night scene. Onomichi after the rain, drawn at device pixels.
   Five layers (sky, far, mid, near, fg), each an indexed PNG whose palette drifts through the night.
   API: see SCENE-API.md.  window.CityScene (alias window.Scene). No modules, no dependencies. */
(function () {
  'use strict';
  const ORDER = ['sky', 'far', 'mid', 'near', 'fg'];
  const MOODS = ['rain', 'deep', 'predawn', 'dawn'];
  const MOOD_TIMES = { rain: 19.5, deep: 24.5, predawn: 27.8, dawn: 29.5 };
  // per-mood light colours for the life lane to tint its sprites with
  const MOOD_COLORS = {
    rain:    { sky: [24, 22, 66], glow: [255, 196, 120], warm: [255, 208, 138], water: [26, 24, 70], haze: [52, 36, 96], moon: [236, 230, 250] },
    deep:    { sky: [12, 13, 46], glow: [255, 190, 110], warm: [255, 208, 138], water: [14, 15, 48], haze: [36, 30, 82], moon: [244, 240, 251] },
    predawn: { sky: [30, 40, 96], glow: [230, 180, 130], warm: [232, 190, 140], water: [26, 34, 84], haze: [60, 70, 130], moon: [220, 226, 246] },
    dawn:    { sky: [96, 108, 168], glow: [255, 200, 160], warm: [240, 190, 150], water: [70, 80, 140], haze: [150, 140, 180], moon: [236, 236, 246] },
  };

  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

  function hoursToMood(h) {           // -> {a, b, t, u (0..1 across the night)}
    const keys = MOODS.map((m) => MOOD_TIMES[m]);
    h = clamp(h, keys[0], keys[keys.length - 1]);
    let i = 0;
    while (i < keys.length - 2 && h > keys[i + 1]) i++;
    const t = (h - keys[i]) / (keys[i + 1] - keys[i]);
    return { a: MOODS[i], b: MOODS[i + 1], t: clamp(t, 0, 1), u: (h - keys[0]) / (keys[keys.length - 1] - keys[0]) };
  }

  function loadImage(src) {
    return new Promise((res, rej) => { const i = new Image(); i.decoding = 'async'; i.onload = () => res(i); i.onerror = () => rej(new Error('scene: ' + src)); i.src = src; });
  }

  function start(container, opts) {
    opts = opts || {};
    const base = opts.base || '';
    const reduced = opts.reduced != null ? !!opts.reduced : matchMedia('(prefers-reduced-motion: reduce)').matches;
    const S = {
      doc: null, variant: null, V: null, layers: {}, overlays: [], listeners: [], moodListeners: [],
      dw: 0, dh: 0, dpr: 1, scale: 1, ox: 0, oy: 0, par: {}, target: { x: 0, y: 0 }, cur: { x: 0, y: 0 },
      hours: opts.time != null ? opts.time : 24.5, paletteKey: '', paused: false, raf: 0, destroyed: false,
    };
    ORDER.forEach((n) => { S.par[n] = [0, 0]; });
    if (getComputedStyle(container).position === 'static') container.style.position = 'fixed';

    // the variant whose whole-number scale covers the screen with the least crop:
    // hd 1920x1080 (1080p at 1x, 4K at 2x, most laptops at 2x), desktop 2560x1440, portrait 1170x2532
    // scale that covers dw x dh with variant V: whole multiples where the crop stays modest,
    // else nearest-neighbour cover at a fractional scale (on HiDPI screens the uneven columns are invisible)
    function fitScale(V, dw, dh, dpr) {
      const pad = V.pad || 16;
      let s = Math.max(dw / (V.w - 2 * pad), dh / (V.h - 2 * pad));
      if (s <= 1) return { s: 1, tight: false };
      if (s <= 1.06) return { s: 1, tight: true };            // nearly exact: spend the parallax margin instead
      const k = Math.ceil(s);
      if (k / s <= (dpr >= 1.75 ? 1.15 : 1.45)) return { s: k, tight: false };
      return { s, tight: false };
    }
    function pickVariant() {
      if (opts.variant) return opts.variant;
      const vs = (S.doc && S.doc.variants) || {};
      const dpr = opts.dpr || window.devicePixelRatio || 1;
      const dw = innerWidth * dpr, dh = innerHeight * dpr;
      if (innerWidth / Math.max(1, innerHeight) < 0.8 && vs.portrait) return 'portrait';
      let best = null, cost = 1e9;
      for (const v of ['hd', 'desktop']) {
        const V = vs[v]; if (!V) continue;
        const f = fitScale(V, dw, dh, dpr);
        const c = 1 - Math.min(1, (dw * dh) / (V.w * f.s * V.h * f.s)) + (Number.isInteger(f.s) ? 0 : 0.2);
        if (c < cost) { cost = c; best = v; }
      }
      return best || (vs.desktop ? 'desktop' : Object.keys(vs)[0]);
    }

    // ------------------------------------------------------------ geometry
    function layout() {
      const dpr = opts.dpr || window.devicePixelRatio || 1;
      const r = container.getBoundingClientRect();
      const cw = r.width || innerWidth, ch = r.height || innerHeight;
      S.dpr = dpr;
      S.dw = Math.max(1, Math.round(cw * dpr)); S.dh = Math.max(1, Math.round(ch * dpr));
      if (!S.V) return;
      const { w, h } = S.V, pad = S.V.pad || 16;
      const fit = fitScale(S.V, S.dw, S.dh, dpr);
      const s = fit.s, tight = fit.tight;
      S.scale = s;
      const fx = S.V.focus ? S.V.focus[0] : 0.5, fy = S.V.focus ? S.V.focus[1] : 0.5;
      const pd = tight ? 0 : pad;
      const minX = Math.min(0, S.dw - (w - pd) * s), maxX = -pd * s;
      const minY = Math.min(0, S.dh - (h - pd) * s), maxY = -pd * s;
      let ox = S.dw / 2 - fx * w * s, oy = S.dh / 2 - fy * h * s;
      // never crop the moon: keep it and its glow inside the frame when the crop is tight
      const mo = S.V.anchors && S.V.anchors.moon;
      if (mo) {
        const top = mo.y - mo.r * 2.2, right = mo.x + mo.r * 2.2, left = mo.x - mo.r * 2.2;
        oy = Math.max(oy, -top * s);
        ox = Math.min(Math.max(ox, -left * s), S.dw - right * s);
      }
      S.ox = Math.round(clamp(ox, minX, maxX));
      S.oy = Math.round(clamp(oy, minY, maxY));
      const all = ORDER.map((n) => S.layers[n] && S.layers[n].cv).concat(S.overlays.map((o) => o.cv));
      for (const cv of all) {
        if (!cv) continue;
        if (cv.width !== S.dw || cv.height !== S.dh) { cv.width = S.dw; cv.height = S.dh; }
        cv.style.width = cw + 'px'; cv.style.height = ch + 'px';
      }
    }

    function draw(name) {
      const L = S.layers[name];
      if (!L || !L.src) return;
      const ctx = L.ctx, s = S.scale, [dx, dy] = S.par[name];
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, S.dw, S.dh);
      ctx.drawImage(L.src, 0, 0, S.V.w, S.V.h, S.ox + Math.round(dx * s), S.oy + Math.round(dy * s), Math.round(S.V.w * s), Math.round(S.V.h * s));
    }
    function drawAll() { ORDER.forEach(draw); }
    function changed() { S.listeners.forEach((cb) => { try { cb(api.view()); } catch (e) { console.error(e); } }); }

    // ------------------------------------------------------------ palettes (mood drift)
    function moodPalette(L, m) {
      const A = L.meta.moods[m.a], B = L.meta.moods[m.b], n = A.length;
      const out = new Uint32Array(n + 1);
      for (let i = 0; i < n; i++) {
        const r = Math.round(lerp(A[i][0], B[i][0], m.t)), g = Math.round(lerp(A[i][1], B[i][1], m.t)), b = Math.round(lerp(A[i][2], B[i][2], m.t));
        out[i + 1] = (255 << 24) | (b << 16) | (g << 8) | r;
      }
      return out;
    }
    function recolor(name, m) {
      const L = S.layers[name];
      if (!L || !L.idx) return;
      const lut = moodPalette(L, m), idx = L.idx, px = L.u32;
      for (let i = 0, n = idx.length; i < n; i++) px[i] = lut[idx[i]];
      L.sctx.putImageData(L.img, 0, 0);
    }
    let moodQueue = [];
    function applyMood(force) {
      const m = hoursToMood(S.hours);
      const key = m.a + m.b + Math.round(m.t * 240);
      if (!force && key === S.paletteKey) return;
      S.paletteKey = key;
      moodQueue = ORDER.filter((n) => S.layers[n] && S.layers[n].idx);
      pumpMood(m);
      S.moodListeners.forEach((cb) => { try { cb(m.u, api.moodColors(m.u)); } catch (e) { console.error(e); } });
    }
    function pumpMood(m) {
      // one layer per frame, so a palette step never costs a long frame
      const n = moodQueue.shift();
      if (!n) return;
      recolor(n, m); draw(n);
      if (moodQueue.length) requestAnimationFrame(() => pumpMood(m));
    }

    // ------------------------------------------------------------ loading
    async function loadVariant(v) {
      const V = S.doc.variants[v];
      S.variant = v; S.V = V; S.paletteKey = '';
      // canvases (reuse across variant switches)
      ORDER.forEach((n, z) => {
        let L = S.layers[n];
        if (!L) {
          const cv = document.createElement('canvas');
          cv.className = 'scene-layer scene-' + n;
          cv.setAttribute('aria-hidden', 'true');
          Object.assign(cv.style, { position: 'absolute', left: '0', top: '0', zIndex: String(z * 10), imageRendering: 'pixelated', pointerEvents: 'none' });
          container.appendChild(cv);
          L = S.layers[n] = { cv, ctx: cv.getContext('2d') };
        }
        L.meta = V.layers[n]; L.src = null; L.idx = null;
      });
      layout();
      const m = hoursToMood(S.hours);
      let first = true;
      // sky and far first: the page shows the night quickly, the town settles in after
      for (const n of (V.order || ORDER)) {
        const meta = V.layers[n];
        const img = await loadImage(base + meta.src);
        if (S.variant !== v || S.destroyed) return;
        const L = S.layers[n];
        const sc = document.createElement('canvas'); sc.width = V.w; sc.height = V.h;
        const sctx = sc.getContext('2d', { willReadFrequently: true });
        sctx.drawImage(img, 0, 0);
        const id = sctx.getImageData(0, 0, V.w, V.h);
        const u32 = new Uint32Array(id.data.buffer);
        const pal = meta.palette, map = new Map();
        pal.forEach((c, i) => map.set((255 << 24 | c[2] << 16 | c[1] << 8 | c[0]) >>> 0, i + 1));
        const idx = new Uint8Array(V.w * V.h);
        let miss = new Map();
        for (let i = 0, N = u32.length; i < N; i++) {
          const c = u32[i];
          if ((c >>> 24) < 128) continue;
          const k = map.get((c | 0xff000000) >>> 0);
          if (k !== undefined) { idx[i] = k; continue; }
          let j = miss.get(c);                                // colour-managed decode: nearest entry
          if (j === undefined) {
            const r = c & 255, g = (c >> 8) & 255, b = (c >> 16) & 255; let bd = 1e9; j = 1;
            for (let q = 0; q < pal.length; q++) { const d = (pal[q][0] - r) ** 2 + (pal[q][1] - g) ** 2 + (pal[q][2] - b) ** 2; if (d < bd) { bd = d; j = q + 1; } }
            miss.set(c, j);
          }
          idx[i] = j;
        }
        Object.assign(L, { src: sc, sctx, img: id, u32, idx });
        if (m.a !== 'deep' || m.t > 0.001 || m.b !== 'deep') recolor(n, m);
        draw(n);
        if (first) { first = false; }
      }
      S.paletteKey = '';
      applyMood(true);
      drawAll();
      changed();
    }

    // ------------------------------------------------------------ parallax: gentle, pointer only, integer art pixels
    const MAXP = 10;   // art pixels at depth 1
    function onPointer(e) {
      if (reduced || S.paused) return;
      S.target.x = clamp((e.clientX / innerWidth) * 2 - 1, -1, 1);
      S.target.y = clamp((e.clientY / innerHeight) * 2 - 1, -1, 1);
      if (!S.raf) S.raf = requestAnimationFrame(stepParallax);
    }
    let lastStep = 0;
    function stepParallax(now) {
      S.raf = 0;
      if (now - lastStep < 66) { S.raf = requestAnimationFrame(stepParallax); return; }   // ~15 fps easing
      lastStep = now;
      S.cur.x += (S.target.x - S.cur.x) * 0.25;
      S.cur.y += (S.target.y - S.cur.y) * 0.25;
      let moved = false;
      for (const n of ORDER) {
        const d = S.V ? S.V.layers[n].depth : 0;
        const nx = -Math.round(S.cur.x * d * MAXP), ny = -Math.round(S.cur.y * d * MAXP * 0.5);
        if (nx !== S.par[n][0] || ny !== S.par[n][1]) { S.par[n] = [nx, ny]; draw(n); moved = true; }
      }
      if (moved) changed();
      if (Math.abs(S.target.x - S.cur.x) > 0.01 || Math.abs(S.target.y - S.cur.y) > 0.01) S.raf = requestAnimationFrame(stepParallax);
    }

    // ------------------------------------------------------------ resize / dpr
    let rzT = 0;
    function onResize() {
      clearTimeout(rzT);
      rzT = setTimeout(() => {
        const v = pickVariant();
        if (S.doc && v !== S.variant && S.doc.variants[v]) { loadVariant(v).then(changed); return; }
        layout(); drawAll(); changed();
      }, 120);
    }
    let mq = null;
    function watchDpr() {
      if (mq) mq.removeEventListener('change', onDpr);
      mq = matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
      mq.addEventListener('change', onDpr);
    }
    function onDpr() { watchDpr(); onResize(); }
    addEventListener('resize', onResize);
    addEventListener('pointermove', onPointer, { passive: true });
    watchDpr();

    // ------------------------------------------------------------ the controller
    const api = {
      get anchors() { return S.V ? S.V.anchors : null; },
      get variant() { return S.variant; },
      ready: null,
      setTime(h) { S.hours = +h; if (S.V) applyMood(false); },
      setMood(t) { api.setTime(MOOD_TIMES.rain + clamp(+t, 0, 1) * (MOOD_TIMES.dawn - MOOD_TIMES.rain)); },
      mood() { return hoursToMood(S.hours).u; },
      time() { return S.hours; },
      moodColors(t) {
        const m = hoursToMood(t == null ? S.hours : MOOD_TIMES.rain + clamp(t, 0, 1) * (MOOD_TIMES.dawn - MOOD_TIMES.rain));
        const A = MOOD_COLORS[m.a], B = MOOD_COLORS[m.b], out = {};
        for (const k in A) out[k] = 'rgb(' + A[k].map((v, i) => Math.round(lerp(v, B[k][i], m.t))).join(',') + ')';
        return out;
      },
      onMood(cb) { S.moodListeners.push(cb); },
      // the current (mood-drifted) css colour of the palette entry nearest to rgb in that layer's night palette
      moodColor(layer, rgb) {
        const L = S.layers[layer || 'near'];
        if (!L || !L.meta) return 'rgb(' + rgb.join(',') + ')';
        const pal = L.meta.palette;
        let j = 0, bd = 1e9;
        for (let q = 0; q < pal.length; q++) { const d = (pal[q][0] - rgb[0]) ** 2 + (pal[q][1] - rgb[1]) ** 2 + (pal[q][2] - rgb[2]) ** 2; if (d < bd) { bd = d; j = q; } }
        return api.paletteColor(layer, j + 1);
      },
      // idx is 1-based, as in the PNG (0 = transparent)
      paletteColor(layer, idx) {
        const L = S.layers[layer || 'near'];
        if (!L || !L.meta || idx < 1) return 'rgba(0,0,0,0)';
        const m = hoursToMood(S.hours), A = L.meta.moods[m.a][idx - 1], B = L.meta.moods[m.b][idx - 1];
        return 'rgb(' + A.map((v, i) => Math.round(lerp(v, B[i], m.t))).join(',') + ')';
      },
      onChange(cb) { S.listeners.push(cb); },
      view() {
        const par = {};
        ORDER.forEach((n) => { par[n] = S.par[n].slice(); });
        return { variant: S.variant, w: S.V ? S.V.w : 0, h: S.V ? S.V.h : 0, scale: S.scale, dpr: S.dpr, ox: S.ox, oy: S.oy, dw: S.dw, dh: S.dh, parallax: par };
      },
      toScreen(x, y, layer) {
        const p = S.par[layer || 'near'] || [0, 0];
        return [Math.round((x + p[0]) * S.scale + S.ox), Math.round((y + p[1]) * S.scale + S.oy)];
      },
      overlay(name) {
        const z = ORDER.indexOf(name);
        if (z < 0) throw new Error('scene: no layer ' + name);
        const found = S.overlays.find((o) => o.name === name);
        if (found) return found.cv;
        const cv = document.createElement('canvas');
        cv.className = 'scene-overlay scene-over-' + name;
        cv.setAttribute('aria-hidden', 'true');
        Object.assign(cv.style, { position: 'absolute', left: '0', top: '0', zIndex: String(z * 10 + 5), imageRendering: 'pixelated', pointerEvents: 'none' });
        container.appendChild(cv);
        S.overlays.push({ name, cv });
        layout();
        return cv;
      },
      occluders() { /* reserved: the UI may pass window rects; the scene draws everything for now */ },
      pause() { S.paused = true; if (S.raf) { cancelAnimationFrame(S.raf); S.raf = 0; } },
      resume() { S.paused = false; },
      resize() { onResize(); },
      destroy() {
        S.destroyed = true; api.pause();
        removeEventListener('resize', onResize); removeEventListener('pointermove', onPointer);
        if (mq) mq.removeEventListener('change', onDpr);
        ORDER.forEach((n) => S.layers[n] && S.layers[n].cv.remove());
        S.overlays.forEach((o) => o.cv.remove());
      },
    };
    api.ready = fetch(base + (opts.json || 'art/scene2.json'))
      .then((r) => { if (!r.ok) throw new Error('scene: scene2.json ' + r.status); return r.json(); })
      .then((doc) => { S.doc = doc; return loadVariant(pickVariant()); })
      .then(() => api);
    CityScene.current = api;
    return api;
  }

  const CityScene = { start, current: null, version: 2, moods: MOODS.slice(), moodTimes: Object.assign({}, MOOD_TIMES) };
  window.CityScene = CityScene;
  if (!window.Scene) window.Scene = CityScene;
})();

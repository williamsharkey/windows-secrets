/* CITYPOP DEPROGRAMMED: the night outside, the media player, Sound Recorder's wave, the event list, the clock. */
(() => {
'use strict';
const $ = (s) => document.querySelector(s);
const PAL = ['#07081a', '#0d1030', '#171a46', '#23215a', '#33226a', '#4a2470', '#6a2a74', '#8c3478', '#b0507e',
  '#2a1a1c', '#3e2824', '#5a3a2c', '#c89058', '#f0d6a0', '#d8d0f0', '#9a90c8'];
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------------ the night (a 320 x 200 scene, scaled whole) */
const night = { cv: $('#night'), ok: false };
function hexToU32(h) { const r = parseInt(h.slice(1, 3), 16), g = parseInt(h.slice(3, 5), 16), b = parseInt(h.slice(5, 7), 16); return (255 << 24) | (b << 16) | (g << 8) | r; }
const PU = PAL.map(hexToU32);

async function startNight() {
  const [img, meta] = await Promise.all([
    new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = 'art/scene.png'; }),
    fetch('art/scene.json').then((r) => r.json())]);
  const W = meta.w, H = meta.h;
  const off = document.createElement('canvas'); off.width = W; off.height = H;
  const oc = off.getContext('2d', { willReadFrequently: true });
  oc.drawImage(img, 0, 0);
  const base = oc.getImageData(0, 0, W, H);
  const baseU = new Uint32Array(base.data.buffer.slice(0));
  const frame = oc.createImageData(W, H);
  const fu = new Uint32Array(frame.data.buffer);
  const idx = new Uint8Array(W * H);   // palette index of every base pixel
  const lut = new Map(PU.map((u, i) => [u, i]));
  for (let i = 0; i < W * H; i++) idx[i] = lut.has(baseU[i]) ? lut.get(baseU[i]) : 0;
  const wins = meta.windows.map((w) => ({ x: w[0], y: w[1], w: w[2], h: w[3], lit: w[4], to: w[4], k: w[4] ? 1 : 0 }));
  const ripples = [], drops = [];
  let train = null, ghost = null, nextTrain = 40 + Math.random() * 60, nextGhost = 70 + Math.random() * 90;
  const ctx = night.cv.getContext('2d');
  let scale = 1, ox = 0, oy = 0;
  function fit() {
    const dpr = window.devicePixelRatio || 1;
    const cw = Math.round(innerWidth * dpr), ch = Math.round(innerHeight * dpr);
    night.cv.width = cw; night.cv.height = ch;
    scale = Math.max(1, Math.ceil(Math.max(cw / W, ch / H)));      // whole device pixels per scene pixel, covering
    ox = Math.floor((cw - W * scale) / 2); oy = Math.floor((ch - H * scale) * 0.62);
    ctx.imageSmoothingEnabled = false;
  }
  fit(); addEventListener('resize', fit);
  const put = (x, y, c) => { if (x >= 0 && y >= 0 && x < W && y < H) fu[y * W + x] = PU[c]; };
  const mix = (x, y, c, a) => { if (x >= 0 && y >= 0 && x < W && y < H && a > BAYER[(y & 3) * 4 + (x & 3)]) fu[y * W + x] = PU[c]; };
  let t0 = performance.now(), last = 0;
  function draw(now) {
    const t = (now - t0) / 1000, dt = Math.min(0.2, t - last); last = t;
    fu.set(baseU);
    // the haze: a slow, thin mist drifting over the water and the lower town
    const [h0, h1] = meta.haze;
    for (let y = h0; y < h1; y++) {
      const band = Math.sin((y - h0) / (h1 - h0) * Math.PI);
      for (let x = 0; x < W; x++) {
        const v = 0.5 + 0.5 * Math.sin(x * 0.045 + t * 0.07 + Math.sin(y * 0.13 + t * 0.05) * 1.6);
        const a = band * v * 0.16;
        if (a > BAYER[(y & 3) * 4 + (x & 3)]) { const i = idx[y * W + x]; if (i <= 6) fu[y * W + x] = PU[i + 1 <= 6 ? i + 1 : 15]; }
      }
    }
    // the moon's halo breathes
    const [mx, my, mr] = meta.moon;
    const hr = mr * (2.1 + 0.25 * Math.sin(t * 0.21));
    for (let y = Math.floor(my - hr - 2); y <= my + hr + 2; y++) for (let x = Math.floor(mx - hr - 2); x <= mx + hr + 2; x++) {
      const d = Math.hypot(x - mx, y - my);
      if (d > mr + 1 && d < hr) mix(x, y, 15, 0.12 * (1 - (d - mr) / (hr - mr)));
    }
    // stars: a slow twinkle
    for (const s of meta.stars) {
      const v = 0.5 + 0.5 * Math.sin(t * (0.6 + s[2] * 0.9) + s[2] * 40);
      if (v > 0.35) put(s[0], s[1], v > 0.85 ? 14 : v > 0.6 ? 15 : 4);
    }
    // windows: now and then a light goes off, another comes on
    if (Math.random() < dt / 3.5) { const w = wins[(Math.random() * wins.length) | 0]; w.to = w.to ? 0 : 1; }
    for (const w of wins) {
      if (w.k !== w.to) w.k += Math.sign(w.to - w.k) * Math.min(Math.abs(w.to - w.k), dt / 2.5);
      if ((w.lit && w.k < 0.999) || (!w.lit && w.k > 0.001)) for (let y = w.y; y < w.y + w.h; y++) for (let x = w.x; x < w.x + w.w; x++) {
        fu[y * W + x] = PU[w.k > BAYER[(y & 3) * 4 + (x & 3)] ? 12 : 1];
      }
    }
    // drips into the puddles; rings spread and fade
    if (!reduced && Math.random() < dt / 2.6) {
      const p = meta.puddles[(Math.random() * meta.puddles.length) | 0];
      ripples.push({ x: p[0] + (Math.random() - 0.5) * p[2], y: p[1], rx: p[2], ry: p[3], r: 0 });
    }
    for (let i = ripples.length - 1; i >= 0; i--) {
      const r = ripples[i]; r.r += dt * 5;
      const a = 1 - r.r / (r.rx * 0.8);
      if (a <= 0) { ripples.splice(i, 1); continue; }
      const ry = Math.max(0.6, r.r * r.ry / r.rx);
      for (let k = 0; k < 40; k++) {
        const th = k / 40 * Math.PI * 2, x = Math.round(r.x + Math.cos(th) * r.r), y = Math.round(r.y + Math.sin(th) * ry);
        if (idx[y * W + x] >= 2 && idx[y * W + x] <= 6 || idx[y * W + x] === 15) mix(x, y, 14, a * 0.8);
      }
    }
    // a drop now and then from the lamp's arm
    if (!reduced && meta.streetlamp && Math.random() < dt / 7) drops.push({ x: meta.streetlamp[0] - 2, y: meta.streetlamp[1] + 1, v: 0 });
    for (let i = drops.length - 1; i >= 0; i--) {
      const d = drops[i]; d.v += dt * 60; d.y += d.v * dt;
      if (d.y > meta.streetlamp[1] + 26) { drops.splice(i, 1); continue; }
      put(Math.round(d.x), Math.round(d.y), 15);
    }
    // the night train along the shore, every minute or two
    nextTrain -= dt;
    if (!train && nextTrain < 0) { train = { x: -60, cars: 4 + ((Math.random() * 3) | 0) }; nextTrain = 80 + Math.random() * 70; }
    if (train) {
      train.x += dt * 9;
      const y = meta.rail, len = train.cars * 13;
      for (let x = Math.floor(train.x); x < train.x + len; x++) {
        if (x < 0 || x >= W) continue;
        put(x, y, 1); put(x, y - 1, 1); put(x, y - 2, 0);
        if ((x - Math.floor(train.x)) % 13 > 1 && (x - Math.floor(train.x)) % 3 === 0) put(x, y - 1, 13);
      }
      if (train.x > W + 10) train = null;
    }
    // someone walks down the stairs, very faint, and is gone before the bottom
    nextGhost -= dt;
    if (!ghost && nextGhost < 0 && meta.lane) { ghost = { u: 0 }; nextGhost = 120 + Math.random() * 120; }
    if (ghost) {
      ghost.u += dt / 40;
      const [a0, a1, ytop] = meta.lane, u = ghost.u;
      const y = Math.round(ytop + 2 + u * (H - ytop) * 0.7), x = Math.round((a0 + a1) / 2 + Math.sin(u * 9) * 2);
      const hgt = Math.round(3 + u * 10), alpha = 0.32 * Math.sin(Math.min(1, u * 1.3) * Math.PI);
      for (let k = 0; k < hgt; k++) for (let j = -1; j <= 1; j++) mix(x + j, y - k, k > hgt - 3 ? 15 : 3, alpha * (j === 0 ? 1 : 0.6));
      for (let j = -3; j <= 3; j++) mix(x + j, y - hgt - 1, 4, alpha);   // the umbrella
      if (ghost.u >= 1) ghost = null;
    }
    oc.putImageData(frame, 0, 0);
    ctx.drawImage(off, 0, 0, W, H, ox, oy, W * scale, H * scale);
  }
  night.ok = true;
  // a modest frame rate, and nothing at all while the tab is hidden
  let timer = 0;
  function loop() { if (document.hidden) { timer = 0; return; } draw(performance.now()); timer = setTimeout(() => requestAnimationFrame(loop), reduced ? 500 : 83); }
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !timer) loop(); });
  loop();
}
startNight().catch(() => {});

/* ------------------------------------------------------------------ the player */
const A = [new Audio(), new Audio()];     // two decks: the next track waits loaded in the other one
A.forEach((a) => { a.preload = 'auto'; a.crossOrigin = 'anonymous'; });
let cur = 0, deck = 0, album = null, ac = null, an = null, gain = null, evdata = {}, loadedNext = -1;
const opus = A[0].canPlayType('audio/ogg; codecs=opus') !== '' ;
const fmt = (s) => { s = Math.max(0, s | 0); return String((s / 60) | 0).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
const src = (t) => (opus ? t.opus : t.mp3);
const list = $('#list');

function webaudio() {
  if (ac) return;
  try {
    ac = new (window.AudioContext || window.webkitAudioContext)();
    an = ac.createAnalyser(); an.fftSize = 1024; gain = ac.createGain();
    A.forEach((a) => ac.createMediaElementSource(a).connect(gain));
    gain.connect(an); an.connect(ac.destination);
    gain.gain.value = $('#vol').value / 100;
  } catch (e) { ac = null; }
}
function setVol(v) {
  v = Math.max(0, Math.min(100, v)); $('#vol').value = v;
  if (gain) gain.gain.value = v / 100; else A.forEach((a) => { a.volume = v / 100; });
}
function show(i) {
  const t = album.tracks[i];
  [...list.children].forEach((li, k) => { li.classList.toggle('on', k === i); li.setAttribute('aria-current', k === i ? 'true' : 'false'); });
  $('#tno').textContent = String(t.n).padStart(2, '0');
  $('#ttitle').textContent = t.title; $('#tnote').textContent = t.note;
  $('#len').textContent = '/ ' + fmt(t.seconds);
  $('#rectitle').textContent = 'Sound Recorder - TRACK' + String(t.n).padStart(2, '0') + '.WAV';
  $('#rlen').textContent = t.seconds.toFixed(2) + ' sec.';
  $('#evname').textContent = 'TRACK' + String(t.n).padStart(2, '0') + '.MID';
  document.title = t.title + ' - CITYPOP DEPROGRAMMED';
  if ('mediaSession' in navigator) {
    navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: 'Algorithmic Industries', album: 'CITYPOP DEPROGRAMMED',
      artwork: [{ src: 'art/cover-640.png', sizes: '640x640', type: 'image/png' }] });
  }
  loadEvents(i);
}
function loadEvents(i) {
  const t = album.tracks[i];
  if (evdata[i] || !t.events) return;
  evdata[i] = 'loading';
  fetch(t.events).then((r) => r.json()).then((d) => { evdata[i] = d; }).catch(() => { evdata[i] = null; });
}
function prepare(i) {   // the next track into the idle deck
  if (!album || i < 0 || i >= album.tracks.length || loadedNext === i) return;
  const a = A[1 - deck]; a.src = src(album.tracks[i]); a.load(); loadedNext = i; loadEvents(i);
}
function play(i, from = 0) {
  webaudio(); if (ac && ac.state === 'suspended') ac.resume();
  const t = album.tracks[i];
  let a;
  if (loadedNext === i) { deck = 1 - deck; a = A[deck]; } else { a = A[deck]; a.src = src(t); }
  A[1 - deck].pause();
  loadedNext = -1; cur = i;
  a.currentTime = from;
  a.play().catch(() => {});
  show(i); playing(true);
}
function playing(on) { $('#playicon').setAttribute('d', on ? 'M3 2h4v12H3zM9 2h4v12H9z' : 'M4 2v12l10-6z'); $('#play').setAttribute('aria-label', on ? 'Pause' : 'Play'); }
function toggle() {
  const a = A[deck];
  if (!a.src) return play(cur);
  if (a.paused) { webaudio(); if (ac) ac.resume(); a.play(); playing(true); } else { a.pause(); playing(false); }
}
function step(d) { play((cur + d + album.tracks.length) % album.tracks.length); }
A.forEach((a, k) => {
  a.addEventListener('ended', () => { if (k === deck) step(1); });     // continuous play, round the album
  a.addEventListener('timeupdate', () => {
    if (k !== deck) return;
    const t = album.tracks[cur];
    if (a.currentTime > 20 || a.currentTime > t.seconds * 0.5) prepare((cur + 1) % album.tracks.length);
  });
});
$('#play').onclick = toggle;
$('#stop').onclick = () => { const a = A[deck]; a.pause(); a.currentTime = 0; playing(false); };
$('#next').onclick = () => step(1);
$('#prev').onclick = () => { const a = A[deck]; if (a.currentTime > 4) a.currentTime = 0; else step(-1); };
$('#vol').oninput = (e) => setVol(+e.target.value);
$('#pos').oninput = (e) => { const a = A[deck]; if (a.duration) a.currentTime = e.target.value / 1000 * a.duration; };
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' && e.target.type !== 'range') return;
  const a = A[deck], k = e.key;
  if (k === ' ' || k === 'k') { e.preventDefault(); toggle(); }
  else if (k === 'n' || k === 'N') step(1);
  else if (k === 'p' || k === 'P') step(-1);
  else if (k === 's' || k === 'S') $('#stop').onclick();
  else if (k === 'ArrowRight' && e.target.tagName !== 'INPUT') { a.currentTime = Math.min((a.duration || 0) - 0.5, a.currentTime + 10); }
  else if (k === 'ArrowLeft' && e.target.tagName !== 'INPUT') { a.currentTime = Math.max(0, a.currentTime - 10); }
  else if (k === 'ArrowUp') { e.preventDefault(); setVol(+$('#vol').value + 5); }
  else if (k === 'ArrowDown') { e.preventDefault(); setVol(+$('#vol').value - 5); }
  else { const n = '1234567890-='.indexOf(k); if (n >= 0 && album && n < album.tracks.length) play(n); }
});
if ('mediaSession' in navigator) {
  navigator.mediaSession.setActionHandler('play', toggle); navigator.mediaSession.setActionHandler('pause', toggle);
  navigator.mediaSession.setActionHandler('nexttrack', () => step(1)); navigator.mediaSession.setActionHandler('previoustrack', () => step(-1));
}

fetch('album.json').then((r) => r.json()).then((d) => {
  album = d;
  list.innerHTML = '';
  d.tracks.forEach((t, i) => {
    const li = document.createElement('li'); li.tabIndex = 0;
    li.innerHTML = `<span class="n">${String(t.n).padStart(2, '0')}</span><span></span><span class="d">${fmt(t.seconds)}</span>`;
    li.children[1].textContent = t.title;
    li.onclick = () => play(i);
    li.onkeydown = (e) => { if (e.key === 'Enter') play(i); };
    list.appendChild(li);
  });
  const total = d.tracks.reduce((s, t) => s + t.seconds, 0);
  $('#tnote').textContent = `${d.tracks.length} tracks, ${Math.round(total / 60)} minutes. ` + $('#tnote').textContent.replace(/^Twelve tracks, about 45 minutes\. /, '');
  const h = location.hash.match(/^#(\d+)/);
  if (h) { cur = Math.max(0, Math.min(d.tracks.length - 1, +h[1] - 1)); }
  show(cur);
});

/* ------------------------------------------------------------------ Sound Recorder's wave, the event list, the clock */
const wv = $('#wave'), wc = wv.getContext('2d');
const buf = new Uint8Array(1024);
const ev = $('#evlist');
const NOTE = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-'];
const nn = (n) => NOTE[n % 12] + ((n / 12 | 0) - 1);
const pad = (s, n) => (s + ' '.repeat(n)).slice(0, n);
let lastEv = '';
function ui() {
  const a = A[deck];
  if (album) {
    const t = a.currentTime || 0;
    $('#time').textContent = fmt(t);
    if (a.duration && document.activeElement !== $('#pos')) $('#pos').value = Math.round(t / a.duration * 1000);
    $('#rpos').textContent = t.toFixed(2) + ' sec.';
    // the wave: green on black, as Sound Recorder draws it
    const W = wv.width = 160, H = wv.height = 40;
    wc.fillStyle = '#000'; wc.fillRect(0, 0, W, H);
    wc.fillStyle = '#2a6a30'; wc.fillRect(0, H / 2, W, 1);
    if (an && !a.paused) {
      an.getByteTimeDomainData(buf);
      wc.fillStyle = '#7fe08a';
      for (let x = 0; x < W; x++) {
        const v = (buf[(x * 6) % 1024] - 128) / 128, y = Math.round(H / 2 - v * H * 0.9);
        const y0 = Math.min(y, H / 2), y1 = Math.max(y, H / 2);
        wc.fillRect(x, y0, 1, Math.max(1, y1 - y0));
      }
    }
    // the event list: the last notes played, newest at the bottom
    const d = evdata[cur];
    if (d && d.ev) {
      const ms = t * 1000;
      let lo = 0, hi = d.ev.length;
      while (lo < hi) { const m = (lo + hi) >> 1; if (d.ev[m][0] <= ms) lo = m + 1; else hi = m; }
      const rows = [];
      for (let k = Math.max(0, lo - 13); k < lo; k++) {
        const e = d.ev[k];
        const tt = e[0] / 1000;
        rows.push(`${String((tt / 60) | 0).padStart(2, '0')}:${(tt % 60).toFixed(3).padStart(6, '0')}  ${pad(d.parts[e[1]], 8)} ${pad(nn(e[2]), 4)} ${String(e[3]).padStart(3)}  ${String(e[4]).padStart(5)}`);
      }
      const html = '<span class="hd">TIME       PART     NOTE VEL    LEN</span>\n' + rows.map((r, k) => (k === rows.length - 1 ? '<span class="now">' + r + '</span>' : r)).join('\n');
      if (html !== lastEv) { ev.innerHTML = html; lastEv = html; }
    } else if (!lastEv) {
      ev.innerHTML = '<span class="hd">TIME       PART     NOTE VEL    LEN</span>\n(press Play)';
      lastEv = 'x';
    }
  }
  clock();
}
const cc = $('#clk'), cx = cc.getContext('2d');
function clock() {
  const now = new Date(), S = 96, c = S / 2;
  cx.fillStyle = '#12102a'; cx.fillRect(0, 0, S, S);
  for (let i = 0; i < 12; i++) {
    const a = i / 12 * Math.PI * 2, x = Math.round(c + Math.sin(a) * 40), y = Math.round(c - Math.cos(a) * 40);
    cx.fillStyle = i % 3 ? '#6b5f9e' : '#e6dcf5'; cx.fillRect(x - 1, y - 1, i % 3 ? 2 : 3, i % 3 ? 2 : 3);
  }
  const hand = (frac, len, w, col) => {
    const a = frac * Math.PI * 2;
    cx.fillStyle = col;
    for (let r = 0; r < len; r += 0.5) cx.fillRect(Math.round(c + Math.sin(a) * r - w / 2), Math.round(c - Math.cos(a) * r - w / 2), w, w);
  };
  const h = now.getHours() % 12, m = now.getMinutes(), s = now.getSeconds();
  hand((h + m / 60) / 12, 22, 3, '#e6dcf5'); hand((m + s / 60) / 60, 32, 2, '#e6dcf5'); hand(s / 60, 34, 1, '#b0507e');
}
setInterval(() => { if (!document.hidden) ui(); }, 100);
ui();
})();

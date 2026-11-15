// CITYPOP DEPROGRAMMED - Ensemble: the page. One worker runs Windows 3.11 with SNDWAVE2000 Ensemble and the album
// player (ens-worker.js); an AudioWorklet plays the lane card's DAC ring out of the worker's shared memory. Nothing of
// the machine is fetched until Play. The night behind it is /citypop/'s (scene and life).
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const MAN = JSON.parse($('#manifest').textContent);
  const TR = MAN.tracks;   // [{i, start, end, title}]
  const ALBUM_END = TR[TR.length - 1].end;
  const KEY = 'cpens.';
  const store = { get(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : v; } catch (e) { return d; } },
                  set(k, v) { try { localStorage.setItem(KEY + k, v); } catch (e) {} } };
  const reduced = () => window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DPR = Math.min(2, window.devicePixelRatio || 1);
  const playB = $('#play'), stopB = $('#stop'), sel = $('#track'), colors = $('#colors'), status = $('#status'), statsEl = $('#stats'), cv = $('#screen');
  const fmt = s => { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  TR.forEach(t => { const o = document.createElement('option'); o.value = t.i; o.textContent = (t.i + 1) + '. ' + t.title + ' (' + fmt(t.end - t.start) + ')'; sel.appendChild(o); });
  sel.value = store.get('track', '0');
  colors.checked = store.get('colors', '1') === '1';
  const say = s => { status.textContent = s; };

  // ---------------------------------------------------------------- the night (from /citypop/)
  let scene = null, life = null;
  function loadScript(s) { return new Promise((res, rej) => { const e = document.createElement('script'); e.src = s; e.async = true; e.onload = res; e.onerror = rej; document.head.appendChild(e); }); }
  function occlude() {
    if (!life || !life.setOccluders) return;
    const r = [...document.querySelectorAll('.win')].map(w => { const b = w.getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
    try { life.setOccluders(r); } catch (e) {}
  }
  (async () => {
    try {
      await loadScript('/citypop/scene/scene.js?v=' + MAN.ui);
      if (window.CityScene) scene = CityScene.start($('#scene'), { dpr: DPR, reduced: reduced(), time: 19.5, base: '/citypop/' });
      await loadScript('/citypop/life/life.js?v=' + MAN.ui);
      if (window.CityLife) life = CityLife.start($('#life'), { dpr: DPR, reduced: reduced(), scene, analyser: an || null, seed: (Date.now() / 86400000) | 0 });
      occlude();
    } catch (e) { /* the window works without the night */ }
  })();
  addEventListener('resize', () => setTimeout(occlude, 100));
  addEventListener('scroll', () => setTimeout(occlude, 100), { passive: true });

  // ---------------------------------------------------------------- the machine
  let W = null, ac = null, node = null, an = null, started = false, playing = false, lastInfo = null, lastStats = null, bm = null;
  cv.pxSource = null;
  function show(bitmap) { if (bm && bm.close) bm.close(); bm = bitmap; cv.pxSource = bitmap; if (window.pxfit) pxfit.draw(cv); }

  async function start() {
    if (!window.crossOriginIsolated || typeof SharedArrayBuffer === 'undefined') { say('This browser does not give the page shared memory, which the machine needs. A recent Chrome, Edge or Firefox does.'); return; }
    playB.disabled = true; started = true;
    say('Starting the sound...');
    ac = new AudioContext({ latencyHint: 'playback', sampleRate: 48000 });
    await ac.audioWorklet.addModule('audio-worklet.js?v=' + MAN.v);
    node = new AudioWorkletNode(ac, 'ens-out', { numberOfInputs: 0, numberOfOutputs: 1, outputChannelCount: [2] });
    an = ac.createAnalyser(); an.fftSize = 1024;
    node.connect(ac.destination); node.connect(an);
    if (life && life.setAnalyser) try { life.setAnalyser(an); } catch (e) {}
    node.port.onmessage = e => { if (e.data.t === 'a') audio = e.data; };
    say('Fetching the machine...');
    const [conf, names, schedule] = await Promise.all([
      fetch(MAN.base + 'w31.conf?v=' + MAN.v).then(r => r.text()),
      fetch(MAN.base + 'names.txt?v=' + MAN.v).then(r => r.text()),
      fetch(MAN.base + 'schedule.json?v=' + MAN.v).then(r => r.json())]);
    W = new Worker('ens-worker.js?v=' + MAN.v, { name: 'ensemble' });
    W.onmessage = onWorker;
    W.onerror = e => say('The machine stopped: ' + (e.message || 'worker error'));
    const from = +sel.value;
    W.postMessage({ t: 'init', files: MAN.files.map(f => ({ name: f.name, url: MAN.base + f.url + '?v=' + f.v, size: f.size })),
                    conf, libraryNames: names, schedule, discUrl: MAN.base + MAN.disc.url + '?v=' + MAN.disc.v, discSize: MAN.disc.size,
                    discChunk: 262144, lead: MAN.lead, colors: colors.checked, from, play: true });
    playing = true; stopB.disabled = false;
  }
  let audio = null, tResume = 0, tReady = 0;
  function onWorker(e) {
    const m = e.data;
    switch (m.t) {
    case 'progress': say('Fetching the machine: ' + (m.loaded / 1e6).toFixed(1) + ' of ' + (m.total / 1e6).toFixed(1) + ' MB'); break;
    case 'mem': node.port.postMessage({ t: 'mem', buffer: m.buffer, base: m.base, lay: m.lay, lead: MAN.lead, leadMax: MAN.leadMax, master: MAN.master }); break;
    case 'resumed': tResume = m.ms; say('Windows is up (' + (m.ms / 1000).toFixed(1) + ' s). ENSEMBLE.EXE is getting ready...'); break;
    case 'ready': tReady = m.ms; say('Building the first presets in Sound Recorder...'); break;
    case 'frame': show(m.bitmap); break;
    case 'hb': lastInfo = m.info; onInfo(m.info); break;
    case 'stats': lastStats = m.stats; drawStats(); break;
    case 'error': say('The machine stopped: ' + m.msg); break;
    }
  }
  let shownTrack = -2, lastTime = 0, gaps0 = -1;   // gaps0: the worklet's gaps before the music (the start is not one)
  function onInfo(i) {
    if (!playing) return;
    if (i.phase === 1) { say('Building track ' + (+sel.value + 1) + "'s presets in Sound Recorder..."); return; }
    if (i.phase !== 2) return;
    if (gaps0 < 0 && audio && i.pos > 1) { gaps0 = audio.gaps; node.port.postMessage({ t: 'reset' }); }
    if (i.pos >= ALBUM_END) { say('The end of the album.'); return; }
    if (i.track !== shownTrack && i.track >= 0) {
      shownTrack = i.track; sel.value = i.track; store.set('track', i.track);
      const t = TR[i.track];
      document.title = t.title + ' - CITYPOP DEPROGRAMMED - Ensemble';
      if (life && life.onTrack) try { life.onTrack(i.track + 1, { bpm: MAN.bpm[i.track] || 100, title: t.title }); } catch (e) {}
    }
    const t = TR[Math.max(0, i.track)];
    say((i.track + 1) + '. ' + t.title + '  ' + fmt(i.pos - t.start) + ' / ' + fmt(t.end - t.start));
    const now = performance.now();
    if (scene && scene.setTime && now - lastTime > 4000) { lastTime = now; try { scene.setTime(19.5 + 10 * Math.min(1, Math.max(0, i.pos / ALBUM_END))); } catch (e) {} }
  }
  function drawStats() {
    const i = lastInfo; if (!i) return;
    const lines = [];
    const lead = i.phase === 2 ? (i.emu - i.pos) : 0;
    lines.push('Windows ahead of the speakers ' + lead.toFixed(2) + ' s   emulator busy ' + (i.load / 10).toFixed(0) + '%   notes ' + i.notes +
               '   card late ' + i.late + '   audio gaps ' + (audio && gaps0 >= 0 ? audio.gaps - gaps0 : 0));
    lines.push('switches ' + i.switches + ' (built in Sound Recorder ' + i.builds + ')   notes late for a switch ' + i.switchLate);
    if (lastStats) {
      lines.push('');
      lines.push('track                                     switches  builds  building  late  replaced');
      lastStats.forEach((s, k) => { if (!s[0] && !s[1] && !s[3]) return;
        lines.push(String(k + 1).padStart(2) + ' ' + TR[k].title.slice(0, 38).padEnd(38) + String(s[0]).padStart(9) + String(s[1]).padStart(8) + (s[2].toFixed(1) + ' s').padStart(10) + String(s[3]).padStart(6) + String(s[4]).padStart(10)); });
    }
    statsEl.textContent = lines.join('\n'); statsEl.hidden = false;
  }
  setInterval(() => { if (W && playing) W.postMessage({ t: 'stats' }); }, 2000);
  window.cpens = { get ac() { return ac; }, get audio() { return audio; }, get info() { return lastInfo; }, get stats() { return lastStats; }, timing: () => ({ resume: tResume, ready: tReady }) };

  playB.onclick = () => {
    if (!started) { start().catch(err => { say('Could not start: ' + (err && err.message || err)); playB.disabled = false; started = false; }); return; }
    if (ac.state !== 'running') ac.resume();
    W.postMessage({ t: 'play', track: +sel.value }); playing = true; shownTrack = -2; gaps0 = -1; playB.disabled = true; stopB.disabled = false;
  };
  stopB.onclick = () => { if (!W) return; W.postMessage({ t: 'stop' }); playing = false; playB.disabled = false; stopB.disabled = true; say('Stopped. Windows is still running; Play starts the selected track.'); };
  sel.onchange = () => { store.set('track', sel.value); if (W && playing) { W.postMessage({ t: 'play', track: +sel.value }); shownTrack = -2; gaps0 = -1; } };
  colors.onchange = () => { store.set('colors', colors.checked ? '1' : '0'); if (W) W.postMessage({ t: 'colors', on: colors.checked }); };

  // the pointer: Windows' own (the left button drags windows, the right is the right)
  function at(e) {
    const s = cv._pxs, r = cv.getBoundingClientRect(); if (!s) return null;
    const dpr = window.devicePixelRatio || 1;
    return { x: Math.floor((e.clientX - r.left) * dpr * s.nw / s.dw), y: Math.floor((e.clientY - r.top) * dpr * s.nh / s.dh) };
  }
  cv.addEventListener('pointermove', e => { if (!W) return; const p = at(e); if (p) W.postMessage({ t: 'm', x: p.x, y: p.y }); });
  cv.addEventListener('pointerdown', e => { if (!W) return; e.preventDefault(); cv.setPointerCapture(e.pointerId); const p = at(e); if (p) W.postMessage({ t: 'b', x: p.x, y: p.y, bit: e.button === 2 ? 2 : 1, down: true }); });
  cv.addEventListener('pointerup', e => { if (!W) return; const p = at(e); if (p) W.postMessage({ t: 'b', x: p.x, y: p.y, bit: e.button === 2 ? 2 : 1, down: false }); });
  cv.addEventListener('contextmenu', e => e.preventDefault());

  // before Play: Windows' screen as the snapshot left it
  const still = new Image();
  still.onload = () => { if (!bm) { cv.pxSource = still; if (window.pxfit) pxfit.draw(cv); } };
  still.src = colors.checked ? 'still-loft.png' : 'still.png';
  colors.addEventListener('change', () => { if (!bm) still.src = colors.checked ? 'still-loft.png' : 'still.png'; });
})();

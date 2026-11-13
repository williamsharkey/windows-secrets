// BASILISK 16, "Try it online" (sndrec.html): Windows for Workgroups 3.11 and its sixteen Sound Recorders, the
// plugin's own engine compiled to WebAssembly (tools/basilisk16-web). Nothing is fetched until the button is
// pressed. The machine runs in a worker; the page only forwards the pointer, the keys and MIDI, and watches it.
(function () {
  'use strict';
  var CFG = /*CONFIG*/{"v":"3f8a5b0eb1","files":[{"name":"b16.wasm","size":2513059,"gz":1029977},{"name":"w31web.state","size":5848612,"gz":1388626},{"name":"drive.zip","size":3363161,"gz":3363161}],"lead":2048}/*END*/;
  var DATA = null;   // b16-data.json, fetched on the click: the machine's settings, the library's names, the presets
  var root = document.getElementById('b16try');
  if (!root) return;
  var base = (function () { var s = document.currentScript; return s ? s.src.replace(/[^\/]*$/, '') : 'sndrec/try/'; })();
  var $ = function (s) { return root.querySelector(s); };
  var over = $('.b16over'), go = $('.b16go'), bar = $('.b16prog i'),
      msg = $('.b16msg'), stopB = $('.b16stop'), midiB = $('.b16midi'), presetS = $('.b16preset'), stat = $('.b16stat');
  var canvas = null, worker = null, actx = null, node = null, running = false, ready = false, paused = false;
  var memMsg = null, hb = { t: 0, dac: -1, dacT: 0 }, audio = { hist: [] }, wd = 0, tClick = 0, times = null, midi = null, held = {};
  // audio health, for the page (the "i" readout) and for tests: gaps (the ring ran dry), frames short, frame-
  // production stalls (the emulator made nothing for 50 ms), the current lead and the note latency
  var stats = window.__b16stats = { gaps: 0, shortFrames: 0, stalls: 0, lead: 0, latencyMs: 0 };
  var infoB = null, infoS = null;
  function showStats() {
    if (infoS && !infoS.hidden) infoS.textContent = 'audio: ' + stats.gaps + (stats.gaps === 1 ? ' gap' : ' gaps') + ', ' + stats.stalls + ' stalls, ~' + stats.latencyMs + ' ms';
  }
  var api = window.__b16 = { state: 'idle', stats: null, times: null, ready: false, events: [] };
  function setState(s) { api.state = s; root.setAttribute('data-state', s); }
  function say(t) { msg.textContent = t || ''; }
  function mb(n) { return (n / 1048576).toFixed(1); }
  var total = CFG.files.reduce(function (a, f) { return a + (f.gz || f.size); }, 0);
  $('.b16size').textContent = mb(total) + ' MB';

  var supported = window.crossOriginIsolated && typeof SharedArrayBuffer === 'function' && window.Worker &&
                  (window.AudioContext || window.webkitAudioContext) && window.AudioWorkletNode;
  if (!supported) {
    go.disabled = true;
    say(window.crossOriginIsolated === false && typeof SharedArrayBuffer !== 'function'
      ? 'This browser cannot run it here (it needs SharedArrayBuffer and AudioWorklet). Current Chrome, Edge, Firefox and Safari can.'
      : 'This browser cannot run the online version (it needs SharedArrayBuffer and AudioWorklet).');
  }
  if (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)) $('.b16mobile').hidden = false;
  // the screen: one canvas, sized by pxfit (the page's pixel-exact pictures: every Windows pixel exactly k x k device
  // pixels, or an exact 1/n reduction when even k = 1 does not fit). It shows the poster until Windows runs.
  var canvas = null, posterSrc = null;
  function screen() {
    var c = document.getElementById('b16screen');
    if (c && c !== canvas && c.tagName === 'CANVAS') {
      canvas = c; canvas.tabIndex = 0;
      canvas.setAttribute('aria-label', 'Windows for Workgroups 3.11 running BASILISK 16. Click to play; the keys go to Windows.');
      bindInput(canvas);
    }
    return canvas;
  }
  function show(src) {
    var c = screen(); if (!c) return;
    var old = c.pxSource;
    c.pxSource = src;
    if (old && old !== posterSrc && old.close) old.close();
    if (window.pxfit) pxfit.draw(c); else { var x = c.getContext('2d'); x.imageSmoothingEnabled = false; x.drawImage(src, 0, 0, c.width, c.height); }
  }
  screen();
  function fillPresets() {
    presetS.innerHTML = '<option value="">Preset…</option>' + DATA.presets.map(function (p, i) {
      return '<option value="' + i + '">' + p[0].replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</option>'; }).join('');
  }

  infoB = $('.b16info'); infoS = $('.b16infotext');
  if (infoB) infoB.addEventListener('click', function () {
    infoS.hidden = !infoS.hidden; infoB.setAttribute('aria-pressed', String(!infoS.hidden)); showStats();
  });

  // ---------------------------------------------------------------- start
  go.addEventListener('click', start);
  function start() {
    if (running || !supported) return;
    tClick = performance.now();
    setState('loading'); go.style.visibility = 'hidden'; $('.b16prog').style.visibility = ''; bar.style.width = '0%'; say('Loading Windows for Workgroups 3.11…');
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      try { actx = new AC({ sampleRate: 48000, latencyHint: 'interactive' }); } catch (e) { actx = new AC({ latencyHint: 'interactive' }); }
      actx.resume();
    } catch (e) { return fail('Audio could not start: ' + e.message); }
    screen();
    if (canvas && canvas.pxSource && !posterSrc) posterSrc = canvas.pxSource;
    running = true; ready = false; paused = false; hb = { t: performance.now(), dac: -1, dacT: performance.now() }; audio.hist = [];
    var dataP = DATA ? Promise.resolve(DATA) : fetch(base + 'b16-data.json?v=' + CFG.v).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
    Promise.all([actx.audioWorklet.addModule(base + 'b16-audio.js?v=' + CFG.v), dataP]).then(function (res) {
      if (!running) return;
      if (!DATA) { DATA = res[1]; fillPresets(); }
      node = new AudioWorkletNode(actx, 'b16-out', { numberOfInputs: 0, numberOfOutputs: 1, outputChannelCount: [2] });
      node.connect(actx.destination);
      node.port.onmessage = onAudio;
      worker = new Worker(base + 'b16-worker.js?v=' + CFG.v);
      worker.onmessage = onWorker;
      worker.onerror = function (e) { fail('The emulator stopped: ' + (e.message || 'error')); };
      worker.postMessage({ t: 'init', conf: DATA.conf, lead: CFG.lead, layers: DATA.layers, libraryNames: DATA.libraryNames,
        relDrag: DATA.relDrag,   /* (libMap: fetching library pieces ahead raced the emulator's own reads; off for now) */ libraryUrl: new URL(base + 'library.zip', location.href).href, librarySize: DATA.librarySize, libraryChunk: 262144,
        files: CFG.files.map(function (f) { return { name: f.name, size: f.size, url: base + f.name + '?v=' + CFG.v }; }) });
      clearInterval(wd); wd = setInterval(watchdog, 500);
    }).catch(function (e) { fail('It could not start: ' + e.message); });
  }

  function onWorker(e) {
    var m = e.data;
    if (m.t === 'progress') { bar.style.width = Math.min(100, 100 * m.loaded / Math.max(1, m.total)).toFixed(1) + '%'; if (m.loaded >= m.total) say('Resuming the machine…'); }
    else if (m.t === 'mem') memMsg = m;
    else if (m.t === 'ready') {
      // the sound starts now (not while the machine resumes, which would only be a stretch of silence)
      if (node && memMsg) node.port.postMessage({ t: 'mem', buffer: memMsg.buffer, base: memMsg.base, lay: memMsg.lay, lead: CFG.lead, leadMax: 3584 });
      ready = true; api.ready = true; setState('running');
      times = api.times = { clickToReady: Math.round(performance.now() - tClick), worker: m.ms };
      over.hidden = true; say('');
      stopB.disabled = false; midiB.disabled = !navigator.requestMIDIAccess; presetS.disabled = false;
      try { if (canvas) canvas.focus({ preventScroll: true }); } catch (err) {}
      status();
    } else if (m.t === 'hb') {
      var now = performance.now();
      if (m.dac !== hb.dac) { hb.dac = m.dac; hb.dacT = now; }
      hb.t = now; api.stats = m; stats.stalls = m.stalls || 0; showStats();
      if (m.building) stat.textContent = 'Sound Recorder is building the sound…'; else status();
    } else if (m.t === 'frame') {
      if (running) show(m.bitmap); else if (m.bitmap.close) m.bitmap.close();
    } else if (m.t === 'info') { var cb = pending[m.id]; delete pending[m.id]; if (cb) cb(m.info); }
    else if (m.t === 'error') fail('The emulator stopped: ' + m.msg);
  }
  function onAudio(e) {
    var m = e.data;
    if (m.t === 'a') {
      audio.hist.push(m); if (audio.hist.length > 16) audio.hist.shift();
      api.audio = { under: m.under, blocks: m.blocks };
      stats.gaps = m.gaps; stats.shortFrames = m.short; stats.lead = m.lead;
      // the latency of a note: the emulator's lead plus the time Windows gets to press Play, plus the output
      stats.latencyMs = Math.round((m.lead + 1536) / 48 + ((actx && (actx.outputLatency || actx.baseLatency)) || 0) * 1000);
      showStats();
    } else if (m.t === 'tap' && api.tapSink) api.tapSink(m.d);
  }
  function status() {
    var t = midi ? 'MIDI: ' + midi + '. ' : '';
    stat.textContent = t + (paused ? 'Paused while the page is hidden.' : 'Running. Click the screen, then play the on-screen keys or press Keys.');
  }

  // ---------------------------------------------------------------- stop, watchdog
  function stop(text) {
    if (!running && !worker) return;
    running = false; ready = false; api.ready = false;
    clearInterval(wd);
    if (worker) { worker.terminate(); worker = null; }
    if (node) { try { node.disconnect(); } catch (e) {} node = null; }
    if (actx) { try { actx.close(); } catch (e) {} actx = null; }
    if (posterSrc) show(posterSrc);
    over.hidden = false; $('.b16prog').style.visibility = 'hidden';
    go.style.visibility = ''; go.textContent = 'Restart';
    stopB.disabled = true; midiB.disabled = true; presetS.disabled = true; stat.textContent = '';
    say(text || 'Stopped.');
    setState('stopped');
  }
  function fail(text) { stop(text); setState('failed'); }
  api.stop = function () { stop(); };
  stopB.addEventListener('click', function () { stop('Stopped. Press Restart to run it again.'); });
  function watchdog() {
    if (!running || paused) return;
    var now = performance.now();
    if (!ready) { if (now - tClick > 90000) fail('It took too long to load. Check the connection, then press Restart.'); return; }
    // the worker or the emulator stopped answering
    if (now - hb.t > 2500 || now - hb.dacT > 2500) {
      api.events.push('watchdog:stall'); stop('Stopped to keep your browser responsive. Press Restart to try again.'); return; }
    // the audio keeps running dry: the computer cannot keep up
    var h = audio.hist.slice(-12);
    if (h.length >= 12 && h.every(function (x) { return x.under > x.blocks * 0.25; })) {
      api.events.push('watchdog:audio'); stop('Stopped: this computer could not keep the sound going in real time. Press Restart to try again, ideally with fewer tabs open.'); }
  }
  document.addEventListener('visibilitychange', function () {
    if (!running || !ready) return;
    paused = document.hidden;
    worker.postMessage({ t: 'pause', p: paused });
    if (paused) actx.suspend(); else { actx.resume(); hb.t = hb.dacT = performance.now(); audio.hist = []; }
    status();
  });

  // ---------------------------------------------------------------- the pointer and the keys go to Windows
  var RK = { Backspace: 8, Tab: 9, Enter: 13, Escape: 27, Space: 32, Delete: 127, ArrowUp: 273, ArrowDown: 274, ArrowRight: 275, ArrowLeft: 276,
    Insert: 277, Home: 278, End: 279, PageUp: 280, PageDown: 281, ShiftRight: 303, ShiftLeft: 304, ControlRight: 305, ControlLeft: 306,
    AltRight: 307, AltLeft: 308, CapsLock: 301, Minus: 45, Equal: 61, BracketLeft: 91, BracketRight: 93, Backslash: 92, Semicolon: 59,
    Quote: 39, Backquote: 96, Comma: 44, Period: 46, Slash: 47, NumpadEnter: 271, NumpadAdd: 270, NumpadSubtract: 269,
    NumpadMultiply: 268, NumpadDivide: 267, NumpadDecimal: 266 };
  function rk(code) {
    if (RK[code]) return RK[code];
    var m;
    if ((m = /^Key([A-Z])$/.exec(code))) return m[1].toLowerCase().charCodeAt(0);
    if ((m = /^Digit([0-9])$/.exec(code))) return 48 + +m[1];
    if ((m = /^Numpad([0-9])$/.exec(code))) return 256 + +m[1];
    if ((m = /^F([0-9]+)$/.exec(code)) && +m[1] <= 12) return 281 + +m[1];
    return 0;
  }
  function bindInput(cv) {
    function at(e) {
      // Windows' pixel under the pointer: the picture is s.dw device pixels wide for 1024 (the canvas may be padded)
      var r = cv.getBoundingClientRect(), s = cv._pxs, dpr = window.devicePixelRatio || 1;
      if (!s) return { x: Math.round((e.clientX - r.left) * 1024 / r.width), y: Math.round((e.clientY - r.top) * 768 / r.height) };
      return { x: Math.floor((e.clientX - r.left) * dpr * (s.sw || s.nw) / s.dw), y: Math.floor((e.clientY - r.top) * dpr * (s.sh || s.nh) / s.dh) };
    }
    cv.addEventListener('pointermove', function (e) { if (worker && ready) { var p = at(e); worker.postMessage({ t: 'm', x: p.x, y: p.y }); } });
    cv.addEventListener('pointerdown', function (e) {
      if (!worker || !ready) return;
      e.preventDefault(); cv.focus({ preventScroll: true });
      try { cv.setPointerCapture(e.pointerId); } catch (err) {}
      var p = at(e); worker.postMessage({ t: 'b', x: p.x, y: p.y, bit: e.button === 2 ? 2 : 1, down: true });
    });
    cv.addEventListener('pointerup', function (e) { if (worker) { var p = at(e); worker.postMessage({ t: 'b', x: p.x, y: p.y, bit: e.button === 2 ? 2 : 1, down: false }); } });
    cv.addEventListener('pointercancel', function () { if (worker) worker.postMessage({ t: 'b', bit: 1, down: false }); });
    cv.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    cv.addEventListener('keydown', function (e) {
      if (!worker || !ready) return;
      var k = rk(e.code); if (!k) return;
      e.preventDefault();
      if (e.repeat || held[k]) return;
      held[k] = 1; worker.postMessage({ t: 'k', down: true, rk: k });
    });
    cv.addEventListener('keyup', function (e) {
      var k = rk(e.code); if (!k || !worker) return;
      e.preventDefault(); delete held[k]; worker.postMessage({ t: 'k', down: false, rk: k });
    });
    cv.addEventListener('blur', function () {   // nothing stays held when the focus leaves
      if (!worker) return;
      for (var k in held) worker.postMessage({ t: 'k', down: false, rk: +k });
      held = {};
    });
  }

  // ---------------------------------------------------------------- Web MIDI (opt-in): notes, mod wheel, pitch bend
  midiB.addEventListener('click', function () {
    if (!navigator.requestMIDIAccess || !worker) return;
    midiB.disabled = true;
    navigator.requestMIDIAccess({ sysex: false }).then(function (acc) {
      function hook() {
        var names = [];
        acc.inputs.forEach(function (inp) { names.push(inp.name); inp.onmidimessage = onMidi; });
        midi = names.length ? names.join(', ') : 'no input connected yet';
        midiB.textContent = 'Web MIDI on'; midiB.setAttribute('aria-pressed', 'true'); status();
      }
      acc.onstatechange = hook; hook();
    }, function (err) { midiB.disabled = false; stat.textContent = 'Web MIDI was not allowed (' + (err && err.name || 'error') + ').'; });
  });
  function onMidi(e) {
    var d = e.data; if (!worker || !ready || !d || d.length < 2) return;
    var st = d[0] & 0xF0;
    if (st === 0x90 || st === 0x80 || st === 0xE0 || (st === 0xB0 && (d[1] === 1 || d[1] === 64 || d[1] === 120 || d[1] === 123)))
      worker.postMessage({ t: 'midi', d: [d[0], d[1], d[2] || 0] });
  }
  api.midi = function (a, b, c) { if (worker) worker.postMessage({ t: 'midi', d: [a, b, c] }); };

  // ---------------------------------------------------------------- presets (the plugin's program list)
  presetS.addEventListener('change', function () {
    var p = DATA && DATA.presets[+presetS.value];
    if (p && worker) { worker.postMessage({ t: 'dna', text: p[1] }); if (canvas) canvas.focus({ preventScroll: true }); }
  });

  // ---------------------------------------------------------------- tests
  var pending = {}, nextId = 1;
  api.start = start;
  api.info = function () { return new Promise(function (res) { if (!worker) return res(null); var id = nextId++; pending[id] = res; worker.postMessage({ t: 'info', id: id }); }); };
  api.stall = function (ms) { if (worker) worker.postMessage({ t: 'stall', ms: ms }); };
  api.engineStall = function () { if (worker) worker.postMessage({ t: 'enginestall' }); };
  api.tap = function (on, sink) { api.tapSink = sink; if (node) node.port.postMessage({ t: 'tap', on: on }); };
  api.ctxRate = function () { return actx && actx.sampleRate; };
})();

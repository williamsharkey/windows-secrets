// BASILISK 16, "Try it online" (sndrec.html): Windows for Workgroups 3.11 and its sixteen Sound Recorders, the
// plugin's own engine compiled to WebAssembly (tools/basilisk16-web). Nothing is fetched until the button is
// pressed. The machine runs in a worker; the page only forwards the pointer, the keys and MIDI, and watches it.
(function () {
  'use strict';
  var CFG = /*CONFIG*/{"v":"390198a1d4","files":[{"name":"b16.wasm","size":2523434,"gz":1034128},{"name":"w31web.state","size":5842196,"gz":1362890},{"name":"drive.zip","size":3366379,"gz":3366379}],"lead":2048}/*END*/;
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
        relDrag: DATA.relDrag, libMap: DATA.libMap, libTsv: DATA.libTsv, libraryUrl: new URL(base + 'library.zip', location.href).href, librarySize: DATA.librarySize, libraryChunk: 262144,
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
      onRunning();
    } else if (m.t === 'hb') {
      var now = performance.now();
      if (m.dac !== hb.dac) { hb.dac = m.dac; hb.dacT = now; }
      hb.t = now; api.stats = m; stats.stalls = m.stalls || 0; showStats();
      onHeartbeat(m);
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
    onStopped();
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

  // ================================================================ state files, slots, microphone, drag and drop
  // A state is the plugin's own state text (packages/basilisk-synth/design/STATE.md): the DNA (parameters, globals and
  // macros are in it) and any other lines, kept as they came. `.b16` is that text, zlib-compressed, with a 16-byte
  // header; a `.vstpreset` carries the same text as the plugin's component state, so either opens in the DAW.
  var curDna = '', extras = [], pendingState = null, savedText = '', autoT = 0, U = window.B16UI;
  function stateText(dna) { return 'BASILISK-SYNTH 1\ndna ' + (dna || curDna || 'ding#16;R120') + '\nreference 0\n' + extras.join(''); }
  function parseState(text) {
    var lines = text.replace(/\r/g, '').split('\n'), dna = null, ex = [];
    if (!/^BASILISK-SYNTH /.test(lines[0])) { var t = lines[0].trim(); return t ? { dna: t, extras: [] } : null; }   // a bare DNA line
    for (var i = 1; i < lines.length; i++) {
      var l = lines[i]; if (!l) continue;
      if (l.lastIndexOf('dna ', 0) === 0) dna = l.slice(4); else if (l.lastIndexOf('reference ', 0) !== 0) ex.push(l + '\n');
    }
    return dna ? { dna: dna, extras: ex } : null;
  }
  var CRC = (function () { var t = new Uint32Array(256); for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { var c = 0xFFFFFFFF; for (var i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function streamBytes(bytes, stream) {
    return new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer().then(function (a) { return new Uint8Array(a); });
  }
  function encodeB16(text) {
    var raw = new TextEncoder().encode(text), crc = crc32(raw);
    var z = window.CompressionStream ? streamBytes(raw, new CompressionStream('deflate')) : Promise.resolve(null);
    return z.then(function (comp) {
      var body = comp || raw, out = new Uint8Array(16 + body.length), dv = new DataView(out.buffer);
      out.set([66, 49, 54, 83]); dv.setUint16(4, 1, true); dv.setUint16(6, comp ? 1 : 0, true);
      dv.setUint32(8, raw.length, true); dv.setUint32(12, crc, true); out.set(body, 16);
      return out;
    });
  }
  function decodeB16(b) {
    var dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    if (b.length < 16 || String.fromCharCode(b[0], b[1], b[2], b[3]) !== 'B16S') return Promise.reject(new Error('not a .b16 file'));
    if (dv.getUint16(4, true) !== 1) return Promise.reject(new Error('a .b16 of a newer version'));
    var flags = dv.getUint16(6, true), len = dv.getUint32(8, true), crc = dv.getUint32(12, true), body = b.subarray(16);
    var p = flags & 1 ? (window.DecompressionStream ? streamBytes(body, new DecompressionStream('deflate')) : Promise.reject(new Error('this browser cannot decompress it'))) : Promise.resolve(body);
    return p.then(function (raw) {
      if (raw.length !== len || crc32(raw) !== crc) throw new Error('the file is damaged (its check sum does not match)');
      return new TextDecoder().decode(raw);
    });
  }
  // .vstpreset: the VST3 preset container around the DPF component state (as DPF writes it; loaded and checked in
  // BasiliskHost by the 3.11 lane); the class id is DPF's ('DPF ', 'clas', 'B311', 'Wshk'), in the host OS's string form
  function classId(mac) {
    var w = ['DPF ', 'clas', 'B311', 'Wshk'].map(function (s) { return ((s.charCodeAt(0) << 24) | (s.charCodeAt(1) << 16) | (s.charCodeAt(2) << 8) | s.charCodeAt(3)) >>> 0; });
    var raw = new Uint8Array(16), dv = new DataView(raw.buffer); w.forEach(function (x, i) { dv.setUint32(i * 4, x, true); });
    var hex = function (a) { return Array.prototype.map.call(a, function (x) { return (x < 16 ? '0' : '') + x.toString(16).toUpperCase(); }).join(''); };
    if (mac) return hex(raw);
    var h8 = function (v, n) { var t = v.toString(16).toUpperCase(); while (t.length < n) t = '0' + t; return t; };
    return h8(dv.getUint32(0, true), 8) + h8(dv.getUint16(4, true), 4) + h8(dv.getUint16(6, true), 4) + hex(raw.subarray(8));
  }
  function latin1(s) { var o = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) o[i] = s.charCodeAt(i) & 255; return o; }
  function encodeVstPreset(text) {
    var t = new TextEncoder().encode(text);
    // DPF's own chunk: fields separated by NUL, ended by 0xFE (without it DPF's setState reads past the end)
    var a = latin1('__dpf_state_begin__\0state\0'), z = latin1('\0__dpf_state_end__\0\xfe\0');
    var comp = new Uint8Array(a.length + t.length + z.length); comp.set(a); comp.set(t, a.length); comp.set(z, a.length + t.length);
    var head = latin1('VST3'), cid = latin1(classId(/Mac/.test(navigator.platform)));
    var off = 4 + 4 + 32 + 8, lst = off + comp.length, out = new Uint8Array(lst + 4 + 4 + 4 + 16), dv = new DataView(out.buffer);
    out.set(head); dv.setInt32(4, 1, true); out.set(cid, 8); dv.setBigInt64(40, BigInt(lst), true); out.set(comp, off);
    out.set(latin1('List'), lst); dv.setInt32(lst + 4, 1, true); out.set(latin1('Comp'), lst + 8); dv.setBigInt64(lst + 12, BigInt(off), true); dv.setBigInt64(lst + 20, BigInt(comp.length), true);
    return out;
  }
  function decodeVstPreset(b) {
    if (String.fromCharCode(b[0], b[1], b[2], b[3]) !== 'VST3') throw new Error('not a .vstpreset');
    var s = ''; for (var i = 48; i < b.length; i++) s += String.fromCharCode(b[i]);
    var m = /__dpf_state_begin__[\xff\0]state[\xff\0]([\s\S]*?)[\xff\0]/.exec(s);
    if (!m) throw new Error('this preset is not BASILISK 16’s');
    return new TextDecoder().decode(latin1(m[1]));
  }
  function readStateFile(file) {
    return file.arrayBuffer().then(function (ab) {
      var b = new Uint8Array(ab), magic = String.fromCharCode(b[0], b[1], b[2], b[3]);
      if (magic === 'B16S') return decodeB16(b);
      if (magic === 'VST3') return decodeVstPreset(b);
      throw new Error('not a BASILISK 16 state (.b16 or .vstpreset)');
    });
  }
  function applyState(text) {
    var st = parseState(text);
    if (!st) { note('That state has no DNA.'); return false; }
    extras = st.extras;
    if (running && ready && worker) { curDna = st.dna; worker.postMessage({ t: 'dna', text: st.dna }); savedText = ''; }
    else { pendingState = text; if (!running) start(); }
    return true;
  }
  api.stateText = function () { return stateText(); };
  api.applyState = applyState;
  api.encodeB16 = function (t) { return encodeB16(t || stateText()); };
  api.decodeB16 = decodeB16;
  api.encodeVstPreset = function (t) { return encodeVstPreset(t || stateText()); };
  api.decodeVstPreset = decodeVstPreset;

  // ---------------------------------------------------------------- slots (IndexedDB; every call guarded)
  var db = null;
  function idb() {
    if (db) return db;
    db = new Promise(function (res, rej) {
      try {
        var r = indexedDB.open('basilisk16', 1);
        r.onupgradeneeded = function () { r.result.createObjectStore('slots', { keyPath: 'name' }); };
        r.onsuccess = function () { res(r.result); }; r.onerror = function () { rej(r.error); };
      } catch (e) { rej(e); }
    });
    return db;
  }
  function tx(mode, fn) {
    return idb().then(function (d) { return new Promise(function (res, rej) {
      try { var t = d.transaction('slots', mode), s = t.objectStore('slots'), out = fn(s); t.oncomplete = function () { res(out && out.result !== undefined ? out.result : out); }; t.onerror = function () { rej(t.error); }; }
      catch (e) { rej(e); }
    }); });
  }
  var slots = { list: function () { return tx('readonly', function (s) { return s.getAll(); }).catch(function () { return []; }); },
    put: function (name, bytes) { return tx('readwrite', function (s) { s.put({ name: name, data: bytes, t: Date.now() }); }); },
    del: function (name) { return tx('readwrite', function (s) { s.delete(name); }); } };
  var AUTO = 'AUTOSAVE';
  function autosave() {
    clearTimeout(autoT);
    autoT = setTimeout(function () {
      var t = stateText(); if (!curDna || t === savedText) return;
      encodeB16(t).then(function (b) { return slots.put(AUTO, b); }).then(function () { savedText = t; refreshSlots(); }).catch(function () {});
    }, 3000);
  }
  api.slots = slots;

  // ---------------------------------------------------------------- the row under the screen
  var row = $('.b16slots'), iconsEl = $('.b16icons'), btnsEl = $('.b16row'), sel = null, iconBtns = {}, B = {}, statusL = null, meterCv = null;
  function eightThree(s) { return (s || '').toUpperCase().replace(/[^A-Z0-9_\-]/g, '').slice(0, 8); }
  function note(t) { if (statusL) statusL.set(t); }
  function select(name) {
    sel = name;
    Object.keys(iconBtns).forEach(function (n) { iconBtns[n].setSelected(n === name); });
    showButtons();
  }
  function showButtons() {
    if (!B.open) return;
    var named = sel && sel !== AUTO;
    // what appears when the machine runs keeps its place from the start (hidden, not removed): nothing moves then
    var vis = function (el, on) { el.style.visibility = on ? '' : 'hidden'; el.tabIndex = on ? 0 : -1; el.setAttribute('aria-hidden', String(!on)); };
    vis(B.mic, ready); vis(meterCv, ready); vis(B.save, ready); vis(B.saveas, ready);
    vis(B.down, ready || !!sel); vis(B.vst, ready || !!sel);
    B.rename.hidden = !named; B.del.hidden = !named;
  }
  function refreshSlots() {
    if (!U || !iconsEl) return Promise.resolve();
    return slots.list().then(function (all) {
      all.sort(function (a, b) { return a.name === AUTO ? -1 : b.name === AUTO ? 1 : a.name < b.name ? -1 : 1; });
      iconsEl.textContent = ''; iconBtns = {};
      var bytes = 0;
      all.forEach(function (sl) {
        bytes += sl.data.length;
        var ic = U.icon(sl.name + '.B16', { aria: (sl.name === AUTO ? 'Autosave' : sl.name) + ' slot: Enter or double-click to load' });
        ic.addEventListener('click', function () { select(sl.name); });
        ic.addEventListener('dblclick', function () { loadSlot(sl.name); });
        ic.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') { e.preventDefault(); loadSlot(sl.name); }
          else if (e.key === 'Delete' && sl.name !== AUTO) { e.preventDefault(); select(sl.name); B.del.click(); }
          else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { var n = e.key === 'ArrowRight' ? ic.nextSibling : ic.previousSibling; if (n) { n.focus(); n.click(); } }
        });
        iconsEl.appendChild(ic); iconBtns[sl.name] = ic;
      });
      if (!all.length) { var hint = U.label('Saved states appear here: Save As... keeps one; Open... or drop a .b16 file.', { color: U.C.gray }); hint.style.margin = '6px'; iconsEl.appendChild(hint); }
      if (sel && !iconBtns[sel]) sel = null;
      select(sel);
      var est = navigator.storage && navigator.storage.estimate ? navigator.storage.estimate() : Promise.resolve(null);
      est.then(function () {
        note(all.length ? all.length + (all.length === 1 ? ' state' : ' states') + ', ' + Math.max(1, Math.round(bytes / 1024)) + ' KB' : (ready ? 'No saved states yet.' : ''));
      });
    });
  }
  function loadSlot(name) {
    return slots.list().then(function (all) {
      var sl = all.filter(function (x) { return x.name === name; })[0]; if (!sl) return;
      return decodeB16(sl.data).then(function (t) { select(name); if (applyState(t)) note('Loaded ' + name + '.B16'); });
    }).catch(function (e) { note('Could not load it: ' + e.message); });
  }
  function download(bytes, name, type) {
    var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([bytes], { type: type })); a.download = name;
    document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function currentOrSelected() {   // the running synth's state, or (before it runs) the selected slot's
    if (ready) return Promise.resolve(stateText());
    return slots.list().then(function (all) { var sl = all.filter(function (x) { return x.name === sel; })[0]; if (!sl) throw new Error('nothing selected'); return decodeB16(sl.data); });
  }
  function openFiles(files) {
    var f = files && files[0]; if (!f) return;
    if (/\.wav$/i.test(f.name) || f.type === 'audio/wav' || f.type === 'audio/x-wav') { note('WAV import into Sound Recorder is not in this version yet.'); return; }
    readStateFile(f).then(function (t) {
      var name = eightThree(f.name.replace(/\.[^.]*$/, '')) || 'IMPORT';
      return encodeB16(t).then(function (b) { return slots.put(name, b); }).then(function () { return refreshSlots(); }).then(function () { select(name); applyState(t); note('Opened ' + f.name); });
    }).catch(function (e) { note(e.message.charAt(0).toUpperCase() + e.message.slice(1) + '.'); });
  }
  api.openFiles = openFiles;
  function buildRow() {
    if (!U || !row) return;
    var picker = document.createElement('input'); picker.type = 'file'; picker.accept = '.b16,.vstpreset,application/x-basilisk16-state'; picker.hidden = true;
    picker.addEventListener('change', function () { openFiles(picker.files); picker.value = ''; });
    row.appendChild(picker);
    B.mic = U.button('', { sprite: 'mic', width: 27, aria: 'Microphone into Sound Recorder' });
    meterCv = document.createElement('canvas'); meterCv.className = 'b16meter'; meterCv.setAttribute('aria-hidden', 'true');
    B.open = U.button('Open...', { aria: 'Open a state file (.b16 or .vstpreset)' });
    B.save = U.button('Save', { aria: 'Save the state into the selected slot' });
    B.saveas = U.button('Save As...', { aria: 'Save the state into a new named slot' });
    B.rename = U.button('Rename...'); B.del = U.button('Delete');
    B.down = U.button('Download', { aria: 'Download the state as a .b16 file' });
    B.vst = U.button('VST3 Preset', { aria: 'Download the state as a .vstpreset for the BASILISK 16 plugin' });
    statusL = U.label('', { max: 360 });
    [B.mic, meterCv, B.open, B.save, B.saveas, B.down, B.vst, B.rename, B.del, statusL].forEach(function (el) { btnsEl.appendChild(el); });
    drawMeter(0);
    B.open.addEventListener('click', function () { picker.click(); });
    B.save.addEventListener('click', function () {
      if (!sel || sel === AUTO) { B.saveas.click(); return; }
      encodeB16(stateText()).then(function (b) { return slots.put(sel, b); }).then(refreshSlots).then(function () { note('Saved ' + sel + '.B16'); });
    });
    B.saveas.addEventListener('click', function () {
      U.dialog(stage, { title: 'Save As', prompt: 'State name (8 letters):', value: sel && sel !== AUTO ? sel : '', filter: eightThree }).then(function (v) {
        v = eightThree(v); if (!v) return;
        if (v === AUTO) { note('AUTOSAVE is the automatic slot: choose another name.'); return; }
        return encodeB16(stateText()).then(function (b) { return slots.put(v, b); }).then(refreshSlots).then(function () { select(v); note('Saved ' + v + '.B16'); });
      });
    });
    B.rename.addEventListener('click', function () {
      var old = sel; if (!old || old === AUTO) return;
      U.dialog(stage, { title: 'Rename', prompt: 'New name for ' + old + '.B16:', value: old, filter: eightThree }).then(function (v) {
        v = eightThree(v); if (!v || v === old || v === AUTO) return;
        return slots.list().then(function (all) { var sl = all.filter(function (x) { return x.name === old; })[0]; if (!sl) return;
          return slots.put(v, sl.data).then(function () { return slots.del(old); }); }).then(refreshSlots).then(function () { select(v); });
      });
    });
    B.del.addEventListener('click', function () {
      var old = sel; if (!old || old === AUTO) return;
      U.dialog(stage, { title: 'Delete', prompt: 'Delete ' + old + '.B16?', edit: false, ok: 'Delete' }).then(function (v) {
        if (v) return slots.del(old).then(function () { sel = null; return refreshSlots(); });
      });
    });
    B.down.addEventListener('click', function () {
      currentOrSelected().then(encodeB16).then(function (b) { download(b, (sel && !ready ? sel : 'BASILISK') + '.b16', 'application/x-basilisk16-state'); }).catch(function (e) { note(e.message); });
    });
    B.vst.addEventListener('click', function () {
      currentOrSelected().then(function (t) { download(encodeVstPreset(t), (sel && !ready ? sel : 'BASILISK 16') + '.vstpreset', 'application/octet-stream'); }).catch(function (e) { note(e.message); });
    });
    B.mic.addEventListener('click', toggleMic);
    showButtons();
    refreshSlots();
  }

  // ---------------------------------------------------------------- the microphone into Sound Recorder (the card's ADC)
  var mic = null;
  function drawMeter(level) {
    if (!U || !meterCv) return;
    var W = 8, H = 23, n = Math.round(Math.min(1, level * 1.4) * 9);
    U.canvas(meterCv, W, H, function (ctx) {
      ctx.fillStyle = U.C.lo; ctx.fillRect(0, 0, W, 1); ctx.fillRect(0, 0, 1, H);
      ctx.fillStyle = U.C.hi; ctx.fillRect(0, H - 1, W, 1); ctx.fillRect(W - 1, 0, 1, H);
      ctx.fillStyle = U.C.ink; ctx.fillRect(1, 1, W - 2, H - 2);
      for (var i = 0; i < 9; i++) { ctx.fillStyle = i < n ? (i >= 7 ? '#ff0000' : i >= 5 ? '#ffff00' : '#00ff00') : '#004000'; ctx.fillRect(2, H - 4 - i * 2 - 1, W - 4, 1); }
    });
  }
  function toggleMic() {
    if (mic) { stopMic(); note('Microphone off.'); return; }
    if (!ready || !actx || !navigator.mediaDevices) return;
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } }).then(function (s) {
      var src = actx.createMediaStreamSource(s), n = new AudioWorkletNode(actx, 'b16-mic', { numberOfInputs: 1, numberOfOutputs: 0 });
      src.connect(n);
      var lvl = 0;
      n.port.onmessage = function (e) { if (worker) worker.postMessage({ t: 'mic', d: e.data.d }, [e.data.d.buffer]); lvl = Math.max(e.data.peak, lvl * 0.7); drawMeter(lvl); };
      mic = { s: s, src: src, n: n };
      worker.postMessage({ t: 'micon', on: true });
      B.mic.setToggled(true);
      note('Microphone on: press Record in a Sound Recorder.');
    }, function (err) {
      note(err && err.name === 'NotAllowedError' ? 'The microphone was not allowed. Allow it in the address bar, then try again.' : 'No microphone could be opened (' + (err && err.name || 'error') + ').');
    });
  }
  function stopMic() {
    if (!mic) return;
    try { mic.s.getTracks().forEach(function (t) { t.stop(); }); mic.src.disconnect(); mic.n.disconnect(); } catch (e) {}
    mic = null; if (worker) worker.postMessage({ t: 'micon', on: false });
    if (B.mic) B.mic.setToggled(false); drawMeter(0);
  }
  api.mic = function () { return !!mic; };

  // ---------------------------------------------------------------- drag and drop onto the screen
  var stage = $('.b16stage'), dropEl = $('.b16drop'), dragN = 0;
  function dropMsg(show) {
    if (!dropEl || !U) return;
    dropEl.hidden = !show;
    if (show) {
      var cv = dropEl.querySelector('canvas'), t = 'Drop here to load this synth state', W = U.measure(t, 'system') + 40, H = 46;
      U.canvas(cv, W, H, function (ctx) {
        ctx.fillStyle = U.C.ink; ctx.fillRect(0, 0, W, H); ctx.fillStyle = U.C.face; ctx.fillRect(1, 1, W - 2, H - 2);
        ctx.fillStyle = U.C.hi; ctx.fillRect(1, 1, W - 3, 1); ctx.fillRect(1, 1, 1, H - 3);
        ctx.fillStyle = U.C.lo; ctx.fillRect(1, H - 2, W - 2, 1); ctx.fillRect(W - 2, 1, 1, H - 2);
        U.text(ctx, t, 20, (H - U.fontHeight('system')) >> 1, 'system', U.C.ink);
      });
    }
  }
  function hasFiles(e) { return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0; }
  window.addEventListener('dragenter', function (e) { if (hasFiles(e)) { dragN++; dropMsg(true); } });
  window.addEventListener('dragleave', function () { if (--dragN <= 0) { dragN = 0; dropMsg(false); } });
  window.addEventListener('dragover', function (e) { if (hasFiles(e) && stage && stage.contains(e.target)) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; } });
  window.addEventListener('drop', function (e) {
    dragN = 0; dropMsg(false);
    if (!hasFiles(e) || !stage || !stage.contains(e.target)) return;
    e.preventDefault(); openFiles(e.dataTransfer.files);
  });

  // ---------------------------------------------------------------- the emulator's own events
  function onRunning() {
    if (pendingState) { var t = pendingState; pendingState = null; applyState(t); }
    showButtons(); refreshSlots();
  }
  function onHeartbeat(m) {
    if (m.dna && m.dna !== curDna) { curDna = m.dna; autosave(); }
  }
  function onStopped() { stopMic(); showButtons(); }
  if (U) U.load(base, CFG.v).then(buildRow).catch(function () {});
  // a machine started without a click (a dropped file, a slot opened by keyboard) may get a suspended AudioContext:
  // the next click lets it play
  document.addEventListener('pointerdown', function () { if (actx && actx.state === 'suspended' && !paused) actx.resume(); }, true);

  // ---------------------------------------------------------------- tests
  var pending = {}, nextId = 1;
  api.start = start;
  api.info = function () { return new Promise(function (res) { if (!worker) return res(null); var id = nextId++; pending[id] = res; worker.postMessage({ t: 'info', id: id }); }); };
  api.stall = function (ms) { if (worker) worker.postMessage({ t: 'stall', ms: ms }); };
  api.engineStall = function () { if (worker) worker.postMessage({ t: 'enginestall' }); };
  api.tap = function (on, sink) { api.tapSink = sink; if (node) node.port.postMessage({ t: 'tap', on: on }); };
  api.ctxRate = function () { return actx && actx.sampleRate; };
})();

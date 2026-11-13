// BASILISK 16 in the browser: the worker that runs the machine (appended to the Emscripten output, b16-worker.js,
// so that the engine's own threads load the same file). It fetches the machine, resumes the snapshot, runs the
// host's tick, draws Windows' screen and passes the pointer, the keys and MIDI on. The page never waits for it.
if (typeof WorkerGlobalScope !== 'undefined' && self.name !== 'em-pthread') (function () {
  'use strict';
  let M = null, lay = null, S = 0, img = null, tickTimer = 0, running = false;
  let t0 = 0, lastPost = 0;
  const post = (m, tr) => self.postMessage(m, tr || []);

  async function fetchAll(files, onBytes) {
    // every file in parallel; progress in bytes as they arrive
    return Promise.all(files.map(async f => {
      const r = await fetch(f.url, { credentials: 'same-origin' });
      if (!r.ok) throw new Error(f.url + ': HTTP ' + r.status);
      const len = f.size || +r.headers.get('Content-Length') || 0;
      const out = new Uint8Array(len);
      let at = 0, chunks = null;
      const rd = r.body.getReader();
      for (;;) {
        const { done, value } = await rd.read();
        if (done) break;
        if (!chunks && at + value.length <= out.length) out.set(value, at);
        else { if (!chunks) chunks = [out.subarray(0, at)]; chunks.push(value); }
        at += value.length; onBytes(value.length);
      }
      if (chunks) { const all = new Uint8Array(at); let p = 0; for (const c of chunks) { all.set(c, p); p += c.length; } return all; }
      return at === out.length ? out : out.subarray(0, at);
    }));
  }

  function info(withLog) { return JSON.parse(M.UTF8ToString(M._b16_info(withLog ? 1 : 0))); }

  // the screen goes to the page as an ImageBitmap at Windows' own 1024x768: the page draws it at exactly k x k device
  // pixels per Windows pixel (pxfit, the site's pixel-exact pictures), never resampled
  let inFlight = false;
  function draw() {
    if (!running) return;
    const p = inFlight ? 0 : M._b16_frame();
    if (p) {
      const h32 = new Uint32Array(M.wasmMemory.buffer);
      const w = h32[p >> 2], h = h32[(p >> 2) + 1];
      if (!img || img.width !== w || img.height !== h) img = new ImageData(w, h);
      img.data.set(new Uint8Array(M.wasmMemory.buffer, p + 8, w * h * 4));
      inFlight = true;
      createImageBitmap(img).then(bm => { inFlight = false; post({ t: 'frame', bitmap: bm }, [bm]); }, () => { inFlight = false; });
    }
    setTimeout(draw, 16);
  }

  function tick() {
    if (!running) return;
    M._b16_tick();
    const now = performance.now();
    if (now - lastPost > 250) {
      lastPost = now;
      const i = info(false);
      post({ t: 'hb', dac: i.dac, beat: i.beat, load: i.load, late: i.late, ontime: i.ontime, state: i.state, ready: i.ready,
             building: i.building || i.inFlight, dna: i.dna, notes: i.notes, keys: i.keys, error: i.error });
      if (i.state === 9) { running = false; post({ t: 'error', msg: i.error || 'the machine stopped' }); }
    }
  }

  async function init(m) {
    t0 = performance.now();
    const files = m.files;   // [{name, url, size}] : b16.wasm, w31web.state, drive.zip
    let loaded = 0; const total = files.reduce((a, f) => a + (f.size || 0), 0);
    let lastP = 0;
    const bufs = await fetchAll(files, n => {
      loaded += n;
      const now = performance.now();
      if (now - lastP > 60) { lastP = now; post({ t: 'progress', loaded, total }); }
    });
    post({ t: 'progress', loaded: total, total });
    const tFetched = performance.now();
    const by = {}; files.forEach((f, i) => by[f.name] = bufs[i]);
    M = await B16Module({ wasmBinary: by['b16.wasm'], print: s => console.log('[b16] ' + s), printErr: s => console.log('[b16] ' + s) });
    const tModule = performance.now();
    M.FS.mkdir('/machine');
    M.FS.writeFile('/machine/drive.zip', by['drive.zip']);
    M.FS.writeFile('/machine/w31web.state', by['w31web.state']);
    M.FS.writeFile('/machine/w31.conf', m.conf);
    if (!M._b16_fetchfile(M.stringToNewUTF8('/machine/library.zip'), M.stringToNewUTF8(m.libraryUrl), m.librarySize, m.libraryChunk || 262144))
      throw new Error('cannot set up the library disc');
    const ok = M.ccall('b16_start', 'number', ['string', 'string', 'string', 'string', 'number', 'string'],
                       ['/machine/w31.conf', '/machine/w31web.state', '', '', m.lead || 2048, m.libraryNames || '']);
    if (!ok) throw new Error('the engine did not start');
    if (m.relDrag === false) M._b16_relscale(0);   // (the guest's driver moves the pointer during drags itself)
    (m.layers || []).forEach((L, i) => { if (L[0]) M._b16_layer(i, L[1], L[2], L[3], L[4]); });
    const o = M._b16_layout() >> 2, h32 = new Int32Array(M.wasmMemory.buffer);
    lay = {}; ['state', 'quit', 'host_beat', 'engine_beat', 'dac_w', 'host_r', 'realtime', 'vid_seq', 'vid_w', 'vid_h', 'vid_want',
               'mouse_x', 'mouse_y', 'mouse_btn', 'mouse_seq', 'ring', 'vid', 'ring_len', 'underruns', 'emu_load', 'offline',
               'grant_until', 'sched_late', 'error', 'gain', 'size', 'w', 'h'].forEach((k, i) => lay[k] = h32[o + i]);
    S = M._b16_shm();
    running = true;
    tickTimer = setInterval(tick, 4);
    // the AudioWorklet reads the card's DAC ring straight out of the machine's memory
    post({ t: 'mem', buffer: M.wasmMemory.buffer, base: S, lay });
    // ready: Windows answered (the snapshot was taken with BASILISK 16 assembled)
    let tRunning = 0;
    await new Promise((res, rej) => {
      const w = () => {
        const i = info(false);
        if (i.state >= 2 && !tRunning) tRunning = performance.now();
        if (i.state === 9) return rej(new Error(i.error || 'the machine snapshot did not load'));
        if (i.ready) return res();
        setTimeout(w, 5);
      };
      w();
    });
    draw();
    const tReady = performance.now();
    post({ t: 'ready', ms: { fetch: Math.round(tFetched - t0), module: Math.round(tModule - tFetched), resume: Math.round(tRunning - tModule),
                             answer: Math.round(tReady - tRunning), total: Math.round(tReady - t0) } });
  }

  self.onmessage = e => {
    const m = e.data;
    try {
      switch (m.t) {
      case 'init': init(m).catch(err => post({ t: 'error', msg: String(err && err.message || err) })); break;
      case 'm': if (M) M._b16_mouse(m.x, m.y); break;
      case 'b': if (M) { if (m.x !== undefined) M._b16_mouse(m.x, m.y); M._b16_button(m.bit, m.down ? 1 : 0); } break;
      case 'k': if (M) M._b16_key(m.down ? 1 : 0, m.rk); break;
      case 'midi': if (M) M._b16_midi(m.d[0], m.d[1] || 0, m.d[2] || 0); break;
      case 'dna': if (M) { const p = M.stringToNewUTF8(m.text); M._b16_dna(p); M._free(p); } break;
      case 'pause': if (M) M._b16_pause(m.p ? 1 : 0); break;
      case 'info': { const r = M ? info(true) : null; if (r) r.lazy = Array.from(new Uint32Array(M.wasmMemory.buffer, M._b16_lazy_vars(), 8)); post({ t: 'info', id: m.id, info: r }); break; }
      // tests: make the worker (or only the engine) stop answering, to see the page's watchdog act
      case 'stall': { const end = performance.now() + m.ms; while (performance.now() < end) {} break; }
      case 'enginestall': if (M) new Uint32Array(M.wasmMemory.buffer)[(S + lay.quit) >> 2] = 1; break;   // the engine thread ends: no frames, no sound
      }
    } catch (err) { post({ t: 'error', msg: String(err && err.message || err) }); }
  };
})();

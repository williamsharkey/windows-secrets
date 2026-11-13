// BASILISK 3.11 in the browser: the worker that runs the machine (appended to the Emscripten output, b31-worker.js,
// so the engine's own threads load the same file). Adapted from tools/basilisk16-web/worker-main.js. It fetches the
// engine, the snapshot and C:, resumes the snapshot (BASILISK 3.11 already assembled), draws Windows' screen, passes
// the pointer and the keys on, and carries BASILISK.EXE's lines to and from the page.
if (typeof WorkerGlobalScope !== 'undefined' && self.name !== 'em-pthread') (function () {
  'use strict';
  let M = null, S = 0, dacOff = 0, img = null, running = false, paused = false;
  const post = (m, tr) => self.postMessage(m, tr || []);

  async function fetchBytes(url, onBytes) {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) throw new Error(url + ': HTTP ' + r.status);
    const parts = []; let n = 0;
    const rd = r.body.getReader();
    for (;;) { const { done, value } = await rd.read(); if (done) break; parts.push(value); n += value.length; onBytes(value.length); }
    const out = new Uint8Array(n); let p = 0; for (const c of parts) { out.set(c, p); p += c.length; }
    return out;
  }
  // C: as one gzip stream of records: [u16 name length][name][u32 size][bytes]; names ending in / are folders
  async function unpack(gz, root) {
    const raw = new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
    const dv = new DataView(raw.buffer); let p = 0, files = 0;
    const td = new TextDecoder('latin1');
    while (p < raw.length) {
      const nl = dv.getUint16(p, true); p += 2;
      const name = td.decode(raw.subarray(p, p + nl)); p += nl;
      const sz = dv.getUint32(p, true); p += 4;
      if (name.endsWith('/')) M.FS.mkdirTree(root + '/' + name.slice(0, -1));
      else { M.FS.writeFile(root + '/' + name, raw.subarray(p, p + sz)); files++; }
      p += sz;
    }
    return files;
  }

  let inFlight = false;
  function draw() {
    if (!running) return;
    const p = inFlight || paused ? 0 : M._b31_frame();
    if (p) {
      const h32 = new Uint32Array(M.wasmMemory.buffer), w = h32[p >> 2], h = h32[(p >> 2) + 1];
      if (!img || img.width !== w || img.height !== h) img = new ImageData(w, h);
      img.data.set(new Uint8Array(M.wasmMemory.buffer, p + 8, w * h * 4));
      inFlight = true;
      createImageBitmap(img).then(bm => { inFlight = false; post({ t: 'frame', bitmap: bm }, [bm]); }, () => { inFlight = false; });
    }
    setTimeout(draw, 16);
  }
  function latin1At(p) { const h = new Uint8Array(M.wasmMemory.buffer); let e = p; while (h[e]) e++; let s = ''; for (let i = p; i < e; i += 8192) s += String.fromCharCode.apply(null, h.subarray(i, Math.min(e, i + 8192))); return s; }
  function sendLatin1(s) { const p = M._malloc(s.length + 1), h = new Uint8Array(M.wasmMemory.buffer); for (let i = 0; i < s.length; i++) { const c = s.charCodeAt(i); h[p + i] = c > 0 && c < 256 ? c : 63; } h[p + s.length] = 0; M._b31_send(p); M._free(p); }
  function info() { return JSON.parse(M.UTF8ToString(M._b31_info())); }
  let lastPost = 0, lastDac = -1, lastDacT = 0;
  function tick() {
    if (!running) return;
    const s = latin1At(M._b31_tick());
    if (s) post({ t: 'lines', s });
    const now = performance.now();
    const d = new Uint32Array(M.wasmMemory.buffer)[(S + dacOff) >> 2];
    if (d !== lastDac) { lastDac = d; lastDacT = now; }
    if (now - lastPost > 250) {
      lastPost = now;
      const i = info();
      post({ t: 'hb', dac: i.dac, beat: i.beat, load: i.load, state: i.state, dacAge: paused ? 0 : now - lastDacT });
      if (i.state === 9) { running = false; post({ t: 'error', msg: i.error || 'the machine stopped' }); }
    }
  }
  async function init(m) {
    const t0 = performance.now();
    let loaded = 0, lastP = 0; const total = m.files.reduce((a, f) => a + (f.size || 0), 0);
    const bufs = await Promise.all(m.files.map(f => fetchBytes(f.url, n => {
      loaded += n; const now = performance.now();
      if (now - lastP > 60) { lastP = now; post({ t: 'progress', loaded, total }); }
    })));
    const by = {}; m.files.forEach((f, i) => by[f.name] = bufs[i]);
    const tFetched = performance.now();
    M = await B31Module({ wasmBinary: by['b31.wasm'], print: s => console.log('[b31] ' + s), printErr: s => console.log('[b31] ' + s) });
    M.FS.mkdir('/machine'); M.FS.mkdir('/machine/c');
    const files = await unpack(by['drive.bin.gz'], '/machine/c');
    M.FS.writeFile('/machine/w31web.state', by['w31web.state']);
    M.FS.writeFile('/machine/w31.conf', m.conf);
    const tUnpacked = performance.now();
    if (!M.ccall('b31_start', 'number', ['string', 'string', 'string', 'string'], ['/machine/w31.conf', '/machine/w31web.state', '', '']))
      throw new Error('the engine did not start');
    S = M._b31_shm(); dacOff = M._b31_dac_off();
    running = true;
    setInterval(tick, 4);
    await new Promise((res, rej) => {
      const w = () => { const i = info(); if (i.state === 9) return rej(new Error(i.error || 'the snapshot did not load')); if (i.state >= 2) return res(); setTimeout(w, 5); };
      w();
    });
    draw();
    post({ t: 'ready', files, ms: { fetch: Math.round(tFetched - t0), unpack: Math.round(tUnpacked - tFetched), resume: Math.round(performance.now() - tUnpacked), total: Math.round(performance.now() - t0) } });
  }
  self.onmessage = e => {
    const m = e.data;
    try {
      switch (m.t) {
      case 'init': init(m).catch(err => post({ t: 'error', msg: String(err && err.message || err) })); break;
      case 'm': if (M) M._b31_mouse(m.x, m.y); break;
      case 'b': if (M) { if (m.x !== undefined) M._b31_mouse(m.x, m.y); M._b31_button(m.bit, m.down ? 1 : 0); } break;
      case 'k': if (M) M._b31_key(m.down ? 1 : 0, m.rk); break;
      case 'send': if (M) sendLatin1(m.s); break;
      case 'pause': if (M) { M._b31_pause(m.p ? 1 : 0); paused = !!m.p; } break;
      case 'info': post({ t: 'info', id: m.id, info: M ? info() : null }); break;
      case 'read': { let d = null; try { d = M.FS.readFile('/machine/c/' + m.path); } catch (err) {} post({ t: 'file', id: m.id, data: d }); break; }
      case 'stall': { const end = performance.now() + m.ms; while (performance.now() < end) {} break; }
      }
    } catch (err) { post({ t: 'error', msg: String(err && err.message || err) }); }
  };
})();

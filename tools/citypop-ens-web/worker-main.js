// SNDWAVE1993 Ensemble in the browser: the worker that runs the machine (appended to the Emscripten output,
// ens-worker.js, so the engine's own threads load the same file). It fetches the machine, resumes the snapshot, runs
// the album player's tick, draws Windows' screen and passes the pointer and keys on. The page never waits for it.
if (typeof WorkerGlobalScope !== 'undefined' && self.name !== 'em-pthread') (function () {
  'use strict';
  let M = null, lay = null, S = 0, img = null, running = false, lastPost = 0;
  const post = (m, tr) => self.postMessage(m, tr || []);

  async function fetchAll(files, onBytes) {
    return Promise.all(files.map(async f => {
      const r = await fetch(f.url, { credentials: 'same-origin' });
      if (!r.ok) throw new Error(f.url + ': HTTP ' + r.status);
      const parts = []; let at = 0;
      const rd = r.body.getReader();
      for (;;) { const { done, value } = await rd.read(); if (done) break; parts.push(value); at += value.length; onBytes(value.length); }
      const all = new Uint8Array(at); let p = 0; for (const c of parts) { all.set(c, p); p += c.length; }
      return all;
    }));
  }

  // the pack disc (P:, packs.zip) is read in pieces; the pieces of the sounds the next presets use are fetched ahead
  let disc = null; const discQ = []; let discBusy = false;
  function discWant(ranges, first) {
    if (!disc) return;
    const c = disc.chunk, add = [];
    for (const [a, e] of ranges) for (let i = Math.floor(a / c); i <= Math.floor((e - 1) / c); i++) add.push(i);
    if (first) discQ.unshift(...add); else discQ.push(...add);
    discPump();
  }
  async function discPump() {
    if (discBusy) return; discBusy = true;
    try {
      while (discQ.length && running) {
        const i = discQ.shift();
        if (M._b16_lazy_has(i)) continue;
        const a = i * disc.chunk, e = Math.min(disc.size, a + disc.chunk) - 1;
        const r = await fetch(disc.url, { headers: { Range: 'bytes=' + a + '-' + e } });
        if (r.status !== 206) continue;
        M.b16LazyCache.set(a, new Uint8Array(await r.arrayBuffer()));
      }
    } catch (err) {} finally { discBusy = false; }
  }

  function info(withLog) { return JSON.parse(M.UTF8ToString(M._ens_info(withLog ? 1 : 0))); }

  // Windows' screen, a few times a second: DOSBox renders a frame only when one is asked for (vid_want), so the
  // emulator does not draw 60 frames a second nobody needs (the scaler costs as much as a third of a busy machine)
  let inFlight = false, frames = 0, asked = 0;
  const FRAME_MS = 160;
  function want(on) { new Uint32Array(M.wasmMemory.buffer)[(S + lay.vid_want) >> 2] = on ? 1 : 0; }
  function draw() {
    if (!running) return;
    const now = performance.now();
    const seq = () => new Uint32Array(M.wasmMemory.buffer)[(S + lay.vid_seq) >> 2];
    if (!asked && now - lastFrame >= FRAME_MS) { want(true); asked = now; seqAsked = seq(); }
    let p = 0;
    if (asked && !inFlight && seq() !== seqAsked && !(seq() & 1)) {   // a frame came: take it (if it changed), and no more
      p = M._ens_frame(); want(false); asked = 0; lastFrame = now;
    } else if (asked && now - asked > 500) { want(false); asked = 0; lastFrame = now; }
    if (p) {
      const h32 = new Uint32Array(M.wasmMemory.buffer);
      const w = h32[p >> 2], h = h32[(p >> 2) + 1];
      if (!img || img.width !== w || img.height !== h) img = new ImageData(w, h);
      img.data.set(new Uint8Array(M.wasmMemory.buffer, p + 8, w * h * 4));
      inFlight = true; frames++;
      createImageBitmap(img).then(bm => { inFlight = false; post({ t: 'frame', bitmap: bm }, [bm]); }, () => { inFlight = false; });
    }
    setTimeout(draw, 20);
  }
  let lastFrame = 0, seqAsked = 0;

  let wantTrack = -1, prefetched = -1, schedule = null;
  function tick() {
    if (!running) return;
    M._ens_tick();
    const now = performance.now();
    if (now - lastPost > 250) {
      lastPost = now;
      const i = info(false);
      // fetch ahead: the sounds of the track after the one now playing
      if (schedule && i.track >= 0 && prefetched < i.track + 1) { prefetched = i.track + 1; discWant(schedule.ranges[prefetched] || [], false); }
      post({ t: 'hb', info: i });
      if (i.state === 9) { running = false; post({ t: 'error', msg: i.error || 'the machine stopped' }); }
    }
  }

  async function init(m) {
    const t0 = performance.now();
    const files = m.files;
    let loaded = 0, lastP = 0; const total = files.reduce((a, f) => a + (f.size || 0), 0);
    const bufs = await fetchAll(files, n => { loaded += n; const now = performance.now(); if (now - lastP > 60) { lastP = now; post({ t: 'progress', loaded, total }); } });
    post({ t: 'progress', loaded: total, total });
    const by = {}; files.forEach((f, i) => by[f.name] = bufs[i]);
    M = await EnsModule({ wasmBinary: by['ens.wasm'], print: s => console.log('[ens] ' + s), printErr: s => console.log('[ens] ' + s) });
    M.FS.mkdir('/machine'); M.FS.mkdir('/machine/rec');
    M.FS.writeFile('/machine/drive.zip', by['drive.zip']);
    M.FS.writeFile('/machine/library.zip', by['library.zip']);
    if (by['ens.state.lzma']) {   // the snapshot, packed: unpacked here, in the engine's own memory
      const z = by['ens.state.lzma'], src = M._malloc(z.length); new Uint8Array(M.wasmMemory.buffer).set(z, src);
      const n = M._ens_unlzma_size(src), dst = M._malloc(n);
      const got = M._ens_unlzma(src, z.length, dst, n); M._free(src);
      if (got !== n) throw new Error('the snapshot did not unpack');
      M.FS.writeFile('/machine/w31web.state', new Uint8Array(M.wasmMemory.buffer, dst, n).slice()); M._free(dst);
    } else M.FS.writeFile('/machine/w31web.state', by['ens.state']);
    M.FS.writeFile('/machine/w31.conf', m.conf);
    if (!M._b16_fetchfile(M.stringToNewUTF8('/machine/packs.zip'), M.stringToNewUTF8(m.discUrl), m.discSize, m.discChunk || 262144))
      throw new Error('cannot set up the pack disc');
    M.b16LazyCache = new Map();
    disc = { url: m.discUrl, size: m.discSize, chunk: m.discChunk || 262144 };
    const album = new TextDecoder().decode(by['album.ens']);
    const pa = M.stringToNewUTF8(album); M._ens_album(pa); M._free(pa);
    schedule = m.schedule || null;
    if (schedule) {   // the first track's sounds before the first note (Windows reads them while it plays: a piece it waits
                      // for stops the emulator), the next track's behind them
      const c = disc.chunk, want = new Set();
      // (from the first track, whose sounds the snapshot holds built: the second track's, which build while it plays;
      // from any other: that track's own, which build before its first note - the next one's follow at once)
      for (const t of [(m.from || 0) === 0 ? 1 : m.from])
        for (const [a, e] of schedule.ranges[t] || []) for (let i = Math.floor(a / c); i <= Math.floor((e - 1) / c); i++) want.add(i);
      let got = 0; const all = [...want], total2 = all.length;
      await Promise.all([0, 1, 2, 3].map(async w => { for (let k = w; k < all.length; k += 4) {
        const i = all[k], a = i * c, e = Math.min(disc.size, a + c) - 1;
        const r = await fetch(disc.url, { headers: { Range: 'bytes=' + a + '-' + e } });
        if (r.status === 206) M.b16LazyCache.set(a, new Uint8Array(await r.arrayBuffer()));
        post({ t: 'progress', loaded: total + (++got) * c, total: total + total2 * c }); } }));
      prefetched = (m.from || 0);
    }
    if (m.colors) M._ens_colors(1);
    const ok = M.ccall('ens_start', 'number', ['string', 'string', 'string', 'string', 'number', 'string'],
                       ['/machine/w31.conf', '/machine/w31web.state', '', '', m.lead || 96000, m.libraryNames || '']);
    if (!ok) throw new Error('the engine did not start');
    const o = M._ens_layout() >> 2, h32 = new Int32Array(M.wasmMemory.buffer);
    lay = {}; ['state', 'quit', 'host_beat', 'engine_beat', 'dac_w', 'host_r', 'realtime', 'vid_seq', 'vid_w', 'vid_h', 'vid_want',
               'mouse_x', 'mouse_y', 'mouse_btn', 'mouse_seq', 'ring', 'vid', 'ring_len', 'underruns', 'emu_load', 'offline',
               'grant_until', 'sched_late', 'error', 'gain', 'size', 'w', 'h', 'lead'].forEach((k, i) => lay[k] = h32[o + i]);
    S = M._ens_shm();
    running = true;
    if (schedule) { prefetched = (m.from || 0) + 1; if (m.from) discWant(schedule.ranges[prefetched] || [], false); }
    setInterval(tick, 5);
    post({ t: 'mem', buffer: M.wasmMemory.buffer, base: S, lay });
    let resumed = false;
    await new Promise((res, rej) => {
      const w = () => {
        const i = info(false);
        if (i.state >= 2 && !resumed) { resumed = true; draw(); post({ t: 'resumed', ms: Math.round(performance.now() - t0) }); }
        if (i.state === 9) return rej(new Error(i.error || 'the machine snapshot did not load'));
        if (i.ready) return res();
        setTimeout(w, 5);
      };
      w();
    });
    post({ t: 'ready', ms: Math.round(performance.now() - t0) });
    // Windows' clock: the local time, in 1993 (29 February is the 28th: 1993 has none)
    const clock = () => { const d = new Date(); let mo = d.getMonth() + 1, da = d.getDate(); if (mo === 2 && da === 29) da = 28;
      const a = M.stringToNewUTF8(['time 1993', mo, da, d.getHours(), d.getMinutes(), d.getSeconds()].join(' ')); M._ens_line(a); M._free(a); };
    clock(); setInterval(clock, 60000);
    if (m.play !== false) M._ens_play(m.from || 0);
  }

  self.onmessage = e => {
    const m = e.data;
    try {
      switch (m.t) {
      case 'init': init(m).catch(err => post({ t: 'error', msg: String(err && err.message || err) })); break;
      case 'm': if (M) M._ens_mouse(m.x, m.y); break;
      case 'b': if (M) { if (m.x !== undefined) M._ens_mouse(m.x, m.y); M._ens_button(m.bit, m.down ? 1 : 0); } break;
      case 'k': if (M) M._ens_key(m.down ? 1 : 0, m.rk); break;
      case 'play': if (M) { prefetched = -1; if (schedule) discWant(schedule.ranges[m.track] || [], true); M._ens_play(m.track); } break;
      case 'stop': if (M) M._ens_stop(); break;
      case 'colors': if (M) M._ens_colors(m.on ? 1 : 0); break;
      case 'line': if (M) { const a = M.stringToNewUTF8(m.text); M._ens_line(a); M._free(a); } break;
      case 'pause': if (M) M._ens_pause(m.p ? 1 : 0); break;
      case 'stats': if (M) post({ t: 'stats', id: m.id, stats: JSON.parse(M.UTF8ToString(M._ens_stats())), info: info(true) }); break;
      }
    } catch (err) { post({ t: 'error', msg: String(err && err.message || err) }); }
  };
})();

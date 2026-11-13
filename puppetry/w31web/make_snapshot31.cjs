// BASILISK 3.11's snapshot for the DOSBox Pure web engine: boot Windows for Workgroups 3.11 in the engine itself
// (under node), let BASILISK.EXE assemble the suite, freeze the machine a few emulated seconds later, and write C: as
// Windows left it (so the snapshot's open files are all there when the browser resumes it).
//   node make_snapshot31.cjs OUT_DIR drive0.bin.gz w31.conf     -> OUT_DIR/w31web.state, drive.bin.gz, frame.rgba
const fs = require('fs'), path = require('path'), zlib = require('zlib');
const [outDir, drive0, confPath] = process.argv.slice(2);
const B31Module = require(path.resolve(outDir, 'b31-worker.js'));
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const M = await B31Module({ print: s => console.log('[b31] ' + s), printErr: s => console.error('[b31] ' + s) });
  M.FS.mkdir('/machine'); M.FS.mkdir('/machine/c');
  const raw = zlib.gunzipSync(fs.readFileSync(drive0));
  for (let p = 0; p < raw.length;) {
    const nl = raw.readUInt16LE(p); p += 2; const name = raw.subarray(p, p + nl).toString('latin1'); p += nl;
    const sz = raw.readUInt32LE(p); p += 4;
    if (name.endsWith('/')) M.FS.mkdirTree('/machine/c/' + name.slice(0, -1)); else M.FS.writeFile('/machine/c/' + name, raw.subarray(p, p + sz));
    p += sz;
  }
  M.FS.writeFile('/machine/w31.conf', fs.readFileSync(confPath));
  const t0 = Date.now();
  M.ccall('b31_start', 'number', ['string', 'string', 'string', 'string'], ['/machine/w31.conf', '', '/machine/w31web.state', '/machine/engine.log']);
  const info = () => JSON.parse(M.UTF8ToString(M._b31_info()));
  let assembledAt = 0, snapAt = 0, st;
  for (;;) {
    M._b31_grant(48000);           // flat out: no clock under node
    const ptr = M._b31_tick(); const h = new Uint8Array(M.wasmMemory.buffer); let e = ptr; while (h[e]) e++;
    const s = Buffer.from(h.subarray(ptr, e)).toString('latin1');
    for (const l of s.split('\x04').filter(Boolean)) {
      console.log('guest:', JSON.stringify(l.slice(0, 80)));
      if (l === 'Rassembled' && !assembledAt) { st = info(); assembledAt = st.dac; console.log('assembled at', ((Date.now() - t0) / 1000).toFixed(1), 's wall'); }
    }
    st = info();
    if (st.state === 9) throw new Error('engine failed: ' + st.error);
    if (assembledAt && !snapAt && st.dac > assembledAt + 3 * 48000) { M._b31_snapshot(); snapAt = st.dac; }
    if (snapAt) {
      let log = ''; try { log = new TextDecoder().decode(M.FS.readFile('/machine/engine.log')); } catch (e) {}
      if (log.includes('snapshot')) break;
    }
    if (Date.now() - t0 > 900000) throw new Error('timed out');
    await sleep(5);
  }
  let fp = 0;
  for (let k = 0; k < 400 && !fp; k++) { M._b31_grant(2000); await sleep(5); fp = M._b31_frame(); }
  if (fp) {
    const h32 = new Uint32Array(M.wasmMemory.buffer), w = h32[fp >> 2], h = h32[(fp >> 2) + 1];
    fs.writeFileSync(path.join(outDir, 'frame.rgba'), Buffer.from(new Uint8Array(M.wasmMemory.buffer, fp, 8 + w * h * 4)));
  }
  M._b31_stop();
  // C: as Windows left it, in the worker's format
  const parts = [];
  (function walk(dir, rel) {
    for (const n of M.FS.readdir(dir).filter(n => n !== '.' && n !== '..').sort()) {
      const full = dir + '/' + n, r = rel + n, isDir = (M.FS.stat(full).mode & 0o170000) === 0o040000;
      const nb = Buffer.from(isDir ? r + '/' : r, 'latin1'), data = isDir ? Buffer.alloc(0) : Buffer.from(M.FS.readFile(full));
      const hd = Buffer.alloc(2 + nb.length + 4); hd.writeUInt16LE(nb.length, 0); nb.copy(hd, 2); hd.writeUInt32LE(data.length, 2 + nb.length);
      parts.push(hd, data);
      if (isDir) walk(full, r + '/');
    }
  })('/machine/c', '');
  fs.writeFileSync(path.join(outDir, 'drive.bin.gz'), zlib.gzipSync(Buffer.concat(parts), { level: 9 }));
  fs.writeFileSync(path.join(outDir, 'w31web.state'), M.FS.readFile('/machine/w31web.state'));
  console.log(new TextDecoder().decode(M.FS.readFile('/machine/engine.log')));
  console.log('snapshot', fs.statSync(path.join(outDir, 'w31web.state')).size, 'drive', fs.statSync(path.join(outDir, 'drive.bin.gz')).size, 'in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });

// The web edition's snapshot: boot Windows for Workgroups 3.11 in the web engine itself (b16.wasm, under node),
// let it assemble BASILISK 16, build the default DNA, and freeze the machine there. The browser resumes from it,
// so the synth is ready the moment the snapshot is loaded (no boot, no assembly).
//
//   node make_snapshot.cjs OUT_DIR MACHINE_DIR LIBRARY.zip LIBRARY.names.txt
// writes OUT_DIR/w31web.state and OUT_DIR/state.json (the layer replies the host must know)
const fs = require('fs'), path = require('path');
const [outDir, machine, libZip, libNames] = process.argv.slice(2);
const B16Module = require(path.resolve(outDir, 'b16-worker.js'));
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const M = await B16Module({ print: s => console.log('[b16] ' + s), printErr: s => console.error('[b16] ' + s) });
  M.FS.mkdir('/machine');
  M.FS.writeFile('/machine/drive.zip', fs.readFileSync(path.join(machine, 'drive.zip')));
  M.FS.writeFile('/machine/library.zip', fs.readFileSync(libZip));
  M.FS.writeFile('/machine/w31.conf', fs.readFileSync(path.join(machine, 'w31.conf')));
  const names = fs.readFileSync(libNames, 'utf8');
  const t0 = Date.now();
  M.ccall('b16_start', 'number', ['string', 'string', 'string', 'string', 'number', 'string'],
          ['/machine/w31.conf', '', '/machine/w31web.state', '/machine/engine.log', 2048, names]);
  const info = () => JSON.parse(M.UTF8ToString(M._b16_info(1)));
  let st, readyAt = 0, snapAt = 0;
  for (;;) {
    // Windows runs at its own pace (the engine's clock) until the snapshot: run flat out, 1.2.1's guest leaves the
    // keyboard strip's white keys unpainted
    if (snapAt || (readyAt && st.dac > readyAt + 288000)) M._b16_grant(48000);
    M._b16_tick();
    st = info();
    for (const l of st.log) console.log('guest: ' + l);
    if (st.state === 9) throw new Error('engine failed: ' + st.error);
    if (!readyAt && st.ready && st.built > 0 && !st.inFlight) { readyAt = st.dac; console.log('ready + built at', ((Date.now() - t0) / 1000).toFixed(1), 's wall, dac', st.dac); }
    // six more emulated seconds for Windows to settle (paint everything, idle), then the snapshot
    if (readyAt && !snapAt && st.dac > readyAt + 288000) { M._b16_snapshot(); snapAt = st.dac; }
    if (snapAt) {
      let log = '';
      try { log = new TextDecoder().decode(M.FS.readFile('/machine/engine.log')); } catch (e) {}
      if (log.includes('snapshot')) break;
    }
    if (Date.now() - t0 > 600000) throw new Error('timed out');
    await sleep(5);
  }
  // the screen at the snapshot: the page's poster (frame.rgba, w and h first as two little-endian uint32)
  let fp = 0;
  for (let k = 0; k < 400 && !fp; k++) { M._b16_grant(2000); await sleep(5); fp = M._b16_frame(); }
  if (fp) {
    const h32 = new Uint32Array(M.wasmMemory.buffer), w = h32[fp >> 2], h = h32[(fp >> 2) + 1];
    fs.writeFileSync(path.join(outDir, 'frame.rgba'), Buffer.from(new Uint8Array(M.wasmMemory.buffer, fp, 8 + w * h * 4)));
    console.log('frame', w, 'x', h);
  }
  const state = M.FS.readFile('/machine/w31web.state');
  fs.writeFileSync(path.join(outDir, 'w31web.state'), state);
  fs.writeFileSync(path.join(outDir, 'state.json'), JSON.stringify({ dna: st.dna, layers: st.layers }) + '\n');
  console.log(new TextDecoder().decode(M.FS.readFile('/machine/engine.log')));
  console.log('snapshot', state.length, 'bytes; dna', st.dna, 'layers', JSON.stringify(st.layers), 'in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });

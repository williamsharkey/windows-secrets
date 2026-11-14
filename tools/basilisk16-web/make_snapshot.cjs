// The web edition's snapshot: boot Windows for Workgroups 3.11 in the web engine itself (b16.wasm, under node),
// let it assemble BASILISK 16, build the default DNA, and freeze the machine there. The browser resumes from it,
// so the synth is ready the moment the snapshot is loaded (no boot, no assembly).
//
//   node make_snapshot.cjs OUT_DIR MACHINE_DIR LIBRARY.zip LIBRARY.names.txt [--desktop SECONDS]
// writes OUT_DIR/w31web.state and OUT_DIR/state.json (the layer replies the host must know).
// --desktop: instead, the machine just as Windows reaches its desktop (SECONDS on the card's clock, before SYNTH.EXE
// starts its work), with nothing said to it yet: OUT_DIR/w31build.state, for "Watch it build" (the page then says
// hi/time/go, and the whole construction plays out: Calculator, the sixteen Sound Recorders, the assembly).
const fs = require('fs'), path = require('path');
const [outDir, machine, libZip, libNames] = process.argv.slice(2);
const desktop = process.argv.indexOf('--desktop') > 0 ? +process.argv[process.argv.indexOf('--desktop') + 1] : 0;
const stateName = desktop ? 'w31build.state' : 'w31web.state';
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
          ['/machine/w31.conf', '', '/machine/' + stateName, '/machine/engine.log', 2048, names]);
  const info = () => JSON.parse(M.UTF8ToString(M._b16_info(1)));
  let st, readyAt = 0, snapAt = 0;
  if (desktop) {   // no host lines at all (no tick): the card's queue stays empty for the page's own hello
    while (info().dac < desktop * 48000) { M._b16_grant(Math.min(4800, desktop * 48000 - info().dac + 1)); await sleep(2); }
    M._b16_snapshot();
    for (let k = 0; k < 3000; k++) { M._b16_grant(1); await sleep(2); let log = ''; try { log = new TextDecoder().decode(M.FS.readFile('/machine/engine.log')); } catch (e) {} if (log.includes('snapshot')) break; }
    const s2 = M.FS.readFile('/machine/' + stateName);
    fs.writeFileSync(path.join(outDir, stateName), s2);
    let fp = 0; for (let k = 0; k < 50 && !fp; k++) { fp = M._b16_frame(); await sleep(5); }
    if (fp) { const h32 = new Uint32Array(M.wasmMemory.buffer), w = h32[fp >> 2], h = h32[(fp >> 2) + 1];
      fs.writeFileSync(path.join(outDir, 'frame-build.rgba'), Buffer.from(new Uint8Array(M.wasmMemory.buffer, fp, 8 + w * h * 4))); }
    console.log('desktop snapshot', s2.length, 'bytes at', (info().dac / 48000).toFixed(2), 's on the card\'s clock');
    process.exit(0);
  }
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

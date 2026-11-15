// The Ensemble album page's snapshot: boot Windows for Workgroups 3.11 with ENSEMBLE.EXE in the web engine itself
// (ens-worker.js under node), wait until ENSEMBLE has started its ten lanes' first Sound Recorders and settled, and
// freeze the machine there, before `go`: the page then sees the whole assembly.
//   node make_snapshot.cjs OUT_DIR MACHINE_DIR LIBRARY.zip PACKS.zip NAMES.txt
const fs = require('fs'), path = require('path');
const [outDir, machine, libZip, packsZip, namesPath] = process.argv.slice(2);
const EnsModule = require(path.resolve(outDir, 'ens-worker.js'));
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const M = await EnsModule({ print: s => console.log('[ens] ' + s), printErr: s => console.error('[ens] ' + s) });
  M.FS.mkdir('/machine'); M.FS.mkdir('/machine/rec');
  M.FS.writeFile('/machine/drive.zip', fs.readFileSync(path.join(machine, 'drive.zip')));
  M.FS.writeFile('/machine/library.zip', fs.readFileSync(libZip));
  M.FS.writeFile('/machine/packs.zip', fs.readFileSync(packsZip));
  M.FS.writeFile('/machine/w31.conf', fs.readFileSync(path.join(outDir, 'w31.conf')));
  const t0 = Date.now();
  M._ens_quiet(1);
  M.ccall('ens_start', 'number', ['string', 'string', 'string', 'string', 'number', 'string'],
          ['/machine/w31.conf', '', '/machine/ens.state', '/machine/engine.log', 2048, fs.readFileSync(namesPath, 'utf8')]);
  const info = () => JSON.parse(M.UTF8ToString(M._ens_info(1)));
  let upAt = 0, snapAt = 0;
  for (;;) {
    M._ens_grant(48000); M._ens_tick();
    const st = info();
    for (const l of st.log) { console.log('guest: ' + l); if (l.indexOf('ENSEMBLE up') >= 0) upAt = st.dac; }
    if (st.state === 9) throw new Error('engine failed: ' + st.error);
    if (upAt && !snapAt && st.dac > upAt + 4 * 48000) { M._ens_snapshot(); snapAt = st.dac; }
    if (snapAt) { let log = ''; try { log = new TextDecoder().decode(M.FS.readFile('/machine/engine.log')); } catch (e) {} if (log.includes('snapshot')) break; }
    if (Date.now() - t0 > 900000) throw new Error('timed out');
    await sleep(5);
  }
  let fp = 0;
  for (let k = 0; k < 400 && !fp; k++) { M._ens_grant(2000); await sleep(5); fp = M._ens_frame(); }
  if (fp) { const h32 = new Uint32Array(M.wasmMemory.buffer), w = h32[fp >> 2], h = h32[(fp >> 2) + 1];
    fs.writeFileSync(path.join(outDir, 'frame.rgba'), Buffer.from(new Uint8Array(M.wasmMemory.buffer, fp, 8 + w * h * 4))); }
  const state = M.FS.readFile('/machine/ens.state');
  fs.writeFileSync(path.join(outDir, 'ens.state'), state);
  console.log('snapshot', state.length, 'bytes in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });

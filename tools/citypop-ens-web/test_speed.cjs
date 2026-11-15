// The web engine's speed under node: resume the page's snapshot, play the album from a track for SECONDS of album
// time as fast as the engine runs (granted, as albumrender), and report the real-time factor and the switches.
//   node test_speed.cjs OUT_DIR TRACK SECONDS
const fs = require('fs'), path = require('path');
const [outDir, track, seconds] = [process.argv[2], +process.argv[3] || 0, +process.argv[4] || 60];
const EnsModule = require(path.resolve(outDir, 'ens-worker.js'));
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const M = await EnsModule({ print: () => {}, printErr: s => console.error('[ens] ' + s) });
  M.FS.mkdir('/machine'); M.FS.mkdir('/machine/rec');
  for (const f of ['drive.zip', 'library.zip', 'packs.zip', 'w31.conf']) M.FS.writeFile('/machine/' + f, fs.readFileSync(path.join(outDir, f)));
  M.FS.writeFile('/machine/w31web.state', fs.readFileSync(path.join(outDir, 'ens.state')));
  const al = M.stringToNewUTF8(fs.readFileSync(path.join(outDir, 'album.ens'), 'utf8')); M._ens_album(al);
  M.ccall('ens_start', 'number', ['string', 'string', 'string', 'string', 'number', 'string'], ['/machine/w31.conf', '/machine/w31web.state', '', '', 2048, fs.readFileSync(path.join(outDir, 'names.txt'), 'utf8')]);
  const info = () => JSON.parse(M.UTF8ToString(M._ens_info(0)));
  if (process.env.NOVID) { const o = M._ens_layout() >> 2, h32 = new Int32Array(M.wasmMemory.buffer); new Uint32Array(M.wasmMemory.buffer)[(M._ens_shm() + h32[o + 10]) >> 2] = 0; }
  const t0 = Date.now(); let tReady = 0, tPlay = 0, startPos = -1;
  M._ens_play(track);
  const cpu0 = process.cpuUsage();
  for (;;) {
    M._ens_grant(2400); M._ens_tick();
    const i = info();
    if (i.ready && !tReady) tReady = Date.now();
    if (i.phase === 2 && !tPlay) { tPlay = Date.now(); startPos = i.emu; }
    if (i.state === 9) throw new Error(i.error);
    if (tPlay && i.emu - startPos >= seconds) {
      const wall = (Date.now() - tPlay) / 1000, cpu = process.cpuUsage(cpu0);
      console.log(JSON.stringify({ assemble_s: (tReady - t0) / 1000, firstPresets_s: (tPlay - tReady) / 1000, album_s: i.emu - startPos, wall_s: wall,
        realtime_x: (i.emu - startPos) / wall, cpu_s: (cpu.user + cpu.system) / 1e6, late: i.late, ontime: i.ontime, notes: i.notes, stats: JSON.parse(M.UTF8ToString(M._ens_stats())).slice(track, track + 2) }));
      process.exit(0);
    }
    await sleep(0);
  }
})().catch(e => { console.error(e); process.exit(1); });

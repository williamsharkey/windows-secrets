#!/usr/bin/env python3
"""BASILISK SYNTH (XP) macro presets: render the demo phrase with Macro 1 automated, through bsynth-host --set.

    xp_macro.py RENDER_DIR --host bsynth-host.exe --plugin BasiliskSynth.vst3 --work WINDIR [--tries 4] [--warmup 8]

The same curves as macro_bh.py (BASILISK 16 in BasiliskHost): a ramp is sent as a point every 50 ms
("--set Macro 1@T=V", plain value 0..100, T in score seconds), a step curve as its steps. One job at a time; each
take is checked as xp_render.py checks them (every note onset heard), up to --tries takes, the best kept.
Writes RENDER_DIR/wav/<slug>.wav (trimmed like xp_trim.py) and RENDER_DIR/macro.json (curves and takes).
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', '..', 'packages', 'basilisk-synth', 'tools'))
import macro_bh, xp_render, batch_render

ap = argparse.ArgumentParser()
ap.add_argument('render'); ap.add_argument('--host', required=True); ap.add_argument('--plugin', required=True); ap.add_argument('--work', required=True)
ap.add_argument('--tries', type=int, default=4); ap.add_argument('--warmup', type=float, default=8.0); ap.add_argument('--latency', type=int, default=4800)
a = ap.parse_args()
win = lambda p: subprocess.run(['wslpath', '-w', p], capture_output=True, text=True).stdout.strip()
os.makedirs(a.work, exist_ok=True)
done = {}
for row in json.load(open(os.path.join(a.render, 'presets.json'))):
    if row['kind'] != 'macro' or row['name'] not in macro_bh.CURVES: continue
    _, pts = macro_bh.curve_spec(macro_bh.CURVES[row['name']])
    sets = []
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        steps = max(1, int((t1 - t0) / 0.05))
        for k in range(steps): sets.append((t0 + (t1 - t0) * k / steps, v0 + (v1 - v0) * k / steps))
    sets.append(pts[-1])
    mid = os.path.join(a.render, 'mid', row['slug'] + '.mid')
    score = ','.join('%.4f:%d:%d:%.4f' % n for n in batch_render.midi_score(mid))
    tail = row['seconds'] - max(t + d for t, _, _, d in batch_render.midi_score(mid))
    best = None; takes = []
    for n in range(a.tries):
        out = os.path.join(a.work, '%s-%d.wav' % (row['slug'], n)); bat = os.path.join(a.work, 'm.bat')
        args = ['--offline', '--dna', row['dna'], '--score', score, '--warmup', str(a.warmup), '--tail', '%.3f' % tail]
        for t, v in sets: args += ['--set', 'Macro 1@%.3f=%.1f' % (t, v * 100)]
        with open(bat, 'w') as f:
            f.write('@echo off\r\nset BSYNTH_VISIBLE_BUILD=0\r\n"%s" "%s" "%s" %s\r\n' % (win(a.host), win(a.plugin), win(out), ' '.join('"%s"' % x.replace('%', '%%') for x in args)))
        subprocess.run(['cmd.exe', '/c', win(bat)], capture_output=True, text=True, cwd=a.work, timeout=600)
        if not os.path.exists(out): takes.append({'take': n, 'ok': False}); continue
        x = xp_render.take(out, row, a.warmup, a.latency)
        h, tot, pk = xp_render.heard(x, row, mid)
        takes.append({'take': n, 'heard': h, 'onsets': tot, 'peak': round(pk, 4)})
        if best is None or h > best[0]: best = (h, x)
        if h == tot: break
    if best:
        import struct
        x = best[1]
        hdr = b'RIFF' + struct.pack('<I', 36 + len(x)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 3, 2, 48000, 384000, 8, 32) + b'data' + struct.pack('<I', len(x))
        open(os.path.join(a.render, 'wav', row['slug'] + '.wav'), 'wb').write(hdr + x)
    done[row['slug']] = {'program': row['i'], 'curve': pts, 'sets': len(sets), 'takes': takes}
    print(row['slug'], takes, flush=True)
json.dump(done, open(os.path.join(a.render, 'macro.json'), 'w'), indent=1)

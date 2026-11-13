#!/usr/bin/env python3
"""Macro presets: render the demo phrase through the real VST3 in BasiliskHost (--test offline) with Macro 1 automated,
so the demo moves the macro the way a player would. Run from WSL; BasiliskHost.exe and the plugin bundle must sit on
a Windows drive.

    macro_bh.py RENDER_DIR WINDIR [--plugin Basilisk16.vst3] [--host BasiliskHost.exe]

RENDER_DIR: phrases.py's output (presets.json, mid/). WINDIR: a folder under /mnt/c holding the host and the bundle.
For every preset whose phrase kind is 'macro', this writes RENDER_DIR/wav/<slug>.wav (48 kHz float stereo, from the
score's start, latency removed: the same framing as render311) and RENDER_DIR/macro.json (the curves used).
Automation times given to the host are render seconds, so the harness's warmup is added to the score times here.
"""
import argparse, json, os, shutil, struct, subprocess, sys

WARMUP, SR = 8.0, 48000
STEPS = 'steps'   # a repeat-count macro (N): Windows rebuilds per value, so move it in steps, not a ramp

# by preset name: Macro 1 curve over the score's seconds (value 0..1)
CURVES = {
    'Bowl Morph': [(0, 0), (7.5, 1)],
    'Wide Glass': [(0, 0), (4, 1), (7.8, 0.1)],
    'Macro Swell': [(0, 0), (4, 1), (7.8, 0.2)],
    'Macro Layers': [(0, 0), (7.5, 1)],
    'Echo Count': STEPS, 'Macro Echoes': STEPS,
}


def winpath(p):
    return subprocess.run(['wslpath', '-w', p], capture_output=True, text=True).stdout.strip()


def curve_spec(c):
    if c == STEPS:   # 0, 25, 50, 75, 100 % held 2 s each (the phrase plays two chords per value)
        pts = []
        for k in range(5):
            t = k * 2.0
            if k: pts.append((t - 0.01, (k - 1) / 4))
            pts.append((t, k / 4))
        c = pts
    return 'Macro 1:' + ';'.join('%.3f=%.3f' % (t + WARMUP, v) for t, v in c), c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render'); ap.add_argument('windir')
    ap.add_argument('--plugin', default='Basilisk16.vst3'); ap.add_argument('--host', default='BasiliskHost.exe')
    a = ap.parse_args()
    rows = [r for r in json.load(open(os.path.join(a.render, 'presets.json'))) if r['kind'] == 'macro']
    done = {}
    for r in rows:
        if r['name'] not in CURVES: print('no curve for', r['name']); continue
        spec, pts = curve_spec(CURVES[r['name']])
        mid = os.path.join(a.windir, r['slug'] + '.mid')
        shutil.copy(os.path.join(a.render, 'mid', r['slug'] + '.mid'), mid)
        outd = os.path.join(a.windir, 'bh-' + r['slug'])
        cmd = [os.path.join(a.windir, a.host), '--test', winpath(os.path.join(a.windir, a.plugin)), '--tests', 'offline',
               '--program', str(r['i']), '--midi', winpath(mid), '--automate', spec, '--warmup', str(WARMUP),
               '--tail', '2.5', '--out-dir', winpath(outd)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        rep = json.load(open(os.path.join(outd, 'report.json')))
        off = rep['renders']['offline']
        lat = off['latency_samples']
        d = open(os.path.join(outd, 'offline.wav'), 'rb').read()
        i = d.find(b'data')
        x = d[i + 8:]
        start = (int(WARMUP * SR) + lat) * 8
        x = x[start:start + int(round(r['seconds'] * SR)) * 8]
        hdr = b'RIFF' + struct.pack('<I', 36 + len(x)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 3, 2, SR, SR * 8, 8, 32) + b'data' + struct.pack('<I', len(x))
        open(os.path.join(a.render, 'wav', r['slug'] + '.wav'), 'wb').write(hdr + x)
        done[r['slug']] = {'program': r['i'], 'automation': spec, 'curve': pts, 'heard': off['timing']['heard'],
                           'notes': off['timing']['notes'], 'peak_dbfs': off['level']['peak_dbfs'], 'render_s': off['render_s']}
        print('%-16s program %d  %d/%d notes heard  peak %s dBFS  %.1f s' % (r['slug'], r['i'], off['timing']['heard'],
              off['timing']['notes'], off['level']['peak_dbfs'], off['render_s']), flush=True)
    json.dump(done, open(os.path.join(a.render, 'macro.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

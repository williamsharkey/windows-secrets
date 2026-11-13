#!/usr/bin/env python3
"""Render BASILISK SYNTH (XP) demos with retries: XP 1.2.0's offline renders are intermittently silent.

    xp_render.py RENDER_DIR --host bsynth-host.exe --plugin BasiliskSynth.vst3 --work WINDIR [--parallel 4] [--tries 4]

RENDER_DIR is phrases.py's output for the XP program list. Each round renders the jobs still needing it through
packages/basilisk-synth/tools/batch_render.py (one plugin instance and one Windows XP per job), trims the warmup and
latency (xp_trim.py's framing), and checks the take: every distinct note onset must be heard (sound above -50 dBFS
within 0.3 s, 1 s for slow kinds). Jobs with silent onsets are rendered again, up to --tries in all; the take with
the most onsets heard is kept. RENDER_DIR/attempts.json records every take, so a preset that never sounds right is
reported as broken, not hidden. The same job can differ run to run (XP's timing is not sample-accurate).
"""
import argparse, json, os, shutil, struct, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH = os.path.join(HERE, '..', '..', 'packages', 'basilisk-synth', 'tools', 'batch_render.py')
SR = 48000


def note_ons(mid):
    d = open(mid, 'rb').read(); p = d.find(b'MTrk') + 8; t = 0; out = []; run = 0
    while p < len(d):
        v = 0
        while True:
            c = d[p]; p += 1; v = (v << 7) | (c & 0x7F)
            if not c & 0x80: break
        t += v; st = d[p]
        if st == 0xFF: p += 3 + d[p + 2]; continue
        if st & 0x80: p += 1; run = st
        else: st = run
        a, b = d[p], d[p + 1]; p += 2
        if st & 0xF0 == 0x90 and b: out.append(round(t / 960.0, 3))
    return sorted(set(out))


def take(src, row, warm, lat):
    d = open(src, 'rb').read(); i = d.find(b'data'); x = d[i + 8:]
    n = int(round(row['seconds'] * SR)) * 8; s = (int(round(warm * SR)) + lat) * 8
    x = x[s:s + n]; x += b'\0' * (n - len(x))
    return x


def heard(x, row, mid):
    a = np.frombuffer(x, '<f4').reshape(-1, 2).mean(1)
    win = 1.0 if row['kind'] in ('pad', 'drone', 'fx', 'collage') else 0.3
    ons = note_ons(mid); h = 0
    for t in ons:
        seg = a[int(t * SR):int((t + win) * SR)]
        if len(seg) and 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12) > -50: h += 1
    return h, len(ons), float(np.abs(a).max()) if len(a) else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render'); ap.add_argument('--host', required=True); ap.add_argument('--plugin', required=True)
    ap.add_argument('--work', required=True); ap.add_argument('--parallel', type=int, default=4); ap.add_argument('--tries', type=int, default=4)
    ap.add_argument('--warmup', type=float, default=1.0); ap.add_argument('--latency', type=int, default=4800)
    a = ap.parse_args()
    rows = {r['slug']: r for r in json.load(open(os.path.join(a.render, 'presets.json')))}
    jobs = {j['out'].split('/')[-1][:-4]: j for j in json.load(open(os.path.join(a.render, 'jobs.json')))}
    for j in jobs.values():
        if j.get('midi') and not os.path.isabs(j['midi']): j['midi'] = os.path.join(os.path.abspath(a.render), j['midi'])
    os.makedirs(os.path.join(a.render, 'wav'), exist_ok=True)
    best, attempts, logs = {}, {s: [] for s in jobs}, {}
    todo = list(jobs)
    for n in range(a.tries):
        if not todo: break
        out = os.path.join(a.work, 'round%d' % n)
        shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
        jf = os.path.join(out, 'jobs.json'); json.dump([jobs[s] for s in todo], open(jf, 'w'))
        subprocess.run([sys.executable, BATCH, jf, '--host', a.host, '--plugin', a.plugin, '--parallel', str(a.parallel),
                        '--out-dir', out, '--warmup', str(a.warmup)], check=False)
        res = {r['out'].split('/')[-1][:-4]: r for r in json.load(open(os.path.join(out, 'batch.json')))['results']}
        nxt = []
        for s in todo:
            f = os.path.join(out, 'wav', s + '.wav')
            if not os.path.exists(f): attempts[s].append({'round': n, 'ok': False}); nxt.append(s); continue
            x = take(f, rows[s], a.warmup, a.latency)
            h, tot, pk = heard(x, rows[s], jobs[s]['midi'])
            attempts[s].append({'round': n, 'heard': h, 'onsets': tot, 'peak': round(pk, 4)})
            if s not in best or h > best[s][0]: best[s] = (h, x); logs[s] = res.get(s, {})
            if h < tot: nxt.append(s)
        print('round %d: %d jobs, %d with silent onsets' % (n, len(todo), len(nxt)), flush=True)
        todo = nxt
    for s, (h, x) in best.items():
        hdr = b'RIFF' + struct.pack('<I', 36 + len(x)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 3, 2, SR, SR * 8, 8, 32) + b'data' + struct.pack('<I', len(x))
        open(os.path.join(a.render, 'wav', s + '.wav'), 'wb').write(hdr + x)
    json.dump({'results': [dict(logs.get(s, {}), out='wav/%s.wav' % s, log='') for s in best]}, open(os.path.join(a.render, 'batch.json'), 'w'))
    json.dump(attempts, open(os.path.join(a.render, 'attempts.json'), 'w'), indent=1)
    bad = [s for s in jobs if attempts[s] and all((t.get('heard', 0) < t.get('onsets', 1)) for t in attempts[s])]
    print('%d presets; %d needed more than one take; %d never had every onset heard: %s' % (
        len(jobs), sum(1 for s in jobs if len(attempts[s]) > 1), len(bad), ', '.join(bad)))


if __name__ == '__main__':
    main()

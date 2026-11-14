#!/usr/bin/env python3
"""audition: measure every preset of the pack discs through render311, for arranging.

    audition.py [--packs id,id] [--out ~/songs/audition] [--jobs 6]

Each preset plays C3, C4 and C5 (1.2 s each) and one soft C4. For every note: the pitch heard (YIN on the steady
part) against the note asked for, in cents and octaves; the level; and how much of it is still there at 1 s (a
sustaining voice against a decaying one). Kits and percussion get their pads' levels instead. One JSON per pack.
"""
import argparse, concurrent.futures as cf, json, math, os, re, subprocess, sys, tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import songrender as sr   # noqa: E402

NOTES = [(0.0, 48, 100, 1.2), (1.6, 60, 100, 1.2), (3.2, 72, 100, 1.2), (4.8, 60, 50, 0.6)]
KITPADS = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57]


def yin(x, fmin=40, fmax=2200, th=0.15):
    x = x - np.mean(x)
    W = len(x) // 2
    tmin, tmax = int(sr.SR / fmax), min(int(sr.SR / fmin), W - 1)
    a = x[:W]
    d = np.array([0.0] + [float(np.sum((a - x[t:t + W]) ** 2)) for t in range(1, tmax + 2)])
    cm = np.ones_like(d)
    cm[1:] = d[1:] * np.arange(1, len(d)) / np.maximum(np.cumsum(d[1:]), 1e-12)
    t = None
    for k in range(max(2, tmin), tmax):
        if cm[k] < th and cm[k] <= cm[k + 1]:
            t = k; break
    if t is None:
        t = int(np.argmin(cm[max(2, tmin):tmax])) + max(2, tmin)
    a_, b_, c_ = cm[t - 1], cm[t], cm[t + 1]
    den = a_ - 2 * b_ + c_
    p = t + (min(0.5, max(-0.5, 0.5 * (a_ - c_) / den)) if den else 0)
    return sr.SR / p, float(cm[t])


def analyse(wav, kit):
    x = sr.read_f32_wav(wav).astype(np.float64)
    m = x.mean(axis=1)
    res = {'peak_db': round(20 * math.log10(np.max(np.abs(x)) + 1e-12), 1)}
    if kit:
        pads = {}
        for i, n in enumerate(KITPADS):
            s = m[int(i * 0.3 * sr.SR):int((i * 0.3 + 0.28) * sr.SR)]
            pk = float(np.max(np.abs(s))) if len(s) else 0
            pads[n] = round(20 * math.log10(pk + 1e-9), 1)
        res['pads'] = pads
        return res
    notes = []
    for t, n, v, du in NOTES:
        a = int(t * sr.SR)
        seg = m[a:a + int(1.55 * sr.SR)]
        if len(seg) < sr.SR:
            seg = np.pad(seg, (0, sr.SR - len(seg)))
        env = np.sqrt(np.convolve(seg ** 2, np.ones(480) / 480, 'same'))
        pk = float(env.max()) + 1e-9
        at = int(np.argmax(env > pk * 0.5))
        r = {'note': n, 'vel': v, 'level_db': round(20 * math.log10(pk), 1), 'attack_ms': round(at / 48, 0),
             'at_1s_db': round(20 * math.log10(env[min(len(env) - 1, int(1.0 * sr.SR))] / pk + 1e-9), 1),
             'at_300ms_db': round(20 * math.log10(env[int(0.3 * sr.SR)] / pk + 1e-9), 1)}
        if v == 100:
            st = max(at + int(0.06 * sr.SR), int(0.08 * sr.SR))
            w = seg[st:st + 4096]
            f0, q = yin(w) if np.sqrt(np.mean(w ** 2)) > 1e-4 else (0, 1)
            if f0 > 20:
                exp = 440 * 2 ** ((n - 69) / 12)
                c = 1200 * math.log2(f0 / exp)
                octv = int(round(c / 1200))
                r.update({'f0': round(f0, 2), 'cents': round(c - 1200 * octv, 1), 'octave': octv, 'clarity': round(1 - q, 2)})
        notes.append(r)
    res['notes'] = notes
    return res


def job(render311, machine, dna, kit, tmpd):
    wav = os.path.join(tmpd, 'a.wav')
    sc = ','.join(f'{i * 0.3:.2f}:{n}:105:0.2' for i, n in enumerate(KITPADS)) if kit else \
        ','.join(f'{t}:{n}:{v}:{d}' for t, n, v, d in NOTES)
    r = subprocess.run(['nice', '-n', '10', render311, '--machine', machine, '--core', os.path.join(machine, 'dosbox_pure_libretro.so'),
                        '--dna', dna, '--score', sc, '--out', wav, '--tail', '1.5', '--bits', '32'],
                       capture_output=True, text=True, env=dict(os.environ, TMPDIR=tmpd))
    if r.returncode:
        return {'error': r.stderr[-300:]}
    try:
        return analyse(wav, kit)
    finally:
        os.remove(wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--packs', default='')
    ap.add_argument('--out', default=os.path.expanduser('~/songs/audition'))
    ap.add_argument('--render311', default=sr.DEF_RENDER311)
    ap.add_argument('--machine', default=sr.DEF_MACHINE)
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    root = os.path.join(a.machine, 'packs')
    want = set(filter(None, a.packs.split(',')))
    for l in open(os.path.join(root, 'PACKS.TSV')):
        f = l.rstrip('\n').split('\t')
        if len(f) < 2 or (want and f[1] not in want):
            continue
        d, pid = f[0], f[1]
        outp = os.path.join(a.out, pid + '.json')
        if os.path.exists(outp):
            continue
        rows = [r.rstrip('\n').split('\t') for r in open(os.path.join(root, d, 'PRESETS.TSV'), encoding='utf-8', errors='replace') if not r.startswith('#')]
        rows = [r for r in rows if len(r) >= 3]
        res = {}
        with tempfile.TemporaryDirectory(dir=a.out) as tmp, cf.ThreadPoolExecutor(min(6, a.jobs)) as ex:
            fut = {}
            for i, r in enumerate(rows):
                cat, name, dna = r[0], r[1], r[2]
                kit = cat in ('Kit', 'Genre', 'Electromech', 'Machine') or bool(re.search(r';.*k\d+[jl,ki]', dna))
                td = os.path.join(tmp, str(i)); os.makedirs(td)
                fut[ex.submit(job, a.render311, a.machine, dna, kit, td)] = (cat, name, dna, kit)
            for fu in cf.as_completed(fut):
                cat, name, dna, kit = fut[fu]
                res[name] = dict(category=cat, dna=dna, kit=kit, **fu.result())
        json.dump(res, open(outp, 'w'), indent=1)
        print(pid, len(res), flush=True)


if __name__ == '__main__':
    main()

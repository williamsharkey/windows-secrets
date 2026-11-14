#!/usr/bin/env python3
"""Render each Rainy Loft preset through render311 and measure it: level, pitch against the note asked, clipping,
silence. For kits, each pad; for textures, the level over 8 s.

    check_presets.py [--names "Loft Tine,Harbour Reed"] [--machine ~/cpd/machine] [--render311 ~/cpd/bin/render311]
                     [--jobs 4] [--out ~/cpd/check]
"""
import argparse, concurrent.futures as cf, json, math, os, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'sounds'))
import dsp   # noqa: E402

RANGES = {'Keys': (36, 96), 'Bass': (28, 55), 'Lead': (55, 86), 'Bell': (60, 96), 'Pluck': (40, 76), 'Vocal': (48, 76),
          'Pad': (48, 76), 'FX': (60, 60), 'Texture': (60, 60)}
KIT = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 62, 63, 64]


def read(path):
    with wave.open(path) as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        b = w.readframes(n)
    if sw == 4:
        x = np.frombuffer(b, '<i4').astype(np.float64) / 2 ** 31
    elif sw == 3:
        a = np.frombuffer(b, np.uint8).reshape(-1, 3)
        x = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int8).astype(np.int32) << 16)) / 2 ** 23
    else:
        x = np.frombuffer(b, '<i2').astype(np.float64) / 32768
    return x.reshape(-1, ch), sr


def score(cat):
    if cat == 'Kit':
        return [(i * 1.0, n, 100, 0.5) for i, n in enumerate(KIT)], 1.0
    lo, hi = RANGES.get(cat, (48, 84))
    if lo == hi:
        return [(0.0, 60, 100, 8.0)], 9.0
    ns = list(range(lo, hi + 1, 6))
    sc = [(i * 1.6, n, 100, 1.2) for i, n in enumerate(ns)]
    sc.append((len(ns) * 1.6, (lo + hi) // 2, 45, 1.2))
    return sc, 1.6


def chroma_off(seg, sr, n):
    """the strongest pitch class of the note (spectral peaks folded to 12 classes, 60 Hz..5 kHz), in semitones
    from the note asked (0 = in key; robust for ensembles, bells and vibrato)"""
    seg = seg[:int(0.6 * sr)] * np.hanning(min(len(seg), int(0.6 * sr)))
    sp = np.abs(np.fft.rfft(seg, 1 << 16)); fr = np.fft.rfftfreq(1 << 16, 1 / sr)
    ok = (fr > 60) & (fr < 5000)
    sp, fr = sp[ok], fr[ok]
    ch = np.zeros(12)
    m = 69 + 12 * np.log2(fr / 440)
    np.add.at(ch, np.round(m).astype(int) % 12, sp ** 2)
    k = (int(np.argmax(ch)) - n) % 12
    return k if k <= 6 else k - 12


def run(job):
    name, cat, dna, a = job
    sc, step = score(cat)
    out = os.path.join(a.out, name.replace(' ', '_') + '.wav')
    s = ','.join(f'{t:.3f}:{n}:{v}:{d:.3f}' for t, n, v, d in sc)
    r = subprocess.run(['nice', '-n', '10', a.render311, '--machine', a.machine, '--core',
                        os.path.join(a.machine, 'dosbox_pure_libretro.so'), '--dna', dna, '--score', s,
                        '--out', out, '--tail', '2'], capture_output=True, text=True)
    if r.returncode:
        return name, {'error': r.stderr[-300:]}
    x, sr = read(out)
    m = x.mean(axis=1)
    res = {'cat': cat, 'peak_db': round(20 * math.log10(np.max(np.abs(x)) + 1e-12), 1), 'notes': []}
    for t, n, v, d in sc:
        a0 = int((t + 0.03) * sr); a1 = int((t + min(d, step) - 0.05) * sr)
        seg = m[a0:a1]
        lev = 20 * math.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)
        e = {'note': n, 'vel': v, 'db': round(lev, 1)}
        if cat not in ('Kit', 'FX', 'Texture') and lev > -55:
            e['pc'] = chroma_off(seg, sr, n)
            try:
                seg48 = seg if sr == 48000 else seg
                f = dsp.f0(seg48, 25, 2500, 0.05, 0.4)
                c = 1200 * math.log2(f / (440 * 2 ** ((n - 69) / 12)))
                oc = round(c / 1200)
                e['cents'] = round(c - 1200 * oc); e['oct'] = oc
            except Exception:
                pass
        res['notes'].append(e)
    os.remove(out)
    return name, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--names', default='')
    ap.add_argument('--machine', default=os.path.expanduser('~/cpd/machine'))
    ap.add_argument('--render311', default=os.path.expanduser('~/cpd/bin/render311'))
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--out', default=os.path.expanduser('~/cpd/check'))
    ap.add_argument('--tsv', default=os.path.join(HERE, '..', 'pack', 'presets.tsv'))
    ap.add_argument('--dna', default='', help='NAME=CAT=DNA, to try a DNA that is not in the TSV yet')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    want = set(x.strip() for x in a.names.split(',') if x.strip())
    jobs = []
    for l in open(a.tsv, encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        c, n, d = l.rstrip('\n').split('\t')[:3]
        if not want or n in want:
            jobs.append((n, c, d, a))
    if a.dna:
        n, c, d = a.dna.split('=', 2); jobs = [(n, c, d, a)]
    res = {}
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for name, r in ex.map(run, jobs):
            res[name] = r
            if 'error' in r:
                print(f'{name:24s} ERROR {r["error"]}'); continue
            ns = r['notes']
            lv = ' '.join(f'{e["note"]}:{e["db"]:.0f}' + (f'[{e["pc"]:+d}]' if e.get('pc') else '') for e in ns)
            quiet = [e['note'] for e in ns if e['db'] < -50]
            print(f'{name:24s} peak {r["peak_db"]:6.1f}  {lv}' + (f'  SILENT {quiet}' if quiet else ''))
    json.dump(res, open(os.path.join(a.out, 'check.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

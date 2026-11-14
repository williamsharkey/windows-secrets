#!/usr/bin/env python3
"""The 3.11 re-check on a release build, and the Sound Pack Explorer's preview clips, in one pass.

    LIBBUILD_V3=<pinned build> recheck.py [--libs library.json library-p2.json ...] [--parallel 4] [--out ~/libbuild/previews]

For every preset: (1) its probe is rendered through render311 and checked again exactly as when it was made
(score.check: silence, notes heard, DC, tuning and key tracking, fit); (2) a short preview is rendered: about 4 s of
its kind's figure (one bar for kits), levelled to -16 LUFS (a -1 dBFS limiter only if needed), faded, and encoded mono
as MP3 (48 kHz, 48 kbps) and Opus (.ogg, 24 kbps). Results go into each library json as `check311` (build, ok, why, score);
the clips go to OUT/<slug>.{mp3,ogg} with OUT/manifest.json (slug, pack, category, name, canonical DNA, recipe one
line and lines, seconds, peak and LUFS of the clip, ok and flags of the re-check, the owner's rating, the build).
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, save_json, RENDER311, MACHINE
from catdefs import CATS
import phrases, render, score
from audio import ebur128, read_wav


def preview_score(kind, dna):
    """about 4 s of a figure that shows the preset's job"""
    if kind == 'kit':
        pads = set(phrases.kit_pads(dna))
        g = [n for n in phrases.kit_groove() if n[0] < 2.4 and n[1] in pads]
        if len(g) < 6: g += [(round(0.15 * i, 3), n, 100, 0.12) for i, n in enumerate(sorted(pads)[:16])]
        return sorted(set(g)), 1.2
    if kind in ('pad', 'drone'):
        return [(0.0, 48, 90, 3.0), (0.0, 55, 84, 3.0), (0.0, 60, 80, 3.0), (0.0, 64, 76, 3.0)], 1.0
    if kind == 'bass':
        line = [36, 36, 48, 36, 43, 43, 46, 41]
        return [(round(i * 0.4, 3), n, 108 if i % 2 == 0 else 92, 0.34) for i, n in enumerate(line)], 0.8
    if kind == 'lead':
        seq = [(0.0, 69, 0.45), (0.5, 72, 0.45), (1.0, 74, 0.9), (2.0, 76, 0.45), (2.5, 74, 1.0)]
        return [(t, n, 100, d) for t, n, d in seq], 0.8
    if kind in ('bell', 'pluck'):
        seq = [72, 76, 79, 84, 79, 76, 74, 72] if kind == 'bell' else [60, 64, 67, 72, 67, 64, 60, 67]
        step = 0.45 if kind == 'bell' else 0.3
        return [(round(i * step, 3), n, 100 - (i % 3) * 8, step * 0.9) for i, n in enumerate(seq)], 1.0
    if kind == 'fx':
        return [(0.0, 60, 100, 3.0)], 1.0
    if kind == 'perc':
        hits = [(0, 60), (1, 60), (2, 48), (3, 60), (4, 72), (5, 60), (6, 48), (7, 64)]
        return [(i * 0.3, n, 105, 0.12) for i, n in hits], 0.8
    # keys: a chord, then a short melody over it
    return [(0.0, 48, 80, 1.5), (0.0, 55, 76, 1.5), (0.0, 64, 76, 1.5), (1.6, 45, 76, 1.5), (1.6, 52, 72, 1.5),
            (1.6, 60, 72, 1.5), (0.4, 72, 92, 0.35), (0.8, 74, 88, 0.35), (1.2, 76, 92, 0.6), (2.0, 74, 88, 0.35),
            (2.4, 72, 92, 0.8)], 0.8


import numpy as np


def encode(wav, out_base, lufs_target=-16.0):
    I = ebur128(wav)
    x, _ = read_wav(wav)
    pk = float(20 * np.log10(np.abs(x).max() + 1e-12))
    g = (lufs_target - I) if I is not None and I > -70 else 0.0
    af = 'volume=%.2fdB' % g
    if pk + g > -1: af += ',alimiter=limit=0.891:attack=1:release=60:level=disabled'
    dur = len(x) / 48000
    af += ',afade=t=out:st=%.3f:d=0.2' % max(0, dur - 0.2)
    os.makedirs(os.path.dirname(out_base), exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', wav, '-af', af, '-ac', '1', '-ar', '48000', '-c:a', 'libopus', '-b:a', '24k',
                    '-vbr', 'on', '-application', 'audio', '-map_metadata', '-1', out_base + '.ogg'], check=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', wav, '-af', af, '-ac', '1', '-ar', '48000', '-c:a', 'libmp3lame', '-b:a', '48k',
                    '-map_metadata', '-1', '-write_xing', '1', out_base + '.mp3'], check=True)
    I2 = ebur128(out_base + '.mp3')
    y, _ = read_wav(subprocess.run(['ffmpeg', '-v', 'error', '-i', out_base + '.mp3', '-f', 'wav', '-'], capture_output=True).stdout)
    return I2, round(dur, 2), round(float(20 * np.log10(np.abs(y).max() + 1e-12)), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--libs', nargs='+', default=['library.json'])
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--out', default=os.path.expanduser('~/libbuild/previews'))
    ap.add_argument('--build', default=os.environ.get('SNDWAVE_BUILD', '?'))
    ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args()
    libs = {f: load_json(f) for f in a.libs}
    from make_discs import ratings
    ratings_by_slug = ratings()
    allp = [(f, p) for f, L in libs.items() for p in L]
    # 1. the probes, checked again
    jobs = []
    for f, p in allp:
        k = CATS[p['scat']]['kind']
        s, tail, singles = phrases.probe(k, p['dna_final'])
        jobs.append(dict(dna=p['dna_final'], score=s, tail=tail, kind=k, singles=singles))
    res = render.render_all(jobs, a.parallel, progress=True)
    nok = 0
    for (f, p), r in zip(allp, res):
        ok, sc, why, info = score.check(r, p['scat'], CATS[p['scat']]['kind'])
        p['check311'] = {'build': a.build, 'ok': ok, 'why': why, 'score': sc}
        nok += ok
    print('re-check: %d/%d pass' % (nok, len(allp)), flush=True)
    if a.check_only:
        for f, L in libs.items(): save_json(f, L)
        return
    # 2. the previews
    jobs = []
    for f, p in allp:
        k = CATS[p['scat']]['kind']
        s, tail = preview_score(k, p['dna_final'])
        jobs.append(dict(dna=p['dna_final'], score=s, tail=tail, kind=k, keep=True))
    res = render.render_all(jobs, a.parallel, progress=True)
    index = []
    for (f, p), j, r in zip(allp, jobs, res):
        wav = render.wav_path(j['dna'], j['score'], j['tail'])
        if not r.get('ok') or not os.path.exists(wav): continue
        base = os.path.join(a.out, p['slug'])
        I, dur, pk = encode(wav, base)
        os.remove(wav)
        rat = ratings_by_slug.get(p['slug'], {})
        index.append({'slug': p['slug'], 'pack': p['pack'], 'pack_name': p['pack_name'], 'category': p['category'], 'name': p['name'],
                      'dna': p.get('canonical') or p['dna_final'], 'recipe_one': p.get('recipe_one'), 'recipe': p.get('recipe'),
                      'mp3': p['slug'] + '.mp3', 'ogg': p['slug'] + '.ogg', 'seconds': dur, 'peak_dbfs': pk, 'lufs': I,
                      'ok': p['check311']['ok'], 'flags': p['check311']['why'], 'rating': rat.get('rating'), 'verdict': rat.get('verdict'),
                      'edition': p['edition'], 'v3': p['v3'], 'tags': p.get('tags', [])})
    json.dump({'build': a.build, 'renderer': 'render311 (%s)' % a.build, 'lufs_target': -16, 'mp3': '48 kHz mono 48 kbps',
               'ogg': 'Opus mono 24 kbps', 'fade_s': 0.2, 'presets': index}, open(os.path.join(a.out, 'manifest.json'), 'w'), indent=1)
    for f, L in libs.items(): save_json(f, L)
    tot = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fs in os.walk(a.out) for fn in fs)
    print('previews: %d clips, %.1f MB -> %s' % (len(index), tot / 1e6, a.out))


if __name__ == '__main__':
    main()

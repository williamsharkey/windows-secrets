#!/usr/bin/env python3
"""Finalize the selection: set the G gene, render each preset's demo phrase through the real machine, check it
again, re-render when G moved, encode an MP3 for listening, and attach the recipe.

    finalize.py [--parallel 7] [--target -18] [--mp3-dir DIR]     data/selection.json -> data/library.json

Level rule (pack-plan 6.5): phrase loudness about TARGET (gated, dB), peaks between -6 and -1 dBFS; G is the only
change. Checks on the phrase: every note onset heard, no card clipping, no DC, not silent, ends inside the tail.
"""
import argparse, json, math, os, re, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DNA, WORK, MACHINE, RECIPE_CLI, load_json, save_json
import phrases, render, score
from audio import read_wav, ebur128

MP3 = os.path.join(WORK, 'mp3')


def with_gain(dna, g):
    d = DNA.parse(dna)
    if g: d.glob['G'] = g
    else: d.glob.pop('G', None)
    return d.text()


def mono_phrase(dna):
    d = DNA.parse(dna)
    return any(len(L.genes.get('H', [0])) >= 3 for L in d.layers)


def job(p, dna):
    notes, tail, label = phrases.phrase(p['kind'], mono=mono_phrase(dna))
    j = dict(dna=dna, score=notes, tail=tail, kind=p['kind'], keep=True)
    from evolve import needs_bpm, BPM
    if needs_bpm(dna): j['bpm'] = BPM.get(p['pack'], 120); p['bpm'] = j['bpm']
    return j, label


def measure(path, r, dna):
    I = ebur128(path)
    x, _ = read_wav(path)
    pk = float(20 * np.log10(np.abs(x).max() + 1e-12))
    return I, pk


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def encode(wav, mp3):
    x, _ = read_wav(wav)
    mono = x.shape[1] == 1 or float(np.abs(x[:, 0] - x[:, 1]).max()) < 1e-6
    dur = len(x) / 48000
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', wav, '-af', 'afade=t=out:st=%.3f:d=0.3' % max(0, dur - 0.3),
                    '-ac', '1' if mono else '2', '-c:a', 'libmp3lame', '-b:a', '96k', '-map_metadata', '-1', mp3], check=True)
    env = np.abs(x.mean(axis=1)); n = max(1, len(env) // 48)
    return [round(float(min(1, env[k * n:(k + 1) * n].max())), 3) for k in range(48)], mono


def add_recipes(keep):
    names = os.path.join(MACHINE, 'library.names.txt')
    out = subprocess.run([RECIPE_CLI, names], input='\n'.join(p['dna_final'] for p in keep) + '\n', capture_output=True, text=True).stdout
    rec = [json.loads(l) for l in out.splitlines() if l.strip()]
    assert len(rec) == len(keep)
    for p, r in zip(keep, rec):
        assert r['dna'] == p['dna_final']
        p['recipe'] = r['plines']; p['recipe_one'] = r['pone']; p['canonical'] = r['canonical']; p['recipe_ok'] = r['ok']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parallel', type=int, default=7)
    ap.add_argument('--target', type=float, default=-18.0)
    ap.add_argument('--sel', default='selection.json'); ap.add_argument('--out', default='library.json')
    ap.add_argument('--shard', default='0/1'); ap.add_argument('--merge', nargs='*')
    a = ap.parse_args()
    os.makedirs(MP3, exist_ok=True)
    if a.merge is not None:
        keep = []
        for f in a.merge: keep += load_json(f)
        add_recipes(keep)
        save_json(a.out, keep)
        print('merged', len(keep)); return
    sel = load_json(a.sel)
    si, sn = (int(x) for x in a.shard.split('/'))
    sel = [p for i, p in enumerate(sel) if i % sn == si]
    t0 = time.time()
    # G from the probe render's loudness
    for p in sel:
        g0 = int(DNA.parse(p['dna']).glob.get('G', 0))
        p['G'] = score.gain_for(p['info'].get('loud'), p['info'].get('peak_db'), g0, a.target)
        p['dna_final'] = with_gain(p['dna'], p['G'])
    for attempt in range(3):
        todo = [p for p in sel if not p.get('final_ok') and not p.get('dropped')]
        if not todo: break
        jobs = []
        for p in todo:
            j, label = job(p, p['dna_final']); p['phrase'] = label; jobs.append(j)
        res = render.render_all(jobs, a.parallel, progress=True)
        for p, j, r in zip(todo, jobs, res):
            wav = render.wav_path(j['dna'], j['score'], j['tail'], j.get('bpm'))
            why = []
            if not r.get('ok'): why.append('phrase render failed')
            else:
                if r['peak_db'] < -45: why.append('silent')
                if r['heard'] < r['onsets']: why.append('%d of %d onsets not heard' % (r['onsets'] - r['heard'], r['onsets']))
                if r['dc'] > 0.08: why.append('DC')
                if r['end_rel_db'] > -14: why.append('still sounding at the end')
                if r.get('late'): p['late'] = r['late']
            if why:
                p['dropped'] = why; p['final_ok'] = False
                if os.path.exists(wav): os.remove(wav)
                continue
            I, pk = measure(wav, r, j['dna'])
            g = p['G']
            gn = g + (a.target - I) if I is not None else g
            gn = min(gn, g + (-1.0 - pk))                 # peaks at or under -1 dBFS
            if pk + (gn - g) < -6.0: gn = min(g + (-6.0 - pk), g + (-1.0 - pk))   # and not under -6
            gn = int(max(-60, min(24, math.floor(gn))))
            p['phrase_lufs'], p['phrase_peak'] = I, round(pk, 2)
            if abs(gn - g) >= 2 and attempt < 2:
                p['G'] = gn; p['dna_final'] = with_gain(p['dna'], gn)
                os.remove(wav)
                continue
            p['final_ok'] = True
            p['slug'] = slug(p['pack'] + '-' + p['name'])
            p['wave'], p['mono'] = encode(wav, os.path.join(MP3, p['slug'] + '.mp3'))
            p['phrase_seconds'] = r['seconds']
            os.remove(wav)
        print('attempt %d: %d ok, %d dropped, %.0f s' % (attempt, sum(bool(p.get('final_ok')) for p in sel),
              sum(bool(p.get('dropped')) for p in sel), time.time() - t0), flush=True)
    keep = [p for p in sel if p.get('final_ok')]
    if os.path.exists(RECIPE_CLI): add_recipes(keep)
    save_json(a.out, keep)
    save_json(a.out.replace('.json', '-dropped.json'), [p for p in sel if p.get('dropped')])
    print('final: %d kept, %d dropped; renders %s; %.0f s' % (len(keep), len(sel) - len(keep), render.STATS, time.time() - t0))


if __name__ == '__main__':
    main()

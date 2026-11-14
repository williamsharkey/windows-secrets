#!/usr/bin/env python3
"""The owner's octave decision (2026-11-14): presets whose first layer is a sound named in the C3 = middle C
convention (sources.json octave_from_measure) played an octave above the written note. Fix them so they play at
the written pitch, except the ones the owner rated or kept (builder/ratings), which stay exactly as heard.

    octave_fix.py [--dry]        data/library.json (dna_final, canonical) -> the same, plus octave_fix records

The fix: K + 12 (pitch = 2^((note - K)/12) at the sample's own rate, so a higher K plays lower). Other key-tracked
layers whose own sounds are named correctly get T + 12, so they stay where they were heard; layers that are
themselves octave-misnamed come down with the first one.
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DNA, load_json, save_json, RECIPE_CLI, MACHINE
from make_discs import ratings


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    S = load_json('sources.json'); L = load_json('library.json'); R = ratings()
    bad = {n for n, r in S.items() if r.get('octave_from_measure')}
    fixed, kept = [], []
    # packs built after the octave correction in analyze_sources already have the right K
    AFTER = {'tape-parlour', 'courtyard-chapel', 'listening-post', 'office-machinery', 'polysynth-showroom'}
    for p in L:
        if p['pack'] in AFTER or p.get('octave_fix'): continue
        d = DNA.parse(p['dna_final'])
        if not d.layers or d.pads: continue
        L0 = d.layers[0]
        if L0.src not in bad or L0.genes.get('F'): continue
        r = R.get(p['slug'], {})
        if r.get('verdict') == 'keep' or (r.get('rating') is not None and r['rating'] != 5):
            kept.append((p['pack'], p['name'], r.get('rating'), r.get('verdict'))); continue
        d.glob['K'] = min(127, d.glob.get('K', 60) + 12)
        for M in d.layers[1:]:
            if M.genes.get('F') or M.src in bad: continue
            M.genes['T'] = max(-48, min(48, M.genes.get('T', 0) + 12))
        p['octave_fix'] = {'from': p['dna_final'], 'reason': 'first layer %s is named an octave low (C3 = middle C)' % L0.src}
        p['dna_final'] = d.text()
        fixed.append(p)
    if fixed and not a.dry:
        out = subprocess.run([RECIPE_CLI, os.path.join(MACHINE, 'library.names.txt')], input='\n'.join(p['dna_final'] for p in fixed) + '\n',
                             capture_output=True, text=True).stdout.splitlines()
        for p, l in zip(fixed, out):
            r = json.loads(l); assert r['ok'], p['name']
            p['canonical'] = r['canonical']; p['recipe'] = r['plines']; p['recipe_one'] = r['pone']; p['recipe_ok'] = r['ok']
            p['dna_final'] = r['canonical']
        save_json('library.json', L)
    report = {'fixed': [(p['pack'], p['name']) for p in fixed], 'kept_as_rated': kept}
    save_json('octave-fix.json', report)
    print('fixed %d, kept as rated %d' % (len(fixed), len(kept)))


if __name__ == '__main__':
    main()

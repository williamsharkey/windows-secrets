#!/usr/bin/env python3
"""Mark each preset album.json credits by where a listener can find it: "shipped" (on SNDWAVE2000's released pack
discs with this exact DNA), "rainy-loft" (the album's own pack, coming in 1.4) or "album" (an album-only DNA: a
pack-disc preset as it was on the 1.3.0 release-candidate discs, or a DNA written for the album).

    annotate_presets.py SITE/album.json [--shipped ~/bs311/machine131] [--ours ~/cpd/machine]
"""
import argparse, json, os


def presets(root):
    P = {}
    for l in open(os.path.join(root, 'packs', 'PACKS.TSV'), encoding='cp1252').read().splitlines():
        f = l.split('\t')
        if len(f) < 2:
            continue
        tsv = os.path.join(root, 'packs', f[0], 'PRESETS.TSV')
        if os.path.exists(tsv):
            for r in open(tsv, encoding='cp1252', errors='replace'):
                g = r.rstrip('\r\n').split('\t')
                if len(g) >= 3 and not r.startswith('#'):
                    P[(f[1], g[1])] = g[2]
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('album')
    ap.add_argument('--shipped', default=os.path.expanduser('~/bs311/machine131'))
    ap.add_argument('--ours', default=os.path.expanduser('~/cpd/machine'))
    a = ap.parse_args()
    S, O = presets(a.shipped), presets(a.ours)
    d = json.load(open(a.album))
    n = {'shipped': 0, 'rainy-loft': 0, 'album': 0}
    for t in d['tracks']:
        for p in t.get('presets', []):
            lab = p.get('preset') or ''
            if lab.startswith('dna:') or ':' not in lab:
                p['where'] = 'album'
            else:
                pk, name = lab.split(':', 1)
                if pk == 'rainy-loft':
                    p['where'] = 'rainy-loft'
                elif S.get((pk, name)) is not None and S.get((pk, name)) == O.get((pk, name)):
                    p['where'] = 'shipped'
                else:
                    p['where'] = 'album'
                    p['after'] = f'{pk}: {name} (1.3.0 RC discs)'
            n[p['where']] += 1
    json.dump(d, open(a.album, 'w'), indent=1, ensure_ascii=False)
    print(n)


if __name__ == '__main__':
    main()

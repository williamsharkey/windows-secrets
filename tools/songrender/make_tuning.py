#!/usr/bin/env python3
"""make_tuning: the preset tuning table the song scripts apply (packages/basilisk-synth/library/songs/tuning.json).

    make_tuning.py [--audition ~/songs/audition] [--out .../songs/tuning.json] [--machine M --dna-out tuning-dna.json]

From audition.py's measurements: a preset gets a correction only when its notes are clear (YIN clarity > 0.85),
agree with each other (spread under 20 cents over at least two notes), and sit 10 to 90 cents off the note asked
(further off, or near a fourth or fifth, is a harmonic read, not a detuned sample). The value is the cents to add (a sharp preset gets a negative value).
--dna-out writes the same values keyed by FNV-1a 64 (hex, offset basis 0xcbf29ce484222325) of the exact DNA text.
"""
import argparse, json, os, statistics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audition', default=os.path.expanduser('~/songs/audition'))
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--out', default=os.path.join(here, '..', '..', 'packages', 'basilisk-synth', 'library', 'songs', 'tuning.json'))
    ap.add_argument('--machine', default=None, help='with --dna-out: the machine whose pack discs give each preset its DNA')
    ap.add_argument('--dna-out', default=None, help='also write the table keyed by FNV-1a 64 of the exact DNA text (for the plugin)')
    a = ap.parse_args()
    out = {}
    for f in sorted(os.listdir(a.audition)):
        if not f.endswith('.json'):
            continue
        pk = f[:-5]
        for name, r in json.load(open(os.path.join(a.audition, f))).items():
            ns = [n for n in r.get('notes', []) if 'cents' in n and n.get('clarity', 0) > 0.85 and n['level_db'] > -45]
            if len(ns) < 2:
                continue
            cs = [n['cents'] for n in ns]
            c = statistics.median(cs)
            if max(cs) - min(cs) < 20 and 10 <= abs(c) <= 90:
                out[f'{pk}:{name}'] = round(-c)
    json.dump(dict(sorted(out.items())), open(a.out, 'w'), indent=0)
    print(len(out), 'presets get a correction ->', os.path.abspath(a.out))
    if a.dna_out:
        import songrender as sr
        P = sr.presets(a.machine or sr.DEF_MACHINE)
        d = {}
        for k, c in out.items():
            pk, name = k.split(':', 1)
            dna = P.get(pk, {}).get(name)
            if dna:
                d['%016x' % fnv1a64(dna.encode('utf-8'))] = {'cents': c, 'pack': pk, 'name': name}
        json.dump(dict(sorted(d.items())), open(a.dna_out, 'w'), indent=0)
        print(len(d), 'by DNA ->', os.path.abspath(a.dna_out))


def fnv1a64(b):
    h = 0xcbf29ce484222325
    for x in b:
        h = ((h ^ x) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


if __name__ == '__main__':
    main()

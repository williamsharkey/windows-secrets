#!/usr/bin/env python3
"""make_tuning: the preset tuning table the song scripts apply (packages/basilisk-synth/library/songs/tuning.json).

    make_tuning.py [--audition ~/songs/audition] [--out .../songs/tuning.json]

From audition.py's measurements: a preset gets a correction only when its notes are clear (YIN clarity > 0.85),
agree with each other (spread under 20 cents over at least two notes), and sit 10 to 90 cents off the note asked
(further off, or near a fourth or fifth, is a harmonic read, not a detuned sample). The value is the cents to add.
"""
import argparse, json, os, statistics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audition', default=os.path.expanduser('~/songs/audition'))
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--out', default=os.path.join(here, '..', '..', 'packages', 'basilisk-synth', 'library', 'songs', 'tuning.json'))
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


if __name__ == '__main__':
    main()

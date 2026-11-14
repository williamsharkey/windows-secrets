#!/usr/bin/env python3
"""songcheck: each song's tracks against the preset audition (audition.py).

    songcheck.py SONG.song [...] [--audition ~/songs/audition] [--fix]

For each pitched track: the cents and octave the preset is heard at (median over its clear notes), the tune= the
song sets, and the track's note range. --fix writes tune= into the song's generating script's track table when the
preset is more than 12 cents off and the song sets nothing (scripts keep the source of truth).
"""
import argparse, json, os, re, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import songrender as sr   # noqa: E402
from smf import Smf   # noqa: E402


def heard(a):
    ns = [n for n in a.get('notes', []) if 'cents' in n and n.get('clarity', 0) > 0.8 and n['level_db'] > -50]
    if not ns:
        return None
    c = statistics.median(n['cents'] for n in ns)
    o = statistics.median(n['octave'] for n in ns)
    spread = max(n['cents'] for n in ns) - min(n['cents'] for n in ns)
    return round(c, 1), int(o), round(spread, 1), len(ns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('songs', nargs='+')
    ap.add_argument('--audition', default=os.path.expanduser('~/songs/audition'))
    ap.add_argument('--machine', default=sr.DEF_MACHINE)
    a = ap.parse_args()
    for p in a.songs:
        s = sr.Song(p)
        smf = Smf.read(s.midi_path)
        print(f'== {s.slug} ({s.meta["pack"]})')
        for t in s.tracks:
            dna, label = sr.resolve(s, t, a.machine)
            pk, name = (label.split(':', 1) + [''])[:2] if ':' in label else (s.meta['pack'], t.preset)
            aud = {}
            f = os.path.join(a.audition, pk + '.json')
            if os.path.exists(f):
                aud = json.load(open(f)).get(name, {})
            ex = smf.extract(s.selector(t), t.tr)
            notes = [e[1] for _, e in ex.tracks[0] if e[0] & 0xF0 == 0x90 and e[2] > 0]
            rng = f'{min(notes)}-{max(notes)}' if notes else '-'
            if aud.get('kit'):
                quiet = [n for n in sorted(set(notes)) if aud['pads'].get(str(n), -99) < -45]
                print(f'   {t.name:12s} kit  notes {rng:8s} silent pads used: {quiet}')
                continue
            h = heard(aud) if aud else None
            lv = [n['level_db'] for n in aud.get('notes', [])[:3]]
            flag = ''
            if h:
                c, o, spread, n = h
                if abs(c + t.tune) > 15:
                    flag += f' DETUNED({c + t.tune:+.0f}c)'
                if o != 0:
                    flag += f' OCTAVE{o:+d}'
            print(f'   {t.name:12s} heard {str(h):24s} tune={t.tune:+.0f} notes {rng:8s} levels {lv}{flag}')


if __name__ == '__main__':
    main()

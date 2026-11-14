#!/usr/bin/env python3
"""Merge finalized new packs (finalize.py outputs) into data/library.json; they ship to the 3.11 synth only.

    merge_new.py library-p2.json library-tape.json
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, save_json

L = load_json('library.json')
have = {p['slug'] for p in L}
packs = set()
for f in sys.argv[1:]:
    N = load_json(f)
    for p in N:
        p['ships'] = ['3.11']            # XP development has ended; these packs' own sounds are not on XP's disc
        packs.add(p['pack'])
    L = [p for p in L if p['pack'] not in {q['pack'] for q in N}] + N
save_json('library.json', L)
print(len(L), 'presets; replaced or added packs:', sorted(packs))

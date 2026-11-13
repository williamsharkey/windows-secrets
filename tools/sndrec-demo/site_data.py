#!/usr/bin/env python3
"""site_data.py OUT.json EDITION=RENDER_DIR [...]: merge encode.py's manifest.json files into the page's preset list."""
import json, sys

PLUGIN = {'b16': 'BASILISK 16', 'xp': 'BASILISK SYNTH'}


def pack(ed, cat):
    if ed == 'b16':
        if cat == 'BASILISK 16': return '3.11 originals'
        if cat.startswith('B16 '): return 'Library disc'
    if cat == 'Library': return 'Library disc'
    return 'Factory'


out = {'editions': {}}
for arg in sys.argv[2:]:
    ed, d = arg.split('=', 1)
    rows = json.load(open(d + '/manifest.json'))
    out['editions'][ed] = {'plugin': PLUGIN.get(ed, ed), 'presets': [{
        'n': r['i'], 'cat': r['cat'].replace('B16 ', '') if r['cat'] != 'BASILISK 16' else 'Classic', 'program': r['cat'] + ': ' + r['name'],
        'pack': pack(ed, r['cat']), 'name': r['name'], 'dna': r['dna'], 'phrase': r['phrase'],
        'file': ('sndrec/audio/%s/%s' % (ed, r['file'])) if r['file'] else None, 'sec': r['render_seconds'],
        'wave': [round(x * 100) for x in r['wave']], 'flags': [f for f in r['flags'] if not f.startswith('hot')],
        'hot': next((f for f in r['flags'] if f.startswith('hot')), None), 'note': r.get('note'),
        'macro': r.get('macro_curve') is not None} for r in rows]}
json.dump(out, open(sys.argv[1], 'w'), separators=(',', ':'))
print(sys.argv[1], sum(len(e['presets']) for e in out['editions'].values()), 'presets')

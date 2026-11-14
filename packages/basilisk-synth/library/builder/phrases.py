"""Scores for the builder.

probe(kind): a short screening score of isolated notes (for pitch, key tracking, envelope and brightness) plus,
for polyphonic kinds, one chord (for summing and voice pools). Each returns (score, tail, singles) where singles
are the indices of the isolated notes the analysis measures.

phrase(kind): the musical demo phrase, from tools/sndrec-demo/phrases.py (the sndrec.html demos' generator),
used for the final render that is checked again and encoded for listening.
"""
import importlib.util, os
from common import REPO

_spec = importlib.util.spec_from_file_location('demo_phrases', os.path.join(REPO, 'tools', 'sndrec-demo', 'phrases.py'))
demo = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(demo)


def _singles(notes, start, step, hold, vel=100):
    return [(start + i * step, n, vel, hold) for i, n in enumerate(notes)]


def probe(kind):
    if kind == 'bass':
        s = _singles([36, 43, 48], 0.0, 1.2, 0.9)
        s += [(3.6 + 0.25 * i, 36, 110, 0.2) for i in range(4)]
        return s, 1.0, [0, 1, 2]
    if kind in ('pad', 'drone'):
        s = _singles([48, 60], 0.0, 2.8, 2.0) + [(5.6, 55, 90, 2.0), (5.6, 60, 90, 2.0), (5.6, 64, 90, 2.0)]
        return s, 2.0, [0, 1]
    if kind == 'lead':
        return _singles([60, 67, 72], 0.0, 1.6, 1.2), 1.2, [0, 1, 2]
    if kind == 'pluck':
        s = _singles([48, 60, 72], 0.0, 1.1, 0.6) + [(3.3, 60, 96, 0.6), (3.3, 64, 96, 0.6), (3.3, 67, 96, 0.6)]
        return s, 1.2, [0, 1, 2]
    if kind == 'bell':
        s = _singles([60, 72, 79], 0.0, 1.8, 1.0) + [(5.4, 60, 90, 1.0), (5.4, 67, 90, 1.0)]
        return s, 2.0, [0, 1, 2]
    if kind == 'fx':
        return [(0.0, 60, 100, 3.0), (4.0, 48, 100, 2.0)], 2.5, [0, 1]
    if kind == 'perc':
        return [(0.0, 60, 110, 0.15), (0.5, 60, 90, 0.15), (1.0, 48, 110, 0.15), (1.5, 72, 100, 0.15)], 0.8, [0, 2, 3]
    # keys (default)
    s = _singles([48, 60, 72], 0.0, 1.5, 1.0) + [(4.5, 60, 92, 1.0), (4.5, 64, 92, 1.0), (4.5, 67, 92, 1.0)]
    return s, 1.5, [0, 1, 2]


# builder kind -> demo phrase kind (tools/sndrec-demo/phrases.py KINDS)
PHRASE_OF = {'keys': 'keys', 'pluck': 'arp', 'bass': 'bass', 'pad': 'pad', 'drone': 'drone', 'lead': 'lead',
             'bell': 'melody', 'fx': 'fx', 'perc': 'perc', 'mono': 'mono'}


def phrase(kind, mono=False):
    k = 'mono' if mono and kind in ('keys', 'bell', 'lead', 'pluck') else PHRASE_OF.get(kind, 'keys')
    notes, tail = demo.KINDS[k]()
    return [tuple(n) for n in notes], tail, demo.LABEL[k]

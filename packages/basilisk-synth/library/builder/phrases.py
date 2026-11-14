"""Scores for the builder.

probe(kind): a short screening score of isolated notes (for pitch, key tracking, envelope and brightness) plus,
for polyphonic kinds, one chord (for summing and voice pools). Each returns (score, tail, singles) where singles
are the indices of the isolated notes the analysis measures.

phrase(kind): the musical demo phrase, from tools/sndrec-demo/phrases.py (the sndrec.html demos' generator),
used for the final render that is checked again and encoded for listening.
"""
import importlib.util, os, re
from common import REPO

_spec = importlib.util.spec_from_file_location('demo_phrases', os.path.join(REPO, 'tools', 'sndrec-demo', 'phrases.py'))
demo = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(demo)


def _singles(notes, start, step, hold, vel=100):
    return [(start + i * step, n, vel, hold) for i, n in enumerate(notes)]


def kit_pads(dna):
    """the notes a kit DNA maps (its k tokens: k<lo>[,<hi>])"""
    out = set()
    for lo, hi in re.findall(r'k(\d+)(?:,(\d+))?', dna.split(';', 1)[1] if ';' in dna else ''):
        out.update(range(int(lo), int(hi or lo) + 1))
    return sorted(out)


def probe(kind, dna=None):
    if kind == 'kit' and dna:
        notes = kit_pads(dna) or [36]
        return [(0.35 * i, n, 105, 0.2) for i, n in enumerate(notes)], 2.0, [0, 1, 2][:len(notes)]
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
    if kind == 'kit':
        # every GM pad a kit may map, one at a time (the first three are the singles the analysis measures)
        notes = [36, 38, 42, 46, 39, 37, 35, 40, 41, 43, 44, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55]
        return [(0.3 * i, n, 105, 0.2) for i, n in enumerate(notes)], 1.0, [0, 1, 2]
    if kind == 'perc':
        return [(0.0, 60, 110, 0.15), (0.5, 60, 90, 0.15), (1.0, 48, 110, 0.15), (1.5, 72, 100, 0.15)], 0.8, [0, 2, 3]
    # keys (default)
    s = _singles([48, 60, 72], 0.0, 1.5, 1.0) + [(4.5, 60, 92, 1.0), (4.5, 64, 92, 1.0), (4.5, 67, 92, 1.0)]
    return s, 1.5, [0, 1, 2]


# builder kind -> demo phrase kind (tools/sndrec-demo/phrases.py KINDS)
PHRASE_OF = {'keys': 'keys', 'pluck': 'arp', 'bass': 'bass', 'pad': 'pad', 'drone': 'drone', 'lead': 'lead',
             'bell': 'melody', 'fx': 'fx', 'perc': 'perc', 'mono': 'mono', 'kit': 'perc'}


def kit_groove():
    # two bars at 100 bpm in sixteenths, then a fill: kick 36, snare 38, closed hat 42, open hat 46, clap 39,
    # rim 37, toms 50/47/45, crash 49; then each pad 35-55 once, so every pad of a kit is heard in the demo
    st = 0.15
    hits = []
    for bar in range(2):
        b = bar * 16
        for s in (0, 6, 8, 11): hits.append((b + s, 36, 118))
        for s in (4, 12): hits.append((b + s, 38, 110))
        for s in range(0, 16, 2): hits.append((b + s, 42, 78 if s % 4 else 92))
        hits.append((b + 14, 46, 90)); hits.append((b + 12, 39, 84)); hits.append((b + 7, 37, 70))
    for k, n in enumerate((50, 50, 47, 47, 45, 45, 49)): hits.append((32 + k, n, 112))
    out = [(round(s * st, 3), n, v, 0.12) for s, n, v in hits]
    t0 = 40 * st
    out += [(round(t0 + 0.22 * i, 3), n, 100, 0.12) for i, n in enumerate(range(35, 56))]
    return sorted(out)


def phrase(kind, mono=False, dna=None):
    if kind == 'kit':
        pads = set(kit_pads(dna)) if dna else None
        g = [n for n in kit_groove() if pads is None or n[1] in pads]
        if pads:   # the groove's missing roles: every pad once at the end covers the kit
            t0 = max([n[0] for n in g] + [0]) + 0.4
            g += [(round(t0 + 0.22 * i, 3), n, 100, 0.12) for i, n in enumerate(sorted(pads))]
            g = sorted(set(g))
        return g, 2.0, 'groove and every pad'
    k = 'mono' if mono and kind in ('keys', 'bell', 'lead', 'pluck') else PHRASE_OF.get(kind, 'keys')
    notes, tail = demo.KINDS[k]()
    return [tuple(n) for n in notes], tail, demo.LABEL[k]

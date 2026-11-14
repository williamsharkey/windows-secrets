#!/usr/bin/env python3
"""Curate the evolved candidates into packs (pack-plan.md): the best passing candidate of each lineage, heroes
first, near-duplicates rejected by feature distance within the pack (and identical DNA anywhere), each group
capped at its count; the three researched packs take one preset per target. Names, tags and badges are attached.

    curate.py STATE.json [STATE2.json ...] [--min-dist 1.6] [--min-score 55]   -> data/selection.json
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DNA, edition, origins, uses_v3, save_json, W31
from packs import PACKS, PACK_BY_ID, PROG, W31_ONLY
from catdefs import CATS
from names import Namer

TAGS = {'Keys': 'keys', 'EP': 'electric piano', 'Organ': 'organ', 'Bass': 'bass', 'Pads': 'pad', 'Strings': 'strings',
        'Choir/Vox': 'vocal', 'Brass/Stabs': 'stab', 'Leads': 'lead', 'Plucks/Arps': 'pluck', 'Bells/Mallets': 'bell',
        'World': 'world', 'FX/Risers': 'fx', 'Drones/Ambient': 'drone', 'Textures': 'texture', 'Lo-fi/Vaporwave': 'lo-fi',
        'Frutiger Aero': 'aero', 'Y2K/Corporate': 'corporate', 'Electromech': 'electromech', 'Perc': 'perc'}


def describe_tags(row, t, r):
    tags = [TAGS.get(t['scat'], t['scat'].lower())]
    if t['group'] and t['group'].lower() not in tags: tags.append(t['group'].lower())
    d = DNA.parse(row['dna'])
    st = ''.join(''.join(L.steps) for L in d.layers)
    if 'R' in st: tags.append('reversed')
    if 'E' in st: tags.append('echo')
    if 'CP' in st: tags.append('looped')
    if '<' in st: tags.append('slowed')
    if any('U' in L.genes for L in d.layers): tags.append('detuned')
    if any(len(L.genes.get('H', [0])) > 1 for L in d.layers): tags.append('harmony')
    if len(d.layers) > 1: tags.append('%d layers' % len(d.layers))
    if any('Ja' in L.genes for L in d.layers): tags.append('drawn envelope')
    if any('Q' in L.genes or 'Jp' in L.genes for L in d.layers): tags.append('stereo')
    if row.get('v3'): tags.append('v3')
    if t.get('src') in ('genres', 'modern-favorites') and t.get('id'):
        tags.append(t['id'].split('-')[0] if t['src'] == 'genres' else 'favorite')
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('states', nargs='+')
    ap.add_argument('--min-dist', type=float, default=1.6)
    ap.add_argument('--min-score', type=float, default=55)
    ap.add_argument('--min-score-research', type=float, default=20)
    ap.add_argument('--rescore', action='store_true'); ap.add_argument('--feat', default=os.path.expanduser('~/libbuild/feat'))
    a = ap.parse_args()
    T, rows = [], []
    for f in a.states:
        s = json.load(open(f))
        off = len(T)
        T += s['targets']
        for r in s['rows']:
            r = dict(r); r['t'] += off; rows.append(r)
    if a.rescore:
        # the checks again, from the cached analyses (no render): thresholds can change after the run
        import score
        from common import WORK
        n = 0
        for r in rows:
            fp = os.path.join(a.feat, (r.get('key') or 'x') + '.json')
            if not os.path.exists(fp): continue
            fr = json.load(open(fp)); t = T[r['t']]
            ok, sc, why, info = score.check(fr, t['scat'], CATS[t['scat']]['kind'])
            f = score.features(fr) if ok else None
            r.update(ok=ok, score=sc, why=why, info=info, feat=f.round(3).tolist() if f is not None else None); n += 1
        print('rescored', n)
    # best passing row per lineage (the researched packs accept a lower fit score: their targets define the fit)
    best_all = {}
    for r in rows:
        if not r['ok'] or not r.get('feat'): continue
        k = (r['t'], r['lin'])
        if k not in best_all or r['score'] > best_all[k]['score']: best_all[k] = r
    best = {}
    for r in rows:
        if not r['ok'] or r['score'] < a.min_score or not r.get('feat'): continue
        k = (r['t'], r['lin'])
        if k not in best or r['score'] > best[k]['score']: best[k] = r
    print(len(rows), 'rows,', sum(r['ok'] for r in rows), 'pass,', len(best), 'lineages with a keeper')
    namer = Namer()
    chosen, used_dna = [], set()
    pack_feats = {}

    def novel(pid, f):
        fs = pack_feats.get(pid)
        if not fs: return True, 99.0
        dmin = float(np.min(np.linalg.norm(np.array(fs) - np.array(f), axis=1)))
        # researched packs are one design per target: only a near-copy is rejected there
        return dmin >= (a.min_dist * 0.5 if 'research' in PACK_BY_ID[pid] else a.min_dist), dmin

    def take(pid, group, prog, r, why):
        t = T[r['t']]
        canon = r['dna']
        if canon in used_dna: return False
        ok, dmin = novel(pid, r['feat'])
        if not ok: return False
        used_dna.add(canon); pack_feats.setdefault(pid, []).append(r['feat'])
        hero = r['lin'] == 'hero'
        keepname = t['name'] if (hero and t['src'] in ('genres', 'modern-favorites', 'aesthetic', 'electromech')) else None
        name = namer.keep_or_make(keepname, t['scat'], canon)
        ed = edition(canon)
        lib = 'library' in origins(canon)
        v3 = uses_v3(canon)
        chosen.append(dict(pack=pid, pack_name=PACK_BY_ID[pid]['name'], group=group, category=prog, name=name, dna=canon,
                           scat=t['scat'], kind=CATS[t['scat']]['kind'], lineage=r['lin'], target=t['id'], target_name=t['name'],
                           source=t['src'], score=r['score'], key=r['key'], info=r['info'], novelty=round(dmin, 2),
                           edition=ed, library=lib, v3=v3, origins=origins(canon),
                           ships=['3.11'] if v3 else ['3.11', 'XP'],
                           tags=describe_tags(r, t, r), why=why, character=t.get('character', '')))
        return True

    # 1. researched packs: one per target (hero if within 8 points of the best)
    for p in PACKS:
        if 'research' not in p: continue
        for ti, t in enumerate(T):
            if t['pack'] != p['id']: continue
            cs = sorted([r for (tt, l), r in best_all.items() if tt == ti and r['score'] >= a.min_score_research],
                        key=lambda r: -r['score'])
            if not cs: continue
            heroes = [r for r in cs if r['lin'] == 'hero' and r['score'] >= cs[0]['score'] - 8]
            for r in (heroes + cs):
                if take(p['id'], t['group'], prog_of(t['scat'] if t['group'] == 'Electromech' else t['group']), r, 'researched target'): break
    # 2. genre packs, group by group: heroes, then variants and fills by score
    heritage = PACK_BY_ID['w3x-heritage']
    for p in PACKS:
        if 'research' in p or p['id'] == 'w3x-heritage': continue
        for gname, cat, n2, n3 in p['groups']:
            cs = [r for (ti, l), r in best.items() if T[ti]['pack'] == p['id'] and T[ti]['group'] == gname]
            if not cs: continue
            def key(r):
                return (r['lin'] == 'hero', r['score'] + (6 if r['lin'] != 'fill' else 0))
            cs.sort(key=key, reverse=True)
            n_v2 = n_v3 = 0
            for r in cs:
                if r['lin'] == 'w311' and edition(r['dna']) == 'w31' and 'library' not in origins(r['dna']):
                    continue          # the 3.x twins go to the Heritage Edition first (below)
                if r.get('v3'):
                    if n_v3 >= n3: continue
                    if take(p['id'], gname, prog_of(gname), r, 'v3 twin'): n_v3 += 1
                else:
                    if n_v2 >= n2: continue
                    if take(p['id'], gname, prog_of(gname), r, r['lin']): n_v2 += 1
    # 3. Heritage Edition: W3.11-only presets (3.x sounds only, no library), twins and fills
    for gname, cat, n2, n3 in heritage['groups']:
        cs = [r for (ti, l), r in best.items()
              if (T[ti]['pack'] == 'w3x-heritage' and T[ti]['group'] == gname) or (l == 'w311' and T[ti]['scat'] == cat)]
        cs = [r for r in cs if set(DNA.parse(r['dna']).names()) <= set(W31_ONLY)]
        cs.sort(key=lambda r: (r['lin'] == 'w311', r['score']), reverse=True)
        n = 0
        for r in cs:
            if n >= n2 + n3: break
            if r.get('v3') and n >= n2: pass
            if take('w3x-heritage', gname, prog_of(gname), r, 'heritage'): n += 1
    save_json('selection.json', chosen)
    # what each pack group still lacks (for evolve.py --deficits)
    de = {}
    for p in PACKS:
        for gname, cat, n2, n3 in p.get('groups', []):
            have = sum(1 for c in chosen if c['pack'] == p['id'] and c['group'] == gname and not c['v3'])
            if have < n2: de.setdefault(p['id'], {})[gname] = n2 - have
    save_json('deficits.json', de)
    print('deficit', sum(sum(v.values()) for v in de.values()))
    by = {}
    for c in chosen: by[c['pack_name']] = by.get(c['pack_name'], 0) + 1
    for k, v in by.items(): print('%-40s %d' % (k, v))
    print('total', len(chosen), '; w31', sum(c['edition'] == 'w31' for c in chosen), '; v3', sum(c['v3'] for c in chosen),
          '; library', sum(c['library'] for c in chosen))


def prog_of(g):
    return PROG.get(g, {'Choir/Vox': 'Vocal', 'Bells/Mallets': 'Bell', 'Plucks/Arps': 'Pluck', 'Brass/Stabs': 'Stab',
                        'FX/Risers': 'FX', 'Drones/Ambient': 'Drone', 'Textures': 'Texture', 'Leads': 'Lead', 'Pads': 'Pad',
                        'Lo-fi/Vaporwave': 'Keys', 'Frutiger Aero': 'Bell', 'Y2K/Corporate': 'Keys', 'Electromech': 'Keys',
                        'World': 'Pluck', 'EP': 'Keys'}.get(g, g))


if __name__ == '__main__':
    main()

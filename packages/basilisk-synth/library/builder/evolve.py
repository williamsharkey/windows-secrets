#!/usr/bin/env python3
"""Generate, render and score candidates for every pack (research/pack-plan.md), in rounds.

    evolve.py [--parallel 8] [--rounds 3] [--fill 1.0] [--pack ID] [--limit N] [--out NAME]

Targets:
- genres.json and modern-favorites.json (not the kits: v3 kit mode is not built yet), each in its pack and group;
- the three researched packs (preset-targets, aesthetic drafts, electromech instruments): one lineage each;
- fills: template targets composed from the category pools (catdefs.py), biased to the pack's palette (pack
  'prefer'; the Heritage Edition only uses the six 3.x sounds), where a group has fewer seeds than its count.

A target grows lineages by the plan's rules (section 3): hero (its DNA, and an auto-rooted copy), source swaps
(the target's alternates), the W3.11 edition twin (XP sounds -> 3.x sounds), a register/character twin, and a v3
twin (W/Y genes) where the group has a v3 share. Round 0 renders every lineage's start; later rounds mutate each
lineage's best (retuning it when its pitch class is a semitone or more off) and repair lineages that failed.
Every candidate is rendered by render311 through the real Windows 3.11 machine and checked (score.py).
State: $LIBBUILD/state/<out>.json.
"""
import argparse, json, os, random, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DNA, WORK, LIB, uses_v3, W31, BUILTIN
from catdefs import CATS
from packs import PACKS, PACK_BY_ID, PLAN_PACK, ROLE_CAT, group_for, W31_ONLY
import gen, phrases, render, score

STATE = os.path.join(WORK, 'state')
os.makedirs(STATE, exist_ok=True)
EM_SCORE = {'Bells': 'Bells/Mallets', 'Mallets': 'Bells/Mallets', 'Leads': 'Leads', 'Drones': 'Drones/Ambient',
            'FX': 'FX/Risers', 'Plucks': 'Plucks/Arps', 'Keys': 'Keys', 'Pads': 'Pads', 'Voices': 'Choir/Vox'}
# W3.11 twin: an XP sound -> the 3.x sound in the same role
TWIN31 = {'dingxp': 'ding', 'xpding': 'ding', 'default': 'ding', 'print': 'ding', 'exclaim': 'ding', 'error': 'chimes',
          'chimesxp': 'chimes', 'xpnotify': 'chimes', 'notify': 'chimes', 'chordxp': 'chord', 'hwfail': 'chord',
          'hwin': 'chord', 'hwout': 'chord', 'critstop': 'chord', 'batcrit': 'chord', 'batlow': 'ringout',
          'tadaxp': 'tada', 'startup': 'tada', 'logon': 'tada', 'logoff': 'chord', 'shutdown': 'chord',
          'xpringout': 'ringout', 'xpringin': 'ringin', 'popup': 'ringin', 'balloon': 'ding', 'menu': 'ringin',
          'start': 'ringin', 'xpstart': 'ringin', 'infobar': 'ding', 'recycle': 'ringin', 'xprecycle': 'ringin',
          'minimize': 'ringout', 'restore': 'ringout', 'chimes': 'chimes'}
V3_ONLY_WY = re.compile(r'[WY]')


def fixname(s):
    return s.replace('piano_upright_c#', 'piano_upright_cs').replace('bass_guitar_g#', 'bass_guitar_gs')


def auto_k(d):
    r = gen.layer_root(d.layers[0])
    if r is None: return None
    e = d.copy(); e.glob['K'] = int(round(r))
    return e


def fold(x):
    return ((x + 6) % 12) - 6


def _root(name):
    return gen.SRC.get(name, {}).get('root_used') if gen.SRC.get(name, {}).get('tonal') else None


def _resrc(e, i, name):
    """put a new source into layer i, keeping the layer's pitch (K for layer 0, T for the others) within a fifth"""
    L = e.layers[i]
    a, b = _root(L.src), _root(name)
    L.src = name
    if a is None or b is None: return
    dk = int(round(fold(a - b)))
    if i == 0:
        e.glob['K'] = max(0, min(127, e.glob.get('K', 60) - dk))
        for M in e.layers[1:]:
            if not M.genes.get('F'): M.genes['T'] = max(-48, min(48, M.genes.get('T', 0) - dk))
    elif not L.genes.get('F'):
        L.genes['T'] = max(-48, min(48, L.genes.get('T', 0) + dk))


def swap_source(d, name):
    if not gen.known(name): return None
    e = d.copy()
    _resrc(e, 0, name)
    return e


def twin31(d):
    e = d.copy(); changed = False
    for i, L in enumerate(e.layers):
        if L.src in BUILTIN and L.src not in W31 and L.src not in ('ringin', 'ringout'):
            _resrc(e, i, TWIN31.get(L.src, 'ding')); changed = True
        L.steps = [('I' + TWIN31.get(x[1:], 'ding') if x[:1] == 'I' and x[1:] in BUILTIN and x[1:] not in W31 | {'ringin', 'ringout'}
                    else 'M' + TWIN31.get(x[1:], 'ding') if x[:1] == 'M' and x[1:] in BUILTIN and x[1:] not in W31 | {'ringin', 'ringout'}
                    else x) for x in L.steps]
    if not changed: return None
    return e


def register_twin(d, kind, rng):
    e = d.copy(); L = e.layers[0]
    if kind in ('pad', 'drone'):
        L.steps.append('<'); e.glob['K'] = e.glob.get('K', 60) - 12; e.glob['A'] = int(e.glob.get('A', 300) * 1.6) + 100
    elif kind in ('bass',):
        L.steps.append('<'); e.glob['K'] = e.glob.get('K', 60) - 12; e.glob['S'] = rng.choice([0, 60]); e.glob['D'] = 400
    elif kind in ('lead',):
        e.glob.update(A=rng.choice([150, 300]), S=95, R=600)
    else:   # keys, pluck, bell, perc: a pluck/sustain swap
        if e.glob.get('S', 100) > 40: e.glob.update(D=rng.choice([250, 400]), S=0, R=200)
        else: e.glob.update(A=rng.choice([60, 200]), S=85, R=900); L.genes['U'] = (2, 8)
    return e


class T:   # a target
    def __init__(self, **k): self.__dict__.update(k)


def plan_targets(a, rng):
    R = os.path.join(LIB, 'research')
    TT = []
    for f in ('genres.json', 'modern-favorites.json'):
        for x in json.load(open(os.path.join(R, f)))['targets']:
            pack = PLAN_PACK.get(x.get('pack'))
            if not pack or x['role'] == 'drums': continue
            g = group_for(pack, x['role'])
            if not g: continue
            d = gen.clean_dna(fixname(x['dna']))
            if not d: continue
            alts = [fixname(n) for n in (x.get('alternates') or {}).get('windows', []) + (x.get('alternates') or {}).get('library', [])]
            v3 = None
            if x.get('v3_dna'):
                body = re.sub(r';.*', '', fixname(x['v3_dna']))
                extra = set(re.findall(r'(?<![a-z0-9_])([NSVZG])(?=[a-z0-9.])', body))
                if not extra:
                    v3d = gen.clean_dna(fixname(x['v3_dna']))
                    if v3d and uses_v3(v3d.text()): v3 = v3d.text()
            TT.append(T(id=x['id'], src=f.split('.')[0], name=x['name'], pack=pack, group=g[0], scat=g[1],
                        role=x['role'], seed=d.text(), alts=alts, v3=v3, character=x.get('character', ''),
                        priority=x.get('priority', 2)))
    rp = {'preset-targets': 'rom-reference', 'aesthetic': 'lifestyle-aesthetics', 'electromech': 'electromech-heritage'}
    for t in gen.research_targets():
        if t['src'] == 'factory': continue
        sc = EM_SCORE.get(t.get('sub'), 'Keys') if t['src'] == 'electromech' else t['cat']
        TT.append(T(id=t['id'], src=t['src'], name=t['ref'], pack=rp[t['src']], group=t['cat'], scat=sc, role='',
                    seed=t['seed'], alts=[], v3=None, character=t.get('character', ''), priority=t.get('priority', 2)))
    # fills: per pack group, the count minus what its seeds will yield (about 3 kept per seed)
    for p in PACKS:
        for name, cat, n2, n3 in p.get('groups', []):
            seeds = sum(1 for t in TT if t.pack == p['id'] and t.group == name)
            need = int(round(a.fill * max(0, n2 - 3 * seeds) * 1.6))
            if p['id'] == 'w3x-heritage': need = int(round(a.fill * n2 * 1.5))
            for i in range(need):
                TT.append(T(id='%s-%s-%03d' % (p['id'], name.lower().replace(' ', '-'), i), src='fill', name='', pack=p['id'],
                            group=name, scat=cat, role=name.lower(), seed=None, alts=[], v3=None, character='', priority=3,
                            only=p.get('only'), prefer=p.get('prefer', [])))
    if getattr(a, 'repair', None):
        # a repair wave: researched targets with no passing lineage, restarted from their best candidate
        TT = [T(**t) for t in json.load(open(a.repair))]
        return TT
    if getattr(a, 'deficits', None):
        # a fill wave: only new template targets, for the pack groups still short after curation
        de = json.load(open(a.deficits)); TT = []
        for p in PACKS:
            for name, cat, n2, n3 in p.get('groups', []):
                for i in range(int(round(de.get(p['id'], {}).get(name, 0) * 1.5))):
                    TT.append(T(id='%s-%s-w%03d' % (p['id'], name.lower().replace(' ', '-'), i), src='fill', name='', pack=p['id'],
                                group=name, scat=cat, role=name.lower(), seed=None, alts=[], v3=None, character='', priority=3,
                                only=p.get('only'), prefer=p.get('prefer', [])))
    if a.pack: TT = [t for t in TT if t.pack == a.pack]
    if a.limit: TT = rng.sample(TT, min(a.limit, len(TT)))
    return TT


def lineages(t, rng):
    """[(lineage, dna)] for round 0"""
    kind = CATS[t.scat]['kind']
    out = []
    if t.seed:
        d = DNA.parse(t.seed)
        out.append(('hero', d.text()))
        if 'K' not in d.glob:
            e = auto_k(d)
            if e: out.append(('hero', e.text()))
        if t.src in ('genres', 'modern-favorites'):
            for n in t.alts[:1]:
                e = swap_source(d, n)
                if e: out.append(('swap-' + n, e.text()))
            e = twin31(d)
            if e: out.append(('w311', e.text()))
            if t.priority == 1: out.append(('register', register_twin(d, kind, rng).text()))
            pk = PACK_BY_ID[t.pack]
            g = [x for x in pk['groups'] if x[0] == t.group]
            if t.v3: out.append(('v3', t.v3))
            elif g and g[0][3] > 0 or t.scat in gen.V3W: out.append(('v3', gen.humanize(d, t.scat, rng).text()))
    else:
        for i in range(2):
            d, _ = gen.compose(t.scat, rng, prefer=set(t.prefer or ()), only=set(t.only) if t.only else None)
            out.append(('fill', d.text()))
    return out


BPM = {'workgroup-house': 122, 'techno-server': 130, 'trance-connectivity': 138, 'breakbeat-resource': 172,
       'bass-enterprise': 140, 'beat-management': 90, 'retro-display': 105, 'screen-saver': 80, 'diagnostics': 120,
       'leisure': 110, 'game-port': 140, 'workstation-classics': 128, 'studio-archive': 100, 'w3x-heritage': 120}


def needs_bpm(dna):
    return any('W' in L.genes and re.search(r'[bgt]', re.sub(r'[\d.~]', '', L.genes['W'])) for L in DNA.parse(dna).layers)


def v3_variants(t, rng):
    """the plan's v3 slots with the features on 3.11 now (15040db): glide/legato, strum, beat gates and looping
    wobbles, tempo-synced taps; each from the target's hero DNA"""
    d = DNA.parse(t.seed); kind = CATS[t.scat]['kind']; out = []
    L0 = d.layers[0]
    if kind in ('bass', 'lead'):
        e = d.copy(); e.layers[0].genes['N'] = rng.choice(['lg%d' % rng.choice([40, 60, 90, 140]), 'mg%d' % rng.choice([30, 60]), 'cg%d' % rng.choice([50, 100])])
        out.append(('v3-glide', e.text()))
    if kind in ('keys', 'pluck', 'bell') or t.scat in ('Brass/Stabs',):
        e = d.copy(); L = e.layers[0]
        if len(L.genes.get('H', [0])) < 3: L.genes['H'] = rng.choice([[0, 4, 7], [0, 3, 7], [0, 7, 12], [0, 3, 7, 10], [0, 4, 7, 11]])
        L.genes['S'] = 's%d' % rng.choice([15, 25, 40, 60])
        out.append(('v3-strum', e.text()))
    if kind in ('pad', 'bass', 'drone') or t.scat in ('Brass/Stabs', 'Textures', 'Strings'):
        e = d.copy(); L = e.layers[0]
        step = rng.choice([125, 250]) // 1      # 1/16 or 1/8 at 120 bpm, scaled by Wt
        on = int(step * rng.choice([0.5, 0.7]))
        L.genes['Ja'] = [(0, 100), (on, 100), (on + 10, 8), (step, 8), (step + 1, 100)]
        L.genes['W'] = L.genes.get('W', '') + 'r4t'
        e.glob['A'] = 0; e.glob['S'] = 100
        out.append(('v3-gate', e.text()))
    if len(d.layers) > 1 and any('O' in L.genes for L in d.layers[1:]):
        e = d.copy()
        for L in e.layers[1:]:
            if 'O' in L.genes:
                o = L.genes.pop('O'); L.genes['W'] = L.genes.get('W', '') + 'b%d' % max(1, round(o / 125.0))
        out.append(('v3-sync', e.text()))
    return out


def job_for(t, dna):
    k = CATS[t.scat]['kind']
    s, tail, singles = phrases.probe(k)
    j = dict(dna=dna, score=s, tail=tail, kind=k, singles=singles)
    if needs_bpm(dna): j['bpm'] = BPM.get(t.pack, 120)
    return j


def evaluate(TT, cands, a, done):
    todo, seen = [], set()
    for ti, lin, dna, org in cands:
        if (ti, dna) in seen or (ti, dna) in done: continue
        if len(dna) > 1024: continue
        seen.add((ti, dna)); todo.append((ti, lin, dna, org))
    res = render.render_all([job_for(TT[ti], dna) for ti, _, dna, _ in todo], a.parallel, progress=True)
    rows = []
    for (ti, lin, dna, org), r in zip(todo, res):
        t = TT[ti]
        ok, sc, why, info = score.check(r, t.scat, CATS[t.scat]['kind'])
        f = score.features(r) if ok else None
        rows.append(dict(t=ti, lin=lin, dna=dna, origin=org, ok=ok, score=sc, why=why, info=info, key=r.get('key'),
                         feat=f.round(3).tolist() if f is not None else None, v3=uses_v3(dna)))
        done.add((ti, dna))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--parallel', type=int, default=8)
    ap.add_argument('--fill', type=float, default=1.0)
    ap.add_argument('--pack'); ap.add_argument('--limit', type=int)
    ap.add_argument('--seed', type=int, default=1999)
    ap.add_argument('--out', default='evolve')
    ap.add_argument('--repair', help='JSON list of targets (with seed = best DNA so far)')
    ap.add_argument('--deficits', help='JSON {pack: {group: missing}}: a fill wave for those groups')
    ap.add_argument('--v3pass', action='store_true', help='only the v3 (N S W-time) variants of the plan targets')
    ap.add_argument('--shard', default='0/1', help='i/n: this run takes the targets whose index is i mod n')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    open(os.path.join(render.RUN, 'evolve.pid'), 'w').write(str(os.getpid()))
    TT = plan_targets(a, rng)
    si, sn = (int(x) for x in a.shard.split('/'))
    TT = [t for i, t in enumerate(TT) if i % sn == si]
    rng = random.Random(a.seed * 10 + si)
    print(len(TT), 'targets', flush=True)
    t0 = time.time(); rows = []; done = set()

    def save():
        json.dump({'targets': [t.__dict__ for t in TT], 'rows': rows, 'stats': render.STATS, 'wall': time.time() - t0},
                  open(os.path.join(STATE, a.out + '.json'), 'w'))

    if a.v3pass:
        TT = [t for t in TT if t.src in ('genres', 'modern-favorites')]
        c0 = [(i, lin, dna, 'start') for i, t in enumerate(TT) for lin, dna in v3_variants(t, rng)]
    else:
        c0 = [(i, lin, dna, 'start') for i, t in enumerate(TT) for lin, dna in lineages(t, rng)]
    rows += evaluate(TT, c0, a, done)
    print('round 0: %d rows, %d pass, %.0f s' % (len(rows), sum(r['ok'] for r in rows), time.time() - t0), flush=True)
    save()
    for rnd in range(1, a.rounds):
        by = {}
        for r in rows: by.setdefault((r['t'], r['lin']), []).append(r)
        cn = []
        for (ti, lin), rs in by.items():
            t = TT[ti]
            rs.sort(key=lambda r: (r['ok'], r['score']), reverse=True)
            best = rs[0]
            if rnd > 1 and best['ok']: continue      # good enough: spend renders on repairs
            d = DNA.parse(best['dna'])
            if best['info'].get('retune') is not None:
                cn.append((ti, lin, gen.retune(d, best['info']['retune']).text(), 'retune'))
            n = 1 if best['ok'] else 2
            for _ in range(n):
                m, log = gen.mutate(d, t.scat, rng)
                if lin == 'w311' or getattr(t, 'only', None):
                    m = twin31(m) or m
                if not lin.startswith('v3'):
                    for L in m.layers: L.genes.pop('W', None); L.genes.pop('Y', None)
                cn.append((ti, lin, m.text(), 'mutant:' + '+'.join(log)))
        rows += evaluate(TT, cn, a, done)
        print('round %d: %d rows, %d pass, %.0f s; renders %s' % (rnd, len(rows), sum(r['ok'] for r in rows), time.time() - t0,
                                                                   render.STATS), flush=True)
        save()
    save()
    print('done', len(TT), 'targets', len(rows), 'rows', sum(r['ok'] for r in rows), 'pass', render.STATS)


if __name__ == '__main__':
    main()

"""Candidate generation: compose a DNA from a category's pools (in tune by construction, from the measured roots),
mutate DNAs over real Sound Recorder steps and voice genes, and gather the research targets as seeds.

Everything is DNA v2. Ideas that need v3 (kits, grains, tape, mono/legato) are written to data/v3-ideas.json.
"""
import json, math, os, random, re
from common import DNA, Layer, LIB, load_json, library_names, BUILTIN
from catdefs import CATS, ROLES, LOOP, RESEARCH_CAT, KEYWORDS, AES_CAT, EM_KIND

SRC = load_json('sources.json', {})
KNOWN = set(BUILTIN) | set(library_names())
STEPCH = set('+-<>ERCPX[]')


def known(n):
    return n in KNOWN and n in SRC


def wpick(rng, items):
    """items: [(value, weight), ...]"""
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    for v, w in items:
        x -= w
        if x <= 0: return v
    return items[-1][0]


def loguni(rng, lo, hi):
    if lo <= 0: return rng.uniform(lo, hi)
    return math.exp(rng.uniform(math.log(lo), math.log(hi)))


# ------------------------------------------------------------------ roots
def seg_root(name, a=None, b=None):
    """the pitch of a source, or of the part of it kept by a trim (a..b seconds)"""
    r = SRC.get(name)
    if not r: return None
    if a is not None and r.get('segs'):
        mid = a + 0.25 * ((b or r['seconds']) - a)
        for s in r['segs']:
            if s[0] <= mid < s[1] and s[2] is not None and s[3] > 0.6 and 'name_root' not in r:
                return s[2]
    return r.get('root_used')


def steps_speed(steps):
    return 12 * (sum(1 for s in steps if s == '>') - sum(1 for s in steps if s == '<'))


def trim_of(steps):
    """(a, b) seconds of the source kept by leading @t..] @t..[ steps, if the layer starts with them"""
    a = b = None
    for s in steps[:4]:
        m = re.match(r'@t(\d+)$', s)
        if m: pos = int(m.group(1)) / 1000.0; continue
        if s == ']' and 'pos' in dir(): b = pos
        elif s == '[' and 'pos' in dir(): a = pos
        else: break
    return a, b


def layer_root(L):
    """effective root of a layer as built (source/segment root + octaves of speed steps), or None if not tonal"""
    r = SRC.get(L.src)
    if not r or not r.get('tonal'): return None
    a = b = None
    pos = None
    for s in L.steps:
        m = re.match(r'@t(\d+)$', s)
        if m: pos = int(m.group(1)) / 1000.0; continue
        if s == ']' and pos is not None: b = pos if b is None else b
        elif s == '[' and pos is not None: a = pos
    root = seg_root(L.src, a, b)
    if root is None: return None
    return root + steps_speed(L.steps)


def trim_steps(name, trim):
    if trim is None: return []
    if trim == 'loop': return loop_steps(name)
    a, b = trim
    dur = SRC[name]['seconds']
    out = []
    if b is not None and b < dur - 0.02: out += ['@t%d' % int(b * 1000), ']']
    if a and a > 0.005: out += ['@t%d' % int(a * 1000), '[']
    return out


def loop_steps(name, rng=None):
    """a steady chunk of a sustaining sound, pasted to itself into a held tone"""
    r = SRC[name]; d = r['seconds']
    a, b = 0.2 * d, 0.7 * d
    seq = ['@t%d' % int(b * 1000), ']', '@t%d' % int(a * 1000), '[']
    reps = 3 if (b - a) < 0.35 else 2
    for _ in range(reps): seq += ['@0', 'C', 'P']
    return seq


def treat_steps(t):
    out = []
    i = 0
    while i < len(t):
        if t[i] == '@':
            m = re.match(r'@t?\d+', t[i:]); out.append(m.group(0)); i += len(m.group(0))
        else:
            out.append(t[i]); i += 1
    return out


# ------------------------------------------------------------------ compose
def assign_pools(d, poly):
    v = []
    for L in d.layers:
        h = len(L.genes.get('H', [0])); u = L.genes.get('U', (1, 0))[0]
        v.append(max(1, h * u))
    tot = sum(v)
    while tot * poly > 16 and poly > 1: poly -= 1
    while tot > 16:
        k = v.index(max(v)); L = d.layers[k]
        u, c = L.genes.get('U', (1, 0))
        if u > 1: L.genes['U'] = (u - 1, c); v[k] = max(1, len(L.genes.get('H', [0])) * (u - 1))
        elif len(L.genes.get('H', [0])) > 1: L.genes['H'] = L.genes['H'][:-1]; v[k] = len(L.genes['H'])
        else: break
        tot = sum(v)
    if len(d.layers) == 1:
        d.layers[0].genes.pop('#', None)
        return
    left = 16
    for i, L in enumerate(d.layers):
        rest = len(d.layers) - i - 1
        n = max(1, min(left - rest, round(16 * v[i] / tot)))
        if i == len(d.layers) - 1: n = left
        L.genes['#'] = n; left -= n


def compose(cat, rng, prefer=(), only=None):
    c = CATS[cat]
    if only:
        pool = [((n, t), w) for n, w, t in c['pool'] if n in only]
        if len(pool) < 3:
            pool += [((n, [None, 'loop'] if c['kind'] in ('pad', 'lead', 'drone') else [None, (0, SRC[n]['seconds'] * 0.4)]), 1)
                     for n in only if n not in [p[0][0] for p in pool]]
    else:
        pool = [((n, t), w * (4 if n in prefer else 1)) for n, w, t in c['pool'] if known(n)]
        pool += [((n, [None]), 3) for n in prefer if known(n) and n not in [p[0][0] for p in pool]
                 and (SRC[n]['tonal'] or not c['tonal'])]
    name, trims = wpick(rng, pool)
    trim = rng.choice(trims)
    P = Layer(name, trim_steps(name, trim))
    treat = wpick(rng, c['treat'])
    P.steps += treat_steps(treat)
    meta = {'roles': ['primary'], 'cat': cat}
    root = layer_root(P)
    if c.get('fixed') and rng.random() < c['fixed']:
        P.genes['F'] = True; root = None
    elif root is not None and c['speed'] and c['tonal']:
        # octave steps toward the register (Sound Recorder's own speed changes), sometimes left to the rate
        s = round((c['register'] - root) / 12)
        s = max(-3, min(3, s))
        if s and (abs(c['register'] - root) > 24 or rng.random() < 0.6):
            if cat != 'Lo-fi/Vaporwave':
                while s > 0 and '<' in P.steps: P.steps.remove('<'); s -= 1; root += 12
                while s < 0 and '>' in P.steps: P.steps.remove('>'); s += 1; root -= 12
            P.steps += (['>'] * s if s > 0 else ['<'] * (-s))
            root += 12 * s
    U = wpick(rng, c['U'])
    if U[0] > 1: P.genes['U'] = (U[0], max(1, int(round(U[1] * rng.uniform(0.7, 1.3)))))
    H = wpick(rng, c['H'])
    if H != [0]: P.genes['H'] = H
    d = DNA([P])
    nl = wpick(rng, list(zip(c['layers'], c['lw'])))
    tries = 0
    while len(d.layers) < nl and tries < 6:
        tries += 1
        role = wpick(rng, c['companions'])
        L = companion(role, root, rng, c, only)
        if L is None: continue
        d.layers.append(L); meta['roles'].append(role)
    g = {}
    if c['A'][1] > 0: g['A'] = int(loguni(rng, max(1, c['A'][0]), c['A'][1])) if c['A'][0] > 0 else int(rng.choice([0, 0, 1, 2, 3, 5]) if c['A'][1] <= 10 else loguni(rng, 1, c['A'][1]))
    if c['D'][1] > 0: g['D'] = int(loguni(rng, c['D'][0], c['D'][1]))
    g['S'] = int(rng.uniform(*c['S'])) if c['S'][0] != c['S'][1] else c['S'][0]
    g['R'] = int(loguni(rng, c['R'][0], c['R'][1]))
    g['V'] = int(rng.uniform(*c['V']))
    if root is not None: g['K'] = int(round(root))
    d.glob = g
    assign_pools(d, c['poly'])
    return d, meta


def companion(role, root, rng, c, only=None):
    pool = [((n, t), w) for n, w, t in ROLES[role] if known(n) and (not only or n in only)]
    if not pool: return None
    name, trims = wpick(rng, pool)
    L = Layer(name, trim_steps(name, rng.choice(trims)))
    if role == 'click':
        L.genes['F'] = True; L.genes['L'] = int(rng.uniform(15, 45))
        if rng.random() < 0.3: L.steps.append('>')
        return L
    if role == 'air':
        if rng.random() < 0.6: L.genes['F'] = True
        L.genes['L'] = int(rng.uniform(10, 35))
        if rng.random() < 0.5: L.genes['Ja'] = [(0, 100), (int(rng.uniform(40, 200)), 30), (int(rng.uniform(300, 900)), 0)]
        return L
    r = layer_root(L)
    if r is None or root is None:
        if root is not None: return None
        L.genes['L'] = int(rng.uniform(20, 60))
        return L
    interval = {'tine': rng.choice([12, 24, 12, 19]), 'shimmer': rng.choice([12, 24, 19, 12]), 'sub': -12,
                'body': rng.choice([0, 0, -12, 12])}[role]
    if role == 'shimmer':
        L.steps += rng.choice([['R'], ['E'], ['R', 'E'], ['E', 'E'], ['>'], ['R', '>']])
        if '>' in L.steps: r += 12
        L.genes['O'] = int(rng.uniform(40, 400)); L.genes['Q'] = int(rng.uniform(-60, 60))
        L.genes['L'] = int(rng.uniform(15, 40))
    elif role == 'tine':
        L.genes['L'] = int(rng.uniform(12, 40)); L.genes['Q'] = int(rng.uniform(-35, 35))
        if rng.random() < 0.4: L.genes['O'] = int(rng.uniform(5, 25))
    elif role == 'sub':
        L.genes['L'] = int(rng.uniform(30, 70))
    else:
        L.genes['L'] = int(rng.uniform(25, 70)); L.genes['Q'] = int(rng.uniform(-40, 40))
    t = int(round(root - r)) + interval
    while t > 36: t -= 12
    while t < -36: t += 12
    if t: L.genes['T'] = t
    return L


# ------------------------------------------------------------------ mutate
def clampi(v, lo, hi):
    return int(max(lo, min(hi, v)))


def mutate(d, cat, rng, n_ops=None):
    c = CATS[cat]
    d = d.copy()
    ops = n_ops or wpick(rng, [(1, 4), (2, 3), (3, 1)])
    log = []
    for _ in range(ops):
        op = wpick(rng, [('env', 5), ('level', 3), ('pan', 2), ('offset', 2), ('unison', 3), ('harmony', 2),
                         ('swap', 3), ('add', 2), ('drop', 2), ('step', 4), ('trim', 2), ('ja', 2), ('vel', 1), ('echo', 2), ('v3', V3W.get(cat, 0))])
        k = rng.randrange(len(d.layers))
        L = d.layers[k]
        if op == 'env':
            g = rng.choice('ADSR')
            v = d.glob.get(g, {'A': 0, 'D': 0, 'S': 100, 'R': 120}[g])
            if g == 'S': d.glob['S'] = clampi(v + rng.uniform(-25, 25), 0, 100)
            else:
                v = max(v, 5) * 2 ** rng.gauss(0, 0.8)
                lo, hi = c[g]
                d.glob[g] = clampi(v, 0, max(hi * 1.5, 10)) if hi > 0 else 0
        elif op == 'level' and len(d.layers) > 1:
            L.genes['L'] = clampi(L.genes.get('L', 100) * 2 ** rng.gauss(0, 0.5), 5, 200)
        elif op == 'pan':
            L.genes['Q'] = clampi(rng.uniform(-70, 70), -100, 100)
        elif op == 'offset' and k > 0:
            L.genes['O'] = clampi(L.genes.get('O', 0) * 1.5 + rng.uniform(0, 120), 0, 1500)
        elif op == 'unison':
            u, cc = L.genes.get('U', (1, 0))
            u = clampi(u + rng.choice([-1, 1]), 1, 4)
            cc = clampi((cc or 6) * 2 ** rng.gauss(0, 0.4), 1, 40)
            L.genes['U'] = (u, cc if u > 1 else 0)
            if u == 1: L.genes.pop('U')
        elif op == 'harmony':
            H = wpick(rng, c['H'])
            if H == [0]: L.genes.pop('H', None)
            else: L.genes['H'] = H
        elif op in ('swap', 'add'):
            ref = d.glob.get('K', 60) if layer_root(d.layers[0]) is not None else None
            N = companion(wpick(rng, c['companions']), ref, rng, c)
            if N is not None:
                if op == 'swap' and k > 0: d.layers[k] = N
                elif op == 'add' and len(d.layers) < 4: d.layers.append(N)
        elif op == 'drop' and len(d.layers) > 1:
            d.layers.pop(rng.randrange(1, len(d.layers)))
        elif op == 'step':
            s = rng.choice(['E', '+', '-', 'E', 'R', 'C@50X', '@0CP'])
            if s == '+' and L.steps.count('+') > 2: s = '-'
            if s == 'R' and k == 0 and c['kind'] not in ('pad', 'fx', 'drone'): s = 'E'
            L.steps += treat_steps(s)
        elif op == 'echo':
            if 'E' in L.steps: L.steps.remove('E')
            else: L.steps.append('E')
        elif op == 'trim':
            for i, s in enumerate(L.steps):
                m = re.match(r'@t(\d+)$', s)
                if m:
                    L.steps[i] = '@t%d' % max(1, int(int(m.group(1)) * rng.uniform(0.8, 1.2))); break
            else:
                if c['kind'] in ('pluck', 'perc', 'bass'):
                    L.steps = ['@t%d' % int(SRC.get(L.src, {}).get('seconds', 1) * 1000 * rng.uniform(0.25, 0.6)), ']'] + L.steps
        elif op == 'ja':
            if 'Ja' in L.genes and rng.random() < 0.4: L.genes.pop('Ja')
            else:
                kind = c['kind']
                if kind in ('pad', 'drone'):
                    a = int(rng.uniform(200, 1500)); L.genes['Ja'] = [(0, 0), (a, 100), (a + int(rng.uniform(500, 3000)), int(rng.uniform(50, 90)))]
                elif kind in ('pluck', 'perc', 'bass'):
                    L.genes['Ja'] = [(0, 100), (int(rng.uniform(30, 120)), int(rng.uniform(30, 70))), (int(rng.uniform(200, 600)), 0)]
                else:
                    L.genes['Ja'] = [(0, 100), (int(rng.uniform(100, 600)), int(rng.uniform(40, 80))), (int(rng.uniform(800, 3000)), int(rng.uniform(0, 40)))]
        elif op == 'vel':
            d.glob['V'] = clampi(d.glob.get('V', 100) + rng.uniform(-20, 20), 40, 100)
        elif op == 'v3' and V3_OK:
            L.genes.update(v3_genes(c['kind'], cat, rng))
        log.append(op)
    # steps limit and length sanity
    for L in d.layers:
        L.steps = L.steps[:40]
    assign_pools(d, c['poly'])
    return d, log


V3_OK = True     # DNA v3 W (window) and Y (random) render in the pinned BASILISK 16 build (main 4bda617)
V3W = {'Pads': 3, 'Textures': 4, 'Drones/Ambient': 3, 'Lo-fi/Vaporwave': 4, 'FX/Risers': 2, 'Choir/Vox': 2,
       'Strings': 1, 'Frutiger Aero': 1}


def v3_genes(kind, cat, rng):
    """a v3 window and/or per-note randomness suited to the kind"""
    g = {}
    if kind in ('pad', 'drone', 'fx') or cat in ('Textures', 'Lo-fi/Vaporwave'):
        if rng.random() < 0.7:
            a = round(rng.uniform(0.05, 0.4), 2); b = round(a + rng.uniform(0.1, 0.3), 2)
            ln = round(rng.uniform(0.15, 0.5), 2)
            g['W'] = rng.choice(['s%.2f~%.2fl%.2f' % (a, b, ln), 's%.2f~%.2f' % (a, b), 's%.2fe%.2f' % (a, min(0.98, b + 0.3))]).replace('0.', '.')
        y = 'd%d' % int(rng.uniform(4, 25 if cat == 'Lo-fi/Vaporwave' else 14))
        if rng.random() < 0.5: y += 'l%d' % int(rng.uniform(10, 35))
        if rng.random() < 0.4: y += 'q%d' % int(rng.uniform(15, 60))
        g['Y'] = y
    else:
        y = 'd%d' % int(rng.uniform(3, 9)) + 'l%d' % int(rng.uniform(8, 25))
        if rng.random() < 0.5: y += 't%d' % int(rng.uniform(3, 15))
        g['Y'] = y
    return g


def humanize(d, cat, rng):
    """the v3 'humanized' twin of a kept preset: per-note detune, level and timing scatter on every layer"""
    d = d.copy()
    for L in d.layers:
        if L.genes.get('F'): continue
        L.genes.update(v3_genes(CATS[cat]['kind'] if cat in CATS else 'keys', cat, rng))
    return d


def retune(d, cents):
    """move K so the measured pitch class lands on the note (cents > 0: sharp -> raise K)"""
    d = d.copy()
    st = int(round(cents / 100.0))
    if st:
        d.glob['K'] = clampi(d.glob.get('K', 60) + st, 0, 127)
    return d


# ------------------------------------------------------------------ research targets
def research_cat(cat, name):
    if cat in RESEARCH_CAT: return RESEARCH_CAT[cat]
    low = ' ' + name.lower() + ' '
    for keys, c in KEYWORDS:
        if any(k in low for k in keys): return c
    return 'Pads' if 'pad' in cat else 'Keys'


def clean_dna(s):
    """drop layers whose source is unknown and I/M steps naming unknown sounds"""
    d = DNA.parse(s)
    out = []
    for L in d.layers:
        if not known(L.src): continue
        L.steps = [x for x in L.steps if not (x[:1] in 'IM' and len(x) > 1 and not known(x[1:]))]
        out.append(L)
    d.layers = out
    return d if out else None


def research_targets():
    R = os.path.join(LIB, 'research')
    T = []
    for x in json.load(open(os.path.join(R, 'preset-targets.json'))):
        d = clean_dna(x['dna'])
        if not d: continue
        T.append(dict(id='pt-' + x['id'], src='preset-targets', ref=x['name'], cat=research_cat(x['category'], x['name']),
                      seed=d.text(), character=x.get('character', ''), priority=x.get('priority', 2)))
    em = json.load(open(os.path.join(R, 'electromech-presets.json')))
    for x in em['instruments']:
        d = clean_dna(x['dna'])
        if not d: continue
        T.append(dict(id='em-' + re.sub(r'[^a-z0-9]+', '-', x['name'].lower()), src='electromech', ref=x['name'],
                      cat='Electromech', kind=EM_KIND.get(x['category'], 'keys'), seed=d.text(),
                      character=x.get('description', ''), priority=1, sub=x['category']))
    ap = os.path.expanduser('~/ws-aes/packages/basilisk-synth/design/aesthetic-presets.json')
    if os.path.exists(ap):
        for x in json.load(open(ap))['presets']:
            if x.get('needs_new_library'): continue
            d = clean_dna(x['dna'])
            if not d: continue
            T.append(dict(id='ae-' + re.sub(r'[^a-z0-9]+', '-', x['name'].lower()), src='aesthetic', ref=x['name'],
                          cat=AES_CAT.get(x['section'], 'Lo-fi/Vaporwave'), seed=d.text(), character=x.get('intent', ''),
                          priority=1, section=x['section']))
    for p in ['presets/factory.tsv']:
        for line in open(os.path.join(LIB, p)):
            if line.startswith('#') or line.count('\t') < 2: continue
            c, n, s = line.rstrip('\n').split('\t')[:3]
            if c in ('Macro', 'Collage', 'Percussion', 'Library', 'Windows 3.x'): continue
            d = clean_dna(s)
            if d: T.append(dict(id='fx-' + re.sub(r'[^a-z0-9]+', '-', n.lower()), src='factory', ref=n,
                                cat=research_cat(c.lower(), n), seed=d.text(), character='', priority=2))
    return T


V3_IDEAS = [
    {'idea': 'Drum kits from Windows clicks and electromech hits', 'needs': 'v3 kit DNA (k/j tokens: one pad per key, segments of Insert File strips)', 'from': 'electromech-presets.json kits (12), Funk & Hard drafts'},
    {'idea': 'Granular pads from long field recordings (rain, mall, NASA loops)', 'needs': 'v3 grains (position/size/spray per voice)', 'from': 'Textures, Lo-fi'},
    {'idea': 'Tape wow and flutter on hold-music chops', 'needs': 'v3 tape (pitch LFO per voice); v2 only fakes it with unison detune', 'from': 'Lo-fi/Vaporwave, Mall'},
    {'idea': 'Mono/legato leads with glide (Shakuhachi, Pan Flute, synth basses)', 'needs': 'v3 mono mode + portamento', 'from': 'preset-targets leads, bass'},
    {'idea': 'Velocity layers (soft/hard samples per key range)', 'needs': 'v3 key/velocity zones', 'from': 'electromech kits, piano'},
    {'idea': 'Round-robin clicks for typewriter/relay instruments', 'needs': 'v3 round robin', 'from': 'Electromech'},
    {'idea': 'Pitch envelopes (scoops, drops, 808 glide)', 'needs': 'v3 pitch envelope', 'from': 'Shakuhachi Hammer, 808 bass targets'},
]

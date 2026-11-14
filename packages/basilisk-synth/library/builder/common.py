"""Shared pieces of the preset-library builder: paths, the DNA v2 model (parse / format / mutate-friendly),
editions and origins (DNA.md 2.4), and the source table.

Work files (renders, MP3s, caches) live on the Linux side in $LIBBUILD (default ~/libbuild), never on C:.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)                                  # packages/basilisk-synth/library
REPO = os.path.abspath(os.path.join(LIB, '..', '..', '..'))
DATA = os.path.join(HERE, 'data')
WORK = os.environ.get('LIBBUILD', os.path.expanduser('~/libbuild'))
# BASILISK 16 local build at main 4bda617 (DNA v3 W and Y), pinned copies: its v2 renders are bit-identical to the
# 1.2.1 release machine's (checked), so one renderer serves v2 and v3 presets
# 15040db adds N (voice modes), S (stacks), D, W time (Wo Wb Wg Wt Wr Wp) and --bpm; its renders of v2 and W/Y DNAs
# are bit-identical to 4bda617's (checked), so the cached analyses stay valid
MACHINE = os.path.join(WORK, os.environ.get('LIBBUILD_V3', 'v3b'), 'machine')
RENDER311 = os.path.join(WORK, os.environ.get('LIBBUILD_V3', 'v3b'), 'render311')
RECIPE_CLI = os.path.join(WORK, 'bin', 'recipe_cli')

# core/dna.cpp kSoundNames, in index order (XPSOUNDS\X<nn>.WAV on 3.11 is index nn)
BUILTIN = ["chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada",
           "balloon", "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail",
           "hwin", "hwout", "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print",
           "xprecycle", "restore", "xpringin", "xpringout", "shutdown", "startup", "xpstart",
           "chimesxp", "chordxp", "dingxp", "tadaxp"]
W31 = {'chimes', 'chord', 'ding', 'tada'}
BOTH = {'ringin', 'ringout'}


def library_names():
    p = os.path.join(MACHINE, 'library.names.txt')
    return [l.strip() for l in open(p) if l.strip()] if os.path.exists(p) else []


def origin(name):
    if name in W31: return '3.x'
    if name in BOTH: return 'both'
    if name in BUILTIN: return 'XP'
    return 'library'


def display_name(n):
    return n[:-2] + '-xp' if n in ('chimesxp', 'chordxp', 'dingxp', 'tadaxp') else n


# ------------------------------------------------------------------ DNA v2 model
NAME = r'[a-z0-9_]+'
STEP_RE = re.compile(r'@t\d+|@\d+|[IM]' + NAME + r'|[-+<>ERCPX\[\]]')
GENE_RE = re.compile(r'W(?:[selvmobgtrp][\d.~]*)+|Y(?:[dltq]\d+|[kr])+|N(?:[mlcpgk][\dnhl]*)+|S(?:[rxpgsw][\d.x]*)+|D(?:[hbis][\d,]*)+|#\d+|T-?\d+|H-?\d+(?:,-?\d+)*|U\d+~\d+|F|L\d+|O\d+|Q-?\d+|Ja[\d,.]+|Jp[-\d,.]+')
GLOB_RE = re.compile(r'(m\d[^A-Za-z]*(?:[A-Z][-\d,.~]*)?|[A-Z]-?\d+)')


class Layer:
    __slots__ = ('src', 'steps', 'genes')

    def __init__(self, src, steps=None, genes=None):
        self.src, self.steps, self.genes = src, list(steps or []), dict(genes or {})

    def copy(self):
        return Layer(self.src, self.steps, self.genes)

    def text(self):
        g = self.genes
        out = self.src + ''.join(self.steps)
        for k in ('#', 'T', 'H', 'U', 'F', 'L', 'O', 'Q', 'Ja', 'Jp', 'W', 'N', 'S', 'Y', 'D'):
            if k not in g: continue
            v = g[k]
            if k == 'F': out += 'F'
            elif k in 'WYNSD': out += k + v
            elif k == 'H': out += 'H' + ','.join(str(int(x)) for x in v)
            elif k == 'U': out += 'U%d~%d' % v
            elif k in ('Ja', 'Jp'): out += k + '.'.join('%d,%d' % (int(t), int(l)) for t, l in v)
            elif k == 'T' and int(v) == 0: continue
            else: out += '%s%d' % (k, int(v))
        return out

    def names(self):
        return [self.src] + [s[1:] for s in self.steps if s[:1] in 'IM' and len(s) > 1]


class DNA:
    def __init__(self, layers=None, glob=None, macros=''):
        self.layers, self.glob, self.macros = layers or [], dict(glob or {}), macros

    @staticmethod
    def parse(s):
        body, _, gl = s.partition(';')
        layers = []
        for ltxt in body.split('/'):
            m = re.match(NAME, ltxt)
            if not m: continue
            L = Layer(m.group(0))
            p = m.end()
            while p < len(ltxt):
                mg = GENE_RE.match(ltxt, p)
                ms = STEP_RE.match(ltxt, p)
                # a gene letter never starts a step except none overlap; steps use [-+<>ERCPX[]@IM]
                if ms and (not mg or ltxt[p] in '@IM-+<>ERCPX[]'):
                    L.steps.append(ms.group(0)); p = ms.end(); continue
                if mg:
                    t = mg.group(0)
                    if t[0] in 'WYNSD': L.genes[t[0]] = L.genes.get(t[0], '') + t[1:]
                    elif t == 'F': L.genes['F'] = True
                    elif t[0] == '#': L.genes['#'] = int(t[1:])
                    elif t[0] == 'H': L.genes['H'] = [int(x) for x in t[1:].split(',')]
                    elif t[0] == 'U': a, b = t[1:].split('~'); L.genes['U'] = (int(a), int(b))
                    elif t[:2] in ('Ja', 'Jp'):
                        pts = []
                        for pr in t[2:].split('.'):
                            if ',' in pr:
                                a, b = pr.split(',')[:2]
                                if a and b: pts.append((int(a), int(b)))
                        L.genes[t[:2]] = pts
                    else: L.genes[t[0]] = int(t[1:])
                    p = mg.end(); continue
                p += 1
            layers.append(L)
        glob, macros = {}, ''
        for tok in GLOB_RE.findall(gl):
            if tok.startswith('m'): macros += tok
            else: glob[tok[0]] = int(tok[1:])
        return DNA(layers, glob, macros)

    def text(self):
        s = '/'.join(L.text() for L in self.layers)
        g = ''.join('%s%d' % (k, self.glob[k]) for k in 'ADSRBVKG' if k in self.glob)
        g += self.macros
        return s + (';' + g if g else '')

    def copy(self):
        return DNA([L.copy() for L in self.layers], self.glob, self.macros)

    def names(self):
        return [n for L in self.layers for n in L.names()]


def dna_names(s):
    return DNA.parse(s).names()


def edition(s):
    """DNA.md 2.4: 'xp' when the DNA uses any XP file, else 'w31' (library sounds do not count)"""
    return 'xp' if any(origin(n) == 'XP' for n in dna_names(s)) else 'w31'


def uses_v3(s):
    return any(k in L.genes for L in DNA.parse(s).layers for k in 'WYNSD')


def origins(s):
    return sorted(set(origin(n) for n in dna_names(s)))


def load_json(name, default=None):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def save_json(name, obj, indent=1):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), 'w', newline='\n') as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)
        f.write('\n')

"""CITYPOP DEPROGRAMMED: the album's arranging kit, shared by every track script in this folder.

Each track is one script that writes its .mid and .song beside itself (tools/songrender/README.md has the format);
`finish()` does that. Everything here is plain MIDI writing: harmony with extended chords and voice leading, the
comping, bass and drum styles of the record, the theme and its transformations, and a seeded humaniser. All
randomness is seeded, so every script always writes the same file.

The theme (in C; each track moves it): an eight-bar A phrase over Fmaj7 Em7 A7 Dm9 G13 Fmaj7 E7#9 Am9 D9 Dm9 G13, a
pick-up figure G C D E (5 1 2 3) that leaps to the sixth, and an eight-bar B phrase that drifts through Bbmaj7 and
Abmaj7 and comes home on Cmaj9.
"""
import itertools, json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'songrender'))
from compose import Score, Part, pitch, write_song   # noqa: E402,F401

PACK = 'rainy-loft'
ALBUM = 'CITYPOP DEPROGRAMMED'
ARTIST = 'Algorithmic Industries'

# ------------------------------------------------------------------------------------------------ harmony
PCS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
Q = {   # chord quality -> intervals above the root (extensions included; voicings choose among them)
    '': [0, 4, 7], 'maj': [0, 4, 7], 'm': [0, 3, 7], '5': [0, 7],
    'maj7': [0, 4, 7, 11], 'maj9': [0, 4, 7, 11, 14], 'maj7#11': [0, 4, 7, 11, 14, 18], 'maj13': [0, 4, 7, 11, 14, 21],
    '6': [0, 4, 7, 9], '69': [0, 4, 7, 9, 14], 'add9': [0, 4, 7, 14],
    'm7': [0, 3, 7, 10], 'm9': [0, 3, 7, 10, 14], 'm11': [0, 3, 7, 10, 14, 17], 'm6': [0, 3, 7, 9], 'm69': [0, 3, 7, 9, 14],
    'mmaj7': [0, 3, 7, 11], 'mmaj9': [0, 3, 7, 11, 14], 'madd9': [0, 3, 7, 14],
    '7': [0, 4, 7, 10], '9': [0, 4, 7, 10, 14], '13': [0, 4, 7, 10, 14, 21], '7b9': [0, 4, 7, 10, 13],
    '7#9': [0, 4, 7, 10, 15], '7#11': [0, 4, 7, 10, 14, 18], '7b13': [0, 4, 7, 10, 14, 20], '7alt': [0, 4, 10, 13, 15, 20],
    '13b9': [0, 4, 10, 13, 21], '7sus4': [0, 5, 7, 10], '9sus4': [0, 5, 7, 10, 14], '13sus4': [0, 5, 10, 14, 21],
    'sus2': [0, 2, 7], 'sus4': [0, 5, 7], 'm7b5': [0, 3, 6, 10], 'm9b5': [0, 3, 6, 10, 14], 'dim7': [0, 3, 6, 9],
    'aug': [0, 4, 8], 'maj7#5': [0, 4, 8, 11],
}
# which chord members a 4-note rootless voicing prefers, in order (by interval above the root, mod 12)
PREF = [4, 3, 10, 11, 2, 9, 5, 1, 6, 8, 7]


def parse(sym):
    """'Ebmaj9/G' -> (root pc, intervals, bass pc)"""
    bass = None
    if '/' in sym:
        sym, b = sym.split('/')
        bass = (PCS[b[0]] + b[1:].count('#') - b[1:].count('b')) % 12
    m = re.match(r'^([A-G])([#b]?)(.*)$', sym)
    if not m:
        raise ValueError(sym)
    root = (PCS[m.group(1)] + (1 if m.group(2) == '#' else -1 if m.group(2) == 'b' else 0)) % 12
    q = m.group(3)
    if q not in Q:
        raise ValueError(f'chord quality {sym!r}')
    return root, Q[q], root if bass is None else bass


def tones(sym, n=4, rootless=True):
    """the pitch classes of a voicing of n notes"""
    root, iv, _ = parse(sym)
    ivs = sorted(set(i % 12 for i in iv), key=lambda i: PREF.index(i) if i in PREF else 99)
    if not rootless:
        ivs = [0] + [i for i in ivs if i != 0]
    ivs = [i for i in ivs if not (i == 7 and len(ivs) > n and rootless)] or ivs
    pcs = [(root + i) % 12 for i in ivs[:n]]
    return pcs


def voice(pcs, prev=None, lo=52, hi=76, spread=(5, 16)):
    """voice pitch classes in lo..hi, nearest to prev (small motion), avoiding minor ninths and clusters"""
    cands = []
    for pc in pcs:
        c = [n for n in range(lo, hi + 1) if n % 12 == pc]
        cands.append(c or [pc + 12 * 5])
    best, bs = None, 1e9
    centre = (sum(prev) / len(prev)) if prev else (lo + hi) / 2
    for combo in itertools.product(*cands):
        ns = sorted(combo)
        if len(set(ns)) < len(ns):
            continue
        span = ns[-1] - ns[0]
        s = 0.0
        if span < spread[0] or span > spread[1]:
            s += 6 + abs(span - sum(spread) / 2)
        for a, b in itertools.combinations(ns, 2):
            if (b - a) in (1, 13) or (b - a) == 25:
                s += 5
        seconds = sum(1 for a, b in zip(ns, ns[1:]) if b - a <= 2)
        s += 2.5 * max(0, seconds - 1)
        if prev:
            pv = sorted(prev)
            s += sum(min(abs(n - p) for p in pv) for n in ns) * 0.6
        else:
            s += abs(sum(ns) / len(ns) - centre) * 0.4
        if s < bs:
            best, bs = ns, s
    return best


def prog(text, at=0.0, bar=4.0):
    """'Fmaj7 | Em7 A7 | G13:3 Db9:1' -> [(start, beats, sym)]; chords in a bar share it evenly unless timed"""
    out, t = [], float(at)
    for b in text.split('|'):
        syms = b.split()
        if not syms:
            continue
        timed = [s for s in syms if ':' in s]
        rest = bar - sum(float(s.split(':')[1]) for s in timed)
        free = [s for s in syms if ':' not in s]
        each = rest / len(free) if free else 0
        for s in syms:
            if ':' in s:
                sym, d = s.split(':'); d = float(d)
            else:
                sym, d = s, each
            if sym not in ('-', '%'):
                out.append((t, d, sym))
            elif sym == '%' and out:
                out.append((t, d, out[-1][2]))
            t += d
    return out


def transpose_sym(sym, n):
    names = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

    def tr(m):
        pc = (PCS[m.group(1)] + (1 if m.group(2) == '#' else -1 if m.group(2) == 'b' else 0) + n) % 12
        return names[pc]
    parts = sym.split('/')
    parts = [re.sub(r'^([A-G])([#b]?)', tr, p) for p in parts]
    return '/'.join(parts)


def tprog(text, n):
    """transpose a progression text by n semitones"""
    return ' '.join(transpose_sym(t, n) if re.match(r'^[A-G]', t) else t for t in text.split())


def span(ch):
    return max(s + d for s, d, _ in ch) if ch else 0.0


# ------------------------------------------------------------------------------------------------ humanising
class Feel:
    """a seeded humaniser applied per part at the end: lay-back (ms), jitter (ms), velocity jitter, swing (0..1 of a
    sixteenth or eighth)"""
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def apply(self, S, part, lay_ms=0.0, jit_ms=6.0, vel=5, swing=0.0, grid=0.5, bpm=None):
        bpm = bpm or S.tempos[0][1]
        spb = 60.0 / bpm
        out = []
        for b, n, d, v in part.notes:
            bb = b
            if swing:
                k = b / grid
                if abs(k - round(k)) < 1e-3 and int(round(k)) % 2 == 1:
                    bb = b + swing * grid * 0.5
            bb += (lay_ms + self.rng.uniform(-jit_ms, jit_ms)) / 1000.0 / spb
            out.append((max(0.0, bb), n, d, int(max(1, min(127, v + self.rng.randint(-vel, vel))))))
        part.notes = out


# ------------------------------------------------------------------------------------------------ keys
COMP = {   # comping rhythms: (offset in beats, length, velocity scale) within a 4-beat bar
    'ballad': [(0, 3.6, 1.0)],
    'halves': [(0, 1.8, 1.0), (2, 1.8, 0.9)],
    'lofi': [(0, 1.4, 1.0), (1.75, 0.6, 0.8), (2.5, 1.3, 0.92)],
    'citypop': [(0, 0.45, 1.0), (0.75, 0.4, 0.82), (1.5, 0.9, 0.95), (2.75, 0.4, 0.8), (3.5, 0.45, 0.9)],
    'citypop2': [(0, 1.2, 1.0), (1.5, 0.4, 0.8), (2.5, 0.45, 0.9), (3.25, 0.6, 0.85)],
    'bossa': [(0, 0.9, 1.0), (1.5, 0.9, 0.85), (3, 0.45, 0.9)],
    'disco': [(0.5, 0.3, 0.9), (1.5, 0.3, 0.9), (2.5, 0.3, 0.9), (3.5, 0.3, 0.95)],
    'stabs': [(0, 0.3, 1.0), (1.75, 0.25, 0.85), (2.5, 0.3, 0.9)],
    'waltz': [(1, 0.8, 0.85), (2, 0.8, 0.8)],
    'shuffle': [(0, 0.6, 1.0), (1.66, 0.3, 0.8), (2.66, 0.6, 0.9), (3.66, 0.3, 0.8)],
}


def comp(part, chords, style='citypop', vel=70, lo=53, hi=74, n=4, push=True, bar=4.0, rootless=True, rng=None,
         var=0.0):
    """chord hits in a rhythm; push: a chord that starts a bar is anticipated by a sixteenth (tied in), as city pop
    keyboards do; var: chance per hit of being left out (for air)"""
    rng = rng or random.Random(len(chords))
    prev = None
    pat = COMP[style] if isinstance(style, str) else style
    for i, (s, d, sym) in enumerate(chords):
        ns = voice(tones(sym, n, rootless), prev, lo, hi); prev = ns
        # the hits of the pattern that fall in this chord's span (pattern restarts every bar)
        t0 = s
        bar0 = math.floor(s / bar + 1e-6) * bar
        k = 0
        while bar0 + k * bar < s + d - 1e-6:
            for off, ln, vs in pat:
                t = bar0 + k * bar + off
                if t < s - 1e-6 or t >= s + d - 1e-6:
                    continue
                if var and rng.random() < var and t > s + 1e-6:
                    continue
                ln2 = min(ln, s + d - t)
                if push and abs(t - s) < 1e-6 and s > 0.1 and (s % bar) < 1e-6 and i > 0:
                    t -= 0.25; ln2 += 0.25   # anticipation
                for j, nn in enumerate(ns):
                    part.note(t + j * 0.004, nn, ln2 * 0.96, int(vel * vs) - (3 if j == 0 else 0))
            k += 1
    return prev


def sustain(part, chords, vel=60, lo=55, hi=79, n=4, rootless=True, gap=0.05):
    prev = None
    for s, d, sym in chords:
        ns = voice(tones(sym, n, rootless), prev, lo, hi, spread=(7, 19)); prev = ns
        for nn in ns:
            part.note(s, nn, d - gap, vel)


def arp(part, chords, step=0.5, vel=64, lo=60, hi=88, n=4, pattern=(0, 1, 2, 3, 2, 1), gate=1.5, oct_up=True):
    prev = None
    for s, d, sym in chords:
        ns = voice(tones(sym, n, True), prev, lo, hi - 12); prev = ns
        seq = list(ns) + ([ns[0] + 12] if oct_up else [])
        k = 0
        while k * step < d - 1e-6:
            idx = pattern[k % len(pattern)] % len(seq)
            part.note(s + k * step, seq[idx], step * gate, vel - (6 if k % 2 else 0))
            k += 1


# ------------------------------------------------------------------------------------------------ bass
def root(sym, octave=2):
    r, _, b = parse(sym)
    return 12 * (octave + 1) + b


def chord_pc(sym, iv):
    r, ivs, _ = parse(sym)
    return (r + iv) % 12


def near(pc, ref):
    """the pitch of pitch class pc nearest ref"""
    c = ref - ((ref - pc) % 12)
    return c if ref - c <= 6 else c + 12


BASS = {   # (offset, what, length, velocity scale); what: 'R' root, '5', '8' octave, '3', '7', 'A' approach to next
    'ballad': [(0, 'R', 3.5, 1.0), (3.5, 'A', 0.5, 0.75)],
    'fretless': [(0, 'R', 1.5, 1.0), (1.5, '5', 1.0, 0.8), (2.5, '8', 0.75, 0.75), (3.25, '5', 0.5, 0.7), (3.75, 'A', 0.25, 0.7)],
    'citypop': [(0, 'R', 0.7, 1.0), (0.75, 'R', 0.2, 0.6), (1.5, '8', 0.4, 0.8), (2, '5', 0.45, 0.85), (2.5, 'R', 0.7, 0.9),
                (3.25, '8', 0.2, 0.7), (3.5, '5', 0.3, 0.75), (3.75, 'A', 0.25, 0.7)],
    'slap': [(0, 'R', 0.4, 1.0), (0.5, '8', 0.2, 0.9), (0.75, 'R', 0.2, 0.55), (1.5, 'R', 0.3, 0.8), (2, '8', 0.2, 0.95),
             (2.5, 'R', 0.4, 0.85), (3, '7', 0.2, 0.75), (3.5, '8', 0.2, 0.9), (3.75, 'A', 0.2, 0.7)],
    'disco': [(0, 'R', 0.4, 1.0), (0.5, '8', 0.4, 0.9), (1, 'R', 0.4, 0.95), (1.5, '8', 0.4, 0.9), (2, 'R', 0.4, 0.95),
              (2.5, '8', 0.4, 0.9), (3, 'R', 0.4, 0.95), (3.5, '8', 0.3, 0.9)],
    'bossa': [(0, 'R', 1.4, 1.0), (1.5, '5', 0.5, 0.8), (2, '5', 1.4, 0.85), (3.5, 'R', 0.5, 0.75)],
    'lofi': [(0, 'R', 1.4, 1.0), (1.5, 'R', 0.4, 0.7), (2.75, '5', 0.7, 0.8), (3.5, 'A', 0.5, 0.7)],
    'waltz': [(0, 'R', 0.9, 1.0), (2, '5', 0.9, 0.7)],
    'shuffle': [(0, 'R', 0.6, 1.0), (0.66, 'R', 0.3, 0.6), (1, '5', 0.6, 0.8), (2, '8', 0.6, 0.85), (2.66, '7', 0.3, 0.6),
                (3, '5', 0.6, 0.8), (3.66, 'A', 0.3, 0.7)],
    'pedal': [(0, 'R', 3.9, 1.0)],
}


def bassline(part, chords, style='citypop', vel=96, octave=2, bar=4.0, rng=None, var=0.0, lo=28, hi=52):
    rng = rng or random.Random(7)
    pat = BASS[style] if isinstance(style, str) else style
    for i, (s, d, sym) in enumerate(chords):
        r = root(sym, octave)
        while r > hi - 12:
            r -= 12
        while r < lo:
            r += 12
        third = 3 if 3 in parse(sym)[1] else 4
        sev = 11 if 11 in parse(sym)[1] else 10
        nxt = chords[i + 1][2] if i + 1 < len(chords) else sym
        bar0 = math.floor(s / bar + 1e-6) * bar
        k = 0
        while bar0 + k * bar < s + d - 1e-6:
            for off, w, ln, vs in pat:
                t = bar0 + k * bar + off
                if t < s - 1e-6 or t >= s + d - 1e-6:
                    continue
                if var and rng.random() < var and w not in ('R',):
                    continue
                if w == 'A':
                    if t + ln < s + d - 1e-6 and d > 2:   # approach only into the next chord
                        w = '5'
                    else:
                        tgt = near(root(nxt, octave) % 12, r)
                        n = tgt + rng.choice((-1, 1, -2)) if rng.random() < 0.8 else tgt + 7
                        part.note(t, n, min(ln, s + d - t) * 0.9, int(vel * vs)); continue
                n = {'R': r, '5': r + 7, '8': r + 12, '3': r + third, '7': r + sev}[w]
                if n > hi:
                    n -= 12
                part.note(t, n, min(ln, s + d - t) * 0.95, int(vel * vs))
            k += 1


# ------------------------------------------------------------------------------------------------ drums
KICK, RIM, SNARE, CLAP, SNARE2, LTOM, CHH, LTOM2, PHH, MTOM, OHH, MTOM2, HTOM, CRASH, HTOM2, RIDE = \
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51
CABASA, TAMB, COWBELL, SNAP, SHAKER, TRI, CONGA_HI, CONGA_LO, GUIRO, BELL = 52, 54, 56, 57, 58, 59, 62, 63, 60, 53

GROOVE = {   # 16 steps a bar; X accent, x hit, o ghost, g faint ghost
    'citypop': {KICK: 'x.....x...x.....', SNARE: '....X.......X...', CHH: 'x.x.x.x.x.x.x.x.', PHH: '.o.o.o.o.o.o.o.o', OHH: '..............x.',
                SNARE2: '.......g.g....g.'},
    'citypop2': {KICK: 'x..x..x...x..x..', SNARE: '....X.......X...', CHH: 'xoxoxoxoxoxoxoxo', OHH: '......x.......x.', SNARE2: '..g....g.g.g....'},
    'ballad': {KICK: 'x.........x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'},
    'brush': {KICK: 'x.........x.....', SNARE: '....x.......x...', SNARE2: 'o.oo.oo.o.oo.oo.', PHH: '....x.......x...'},
    'lofi': {KICK: 'x......x..x.....', SNARE: '....X.......X...', CHH: 'x.x.x.x.x.x.x.x.', SNARE2: '..........g....g'},
    'bossa': {KICK: 'x..xx..xx..xx..x', RIM: 'x..x..x...x..x..', CHH: 'xxxxxxxxxxxxxxxx'},
    'disco': {KICK: 'x...x...x...x...', SNARE: '....X.......X...', OHH: '..x...x...x...x.', CHH: 'x.o.x.o.x.o.x.o.', CLAP: '....x.......x...'},
    'boogie': {KICK: 'x...x...x...x..o', SNARE: '....X.......X...', CHH: 'xoxoxoxoxoxoxoxo', OHH: '..............x.', CLAP: '....x.......x...'},
    'shuffle': {KICK: 'x.....x.x.......', SNARE: '....X.......X...', CHH: 'x.x.x.x.x.x.x.x.', SNARE2: '..g....g..g...g.'},
    'halftime': {KICK: 'x......x........', SNARE: '........X.......', CHH: 'x.x.x.x.x.x.x.x.', SNARE2: '......g.....g...'},
    'train': {KICK: 'x.....x.x.....x.', SNARE: '....X.......X...', CHH: 'xxxxxxxxxxxxxxxx', SNARE2: '.g.g...g.g.g...g'},
}
VEL = {'X': 112, 'x': 92, 'o': 52, 'g': 34}


def drums(part, style, at, bars, vel=1.0, swing=0.0, drop=(), extra=None, ghost_rng=None, var=0.12, bar=4.0, steps=16, swing8=0.0):
    """a groove for `bars` bars with seeded variation: ghosts and hat accents move a little from bar to bar"""
    rng = ghost_rng or random.Random(int(at * 7) + bars)
    pads = {k: v for k, v in GROOVE[style].items() if k not in drop} if isinstance(style, str) else dict(style)
    if extra:
        pads.update(extra)
    step = bar / steps
    for b in range(bars):
        for n, pat in pads.items():
            pat = pat.replace(' ', '')
            for k in range(steps):
                c = pat[k % len(pat)]
                if c == '.':
                    if n in (SNARE2,) and rng.random() < var * 0.3:
                        c = 'g'
                    else:
                        continue
                elif c in 'og' and rng.random() < var:
                    continue
                v = VEL[c] + rng.randint(-6, 6)
                if n in (CHH, PHH) and k % 4 == 0:
                    v += 8
                t = at + b * bar + k * step + (swing * step if k % 2 else 0) + (swing8 * 2 * step if k % 4 == 2 else 0)
                part.note(t, n, step * 0.9, int(v * vel))
    return at + bars * bar


def fill(part, at, kind='snare', vel=1.0, beats=1.0):
    """a fill in the last `beats` beats before `at`"""
    t0 = at - beats
    if kind == 'snare':
        seq = [(0, SNARE2, 50), (0.25, SNARE2, 62), (0.5, SNARE, 80), (0.75, SNARE, 96)]
    elif kind == 'toms':
        seq = [(0, HTOM, 90), (0.25, HTOM, 80), (0.5, MTOM, 92), (0.75, LTOM, 100)]
    elif kind == 'flam':
        seq = [(0.5, SNARE2, 60), (0.52, SNARE, 100)]
    elif kind == 'roll':
        seq = [(k * 0.125, SNARE2 if k % 2 else SNARE, 40 + k * 8) for k in range(8)]
    else:
        seq = [(0.5, CLAP, 90), (0.75, CLAP, 100)]
    sc = beats / 1.0
    for o, n, v in seq:
        part.note(t0 + o * sc, n, 0.2, int(v * vel))


# ------------------------------------------------------------------------------------------------ the theme
THEME_A = [   # (beat, pitch, length) in C; 8 bars
    (0.5, 'G4', 0.5), (1.0, 'C5', 0.5), (1.5, 'D5', 0.5), (2.0, 'E5', 1.5), (3.5, 'G5', 0.5),
    (4.0, 'A5', 1.0), (5.0, 'G5', 0.5), (5.5, 'E5', 0.5), (6.0, 'D5', 1.0), (7.0, 'C#5', 1.0),
    (8.0, 'D5', 0.5), (8.5, 'E5', 0.5), (9.0, 'F5', 0.5), (9.5, 'A5', 0.5), (10.0, 'C6', 1.0), (11.0, 'A5', 1.0),
    (12.0, 'G5', 1.5), (13.5, 'E5', 0.5), (14.0, 'F5', 0.5), (14.5, 'D5', 0.5), (15.0, 'B4', 1.0),
    (16.5, 'G4', 0.5), (17.0, 'C5', 0.5), (17.5, 'D5', 0.5), (18.0, 'E5', 1.5), (19.5, 'A5', 0.5),
    (20.0, 'G#5', 1.0), (21.0, 'G5', 0.5), (21.5, 'F5', 0.5), (22.0, 'E5', 1.0), (23.0, 'D5', 0.5), (23.5, 'B4', 0.5),
    (24.0, 'C5', 1.5), (25.5, 'B4', 0.5), (26.0, 'A4', 0.5), (26.5, 'F#4', 0.5), (27.0, 'E4', 0.5), (27.5, 'F#4', 0.5),
    (28.0, 'A4', 1.0), (29.0, 'G4', 0.5), (29.5, 'F4', 0.5), (30.0, 'E4', 2.0),
]
CHORDS_A = 'Fmaj7 | Em7 A7 | Dm9 | G13 | Fmaj7 | E7#9 | Am9 D9 | Dm9 G13'
THEME_B = [
    (0.0, 'D5', 1.5), (1.5, 'C5', 0.5), (2.0, 'D5', 1.0), (3.0, 'F5', 1.0),
    (4.0, 'E5', 2.0), (6.0, 'F#5', 1.0), (7.0, 'A5', 1.0),
    (8.0, 'Bb5', 1.5), (9.5, 'A5', 0.5), (10.0, 'F5', 1.0), (11.0, 'D5', 1.0),
    (12.0, 'E5', 2.0), (14.0, 'A5', 0.5), (14.5, 'G5', 0.5), (15.0, 'E5', 1.0),
    (16.0, 'Eb5', 1.5), (17.5, 'C5', 0.5), (18.0, 'G5', 2.0),
    (20.0, 'F5', 1.5), (21.5, 'D5', 0.5), (22.0, 'B4', 1.0), (23.0, 'D5', 1.0),
    (24.0, 'E5', 2.0), (26.0, 'D5', 0.5), (26.5, 'C5', 0.5), (27.0, 'G4', 1.0),
    (28.0, 'D5', 2.0), (30.0, 'E5', 2.0),
]
CHORDS_B = 'Bbmaj7 | Am7 D7 | Gm9 | C13 | Abmaj7 | G7sus4 G7 | Cmaj9 | Cmaj9'
HEAD = THEME_A[:5]   # the pick-up figure and the held third: the motto
CAPRICE = [(0.0, 'A4', 0.5), (0.5, 'A4', 0.25), (0.75, 'C5', 0.25), (1.0, 'B4', 0.25), (1.25, 'A4', 0.25), (1.5, 'E5', 0.5),
           (2.0, 'E4', 0.5)]   # Paganini, Caprice No. 24 (1817, public domain): its first figure, for one wink
C_MAJOR = [0, 2, 4, 5, 7, 9, 11]


def mel(notes, tr=0):
    """theme tuples with names -> (beat, midi, length)"""
    return [(b, pitch(p) + tr if isinstance(p, str) else p + tr, d) for b, p, d in notes]


def shift(notes, beats):
    return [(b + beats, p, d) for b, p, d in notes]


def augment(notes, f):
    return [(b * f, p, d * f) for b, p, d in notes]


def modal(notes, mapping):
    """{pitch class: new pitch class offset}, e.g. to C minor: {4: -1, 9: -1, 11: -1}"""
    return [(b, p + mapping.get(p % 12, 0), d) for b, p, d in notes]


TO_MINOR = {4: -1, 9: -1, 11: -1}       # C major -> C natural minor (Eb, Ab, Bb)
TO_DORIAN = {4: -1, 11: -1}
TO_LYDIAN = {5: 1}


def invert(notes, axis='E5', scale=C_MAJOR):
    """diatonic inversion around axis (the leaps of the theme turned upside down); chromatic notes move by semitone"""
    ax = pitch(axis)

    def deg(p):
        o, pc = divmod(p, 12)
        if pc in scale:
            return o * 7 + scale.index(pc), 0
        return o * 7 + scale.index((pc - 1) % 12), 1
    a, _ = deg(ax)
    out = []
    for b, p, d in notes:
        dg, acc = deg(p)
        nd = 2 * a - dg
        o, k = divmod(nd, 7)
        out.append((b, o * 12 + scale[k] - acc, d))
    return out


def retro(notes):
    end = max(b + d for b, p, d in notes)
    return sorted((end - b - d, p, d) for b, p, d in notes)


def play(part, notes, at=0.0, vel=88, gate=0.94, shape=True, accent_long=True, tr=0, legato=False):
    """place a melody: phrase-shaped velocity (rises to the highest note of each bar group), long notes a little
    louder; legato makes each note touch the next (a glide on legato presets)"""
    if not notes:
        return at
    hi = max(p for _, p, _ in notes)
    lo = min(p for _, p, _ in notes)
    ns = sorted(notes)
    for i, (b, p, d) in enumerate(ns):
        v = vel
        if shape and hi > lo:
            v += int(10 * (p - lo) / (hi - lo)) - 5
        if accent_long and d >= 1.5:
            v += 4
        g = gate
        if legato and i + 1 < len(ns) and ns[i + 1][0] - (b + d) < 0.05:
            dd = ns[i + 1][0] - b + 0.06
        else:
            dd = d * g
        part.note(at + b, p + tr, dd, v)
    return at + max(b + d for b, p, d in notes)


def grace(notes, every=3, below=1, length=0.06, rng=None):
    """little grace notes (a slide into a note from a semitone or a tone below), on some long notes"""
    rng = rng or random.Random(3)
    out = []
    for i, (b, p, d) in enumerate(notes):
        if d >= 1.0 and i % every == 0 and b >= length:
            out.append((b - length, p - (below if rng.random() < 0.6 else 2), length))
        out.append((b, p, d))
    return out


# ------------------------------------------------------------------------------------------------ texture
def texture(part, at, beats, note=60, vel=80, every=None, bpm=84.0, seconds=24.0, overlap=1.0):
    """a long ambience as back-to-back notes of a sample's length (the release crossfades the joins)"""
    every = every or seconds * bpm / 60.0
    t, end = float(at), float(at) + beats
    while t < end - 1e-3:
        d = min(every, end - t)
        part.note(t, note, d + overlap, vel)
        t += every
    return end


def fade(part, t0, t1, v0, v1):
    """scale the velocities of notes in [t0, t1) linearly from v0 to v1 (0..1 multipliers)"""
    out = []
    for b, n, d, v in part.notes:
        if t0 <= b < t1:
            f = v0 + (v1 - v0) * (b - t0) / max(1e-6, t1 - t0)
            v = int(max(1, min(127, v * f)))
        out.append((b, n, d, v))
    part.notes = out


# ------------------------------------------------------------------------------------------------ output
def tuning():
    tj = os.path.join(REPO, 'packages', 'basilisk-synth', 'library', 'songs', 'tuning.json')
    t = json.load(open(tj)) if os.path.exists(tj) else {}
    aj = os.path.join(HERE, 'tuning.json')
    if os.path.exists(aj):
        t.update(json.load(open(aj)))
    return t


def finish(script, S, header, tracks, master=None, echo=None, reverb=None):
    base = os.path.splitext(os.path.abspath(script))[0]
    S.write(base + '.mid')
    header = dict(header)
    header.setdefault('pack', PACK)
    header.setdefault('kind', 'original')
    header.setdefault('album', ALBUM)
    header.setdefault('composer', 'Algorithmic Industries (an original for SNDWAVE2000)')
    header.setdefault('licence', 'CC0-1.0 (the composition and this arrangement)')
    tun = tuning()
    fixed = []
    for name, src, preset, kv in tracks:
        if 'tune' not in kv and not preset.startswith('dna:'):
            key = preset if ':' in preset else header['pack'] + ':' + preset
            if key in tun:
                kv['tune'] = tun[key]
        fixed.append((name, src, preset, kv))
    header['midi'] = os.path.basename(base) + '.mid'
    header.setdefault('script', os.path.basename(script))
    write_song(base + '.song', header, fixed, master or {'loudness': -16, 'ceiling': -1.0},
               echo, reverb)
    print(base + '.song')


# ------------------------------------------------------------------------------------------------ solos
RHYTHMS = [   # one-bar rhythm cells for improvised lines: (offset, length); the theme's own cells first
    [(0.5, 0.5), (1.0, 0.5), (1.5, 0.5), (2.0, 1.5), (3.5, 0.5)],
    [(0.0, 1.0), (1.0, 0.5), (1.5, 0.5), (2.0, 1.0), (3.0, 1.0)],
    [(0.0, 0.5), (0.5, 0.5), (1.0, 0.5), (1.5, 0.5), (2.0, 2.0)],
    [(0.0, 1.5), (1.5, 0.5), (2.5, 0.5), (3.0, 1.0)],
    [(0.25, 0.25), (0.5, 0.25), (0.75, 0.75), (1.5, 0.5), (2.0, 0.5), (2.5, 0.5), (3.0, 0.75)],
    [(0.0, 0.33), (0.33, 0.33), (0.67, 0.33), (1.0, 1.0), (2.5, 0.5), (3.0, 1.0)],
    [(1.0, 0.5), (1.5, 0.5), (2.0, 0.5), (2.5, 1.5)],
    [(0.0, 3.0)],
]


def scale_of(sym, key_pcs):
    """the notes a line may use over a chord: the chord's own tones first, then the key's"""
    r, iv, _ = parse(sym)
    ct = sorted(set((r + i) % 12 for i in iv))
    return ct, sorted(set(key_pcs) | set(ct))


def improvise(chords, key_pcs, seed=1, lo=60, hi=84, density=0.7, start=None, cells=None, bar=4.0, motif=None):
    """a melodic line over chords: chord tones on strong beats, stepwise passing tones in between, contour that
    rises and falls over four bars, the album's rhythm cells; motif: (beat, midi, len) placed at the start"""
    rng = random.Random(seed)
    out = list(motif or [])
    cur = start or (lo + hi) // 2
    t_end = span(chords)
    t0 = chords[0][0]
    nb = int(round((t_end - t0) / bar))
    for b in range(nb):
        bt = t0 + b * bar
        if motif and bt < max(x[0] + x[2] for x in motif) - 1e-6:
            continue
        if rng.random() > density and b % 4 == 3:
            continue   # a breath
        cell = rng.choice(cells or RHYTHMS)
        phase = (b % 4) / 3.0
        target = lo + (hi - lo) * (0.35 + 0.45 * math.sin(math.pi * phase))
        for off, ln in cell:
            t = bt + off
            sym = next((s for s0, d, s in chords if s0 <= t < s0 + d), chords[-1][2])
            ct, sc = scale_of(sym, key_pcs)
            strong = abs(off - round(off)) < 1e-6 and int(round(off)) % 2 == 0 or ln >= 1.0
            pool = ct if strong else sc
            cands = [n for n in range(lo, hi + 1) if n % 12 in pool]
            def cost(n):
                return abs(n - cur) * (1.0 if strong else 1.6) + 0.25 * abs(n - target) + rng.random() * 2.2 + (3 if n == cur else 0)
            n = min(cands, key=cost)
            out.append((t - chords[0][0] + chords[0][0], n, ln))
            cur = n
    return sorted(out)

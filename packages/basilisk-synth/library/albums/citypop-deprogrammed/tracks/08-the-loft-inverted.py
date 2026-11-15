"""8. Var. VII: The Loft, Inverted. D-flat major, 66 bpm: the slow heart of the record. The theme turned upside down
(every interval mirrored around its third), so the pick-up that rose now falls: 1 6 5 3. Re-harmonised for the new
line, on a soft piano alone, then violins with a cello line under them, the choir, and a climax a tone higher with
the horns before the piano is left alone again."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 1                        # D-flat
BPM = 66
S = Score(bpm=BPM, seed=808)
piano = S.part('piano', 1); vln = S.part('violins', 2); cello = S.part('cellos', 3); choir = S.part('choir', 4)
harp = S.part('harp', 5); horn = S.part('horns', 6); bass = S.part('bass', 7); glass = S.part('glass', 8)
flute = S.part('flute', 9); kit = S.part('kit', 10); rain = S.part('rain', 13)
rng = random.Random(88)

IA = invert(mel(THEME_A, 0), 'E5')
IA = [(b, 79 if p == 78 else p, d) for b, p, d in IA]          # bar 2's F#5 becomes G5 (the new harmony wants it)
IB = invert(mel(THEME_B, 0), 'E5')
IA_CH = 'Cmaj9 | Em7 Fmaj9 | Dm11 G13 | Am9 Fmaj7 | Cmaj9 | Em7 Dm9 | Em9 A7 | Dm9 G13'
IB_CH = 'Dm9 | Em7 A7 | Gm9 G7 | Cmaj9 | Am9 | Bbmaj7 | Em7 F6 | Dm9/G G13'
CELLO = [(0, 'E3', 4), (4, 'G3', 2), (6, 'A3', 2), (8, 'F3', 2), (10, 'D3', 2), (12, 'E3', 2), (14, 'C3', 2), (16, 'E3', 4),
         (20, 'G3', 2), (22, 'F3', 2), (24, 'B2', 2), (26, 'C#3', 2), (28, 'A2', 2), (30, 'B2', 2)]   # a line under A, in C


def piano_lh(ch, vel=54, broken=True):
    """the left hand: root, then the chord rolled upward over the bar"""
    prev = None
    for s, d, sym in ch:
        r = root(sym, 2)
        while r < 36:
            r += 12
        piano.note(s, r, d * 0.98, vel + 4)
        ns = voice(tones(sym, 3), prev, 50, 64); prev = ns
        for j, n in enumerate(ns):
            piano.note(s + (0.5 + j * 0.5 if broken else 0.02 * j), n, d - 0.5 - j * 0.5 if broken else d * 0.95, vel - 6)


def pedal(t0, t1):
    for b in range(int(t0), int(t1), 2):
        piano.cc(b, 64, 0); piano.cc(b + 0.06, 64, 127)
    piano.cc(t1, 64, 0)


t = 0.0
# ---- the piano alone (2 + 8): the inverted A, very quietly
for s, d, sym in prog(tprog('Dm9/G | G13', K), at=t):
    for j, n in enumerate(voice(tones(sym, 4), None, 52, 70)):
        piano.note(s + j * 0.25, n, d - j * 0.25, 46)
t += 8
ch = prog(tprog(IA_CH, K), at=t)
piano_lh(ch, vel=48)
play(piano, mel([(b, p, d) for b, p, d in IA], K), at=t, vel=68)
pedal(0, t + 32)
t += 32

# ---- B inverted, the piano still alone (8)
ch = prog(tprog(IB_CH, K), at=t)
piano_lh(ch, vel=46)
play(piano, mel(IB, K), at=t, vel=64)
pedal(t, t + 32)
t += 32

# ---- A: the violins sing it, the cellos underneath; the piano rolls the harmony
ch = prog(tprog(IA_CH, K), at=t)
piano_lh(ch, vel=46)
arp(harp, ch, step=0.5, vel=46, lo=60, hi=86, pattern=(0, 1, 2, 3, 4, 3, 2, 1), gate=2.5)
play(vln, mel(IA, K), at=t, vel=80, legato=True)
play(cello, mel(CELLO, K), at=t, vel=70, legato=True)
bassline(bass, ch, style='ballad', vel=76, rng=rng)
pedal(t, t + 32)
t += 32

# ---- B: the choir and the glass piano; the flute answers
ch = prog(tprog(IB_CH, K), at=t)
sustain(choir, ch, vel=58, lo=55, hi=79, n=4)
play(glass, mel(IB, K), at=t, vel=74)
piano_lh(ch, vel=44)
for b0, ns in ((3.0, ['A5', 'G5', 'E5']), (11.0, ['F5', 'E5', 'D5']), (19.0, ['G5', 'E5', 'C5']), (27.0, ['A5', 'G5', 'F5'])):
    for i, n in enumerate(ns):
        flute.note(t + b0 + i * 0.33, pitch(n) + K, 0.6, 62 - i * 4)
bassline(bass, ch, style='ballad', vel=78, rng=rng)
drums(kit, {RIDE: 'x...x...x...x...'}, t + 16, 4, vel=0.4)
pedal(t, t + 32)
t += 32

# ---- B again, everyone but the horns: brushes, the violins an octave up on its second half
ch = prog(tprog(IB_CH, K), at=t)
sustain(choir, ch, vel=52, lo=55, hi=79, n=4)
play(vln, mel(IB, K), at=t, vel=78, legato=True)
play(cello, mel([(b, p - 12, d) for b, p, d in IB][::2], K - 12), at=t, vel=60, legato=True)
arp(harp, ch, step=0.5, vel=48, lo=60, hi=88, pattern=(0, 1, 2, 3, 4, 3, 2, 1), gate=2.5)
piano_lh(ch, vel=46)
bassline(bass, ch, style='fretless', vel=82, rng=rng, var=0.4)
drums(kit, 'brush', t, 8, vel=0.55)
S.tempo(t + 30, 62)
fill(kit, t + 32, 'roll', 0.6, 2.0)
pedal(t, t + 32)
t += 32

# ---- the climax: A a tone higher (E-flat), violins and horns, the choir full, a broad tempo
S.tempo(t, 64)
K2 = K + 2
ch = prog(tprog(IA_CH, K2), at=t)
play(vln, mel(IA, K2), at=t, vel=96, legato=True)
play(vln, mel(IA, K2 - 12), at=t, vel=80, legato=True)
play(horn, mel(CELLO, K2 + 12), at=t, vel=84, legato=True)
play(cello, mel(CELLO, K2), at=t, vel=86, legato=True)
sustain(choir, ch, vel=66, lo=55, hi=82, n=4)
arp(harp, ch, step=0.5, vel=54, lo=60, hi=90, pattern=(0, 1, 2, 3, 4, 3, 2, 1), gate=2.5)
piano_lh(ch, vel=56, broken=False)
bassline(bass, ch, style='ballad', vel=90, rng=rng)
drums(kit, 'ballad', t, 8, vel=0.6)
kit.note(t, CRASH, 3, 90)
pedal(t, t + 32)
S.tempo(t + 26, 60); S.tempo(t + 29, 54)
t += 32

# ---- B at the climax's height (8): the choir and the violins in octaves, then it lets go
S.tempo(t, 62)
ch = prog(tprog(IB_CH, K2), at=t)
play(vln, mel(IB, K2), at=t, vel=90, legato=True)
play(vln, mel(IB, K2 + 12), at=t, vel=70, legato=True)
play(cello, mel([(b, p - 12, d) for b, p, d in IB], K2), at=t, vel=78, legato=True)
sustain(choir, ch, vel=60, lo=55, hi=82, n=4)
arp(harp, ch, step=0.5, vel=50, lo=60, hi=90, pattern=(0, 1, 2, 3, 4, 3, 2, 1), gate=2.5)
piano_lh(ch, vel=50)
bassline(bass, ch, style='ballad', vel=84, rng=rng)
drums(kit, 'brush', t, 6, vel=0.5)
for p in (vln, cello, choir, harp, bass):
    fade(p, t + 16, t + 32, 1.0, 0.45)
pedal(t, t + 32)
S.tempo(t + 24, 58); S.tempo(t + 30, 52)
t += 32

# ---- home (6): D-flat again, the piano alone with the inverted motto, the rain
S.tempo(t, 60)
ch = prog(tprog('Cmaj9 | Em7 Fmaj9 | Dm9 G13 | Cmaj9 | Fmaj9 | Cmaj9', K), at=t)
piano_lh(ch, vel=42)
play(piano, shift(mel(IA[:5], K), t), vel=60)
play(piano, shift(mel(IA[:4], K + 12), t + 16), vel=50)
choir.note(t + 16, pitch('E5') + K, 8, 50); choir.note(t + 16, pitch('G4') + K, 8, 48)
pedal(t, t + 24)
t += 24 + 6
texture(rain, 0, t, note=60, vel=60, bpm=BPM, seconds=26)

F = Feel(8088)
F.apply(S, piano, lay_ms=10, jit_ms=9, vel=5)
F.apply(S, vln, lay_ms=20, jit_ms=8, vel=3)
F.apply(S, cello, lay_ms=20, jit_ms=8, vel=3)
F.apply(S, horn, lay_ms=24, jit_ms=8, vel=3)
F.apply(S, glass, lay_ms=8, jit_ms=8, vel=4)
F.apply(S, harp, lay_ms=0, jit_ms=8, vel=6)
F.apply(S, flute, lay_ms=14, jit_ms=8, vel=4)

finish(__file__, S, {
    'title': 'Var. VII: The Loft, Inverted',
    'track': 8,
    'note': 'The slow heart: the theme inverted in D-flat at 66, re-harmonised; soft piano alone, then violins and '
            'cellos, choir and glass piano on the inverted B, a climax a tone higher with horns, the piano alone again.',
}, [
    ('rain', 'ch13', 'Balcony Rain', dict(lufs=-36)),
    ('piano', 'ch1', 'Felt Upright', dict(lufs=-19, pan=-8, verb=0.35)),
    ('violins', 'ch2', 'Legato Violins', dict(lufs=-21, pan=-26, verb=0.45)),
    ('cellos', 'ch3', 'Legato Cellos', dict(lufs=-23, pan=24, verb=0.4)),
    ('choir', 'ch4', 'Mist Choir', dict(lufs=-26, pan=8, verb=0.55)),
    ('harp', 'ch5', 'Harbour Harp', dict(lufs=-27, pan=40, verb=0.4, echo=0.1)),
    ('horns', 'ch6', 'Ferry Horns', dict(lufs=-24, pan=-14, verb=0.45)),
    ('bass', 'ch7', 'Fretless Harbour', dict(lufs=-24)),
    ('glass', 'ch8', 'Glass Tine', dict(lufs=-22, pan=30, verb=0.4, echo=0.15)),
    ('flute', 'ch9', 'Late Flute', dict(lufs=-26, pan=-36, verb=0.5, echo=0.2)),
    ('kit', 'ch10', 'Loft Brushes', dict(lufs=-28, verb=0.25)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 4.0},
   echo={'time': '1/4', 'feedback': 0.3, 'tone': 2600, 'pingpong': 'yes', 'level': -9, 'lowcut': 250},
   reverb={'size': 3.4, 'predelay': 28, 'tone': 5000, 'level': -4, 'seed': 3118})

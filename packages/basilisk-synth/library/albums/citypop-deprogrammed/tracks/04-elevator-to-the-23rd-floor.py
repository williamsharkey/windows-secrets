"""4. Var. III: Elevator to the 23rd Floor. B-flat major, a bossa nova at 120 bpm. The theme in augmentation:
every note twice as long, so the flute sings it slowly over a quick, quiet band. The harmony moves twice as often
under it. The chime opens the doors at the start and closes them at the end."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 10 - 12                 # B-flat
BPM = 120
S = Score(bpm=BPM, seed=404)
gtr = S.part('gtr', 1); bass = S.part('bass', 2); flute = S.part('flute', 3); ep = S.part('ep', 4)
strings = S.part('strings', 5); vibes = S.part('vibes', 6); chime = S.part('chime', 7)
kit = S.part('kit', 10); perc = S.part('perc', 11); lobby = S.part('lobby', 13)
rng = random.Random(44)

A16 = tprog('Fmaj7 | Bb7#11 | Em7 | A7b9 | Dm9 | Dm9/C | G13 | Db7#11 | Fmaj7 | F6 | E7#9 | E7b9 | Am9 | D9 | Dm9 | G13sus4 G7b9', K)
B16 = tprog('Bbmaj7 | Bbmaj7 | Am7 | D7b9 | Gm9 | Gm9 | C13 | C7#9 | Abmaj7 | Abmaj7 | G7sus4 | G7b9 | Cmaj9 | A7#9 | Dm9 | G13sus4 G13', K)
TA = augment(mel(THEME_A, K + 12), 2.0)
TB = augment(mel(THEME_B, K + 12), 2.0)
GTR_PAT = [(0, 0.5), (1.5, 0.5), (3.0, 0.5), (4.5, 0.5), (6.0, 0.5)]   # two-bar bossa comping, offsets in beats


def bossa_guitar(ch, vel=62):
    """thumb on the root (1 and 3), fingers on the chord in the two-bar syncopation"""
    prev = None
    for s, d, sym in ch:
        ns = voice(tones(sym, 4), prev, 57, 72); prev = ns
        two = (round(s / 4) % 2)
        for off, ln in GTR_PAT:
            o = off - 4 * two
            if 0 <= o < d:
                for j, n in enumerate(ns):
                    gtr.note(s + o + j * 0.012, n, ln * 0.9, vel - j * 2)
        r = root(sym, 2) + 12
        for o in (0, 2):
            if o < d:
                gtr.note(s + o, r if o == 0 else r + 7 - (12 if r + 7 > 57 else 0), 0.9, vel - 4)


def kit_bossa(t, bars, v=0.72):
    for b in range(bars):
        rim = 'x..x..x...x..x..' if b % 2 == 0 else '..x..x...x..x...'
        drums(kit, {KICK: 'x..xx..xx..xx..x', RIM: rim, CHH: 'x.x.x.x.x.x.x.x.'}, t + 4 * b, 1, vel=v, var=0.08)
        drums(perc, {SHAKER: 'xoxoxoxoxoxoxoxo'}, t + 4 * b, 1, vel=0.5)


def band(ch, t, bars, v=0.72, strings_on=False):
    bossa_guitar(ch)
    bassline(bass, ch, style='bossa', vel=88, rng=rng, var=0.1)
    kit_bossa(t, bars, v)
    if strings_on:
        sustain(strings, ch, vel=42, lo=60, hi=84, n=3)


t = 0.0
# ---- doors (8): the chime, the lobby, the guitar alone; bass and brushes from bar 5
ding = mel([(0.0, 'G5', 1.5), (1.5, 'Eb5', 2.5)], K + 12)     # the elevator's two notes
play(chime, ding, vel=86, shape=False)
ch = prog(tprog('Fmaj7 | Bb7#11 | Fmaj7 | Bb7#11 | Em7 | A7b9 | Dm9 | G13sus4 G7b9', K), at=t)
bossa_guitar(ch[:4], vel=56)
band(ch[4:], t + 16, 4, v=0.62)
t += 32

# ---- A (16 bars): the flute, slowly
ch = prog(A16, at=t)
band(ch, t, 16)
play(flute, grace(TA, every=2), at=t, vel=82, legato=True)
for k in range(4):
    vibes.note(t + 16 * k + 14.5, pitch('D6') + K - 12, 1.2, 50)
t += 64

# ---- B (16 bars): the glass piano has the tune, the flute weaves a line above it
ch = prog(B16, at=t)
band(ch, t, 16, strings_on=True)
play(ep, TB, at=t, vel=74, tr=-12)
line = improvise(ch, [(x + K) % 12 for x in C_MAJOR], seed=404, lo=74, hi=91, density=0.55, cells=RHYTHMS[3:5] + RHYTHMS[6:])
for b, n, d in line:
    flute.note(b, n, d * 0.95, 64 + rng.randint(-6, 4))
t += 64

# ---- interlude (8): the guitar and the vibraphone trade the motto, in double time
ch = prog(tprog('Dm9 | G13 | Em7 | A7b9 | Dm9 | G13 | Gm9 | C13', K), at=t)
band(ch, t, 8)
for k in range(4):
    who = vibes if k % 2 == 0 else ep
    play(who, shift(mel(HEAD, K + 12 if who is vibes else K), t + 8 * k), vel=74)
t += 32

# ---- B again (16): the vibraphone improvises over it, the strings hold the harmony
ch = prog(B16, at=t)
band(ch, t, 16, strings_on=True)
line = improvise(ch, [(x + K) % 12 for x in C_MAJOR], seed=406, lo=65, hi=89, density=0.75)
for b, n, d in line:
    vibes.note(b, n, d * 0.9, 68 + rng.randint(-6, 6))
play(flute, shift(mel(HEAD, K + 12), t + 56), vel=70)
t += 64

# ---- the glass piano's chorus (16) over A
ch = prog(A16, at=t)
band(ch, t, 16)
line = improvise(ch, [(x + K) % 12 for x in C_MAJOR], seed=407, lo=62, hi=86, density=0.7, motif=shift(mel(HEAD, K + 12), t))
for b, n, d in line:
    ep.note(b, n, d * 0.9, 70 + rng.randint(-6, 6))
t += 64

# ---- A again (16): the vibraphone's chorus over it, the flute back for the last eight
ch = prog(A16, at=t)
band(ch, t, 16, strings_on=True)
line = improvise(ch[:8], [(x + K) % 12 for x in C_MAJOR], seed=405, lo=65, hi=89, density=0.8)
for b, n, d in line:
    vibes.note(b, n, d * 0.9, 70 + rng.randint(-6, 6))
play(flute, [(b, p, d) for b, p, d in TA if b >= 32], at=t, vel=84, legato=True)
t += 64

# ---- A once more, quieter, then the doors (8)
ch = prog(A16, at=t)
band(ch, t, 16, v=0.64)
play(flute, TA[:20], at=t, vel=78, legato=True)
play(vibes, mel(THEME_A[20:], K + 12), at=t + 16, vel=56)
fade(gtr, t + 40, t + 64, 1.0, 0.6); fade(kit, t + 40, t + 64, 1.0, 0.4); fade(perc, t + 40, t + 64, 1.0, 0.3)
t += 64
for s, d, sym in prog(tprog('Fmaj9:8', K), at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 55, 77)):
        gtr.note(s + j * 0.09, n, 6, 56)
    bass.note(s, root(sym, 1) + 12, 6, 76)
play(chime, shift(ding, t + 4), vel=80, shape=False)
t += 12
texture(lobby, 0, t, note=60, vel=70, bpm=BPM, seconds=26)

F = Feel(4044)
F.apply(S, flute, lay_ms=14, jit_ms=8, vel=4)
F.apply(S, gtr, lay_ms=0, jit_ms=6, vel=5)
F.apply(S, ep, lay_ms=6, jit_ms=7, vel=4)
F.apply(S, vibes, lay_ms=6, jit_ms=7, vel=4)
F.apply(S, bass, lay_ms=3, jit_ms=4, vel=4)
F.apply(S, kit, jit_ms=4, vel=5)
F.apply(S, perc, jit_ms=6, vel=6)

finish(__file__, S, {
    'title': 'Var. III: Elevator to the 23rd Floor',
    'track': 4,
    'note': 'A bossa nova in B-flat at 120 bpm with the theme in augmentation (every note twice as long) on flute; '
            'a nylon-style guitar on a two-bar pattern, the glass piano on B, the motto traded in double time.',
}, [
    ('lobby', 'ch13', 'City Hush', dict(lufs=-37)),
    ('chime', 'ch7', 'Single Chime', dict(lufs=-24, pan=20, verb=0.5, echo=0.2)),
    ('gtr', 'ch1', 'courtyard-chapel:Faded Pluck', dict(lufs=-20, pan=-24, verb=0.2)),
    ('bass', 'ch2', 'Fretless Harbour', dict(lufs=-21)),
    ('flute', 'ch3', 'Night Flute', dict(lufs=-19, pan=10, verb=0.35, echo=0.14)),
    ('ep', 'ch4', 'Glass Tine', dict(lufs=-22, pan=28, verb=0.3, echo=0.1)),
    ('strings', 'ch5', 'studio-archive:Waxed Aurora', dict(lufs=-28, pan=-38, verb=0.45)),
    ('vibes', 'ch6', 'courtyard-chapel:Delta Tower', dict(lufs=-22, pan=40, verb=0.3, echo=0.12)),
    ('kit', 'ch10', 'Loft Brushes', dict(lufs=-23, verb=0.12)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-28, pan=30, verb=0.12)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 2800, 'pingpong': 'yes', 'level': -8, 'lowcut': 250},
   reverb={'size': 2.2, 'predelay': 20, 'tone': 5000, 'level': -6, 'seed': 3114})

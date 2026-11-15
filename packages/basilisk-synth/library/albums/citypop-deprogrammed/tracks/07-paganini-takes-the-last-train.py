"""7. Var. VI: Paganini Takes the Last Train. A minor, 112 bpm, the driving one. It opens with the first figure of
Paganini's Caprice No. 24 (1817, public domain) on pizzicato and bass, and the theme answers it in the minor. The two
pick-ups are cousins: 1 1 3 2 1 5 and 5 1 2 3. The rest is the album's own, on a train groove with a crossing bell,
and it ends in the major as the train pulls away."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 9 - 12                   # A (minor)
BPM = 112
S = Score(bpm=BPM, seed=707)
pizz = S.part('pizz', 1); bass = S.part('bass', 2); trumpet = S.part('trumpet', 3); ep = S.part('ep', 4)
strings = S.part('strings', 5); flute = S.part('flute', 6); glass = S.part('glass', 7); xing = S.part('crossing', 8)
kit = S.part('kit', 10); perc = S.part('perc', 11); train = S.part('train', 13)
rng = random.Random(77)

MA = tprog('Abmaj7 | Fm9 Bb7#9 | Dm7b5 | Gm9 | Abmaj7 | Fm9 | Cm9 D7b9 | Dm7b5 G7alt', 9)   # the minor A, in A minor
TM = modal(mel(THEME_A, 0), TO_MINOR)
TM = [(b, p + 9 - 12, d) for b, p, d in TM]
KEYM = [(x + 9) % 12 for x in (0, 2, 3, 5, 7, 8, 10)]
CAP = mel(CAPRICE, 0)                      # A4 A4 C5 B4 A4 E5 E4: already in A minor
B = CHORDS_B                               # in C, the relative major
TB = mel(THEME_B, 0)


def band(ch, t, bars, kv=0.82, ep_style='stabs'):
    comp(ep, ch, style=ep_style, vel=64, lo=55, hi=74, rng=rng, var=0.1)
    bassline(bass, ch, style='citypop', vel=96, rng=rng, var=0.15)
    drums(kit, 'train', t, bars, vel=kv)
    drums(perc, {SHAKER: 'xxxxxxxxxxxxxxxx', TAMB: '....x.......x...'}, t, bars, vel=0.5)


def caprice(part, at, reps=2, tr=0, vel=86):
    for k in range(reps):
        play(part, shift(CAP, at + 4 * k), vel=vel, tr=tr, shape=False)


t = 0.0
# ---- the quotation (8): pizzicato and bass in octaves; the drums arrive on bar 5
for k in range(2):
    caprice(pizz, t + 8 * k, reps=1, vel=90)
    caprice(bass, t + 8 * k, reps=1, tr=-24, vel=96)
    play(trumpet, shift(modal(mel(HEAD, 0), TO_MINOR), t + 8 * k + 4), vel=80, tr=9 - 12)   # the theme answers
xing.note(0.0, pitch('E6'), 0.3, 50)
drums(kit, {CHH: 'xxxxxxxxxxxxxxxx'}, t + 16, 2, vel=0.6)
drums(kit, 'train', t + 24, 2, vel=0.75)
fill(kit, t + 32, 'snare', 0.85)
t += 32

# ---- A minor: the muted trumpet
ch = prog(MA, at=t)
band(ch, t, 8)
play(trumpet, grace(TM), at=t, vel=88, legato=True)
for k in range(4):
    for j in range(6):                     # the crossing bell, far down the line
        xing.note(t + 8 * k + 6 + j * 0.5, pitch('E6'), 0.3, 40 + j * 2)
kit.note(t, CRASH, 2, 90)
t += 32

# ---- A minor: flute and trumpet together, strings stab on the off-beats
ch = prog(MA, at=t)
band(ch, t, 8, kv=0.86)
play(trumpet, TM, at=t, vel=86, legato=True)
play(flute, TM, at=t, vel=74, tr=12, legato=True)
comp(strings, ch, style=[(1.5, 0.3, 1.0), (3.5, 0.3, 0.9)], vel=70, lo=57, hi=79, push=False)
fill(kit, t + 32, 'toms', 0.9)
t += 32

# ---- B, in C major for eight bars: the glass piano, the train in the distance
ch = prog(B, at=t)
comp(ep, ch, style='citypop2', vel=60, lo=55, hi=74, rng=rng)
bassline(bass, ch, style='citypop', vel=92, rng=rng, var=0.2)
drums(kit, 'citypop2', t, 8, vel=0.8)
play(glass, TB, at=t, vel=82)
sustain(strings, ch, vel=50, lo=57, hi=81, n=3)
train.note(t, 60, 30, 90)
fill(kit, t + 32, 'roll', 0.85)
t += 32

# ---- the turn (8): the caprice figure in the bass, bar by bar, becomes the theme's pick-up
for k in range(4):
    c = CAP if k < 2 else modal(mel(HEAD, 0), TO_MINOR)
    c = [(b, p + (9 - 24 if k >= 2 else -24), d) for b, p, d in c]
    play(bass, shift(c, t + 8 * k), vel=98, shape=False)
    play(pizz, shift(c, t + 8 * k + 4), vel=84, tr=24, shape=False)
ch = prog(tprog('Am9 | E7b9 | Am9 | E7b9 | Dm9 | G13 | Fmaj7 | E7alt', 0), at=t)
comp(ep, ch, style='stabs', vel=60, lo=55, hi=72, rng=rng)
drums(kit, 'train', t, 8, vel=0.84)
drums(perc, {SHAKER: 'xxxxxxxxxxxxxxxx'}, t, 8, vel=0.5)
t += 32

# ---- choruses: the suitcase piano, then the trumpet
for k, (who, lo_, hi_) in enumerate(((ep, 64, 88), (trumpet, 57, 81))):
    ch = prog(MA, at=t)
    line = improvise(ch, KEYM, seed=700 + k, lo=lo_, hi=hi_, density=0.85)
    for b, n, d in line:
        who.note(b, n, d * 0.9, 84 + rng.randint(-8, 6))
    comp(ep if k == 1 else strings, ch, style='stabs' if k == 1 else [(1.5, 0.3, 1.0), (3.5, 0.3, 0.9)], vel=58, lo=55, hi=76, rng=rng)
    bassline(bass, ch, style='citypop', vel=96, rng=rng, var=0.15)
    drums(kit, 'train', t, 8, vel=0.86)
    drums(perc, {SHAKER: 'xxxxxxxxxxxxxxxx', TAMB: '....x.......x...'}, t, 8, vel=0.5)
    t += 32
fill(kit, t, 'toms', 0.95)

# ---- B again, in C: the flute and the glass piano in octaves; the train passes nearer
ch = prog(B, at=t)
comp(ep, ch, style='citypop2', vel=62, lo=55, hi=74, rng=rng)
bassline(bass, ch, style='citypop', vel=94, rng=rng, var=0.2)
drums(kit, 'citypop2', t, 8, vel=0.84)
drums(perc, {SHAKER: 'xxxxxxxxxxxxxxxx', TAMB: '....x.......x...'}, t, 8, vel=0.5)
play(flute, TB, at=t, vel=80, tr=12, legato=True)
play(glass, TB, at=t, vel=70)
sustain(strings, ch, vel=52, lo=57, hi=81, n=3)
train.note(t + 8, 60, 26, 96)
fill(kit, t + 32, 'toms', 0.9)
t += 32

# ---- the last A minor, everyone; then the caprice once more and A major as the train pulls out
ch = prog(MA, at=t)
band(ch, t, 8, kv=0.9)
play(trumpet, TM, at=t, vel=90, legato=True)
play(flute, TM, at=t, vel=76, tr=12, legato=True)
sustain(strings, ch, vel=54, lo=57, hi=81, n=4)
kit.note(t, CRASH, 2, 100)
t += 32
caprice(pizz, t, reps=1, vel=84); caprice(bass, t, reps=1, tr=-24, vel=94)
drums(kit, 'train', t, 1, vel=0.8)
t += 4
for s, d, sym in prog('A69:8', at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 55, 79)):
        ep.note(s + j * 0.05, n, 7, 62); strings.note(s, n, 7.5, 50)
    bass.note(s, root(sym, 1) + 12, 6, 90)
    kit.note(s, KICK, 0.4, 96); kit.note(s, CRASH, 3, 90)
    play(glass, shift(mel(HEAD, 9), s + 2), vel=60)
train.note(t - 8, 60, 20, 100)
t += 12

F = Feel(7077)
F.apply(S, trumpet, lay_ms=8, jit_ms=8, vel=4)
F.apply(S, flute, lay_ms=10, jit_ms=8, vel=4)
F.apply(S, ep, lay_ms=0, jit_ms=5, vel=5)
F.apply(S, pizz, lay_ms=0, jit_ms=5, vel=5)
F.apply(S, bass, lay_ms=-2, jit_ms=4, vel=4)
F.apply(S, kit, jit_ms=3, vel=4)
F.apply(S, perc, jit_ms=5, vel=6)

finish(__file__, S, {
    'title': 'Var. VI: Paganini Takes the Last Train',
    'track': 7,
    'note': 'A minor at 112 on a train groove. Opens with the first figure of Paganini\'s Caprice No. 24 (1817, public '
            'domain) and the theme answering in the minor; B in C major; the caprice in the bass turns into the '
            'theme\'s pick-up; ends in A major as the train leaves.',
    'source': 'Paganini, Caprice No. 24 in A minor, Op. 1 (published 1820): its opening figure only, quoted twice',
}, [
    ('train', 'ch13', 'Passing Train', dict(lufs=-30, pan=-20)),
    ('crossing', 'ch8', 'Glass Ceiling', dict(lufs=-32, pan=60, verb=0.5, lp=6000)),
    ('pizz', 'ch1', 'Pizzicato Night', dict(lufs=-21, pan=-26, verb=0.25)),
    ('bass', 'ch2', 'Rubber Taxi', dict(lufs=-19)),
    ('trumpet', 'ch3', 'Harmon Glow', dict(lufs=-18, pan=8, verb=0.25, echo=0.12)),
    ('ep', 'ch4', 'Suitcase Night', dict(lufs=-21, pan=-12, verb=0.2)),
    ('strings', 'ch5', 'Humid Strings', dict(lufs=-24, pan=36, verb=0.35)),
    ('flute', 'ch6', 'Night Flute', dict(lufs=-22, pan=-18, verb=0.3, echo=0.12)),
    ('glass', 'ch7', 'Glass Tine', dict(lufs=-21, pan=24, verb=0.3, echo=0.15)),
    ('kit', 'ch10', 'Loft Sticks', dict(lufs=-19, verb=0.08)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-28, pan=-30, verb=0.1)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3000, 'pingpong': 'yes', 'level': -8, 'lowcut': 250},
   reverb={'size': 1.8, 'predelay': 16, 'tone': 5500, 'level': -7, 'seed': 3117})

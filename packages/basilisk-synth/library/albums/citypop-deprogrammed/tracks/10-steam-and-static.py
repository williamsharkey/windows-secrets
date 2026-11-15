"""10. Var. IX: Steam and Static. G-flat major, 60 bpm, no drums: the interlude after the party. The steam wand
and the rain go into Sound Recorder's grain engine and come out as weather: slow clouds of tiny pieces of the
recordings, following the harmony. The theme crosses it once on the crystal bell, each note twice as long again."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 6 - 12                   # G-flat
BPM = 60
S = Score(bpm=BPM, seed=1010)
cloud = S.part('cloud', 1); steam = S.part('steam', 2); bell = S.part('bell', 3); bass = S.part('bass', 4)
glass = S.part('glass', 5); choir = S.part('choir', 6); wand = S.part('wand', 7); static = S.part('static', 8)
rain = S.part('rain', 13)
rng = random.Random(1010)

CH = tprog('Fmaj7 | Fmaj7 | Em7 | A7 | Dm9 | Dm9 | G13 | G13 | Fmaj7 | Fmaj7 | E7#9 | E7#9 | Am9 | D9 | Dm9 | G13sus4', K)
TA = augment(mel(THEME_A, K + 12), 2.0)

t = 0.0
# ---- the steam and the static (4)
wand.note(1.0, 60, 6, 90)
static.note(0.0, 60, 20, 70)
steam.note(4.0, 60, 12, 60)
t += 8

# ---- the clouds follow the chords; the bell carries the theme slowly; the bass hardly moves
ch = prog(CH, at=t)
for s, d, sym in ch:
    ns = voice(tones(sym, 4), None, 55, 79)
    for j, n in enumerate(ns):
        cloud.note(s + j * 0.3, n, d + 1.0, 58 - j * 3)
    steam.note(s, ns[-1] + 12, d + 1, 48)
    bass.note(s, root(sym, 1) + 12, d * 0.95, 66)
sustain(choir, ch, vel=40, lo=55, hi=76, n=3)
play(bell, TA, at=t, vel=74, shape=False)
for k in range(0, 64, 8):
    if rng.random() < 0.7:
        wand.note(t + k + rng.uniform(1, 5), 60, 5, 58 + rng.randint(-8, 8))
t += 64

# ---- the inverted B goes by on the glass piano, inside the cloud (16 bars, slowly)
IB = invert(mel(THEME_B, 0), 'E5')
CHB = tprog('Dm9 | Dm9 | Em7 | A7 | Gm9 | G7 | Cmaj9 | Cmaj9 | Am9 | Am9 | Bbmaj7 | Bbmaj7 | Em7 | F6 | Dm9/G | G13', K)
ch = prog(CHB, at=t)
for s, d, sym in ch:
    ns = voice(tones(sym, 4), None, 55, 79)
    for j, n in enumerate(ns):
        cloud.note(s + j * 0.3, n, d + 1.0, 54 - j * 3)
    steam.note(s, ns[-1] + 12, d + 1, 44)
    bass.note(s, root(sym, 1) + 12, d * 0.95, 62)
play(glass, augment([(b, p + K + 12, d) for b, p, d in IB], 2.0), at=t, vel=62)
sustain(choir, ch, vel=36, lo=55, hi=76, n=3)
wand.note(t + 30, 60, 6, 60)
t += 64

# ---- the glass piano remembers the motto, then the second half of the theme at its own speed, very far off
ch = prog(tprog('Dm9 | G13 | Cmaj9 | Cmaj9 | Fmaj7 | E7#9 | Am9 | Dm9 G13sus4', K), at=t)
for s, d, sym in ch:
    for j, n in enumerate(voice(tones(sym, 4), None, 55, 79)):
        cloud.note(s + j * 0.3, n, d + 1.0, 52 - j * 3)
    bass.note(s, root(sym, 1) + 12, d * 0.95, 60)
play(glass, shift(mel(HEAD, K + 12), t), vel=64)
play(glass, shift(mel(HEAD, K + 12), t + 8), vel=56, tr=-12)
play(bell, [(b - 16 + t + 16, p, d) for b, p, d in mel(THEME_A[20:], K + 12)], vel=60, shape=False)
t += 32
static.note(t - 20, 60, 20, 60)
wand.note(t - 6, 60, 6, 70)
t += 8
texture(rain, 0, t, note=60, vel=74, bpm=BPM, seconds=26)

F = Feel(1010)
F.apply(S, bell, lay_ms=0, jit_ms=12, vel=4)
F.apply(S, glass, lay_ms=10, jit_ms=10, vel=4)

finish(__file__, S, {
    'title': 'Var. IX: Steam and Static',
    'track': 10,
    'note': 'The interlude, in G-flat at 60 with no drums: grain clouds made from the steam wand, the rain and the '
            'glass piano follow the harmony; the theme crosses once on the crystal bell, every note twice as long.',
}, [
    ('rain', 'ch13', 'Rain on the Window', dict(lufs=-30)),
    ('static', 'ch8', 'Radio Static', dict(lufs=-38, hp=400, lp=6000, pan=-30)),
    ('wand', 'ch7', 'Steam Wand', dict(lufs=-32, pan=34, verb=0.3)),
    ('cloud', 'ch1', 'Glass Cloud', dict(lufs=-21, verb=0.5, echo=0.2)),
    ('steam', 'ch2', 'Steam Cloud', dict(lufs=-30, hp=300, verb=0.4)),
    ('bell', 'ch3', 'Crystal Bb', dict(lufs=-21, pan=-16, verb=0.5, echo=0.25)),
    ('bass', 'ch4', 'Fretless Harbour', dict(lufs=-25, lp=900)),
    ('glass', 'ch5', 'Glass Tine', dict(lufs=-24, pan=28, verb=0.55, echo=0.3)),
    ('choir', 'ch6', 'Mist Choir', dict(lufs=-30, pan=-10, verb=0.6)),
], master={'loudness': -17, 'ceiling': -1.0, 'fadeout': 5.0},
   echo={'time': '3/8', 'feedback': 0.4, 'tone': 2400, 'pingpong': 'yes', 'level': -7, 'lowcut': 250},
   reverb={'size': 4.0, 'predelay': 30, 'tone': 4800, 'level': -4, 'seed': 3120})

"""11. Var. X: Last Call at the Listening Bar. D-flat major, 88 bpm, swung: jazz-funk at a bar with good speakers
and four people left. The theme re-harmonised with tritone substitutions under it. Then sixteen bars of electric
piano, the reed and the piano trading fours, B on the strings, and a last A a semitone up in D. Glasses on the
counter."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 1                        # D-flat
BPM = 88
S = Score(bpm=BPM, seed=1111)
ep = S.part('ep', 1); bass = S.part('bass', 2); reed = S.part('reed', 3); clar = S.part('clarinet', 4)
strings = S.part('strings', 5); vibes = S.part('vibes', 6); glasses = S.part('glasses', 7)
kit = S.part('kit', 10); perc = S.part('perc', 11); room = S.part('room', 13)
rng = random.Random(1111)

RA = 'Fmaj7 Bb9 | Em7 A7b9 | Dm9 | G13 Db7#11 | Fmaj7 F#m7b5 | E7#9 Bb13 | Am9 D13 | Dm9 G7alt'
JAZZ = {KICK: 'x.........x.....', SNARE: '....o.......x...', RIDE: 'x...x.x.x...x.x.', PHH: '....x.......x...', SNARE2: '.......g......g.'}


def band(ch, t, bars, kv=0.78, ep_on=True, ev=58):
    if ep_on:
        comp(ep, ch, style='citypop2', vel=ev, lo=52, hi=72, rng=rng, var=0.2)
    bassline(bass, ch, style='fretless', vel=90, rng=rng, var=0.15)
    drums(kit, JAZZ, t, bars, vel=kv, swing8=0.3)
    drums(perc, {SHAKER: 'x.o.x.o.x.o.x.o.'}, t, bars, vel=0.4, swing8=0.3)


t = 0.0
# ---- the piano alone (4)
for s, d, sym in prog(tprog('Dm9 | G13 | Em7 | A7b9', K), at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 52, 76)):
        ep.note(s + j * 0.07, n, d * 0.9, 56)
    ep.note(s, root(sym, 2), d * 0.9, 58)
glasses.note(6.0, 60, 4, 70)
t += 16

# ---- A: the reed over the new harmony
ch = prog(tprog(RA, K), at=t)
band(ch, t, 8)
play(reed, grace(mel(THEME_A, K - 12)), at=t, vel=86, legato=True)
t += 32

# ---- A: the clarinet joins a sixth under the reed; vibes in the gaps
ch = prog(tprog(RA, K), at=t)
band(ch, t, 8, kv=0.82)
TA = mel(THEME_A, K - 12)
play(reed, TA, at=t, vel=86, legato=True)
KEY = [(x + K) % 12 for x in C_MAJOR]
six = [(b, p - 9 if (p - 9) % 12 in KEY else p - 8, d) for b, p, d in TA]
play(clar, six, at=t, vel=72, legato=True)
for b0, ns in ((3.5, ['E5', 'G5']), (11.0, ['A5', 'C6']), (19.5, ['E5', 'A5']), (27.0, ['D5', 'F5', 'A5'])):
    for i, n in enumerate(ns):
        vibes.note(t + b0 + i * 0.5, pitch(n) + K, 0.8, 60)
fill(kit, t + 32, 'snare', 0.75)
t += 32

# ---- the piano's sixteen bars; the left hand thins out
for k in range(2):
    ch = prog(tprog(RA, K), at=t)
    line = improvise(ch, KEY, seed=1100 + k, lo=60, hi=88, density=0.85, motif=shift(mel(HEAD, K), t) if k == 0 else None)
    for b, n, d in line:
        ep.note(b, n, d * 0.88, 76 + rng.randint(-10, 8))
    comp(ep, ch, style='halves', vel=44, lo=48, hi=62, n=3)
    band(ch, t, 8, kv=0.8 + 0.04 * k, ep_on=False)
    if k:
        sustain(strings, ch, vel=38, lo=60, hi=82, n=3)
    t += 32

# ---- trading fours: reed, piano, reed, piano
ch = prog(tprog(RA, K), at=t)
band(ch, t, 8, kv=0.84, ep_on=False)
for k in range(2):
    sub = [c for c in ch if t + 16 * k <= c[0] < t + 16 * k + 16]
    for j, who, lo_, hi_ in ((0, reed, 55, 79), (1, ep, 62, 86)):
        part = [c for c in sub if t + 16 * k + 8 * j <= c[0] < t + 16 * k + 8 * j + 8]
        line = improvise(part, KEY, seed=1120 + 2 * k + j, lo=lo_, hi=hi_, density=0.95, cells=RHYTHMS[1:6])
        for b, n, d in line:
            who.note(b, n, d * (0.95 if who is reed else 0.85), 84 + rng.randint(-8, 6))
        if who is reed:   # the piano comps under the reed's four bars
            comp(ep, part, style='citypop2', vel=50, lo=50, hi=66, n=3)
t += 32

# ---- B on the strings, the reed answering
ch = prog(tprog(CHORDS_B, K), at=t)
band(ch, t, 8, kv=0.78)
play(strings, mel(THEME_B, K), at=t, vel=74, legato=True)
for b0 in (6.5, 14.5, 22.5, 30.0):
    play(reed, shift(mel([(0.0, 'A4', 0.5), (0.5, 'G4', 0.5), (1.0, 'E4', 1.0)], K), t + b0 - 0.5), vel=72)
fill(kit, t + 32, 'roll', 0.8)
t += 32

# ---- B again, the vibes improvise over it; the drums go to the ride
ch = prog(tprog(CHORDS_B, K), at=t)
band(ch, t, 8, kv=0.74)
line = improvise(ch, KEY, seed=1130, lo=65, hi=89, density=0.8)
for b, n, d in line:
    vibes.note(b, n, d * 0.9, 72 + rng.randint(-6, 6))
fill(kit, t + 32, 'snare', 0.8)
t += 32

# ---- the last A, a semitone up (D): reed and clarinet, strings, the piano on top
K2 = K + 1
ch = prog(tprog(RA, K2), at=t)
band(ch, t, 8, kv=0.86)
TA2 = mel(THEME_A, K2 - 12)
play(reed, TA2, at=t, vel=90, legato=True)
KEY2 = [(x + K2) % 12 for x in C_MAJOR]
play(clar, [(b, p - 9 if (p - 9) % 12 in KEY2 else p - 8, d) for b, p, d in TA2], at=t, vel=74, legato=True)
sustain(strings, ch, vel=48, lo=60, hi=84, n=3)
kit.note(t, CRASH, 2, 86)
t += 32
for s, d, sym in prog(tprog('Dm9:4 | G13sus4:2 G7alt:2 | Fmaj9:8', K2), at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 52, 77)):
        ep.note(s + j * 0.05, n, d * 0.95, 60)
    bass.note(s, root(sym, 1) + 12, d * 0.9, 84)
kit.note(t + 8, RIDE, 3, 60)
glasses.note(t + 10, 60, 4, 76)
t += 20
texture(room, 0, t, note=60, vel=70, bpm=BPM, seconds=26)

F = Feel(11011)
for p, lay, jit in ((reed, 18, 10), (clar, 18, 10), (ep, 6, 8), (bass, 5, 5), (vibes, 8, 8), (strings, 10, 6)):
    F.apply(S, p, lay_ms=lay, jit_ms=jit, vel=4, swing=0.6, grid=0.5)
F.apply(S, kit, jit_ms=4, vel=4)
F.apply(S, perc, jit_ms=6, vel=5)

finish(__file__, S, {
    'title': 'Var. X: Last Call at the Listening Bar',
    'track': 11,
    'note': 'Jazz-funk in D-flat at 88, swung: the theme over tritone substitutions, sixteen bars of electric piano, '
            'reed and piano trading fours, B on strings, the last A a semitone up; glasses on the counter.',
}, [
    ('room', 'ch13', 'City Hush', dict(lufs=-36)),
    ('glasses', 'ch7', 'Glasses on the Counter', dict(lufs=-30, pan=36, verb=0.3)),
    ('ep', 'ch1', 'Loft Tine', dict(lufs=-18, pan=-10, verb=0.22, echo=0.05)),
    ('bass', 'ch2', 'Pluck Avenue', dict(lufs=-20, vel=0.75)),
    ('reed', 'ch3', 'Harbour Reed', dict(lufs=-19, pan=14, verb=0.28, echo=0.12)),
    ('clarinet', 'ch4', 'Clarinet After Hours', dict(lufs=-24, pan=-24, verb=0.3)),
    ('strings', 'ch5', 'Velvet Strings', dict(lufs=-26, pan=32, verb=0.45)),
    ('vibes', 'ch6', 'Lobby Vibraphone', dict(lufs=-25, pan=40, verb=0.35, echo=0.15)),
    ('kit', 'ch10', 'Loft Sticks', dict(lufs=-22, verb=0.12)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-32, pan=-30, verb=0.1)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '3/16', 'feedback': 0.28, 'tone': 2800, 'pingpong': 'yes', 'level': -8, 'lowcut': 250},
   reverb={'size': 2.0, 'predelay': 18, 'tone': 5200, 'level': -6, 'seed': 3121})

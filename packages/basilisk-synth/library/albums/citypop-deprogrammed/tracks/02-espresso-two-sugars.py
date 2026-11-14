"""2. Var. I: Espresso, Two Sugars. F major, 96 bpm, a light shuffle. The theme comes apart into its motto: the
vibraphone asks with the pick-up figure, the suitcase piano answers it upside down, the flute plays the whole
tune an eighth late. The machine on the counter starts it and finishes it."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 5                       # F
BPM = 96
SW8 = 0.33
S = Score(bpm=BPM, seed=202)
ep = S.part('ep', 1); bass = S.part('bass', 2); flute = S.part('flute', 3); vibes = S.part('vibes', 4)
horn = S.part('horn', 5); organ = S.part('organ', 6); kit = S.part('kit', 10); perc = S.part('perc', 11)
cafe = S.part('cafe', 12); room = S.part('room', 13); vinyl = S.part('vinyl', 14)
rng = random.Random(22)
KEY = [(x + K) % 12 for x in C_MAJOR]

A = tprog('Fmaj7 | Em7 A7b9 | Dm9 | G13 G7b9 | Fmaj7 | E7#9 | Am9 D9 | Dm9 G13', K)
B = tprog(CHORDS_B, K)
VAMP = tprog('Dm9 | G13 | Dm9 | G13 | Em7 | A7#9 | Dm9 | G13sus4 G13', K)
head = mel(HEAD, K)                       # C5 F5 G5 A5 ...
head_inv = invert(mel(HEAD, 0), 'E5')     # the motto upside down (in C), then moved to F
head_inv = [(b, p + K - 12, d) for b, p, d in head_inv]


def band(ch, t, bars, kit_style='shuffle', kv=0.8, bass_style='shuffle', ep_style='shuffle', ev=60, perc_pat=None, organ_on=True):
    comp(ep, ch, style=ep_style, vel=ev, lo=53, hi=74, rng=rng, var=0.12)
    bassline(bass, ch, style=bass_style, vel=92, rng=rng, var=0.25)
    drums(kit, kit_style, t, bars, vel=kv, swing8=SW8)
    drums(perc, perc_pat or {SHAKER: 'x.o.x.o.x.o.x.o.', SNAP: '....x.......x...'}, t, bars, vel=0.55, swing8=SW8)
    if organ_on:
        sustain(organ, ch, vel=34, lo=53, hi=70, n=3)


t = 0.0
# ---- intro (4): the machine, a cup, the piano finds the key; hats from bar 3
cafe.note(0.0, 60, 15.5, 96)               # Espresso Bar: the shot pulled (one-shot, fixed pitch)
spoon = S.part('spoon', 9); spoon.note(9.0, 60, 6.0, 90)
ch = prog('|'.join(A.split('|')[:4]), at=t)
comp(ep, ch, style='shuffle', vel=52, lo=53, hi=72, rng=rng)
drums(kit, {CHH: 'x.x.x.x.x.x.x.x.'}, 8.0, 2, vel=0.6, swing8=SW8)
fill(kit, 16.0, 'flam', 0.6, 1.0)
t = 16.0

# ---- 1: question and answer on the motto (vibes / piano), the flute's small counter
ch = prog(A, at=t)
band(ch, t, 8, kv=0.7)
for k in (0, 16):
    play(vibes, shift(head, t + k), vel=80)
    play(ep, shift(head_inv, t + k + 4.5), vel=74)
    play(flute, shift([(0.0, pitch('A5') + K - 5, 0.5), (0.5, pitch('G5') + K - 5, 0.5), (1.0, pitch('E5') + K - 5, 1.0)], t + k + 10.5), vel=70)
fill(kit, t + 32, 'snare', 0.7)
t += 32

# ---- 2: the flute plays the whole of A, an eighth late
ch = prog(A, at=t)
band(ch, t, 8, kv=0.78)
play(flute, grace(shift(mel(THEME_A, K), 0.5)), at=t, vel=84, legato=True)
for b0 in (3.5, 11.5, 19.5, 27.5):
    vibes.note(t + b0, pitch('A5') + K - 12 + 12, 0.4, 56)
kit.note(t, CRASH, 2, 72)
fill(kit, t + 32, 'toms', 0.7)
t += 32

# ---- 3: B on the muted trumpet; the piano lays back to halves
ch = prog(B, at=t)
band(ch, t, 8, kv=0.75, ep_style='halves')
play(horn, mel(THEME_B, K - 12), at=t, vel=84, legato=True)
play(vibes, shift(mel([(0.0, 'D5', 0.5), (0.5, 'F5', 0.5), (1.0, 'A5', 1.0)], K), t + 14), vel=60)
play(vibes, shift(mel([(0.0, 'E5', 0.5), (0.5, 'G5', 0.5), (1.0, 'C6', 1.0)], K), t + 30), vel=60)
fill(kit, t + 32, 'snare', 0.75)
t += 32

# ---- 4: vibraphone chorus (eight bars), then the piano's (eight), the first two bars of it in stop-time
for k, (who, lo_, hi_) in enumerate(((vibes, 65, 89), (ep, 62, 84))):
    ch = prog(A, at=t)
    line = improvise(ch, KEY, seed=200 + k, lo=lo_, hi=hi_, density=0.85, motif=shift(head if k == 0 else head_inv, t))
    for b, n, d in line:
        who.note(b, n, d * 0.9, 76 + rng.randint(-8, 6))
    if k == 1:
        hits = prog(A, at=t)    # stop-time: the band hits and holds its breath
        for b0 in (0.0, 1.5, 4.0, 5.5):
            sym = next(s for s0, d0, s in hits if s0 <= t + b0 < s0 + d0)
            for n in voice(tones(sym, 3), None, 52, 66):
                organ.note(t + b0, n, 0.5, 64)
            bass.note(t + b0, root(sym, 2), 0.45, 100)
            kit.note(t + b0, KICK, 0.3, 100); kit.note(t + b0, CRASH if b0 == 0 else OHH, 0.4, 80)
        band(prog(A, at=t + 8)[3:], t + 8, 6, kv=0.82)
        comp(ep, prog(A, at=t + 8)[3:], style='halves', vel=46, lo=48, hi=62, n=3)
    else:
        band(ch, t, 8, kv=0.8, organ_on=False)
    t += 32

# ---- break (4): bass, kit and snaps alone
ch = prog(tprog('Dm9 | G13 | Dm9 | G13 G7b9', K), at=t)
bassline(bass, ch, style='shuffle', vel=96, rng=rng, var=0.1)
drums(kit, 'shuffle', t, 4, vel=0.78, swing8=SW8, drop=(CHH,))
drums(perc, {SNAP: '....x.......x...', SHAKER: 'x.o.x.o.x.o.x.o.'}, t, 4, vel=0.7, swing8=SW8)
fill(kit, t + 16, 'roll', 0.8)
t += 16

# ---- 5: B again, flute and trumpet in sixths
ch = prog(B, at=t)
band(ch, t, 8, kv=0.8)
play(flute, mel(THEME_B, K), at=t, vel=82, legato=True)
low = [(b, p - 9 if (p - 9) % 12 in KEY else p - 8, d) for b, p, d in mel(THEME_B, K)]
play(horn, low, at=t, vel=70, legato=True)
kit.note(t, CRASH, 2, 76)
t += 32

# ---- 6: A with everyone: flute and vibes in octaves, the trumpet answers
ch = prog(A, at=t)
band(ch, t, 8, kv=0.84)
play(flute, grace(mel(THEME_A, K)), at=t, vel=88, legato=True)
play(vibes, mel(THEME_A, K - 12), at=t, vel=64, gate=0.7)
for b0, ns in ((3.0, ['C5', 'D5', 'F5']), (11.0, ['A4', 'C5', 'D5']), (19.5, ['G#4', 'B4', 'D5']), (27.0, ['F4', 'G4', 'A4'])):
    for i, n in enumerate(ns):
        horn.note(t + b0 + i * 0.5, pitch(n) + K, 0.45, 72)
kit.note(t, CRASH, 2, 80)
fill(kit, t + 32, 'toms', 0.75)
t += 32

# ---- tag (8): the motto over a vamp, getting quieter; the machine again
ch = prog(VAMP, at=t)
band(ch, t, 8, kv=0.72, ep_style='halves')
for k in range(4):
    play(vibes if k % 2 == 0 else flute, shift(head, t + 8 * k), vel=74 - 6 * k)
fade(ep, t, t + 32, 1.0, 0.7); fade(kit, t, t + 32, 1.0, 0.55); fade(perc, t, t + 32, 1.0, 0.5)
cafe.note(t + 20, 60, 14, 80)
t += 32
last = prog(tprog('Fmaj9:8', K), at=t)
for s, d, sym in last:
    for j, n in enumerate(voice(tones(sym, 5), None, 53, 77)):
        ep.note(s + j * 0.08, n, 7, 54)
    bass.note(s, root(sym, 1) + 12, 6, 80)
    vibes.note(s + 0.5, pitch('C6') + K - 12, 4, 50)
kit.note(t, RIDE, 2, 46)
spoon.note(t + 3, 60, 5, 70)
t += 10

texture(room, 0, t, note=60, vel=74, bpm=BPM, seconds=26)
texture(vinyl, 0, t, note=60, vel=66, bpm=BPM, seconds=26)

F = Feel(2022)
for p, lay, jit in ((flute, 16, 9), (horn, 14, 9), (vibes, 6, 7), (ep, 4, 6), (bass, 5, 5), (organ, 6, 6)):
    F.apply(S, p, lay_ms=lay, jit_ms=jit, vel=4, swing=0.66, grid=0.5)
F.apply(S, kit, jit_ms=4, vel=4)
F.apply(S, perc, jit_ms=6, vel=6)

finish(__file__, S, {
    'title': 'Var. I: Espresso, Two Sugars',
    'track': 2,
    'note': 'The theme in F, as a light shuffle: the motto traded between vibraphone and suitcase piano (once as '
            'written, once upside down), the flute an eighth late, muted trumpet on B, two choruses, a stop-time.',
}, [
    ('room', 'ch13', 'City Hush', dict(lufs=-36)),
    ('vinyl', 'ch14', 'Vinyl Dust', dict(lufs=-40, hp=150)),
    ('cafe', 'ch12', 'Espresso Bar', dict(lufs=-30, pan=-35, verb=0.15)),
    ('spoon', 'ch9', 'Cup and Spoon', dict(lufs=-32, pan=30, verb=0.15)),
    ('ep', 'ch1', 'Suitcase Night', dict(lufs=-19, pan=-14, verb=0.2)),
    ('bass', 'ch2', 'Pluck Avenue', dict(lufs=-20)),
    ('flute', 'ch3', 'Night Flute', dict(lufs=-20, pan=10, verb=0.3, echo=0.12)),
    ('vibes', 'ch4', 'courtyard-chapel:Delta Tower', dict(lufs=-21, pan=24, verb=0.25, echo=0.1)),
    ('horn', 'ch5', 'Harmon Glow', dict(lufs=-21, pan=-8, verb=0.3, echo=0.08)),
    ('organ', 'ch6', 'tape-parlour:Night Stops', dict(lufs=-29, pan=16, verb=0.2)),
    ('kit', 'ch10', 'Loft Sticks', dict(lufs=-20, verb=0.1)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-27, pan=-24, verb=0.12)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '1/8', 'feedback': 0.28, 'tone': 3000, 'pingpong': 'yes', 'level': -7, 'lowcut': 220},
   reverb={'size': 1.8, 'predelay': 16, 'tone': 5500, 'level': -6, 'seed': 3112})

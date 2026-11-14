"""6. Var. V: Neon Waltz. A-flat major, 3/4 at 120. The theme put into waltz time: each of its bars becomes two,
and the pick-up becomes the second and third beats. A glass piano and a folk harp, pizzicato bass on the one,
brushes on two and three, strings that swell where the theme leaps. Halfway through, a harmonica has the tune a
tone higher."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 8 - 12                   # A-flat
BPM = 120
BAR = 3.0
S = Score(bpm=BPM, seed=606)
glass = S.part('glass', 1); harp = S.part('harp', 2); bass = S.part('bass', 3); strings = S.part('strings', 4)
flute = S.part('flute', 5); harm = S.part('harmonica', 6); box = S.part('box', 7); kit = S.part('kit', 10)
perc = S.part('perc', 11); night = S.part('night', 13)
rng = random.Random(66)

WA = [(1, 'G4', 1), (2, 'C5', 1), (3, 'D5', 1), (4, 'E5', 2), (6, 'G5', 1), (7, 'A5', 2), (9, 'G5', 1), (10, 'E5', 1),
      (11, 'C#5', 1), (12, 'D5', 1), (13, 'E5', 1), (14, 'F5', 1), (15, 'A5', 1), (16, 'C6', 2), (18, 'A5', 2), (20, 'G5', 1),
      (21, 'E5', 1), (22, 'F5', 0.5), (22.5, 'D5', 0.5), (23, 'B4', 1), (25, 'G4', 1), (26, 'C5', 1), (27, 'D5', 1),
      (28, 'E5', 2), (30, 'A5', 1), (31, 'G#5', 2), (33, 'G5', 1), (34, 'F5', 1), (35, 'E5', 1), (36, 'C5', 2), (38, 'B4', 1),
      (39, 'A4', 1), (40, 'F#4', 1), (41, 'E4', 1), (42, 'A4', 2), (44, 'G4', 1), (45, 'F4', 1), (46, 'E4', 2)]
WCH = 'Fmaj7 | Fmaj7 | Em7 | A7 | Dm9 | Dm9 | G13 | G13 | Fmaj7 | Fmaj7 | E7#9 | E7 | Am9 | D9 | Dm9 | G13'
WB_CH = 'Bbmaj7 | Bbmaj7 | Am7 | D7 | Gm9 | Gm9 | C13 | C13 | Abmaj7 | Abmaj7 | G7sus4 | G7 | Cmaj9 | Cmaj9 | Dm9 | G13'
WB = [(round(b * 1.5 * 2) / 2, p, max(0.5, round(d * 1.5 * 2) / 2)) for b, p, d in mel(THEME_B, 0)]


def waltz_band(ch, t, bars, kv=0.7, harp_on=True, st=True):
    for s, d, sym in ch:
        r = root(sym, 2) + 12
        bass.note(s, r, 1.6, 90)
        if d > 2:
            bass.note(s + 2, r + 7 if r + 7 <= 52 else r - 5, 0.8, 64)
    if harp_on:
        arp(harp, ch, step=0.5, vel=56, lo=55, hi=86, pattern=(0, 1, 2, 3, 4, 2), gate=2.4)
    if st:
        sustain(strings, ch, vel=44, lo=56, hi=84, n=4)
    for b in range(bars):
        tb = t + b * BAR
        kit.note(tb, KICK, 0.4, int(80 * kv)); kit.note(tb + 1, SNARE, 0.4, int(62 * kv)); kit.note(tb + 2, SNARE, 0.4, int(56 * kv))
        kit.note(tb + 1.5, SNARE2, 0.3, int(36 * kv)); kit.note(tb + 2.5, SNARE2, 0.3, int(32 * kv))
        perc.note(tb, SHAKER, 0.2, 54); perc.note(tb + 1, SHAKER, 0.2, 44); perc.note(tb + 2, SHAKER, 0.2, 44)
        if b % 4 == 0:
            perc.note(tb, TRI, 1.0, 50)


t = 0.0
# ---- intro (8): the music box turns over the first chords
ch = prog(tprog('Fmaj7 | Fmaj7 | Em7 | A7 | Dm9 | Dm9 | G13 | G13', K), at=t, bar=BAR)
arp(box, ch, step=0.5, vel=60, lo=72, hi=96, pattern=(0, 2, 1, 3, 2, 4), gate=2)
for s, d, sym in ch[4:]:
    bass.note(s, root(sym, 2) + 12, 1.6, 78)
t += 8 * BAR

# ---- A: the glass piano
ch = prog(tprog(WCH, K), at=t, bar=BAR)
waltz_band(ch, t, 16, st=False)
play(glass, mel(WA, K + 12), at=t, vel=80)
t += 16 * BAR

# ---- A: the flute, the strings come up under it
ch = prog(tprog(WCH, K), at=t, bar=BAR)
waltz_band(ch, t, 16, kv=0.76)
play(flute, grace(mel(WA, K + 12)), at=t, vel=80, legato=True)
for b0, n in ((7, 'C6'), (16, 'E6'), (31, 'B5'), (36, 'E6')):
    glass.note(t + b0, pitch(n) + K, 1.8, 54)
t += 16 * BAR

# ---- B in waltz time: strings have it, the harp keeps turning
ch = prog(tprog(WB_CH, K), at=t, bar=BAR)
waltz_band(ch, t, 16, kv=0.72, st=False)
play(strings, mel(WB, K + 12), at=t, vel=76, legato=True)
sustain(strings, ch, vel=40, lo=56, hi=76, n=3)
t += 16 * BAR

# ---- the glass piano's chorus (16), the harp under it
ch = prog(tprog(WCH, K), at=t, bar=BAR)
waltz_band(ch, t, 16, kv=0.74, st=False)
line = improvise(ch, [(x + K) % 12 for x in C_MAJOR], seed=606, lo=67, hi=91, density=0.8, bar=BAR,
                 cells=[[(0, 1), (1, 1), (2, 1)], [(0, 2), (2, 1)], [(0, 1.5), (1.5, 0.5), (2, 1)], [(1, 1), (2, 0.5), (2.5, 0.5)]])
for b, n, d in line:
    glass.note(b, n, d * 0.9, 72 + rng.randint(-6, 6))
t += 16 * BAR

# ---- the strings alone (8), a turn toward the new key
ch = prog(tprog('Dm9 | Dm9 | G13 | G13 | Em7 | A7 | Dm9 | G7sus4', K + 2), at=t, bar=BAR)
sustain(strings, ch, vel=60, lo=55, hi=84, n=4)
arp(harp, ch, step=0.5, vel=46, lo=55, hi=86, pattern=(0, 1, 2, 3, 4, 2), gate=2.4)
for s, d, sym in ch:
    bass.note(s, root(sym, 2) + 12, 1.6, 78)
t += 8 * BAR

# ---- A a tone higher: the harmonica, the glass piano answering in thirds
K2 = K + 2
ch = prog(tprog(WCH, K2), at=t, bar=BAR)
waltz_band(ch, t, 16, kv=0.8)
play(harm, mel(WA, K2 + 12), at=t, vel=84, legato=True)
thirds = [(b, p - 3 if (p - 3) % 12 in [(x + K2) % 12 for x in C_MAJOR] else p - 4, d) for b, p, d in mel(WA, K2 + 12)]
play(glass, shift(thirds, 0.0), at=t, vel=60)
t += 16 * BAR

# ---- B again in the new key; the flute and the harmonica share it
ch = prog(tprog(WB_CH, K2), at=t, bar=BAR)
waltz_band(ch, t, 16, kv=0.76)
half = len(WB) // 2
play(flute, mel(WB[:half], K2 + 12), at=t, vel=78, legato=True)
play(harm, mel(WB[half:], K2 + 12), at=t, vel=80, legato=True)
t += 16 * BAR

# ---- A home again (A-flat), quieter; the music box takes the last phrase
ch = prog(tprog(WCH, K), at=t, bar=BAR)
waltz_band(ch, t, 16, kv=0.66, st=True)
play(glass, mel(WA[:24], K + 12), at=t, vel=74)
play(box, mel(WA[24:], K + 24), at=t, vel=64)
fade(harp, t + 24, t + 48, 1.0, 0.5); fade(kit, t + 24, t + 48, 1.0, 0.4)
t += 16 * BAR
for s, d, sym in prog(tprog('Fmaj9:9', K), at=t, bar=BAR):
    for j, n in enumerate(voice(tones(sym, 5), None, 56, 80)):
        glass.note(s + j * 0.15, n, 6, 56); strings.note(s, n, 7, 40)
    bass.note(s, root(sym, 1) + 12, 4, 72)
    box.note(s + 3, pitch('C6') + K + 12, 3, 50)
t += 12
texture(night, 0, t, note=60, vel=70, bpm=BPM, seconds=26)

F = Feel(6066)
F.apply(S, glass, lay_ms=10, jit_ms=8, vel=4)
F.apply(S, flute, lay_ms=16, jit_ms=9, vel=4)
F.apply(S, harm, lay_ms=16, jit_ms=9, vel=4)
F.apply(S, harp, lay_ms=0, jit_ms=8, vel=6)
F.apply(S, bass, lay_ms=4, jit_ms=5, vel=4)
F.apply(S, kit, jit_ms=6, vel=5)
F.apply(S, perc, jit_ms=8, vel=6)

finish(__file__, S, {
    'title': 'Var. V: Neon Waltz',
    'track': 6,
    'note': 'The theme in waltz time (each bar becomes two) in A-flat at 120: glass piano, folk harp, pizzicato bass, '
            'brushes, a music box; a harmonica takes it a tone higher; B on strings.',
}, [
    ('night', 'ch13', 'Night Insects', dict(lufs=-38)),
    ('glass', 'ch1', 'Glass Tine', dict(lufs=-19, pan=-14, verb=0.3, echo=0.08)),
    ('harp', 'ch2', 'courtyard-chapel:Faded Pluck', dict(lufs=-24, pan=34, verb=0.3)),
    ('bass', 'ch3', 'Night Pizz Bass', dict(lufs=-21)),
    ('strings', 'ch4', 'dna:violin_section_sus_c4@t7500]@t200[#8Vw3,4/cello_section_sus_c3@t7500]@t200[#8T12L70Vw3,4;A240S95R900V70K60', dict(lufs=-24, pan=-36, verb=0.45)),
    ('flute', 'ch5', 'Night Flute', dict(lufs=-19, pan=12, verb=0.35, echo=0.12)),
    ('harmonica', 'ch6', 'tape-parlour:Hollow Revival', dict(lufs=-20, pan=4, verb=0.3, echo=0.1)),
    ('box', 'ch7', 'courtyard-chapel:Late Ladder', dict(lufs=-26, pan=42, verb=0.45, echo=0.2)),
    ('kit', 'ch10', 'Loft Brushes', dict(lufs=-26, verb=0.15)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-31, pan=-28, verb=0.2)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '1/4', 'feedback': 0.3, 'tone': 2800, 'pingpong': 'yes', 'level': -8, 'lowcut': 250},
   reverb={'size': 2.6, 'predelay': 22, 'tone': 5200, 'level': -5, 'seed': 3116})

"""Between Meetings: an original ambient piece, 72 bpm, D major. Waves, a singing-bowl drone, a string pad, a
marimba ostinato, glockenspiel, a breathy flute tune and a hermit thrush."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=72, seed=1999)
waves = S.part('waves', 1)
drone = S.part('drone', 2)
pad = S.part('pad', 3)
organ = S.part('organ', 4)
marimba = S.part('marimba', 5)
glock = S.part('glock', 6)
flute = S.part('flute', 7)
bird = S.part('bird', 8)
bell = S.part('bell', 9)
creek = S.part('creek', 11)

PROG = 'Dmaj7 Bm7 Gmaj7 Asus4'
GLOCK = 'h F#5 A5 | w E5 | h D5 B4 | w C#5'
FLUTE = 'h. A5 q F#5 | w F#5 | h. B5 q A5 | h E5 F#5 | h. A5 q D6 | w C#6 | h B5 A5 | w A5'


def ostinato(at, bars, vel=62):
    t, prev = at, None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG.split()[k % 4], 4), 57, 74); prev = ns
        seq = [ns[0], ns[2], ns[1], ns[3] if len(ns) > 3 else ns[0] + 12, ns[2], ns[1], ns[2], ns[0] + 12]
        for i in range(8):
            marimba.note(t + i * 0.5, seq[i], 0.45, vel - (0 if i % 4 == 0 else 10))
        t += 4


t = 0.0
hold(waves, 0, 60, 32, 84)
hold(drone, 0, 50, 30, 70); hold(drone, 2, 57, 28, 60)
pad.chords(' '.join([PROG] * 2), at=8, beats=4, style='pad', vel=60, lo=55, hi=72)
t = 32
# A (8): the marimba starts, the glockenspiel answers
ostinato(t, 8); pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
glock.mel(GLOCK, at=t + 16, vel=70)
hold(drone, t, 50, 31, 64)
t += 32
# B (8): the flute
ostinato(t, 8, 58); pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
flute.mel(FLUTE, at=t, vel=86, tr=-12)
organ.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=52, lo=50, hi=66)
bell.note(t + 28, 81, 3, 60)
hold(creek, t, 60, 32, 70)
t += 32
# C (8): everyone, the thrush
ostinato(t, 8, 64); pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=60, lo=55, hi=72)
flute.mel(FLUTE, at=t, vel=90, tr=-12)
glock.mel(GLOCK + ' | ' + GLOCK, at=t, vel=64)
organ.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=54, lo=50, hi=66)
for k, b in enumerate((2, 9, 13, 21, 26)):
    bird.note(t + b, 89, 0.6, 80 - 4 * k)
hold(waves, t, 60, 32, 80)
hold(drone, t, 50, 31, 66)
t += 32
# outro (8): the marimba thins out, the waves stay
ostinato(t, 4, 54)
pad.chords('Dmaj7:8 Gmaj7:8 Dmaj7:16', at=t, style='pad', vel=56, lo=55, hi=72)
glock.mel('h F#5 A5 | w E5 | w D5', at=t + 16, vel=60)
bell.note(t + 24, 86, 4, 56)
hold(waves, t, 60, 34, 76); hold(drone, t, 50, 32, 62)
t += 32

S.humanize(ms=10, vel=5, parts=['marimba', 'glock', 'flute'])
finish(__file__, S, {
    'title': 'Between Meetings',
    'pack': 'screen-saver',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Ambient in D major, 72 bpm: ocean waves, a singing-bowl drone, string pad, pipe-organ pad, marimba '
            'ostinato, glockenspiel, a breathy flute tune, a creek and a hermit thrush.',
}, [
    ('waves', 'ch1', 'Ocean Shelf', dict(lufs=-28, width=1.4)),
    ('drone', 'ch2', 'Northern Dormant', dict(lufs=-27, verb=0.3)),
    ('pad', 'ch3', 'Global Pad', dict(lufs=-24, verb=0.45, width=1.4)),
    ('organ', 'ch4', 'Opal Bloom', dict(lufs=-27, pan=-15, verb=0.4)),
    ('marimba', 'ch5', 'Water Marimba', dict(lufs=-22, pan=-12, echo=0.3, verb=0.35)),
    ('glock', 'ch6', 'Sunday Chimes', dict(lufs=-24, pan=24, echo=0.35, verb=0.45)),
    ('flute', 'ch7', 'Breath Flute', dict(lufs=-20, pan=6, echo=0.2, verb=0.45)),
    ('bird', 'ch8', 'Thrush Morning', dict(lufs=-27, pan=38, verb=0.35)),
    ('bell', 'ch9', 'Felt Ring', dict(lufs=-26, pan=-30, echo=0.4, verb=0.5)),
    ('creek', 'ch11', 'Creek Bed', dict(lufs=-31, pan=-20, width=1.3)),
], master={'loudness': -17, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.45, 'tone': 3000, 'level': -4},
   reverb={'size': 4.0, 'predelay': 30, 'tone': 5000, 'level': -3})

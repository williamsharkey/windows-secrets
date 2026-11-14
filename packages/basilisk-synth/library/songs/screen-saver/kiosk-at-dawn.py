"""Kiosk at Dawn: an original ambient piece, 64 bpm, F Lydian. Crickets give way to a creek and a morning bird,
singing bowls and a pipe-organ pad open up, a horizon horn plays a long call, the glockenspiel and corner peal
answer, and the mall's ambience comes up as the doors open."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=64, seed=2000)
crickets = S.part('crickets', 1)
creek = S.part('creek', 2)
bird = S.part('bird', 3)
bowl = S.part('bowl', 4)
organ = S.part('organ', 5)
horn = S.part('horn', 6)
glock = S.part('glock', 7)
peal = S.part('peal', 8)
pad = S.part('pad', 9)
mall = S.part('mall', 11)
choir = S.part('choir', 12)

PROG = 'Fmaj7 G6 Em7 Am7'
CALL = 'w A4 | h. G4 q C5 | w B4 | w r | w A4 | h. C5 q D5 | w E5 | w r'

t = 0.0
hold(crickets, 0, 60, 24, 76)
hold(bowl, 4, 53, 20, 64, 10)
t = 16
hold(creek, t, 60, 48, 70)
organ.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=56, lo=53, hi=69)
for k, b in enumerate((3, 11, 22, 37)):
    bird.note(t + b, 89, 0.6, 72 - 3 * k)
horn.mel(CALL, at=t + 8, vel=82)
glock.mel('h. r q E6 | w r | h. r q D6 | w r | h. r q C6 | w r | h. r q B5 | w r', at=t + 8, vel=60)
t += 64
pad.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
choir.chords(' '.join([PROG] * 2), at=t + 32, beats=4, style='pad', vel=52, lo=55, hi=69)
horn.mel(CALL, at=t, vel=86); peal.mel('q E5 G5 B5 E6 | w r | q D5 F#5 A5 D6 | w r ' * 2, at=t + 32, vel=56)
hold(mall, t + 16, 60, 48, 66)
hold(bowl, t, 53, 32, 60, 10)
t += 64
organ.chords('Fmaj7:8 Fmaj7:8', at=t, style='pad', vel=54, lo=53, hi=69)
glock.mel('w A5 | w C6 | w E6 | w F6', at=t, vel=56)
hold(mall, t, 60, 16, 60)
t += 16

finish(__file__, S, {
    'title': 'Kiosk at Dawn',
    'pack': 'screen-saver',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Ambient in F Lydian, 64 bpm: crickets, a creek, a hermit thrush, singing bowls, the pipe-organ pad, a '
            'horizon horn\'s long call, glockenspiel, a corner peal, a string pad and choir, then the shopping-centre '
            'ambience as the doors open.',
    'tail': 6,
}, [
    ('crickets', 'ch1', 'Noble Static', dict(lufs=-30, width=1.4)),
    ('creek', 'ch2', 'Creek Bed', dict(lufs=-30, pan=-20, width=1.3)),
    ('bird', 'ch3', 'Thrush Morning', dict(lufs=-27, pan=36, verb=0.4)),
    ('bowl', 'ch4', 'Granite Dormant', dict(lufs=-27, verb=0.4)),
    ('organ', 'ch5', 'Opal Bloom', dict(lufs=-25, pan=-10, verb=0.45)),
    ('horn', 'ch6', 'Distant Horizon Horn', dict(lufs=-20, pan=6, echo=0.2, verb=0.5)),
    ('glock', 'ch7', 'Sunday Chimes', dict(lufs=-25, pan=26, echo=0.35, verb=0.5)),
    ('peal', 'ch8', 'Corner Peal', dict(lufs=-27, pan=-28, echo=0.3, verb=0.5)),
    ('pad', 'ch9', 'Vinyl Aurora', dict(lufs=-26, verb=0.45, width=1.4)),
    ('mall', 'ch11', 'Daylight Traffic', dict(lufs=-30, width=1.4)),
    ('choir', 'ch12', 'Sunlit Drift', dict(lufs=-27, verb=0.5, width=1.3)),
], master={'loudness': -17, 'ceiling': -1.0, 'fadeout': 3},
   echo={'time': '3/8', 'feedback': 0.45, 'tone': 3000, 'level': -4},
   reverb={'size': 4.0, 'predelay': 30, 'tone': 5000, 'level': -3})

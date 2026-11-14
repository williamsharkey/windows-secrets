"""Compost Heap Hardcore: an original 1993-style hardcore track, 150 bpm, D minor. Taiko on the build, a
breakbeat with the hands kit on top, the rave scream and the hoover, rave-piano stabs a fifth apart, the
mouth-kit, the timpani, a goose-voice chant and the crystal-fantasia pad in the breakdown."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=150, seed=1993)
kit = S.part('kit', 10)
hands = S.part('hands', 9)
taiko = S.part('taiko', 11)
piano = S.part('ravepiano', 1)
hoover = S.part('hoover', 2)
scream = S.part('scream', 3)
organ = S.part('organbass', 4)
pad = S.part('pad', 5)
chant = S.part('chant', 6)
timp = S.part('timpani', 7)
reese = S.part('reese', 8)

PROG = ['Dm', 'Bb', 'C', 'A']
BREAK = [{KICK: 'x.........x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.xx'},
         {KICK: 'x.x.......x..x..', SNARE: '....x..o....x..o', CHH: 'x.x.x.xxx.x.x.x.'}]
HOOV = 'q D4 e D4 F4 q A4 e G4 F4 | q Bb3 e Bb3 D4 q F4 e E4 D4 | q C4 e C4 E4 q G4 e F4 E4 | q A3 e A3 C#4 q E4 e D4 C#4'


def breaks(at, bars):
    for k in range(bars):
        kit.drums(BREAK[k % 2] if k % 8 != 7 else {KICK: 'x.........x.....', SNARE: '....x.xxo.xxXxXX'}, at=at + 4 * k, bars=1)
    hands.drums({37: '..x...x...x..x..', 39: '....x.......x...'}, at=at, bars=bars, vel={'x': 70})


def stabs(at, bars, vel=90):
    for k in range(bars):
        r = root_of(PROG[k % 4], 4)
        for off in (0, 0.75, 1.5, 2.5, 3.25):
            piano.note(at + 4 * k + off, r, 0.35, vel); piano.note(at + 4 * k + off, r + 7, 0.35, vel - 10)


def organ_bass(at, bars):
    for k in range(bars):
        r = root_of(PROG[k % 4], 2)
        for j in range(8):
            organ.note(at + 4 * k + j * 0.5, r + (12 if j % 2 else 0), 0.4, 98)


t = 0.0
taiko.drums({36: 'x.......x.......', 38: '....x.......x.x.'}, at=0, bars=8, vel={'x': 96})
pad.chords('Dm Bb C A Dm Bb C A', at=0, beats=4, style='pad', vel=60, lo=55, hi=72)
chant.mel('w D5 | w D5 | w F5 | w E5', at=16, vel=84)
t = 32
scream.note(t, 36, 1.5, 100); kit.note(t, CRASH, 2, 116)
breaks(t, 16); organ_bass(t, 16); stabs(t, 16)
timp.drums({36: 'x...x.x.........', 38: '..............x.'}, at=t, bars=16, vel={'x': 86})
t += 64
breaks(t, 16); organ_bass(t, 16)
for k in range(4):
    hoover.mel(HOOV, at=t + 16 * k, vel=102)
scream.note(t + 30, 36, 1.5, 96); scream.note(t + 62, 36, 1.5, 100)
t += 64
# breakdown
pad.chords('Dm Bb C A Dm Bb C A', at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
chant.mel('w D5 | w D5 | w F5 | w E5 | w D5 | w F5 | w G5 | w E5', at=t, vel=84)
taiko.drums({36: 'x...............'}, at=t, bars=8, vel={'x': 90})
reese.chords('Dm Bb C A Dm Bb C A', at=t, beats=4, style='pad', vel=70, lo=38, hi=50)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=t + 24, bars=2, vel={'x': 84})
t += 32
scream.note(t, 36, 1.5, 104); kit.note(t, CRASH, 2, 118)
breaks(t, 16); organ_bass(t, 16); stabs(t, 16, 92)
for k in range(4):
    hoover.mel(HOOV, at=t + 16 * k, vel=104)
t += 64
piano.note(t, pitch('D4'), 1, 100); piano.note(t, pitch('A4'), 1, 90); kit.note(t, KICK, 1, 110); scream.note(t, 36, 1.5, 100)

finish(__file__, S, {
    'title': 'Compost Heap Hardcore',
    'pack': 'garden-rhythm',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Early-90s hardcore in D minor, 150 bpm: taiko on the build, breakbeats from the radio kit with the hands '
            'kit on top, rave-piano fifths, rave-organ bass, the hoover riff, the scream, timpani, a goose-voice chant, '
            'a reese and the crystal-fantasia pad in the breakdown. All from the pack.',
}, [
    ('kit', 'ch10', 'Humid Haze', dict(lufs=-17, verb=0.05)),
    ('hands', 'ch9', 'Wired Drift', dict(lufs=-24, pan=24, verb=0.1)),
    ('taiko', 'ch11', 'Gentle Bloom', dict(lufs=-20, verb=0.3)),
    ('ravepiano', 'ch1', 'Rural Brass', dict(lufs=-20, pan=-10, verb=0.2)),
    ('hoover', 'ch2', 'Lagoon Stab', dict(lufs=-20, pan=6, width=1.3, verb=0.15)),
    ('scream', 'ch3', 'Global Salute', dict(lufs=-23, echo=0.3, verb=0.3)),
    ('organbass', 'ch4', 'Brass Blast', dict(lufs=-20)),
    ('pad', 'ch5', 'Electric Canopy', dict(lufs=-26, verb=0.35, width=1.4)),
    ('chant', 'ch6', 'Warm Chant', dict(lufs=-22, echo=0.3, verb=0.35)),
    ('timpani', 'ch7', 'Lucid Haze', dict(lufs=-24, verb=0.3)),
    ('reese', 'ch8', 'Electric Stab', dict(lufs=-24, width=1.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3500, 'level': -4},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 5500, 'level': -6})

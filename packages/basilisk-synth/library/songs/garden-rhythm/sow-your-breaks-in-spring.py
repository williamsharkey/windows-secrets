"""Sow Your Breaks in Spring: an original early-90s rave track, 140 bpm, A minor. A talking machine says hello,
taiko hits, then breakbeats, the rave piano, organ bass, the hoover riff and a scream; a steelpan breakdown with a
robot choir, and a tabla kit on top for the last run."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=140, seed=1992)
kit = S.part('kit', 10)
taiko = S.part('taiko', 9)
tabla = S.part('tabla', 11)
piano = S.part('ravepiano', 1)
organ = S.part('organbass', 2)
hoover = S.part('hoover', 3)
scream = S.part('scream', 4)
pad = S.part('pad', 5)
hello = S.part('hello', 6)
robot = S.part('robot', 7)
pan = S.part('steelpan', 8)
shaker = S.part('shaker', 12)

PROG = 'Am F C G'
HOOVER = 'q A3 e A3 C4 q E4 e D4 C4 | q A3 e A3 C4 q G4 e E4 D4 | q F3 e F3 A3 q C4 e A3 F3 | q G3 e G3 B3 q D4 e B3 G3'
PAN = 'q E5 e A5 G5 q E5 C5 | h D5 q C5 A4 | q E5 e G5 A5 q C6 A5 | w G5'
BREAKS = [{KICK: 'x.........x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.xx'},
          {KICK: 'x.x.......x.....', SNARE: '....x..o....x..o', CHH: 'x.x.x.xxx.x.x.x.'},
          {KICK: 'x.........x..x..', SNARE: '....x.......x.o.', CHH: 'x.xxx.x.x.xxx.x.'},
          {KICK: 'x.........x.....', SNARE: '....x..x.x..xxxx', CHH: 'x.x.x.x.x.x.....'}]


def breaks(at, bars):
    for k in range(bars):
        kit.drums(BREAKS[k % 4] if k % 8 != 7 else BREAKS[3], at=at + 4 * k, bars=1)
    shaker.drums({61: 'oxoxoxoxoxoxoxox'}, at=at, bars=bars, vel={'x': 60, 'o': 40})


def rave_piano(at, bars, vel=88):
    t, prev = at, None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG.split()[k % 4], 5), 64, 79); prev = ns
        for off in (0, 0.75, 1.5, 2.5, 3.25):
            for n in ns:
                piano.note(t + off, n, 0.35, vel - (8 if off in (0.75, 3.25) else 0))
        t += 4


def organ_bass(at, bars, vel=98):
    bass_pat = [(0, 0, 0.4), (0.5, '8', 0.2), (1, 0, 0.4), (1.5, '8', 0.2), (2, 0, 0.4), (2.5, '8', 0.2), (3, 0, 0.4), (3.5, '8', 0.2)]
    organ.bass(' '.join([PROG] * (bars // 4)), at=at, beats=4, pattern=bass_pat, vel=vel, octave=2)


t = 0.0
# intro (8): the pad, hello, the taiko
pad.chords(' '.join([PROG] * 2), at=0, beats=4, style='pad', vel=62, lo=55, hi=72)
hello.note(2, 60, 3, 90); hello.note(18, 60, 3, 86)
taiko.drums({36: 'x...............', 38: '............x.x.'}, at=16, bars=4, vel={'x': 100})
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=24, bars=2, vel={'x': 80})
t = 32
# A (16): breaks, the rave piano, organ bass
kit.note(t, CRASH, 2, 116); scream.note(t, 36, 1.5, 96)
breaks(t, 16); rave_piano(t, 16); organ_bass(t, 16)
t += 64
# B (8): the hoover riff, a scream every four bars
breaks(t, 8); organ_bass(t, 8, 100)
hoover.mel(HOOVER, at=t, vel=100); hoover.mel(HOOVER, at=t + 16, vel=104)
scream.note(t + 14, 36, 1.5, 92); scream.note(t + 30, 36, 1.5, 96)
pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=54, lo=55, hi=72)
t += 32
# break (8): steelpan, the robot choir, taiko
pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
pan.mel(PAN, at=t, vel=88); pan.mel(PAN, at=t + 16, vel=92)
robot.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=62, lo=55, hi=69)
taiko.drums({36: 'x.......x.......', 38: '....x.......x.x.'}, at=t + 16, bars=4, vel={'x': 92})
hello.note(t + 28, 60, 3, 92)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=t + 24, bars=2, vel={'x': 84})
t += 32
# A' (16): everything, the tabla kit on top
kit.note(t, CRASH, 2, 118); scream.note(t, 36, 1.5, 100)
breaks(t, 16); rave_piano(t, 16, 90); organ_bass(t, 16, 102)
tabla.drums({36: '..x...x...x..x..', 37: 'x.....x.....x...', 38: '....o.....o....o'}, at=t, bars=16, vel={'x': 80, 'o': 60})
hoover.mel(HOOVER, at=t + 32, vel=100); hoover.mel(HOOVER, at=t + 48, vel=104)
pan.mel(PAN, at=t + 16, vel=80, tr=12)
t += 64
# outro (8)
breaks(t, 4); organ_bass(t, 4, 96)
pad.chords('Am F C G Am:16', at=t, beats=4, style='pad', vel=60, lo=55, hi=72)
hello.note(t + 20, 60, 3, 88)
taiko.drums({36: 'x...............'}, at=t + 16, bars=4, vel={'x': 96})
t += 32
piano.chords('Am:2', at=t, style='pad', vel=96, lo=64, hi=79); kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 3, 110)
scream.note(t, 36, 1.5, 100)

S.humanize(ms=2, vel=3, parts=['ravepiano', 'steelpan', 'pad'])
finish(__file__, S, {
    'title': 'Sow Your Breaks in Spring',
    'pack': 'garden-rhythm',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Early-90s rave in A minor, 140 bpm: a talking machine says hello, taiko hits, breakbeats from the radio '
            'kit, rave piano, rave-organ bass, the hoover riff, a scream, a steelpan breakdown with a robot choir, '
            'a tabla kit on the last run. All from the pack.',
}, [
    ('kit', 'ch10', 'Second Bloom', dict(lufs=-16.5, verb=0.05)),
    ('taiko', 'ch9', 'Gentle Bloom', dict(lufs=-21, verb=0.3)),
    ('tabla', 'ch11', 'Coded Bloom', dict(lufs=-24, pan=24, verb=0.1)),
    ('ravepiano', 'ch1', 'Lucid Punch', dict(lufs=-20, pan=-10, verb=0.2)),
    ('organbass', 'ch2', 'Molten Brass', dict(lufs=-20)),
    ('hoover', 'ch3', 'Lagoon Stab', dict(lufs=-20, pan=8, width=1.3, verb=0.15)),
    ('scream', 'ch4', 'Global Salute', dict(lufs=-23, echo=0.3, verb=0.3)),
    ('pad', 'ch5', 'Bakelite Bloom', dict(lufs=-25, verb=0.35, width=1.4)),
    ('hello', 'ch6', 'Rubber Ahh', dict(lufs=-21, echo=0.35, verb=0.3)),
    ('robot', 'ch7', 'Grey Choir', dict(lufs=-25, pan=-14, verb=0.4)),
    ('steelpan', 'ch8', 'Digital Tower', dict(lufs=-21, pan=16, echo=0.3, verb=0.3)),
    ('shaker', 'ch12', 'Swift Shaker', dict(lufs=-29, pan=-30)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3500, 'level': -4},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 5500, 'level': -6})

"""Wow and Flutter Waltz: an original baroque-pop waltz on tape-replay voices, 3/4 at 118 bpm, A minor. The bowed
psaltery and violins over a harmonica-organ, a solo violin line, the ocarina in the middle, the choir drone and a
tuba bass."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=118, seed=1968)
psal = S.part('psaltery', 1)
violin = S.part('violin', 2)
violins = S.part('violins', 3)
organ = S.part('organ', 4)
tuba = S.part('tuba', 5)
ocarina = S.part('ocarina', 6)
choir = S.part('choir', 7)
piano = S.part('piano', 8)
horn = S.part('horn', 9)
kit = S.part('kit', 10)

A = 'Am Am E7 E7 Am Am Dm E7 Am Am G G C C Dm E7'
AMEL = ('h E5 q A5 | h. C6 | h B5 q G#5 | h. E5 | h E5 q A5 | h C6 q E6 | h D6 q B5 | h. G#5 | '
        'h A5 q C6 | h B5 q A5 | h G5 q D6 | h. B5 | h C6 q E6 | h D6 q C6 | h B5 q A5 | h. G#5')
B = 'F F C C Dm Dm E7 E7'
BMEL = 'h A5 q C6 | h. F6 | h E6 q C6 | h. G5 | h F5 q A5 | h D6 q C6 | h B5 q G#5 | h. E5'
BAR = 3.0


def waltz(at, prog, vel=64):
    prev = None
    for k, sy in enumerate(prog.split()):
        t = at + BAR * k
        ns = voice_lead(prev, chord(sy, 4), 55, 69); prev = ns
        r = root_of(sy, 2) + 12
        tuba.note(t, r, 0.9, 88)
        for off in (1, 2):
            for n in ns[:3]:
                organ.note(t + off, n, 0.7, vel - 4 * (off - 1))
        kit.note(t, KICK, 0.2, 70); kit.note(t + 1, CHH, 0.2, 48); kit.note(t + 2, CHH, 0.2, 44)


t = 0.0
piano.mel('h E5 q A5 | h. C6 | h B5 q G#5 | h. E5', at=0, vel=70)
t = 12
waltz(t, A); psal.mel(AMEL, at=t, vel=86)
t += 48
waltz(t, A); violin.mel(AMEL, at=t, vel=88); violins.chords(A, at=t, beats=BAR, style='pad', vel=54, lo=57, hi=72)
t += 48
waltz(t, B, 58); ocarina.mel(BMEL, at=t, vel=84); choir.chords(B, at=t, beats=BAR, style='pad', vel=58, lo=55, hi=67)
horn.mel('h. A4 | h. C5 | h. G4 | h. C5 | h. A4 | h. F4 | h. E4 | h. G#4', at=t, vel=66)
t += 24
waltz(t, A, 66); violins.mel(AMEL, at=t, vel=90); psal.mel(AMEL, at=t, vel=74, tr=12)
choir.chords(A, at=t, beats=BAR, style='pad', vel=54, lo=55, hi=67)
t += 48
for p, lo, hi, v in ((organ, 55, 69, 62), (violins, 57, 74, 64), (choir, 55, 67, 56)):
    p.chords('Am:6', at=t, style='pad', vel=v, lo=lo, hi=hi)
tuba.note(t, pitch('A2'), 6, 88); violin.note(t, pitch('A5'), 6, 84)

S.humanize(ms=8, vel=5)
finish(__file__, S, {
    'title': 'Wow and Flutter Waltz',
    'pack': 'tape-parlour',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A baroque-pop waltz in A minor, 3/4 at 118 bpm, on tape-replay voices: bowed psaltery, a solo violin, '
            'violins, a harmonica-organ waltz, a tuba bass, the ocarina and a horn in the middle, the choir, a parlour '
            'piano intro. Drums: Kit Manager 98 (Half-Time Kit).',
}, [
    ('psaltery', 'ch1', 'Amber Strings', dict(lufs=-20, pan=-10, verb=0.3)),
    ('violin', 'ch2', 'Upper Legato', dict(lufs=-20, pan=8, verb=0.3)),
    ('violins', 'ch3', 'Northern Strings', dict(lufs=-23, pan=22, verb=0.35)),
    ('organ', 'ch4', 'Bakelite Stops', dict(lufs=-25, pan=-18, verb=0.25)),
    ('tuba', 'ch5', 'Office Horns', dict(lufs=-21)),
    ('ocarina', 'ch6', 'Federal Spark', dict(lufs=-20, pan=4, echo=0.1, verb=0.35)),
    ('choir', 'ch7', 'Upper Murmur', dict(lufs=-26, verb=0.4)),
    ('piano', 'ch8', 'Swift Ivories', dict(lufs=-22, pan=14, verb=0.25)),
    ('horn', 'ch9', 'Pewter Herald', dict(lufs=-24, pan=-20, verb=0.35)),
    ('kit', 'ch10', 'kit-manager:Half-Time Kit', dict(lufs=-22, verb=0.12, lp=8000)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.2, 'tone': 2800, 'level': -9},
   reverb={'size': 1.9, 'predelay': 20, 'tone': 4500, 'level': -4})

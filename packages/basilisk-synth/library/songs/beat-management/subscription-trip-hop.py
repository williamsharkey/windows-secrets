"""Subscription (Trip-Hop Edition): an original trip-hop track, 82 bpm, D minor. A slow heavy break, a long boom
glide bass, noir strings and a tremolo erhu, felt-ding piano, a vinyl murmur and a flute line over the top."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=82, seed=1998)
kit = S.part('kit', 10)
bass = S.part('bass', 1)
strings = S.part('strings', 2)
erhu = S.part('erhu', 3)
piano = S.part('piano', 4)
flute = S.part('flute', 5)
murmur = S.part('murmur', 6)
bell = S.part('bell', 7)
choir = S.part('choir', 8)
scratch = S.part('scratch', 9)

PROG = 'Dm Bbmaj7 Gm7 A7'
MEL = 'h. A5 q G5 | h F5 E5 | h. D5 q E5 | w C#5 | h. A5 q Bb5 | h C6 Bb5 | q A5 G5 F5 E5 | w D5'
BEAT = {KICK: 'x.......x.x.....', SNARE: '....x.......x...', CHH: 'x...x...x...x...', OHH: '..........x.....'}


def beat(at, bars):
    for k in range(bars):
        kit.drums(BEAT if k % 4 != 3 else {KICK: 'x.......x.x...x.', SNARE: '....x.......x.x.', CHH: 'x...x...x...x...'},
                  at=at + 4 * k, bars=1, swing=0.15)


def glide(at, bars, vel=100):
    for k in range(bars):
        r = root_of(PROG.split()[k % 4], 2) + 12
        bass.note(at + 4 * k, r, 2.6, vel); bass.note(at + 4 * k + 3, r + 7 if k % 2 else r - 2, 0.9, vel - 12)


t = 0.0
hold(murmur, 0, 60, 16, 76)
piano.chords(PROG, at=0, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(0, 1.8), (2.5, 1.2)])
t = 16
beat(t, 16); glide(t, 16)
strings.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=60, lo=50, hi=67)
piano.chords(' '.join([PROG] * 4), at=t, beats=4, style='block', vel=58, lo=55, hi=72, rhythm=[(0, 1.8), (2.5, 1.2)])
erhu.mel(MEL, at=t + 32, vel=84, tr=-12)
hold(murmur, t, 60, 64, 62)
t += 64
beat(t, 16); glide(t, 16)
flute.mel(MEL, at=t, vel=88, tr=-12); flute.mel(MEL, at=t + 32, vel=90, tr=-12)
erhu.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=56, lo=55, hi=69)
choir.chords(' '.join([PROG] * 2), at=t + 32, beats=4, style='pad', vel=56, lo=52, hi=67)
for k in (7, 15):
    for i, n in enumerate((60, 64, 60)):
        scratch.note(t + 4 * k + 2 + i * 0.33, n, 0.25, 88)
t += 64
# coda: the piano and bell alone, the murmur
piano.chords(PROG + ' Dm:8', at=t, beats=4, style='block', vel=58, lo=55, hi=72, rhythm=[(0, 3.6)])
bell.mel('h. A5 q G5 | h F5 E5 | h. D5 q E5 | w C#5 | w D5', at=t, vel=70)
hold(murmur, t, 60, 24, 66)
t += 24

finish(__file__, S, {
    'title': 'Subscription (Trip-Hop Edition)',
    'pack': 'beat-management',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Trip-hop in D minor, 82 bpm: a slow heavy break, the long-boom glide bass, noir strings, a tremolo erhu, '
            'felt-ding piano, the flute line, a choir, scratches, a floor murmur and a bell coda. Drums: Kit Manager 98 '
            '(Twelve-Bit Crate Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Twelve-Bit Crate Kit', dict(lufs=-17, verb=0.08)),
    ('bass', 'ch1', 'Long Boom Glide', dict(lufs=-19)),
    ('strings', 'ch2', 'Noir Strings', dict(lufs=-24, pan=-16, verb=0.4, width=1.3)),
    ('erhu', 'ch3', 'Dusk Tremolo', dict(lufs=-22, pan=16, echo=0.15, verb=0.35)),
    ('piano', 'ch4', 'Felt Ding Piano', dict(lufs=-22, pan=-10, verb=0.3)),
    ('flute', 'ch5', 'Flute Loop Lead', dict(lufs=-20, pan=6, echo=0.2, verb=0.35)),
    ('murmur', 'ch6', 'Steady Murmur', dict(lufs=-31, width=1.4)),
    ('bell', 'ch7', 'Dusty Vibes', dict(lufs=-23, pan=24, echo=0.25, verb=0.4)),
    ('choir', 'ch8', 'Night Choir Pad', dict(lufs=-26, verb=0.45, width=1.3)),
    ('scratch', 'ch9', 'Desk Scratch', dict(lufs=-25, pan=-8)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 2500, 'level': -5},
   reverb={'size': 2.2, 'predelay': 20, 'tone': 4500, 'level': -4})

"""Teleprinter Polka: an original polka, 2/4 at 126 bpm (in quarters), B-flat major. A relay marimba and the
sounder keys oom-pah, the CSIRAC pulse and the typewriter bell take the tune, the exchange ringer on the trio,
the teleprinter kit, a newsroom burst at the end."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=126, seed=1933)
kit = S.part('kit', 10)
bass = S.part('hootbass', 1)
marimba = S.part('marimba', 2)
sounder = S.part('sounder', 3)
pulse = S.part('pulse', 4)
tbell = S.part('typebell', 5)
ringer = S.part('ringer', 6)
mallet = S.part('mallet', 7)
news = S.part('news', 8)
spring = S.part('spring', 9)

A = 'Bb Bb F7 F7 F7 F7 Bb Bb'
AMEL = 'e F5 D5 F5 Bb5 | q D6 Bb5 | e C6 A5 F5 A5 | q C6 r | e Eb6 C6 A5 F5 | e Eb5 G5 F5 Eb5 | q D5 F5 | q Bb5 r'
T = 'Eb Eb Bb Bb F7 F7 Bb Bb'
TMEL = 'q G5 Bb5 | h Eb6 | q D6 C6 | h Bb5 | q A5 C6 | q Eb6 D6 | q C6 A5 | h Bb5'
BAR = 2.0


def oompah(at, prog, vel=74):
    prev = None
    for k, sy in enumerate(prog.split()):
        t = at + BAR * k
        ns = voice_lead(prev, chord(sy, 4), 57, 69); prev = ns
        r = root_of(sy, 2) + 12
        bass.note(t, r if k % 2 == 0 else r + 7 - (12 if r + 7 > 55 else 0), 0.8, 92)
        for n in ns[:3]:
            marimba.note(t + 1, n, 0.4, vel)
        sounder.note(t + 1.5, ns[-1] + 12, 0.2, vel - 14)
        kit.note(t, 36, 0.2, 86); kit.note(t + 1, 38, 0.2, 70)


t = 0.0
news.note(0, 60, 3, 80)
pulse.mel('e F5 G5 A5 Bb5 | q C6 F5', at=4, vel=86)
t = 8
for r in range(3):
    oompah(t, A); pulse.mel(AMEL, at=t, vel=90); oompah(t + 16, A); tbell.mel(AMEL, at=t + 16, vel=80)
    t += 32
    oompah(t, T, 66); ringer.mel(TMEL, at=t, vel=84); mallet.mel(TMEL, at=t + 16, vel=80)
    oompah(t + 16, T, 70)
    t += 32
oompah(t, A); pulse.mel(AMEL, at=t, vel=94); tbell.mel(AMEL, at=t, vel=72); spring.note(t + 14, 55, 2, 80)
t += 16
pulse.mel('e Bb5 F5 D5 F5 | q Bb5 r', at=t, vel=96); bass.note(t + 2, pitch('Bb2'), 2, 96); kit.note(t + 2, 36, 0.3, 100)
news.note(t + 3, 60, 3, 84)

finish(__file__, S, {
    'title': 'Teleprinter Polka',
    'pack': 'electromech-heritage',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A polka in B-flat, 2/4: a Ferranti-hoot bass, relay-marimba and sounder-key oom-pah, the CSIRAC pulse and '
            'the typewriter bell on the tune, the exchange ringer and relay mallet on the trio, the teleprinter kit, '
            'a contact spring and the newsroom teleprinter. Drums: Kit Manager 98 (Teletype 33).',
}, [
    ('kit', 'ch10', 'kit-manager:Teletype 33', dict(lufs=-21, verb=0.1)),
    ('hootbass', 'ch1', 'Ferranti Hoot', dict(lufs=-20)),
    ('marimba', 'ch2', 'Relay Marimba', dict(lufs=-23, pan=-20, verb=0.2)),
    ('sounder', 'ch3', 'Sounder Keys', dict(lufs=-26, pan=18, verb=0.2)),
    ('pulse', 'ch4', 'CSIRAC Pulse', dict(lufs=-20, pan=6, echo=0.15, verb=0.15)),
    ('typebell', 'ch5', 'Teletype Bell Keyboard', dict(lufs=-22, pan=-10, verb=0.3)),
    ('ringer', 'ch6', 'Exchange Ringer', dict(lufs=-22, pan=10, verb=0.35)),
    ('mallet', 'ch7', 'Relay Mallet', dict(lufs=-23, pan=24, verb=0.25)),
    ('news', 'ch8', 'Newsroom', dict(lufs=-25, pan=-24)),
    ('spring', 'ch9', 'Contact Spring', dict(lufs=-25, verb=0.3)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.2, 'tone': 3000, 'level': -9},
   reverb={'size': 1.6, 'predelay': 12, 'tone': 5000, 'level': -6})

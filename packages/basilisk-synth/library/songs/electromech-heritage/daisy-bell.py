"""Daisy Bell (Harry Dacre, 1892), arranged for ELEKTROMECHANIK: the chorus's first strain four times as a waltz
for the telephone exchange. The 1961 vowel voice sings it, a relay marimba plays the oom-pah-pah, a Ferranti hoot
the bass, the exchange ringer and the typewriter bell answer, a motor drone holds the hall."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=120, seed=1892)
vowel = S.part('vowel', 1)
marimba = S.part('marimba', 2)
bass = S.part('hootbass', 3)
pulse = S.part('pulse', 4)
ringer = S.part('ringer', 5)
tbell = S.part('typebell', 6)
organ = S.part('organ', 7)
motor = S.part('motor', 8)
kit = S.part('kit', 10)
sounder = S.part('sounder', 9)

MEL = ('h. G5 | h. E5 | h. C5 | h. G4 | q A4 B4 C5 | h A4 q C5 | h. G4 | h. ~ | '
       'h. D5 | h. G5 | h. E5 | h. C5 | q A4 B4 C5 | h D5 q E5 | h. D5 | h. ~')
PROG = 'C C C C F F C C G G C C F D7 G G'
BAR = 3.0
L = 16 * BAR


def waltz(at, vel=70, drums=True):
    prev = None
    for k, sy in enumerate(PROG.split()):
        t = at + k * BAR
        ns = voice_lead(prev, chord(sy, 4), 57, 69); prev = ns
        r = root_of(sy, 2) + 12
        bass.note(t, r if k % 2 == 0 else r + 7 - (12 if r + 7 > 55 else 0), 0.9, 92)
        for off in (1, 2):
            for n in ns:
                marimba.note(t + off, n, 0.5, vel - 6 * (off - 1))
        if drums:
            kit.note(t, 36, 0.3, 84); kit.note(t + 1, 42, 0.2, 56); kit.note(t + 2, 42, 0.2, 52)


t = 0.0
hold(motor, 0, 48, 12, 74)
ringer.note(0, pitch('A4'), 2, 80)
organ.chords('C:6 G7:6', at=0, style='pad', vel=54, lo=57, hi=72)
t = 12
# 1: the vowel sings over the relay marimba
vowel.mel(MEL, at=t, vel=90); waltz(t, drums=False)
t += L
# 2: the kit and the ringer join; the typewriter bell rings at each line's end
vowel.mel(MEL, at=t, vel=92); waltz(t)
for k in (7, 15):
    tbell.note(t + k * BAR, pitch('G5'), 2, 72)
ringer.note(t, pitch('C5'), 2, 76)
t += L
# 3: the CSIRAC pulse takes the tune an octave up, the vowel holds the harmony
pulse.mel(MEL, at=t, vel=88)
vowel.chords(PROG, at=t, beats=BAR, style='pad', vel=62, lo=55, hi=67)
waltz(t, vel=66)
sounder.chords(PROG, at=t, beats=BAR, style='block', vel=54, lo=60, hi=74, rhythm=[(1.5, 0.3)])
t += L
# 4: everyone; the vowel and the pulse together
vowel.mel(MEL, at=t, vel=96); pulse.mel(MEL, at=t, vel=70, tr=12)
organ.chords(PROG, at=t, beats=BAR, style='pad', vel=52, lo=57, hi=72)
waltz(t, vel=72)
for k in (3, 7, 11, 15):
    tbell.note(t + k * BAR + 2, pitch('E6'), 1, 66)
t += L
vowel.mel('h. C5 | h. C5', at=t, vel=88); organ.chords('C:6', at=t, style='pad', vel=58, lo=57, hi=72)
bass.note(t, pitch('C3'), 6, 92); ringer.note(t + 3, pitch('C5'), 3, 80)
hold(motor, t, 48, 8, 66)

S.humanize(ms=3, vel=3)
finish(__file__, S, {
    'title': 'Daisy Bell',
    'pack': 'electromech-heritage',
    'kind': 'world',
    'composer': 'Harry Dacre (1857-1922)',
    'source': 'Daisy Bell (Bicycle Built for Two), song (1892): the first strain of the chorus, written out from the '
              'song.',
    'licence': 'The work: public domain (published 1892; the composer died 1922). This arrangement: CC0-1.0.',
    'proof': 'https://en.wikipedia.org/wiki/Daisy_Bell',
    'arranger': 'Algorithmic Industries house band',
    'note': 'A waltz at 120 bpm, the chorus\'s first strain four times: the 1961 vowel voice, a relay-marimba '
            'oom-pah-pah, a Ferranti-hoot bass, the CSIRAC pulse, exchange ringer, typewriter bell, dial-tone organ, '
            'sounder keys, a motor drone. Drums: Kit Manager 98 (Teletype 33).',
}, [
    ('vowel', 'ch1', '1961 Vowel', dict(lufs=-19, pan=4, echo=0.15, verb=0.35)),
    ('marimba', 'ch2', 'Relay Marimba', dict(lufs=-23, pan=-20, verb=0.2)),
    ('hootbass', 'ch3', 'Ferranti Hoot', dict(lufs=-21)),
    ('pulse', 'ch4', 'CSIRAC Pulse', dict(lufs=-21, pan=12, echo=0.2, verb=0.15)),
    ('ringer', 'ch5', 'Exchange Ringer', dict(lufs=-24, pan=-10, verb=0.4)),
    ('typebell', 'ch6', 'Typewriter Bell Keys', dict(lufs=-26, pan=30, echo=0.3, verb=0.4)),
    ('organ', 'ch7', 'Dial Tone Organ', dict(lufs=-26, pan=18, verb=0.3)),
    ('motor', 'ch8', 'Motor Room', dict(lufs=-30, verb=0.2)),
    ('kit', 'ch10', 'kit-manager:Teletype 33', dict(lufs=-23, verb=0.1)),
    ('sounder', 'ch9', 'Sounder Keys', dict(lufs=-26, pan=-16, verb=0.2)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.3, 'tone': 3000, 'level': -6},
   reverb={'size': 1.8, 'predelay': 15, 'tone': 5000, 'level': -5})

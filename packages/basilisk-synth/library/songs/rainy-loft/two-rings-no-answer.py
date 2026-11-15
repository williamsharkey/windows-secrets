"""Two Rings, No Answer: an original ballad, 72 bpm, E-flat major, on brushes. Balcony rain and a cup and spoon, the
telephone, then the clarinet over the felt upright and a fretless bass, cellos, a straight-mute trumpet for the
bridge, and the music box at two in the morning; a horn far off in the harbour."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=72, seed=1989)
clar = S.part('clarinet', 1)
mute = S.part('mute', 2)
felt = S.part('felt', 3)
bass = S.part('bass', 4)
cello = S.part('cellos', 5)
box = S.part('musicbox', 6)
rain = S.part('rain', 7)
fx = S.part('cup', 8)
phone = S.part('phone', 9)
kit = S.part('kit', 10)
horn = S.part('horn', 11)

A = 'Ebmaj7 Cm7 Abmaj7 Bb7sus4:2 Bb7:2 Gm7 Cm7 Fm7 Bb7sus4:2 Bb7:2'
B = 'Abmaj7 Gm7 Fm7 Bb7 Abmaj7 Gm7 Cm7 Bb7sus4'
MA = ('q. G4 e Bb4 q D5 Eb5 | h. D5 e C5 Bb4 | q C5 e Eb5 G5 q. F5 e Eb5 | h Eb5 q D5 r | '
      'q. D5 e F5 q Bb5 G5 | h. G5 e F5 Eb5 | q F5 e Ab5 C6 q. Bb5 e Ab5 | w G5')
MB = ('q C6 e Bb5 G5 h Eb5 | q D5 e F5 Bb5 h D6 | q C6 e Ab5 F5 h Eb5 | h D5 q F5 Ab5 | '
      'q G5 e C6 Eb6 h G6 | q F6 e D6 Bb5 h G5 | q Eb6 e D6 C6 q. G5 e Bb5 | w F5')
BASS = [(0, 0, 1.8), (2, '5', 1.4), (3.5, '8', 0.4)]
COMP = [(0, 1.8), (2.5, 1.2)]


def brushes(at, bars, vel=None):
    for k in range(bars):
        last = k % 8 == 7
        kit.drums({KICK: 'x.........x.....', 38: '....o.......x...' if not last else '....o.......x.xx',
                   40: 'x...x...x...x...', 37: '..........o.....'}, at=at + 4 * k, bars=1, swing=0.18,
                  vel=vel or {'x': 74, 'o': 52})


def band(at, prog, strings=False, drums=True):
    felt.chords(prog, at=at, style='block', rhythm=COMP, vel=62, lo=51, hi=70)
    bass.bass(prog, at=at, pattern=BASS, vel=90, octave=2)
    if strings:
        cello.chords(prog, at=at, style='pad', vel=60, lo=43, hi=58)
    if drums:
        brushes(at, 8)


t = 0.0
# intro (4): balcony rain, a cup and spoon, the telephone; the music box plays the changes
hold(rain, 0, 60, 40 * 4 + 6, 64)
fx.note(1, 60, 2, 76)
box.chords('Ebmaj7 Cm7 Abmaj7 Bb7sus4', at=t, style='arp', rhythm=0.5, vel=58, lo=72, hi=88)
phone.note(8, 60, 4, 80)
t += 16
# A (8): the clarinet, no drums yet
band(t, A, drums=False); clar.mel(MA, at=t, vel=88); t += 32
# A (8): brushes and cellos
band(t, A, strings=True); clar.mel(MA, at=t, vel=92); t += 32
# B (8): the straight-mute trumpet takes the bridge, the clarinet underneath
band(t, B, strings=True); mute.mel(MB, at=t, vel=90)
clar.mel('w Eb5 | w D5 | w C5 | w D5 | w Eb5 | w D5 | w Eb5 | w D5', at=t, vel=62); t += 32
# A (8): the clarinet again, the music box doubling the last four bars an octave up
band(t, A, strings=True); clar.mel(MA, at=t, vel=94)
box.mel('q. D6 e F6 q Bb6 G6 | h. G6 e F6 Eb6 | q F6 e Ab6 C7 q. Bb6 e Ab6 | w G6', at=t + 16, vel=56); t += 32
# outro (4): the music box alone, the rain, a horn far off
box.chords('Ebmaj7 Cm7 Abmaj7 Ebmaj7', at=t, style='arp', rhythm=0.5, vel=54, lo=72, hi=88)
felt.chords('Ebmaj7:8', at=t + 8, style='pad', vel=52, lo=51, hi=70)
bass.note(t + 8, pitch('Eb2'), 8, 78); horn.note(t + 4, 60, 8, 70)

S.humanize(ms=10, vel=6)
finish(__file__, S, {
    'title': 'Two Rings, No Answer',
    'pack': 'rainy-loft',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A ballad in E-flat major, 72 bpm, on the Loft Brushes kit: balcony rain, a cup and spoon, the telephone, '
            'the clarinet after hours over the felt upright and the fretless bass, legato cellos, a straight-mute '
            'trumpet for the bridge, the music box at two, a far horn.',
    'tail': 6,
}, [
    ('clarinet', 'ch1', 'Clarinet After Hours', dict(lufs=-18, pan=-4, verb=0.3)),
    ('mute', 'ch2', 'Straight Mute', dict(lufs=-19, pan=6, echo=0.15, verb=0.3)),
    ('felt', 'ch3', 'Felt Upright', dict(lufs=-21, pan=-16, verb=0.25)),
    ('bass', 'ch4', 'Fretless Harbour', dict(lufs=-20)),
    ('cellos', 'ch5', 'Legato Cellos', dict(lufs=-25, pan=14, verb=0.35)),
    ('musicbox', 'ch6', 'Music Box at Two', dict(lufs=-23, pan=24, echo=0.2, verb=0.4)),
    ('rain', 'ch7', 'Balcony Rain', dict(lufs=-30, width=1.4)),
    ('cup', 'ch8', 'Cup and Spoon', dict(lufs=-28, pan=-24, verb=0.2)),
    ('phone', 'ch9', 'Telephone, Two Rings', dict(lufs=-26, pan=30, verb=0.3)),
    ('kit', 'ch10', 'Loft Brushes', dict(lufs=-22, verb=0.12)),
    ('horn', 'ch11', 'Far Horn', dict(lufs=-30, verb=0.5, tune=0)),
], master={'loudness': -17, 'ceiling': -1.0, 'fadeout': 4},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 3000, 'level': -7},
   reverb={'size': 2.8, 'predelay': 22, 'tone': 5000, 'level': -4})

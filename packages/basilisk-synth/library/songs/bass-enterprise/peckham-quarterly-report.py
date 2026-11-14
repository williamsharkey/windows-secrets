"""Peckham Quarterly Report: an original UK garage track, 132 bpm, G minor. A skipping 2-step beat, parallel minor
stabs, the organ bass, a trombone hook, then a speed-garage section on the wobbling sub."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=132, seed=1999)
kit = S.part('kit', 10)
organ = S.part('organbass', 2)
wobble = S.part('wobble', 3)
sub = S.part('sub', 4)
stab = S.part('stab', 5)
horn = S.part('horn', 6)
vowel = S.part('vowel', 7)
chord_ = S.part('chord', 8)
gtr = S.part('bassgtr', 9)
fx = S.part('fx', 11)
doom = S.part('doom', 12)

ROOTS = ['G', 'F', 'Eb', 'F']
HOOK = 'e G4 r Bb4 r q C5 e Bb4 G4 | q F4 e G4 r h r | e G4 r Bb4 r q D5 e C5 Bb4 | q C5 e Bb4 G4 h r'
SHUFFLE = 0.3


def two_step(at, bars, fill_last=True):
    for k in range(bars):
        last = fill_last and k == bars - 1
        pads = {KICK: 'x......x..x.....' if k % 2 == 0 else 'x.........x..x..',
                SNARE: '....x.......x...', CHH: '..x...x...x.x.x.', RIM: '.o....o..o....o.'}
        if last:
            pads = {KICK: 'x......x........', SNARE: '....x.....x.xxXX', CHH: '..x...x.........'}
        kit.drums(pads, at=at + 4 * k, bars=1, swing=SHUFFLE)


def stabs(at, bars, vel=84):
    for k in range(bars):
        n = pitch(ROOTS[k % 4] + '4')
        for off in (0.0, 0.75, 2.5):
            stab.note(at + 4 * k + off + (SHUFFLE * 0.25 if off == 0.75 else 0), n, 0.3, vel)


def organ_bass(at, bars, vel=100):
    for k in range(bars):
        n = pitch(ROOTS[k % 4] + '2')
        for off, du in ((0, 0.6), (1.5, 0.3), (1.75 + SHUFFLE * 0.25, 0.3), (2.5, 0.6), (3.5, 0.4)):
            organ.note(at + 4 * k + off, n, du, vel - (0 if off in (0, 2.5) else 12))


def wobble_bass(at, bars, vel=104):
    for k in range(bars):
        n = pitch(ROOTS[k % 4] + '2')
        wobble.note(at + 4 * k, n, 1.4, vel); wobble.note(at + 4 * k + 1.5, n + 12, 0.4, vel - 14)
        wobble.note(at + 4 * k + 2, n, 1.9, vel - 4)


def four(at, bars):   # speed garage: four to the floor with the shuffle on top
    for k in range(bars):
        kit.drums({KICK: 'x...x...x...x...', SNARE: '....x.......x...', OHH: '..x...x...x...x.', CHH: 'x.xxx.xxx.xxx.xx'},
                  at=at + 4 * k, bars=1, swing=SHUFFLE)


t = 0.0
# intro (8): the vowel pad, the stabs, a rising swoosh
vowel.chords('Gm Fm Ebm Fm Gm Fm Ebm Fm', at=0, beats=4, style='pad', vel=60, lo=53, hi=67)
stabs(16, 4, 72)
fx.note(24, 60, 7.5, 84)
kit.drums({CHH: '..x...x...x.x.x.'}, at=16, bars=4, swing=SHUFFLE, vel={'x': 66})
t = 32
# verse (16): 2-step, organ bass, stabs, the hook
doom.note(t, 24, 3, 100)
two_step(t, 16); organ_bass(t, 16); stabs(t, 16)
horn.mel(HOOK, at=t + 32, vel=88); horn.mel(HOOK, at=t + 48, vel=92)
t += 64
# bridge (8): bass guitar walks, the organ chord, the vowel
gtr.mel('q G2 e Bb2 C3 q D3 F3 | q F2 e A2 C3 q F3 Eb3 | q Eb2 e G2 Bb2 q Eb3 D3 | q F2 G2 A2 C3', at=t, vel=96)
gtr.mel('q G2 e Bb2 C3 q D3 F3 | q F2 e A2 C3 q F3 Eb3 | q Eb2 e G2 Bb2 q Eb3 D3 | h F2 D3', at=t + 16, vel=96)
chord_.chords('Gm7 F Ebmaj7 F Gm7 F Ebmaj7 D7', at=t, beats=4, style='block', vel=70, lo=55, hi=70,
              rhythm=[(0, 0.4), (1.5, 0.4), (3, 0.4)])
vowel.chords('Gm Fm Ebm Fm Gm Fm Ebm D', at=t, beats=4, style='pad', vel=58, lo=53, hi=67)
kit.drums({KICK: 'x.........x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=7, swing=SHUFFLE)
kit.drums({SNARE: 'x.x.x.x.xxxxXXXX'}, at=t + 28, bars=1)
fx.note(t + 24, 60, 7.5, 88)
t += 32
# speed garage (16): four to the floor, the wobbling sub, stabs and hook
doom.note(t, 24, 3, 104); kit.note(t, CRASH, 2, 110)
four(t, 15); two_step(t + 60, 1)
wobble_bass(t, 16); stabs(t, 16, 88)
sub.bass('G F Eb F ' * 4, at=t, beats=4, pattern=[(0, 0, 3.6)], vel=90, octave=1)
horn.mel(HOOK, at=t, vel=92); horn.mel(HOOK, at=t + 16, vel=96); horn.mel(HOOK, at=t + 48, vel=96)
t += 64
# outro (8): back to 2-step, then the vowel alone
two_step(t, 4, fill_last=False); organ_bass(t, 4, 94); stabs(t, 8, 74)
vowel.chords('Gm Fm Ebm Fm Gm:8', at=t + 16, beats=4, style='pad', vel=58, lo=53, hi=67)
t += 32
stab.note(t, pitch('G4'), 0.5, 90); kit.note(t, KICK, 1, 104); doom.note(t, 24, 3, 90)

S.humanize(ms=3, vel=4, parts=['horn', 'bassgtr', 'chord'])
finish(__file__, S, {
    'title': 'Peckham Quarterly Report',
    'pack': 'bass-enterprise',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'UK garage in G minor, 132 bpm: 2-step beat, parallel minor stabs, organ bass, trombone hook, a bass-guitar '
            'bridge, then speed garage on the wobbling sub. Drums: Kit Manager 98 (Half-Time Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Half-Time Kit', dict(lufs=-16.5, verb=0.05)),
    ('organbass', 'ch2', 'Organ Bass 2-Step', dict(lufs=-19)),
    ('wobble', 'ch3', 'Wobbly Speed Sub', dict(lufs=-19)),
    ('sub', 'ch4', 'Floor Rumble', dict(lufs=-24)),
    ('stab', 'ch5', 'Two-Step Minor Stab', dict(lufs=-21, pan=-14, echo=0.22, verb=0.15)),
    ('horn', 'ch6', 'Lattice Accent', dict(lufs=-20, pan=12, echo=0.2, verb=0.2)),
    ('vowel', 'ch7', 'Marble Vowel', dict(lufs=-25, verb=0.4, width=1.3)),
    ('chord', 'ch8', 'Golden Chord', dict(lufs=-24, pan=20, verb=0.25)),
    ('bassgtr', 'ch9', 'Ocean Bass', dict(lufs=-20)),
    ('fx', 'ch11', 'Cedar Ascent', dict(lufs=-26, verb=0.4)),
    ('doom', 'ch12', 'Impact Doom', dict(lufs=-24, verb=0.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 1.6, 'predelay': 12, 'tone': 5500, 'level': -7})

"""After Midnight Dubplate: an original dark 2-step / bassline track, 134 bpm, F minor. A wobbling speed sub, the
error growl, sub thumps, the two-step minor stab, a trombone call, the vowel pad and an impact on every section."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=134, seed=2001)
kit = S.part('kit', 10)
wob = S.part('wobble', 1)
growl = S.part('growl', 2)
sub = S.part('sub', 3)
stab = S.part('stab', 4)
horn = S.part('horn', 5)
vowel = S.part('vowel', 6)
doom = S.part('doom', 7)
fx = S.part('fx', 8)
salute = S.part('salute', 9)

ROOTS = ['F', 'F', 'Db', 'Eb']
SW = 0.28


def two_step(at, bars):
    for k in range(bars):
        last = k % 8 == 7
        pads = {KICK: 'x......x..x.....' if k % 2 == 0 else 'x.........x..x..', SNARE: '....x.......x...' if not last else '....x.....x.xxXX',
                CHH: '..x...x...x.x.x.', RIM: '.o....o..o....o.'}
        kit.drums(pads, at=at + 4 * k, bars=1, swing=SW)


def bass(at, bars, growl_on=False):
    for k in range(bars):
        n = pitch(ROOTS[k % 4] + '2')
        wob.note(at + 4 * k, n, 1.4, 104); wob.note(at + 4 * k + 1.5, n + 12, 0.4, 90); wob.note(at + 4 * k + 2, n, 1.9, 98)
        sub.note(at + 4 * k, n - 12 if n - 12 >= 28 else n, 3.8, 84)
        if growl_on and k % 2 == 1:
            growl.note(at + 4 * k + 2.75, n + 12, 0.8, 92)


def stabs(at, bars):
    for k in range(bars):
        n = pitch(ROOTS[k % 4] + '4')
        for off in (0.0, 0.75 + SW * 0.25, 2.5):
            stab.note(at + 4 * k + off, n, 0.3, 84)


CALL = 'q C5 e Ab4 F4 h r | q Db5 e C5 Ab4 h r | q C5 e Ab4 F4 q Eb5 C5 | h. Ab4 q r'
t = 0.0
vowel.chords('Fm Fm Dbmaj7 Eb', at=0, beats=4, style='pad', vel=60, lo=53, hi=67)
fx.note(8, 60, 8, 82)
t = 16
doom.note(t, 24, 3, 104)
two_step(t, 16); bass(t, 16); stabs(t + 32, 8)
t += 64
doom.note(t, 24, 3, 104)
two_step(t, 16); bass(t, 16, growl_on=True); stabs(t, 16)
for k in range(4):
    horn.mel(CALL, at=t + 16 * k, vel=90)
t += 64
# breakdown: the vowel, the salute, a sweep
vowel.chords('Fm Fm Dbmaj7 Eb Fm Fm Dbmaj7 C', at=t, beats=4, style='pad', vel=64, lo=53, hi=67)
for k in range(8):
    salute.note(t + 4 * k, pitch(ROOTS[k % 4] + '3'), 1.5, 80)
fx.note(t + 24, 60, 8, 86)
kit.drums({KICK: 'x.........x.....', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=7, swing=SW)
kit.drums({SNARE: 'x.x.x.x.xxxxXXXX'}, at=t + 28, bars=1)
t += 32
doom.note(t, 24, 3, 108); kit.note(t, CRASH, 2, 110)
two_step(t, 16); bass(t, 16, growl_on=True); stabs(t, 16)
for k in range(4):
    horn.mel(CALL, at=t + 16 * k, vel=94)
t += 64
stab.note(t, pitch('F4'), 0.5, 90); kit.note(t, KICK, 1, 104); doom.note(t, 24, 3, 94)

finish(__file__, S, {
    'title': 'After Midnight Dubplate',
    'pack': 'bass-enterprise',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Dark 2-step in F minor, 134 bpm: the wobbling speed sub over a sub thump, the error growl, the two-step '
            'minor stab, a trombone call, the vowel pad, the still salute, an impact on every section. Drums: Kit '
            'Manager 98 (Half-Time Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Half-Time Kit', dict(lufs=-17, verb=0.05)),
    ('wobble', 'ch1', 'Wobbly Speed Sub', dict(lufs=-19)),
    ('growl', 'ch2', 'Error Growl', dict(lufs=-23, pan=8)),
    ('sub', 'ch3', 'Half-Step Sub', dict(lufs=-25)),
    ('stab', 'ch4', 'Two-Step Minor Stab', dict(lufs=-21, pan=-14, echo=0.22, verb=0.15)),
    ('horn', 'ch5', 'Lattice Accent', dict(lufs=-21, pan=12, echo=0.2, verb=0.2)),
    ('vowel', 'ch6', 'Marble Vowel', dict(lufs=-25, verb=0.4, width=1.3)),
    ('doom', 'ch7', 'Impact Doom', dict(lufs=-24, verb=0.3)),
    ('fx', 'ch8', 'Basement Swoosh', dict(lufs=-26, verb=0.4)),
    ('salute', 'ch9', 'Still Salute', dict(lufs=-25, pan=-20, verb=0.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 1.6, 'predelay': 12, 'tone': 5500, 'level': -7})

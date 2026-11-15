"""Fax Machine Fanfare: an original industrial march, 104 bpm, C major. The civil-defence bugle sounds a call,
floppy drives and keyboards keep step, the PC speaker plays the trio, a hard disk spins up for the last strain."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=104, seed=1998)
bugle = S.part('bugle', 1)
low = S.part('lowbugle', 2)
beep = S.part('beep', 3)
drives = S.part('drives', 4)
kit = S.part('kit', 10)
beepkit = S.part('beepkit', 9)
floppy = S.part('floppy', 5)
clack = S.part('clack', 6)
snare = S.part('opl3', 7)
spin = S.part('spinup', 8)
hum = S.part('hum', 11)
latch = S.part('latch', 12)

CALL = 'q C5 e C5 C5 q E5 C5 | q G5 e G5 G5 h G5 | q E5 e E5 G5 q C6 G5 | h E5 q C5 r'
MARCH = ('q C5 E5 G5 C6 | h B5 q A5 G5 | q F5 A5 C6 F5 | h. E5 q r | q D5 F5 A5 D6 | h C6 q B5 A5 | '
         'q G5 B5 D6 B5 | h. C6 q r')
TRIO = ('h E5 q F5 G5 | h A5 G5 | q F5 E5 D5 E5 | h. C5 q r | h D5 q E5 F5 | h G5 F5 | q E5 D5 C5 B4 | h. C5 q r')
PROG_M = 'C G F C D G G C'
PROG_T = 'F C Bb F G C G C'


def street(at, bars, prog, roll=False):
    for k in range(bars):
        x = at + 4 * k
        kit.drums({KICK: 'x.......x.......', SNARE: 'x.ox....x.oxo.o.' if not roll else 'xoxoxoxoxoxoxoxo'}, at=x, bars=1,
                  vel={'x': 94, 'o': 54})
        snare.drums({60: '....x.......x...'}, at=x, bars=1, vel={'x': 70})
        clack.drums({60: '..x...x...x...x.'}, at=x, bars=1, vel={'x': 58})
        r = root_of(prog.split()[k % 8], 2)
        drives.note(x, r + 12, 1.6, 96); drives.note(x + 2, r + 19 if r + 19 <= 50 else r + 7, 1.6, 88)
        if k % 4 == 3:
            floppy.note(x + 2, 60, 1.6, 76)


t = 0.0
spin.note(0, 30, 8, 90); hold(hum, 0, 60, 8, 60)
latch.note(6, 56, 1, 84)
t = 8
bugle.mel(CALL, at=t, vel=96); street(t, 4, 'C G C C', roll=True)
t += 16
bugle.mel(MARCH, at=t, vel=94); street(t, 8, PROG_M)
t += 32
bugle.mel(MARCH, at=t, vel=96); low.mel(MARCH, at=t, vel=78, tr=-12); street(t, 8, PROG_M)
t += 32
# the trio: the PC speaker, softer, the beep kit
beep.mel(TRIO, at=t, vel=86, tr=12); low.mel(TRIO, at=t, vel=72); street(t, 8, PROG_T)
beepkit.drums({36: 'x.......x.......', 42: '..x...x...x...x.'}, at=t, bars=8, vel={'x': 64})
hold(hum, t, 60, 32, 56)
t += 32
# the last strain: a spin-up, bugle call then the trio grandioso
spin.note(t - 6, 30, 6, 88)
bugle.mel(CALL, at=t, vel=98); street(t, 4, 'C G C C', roll=True)
t += 16
bugle.mel(TRIO, at=t, vel=98); beep.mel(TRIO, at=t, vel=78, tr=24); low.mel(TRIO, at=t, vel=80, tr=-12)
street(t, 8, PROG_T); beepkit.drums({36: 'x.......x.......', 42: '..x...x...x...x.'}, at=t, bars=8, vel={'x': 66})
t += 32
bugle.mel('q C5 E5 G5 r | w C6', at=t, vel=100); drives.note(t, pitch('C3'), 6, 98)
kit.note(t + 4, KICK, 1, 110); kit.note(t + 4, CRASH, 3, 110); latch.note(t + 6, 56, 1, 84)

finish(__file__, S, {
    'title': 'Fax Machine Fanfare',
    'pack': 'office-machinery',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'An industrial march in C, 104 bpm: a bugle call, march and trio on the civil-defence bugle, the PC speaker '
            'on the trio, twelve drives on the bass, a spacebar-kit side drum, OPL3 snare, floppy drives, keyboard '
            'clacks, a floppy latch, a hard disk spinning up.',
}, [
    ('bugle', 'ch1', 'Signal Uplink', dict(lufs=-19, pan=-4, verb=0.3)),
    ('lowbugle', 'ch2', 'White Dive', dict(lufs=-23, pan=-18, verb=0.3)),
    ('beep', 'ch3', 'Cedar Hat', dict(lufs=-23, pan=16, echo=0.15)),
    ('drives', 'ch4', 'Ocean Crowd', dict(lufs=-20)),
    ('kit', 'ch10', 'Solar Haze', dict(lufs=-18, verb=0.08)),
    ('beepkit', 'ch9', 'Winter Canopy', dict(lufs=-27, pan=-22)),
    ('floppy', 'ch5', 'Silent Uplink', dict(lufs=-26, pan=26, echo=0.2)),
    ('clack', 'ch6', 'Electric Clack', dict(lufs=-29, pan=32)),
    ('opl3', 'ch7', 'Bright Block', dict(lufs=-26, pan=4, verb=0.15)),
    ('spinup', 'ch8', 'Open Uplink', dict(lufs=-24, verb=0.2)),
    ('hum', 'ch11', 'Honey Murmur', dict(lufs=-32, width=1.3)),
    ('latch', 'ch12', 'Lucid Surge', dict(lufs=-25, pan=-28)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.2, 'tone': 3000, 'level': -10},
   reverb={'size': 1.6, 'predelay': 12, 'tone': 5000, 'level': -6})

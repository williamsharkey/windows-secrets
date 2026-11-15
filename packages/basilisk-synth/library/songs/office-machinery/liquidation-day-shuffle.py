"""Liquidation Day Shuffle: an original machine-funk piece, 104 bpm, E minor. A hard disk spins up and a tape deck
starts; then a spacebar kit and a PC-speaker kit, floppy-drive percussion, twelve drives humming the bass, a
PC-speaker riff and the civil-defence bugle."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *
chord_cap(8)   # rendered before render311 --lookahead: chords thinned to 8 recorders an instant (_lib.cap_chords)

S = Score(bpm=104, seed=1998)
kit = S.part('kit', 10)
beepkit = S.part('beepkit', 9)
drives = S.part('drives', 2)
beep = S.part('beep', 3)
bugle = S.part('bugle', 4)
spin = S.part('spinup', 5)
tape = S.part('tape', 6)
floppy = S.part('floppy', 7)
latch = S.part('latch', 8)
snare = S.part('opl3', 11)
clack = S.part('clack', 12)
hum = S.part('hum', 13)
insert = S.part('insert', 14)

ROOTS = ['E', 'E', 'C', 'D']
RIFF = 'e E5 r E5 G5 r E5 D5 B4 | e E5 r E5 G5 r A5 G5 E5 | e C5 r C5 E5 r C5 B4 G4 | e D5 r D5 F#5 r A5 F#5 D5'
BUGLE = 'q. G4 e C5 q E5 C5 | h G5 q E5 C5 | q. G4 e C5 q E5 G5 | h. C5 q r'
SW = 0.2


def beat(at, bars, fill=True):
    for k in range(bars):
        last = fill and k % 8 == 7
        kit.drums({KICK: 'x......x..x.....', SNARE: '....x.......x...' if not last else '....x.....xxxxxx',
                   CHH: 'x.x.x.x.x.x.x.x.', RIM: '.......o......o.'}, at=at + 4 * k, bars=1, swing=SW)
    snare.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 80}, swing=SW)
    clack.drums({60: '..x...x...x..x..'}, at=at, bars=bars, vel={'x': 64}, swing=SW)


def drive_bass(at, bars, vel=96):
    for k in range(bars):
        n = pitch(ROOTS[k % 4] + '2')
        for off, du in ((0, 0.9), (1.5, 0.4), (2.5, 0.4), (3, 0.9)):
            drives.note(at + 4 * k + off + (SW * 0.25 if off in (1.5, 2.5) else 0), n, du, vel)


def floppies(at, bars):
    for k in range(bars):
        if k % 2 == 1:
            floppy.note(at + 4 * k + 2.5, 60, 1.2, 76)


t = 0.0
# intro (4): spin-up, tape deck, drive hum
spin.note(0, 30, 8, 92); tape.note(6, 8, 3, 88)
hold(hum, 2, 60, 14, 70)
insert.note(12, 60, 1, 80); latch.note(14, 56, 1, 84)
t = 16
# A (16): the groove, the drives, the beep riff
beat(t, 16); drive_bass(t, 16); floppies(t, 16)
beepkit.drums({36: 'x...............', 38: '............x...', 42: '..x...x...x...x.'}, at=t + 32, bars=8, vel={'x': 70})
beep.mel(RIFF, at=t + 32, vel=84); beep.mel(RIFF, at=t + 48, vel=88)
hold(hum, t, 60, 64, 60)
t += 64
# B (8): the bugle call
beat(t, 8); drive_bass(t, 8, 100)
bugle.mel(BUGLE, at=t, vel=92); bugle.mel(BUGLE, at=t + 16, vel=96)
beepkit.drums({36: 'x.......x.......', 42: 'x.x.x.x.x.x.x.x.'}, at=t, bars=8, vel={'x': 66})
t += 32
# break (4): floppies and latches, the tape deck
for k in range(8):
    floppy.note(t + 2 * k, 60 + (k % 3) * 2, 1.2, 80)
latch.note(t + 3, 56, 1, 84); latch.note(t + 11, 56, 1, 84)
tape.note(t + 13, 8, 3, 86)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.'}, at=t + 8, bars=2, swing=SW)
t += 16
# A' (16): everything
beat(t, 16); drive_bass(t, 16, 100); floppies(t, 16)
beep.mel(RIFF, at=t, vel=88); beep.mel(RIFF, at=t + 16, vel=90)
bugle.mel(BUGLE, at=t + 32, vel=94); beep.mel(RIFF, at=t + 32, vel=78); beep.mel(RIFF, at=t + 48, vel=84)
bugle.mel(BUGLE, at=t + 48, vel=98)
beepkit.drums({36: 'x...............', 38: '............x...', 42: '..x...x...x...x.'}, at=t, bars=16, vel={'x': 70})
hold(hum, t, 60, 64, 62)
t += 64
# outro (8): down to the drives, then everything switched off
beat(t, 4, fill=False); drive_bass(t, 6, 92)
beep.mel('e E5 r E5 G5 r E5 D5 B4 | q E5 r h r', at=t + 16, vel=80)
hold(hum, t, 60, 28, 58)
tape.note(t + 24, 8, 3, 84)
bugle.mel('h. E5 q r', at=t + 24, vel=84)

finish(__file__, S, {
    'title': 'Liquidation Day Shuffle',
    'pack': 'office-machinery',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Machine funk in E minor, 104 bpm, shuffled: hard-disk spin-up, tape-deck start, a spacebar kit and a '
            'PC-speaker kit, floppy reads and latches, an OPL3 snare, keyboard clacks, twelve drives humming the bass, '
            'a PC-speaker riff and the civil-defence bugle.',
}, [
    ('kit', 'ch10', 'Rubber Canopy', dict(lufs=-17, verb=0.06)),
    ('beepkit', 'ch9', 'Coded Mist', dict(lufs=-26, pan=-22)),
    ('drives', 'ch2', 'Ocean Crowd', dict(lufs=-20)),
    ('beep', 'ch3', 'Cedar Hat', dict(lufs=-22, pan=10, echo=0.2, verb=0.15)),
    ('bugle', 'ch4', 'Signal Uplink', dict(lufs=-20, pan=-6, echo=0.15, verb=0.35)),
    ('spinup', 'ch5', 'Open Uplink', dict(lufs=-23, verb=0.2)),
    ('tape', 'ch6', 'Still Swoosh', dict(lufs=-24, verb=0.2)),
    ('floppy', 'ch7', 'Rural Burst', dict(lufs=-25, pan=26, echo=0.2)),
    ('latch', 'ch8', 'Lucid Surge', dict(lufs=-25, pan=-28)),
    ('opl3', 'ch11', 'Bright Block', dict(lufs=-25, pan=4, verb=0.15)),
    ('clack', 'ch12', 'Jade Clack', dict(lufs=-28, pan=32)),
    ('hum', 'ch13', 'Velvet Room', dict(lufs=-31, width=1.3)),
    ('insert', 'ch14', 'Yellow Hat', dict(lufs=-26, pan=18)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3000, 'level': -6},
   reverb={'size': 1.4, 'predelay': 10, 'tone': 5000, 'level': -7})

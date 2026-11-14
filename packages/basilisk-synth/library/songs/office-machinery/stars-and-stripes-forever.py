"""The Stars and Stripes Forever (John Philip Sousa, 1896), arranged for Office Machinery as a march for the
computer room: the civil-defence bugle on the tune, the PC speaker on the piccolo part, twelve drives humming the
bass, a spacebar kit for the side drum, floppy drives and keyboard clacks."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'TheStarsAndStripesForever.mid'))
S = Score(bpm=232, seed=1896)
bugle = S.part('bugle', 1)
beep = S.part('beep', 2)
low = S.part('lowbugle', 3)
drives = S.part('drives', 4)
kit = S.part('kit', 10)
beepkit = S.part('beepkit', 9)
floppy = S.part('floppy', 5)
clack = S.part('clack', 6)
snare = S.part('opl3', 7)
spin = S.part('spinup', 8)
hum = S.part('hum', 11)

# (from bar, to bar): intro and first strain, the trio, the break strain, the grandioso trio
PLAN = [(0, 20), (72, 104), (104, 128), (184, 212)]
t = 8.0
spin.note(0, 30, 8, 92)
for si, (a, b) in enumerate(PLAN):
    A, Bb = a * 4.0, b * 4.0
    rh = beats(src.tracks[0], A, Bb, t); lhn = beats(src.tracks[1], A, Bb, t)
    top = skyline(rh)
    put(bugle if si != 2 else low, top, vel=96, lo=60, hi=84)
    if si == 3:   # the grandioso: the PC speaker plays the tune an octave up (the piccolo's place)
        put(beep, top, tr=12, vel=82, lo=72, hi=96)
    if si == 1:
        put(low, [n for n in rh if n not in top], vel=70, lo=52, hi=72)
    for x, p, d, v in floor(lhn):
        n = p
        while n > 50:
            n -= 12
        while n < 33:
            n += 12
        drives.note(x, n, min(d, 1.6), 96)
    bars = b - a
    for k in range(bars):
        x = t + 4 * k
        kit.drums({KICK: 'x.......x.......', SNARE: 'x.ox....x.oxo.o.' if si != 2 else 'xoxoxoxoxoxoxoxo'}, at=x, bars=1, vel={'x': 96, 'o': 56})
        snare.drums({60: '....x.......x...'}, at=x, bars=1, vel={'x': 72})
        clack.drums({60: '..x...x...x...x.'}, at=x, bars=1, vel={'x': 60})
        if k % 4 == 3:
            floppy.note(x + 2, 60, 1.6, 78)
        if si == 3:
            beepkit.drums({36: 'x.......x.......', 42: '..x...x...x...x.'}, at=x, bars=1, vel={'x': 64})
    kit.note(t, CRASH, 2, 108)
    t += bars * 4.0
hold(hum, 0, 60, t + 4, 56, 32)
for p, lo, hi, v in ((bugle, 60, 84, 100), (low, 52, 72, 84)):
    p.chords('Ab:6', at=t, style='pad', vel=v, lo=lo, hi=hi)
drives.note(t, pitch('Ab1') + 12, 6, 100); kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 3, 110)

S.humanize(ms=3, vel=3, parts=['bugle', 'lowbugle', 'beep'])
finish(__file__, S, {
    'title': 'The Stars and Stripes Forever',
    'pack': 'office-machinery',
    'kind': 'world',
    'composer': 'John Philip Sousa (1854-1932)',
    'source': 'The Stars and Stripes Forever, march (1896), piano edition: the introduction and first strain, the '
              'trio, the break strain and the grandioso. Score: The Mutopia Project, from The John Church Company '
              '(Cincinnati, 1897).',
    'licence': 'The work: public domain (published 1897; the composer died 1932). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=626',
    'arranger': 'Algorithmic Industries house band',
    'note': 'A march for the computer room in cut time: the civil-defence bugle on the tune (a lower bugle in the '
            'break strain), the PC speaker on the grandioso\'s piccolo line, twelve drives on the bass, a spacebar '
            'kit side drum, an OPL3 snare, floppy drives, keyboard clacks and a hard disk spinning up.',
}, [
    ('bugle', 'ch1', 'Signal Uplink', dict(lufs=-19, pan=-4, verb=0.3)),
    ('beep', 'ch2', 'Cedar Hat', dict(lufs=-23, pan=16, echo=0.15)),
    ('lowbugle', 'ch3', 'White Dive', dict(lufs=-22, pan=-18, verb=0.3)),
    ('drives', 'ch4', 'Ocean Crowd', dict(lufs=-20)),
    ('kit', 'ch10', 'Rubber Canopy', dict(lufs=-18, verb=0.08)),
    ('beepkit', 'ch9', 'Coded Mist', dict(lufs=-27, pan=-22)),
    ('floppy', 'ch5', 'Rural Burst', dict(lufs=-26, pan=26, echo=0.2)),
    ('clack', 'ch6', 'Jade Clack', dict(lufs=-29, pan=32)),
    ('opl3', 'ch7', 'Bright Block', dict(lufs=-26, pan=4, verb=0.15)),
    ('spinup', 'ch8', 'Open Uplink', dict(lufs=-24, verb=0.2)),
    ('hum', 'ch11', 'Velvet Room', dict(lufs=-32, width=1.3)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.2, 'tone': 3000, 'level': -10},
   reverb={'size': 1.6, 'predelay': 12, 'tone': 5000, 'level': -6})

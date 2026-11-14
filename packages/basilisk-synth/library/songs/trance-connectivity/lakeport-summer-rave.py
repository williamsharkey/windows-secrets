"""Lakeport Summer Rave: an original progressive trance track, 132 bpm, E minor. A gated pluck pattern builds for
sixteen bars, a rolling bass under it, a long breakdown on the breakdown grand and choir, then the motor-whine
lead with brass chords."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=132, seed=1999)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
pluck = S.part('pluck', 3)
lead = S.part('lead', 4)
pad = S.part('pad', 5)
brass = S.part('brass', 6)
piano = S.part('piano', 7)
riser = S.part('riser', 8)
choir = S.part('choir', 9)
plink = S.part('plink', 11)
fx = S.part('fx', 12)

PROG = 'Em C G D'
GATE = 'x.xx.x.xx.x.xx.x'
LEAD = ('q. B5 e A5 q G5 E5 | q. C6 e B5 h G5 | q. B5 e D6 q B5 G5 | h A5 F#5 | '
        'q. B5 e A5 q G5 E5 | q. C6 e D6 h E6 | q. D6 e B5 q G5 B5 | w A5')
ROLL = [(b + o, 0, 0.2) for b in range(4) for o in (0.25, 0.5, 0.75)]


def gated(at, bars, vel=66):
    t, prev = at, None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG.split()[k % 4], 4), 60, 76); prev = ns
        for i, c in enumerate(GATE):
            if c == 'x':
                pluck.note(t + i * 0.25, ns[(i // 2) % len(ns)] + (12 if i >= 8 else 0), 0.2, vel)
        t += 4


t = 0.0
groove(kit, 'trance', 0, 8, drop=(CHH, CLAP)); gated(0, 8, 54)
plink.drums({76: 'x..x..x.x..x..x.'}, at=16, bars=4, vel={'x': 64})
t = 32
groove(kit, 'trance', t, 15); groove(kit, 'trance', t + 60, 1, fill=True)
bass.bass(' '.join([PROG] * 4), at=t, beats=4, pattern=ROLL, vel=100); gated(t, 16, 66)
pad.chords(' '.join([PROG] * 4), at=t + 32, beats=4, style='pad', vel=54, lo=55, hi=72)
fx.note(t + 56, 60, 8, 80)
t += 64
# breakdown
piano.chords(' '.join([PROG] * 4), at=t, beats=4, style='arpud', vel=64, lo=55, hi=79, rhythm=0.5)
piano.mel(LEAD, at=t + 32, vel=82, tr=-12)
choir.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=62, lo=55, hi=70)
riser.note(t + 32, 60, 31.5, 86)
kit.drums({SNARE: 'x...x...x...x...'}, at=t + 48, bars=3, vel={'x': 62})
kit.drums({SNARE: 'x.x.x.x.x.x.x.x.xxxxxxxxxxxxxxxx'}, at=t + 56, bars=2, vel={'x': 84})
t += 64
# drop
kit.note(t, CRASH, 1.5, 116)
groove(kit, 'trance', t, 31); groove(kit, 'trance', t + 124, 1, fill=True)
bass.bass(' '.join([PROG] * 8), at=t, beats=4, pattern=ROLL, vel=104); gated(t, 32, 68)
for k in range(4):
    lead.mel(LEAD, at=t + 32 * k, vel=94 if k % 2 == 0 else 98, tr=-12)
brass.chords(' '.join([PROG] * 8), at=t, beats=4, style='block', vel=70, lo=55, hi=72, rhythm=[(0, 0.7), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)])
pad.chords(' '.join([PROG] * 8), at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
t += 128
groove(kit, 'trance', t, 4, drop=(CHH, CLAP)); gated(t, 4, 56)
t += 16
pad.chords('Em:8', at=t, style='pad', vel=60, lo=55, hi=72); kit.note(t, KICK, 1, 104)

S.humanize(ms=2, vel=3, parts=['piano', 'lead'])
finish(__file__, S, {
    'title': 'Lakeport Summer Rave',
    'pack': 'trance-connectivity',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Progressive trance in E minor, 132 bpm: a gated pluck pattern, a rolling bass, plinks, a long breakdown on '
            'the breakdown grand and choir with a riser, then the motor-whine lead with brass chords. Drums: Kit '
            'Manager 98 (Punch Kick Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Punch Kick Kit', dict(lufs=-16, verb=0.05)),
    ('bass', 'ch2', 'Northern Pulse', dict(lufs=-19)),
    ('pluck', 'ch3', 'Broadcast Harp', dict(lufs=-23, pan=-16, echo=0.3, verb=0.2)),
    ('lead', 'ch4', 'Opal Ray', dict(lufs=-19, pan=4, echo=0.25, verb=0.3)),
    ('pad', 'ch5', 'Misty Veil', dict(lufs=-25, verb=0.4, width=1.4)),
    ('brass', 'ch6', 'Civic Brass', dict(lufs=-23, pan=14, verb=0.25)),
    ('piano', 'ch7', 'Hollow Salon', dict(lufs=-20, pan=-4, echo=0.15, verb=0.45)),
    ('riser', 'ch8', 'Plaza Riser', dict(lufs=-25, verb=0.4)),
    ('choir', 'ch9', 'Coral Tide', dict(lufs=-25, verb=0.45, width=1.3)),
    ('plink', 'ch11', 'Echo Plink', dict(lufs=-26, pan=30, echo=0.35)),
    ('fx', 'ch12', 'Washed Lift', dict(lufs=-26, verb=0.4)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.4, 'tone': 3500, 'level': -3},
   reverb={'size': 2.8, 'predelay': 22, 'tone': 6000, 'level': -5})

"""Aquarium (Level 3): an original slowed mall-pop piece, 74 bpm, D-flat major. Tank bubbles and an aquarium
screensaver bell, a rounded major-seventh chord, the slow-jam bass, VHS bell pad, hold music in the distance, the
atrium keys and a goodbye pad at closing time."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=74, seed=2002)
kit = S.part('kit', 10)
bubbles = S.part('bubbles', 1)
bell = S.part('bell', 2)
chordp = S.part('chord', 3)
bass = S.part('bass', 4)
vhs = S.part('vhspad', 5)
hold_ = S.part('holdmusic', 6)
keys = S.part('keys', 7)
goodbye = S.part('goodbye', 8)
reef = S.part('reef', 9)
ping = S.part('ping', 11)

PROG = 'Dbmaj7 Cm7 Bbm7 Gbmaj7'
MEL = 'h. F5 e Eb5 F5 | w Eb5 | h. Db5 e C5 Db5 | w Bb4 | h. Ab5 e Gb5 F5 | w Eb5 | h F5 Eb5 | w Db5'

t = 0.0
hold(reef, 0, 44, 16, 80, 12)
bubbles.note(2, 60, 3, 76); ping.note(8, 91, 2, 66)
t = 16
for sec in range(4):
    groove(kit, 'boombap', t, 8, swing=0.2) if sec in (1, 2) else None
    chordp.drums({60: '..x.....x.x.....'}, at=t, bars=8, vel={'x': 70})
    bass.bass(' '.join([PROG] * 2), at=t, beats=4, pattern=[(0, 0, 1.4), (1.5, '8', 0.4), (2.5, 0, 1.2)], vel=92)
    vhs.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=58, lo=53, hi=70)
    if sec == 0:
        bell.mel(MEL, at=t, vel=80)
    if sec == 1:
        keys.mel(MEL, at=t, vel=84); bubbles.note(t + 12, 60, 3, 70)
    if sec == 2:
        keys.mel(MEL, at=t, vel=86); bell.mel(MEL, at=t, vel=62, tr=12)
        hold_.note(t + 4, 60, 12, 54)
    if sec == 3:
        bell.mel(MEL, at=t, vel=76); goodbye.chords('Dbmaj7:16 Gbmaj7:16', at=t, style='pad', vel=58, lo=50, hi=67)
    t += 32
ping.note(t, 91, 3, 64); bubbles.note(t, 60, 3, 70); hold(reef, t, 44, 12, 70, 12)

S.humanize(ms=8, vel=5, parts=['bell', 'keys', 'bass'])
finish(__file__, S, {
    'title': 'Aquarium (Level 3)',
    'pack': 'lifestyle-aesthetics',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Slowed mall-pop in D-flat, 74 bpm: tank bubbles, the reef pad, the aquarium screensaver bell, the rounded '
            'major-seventh chord, the slow-jam bass, a VHS bell pad, distant hold music, the atrium keys, a reflection '
            'ping and the goodbye pad at closing. Drums: Kit Manager 98 (Echo Chamber Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', dict(lufs=-20, verb=0.2, lp=8000)),
    ('bubbles', 'ch1', 'Tank Bubbles', dict(lufs=-26, pan=-24, verb=0.4)),
    ('bell', 'ch2', 'Aquarium Screensaver', dict(lufs=-21, pan=10, echo=0.3, verb=0.45)),
    ('chord', 'ch3', 'Rounded Corner Chord', dict(lufs=-25, pan=-20, echo=0.3, verb=0.3)),
    ('bass', 'ch4', 'Slow Jam Bass', dict(lufs=-20)),
    ('vhspad', 'ch5', 'VHS Bell Pad', dict(lufs=-26, verb=0.4, width=1.3)),
    ('holdmusic', 'ch6', 'Hold Music Loop', dict(lufs=-30, pan=30, lp=3000, verb=0.4)),
    ('keys', 'ch7', 'Atrium Keys', dict(lufs=-20, pan=-6, echo=0.2, verb=0.35)),
    ('goodbye', 'ch8', 'Goodbye Pad', dict(lufs=-26, verb=0.45, width=1.3)),
    ('reef', 'ch9', 'Reef Pad', dict(lufs=-29, width=1.4)),
    ('ping', 'ch11', 'Reflection Ping', dict(lufs=-27, pan=26, echo=0.4, verb=0.5)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.4, 'tone': 2800, 'level': -4},
   reverb={'size': 3.2, 'predelay': 30, 'tone': 4500, 'level': -3})

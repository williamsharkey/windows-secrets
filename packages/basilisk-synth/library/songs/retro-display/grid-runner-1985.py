"""Grid Runner 1985: an original outrun track, 118 bpm, A minor. Driving sixteenth bass, gated drums, a laser grid
sweep, the sun-glare lead, digital hammers, the night-window strings and the rooftop sax for the last chorus."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=118, seed=1985)
kit = S.part('kit', 10)
bass = S.part('bass', 1)
lead = S.part('lead', 2)
hammers = S.part('hammers', 3)
strings = S.part('strings', 4)
sax = S.part('sax', 5)
sweep = S.part('sweep', 6)
pad = S.part('pad', 7)
snare2 = S.part('snare2', 8)
arp = S.part('arp', 9)

PROG = 'Am F C G'
VERSE = 'q. E5 e D5 q C5 A4 | h. C5 q D5 | q. E5 e G5 q E5 D5 | h. D5 q r'
CHORUS = 'h A5 q G5 E5 | h F5 q E5 C5 | h G5 q E5 C5 | h. D5 q B4 | h A5 q G5 E5 | h F5 q A5 C6 | h B5 q G5 D5 | w E5'


def drive(at, bars, vel=98):
    bass.bass(' '.join([PROG] * (bars // 4)), at=at, beats=4, pattern=[(i * 0.25, 0 if i % 4 else '8', 0.2) for i in range(16)], vel=vel)


def drums(at, bars):
    groove(kit, 'synthpop', at, bars - 1, extra={KICK: 'x...x...x...x...'}); groove(kit, 'synthpop', at + 4 * (bars - 1), 1, fill=True)
    snare2.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 88})


def arps(at, bars):
    arp.chords(' '.join([PROG] * (bars // 4)), at=at, beats=4, style='arpud', vel=56, lo=64, hi=84, rhythm=0.25)


t = 0.0
sweep.note(0, 60, 8, 84); pad.chords(PROG + ' ' + PROG, at=0, beats=4, style='pad', vel=58, lo=52, hi=71)
drive(16, 4, 86)
t = 32
drums(t, 16); drive(t, 16); arps(t + 32, 8)
for k in range(4):
    lead.mel(VERSE, at=t + 16 * k, vel=88)
hammers.chords(' '.join([PROG] * 4), at=t, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(0, 0.4), (0.75, 0.3), (2, 0.4), (2.75, 0.3)])
t += 64
drums(t, 8); drive(t, 8, 102); arps(t, 8)
lead.mel(CHORUS, at=t, vel=96); strings.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
t += 32
# break: strings and the sweep over the drive
drive(t, 8, 90); strings.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=70, lo=55, hi=72)
sweep.note(t + 24, 60, 8, 84); kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxXXXX'}, at=t + 24, bars=2)
t += 32
kit.note(t, CRASH, 2, 110)
drums(t, 8); drive(t, 8, 104); arps(t, 8)
sax.mel(CHORUS, at=t, vel=96, tr=-12); lead.mel(CHORUS, at=t, vel=86)
strings.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=62, lo=55, hi=72)
t += 32
drive(t, 4, 90); pad.chords('Am:16', at=t, style='pad', vel=60, lo=52, hi=71); lead.mel('h A5 E5 | w A4', at=t, vel=84)
t += 16
kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 2, 100)

S.humanize(ms=2, vel=3, parts=['lead', 'sax'])
finish(__file__, S, {
    'title': 'Grid Runner 1985',
    'pack': 'retro-display',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Outrun in A minor, 118 bpm: a driving sixteenth bass, four-on-the-floor gated drums, the laser grid sweep, '
            'the sun-glare lead, digital hammers, kalimba arpeggios, night-window strings and the rooftop sax on the '
            'last chorus. Drums: Kit Manager 98 (Echo Chamber Kit) with the pack\'s Yellow Snare.',
}, [
    ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', dict(lufs=-17, verb=0.12)),
    ('bass', 'ch1', 'Remote Basement', dict(lufs=-19)),
    ('lead', 'ch2', 'Sun Glare Lead', dict(lufs=-20, pan=4, echo=0.25, verb=0.3)),
    ('hammers', 'ch3', 'Digital Hammers', dict(lufs=-24, pan=-18, verb=0.25)),
    ('strings', 'ch4', 'Night Window Strings', dict(lufs=-24, pan=14, verb=0.35, width=1.3)),
    ('sax', 'ch5', 'Rooftop Sax Lead', dict(lufs=-20, pan=-6, echo=0.2, verb=0.35)),
    ('sweep', 'ch6', 'Laser Grid Sweep', dict(lufs=-26, verb=0.4)),
    ('pad', 'ch7', 'Laser Glow', dict(lufs=-27, verb=0.4, width=1.4)),
    ('snare2', 'ch8', 'Yellow Snare', dict(lufs=-26, verb=0.4)),
    ('arp', 'ch9', 'Violet Chords', dict(lufs=-26, pan=24, echo=0.3, verb=0.2)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3200, 'level': -3},
   reverb={'size': 2.6, 'predelay': 18, 'tone': 5500, 'level': -5})

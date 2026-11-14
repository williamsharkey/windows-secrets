"""Session Musician on Call: an original new jack swing track, 100 bpm, G minor. A swung machine beat, a slap-ish
bass, stabbing brass, an organ bark, the chorus on the vocal pad, the tines and a lead in the bridge."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=100, seed=1990)
kit = S.part('kit', 10)
bass = S.part('bass', 1)
brass = S.part('brass', 2)
organ = S.part('organ', 3)
vox = S.part('vox', 4)
tines = S.part('tines', 5)
lead = S.part('lead', 6)
piano = S.part('piano', 7)
plink = S.part('plink', 8)
strings = S.part('strings', 9)

PROG = 'Gm7 Cm7 F7 Bbmaj7'
SW = 0.3
HOOK = 'q. Bb4 e C5 q D5 r | q. F5 e D5 h C5 | q. Bb4 e C5 q D5 F5 | h. G5 q r'
BRIDGE = 'Ebmaj7 D7 Gm7 C7 Ebmaj7 D7 Gm7 D7'


def swing_beat(at, bars):
    for k in range(bars):
        kit.drums({KICK: 'x..x..x...x..x..', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.', CLAP: '....x.......x...'},
                  at=at + 4 * k, bars=1, swing=SW)


def bassline(at, prog, reps, vel=98):
    pat = [(0, 0, 0.4), (0.75 + SW * 0.25, '8', 0.2), (1.5, 0, 0.3), (2.5, '5', 0.3), (3, '7', 0.3), (3.5, '8', 0.3)]
    bass.bass(' '.join([prog] * reps), at=at, beats=4, pattern=pat, vel=vel)


def stabs(at, prog, reps, vel=82):
    brass.chords(' '.join([prog] * reps), at=at, beats=4, style='block', vel=vel, lo=55, hi=72, rhythm=[(0, 0.3), (1.75 + SW * 0.25, 0.3), (3, 0.3)])


t = 0.0
strings.chords(PROG, at=0, beats=4, style='pad', vel=60, lo=55, hi=72)
plink.chords(PROG, at=0, beats=4, style='arp', vel=54, lo=62, hi=84, rhythm=0.5)
t = 16
swing_beat(t, 16); bassline(t, PROG, 4); stabs(t, PROG, 4)
organ.chords(' '.join([PROG] * 2), at=t + 32, beats=4, style='block', vel=56, lo=55, hi=70, rhythm=[(0.75, 0.3), (2.75, 0.3)])
for k in range(4):
    lead.mel(HOOK, at=t + 16 * k, vel=88 if k < 2 else 92)
t += 64
# chorus: the vocal pad sings the hook, tines underneath
swing_beat(t, 16); bassline(t, PROG, 4, 100); stabs(t, PROG, 4, 86)
for k in range(4):
    vox.mel(HOOK, at=t + 16 * k, vel=90, tr=12 if k % 2 else 0)
tines.chords(' '.join([PROG] * 4), at=t, beats=4, style='block', vel=58, lo=58, hi=74, rhythm=[(0, 1.4), (2.5, 1.0)])
t += 64
# bridge
swing_beat(t, 8); bassline(t, BRIDGE, 1, 94)
piano.chords(BRIDGE, at=t, beats=4, style='block', vel=62, lo=55, hi=72, rhythm=[(0, 1.4), (1.5, 0.4), (2.5, 1.2)])
lead.mel('h G5 q F5 Eb5 | h F#5 q D5 A4 | h Bb4 q D5 G5 | h E5 q C5 G4 | h G5 q Bb5 G5 | h A5 q F#5 D5 | w G5 | h F#5 A5', at=t, vel=90)
strings.chords(BRIDGE, at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
t += 32
kit.note(t, CRASH, 2, 108)
swing_beat(t, 16); bassline(t, PROG, 4, 102); stabs(t, PROG, 4, 88)
for k in range(4):
    vox.mel(HOOK, at=t + 16 * k, vel=92, tr=12); lead.mel(HOOK, at=t + 16 * k, vel=74)
t += 64
brass.chords('Gm7:4', at=t, style='pad', vel=88, lo=55, hi=72); kit.note(t, KICK, 1, 104); bass.note(t, pitch('G2'), 2, 100)

S.humanize(ms=3, vel=4, parts=['lead', 'vox', 'piano', 'tines'])
finish(__file__, S, {
    'title': 'Session Musician on Call',
    'pack': 'rom-reference',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'New jack swing in G minor, 100 bpm: a swung machine beat, a bouncing bass, brass stabs, an organ bark, the '
            'hook on a lead and the vocal pad, tines, a piano bridge, strings and plinks. Drums: Kit Manager 98 '
            '(Breaker Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-16.5, verb=0.08)),
    ('bass', 'ch1', 'Digital Low', dict(lufs=-19)),
    ('brass', 'ch2', 'Granite Horns', dict(lufs=-22, pan=14, verb=0.2)),
    ('organ', 'ch3', 'Pastel Bark', dict(lufs=-26, pan=-22, verb=0.2)),
    ('vox', 'ch4', 'Dial Ahh', dict(lufs=-21, pan=-4, echo=0.15, verb=0.35)),
    ('tines', 'ch5', 'Jade Tines', dict(lufs=-24, pan=-16, verb=0.3)),
    ('lead', 'ch6', 'Rubber Line', dict(lufs=-20, pan=6, echo=0.2, verb=0.3)),
    ('piano', 'ch7', 'Still Ballad', dict(lufs=-22, pan=-10, verb=0.3)),
    ('plink', 'ch8', 'Orbital Plink', dict(lufs=-27, pan=28, echo=0.3)),
    ('strings', 'ch9', 'Zinc Ensemble', dict(lufs=-25, pan=10, verb=0.4, width=1.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -5},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 6000, 'level': -5})

"""Mailing List Riot: an original big beat track, 124 bpm, E minor. A fat break, a growling bass riff, the stadium
riff stab, orchestra hits, the block-party siren, a robot voice, a rising synth and a breakdown on keys."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=124, seed=1998)
kit = S.part('kit', 10)
bass = S.part('bass', 1)
riff = S.part('riff', 2)
hit = S.part('hit', 3)
siren = S.part('siren', 4)
robot = S.part('robot', 5)
keys = S.part('keys', 6)
lead = S.part('lead', 7)
snare = S.part('snare', 8)
clap = S.part('clap', 9)
fx = S.part('fx', 11)
pad = S.part('pad', 12)

BIG = [{KICK: 'x.....x...x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.', OHH: '..............x.'},
       {KICK: 'x.....x.x.x.....', SNARE: '....x.......x..o', CHH: 'x.x.x.x.x.x.x.x.'},
       {KICK: 'x.....x...x...x.', SNARE: '....x...o...x...', CHH: 'x.x.x.x.x.x.xxxx'},
       {KICK: 'x.....x...x.....', SNARE: '....x...x.x.xxXX', CHH: 'x.x.x.x.........'}]
BASSRIFF = 'e E2 E2 r E3 r D3 r B2 | e E2 E2 r G2 r A2 B2 r'
RIFF = 'q E4 e r G4 q A4 e B4 r | q D5 e B4 r h r'


def beat(at, bars):
    for k in range(bars):
        kit.drums(BIG[k % 4] if (k % 8) != 7 else BIG[3], at=at + 4 * k, bars=1)
    snare.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 86})
    clap.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 70})


def bassline(at, bars):
    for k in range(0, bars, 2):
        bass.mel(BASSRIFF, at=at + 4 * k, vel=100, tr=12)


t = 0.0
siren.note(0, 60, 3.5, 92)
riff.mel(RIFF + ' | ' + RIFF, at=4, vel=88)
fx.note(8, 60, 8, 80)
t = 20
kit.note(t, CRASH, 2, 116); hit.note(t, pitch('E5'), 0.5, 100)
beat(t, 16); bassline(t, 16)
for k in range(8):
    riff.mel(RIFF, at=t + 8 * k, vel=90)
for k in (0, 4, 8, 12):
    hit.note(t + 4 * k, pitch('E5'), 0.5, 96)
t += 64
robot.mel('h E4 G4 | w A4 | h B4 D5 | w E5', at=t - 16, vel=88)
beat(t, 16); bassline(t, 16)
lead.mel('w E5 | w G5 | w A5 | w B5 | w D6 | w B5 | w A5 | w G5 | w E5 | w G5 | w A5 | w B5 | h D6 E6 | w D6 | w B5 | w E6', at=t, vel=86)
pad.chords('Em C G D ' * 4, at=t, beats=4, style='pad', vel=54, lo=55, hi=72)
siren.note(t + 60, 60, 3.5, 90)
t += 64
# breakdown
keys.chords('Em C G D Em C G D', at=t, beats=4, style='block', vel=64, lo=55, hi=72, rhythm=[(0, 1.4), (1.5, 0.4), (2.5, 1.2)])
robot.mel('h E4 G4 | w A4 | h B4 D5 | w E5 | h E4 G4 | w A4 | h B4 A4 | w G4', at=t, vel=84)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=6); kit.drums({SNARE: 'x.x.x.x.xxxxXXXX'}, at=t + 28, bars=1)
fx.note(t + 24, 60, 8, 84)
t += 32
kit.note(t, CRASH, 2, 118); hit.note(t, pitch('E5'), 0.5, 104); siren.note(t, 60, 3.5, 94)
beat(t, 16); bassline(t, 16)
for k in range(8):
    riff.mel(RIFF, at=t + 8 * k, vel=92)
lead.mel('w E5 | w G5 | w A5 | w B5 | w D6 | w B5 | w A5 | w G5', at=t + 32, vel=88)
t += 64
hit.note(t, pitch('E5'), 1, 104); kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 3, 110); bass.note(t, pitch('E3'), 2, 100)

finish(__file__, S, {
    'title': 'Mailing List Riot',
    'pack': 'breakbeat-resource',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Big beat in E minor, 124 bpm: a fat break with the pack\'s snare and clap on top, a growling bass riff, the '
            'stadium riff stab, orchestra hits, the block-party siren, a robot voice, a rising synth, a keys '
            'breakdown. Drums: Kit Manager 98 (Breaker Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-16, verb=0.08)),
    ('bass', 'ch1', 'Night End', dict(lufs=-19)),
    ('riff', 'ch2', 'Stadium Riff Stab', dict(lufs=-20, pan=-8, verb=0.2)),
    ('hit', 'ch3', 'Breaker Orchestra Hit', dict(lufs=-21, verb=0.3)),
    ('siren', 'ch4', 'Block Party Siren', dict(lufs=-23, echo=0.35, verb=0.3)),
    ('robot', 'ch5', 'Robot Workgroup Voice', dict(lufs=-21, pan=10, echo=0.2, verb=0.3)),
    ('keys', 'ch6', 'Night Upright', dict(lufs=-22, pan=-16, verb=0.3)),
    ('lead', 'ch7', 'Steady Ray', dict(lufs=-22, pan=14, echo=0.25, verb=0.3)),
    ('snare', 'ch8', 'Office Snare', dict(lufs=-26, pan=6)),
    ('clap', 'ch9', 'Inland Clap', dict(lufs=-27, pan=-6, verb=0.2)),
    ('fx', 'ch11', 'Mint Uplink', dict(lufs=-26, verb=0.4)),
    ('pad', 'ch12', 'Cathode Bloom', dict(lufs=-26, verb=0.4, width=1.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3000, 'level': -5},
   reverb={'size': 1.8, 'predelay': 15, 'tone': 5000, 'level': -6})

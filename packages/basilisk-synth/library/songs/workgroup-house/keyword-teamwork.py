"""Keyword: Teamwork: an original French-touch filter house track, 124 bpm, G minor. An organ riff through a
sweep, a disco bass, strings, the robot-mouth talking a hook, choir in the breakdown, a modem in the outro."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=124, seed=97)
kit = S.part('kit', 10)
organ = S.part('organ', 1)
bass = S.part('bass', 2)
strings = S.part('strings', 3)
robot = S.part('robot', 4)
choir = S.part('choir', 5)
keys = S.part('keys', 6)
fx = S.part('fx', 7)
modem = S.part('modem', 8)
hat = S.part('dialhat', 9)
pluck = S.part('pluck', 11)

PROG = 'Gm7 Gm7 Ebmaj7 F'
RIFF = 'e G4 r Bb4 G4 r D5 r C5 | e Bb4 r G4 Bb4 r C5 D5 r | e Eb5 r G4 Eb5 r D5 r C5 | e D5 r F4 A4 r C5 r A4'
HOOK = 'q. D5 e C5 q Bb4 G4 | h. r q r | q. D5 e F5 q Eb5 D5 | h. C5 q r'


def bassline(at, bars, vel=100):
    pat = [(0, 0, 0.4), (0.5, '8', 0.3), (1.5, 0, 0.3), (2, '8', 0.4), (2.75, 0, 0.2), (3, '5', 0.4), (3.5, '8', 0.3)]
    bass.bass(' '.join([PROG] * (bars // 4)), at=at, beats=4, pattern=pat, vel=vel)


def beat(at, bars, lite=False):
    groove(kit, 'house_lite' if lite else 'house', at, bars - 1); groove(kit, 'house', at + 4 * (bars - 1), 1, fill=not lite)
    hat.drums({60: 'o.x.o.x.o.x.o.xo'}, at=at, bars=bars, vel={'x': 70, 'o': 44})


t = 0.0
organ.mel(RIFF + ' | ' + RIFF, at=0, vel=80)
fx.note(16, 60, 15.5, 84)
beat(16, 4, lite=True)
t = 32
beat(t, 16); bassline(t, 16)
for k in range(4):
    organ.mel(RIFF, at=t + 16 * k, vel=86)
strings.chords(' '.join([PROG] * 2), at=t + 32, beats=4, style='pad', vel=58, lo=55, hi=72)
t += 64
for k in range(4):
    robot.mel(HOOK, at=t + 16 * k, vel=92)
    organ.mel(RIFF, at=t + 16 * k, vel=80)
beat(t, 16); bassline(t, 16, 104)
pluck.chords(' '.join([PROG] * 4), at=t, beats=4, style='arp', vel=56, lo=62, hi=79, rhythm=0.25)
t += 64
# breakdown
choir.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=66, lo=55, hi=70)
keys.chords(' '.join([PROG] * 2), at=t, beats=4, style='block', vel=62, lo=55, hi=72, rhythm=[(0, 1.4), (1.5, 0.4), (2.5, 1.2)])
robot.mel(HOOK + ' | ' + HOOK, at=t, vel=84)
fx.note(t + 24, 48, 7.8, 84)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=t + 24, bars=2, vel={'x': 74})
t += 32
kit.note(t, CRASH, 2, 110)
beat(t, 16); bassline(t, 16, 104)
for k in range(4):
    organ.mel(RIFF, at=t + 16 * k, vel=88); robot.mel(HOOK, at=t + 16 * k, vel=94)
strings.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
t += 64
beat(t, 4, lite=True); organ.mel(RIFF, at=t, vel=74)
modem.note(t + 4, 60, 12, 80)
t += 16
organ.note(t, pitch('G4'), 2, 84); kit.note(t, KICK, 1, 104)

S.humanize(ms=2, vel=3, parts=['robot', 'keys', 'strings'])
finish(__file__, S, {
    'title': 'Keyword: Teamwork',
    'pack': 'workgroup-house',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'French-touch filter house in G minor, 124 bpm: an organ riff, a disco bass, strings, sixteenth plucks, '
            'the robot mouth\'s hook, a choir and tine-EP breakdown, a sweep, the modem in the outro. Drums: Kit Manager '
            '98 (Jack Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Jack Box Kit', dict(lufs=-17, verb=0.05)),
    ('organ', 'ch1', 'Humid Organ', dict(lufs=-20, pan=-8, echo=0.15, verb=0.15)),
    ('bass', 'ch2', 'Round Floor Sub', dict(lufs=-19)),
    ('strings', 'ch3', 'Cathode Strings', dict(lufs=-25, pan=20, verb=0.35)),
    ('robot', 'ch4', 'Robot Mouth Lead', dict(lufs=-20, pan=6, echo=0.25, verb=0.2)),
    ('choir', 'ch5', 'Felt Field', dict(lufs=-25, verb=0.45, width=1.3)),
    ('keys', 'ch6', 'Coral Ballad', dict(lufs=-23, pan=-20, echo=0.15, verb=0.25)),
    ('fx', 'ch7', 'Low-Pass Sweep Wash', dict(lufs=-25, echo=0.3, verb=0.3)),
    ('modem', 'ch8', 'Polar Ascent', dict(lufs=-25, echo=0.3, verb=0.3)),
    ('dialhat', 'ch9', 'Dial Hat', dict(lufs=-28, pan=30)),
    ('pluck', 'ch11', 'Steel Flick', dict(lufs=-25, pan=26, echo=0.25)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3200, 'level': -4},
   reverb={'size': 1.8, 'predelay': 16, 'tone': 6000, 'level': -5})

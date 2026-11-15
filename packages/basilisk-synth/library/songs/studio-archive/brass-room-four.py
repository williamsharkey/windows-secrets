"""Brass Room Four: an original concert march for the Studio Instruments Archive, 112 bpm, B-flat major. A fanfare
on trumpets and horns, the march on the trombone section, a trio for the bells and woodwind-ish keys, the strings
taking the last strain, timpani-style taps."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=112, seed=1995)
trumpet = S.part('trumpet', 1)
horns = S.part('horns', 2)
trombone = S.part('trombones', 3)
tuba = S.part('bass', 4)
bells = S.part('bells', 5)
keys = S.part('keys', 6)
strings = S.part('strings', 7)
cellos = S.part('cellos', 8)
snap = S.part('snap', 9)
tap = S.part('tap', 11)
piano = S.part('piano', 12)

FANFARE = 'e F5 F5 q Bb5 e F5 F5 q D6 | h C6 q Bb5 r | e F5 F5 q Bb5 e D6 C6 q Bb5 | h F6 h r'
MARCH = 'q Bb4 D5 F5 Bb5 | h A5 q G5 F5 | q Eb5 G5 C6 Bb5 | h. A5 q r | q C5 Eb5 G5 C6 | h Bb5 q A5 G5 | q F5 G5 A5 C6 | h. Bb5 q r'
TRIO = 'h D5 q Eb5 F5 | h G5 F5 | q Eb5 D5 C5 D5 | h. Bb4 q r | h C5 q D5 Eb5 | h F5 G5 | q F5 Eb5 D5 C5 | h. Bb4 q r'
PM = 'Bb F7 Cm F Cm Bb/D F7 Bb'
PT = 'Eb Eb Ab Eb F7 Bb F7 Bb'


def band(at, prog, vel=84):
    for k, sy in enumerate(prog.split()):
        r = root_of(sy, 2)
        tuba.note(at + 4 * k, r + 12, 0.9, vel); tuba.note(at + 4 * k + 2, r + 19 if r + 19 <= 52 else r + 7, 0.9, vel - 6)
        snap.note(at + 4 * k + 1, 60, 0.2, 64); snap.note(at + 4 * k + 3, 60, 0.2, 64)
        tap.note(at + 4 * k, 60, 0.3, 74)
    trombone.chords(prog, at=at, beats=4, style='block', vel=vel - 14, lo=50, hi=64, rhythm=[(1, 0.6), (3, 0.6)])


t = 0.0
trumpet.mel(FANFARE, at=0, vel=96); horns.mel(FANFARE, at=0, vel=78, tr=-12)
tap.drums({60: 'x...x...x...x...'}, at=0, bars=4, vel={'x': 80})
t = 16
band(t, PM); horns.mel(MARCH, at=t, vel=90)
t += 32
band(t, PM); trumpet.mel(MARCH, at=t, vel=92); horns.mel(MARCH, at=t, vel=74, tr=-12); piano.chords(PM, at=t, beats=4, style='block', vel=56, lo=55, hi=72, rhythm=[(1, 0.6), (3, 0.6)])
t += 32
band(t, PT, 74); bells.mel(TRIO, at=t, vel=84, tr=12); keys.mel(TRIO, at=t, vel=74)
cellos.chords(PT, at=t, beats=4, style='pad', vel=58, lo=43, hi=58)
t += 32
band(t, PT, 78); strings.mel(TRIO, at=t, vel=88, tr=12); horns.mel(TRIO, at=t, vel=76); bells.mel(TRIO, at=t + 16, vel=62, tr=24)
cellos.chords(PT, at=t, beats=4, style='pad', vel=60, lo=43, hi=58)
t += 32
trumpet.mel(FANFARE, at=t, vel=98); horns.mel(FANFARE, at=t, vel=80, tr=-12)
band(t, 'Bb F7 Bb F7', 86)
t += 16
band(t, PM, 90); trumpet.mel(MARCH, at=t, vel=96); strings.mel(MARCH, at=t, vel=80, tr=12); horns.mel(MARCH, at=t, vel=78, tr=-12)
t += 32
for p, lo, hi, v in ((trumpet, 62, 77, 96), (horns, 53, 69, 84), (trombone, 46, 62, 82), (strings, 62, 81, 76), (cellos, 41, 55, 70)):
    p.chords('Bb:6', at=t, style='pad', vel=v, lo=lo, hi=hi)
tuba.note(t, pitch('Bb1') + 12, 6, 92); tap.drums({60: 'xxxxxxxx'}, at=t, bars=1, step=0.125, beats_per_bar=1.0, vel={'x': 84})

S.humanize(ms=5, vel=4)
finish(__file__, S, {
    'title': 'Brass Room Four',
    'pack': 'studio-archive',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A concert march in B-flat, 112 bpm: a trumpet and horn fanfare, the march on horns and trumpet over '
            'trombone off-beats and a marimba bass, a trio for glockenspiel and keys with cellos, the strings on the '
            'last strain, snaps and taps for the drum line.',
}, [
    ('trumpet', 'ch1', 'White Stab', dict(lufs=-20, pan=-6, verb=0.35)),
    ('horns', 'ch2', 'Swift Fanfare', dict(lufs=-21, pan=12, verb=0.4)),
    ('trombones', 'ch3', 'Upper Horns', dict(lufs=-24, pan=24, verb=0.3)),
    ('bass', 'ch4', 'Signal Bass', dict(lufs=-22, verb=0.2)),
    ('bells', 'ch5', 'Basement Chimes', dict(lufs=-23, pan=30, echo=0.15, verb=0.4)),
    ('keys', 'ch6', 'Harbor Study', dict(lufs=-23, pan=-20, verb=0.3)),
    ('strings', 'ch7', 'Humid Swell', dict(lufs=-21, pan=-24, verb=0.4)),
    ('cellos', 'ch8', 'Crystal Legato', dict(lufs=-25, pan=20, verb=0.35)),
    ('snap', 'ch9', 'Clear Snap', dict(lufs=-28, pan=8, verb=0.3)),
    ('tap', 'ch11', 'Warm Tap', dict(lufs=-27, pan=-10)),
    ('piano', 'ch12', 'Velvet Etude', dict(lufs=-25, pan=-14, verb=0.3)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.2, 'tone': 3000, 'level': -12},
   reverb={'size': 2.4, 'predelay': 22, 'tone': 5500, 'level': -4})

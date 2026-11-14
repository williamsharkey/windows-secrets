"""A Visit to the Instrument Room: an original light-orchestral tour, 104 bpm, F major. One tune passed from the
piano to the strings, the brass, the bells and vibes, then everyone together."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=104, seed=1995)
piano = S.part('piano', 1)
bass = S.part('bass', 2)
violins = S.part('violins', 3)
cello = S.part('cello', 4)
horns = S.part('horns', 5)
trombone = S.part('trombone', 6)
trumpet = S.part('trumpet', 7)
glock = S.part('glock', 8)
vibes = S.part('vibes', 9)
block = S.part('block', 11)
snap = S.part('snap', 12)
organ = S.part('organ', 13)

PROG = 'F C Dm Bb F/C C7 F F'
BRIDGE = 'Bb C Am Dm Gm7 C7 F F'
THEME = ('q C5 F5 A5 F5 | q. G5 e F5 q E5 C5 | q D5 F5 A5 D6 | h. Bb5 q A5 | '
         'q A5 e G5 F5 q C6 A5 | q G5 e F5 E5 q G5 Bb5 | h A5 q G5 E5 | h. F5 q r')
BRIDGE_MEL = 'w D6 | w C6 | h C6 A5 | w F5 | h Bb5 G5 | h E5 G5 | w F5 | w r'


def walk(at, prog, vel=92):
    bass.bass(prog, at=at, beats=4, pattern=[(0, 0, 0.9), (1, '5', 0.9), (2, 0, 0.9), (3, '5', 0.9)], vel=vel)


def oompah(part, at, prog, vel=62, lo=55, hi=70):
    part.chords(prog, at=at, beats=4, style='block', vel=vel, lo=lo, hi=hi, rhythm=[(1, 0.8), (3, 0.8)])


t = 0.0
# 1. the piano (8): the tune, the marimba bass walks under it
piano.mel(THEME, at=t, vel=88)
piano.chords(PROG, at=t, beats=4, style='block', vel=58, lo=48, hi=62, rhythm=[(1, 0.8), (2, 0.8), (3, 0.8)])
walk(t, PROG)
block.drums({60: 'x...x...x...x...'}, at=t + 16, bars=4, vel={'x': 60})
t += 32
# 2. the strings (8): violins sing it, cellos below, the piano accompanies
violins.mel(THEME, at=t, vel=90)
cello.chords(PROG, at=t, beats=4, style='pad', vel=66, lo=41, hi=55)
oompah(piano, t, PROG, 56); walk(t, PROG, 86)
t += 32
# 3. the brass (8): horns, trombones on the off-beats, the trumpet tops the last phrase
horns.mel(THEME, at=t, vel=94)
oompah(trombone, t, PROG, 70, 50, 64)
trumpet.mel('h. r q r | h. r q r | h. r q r | h. r q r | q A5 e G5 F5 q C6 A5 | q G5 e F5 E5 q G5 Bb5 | h A5 q G5 E5 | h. F5 q r',
            at=t, vel=88)
walk(t, PROG, 94)
snap.drums({60: 'x.......x.x.x...'}, at=t, bars=8, vel={'x': 70})
t += 32
# 4. the bells (8): glockenspiel tune, vibes rolling, the organ holds
glock.mel(THEME, at=t, vel=84)
vibes.chords(PROG, at=t, beats=4, style='arpud', vel=58, lo=60, hi=79, rhythm=0.5)
organ.chords(PROG, at=t, beats=4, style='pad', vel=52, lo=53, hi=67)
walk(t, PROG, 80)
t += 32
# bridge (8): strings and horns in a minor turn
violins.mel(BRIDGE_MEL, at=t, vel=88); horns.chords(BRIDGE, at=t, beats=4, style='pad', vel=62, lo=53, hi=67)
cello.chords(BRIDGE, at=t, beats=4, style='pad', vel=64, lo=41, hi=55)
piano.chords(BRIDGE, at=t, beats=4, style='arp', vel=54, lo=60, hi=76, rhythm=0.5)
walk(t, BRIDGE, 86)
t += 32
# 5. everyone (8)
violins.mel(THEME, at=t, vel=96); horns.mel(THEME, at=t, vel=86, tr=-12); piano.mel(THEME, at=t, vel=82)
glock.mel(THEME, at=t, vel=70, tr=12)
oompah(trombone, t, PROG, 72, 50, 64); cello.chords(PROG, at=t, beats=4, style='pad', vel=66, lo=41, hi=55)
vibes.chords(PROG, at=t, beats=4, style='arpud', vel=52, lo=60, hi=79, rhythm=0.5)
walk(t, PROG, 98)
snap.drums({60: 'x.......x.x.x...'}, at=t, bars=8, vel={'x': 74})
block.drums({60: '..x...x...x...x.'}, at=t, bars=8, vel={'x': 56})
t += 32
# cadence (4): Bb - C7 - F, held, the trumpet on top
cad = 'Bb:2 C7:2 F:8'
for p, lo, hi, v in ((horns, 55, 70, 80), (trombone, 50, 64, 76), (cello, 41, 55, 70), (organ, 53, 67, 56), (violins, 62, 77, 80)):
    p.chords(cad, at=t, style='pad', vel=v, lo=lo, hi=hi)
trumpet.mel('h D6 E6 | w F6 | w F6', at=t, vel=92, tr=-12)
bass.mel('h Bb2 C3 | w F2 | w F2', at=t, vel=96)
glock.note(t + 4, pitch('F6'), 4, 80); piano.chords('F:8', at=t + 4, style='pad', vel=70, lo=53, hi=77)
snap.note(t + 4, 60, 0.5, 90)

S.humanize(ms=6, vel=5)
finish(__file__, S, {
    'title': 'A Visit to the Instrument Room',
    'pack': 'studio-archive',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A light-orchestral tour in F major, 104 bpm: one tune passed from the upright piano to the violins and '
            'cellos, the horns, trombones and trumpet, the glockenspiel and vibes, then everyone together.',
}, [
    ('piano', 'ch1', 'Mild Ivories', dict(lufs=-21, pan=-16, verb=0.3)),
    ('bass', 'ch2', 'Signal Bass', dict(lufs=-22, verb=0.15)),
    ('violins', 'ch3', 'Humid Swell', dict(lufs=-21, pan=-24, verb=0.4)),
    ('cello', 'ch4', 'Crystal Legato', dict(lufs=-24, pan=22, verb=0.35)),
    ('horns', 'ch5', 'Opal Fanfare', dict(lufs=-21, pan=12, verb=0.35)),
    ('trombone', 'ch6', 'Upper Horns', dict(lufs=-25, pan=26, verb=0.3)),
    ('trumpet', 'ch7', 'White Stab', dict(lufs=-22, pan=-4, verb=0.35)),
    ('glock', 'ch8', 'Basement Chimes', dict(lufs=-23, pan=30, echo=0.15, verb=0.4)),
    ('vibes', 'ch9', 'Frosted Salon', dict(lufs=-25, pan=-30, verb=0.35)),
    ('block', 'ch11', 'Warm Tap', dict(lufs=-30, pan=-36)),
    ('snap', 'ch12', 'Clear Snap', dict(lufs=-28, pan=8, verb=0.3)),
    ('organ', 'ch13', 'Wired Felt', dict(lufs=-28, verb=0.35)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.25, 'tone': 3000, 'level': -8},
   reverb={'size': 2.4, 'predelay': 22, 'tone': 5500, 'level': -4})

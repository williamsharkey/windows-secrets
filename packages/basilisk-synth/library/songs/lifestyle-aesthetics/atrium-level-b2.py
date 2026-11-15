"""Atrium Level B2: an original city-pop / mall-pop piece, 96 bpm, C major. An escalator rises, then tines and
nylon guitar over a slow-jam bass, a rounded major-seventh chord, kalimba and marimba droplets, coins in the
fountain and a faraway choir."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=96, seed=2002)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
tines = S.part('tines', 3)
nylon = S.part('nylon', 4)
chordp = S.part('chord', 5)
kalimba = S.part('kalimba', 6)
marimba = S.part('marimba', 7)
choir = S.part('choir', 8)
pad = S.part('pad', 9)
escal = S.part('escalator', 11)
coins = S.part('coins', 12)
sparkle = S.part('sparkle', 13)

A = 'Fmaj7 E7 Am7 Gm7:2 C7:2 Fmaj7 Em7:2 A7:2 Dm7 G7sus4:2 G7:2'
B = 'Cmaj7 Am7 Dm7 G7 Em7 A7 Dm7:2 G7:2 Cmaj7'
AMEL = ('q. A5 e G5 q E5 C5 | h B4 q. G#4 e B4 | q. C5 e E5 q G5 E5 | h F5 q E5 D5 | '
        'q. A5 e C6 q E6 C6 | h B5 q A5 G5 | q. A5 e F5 q D5 F5 | w G5')
BMEL = ('q E5 e G5 B5 q. B5 e A5 | h G5 q E5 C5 | q F5 e A5 C6 q. C6 e B5 | h. B5 q r | '
        'q G5 e B5 D6 q. D6 e C6 | h C#6 q A5 G5 | q F5 A5 G5 B5 | w C6')


def band(at, prog, vel=96, fill=True):
    n = int(prog_len(prog) // 4)
    groove(kit, 'disco', at, n, fill=fill, drop=(OHH,), swing=0.1)
    bass.bass(prog, at=at, beats=4, pattern=[(0, 0, 0.9), (1.5, '8', 0.3), (1.75, 0, 0.4), (2.5, '5', 0.4), (3, 0, 0.6), (3.75, '-1', 0.2)], vel=vel)


def tine_comp(at, prog, vel=60):
    tines.chords(prog, at=at, beats=4, style='block', vel=vel, lo=57, hi=74, rhythm=[(0, 1.4), (1.5, 0.4), (2.5, 1.4)])


t = 0.0
# intro (4): the escalator, kalimba droplets
escal.note(0, 39, 8, 90)
kalimba.chords('Fmaj7:4 E7:4 Am7:4 G7:4', at=0, style='arpud', vel=60, lo=64, hi=84, rhythm=0.5)
sparkle.note(12, 79, 4, 70)
t = 16
# A (8)
band(t, A); tine_comp(t, A)
nylon.mel(AMEL, at=t, vel=88, tr=-12)
pad.chords(A, at=t, beats=4, style='pad', vel=50, lo=53, hi=67)
t += 32
# B (8): the chorus, the rounded chord on the offbeats
band(t, B); tine_comp(t, B, 58)
tines.mel(BMEL, at=t, vel=86, tr=-12)
chordp.drums({60: '..x.....x.x.....'}, at=t, bars=8, vel={'x': 72})
marimba.chords(B, at=t, beats=4, style='arp', vel=54, lo=64, hi=81, rhythm=0.5)
t += 32
# interlude (4): coins in the fountain, the sparkle, the bass alone
bass.bass('Fmaj7 Em7 Dm7 G7', at=t, beats=4, pattern=[(0, 0, 1.4), (2, '5', 0.9), (3, '8', 0.9)], vel=90)
for k in range(5):
    coins.note(t + 2 + k * 2.5, 79 + k, 2, 70)
sparkle.note(t + 8, 79, 4, 70)
pad.chords('Fmaj7 Em7 Dm7 G7', at=t, beats=4, style='pad', vel=56, lo=53, hi=67)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.', RIM: '....x.......x...'}, at=t, bars=4, swing=0.1)
t += 16
# A (8): marimba takes the tune, nylon answers
band(t, A); tine_comp(t, A, 56)
marimba.mel(AMEL, at=t, vel=84, tr=-12)
nylon.chords(A, at=t, beats=4, style='broken', vel=58, lo=55, hi=72, rhythm=0.5)
t += 32
# B (8) twice: choir on the second
band(t, B); tine_comp(t, B, 60)
nylon.mel(BMEL, at=t, vel=90, tr=-12)
chordp.drums({60: '..x.....x.x.....'}, at=t, bars=8, vel={'x': 72})
t += 32
band(t, B, fill=False); tine_comp(t, B, 62)
tines.mel(BMEL, at=t, vel=90, tr=-12); nylon.mel(BMEL, at=t, vel=74, tr=-24)
choir.chords(B, at=t, beats=4, style='pad', vel=62, lo=52, hi=67)
marimba.chords(B, at=t, beats=4, style='arp', vel=52, lo=64, hi=81, rhythm=0.5)
t += 32
# outro (4)
kalimba.chords('Cmaj7:16', at=t, style='arpud', vel=56, lo=64, hi=88, rhythm=0.5)
tines.chords('Cmaj7:12', at=t, style='pad', vel=58, lo=57, hi=74)
bass.note(t, pitch('C2'), 8, 92); escal.note(t + 4, 39, 8, 76)
coins.note(t + 10, 84, 3, 64)

S.humanize(ms=5, vel=4, parts=['tines', 'nylon', 'marimba', 'kalimba', 'bass'])
finish(__file__, S, {
    'title': 'Atrium Level B2',
    'pack': 'lifestyle-aesthetics',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'City pop in C major, 96 bpm: escalator, tines, nylon guitar, slow-jam bass, the rounded major-seventh '
            'chord, kalimba and marimba droplets, fountain coins, sparkle, a faraway choir. Drums: Kit Manager 98 '
            '(Echo Chamber Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', dict(lufs=-18, verb=0.1)),
    ('bass', 'ch2', 'Slow Jam Bass', dict(lufs=-19)),
    ('tines', 'ch3', 'Atrium Keys', dict(lufs=-22, pan=-16, echo=0.15, verb=0.3)),
    ('nylon', 'ch4', 'Food Court Nylon', dict(lufs=-20, pan=14, verb=0.3)),
    ('chord', 'ch5', 'Rounded Corner Chord', dict(lufs=-25, pan=-24, echo=0.3, verb=0.25)),
    ('kalimba', 'ch6', 'Hydro Kalimba', dict(lufs=-24, pan=26, echo=0.3, verb=0.3)),
    ('marimba', 'ch7', 'Droplet Marimba', dict(lufs=-23, pan=-30, echo=0.2, verb=0.3)),
    ('choir', 'ch8', 'Faraway Choir', dict(lufs=-26, verb=0.5, width=1.3)),
    ('pad', 'ch9', 'Weather Map Pad', dict(lufs=-28, verb=0.4, width=1.3)),
    ('escalator', 'ch11', 'Escalator Ascent', dict(lufs=-25, verb=0.3)),
    ('coins', 'ch12', 'Fountain Coins', dict(lufs=-26, pan=34, echo=0.3, verb=0.5)),
    ('sparkle', 'ch13', 'Sparkle Cascade', dict(lufs=-27, verb=0.5)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -5},
   reverb={'size': 2.2, 'predelay': 20, 'tone': 6000, 'level': -4})

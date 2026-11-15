"""Complimentary Lanai: an original exotica lounge piece, 96 bpm, C major. Crickets and bird calls, a gong, a
beguine on claves and bongo taps, marimba, vibes-bells, lounge piano, strings and a flute tune."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=96, seed=1956)
flute = S.part('flute', 1)
marimba = S.part('marimba', 2)
piano = S.part('piano', 3)
strings = S.part('strings', 4)
cello = S.part('cello', 5)
bells = S.part('bells', 6)
claves = S.part('claves', 7)
bongo = S.part('bongo', 8)
clap = S.part('clap', 9)
crickets = S.part('crickets', 11)
birds = S.part('birds', 12)
gong = S.part('gong', 13)

A = 'Cmaj7 Am7 Dm7 G7 Cmaj7 Am7 Dm7 G7'
B = 'Fmaj7 Fm6 Em7 A7 Dm7 G7 Cmaj7 G7'
MEL_A = ('q. E5 e D5 h B4 | q C5 e A4 G4 h E4 | q. F5 e E5 q D5 A4 | h. B4 q r | '
         'q. E5 e G5 q B5 A5 | h G5 q E5 C5 | q. D5 e E5 q F5 A5 | h. G5 q r')
MEL_B = 'w A5 | h Ab5 F5 | w G5 | h E5 C#5 | q. D5 e E5 q F5 A5 | h G5 F5 | w E5 | h D5 r'


def beguine(at, bars):
    claves.drums({60: 'x..x..x...x.x...'}, at=at, bars=bars, vel={'x': 80})       # 3-2 clave
    bongo.drums({60: '..o.x.o...o.x.oo'}, at=at, bars=bars, vel={'x': 76, 'o': 52})
    clap.drums({60: '............x...'}, at=at, bars=bars, vel={'x': 58})


def bass(at, prog):
    cello.bass(prog, at=at, beats=4, pattern=[(0, 0, 1.4), (1.5, '5', 0.4), (2, '5', 1.4), (3.5, 0, 0.4)], vel=88)


def lounge_piano(at, prog, vel=62):
    piano.chords(prog, at=at, beats=4, style='block', vel=vel, lo=57, hi=74, rhythm=[(0.5, 0.4), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)])


t = 0.0
# intro (4): crickets, the gong, birds, a marimba roll
hold(crickets, 0, 60, 16, 80)
gong.note(0, 55, 6, 90)
birds.note(2, 60, 2, 80); birds.note(9, 62, 2, 74)
marimba.chords('Cmaj7:4 G7:4', at=8, style='arp', vel=60, lo=60, hi=79, rhythm=0.25)
t = 16
# A (8): the flute tune over the beguine
beguine(t, 8); bass(t, A); lounge_piano(t, A)
flute.mel(MEL_A, at=t, vel=88)
bells.chords(A, at=t, beats=4, style='block', vel=54, lo=64, hi=79, rhythm=[(0, 1.8)])
t += 32
# A again: the marimba doubles an octave down, strings come in
beguine(t, 8); bass(t, A); lounge_piano(t, A, 58)
flute.mel(MEL_A, at=t, vel=86); marimba.mel(MEL_A, at=t, vel=74, tr=-12)
strings.chords(A, at=t, beats=4, style='pad', vel=60, lo=55, hi=72)
birds.note(t + 30, 60, 2, 70)
t += 32
# B (8): the bridge, strings carry it, bells answer
beguine(t, 8); bass(t, B); lounge_piano(t, B, 60)
strings.mel(MEL_B, at=t, vel=84)
strings.chords(B, at=t, beats=4, style='pad', vel=52, lo=52, hi=67)
bells.mel('h. r q E6 | h. r q C6 | h. r q B5 | h. r q G5 | h. r q A5 | h. r q B5 | h. r q G5 | w r', at=t, vel=64)
t += 32
# A (8): everyone; the vibes-bells take the first half
gong.note(t, 55, 4, 80)
beguine(t, 8); bass(t, A); lounge_piano(t, A, 62)
bells.mel(MEL_A, at=t, vel=78)
flute.mel('h. r q r | h. r q r | h. r q r | h. r q r | q. E5 e G5 q B5 A5 | h G5 q E5 C5 | q. D5 e E5 q F5 A5 | h. G5 q r',
          at=t, vel=90)
marimba.chords(A, at=t, beats=4, style='arpud', vel=56, lo=60, hi=79, rhythm=0.5)
strings.chords(A, at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
t += 32
# coda (4): Cmaj7 rolled, crickets and birds
cello.note(t, pitch('C3'), 8, 86)
marimba.chords('Cmaj7:4 Cmaj7:4', at=t, style='arp', vel=58, lo=60, hi=84, rhythm=0.25)
piano.chords('Cmaj7:8', at=t, style='pad', vel=58, lo=57, hi=74)
strings.chords('Cmaj7:12', at=t, style='pad', vel=56, lo=55, hi=72)
flute.mel('w E5 | w E5', at=t, vel=78)
gong.note(t + 8, 55, 6, 76)
hold(crickets, t, 60, 18, 76)
birds.note(t + 4, 60, 2, 70); birds.note(t + 10, 64, 2, 64)

S.humanize(ms=8, vel=5, parts=['flute', 'marimba', 'piano', 'bells', 'bongo'])
finish(__file__, S, {
    'title': 'Complimentary Lanai',
    'pack': 'leisure',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Exotica lounge in C major, 96 bpm: crickets, bird calls and a gong, a beguine on claves and bongo taps, '
            'marimba, vibes-bells, lounge piano, strings, cello bass and a flute tune.',
}, [
    ('flute', 'ch1', 'Polished Call', dict(lufs=-20, pan=6, echo=0.15, verb=0.4)),
    ('marimba', 'ch2', 'Island Marimba', dict(lufs=-23, pan=-22, verb=0.3)),
    ('piano', 'ch3', 'Tiki Lounge Piano', dict(lufs=-25, pan=18, verb=0.3)),
    ('strings', 'ch4', 'Volcano Strings', dict(lufs=-23, pan=-8, verb=0.4, width=1.3)),
    ('cello', 'ch5', 'Opal Section', dict(lufs=-21, verb=0.15)),
    ('bells', 'ch6', 'Soft Bells', dict(lufs=-24, pan=28, echo=0.25, verb=0.4)),
    ('claves', 'ch7', 'Steel Block', dict(lufs=-27, pan=-34)),
    ('bongo', 'ch8', 'Twilight Tap', dict(lufs=-26, pan=30)),
    ('clap', 'ch9', 'Golden Clap', dict(lufs=-30, pan=-10, verb=0.3)),
    ('crickets', 'ch11', 'Mild Rain', dict(lufs=-32, width=1.4)),
    ('birds', 'ch12', 'Half-Speed Mockingbird', dict(lufs=-27, pan=40, verb=0.4)),
    ('gong', 'ch13', 'Cedar Gong', dict(lufs=-25, verb=0.5)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 2800, 'level': -5},
   reverb={'size': 2.6, 'predelay': 25, 'tone': 5000, 'level': -4})

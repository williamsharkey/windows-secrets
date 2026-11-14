"""The Restorer's Afternoon: an original late-60s chamber-pop song, 84 bpm, D major, on tape-replay voices. Flutes
over a descending bass, violas and cellos, a choir in the chorus, saxello and trumpet, a recorder counter-line,
a church-organ stop and a parlour piano."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=84, seed=1967)
kit = S.part('kit', 10)
flute = S.part('flute', 1)
violas = S.part('violas', 2)
cellos = S.part('cellos', 3)
bass = S.part('bass', 4)
choir = S.part('choir', 5)
sax = S.part('saxello', 6)
trumpet = S.part('trumpet', 7)
recorder = S.part('recorder', 8)
organ = S.part('organ', 9)
piano = S.part('piano', 11)

V = 'D A/C# Bm Bm7/A G Gm6 D A7'
C = 'G A F#m Bm Em A7 D D'
VMEL = ('q. F#5 e E5 q D5 A4 | h E5 q. C#5 e E5 | q. D5 e C#5 q B4 F#4 | h. A4 q r | '
        'q B4 e C#5 D5 q E5 G5 | h E5 q D5 Bb4 | q A4 e B4 C#5 q D5 F#5 | h. E5 q r')
CMEL = ('h B5 q A5 G5 | h A5 q. E5 e F#5 | q. F#5 e E5 q C#5 A4 | h. B4 q D5 | '
        'q. G5 e F#5 q E5 B4 | h C#5 q E5 G5 | w F#5 | h. F#5 q r')
BASS_V = 'h D2 D2 | h C#2 C#2 | h B1 B1 | h A1 A1 | h G1 G1 | h G1 G1 | h F#1 A1 | h A1 C#2'
BASS_C = 'h G1 D2 | h A1 E2 | h F#1 C#2 | h B1 F#2 | h E2 B1 | h A1 C#2 | h D2 A1 | h D2 F#2'


def beat(at, bars, fill=True):
    for k in range(bars):
        last = fill and k == bars - 1
        kit.drums({KICK: 'x.......x.x.....', SNARE: '....x.......x...' if not last else '....x.....x.xxxx',
                   CHH: 'x.x.x.x.x.x.x.x.'}, at=at + 4 * k, bars=1, vel={'x': 84, 'X': 100, 'o': 50})


def piano_chords(at, prog, vel=58):
    piano.chords(prog, at=at, beats=4, style='block', vel=vel, lo=55, hi=72, rhythm=[(0, 0.9), (1, 0.9), (2, 0.9), (3, 0.9)])


t = 0.0
# intro (4): the organ and the piano, a flute turn
organ.chords('D A/C# Bm A7', at=0, beats=4, style='pad', vel=58, lo=55, hi=69)
piano_chords(0, 'D A/C# Bm A7', 52)
flute.mel('h. r q r | h. r q r | q. D5 e C#5 q B4 F#4 | h. A4 q r', at=0, vel=80, tr=-12)
t = 16
# verse 1 (8): flutes, the descending bass, the piano
beat(t, 8); bass.mel(BASS_V, at=t, vel=92, tr=12); piano_chords(t, V)
flute.mel(VMEL, at=t, vel=90, tr=-12)
cellos.chords(V, at=t + 16, beats=4, style='pad', vel=56, lo=45, hi=60)
t += 32
# chorus (8): the choir, violas, saxello
beat(t, 8); bass.mel(BASS_C, at=t, vel=96, tr=12); piano_chords(t, C, 54)
choir.mel(CMEL, at=t, vel=88, tr=-12)
violas.chords(C, at=t, beats=4, style='pad', vel=64, lo=55, hi=72)
sax.chords(C, at=t, beats=4, style='block', vel=62, lo=50, hi=64, rhythm=[(0, 1.4), (2, 1.4)])
t += 32
# verse 2 (8): the recorder answers the flute
beat(t, 8); bass.mel(BASS_V, at=t, vel=92, tr=12); piano_chords(t, V, 54)
flute.mel(VMEL, at=t, vel=90, tr=-12)
recorder.mel('h. r q r | h. r e A5 B5 | h. r q r | h. r e F#5 G5 | h. r q r | h. r e G5 F#5 | h. r q r | h. r e E5 F#5', at=t, vel=78, tr=-12)
cellos.chords(V, at=t, beats=4, style='pad', vel=58, lo=45, hi=60)
violas.chords(V, at=t, beats=4, style='pad', vel=52, lo=60, hi=74)
t += 32
# chorus (8)
beat(t, 8); bass.mel(BASS_C, at=t, vel=96, tr=12); piano_chords(t, C, 56)
choir.mel(CMEL, at=t, vel=92, tr=-12); flute.mel(CMEL, at=t, vel=74, tr=-12)
violas.chords(C, at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
sax.chords(C, at=t, beats=4, style='block', vel=64, lo=50, hi=64, rhythm=[(0, 1.4), (2, 1.4)])
t += 32
# bridge (4): a piccolo-trumpet solo over the organ
beat(t, 4)
trumpet.mel('q D6 e C#6 B5 q A5 F#5 | q G5 e A5 B5 h A5 | q B5 e C#6 D6 q E6 C#6 | h. E6 q r', at=t, vel=92, tr=-12)
organ.chords('Bm G D A7', at=t, beats=4, style='pad', vel=60, lo=55, hi=69)
bass.mel('h B1 F#2 | h G1 D2 | h D2 A1 | h A1 C#2', at=t, vel=92, tr=12)
t += 16
# last chorus (8), held at the end
beat(t, 7, fill=False)
bass.mel(BASS_C, at=t, vel=98, tr=12); piano_chords(t, C, 58)
choir.mel(CMEL, at=t, vel=94, tr=-12); flute.mel(CMEL, at=t, vel=78, tr=-12); trumpet.mel(CMEL, at=t + 16, vel=70, tr=-24)
violas.chords(C, at=t, beats=4, style='pad', vel=68, lo=55, hi=72); cellos.chords(C, at=t, beats=4, style='pad', vel=60, lo=45, hi=60)
sax.chords(C, at=t, beats=4, style='block', vel=64, lo=50, hi=64, rhythm=[(0, 1.4), (2, 1.4)])
organ.chords(C, at=t, beats=4, style='pad', vel=50, lo=55, hi=69)
t += 32
# coda (4): the opening flute turn, a last D chord
flute.mel('q. D5 e C#5 q B4 F#4 | h. A4 q r | w D5', at=t, vel=82, tr=-12)
for p, lo, hi, v in ((organ, 55, 69, 56), (violas, 57, 74, 60), (cellos, 45, 60, 58), (piano, 55, 74, 56)):
    p.chords('Bm:4 A7:4 D:8', at=t, style='pad', vel=v, lo=lo, hi=hi)
bass.mel('w B1 | w A1 | w D2 | w D2', at=t, vel=90, tr=12)

S.humanize(ms=8, vel=5)
finish(__file__, S, {
    'title': "The Restorer's Afternoon",
    'pack': 'tape-parlour',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Late-60s chamber pop in D major, 84 bpm, on tape-replay voices: flutes over a descending bass, violas, '
            'cellos, choir, saxello, a trumpet solo, a recorder counter-line, the 8-foot organ stop and a parlour '
            'piano. Drums: Kit Manager 98 (Half-Time Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Half-Time Kit', dict(lufs=-19, verb=0.12, lp=9000)),
    ('flute', 'ch1', 'Digital Call', dict(lufs=-19, pan=-10, verb=0.3)),
    ('violas', 'ch2', 'Clear Bows', dict(lufs=-23, pan=24, verb=0.35)),
    ('cellos', 'ch3', 'Rural Cellos', dict(lufs=-24, pan=-26, verb=0.3)),
    ('bass', 'ch4', 'Lunar Bows', dict(lufs=-21)),
    ('choir', 'ch5', 'Faded Voices', dict(lufs=-20, pan=6, verb=0.4)),
    ('saxello', 'ch6', 'Delta Fanfare', dict(lufs=-25, pan=-18, verb=0.25)),
    ('trumpet', 'ch7', 'Pewter Salute', dict(lufs=-21, pan=14, verb=0.35)),
    ('recorder', 'ch8', 'Field Line', dict(lufs=-22, pan=30, echo=0.15, verb=0.3)),
    ('organ', 'ch9', 'Coral Revival', dict(lufs=-26, pan=-6, verb=0.3)),
    ('piano', 'ch11', 'Lattice Recital', dict(lufs=-23, pan=16, verb=0.25)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 2800, 'level': -8},
   reverb={'size': 1.9, 'predelay': 20, 'tone': 4500, 'level': -4})

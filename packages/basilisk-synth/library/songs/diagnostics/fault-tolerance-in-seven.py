"""Fault Tolerance in Seven: an original IDM study in 7/8, 120 bpm, A minor. A broken music box over a beat of
floppy seeks, stamps and relay clicks; stutters, a shattered glass, an erhu line and a choir of error tones."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=120, seed=9407)
box = S.part('musicbox', 1)
bells = S.part('bells', 2)
thud = S.part('thud', 3)
snare = S.part('snare', 4)
tick = S.part('tick', 5)
seek = S.part('seek', 6)
pad = S.part('pad', 7)
err = S.part('errorpad', 8)
erhu = S.part('erhu', 9)
choir = S.part('choir', 11)
stut = S.part('stutter', 12)
glass = S.part('glass', 13)
block = S.part('block', 14)

BAR = 3.5   # 7/8: seven eighths, grouped 2+2+3
PROG = ['Am', 'Fmaj7', 'Dm7', 'E7sus4']
BOX = ['e A5 C6 E6 C6 B5 G5 E5', 'e F5 A5 C6 E6 C6 A5 G5', 'e D5 F5 A5 C6 A5 F5 E5', 'e E5 G5 B5 D6 B5 A5 G#5']
BOX2 = ['e A5 r E6 r q B5 e G5', 'e F5 A5 r E6 q C6 e A5', 'e D5 r A5 C6 q A5 e E5', 'q E5 e G5 q B5 e D6 G#5']


def beat(at, bars, busy=False):
    for k in range(bars):
        b = at + BAR * k
        thud.drums({36: 'x.......x.....' if k % 4 != 3 else 'x.....x.x...x.'}, at=b, bars=1, beats_per_bar=BAR, vel={'x': 104})
        snare.drums({60: '....x......x..' if not busy else '....x..o...x.o'}, at=b, bars=1, beats_per_bar=BAR,
                    vel={'x': 92, 'o': 54})
        tick.drums({60: 'x.x.x.x.x.x.x.' if not busy else 'xxx.x.xxx.x.xx'}, at=b, bars=1, beats_per_bar=BAR,
                   vel={'x': 64})
        if k % 2 == 1:
            seek.note(b + 2.75, 46, 0.5, 86)


def chords_(part, at, bars, vel, lo=52, hi=69):
    prev = None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG[k % 4], 4), lo, hi); prev = ns
        for n in ns:
            part.note(at + BAR * k, n, BAR * 0.98, vel)


def boxline(at, bars, src=BOX, vel=84):
    for k in range(bars):
        box.mel(src[k % 4], at=at + BAR * k, vel=vel)


def stutter(at, n=8, note=60, vel=88):
    for i in range(n):
        stut.note(at + i * 0.125, note + (i % 2) * 12, 0.1, vel - 3 * i)


t = 0.0
# intro (8 bars): the music box alone, then the error pad
boxline(0, 8, vel=78)
chords_(err, 4 * BAR, 4, 54)
glass.note(7 * BAR + 2.5, 89, 1, 90)
t = 8 * BAR
# A (16): the beat starts
beat(t, 16); boxline(t, 16)
chords_(pad, t, 16, 58)
for k in (3, 7, 11, 15):
    stutter(t + BAR * k + 2.5, 8, 60)
block.drums({60: '..x....x...x..'}, at=t + 8 * BAR, bars=8, beats_per_bar=BAR, vel={'x': 70})
t += 16 * BAR
# B (16): the erhu over the broken box, busier beat
beat(t, 16, busy=True); boxline(t, 16, BOX2, 74)
erhu.mel('q. E5 q D5 C5 | h B4 q. A4 | q. C5 q D5 E5 | h. E5 e r | q. A5 q G5 F5 | h E5 q. D5 | '
         'q. C5 q B4 A4 | h. G#4 e r', at=t, vel=88)
erhu.mel('q. E5 q D5 C5 | h B4 q. A4 | q. C5 q D5 E5 | h. E5 e r | q. A5 q G5 F5 | h E5 q. D5 | '
         'q. C5 q B4 C5 | h. B4 e r', at=t + 8 * BAR, vel=92)
chords_(pad, t, 16, 56); chords_(err, t + 8 * BAR, 8, 50)
for k in (7, 15):
    stutter(t + BAR * k + 1.5, 16, 60)
t += 16 * BAR
# break (8): only the choir and the bells; the glass shatters
glass.note(t, 89, 1, 100)
chords_(choir, t, 8, 70, 55, 72)
for k in range(8):
    bells.note(t + BAR * k, pitch(['A5', 'F5', 'D5', 'E5'][k % 4]), 2, 72)
    bells.note(t + BAR * k + 1.5, pitch(['E6', 'C6', 'A5', 'B5'][k % 4]), 1.5, 62)
seek.drums({46: 'x.....x.......'}, at=t + 4 * BAR, bars=4, beats_per_bar=BAR, vel={'x': 80})
t += 8 * BAR
# A' (16): everything
glass.note(t, 89, 1, 96)
beat(t, 16, busy=True); boxline(t, 16, BOX, 86)
erhu.mel('q. A5 q G5 F5 | h E5 q. D5 | q. C5 q B4 A4 | h. G#4 e r', at=t + 8 * BAR, vel=90)
erhu.mel('q. A5 q G5 F5 | h E5 q. D5 | q. C5 q B4 C5 | h. A4 e r', at=t + 12 * BAR, vel=92)
chords_(pad, t, 16, 58); chords_(choir, t + 8 * BAR, 8, 60, 55, 72)
block.drums({60: '..x....x...x..'}, at=t, bars=16, beats_per_bar=BAR, vel={'x': 72})
for k in (3, 7, 11):
    stutter(t + BAR * k + 2.5, 8, 64)
t += 16 * BAR
# outro (8): the beat stops, the box runs down
boxline(t, 4, BOX2, 70)
chords_(err, t, 8, 50)
box.mel('e A5 C6 E6 C6 B5 G5 E5 | q A5 r r e r | h. A4 e r', at=t + 4 * BAR, vel=66)
t += 8 * BAR
glass.note(t - 1, 89, 1, 80)

S.humanize(ms=3, vel=5, parts=['musicbox', 'erhu', 'bells'])
finish(__file__, S, {
    'title': 'Fault Tolerance in Seven',
    'pack': 'diagnostics',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'An IDM study in 7/8 (2+2+3), 120 bpm, A minor: broken music box, a beat of critical-stop thuds, stamp '
            'snares, stamp ticks and floppy seeks, stutters, shattered glass, an erhu line, cello and error pads, '
            'a choir.',
}, [
    ('musicbox', 'ch1', 'Broken Music Box', dict(lufs=-20, pan=-10, echo=0.25, verb=0.3)),
    ('bells', 'ch2', 'Noble Bell', dict(lufs=-24, pan=20, echo=0.3, verb=0.4)),
    ('thud', 'ch3', 'Echo Click', dict(lufs=-19)),
    ('snare', 'ch4', 'Electric Snare', dict(lufs=-22, pan=4, verb=0.15)),
    ('tick', 'ch5', 'Lunar Tick', dict(lufs=-28, pan=28)),
    ('seek', 'ch6', 'Floppy Seek Perc', dict(lufs=-24, pan=-28, echo=0.2)),
    ('pad', 'ch7', 'Copper Veil', dict(lufs=-25, verb=0.35, width=1.3)),
    ('errorpad', 'ch8', 'Digital Veil', dict(lufs=-28, verb=0.4, width=1.4)),
    ('erhu', 'ch9', 'Hollow Song', dict(lufs=-20, pan=10, echo=0.15, verb=0.35)),
    ('choir', 'ch11', 'Inland Cantor', dict(lufs=-25, verb=0.5)),
    ('stutter', 'ch12', 'Stutter Copy Paste', dict(lufs=-26, pan=-20, echo=0.3)),
    ('glass', 'ch13', 'Shatter Transition', dict(lufs=-24, verb=0.5)),
    ('block', 'ch14', 'Laser Block', dict(lufs=-29, pan=36)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 2.2, 'predelay': 18, 'tone': 5500, 'level': -5})

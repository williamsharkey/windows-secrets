"""Friday at Four: an original office singalong, 120 bpm, G major, with a light shuffle. The office piano, the
bass from Accounts, the hum from the back row, a doo-doo choir, the bee-buzzing organ, a sax and a glockenspiel.
Sounds by Paul Chauncy (the Paulywaulophone pack)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=120, seed=4)
kit = S.part('kit', 10)
piano = S.part('piano', 1)
bass = S.part('bass', 2)
hum = S.part('hum', 3)
doo = S.part('doo', 4)
organ = S.part('organ', 5)
sax = S.part('sax', 6)
glock = S.part('glock', 7)
boop = S.part('boop', 8)
fork = S.part('fork', 9)
guitar = S.part('guitar', 11)
chorus = S.part('chorus', 12)

V = 'G C G D G C D G'
C1 = 'C G Am D G Em A7 D'
C2 = 'C G Am D G Em D7 G'
VERSE = ('q B4 B4 e A4 B4 q D5 | q E5 e D5 C5 h E5 | q D5 B4 G4 B4 | h. A4 q r | '
         'q B4 B4 e A4 B4 q D5 | q E5 e G5 E5 h C5 | q B4 e A4 B4 q C5 A4 | h. G4 q r')
CH_A = 'h E5 q E5 G5 | h D5 q B4 D5 | q C5 C5 e B4 C5 q E5 | h. D5 q r | q G5 e F#5 E5 q D5 B4 | q E5 e D5 B4 h G4 | '
CH1 = CH_A + 'q A4 e B4 C#5 q E5 G5 | h. F#5 q r'
CH2 = CH_A + 'q A4 e B4 C5 q D5 F#5 | h. G5 q r'
SW = 0.25


def piano_oompah(at, prog, vel=70):
    t, prev = at, None
    for sym in prog.split():
        ns = voice_lead(prev, chord(sym, 4), 55, 69); prev = ns
        r = root_of(sym, 3)
        for off in (0, 2):
            piano.note(t + off, r if off == 0 else r + 7 - (12 if r + 7 > 55 else 0), 0.8, vel)
            for n in ns:
                piano.note(t + off + 1, n, 0.6, vel - 12)
        t += 4


def bassline(at, prog, vel=94):
    bass.bass(prog, at=at, beats=4, pattern=[(0, 0, 0.9), (1, '5', 0.9), (2, '8', 0.9), (3, '5', 0.9)], vel=vel)


def beat(at, bars):
    for k in range(bars):
        kit.drums({KICK: 'x.......x.......', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'}, at=at + 4 * k, bars=1, swing=SW)


t = 0.0
# intro (4): the tuning fork, the piano
fork.note(0, 67, 3, 80)
piano_oompah(4, 'G D G')
t = 16
# verse 1 (8): piano, bass, the hum from the back row
piano_oompah(t, V); bassline(t, V)
hum.mel(VERSE, at=t, vel=88)
t += 32
# chorus (8): the kit, the organ, the doo choir, boops
beat(t, 8); piano_oompah(t, C1); bassline(t, C1)
hum.mel(CH1, at=t, vel=92); chorus.mel(CH1, at=t, vel=72, tr=-12)
doo.chords(C1, at=t, beats=4, style='pad', vel=60, lo=55, hi=69)
organ.chords(C1, at=t, beats=4, style='block', vel=58, lo=55, hi=72, rhythm=[(1, 0.5), (3, 0.5)])
boop.drums({67: '......x.......x.'}, at=t, bars=8, vel={'x': 76})
t += 32
# verse 2 (8): the sax sings it, glockenspiel answers, guitar strums
beat(t, 8); piano_oompah(t, V, 64); bassline(t, V)
sax.mel(VERSE, at=t, vel=90)
glock.mel('h. r q r | h. r e G5 A5 | h. r q r | h. r e D6 C6 | h. r q r | h. r e G5 A5 | h. r q r | w r', at=t, vel=74)
guitar.chords(V, at=t, beats=4, style='block', vel=56, lo=52, hi=67, rhythm=[(0, 0.5), (1, 0.4), (2, 0.5), (3, 0.4)])
t += 32
# chorus (8)
beat(t, 8); piano_oompah(t, C2); bassline(t, C2)
hum.mel(CH2, at=t, vel=94); sax.mel(CH2, at=t, vel=70, tr=-12)
doo.chords(C2, at=t, beats=4, style='pad', vel=60, lo=55, hi=69)
organ.chords(C2, at=t, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(1, 0.5), (3, 0.5)])
boop.drums({67: '......x.......x.'}, at=t, bars=8, vel={'x': 76})
t += 32
# bridge (4): the bee organ takes a turn, the kit lays out to snare and hats
kit.drums({SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=3, swing=SW)
kit.drums({SNARE: 'x.x.x.x.xxxxXXXX'}, at=t + 12, bars=1)
organ.mel('q G5 e A5 B5 q D6 B5 | q C6 e B5 A5 h G5 | q E5 e F#5 G5 q A5 B5 | h. A5 q r', at=t, vel=92)
bassline(t, 'Em C Am D'); piano_oompah(t, 'Em C Am D', 60)
t += 16
# last chorus, twice (16): everyone; a key change up a tone the second time
beat(t, 8); piano_oompah(t, C2); bassline(t, C2)
hum.mel(CH2, at=t, vel=96); chorus.mel(CH2, at=t, vel=76, tr=-12); sax.mel(CH2, at=t, vel=72, tr=-12)
doo.chords(C2, at=t, beats=4, style='pad', vel=62, lo=55, hi=69)
organ.chords(C2, at=t, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(1, 0.5), (3, 0.5)])
glock.mel(CH2, at=t, vel=60, tr=12)
t += 32
C3 = 'D A Bm E A F#m E7 A'
kit.note(t, CRASH, 2, 110)
beat(t, 8); piano_oompah(t, C3); bassline(t, C3)
hum.mel(CH2, at=t, vel=98, tr=2); chorus.mel(CH2, at=t, vel=78, tr=-10); sax.mel(CH2, at=t, vel=74, tr=-10)
doo.chords(C3, at=t, beats=4, style='pad', vel=64, lo=55, hi=69)
organ.chords(C3, at=t, beats=4, style='block', vel=62, lo=55, hi=72, rhythm=[(1, 0.5), (3, 0.5)])
guitar.chords(C3, at=t, beats=4, style='block', vel=56, lo=52, hi=67, rhythm=[(0, 0.5), (1, 0.4), (2, 0.5), (3, 0.4)])
boop.drums({69: '......x.......x.'}, at=t, bars=8, vel={'x': 78})
t += 32
# ending (2): the last chord, the fork
for p, lo, hi, v in ((piano, 57, 76, 76), (organ, 55, 72, 62), (doo, 55, 69, 64)):
    p.chords('A:8', at=t, style='pad', vel=v, lo=lo, hi=hi)
hum.note(t, pitch('A4'), 6, 90); bass.note(t, pitch('A2'), 6, 96)
kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 3, 104); fork.note(t + 2, 69, 4, 70)

S.humanize(ms=6, vel=5)
finish(__file__, S, {
    'title': 'Friday at Four',
    'pack': 'paulywaulophone',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement); sounds by Paul Chauncy',
    'note': 'An office singalong in G major, 120 bpm, light shuffle: office piano, the bass from Accounts, the hum from '
            'the back row, doo-doo choir, bee-buzzing organ, sax, glockenspiel, boops, guitar, a tuning fork; the last '
            'chorus goes up a tone. Drums: the pack\'s Honey Drift kit.',
}, [
    ('kit', 'ch10', 'Honey Drift', dict(lufs=-18, verb=0.08)),
    ('piano', 'ch1', 'Humid Practice', dict(lufs=-20, pan=-14, verb=0.25)),
    ('bass', 'ch2', 'Wired Anchor', dict(lufs=-20)),
    ('hum', 'ch3', 'Electric Vox', dict(lufs=-19, pan=4, verb=0.3)),
    ('doo', 'ch4', 'Remote Haze', dict(lufs=-25, pan=-6, verb=0.35, width=1.3)),
    ('organ', 'ch5', 'Mint Voice', dict(lufs=-23, pan=20, verb=0.2)),
    ('sax', 'ch6', 'Dial Beam', dict(lufs=-21, pan=-20, echo=0.1, verb=0.3)),
    ('glock', 'ch7', 'Orbital Beam', dict(lufs=-24, pan=28, echo=0.2, verb=0.35)),
    ('boop', 'ch8', 'Humid Chop', dict(lufs=-26, pan=-30, echo=0.25)),
    ('fork', 'ch9', 'Winter Chimes', dict(lufs=-25, verb=0.4)),
    ('guitar', 'ch11', 'Night Ballad', dict(lufs=-25, pan=32, verb=0.2)),
    ('chorus', 'ch12', 'Felt Chorus', dict(lufs=-24, pan=10, verb=0.4)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 3000, 'level': -7},
   reverb={'size': 1.8, 'predelay': 18, 'tone': 5500, 'level': -5})

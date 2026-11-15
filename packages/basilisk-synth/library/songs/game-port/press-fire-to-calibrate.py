"""Press Fire to Calibrate: an original chiptune, 150 bpm, A minor. A 286 boots, then pulse leads, sixteenth-note
chord arpeggios, an octave-jumping bass, noise drums and a coin."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *
chord_cap(8)   # rendered before render311 --lookahead: chords thinned to 8 recorders an instant (_lib.cap_chords)

S = Score(bpm=150, seed=1995)
lead = S.part('lead', 1)
lead2 = S.part('lead2', 2)
arp = S.part('arp', 3)
bass = S.part('bass', 4)
kick = S.part('kick', 5)
snare = S.part('snare', 6)
hat = S.part('hat', 7)
rim = S.part('rim', 8)
boot = S.part('boot', 9)
coin = S.part('coin', 11)
riser = S.part('riser', 12)
echo_ = S.part('voice', 13)

PROG = 'Am F G E'
A = ('e A4 C5 E5 A5 q G5 e E5 C5 | q F5 e E5 F5 h A5 | e G5 F5 E5 D5 q B4 G4 | h. G#4 e B4 E5 | '
     'e A5 G5 A5 C6 q B5 e A5 G5 | q A5 e F5 A5 h C6 | e B5 A5 G5 F5 q E5 D5 | h E5 G#5')
B = ('q C6 e B5 A5 q E5 A5 | q F5 e A5 C6 h F6 | q D6 e C6 B5 q G5 B5 | h. B5 q G#5 | '
     'q C6 e B5 A5 q E5 A5 | q F5 e A5 C6 h F6 | e D6 C6 B5 A5 q G5 B5 | w E6')
COUNTER = 'h E5 C5 | h C5 A4 | h D5 B4 | h B4 G#4 | h E5 C5 | h F5 C5 | h D5 B4 | w G#4'


def arps(at, bars, vel=62, prog=PROG):
    t = at
    for k in range(bars):
        ns = chord(prog.split()[k % 4], 5)
        seq = [ns[0], ns[1], ns[2], ns[0] + 12]
        for i in range(16):
            arp.note(t + i * 0.25, seq[i % 4], 0.2, vel - (0 if i % 4 == 0 else 8))
        t += 4


def bassline(at, bars, vel=98, prog=PROG):
    pat = [(i * 0.5, 0 if i % 2 == 0 else '8', 0.4) for i in range(8)]
    bass.bass(' '.join([prog] * (bars // 4)), at=at, beats=4, pattern=pat, vel=vel, octave=2)


def drums(at, bars, fill=True):
    for k in range(bars):
        b = at + 4 * k
        last = fill and k % 8 == 7
        kick.drums({48: 'x.....x.x.......' if not last else 'x.....x.x.x.x...'}, at=b, bars=1, vel={'x': 104})
        snare.drums({60: '....x.......x...' if not last else '....x.......xxxx'}, at=b, bars=1, vel={'x': 92})
        hat.drums({60: 'x.x.x.x.x.x.x.x.'}, at=b, bars=1, vel={'x': 62})
        rim.drums({72: '...x......x....x'}, at=b, bars=1, vel={'x': 58})


t = 0.0
# boot (4): the 286 starts, the arpeggio fades in
boot.note(0, 41, 8, 96)
arps(8, 2, 50)
riser.note(8, 60, 8, 84)
t = 16
# A (16)
drums(t, 16); bassline(t, 16); arps(t, 16)
lead.mel(A, at=t, vel=94); lead.mel(A, at=t + 32, vel=96)
lead2.mel(COUNTER, at=t + 32, vel=74)
coin.note(t + 31, 72, 1, 80)
t += 64
# B (16)
drums(t, 16); bassline(t, 16, 102); arps(t, 16, 66)
lead.mel(B, at=t, vel=96); lead.mel(B, at=t + 32, vel=98)
lead2.mel(A, at=t + 32, vel=70, tr=-12)
t += 64
# bridge (8): the bass alone with the drums, then the voice and a riser
drums(t, 8, fill=False)
bass.mel('e A2 A3 E3 A3 C4 A3 E3 A3 | e F2 F3 C3 F3 A3 F3 C3 F3 | e G2 G3 D3 G3 B3 G3 D3 G3 | e E2 E3 B2 E3 G#3 E3 B2 E3', at=t, vel=100)
bass.mel('e A2 A3 E3 A3 C4 A3 E3 A3 | e F2 F3 C3 F3 A3 F3 C3 F3 | e G2 G3 D3 G3 B3 G3 D3 G3 | e E2 E3 B2 E3 G#3 E3 B2 E3', at=t + 16, vel=100)
echo_.mel('w A4 | w F4 | w G4 | w G#4', at=t + 16, vel=80)
riser.note(t + 24, 60, 8, 88)
for k in range(4):
    coin.note(t + 28 + k, 72 + k * 2, 0.5, 70 + 4 * k)
t += 32
# A' (16): the tune with its counter-melody, then B to end
drums(t, 16); bassline(t, 16); arps(t, 16, 64)
lead.mel(A, at=t, vel=96); lead2.mel(COUNTER, at=t, vel=74)
lead.mel(B, at=t + 32, vel=100); lead2.mel(A, at=t + 32, vel=70, tr=-12)
t += 64
# end (4): the last chord, the coin
lead.mel('q A5 E5 A5 C6 | w A6', at=t, vel=96)
arp.chords('Am:8', at=t, style='arp', vel=60, lo=69, hi=93, rhythm=0.125)
bass.note(t, pitch('A2'), 6, 100); kick.note(t + 4, 48, 0.5, 104); snare.note(t + 4, 60, 0.5, 96)
coin.note(t + 6, 72, 1, 90)
boot.note(t + 8, 41, 4, 60)

finish(__file__, S, {
    'title': 'Press Fire to Calibrate',
    'pack': 'game-port',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A chiptune in A minor, 150 bpm: the 286 boots, pulse leads with a counter-melody, sixteenth-note chord '
            'arpeggios, an octave-jumping bass, noise drums from the pack\'s percussion, a coin.',
}, [
    ('lead', 'ch1', 'Midnight Signal', dict(lufs=-19, pan=-8, echo=0.15, verb=0.12)),
    ('lead2', 'ch2', 'Cold Voice', dict(lufs=-23, pan=22, echo=0.2, verb=0.15)),
    ('arp', 'ch3', 'Lucid Line', dict(lufs=-25, pan=-26, echo=0.1)),
    ('bass', 'ch4', 'Waxed Line', dict(lufs=-19)),
    ('kick', 'ch5', 'Silver Block', dict(lufs=-20)),
    ('snare', 'ch6', 'Chrome Snap', dict(lufs=-22, verb=0.1)),
    ('hat', 'ch7', 'Slate Tick', dict(lufs=-28, pan=18)),
    ('rim', 'ch8', 'Glass Rim', dict(lufs=-29, pan=-20)),
    ('boot', 'ch9', 'Digital Sweep', dict(lufs=-23, verb=0.2)),
    ('coin', 'ch11', 'Coin Jingle', dict(lufs=-24, pan=10, echo=0.2)),
    ('riser', 'ch12', 'Kinetic Riser', dict(lufs=-26, verb=0.3)),
    ('voice', 'ch13', 'Pastel Signal', dict(lufs=-23, pan=4, echo=0.3, verb=0.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 4000, 'level': -5},
   reverb={'size': 1.2, 'predelay': 10, 'tone': 6000, 'level': -9})

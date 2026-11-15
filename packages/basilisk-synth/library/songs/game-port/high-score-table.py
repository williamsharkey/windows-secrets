"""High Score Table: an original chiptune, 144 bpm, C major then A minor. The name-entry jingle, a bouncing
credits theme on pulse leads with an echo lead a sixteenth behind, a triangle-style bass, noise drums, coin and
a 286 shutdown."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=144, seed=1995)
lead = S.part('lead', 1)
echo_ = S.part('echolead', 2)
arp = S.part('arp', 3)
bass = S.part('bass', 4)
kick = S.part('kick', 5)
snare = S.part('snare', 6)
hat = S.part('hat', 7)
coin = S.part('coin', 8)
fx = S.part('fx', 9)
harm = S.part('harmony', 11)

A = 'C Am F G C Am Dm G'
B = 'Am F C G Am F E E'
AMEL = ('e C5 E5 G5 C6 q G5 E5 | e A4 C5 E5 A5 q E5 C5 | e F5 A5 C6 F6 q C6 A5 | q G5 B5 D6 B5 | '
        'e C5 E5 G5 C6 q E6 C6 | e A5 G5 E5 C5 q A4 C5 | e D5 F5 A5 D6 q C6 A5 | h G5 B5')
BMEL = 'h A5 q C6 E6 | h F5 q A5 C6 | h G5 q E5 C5 | h. B4 q D5 | h A5 q C6 E6 | h F6 q E6 D6 | h E6 q D6 C6 | w B5'


def chip(at, prog, vel=96):
    for k, sy in enumerate(prog.split()):
        r = root_of(sy, 2) + 12
        for i in range(8):
            bass.note(at + 4 * k + i * 0.5, r + (12 if i % 2 else 0), 0.4, vel)
        ns = chord(sy, 5)
        for i in range(16):
            arp.note(at + 4 * k + i * 0.25, ns[i % 3] + (12 if (i // 3) % 2 else 0), 0.2, 58)
        kick.drums({48: 'x.......x.x.....'}, at=at + 4 * k, bars=1, vel={'x': 100})
        snare.drums({60: '....x.......x...' if k % 4 != 3 else '....x.....x.xxxx'}, at=at + 4 * k, bars=1, vel={'x': 88})
        hat.drums({60: 'x.x.x.x.x.x.x.x.'}, at=at + 4 * k, bars=1, vel={'x': 58})


def echoed(mel, at, vel=94, tr=0):
    lead.mel(mel, at=at, vel=vel, tr=tr); echo_.mel(mel, at=at + 0.25, vel=vel - 30, tr=tr)


t = 0.0
lead.mel('e C5 E5 G5 C6 E6 G6 q C7 | h. r q r', at=0, vel=90)
coin.note(4, 72, 1, 86)
t = 8
chip(t, A); echoed(AMEL, t)
t += 32
chip(t, A); echoed(AMEL, t); harm.mel(AMEL, at=t, vel=64, tr=-5)
t += 32
chip(t, B); echoed(BMEL, t)
t += 32
chip(t, B); echoed(BMEL, t, tr=12); harm.mel(BMEL, at=t, vel=64, tr=-3)
t += 32
chip(t, A); echoed(AMEL, t, vel=98)
t += 32
chip(t, B); echoed(BMEL, t, vel=96, tr=12); harm.mel(BMEL, at=t, vel=66, tr=-3)
t += 32
chip(t, A); echoed(AMEL, t, vel=100); harm.mel(AMEL, at=t, vel=66, tr=-5)
t += 32
lead.mel('e C6 G5 E5 C5 G4 E4 q C4 | w C5', at=t, vel=92)
bass.note(t + 4, pitch('C3'), 4, 98); kick.note(t + 4, 48, 0.5, 104); snare.note(t + 4, 60, 0.5, 96)
coin.note(t + 6, 72, 1, 90); fx.note(t + 8, 41, 4, 70)

finish(__file__, S, {
    'title': 'High Score Table',
    'pack': 'game-port',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A chiptune at 144 bpm: a name-entry jingle, then the credits theme in C and a minor-key strain on pulse '
            'leads with a soft echo lead a sixteenth behind, a harmony line, chord arpeggios, an octave bass, noise '
            'drums from the pack\'s percussion, a coin and a 286 shutting down.',
}, [
    ('lead', 'ch1', 'Ivory Signal', dict(lufs=-19, pan=-8, verb=0.1)),
    ('echolead', 'ch2', 'Ivory Signal', dict(lufs=-26, pan=24)),
    ('arp', 'ch3', 'Pastel Signal', dict(lufs=-26, pan=-24)),
    ('bass', 'ch4', 'Cobalt Anchor', dict(lufs=-19)),
    ('kick', 'ch5', 'Silver Block', dict(lufs=-21)),
    ('snare', 'ch6', 'Sunlit Knock', dict(lufs=-23)),
    ('hat', 'ch7', 'Lagoon Click', dict(lufs=-29, pan=18)),
    ('coin', 'ch8', 'Coin Jingle', dict(lufs=-24, echo=0.2)),
    ('fx', 'ch9', 'Matte Uplink', dict(lufs=-25, verb=0.3)),
    ('harmony', 'ch11', 'Warm Lead', dict(lufs=-24, pan=14)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 4000, 'level': -8},
   reverb={'size': 1.2, 'predelay': 10, 'tone': 6000, 'level': -9})

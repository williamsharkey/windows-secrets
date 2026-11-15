"""Last Day Before the Holidays: an original office singalong waltz, 3/4 at 168 bpm, F major. The piano and the
bass from Accounts, the hum from the back row, a doo-doo choir, the tuning fork, glockenspiel bells, the sax on
the middle eight and everyone on the last chorus. Sounds by Paul Chauncy."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=144, seed=1225)
piano = S.part('piano', 1)
bass = S.part('bass', 2)
hum = S.part('hum', 3)
doo = S.part('doo', 4)
glock = S.part('glock', 5)
sax = S.part('sax', 6)
organ = S.part('organ', 7)
fork = S.part('fork', 8)
chorus = S.part('chorus', 9)
kit = S.part('kit', 10)
boop = S.part('boop', 11)

V = 'F F C7 C7 C7 C7 F F Bb Bb F F C7 C7 F F'
VMEL = ('h C5 q F5 | h. A5 | h G5 q F5 | h. E5 | h C5 q G5 | h. Bb5 | h A5 q G5 | h. F5 | '
        'h D6 q C6 | h. Bb5 | h A5 q F5 | h. C6 | h Bb5 q G5 | h. E5 | h. F5 | h. r')
M = 'Dm Dm Am Am Bb Bb C7 C7'
MMEL = 'h A5 q Bb5 | h. C6 | h G5 q A5 | h. E5 | h F5 q G5 | h. A5 | h G5 q E5 | h. C5'
BAR = 3.0


def waltz(at, prog, vel=68, drums=True):
    prev = None
    for k, sy in enumerate(prog.split()):
        t = at + BAR * k
        ns = voice_lead(prev, chord(sy, 4), 55, 69); prev = ns
        r = root_of(sy, 2) + 12
        bass.note(t, r if k % 2 == 0 else r + 7 - (12 if r + 7 > 52 else 0), 0.9, 92)
        for off in (1, 2):
            for n in ns:
                piano.note(t + off, n, 0.6, vel - 6 * (off - 1))
        if drums:
            kit.note(t, KICK, 0.3, 80); kit.note(t + 1, CHH, 0.2, 56); kit.note(t + 2, CHH, 0.2, 52)


t = 0.0
fork.note(0, 65, 3, 80)
piano.mel('h C5 q F5 | h. A5 | h G5 q E5 | h. C5', at=3, vel=78)
t = 15
waltz(t, V, drums=False); hum.mel(VMEL, at=t, vel=88)
t += 48
waltz(t, V); hum.mel(VMEL, at=t, vel=90); doo.chords(V, at=t, beats=BAR, style='pad', vel=58, lo=55, hi=69)
glock.mel('h. r | h. r | h. r | q r E6 G6 | h. r | h. r | h. r | q r F6 A6 | h. r | h. r | h. r | q r C7 A6 | h. r | h. r | h. F6 | h. r', at=t, vel=64)
t += 48
waltz(t, M, 64); sax.mel(MMEL, at=t, vel=90); organ.chords(M, at=t, beats=BAR, style='pad', vel=54, lo=55, hi=69)
boop.drums({67: '..x...'}, at=t, bars=8, step=0.5, beats_per_bar=3.0, vel={'x': 72})
t += 24
waltz(t, V, 64); organ.mel(VMEL, at=t, vel=84); glock.mel(VMEL, at=t, vel=58, tr=12)   # an instrumental verse
t += 48
waltz(t, V, 72); hum.mel(VMEL, at=t, vel=96); chorus.mel(VMEL, at=t, vel=74, tr=-12); sax.mel(VMEL, at=t, vel=66, tr=-12)
doo.chords(V, at=t, beats=BAR, style='pad', vel=62, lo=55, hi=69); organ.chords(V, at=t, beats=BAR, style='pad', vel=50, lo=55, hi=69)
t += 48
for p, lo, hi, v in ((piano, 57, 77, 74), (doo, 55, 69, 64), (organ, 55, 69, 56)):
    p.chords('F:6', at=t, style='pad', vel=v, lo=lo, hi=hi)
hum.note(t, pitch('F5'), 6, 92); bass.note(t, pitch('F2') + 12, 6, 94); fork.note(t + 3, 65, 4, 72)

S.humanize(ms=6, vel=5)
finish(__file__, S, {
    'title': 'Last Day Before the Holidays',
    'pack': 'waulophone', 'credit': 'Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly)',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement); sounds by Paul Chauncy',
    'note': 'An office singalong waltz in F, 3/4: the piano and the bass from Accounts, the hum from the back row, a '
            'doo-doo choir, glockenspiel answers, the sax and the bee-buzzing organ on the middle eight, everyone on '
            'the last chorus, a tuning fork at each end. Drums: the pack\'s Honey Pine Kit.',
}, [
    ('piano', 'ch1', 'Front Room Upright', dict(lufs=-21, pan=-12, verb=0.25)),
    ('bass', 'ch2', 'Boop Bass', dict(lufs=-21)),
    ('hum', 'ch3', 'Hmm Held', dict(lufs=-19, pan=4, verb=0.3)),
    ('doo', 'ch4', 'Doo Choir', dict(lufs=-25, pan=-6, verb=0.35, width=1.3)),
    ('glock', 'ch5', 'Glock Bird', dict(lufs=-24, pan=28, echo=0.2, verb=0.35)),
    ('sax', 'ch6', 'Crooner Sax', dict(lufs=-21, pan=-20, echo=0.1, verb=0.3)),
    ('organ', 'ch7', 'Bee Organ Lead', dict(lufs=-25, pan=20, verb=0.2)),
    ('fork', 'ch8', 'Tuning Fork', dict(lufs=-25, verb=0.4)),
    ('chorus', 'ch9', 'Homunculus Choir', dict(lufs=-23, pan=10, verb=0.4)),
    ('kit', 'ch10', 'Honey Pine Kit', dict(lufs=-21, verb=0.08)),
    ('boop', 'ch11', 'Boop Boop', dict(lufs=-26, pan=-30, echo=0.25)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.25, 'tone': 3000, 'level': -8},
   reverb={'size': 1.8, 'predelay': 18, 'tone': 5500, 'level': -5})

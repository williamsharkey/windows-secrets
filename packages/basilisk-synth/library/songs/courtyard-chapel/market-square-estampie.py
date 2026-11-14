"""Market Square Estampie: an original medieval-style estampie, 6/8 at 132 bpm (eighths), D Mixolydian. Each puncta
is played twice, first with an open ending and then a closed one, as the form asks. Dan tranh and psaltery take the
tune over a didgeridoo bourdon, with a strumstick, balafon and mbira, a kalimba, hand chimes and a gong."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=132, seed=1300)
tranh = S.part('dantranh', 1)
psal = S.part('psaltery', 2)
strum = S.part('strumstick', 3)
drone = S.part('drone', 4)
tabor = S.part('tabor', 5)
mbira = S.part('mbira', 6)
kalimba = S.part('kalimba', 7)
bells = S.part('bells', 8)
gong = S.part('gong', 9)

BAR = 3.0   # 6/8: six eighths = three beats
# three puncta; each = a body + an open (ouvert) and a closed (clos) ending, one bar each
P = [('e D5 E5 F#5 G5 F#5 E5 | q D5 e A4 q D5 e E5 | e F#5 G5 A5 G5 F#5 E5 ', 'q. E5 q. r', 'q. D5 q. r'),
     ('e A5 B5 C6 B5 A5 G5 | q A5 e F#5 q D5 e F#5 | e G5 A5 B5 A5 G5 F#5 ', 'q. E5 q. r', 'q. D5 q. r'),
     ('e D6 C6 B5 A5 G5 F#5 | q G5 e A5 q B5 e G5 | e A5 G5 F#5 E5 D5 C5 ', 'q. E5 q. r', 'q. D5 q. r')]


def punctum(part, i, at, vel=90, tr=0):
    body, ouvert, clos = P[i]
    t = part.mel(body + '| ' + ouvert, at=at, vel=vel, tr=tr)
    t = part.mel(body + '| ' + clos, at=t, vel=vel, tr=tr)
    return t


def rhythm(at, bars, full=True):
    for k in range(bars):
        b = at + BAR * k
        tabor.note(b, 43, 0.3, 92); tabor.note(b + 1.5, 50, 0.2, 70)
        if full:
            tabor.note(b + 1.0, 50, 0.2, 56); tabor.note(b + 2.5, 50, 0.2, 60)
        strum.note(b, 50, 1.4, 86); strum.note(b + 1.5, 57, 1.4, 76)


t = 0.0
# bourdon and gong, the dan tranh glisses in
gong.note(0, 61, 6, 80)
hold(drone, 0, 50, 6 * BAR, 72)
mbira.mel('e D5 A4 D5 F#5 A5 F#5 | e D5 A4 D5 F#5 A5 F#5 | e C5 G4 C5 E5 G5 E5 | e D5 A4 D5 F#5 A5 F#5', at=2 * BAR, vel=70)
t = 6 * BAR
# punctum 1: dan tranh
L = 8 * BAR
hold(drone, t, 50, 3 * L, 70)
rhythm(t, 8, full=False); t = punctum(tranh, 0, t)
# punctum 1 again on the psaltery, kalimba answering; punctum 2
rhythm(t, 8); punctum(psal, 0, t, 92)
kalimba.mel('q. r D6 | q. r A5 | q. r F#6 | q. r E6 | q. r D6 | q. r A5 | q. r F#6 | q. r D6', at=t, vel=64)
t += L
rhythm(t, 8); t = punctum(tranh, 1, t, 92)
# punctum 2 on the psaltery with the mbira; punctum 3 together
hold(drone, t, 50, 3 * L, 70)
rhythm(t, 8); punctum(psal, 1, t, 92); punctum(mbira, 1, t, 64, tr=-12)
t += L
rhythm(t, 8); punctum(tranh, 2, t, 92); t = punctum(psal, 2, t, 84, tr=-12)
bells.note(t - BAR, pitch('D6'), 3, 70)
# all three puncta once more, everyone
for i in range(3):
    rhythm(t, 8); punctum(tranh, i, t, 94); punctum(psal, i, t, 80, tr=12 if i == 0 else 0)
    kalimba.mel('q. D6 r | q. A5 r | q. F#6 r | q. E6 r | q. D6 r | q. A5 r | q. F#6 r | q. D6 r', at=t, vel=58)
    hold(drone, t, 50, L, 70)
    t += L
gong.note(t, 61, 6, 84); bells.note(t, pitch('D6'), 4, 76); bells.note(t, pitch('A6'), 4, 66)
strum.note(t, 50, 3, 90); hold(drone, t, 50, 6, 68); tranh.note(t, pitch('D5'), 3, 90)

S.humanize(ms=8, vel=5)
finish(__file__, S, {
    'title': 'Market Square Estampie',
    'pack': 'courtyard-chapel',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A medieval-style estampie in D Mixolydian, 6/8: three puncta each played with open and closed endings, '
            'on dan tranh and psaltery over a didgeridoo bourdon, strumstick, balafon tabor, mbira, kalimba, hand '
            'chimes and a gong.',
}, [
    ('dantranh', 'ch1', 'Arctic Steps', dict(lufs=-19, pan=-14, verb=0.3)),
    ('psaltery', 'ch2', 'Slate Pick', dict(lufs=-20, pan=14, echo=0.05, verb=0.32)),
    ('strumstick', 'ch3', 'Kinetic Harp', dict(lufs=-23, pan=-6, verb=0.15)),
    ('drone', 'ch4', 'White Dormant', dict(lufs=-28, verb=0.35)),
    ('tabor', 'ch5', 'Brushed Carillon', dict(lufs=-24, pan=-30, verb=0.25)),
    ('mbira', 'ch6', 'Daylight Steps', dict(lufs=-24, pan=26, echo=0.1, verb=0.3)),
    ('kalimba', 'ch7', 'Late Ladder', dict(lufs=-26, pan=32, echo=0.2, verb=0.35)),
    ('bells', 'ch8', 'Marble Tower', dict(lufs=-25, pan=20, echo=0.15, verb=0.45)),
    ('gong', 'ch9', 'Cathode Bells', dict(lufs=-26, verb=0.5)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 3000, 'level': -5},
   reverb={'size': 2.6, 'predelay': 24, 'tone': 5000, 'level': -3})

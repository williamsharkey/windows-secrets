"""Greensleeves to a Ground, with Divisions (anonymous, from Playford's "The Division Violin", 1705), arranged for
Courtyard & Chapel: the tune and its divisions shared between psaltery, folk harp and dan tranh over a harpsichord
continuo, strumstick bass and didgeridoo bourdon, with hand chimes at each cadence."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'division-violin-two-27.mid'))
S = Score(bpm=150, seed=1705)
psal = S.part('psaltery', 1)
harp = S.part('harp', 2)
dant = S.part('dantranh', 3)
hpsi = S.part('harpsichord', 4)
bass = S.part('strumstick', 5)
drone = S.part('drone', 6)
bells = S.part('bells', 7)
tabor = S.part('tabor', 8)
vibes = S.part('vibes', 9)

BAR = 3.0          # a 3/4 measure (the print's 6/4 bars hold two)
STRAINS = 6        # the tune and five divisions: 6 x 16 measures
N = STRAINS * 16
mel = beats(src.all, 0, N * BAR, 0)
CH = {'Gm': [7, 10, 2], 'F': [5, 9, 0], 'Bb': [10, 2, 5], 'D': [2, 6, 9], 'Cm': [0, 3, 7], 'Eb': [3, 7, 10]}
PRIOR = {'Gm': 0.3, 'D': 0.2, 'F': 0.1, 'Bb': 0.1, 'Cm': 0.0, 'Eb': 0.0}


def chord_at(t):
    ns = [(p % 12, min(b + d, t + BAR) - max(b, t), abs(b - t) < 0.01) for b, p, d, v in mel if b < t + BAR and b + d > t]
    best = max(CH, key=lambda c: sum(w * (1.5 if db else 1) for pc, w, db in ns if pc in CH[c]) - 0.5 * sum(w for pc, w, db in ns if pc not in CH[c]) + PRIOR[c])
    return best


prog = [chord_at(k * BAR) for k in range(N)]
# the tune on the psaltery, then the divisions on harp, dan tranh, psaltery, harp, dan tranh
voices = [psal, harp, dant, psal, harp, dant]
for s in range(STRAINS):
    a, b = s * 16 * BAR, (s + 1) * 16 * BAR
    put(voices[s], beats(mel, a, b, a), vel=90 if s == 0 else 86, lo=60 if voices[s] is psal else 55, hi=88)
    if s == 5:
        put(vibes, skyline(beats(mel, a, b, a)), vel=56, lo=60, hi=84)
prev = None
for k, c in enumerate(prog):
    t = k * BAR
    ns = voice_lead(prev, chord(c, 4), 57, 71); prev = ns
    r = root_of(c, 3)
    hpsi.note(t, r - 12 if r > 52 else r, 0.9, 74)
    for n in ns:
        hpsi.note(t + 1, n, 0.8, 62); hpsi.note(t + 2, n, 0.8, 56)
    bass.note(t, r, 1.4, 90); bass.note(t + 1.5, r + 7 if r + 7 < 58 else r - 5, 0.45, 76); bass.note(t + 2, r, 0.9, 82)
    if k >= 16:
        tabor.note(t, 43, 0.3, 86); tabor.note(t + 1.5, 50, 0.2, 60); tabor.note(t + 2, 50, 0.2, 68)
    if k % 16 == 15:
        bells.note(t, pitch('G5'), 3, 74); bells.note(t, pitch('D6'), 3, 64)
for s in range(STRAINS):
    hold(drone, s * 16 * BAR, 43, 16 * BAR - 0.5, 66, 24)
t = N * BAR
for p, lo, hi, v in ((hpsi, 55, 74, 80), (harp, 55, 79, 76), (psal, 62, 79, 80)):
    p.chords('G:6', at=t, style='pad', vel=v, lo=lo, hi=hi)
bass.note(t, pitch('G2'), 6, 92); bells.note(t, pitch('G5'), 4, 80); bells.note(t, pitch('B5'), 4, 70)
hold(drone, t, 43, 6, 66)

S.humanize(ms=7, vel=5)
finish(__file__, S, {
    'title': 'Greensleeves to a Ground',
    'pack': 'courtyard-chapel',
    'kind': 'world',
    'composer': 'Anonymous (English, 16th century tune)',
    'source': 'Greensleeves to a Ground, with divisions: The Division Violin, second part (John Playford, 4th '
              'edition, 1705), No. 27. Score: The Mutopia Project, from the 1705 facsimile.',
    'licence': 'The work: public domain (published 1705). The edition used: public domain (Mutopia). This '
               'arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1730',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The tune and five divisions on psaltery, folk harp and dan tranh, the vibes doubling the last; a '
            'harpsichord continuo and strumstick bass on a ground read from the tune; a didgeridoo bourdon, balafon '
            'tabor, hand chimes at the cadences; a Picardy G major at the end.',
}, [
    ('psaltery', 'ch1', 'Amber Ticks', dict(lufs=-19, pan=6, echo=0.05, verb=0.32)),
    ('harp', 'ch2', 'Glass Spool', dict(lufs=-20, pan=26, echo=0.1, verb=0.3)),
    ('dantranh', 'ch3', 'Chrome Pick', dict(lufs=-20, pan=-20, verb=0.3)),
    ('harpsichord', 'ch4', 'Brass Ballad', dict(lufs=-23, pan=-30, verb=0.22)),
    ('strumstick', 'ch5', 'Floor Harp', dict(lufs=-23, pan=-8, verb=0.15)),
    ('drone', 'ch6', 'Hotel Uplink', dict(lufs=-29, verb=0.35)),
    ('bells', 'ch7', 'Pewter Gong', dict(lufs=-25, pan=22, echo=0.15, verb=0.45)),
    ('tabor', 'ch8', 'Field Carillon', dict(lufs=-26, pan=-36, verb=0.25)),
    ('vibes', 'ch9', 'Pastel Bell', dict(lufs=-27, pan=30, verb=0.35)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 3000, 'level': -5},
   reverb={'size': 2.6, 'predelay': 24, 'tone': 5000, 'level': -3})

"""Bethena, a concert waltz (Scott Joplin, 1905), arranged for the Leisure Accessories Pack: the vibes-bells and a
lounge flute share the tune over the lounge piano's waltz left hand, cello bass and strings, with crickets, a gong
and the bird calls of the executive lounge."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'bethena.mid'))
S = Score(bpm=138, seed=1905)
bells = S.part('bells', 1)
flute = S.part('flute', 2)
piano = S.part('piano', 3)
inner = S.part('marimba', 4)
cello = S.part('cello', 5)
strings = S.part('strings', 6)
brush = S.part('brush', 7)
crickets = S.part('crickets', 8)
gong = S.part('gong', 9)
birds = S.part('birds', 11)

B = 3.0
CUT = 90
gong.note(0, 55, 6, 84)
hold(crickets, 0, 60, CUT * B + 12, 72, 24)
rh = beats(src.tracks[0], 0, CUT * B, 0); lhn = beats(src.tracks[1], 0, CUT * B, 0)
top = skyline(rh)
half = CUT * B / 2
put(bells, [n for n in top if n[0] < half], vel=None, lo=64, hi=91)
put(flute, [n for n in top if n[0] >= half], tr=-12, vel=88, lo=60, hi=84)
put(inner, [n for n in rh if n not in top], vel=54, lo=55, hi=79)
low = floor(lhn)
put(cello, low, vel=86, lo=33, hi=52)
put(piano, [n for n in lhn if n not in low], vel=58, lo=52, hi=72)
arrange(src, half, CUT * B, half, pad=strings, rh_track=0, lh_track=1, pad_step=6.0, pad_range=(55, 72), vel=54)
brush.drums({60: '...x.x'}, at=6, bars=CUT - 3, step=0.5, beats_per_bar=3.0, vel={'x': 54})
for k, b in enumerate((30, 96, 170, CUT * B - 6)):
    birds.note(b, 60 + 2 * (k % 2), 2, 70)
t = CUT * B
for p, lo, hi, v in ((piano, 52, 72, 62), (strings, 55, 72, 62), (inner, 60, 79, 56)):
    p.chords('G:9', at=t, style='pad', vel=v, lo=lo, hi=hi)
cello.note(t, pitch('G2'), 9, 88); bells.note(t, pitch('G5'), 6, 80); gong.note(t + 3, 55, 6, 74)

S.humanize(ms=6, vel=4)
finish(__file__, S, {
    'title': 'Bethena',
    'pack': 'leisure',
    'kind': 'world',
    'composer': 'Scott Joplin (1868-1917)',
    'source': 'Bethena, a concert waltz (1905): the introduction and the first strains. Score: The Mutopia Project, '
              'from the original manuscript.',
    'licence': 'The work: public domain (published 1905; the composer died 1917). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=463',
    'arranger': 'Algorithmic Industries house band',
    'note': 'A lounge waltz at 138 bpm: vibes-bells then a flute on the tune, marimba on the inner voices, lounge '
            'piano on the left hand, cello bass, strings in the second half, brushes on two and three, crickets, '
            'a gong and bird calls.',
}, [
    ('bells', 'ch1', 'Soft Bells', dict(lufs=-20, pan=10, echo=0.2, verb=0.4)),
    ('flute', 'ch2', 'Polished Call', dict(lufs=-20, pan=4, echo=0.15, verb=0.4)),
    ('piano', 'ch3', 'Tiki Lounge Piano', dict(lufs=-24, pan=-18, verb=0.3)),
    ('marimba', 'ch4', 'Island Marimba', dict(lufs=-26, pan=-26, verb=0.3)),
    ('cello', 'ch5', 'Opal Section', dict(lufs=-22, verb=0.15)),
    ('strings', 'ch6', 'Volcano Strings', dict(lufs=-25, pan=12, verb=0.4, width=1.3)),
    ('brush', 'ch7', 'Twilight Tap', dict(lufs=-30, pan=30)),
    ('crickets', 'ch8', 'Mild Rain', dict(lufs=-33, width=1.4)),
    ('gong', 'ch9', 'Cedar Gong', dict(lufs=-25, verb=0.5)),
    ('birds', 'ch11', 'Half-Speed Mockingbird', dict(lufs=-28, pan=38, verb=0.4)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 2800, 'level': -6},
   reverb={'size': 2.6, 'predelay': 25, 'tone': 5000, 'level': -4})

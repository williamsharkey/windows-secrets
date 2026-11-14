"""The Entertainer (Scott Joplin, 1902), arranged for Heritage Edition 3.x: the rag's intro and A and B strains
on a ding piano with its left hand, then the C strain's tune on the tada fanfare, chimes bells and the ringout
whistle. Every sound is one of the six that came with Windows 3.1."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'entertainer.mid'))
S = Score(bpm=80, seed=1902)
rh = S.part('righthand', 1)
inner = S.part('inner', 2)
bass = S.part('stridebass', 3)
lh = S.part('stridechords', 4)
whistle = S.part('whistle', 5)
bells = S.part('bells', 6)
fanfare = S.part('fanfare', 7)
snare = S.part('snare', 8)
shaker = S.part('shaker', 9)

B = 2.0          # 2/4
CUT = 84         # intro, A, A, B, B, A: the first 84 bars
arrange(src, 0, CUT * B, 0, lead=rh, inner=inner, rh_track=0, lh_track=1, lead_range=(64, 91), inner_range=(55, 79), lead_vel=None, vel=None)
lhn = beats(src.tracks[1], 0, CUT * B, 0)
low = floor(lhn)
lows = {(round(x, 3), p) for x, p, d, v in low}
put(bass, low, vel=None, lo=36, hi=55)
put(lh, [n for n in lhn if (round(n[0], 3), n[1]) not in lows], vel=None, lo=52, hi=67)
# the whistle doubles the B strain an octave down; bells mark each strain
put(whistle, skyline(beats(src.tracks[0], 36 * B, 68 * B, 36 * B)), tr=-12, vel=72, lo=60, hi=79)
for k in (4, 20, 36, 52, 68):
    bells.note(k * B, pitch('C6'), 1.5, 70)
snare.drums({60: '..x...x.'}, at=4 * B, bars=(CUT - 4), beats_per_bar=2.0, vel={'x': 66})
shaker.drums({60: 'x.x.x.x.'}, at=4 * B, bars=(CUT - 4), beats_per_bar=2.0, vel={'x': 50})
# the ending: the last four bars of the rag on the fanfare and piano
end = src.bars() * B
t = CUT * B
arrange(src, end - 8, end, t, lead=rh, inner=inner, lh=lh, rh_track=0, lh_track=1, lead_range=(64, 91), inner_range=(55, 79), lh_range=(40, 67))
put(fanfare, skyline(beats(src.tracks[0], end - 8, end, t)), tr=-12, vel=84, lo=60, hi=79)
bells.note(t + 6, pitch('C6'), 3, 80)

S.humanize(ms=5, vel=4)
finish(__file__, S, {
    'title': 'The Entertainer',
    'pack': 'w3x-heritage',
    'kind': 'world',
    'composer': 'Scott Joplin (1868-1917)',
    'source': 'The Entertainer, a ragtime two-step (1902). Score: The Mutopia Project, from a reproduction of the '
              'original 1902 edition.',
    'licence': 'The work: public domain (published 1902; the composer died 1917). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=263',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The intro and the A and B strains on a ding piano with a stride left hand, the B strain doubled by the '
            'ringout whistle, chimes bells on each strain, ding brushes, and the rag\'s last bars on the tada fanfare. '
            'Only the six Windows 3.1 sounds.',
}, [
    ('righthand', 'ch1', 'Still Upright', dict(lufs=-19, pan=6, verb=0.25)),
    ('inner', 'ch2', 'Elevated Ballad', dict(lufs=-24, pan=14, verb=0.25)),
    ('stridebass', 'ch3', 'Field Bass', dict(lufs=-21, pan=-10, verb=0.15)),
    ('stridechords', 'ch4', 'Western Chords', dict(lufs=-24, pan=-16, verb=0.2)),
    ('whistle', 'ch5', 'Gentle Whistle', dict(lufs=-22, pan=20, echo=0.15, verb=0.3)),
    ('bells', 'ch6', 'Urban Ring', dict(lufs=-25, pan=28, verb=0.4)),
    ('fanfare', 'ch7', 'Honey Hit', dict(lufs=-22, pan=-4, verb=0.35)),
    ('snare', 'ch8', 'Basement Snare', dict(lufs=-29, pan=10)),
    ('shaker', 'ch9', 'Hollow Shaker', dict(lufs=-31, pan=-24)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.2, 'tone': 3000, 'level': -9},
   reverb={'size': 1.5, 'predelay': 15, 'tone': 5000, 'level': -6})

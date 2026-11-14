"""Clair de lune (Claude Debussy, Suite bergamasque, 1905), arranged for Listening Post: the opening and the
closing pages played by the deep ocean. A humpback carries the right hand's top line, fin-whale and blue-whale
drones hold the left hand, a singing bowl takes the inner voices; the upsweep, the bloop and the ice in between."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'debussy_Ste_Bergamesq_Clair.mid'))
S = Score(bpm=60, seed=1905)
hump = S.part('humpback', 1)
bowl = S.part('bowl', 2)
fin = S.part('fin', 3)
blue = S.part('blue', 4)
sweep = S.part('upsweep', 5)
bloop = S.part('bloop', 6)
ice = S.part('iceberg', 7)
murmur = S.part('murmur', 8)
dive = S.part('dive', 9)

B = src.bar          # 9/8: 4.5 beats
OPEN, CLOSE = 18, 64  # bars 1-18; then bars 65 to the end


def play(a, b, at):
    rh = beats(src.tracks[0], a, b, at); lhn = beats(src.tracks[1], a, b, at)
    top = skyline(rh)
    put(hump, top, vel=86, lo=60, hi=84, gate=1.0)
    put(bowl, [n for n in rh if n not in top], vel=60, lo=60, hi=79)
    lo_ = floor(lhn)
    put(fin, [(x, p, max(d, 2.0), v) for x, p, d, v in lo_], vel=72, lo=36, hi=55)
    put(blue, [(x, p, max(d, 2.0), v) for x, p, d, v in lhn if (x, p, d, v) not in lo_], vel=64, lo=50, hi=67)
    return at + (b - a)


t = 4.0
bloop.note(0, 19, 6, 80)
t = play(0, OPEN * B, t)
sweep.note(t - 10, 60, 4, 70)
# the passage between: ice, the bloop, the murmur
ice.note(t, 17, 8, 84); bloop.note(t + 4, 19, 6, 76); dive.note(t + 7, 60, 4, 70)
hold(murmur, t - 4, 60, 14, 60)
t += 10
t = play(CLOSE * B, src.bars() * B, t)
sweep.note(t - 6, 63, 4, 66); bloop.note(t, 19, 6, 70)

finish(__file__, S, {
    'title': 'Clair de lune',
    'pack': 'listening-post',
    'kind': 'world',
    'composer': 'Claude Debussy (1862-1918)',
    'source': 'Clair de lune, from Suite bergamasque, L. 75 (published 1905): bars 1-18 and 65 to the end. Score: '
              'The Mutopia Project, from E. Fromont (1905).',
    'licence': 'The work: public domain (published 1905; the composer died 1918). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0. The hydrophone recordings: NOAA PMEL, public domain.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1778',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The opening and closing pages at 60 bpm: a humpback on the top line, a singing bowl on the inner voices, '
            'fin-whale and blue-whale drones on the left hand; ice calving, the bloop and the upsweep between.',
    'tail': 8,
}, [
    ('humpback', 'ch1', 'Ocean Shoreline', dict(lufs=-20, pan=4, echo=0.2, verb=0.5)),
    ('bowl', 'ch2', 'Saffron Dormant', dict(lufs=-25, pan=-14, verb=0.5)),
    ('fin', 'ch3', 'Dial Depth', dict(lufs=-23, pan=-10, verb=0.45)),
    ('blue', 'ch4', 'Lattice Dormant', dict(lufs=-25, pan=14, verb=0.45)),
    ('upsweep', 'ch5', 'Lattice Dive', dict(lufs=-26, pan=24, echo=0.4, verb=0.5)),
    ('bloop', 'ch6', 'Cedar Murmur', dict(lufs=-24, verb=0.4)),
    ('iceberg', 'ch7', 'Swift Room', dict(lufs=-25, pan=-24, verb=0.5)),
    ('murmur', 'ch8', 'Broadcast Murmur', dict(lufs=-31, width=1.4)),
    ('dive', 'ch9', 'Tropic Sweep', dict(lufs=-27, pan=-30, echo=0.4, verb=0.5)),
], master={'loudness': -18, 'ceiling': -1.0, 'fadeout': 4},
   echo={'time': '3/8', 'feedback': 0.4, 'tone': 2200, 'level': -6},
   reverb={'size': 5.5, 'predelay': 40, 'tone': 3500, 'level': -2})

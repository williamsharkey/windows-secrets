"""Premiere Arabesque (Claude Debussy, L. 66 No. 1, 1891), arranged for Professional Workstation Classics: the
triplet runs on glass plucks, the tune on the flute solo and a violin lead, the left hand on a tuba-weight bass and
a glass pad, a light pop beat in the middle."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'debussy_Arabesque_1.mid'))
S = Score(bpm=96, seed=1891)
pluck = S.part('pluck', 1)
flute = S.part('flute', 2)
violin = S.part('violin', 3)
inner = S.part('keys', 4)
bass = S.part('bass', 5)
pad = S.part('pad', 6)
choir = S.part('choir', 7)
fx = S.part('fx', 8)
kit = S.part('kit', 10)

CUT = 46
rh = beats(src.tracks[0], 0, CUT * 4, 0); lhn = beats(src.tracks[1], 0, CUT * 4, 0)
top = skyline(rh)
# the opening runs (bars 1-6) are plucks; then the tune: flute, the violin from bar 26
put(pluck, beats(src.all, 0, 6 * 4, 0), vel=70, lo=52, hi=88)
put(flute, [n for n in top if 6 * 4 <= n[0] < 26 * 4], vel=88, lo=60, hi=88)
put(violin, [n for n in top if n[0] >= 26 * 4], vel=90, lo=60, hi=88)
put(inner, [n for n in rh if n not in top and n[0] >= 6 * 4], vel=56, lo=55, hi=84)
low = floor(lhn)
put(bass, [n for n in low if n[0] >= 6 * 4], vel=86, lo=33, hi=52)
put(pluck, [n for n in lhn if n not in low and n[0] >= 6 * 4], vel=58, lo=48, hi=76)
arrange(src, 6 * 4, CUT * 4, 6 * 4, pad=pad, rh_track=0, lh_track=1, pad_range=(55, 72), vel=50)
arrange(src, 26 * 4, CUT * 4, 26 * 4, pad=choir, rh_track=0, lh_track=1, pad_range=(55, 70), vel=52)
groove(kit, 'synthpop', 14 * 4, 11, drop=(CHH,), extra={CHH: '..x...x...x...x.'})
groove(kit, 'synthpop', 25 * 4, 1, fill=True)
groove(kit, 'synthpop', 26 * 4, 16, extra={CHH: '..x...x...x...x.'})
fx.note(0, 60, 6, 70); fx.note(26 * 4 - 4, 60, 4, 76)
t = CUT * 4
for p, lo, hi, v in ((pad, 55, 72, 60), (choir, 55, 70, 56), (inner, 60, 84, 60)):
    p.chords('E:8', at=t, style='pad', vel=v, lo=lo, hi=hi)
bass.note(t, pitch('E2'), 8, 88); pluck.chords('E:8', at=t, style='arp', vel=60, lo=64, hi=88, rhythm=0.333)
kit.note(t, KICK, 1, 100); kit.note(t, CRASH, 3, 96)

S.humanize(ms=4, vel=4)
finish(__file__, S, {
    'title': 'Premiere Arabesque',
    'pack': 'workstation-classics',
    'kind': 'world',
    'composer': 'Claude Debussy (1862-1918)',
    'source': 'Deux arabesques, L. 66: No. 1 (1891), bars 1-46. Score: The Mutopia Project, from Durand et Fils '
              '(1904).',
    'licence': 'The work: public domain (published 1891; the composer died 1918). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1777',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The opening runs on glass plucks, then the tune on the flute solo and a violin lead, inner voices on '
            'keys, a bass, glass and choir pads, a light pop beat from the second theme. Drums: Kit Manager 98 (Pop '
            'Studio Kit).',
}, [
    ('pluck', 'ch1', 'Glass Pluck Plus', dict(lufs=-21, pan=-14, echo=0.2, verb=0.3)),
    ('flute', 'ch2', 'Global Solo', dict(lufs=-20, pan=6, echo=0.15, verb=0.35)),
    ('violin', 'ch3', 'Opal Lead', dict(lufs=-20, pan=-4, echo=0.15, verb=0.35)),
    ('keys', 'ch4', 'Azure Ticks', dict(lufs=-25, pan=24, verb=0.3)),
    ('bass', 'ch5', 'Meadow Low', dict(lufs=-21)),
    ('pad', 'ch6', 'Bright Pad', dict(lufs=-26, verb=0.4, width=1.3)),
    ('choir', 'ch7', 'Night Mist', dict(lufs=-26, verb=0.45, width=1.3)),
    ('fx', 'ch8', 'Clear Warp', dict(lufs=-27, verb=0.5)),
    ('kit', 'ch10', 'kit-manager:Punch Kick Kit', dict(lufs=-19, verb=0.08)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -5},
   reverb={'size': 2.4, 'predelay': 20, 'tone': 6000, 'level': -4})

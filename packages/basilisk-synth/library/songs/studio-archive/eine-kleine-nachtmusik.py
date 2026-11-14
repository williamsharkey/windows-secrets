"""Eine kleine Nachtmusik (W. A. Mozart, K. 525, first movement, 1787), arranged for the Studio Instruments
Archive: the exposition on the studio's string sections, with the horns, piano and glockenspiel joining as each
theme arrives, then the movement's last bars for everyone."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'eine-kleine-nachtmusik-mvt1.mid'))
S = Score(bpm=138, seed=1787)
v1 = S.part('violins1', 1)
v2 = S.part('violins2', 2)
va = S.part('violas', 3)
vc = S.part('cellos', 4)
bass = S.part('bass', 5)
horns = S.part('horns', 6)
piano = S.part('piano', 7)
glock = S.part('glock', 8)
trumpet = S.part('trumpet', 9)
snap = S.part('timp', 11)

EXPO = 56
end = src.bars() * 4.0
v1n, v2n, van, vcn = src.tracks

put(v1, beats(v1n, 0, EXPO * 4, 0), vel=None, lo=55, hi=91)
put(v2, beats(v2n, 0, EXPO * 4, 0), vel=None, lo=55, hi=86)
put(va, beats(van, 0, EXPO * 4, 0), vel=None, lo=48, hi=76)
put(vc, beats(vcn, 0, EXPO * 4, 0), vel=None, lo=36, hi=64)
put(bass, [n for n in beats(vcn, 0, EXPO * 4, 0)], tr=-12, vel=80, lo=28, hi=48)
# the second theme (bars 28-51): the piano doubles the first violins, the horns hold the cellos' line
put(piano, beats(v1n, 28 * 4, 52 * 4, 28 * 4), vel=66, lo=60, hi=88)
put(horns, [(b, p, max(d, 1.0), v) for b, p, d, v in floor(beats(van + vcn, 28 * 4, 56 * 4, 28 * 4))], vel=70, lo=48, hi=64)
# the opening unison, the "Mannheim rocket", gets the glockenspiel and the trumpet on top
put(glock, skyline(beats(v1n, 0, 4 * 4, 0)), tr=12, vel=70, lo=72, hi=96)
put(trumpet, skyline(beats(v1n, 0, 4 * 4, 0)), vel=72, lo=60, hi=84)
for k in (0, 1, 2, 3):
    snap.note(k * 4.0, 60, 0.4, 84)
# the coda: the movement's last ten bars, everyone
t = EXPO * 4
a = end - 40
for part, notes, lo, hi in ((v1, v1n, 55, 91), (v2, v2n, 55, 86), (va, van, 48, 76), (vc, vcn, 36, 64)):
    put(part, beats(notes, a, end, t), vel=None, lo=lo, hi=hi)
put(bass, beats(vcn, a, end, t), tr=-12, vel=84, lo=28, hi=48)
put(horns, floor(beats(van + vcn, a, end, t)), vel=78, lo=48, hi=64)
put(trumpet, skyline(beats(v1n, a, end, t)), vel=76, lo=60, hi=84)
put(piano, beats(v1n + v2n, a, end, t), vel=64, lo=55, hi=88)
put(glock, skyline(beats(v1n, end - 8, end, t + 32)), tr=12, vel=70, lo=72, hi=96)
for b, p, d, v in floor(beats(vcn, end - 8, end, t + 32)):
    snap.note(b, 60, 0.4, 90)

S.humanize(ms=5, vel=4)
finish(__file__, S, {
    'title': 'Eine kleine Nachtmusik',
    'pack': 'studio-archive',
    'kind': 'world',
    'composer': 'Wolfgang Amadeus Mozart (1756-1791)',
    'source': 'Serenade No. 13 in G, K. 525, "Eine kleine Nachtmusik", first movement (1787): the exposition and the '
              'last ten bars. Score: The Mutopia Project.',
    'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: '
               'CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=900',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The exposition on the studio\'s first and second violins, violas, cellos and a bass; the piano and the '
            'horns join for the second theme, glockenspiel and trumpet top the opening; then the last bars for '
            'everyone, with a tap for timpani.',
}, [
    ('violins1', 'ch1', 'Humid Swell', dict(lufs=-20, pan=-28, verb=0.35)),
    ('violins2', 'ch2', 'Daylight Bows', dict(lufs=-23, pan=-10, verb=0.35)),
    ('violas', 'ch3', 'Static Swell', dict(lufs=-24, pan=10, verb=0.35)),
    ('cellos', 'ch4', 'Crystal Legato', dict(lufs=-22, pan=26, verb=0.3)),
    ('bass', 'ch5', 'Signal Bass', dict(lufs=-25, pan=20, verb=0.2)),
    ('horns', 'ch6', 'Opal Fanfare', dict(lufs=-24, pan=14, verb=0.4)),
    ('piano', 'ch7', 'Mild Ivories', dict(lufs=-24, pan=-18, verb=0.3)),
    ('glock', 'ch8', 'Basement Chimes', dict(lufs=-25, pan=30, verb=0.4)),
    ('trumpet', 'ch9', 'White Stab', dict(lufs=-24, pan=-4, verb=0.4)),
    ('timp', 'ch11', 'Clear Snap', dict(lufs=-28, verb=0.4)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.2, 'tone': 3000, 'level': -12},
   reverb={'size': 2.4, 'predelay': 22, 'tone': 5500, 'level': -4})

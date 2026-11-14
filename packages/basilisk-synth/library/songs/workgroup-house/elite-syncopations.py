"""Elite Syncopations (Scott Joplin, 1902), arranged for the Workgroup House Edition as filtered French-style
house: the rag's strains chopped into four-bar piano loops over a four-to-the-floor kit, a one-finger minor-ninth
stab, the slap disco bass on the left hand, an organ, and the choir in the breakdown."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'EliteSyncopations.mid'))
S = Score(bpm=124, seed=1902)
kit = S.part('kit', 10)
piano = S.part('piano', 1)
inner = S.part('inner', 2)
bass = S.part('bass', 3)
organ = S.part('organ', 4)
choir = S.part('choir', 5)
strings = S.part('strings', 6)
fx = S.part('fx', 7)
hat = S.part('dialhat', 8)
shaker = S.part('shaker', 9)
pad = S.part('pad', 11)


def loop(src_bar, at, reps, lead=True, low=True):
    """the rag's bars [src_bar, src_bar + 8) (2/4) = 4 bars of 4/4, looped"""
    a, b = src_bar * 2.0, (src_bar + 8) * 2.0
    for r in range(reps):
        o = at + r * 16
        rh = beats(src.tracks[0], a, b, o); lhn = beats(src.tracks[1], a, b, o)
        top = skyline(rh)
        if lead:
            put(piano, top, vel=88, lo=60, hi=88)
            put(inner, [n for n in rh if n not in top], vel=60, lo=55, hi=79)
        if low:
            for x, p, d, v in floor(lhn):
                n = p
                while n > 50:
                    n -= 12
                while n < 33:
                    n += 12
                bass.note(x, n, min(d, 0.45), 100)
    return at + reps * 16


def house(at, bars, lite=False):
    groove(kit, 'house_lite' if lite else 'house', at, bars - 1); groove(kit, 'house', at + 4 * (bars - 1), 1, fill=not lite)
    hat.drums({60: 'o.x.o.x.o.x.o.xo'}, at=at, bars=bars, vel={'x': 70, 'o': 44})
    shaker.drums({60: 'xoxoxoxoxoxoxoxo'}, at=at, bars=bars, vel={'x': 62, 'o': 40})


t = 0.0
fx.note(0, 60, 7.5, 84)
house(8, 6, lite=True)
loop(4, 16, 1, lead=True, low=False)
t = 32
house(t, 16); loop(4, t, 2); loop(8, t + 32, 2)
organ.chords(' '.join(chords_of(src.all, 4 * 2.0, 20 * 2.0, 4.0)) * 1, at=t + 32, beats=4, style='block', vel=58, lo=55, hi=72,
             rhythm=[(0.75, 0.3), (2.75, 0.3)])
t += 64
# the second strain
house(t, 16); loop(36, t, 2); loop(44, t + 32, 2)
strings.chords(' '.join(chords_of(src.all, 36 * 2.0, 52 * 2.0, 4.0)) * 1, at=t + 32, beats=4, style='pad', vel=56, lo=55, hi=72)
t += 64
# breakdown: the choir and pad on the trio's harmony, no kick
syms = chords_of(src.all, 84 * 2.0, 100 * 2.0, 4.0)
choir.chords(' '.join(syms), at=t, beats=4, style='pad', vel=66, lo=57, hi=72)
pad.chords(' '.join(syms), at=t, beats=4, style='pad', vel=56, lo=53, hi=69)
loop(84, t + 16, 1, low=False)
fx.note(t + 24, 48, 7.8, 84)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=t + 24, bars=2, vel={'x': 72})
t += 32
# the trio, then the first strain to close
kit.note(t, CRASH, 2, 110)
house(t, 16); loop(84, t, 2); loop(92, t + 32, 2)
organ.chords(' '.join(syms), at=t, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(0.75, 0.3), (2.75, 0.3)])
t += 64
house(t, 4, lite=True); loop(4, t, 1)
t += 16
piano.chords('F:4', at=t, style='pad', vel=84, lo=60, hi=79); kit.note(t, KICK, 1, 104); bass.note(t, pitch('F2'), 2, 100)

S.humanize(ms=2, vel=3, parts=['piano', 'inner', 'choir'])
finish(__file__, S, {
    'title': 'Elite Syncopations',
    'pack': 'workgroup-house',
    'kind': 'world',
    'composer': 'Scott Joplin (1868-1917)',
    'source': 'Elite Syncopations, a rag (1902): four-bar loops cut from its first, second and trio strains. Score: '
              'The Mutopia Project, from John Stark & Son (1902).',
    'licence': 'The work: public domain (published 1902; the composer died 1917). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1540',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Filtered house at 124 bpm: the rag\'s strains looped four bars at a time on the warehouse piano, the left '
            'hand on the slap disco bass, organ stabs, strings, a choir breakdown, dial-tone hats and a shaker. '
            'Drums: Kit Manager 98 (Jack Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Jack Box Kit', dict(lufs=-17, verb=0.05)),
    ('piano', 'ch1', 'Warehouse Piano Stack', dict(lufs=-19, pan=-6, echo=0.12, verb=0.2)),
    ('inner', 'ch2', 'Cable Upright', dict(lufs=-24, pan=18, verb=0.2)),
    ('bass', 'ch3', 'Slap Disco Bass', dict(lufs=-19)),
    ('organ', 'ch4', 'Jack Organ', dict(lufs=-25, pan=20, verb=0.15)),
    ('choir', 'ch5', 'Plaza Cantor', dict(lufs=-23, pan=-6, verb=0.45)),
    ('strings', 'ch6', 'Sampled Strings Swell', dict(lufs=-25, pan=22, verb=0.35)),
    ('fx', 'ch7', 'Low-Pass Sweep Wash', dict(lufs=-25, echo=0.3, verb=0.3)),
    ('dialhat', 'ch8', 'Dial Hat', dict(lufs=-28, pan=30)),
    ('shaker', 'ch9', 'Bright Shaker', dict(lufs=-30, pan=-34)),
    ('pad', 'ch11', 'Midnight Haze', dict(lufs=-26, verb=0.35, width=1.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3200, 'level': -4},
   reverb={'size': 1.8, 'predelay': 16, 'tone': 6000, 'level': -5})

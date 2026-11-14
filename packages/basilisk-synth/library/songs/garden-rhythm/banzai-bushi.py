"""Banzai-Bushi, Japanese traditional, as printed for shamisen in Osaka in 1895, arranged for Garden Rhythm Works
as early-90s rave: the shamisen tune looped on the steelpan and the rave piano, taiko drums and breakbeats, the
hoover and the robot choir, the talking machine shouting its hello."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'J95000-Banzai-Bushi.mid'))
S = Score(bpm=128, seed=1895)
kit = S.part('kit', 10)
taiko = S.part('taiko', 9)
tabla = S.part('tabla', 11)
pan = S.part('steelpan', 1)
piano = S.part('ravepiano', 2)
organ = S.part('organbass', 3)
hoover = S.part('hoover', 4)
pad = S.part('pad', 5)
robot = S.part('robot', 6)
hello = S.part('hello', 7)
mallet = S.part('marimba', 8)
shaker = S.part('shaker', 12)

L = src.bars() * src.bar     # 24 beats: the tune once
tune = src.tracks[0]
syms = chords_of(tune, 0, L, 4.0)
BREAKS = [{KICK: 'x.........x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.xx'},
          {KICK: 'x.x.......x.....', SNARE: '....x..o....x..o', CHH: 'x.x.x.xxx.x.x.x.'}]


def tune_on(part, at, tr=12, vel=90, lo=60, hi=88):
    put(part, beats(tune, 0, L, at), tr=tr, vel=vel, lo=lo, hi=hi)


def rave(at, reps, piano_on=True, hoov=False):
    for r in range(reps):
        o = at + r * L
        for k in range(int(L // 4)):
            kit.drums(BREAKS[k % 2], at=o + 4 * k, bars=1)
            taiko.drums({36: 'x.......x.......', 38: '............x.x.'}, at=o + 4 * k, bars=1, vel={'x': 88})
        shaker.drums({61: 'oxoxoxoxoxoxoxox'}, at=o, bars=int(L // 4), vel={'x': 60, 'o': 40})
        for i, sy in enumerate(syms):
            r_ = root_of(sy, 2)
            for j in range(8):
                organ.note(o + 4 * i + j * 0.5, r_ + (12 if j % 2 else 0), 0.4, 96)
            if piano_on:
                ns = chord(sy, 5)
                for off in (0, 0.75, 1.5, 2.5, 3.25):
                    for n in ns:
                        piano.note(o + 4 * i + off, n, 0.35, 84)
        if hoov:
            put(hoover, beats(tune, 0, L, o), tr=-12, vel=100, lo=48, hi=67)
    return at + reps * L


t = 0.0
# intro: the tune alone on the steelpan, taiko, hello
tune_on(pan, 0, vel=86)
taiko.drums({36: 'x...............'}, at=0, bars=int(L // 4), vel={'x': 96})
hello.note(L - 4, 60, 3, 90)
pad.chords(' '.join(syms), at=0, beats=4, style='pad', vel=60, lo=55, hi=72)
t = L
# A: breaks, organ bass, rave piano, the tune on the pan (twice)
kit.note(t, CRASH, 2, 116)
e = rave(t, 2)
tune_on(pan, t); tune_on(pan, t + L, vel=92)
t = e
# B: the hoover takes the tune, tabla kit on top (twice)
e = rave(t, 2, piano_on=False, hoov=True)
tabla.drums({36: '..x...x...x..x..', 37: 'x.....x.....x...'}, at=t, bars=int(2 * L // 4), vel={'x': 80})
tune_on(mallet, t + L, vel=74)
hello.note(t + L - 3, 60, 3, 90)
t = e
# breakdown: pad and robot choir, the pan alone
pad.chords(' '.join(syms), at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
robot.chords(' '.join(syms), at=t, beats=4, style='pad', vel=60, lo=55, hi=69)
tune_on(pan, t, vel=84)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=t + L - 8, bars=2, vel={'x': 84})
t += L
# A': everything (twice)
kit.note(t, CRASH, 2, 118)
e = rave(t, 3, hoov=True)
tune_on(pan, t, tr=24, vel=88, lo=72, hi=96); tune_on(mallet, t + L, vel=76); tune_on(pan, t + 2 * L, vel=92)
robot.chords(' '.join(syms * 3), at=t, beats=4, style='pad', vel=54, lo=55, hi=69)
t = e
hello.note(t, 60, 3, 92); piano.chords(syms[-1] + ':2', at=t, style='pad', vel=96, lo=64, hi=79)
kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 3, 110); taiko.note(t, 36, 1, 104)

S.humanize(ms=2, vel=3, parts=['steelpan', 'marimba'])
finish(__file__, S, {
    'title': 'Banzai-Bushi',
    'pack': 'garden-rhythm',
    'kind': 'world',
    'composer': 'Japanese traditional',
    'source': 'Banzai-Bushi, as printed for shamisen in Nagai and Obata, "Seiyo gakufu Nihon zokkyokushu" (Osaka: Miki '
              'Shoten, 1895). Score: The Mutopia Project.',
    'licence': 'The work: traditional, public domain. The edition used: public domain (Mutopia; the source was '
               'printed in 1895). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1759',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Early-90s rave at 128 bpm: the shamisen tune on steelpan, marimba and the hoover, taiko and breakbeats, '
            'a tabla kit, rave-organ bass, rave piano, a robot choir and the talking machine\'s hello. All from the '
            'pack.',
}, [
    ('kit', 'ch10', 'Second Bloom', dict(lufs=-17, verb=0.05)),
    ('taiko', 'ch9', 'Gentle Bloom', dict(lufs=-20, verb=0.3)),
    ('tabla', 'ch11', 'Coded Bloom', dict(lufs=-24, pan=24, verb=0.1)),
    ('steelpan', 'ch1', 'Digital Tower', dict(lufs=-20, pan=12, echo=0.3, verb=0.3)),
    ('ravepiano', 'ch2', 'Lucid Punch', dict(lufs=-21, pan=-10, verb=0.2)),
    ('organbass', 'ch3', 'Molten Brass', dict(lufs=-20)),
    ('hoover', 'ch4', 'Lagoon Stab', dict(lufs=-20, pan=6, width=1.3, verb=0.15)),
    ('pad', 'ch5', 'Bakelite Bloom', dict(lufs=-26, verb=0.35, width=1.4)),
    ('robot', 'ch6', 'Grey Choir', dict(lufs=-25, pan=-14, verb=0.4)),
    ('hello', 'ch7', 'Rubber Ahh', dict(lufs=-21, echo=0.35, verb=0.3)),
    ('marimba', 'ch8', 'Lagoon Mallets', dict(lufs=-23, pan=-24, echo=0.2, verb=0.3)),
    ('shaker', 'ch12', 'Swift Shaker', dict(lufs=-29, pan=-30)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3500, 'level': -4},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 5500, 'level': -6})

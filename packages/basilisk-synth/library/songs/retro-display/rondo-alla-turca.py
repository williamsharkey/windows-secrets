"""Rondo alla Turca (W. A. Mozart, Piano Sonata K. 331, third movement, 1783), arranged for Retro Display
Properties as synthwave: the right hand on a chrome lead and a kalimba arpeggio's bright cousin, the left hand on
tine EP and octave bass, gated drums, brass swells on the A-major march."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'KV331_3_RondoAllaTurca.mid'))
S = Score(bpm=126, seed=1783)
lead = S.part('lead', 1)
keys = S.part('keys', 2)
ep = S.part('ep', 3)
bass = S.part('bass', 4)
brass = S.part('brass', 5)
pad = S.part('pad', 6)
sax = S.part('sax', 7)
sweep = S.part('sweep', 8)
kit = S.part('kit', 10)
snare2 = S.part('snare2', 11)

N = src.bars()   # 2/4 bars
INTRO = 8.0
sweep.note(0, 60, 8, 80)
pad.chords('Am:4 E:4', at=0, style='pad', vel=58, lo=52, hi=69)
for k in range(N):
    a = k * 2.0
    at = INTRO + a
    rh = beats(src.tracks[0], a, a + 2, at); lhn = beats(src.tracks[1], a, a + 2, at)
    top = skyline(rh)
    sect = 'A' if k < 24 or 64 <= k < 88 else 'march' if 24 <= k < 32 or 56 <= k < 64 or k >= 96 else 'B'
    voice = sax if 32 <= k < 56 else lead
    put(voice, top, vel=92 if voice is lead else 96, lo=64 if voice is lead else 57, hi=91 if voice is lead else 81)
    put(keys, [n for n in rh if n not in top], vel=62, lo=60, hi=84)
    put(ep, lhn, vel=60, lo=48, hi=72)
    for x, p, d, v in floor(lhn):
        n = p
        while n > 52:
            n -= 12
        while n < 33:
            n += 12
        bass.note(x, n, min(d, 0.45), 96); bass.note(x + 0.5, n + 12, 0.4, 84) if d >= 1 else None
    if sect == 'march':
        sy = chords_of(rh + lhn, at, at + 2, 2.0)
        brass.chords(sy[0] + ':2', at=at, style='pad', vel=72, lo=55, hi=72)
    # drums in 2-bar (one 4/4 bar) units
    if k % 2 == 0:
        last = (k // 2) % 8 == 7
        kit.drums({KICK: 'x.......x.x.....', SNARE: '....x.......x...' if not last else '....x.....x.xxxx',
                   CHH: 'x.x.x.x.x.x.x.x.'}, at=at, bars=1)
        snare2.drums({60: '....x.......x...'}, at=at, bars=1, vel={'x': 84})
    if k in (0, 32, 64):
        kit.note(at, CRASH, 2, 108); sweep.note(at - 4, 60, 4, 76)
t = INTRO + N * 2.0
for p, lo, hi, v in ((brass, 55, 72, 90), (pad, 52, 69, 64), (ep, 52, 72, 70)):
    p.chords('A:6', at=t, style='pad', vel=v, lo=lo, hi=hi)
bass.note(t, pitch('A1') + 12, 6, 100); kit.note(t, KICK, 1, 108); kit.note(t, CRASH, 3, 108)
lead.mel('q A5 C#6 E6 | h A6', at=t, vel=96)

S.humanize(ms=2, vel=3, parts=['keys', 'ep'])
finish(__file__, S, {
    'title': 'Rondo alla Turca',
    'pack': 'retro-display',
    'kind': 'world',
    'composer': 'Wolfgang Amadeus Mozart (1756-1791)',
    'source': 'Piano Sonata No. 11 in A, K. 331, third movement "Alla Turca" (1783). Score: The Mutopia Project.',
    'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: '
               'CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=108',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Synthwave at 126 bpm, the whole movement: chrome lead (a sax in the F-sharp minor episode), inner voices on '
            'bright keys, the left hand on tine EP and an octave bass, brass on the A-major march, gated drums. Drums: '
            'Kit Manager 98 (Echo Chamber Kit) with the pack\'s Yellow Snare.',
}, [
    ('lead', 'ch1', 'Chrome Brass Lead', dict(lufs=-19, pan=4, echo=0.2, verb=0.3)),
    ('keys', 'ch2', 'Violet Chords', dict(lufs=-25, pan=24, echo=0.2, verb=0.2)),
    ('ep', 'ch3', 'Shiny Tine Plaza', dict(lufs=-24, pan=-18, verb=0.25)),
    ('bass', 'ch4', 'Saffron Rumble', dict(lufs=-19)),
    ('brass', 'ch5', 'Digital Swell', dict(lufs=-23, pan=10, verb=0.3, width=1.3)),
    ('pad', 'ch6', 'Northern Bloom', dict(lufs=-27, verb=0.4, width=1.4)),
    ('sax', 'ch7', 'Rooftop Sax Lead', dict(lufs=-19, pan=-6, echo=0.2, verb=0.35)),
    ('sweep', 'ch8', 'Laser Grid Sweep', dict(lufs=-26, verb=0.4)),
    ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', dict(lufs=-17, verb=0.12)),
    ('snare2', 'ch11', 'Yellow Snare', dict(lufs=-26, verb=0.4)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3200, 'level': -4},
   reverb={'size': 2.4, 'predelay': 18, 'tone': 5500, 'level': -5})

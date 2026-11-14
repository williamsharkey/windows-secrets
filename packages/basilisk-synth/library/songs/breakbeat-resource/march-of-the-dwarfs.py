"""March of the Dwarfs (Troldtog), Edvard Grieg, Lyric Pieces Op. 54 No. 3 (1891), arranged for the Breakbeat
Resource Kit as jungle: the march's first two sections over chopped breaks, a reese and a sub, orchestra hits on
its accents, the siren, and a half-time breakdown on the night-bus pad with the tines."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'Troldtog.mid'))
S = Score(bpm=170, seed=1891)
kit = S.part('kit', 10)
lead = S.part('lead', 1)
hit = S.part('hit', 2)
reese = S.part('reese', 3)
sub = S.part('sub', 4)
pad = S.part('pad', 5)
tine = S.part('tine', 6)
siren = S.part('siren', 7)
snare = S.part('snare', 8)
shaker = S.part('shaker', 9)
voices = S.part('voices', 11)
zap = S.part('zap', 12)

SEC1, SEC2 = 70, 104   # 2/4 bars
VARS = [{KICK: 'x.........x.....', SNARE: '....x..o.o..x...', CHH: 'x.xxx.x.x.xxx.x.'},
        {KICK: 'x.........xx....', SNARE: '....x..o....x..o', CHH: 'x.x.x.xxx.x.x.xx'},
        {KICK: 'x..x......x.....', SNARE: '....x.o..o..x.o.', CHH: 'xxx.x.x.xxx.x.x.'},
        {KICK: 'x.........x.....', SNARE: '....x..x.x..xxxx', CHH: 'x.x.x.x.x.x.....'}]


def breaks(at, bars4):
    for k in range(bars4):
        kit.drums(VARS[k % 4], at=at + 4 * k, bars=1)
    snare.drums({60: '....x.......x...'}, at=at, bars=bars4, vel={'x': 84})
    shaker.drums({60: 'oxoxoxoxoxoxoxox'}, at=at, bars=bars4, vel={'x': 62, 'o': 40})


def march(a, b, at):
    rh = beats(src.tracks[0], a * 2.0, b * 2.0, at); lhn = beats(src.tracks[1], a * 2.0, b * 2.0, at)
    top = skyline(rh)
    put(lead, top, vel=90, lo=60, hi=86)
    for x, p, d, v in top:
        if v >= 100 or d >= 1.5:
            hit.note(x, p if p >= 62 else p + 12, 0.4, 96)
    lo_ = floor(lhn)
    for x, p, d, v in lo_:
        n = p
        while n > 50:
            n -= 12
        while n < 34:
            n += 12
        sub.note(x, n, min(d, 1.8), 100)
        reese.note(x, n + 12, min(d, 1.2), 84)
    return at + (b - a) * 2.0


t = 0.0
# intro (8 bars of 4/4): pad and tines on the opening's harmony, the siren
syms = chords_of(src.all, 0, 64, 4.0)
pad.chords(' '.join(syms[:8]), at=0, beats=4, style='pad', vel=62, lo=53, hi=70)
tine.chords(' '.join(syms[:8]), at=0, beats=4, style='arp', vel=54, lo=60, hi=76, rhythm=0.5)
siren.note(24, 60, 3.5, 92)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.'}, at=16, bars=4, vel={'x': 60})
t = 32
kit.note(t, CRASH, 2, 116)
e = march(0, SEC1, t); breaks(t, int((e - t) // 4)); t = e
# breakdown (8 bars, half time): pad, tines, voices
syms2 = chords_of(src.all, SEC1 * 2.0, SEC2 * 2.0, 4.0)
kit.drums({KICK: 'x...............', SNARE: '........x.......', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=7)
kit.drums({SNARE: 'x.x.x.x.xxxxxxxx'}, at=t + 28, bars=1, vel={'x': 84})
pad.chords(' '.join((syms2 * 2)[:8]), at=t, beats=4, style='pad', vel=66, lo=53, hi=70)
voices.chords(' '.join((syms2 * 2)[:8]), at=t, beats=4, style='pad', vel=60, lo=57, hi=69)
for i, sy in enumerate((syms2 * 2)[:8]):
    tine.note(t + 4 * i, root_of(sy, 5), 3.8, 70)
zap.note(t + 28, 72, 1, 86); zap.note(t + 30, 79, 1, 80)
t += 32
siren.note(t, 60, 3.5, 92); kit.note(t, CRASH, 2, 116)
e = march(SEC1, SEC2, t); breaks(t, int((e - t) // 4) + 1); t = e
e = march(0, 16, t); breaks(t, int((e - t) // 4)); t = e
hit.note(t, pitch('D5'), 1, 100); kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 2, 100); sub.note(t, pitch('D2') + 12, 3, 100)

S.humanize(ms=2, vel=3, parts=['lead', 'tine', 'pad'])
finish(__file__, S, {
    'title': 'March of the Dwarfs',
    'pack': 'breakbeat-resource',
    'kind': 'world',
    'composer': 'Edvard Grieg (1843-1907)',
    'source': 'Troldtog (March of the Dwarfs), Lyric Pieces Op. 54 No. 3 (1891): the first and second sections and '
              'the opening again. Score: The Mutopia Project, from C. F. Peters (c. 1891).',
    'licence': 'The work: public domain (published 1891; the composer died 1907). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=2014',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Jungle at 170 bpm: the march on a square lead with orchestra hits on its accents, sub and reese on the '
            'left hand, chopped breaks, the block-party siren, a half-time breakdown on the night-bus pad, tines and '
            'voices. Breaks: Kit Manager 98 (Breaker Box Kit) with the pack\'s Office Snare and Plaza Shaker.',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-16.5, verb=0.06)),
    ('lead', 'ch1', 'Freestyle Square', dict(lufs=-20, pan=6, echo=0.2, verb=0.2)),
    ('hit', 'ch2', 'Breaker Orchestra Hit', dict(lufs=-22, pan=-8, verb=0.3)),
    ('reese', 'ch3', 'Neuro Growl', dict(lufs=-23, width=1.3)),
    ('sub', 'ch4', 'Sound System Sub', dict(lufs=-19)),
    ('pad', 'ch5', 'Night Bus Pad', dict(lufs=-25, verb=0.4, width=1.3)),
    ('tine', 'ch6', 'Liquid Tine', dict(lufs=-23, pan=-20, echo=0.2, verb=0.3)),
    ('siren', 'ch7', 'Block Party Siren', dict(lufs=-24, echo=0.35, verb=0.3)),
    ('snare', 'ch8', 'Office Snare', dict(lufs=-27, pan=6)),
    ('shaker', 'ch9', 'Plaza Shaker', dict(lufs=-30, pan=-30)),
    ('voices', 'ch11', 'Tidal Voices', dict(lufs=-26, pan=-10, verb=0.5)),
    ('zap', 'ch12', 'Zap Gun', dict(lufs=-26, pan=25, echo=0.4)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 5000, 'level': -6})

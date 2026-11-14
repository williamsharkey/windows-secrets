"""Ode to Joy (Ludwig van Beethoven, Symphony No. 9, finale, 1824), arranged for Kit Manager 98: four verses,
each over a different kit, the tune on the calculator's FM register bell and the typing-pool bell, the lower
voices on the signal bells and the relay room's tuned keys."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'ode.mid'))
S = Score(bpm=116, seed=1824)
calc = S.part('calculator', 1)
typing = S.part('typingpool', 2)
bells = S.part('signalbells', 3)
relay = S.part('relayroom', 4)
k1 = S.part('punchkick', 5)
k2 = S.part('swingpad', 6)
k3 = S.part('bigbreak', 7)
k4 = S.part('assembly', 8)
rain = S.part('rainclock', 9)

TR = 7     # G major up to D: the tune lands on the tuned keys (72-84)
L = src.bars() * 4.0
sop = skyline(src.tracks[0])
alto = [n for n in src.tracks[0] if n not in sop]
bassv = floor(src.tracks[1])
tenor = [n for n in src.tracks[1] if n not in bassv]


def verse(at, tune, kit, groove_name, low=True, mid=True):
    put(tune, beats(sop, 0, L, at), tr=TR, vel=92, lo=72, hi=84)
    if mid:
        put(bells, beats(alto, 0, L, at), tr=TR, vel=66, lo=60, hi=67)
    if low:
        put(relay, beats(bassv, 0, L, at), tr=TR, vel=84, lo=60, hi=72)
    groove(kit, groove_name, at, int(L // 4) - 1)
    groove(kit, groove_name, at + L - 4, 1, fill=True)
    return at + L


t = 0.0
rain.drums({KICK: 'x.......x.......', CHH: 'x.x.x.x.x.x.x.x.', 37: '...x.....x....x.'}, at=0, bars=4)
t = 16
t = verse(t, calc, k1, 'synthpop', low=True, mid=False)
t = verse(t, typing, k2, 'boombap', mid=True)
t = verse(t, calc, k3, 'breaks', mid=True)
put(typing, beats(sop, 0, L, t), tr=TR, vel=70, lo=72, hi=84)
t = verse(t, calc, k4, 'house', mid=True)
rain.drums({KICK: 'x.......x.......', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=2)
calc.mel('h D5 F#5 | w A5', at=t, vel=90)
bells.chords('D:8', at=t, style='pad', vel=70, lo=60, hi=67); relay.note(t, 62, 8, 86)

finish(__file__, S, {
    'title': 'Ode to Joy',
    'pack': 'kit-manager',
    'kind': 'world',
    'composer': 'Ludwig van Beethoven (1770-1827)',
    'source': 'The "Ode to Joy" theme from the finale of Symphony No. 9, Op. 125 (1824), as a four-part hymn. Score: '
              'The Mutopia Project.',
    'licence': 'The work: public domain. The edition used: public domain (Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=528',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Four verses in D, each over another kit (Punch Kick, Twelve-Bit Crate, Breaker Box, Assembly Line), between the '
            'Rain Clock kit; the tune on Calculator Bureau and Typing Pool\'s tuned keys, the alto on Signal Bells, '
            'the bass on Relay Room. Every sound is a Kit Manager 98 kit.',
}, [
    ('calculator', 'ch1', 'Calculator Bureau', dict(lufs=-19, pan=6, echo=0.2, verb=0.3)),
    ('typingpool', 'ch2', 'Typing Pool', dict(lufs=-21, pan=24, echo=0.15, verb=0.25)),
    ('signalbells', 'ch3', 'Signal Bells', dict(lufs=-24, pan=-22, echo=0.2, verb=0.35)),
    ('relayroom', 'ch4', 'Relay Room', dict(lufs=-22, pan=-4, verb=0.15)),
    ('punchkick', 'ch5', 'Punch Kick Kit', dict(lufs=-18, verb=0.06)),
    ('swingpad', 'ch6', 'Twelve-Bit Crate Kit', dict(lufs=-18, verb=0.06)),
    ('bigbreak', 'ch7', 'Breaker Box Kit', dict(lufs=-18, verb=0.06)),
    ('assembly', 'ch8', 'Assembly Line Kit', dict(lufs=-18, verb=0.06)),
    ('rainclock', 'ch9', 'Rain Clock Kit', dict(lufs=-20, verb=0.2)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -5},
   reverb={'size': 1.8, 'predelay': 15, 'tone': 5500, 'level': -6})

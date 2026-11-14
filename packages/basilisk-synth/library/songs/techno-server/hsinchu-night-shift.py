"""Hsinchu Night Shift: an original minimal techno track, 128 bpm, A minor. A morse-code sequence that shifts
by one step every eight bars, minor-seventh stabs into the feedback chain, relay ticks, a spring tank, a riser and
the cold choir wash."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=128, seed=4)
kit = S.part('kit', 10)
morse = S.part('morse', 1)
stab = S.part('stab', 2)
chain = S.part('chain', 3)
sub = S.part('sub', 4)
wash = S.part('wash', 5)
tick = S.part('tick', 6)
click = S.part('click', 7)
spring = S.part('spring', 8)
riser = S.part('riser', 9)
texture = S.part('texture', 11)
shaker = S.part('shaker', 12)

SEQ = [69, 72, 76, 69, 74, 69, 72, 79, 69, 72, 76, 81, 74, 72, 69, 67]


def morse_bars(at, bars, shift):
    for k in range(bars):
        for i in range(16):
            n = SEQ[(i + shift) % 16]
            if (i + shift) % 3 != 2:
                morse.note(at + 4 * k + i * 0.25, n, 0.18, 82 - (0 if i % 4 == 0 else 12))


def subs(at, bars, root='A1'):
    for k in range(bars):
        for b in range(4):
            sub.note(at + 4 * k + b + 0.5, pitch(root) + 12, 0.4, 98)


def beat(at, bars, full=True):
    groove(kit, 'techno', at, bars, drop=() if full else (CLAP, RIM))
    tick.drums({67: '..o...x...o..x.o', 72: '.......o.......x'}, at=at, bars=bars, vel={'x': 72, 'o': 50})
    if full:
        shaker.drums({60: 'oxoxoxoxoxoxoxox'}, at=at, bars=bars, vel={'x': 58, 'o': 38})


t = 0.0
hold(texture, 0, 60, 32, 70)
click.drums({60: 'x..x..x...x..x..'}, at=0, bars=8, vel={'x': 66})
morse_bars(16, 4, 0)
t = 32
for sec in range(4):   # four eight-bar shifts
    beat(t, 8, full=sec > 0); subs(t, 8, 'A1' if sec % 2 == 0 else 'F1'); morse_bars(t, 8, sec * 3)
    for k in range(8):
        stab.note(t + 4 * k + 0.5, pitch('A4' if sec % 2 == 0 else 'F4'), 0.3, 84)
        if k % 2 == 1:
            chain.note(t + 4 * k + 2.75, pitch('E4' if sec % 2 == 0 else 'C4'), 0.4, 74)
    if sec == 3:
        riser.note(t + 16, 27, 16, 86)
    t += 32
# breakdown: the wash, the spring, the morse alone
wash.chords('Am7:8 Fmaj7:8 Am7:8 G:8', at=t, style='pad', vel=66, lo=55, hi=72)
morse_bars(t, 8, 7); spring.note(t, 55, 4, 90); spring.note(t + 16, 55, 4, 84)
hold(texture, t, 60, 32, 66)
t += 32
kit.note(t, CRASH, 2, 108)
for sec in range(2):
    beat(t, 8); subs(t, 8, 'A1' if sec == 0 else 'F1'); morse_bars(t, 8, 9 + sec * 3)
    wash.chords('Am7:8 Fmaj7:8 Am7:8 G:8' if sec == 0 else 'Fmaj7:8 G:8 Am7:16', at=t, style='pad', vel=54, lo=55, hi=72)
    for k in range(8):
        stab.note(t + 4 * k + 0.5, pitch('A4' if sec == 0 else 'F4'), 0.3, 86)
        chain.note(t + 4 * k + 2.75, pitch('E4' if sec == 0 else 'C4'), 0.4, 74)
    t += 32
beat(t, 4, full=False); morse_bars(t, 4, 0); spring.note(t + 16, 55, 4, 84)
t += 16
kit.note(t, KICK, 1, 104)

finish(__file__, S, {
    'title': 'Hsinchu Night Shift',
    'pack': 'techno-server',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Minimal techno in A minor, 128 bpm: a morse-code sequence shifting a step every eight bars, a minor-seventh '
            'stab and the feedback chain, an offbeat sub, relay ticks and a shaker, the spring tank, a riser, the '
            'cold choir wash in the breakdown. Drums: Kit Manager 98 (Long Boom Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Long Boom Kit', dict(lufs=-16.5, verb=0.04)),
    ('morse', 'ch1', 'Granite Line', dict(lufs=-21, pan=-10, echo=0.4, verb=0.15)),
    ('stab', 'ch2', 'Washed Fanfare', dict(lufs=-22, pan=8, echo=0.45, verb=0.25)),
    ('chain', 'ch3', 'Feedback Chain Stab', dict(lufs=-25, pan=-16, echo=0.5, verb=0.3)),
    ('sub', 'ch4', 'Quiet Sub', dict(lufs=-19)),
    ('wash', 'ch5', 'Cold Wash', dict(lufs=-25, verb=0.45, width=1.3)),
    ('tick', 'ch6', 'Rural Tick', dict(lufs=-28, pan=30, echo=0.25)),
    ('click', 'ch7', 'Coral Click', dict(lufs=-28, pan=-28)),
    ('spring', 'ch8', 'Spring Tank Hit', dict(lufs=-24, verb=0.4)),
    ('riser', 'ch9', 'Crystal Riser', dict(lufs=-26, verb=0.4)),
    ('texture', 'ch11', 'Marble Current', dict(lufs=-30, verb=0.3)),
    ('shaker', 'ch12', 'Vinyl Shaker', dict(lufs=-30, pan=20)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.5, 'tone': 2400, 'level': -3, 'lowcut': 250},
   reverb={'size': 2.4, 'predelay': 20, 'tone': 4500, 'level': -6})

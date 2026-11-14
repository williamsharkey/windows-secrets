"""Netsplit at 3AM: an original jungle track, 170 bpm, D minor. A night-bus pad and tine chords, then chopped
breaks, the block-party siren, orchestra hits and a growling reese."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=170, seed=7)
kit = S.part('kit', 10)
sub = S.part('sub', 2)
reese = S.part('reese', 3)
pad = S.part('pad', 4)
tine = S.part('tine', 5)
hit = S.part('hit', 6)
whistle = S.part('whistle', 7)
voices = S.part('voices', 8)
siren = S.part('siren', 9)
snare = S.part('snare', 11)
shaker = S.part('shaker', 12)
zap = S.part('zap', 13)

PROG = 'Dm9 Bbmaj7 Gm9 A7'
TUNE = 'h. A4 q C5 | h D5 q. C5 e A4 | w G4 | h E4 F4 | h. A4 q C5 | h D5 q. E5 e F5 | w E5 | w C#5'
VARS = [
    {KICK: 'x.........x.....', SNARE: '....x..o.o..x...', CHH: 'x.xxx.x.x.xxx.x.'},
    {KICK: 'x.........xx....', SNARE: '....x..o....x..o', CHH: 'x.x.x.xxx.x.x.xx'},
    {KICK: 'x..x......x.....', SNARE: '....x.o..o..x.o.', CHH: 'xxx.x.x.xxx.x.x.'},
    {KICK: 'x.........x...x.', SNARE: '....x..o.o..x.xo', CHH: 'x.xxx.xxx.xxx.xx'},
]


def breaks(at, bars, fill=True):
    for k in range(bars):
        v = VARS[k % 4]
        if fill and k % 8 == 7:
            kit.drums({KICK: 'x.........x.....', SNARE: '....x.xxo.xxXxXX', CHH: 'x.x.x.x.........'}, at=at + 4 * k, bars=1)
        else:
            kit.drums(v, at=at + 4 * k, bars=1)
    snare.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 84})
    shaker.drums({60: 'oxoxoxoxoxoxoxox'}, at=at, bars=bars, vel={'x': 62, 'o': 40})


def subline(at, bars, vel=104):
    for k in range(bars):
        r = root_of(PROG.split()[k % 4], 2) + 12
        sub.note(at + 4 * k, r, 2.4, vel); sub.note(at + 4 * k + 2.5, r, 1.3, vel - 12)


def reeseline(at, bars, vel=92):
    for k in range(bars):
        r = root_of(PROG.split()[k % 4], 2) + 12
        reese.note(at + 4 * k, r, 1.5, vel); reese.note(at + 4 * k + 1.75, r + (3 if k % 2 else 0), 0.5, vel - 10)
        reese.note(at + 4 * k + 2.5, r + 7 if k % 4 == 3 else r, 1.4, vel - 6)


def hits(at, bars, vel=96):
    for k in range(bars):
        if k % 2 == 0:
            r = root_of(PROG.split()[k % 4], 4)
            hit.note(at + 4 * k, r, 0.5, vel); hit.note(at + 4 * k + 1.5, r, 0.4, vel - 12)


t = 0.0
# intro (16)
pad.chords(' '.join([PROG] * 4), at=0, beats=4, style='pad', vel=62, lo=53, hi=70)
tine.chords(' '.join([PROG] * 2), at=32, beats=4, style='block', vel=58, lo=58, hi=74, rhythm=[(0, 1.4), (1.5, 0.5), (2.5, 1.4)])
voices.chords(PROG, at=32, beats=8, style='pad', vel=64, lo=57, hi=69)
siren.note(48, 60, 3.5, 92); siren.note(56, 60, 3.5, 92)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.'}, at=48, bars=4, vel={'x': 60})
t = 64
# drop A (32)
kit.note(t, CRASH, 2, 116)
breaks(t, 32); subline(t, 32); hits(t, 16)
tine.chords(' '.join([PROG] * 4), at=t + 64, beats=4, style='block', vel=56, lo=58, hi=74, rhythm=[(0, 1.4), (2.5, 1.0)])
pad.chords(' '.join([PROG] * 4), at=t + 64, beats=4, style='pad', vel=54, lo=53, hi=70)
siren.note(t + 60, 60, 3.5, 88); zap.note(t + 120, 72, 1, 90); zap.note(t + 122, 79, 1, 84)
t += 128
# break (16): half-time, the whistle tune
kit.drums({KICK: 'x...............', SNARE: '........x.......', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=14)
kit.drums({SNARE: 'x.x.x.x.xxxxxxxx'}, at=t + 56, bars=2, vel={'x': 80})
pad.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=66, lo=53, hi=70)
tine.chords(' '.join([PROG] * 4), at=t, beats=4, style='arp', vel=54, lo=60, hi=76, rhythm=0.5)
whistle.mel(TUNE, at=t, vel=86); whistle.mel(TUNE, at=t + 32, vel=90)
voices.chords(PROG + ' ' + PROG, at=t + 32, beats=4, style='pad', vel=60, lo=57, hi=69)
sub.bass(' '.join([PROG] * 4), at=t, beats=4, pattern=[(0, 0, 3.8)], vel=90, octave=3)
t += 64
# drop B (24): the reese, hits, zaps
kit.note(t, CRASH, 2, 116); siren.note(t, 60, 3.5, 92)
breaks(t, 24); subline(t, 24, 100); reeseline(t, 24); hits(t, 24, 100)
whistle.mel(TUNE, at=t + 32, vel=82)
for k in range(6):
    zap.note(t + 16 * k + 14, 72 + (k % 3) * 5, 0.8, 86)
t += 96
# outro (8)
kit.drums(VARS[0], at=t, bars=4)
pad.chords('Dm9:16 Bbmaj7:8 A7:8', at=t, beats=4, style='pad', vel=58, lo=53, hi=70)
tine.chords('Dm9:32', at=t, style='arp', vel=50, lo=60, hi=76, rhythm=0.5)
t += 32
hit.note(t, pitch('D4'), 1, 100); kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 2, 100)

S.humanize(ms=2, vel=4, parts=['tine', 'whistle', 'pad', 'voices'])
finish(__file__, S, {
    'title': 'Netsplit at 3AM',
    'pack': 'breakbeat-resource',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Jungle in D minor, 170 bpm: night-bus pad, tine chords, chopped breaks, the block-party siren, orchestra '
            'hits, sub and reese, a whistle tune in the half-time break. Breaks: Kit Manager 98 (Breaker Box Kit) '
            'layered with the pack\'s Office Snare and Plaza Shaker.',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-16.5, verb=0.06)),
    ('sub', 'ch2', 'Sound System Sub', dict(lufs=-19)),
    ('reese', 'ch3', 'Neuro Growl', dict(lufs=-22, pan=0, width=1.3)),
    ('pad', 'ch4', 'Night Bus Pad', dict(lufs=-25, verb=0.4, width=1.3)),
    ('tine', 'ch5', 'Liquid Tine', dict(lufs=-23, pan=-20, echo=0.2, verb=0.3)),
    ('hit', 'ch6', 'Breaker Orchestra Hit', dict(lufs=-21, pan=8, verb=0.3)),
    ('whistle', 'ch7', 'Upper Whistle', dict(lufs=-21, pan=12, echo=0.3, verb=0.35)),
    ('voices', 'ch8', 'Tidal Voices', dict(lufs=-26, pan=-10, verb=0.5)),
    ('siren', 'ch9', 'Block Party Siren', dict(lufs=-24, echo=0.35, verb=0.3)),
    ('snare', 'ch11', 'Office Snare', dict(lufs=-27, pan=6)),
    ('shaker', 'ch12', 'Plaza Shaker', dict(lufs=-30, pan=-30)),
    ('zap', 'ch13', 'Zap Gun', dict(lufs=-26, pan=25, echo=0.4)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.4, 'tone': 3000, 'level': -3},
   reverb={'size': 2.2, 'predelay': 15, 'tone': 5000, 'level': -6})

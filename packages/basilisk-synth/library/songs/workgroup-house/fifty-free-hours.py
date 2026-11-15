"""Fifty Free Hours: an original deep house track, 122 bpm, F minor. A modem dials in, one-finger minor-ninth stabs,
an organ bass stab, a talking-robot hook and a choir breakdown."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=122, seed=1997)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
stab = S.part('stab', 3)
organ = S.part('organ', 4)
keys = S.part('keys', 5)
pad = S.part('pad', 6)
lead = S.part('lead', 7)
choir = S.part('choir', 8)
fx = S.part('fx', 9)
hat = S.part('dialhat', 11)
shaker = S.part('shaker', 12)
strings = S.part('strings', 13)

PROG = 'Fm7 Dbmaj7 Eb Cm7'
STAB_ROOT = {'Fm7': 'F4', 'Dbmaj7': 'Bb3', 'Eb': 'C4', 'Cm7': 'C4'}   # the stab plays a minor ninth on its note
HOOK = 'e r F5 Ab5 F5 q C6 e Bb5 Ab5 | q F5 e Eb5 F5 h r | e r F5 Ab5 Bb5 q C6 e Eb6 C6 | q Bb5 Ab5 h F5'
BASSPAT = [(0, 0, 0.45), (0.75, 0, 0.2), (1.5, '8', 0.4), (2.5, 0, 0.45), (3.25, '5', 0.2), (3.5, '8', 0.45)]


def stabs(at, bars, vel=84):
    t = at
    for k in range(bars):
        sym = PROG.split()[k % 4]
        n = pitch(STAB_ROOT[sym])
        for off in (0.5, 1.25, 2.5, 3.25):
            stab.note(t + off, n, 0.35, vel - (6 if off in (1.25, 3.25) else 0))
        t += 4


def organ_bar(at, bars, vel=80):
    for k in range(bars):
        r = root_of(PROG.split()[k % 4], 4)
        organ.note(at + 4 * k + 0.75, r, 0.3, vel); organ.note(at + 4 * k + 2.75, r, 0.3, vel - 10)


def hats(at, bars, vel=70):
    hat.drums({60: 'o.x.o.x.o.x.o.xo'}, at=at, bars=bars, vel={'x': vel, 'o': vel - 26})


def shake(at, bars):
    shaker.drums({60: 'xoxoxoxoxoxoxoxo'}, at=at, bars=bars, vel={'x': 66, 'o': 44})


t = 0.0
# intro (8 bars): the modem dials in, the pad, then the kick
fx.note(0, 60, 7.5, 92)
pad.chords(PROG + ' ' + PROG, at=0, beats=4, style='pad', vel=58, lo=53, hi=70)
groove(kit, 'house_lite', 8, 4, drop=(CHH,))
hats(16, 2)
t = 32
# groove A (16 bars)
groove(kit, 'house', t, 15, fill=False); groove(kit, 'house', t + 60, 1, fill=True)
bass.bass(' '.join([PROG] * 4), at=t, beats=4, pattern=BASSPAT, vel=100)
stabs(t, 16); organ_bar(t + 32, 8); hats(t, 16); shake(t + 32, 8)
keys.chords(' '.join([PROG] * 2), at=t + 32, beats=4, style='block', vel=60, lo=55, hi=72,
            rhythm=[(1.5, 0.4), (3.0, 0.9)])
t += 64
# breakdown (8 bars): no kick, the choir sings, the EP and strings swell, the sweep rises
pad.chords(PROG + ' ' + PROG, at=t, beats=4, style='pad', vel=64, lo=53, hi=70)
keys.chords(PROG + ' ' + PROG, at=t, beats=4, style='arp', vel=58, lo=60, hi=76, rhythm=0.5)
choir.mel('h C5 Ab4 | w Bb4 | h G4 Bb4 | w C5 | h Eb5 C5 | w Db5 | h Bb4 G4 | w C5', at=t, vel=78)
strings.chords(PROG + ' ' + PROG, at=t + 16, beats=4, style='pad', vel=70, lo=55, hi=72)
fx.note(t + 24, 48, 7.8, 84)
hats(t + 16, 4)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxxxxx'}, at=t + 24, bars=2, vel={'x': 70})
t += 32
# drop (16 bars): everything, the robot hook
groove(kit, 'house', t, 15); groove(kit, 'house', t + 60, 1, fill=True)
kit.note(t, CRASH, 1, 110)
bass.bass(' '.join([PROG] * 4), at=t, beats=4, pattern=BASSPAT, vel=104)
stabs(t, 16, 88); organ_bar(t, 16); hats(t, 16, 76); shake(t, 16)
for k in range(4):
    lead.mel(HOOK, at=t + 16 * k, vel=92 if k % 2 == 0 else 86, tr=-12)
choir.mel('w C5 | w Db5 | w Bb4 | w C5', at=t + 48, vel=62)
strings.chords(' '.join([PROG] * 2), at=t + 32, beats=4, style='pad', vel=58, lo=55, hi=72)
t += 64
# outro (8 bars): the hook once more, then down to the kick and the stab
groove(kit, 'house', t, 4)
groove(kit, 'house_lite', t + 16, 4)
bass.bass(PROG, at=t, beats=4, pattern=BASSPAT, vel=96)
stabs(t, 8, 78); hats(t, 6)
lead.mel(HOOK, at=t, vel=84, tr=-12)
pad.chords(PROG + ' Fm7:4', at=t + 16, beats=4, style='pad', vel=56, lo=53, hi=70)
fx.note(t + 28, 60, 4, 70)
t += 32
kit.note(t, KICK, 1, 100); stab.note(t, pitch('F4'), 1.5, 84)

S.humanize(ms=3, vel=4, parts=['keys', 'lead', 'choir', 'strings', 'pad'])
finish(__file__, S, {
    'title': 'Fifty Free Hours',
    'pack': 'workgroup-house',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Deep house in F minor, 122 bpm. The modem dials up, a one-finger minor-ninth stab, organ bass stab, '
            'talking-robot hook, choir breakdown. Drums: Kit Manager 98 (Jack Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Jack Box Kit', dict(lufs=-17, pan=0, verb=0.05)),
    ('bass', 'ch2', 'Slap Disco Bass', dict(lufs=-19, pan=0)),
    ('stab', 'ch3', 'Velvet Minor Nine', dict(lufs=-21, pan=-12, echo=0.18, verb=0.18)),
    ('organ', 'ch4', 'Jack Organ', dict(lufs=-24, pan=18, verb=0.15)),
    ('keys', 'ch5', 'Afterhours Tine', dict(lufs=-24, pan=-25, echo=0.15, verb=0.25)),
    ('pad', 'ch6', 'Midnight Haze', dict(lufs=-25, pan=0, verb=0.35, width=1.3)),
    ('lead', 'ch7', 'Robot Mouth Lead', dict(lufs=-20, pan=6, echo=0.25, verb=0.2)),
    ('choir', 'ch8', 'Plaza Cantor', dict(lufs=-23, pan=-6, verb=0.45)),
    ('modem', 'ch9', 'Polar Ascent', dict(lufs=-24, pan=0, echo=0.3, verb=0.3)),
    ('dialhat', 'ch11', 'Dial Hat', dict(lufs=-27, pan=30)),
    ('shaker', 'ch12', 'Bright Shaker', dict(lufs=-29, pan=-34)),
    ('strings', 'ch13', 'Sampled Strings Swell', dict(lufs=-25, pan=22, verb=0.35)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3200, 'level': -3},
   reverb={'size': 1.8, 'predelay': 16, 'tone': 6000, 'level': -5})

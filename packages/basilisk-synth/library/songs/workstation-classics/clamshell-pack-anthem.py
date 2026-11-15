"""Clamshell Pack Anthem: an original happy-trance pop track, 136 bpm, F major. Bouncing offbeat bass, glass
plucks, a ladder arpeggio, the arena pluck chords, a choir hook and the flute solo lead on the chorus."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=136, seed=2000)
kit = S.part('kit', 10)
bass = S.part('bass', 1)
pluck = S.part('pluck', 2)
ladder = S.part('ladder', 3)
chords_ = S.part('chords', 4)
choir = S.part('choir', 5)
lead = S.part('lead', 6)
pad = S.part('pad', 7)
fx = S.part('fx', 8)
stab = S.part('stab', 9)

V = 'F C Dm Bb'
C = 'Bb C Am Dm Bb C F F'
HOOK = 'q A5 e A5 G5 q F5 C6 | q A5 e G5 F5 h G5 | q F5 e F5 E5 q D5 A5 | h. F5 q r'
CH = 'h F6 q E6 D6 | h E6 q C6 A5 | h C6 q A5 G5 | h. A5 q r | h F6 q E6 D6 | h E6 q G6 E6 | h C6 q D6 E6 | w F6'


def off(at, prog, reps, vel=100):
    bass.bass(' '.join([prog] * reps), at=at, beats=4, pattern=[(0.5, 0, 0.4), (1.5, 0, 0.4), (2.5, 0, 0.4), (3.5, '8', 0.4)], vel=vel)


def arps(at, prog, reps):
    ladder.chords(' '.join([prog] * reps), at=at, beats=4, style='arp', vel=60, lo=65, hi=84, rhythm=0.25)


t = 0.0
pluck.chords(V + ' ' + V, at=0, beats=4, style='block', vel=58, lo=60, hi=77, rhythm=[(0, 0.3), (0.75, 0.3), (1.5, 0.3), (2.5, 0.3), (3.0, 0.3)])
fx.note(24, 60, 8, 80)
t = 32
groove(kit, 'trance', t, 15); groove(kit, 'trance', t + 60, 1, fill=True)
off(t, V, 4); arps(t, V, 4)
for k in range(4):
    choir.mel(HOOK, at=t + 16 * k, vel=86 + 2 * k, tr=-12)
t += 64
kit.note(t, CRASH, 2, 112)
groove(kit, 'trance', t, 15); groove(kit, 'trance', t + 60, 1, fill=True)
off(t, C, 2, 104); arps(t, C, 2)
lead.mel(CH + ' | ' + CH, at=t, vel=96, tr=-12)
chords_.chords(' '.join([C] * 2), at=t, beats=4, style='block', vel=72, lo=55, hi=72, rhythm=[(0, 0.5), (1.5, 0.5), (3, 0.3)])
pad.chords(' '.join([C] * 2), at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
stab.drums({62: 'x...............'}, at=t, bars=16, vel={'x': 76})
t += 64
# break
pad.chords(' '.join([V] * 2), at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
choir.mel(HOOK + ' | ' + HOOK, at=t, vel=84, tr=-12)
fx.note(t + 24, 60, 8, 86); kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxXXXX'}, at=t + 24, bars=2, vel={'x': 80, 'X': 100})
t += 32
kit.note(t, CRASH, 2, 116)
groove(kit, 'trance', t, 15); groove(kit, 'trance', t + 60, 1, fill=True)
off(t, C, 2, 104); arps(t, C, 2)
lead.mel(CH + ' | ' + CH, at=t, vel=98, tr=-12); choir.mel(CH, at=t + 32, vel=72, tr=-24)
chords_.chords(' '.join([C] * 2), at=t, beats=4, style='block', vel=74, lo=55, hi=72, rhythm=[(0, 0.5), (1.5, 0.5), (3, 0.3)])
t += 64
chords_.chords('F:4', at=t, style='pad', vel=88, lo=57, hi=72); kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 3, 100)

S.humanize(ms=2, vel=3, parts=['choir', 'lead'])
finish(__file__, S, {
    'title': 'Clamshell Pack Anthem',
    'pack': 'workstation-classics',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Happy-trance pop in F, 136 bpm: an offbeat bass, glass plucks, a ladder arpeggio, a choir hook, the flute '
            'solo lead on the chorus, arena-pluck chords, a salute stab, a pad. Drums: Kit Manager 98 (Punch Kick Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Punch Kick Kit', dict(lufs=-16.5, verb=0.06)),
    ('bass', 'ch1', 'Neon Rumble', dict(lufs=-19)),
    ('pluck', 'ch2', 'Glass Pluck Plus', dict(lufs=-23, pan=-18, echo=0.2, verb=0.15)),
    ('ladder', 'ch3', 'Ultra Ladder', dict(lufs=-25, pan=22, echo=0.25)),
    ('chords', 'ch4', 'Elevated Horns', dict(lufs=-22, pan=12, verb=0.2)),
    ('choir', 'ch5', 'Night Mist', dict(lufs=-21, pan=-6, verb=0.4)),
    ('lead', 'ch6', 'Global Solo', dict(lufs=-19, pan=4, echo=0.25, verb=0.3)),
    ('pad', 'ch7', 'Rapid Glow', dict(lufs=-26, verb=0.4, width=1.3)),
    ('fx', 'ch8', 'Rusty Ascent', dict(lufs=-26, verb=0.4)),
    ('stab', 'ch9', 'Washed Salute', dict(lufs=-25, pan=-14, echo=0.3, verb=0.2)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.32, 'tone': 3500, 'level': -4},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 6000, 'level': -6})

"""100% Compatible: an original Eurodance track, 132 bpm, D minor. An offbeat mono bass, arena plucks, a choir pad,
poly-brass stabs, a degaussed monitor and the big lead in the chorus."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=132, seed=2000)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
pluck = S.part('pluck', 3)
brass = S.part('brass', 4)
lead = S.part('lead', 5)
verse = S.part('verse', 6)
choir = S.part('choir', 7)
strings = S.part('strings', 8)
lift = S.part('lift', 9)
degauss = S.part('degauss', 11)
stab = S.part('stab', 12)

V = 'Dm Bb C Am'
C = 'Dm Bb C A'
VERSE = 'q D5 D5 e C5 D5 q F5 | q. F5 e D5 h Bb4 | q C5 C5 e Bb4 C5 q E5 | q. E5 e C5 h A4'
HOOK = 'e A5 A5 r A5 q G5 F5 | e F5 F5 r F5 q E5 D5 | e E5 E5 r E5 q G5 E5 | h. E5 q C#5'


def offbass(at, prog, reps, vel=100):
    pat = [(0.5, 0, 0.4), (1.5, 0, 0.4), (2.5, 0, 0.4), (3.5, '8', 0.4)]
    bass.bass(' '.join([prog] * reps), at=at, beats=4, pattern=pat, vel=vel)


def plucks(at, prog, reps, vel=66):
    pluck.chords(' '.join([prog] * reps), at=at, beats=4, style='block', vel=vel, lo=60, hi=76,
                 rhythm=[(0, 0.3), (0.75, 0.3), (1.5, 0.3), (2.5, 0.3), (3.0, 0.3), (3.5, 0.3)])


def brass_stabs(at, prog, reps, vel=80):
    brass.chords(' '.join([prog] * reps), at=at, beats=4, style='block', vel=vel, lo=57, hi=72,
                 rhythm=[(0, 0.5), (1.5, 0.5), (3.0, 0.3)])


t = 0.0
# intro (8)
degauss.note(0, 60, 3, 96)
choir.chords(' '.join([V] * 2), at=0, beats=4, style='pad', vel=58, lo=55, hi=72)
plucks(16, V, 1, 56)
groove(kit, 'house_lite', 16, 4, drop=(CHH,), fill=False)
lift.note(24, 48, 8, 84)
t = 32
# verse (16)
groove(kit, 'disco', t, 15); groove(kit, 'disco', t + 60, 1, fill=True)
offbass(t, V, 4); plucks(t, V, 4)
choir.chords(' '.join([V] * 4), at=t, beats=4, style='pad', vel=54, lo=55, hi=72)
for k in range(4):
    verse.mel(VERSE, at=t + 16 * k, vel=86 + 2 * k)
t += 64
# chorus (16)
kit.note(t, CRASH, 2, 112)
groove(kit, 'disco', t, 15); groove(kit, 'disco', t + 60, 1, fill=True)
offbass(t, C, 4, 104); plucks(t, C, 4, 62); brass_stabs(t, C, 4)
for k in range(4):
    lead.mel(HOOK, at=t + 16 * k, vel=96)
strings.chords(' '.join([C] * 4), at=t, beats=4, style='pad', vel=60, lo=55, hi=72)
stab.drums({62: 'x...............'}, at=t, bars=16, vel={'x': 78})
t += 64
# break (8): strings and choir, the monitor degausses, the lift
degauss.note(t, 60, 3, 92)
strings.chords('Bb C Dm Dm Bb C A A', at=t, beats=4, style='pad', vel=70, lo=55, hi=72)
choir.mel('w F5 | w G5 | h A5 F5 | w D5 | w F5 | w G5 | w E5 | w C#5', at=t, vel=74)
pluck.chords('Bb C Dm Dm Bb C A A', at=t + 16, beats=4, style='arp', vel=54, lo=62, hi=77, rhythm=0.25)
lift.note(t + 16, 48, 16, 88)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxXXXX'}, at=t + 24, bars=2, vel={'x': 80, 'X': 100})
t += 32
# chorus (16), with the verse line under it
kit.note(t, CRASH, 2, 116)
groove(kit, 'disco', t, 15); groove(kit, 'disco', t + 60, 1, fill=True)
offbass(t, C, 4, 104); plucks(t, C, 4, 64); brass_stabs(t, C, 4, 84)
for k in range(4):
    lead.mel(HOOK, at=t + 16 * k, vel=98)
verse.mel(VERSE, at=t + 32, vel=76, tr=-12); verse.mel(VERSE, at=t + 48, vel=78, tr=-12)
strings.chords(' '.join([C] * 4), at=t, beats=4, style='pad', vel=60, lo=55, hi=72)
choir.chords(' '.join([C] * 4), at=t, beats=4, style='pad', vel=52, lo=55, hi=72)
t += 64
# outro (8)
groove(kit, 'disco', t, 4); groove(kit, 'house_lite', t + 16, 4, drop=(CHH,))
offbass(t, V, 1, 96); plucks(t, V, 2, 56)
choir.chords('Dm Bb C Am Dm:16', at=t, beats=4, style='pad', vel=54, lo=55, hi=72)
t += 32
brass.chords('Dm:2', at=t, style='pad', vel=90, lo=57, hi=72); kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 2, 100)
degauss.note(t + 1, 60, 3, 80)

S.humanize(ms=2, vel=3, parts=['verse', 'lead', 'choir', 'strings'])
finish(__file__, S, {
    'title': '100% Compatible',
    'pack': 'workstation-classics',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Eurodance in D minor, 132 bpm: offbeat mono bass, arena plucks, choir pad, poly-brass stabs, a degaussed '
            'monitor and the chorus lead. Drums: Kit Manager 98 (Punch Kick Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Punch Kick Kit', dict(lufs=-16.5, verb=0.06)),
    ('bass', 'ch2', 'Ladder Mono Bass', dict(lufs=-19)),
    ('pluck', 'ch3', 'Arena Pluck', dict(lufs=-23, pan=-20, echo=0.2, verb=0.15)),
    ('brass', 'ch4', 'Poly Brass Circuit', dict(lufs=-22, pan=16, verb=0.2)),
    ('lead', 'ch5', 'Chrome Pilot', dict(lufs=-19, pan=0, echo=0.25, verb=0.25)),
    ('verse', 'ch6', 'Lobby Song', dict(lufs=-20, pan=-6, echo=0.2, verb=0.25)),
    ('choir', 'ch7', 'Night Mist', dict(lufs=-25, verb=0.4, width=1.3)),
    ('strings', 'ch8', 'Pale Cloud', dict(lufs=-24, pan=10, verb=0.35, width=1.3)),
    ('lift', 'ch9', 'Brass Lift', dict(lufs=-26, verb=0.4)),
    ('degauss', 'ch11', 'Dusk Sweep', dict(lufs=-23, verb=0.3)),
    ('stab', 'ch12', 'Saffron Stab', dict(lufs=-26, pan=-14, echo=0.3, verb=0.2)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.32, 'tone': 3500, 'level': -4},
   reverb={'size': 2.0, 'predelay': 15, 'tone': 6000, 'level': -6})

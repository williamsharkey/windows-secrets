"""Mission-Critical Repetition: an original dub techno track, 126 bpm, C minor. One-finger dub chords into a long
echo, a sub on the offbeat, Detroit strings, a relay-tick groove and a transmission from orbit."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=126, seed=40)
kit = S.part('kit', 10)
sub = S.part('sub', 2)
dub = S.part('dub', 3)
strings = S.part('strings', 4)
lead = S.part('lead', 5)
hum = S.part('hum', 6)
click = S.part('click', 7)
tick = S.part('tick', 8)
hat = S.part('hat', 9)
voice = S.part('voice', 11)
sweep = S.part('sweep', 12)
clap = S.part('clap', 13)

# the dub chord's note per bar (it plays a minor triad on it): C, C, Ab, Bb
DUBROOT = ['C4', 'C4', 'Ab3', 'Bb3']
SUBROOT = ['C2', 'C2', 'Ab1', 'Bb1']


def dubs(at, bars, vel=86, busy=False):
    for k in range(bars):
        n = pitch(DUBROOT[k % 4]) + 12 * 0
        for off in ((0.5, 1.75, 3.0) if busy else (0.5, 2.25)):
            dub.note(at + 4 * k + off, n, 0.3, vel - (8 if off > 1 else 0))


def subs(at, bars, vel=100):
    for k in range(bars):
        n = pitch(SUBROOT[k % 4]) + 12
        for b in range(4):
            sub.note(at + 4 * k + b + 0.5, n, 0.42, vel - (0 if b % 2 == 0 else 8))


def clicks(at, bars, vel=70):
    click.drums({60: 'x..x..x...x..x..'}, at=at, bars=bars, vel={'x': vel})


def ticks(at, bars):
    tick.drums({67: '..o...x...o..x.o', 72: '.......o.......x'}, at=at, bars=bars, vel={'x': 74, 'o': 52})


def hats(at, bars):
    hat.drums({60: '..x...x...x...x.'}, at=at, bars=bars, vel={'x': 78})


LEAD = 'q. C5 e Eb5 q G5 Bb4 | h. C5 q r | q. Eb5 e F5 q G5 Bb4 | h. Ab4 q r'

t = 0.0
hum.note(0, 54, 15.5, 80)
clicks(0, 8)
groove(kit, 'techno', 16, 4, drop=(CLAP, RIM, CHH))
t = 32
# A (16)
groove(kit, 'techno', t, 16, drop=(CLAP,))
subs(t, 16); dubs(t, 16); clicks(t, 8); hats(t + 16, 8)
t += 64
# B (16): the strings, the claps, the ticks
groove(kit, 'techno', t, 15); groove(kit, 'techno', t + 60, 1, fill=True)
subs(t, 16); dubs(t, 16, busy=True); ticks(t, 16); hats(t, 16)
clap.drums({60: '....x.......x...'}, at=t, bars=16, vel={'x': 80})
strings.chords('Cm9 Cm9 Abmaj7 Bb6 ' * 4, at=t, beats=4, style='pad', vel=64, lo=55, hi=70)
t += 64
# break (8): the transmission, the sweep, strings alone with the dub chord
voice.note(t + 2, 60, 6, 96)
sweep.note(t + 16, 60, 15, 80)
strings.chords('Cm9 Cm9 Abmaj7 Bb6 ' * 2, at=t, beats=4, style='pad', vel=70, lo=55, hi=70)
dubs(t, 8, 80)
hum.note(t, 54, 31, 70)
clicks(t + 16, 4, 62)
t += 32
# C (16): everything, the motor-whine lead
kit.note(t, CRASH, 1, 108)
groove(kit, 'techno', t, 15); groove(kit, 'techno', t + 60, 1, fill=True)
subs(t, 16, 104); dubs(t, 16, 88, busy=True); ticks(t, 16); hats(t, 16); clicks(t, 16, 60)
clap.drums({60: '....x.......x...'}, at=t, bars=16, vel={'x': 84})
strings.chords('Cm9 Cm9 Abmaj7 Bb6 ' * 4, at=t, beats=4, style='pad', vel=60, lo=55, hi=70)
for k in range(4):
    lead.mel(LEAD, at=t + 16 * k, vel=88)
t += 64
# outro (8)
groove(kit, 'techno', t, 4, drop=(CLAP,)); groove(kit, 'techno', t + 16, 4, drop=(CLAP, RIM, CHH))
subs(t, 4); dubs(t, 8, 78); hats(t, 4)
hum.note(t + 8, 54, 24, 72)
voice.note(t + 20, 60, 6, 80)
t += 32
kit.note(t, KICK, 1, 100); dub.note(t, pitch('C4'), 0.4, 86)

S.humanize(ms=2, vel=3, parts=['strings', 'lead'])
finish(__file__, S, {
    'title': 'Mission-Critical Repetition',
    'pack': 'techno-server',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Dub techno in C minor, 126 bpm: one-finger dub chords into a long echo, offbeat sub, Detroit strings, '
            'relay ticks, mains hum and a transmission from Apollo 8. Drums: Kit Manager 98 (Long Boom Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Long Boom Kit', dict(lufs=-16.5, verb=0.04)),
    ('sub', 'ch2', 'Dot Sub', dict(lufs=-19)),
    ('dub', 'ch3', 'One-Finger Dub Chord', dict(lufs=-21, pan=-10, echo=0.55, verb=0.25)),
    ('strings', 'ch4', 'Motor City Strings', dict(lufs=-24, pan=12, verb=0.35, width=1.3)),
    ('lead', 'ch5', 'Soft Pilot', dict(lufs=-22, pan=8, echo=0.35, verb=0.2)),
    ('hum', 'ch6', 'Dusk Texture', dict(lufs=-30, verb=0.2)),
    ('click', 'ch7', 'Coded Click', dict(lufs=-28, pan=-30, echo=0.2)),
    ('tick', 'ch8', 'Relay Wood Tick', dict(lufs=-28, pan=32, echo=0.25)),
    ('hat', 'ch9', 'Copper Hat', dict(lufs=-28, pan=18)),
    ('voice', 'ch11', 'Transmission Voice', dict(lufs=-22, echo=0.3, verb=0.3)),
    ('sweep', 'ch12', 'Rose Sweep', dict(lufs=-27, verb=0.4, width=1.4)),
    ('clap', 'ch13', 'Indigo Clap', dict(lufs=-26, pan=-6, verb=0.2)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.55, 'tone': 2400, 'level': -2, 'lowcut': 250},
   reverb={'size': 2.4, 'predelay': 20, 'tone': 4500, 'level': -6})

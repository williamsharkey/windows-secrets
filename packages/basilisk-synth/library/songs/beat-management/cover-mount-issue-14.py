"""Cover Mount (Issue 14): an original lo-fi boom-bap beat, 88 bpm, C minor / E-flat. Rain on the window, an upright
piano loop, upright bass, vibes, a flute hook, desk scratches and a choir at the end."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=88, seed=14)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
piano = S.part('piano', 3)
vibes = S.part('vibes', 4)
flute = S.part('flute', 5)
strings = S.part('strings', 6)
rain = S.part('rain', 7)
scratch = S.part('scratch', 8)
choir = S.part('choir', 9)
ep = S.part('ep', 11)

PROG = 'Ebmaj7 Dm7b5:2 G7:2 Cm7 Fm7:2 Bb7:2'
HOOK = 'q. G5 e Bb5 h G5 | q F5 e Eb5 D5 q. F5 e D5 | h. Eb5 q C5 | q. Ab5 e G5 q F5 D5'
SW = 0.22


def beat(at, bars, ghost=True):
    for k in range(bars):
        pads = {KICK: 'x......x..x.....' if k % 4 != 3 else 'x......x..x...x.', SNARE: '....x.......x...',
                CHH: 'x.x.x.x.x.x.x.x.' if k % 2 == 0 else 'x.x.x.x.x.x.x.xx'}
        if ghost:
            pads[RIM] = '.......o.....o..'
        kit.drums(pads, at=at + 4 * k, bars=1, swing=SW)


def piano_loop(at, bars, vel=70):
    for k in range(0, bars, 4):
        piano.chords(PROG, at=at + 4 * k, beats=4, style='block', vel=vel, lo=55, hi=72,
                     rhythm=[(0, 1.2), (1.5 + SW * 0.5, 0.6), (3.0, 0.8)])


def bassline(at, bars, vel=100):
    pat = [(0, 0, 1.0), (1.5 + SW * 0.5, '5', 0.4), (2, 0, 0.9), (3.5 + SW * 0.5, '8', 0.4)]
    for k in range(0, bars, 4):
        bass.bass(PROG, at=at + 4 * k, beats=4, pattern=pat, vel=vel)


def scratches(at):
    for i, (o, n) in enumerate(((0, 60), (0.5, 64), (0.75, 60), (1.0, 67))):
        scratch.note(at + o, n, 0.2, 92)


t = 0.0
rain.note(0, 60, 16, 90)
piano_loop(0, 4, 62)
t = 16
# A (16)
kit.note(t, CRASH, 2, 90)
beat(t, 16); bassline(t, 16); piano_loop(t, 16)
vibes.mel('h. G5 q r | w r | h. Eb5 q r | w r | h. Bb5 q r | w r | h. G5 q r | h r q F5 D5', at=t + 32, vel=70)
scratches(t + 30); scratches(t + 62)
rain.note(t, 60, 64, 70)
t += 64
# B (8): the flute hook, the violins under it
beat(t, 8); bassline(t, 8); piano_loop(t, 8, 62)
flute.mel(HOOK, at=t, vel=88, tr=-12); flute.mel(HOOK, at=t + 16, vel=92, tr=-12)
strings.chords('Ebmaj7 Dm7b5:2 G7:2 Cm7 Fm7:2 Bb7:2 ' * 2, at=t, beats=4, style='pad', vel=60, lo=55, hi=72)
scratches(t + 30)
t += 32
# A' (8): the EP takes the chords, vibes answer
beat(t, 8); bassline(t, 8)
ep.chords(PROG + ' ' + PROG, at=t, beats=4, style='block', vel=66, lo=55, hi=72,
          rhythm=[(0, 1.0), (1.75, 0.5), (2.5, 1.2)])
vibes.mel('q G5 e Bb5 G5 h F5 | w D5 | q Eb5 e G5 Eb5 h C5 | w D5 | '
          'q G5 e Bb5 G5 h F5 | w D5 | q Eb5 e G5 Bb5 h C6 | w Bb5', at=t, vel=72)
t += 32
# B' (8): everything, the choir
beat(t, 7); kit.drums({KICK: 'x.......x.......', SNARE: '....x...x.x.xxxx'}, at=t + 28, bars=1)
bassline(t, 8); piano_loop(t, 8, 64)
flute.mel(HOOK, at=t, vel=92, tr=-12); flute.mel(HOOK, at=t + 16, vel=96, tr=-12)
strings.chords('Ebmaj7 Dm7b5:2 G7:2 Cm7 Fm7:2 Bb7:2 ' * 2, at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
choir.chords('Ebmaj7 Dm7b5:2 G7:2 Cm7 Fm7:2 Bb7:2 ' * 2, at=t, beats=4, style='pad', vel=58, lo=52, hi=67)
scratches(t + 14); scratches(t + 30)
t += 32
# outro (4): the piano alone in the rain
piano_loop(t, 4, 58)
rain.note(t, 60, 18, 80)
t += 16
piano.chords('Ebmaj7:4', at=t, style='pad', vel=60, lo=55, hi=72)

S.humanize(ms=8, vel=6, parts=['piano', 'ep', 'vibes', 'flute', 'bass'])
finish(__file__, S, {
    'title': 'Cover Mount (Issue 14)',
    'pack': 'beat-management',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Lo-fi boom bap, 88 bpm, swung: rain on the window, upright-piano loop, upright bass, vibes, flute hook, '
            'violins, desk scratches, a choir at the end. Drums: Kit Manager 98 (Twelve-Bit Crate Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Twelve-Bit Crate Kit', dict(lufs=-17, verb=0.06)),
    ('bass', 'ch2', 'Upright Thump', dict(lufs=-19)),
    ('piano', 'ch3', 'Cedar Study', dict(lufs=-21, pan=-14, verb=0.25, lp=9000)),
    ('vibes', 'ch4', 'Study Vibes', dict(lufs=-23, pan=24, echo=0.2, verb=0.3)),
    ('flute', 'ch5', 'Civic Wire', dict(lufs=-20, pan=8, echo=0.25, verb=0.3)),
    ('strings', 'ch6', 'Golden Section', dict(lufs=-25, pan=-20, verb=0.35)),
    ('rain', 'ch7', 'Window Rain Room', dict(lufs=-31, width=1.4)),
    ('scratch', 'ch8', 'Desk Scratch', dict(lufs=-24, pan=-8)),
    ('choir', 'ch9', 'Winter Choir', dict(lufs=-26, verb=0.45, width=1.3)),
    ('ep', 'ch11', 'Wide Flick', dict(lufs=-22, pan=-10, echo=0.15, verb=0.25)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.3, 'tone': 2500, 'level': -5},
   reverb={'size': 1.5, 'predelay': 15, 'tone': 4500, 'level': -6})

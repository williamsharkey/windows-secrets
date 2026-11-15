"""Saturday on the Keyboard Floor: an original 1985 synth-pop song, 120 bpm, D minor / F. Big poly brass stabs, a
cream mono bass, FM piano and clav, a PWM lead, vocoder strings and choir, and a buzzy solo."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=120, seed=1985)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
brass = S.part('brass', 3)
fmpiano = S.part('fmpiano', 4)
clav = S.part('clav', 5)
lead = S.part('lead', 6)
solo = S.part('solo', 7)
vstrings = S.part('vstrings', 8)
vchoir = S.part('vchoir', 9)
pad = S.part('pad', 11)
ep = S.part('ep', 12)
female = S.part('female', 13)

V = 'Dm Bb F C'
CH = 'Bb C Dm Dm Bb C F A7'
VMEL = 'q. D5 e E5 q F5 A5 | h G5 q F5 D5 | q. C5 e D5 q F5 C6 | h. A5 q G5'
CMEL = 'h D6 q C6 Bb5 | h C6 q Bb5 A5 | q. A5 e G5 q F5 D5 | h. D5 q r | h D6 q C6 Bb5 | h E6 q D6 C6 | h. F6 q E6 | w C#6'
SOLO = ('e D5 F5 A5 D6 q C6 e A5 F5 | q G5 e Bb5 D6 h F6 | e F6 E6 D6 C6 q A5 e F5 A5 | h G5 q E5 C5 | '
        'e D5 F5 A5 D6 q E6 e D6 C6 | q D6 e Bb5 G5 h D5 | e C5 F5 A5 C6 q F6 e E6 D6 | h. E6 q r')


def drums(at, bars, fill=True):
    groove(kit, 'synthpop', at, bars, fill=fill, extra={CLAP: '....x.......x...'})


def eighths(at, prog, vel=96):
    bass.bass(prog, at=at, beats=4, pattern=[(i * 0.5, 0 if i not in (3, 7) else '8', 0.42) for i in range(8)], vel=vel)


def stabs(at, prog, vel=84):
    brass.chords(prog, at=at, beats=4, style='block', vel=vel, lo=57, hi=74,
                 rhythm=[(0, 0.4), (0.75, 0.3), (1.5, 0.4), (2.5, 0.4), (3.0, 0.3)])


def clavs(at, prog, vel=62):
    clav.chords(prog, at=at, beats=4, style='block', vel=vel, lo=60, hi=74,
                rhythm=[(0.5, 0.2), (1.25, 0.2), (2.5, 0.2), (3.25, 0.2), (3.75, 0.2)])


t = 0.0
# intro (8): the brass riff over the pad
pad.chords('Dm Bb F C Dm Bb F C', at=0, beats=4, style='pad', vel=58, lo=55, hi=72)
stabs(16, V, 80)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.'}, at=16, bars=4)
t = 32
# verse (16)
drums(t, 16); eighths(t, ' '.join([V] * 4))
fmpiano.chords(' '.join([V] * 4), at=t, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(0, 1.4), (2, 1.4)])
for k in range(4):
    lead.mel(VMEL, at=t + 16 * k, vel=88 + k * 2, tr=-12)
clavs(t + 32, ' '.join([V] * 2))
t += 64
# chorus (8): brass, vocoder strings and choir
kit.note(t, CRASH, 2, 112)
drums(t, 8); eighths(t, CH, 100); stabs(t, CH)
lead.mel(CMEL, at=t, vel=96, tr=-12); vchoir.mel(CMEL, at=t, vel=76, tr=-24)
vstrings.chords(CH, at=t, beats=4, style='pad', vel=64, lo=55, hi=72)
t += 32
# solo (8): the buzzy lead over the verse changes, the EP
drums(t, 8); eighths(t, V + ' ' + V)
solo.mel(SOLO, at=t, vel=96, tr=-12)
ep.chords(V + ' ' + V, at=t, beats=4, style='arp', vel=56, lo=60, hi=79, rhythm=0.25)
clavs(t, V + ' ' + V, 60)
pad.chords(V + ' ' + V, at=t, beats=4, style='pad', vel=52, lo=55, hi=72)
t += 32
# breakdown (4): vocoder female, the pad
female.mel('w F5 | w G5 | w A5 | w E5', at=t, vel=82, tr=-12)
pad.chords('Bb C Dm A7', at=t, beats=4, style='pad', vel=62, lo=55, hi=72)
kit.drums({SNARE: 'x...x...x...x...x.x.x.x.xxxxXXXX'}, at=t + 8, bars=2, vel={'x': 84, 'X': 104})
t += 16
# chorus x2 (16)
for k in range(2):
    kit.note(t, CRASH, 2, 114)
    drums(t, 8, fill=k == 0); eighths(t, CH, 102); stabs(t, CH, 88)
    lead.mel(CMEL, at=t, vel=98, tr=-12); vchoir.mel(CMEL, at=t, vel=78, tr=-24)
    vstrings.chords(CH, at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
    clavs(t, CH, 58)
    if k == 1:
        female.chords(CH, at=t, beats=4, style='pad', vel=58, lo=60, hi=74)
    t += 32
# end (2)
for p, v in ((brass, 92), (vstrings, 70), (pad, 60)):
    p.chords('Dm:8', at=t, style='pad', vel=v, lo=57, hi=74)
bass.note(t, pitch('D2'), 6, 100); kit.note(t, KICK, 1, 108); kit.note(t, CRASH, 3, 108)

S.humanize(ms=3, vel=3, parts=['lead', 'solo', 'fmpiano', 'female'])
finish(__file__, S, {
    'title': 'Saturday on the Keyboard Floor',
    'pack': 'polysynth-showroom',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': '1985 synth-pop in D minor, 120 bpm: poly brass stabs, a cream mono bass in eighths, FM piano and clav, '
            'a PWM lead, vocoder strings, male and female vocoder choirs, a buzzy solo, FM EP arpeggios. Drums: '
            'Kit Manager 98 (Breaker Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-17, verb=0.12)),
    ('bass', 'ch2', 'Ivory Low', dict(lufs=-19)),
    ('brass', 'ch3', 'Orbital Accent', dict(lufs=-20, pan=-8, verb=0.2, width=1.2)),
    ('fmpiano', 'ch4', 'Stone Parlour', dict(lufs=-23, pan=-20, verb=0.25)),
    ('clav', 'ch5', 'Paper Recital', dict(lufs=-25, pan=26)),
    ('lead', 'ch6', 'Silent Ray', dict(lufs=-19, pan=6, echo=0.2, verb=0.25)),
    ('solo', 'ch7', 'Wired Call', dict(lufs=-20, pan=-4, echo=0.25, verb=0.25)),
    ('vstrings', 'ch8', 'Foggy Section', dict(lufs=-24, pan=14, verb=0.35, width=1.3)),
    ('vchoir', 'ch9', 'Static Chorus', dict(lufs=-25, pan=-12, verb=0.4)),
    ('pad', 'ch11', 'Plaza Field', dict(lufs=-26, verb=0.35, width=1.3)),
    ('ep', 'ch12', 'Mild Chords', dict(lufs=-25, pan=30, echo=0.3, verb=0.2)),
    ('female', 'ch13', 'Rose Breath', dict(lufs=-23, pan=8, verb=0.4)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3500, 'level': -4},
   reverb={'size': 2.2, 'predelay': 18, 'tone': 6000, 'level': -5})

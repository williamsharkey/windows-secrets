"""Buffer Underrun Waltz: an original glitch waltz, 3/4 at 108 bpm, D minor. A slightly broken music box waltz
that drops beats where the buffer runs dry: stutters fill the gaps, the error bells chime, the helium choir stack
sings the second strain, floppy seeks keep the one."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=108, seed=9407)
box = S.part('musicbox', 1)
bells = S.part('bells', 2)
glock = S.part('glock', 3)
choir = S.part('choir', 4)
pad = S.part('pad', 5)
thud = S.part('thud', 6)
tick = S.part('tick', 7)
seek = S.part('seek', 8)
stut = S.part('stutter', 9)
clap = S.part('clap', 11)
ahh = S.part('ahh', 12)

A = 'Dm Dm A7 A7 Dm Dm Gm A7'
B = 'F F C C Bb Gm A7 Dm'
AMEL = 'h D5 q F5 | h A5 q F5 | h E5 q G5 | h. A5 | h F5 q D5 | h Bb5 q A5 | h G5 q E5 | h. C#5'
BMEL = 'h C6 q A5 | h F5 q A5 | h G5 q E5 | h. C5 | h D5 q F5 | h Bb5 q G5 | h A5 q C#5 | h. D5'
BAR = 3.0


def waltz(at, prog, drop=(), vel=64):
    prev = None
    for k, sy in enumerate(prog.split()):
        t = at + BAR * k
        if k in drop:   # the buffer runs dry: a stutter instead of the bar
            for i in range(12):
                stut.note(t + i * 0.25, 72 + (i % 3) * 7, 0.2, 86 - 3 * i)
            continue
        ns = voice_lead(prev, chord(sy, 4), 55, 67); prev = ns
        thud.note(t, 36, 0.4, 96)
        for off in (1, 2):
            for n in ns[:2]:
                glock.note(t + off, n + 12, 0.4, vel - 8)
            tick.note(t + off, 60, 0.2, 60)
        if k % 4 == 3:
            seek.note(t + 2, 46, 0.5, 80)


def melody(part, mel, at, drop=(), vel=86, tr=0):
    x = Part(S, 'tmp', 16)
    x.mel(mel, at=at, vel=vel, tr=tr)
    put(part, [n for n in x.notes if int((n[0] - at) // BAR) not in drop])


t = 0.0
melody(box, AMEL, 0, vel=80, tr=12)
pad.chords(A, at=0, beats=BAR, style='pad', vel=50, lo=52, hi=67)
t = 8 * BAR
waltz(t, A, drop=(3,)); melody(box, AMEL, t, drop=(3,), tr=12)
t += 8 * BAR
waltz(t, A, drop=(5,)); melody(box, AMEL, t, drop=(5,), tr=12); melody(bells, AMEL, t, drop=(5,), vel=62)
t += 8 * BAR
waltz(t, B, drop=(3, 7)); choir.chords(B, at=t, beats=BAR, style='pad', vel=60, lo=55, hi=69); melody(ahh, BMEL, t, drop=(3, 7), vel=84, tr=-12)
t += 8 * BAR
waltz(t, B); melody(box, BMEL, t, tr=12); clap.drums({60: '...x.x'}, at=t, bars=8, step=0.5, beats_per_bar=3.0, vel={'x': 70})
choir.chords(B, at=t, beats=BAR, style='pad', vel=56, lo=55, hi=69)
t += 8 * BAR
waltz(t, A, drop=(1, 3, 5)); melody(box, AMEL, t, drop=(1, 3, 5), tr=12); melody(bells, AMEL, t, vel=60)
t += 8 * BAR
waltz(t, A); melody(box, AMEL, t, tr=12); melody(ahh, AMEL, t, vel=80, tr=-12); pad.chords(A, at=t, beats=BAR, style='pad', vel=52, lo=52, hi=67)
t += 8 * BAR
box.mel('h. D6 | h. r', at=t, vel=82); bells.note(t, pitch('D6'), 4, 70)
for i in range(16):
    stut.note(t + 3 + i * 0.125, 74, 0.1, 80 - 4 * i)

S.humanize(ms=3, vel=4, parts=['musicbox', 'bells'])
finish(__file__, S, {
    'title': 'Buffer Underrun Waltz',
    'pack': 'diagnostics',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A glitch waltz in D minor, 3/4 at 108 bpm: a music-box waltz that drops whole bars where the buffer runs '
            'dry and stutters fill them, a molten glock on the off-beats, Noble Bell doubling, the helium choir stack '
            'and Bakelite Ahh on the second strain, thuds, ticks, a clap and floppy seeks.',
}, [
    ('musicbox', 'ch1', 'Broken Music Box', dict(lufs=-19, pan=-8, echo=0.25, verb=0.35)),
    ('bells', 'ch2', 'Noble Bell', dict(lufs=-24, pan=20, echo=0.3, verb=0.4)),
    ('glock', 'ch3', 'Amber Bells', dict(lufs=-25, pan=26, verb=0.3)),
    ('choir', 'ch4', 'Helium Choir Stack', dict(lufs=-25, verb=0.45)),
    ('pad', 'ch5', 'Copper Veil', dict(lufs=-26, verb=0.4, width=1.3)),
    ('thud', 'ch6', 'Glass Click', dict(lufs=-21)),
    ('tick', 'ch7', 'Violet Click', dict(lufs=-28, pan=-24)),
    ('seek', 'ch8', 'Floppy Seek Perc', dict(lufs=-25, pan=-26, echo=0.2)),
    ('stutter', 'ch9', 'Tinted Ascent', dict(lufs=-25, pan=16, echo=0.3)),
    ('clap', 'ch11', 'Coral Clap', dict(lufs=-26, pan=8, verb=0.2)),
    ('ahh', 'ch12', 'Bakelite Ahh', dict(lufs=-21, pan=4, verb=0.4)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 2.4, 'predelay': 20, 'tone': 5000, 'level': -4})

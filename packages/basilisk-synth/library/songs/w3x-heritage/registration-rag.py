"""Registration Rag: an original piano rag, 92 bpm, C major with a B strain in F. Every note comes from the six
Windows 3.1 sounds (DING, CHIMES, CHORD, TADA, RINGIN, RINGOUT): a ding piano with a stride left hand, chimes bells,
a ringout whistle and a tada fanfare."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=92, seed=1993)
rh = S.part('righthand', 1)
bass = S.part('stridebass', 2)
lh = S.part('stridechords', 3)
whistle = S.part('whistle', 4)
bells = S.part('bells', 5)
fanfare = S.part('fanfare', 6)
snare = S.part('snare', 7)
shaker = S.part('shaker', 8)
pad = S.part('pad', 9)
lead = S.part('lead', 11)

A_CH = 'C C G7 C C C7 F F#dim7 C/G A7 D7 G7 C A7 D7:2 G7:2 C'
A_MEL = ('e E5 G5 q C6 e E6 C6 q G5 | e A5 G5 E5 G5 h C5 | e B4 D5 q F5 e A5 G5 q F5 | e E5 D5 C5 D5 h E5 | '
         'e E5 G5 q C6 e E6 C6 q G5 | e Bb5 A5 G5 E5 h C5 | e A4 C5 q F5 e A5 G5 q F5 | e F#5 A5 C6 A5 h Eb5 | '
         'q. E5 e G5 q C6 E5 | e C#5 E5 G5 A5 q C#6 A5 | e D5 F#5 A5 C6 q F#5 D5 | e B4 D5 F5 G5 q B5 G5 | '
         'e E5 G5 q C6 e A5 G5 q E5 | e C#5 E5 q A5 e G5 E5 q C#5 | e D5 F#5 A5 F#5 G5 B5 D6 B5 | q C6 G5 h C5')
B_CH = 'F F C7 C7 C7 C7 F F F F7 Bb Bbm F/C D7 G7:2 C7:2 F'
B_MEL = ('e r A5 q A5 e C6 A5 q F5 | e G5 A5 G5 F5 h C5 | e r G5 q G5 e Bb5 G5 q E5 | e F5 G5 F5 E5 h C5 | '
         'e r Bb5 q Bb5 e D6 Bb5 q G5 | e A5 Bb5 A5 G5 h E5 | q F5 e A5 C6 q F6 C6 | h. A5 q r | '
         'e r A5 q A5 e C6 A5 q F5 | e Eb5 F5 A5 C6 h Eb6 | e D6 C6 Bb5 A5 q Bb5 F5 | e Db6 C6 Bb5 F5 h Db5 | '
         'q. C6 e A5 q F5 A5 | e F#5 A5 C6 D6 q C6 A5 | e G5 B5 D6 B5 Bb5 G5 E5 C5 | q A5 C6 h F5')


def stride(at, prog, vel=84):
    t, prev = at, None
    for sym in prog.split():
        b = 4.0
        if ':' in sym:
            sym, b = sym.split(':'); b = float(b)
        ns = voice_lead(prev, chord(sym, 4), 55, 67); prev = ns
        r = root_of(sym, 2)
        for off in range(0, int(b), 2):
            bass.note(t + off, r + (12 if off == 0 else 7 + 12 if r + 19 < 50 else 7), 0.8, vel)
            for n in ns:
                lh.note(t + off + 1, n, 0.6, vel - 16)
        t += b
    return t


def brushes(at, bars):
    snare.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 70})
    shaker.drums({60: 'x.x.x.x.x.x.x.x.'}, at=at, bars=bars, vel={'x': 54})


t = 0.0
# intro (4): a tada fanfare, the stride vamp
fanfare.mel('q C5 E5 G5 C6 | h. C6 q r', at=t, vel=88)
stride(t, 'C G7 C G7')
rh.mel('h. r e r G5 | e A5 G5 F#5 G5 h E5 | e r D5 E5 F5 G5 A5 B5 D6', at=t + 4, vel=80)
t = 16
# A strain (16)
rh.mel(A_MEL, at=t, vel=90); stride(t, A_CH); brushes(t + 32, 8)
bells.note(t + 60, pitch('C6'), 2, 70)
t += 64
# B strain (16): in F, the whistle doubles
rh.mel(B_MEL, at=t, vel=90); stride(t, B_CH); brushes(t, 16)
whistle.mel(B_MEL, at=t + 32, vel=78, tr=-12)
pad.chords(B_CH, at=t, beats=4, style='pad', vel=46, lo=53, hi=67)
fanfare.note(t + 28, pitch('C5'), 1, 80)
t += 64
# A strain again (16): the ringout lead takes it, bells on the downbeats
lead.mel(A_MEL, at=t, vel=88, tr=-12); rh.mel(A_MEL, at=t, vel=74); stride(t, A_CH, 88); brushes(t, 16)
for k in range(0, 16, 2):
    bells.note(t + 4 * k, pitch(['E6', 'G6', 'E6', 'F6', 'G6', 'A6', 'F6', 'C6'][k // 2]), 1.5, 64)
t += 64
# coda (4)
rh.mel('e G5 A5 G5 F#5 G5 E5 C5 E5 | e D5 F5 A5 G5 B5 D6 F6 D6 | q C6 e r G5 q C6 r | w C5+E5+G5+C6', at=t, vel=92)
stride(t, 'C G7 C:2 G7:2 C')
fanfare.mel('w r | w r | q C5 E5 G5 r | w C6', at=t, vel=92)
bells.note(t + 12, pitch('C6'), 3, 80)
snare.note(t + 10, 60, 0.4, 90)

S.humanize(ms=6, vel=5, parts=['righthand', 'whistle', 'lead'])
finish(__file__, S, {
    'title': 'Registration Rag',
    'pack': 'w3x-heritage',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A piano rag, 92 bpm: intro, A strain in C, B strain in F, A strain, coda. Every sound is one of the six '
            'that came with Windows 3.1: a ding piano with a stride left hand, chimes bells, a ringout whistle and '
            'lead, a tada fanfare, ding and ringin brushes.',
}, [
    ('righthand', 'ch1', 'Still Upright', dict(lufs=-19, pan=6, verb=0.25)),
    ('stridebass', 'ch2', 'Field Bass', dict(lufs=-21, pan=-10, verb=0.15)),
    ('stridechords', 'ch3', 'Western Chords', dict(lufs=-24, pan=-16, verb=0.2)),
    ('whistle', 'ch4', 'Gentle Whistle', dict(lufs=-22, pan=20, echo=0.15, verb=0.3)),
    ('bells', 'ch5', 'Urban Ring', dict(lufs=-25, pan=28, verb=0.4)),
    ('fanfare', 'ch6', 'Honey Hit', dict(lufs=-22, pan=-4, verb=0.35)),
    ('snare', 'ch7', 'Basement Snare', dict(lufs=-28, pan=10)),
    ('shaker', 'ch8', 'Hollow Shaker', dict(lufs=-31, pan=-24)),
    ('pad', 'ch9', 'Honey Haze', dict(lufs=-30, verb=0.4)),
    ('lead', 'ch11', 'Slate Pilot', dict(lufs=-21, pan=14, echo=0.15, verb=0.3)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 3000, 'level': -8},
   reverb={'size': 1.6, 'predelay': 15, 'tone': 5000, 'level': -6})

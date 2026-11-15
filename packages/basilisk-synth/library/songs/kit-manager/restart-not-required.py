"""Restart Not Required: an original drum-kit showcase, 116 bpm, C major. Kits take turns: rain-clock drops, a big
break, a half-time 808, a swing kit; the electromechanical kits play the tune on their tuned keys (the calculator's
FM register bell, the signal bells, the typing-pool bell) and a relay line."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *
chord_cap(8)   # rendered before render311 --lookahead: chords thinned to 8 recorders an instant (_lib.cap_chords)

S = Score(bpm=116, seed=98)
rain = S.part('rainclock', 1)
brk = S.part('bigbreak', 2)
h808 = S.part('halftime808', 3)
swing = S.part('swingpad', 4)
calc = S.part('calculator', 5)
bells = S.part('signalbells', 6)
typing = S.part('typingpool', 7)
relay = S.part('relayroom', 8)

MEL = ('q C5 E5 G5 e A5 G5 | h E5 q D5 C5 | q D5 E5 G5 e C6 A5 | w G5 | '
       'q A5 G5 E5 e D5 C5 | h D5 q E5 G5 | q A5 C6 e B5 A5 q G5 | w C5')
PROG = ['C', 'Am', 'F', 'G', 'Am', 'F', 'G', 'C']


def relay_line(at, bars, vel=90):
    for k in range(bars):
        r = pitch(PROG[k % 8] + '4') if PROG[k % 8] in ('C', 'F', 'G') else pitch('A4')
        r = r if r <= 72 else r - 12
        for off, iv in ((0, 0), (1.5, 0), (2, 7), (3, 12)):
            n = r + iv
            while n > 72:
                n -= 12
            relay.note(at + 4 * k + off, n, 0.4, vel - (0 if off == 0 else 10))


def bell_chords(at, bars, vel=66):
    prev = None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG[k % 8], 4), 60, 67); prev = ns
        ns = [n for n in ns if 60 <= n <= 67]   # the bells' lower tuned keys
        for n in ns:
            bells.note(at + 4 * k, n, 1.8, vel)
            bells.note(at + 4 * k + 2.5, n, 1.2, vel - 10)


def machine_perc(part, at, bars, pats):
    part.drums(pats, at=at, bars=bars, vel={'x': 84, 'o': 56, 'X': 104})


t = 0.0
# intro (4): the rain clock kit alone
rain.drums({KICK: 'x.......x.......', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.', 37: '...x.....x....x.'}, at=0, bars=4)
t = 16
# A (16): the big break, the relay line, the calculator's bell tune
groove(brk, 'breaks', t, 7, fill=False); groove(brk, 'breaks', t + 28, 1, fill=True)
groove(brk, 'breaks', t + 32, 7, fill=False); groove(brk, 'breaks', t + 60, 1, fill=True)
relay_line(t, 16)
calc.mel(MEL, at=t + 32, vel=92)
machine_perc(calc, t, 8, {36: 'x...............', 40: '......x.......x.', 44: '..o...o...o...o.'})
t += 64
# B (8): the half-time 808, the signal bells, the typing pool
groove(h808, 'halftime', t, 7, extra={CLAP: '........x.......'}); groove(h808, 'halftime', t + 28, 1, fill=True)
bell_chords(t, 8)
machine_perc(typing, t, 8, {36: 'x.....x...x.....', 38: '....x.......x...', 42: 'xxxxxxxxxxxxxxxx'})
typing.mel('h. r q r | h. E5 q D5 | h. r q r | h G5 E5 | h. r q r | h. D5 q C5 | h. r q r | w G5', at=t, vel=84)
t += 32
# C (8): the swing kit, the tune again on the calculator, the bells answer
groove(swing, 'boombap', t, 7, swing=0.25); groove(swing, 'boombap', t + 28, 1, fill=True)
calc.mel(MEL, at=t, vel=94)
bells.mel('h. r q E5 | h. r q G5 | h. r q E5 | h. r q D5 | h. r q E5 | h. r q F5 | h. r q D5 | w E5', at=t, vel=70)
relay_line(t, 8, 84)
t += 32
# D (16): everything at once, every kit
for k in range(2):
    groove(brk, 'breaks', t + 32 * k, 7); groove(brk, 'breaks', t + 32 * k + 28, 1, fill=True)
    groove(h808, 'halftime', t + 32 * k, 8, drop=(CHH,))
    groove(swing, 'house_lite', t + 32 * k, 8, drop=(KICK,))
    machine_perc(typing, t + 32 * k, 8, {42: 'x.x.x.x.x.x.x.x.'})
    calc.mel(MEL, at=t + 32 * k, vel=96)
    bell_chords(t + 32 * k, 8, 62)
    relay_line(t + 32 * k, 8, 92)
typing.mel('w r | w r | w r | w r | w r | w r | w r | w r | '
           'h. E5 q D5 | h C5 G5 | h. A5 q G5 | w E5 | h. F5 q E5 | h D5 E5 | h. F5 q D5 | w C5', at=t, vel=80)
t += 64
# outro (4): the rain clock, the last bell
rain.drums({KICK: 'x.......x.......', CHH: 'x.x.x.x.x.x.x.x.', 37: '...x.....x....x.'}, at=t, bars=3)
calc.mel('q C5 E5 G5 C6 | w C6', at=t + 8, vel=88)
bells.chords('C:8', at=t + 12, style='pad', vel=70, lo=60, hi=67)
t += 16
rain.note(t + 4, KICK, 1, 100)

finish(__file__, S, {
    'title': 'Restart Not Required',
    'pack': 'kit-manager',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A drum-kit showcase in C major, 116 bpm, eight kits: Rain Clock, Breaker Box, Half-Time and Twelve-Bit Crate '
            'take turns; Calculator Bureau, Signal Bells and Typing Pool play the tune and chords on their tuned keys, '
            'Relay Room plays a relay line. Every sound is a Kit Manager 98 kit.',
}, [
    ('rainclock', 'ch1', 'Rain Clock Kit', dict(lufs=-19, verb=0.2)),
    ('bigbreak', 'ch2', 'Breaker Box Kit', dict(lufs=-17, verb=0.06)),
    ('halftime808', 'ch3', 'Half-Time Kit', dict(lufs=-18, verb=0.08)),
    ('swingpad', 'ch4', 'Twelve-Bit Crate Kit', dict(lufs=-19, pan=-10, verb=0.08)),
    ('calculator', 'ch5', 'Calculator Bureau', dict(lufs=-19, pan=8, echo=0.2, verb=0.3)),
    ('signalbells', 'ch6', 'Signal Bells', dict(lufs=-23, pan=-22, echo=0.2, verb=0.35)),
    ('typingpool', 'ch7', 'Typing Pool', dict(lufs=-23, pan=26, echo=0.15, verb=0.25)),
    ('relayroom', 'ch8', 'Relay Room', dict(lufs=-22, pan=-4, verb=0.15)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -5},
   reverb={'size': 1.8, 'predelay': 15, 'tone': 5500, 'level': -6})

"""Uninstall Complete: an original drum-and-bass kit showcase, 172 bpm, A minor. Breaks on three kits in turn, the
mainframe hall's tuned keys on the bass line, the teletype's tuned keys on the tune, the message center's bells
above, a line printer and a card punch in the breakdown."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=172, seed=98)
breaker = S.part('breakerbox', 1)
noise = S.part('noisechannel', 2)
twelve = S.part('twelvebit', 3)
mainframe = S.part('mainframe', 4)
teletype = S.part('teletype', 5)
message = S.part('message', 6)
card = S.part('cardroom', 7)
echo_ = S.part('echochamber', 8)

PROG = ['Am', 'F', 'C', 'G']
TUNE = 'h E5 C5 | q D5 E5 h C5 | h. A4 q C5 | w B4 | h E5 G5 | q F5 E5 h D5 | h. C5 q B4 | w A4'
BASSL = {'Am': [69, 69, 64, 67], 'F': [65, 65, 69, 72], 'C': [72, 67, 64, 67], 'G': [67, 71, 67, 62]}
VARS = [{KICK: 'x.........x.....', SNARE: '....x..o.o..x...', CHH: 'x.xxx.x.x.xxx.x.'},
        {KICK: 'x.........xx....', SNARE: '....x..o....x..o', CHH: 'x.x.x.xxx.x.x.xx'},
        {KICK: 'x..x......x.....', SNARE: '....x.o..o..x.o.', CHH: 'xxx.x.x.xxx.x.x.'},
        {KICK: 'x.........x.....', SNARE: '....x..x.x..xxXX', CHH: 'x.x.x.x.x.x.....'}]


ARP = {'Am': (72, 76, 79, 76), 'F': (72, 77, 72, 77), 'C': (72, 76, 79, 76), 'G': (74, 79, 74, 79)}


def tune(at, vel):
    """the tune folded into the teletype's tuned keys (72-84)"""
    x = Part(S, 'tmp', 16)
    x.mel(TUNE, at=at, vel=vel)
    put(teletype, x.notes, lo=72, hi=84)


def breaks(kit, at, bars):
    for k in range(bars):
        kit.drums(VARS[k % 4], at=at + 4 * k, bars=1)


def bassline(at, bars, vel=96):
    for k in range(bars):
        notes = BASSL[PROG[k % 4]]
        for i, n in enumerate(notes):
            n2 = n - 12 if n > 71 else n   # the hall's lower tuned octave: 60-71
            mainframe.note(at + 4 * k + i, n2, 0.9, vel - (0 if i == 0 else 10))


t = 0.0
echo_.drums({KICK: 'x.......x.......', CHH: 'x.x.x.x.x.x.x.x.'}, at=0, bars=4)
message.mel('w A6 | w F6 | w C7 | w B6', at=0, vel=70)
t = 16
breaks(breaker, t, 16); bassline(t, 16)
tune(t + 32, 92)
t += 64
breaks(noise, t, 16); bassline(t, 16)
tune(t, 94); tune(t + 32, 96)
message.mel('w A6 | w F6 | w C7 | w B6 | w A6 | w F6 | w E6 | w E6', at=t + 32, vel=64)
t += 64
# breakdown: half time on the echo chamber kit, the card room's tuned keys arpeggiate, a line printer
echo_.drums({KICK: 'x...............', SNARE: '........x.......', CHH: 'x.x.x.x.x.x.x.x.'}, at=t, bars=7)
echo_.drums({SNARE: 'x.x.x.x.xxxxxxxx'}, at=t + 28, bars=1)
for k in range(8):
    for i, n in enumerate(ARP[PROG[k % 4]]):
        card.note(t + 4 * k + i, n, 0.9, 74)
bassline(t, 8, 84)
t += 32
breaks(twelve, t, 16); breaks(breaker, t + 32, 8); bassline(t, 16, 100)
tune(t, 96); tune(t + 32, 98)
message.mel('w A6 | w F6 | w C7 | w B6 | w A6 | w F6 | w E6 | w E6', at=t, vel=66)
t += 64
# the last run: the echo chamber and breaker box together, the card room under the tune
breaks(echo_, t, 16); breaks(breaker, t, 16); bassline(t, 16, 100)
tune(t, 98); tune(t + 32, 98)
for k in range(16):
    for i, n in enumerate(ARP[PROG[k % 4]]):
        card.note(t + 4 * k + i, n, 0.9, 64)
t += 64
teletype.mel('h E5 C6 | w A5', at=t, vel=96); mainframe.note(t, 69, 6, 98)
breaker.note(t, KICK, 1, 110); breaker.note(t, CRASH, 3, 110)

finish(__file__, S, {
    'title': 'Uninstall Complete',
    'pack': 'kit-manager',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Drum and bass at 172 bpm, all on Kit Manager 98: breaks on the Breaker Box, Noise Channel and '
            'Twelve-Bit Crate kits, the bass line on Mainframe Hall\'s tuned keys, the tune on Teletype 33\'s, bells '
            'on Message Center, a Card Room arpeggio and the Echo Chamber kit in the breakdown.',
}, [
    ('breakerbox', 'ch1', 'Breaker Box Kit', dict(lufs=-17, verb=0.05)),
    ('noisechannel', 'ch2', 'Noise Channel Kit', dict(lufs=-18, verb=0.05)),
    ('twelvebit', 'ch3', 'Twelve-Bit Crate Kit', dict(lufs=-18, verb=0.05)),
    ('mainframe', 'ch4', 'Mainframe Hall', dict(lufs=-19, verb=0.1)),
    ('teletype', 'ch5', 'Teletype 33', dict(lufs=-20, pan=8, echo=0.2, verb=0.25)),
    ('message', 'ch6', 'Message Center', dict(lufs=-25, pan=-24, echo=0.3, verb=0.4)),
    ('cardroom', 'ch7', 'Card Room', dict(lufs=-23, pan=24, echo=0.2, verb=0.3)),
    ('echochamber', 'ch8', 'Echo Chamber Kit', dict(lufs=-19, verb=0.2)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 3500, 'level': -5},
   reverb={'size': 1.8, 'predelay': 15, 'tone': 5500, 'level': -6})

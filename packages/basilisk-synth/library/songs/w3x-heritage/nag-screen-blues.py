"""Nag Screen Blues: an original 12-bar shuffle blues, 96 bpm, G, on the six Windows 3.1 sounds: a ding piano
with a walking bass, ding chords on the off-beats, a ringout whistle and a tada horn trading choruses, chimes on
the turnarounds."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=96, seed=31)
piano = S.part('piano', 1)
bass = S.part('bass', 2)
comp = S.part('comp', 3)
whistle = S.part('whistle', 4)
horn = S.part('horn', 5)
bells = S.part('bells', 6)
snare = S.part('snare', 7)
shaker = S.part('shaker', 8)
lead = S.part('lead', 9)

BLUES = 'G7 C7 G7 G7 C7 C7 G7 G7 D7 C7 G7 D7'
SW = 0.33
WHISTLE = ('e. G5 s Bb5 q B5 h G5 | h. r q r | e. G5 s Bb5 q B5 e D6 B5 q G5 | h. r q r | '
           'e. C6 s D6 q Eb6 h C6 | q Bb5 G5 h r | e. G5 s Bb5 q B5 h D6 | h. r q r | '
           'q A5 C6 D6 F6 | q E6 D6 C6 Bb5 | w G5 | h. r q D5')
HORN = ('q D5 F5 G5 r | e Bb5 A5 G5 F5 h G5 | q D5 F5 G5 Bb5 | h. G5 q r | q F5 Ab5 Bb5 r | e C6 Bb5 Ab5 G5 h F5 | '
        'q D5 F5 G5 Bb5 | h. G5 q r | q A5 F#5 A5 C6 | q Bb5 G5 E5 G5 | w G5 | h F#5 A5')


def walk(at):
    for k, sy in enumerate(BLUES.split()):
        r = root_of(sy, 2) + 12
        line = [r, r + 4, r + 7, r + 9] if k % 2 == 0 else [r + 10, r + 9, r + 7, r + 4]
        for i, n in enumerate(line):
            bass.note(at + 4 * k + i, n, 0.85, 92 - (0 if i == 0 else 8))


def comp_(at, vel=62):
    prev = None
    for k, sy in enumerate(BLUES.split()):
        ns = voice_lead(prev, chord(sy, 4), 55, 67); prev = ns
        for off in (1 + SW * 0.5, 3 + SW * 0.5):
            for n in ns:
                comp.note(at + 4 * k + off, n, 0.4, vel)


def drums(at):
    snare.drums({60: '....x.......x...'}, at=at, bars=12, vel={'x': 70})
    shaker.drums({60: 'x.x.x.x.x.x.x.x.'}, at=at, bars=12, vel={'x': 52}, swing=SW)


def piano_riff(at, vel=84):
    for k, sy in enumerate(BLUES.split()):
        r = root_of(sy, 4)
        for off, iv in ((0, 0), (0.5 + SW * 0.25, 4), (1, 7), (1.5 + SW * 0.25, 9), (2, 10), (2.5 + SW * 0.25, 9), (3, 7), (3.5 + SW * 0.25, 4)):
            piano.note(at + 4 * k + off, r + iv, 0.4, vel - (0 if off == 0 else 10))


t = 0.0
# intro: the last four bars on the piano, a chimes bell
piano.mel('q D5 F5 G5 Bb5 | q B5 G5 F5 D5 | w G5 | h F#5 A5', at=0, vel=84)
bass.mel('q D3 F#3 A3 C4 | q C3 E3 G3 Bb3 | q G2 B2 D3 F3 | q D3 F#3 A3 C4', at=0, vel=90)
bells.note(12, pitch('D6'), 2, 70)
t = 16
# chorus 1: the piano boogie, the walking bass
piano_riff(t); walk(t); drums(t)
t += 48
# chorus 2: the whistle sings it
whistle.mel(WHISTLE, at=t, vel=88, tr=-12); walk(t); comp_(t); drums(t)
bells.note(t + 44, pitch('G6'), 2, 64)
t += 48
# chorus 3: the tada horn answers
horn.mel(HORN, at=t, vel=92, tr=-12); walk(t); comp_(t, 58); drums(t)
t += 48
# chorus 4: everyone, the ringout lead on the whistle's tune, the boogie under it
lead.mel(WHISTLE, at=t, vel=90, tr=-12); piano_riff(t, 74); walk(t); comp_(t, 56); drums(t)
bells.note(t + 40, pitch('G6'), 2, 70)
t += 48
# ending: the classic tag
piano.mel('e G5 F#5 F5 E5 Eb5 D5 Db5 C5 | h. G4+B4+F5 q r', at=t, vel=88)
bass.mel('h G2 Db3 | h. G2 q r', at=t, vel=94)
horn.note(t + 4, pitch('G4'), 3, 84); bells.note(t + 4, pitch('G6'), 3, 72)

S.humanize(ms=6, vel=5)
finish(__file__, S, {
    'title': 'Nag Screen Blues',
    'pack': 'w3x-heritage',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A 12-bar shuffle blues in G, 96 bpm, four choruses: ding piano boogie and walking ding bass, ding chords on '
            'the off-beats, the ringout whistle and the tada horn trading choruses, chimes on the turnarounds. Only the '
            'six Windows 3.1 sounds.',
}, [
    ('piano', 'ch1', 'Still Upright', dict(lufs=-20, pan=6, verb=0.25)),
    ('bass', 'ch2', 'Field Bass', dict(lufs=-20, pan=-8, verb=0.15)),
    ('comp', 'ch3', 'Western Chords', dict(lufs=-25, pan=-18, verb=0.2)),
    ('whistle', 'ch4', 'Gentle Whistle', dict(lufs=-20, pan=14, echo=0.15, verb=0.3)),
    ('horn', 'ch5', 'Indigo Wire', dict(lufs=-20, pan=-12, verb=0.3)),
    ('bells', 'ch6', 'Urban Ring', dict(lufs=-25, pan=28, verb=0.4)),
    ('snare', 'ch7', 'Basement Snare', dict(lufs=-28, pan=10)),
    ('shaker', 'ch8', 'Hollow Shaker', dict(lufs=-31, pan=-24)),
    ('lead', 'ch9', 'Slate Pilot', dict(lufs=-21, pan=4, echo=0.15, verb=0.3)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.2, 'tone': 3000, 'level': -9},
   reverb={'size': 1.6, 'predelay': 15, 'tone': 5000, 'level': -6})

"""Sixteen Colours at Sunset: an original synthwave track, 100 bpm, E minor. Gated drums, octave bass in eighths,
a chrome lead, brass swells, a kalimba arpeggio and a rooftop sax solo."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=100, seed=1985)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
ep = S.part('ep', 3)
arp = S.part('arp', 4)
lead = S.part('lead', 5)
sax = S.part('sax', 6)
brass = S.part('brass', 7)
pad = S.part('pad', 8)
sweep = S.part('sweep', 9)
snare2 = S.part('snare2', 11)
orch = S.part('orch', 12)

PROG = 'Em C G D'
VERSE = 'q. B4 e A4 q G4 E4 | h. G4 q A4 | q. B4 e D5 q E5 D5 | h. A4 q r'
CHORUS = 'h E5 q D5 B4 | h C5 q. B4 e A4 | h G5 q F#5 D5 | w F#5'
SOLO = ('e E5 F#5 G5 B5 q A5 G5 | e E5 D5 E5 G5 h E5 | e D5 E5 G5 A5 q B5 D6 | h. B5 e A5 G5 | '
        'q F#5 e E5 D5 q E5 G5 | h E5 q. D5 e B4 | q D5 G5 B5 A5 | w F#5')


def drums(at, bars, fill=True):
    groove(kit, 'synthpop', at, bars, fill=fill)
    snare2.drums({60: '....x.......x...'}, at=at, bars=bars, vel={'x': 90})


def octaves(at, bars, vel=96):
    pat = [(i * 0.5, 0 if i % 2 == 0 else '8', 0.4) for i in range(8)]
    bass.bass(' '.join([PROG] * (bars // 4)), at=at, beats=4, pattern=pat, vel=vel)


def arp16(at, bars, vel=62):
    t, prev = at, None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG.split()[k % 4], 4), 64, 79); prev = ns
        seq = [ns[0], ns[1], ns[2], ns[1]]
        for i in range(16):
            arp.note(t + i * 0.25, seq[i % 4] + (12 if i >= 8 else 0), 0.2, vel - (0 if i % 4 == 0 else 8))
        t += 4


t = 0.0
# intro (8)
pad.chords(' '.join([PROG] * 2), at=0, beats=4, style='pad', vel=60, lo=52, hi=71)
arp16(16, 4, 54)
sweep.note(0, 60, 8, 80); sweep.note(28, 60, 4, 84)
t = 32
# verse (16)
orch.note(t, 64, 1.5, 96)
drums(t, 16); octaves(t, 16)
ep.chords(' '.join([PROG] * 4), at=t, beats=4, style='block', vel=64, lo=55, hi=72,
          rhythm=[(0, 0.9), (1.5, 0.4), (2.5, 0.9)])
for k in range(4):
    lead.mel(VERSE, at=t + 16 * k, vel=86 if k < 2 else 92)
arp16(t + 32, 8, 54)
t += 64
# chorus (8): brass swells
drums(t, 8); octaves(t, 8, 100); arp16(t, 8, 58)
brass.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=74, lo=55, hi=72)
lead.mel(CHORUS, at=t, vel=96); lead.mel(CHORUS, at=t + 16, vel=98)
pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=54, lo=52, hi=71)
t += 32
# sax solo (8)
drums(t, 8); octaves(t, 8); arp16(t, 8, 52)
ep.chords(' '.join([PROG] * 2), at=t, beats=4, style='block', vel=60, lo=55, hi=72, rhythm=[(0, 0.9), (2.5, 0.9)])
sax.mel(SOLO, at=t, vel=96, tr=-12)
pad.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=54, lo=52, hi=71)
t += 32
# last chorus (8), the sax doubling
orch.note(t, 64, 1.5, 100); sweep.note(t - 4, 60, 4, 84)
drums(t, 8); octaves(t, 8, 102); arp16(t, 8, 60)
brass.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=78, lo=55, hi=72)
lead.mel(CHORUS, at=t, vel=98); lead.mel(CHORUS, at=t + 16, vel=100)
sax.mel(CHORUS, at=t + 16, vel=80, tr=-12)
t += 32
# outro (8)
drums(t, 4, fill=False)
octaves(t, 4, 90); arp16(t, 8, 50)
pad.chords('Em C G D Em:16', at=t, beats=4, style='pad', vel=58, lo=52, hi=71)
lead.mel(VERSE, at=t, vel=80)
t += 32
orch.note(t, 64, 2, 96); kit.note(t, KICK, 1, 100); kit.note(t, CRASH, 2, 100)

S.humanize(ms=3, vel=4, parts=['ep', 'lead', 'sax'])
finish(__file__, S, {
    'title': 'Sixteen Colours at Sunset',
    'pack': 'retro-display',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Synthwave in E minor, 100 bpm: gated drums, octave bass in eighths, tine EP, chrome lead, brass swells, '
            'a kalimba arpeggio, a sax solo. Drums: Kit Manager 98 (Echo Chamber Kit) with the pack\'s Yellow Snare.',
}, [
    ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', dict(lufs=-17, verb=0.12)),
    ('bass', 'ch2', 'Saffron Rumble', dict(lufs=-19)),
    ('ep', 'ch3', 'Shiny Tine Plaza', dict(lufs=-23, pan=-18, echo=0.15, verb=0.25)),
    ('arp', 'ch4', 'Violet Chords', dict(lufs=-25, pan=22, echo=0.3, verb=0.2)),
    ('lead', 'ch5', 'Chrome Brass Lead', dict(lufs=-20, pan=4, echo=0.25, verb=0.3)),
    ('sax', 'ch6', 'Rooftop Sax Lead', dict(lufs=-20, pan=-6, echo=0.2, verb=0.35)),
    ('brass', 'ch7', 'Digital Swell', dict(lufs=-23, pan=10, verb=0.3, width=1.3)),
    ('pad', 'ch8', 'Northern Bloom', dict(lufs=-26, verb=0.4, width=1.4)),
    ('sweep', 'ch9', 'Laser Grid Sweep', dict(lufs=-26, verb=0.4)),
    ('snare2', 'ch11', 'Yellow Snare', dict(lufs=-26, verb=0.4)),
    ('orch', 'ch12', 'Waxed Orchestra', dict(lufs=-23, verb=0.4)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.38, 'tone': 3200, 'level': -3},
   reverb={'size': 2.6, 'predelay': 18, 'tone': 5500, 'level': -5})

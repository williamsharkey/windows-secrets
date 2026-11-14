"""Postcard to the Ceiling: an original uplifting trance track, 138 bpm, A minor. A rolling offbeat bass, sixteenth
plucks, a piano breakdown and the hands-in-the-air lead."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=138, seed=1999)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
pluck = S.part('pluck', 3)
lead = S.part('lead', 4)
pad = S.part('pad', 5)
brass = S.part('brass', 6)
piano = S.part('piano', 7)
riser = S.part('riser', 8)
burst = S.part('burst', 9)
plink = S.part('plink', 11)

PROG = 'Am F C G'
ANTHEM = ('q E5 e E5 A5 q G5 E5 | q. C5 e D5 h E5 | q E5 e E5 G5 q A5 G5 | h. D5 q B4 | '
          'q E5 e E5 A5 q B5 C6 | q. A5 e G5 h A5 | q G5 E5 G5 C6 | w B5')
ROLL = [(b + o, 0, 0.2) for b in range(4) for o in (0.25, 0.5, 0.75)]


def arp16(part, at, bars, vel=74, lo=60, hi=77, prog=PROG):
    t, prev = at, None
    for k in range(bars):
        sym = prog.split()[k % 4]
        ns = voice_lead(prev, chord(sym, 4), lo, hi); prev = ns
        seq = [ns[0], ns[1], ns[2], ns[0] + 12, ns[2], ns[1]]
        for i in range(16):
            part.note(t + i * 0.25, seq[i % len(seq)], 0.22, vel - (0 if i % 4 == 0 else 10))
        t += 4


def roll(at, bars, vel=100):
    bass.bass(' '.join([PROG] * (bars // 4)), at=at, beats=4, pattern=ROLL, vel=vel)


t = 0.0
# intro (8): kick, plinks, a riser
groove(kit, 'trance', 0, 8, drop=(CHH, CLAP))
plink.drums({69: 'x..x..x.x..x..x.'}, at=0, bars=8, vel={'x': 70})
riser.note(16, 60, 15.5, 80)
t = 32
# build (16): the roll, the plucks, the claps
groove(kit, 'trance', t, 15); groove(kit, 'trance', t + 60, 1, fill=True)
roll(t, 16); arp16(pluck, t, 16, 70)
pad.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
burst.note(t, 60, 6, 90)
t += 64
# breakdown (16): piano and pad; the riser and a snare roll into the drop
piano.mel(ANTHEM, at=t, vel=82)
piano.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=58, lo=48, hi=64)
piano.mel(ANTHEM, at=t + 32, vel=88)
pad.chords(' '.join([PROG] * 4), at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
arp16(pluck, t + 32, 8, 58)
riser.note(t + 32, 60, 31.5, 86)
kit.drums({SNARE: 'x...x...x...x...'}, at=t + 48, bars=4, vel={'x': 62})
kit.drums({SNARE: 'x.x.x.x.x.x.x.x.'}, at=t + 56, bars=1, vel={'x': 76})
kit.drums({SNARE: 'xxxxxxxxxxxxxxxx'}, at=t + 60, bars=1, vel={'x': 94})
t += 64
# drop (24): the lead, the brass chords, everything
kit.note(t, CRASH, 1.5, 116); burst.note(t, 60, 6, 96)
groove(kit, 'trance', t, 23); groove(kit, 'trance', t + 92, 1, fill=True)
roll(t, 24, 104); arp16(pluck, t, 24, 68)
for k in range(3):
    lead.mel(ANTHEM, at=t + 32 * k, vel=96 if k != 1 else 90, tr=-12)
brass.chords(' '.join([PROG] * 6), at=t, beats=4, style='block', vel=74, lo=55, hi=72,
             rhythm=[(0, 0.7), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)])
pad.chords(' '.join([PROG] * 6), at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
piano.mel(ANTHEM, at=t + 64, vel=72)
t += 96
# outro (8)
groove(kit, 'trance', t, 4); groove(kit, 'trance', t + 16, 4, drop=(CHH, CLAP))
roll(t, 4, 96); arp16(pluck, t, 8, 60)
plink.drums({69: 'x..x..x.x..x..x.'}, at=t, bars=8, vel={'x': 64})
pad.chords('Am F C G Am:16', at=t, beats=4, style='pad', vel=54, lo=55, hi=72)
t += 32
kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 2, 96)

S.humanize(ms=2, vel=3, parts=['piano', 'lead', 'pad'])
finish(__file__, S, {
    'title': 'Postcard to the Ceiling',
    'pack': 'trance-connectivity',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Uplifting trance in A minor, 138 bpm: rolling offbeat bass, sixteenth plucks, a piano breakdown, the lead '
            'and brass chords on the drop. Drums: Kit Manager 98 (Punch Kick Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Punch Kick Kit', dict(lufs=-16, verb=0.05)),
    ('bass', 'ch2', 'Waxed Weight', dict(lufs=-19)),
    ('pluck', 'ch3', 'Echo Pluck 138', dict(lufs=-23, pan=-18, echo=0.3, verb=0.2)),
    ('lead', 'ch4', 'Neon Solo', dict(lufs=-19, pan=4, echo=0.25, verb=0.3)),
    ('pad', 'ch5', 'Grey Mist', dict(lufs=-25, verb=0.4, width=1.4)),
    ('brass', 'ch6', 'Paper Brass', dict(lufs=-23, pan=14, verb=0.25)),
    ('piano', 'ch7', 'Breakdown Grand', dict(lufs=-20, pan=-4, echo=0.15, verb=0.45)),
    ('riser', 'ch8', 'Midnight Riser', dict(lufs=-25, verb=0.4)),
    ('burst', 'ch9', 'Dusk Burst', dict(lufs=-24, verb=0.5)),
    ('plink', 'ch11', 'Signal Plink', dict(lufs=-26, pan=30, echo=0.35)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.4, 'tone': 3500, 'level': -3},
   reverb={'size': 2.8, 'predelay': 22, 'tone': 6000, 'level': -5})

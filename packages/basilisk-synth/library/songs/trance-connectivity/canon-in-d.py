"""Canon in D (Johann Pachelbel, c. 1680), arranged for the Trance Connectivity Kit: the ground bass rolling on the
offbeat, the canon's famous variations climbing from the piano breakdown to the hands-in-the-air lead, sixteenth
plucks and brass chords."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=136, seed=1680)
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
strings = S.part('strings', 12)

GROUND = 'D A Bm F#m G D G A'          # one chord a bar here (two beats each in the original)
# the canon's opening variations (one bar per chord); V4 is the arranger's own eighth-note division on the ground
V1 = 'w F#5 | w E5 | w D5 | w C#5 | w B4 | w A4 | w B4 | w C#5'
V2 = 'h D5 C#5 | h B4 A4 | h G4 F#4 | h G4 E4 | h D4 F#4 | h A4 G4 | h F#4 D4 | h F#4 E4'
V3 = 'q D4 F#4 A4 G4 | q F#4 D4 F#4 E4 | q D4 B3 D4 A4 | q G4 B4 A4 G4 | q F#4 D4 E4 C#5 | q D5 F#5 A5 A4 | q B4 G4 A4 F#4 | q D4 D5 D5 C#5'
V4 = ('e D5 C#5 D5 D4 C#4 A4 E4 F#4 | e D4 D5 C#5 B4 C#5 F#5 A5 B5 | e G5 F#5 E5 G5 F#5 E5 D5 C#5 | e B4 A4 G4 F#4 E4 G4 F#4 E4 | '
      'e D4 E4 F#4 G4 A4 E4 A4 G4 | e F#4 B4 A4 G4 A4 G4 F#4 E4 | e D4 B3 B4 C#5 D5 C#5 B4 A4 | e G4 F#4 E4 B4 A4 B4 A4 G4')
ROLL = [(b + o, 0, 0.2) for b in range(4) for o in (0.25, 0.5, 0.75)]


def arp16(at, reps, vel=68):
    t, prev = at, None
    for k in range(8 * reps):
        ns = voice_lead(prev, chord(GROUND.split()[k % 8], 4), 62, 78); prev = ns
        seq = [ns[0], ns[1], ns[2], ns[0] + 12, ns[2], ns[1]]
        for i in range(16):
            pluck.note(t + i * 0.25, seq[i % 6], 0.22, vel - (0 if i % 4 == 0 else 10))
        t += 4


def roll(at, reps, vel=100):
    bass.bass(' '.join([GROUND] * reps), at=at, beats=4, pattern=ROLL, vel=vel)


t = 0.0
# intro (8): the ground on the plinks, kick
groove(kit, 'trance', 0, 8, drop=(CHH, CLAP))
plink.mel(' '.join('w ' + n for n in 'D5 A4 B4 F#4 G4 D4 G4 A4'.split()), at=0, vel=64)
riser.note(16, 60, 15.5, 80)
t = 32
# build (16): the roll, V1 on strings, V2 on the lead, plucks
groove(kit, 'trance', t, 15); groove(kit, 'trance', t + 60, 1, fill=True)
roll(t, 2); arp16(t, 2, 62)
strings.mel(V1 + ' | ' + V1, at=t, vel=74)
lead.mel(V2, at=t + 32, vel=88)
pad.chords(' '.join([GROUND] * 2), at=t, beats=4, style='pad', vel=54, lo=55, hi=72)
t += 64
# breakdown (16): the piano plays V3 then V4, the pad, the riser
piano.chords(GROUND, at=t, beats=4, style='pad', vel=56, lo=50, hi=64)
piano.mel(V3, at=t, vel=84); piano.mel(V4, at=t + 32, vel=88)
pad.chords(' '.join([GROUND] * 2), at=t, beats=4, style='pad', vel=66, lo=55, hi=72)
strings.mel(V1, at=t + 32, vel=70)
riser.note(t + 32, 60, 31.5, 86)
kit.drums({SNARE: 'x...x...x...x...'}, at=t + 48, bars=4, vel={'x': 62})
kit.drums({SNARE: 'x.x.x.x.x.x.x.x.'}, at=t + 56, bars=1, vel={'x': 76})
kit.drums({SNARE: 'xxxxxxxxxxxxxxxx'}, at=t + 60, bars=1, vel={'x': 94})
t += 64
# drop (24): V4 on the lead an octave up, V2 and V1 underneath, brass, everything
kit.note(t, CRASH, 1.5, 116); burst.note(t, 60, 6, 96)
groove(kit, 'trance', t, 23); groove(kit, 'trance', t + 92, 1, fill=True)
roll(t, 3, 104); arp16(t, 3, 66)
lead.mel(V4, at=t, vel=96, tr=12); lead.mel(V3, at=t + 32, vel=94, tr=12); lead.mel(V4, at=t + 64, vel=98, tr=12)
strings.mel(V2, at=t, vel=70); strings.mel(V1, at=t + 32, vel=72, tr=12); strings.mel(V2, at=t + 64, vel=72, tr=12)
brass.chords(' '.join([GROUND] * 3), at=t, beats=4, style='block', vel=72, lo=55, hi=72,
             rhythm=[(0, 0.7), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)])
pad.chords(' '.join([GROUND] * 3), at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
t += 96
# outro (8)
groove(kit, 'trance', t, 4); groove(kit, 'trance', t + 16, 4, drop=(CHH, CLAP))
roll(t, 1, 96); arp16(t, 1, 58)
plink.mel(' '.join('w ' + n for n in 'D5 A4 B4 F#4 G4 D4 G4 A4'.split()), at=t, vel=62)
t += 32
pad.chords('D:8', at=t, style='pad', vel=64, lo=55, hi=72); kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 2, 96)
lead.note(t, pitch('D6'), 4, 90)

S.humanize(ms=2, vel=3, parts=['piano', 'lead', 'strings'])
finish(__file__, S, {
    'title': 'Canon in D',
    'pack': 'trance-connectivity',
    'kind': 'world',
    'composer': 'Johann Pachelbel (1653-1706)',
    'source': 'Canon in D for three violins and basso continuo (c. 1680): the ground and the first violin\'s opening '
              'variations, with one eighth-note division on the ground written by the arranger in the same manner.',
    'licence': 'The work: public domain (17th century). This arrangement: CC0-1.0.',
    'proof': 'https://imslp.org/wiki/Canon_and_Gigue_in_D_major,_P.37_(Pachelbel,_Johann)',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Uplifting trance at 136 bpm: the ground as a rolling offbeat bass and plinks, the variations climbing '
            'from strings and a piano breakdown to the lead an octave up, sixteenth plucks, brass chords. Drums: Kit '
            'Manager 98 (Punch Kick Kit).',
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
    ('plink', 'ch11', 'Signal Plink', dict(lufs=-25, pan=30, echo=0.35)),
    ('strings', 'ch12', 'Blue Signal', dict(lufs=-22, pan=-14, echo=0.15, verb=0.35)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.4, 'tone': 3500, 'level': -3},
   reverb={'size': 2.8, 'predelay': 22, 'tone': 6000, 'level': -5})

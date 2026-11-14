"""Oh! Susanna (Stephen Foster, 1848), arranged for the Paulywaulophone as an office singalong: verse and chorus
six times, the hum from the back row first, then the piano, the bass from Accounts, the kit, the sax, the
bee-buzzing organ and the doo-doo choir; up a tone for the last two. Sounds by Paul Chauncy."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=116, seed=1848)
hum = S.part('hum', 1)
piano = S.part('piano', 2)
bass = S.part('bass', 3)
sax = S.part('sax', 4)
organ = S.part('organ', 5)
doo = S.part('doo', 6)
glock = S.part('glock', 7)
boop = S.part('boop', 8)
guitar = S.part('guitar', 9)
kit = S.part('kit', 10)
chorus = S.part('chorus', 11)
fork = S.part('fork', 12)

VERSE = ('e E4 G4 e. G4 s A4 | e G4 E4 e. C4 s D4 | e E4 E4 D4 C4 | q D4 e C4 D4 | '
         'e E4 G4 e. G4 s A4 | e G4 E4 e. C4 s D4 | e E4 E4 D4 D4 | q C4 e C4 D4')
CHORUS = ('q F4 F4 | e A4 q A4 e A4 | e G4 G4 E4 C4 | q D4 e C4 D4 | '
          'e E4 G4 e. G4 s A4 | e G4 E4 e. C4 s D4 | e E4 E4 D4 D4 | h C4')
SONG = VERSE + ' | ' + CHORUS
PROG = 'C C C G C C G C F F C G C C G C'      # one chord per 2/4 bar
BAR = 2.0
L = 16 * BAR


def band(at, tr=0, kit_on=True, gtr=False, vel=70):
    prev = None
    for k, sy in enumerate(PROG.split()):
        t = at + k * BAR
        ns = voice_lead(prev, [n + tr for n in chord(sy, 4)], 55, 69); prev = ns
        r = root_of(sy, 2) + tr
        bass.note(t, r, 0.8, 94); bass.note(t + 1, r + 7, 0.8, 84)
        piano.note(t, r + 12, 0.45, vel)
        for n in ns:
            piano.note(t + 0.5, n, 0.4, vel - 10); piano.note(t + 1.5, n, 0.4, vel - 14)
        if gtr:
            for n in ns:
                guitar.note(t + 0.5, n, 0.3, 54); guitar.note(t + 1.5, n, 0.3, 50)
    if kit_on:
        kit.drums({KICK: 'x...x...', SNARE: '..x...x.', CHH: 'xxxxxxxx'}, at=at, bars=16, beats_per_bar=2.0, vel={'x': 84})


t = 0.0
fork.note(0, 72, 3, 80)
piano.chords('C:2 G7:2 C:2 G7:2', at=2, style='block', vel=64, lo=55, hi=69, rhythm=[(0, 0.4), (1, 0.4)])   # a four-bar intro
bass.mel('q C3 G2 | q C3 G2 | q C3 G2 | q G2 B2', at=2, vel=90)
t = 2 + 8.0
# the pickup into each verse ("I come from...")
def round_(at, voice, tr=0, vel=90, extra=None):
    voice.mel('e C4 D4', at=at - 1, vel=vel - 6, tr=12 + tr)
    voice.mel(SONG, at=at, vel=vel, tr=12 + tr)
    if extra:
        extra(at)
    return at + L


band(t, kit_on=False); t = round_(t, hum)            # 1: the hum and the piano
band(t, kit_on=True); t = round_(t, hum, vel=92)      # 2: the kit joins
band(t, gtr=True); t = round_(t, sax, vel=92, extra=lambda a: boop.drums({67: '......x.'}, at=a, bars=16, beats_per_bar=2.0, vel={'x': 74}))
band(t, gtr=True)
organ.mel(SONG, at=t, vel=86, tr=12)
doo.chords(' '.join(PROG.split()), at=t, beats=BAR, style='pad', vel=58, lo=55, hi=69)
t = round_(t, chorus, vel=80, tr=-12)
# up a tone for the last two
kit.note(t - 1, CRASH, 2, 108)
band(t, tr=2, gtr=True); doo.chords(' '.join(PROG.split()), at=t, beats=BAR, style='pad', vel=58, lo=57, hi=71)
t2 = round_(t, hum, tr=2, vel=96); sax.mel(SONG, at=t, vel=72, tr=2)
t = t2
band(t, tr=2, gtr=True); organ.mel(SONG, at=t, vel=80, tr=14)
doo.chords(' '.join(PROG.split()), at=t, beats=BAR, style='pad', vel=60, lo=57, hi=71)
glock.mel(CHORUS, at=t + 16, vel=70, tr=26)
t = round_(t, hum, tr=2, vel=98); sax.mel(SONG, at=t - L, vel=74, tr=2)
for p, lo, hi, v in ((piano, 57, 74, 76), (organ, 57, 74, 64), (doo, 57, 71, 64)):
    p.chords('D:4', at=t, style='pad', vel=v, lo=lo, hi=hi)
hum.note(t, pitch('D5'), 4, 92); bass.note(t, pitch('D2'), 4, 96); kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 3, 104)
fork.note(t + 1, 74, 4, 70)

S.humanize(ms=6, vel=5)
finish(__file__, S, {
    'title': 'Oh! Susanna',
    'pack': 'paulywaulophone',
    'kind': 'world',
    'composer': 'Stephen Foster (1826-1864)',
    'source': 'Oh! Susanna, song (1848): verse and chorus, written out from the song.',
    'licence': 'The work: public domain (published 1848; the composer died 1864). This arrangement: CC0-1.0; sounds '
               'by Paul Chauncy.',
    'proof': 'https://en.wikipedia.org/wiki/Oh!_Susanna',
    'arranger': 'Algorithmic Industries house band',
    'note': 'An office singalong at 116 bpm: six rounds of verse and chorus, the hum from the back row, office piano, '
            'the bass from Accounts, guitar, the sax, the bee-buzzing organ, the doo-doo choir, boops, a glockenspiel '
            'and a tuning fork; up a tone for the last two rounds. Drums: the pack\'s Honey Drift kit.',
}, [
    ('hum', 'ch1', 'Electric Vox', dict(lufs=-19, pan=4, verb=0.3)),
    ('piano', 'ch2', 'Humid Practice', dict(lufs=-21, pan=-14, verb=0.25)),
    ('bass', 'ch3', 'Wired Anchor', dict(lufs=-20)),
    ('sax', 'ch4', 'Dial Beam', dict(lufs=-21, pan=-20, echo=0.1, verb=0.3)),
    ('organ', 'ch5', 'Mint Voice', dict(lufs=-23, pan=20, verb=0.2)),
    ('doo', 'ch6', 'Remote Haze', dict(lufs=-25, pan=-6, verb=0.35, width=1.3)),
    ('glock', 'ch7', 'Orbital Beam', dict(lufs=-24, pan=28, echo=0.2, verb=0.35)),
    ('boop', 'ch8', 'Humid Chop', dict(lufs=-26, pan=-30, echo=0.25)),
    ('guitar', 'ch9', 'Night Ballad', dict(lufs=-25, pan=32, verb=0.2)),
    ('kit', 'ch10', 'Honey Drift', dict(lufs=-18, verb=0.08)),
    ('chorus', 'ch11', 'Felt Chorus', dict(lufs=-22, pan=10, verb=0.4)),
    ('fork', 'ch12', 'Winter Chimes', dict(lufs=-25, verb=0.4)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 3000, 'level': -7},
   reverb={'size': 1.8, 'predelay': 18, 'tone': 5500, 'level': -5})

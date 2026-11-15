"""Umbrella Stand, Third Floor: an original city-pop piece, 100 bpm, F major. Rain on the window, then the loft tine
piano, a rubber bass, sixteenth-note guitar chops, the Couch Disco kit, the neon sign lead with brass stabs and a
vocoder chorus; a train goes past at the end."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=100, seed=1988)
lead = S.part('lead', 1)
tine = S.part('tine', 2)
gtr = S.part('guitar', 3)
bass = S.part('bass', 4)
brass = S.part('brass', 5)
vox = S.part('vocoder', 6)
rain = S.part('rain', 7)
train = S.part('train', 8)
phone = S.part('phone', 9)
kit = S.part('kit', 10)

A = 'Bbmaj7 Am7 Gm7 C7sus4 Bbmaj7 Am7 Gm7 C7sus4'
B = 'Dm7 Gm7 Bbmaj7 C7 Dm7 Gm7 Ebmaj7 C7sus4'
MA = ('e r A5 q A5 e G5 F5 q G5 | q. E5 e C5 h r | e r D5 F5 A5 q C6 e Bb5 A5 | h G5 q. r e C5 | '
      'e D5 F5 A5 C6 q D6 e C6 A5 | q. C6 e A5 q G5 e E5 C5 | q D5 e F5 G5 q A5 e G5 F5 | w G5')
MB = ('q A5 e A5 C6 q D6 e C6 A5 | h. Bb5 e A5 G5 | q F5 e A5 D6 q. C6 e A5 | h G5 q E5 C5 | '
      'q A5 e A5 C6 q D6 e F6 E6 | q D6 e C6 Bb5 h A5 | q G5 e Bb5 Eb6 q D6 e C6 Bb5 | w C6')
BASS = [(0, 0, 0.7), (0.75, '8', 0.25), (1.5, 0, 0.4), (2, '5', 0.9), (3, 0, 0.4), (3.5, '8', 0.4)]
CHOP = [(0.5, 0.2), (1.25, 0.15), (1.5, 0.2), (2.5, 0.2), (3.25, 0.15), (3.5, 0.2)]
PUSH = [(0, 1.4), (1.5, 0.4), (2.5, 1.4)]


def band(at, prog, guitar=True, drums='disco', vel=96):
    bars = len(prog.split())
    tine.chords(prog, at=at, style='block', rhythm=PUSH, vel=66, lo=53, hi=72)
    bass.bass(prog, at=at, pattern=BASS, vel=vel, octave=2)
    if guitar:
        gtr.chords(prog, at=at, style='block', rhythm=CHOP, vel=60, lo=60, hi=76)
    if drums:
        groove(kit, drums, at, bars, fill=True)


t = 0.0
# intro (4): the rain, the tine piano alone, a hat count-in
hold(rain, 0, 60, 4 * 56 + 8, 64)
tine.chords('Bbmaj7 Am7 Gm7 C7sus4', at=t, style='pad', vel=60, lo=53, hi=72)
kit.drums({42: '..............xx'}, at=t + 12, bars=1, vel={'x': 70})
t += 16
# A (8): the groove and the tune
band(t, A); lead.mel(MA, at=t, vel=90); t += 32
# A (8): brass stabs on the and of four
band(t, A); lead.mel(MA, at=t, vel=94)
brass.chords(A, at=t, style='block', rhythm=[(3.5, 0.4)], vel=78, lo=58, hi=74); t += 32
# B (8): the vocoder chorus comes in
band(t, B); lead.mel(MB, at=t, vel=96)
vox.chords(B, at=t, style='pad', vel=64, lo=55, hi=72); t += 32
# break (4): bass and kit, the telephone rings twice
bass.bass('Gm7 C7sus4 Gm7 C7sus4', at=t, pattern=BASS, vel=92); groove(kit, 'house_lite', t, 4)
phone.note(t + 2, 60, 4, 84); t += 16
# A (8) and B (8): everyone
band(t, A); lead.mel(MA, at=t, vel=96)
brass.chords(A, at=t, style='block', rhythm=[(3.5, 0.4)], vel=80, lo=58, hi=74); t += 32
band(t, B); lead.mel(MB, at=t, vel=98)
vox.chords(B, at=t, style='pad', vel=66, lo=55, hi=72)
brass.chords(B, at=t, style='block', rhythm=[(3.5, 0.4)], vel=80, lo=58, hi=74); t += 32
# outro (4): the tine piano and the rain; a train passes
tine.chords('Bbmaj7 Am7 Gm7 Fmaj7', at=t, style='pad', vel=60, lo=53, hi=72)
bass.note(t + 12, pitch('F2'), 4, 84); train.note(t, 60, 12, 80)

S.humanize(ms=6, vel=5)
finish(__file__, S, {
    'title': 'Umbrella Stand, Third Floor',
    'pack': 'rainy-loft',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'City pop in F major, 100 bpm: rain on the window, the loft tine piano, the rubber taxi bass, taxi rhythm '
            'guitar chops, the Couch Disco kit, the neon sign lead, rooftop brass stabs, the vocoder chorus, a telephone '
            'and a passing train.',
}, [
    ('lead', 'ch1', 'Neon Sign Lead', dict(lufs=-18, pan=-4, echo=0.15, verb=0.2)),
    ('tine', 'ch2', 'Loft Tine', dict(lufs=-21, pan=-18, verb=0.2)),
    ('guitar', 'ch3', 'Taxi Rhythm Guitar', dict(lufs=-24, pan=26, verb=0.1)),
    ('bass', 'ch4', 'Rubber Taxi', dict(lufs=-18)),
    ('brass', 'ch5', 'Rooftop Brass', dict(lufs=-22, pan=12, verb=0.2)),
    ('vocoder', 'ch6', 'Vocoder Chorus', dict(lufs=-25, width=1.3, verb=0.3)),
    ('rain', 'ch7', 'Rain on the Window', dict(lufs=-30, width=1.4)),
    ('train', 'ch8', 'Passing Train', dict(lufs=-26, width=1.3, verb=0.2)),
    ('phone', 'ch9', 'Telephone, Two Rings', dict(lufs=-26, pan=-30, verb=0.25)),
    ('kit', 'ch10', 'Couch Disco', dict(lufs=-18, verb=0.06)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
   reverb={'size': 1.8, 'predelay': 14, 'tone': 5500, 'level': -7})

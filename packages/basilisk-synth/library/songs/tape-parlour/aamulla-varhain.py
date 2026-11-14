"""Aamulla varhain (Early in the Morning), Finnish traditional, arranged for the Tape Parlour Ensemble as a late-60s
chamber-pop song on tape-replay voices: the tune on the flute, then the choir, the recorder and the cellos, over the
parlour piano's chords, a contrabass and a soft kit, the 8-foot organ stop at the end."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'AAMULLAVARHAIN.mid'))
S = Score(bpm=80, seed=1967)
flute = S.part('flute', 1)
choir = S.part('choir', 2)
recorder = S.part('recorder', 3)
cellos = S.part('cellos', 4)
violas = S.part('violas', 5)
piano = S.part('piano', 6)
bass = S.part('bass', 7)
organ = S.part('organ', 8)
trumpet = S.part('trumpet', 9)
kit = S.part('kit', 10)

L = src.bars() * 4.0
tune, acc = src.tracks[1], src.tracks[0]
syms = chords_of(acc, 0, L, 2.0)


def accomp(at, piano_on=True, strings=False, kit_on=False):
    if piano_on:
        put(piano, beats(acc, 0, L, at), vel=58, lo=52, hi=74)
    prev = None
    for i, sy in enumerate(syms):
        r = root_of(sy, 2)
        bass.note(at + 2 * i, r + 12 if r < 40 else r, 1.9, 88)
        if strings:
            ns = voice_lead(prev, chord(sy, 4), 52, 67); prev = ns
            for n in ns:
                violas.note(at + 2 * i, n, 1.95, 56)
    if kit_on:
        for k in range(int(L // 4)):
            kit.drums({KICK: 'x.......x.x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'}, at=at + 4 * k, bars=1,
                      vel={'x': 80})


t = 0.0
put(piano, beats(acc, L - 8, L, 0), vel=56, lo=52, hi=74)
t = 8.0
put(flute, beats(tune, 0, L, t), vel=88, lo=60, hi=84); accomp(t)
t += L
put(choir, beats(tune, 0, L, t), vel=88, lo=60, hi=79); accomp(t, strings=True, kit_on=True)
put(recorder, [(b + 0.5, p + 12, d * 0.5, v) for b, p, d, v in beats(tune, 0, L, t) if d >= 1.0], vel=64, lo=67, hi=88)
t += L
put(cellos, beats(tune, 0, L, t), tr=-12, vel=86, lo=45, hi=67); accomp(t, strings=True, kit_on=True)
put(flute, [(b, p + 12, d, v) for b, p, d, v in beats(tune, L / 2, L, t + L / 2)], vel=74, lo=67, hi=88)
t += L
# the instrumental: trumpet, the organ, the piano alone underneath
put(trumpet, beats(tune, 0, L, t), vel=88, lo=60, hi=79); accomp(t, kit_on=True)
organ.chords(' '.join(syms), at=t, beats=2, style='pad', vel=56, lo=52, hi=67)
t += L
# the last verse: choir and flute together, strings, a ritardando on the last line
put(choir, beats(tune, 0, L, t), vel=92, lo=60, hi=79); put(flute, beats(tune, 0, L, t), vel=78, lo=60, hi=84)
accomp(t, strings=True, kit_on=True)
S.tempo(t + L - 8, 72); S.tempo(t + L - 4, 62)
t += L
organ.chords(syms[-1] + ':6', at=t, style='pad', vel=62, lo=52, hi=67); piano.chords(syms[-1] + ':6', at=t, style='pad', vel=60, lo=52, hi=72)
bass.note(t, root_of(syms[-1], 2) + 12, 6, 88)
S.tempo(t, 62)

S.humanize(ms=8, vel=5)
finish(__file__, S, {
    'title': 'Aamulla varhain',
    'pack': 'tape-parlour',
    'kind': 'world',
    'composer': 'Finnish traditional',
    'source': 'Aamulla varhain (Early in the Morning), Finnish folk song. Score: The Mutopia Project (voice and piano; '
              'the tune is taken, the arrangement is new).',
    'licence': 'The work: traditional, public domain. The edition used: public domain (Mutopia). This arrangement: '
               'CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1020',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Late-60s chamber pop at 80 bpm on tape-replay voices: the tune on flute, choir, cellos and trumpet in '
            'turn, a recorder answering, violas, a parlour piano, a contrabass, the 8-foot organ stop, a soft kit, '
            'a ritardando at the end. Drums: Kit Manager 98 (Half-Time Kit).',
}, [
    ('flute', 'ch1', 'Digital Call', dict(lufs=-19, pan=-10, verb=0.3)),
    ('choir', 'ch2', 'Faded Voices', dict(lufs=-20, pan=6, verb=0.4)),
    ('recorder', 'ch3', 'Field Line', dict(lufs=-23, pan=30, echo=0.15, verb=0.3)),
    ('cellos', 'ch4', 'Warm Legato', dict(lufs=-21, pan=-24, verb=0.3)),
    ('violas', 'ch5', 'Clear Bows', dict(lufs=-24, pan=24, verb=0.35)),
    ('piano', 'ch6', 'Lattice Recital', dict(lufs=-22, pan=16, verb=0.25)),
    ('bass', 'ch7', 'Lunar Bows', dict(lufs=-22)),
    ('organ', 'ch8', 'Coral Revival', dict(lufs=-26, pan=-6, verb=0.3)),
    ('trumpet', 'ch9', 'Pewter Salute', dict(lufs=-21, pan=10, verb=0.35)),
    ('kit', 'ch10', 'kit-manager:Half-Time Kit', dict(lufs=-20, verb=0.12, lp=9000)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 2800, 'level': -8},
   reverb={'size': 1.9, 'predelay': 20, 'tone': 4500, 'level': -4})

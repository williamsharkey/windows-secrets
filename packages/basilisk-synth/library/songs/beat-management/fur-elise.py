"""Fur Elise (Ludwig van Beethoven, WoO 59, 1810), arranged for the Beat Management Console as a lo-fi beat in 6/8:
rain on the window, the tune on an upright piano and vibes, the left hand on tines, upright bass, a dusty
shuffle kit, a flute in the middle section, desk scratches."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'fur_Elise_WoO59.mid'))
S = Score(bpm=100, seed=1810)
piano = S.part('piano', 1)
tines = S.part('tines', 2)
vibes = S.part('vibes', 3)
bass = S.part('bass', 4)
flute = S.part('flute', 5)
strings = S.part('strings', 6)
rain = S.part('rain', 7)
scratch = S.part('scratch', 8)
choir = S.part('choir', 9)
kit = S.part('kit', 10)

PICK = 0.5                     # the two-sixteenth pickup
END = src.bars() * src.bar
INTRO = 6.0
hold(rain, 0, 60, INTRO + END + 6, 80, 16)
arrange(src, PICK, PICK + 6, 0, inner=tines, rh_track=1, lh_track=1, inner_range=(45, 72), vel=60)
t0 = INTRO - PICK
arrange(src, 0, END, t0, lead=piano, inner=piano, lh=tines, rh_track=0, lh_track=1,
        lead_range=(57, 88), inner_range=(52, 80), lh_range=(45, 72), lead_vel=None, vel=None)
# vibes double the tune in the first return; the flute takes the F major episode; strings under the storm
put(vibes, skyline(beats(src.tracks[0], 0, 33 * 1.5, t0)), vel=58, lo=64, hi=91)
put(flute, skyline(beats(src.tracks[0], 34 * 1.5, 56 * 1.5, t0 + 34 * 1.5)), tr=-12, vel=84, lo=60, hi=81)
arrange(src, 60 * 1.5, 80 * 1.5, t0 + 60 * 1.5, pad=strings, rh_track=0, lh_track=1, pad_step=3.0, pad_range=(50, 67), vel=60)
arrange(src, 80 * 1.5, END, t0 + 80 * 1.5, pad=choir, rh_track=0, lh_track=1, pad_step=3.0, pad_range=(52, 67), vel=54)
# the bass: the left hand's lowest note on each 6/8 downbeat
for b, p, d, v in floor(beats(src.tracks[1], 0, END, t0)):
    if abs(((b - t0 - PICK) / 1.5) - round((b - t0 - PICK) / 1.5)) < 0.01:
        n = p
        while n > 52:
            n -= 12
        while n < 33:
            n += 12
        bass.note(b, n, 1.2, 96)
# the beat: 6/8 boom-bap, one cycle every two 3/8 bars
sw = {'x': 92, 'X': 112, 'o': 52}
for k in range(int((END - PICK) // 3)):
    b = t0 + PICK + 3 * k
    if 8 <= k < 52 or k >= 56:
        kit.drums({KICK: 'x.....x.x...', SNARE: '...x.....x..' if k % 4 != 3 else '...x....xx.x', CHH: 'x.x.x.x.x.x.'},
                  at=b, bars=1, step=0.25, beats_per_bar=3.0, vel=sw)
    if k % 8 == 7:
        for i, n in enumerate((60, 64, 60, 67)):
            scratch.note(b + 2 + i * 0.25, n, 0.2, 90)
t = t0 + END
piano.chords('Am:6', at=t, style='pad', vel=70, lo=57, hi=76); bass.note(t, pitch('A1') + 12, 4, 96)

S.humanize(ms=8, vel=5, parts=['piano', 'tines', 'vibes', 'flute'])
finish(__file__, S, {
    'title': 'Fur Elise',
    'pack': 'beat-management',
    'kind': 'world',
    'composer': 'Ludwig van Beethoven (1770-1827)',
    'source': 'Bagatelle No. 25 in A minor, WoO 59, "Fur Elise" (1810, first published 1867). Score: The Mutopia '
              'Project, from Breitkopf & Hartel (1888).',
    'licence': 'The work: public domain. The edition used: public domain (Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=931',
    'arranger': 'Algorithmic Industries house band',
    'note': 'A lo-fi beat in 6/8 at 100 bpm, the whole bagatelle: upright piano, tines on the left hand, vibes, a '
            'flute in the F major episode, strings under the stormy part, the choir at the end, upright bass, rain and '
            'scratches. Drums: Kit Manager 98 (Twelve-Bit Crate Kit).',
}, [
    ('piano', 'ch1', 'Cedar Study', dict(lufs=-19, pan=-8, verb=0.25, lp=9000)),
    ('tines', 'ch2', 'Wide Flick', dict(lufs=-23, pan=16, verb=0.25)),
    ('vibes', 'ch3', 'Study Vibes', dict(lufs=-25, pan=26, echo=0.2, verb=0.3)),
    ('bass', 'ch4', 'Upright Thump', dict(lufs=-20)),
    ('flute', 'ch5', 'Civic Wire', dict(lufs=-21, pan=6, echo=0.2, verb=0.3)),
    ('strings', 'ch6', 'Golden Section', dict(lufs=-25, pan=-20, verb=0.35)),
    ('rain', 'ch7', 'Window Rain Room', dict(lufs=-31, width=1.4)),
    ('scratch', 'ch8', 'Desk Scratch', dict(lufs=-25, pan=-8)),
    ('choir', 'ch9', 'Winter Choir', dict(lufs=-27, verb=0.45, width=1.3)),
    ('kit', 'ch10', 'kit-manager:Twelve-Bit Crate Kit', dict(lufs=-18, verb=0.06)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 2500, 'level': -6},
   reverb={'size': 1.6, 'predelay': 15, 'tone': 4500, 'level': -6})

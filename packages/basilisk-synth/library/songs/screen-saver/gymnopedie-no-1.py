"""Gymnopedie No. 1 (Erik Satie, 1888), arranged for the Ambient Screen Saver Collection: a breathy flute takes the
tune over the glass-harp chords and a low singing-bowl bass, with marimba, chimes and the sea."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'gymnopedie_1.mid'))
S = Score(bpm=66, seed=1888)
flute = S.part('flute', 1)
glass = S.part('glass', 2)
bowl = S.part('bassbowl', 3)
marimba = S.part('marimba', 4)
chimes = S.part('chimes', 5)
waves = S.part('waves', 6)
pad = S.part('strings', 7)
bird = S.part('bird', 8)

INTRO = 6.0   # two bars of sea first
end = src.bars() * src.bar
arrange(src, 0, end, INTRO, lead=flute, inner=glass, rh_track=0, lh_track=None,
        lead_range=(62, 86), inner_range=(55, 74), lead_vel=86, vel=58)
arrange(src, 0, end, INTRO, bass=bowl, rh_track=1, lh_track=1, bass_range=(38, 55), vel=70)
# the marimba doubles the chords softly from the second phrase; chimes touch the melody's long notes
for b, p, d, v in beats(src.tracks[0], 12, end, INTRO + 12):
    if p < 72:
        marimba.note(b + 0.02, p, 0.9, 46)
for b, p, d, v in skyline(beats(src.tracks[0], 12, end, INTRO + 12)):
    if d >= 3 and p >= 72:
        chimes.note(b, p + 12, 2.5, 52)
# strings hold the harmony in the middle phrase (bars 17-32)
arrange(src, 48, 96, INTRO + 48, pad=pad, rh_track=0, lh_track=1, pad_range=(54, 69), vel=48)
hold(waves, 0, 60, INTRO + end + 6, 72, 16)
for k, t in enumerate((INTRO + 40, INTRO + 90, INTRO + end - 4)):
    bird.note(t, 89, 0.6, 64 - 4 * k)

finish(__file__, S, {
    'title': 'Gymnopedie No. 1',
    'pack': 'screen-saver',
    'kind': 'world',
    'composer': 'Erik Satie (1866-1925)',
    'source': 'Gymnopedie No. 1 for piano (1888). Score: The Mutopia Project, typeset from the Dover edition.',
    'licence': 'The work: public domain (published 1888; the composer died 1925). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=37',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The whole piece at 66 bpm: breathy flute melody, glass-harp chords, singing-bowl bass, marimba, chimes, '
            'string pad in the middle phrase, the sea and a hermit thrush.',
    'tail': 6,
}, [
    ('flute', 'ch1', 'Breath Flute', dict(lufs=-20, pan=4, echo=0.15, verb=0.45)),
    ('glass', 'ch2', 'Ivory Canopy', dict(lufs=-24, pan=-14, verb=0.4)),
    ('bassbowl', 'ch3', 'Northern Dormant', dict(lufs=-24, verb=0.3)),
    ('marimba', 'ch4', 'Water Marimba', dict(lufs=-27, pan=-26, echo=0.25, verb=0.35)),
    ('chimes', 'ch5', 'Sunday Chimes', dict(lufs=-27, pan=28, echo=0.3, verb=0.5)),
    ('waves', 'ch6', 'Ocean Shelf', dict(lufs=-31, width=1.4)),
    ('strings', 'ch7', 'Lunar Canopy', dict(lufs=-27, pan=12, verb=0.45, width=1.3)),
    ('bird', 'ch8', 'Thrush Morning', dict(lufs=-29, pan=38, verb=0.4)),
], master={'loudness': -17, 'ceiling': -1.0, 'fadeout': 3},
   echo={'time': '3/8', 'feedback': 0.35, 'tone': 3000, 'level': -5},
   reverb={'size': 3.6, 'predelay': 30, 'tone': 5000, 'level': -3})

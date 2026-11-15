"""Prelude in D-flat, Op. 28 No. 15 ('Raindrop') (Frederic Chopin (1810-1849)), arranged for the rainy-loft pack from
a public-domain Mutopia edition (sources/Chop-28-15.mid): the first section, bars 1-27."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['tine'], 'inner': 'vibes', 'lh': 'felt', 'bass': 'bass', 'pad': 'strings'}
HEADER = {'title': 'Raindrop Prelude', 'pack': 'rainy-loft', 'kind': 'world', 'composer': 'Frederic Chopin (1810-1849)',
          'source': 'Prelude in D-flat major, Op. 28 No. 15 (1839), bars 1-27. Score: The Mutopia Project, from Edition Peters.',
          'licence': 'The work: public domain (published 1839; the composer died 1849). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.',
          'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=471', 'arranger': 'Algorithmic Industries house band',
          'note': 'The D-flat section at 60 bpm: the tune on the loft tine piano, the repeated A-flat on the lobby vibraphone, '
                  'the left hand on the felt upright, a fretless bass under it and the haze strings.'}
TRACKS = [('tine', 'ch1', 'Loft Tine', {'lufs': -18, 'pan': -6, 'verb': 0.35}),
          ('vibes', 'ch2', 'Lobby Vibraphone', {'lufs': -24, 'pan': 18, 'echo': 0.15, 'verb': 0.4}),
          ('felt', 'ch3', 'Felt Upright', {'lufs': -22, 'pan': -16, 'verb': 0.3}),
          ('bass', 'ch4', 'Fretless Harbour', {'lufs': -22}),
          ('strings', 'ch5', 'Haze Strings', {'lufs': -27, 'width': 1.3, 'verb': 0.4})]
world_song(__file__, 'Chop-28-15.mid', 60, HEADER, ROLES, TRACKS, a=0.0, b=27 * 4.0, passes=1, intro_pass=False,
           master={'loudness': -17, 'ceiling': -1.0, 'fadeout': 3},
           echo={'time': '1/4', 'feedback': 0.3, 'tone': 3000, 'level': -7},
           reverb={'size': 3.2, 'predelay': 24, 'tone': 5000, 'level': -4})

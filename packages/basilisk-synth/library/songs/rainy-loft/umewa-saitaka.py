"""Umewa Saitaka (traditional, Japan), arranged for the rainy-loft pack from a public-domain Mutopia edition
(sources/J95002-UmewaSaitaka.mid, from Nagai and Obata's 1895 collection)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['flute', 'reed', 'clarinet', 'flute'], 'lh': 'tine', 'bass': 'bass', 'pad': 'strings', 'kit': 'kit'}
HEADER = {'title': 'Umewa Saitaka', 'pack': 'rainy-loft', 'kind': 'world', 'composer': 'Traditional (Japan)',
          'source': 'Umewa Saitaka, a shamisen song, from Nagai and Obata, "Seiyo gakufu Nihon zokkyokushu" (Osaka, 1895). Score: The Mutopia Project.',
          'licence': 'The work: traditional, public domain (published 1895). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.',
          'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1762', 'arranger': 'Algorithmic Industries house band',
          'note': 'The song four times at 88 bpm over brushes: the night flute, the harbour reed and the clarinet in turn, '
                  'chords on the loft tine piano, the pluck bass and velvet strings. Drums: the pack\'s Loft Brushes kit.'}
TRACKS = [('flute', 'ch1', 'Night Flute', {'lufs': -19, 'pan': -6, 'echo': 0.15, 'verb': 0.3}),
          ('reed', 'ch2', 'Harbour Reed', {'lufs': -20, 'pan': 8, 'echo': 0.15, 'verb': 0.3}),
          ('clarinet', 'ch6', 'Clarinet After Hours', {'lufs': -20, 'pan': 4, 'verb': 0.3}),
          ('tine', 'ch3', 'Loft Tine', {'lufs': -22, 'pan': -18, 'verb': 0.25}),
          ('bass', 'ch4', 'Pluck Avenue', {'lufs': -20}),
          ('strings', 'ch5', 'Velvet Strings', {'lufs': -27, 'width': 1.3, 'verb': 0.35}),
          ('kit', 'ch10', 'Loft Brushes', {'lufs': -21, 'verb': 0.12})]
world_song(__file__, 'J95002-UmewaSaitaka.mid', 88, HEADER, ROLES, TRACKS, passes=4, groove_name='boombap',
           master={'loudness': -16, 'ceiling': -1.0},
           echo={'time': '3/8', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.2, 'predelay': 18, 'tone': 5500, 'level': -6})

"""The Dying Swan (Louis Moreau Gottschalk (1829-1869)), arranged for the leisure pack from a public-domain Mutopia edition
(sources/TheDyingSwan.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['bells'], 'inner': 'marimba', 'lh': 'piano', 'bass': 'cello', 'pad': 'strings'}
HEADER = {'title': 'The Dying Swan', 'pack': 'leisure', 'kind': 'world', 'composer': 'Louis Moreau Gottschalk (1829-1869)', 'source': 'The Dying Swan, Op. 100, for piano. Score: The Mutopia Project, from Kunkel Brothers (1870).', 'licence': 'The work: public domain (published 1870; the composer died 1869). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=942', 'arranger': 'Algorithmic Industries house band', 'note': 'A lounge reading at 84 bpm: vibes-bells on the tune, marimba on the inner voices, the lounge piano on the left hand, cello bass, strings.'}
TRACKS = [('bells', 'ch1', 'Soft Bells', {'lufs': -20, 'pan': 8, 'echo': 0.2, 'verb': 0.4}), ('marimba', 'ch2', 'Island Marimba', {'lufs': -25, 'pan': -24, 'verb': 0.3}), ('piano', 'ch3', 'Tiki Lounge Piano', {'lufs': -23, 'pan': -14, 'verb': 0.3}), ('cello', 'ch4', 'Opal Section', {'lufs': -22, 'verb': 0.15}), ('strings', 'ch5', 'Volcano Strings', {'lufs': -25, 'pan': 14, 'verb': 0.4, 'width': 1.3})]
world_song(__file__, 'TheDyingSwan.mid', 84, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=236, passes=1, intro_pass=False)

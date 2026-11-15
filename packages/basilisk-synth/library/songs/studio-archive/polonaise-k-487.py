"""Polonaise (K. 487 No. 4) (Wolfgang Amadeus Mozart (1756-1791)), arranged for the studio-archive pack from a public-domain Mutopia edition
(sources/no4.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['horns', 'trumpet', 'violins'], 'lh': 'trombones', 'bass': 'bass', 'pad': 'strings'}
HEADER = {'title': 'Polonaise (K. 487 No. 4)', 'pack': 'studio-archive', 'kind': 'world', 'composer': 'Wolfgang Amadeus Mozart (1756-1791)', 'source': 'Twelve Duets, K. 487: No. 4, Polonaise (1786), for two horns. Score: The Mutopia Project.', 'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=393', 'arranger': 'Algorithmic Industries house band', 'note': "The horn duet three times for the studio's brass and strings: the first horn part on horns, trumpet and violins in turn, the second on trombones, a marimba bass on the chord roots, a string pad."}
TRACKS = [('horns', 'ch1', 'Opal Fanfare', {'lufs': -20, 'pan': 10, 'verb': 0.4}), ('trumpet', 'ch2', 'White Stab', {'lufs': -21, 'pan': -6, 'verb': 0.35}), ('violins', 'ch3', 'Humid Swell', {'lufs': -20, 'pan': -22, 'verb': 0.4}), ('trombones', 'ch4', 'Upper Horns', {'lufs': -23, 'pan': 24, 'verb': 0.3}), ('bass', 'ch5', 'Signal Bass', {'lufs': -22}), ('strings', 'ch6', 'Waxed Aurora', {'lufs': -26, 'verb': 0.4})]
world_song(__file__, 'no4.mid', 108, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=3, intro_pass=False)

"""Old Hundredth (Louis Bourgeois (attributed), Genevan Psalter (1551)), arranged for the electromech-heritage pack from a public-domain Mutopia edition
(sources/Old100-orig.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['vowel', 'pulse'], 'inner': 'sounder', 'lh': 'marimba', 'bass': 'hootbass', 'pad': 'organ', 'kit': 'kit'}
HEADER = {'title': 'Old Hundredth', 'pack': 'electromech-heritage', 'kind': 'world', 'composer': 'Louis Bourgeois (attributed), Genevan Psalter (1551)', 'source': 'Old Hundredth (Psalm 134 in the Genevan Psalter, 1551), the original rhythm, in four parts. Score: The Mutopia Project.', 'licence': 'The work: public domain (published 1551). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=194', 'arranger': 'Algorithmic Industries house band', 'note': 'The psalm tune twice for the telephone exchange: the 1961 vowel and then the CSIRAC pulse on the melody, sounder keys and a relay marimba on the inner and lower voices, a Ferranti-hoot bass, the dial-tone organ. Drums: Kit Manager 98 (Relay Room).'}
TRACKS = [('vowel', 'ch1', '1961 Vowel', {'lufs': -19, 'pan': 4, 'echo': 0.15, 'verb': 0.35}), ('pulse', 'ch2', 'CSIRAC Pulse', {'lufs': -20, 'pan': 10, 'echo': 0.2}), ('sounder', 'ch3', 'Sounder Keys', {'lufs': -25, 'pan': -16, 'verb': 0.2}), ('marimba', 'ch4', 'Relay Marimba', {'lufs': -23, 'pan': -20, 'verb': 0.2}), ('hootbass', 'ch5', 'Ferranti Hoot', {'lufs': -20}), ('organ', 'ch6', 'Dial Tone Organ', {'lufs': -26, 'pan': 18, 'verb': 0.3}), ('kit', 'ch10', 'kit-manager:Relay Room', {'lufs': -21, 'verb': 0.08})]
world_song(__file__, 'Old100-orig.mid', 100, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=2, groove_name='halftime')

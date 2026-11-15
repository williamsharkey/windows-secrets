"""Nuż my dziś krześcijani (Polish traditional (1586)), arranged for the bass-enterprise pack from a public-domain Mutopia edition
(sources/Nuz_my_dzis_krzescijani.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['horn', 'section', 'horn', 'chord'], 'inner': 'chord', 'bass': 'organbass', 'pad': 'vowel', 'kit': 'kit'}
HEADER = {'title': 'Nuż my dziś krześcijani', 'pack': 'bass-enterprise', 'kind': 'world', 'composer': 'Polish traditional (1586)', 'source': 'Nuż my dziś krześcijani, a Polish Christmas carol printed in 1586, in a four-part setting. Score: The Mutopia Project.', 'licence': 'The work: public domain (published 1586). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=856', 'arranger': 'Algorithmic Industries house band', 'note': 'UK garage at 132 bpm, four times: the carol on the trombone hook and a brass section in turn, the inner voices on the organ chord, the bass voice on the 2-step organ bass, the vowel pad. Drums: Kit Manager 98 (Half-Time Kit).'}
TRACKS = [('horn', 'ch1', 'Lattice Accent', {'lufs': -20, 'pan': 12, 'echo': 0.2, 'verb': 0.2}), ('section', 'ch2', 'Lagoon Section', {'lufs': -21, 'pan': -12, 'verb': 0.2}), ('chord', 'ch3', 'Golden Chord', {'lufs': -24, 'pan': -16, 'verb': 0.25}), ('organbass', 'ch4', 'Organ Bass 2-Step', {'lufs': -19}), ('vowel', 'ch5', 'Marble Vowel', {'lufs': -26, 'verb': 0.4, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Half-Time Kit', {'lufs': -17, 'verb': 0.05})]
world_song(__file__, 'Nuz_my_dzis_krzescijani.mid', 132, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=4, groove_name='2step')

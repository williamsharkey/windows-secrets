"""The Mountaineer's Song (Edvard Grieg (1843-1907)), arranged for the rom-reference pack from a public-domain Mutopia edition
(sources/7-MountaineersSong.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['lead', 'tines'], 'lh': 'piano', 'bass': 'bass', 'pad': 'strings', 'kit': 'kit'}
HEADER = {'title': "The Mountaineer's Song", 'pack': 'rom-reference', 'kind': 'world', 'composer': 'Edvard Grieg (1843-1907)', 'source': "Lualat (The Mountaineer's Song), Lyric Pieces Op. 73 No. 7 (1905): the first section. Score: The Mutopia Project, from C. F. Peters (1907).", 'licence': 'The work: public domain (published 1905; the composer died 1907). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1628', 'arranger': 'Algorithmic Industries house band', 'note': 'Late-80s workstation pop at 116 bpm, twice: the tune on a lead and then tines, the inner voices on a gamelan pluck, the left hand on piano, a bass, string swells. Drums: Kit Manager 98 (Breaker Box Kit).'}
TRACKS = [('lead', 'ch1', 'Cathode Lead', {'lufs': -19, 'pan': 4, 'echo': 0.2, 'verb': 0.3}), ('tines', 'ch2', 'Jade Tines', {'lufs': -20, 'pan': -8, 'echo': 0.15, 'verb': 0.3}), ('piano', 'ch4', 'Lagoon Piano', {'lufs': -23, 'pan': -16, 'verb': 0.3}), ('bass', 'ch5', 'Neon Basement', {'lufs': -19}), ('strings', 'ch6', 'Blue Swell', {'lufs': -25, 'verb': 0.4, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -17.5, 'verb': 0.12})]
world_song(__file__, '7-MountaineersSong.mid', 116, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=152, passes=2)

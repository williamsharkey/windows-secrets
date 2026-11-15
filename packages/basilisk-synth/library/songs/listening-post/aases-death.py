"""Aase's Death (Edvard Grieg (1843-1907)), arranged for the listening-post pack from a public-domain Mutopia edition
(sources/02-lamortdase.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *
chord_cap(8)   # pads on many-voice DNAs: at most 8 recorders an instant (songqa found late notes)

ROLES = {'leads': ['humpback'], 'inner': 'bowl', 'lh': 'fin', 'pad': 'blue'}
HEADER = {'title': "Aase's Death", 'pack': 'listening-post', 'kind': 'world', 'composer': 'Edvard Grieg (1843-1907)', 'source': "Aase's Death, Peer Gynt Suite No. 1, Op. 46 No. 2 (1875), piano version. Score: The Mutopia Project, from Kunkel Brothers (1891).", 'licence': 'The work: public domain (composed 1875; the composer died 1907). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=246', 'arranger': 'Algorithmic Industries house band', 'note': 'Slowly, at 52 bpm, in the deep ocean: a humpback on the tune, a singing bowl on the inner voices, fin-whale drones on the bass line, blue-whale drones holding the chords.'}
TRACKS = [('humpback', 'ch1', 'Ocean Shoreline', {'lufs': -20, 'pan': 4, 'echo': 0.2, 'verb': 0.5}), ('bowl', 'ch2', 'Saffron Dormant', {'lufs': -26, 'pan': -14, 'verb': 0.5}), ('fin', 'ch3', 'Dial Depth', {'lufs': -23, 'pan': -10, 'verb': 0.45}), ('blue', 'ch4', 'Lattice Dormant', {'lufs': -25, 'pan': 12, 'verb': 0.45})]
world_song(__file__, '02-lamortdase.mid', 52, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=148, passes=1, intro_pass=False)

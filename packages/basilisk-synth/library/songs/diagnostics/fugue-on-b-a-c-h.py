"""Fugue on B-A-C-H (Nikolai Rimsky-Korsakov (1844-1908)), arranged for the diagnostics pack from a public-domain Mutopia edition
(sources/Rimsky.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['musicbox', 'erhu'], 'inner': 'bells', 'lh': 'cello', 'pad': 'errorpad', 'kit': 'kit'}
HEADER = {'title': 'Fugue on B-A-C-H', 'pack': 'diagnostics', 'kind': 'world', 'composer': 'Nikolai Rimsky-Korsakov (1844-1908)', 'source': 'Fugue on the name B-A-C-H, for piano: the exposition. Score: The Mutopia Project.', 'licence': 'The work: public domain (the composer died 1908). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1271', 'arranger': 'Algorithmic Industries house band', 'note': 'The exposition twice over broken beats: the subject on the broken music box and then the erhu, the inner voices on Noble Bell, the left hand on the cello pad, an error pad. Drums: Kit Manager 98 (Noise Channel Kit).'}
TRACKS = [('musicbox', 'ch1', 'Broken Music Box', {'lufs': -19, 'pan': -8, 'echo': 0.25, 'verb': 0.3}), ('erhu', 'ch2', 'Hollow Song', {'lufs': -20, 'pan': 10, 'echo': 0.15, 'verb': 0.35}), ('bells', 'ch3', 'Noble Bell', {'lufs': -24, 'pan': 22, 'echo': 0.3, 'verb': 0.4}), ('cello', 'ch4', 'Copper Veil', {'lufs': -23, 'pan': -14, 'verb': 0.3}), ('errorpad', 'ch5', 'Digital Veil', {'lufs': -28, 'verb': 0.4, 'width': 1.4}), ('kit', 'ch10', 'kit-manager:Noise Channel Kit', {'lufs': -19, 'verb': 0.08})]
world_song(__file__, 'Rimsky.mid', 112, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=160, passes=2, groove_name='breaks')

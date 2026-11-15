"""Pineapple Rag (Scott Joplin (1868-1917)), arranged for the workgroup-house pack from a public-domain Mutopia edition
(sources/PineappleRag.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['piano', 'organ'], 'inner': 'upright', 'lh': 'keys', 'bass': 'bass', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Pineapple Rag', 'pack': 'workgroup-house', 'kind': 'world', 'composer': 'Scott Joplin (1868-1917)', 'source': 'Pineapple Rag (1908): the introduction and first strains. Score: The Mutopia Project, from Seminary Music Co. (1908).', 'licence': 'The work: public domain (published 1908; the composer died 1917). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1899', 'arranger': 'Algorithmic Industries house band', 'note': 'Filtered house at 124 bpm, twice: the rag on the warehouse piano and then an organ, the inner voices on an upright, the left hand on a tine EP, the slap disco bass, a pad. Drums: Kit Manager 98 (Jack Box Kit).'}
TRACKS = [('piano', 'ch1', 'Warehouse Piano Stack', {'lufs': -19, 'pan': -6, 'echo': 0.12, 'verb': 0.2}), ('organ', 'ch2', 'Humid Organ', {'lufs': -21, 'pan': 12, 'verb': 0.15}), ('upright', 'ch3', 'Cable Upright', {'lufs': -24, 'pan': 18, 'verb': 0.2}), ('keys', 'ch4', 'Coral Ballad', {'lufs': -24, 'pan': -20, 'verb': 0.25}), ('bass', 'ch5', 'Slap Disco Bass', {'lufs': -19}), ('pad', 'ch6', 'Midnight Haze', {'lufs': -26, 'verb': 0.35, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Jack Box Kit', {'lufs': -17, 'verb': 0.05})]
world_song(__file__, 'PineappleRag.mid', 124, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=128, passes=2, groove_name='house')

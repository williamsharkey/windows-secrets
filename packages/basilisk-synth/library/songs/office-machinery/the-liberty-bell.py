"""The Liberty Bell (John Philip Sousa (1854-1932)), arranged for the office-machinery pack from a public-domain Mutopia edition
(sources/TheLibertyBell.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['bugle', 'beep'], 'lh': 'lowbugle', 'bass': 'drives', 'kit': 'kit'}
HEADER = {'title': 'The Liberty Bell', 'pack': 'office-machinery', 'kind': 'world', 'composer': 'John Philip Sousa (1854-1932)', 'source': 'The Liberty Bell, march (1893), piano edition: the introduction and first strains. Score: The Mutopia Project, from The John Church Company.', 'licence': 'The work: public domain (published 1893; the composer died 1932). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=625', 'arranger': 'Algorithmic Industries house band', 'note': 'A march in 6/8 for the computer room, twice: the civil-defence bugle and then the PC speaker on the tune, the low bugle on the accompaniment, twelve drives on the bass, a spacebar kit.'}
TRACKS = [('bugle', 'ch1', 'Signal Uplink', {'lufs': -19, 'pan': -4, 'verb': 0.3}), ('beep', 'ch2', 'Cedar Hat', {'lufs': -22, 'pan': 16, 'echo': 0.15}), ('lowbugle', 'ch3', 'White Dive', {'lufs': -23, 'pan': -18, 'verb': 0.3}), ('drives', 'ch4', 'Ocean Crowd', {'lufs': -20}), ('kit', 'ch10', 'Solar Haze', {'lufs': -18, 'verb': 0.08})]
world_song(__file__, 'TheLibertyBell.mid', 200, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=192, passes=2)

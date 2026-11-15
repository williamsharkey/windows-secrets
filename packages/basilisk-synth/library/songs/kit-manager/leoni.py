"""Leoni (Hebrew melody (Yigdal), adapted by Meyer Lyon (18th century)), arranged for the kit-manager pack from a public-domain Mutopia edition
(sources/Leoni.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['calculator', 'typingpool'], 'lh': 'signalbells', 'bass': 'relayroom', 'kit': 'kit'}
HEADER = {'title': 'Leoni', 'pack': 'kit-manager', 'kind': 'world', 'composer': 'Hebrew melody (Yigdal), adapted by Meyer Lyon (18th century)', 'source': 'Leoni, the Yigdal melody as sung by Meyer Lyon in London (18th century), as a four-part hymn. Score: The Mutopia Project.', 'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=525', 'arranger': 'Algorithmic Industries house band', 'note': "Four verses on Kit Manager 98: the melody on Calculator Bureau and Typing Pool's tuned keys in turn, the lower voices on Signal Bells and Relay Room's, a break on the Breaker Box Kit."}
TRACKS = [('calculator', 'ch1', 'Calculator Bureau', {'lufs': -19, 'pan': 6, 'echo': 0.2, 'verb': 0.3}), ('typingpool', 'ch2', 'Typing Pool', {'lufs': -20, 'pan': 24, 'echo': 0.15, 'verb': 0.25}), ('signalbells', 'ch3', 'Signal Bells', {'lufs': -24, 'pan': -22, 'echo': 0.2, 'verb': 0.35}), ('relayroom', 'ch4', 'Relay Room', {'lufs': -21, 'verb': 0.15}), ('kit', 'ch10', 'Breaker Box Kit', {'lufs': -17, 'verb': 0.06})]
world_song(__file__, 'Leoni.mid', 116, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=4, groove_name='breaks', ranges={'lead': (72, 84), 'lh': (60, 67), 'bass': (60, 72)})

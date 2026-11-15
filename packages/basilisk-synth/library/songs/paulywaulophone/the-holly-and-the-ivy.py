"""The Holly and the Ivy (English traditional), arranged for the paulywaulophone pack from a public-domain Mutopia edition
(sources/thehollyandtheivy.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['hum', 'sax', 'organ', 'chorus', 'hum'], 'bass': 'bass', 'pad': 'doo', 'kit': 'kit'}
HEADER = {'title': 'The Holly and the Ivy', 'pack': 'paulywaulophone', 'kind': 'world', 'composer': 'English traditional', 'source': 'The Holly and the Ivy, English traditional carol. Score: The Mutopia Project.', 'licence': 'The work: traditional, public domain. The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=644', 'arranger': 'Algorithmic Industries house band', 'note': 'An office singalong, five verses: the hum from the back row, the sax, the bee-buzzing organ and the chorus take the tune in turn, the bass from Accounts, the doo-doo choir. Sounds by Paul Chauncy.'}
TRACKS = [('hum', 'ch1', 'Electric Vox', {'lufs': -19, 'pan': 4, 'verb': 0.3}), ('sax', 'ch2', 'Dial Beam', {'lufs': -20, 'pan': -20, 'echo': 0.1, 'verb': 0.3}), ('organ', 'ch3', 'Mint Voice', {'lufs': -21, 'pan': 20, 'verb': 0.2}), ('chorus', 'ch4', 'Felt Chorus', {'lufs': -21, 'pan': 10, 'verb': 0.4}), ('bass', 'ch5', 'Wired Anchor', {'lufs': -20}), ('doo', 'ch6', 'Remote Haze', {'lufs': -25, 'verb': 0.35, 'width': 1.3}), ('kit', 'ch10', 'Honey Drift', {'lufs': -21, 'verb': 0.08})]
world_song(__file__, 'thehollyandtheivy.mid', 120, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=5, groove_name='waltz')

"""Good King Wenceslas (Traditional (Piae Cantiones, 1582)), arranged for the w3x-heritage pack from a public-domain Mutopia edition
(sources/GoodKingWenceslas.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['piano', 'whistle', 'horn'], 'lh': 'chords', 'bass': 'bass', 'pad': 'pad'}
HEADER = {'title': 'Good King Wenceslas', 'pack': 'w3x-heritage', 'kind': 'world', 'composer': 'Traditional (Piae Cantiones, 1582)', 'source': 'Good King Wenceslas: the 1582 spring carol "Tempus adest floridum" with J. M. Neale\'s 1853 words. Score: The Mutopia Project.', 'licence': 'The work: public domain (melody 1582; words 1853). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=905', 'arranger': 'Algorithmic Industries house band', 'note': 'Three verses on the six Windows 3.1 sounds: the ding piano, the ringout whistle and the tada horn take the tune in turn, ding chords, a ding bass, a ringout pad.'}
TRACKS = [('piano', 'ch1', 'Still Upright', {'lufs': -19, 'pan': 6, 'verb': 0.25}), ('whistle', 'ch2', 'Gentle Whistle', {'lufs': -20, 'pan': 14, 'echo': 0.15, 'verb': 0.3}), ('horn', 'ch3', 'Indigo Wire', {'lufs': -20, 'pan': -12, 'verb': 0.3}), ('chords', 'ch4', 'Western Chords', {'lufs': -24, 'pan': -16, 'verb': 0.2}), ('bass', 'ch5', 'Field Bass', {'lufs': -20, 'verb': 0.15}), ('pad', 'ch6', 'Honey Haze', {'lufs': -29, 'verb': 0.4})]
world_song(__file__, 'GoodKingWenceslas.mid', 108, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=3)

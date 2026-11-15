"""Saakorasa (Japanese traditional), arranged for the garden-rhythm pack from a public-domain Mutopia edition
(sources/J95004-Saakorasa.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['steelpan', 'mallets', 'hoover', 'steelpan', 'mallets', 'hoover'], 'bass': 'organbass', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Saakorasa', 'pack': 'garden-rhythm', 'kind': 'world', 'composer': 'Japanese traditional', 'source': 'Saakorasa, as printed for shamisen in Nagai and Obata, "Seiyo gakufu Nihon zokkyokushu" (Osaka: Miki Shoten, 1895). Score: The Mutopia Project.', 'licence': 'The work: traditional, public domain; the source was printed in 1895. The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1764', 'arranger': 'Algorithmic Industries house band', 'note': 'Early-90s rave, six times through: the shamisen tune on the steelpan, the marimba and the hoover in turn, a rave-organ bass on the chord roots, the organ pad, breakbeats on the radio kit. All from the pack.'}
TRACKS = [('steelpan', 'ch1', 'Digital Tower', {'lufs': -20, 'pan': 12, 'echo': 0.3, 'verb': 0.3}), ('mallets', 'ch2', 'Lagoon Mallets', {'lufs': -21, 'pan': -22, 'echo': 0.2, 'verb': 0.3}), ('hoover', 'ch3', 'Lagoon Stab', {'lufs': -21, 'width': 1.2, 'verb': 0.15}), ('organbass', 'ch4', 'Molten Brass', {'lufs': -20}), ('pad', 'ch5', 'Bakelite Bloom', {'lufs': -26, 'verb': 0.35, 'width': 1.4}), ('kit', 'ch10', 'Second Bloom', {'lufs': -17, 'verb': 0.05})]
world_song(__file__, 'J95004-Saakorasa.mid', 132, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=6, groove_name='breaks')

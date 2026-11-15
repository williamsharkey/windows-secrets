"""Yanreso Hoi (Japanese traditional), arranged for the game-port pack from a public-domain Mutopia edition
(sources/J95000-YanresoHoi.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['lead', 'lead2', 'lead3'], 'bass': 'bass', 'pad': 'arp', 'kit': 'kit'}
HEADER = {'title': 'Yanreso Hoi', 'pack': 'game-port', 'kind': 'world', 'composer': 'Japanese traditional', 'source': 'Yanreso Hoi, as printed for shamisen in Nagai and Obata, "Seiyo gakufu Nihon zokkyokushu" (Osaka: Miki Shoten, 1895). Score: The Mutopia Project.', 'licence': 'The work: traditional, public domain; the source was printed in 1895. The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1760', 'arranger': 'Algorithmic Industries house band', 'note': 'Six times through as a chiptune: the shamisen tune on three pulse leads in turn, a pulse bass on the chord roots, held chords on a pulse, the noise-channel kit.'}
TRACKS = [('lead', 'ch1', 'Midnight Signal', {'lufs': -20, 'pan': -8, 'echo': 0.12}), ('lead2', 'ch2', 'Second Ray', {'lufs': -21, 'pan': 20, 'echo': 0.12}), ('lead3', 'ch3', 'Ivory Signal', {'lufs': -21, 'pan': -20, 'echo': 0.12}), ('bass', 'ch4', 'Waxed Line', {'lufs': -19}), ('arp', 'ch5', 'Lucid Line', {'lufs': -26, 'pan': 24}), ('kit', 'ch10', 'kit-manager:Noise Channel Kit', {'lufs': -19, 'verb': 0.05})]
world_song(__file__, 'J95000-YanresoHoi.mid', 150, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=6, groove_name='synthpop')

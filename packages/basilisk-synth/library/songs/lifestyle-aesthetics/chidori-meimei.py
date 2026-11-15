"""Chidori Meimei (Japanese traditional), arranged for the lifestyle-aesthetics pack from a public-domain Mutopia edition
(sources/J95006-ChidoriMeimei.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['kalimba', 'tines', 'glass'], 'bass': 'bass', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Chidori Meimei', 'pack': 'lifestyle-aesthetics', 'kind': 'world', 'composer': 'Japanese traditional', 'source': 'Chidori Meimei, as printed for shamisen in Nagai and Obata, "Seiyo gakufu Nihon zokkyokushu" (Osaka: Miki Shoten, 1895). Score: The Mutopia Project.', 'licence': 'The work: traditional, public domain; the source was printed in 1895. The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1765', 'arranger': 'Algorithmic Industries house band', 'note': 'Three times through over a slow mall-pop groove: the shamisen tune on kalimba, atrium keys and glass keyboard in turn, a slow-jam bass on the chord roots, the weather-map pad. Drums: Kit Manager 98 (Echo Chamber Kit).'}
TRACKS = [('kalimba', 'ch1', 'Hydro Kalimba', {'lufs': -20, 'pan': -8, 'echo': 0.25, 'verb': 0.35}), ('tines', 'ch2', 'Atrium Keys', {'lufs': -20, 'pan': 8, 'echo': 0.15, 'verb': 0.3}), ('glass', 'ch3', 'Glass Keyboard', {'lufs': -22, 'pan': 20, 'echo': 0.3, 'verb': 0.4}), ('bass', 'ch4', 'Slow Jam Bass', {'lufs': -20}), ('pad', 'ch5', 'Weather Map Pad', {'lufs': -27, 'verb': 0.4, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', {'lufs': -20, 'verb': 0.15})]
world_song(__file__, 'J95006-ChidoriMeimei.mid', 96, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=3, groove_name='boombap')

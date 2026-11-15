"""Kontakion of Christmas (Dmitry Bortniansky (1751-1825)), arranged for the trance-connectivity pack from a public-domain Mutopia edition
(sources/bortniansky-xmas-kontakion.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['lead', 'violin'], 'inner': 'choir', 'lh': 'piano', 'bass': 'bass', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Kontakion of Christmas', 'pack': 'trance-connectivity', 'kind': 'world', 'composer': 'Dmitry Bortniansky (1751-1825)', 'source': 'Kontakion of Christmas, for four voices: the first section. Score: The Mutopia Project.', 'licence': 'The work: public domain (the composer died 1825). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1323', 'arranger': 'Algorithmic Industries house band', 'note': "Trance at 136 bpm, twice: the Russian Orthodox hymn's top voice on the lead and then a violin lead, the inner voices on a choir, the lower voices on the breakdown grand, a bass, a pad. Drums: Kit Manager 98 (Punch Kick Kit)."}
TRACKS = [('lead', 'ch1', 'Neon Solo', {'lufs': -19, 'pan': 4, 'echo': 0.25, 'verb': 0.3}), ('violin', 'ch2', 'Blue Signal', {'lufs': -20, 'pan': -6, 'echo': 0.15, 'verb': 0.35}), ('choir', 'ch3', 'Coral Tide', {'lufs': -24, 'verb': 0.45, 'width': 1.3}), ('piano', 'ch4', 'Breakdown Grand', {'lufs': -22, 'pan': -4, 'verb': 0.4}), ('bass', 'ch5', 'Waxed Weight', {'lufs': -19}), ('pad', 'ch6', 'Grey Mist', {'lufs': -25, 'verb': 0.4, 'width': 1.4}), ('kit', 'ch10', 'kit-manager:Punch Kick Kit', {'lufs': -16.5, 'verb': 0.05})]
world_song(__file__, 'bortniansky-xmas-kontakion.mid', 136, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=160, passes=2, groove_name='trance')

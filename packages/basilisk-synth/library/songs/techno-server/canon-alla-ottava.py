"""Canon alla Ottava (Johann Sebastian Bach (1685-1750)), arranged for the techno-server pack from a public-domain Mutopia edition
(sources/contrapunctusXII.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['morse', 'lead'], 'lh': 'strings', 'bass': 'sub', 'kit': 'kit'}
HEADER = {'title': 'Canon alla Ottava', 'pack': 'techno-server', 'kind': 'world', 'composer': 'Johann Sebastian Bach (1685-1750)', 'source': 'Die Kunst der Fuge, BWV 1080: Contrapunctus XII, Canon alla Ottava: the opening. Score: The Mutopia Project, from Breitkopf & Hartel.', 'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=746', 'arranger': 'Algorithmic Industries house band', 'note': "Techno at 126 bpm, twice: the canon's upper voice on morse blips and then the motor-whine lead, its lower voice on Detroit strings, a hit on the inner notes, an offbeat sub. Drums: Kit Manager 98 (Long Boom Kit)."}
TRACKS = [('morse', 'ch1', 'Granite Line', {'lufs': -21, 'pan': -10, 'echo': 0.4, 'verb': 0.15}), ('lead', 'ch2', 'Soft Pilot', {'lufs': -20, 'pan': 8, 'echo': 0.3, 'verb': 0.2}), ('strings', 'ch4', 'Motor City Strings', {'lufs': -23, 'pan': -14, 'verb': 0.35}), ('sub', 'ch5', 'Dot Sub', {'lufs': -19}), ('kit', 'ch10', 'kit-manager:Long Boom Kit', {'lufs': -16.5, 'verb': 0.04})]
world_song(__file__, 'contrapunctusXII.mid', 126, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=162, passes=2, groove_name='techno')

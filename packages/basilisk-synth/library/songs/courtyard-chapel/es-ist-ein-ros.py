"""Es ist ein' Ros entsprungen (German traditional (16th century)), arranged for the courtyard-chapel pack from a public-domain Mutopia edition
(sources/es_ist_ein_ros.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['psaltery', 'harp', 'dantranh'], 'lh': 'harpsichord', 'inner': 'bells', 'bass': 'strumstick', 'pad': 'drone'}
HEADER = {'title': "Es ist ein' Ros entsprungen", 'pack': 'courtyard-chapel', 'kind': 'world', 'composer': 'German traditional (16th century)', 'source': "Es ist ein' Ros entsprungen, a German carol first printed in the Speierisches Gebetbuch (1599), in a four-part hymn setting. Score: The Mutopia Project.", 'licence': 'The work: traditional, public domain (16th century). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1240', 'arranger': 'Algorithmic Industries house band', 'note': 'The carol three times: the tune on psaltery, folk harp and dan tranh in turn, the lower voices on the harpsichord, hand chimes on the alto, a strumstick bass and a didgeridoo bourdon.'}
TRACKS = [('psaltery', 'ch1', 'Amber Ticks', {'lufs': -19, 'pan': 8, 'verb': 0.35}), ('harp', 'ch2', 'Glass Spool', {'lufs': -20, 'pan': 24, 'verb': 0.35}), ('dantranh', 'ch3', 'Chrome Pick', {'lufs': -20, 'pan': -18, 'verb': 0.3}), ('harpsichord', 'ch4', 'Brass Ballad', {'lufs': -23, 'pan': -28, 'verb': 0.25}), ('bells', 'ch5', 'Orbital Ring', {'lufs': -25, 'pan': 20, 'verb': 0.45}), ('strumstick', 'ch6', 'Floor Harp', {'lufs': -23, 'pan': -6, 'verb': 0.15}), ('drone', 'ch7', 'Hotel Uplink', {'lufs': -29, 'verb': 0.35})]
world_song(__file__, 'es_ist_ein_ros.mid', 80, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=3)

"""Polonaise in G minor (attributed to Johann Sebastian Bach), arranged for the retro-display pack from a public-domain Mutopia edition
(sources/BWV-119.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['lead', 'sax', 'arp', 'lead', 'sax'], 'lh': 'ep', 'bass': 'bass', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Polonaise in G minor', 'pack': 'retro-display', 'kind': 'world', 'composer': 'attributed to Johann Sebastian Bach', 'source': 'Polonaise in G minor, BWV Anh. 119, from the Notebook for Anna Magdalena Bach (1725). Score: The Mutopia Project, from the Bach-Gesellschaft Ausgabe.', 'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1016', 'arranger': 'Algorithmic Industries house band', 'note': 'Five times through as a synthwave waltz: the chrome lead, the rooftop sax and a kalimba line take turns, tine EP on the left hand, brass swells, the rumble bass, a pad. Drums: Kit Manager 98 (Echo Chamber Kit).'}
TRACKS = [('lead', 'ch1', 'Chrome Brass Lead', {'lufs': -19, 'pan': 4, 'echo': 0.2, 'verb': 0.3}), ('sax', 'ch2', 'Rooftop Sax Lead', {'lufs': -20, 'pan': -6, 'echo': 0.2, 'verb': 0.35}), ('arp', 'ch3', 'Violet Chords', {'lufs': -22, 'pan': 22, 'echo': 0.3}), ('ep', 'ch4', 'Shiny Tine Plaza', {'lufs': -24, 'pan': -18, 'verb': 0.25}), ('bass', 'ch6', 'Saffron Rumble', {'lufs': -19}), ('pad', 'ch7', 'Northern Bloom', {'lufs': -27, 'verb': 0.4, 'width': 1.4}), ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', {'lufs': -18, 'verb': 0.12})]
world_song(__file__, 'BWV-119.mid', 116, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=5)

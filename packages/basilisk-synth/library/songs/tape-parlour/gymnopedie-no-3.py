"""Gymnopedie No. 3 (Erik Satie (1866-1925)), arranged for the tape-parlour pack from a public-domain Mutopia edition
(sources/gymnopedie_3.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['flute'], 'inner': 'choir', 'lh': 'piano', 'bass': 'bass', 'pad': 'organ'}
HEADER = {'title': 'Gymnopedie No. 3', 'pack': 'tape-parlour', 'kind': 'world', 'composer': 'Erik Satie (1866-1925)', 'source': 'Gymnopedie No. 3 for piano (1888). Score: The Mutopia Project, typeset from the Dover edition.', 'licence': 'The work: public domain (published 1888; the composer died 1925). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=39', 'arranger': 'Algorithmic Industries house band', 'note': 'The whole piece at 66 bpm on tape-replay voices: the tune on the flute, the chords on choir and parlour piano, a contrabass, the 8-foot organ stop.'}
TRACKS = [('flute', 'ch1', 'Dusk Pilot', {'lufs': -19, 'pan': -8, 'verb': 0.35}), ('choir', 'ch2', 'Modular Chorus', {'lufs': -23, 'pan': 10, 'verb': 0.4}), ('piano', 'ch3', 'Swift Ivories', {'lufs': -22, 'pan': 16, 'verb': 0.3}), ('bass', 'ch4', 'Vinyl Section', {'lufs': -22}), ('organ', 'ch5', 'Noble Stops', {'lufs': -27, 'pan': -6, 'verb': 0.35})]
world_song(__file__, 'gymnopedie_3.mid', 66, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=1, intro_pass=False)

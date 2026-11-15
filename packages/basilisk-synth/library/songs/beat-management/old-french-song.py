"""Old French Song (Pyotr Ilyich Tchaikovsky (1840-1893)), arranged for the beat-management pack from a public-domain Mutopia edition
(sources/16OldFrenchSong.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['piano', 'flute', 'vibes'], 'lh': 'ep', 'bass': 'bass', 'pad': 'strings', 'kit': 'kit'}
HEADER = {'title': 'Old French Song', 'pack': 'beat-management', 'kind': 'world', 'composer': 'Pyotr Ilyich Tchaikovsky (1840-1893)', 'source': 'Old French Song, Album for the Young, Op. 39 No. 16 (1878). Score: The Mutopia Project, from Schirmer (1904).', 'licence': 'The work: public domain (published 1878; the composer died 1893). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=2080', 'arranger': 'Algorithmic Industries house band', 'note': 'A lo-fi beat at 84 bpm, three times: the tune on the upright piano, the flute and the vibes in turn, the left hand on tines, upright bass, violins. Drums: Kit Manager 98 (Twelve-Bit Crate Kit).'}
TRACKS = [('piano', 'ch1', 'Cedar Study', {'lufs': -20, 'pan': -8, 'verb': 0.25, 'lp': 9000}), ('flute', 'ch2', 'Civic Wire', {'lufs': -20, 'pan': 8, 'echo': 0.2, 'verb': 0.3}), ('vibes', 'ch3', 'Study Vibes', {'lufs': -22, 'pan': 22, 'echo': 0.2, 'verb': 0.3}), ('ep', 'ch4', 'Wide Flick', {'lufs': -23, 'pan': -18, 'verb': 0.25}), ('bass', 'ch5', 'Upright Thump', {'lufs': -19}), ('strings', 'ch6', 'Golden Section', {'lufs': -25, 'verb': 0.35}), ('kit', 'ch10', 'kit-manager:Twelve-Bit Crate Kit', {'lufs': -17, 'verb': 0.06})]
world_song(__file__, '16OldFrenchSong.mid', 84, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, passes=3, groove_name='boombap')

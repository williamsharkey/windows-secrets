"""By the Fireside (January) (Pyotr Ilyich Tchaikovsky (1840-1893)), arranged for the screen-saver pack from a public-domain Mutopia edition
(sources/Tschaikowsky-op37.1.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['flute'], 'inner': 'glass', 'lh': 'marimba', 'bass': 'bowl', 'pad': 'pad'}
HEADER = {'title': 'By the Fireside (January)', 'pack': 'screen-saver', 'kind': 'world', 'composer': 'Pyotr Ilyich Tchaikovsky (1840-1893)', 'source': 'The Seasons, Op. 37a: January, "By the Fireside" (1876): the first section. Score: The Mutopia Project, from Rob. Forberg, Leipzig.', 'licence': 'The work: public domain (published 1876; the composer died 1893). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1171', 'arranger': 'Algorithmic Industries house band', 'note': 'The first section at 72 bpm: the breathy flute on the tune, the glass harp on the inner voices, the marimba on the left hand, a singing-bowl bass, a string pad.'}
TRACKS = [('flute', 'ch1', 'Breath Flute', {'lufs': -20, 'pan': 4, 'echo': 0.15, 'verb': 0.45}), ('glass', 'ch2', 'Ivory Canopy', {'lufs': -24, 'pan': -14, 'verb': 0.4}), ('marimba', 'ch3', 'Water Marimba', {'lufs': -24, 'pan': 22, 'echo': 0.2, 'verb': 0.35}), ('bowl', 'ch4', 'Northern Dormant', {'lufs': -25, 'verb': 0.3}), ('pad', 'ch5', 'Global Pad', {'lufs': -26, 'verb': 0.45, 'width': 1.4})]
world_song(__file__, 'Tschaikowsky-op37.1.mid', 72, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=153, passes=1, intro_pass=False)

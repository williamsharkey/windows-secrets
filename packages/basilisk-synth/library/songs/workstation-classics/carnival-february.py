"""Carnival (February) (Pyotr Ilyich Tchaikovsky (1840-1893)), arranged for the workstation-classics pack from a public-domain Mutopia edition
(sources/Tschaikowsky-op37.2.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['lead', 'flute'], 'inner': 'pluck', 'lh': 'pizz', 'bass': 'bass', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Carnival (February)', 'pack': 'workstation-classics', 'kind': 'world', 'composer': 'Pyotr Ilyich Tchaikovsky (1840-1893)', 'source': 'The Seasons, Op. 37a: February, "Carnival" (1876): the first section. Score: The Mutopia Project, from Rob. Forberg, Leipzig.', 'licence': 'The work: public domain (published 1876; the composer died 1893). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1398', 'arranger': 'Algorithmic Industries house band', 'note': 'Eurodance at 132 bpm, twice: the carnival tune on a lead and the flute solo, arena plucks and pizzicato on the accompaniment, the mono bass, a pad. Drums: Kit Manager 98 (Punch Kick Kit).'}
TRACKS = [('lead', 'ch1', 'Chrome Pilot', {'lufs': -19, 'pan': 4, 'echo': 0.2, 'verb': 0.25}), ('flute', 'ch2', 'Global Solo', {'lufs': -20, 'pan': -4, 'echo': 0.2, 'verb': 0.3}), ('pluck', 'ch3', 'Arena Pluck', {'lufs': -24, 'pan': -20, 'echo': 0.2}), ('pizz', 'ch4', 'Felt Pizz', {'lufs': -25, 'pan': 22}), ('bass', 'ch5', 'Ladder Mono Bass', {'lufs': -19}), ('pad', 'ch6', 'Pale Cloud', {'lufs': -26, 'verb': 0.35}), ('kit', 'ch10', 'kit-manager:Punch Kick Kit', {'lufs': -17, 'verb': 0.06})]
world_song(__file__, 'Tschaikowsky-op37.2.mid', 132, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=168, passes=2, groove_name='disco')

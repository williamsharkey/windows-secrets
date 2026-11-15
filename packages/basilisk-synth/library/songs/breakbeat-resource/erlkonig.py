"""Erlkonig (Franz Schubert (1797-1828)), arranged for the breakbeat-resource pack from a public-domain Mutopia edition
(sources/Erlkoenig.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['whistle', 'square', 'pilot'], 'lh': 'keys', 'bass': 'sub', 'pad': 'pad', 'kit': 'kit'}
HEADER = {'title': 'Erlkonig', 'pack': 'breakbeat-resource', 'kind': 'world', 'composer': 'Franz Schubert (1797-1828)', 'source': 'Erlkonig, D. 328 (1815): the opening. Score: The Mutopia Project.', 'licence': 'The work: public domain (published 1821; the composer died 1828). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1030', 'arranger': 'Algorithmic Industries house band', 'note': "Jungle at 170 bpm, three times: the voice part on the whistle, the square lead and a pilot lead, the piano's galloping octaves on an upright, a sub, the night-bus pad. Breaks: Kit Manager 98 (Breaker Box Kit)."}
TRACKS = [('whistle', 'ch1', 'Upper Whistle', {'lufs': -20, 'pan': 10, 'echo': 0.25, 'verb': 0.3}), ('square', 'ch2', 'Freestyle Square', {'lufs': -20, 'pan': -6, 'echo': 0.2}), ('pilot', 'ch3', 'Velvet Pilot', {'lufs': -20, 'pan': 4, 'echo': 0.2}), ('keys', 'ch4', 'Night Upright', {'lufs': -24, 'pan': -18, 'verb': 0.2}), ('sub', 'ch5', 'Sound System Sub', {'lufs': -19}), ('pad', 'ch6', 'Night Bus Pad', {'lufs': -26, 'verb': 0.4, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -16.5, 'verb': 0.06})]
world_song(__file__, 'Erlkoenig.mid', 170, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=128, passes=3, groove_name='jungle', up_tracks=[0], low_tracks=[1, 2])

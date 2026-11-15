"""Doumka (Pyotr Ilyich Tchaikovsky (1840-1893)), arranged for the polysynth-showroom pack from a public-domain Mutopia edition
(sources/dumka.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

ROLES = {'leads': ['lead', 'solo'], 'inner': 'fmpiano', 'lh': 'clav', 'bass': 'bass', 'pad': 'vstrings', 'kit': 'kit'}
HEADER = {'title': 'Doumka', 'pack': 'polysynth-showroom', 'kind': 'world', 'composer': 'Pyotr Ilyich Tchaikovsky (1840-1893)', 'source': 'Doumka, Op. 59 (1886): the opening section. Score: The Mutopia Project.', 'licence': 'The work: public domain (published 1886; the composer died 1893). The edition used: public domain (Mutopia). This arrangement: CC0-1.0.', 'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=341', 'arranger': 'Algorithmic Industries house band', 'note': 'The opening twice as 1985 synth-pop: a PWM lead then the buzzy lead on the tune, an FM piano on the inner voices, a clav on the left hand, the cream mono bass, vocoder strings. Drums: Kit Manager 98 (Breaker Box Kit).'}
TRACKS = [('lead', 'ch1', 'Silent Ray', {'lufs': -19, 'pan': 4, 'echo': 0.2, 'verb': 0.3}), ('solo', 'ch2', 'Wired Call', {'lufs': -20, 'pan': -6, 'echo': 0.2, 'verb': 0.3}), ('fmpiano', 'ch3', 'Stone Parlour', {'lufs': -23, 'pan': -18, 'verb': 0.3}), ('clav', 'ch4', 'Paper Recital', {'lufs': -25, 'pan': 24}), ('bass', 'ch5', 'Ivory Low', {'lufs': -20}), ('vstrings', 'ch6', 'Foggy Section', {'lufs': -25, 'verb': 0.4, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -18, 'verb': 0.15})]
world_song(__file__, 'dumka.mid', 112, HEADER, ROLES, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
           echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'level': -6},
           reverb={'size': 2.4, 'predelay': 20, 'tone': 5500, 'level': -5}, a=0, b=152, passes=2)

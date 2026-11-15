"""Chipnese (Spring Spring, CC0), re-voiced for the garden-rhythm pack: the notes of a 0CC-FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/chipnese.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {6: ('steelpan', 1, 0, 60, 88, 0.9), 7: ('mallets', 2, 12, 55, 84, 0.85), 3: ('organbass', 3, 12, 36, 55, 1.0), 2: ('stab', 4, 12, 55, 79, 0.8), 1: ('pan2', 5, 0, 60, 88, 0.8), 8: ('hoover', 6, -12, 48, 67, 0.8), 4: ('kit', 10, 'pad', 42, 0.8)}
HEADER = {'title': 'Chipnese', 'pack': 'garden-rhythm', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Chipnese, a 0CC-FamiTracker module (chipnese.0cc) from OpenGameArt (https://opengameart.org/sites/default/files/chipnese_0.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/chipnese', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '1f247922c637e7bf001ca2c06c6350ab5f96c39493ac8fc364ad6a46f08d35a0', 'note': "Played twice through: the NES module's VRC6 lines on the steelpan and marimbas, the triangle on the rave-organ bass, pulse 2 on a rave chord, pulse 1 on a steelpan peal, the VRC6 saw on the hoover, the noise on the radio kit."}
TRACKS = [('steelpan', 'ch1', 'Digital Tower', {'lufs': -20, 'pan': 12, 'echo': 0.25, 'verb': 0.3}), ('mallets', 'ch2', 'Lagoon Mallets', {'lufs': -22, 'pan': -22, 'verb': 0.3}), ('organbass', 'ch3', 'Molten Brass', {'lufs': -20}), ('stab', 'ch4', 'Winter Salute', {'lufs': -24, 'pan': 20}), ('pan2', 'ch5', 'Brass Peal', {'lufs': -25, 'pan': -12, 'echo': 0.2}), ('hoover', 'ch6', 'Lagoon Stab', {'lufs': -23, 'width': 1.2}), ('kit', 'ch10', 'Humid Haze', {'lufs': -19, 'verb': 0.05})]
module_song(__file__, 'chipnese.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2, cut=420)

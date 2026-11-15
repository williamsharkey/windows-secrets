"""Lasso Lady (congusbongus, CC0), re-voiced for the beat-management pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/lassolady.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('flute', 1, 12, 60, 84, 0.95), 2: ('bass', 2, 12, 33, 52, 1.0), 3: ('vibes', 3, 0, 60, 84, 0.8), 4: ('kit', 10, 'pad', 42, 0.8)}
HEADER = {'title': 'Lasso Lady', 'pack': 'beat-management', 'kind': 'chiptune', 'composer': 'congusbongus', 'source': 'Lasso Lady, a FamiTracker module (lassolady.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/lassolady_1.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/lasso-lady-seamless-loop', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'cb6bb1ceaa607e02ee74f099fb30876338423413a411285715bed7656e21494f', 'note': "Played twice through: the NES module's pulse 1 on the flute, pulse 2 on the upright bass, the triangle on vibes, the noise on Kit Manager 98 (Twelve-Bit Crate Kit)."}
TRACKS = [('flute', 'ch1', 'Civic Wire', {'lufs': -20, 'pan': 6, 'echo': 0.2, 'verb': 0.3}), ('bass', 'ch2', 'Cathode Groove', {'lufs': -19}), ('vibes', 'ch3', 'Study Vibes', {'lufs': -24, 'pan': 24, 'verb': 0.3}), ('kit', 'ch10', 'kit-manager:Twelve-Bit Crate Kit', {'lufs': -19, 'verb': 0.06})]
module_song(__file__, 'lassolady.notes.mid', 140, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

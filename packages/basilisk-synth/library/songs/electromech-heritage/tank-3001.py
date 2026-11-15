"""Tank 3001 (Spring Spring, CC0), re-voiced for the electromech-heritage pack: the notes of a 0CC-FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/Coding_Pirates_Showcase_OST_3_2a03.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('hootbass', 1, 24, 40, 58, 1.0), 2: ('pulse', 2, 12, 55, 81, 0.95), 3: ('marimba', 3, 12, 52, 76, 0.85), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Tank 3001', 'pack': 'electromech-heritage', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Tank 3001, a 0CC-FamiTracker module (Coding_Pirates_Showcase_OST_3_2a03.0cc) from OpenGameArt (https://opengameart.org/sites/default/files/Guropper.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/guropper', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '5cfdc3475f49dc5d3f352a9a6be67d21dd4209d35ddb7077c85fe7e3769f1ace', 'note': "Played four times through: the NES module's pulse 1 on the Ferranti hoot, pulse 2 on the CSIRAC pulse, the triangle on the relay marimba, the noise on Kit Manager 98 (Solenoid Lab)."}
TRACKS = [('hootbass', 'ch1', 'Ferranti Hoot', {'lufs': -19}), ('pulse', 'ch2', 'CSIRAC Pulse', {'lufs': -20, 'pan': 8, 'echo': 0.2}), ('marimba', 'ch3', 'Relay Marimba', {'lufs': -22, 'pan': -18, 'verb': 0.2}), ('kit', 'ch10', 'kit-manager:Solenoid Lab', {'lufs': -20, 'verb': 0.08})]
module_song(__file__, 'Coding_Pirates_Showcase_OST_3_2a03.notes.mid', 140, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=4)

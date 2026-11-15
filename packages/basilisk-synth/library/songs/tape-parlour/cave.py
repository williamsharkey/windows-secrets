"""Cave (Wolfgang_, CC0), re-voiced for the tape-parlour pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/Cave.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('bass', 1, 24, 36, 55, 1.0), 2: ('cellos', 2, 24, 45, 67, 0.9), 3: ('flute', 3, 12, 60, 84, 0.9), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.8)}
HEADER = {'title': 'Cave', 'pack': 'tape-parlour', 'kind': 'chiptune', 'composer': 'Wolfgang_', 'source': 'Cave, a FamiTracker module (Cave.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/cave_1.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/8-bit-cave-loop', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'be13735b4e5e625568dbb03b72750d9fb6802cb946fd74e3afd23e2c9b31f6af', 'note': "Played twice through on tape-replay voices: the NES module's pulse 1 on the contrabass, pulse 2 on the cellos, the triangle on the flute, the noise on Kit Manager 98 (Half-Time Kit)."}
TRACKS = [('bass', 'ch1', 'Lunar Bows', {'lufs': -20}), ('cellos', 'ch2', 'Warm Legato', {'lufs': -21, 'pan': -16, 'verb': 0.3}), ('flute', 'ch3', 'Kinetic Ray', {'lufs': -21, 'pan': 10, 'verb': 0.3}), ('kit', 'ch10', 'kit-manager:Half-Time Kit', {'lufs': -21, 'verb': 0.12, 'lp': 8000})]
module_song(__file__, 'Cave.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

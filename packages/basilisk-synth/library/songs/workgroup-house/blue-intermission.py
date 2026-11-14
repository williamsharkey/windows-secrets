"""Blue Intermission (congusbongus, CC0), re-voiced for the workgroup-house pack: the notes of a FastTracker 2 module from OpenGameArt played on
the pack's own presets (sources/cc0/blue_intermission.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('bass', 2, -24, 33, 52, 1.0), 4: ('rhodes', 3, 0, 50, 79, 0.9), 5: ('kit', 10, 'pad', 36, 1.0), 2: ('kit', 10, 'pad', 39, 1.0), 3: ('shaker', 11, 'pad', 60, 0.8), 6: ('kit', 10, 'pad', 46, 0.8)}
HEADER = {'title': 'Blue Intermission', 'pack': 'workgroup-house', 'kind': 'chiptune', 'composer': 'congusbongus', 'source': 'Blue Intermission, a FastTracker 2 module (blue_intermission.xm) from OpenGameArt (https://opengameart.org/sites/default/files/blue_intermission.xm_.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/blue-intermission', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'f28c417be6b073f49281e4c3ce1800dc6ef38d3f138cbb5cf1f99567975a009e', 'note': "Downtempo house at 87 bpm: the module's house bass on the slap disco bass, its Rhodes on the tine EP, its drums on Kit Manager 98 (Jack Box Kit), its shaker on the pack's Bright Shaker."}
TRACKS = [('bass', 'ch2', 'Slap Disco Bass', {'lufs': -19}), ('rhodes', 'ch3', 'Afterhours Tine', {'lufs': -21, 'pan': -12, 'echo': 0.18, 'verb': 0.25}), ('kit', 'ch10', 'kit-manager:Jack Box Kit', {'lufs': -17, 'verb': 0.05}), ('shaker', 'ch11', 'Bright Shaker', {'lufs': -28, 'pan': -30})]
module_song(__file__, 'blue_intermission.notes.mid', 87, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=246)

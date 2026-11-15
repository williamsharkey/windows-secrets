"""Map (SketchyLogic, CC0), re-voiced for the listening-post pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/Map.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {7: ('humpback', 1, 0, 60, 84, 0.9), 3: ('fin', 2, 12, 43, 60, 0.85), 6: ('blue', 3, 12, 50, 67, 0.8), 1: ('bowl', 4, 12, 60, 79, 0.8), 5: ('bloop', 5, 'pad', 19, 0.7)}
HEADER = {'title': 'Map', 'pack': 'listening-post', 'kind': 'chiptune', 'composer': 'SketchyLogic', 'source': 'Map, a FamiTracker module (Map.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/FTM.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/nes-shooter-music-5-tracks-3-jingles', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '6c80bb930bf50df4b1747a6c490970e41e5d4faa92a5081f46bdd7a6751d1e45', 'note': 'The NES map theme at half speed, twice, in the deep ocean: its VRC6 lead on the humpback, triangle and VRC6 bass on fin-whale and blue-whale drones, pulse 1 on a singing bowl, the samples on the bloop.'}
TRACKS = [('humpback', 'ch1', 'Ocean Shoreline', {'lufs': -20, 'pan': 4, 'echo': 0.25, 'verb': 0.5}), ('fin', 'ch2', 'Dial Depth', {'lufs': -23, 'pan': -12, 'verb': 0.45}), ('blue', 'ch3', 'Lattice Dormant', {'lufs': -25, 'pan': 12, 'verb': 0.45}), ('bowl', 'ch4', 'Saffron Dormant', {'lufs': -27, 'verb': 0.5}), ('bloop', 'ch5', 'Cedar Murmur', {'lufs': -26, 'verb': 0.4})]
module_song(__file__, 'Map.notes.mid', 70, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2, stretch=2.0)

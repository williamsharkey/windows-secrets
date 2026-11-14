"""Soft Then Loud (Phillip Miller (redactionary), CC0), re-voiced for the listening-post pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_11-soft_then_loud.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {3: ('fin', 1, 12, 43, 60, 0.9), 1: ('blue', 2, 0, 55, 67, 0.85), 2: ('humpback', 3, 12, 60, 84, 0.9), 4: ('bloop', 4, 'pad', 19, 0.6)}
HEADER = {'title': 'Soft Then Loud', 'pack': 'listening-post', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'soft then loud (11), a FamiTracker module (nes_11-soft_then_loud.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '1086c5b6d9edfcb98954bd8bf576e0e5e22a5af12752b12cf6c00ea0513045a1', 'note': 'The NES module at half speed in the deep ocean: the triangle on fin-whale drones, pulse 1 on blue-whale drones, pulse 2 on the humpback, the noise on the bloop.'}
TRACKS = [('fin', 'ch1', 'Dial Depth', {'lufs': -22, 'pan': -12, 'verb': 0.45}), ('blue', 'ch2', 'Lattice Dormant', {'lufs': -24, 'pan': 14, 'verb': 0.45}), ('humpback', 'ch3', 'Ocean Shoreline', {'lufs': -20, 'pan': 4, 'echo': 0.2, 'verb': 0.5}), ('bloop', 'ch4', 'Cedar Murmur', {'lufs': -26, 'verb': 0.4})]
module_song(__file__, 'nes_11-soft_then_loud.notes.mid', 60, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, stretch=2.0, cut=172)

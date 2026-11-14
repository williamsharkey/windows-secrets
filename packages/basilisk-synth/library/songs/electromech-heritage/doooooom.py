"""Doooooom (Phillip Miller (redactionary), CC0), re-voiced for the electromech-heritage pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_02-doom.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('hootbass', 1, 12, 36, 55, 1.0), 2: ('pulse', 2, 12, 55, 81, 0.95), 3: ('marimba', 3, 12, 52, 76, 0.85), 4: ('kit', 10, 'pad', 38, 0.9)}
HEADER = {'title': 'Doooooom', 'pack': 'electromech-heritage', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'Doooooom (2), a FamiTracker module (nes_02-doom.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '4e8d89f104ef349e369e3f3bec1b2a69484da8ca6bc6cfd22667e6d544ede2f9', 'note': "Played twice through: the NES module's pulse 1 on the Ferranti hoot, pulse 2 on the CSIRAC pulse, the triangle on the relay marimba, the noise on Kit Manager 98 (Relay Room)."}
TRACKS = [('hootbass', 'ch1', 'Ferranti Hoot', {'lufs': -19}), ('pulse', 'ch2', 'CSIRAC Pulse', {'lufs': -20, 'pan': 10, 'echo': 0.2, 'verb': 0.15}), ('marimba', 'ch3', 'Relay Marimba', {'lufs': -22, 'pan': -18, 'verb': 0.2}), ('kit', 'ch10', 'kit-manager:Relay Room', {'lufs': -19, 'verb': 0.08})]
module_song(__file__, 'nes_02-doom.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

"""World 7-8 (Phillip Miller (redactionary), CC0), re-voiced for the rom-reference pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_07-jazz.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 60, 84, 0.95), 2: ('tines', 2, 0, 52, 84, 0.85), 3: ('bass', 3, -12, 33, 52, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.85)}
HEADER = {'title': 'World 7-8', 'pack': 'rom-reference', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'World 7-8, a FamiTracker module (nes_07-jazz.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'fa685b8f913b3c6288be4af510930a2126b188acc57cc9886f99cf8ff26e4a47', 'note': "Jazz-fusion on workstation voices at 112 bpm: the NES module's pulse 1 on the lead, pulse 2 on the tines, the triangle on the bass, the noise on Kit Manager 98 (Breaker Box Kit)."}
TRACKS = [('lead', 'ch1', 'Cathode Lead', {'lufs': -19, 'pan': 4, 'echo': 0.2, 'verb': 0.3}), ('tines', 'ch2', 'Jade Tines', {'lufs': -22, 'pan': -16, 'echo': 0.15, 'verb': 0.3}), ('bass', 'ch3', 'Neon Basement', {'lufs': -20}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -18, 'verb': 0.1})]
module_song(__file__, 'nes_07-jazz.notes.mid', 112, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6})

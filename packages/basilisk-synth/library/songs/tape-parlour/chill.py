"""Chill (Phillip Miller (redactionary), CC0), re-voiced for the tape-parlour pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_23-chill.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('flute', 1, 0, 60, 84, 0.95), 2: ('violas', 2, 12, 55, 76, 0.85), 3: ('bass', 3, -12, 36, 55, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.8)}
HEADER = {'title': 'Chill', 'pack': 'tape-parlour', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'chill (23), a FamiTracker module (nes_23-chill.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'a4adce0acd373c153bc0f7c26cee5e9a02335a31c50d07f0727932857db1a64d', 'note': "Played three times through on tape-replay voices: the NES module's pulse 1 on the flute, pulse 2 on the violas, the triangle on the contrabass, the noise on Kit Manager 98 (Half-Time Kit)."}
TRACKS = [('flute', 'ch1', 'Dusk Pilot', {'lufs': -19, 'pan': -8, 'verb': 0.3}), ('violas', 'ch2', 'Hollow Legato', {'lufs': -22, 'pan': 20, 'verb': 0.35}), ('bass', 'ch3', 'Vinyl Section', {'lufs': -21}), ('kit', 'ch10', 'kit-manager:Half-Time Kit', {'lufs': -20, 'verb': 0.12, 'lp': 9000})]
module_song(__file__, 'nes_23-chill.notes.mid', 112, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=3)

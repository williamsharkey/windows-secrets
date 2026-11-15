"""Dark 8-Bit Melody (qubodup, CC0), re-voiced for the diagnostics pack: the notes of a FastTracker 2 module from OpenGameArt played on
the pack's own presets (sources/cc0/8bitMelody.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('musicbox', 1, 12, 60, 88, 0.95), 4: ('erhu', 2, 12, 60, 81, 0.85), 3: ('stutter', 3, 0, 60, 76, 0.8), 2: ('thud', 4, 'split', [(50, 36), (127, 60)], 0.9)}
HEADER = {'title': 'Dark 8-Bit Melody', 'pack': 'diagnostics', 'kind': 'chiptune', 'composer': 'qubodup', 'source': 'Dark 8-Bit Melody, a FastTracker 2 module (8bitMelody.xm) from OpenGameArt (https://opengameart.org/sites/default/files/dark_8_bit_melody_sources.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/dark-8bit-song', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '52ee4abbded7d457abed7bbe1c9c7ee2981ac88b6cad0d1b300e6471908ee636', 'note': "Played twice through: the module's pianos on the broken music box and the erhu, its overdrive on stutters, its noises on critical-stop thuds."}
TRACKS = [('musicbox', 'ch1', 'Broken Music Box', {'lufs': -20, 'pan': -8, 'echo': 0.25, 'verb': 0.35}), ('erhu', 'ch2', 'Hollow Song', {'lufs': -21, 'pan': 12, 'verb': 0.35}), ('stutter', 'ch3', 'Stutter Copy Paste', {'lufs': -25, 'pan': 18, 'echo': 0.3}), ('thud', 'ch4', 'Echo Click', {'lufs': -21})]
module_song(__file__, '8bitMelody.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

"""Level 0 (controllerhead, CC0), re-voiced for the workgroup-house pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nrom_level0.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('organ', 1, 12, 55, 79, 0.85), 2: ('stab', 2, 0, 52, 72, 0.85), 3: ('bass', 3, 0, 33, 52, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Level 0', 'pack': 'workgroup-house', 'kind': 'chiptune', 'composer': 'controllerhead', 'source': 'Level 0, a FamiTracker module (nrom_level0.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/nrom_level0_famitracker.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/nes-level-0', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '1d2b56cdf317107b38ba7b9d8083741c39e4e2199e5a1ecb0d106d0c9e7b36a8', 'note': "Played twice through as house: the NES module's pulse 1 on an organ, pulse 2 on a stab, the triangle on the bass, the noise on Kit Manager 98 (Jack Box Kit)."}
TRACKS = [('organ', 'ch1', 'Gentle Revival', {'lufs': -21, 'pan': -8, 'echo': 0.15}), ('stab', 'ch2', 'Rainy Accent', {'lufs': -22, 'pan': 14, 'echo': 0.2}), ('bass', 'ch3', 'Remote Foundation', {'lufs': -19}), ('kit', 'ch10', 'kit-manager:Jack Box Kit', {'lufs': -17, 'verb': 0.05})]
module_song(__file__, 'nrom_level0.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

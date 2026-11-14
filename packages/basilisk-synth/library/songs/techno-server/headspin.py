"""Headspin (congusbongus, CC0), re-voiced for the techno-server pack: the notes of a FastTracker 2 module from OpenGameArt played on
the pack's own presets (sources/cc0/headspin.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('kit', 10, 'pad', 36, 1.0), 3: ('kit', 10, 'pad', 39, 1.0), 4: ('kit', 10, 'pad', 46, 0.8), 2: ('click', 11, 'pad', 60, 0.8), 5: ('sub', 2, -24, 36, 55, 1.0), 6: ('stab', 3, -12, 52, 76, 0.9), 7: ('lead', 4, -12, 60, 84, 0.95), 9: ('pad', 5, 0, 55, 72, 0.9), 8: ('strings', 6, 0, 53, 72, 0.85)}
HEADER = {'title': 'Headspin', 'pack': 'techno-server', 'kind': 'chiptune', 'composer': 'congusbongus', 'source': 'Headspin, a FastTracker 2 module (headspin.xm) from OpenGameArt (https://opengameart.org/sites/default/files/headspin.xm_.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/headspin', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '0d217fe3e41273ba673c66fc6b0bccaaa573bd13204763da4522d961eebd464c', 'note': "Techno at 118 bpm: the module's VS bass on the dot sub, its guitar riff on a dub stab, its synth on the motor-whine lead, its pad and Rhodes on the singing-bowl pad and Detroit strings, its silverware on Coded Click, its drums on Kit Manager 98 (Long Boom Kit)."}
TRACKS = [('kit', 'ch10', 'kit-manager:Long Boom Kit', {'lufs': -17, 'verb': 0.04}), ('click', 'ch11', 'Coded Click', {'lufs': -28, 'pan': -28, 'echo': 0.2}), ('sub', 'ch2', 'Dot Sub', {'lufs': -19}), ('stab', 'ch3', 'Slow Stab', {'lufs': -22, 'pan': -10, 'echo': 0.45, 'verb': 0.2}), ('lead', 'ch4', 'Soft Pilot', {'lufs': -21, 'pan': 8, 'echo': 0.3, 'verb': 0.2}), ('pad', 'ch5', 'Electric Haze', {'lufs': -26, 'verb': 0.4, 'width': 1.3}), ('strings', 'ch6', 'Motor City Strings', {'lufs': -24, 'pan': 14, 'verb': 0.35})]
module_song(__file__, 'headspin.notes.mid', 118, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=340)

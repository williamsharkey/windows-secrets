"""Leap (nene, CC0), re-voiced for the rom-reference pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/leap.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 60, 84, 0.95), 3: ('keys', 2, 0, 55, 84, 0.85), 4: ('keys2', 3, 12, 52, 72, 0.8), 5: ('strings', 4, 0, 55, 76, 0.8), 6: ('bass', 5, 12, 33, 52, 1.0), 7: ('gtr', 6, 0, 48, 67, 0.75), 9: ('kit', 10, 0, 0, 127, 1.0)}
HEADER = {'title': 'Leap', 'pack': 'rom-reference', 'kind': 'chiptune', 'composer': 'nene', 'source': 'leap, a Standard MIDI File (leap.mid) from OpenGameArt (https://opengameart.org/sites/default/files/leap.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/leap-8bit', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'c6d21f3d5416168c75f2f9cc1913d7293b4ac3e86f8aabee5939ec1f2346fc29', 'note': "The MIDI file's lead guitar, keyboards, strings, bass and rhythm guitar on workstation voices, its General MIDI drums on Kit Manager 98 (Breaker Box Kit)."}
TRACKS = [('lead', 'ch1', 'Cathode Lead', {'lufs': -19, 'pan': 4, 'echo': 0.2, 'verb': 0.3}), ('keys', 'ch2', 'Lagoon Piano', {'lufs': -22, 'pan': -16, 'verb': 0.3}), ('keys2', 'ch3', 'Jade Tines', {'lufs': -25, 'pan': 18}), ('strings', 'ch4', 'Blue Swell', {'lufs': -25, 'verb': 0.4}), ('bass', 'ch5', 'Neon Basement', {'lufs': -19}), ('gtr', 'ch6', 'Floor Pluck', {'lufs': -26, 'pan': -26}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -17, 'verb': 0.1})]
module_song(__file__, 'leap.mid', 120, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=340)

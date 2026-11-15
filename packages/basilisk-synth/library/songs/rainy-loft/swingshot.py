"""Swingshot (Haley Halcyon, CC0), re-voiced for the rainy-loft pack: the notes of a FamiTracker module from
OpenGameArt played on the pack's own presets (sources/cc0/swing.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {2: ('mute', 1, -6, 60, 84, 1.0), 1: ('tine', 2, -6, 50, 72, 0.85), 3: ('bass', 4, 0, 33, 60, 1.0),
        4: ('kit', 10, 'split', [(38, 36), (40, 38), (127, 42)], 0.85)}
HEADER = {'title': 'Swingshot', 'pack': 'rainy-loft', 'kind': 'chiptune', 'composer': 'Haley Halcyon',
          'source': 'Swingshot (swing jazz), a FamiTracker module (swing.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/swing.ftm_.7z). Its notes are played here; its chip voices are not used.',
          'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.',
          'proof': 'https://opengameart.org/content/nes-chiptune-swingshot-swing-jazz', 'arranger': 'Algorithmic Industries house band',
          'note': 'A NES swing tune (2A03) played twice in a late-night jazz room: pulse 2 on the straight-mute trumpet, '
                  'pulse 1 on the loft tine piano, the triangle\'s walking line on the fretless bass, the noise channel '
                  'on the pack\'s Loft Brushes kit.'}
TRACKS = [('mute', 'ch1', 'Straight Mute', {'lufs': -19, 'pan': -6, 'echo': 0.12, 'verb': 0.25}),
          ('tine', 'ch2', 'Loft Tine', {'lufs': -22, 'pan': 16, 'verb': 0.2}),
          ('bass', 'ch4', 'Fretless Harbour', {'lufs': -20}),
          ('kit', 'ch10', 'Loft Brushes', {'lufs': -21, 'verb': 0.1})]
module_song(__file__, 'swing.notes.mid', 190, PLAN, HEADER, TRACKS, loops=2,
            master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3},
            echo={'time': '3/8', 'feedback': 0.25, 'tone': 3200, 'level': -7},
            reverb={'size': 2.2, 'predelay': 18, 'tone': 5200, 'level': -6})

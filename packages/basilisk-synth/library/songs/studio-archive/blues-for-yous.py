"""Blues for Yous (Phillip Miller (redactionary), CC0), re-voiced for the studio-archive pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_03-blues.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {2: ('piano', 1, 0, 52, 79, 0.9), 1: ('horns', 2, 0, 52, 76, 0.9), 3: ('bass', 3, -12, 33, 52, 1.0), 4: ('snap', 4, 'split', [(38, 60), (127, 60)], 0.8)}
HEADER = {'title': 'Blues for Yous', 'pack': 'studio-archive', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'Blues For Yous (3), a FamiTracker module (nes_03-blues.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'bb3b14858de49ac130b274d22e34cb90e86c37a8afa17e3805fa47eb8138441c', 'note': "Played twice through: the NES module's pulse 2 on the upright piano, pulse 1 on the horns, the triangle on the marimba bass, the noise on a mouse-click snap."}
TRACKS = [('piano', 'ch1', 'Mild Ivories', {'lufs': -20, 'pan': -14, 'verb': 0.3}), ('horns', 'ch2', 'Twilight Horns', {'lufs': -21, 'pan': 14, 'verb': 0.35}), ('bass', 'ch3', 'Signal Bass', {'lufs': -21}), ('snap', 'ch4', 'Honey Click', {'lufs': -27, 'pan': 20})]
module_song(__file__, 'nes_03-blues.notes.mid', 112, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

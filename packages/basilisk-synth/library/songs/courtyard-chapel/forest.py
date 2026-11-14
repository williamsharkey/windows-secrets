"""Forest (Spring Spring, CC0), re-voiced for the courtyard-chapel pack: the notes of an Impulse Tracker module from OpenGameArt played on
the pack's own presets (sources/cc0/forestCLEAN.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {2: ('harp', 1, 0, 52, 84, 0.9), 4: ('psaltery', 2, 12, 64, 88, 0.95), 5: ('felt', 3, 0, 55, 81, 0.9), 6: ('harpsichord', 4, 0, 45, 76, 0.85), 3: ('tabor', 5, -24, 40, 55, 0.9), 1: ('warp', 6, 0, 49, 60, 0.8)}
HEADER = {'title': 'Forest', 'pack': 'courtyard-chapel', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Forest, an Impulse Tracker module (forestCLEAN.it) from OpenGameArt (https://opengameart.org/sites/default/files/OST.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/haydenwoffle-it-soundtrack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '578ba7fa3d652d87383c16b039eb5db38550e1c2b945c499d5b725ba02d107eb', 'note': "Medieval-style: the module's forest harp on the folk harp, its flute on the psaltery, its bagpipe on the high harpsichord, its harpsiclavichord on the Flemish harpsichord, its war drum on the balafon tabor, its wind on a dan tranh glissando."}
TRACKS = [('harp', 'ch1', 'Faded Pluck', {'lufs': -20, 'pan': 20, 'echo': 0.1, 'verb': 0.3}), ('psaltery', 'ch2', 'Slate Pick', {'lufs': -20, 'pan': -6, 'echo': 0.05, 'verb': 0.32}), ('felt', 'ch3', 'Noble Felt', {'lufs': -22, 'pan': -20, 'verb': 0.25}), ('harpsichord', 'ch4', 'Soft Etude', {'lufs': -22, 'pan': -30, 'verb': 0.22}), ('tabor', 'ch5', 'Brushed Carillon', {'lufs': -23, 'pan': 30, 'verb': 0.25}), ('warp', 'ch6', 'Winter Warp', {'lufs': -27, 'verb': 0.4})]
module_song(__file__, 'forestCLEAN.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6})

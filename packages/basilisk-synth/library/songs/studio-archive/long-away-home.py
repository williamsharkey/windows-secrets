"""Long Away Home (nene, CC0), re-voiced for the studio-archive pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/Long_Away_Home.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('strings', 1, 0, 52, 72, 0.85), 2: ('violas', 2, 0, 52, 72, 0.7), 3: ('horn', 3, 0, 55, 79, 0.95), 4: ('bass', 4, 12, 36, 55, 1.0), 6: ('bells', 5, 12, 64, 91, 0.85), 7: ('piano', 6, 0, 55, 84, 0.85), 5: ('snap', 7, 'split', [(40, 60), (127, 60)], 0.6)}
HEADER = {'title': 'Long Away Home', 'pack': 'studio-archive', 'kind': 'chiptune', 'composer': 'nene', 'source': 'Long_Away_Home, a Standard MIDI File (Long_Away_Home.mid) from OpenGameArt (https://opengameart.org/sites/default/files/Long%20Away%20Home.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/long-away-home-8bit', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'a43e1a05f9f9b0ede3270bf62d395658cdae01d39184ed642d009c9dec622161', 'note': "The MIDI file on the studio's strings, violas, horns, marimba bass, glockenspiel and piano, its percussion on a soft snap."}
TRACKS = [('strings', 'ch1', 'Humid Swell', {'lufs': -22, 'pan': -22, 'verb': 0.4}), ('violas', 'ch2', 'Static Swell', {'lufs': -25, 'pan': 18, 'verb': 0.35}), ('horn', 'ch3', 'Opal Fanfare', {'lufs': -20, 'pan': 8, 'verb': 0.4}), ('bass', 'ch4', 'Signal Bass', {'lufs': -21}), ('bells', 'ch5', 'Crystal Toll', {'lufs': -25, 'pan': 28, 'verb': 0.4}), ('piano', 'ch6', 'Mild Ivories', {'lufs': -23, 'pan': -12, 'verb': 0.3}), ('snap', 'ch7', 'Clear Snap', {'lufs': -29, 'verb': 0.3})]
module_song(__file__, 'Long_Away_Home.mid', 120, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6})

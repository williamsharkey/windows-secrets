"""Doggo (Spring Spring, CC0), re-voiced for the waulophone pack: the notes of an Impulse Tracker module from OpenGameArt played on
the pack's own presets (sources/cc0/doggoCLEAN.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {3: ('piano', 1, 0, 48, 81, 0.9), 4: ('organ', 2, 0, 52, 79, 0.85), 2: ('sax', 3, 12, 60, 79, 0.95), 6: ('bass', 4, -12, 33, 52, 1.0), 5: ('hum', 5, 12, 55, 72, 0.85), 1: ('boop', 6, 0, 60, 79, 0.9)}
HEADER = {'title': 'Doggo', 'pack': 'waulophone', 'credit': 'Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly)', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Doggo, an Impulse Tracker module (doggoCLEAN.it) from OpenGameArt (https://opengameart.org/sites/default/files/OST.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/haydenwoffle-it-soundtrack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '9362e4128d8fa85cafc44198b66ecc801fe6c3cf60999d3fadd86a237d1aea5a', 'note': "The module's piano, organ, sax and bass parts on the office piano, the bee-buzzing organ, the sax and the bass from Accounts; its second organ on the hum from the back row; its woofs on the boop. Sounds by Paul Chauncy."}
TRACKS = [('piano', 'ch1', 'Kettle On', {'lufs': -19, 'pan': -12, 'verb': 0.25}), ('organ', 'ch2', 'Bee Organ Lead', {'lufs': -23, 'pan': 18, 'verb': 0.2}), ('sax', 'ch3', 'Crooner Sax', {'lufs': -21, 'pan': -20, 'echo': 0.1, 'verb': 0.3}), ('bass', 'ch4', 'Barry Sings Low', {'lufs': -20}), ('hum', 'ch5', 'Hmm Held', {'lufs': -23, 'pan': 6, 'verb': 0.3}), ('boop', 'ch6', 'Boop Boop', {'lufs': -25, 'pan': 30, 'echo': 0.2})]
module_song(__file__, 'doggoCLEAN.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6})

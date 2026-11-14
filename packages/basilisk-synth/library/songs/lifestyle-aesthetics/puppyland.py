"""Puppyland (Spring Spring, CC0), re-voiced for the lifestyle-aesthetics pack: the notes of an Impulse Tracker module from OpenGameArt played on
the pack's own presets (sources/cc0/puppylandCLEAN.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {10: ('keys', 1, 0, 52, 79, 0.9), 11: ('kalimba', 2, 0, 64, 86, 0.85), 1: ('bass', 3, 0, 33, 55, 1.0), 2: ('mallets', 4, 0, 60, 84, 0.85), 9: ('kit', 10, 'pad', 36, 1.0), 5: ('kit', 10, 'pad', 42, 0.8), 7: ('kit', 10, 'pad', 38, 0.9)}
HEADER = {'title': 'Puppyland', 'pack': 'lifestyle-aesthetics', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Puppyland, an Impulse Tracker module (puppylandCLEAN.it) from OpenGameArt (https://opengameart.org/sites/default/files/OST.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/haydenwoffle-it-soundtrack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '3167f1933bc1ff94e7c27ab10640cbbc3dd21083256ab93073137c5acb76a3cb', 'note': "Played twice through: the module's keys on the atrium keys, its high line on the kalimba, its bell on the marimba, its bass on the slow-jam bass, its 303-style drums on Kit Manager 98 (Echo Chamber Kit)."}
TRACKS = [('keys', 'ch1', 'Atrium Keys', {'lufs': -20, 'pan': -10, 'echo': 0.15, 'verb': 0.3}), ('kalimba', 'ch2', 'Hydro Kalimba', {'lufs': -22, 'pan': 22, 'echo': 0.25, 'verb': 0.3}), ('bass', 'ch3', 'Slow Jam Bass', {'lufs': -20}), ('mallets', 'ch4', 'Droplet Marimba', {'lufs': -23, 'pan': -26, 'echo': 0.2, 'verb': 0.3}), ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', {'lufs': -18, 'verb': 0.1})]
module_song(__file__, 'puppylandCLEAN.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2, cut=354)

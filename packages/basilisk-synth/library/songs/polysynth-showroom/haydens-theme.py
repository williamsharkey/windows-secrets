"""Hayden's Theme (Spring Spring, CC0), re-voiced for the polysynth-showroom pack: the notes of an Impulse Tracker module from OpenGameArt played on
the pack's own presets (sources/cc0/haydenCLEAN.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('fmpiano', 1, 0, 52, 91, 0.9), 2: ('brass', 2, 12, 48, 67, 0.85), 3: ('bass', 3, 0, 28, 52, 1.0)}
HEADER = {'title': "Hayden's Theme", 'pack': 'polysynth-showroom', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': "Hayden's Theme, an Impulse Tracker module (haydenCLEAN.it) from OpenGameArt (https://opengameart.org/sites/default/files/OST.zip). Its notes are played here; its samples or chip voices are not used.", 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/haydenwoffle-it-soundtrack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '711dcf5a03e21306d87b1ab4e08e5aefe40a234759fe2f590d10137c45d77a71', 'note': "The module's puppy piano on an FM piano, its middle line on poly brass, its basset on the cream mono bass."}
TRACKS = [('fmpiano', 'ch1', 'Stone Parlour', {'lufs': -19, 'pan': -6, 'echo': 0.15, 'verb': 0.3}), ('brass', 'ch2', 'Lucid Herald', {'lufs': -22, 'pan': 14, 'verb': 0.3}), ('bass', 'ch3', 'Ivory Low', {'lufs': -20})]
module_song(__file__, 'haydenCLEAN.notes.mid', 121, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=340)

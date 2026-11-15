"""Puppy Playing in the Garden (Spring Spring, CC0), re-voiced for the lifestyle-aesthetics pack: the notes of a 0CC-FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/puppy.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {6: ('kalimba', 1, 0, 60, 86, 0.9), 1: ('keys', 2, 0, 55, 79, 0.85), 2: ('marimba', 3, 0, 55, 81, 0.8), 3: ('bass', 4, 12, 33, 55, 1.0), 5: ('kit', 10, 'pad', 36, 1.0), 4: ('kit', 10, 'pad', 42, 0.8)}
HEADER = {'title': 'Puppy Playing in the Garden', 'pack': 'lifestyle-aesthetics', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Puppy Playing in the Garden, a 0CC-FamiTracker module (puppy.0cc) from OpenGameArt (https://opengameart.org/sites/default/files/puppy.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/puppy-playing-in-the-garden', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '27a14bd6089e8612a5cd10da1cd3b31db096d129753d17c265e53f61b9e63370', 'note': "Played twice through: the NES module's VRC6 pulse on the kalimba, the pulses on tines and marimba, the triangle on the slow-jam bass, DPCM and noise on Kit Manager 98 (Echo Chamber Kit)."}
TRACKS = [('kalimba', 'ch1', 'Hydro Kalimba', {'lufs': -20, 'pan': 10, 'echo': 0.25, 'verb': 0.3}), ('keys', 'ch2', 'Midnight Tines', {'lufs': -22, 'pan': -14, 'verb': 0.3}), ('marimba', 'ch3', 'Atrium Marimba', {'lufs': -23, 'pan': 24, 'verb': 0.3}), ('bass', 'ch4', 'Slow Jam Bass', {'lufs': -20}), ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', {'lufs': -19, 'verb': 0.1})]
module_song(__file__, 'puppy.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2, cut=354)

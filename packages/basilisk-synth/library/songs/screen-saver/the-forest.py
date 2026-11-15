"""The Forest (Wolfgang_, CC0), re-voiced for the screen-saver pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/TheForest.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('flute', 1, 12, 60, 84, 0.9), 2: ('marimba', 2, 12, 55, 81, 0.85), 3: ('bass', 3, 12, 48, 64, 0.85), 4: ('chime', 4, 'pad', 71, 0.6)}
HEADER = {'title': 'The Forest', 'pack': 'screen-saver', 'kind': 'chiptune', 'composer': 'Wolfgang_', 'source': 'The Forest, a FamiTracker module (TheForest.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/TheForest.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/8-bit-forest-theme', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '7db40d51ccd13b769a2a4da4b4f0b0d2786b749d204155302c7bf7eba5c4c07e', 'note': "Played twice through: the NES module's pulse 1 on the breathy flute, pulse 2 on the marimba, the triangle on the horn pad, the noise on a wind chime."}
TRACKS = [('flute', 'ch1', 'Breath Flute', {'lufs': -20, 'pan': 4, 'echo': 0.2, 'verb': 0.45}), ('marimba', 'ch2', 'Water Marimba', {'lufs': -22, 'pan': -16, 'echo': 0.25, 'verb': 0.35}), ('bass', 'ch3', 'Cathode Halo', {'lufs': -24, 'verb': 0.3}), ('chime', 'ch4', 'Frosted Peal', {'lufs': -30, 'pan': 28, 'verb': 0.4})]
module_song(__file__, 'TheForest.notes.mid', 120, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

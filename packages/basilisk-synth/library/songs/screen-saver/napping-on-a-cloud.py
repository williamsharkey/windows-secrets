"""Napping on a Cloud (congusbongus, CC0), re-voiced for the screen-saver pack: the notes of a FastTracker 2 module from OpenGameArt played on
the pack's own presets (sources/cc0/napping_on_a_cloud.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('flute', 1, -12, 60, 84, 0.9), 5: ('glass', 2, 0, 55, 76, 0.85), 2: ('bass', 3, -24, 36, 55, 0.9), 6: ('marimba', 4, -12, 55, 81, 0.8), 3: ('gong', 5, 'pad', 60, 0.8), 4: ('chime', 6, 'pad', 71, 0.6)}
HEADER = {'title': 'Napping on a Cloud', 'pack': 'screen-saver', 'kind': 'chiptune', 'composer': 'congusbongus', 'source': 'Napping on a cloud, a FastTracker 2 module (napping_on_a_cloud.xm) from OpenGameArt (https://opengameart.org/sites/default/files/napping_on_a_cloud.xm_.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/napping-on-a-cloud', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '5d0ff2a44bc0ff7c0eaad9a91da605f37f1d323e7af241b1521cc279dd3d1f9a', 'note': "Ambient at 81 bpm: the module's melody on the breathy flute, its dub chords on the glass harp, its bass on the horn pad, its buzz line on the marimba, its percussion on a gong and its hat on a wind chime."}
TRACKS = [('flute', 'ch1', 'Breath Flute', {'lufs': -20, 'pan': 4, 'echo': 0.2, 'verb': 0.45}), ('glass', 'ch2', 'Ivory Canopy', {'lufs': -24, 'pan': -14, 'verb': 0.4}), ('bass', 'ch3', 'Cathode Halo', {'lufs': -23, 'verb': 0.2}), ('marimba', 'ch4', 'Water Marimba', {'lufs': -24, 'pan': 24, 'echo': 0.25, 'verb': 0.35}), ('gong', 'ch5', 'Yellow Gong', {'lufs': -27, 'verb': 0.4}), ('chime', 'ch6', 'Frosted Peal', {'lufs': -30, 'pan': 30, 'verb': 0.4})]
module_song(__file__, 'napping_on_a_cloud.notes.mid', 81, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=230)

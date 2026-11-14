"""Rhythmove (northivanastan, CC0), re-voiced for the office-machinery pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/rhythmove.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('beep', 1, -12, 64, 88, 0.85), 2: ('bugle', 2, 0, 60, 84, 0.95), 3: ('lowbugle', 3, 12, 52, 72, 0.9), 4: ('drives', 4, 12, 33, 52, 1.0), 5: ('kit', 10, 0, 0, 127, 1.0), 6: ('inductor', 5, 0, 45, 67, 0.85)}
HEADER = {'title': 'Rhythmove', 'pack': 'office-machinery', 'kind': 'chiptune', 'composer': 'northivanastan', 'source': 'Rhythmove, a Standard MIDI File (rhythmove.mid) from OpenGameArt (https://opengameart.org/sites/default/files/rhythmove.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/rhythmove', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'c37e73690ce553261a794f70a1ec1aed3d6bac82e91c32e9826486e9c1683c55', 'note': 'A CC0 MIDI file on office machinery: its strings on the PC speaker, its synth brass on the civil-defence bugle, its square lead on the low bugle, its bass on twelve drives, its General MIDI drums on the spacebar kit, its guitars on a hard-disk inductor.'}
TRACKS = [('beep', 'ch1', 'Cedar Hat', {'lufs': -24, 'pan': 16, 'echo': 0.15}), ('bugle', 'ch2', 'Signal Uplink', {'lufs': -20, 'pan': -4, 'verb': 0.3}), ('lowbugle', 'ch3', 'White Dive', {'lufs': -22, 'pan': -18, 'verb': 0.3}), ('drives', 'ch4', 'Ocean Crowd', {'lufs': -20}), ('kit', 'ch10', 'Rubber Canopy', {'lufs': -17, 'verb': 0.06}), ('inductor', 'ch5', 'Steady Texture', {'lufs': -25, 'pan': 24})]
module_song(__file__, 'rhythmove.mid', 120, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=340)

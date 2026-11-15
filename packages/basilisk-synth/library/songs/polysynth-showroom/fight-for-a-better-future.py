"""Fight for a Better Future (nene, CC0), re-voiced for the polysynth-showroom pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/fight_for_better_future.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 60, 86, 0.95), 2: ('brass', 2, 0, 48, 72, 0.8), 3: ('brass2', 3, 0, 48, 72, 0.75), 4: ('bass', 4, 12, 33, 52, 1.0), 6: ('solo', 5, 0, 60, 86, 0.85), 7: ('strings', 6, 0, 55, 76, 0.8), 5: ('kit', 10, 0, 0, 127, 1.0)}
HEADER = {'title': 'Fight for a Better Future', 'pack': 'polysynth-showroom', 'kind': 'chiptune', 'composer': 'nene', 'source': 'fight_for_better_future, a Standard MIDI File (fight_for_better_future.mid) from OpenGameArt (https://opengameart.org/sites/default/files/fight_for_better_future.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/fight-for-better-future-rockmetal', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '939a374f1f892f60bdf2cdf1380af32b7bda344a072a0865a7de4c0983862e43', 'note': "Played twice through as 1985 synth rock: the MIDI file's lead guitar on the buzzy lead, the rhythm guitars on poly brass, its synth on a PWM lead, strings on vocoder strings, its bass on the cream mono bass, its General MIDI drums on Kit Manager 98 (Breaker Box Kit)."}
TRACKS = [('lead', 'ch1', 'Amber Line', {'lufs': -20, 'pan': 4, 'echo': 0.2}), ('brass', 'ch2', 'Signal Stab', {'lufs': -23, 'pan': -20}), ('brass2', 'ch3', 'Metro Chord', {'lufs': -24, 'pan': 20}), ('bass', 'ch4', 'Broadcast Cellar', {'lufs': -19}), ('solo', 'ch5', 'Tropic Signal', {'lufs': -22, 'pan': -8, 'echo': 0.2}), ('strings', 'ch6', 'Hollow Swell', {'lufs': -25, 'verb': 0.35}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -17, 'verb': 0.15})]
module_song(__file__, 'fight_for_better_future.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

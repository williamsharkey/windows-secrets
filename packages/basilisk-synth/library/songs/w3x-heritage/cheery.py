"""Cheery (Phillip Miller (redactionary), CC0), re-voiced for the w3x-heritage pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_03-cheery.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {6: ('lead', 1, 0, 60, 84, 0.95), 2: ('chords', 2, 12, 55, 72, 0.85), 1: ('bass', 3, 0, 36, 52, 1.0), 3: ('bells', 4, 0, 64, 88, 0.8), 4: ('shaker', 5, 'pad', 60, 0.8)}
HEADER = {'title': 'Cheery', 'pack': 'w3x-heritage', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'cheery, a FamiTracker module (nes_03-cheery.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '067e24b44b43fb785afcfc1a1f55a0a5980506ee8658add9eb27c1e9333c1f53', 'note': 'Played twice through on the six Windows 3.1 sounds: the VRC6 pulse on the ding piano, pulse 2 on ding chords, pulse 1 on the ding bass, the triangle on chimes bells, the noise on a ding shaker.'}
TRACKS = [('lead', 'ch1', 'Still Upright', {'lufs': -19, 'pan': 6, 'verb': 0.25}), ('chords', 'ch2', 'Western Chords', {'lufs': -23, 'pan': -16, 'verb': 0.2}), ('bass', 'ch3', 'Field Bass', {'lufs': -20, 'verb': 0.15}), ('bells', 'ch4', 'Urban Ring', {'lufs': -25, 'pan': 28, 'verb': 0.4}), ('shaker', 'ch5', 'Hollow Shaker', {'lufs': -28, 'pan': -24})]
module_song(__file__, 'nes_03-cheery.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)

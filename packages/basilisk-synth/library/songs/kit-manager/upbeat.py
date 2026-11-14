"""Upbeat (Phillip Miller (redactionary), CC0), re-voiced for the kit-manager pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_19-upbeat.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('typingpool', 1, 0, 72, 84, 0.95), 2: ('calculator', 2, 0, 72, 84, 0.95), 3: ('relayroom', 3, 0, 60, 72, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Upbeat', 'pack': 'kit-manager', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'upbeat (19), a FamiTracker module (nes_19-upbeat.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '50e5bd238a2e9f437d03f30ee1a3bb52504d6827ea57e5bf4e06e9ea1829a676', 'note': "Played three times through on Kit Manager 98: the NES module's pulses on the Typing Pool and Calculator Bureau tuned keys, the triangle on Relay Room's, the noise on the Half-Time Kit."}
TRACKS = [('typingpool', 'ch1', 'Typing Pool', {'lufs': -21, 'pan': 24, 'echo': 0.15, 'verb': 0.25}), ('calculator', 'ch2', 'Calculator Bureau', {'lufs': -20, 'pan': -6, 'echo': 0.2, 'verb': 0.3}), ('relayroom', 'ch3', 'Relay Room', {'lufs': -21, 'verb': 0.15}), ('kit', 'ch10', 'Half-Time Kit', {'lufs': -18, 'verb': 0.06})]
module_song(__file__, 'nes_19-upbeat.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=3)

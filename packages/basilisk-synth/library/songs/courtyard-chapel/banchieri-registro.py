"""Banchieri, Registro 1 (chip arrangement) (TheOuterLinux, CC0), re-voiced for the courtyard-chapel pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/Banchieri_-_Reg_1.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('psaltery', 1, 0, 60, 84, 0.9), 2: ('harp', 2, 0, 48, 72, 0.85), 3: ('dantranh', 3, 0, 55, 79, 0.9), 4: ('harpsichord', 4, 0, 45, 72, 0.85), 5: ('psaltery', 1, 0, 60, 84, 0.9), 6: ('harp', 2, 0, 48, 72, 0.85), 7: ('dantranh', 3, 0, 55, 79, 0.9), 8: ('harpsichord', 4, 0, 45, 72, 0.85), 9: ('psaltery', 1, 0, 60, 84, 0.9), 10: ('harp', 2, 0, 48, 72, 0.85), 11: ('dantranh', 3, 0, 55, 79, 0.9), 12: ('harpsichord', 4, 0, 45, 72, 0.85)}
HEADER = {'title': 'Banchieri, Registro 1 (chip arrangement)', 'pack': 'courtyard-chapel', 'kind': 'chiptune', 'composer': 'TheOuterLinux', 'source': 'Banchieri_-_Reg_1, a Standard MIDI File (Banchieri_-_Reg_1.mid) from OpenGameArt (https://opengameart.org/sites/default/files/NES%20-%20Banchieri.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/nes-or-gameboy-banchieri-reg-1', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'd638e2bb7c08a37883c2a7c2d49e5df68b06c6343b75df16dec28770986b27a0', 'note': "An NES and Game Boy arrangement of Adriano Banchieri's organ registro (1605) played on the courtyard's plucked strings: psaltery, folk harp, dan tranh and harpsichord, the composer's voices kept apart."}
TRACKS = [('psaltery', 'ch1', 'Slate Pick', {'lufs': -20, 'pan': 8, 'verb': 0.32}), ('harp', 'ch2', 'Faded Pluck', {'lufs': -21, 'pan': 26, 'verb': 0.3}), ('dantranh', 'ch3', 'Arctic Steps', {'lufs': -21, 'pan': -18, 'verb': 0.3}), ('harpsichord', 'ch4', 'Soft Etude', {'lufs': -22, 'pan': -30, 'verb': 0.22})]
module_song(__file__, 'Banchieri_-_Reg_1.mid', 120, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=340)

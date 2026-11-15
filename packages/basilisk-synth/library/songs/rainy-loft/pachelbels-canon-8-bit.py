"""Pachelbel's Canon in D (ctske, CC0), re-voiced for the rainy-loft pack: the notes of a 0CC-FamiTracker module from
OpenGameArt played on the pack's own presets (sources/cc0/pachelbelscanon.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {3: ('bass', 4, -12, 36, 55, 1.0), 1: ('tine', 1, 0, 50, 86, 0.9), 2: ('violins', 2, 0, 55, 88, 0.85),
        6: ('harp', 3, 0, 48, 84, 0.8)}
HEADER = {'title': "Pachelbel's Canon (8-bit)", 'pack': 'rainy-loft', 'kind': 'chiptune', 'composer': 'ctske (after Johann Pachelbel)',
          'source': "Pachelbel's Canon in D, a 0CC-FamiTracker module (pachelbelscanon.0cc) from OpenGameArt (https://opengameart.org/sites/default/files/pachelbelscanon.zip). Its notes are played here; its chip voices are not used.",
          'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page; the canon itself is public domain). This arrangement: CC0-1.0.',
          'proof': 'https://opengameart.org/content/8-bit-pachelbels-canon-in-d', 'arranger': 'Algorithmic Industries house band',
          'note': 'A NES module (2A03 + VRC6) re-voiced for a rainy loft at 2 a.m.: the triangle\'s ground on the fretless bass, '
                  'the canon\'s three voices on the loft tine piano, legato violins and the harbour harp, with the haze strings.'}
TRACKS = [('tine', 'ch1', 'Loft Tine', {'lufs': -20, 'pan': -14, 'verb': 0.3}),
          ('violins', 'ch2', 'Legato Violins', {'lufs': -21, 'pan': 16, 'verb': 0.35}),
          ('harp', 'ch3', 'Harbour Harp', {'lufs': -23, 'pan': 28, 'echo': 0.15, 'verb': 0.3}),
          ('bass', 'ch4', 'Fretless Harbour', {'lufs': -20})]
module_song(__file__, 'pachelbelscanon.notes.mid', 75, PLAN, HEADER, TRACKS, cut=75 * 2.5,
            master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 6},
            echo={'time': '1/4', 'feedback': 0.3, 'tone': 3000, 'level': -7},
            reverb={'size': 2.8, 'predelay': 22, 'tone': 5000, 'level': -5})

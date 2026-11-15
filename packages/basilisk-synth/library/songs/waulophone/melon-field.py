"""The War over a Melon Field (Spring Spring, CC0), re-voiced for the waulophone pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/short_theme_melon_midi.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('organ', 1, 0, 60, 84, 0.9), 2: ('bass', 2, 12, 33, 52, 1.0), 4: ('sax', 3, 0, 55, 79, 0.95), 5: ('hum', 4, 0, 55, 72, 0.85), 3: ('kit', 10, 0, 0, 127, 1.0)}
HEADER = {'title': 'The War over a Melon Field', 'pack': 'waulophone', 'credit': 'Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly)', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'short_theme_melon_midi, a Standard MIDI File (short_theme_melon_midi.mid) from OpenGameArt (https://opengameart.org/sites/default/files/short%20theme%20melon%20midi.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/the-war-over-a-melon-field-themes-and-jingles', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '74d7759d269e816a43e58a550764d1bb93ecb22b3b470b6783b16e008083c11d', 'note': "The MIDI file's harmonica, synth and brass lines on the bee-buzzing organ, the sax and the big-ears hum, its bass on Barry, its General MIDI drums on the pack's Honey Pine Kit. Sounds by Paul Chauncy."}
TRACKS = [('organ', 'ch1', 'Bee Organ Lead', {'lufs': -21, 'pan': 18, 'verb': 0.2}), ('bass', 'ch2', 'Barry Sings Low', {'lufs': -20}), ('sax', 'ch3', 'Crooner Sax', {'lufs': -20, 'pan': -16, 'echo': 0.1, 'verb': 0.3}), ('hum', 'ch4', 'Hmm Held', {'lufs': -22, 'verb': 0.3}), ('kit', 'ch10', 'Honey Pine Kit', {'lufs': -19, 'verb': 0.08})]
module_song(__file__, 'short_theme_melon_midi.mid', 120, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2, cut=340)

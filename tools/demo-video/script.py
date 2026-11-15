"""The narration: Harlan Pettibone (HOST, an invented host) and the announcer (ANN). Kokoro-82M voices, local.

Each line: (id, speaker, text, caption). The caption is what is burned in (None: the text itself). Spoken text spells
things the way they should be said; captions keep the written forms (SOUNDREC.EXE, 3.11, 1,437).
"""

VOICES = {
    # an older, warmer man: a blend of two Kokoro American male voices, a little slow
    'HOST': {'lang': 'a', 'voice': ('am_michael', 0.55, 'am_santa', 0.45), 'speed': 1.0},
    # the deadpan announcer: Kokoro's deepest, flattest male voice
    'ANN': {'lang': 'a', 'voice': ('am_onyx', 1.0), 'speed': 0.95},
}

LINES = [
    ('ann_open', 'ANN', "Algorithmic Industries Home Learning presents: Getting Started with Sound Wave nineteen ninety-three.",
     "Algorithmic Industries Home Learning presents: Getting Started with SNDWAVE1993."),
    ('h_hello', 'HOST', "Hello. I'm Harlan Pettibone.", None),
    ('h_what', 'HOST', "What you just watched was Windows for Workgroups three point one one, from nineteen ninety-three, starting up inside a plugin. "
                       "Those sixteen windows are Sound Recorders. Now they're a synthesizer.",
     "What you just watched was Windows for Workgroups 3.11, from 1993, starting up inside a plugin. "
     "Those sixteen windows are Sound Recorders. Now they're a synthesizer."),
    ('h_1993', 'HOST', "This is nineteen ninety-three technology. I was there.", "This is 1993 technology. I was there."),
    ('h_real', 'HOST', "It's a real Windows, emulated. Program Manager. Accessories. Sound Recorder.", None),
    ('h_ver', 'HOST', "Sound rec dot exe. The sixteen-bit original. File version three point one, copyright Microsoft, nineteen ninety-one. This copy is dated November eighth, nineteen ninety-three.",
     "SOUNDREC.EXE. The 16-bit original. File version 3.1, copyright Microsoft, 1991. This copy is dated November 8, 1993."),
    ('h_res', 'HOST', "System resources: sixteen percent free. Seems about right.", None),
    ('h_play', 'HOST', "Every note you play, Windows presses Play on one of them.", None),
    ('h_packs', 'HOST', "Twenty-six sound pack discs. Fourteen hundred and thirty-seven presets. Pick a disc, pick a preset, press Load preset.",
     "26 sound pack discs. 1,437 presets. Pick a disc, pick a preset, press Load preset."),
    ('h_granite', 'HOST', "Granite Cloud. A flute, slowed down.", None),
    ('h_shaded', 'HOST', "Shaded End. The Windows XP ding, very slowed down.", None),
    ('h_rounded', 'HOST', "Rounded Corner Chord. X P's notify sound, as a major seventh.", "Rounded Corner Chord. XP's Notify sound, as a major seventh."),
    ('h_daw', 'HOST', "It's a VST3, Audio Unit and CLAP instrument, for Windows and Mac. It works in Ableton Live and other DAWs.", None),
    ('h_vibe', 'HOST', "For vaporwave, or Frutiger Aero: slow chords, a long release, and a little wow and flutter.", None),
    ('h_song', 'HOST', "New in one point four: the Song tab. Import a MIDI file, give each track a preset, and press Render. "
                       "Every track plays in its own Windows, on its own sixteen Sound Recorders.",
     "New in 1.4: the Song tab. Import a MIDI file, give each track a preset, and press Render. "
     "Every track plays in its own Windows, on its own sixteen Sound Recorders."),
    ('h_export', 'HOST', "Then export the WAV.", None),
    ('h_kits', 'HOST', "Drum kits, with a calculator for the pads.", None),
    ('h_mines', 'HOST', "The sequencer is Minesweeper. Numbers play, flags accent. Lose, and those columns go up an octave.", None),
    ('h_rec', 'HOST', "And it records, into a real Sound Recorder.", None),
    ('h_free', 'HOST', "It's free. Download it, or try it in your web browser, at william sharkey dot com, slash sound wave nineteen ninety-three.",
     "It's free. Download it, or try it in your web browser: williamsharkey.com/sndwave1993"),
    ('h_citypop', 'HOST', "This whole album, City Pop nineteen ninety-three, was made on it.", "This whole album, CITYPOP1993, was made on it."),
    ('h_citypop2', 'HOST', "Coming in version one point five: it plays right inside the plugin.",
     "Coming in version 1.5: it plays right inside the plugin."),
    ('h_bye', 'HOST', "Take your time. Windows will wait. I'm Harlan Pettibone.", None),
    ('ann_tag', 'ANN', "Sound Wave nineteen ninety-three. Total sound solutions for globalized audio.", "SNDWAVE1993. Total sound solutions for globalized audio."),
    # shorter forms for the two-minute spot (the long cut uses the full lines above)
    ('s_what', 'HOST', "That was Windows for Workgroups three point one one, from nineteen ninety-three, starting up inside a plugin. "
                       "Its sixteen Sound Recorders are now a synthesizer.",
     "That was Windows for Workgroups 3.11, from 1993, starting up inside a plugin. Its sixteen Sound Recorders are now a synthesizer."),
    ('s_ver', 'HOST', "Sound rec dot exe. File version three point one, copyright Microsoft, nineteen ninety-one. This copy is dated November eighth, nineteen ninety-three.",
     "SOUNDREC.EXE. File version 3.1, copyright Microsoft, 1991. This copy is dated November 8, 1993."),
    ('s_song', 'HOST', "New in one point four: the Song tab. Import a MIDI file, give each track a preset, and render. "
                       "Every track gets its own Windows, and its own sixteen Sound Recorders.",
     "New in 1.4: the Song tab. Import a MIDI file, give each track a preset, and render. "
     "Every track gets its own Windows, and its own sixteen Sound Recorders."),
    ('s_more', 'HOST', "Drum kits, with a calculator for the pads. A Minesweeper sequencer: numbers play, flags accent. "
                       "And it records, into a real Sound Recorder.", None),
]


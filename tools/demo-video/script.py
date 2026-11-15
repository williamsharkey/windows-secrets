"""The narration: Clement Ashby (HOST), the invented host of the invented public-access show "Computing at Your
Pace", and the announcer (ANN). Kokoro-82M voices, local.

Each line: (id, speaker, text, caption). The caption is what is burned in (None: the text itself). Spoken text spells
things the way they should be said and carries Clement's pauses ("..."); captions keep the written forms.
"""

VOICES = {
    # gentle, a little halting: Kokoro's am_michael, a touch slow
    'HOST': {'lang': 'a', 'voice': ('am_michael', 1.0), 'speed': 0.95},
    # the deadpan announcer: Kokoro's deepest, flattest male voice
    'ANN': {'lang': 'a', 'voice': ('am_onyx', 1.0), 'speed': 0.95},
}

LINES = [
    ('ann_open', 'ANN', "Algorithmic Industries Home Learning presents: Computing at Your Pace. Today: Sound Wave nineteen ninety-three.",
     "Algorithmic Industries Home Learning presents: Computing at Your Pace. Today: SNDWAVE1993."),
    ('h_hello', 'HOST', "Hello... and welcome back to Computing at Your Pace. I'm Clement Ashby.", None),
    ('h_what', 'HOST', "What you just watched was Windows for Workgroups three point one one, from nineteen ninety-three... starting up "
                       "inside a plugin. Those sixteen windows are Sound Recorders. And now... they are a synthesizer.",
     "What you just watched was Windows for Workgroups 3.11, from 1993, starting up inside a plugin. "
     "Those sixteen windows are Sound Recorders. And now, they are a synthesizer."),
    ('h_1993', 'HOST', "This is nineteen ninety-three technology. I was thirty-one. I'm more excited now.",
     "This is 1993 technology. I was thirty-one. I'm more excited now."),
    ('h_real', 'HOST', "It is a real Windows. Emulated. Here's Program Manager... Accessories... and, Sound Recorder.",
     "It is a real Windows. Emulated. Here's Program Manager. Accessories. And Sound Recorder."),
    ('h_ver', 'HOST', "Sound rec dot exe. The sixteen-bit original. File version three point one, copyright Microsoft, nineteen ninety-one. "
                      "This copy is dated November eighth, nineteen ninety-three.",
     "SOUNDREC.EXE. The 16-bit original. File version 3.1, copyright Microsoft, 1991. This copy is dated November 8, 1993."),
    ('h_res', 'HOST', "System resources: sixteen percent free. That seems... fine.", "System resources: sixteen percent free. That seems fine."),
    ('h_play', 'HOST', "Every note you play, Windows presses Play on one of them. I find that... very moving.",
     "Every note you play, Windows presses Play on one of them. I find that very moving."),
    ('h_packs', 'HOST', "Twenty-six sound pack discs. Fourteen hundred and thirty-seven presets. Pick a disc, pick a preset, press Load preset.",
     "26 sound pack discs. 1,437 presets. Pick a disc, pick a preset, press Load preset."),
    ('h_granite', 'HOST', "Granite Cloud. A flute... slowed down.", "Granite Cloud. A flute, slowed down."),
    ('h_shaded', 'HOST', "Shaded End. The Windows XP ding, very slowed down. It's a bass now. Good for it.", None),
    ('h_rounded', 'HOST', "Rounded Corner Chord. X P's notify sound, as a major seventh.", "Rounded Corner Chord. XP's Notify sound, as a major seventh."),
    ('h_daw', 'HOST', "It's a VST3, Audio Unit and CLAP instrument, for Windows and Mac. It works in Ableton Live, and other DAWs.", None),
    ('h_vibe', 'HOST', "For vaporwave, or Frutiger Aero... slow chords, a long release, and a little wow and flutter. I'm told this is the vibe.",
     "For vaporwave, or Frutiger Aero: slow chords, a long release, and a little wow and flutter. I'm told this is the vibe."),
    ('h_song', 'HOST', "Now. New in one point four: the Song tab. Import a MIDI file, and give each track a preset. Press Render. "
                       "Every track plays in its own Windows three point one one, on its own sixteen Sound Recorders. Then they're mixed.",
     "Now. New in 1.4: the Song tab. Import a MIDI file, and give each track a preset. Press Render. "
     "Every track plays in its own Windows 3.11, on its own sixteen Sound Recorders. Then they're mixed."),
    ('h_export', 'HOST', "Then... export the WAV.", "Then, export the WAV."),
    ('h_kits', 'HOST', "There are drum kits. With a calculator, for the pads.", None),
    ('h_mines', 'HOST', "The sequencer is Minesweeper. Numbers play. Flags accent. If you lose... those columns go up an octave. I lose a lot.",
     "The sequencer is Minesweeper. Numbers play. Flags accent. If you lose, those columns go up an octave. I lose a lot."),
    ('h_rec', 'HOST', "And it records, into a real Sound Recorder.", None),
    ('h_free', 'HOST', "It's free. Download it, or try it in your web browser, at william sharkey dot com, slash sound wave nineteen ninety-three.",
     "It's free. Download it, or try it in your web browser: williamsharkey.com/sndwave1993"),
    ('h_citypop', 'HOST', "This whole album, City Pop nineteen ninety-three, was made on it.", "This whole album, CITYPOP1993, was made on it."),
    ('h_citypop2', 'HOST', "Coming in version one point five: it plays right inside the plugin.",
     "Coming in version 1.5: it plays right inside the plugin."),
    ('h_bye', 'HOST', "That's our show. Take your time. Windows will wait. I'm Clement Ashby... and this has been Computing at Your Pace.",
     "That's our show. Take your time. Windows will wait. I'm Clement Ashby, and this has been Computing at Your Pace."),
    ('ann_tag', 'ANN', "Sound Wave nineteen ninety-three. Total sound solutions for globalized audio.", "SNDWAVE1993. Total sound solutions for globalized audio."),
    # shorter forms for the two-minute spot (the long cut uses the full lines above)
    ('s_what', 'HOST', "That was Windows for Workgroups three point one one, from nineteen ninety-three, starting up inside a plugin. "
                       "Its sixteen Sound Recorders are now... a synthesizer.",
     "That was Windows for Workgroups 3.11, from 1993, starting up inside a plugin. Its sixteen Sound Recorders are now a synthesizer."),
    ('s_ver', 'HOST', "Sound rec dot exe. File version three point one, copyright Microsoft, nineteen ninety-one. This copy is dated November eighth, nineteen ninety-three.",
     "SOUNDREC.EXE. File version 3.1, copyright Microsoft, 1991. This copy is dated November 8, 1993."),
    ('s_song', 'HOST', "New in one point four: the Song tab. Import a MIDI file, give each track a preset, and render. "
                       "Every track gets its own Windows... and its own sixteen Sound Recorders.",
     "New in 1.4: the Song tab. Import a MIDI file, give each track a preset, and render. "
     "Every track gets its own Windows, and its own sixteen Sound Recorders."),
    ('s_more', 'HOST', "Drum kits, with a calculator for the pads. A Minesweeper sequencer: numbers play, flags accent. "
                       "And it records... into a real Sound Recorder.",
     "Drum kits, with a calculator for the pads. A Minesweeper sequencer: numbers play, flags accent. And it records, into a real Sound Recorder."),
    ('s_bye', 'HOST', "Take your time. Windows will wait. I'm Clement Ashby... and this has been Computing at Your Pace.",
     "Take your time. Windows will wait. I'm Clement Ashby, and this has been Computing at Your Pace."),
]

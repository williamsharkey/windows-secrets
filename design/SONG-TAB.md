# SNDWAVE1993: the Song tab (a proposal for 1.4)

The Song tab composes, voices, mixes and renders multi-instrument songs inside SNDWAVE1993. It is the plugin
version of `tools/songrender`, the headless renderer that made the pack demo songs (one per pack so far, 25 songs,
about 300 stems). Everything below comes from building and running that renderer. The measured numbers are from it.

## 1. What it does

- **Import or write the notes.** A Standard MIDI File (type 0 or 1), or notes entered on the tab. Up to 16 tracks.
- **Voice each track.** Each track gets a preset from any inserted pack disc, or a DNA typed in. Its MIDI channel or
  file track is its source. It has a transpose and a fine tune in cents.
- **Mix.** Each track has volume, pan, sends to one shared echo and one shared reverb, and mute and solo. The master
  has a loudness target and a true-peak ceiling.
- **Render.** Every track is played by its own emulated Windows 3.11 with its own 16 Sound Recorders, offline, then
  mixed. The result is a WAV in My Recordings. It plays back through a recorder like any other recording, or
  exports through the host's file dialog.

What sounds is the same rule as the rest of SNDWAVE1993: every note is played by Sound Recorder. The mixer only
scales, delays and sums the recorders' output.

## 2. The page (Windows 3.11, no new widget kinds)

Windows 3.1 already had the model for this page: Control Panel's **MIDI Mapper**. Its Setup dialog is a 16-row grid
of channels with a destination and a patch map. The Song tab is that grid, with the presets in place of ports, plus
**Media Player**'s transport and a **Voice Mixer** strip (the Program Manager group that 1.3.0 already has). Every
control is a stock Win16 control: push buttons, check boxes, combo boxes, list boxes and scroll bars. The tab is
built and torn down like the other pages (one repaint per switch).

```
 [Main][Voices][Playback][Scales][Rec][Mines][Library][Song]            <- the tab row in the DNA row
 +-----------------------------------------------------------------------------------------------+
 | Song: [The Leaning Cloister Galliard        ]  Tempo [104]  Bars [ 33]  [Import MIDI...][Save..]|
 |  Src   Preset (pack: name)                Tr   Tune  Vol      Pan      Echo  Verb  M  S  Active|
 |  Ch 1  [courtyard-chapel: Slate Pick   v] [ 0] [ -5] [==|===] [==|==]  [ 5] [32]  [ ][ ]  [x]  |
 |  Ch 2  [courtyard-chapel: Soft Etude   v] [ 0] [ -5] [=|====] [|====]  [ 0] [22]  [ ][ ]  [x]  |
 |  ...   (16 rows; a row with no notes is greyed)                                                 |
 |  Ch16  [(none)                         v]                                                       |
 | [Notes...]  [Echo...] [Reverb...]  Master: Loudness [-16] LUFS  Ceiling [-1.0] dB              |
 | [|<<] [ > ] [ [] ] [ Render ]  ==========|=================  0:41 / 1:33    Engines [4 v]       |
 | Status: Rendering track 3 of 8 (Faded Pluck): 61%                                              |
 +-----------------------------------------------------------------------------------------------+
```

- **The grid.** One row per MIDI channel. The Src combo can name a file track instead (`Tr 3`) or a channel and a
  track together.
  - The Preset combo lists the inserted pack discs' presets by pack. Its last entry, "DNA...", opens the DNA line
    for that track.
  - Vol and Pan are horizontal scroll bars, as in the Voice Mixer. Echo and Verb are edit fields from 0 to 100.
  - Tune comes from the preset's measured tuning (section 6) until the user changes it.
- **Notes...** opens a list box of the track's events: bar:beat:tick, note, velocity and length, in the system
  fixed font. It is the event list that Windows 3.1 sequencers used. Insert, Delete and Edit buttons change it.
  A piano roll drawn in a child window (16 colours, one per channel, cells like the Mines board) can follow later.
  The event list is enough to fix a note, and import does the rest.
- **Transport.** Media Player's buttons: Rewind, Play, Stop, and Render.
  - Play plays the last render, through a recorder, from the scroll bar's position.
  - Before a render exists, Play plays the selected track live through this instance's own recorders. That is an
    audition, not the mix.
- **Engines** sets how many emulators render at once, from 1 to 8. The default is the host's cores minus two,
  capped at 4.

## 3. How it maps onto recorders and engines

**One engine per track.** An instance's Windows has 16 recorders. A song needs them per track: a pad chord with a
harmony gene can hold 8 recorders, and a kit can hold all 16. Splitting one Windows' recorders between tracks would
leave each track two recorders. So the Song tab works the way `songrender` does, and the way a DAW with one plugin per
track does: each track renders in its own emulated PC.

| | The instance's own Windows (on screen) | A render engine (one per track) |
|---|---|---|
| What it is | the editor, the tabs, live playing | DOSBox Pure core + the machine snapshot, no screen (`vid_want = 0`) |
| Lifetime | the instance's | one track's render, then freed |
| Builds | the instance's DNA | the track's DNA, built by Sound Recorder (no assembly animation) |
| Plays | live MIDI, previews | the track's notes, stamped to the DAC sample (render311's loop) |
| Output | the plugin output | a stem in memory (float) |

- **The engine is render311's code.** It moves from `tools/render311.cpp` into `plugin/SongEngine.h`, so the
  plugin and the command line share one loop:
  1. resume the snapshot;
  2. send `hi 3`, the pack list and the DNA;
  3. wait for `built`;
  4. send the layer envelopes;
  5. stamp every note `kLat` after its time;
  6. read the DAC ring.

  Each engine runs on a worker thread with its own private copy of the core. That is the same rule as instances
  today: a copy each, so their statics never meet.
- **Mixing** is host code in double precision:
  - track gain from volume or a loudness target;
  - constant-power pan;
  - the echo and reverb as convolutions (a seeded reverb impulse response, so it is deterministic);
  - BS.1770 loudness;
  - a look-ahead limiter on 4x-oversampled peaks.

  It is `songrender.py`'s mix, ported (about 300 lines).
- **The result.** The mixed WAV goes to My Recordings as `u_song_<slug>` (RECORDING.md). It plays through a recorder.
  Projects keep it by hash, so a reloaded project plays at once and never needs a render.

## 4. CPU, memory and time

Measured with `songrender` on the build PC (16 cores, x86-64, Linux):

| Measure | Value |
|---|---|
| One engine, idle PC | 7-8.5x real time (render311's own figure) |
| One engine, PC loaded by other work (load 9-22) | 1.5-3.1x real time; a dense harpsichord part (638 events) 1.5x |
| Resume + build per track | 1.2-4.2 s (8.9 s for a long collage under load) |
| 8-track, 93 s song, 6 engines at once, loaded PC | 84 s for the stems, 20 s for the mix (Python; C++ will be faster) |
| Late notes | 0 in every render so far |
| Stem, 24-bit FLAC | about 3 MB per track-minute (silence compresses) |
| Repeat renders | bit-identical stems, WAV, Opus and MP3 |

For the plugin:
- **Time.** 4 engines on a typical 8-core machine render an 8-track, 2-minute song in about 30-60 s.
- **The host keeps running.** Engines run at below-normal thread priority. The instance's own Windows keeps playing
  live, and offline host renders of other tracks are unaffected.
- **Memory.** Each engine is one DOSBox Pure core plus the machine (the snapshot and the drive): about 40-60 MB.
  4 engines are about 200 MB, freed after the render.
- **Real time.** Real-time multi-engine playback (no render) costs about a third of a core per playing engine
  (README: 33-38 % playing). It is possible for 4-6 tracks, but it is not proposed for 1.4. Live playback never
  waits for Windows, so a live song would start silently while each engine assembles, and it would differ from the
  render. Render-then-play is exact and cheap.

## 5. State format

The song lives in the plugin state as extra lines (`bsynth::State::extra`, the mechanism `key`, `packs` and `user`
lines use), so old builds ignore it and keep it:

```
song 1
songtext <base64 of the .song text: the exact format of tools/songrender/README.md>
songmidi <base64 of the Standard MIDI File, up to 512 KB>
songmix <sha256 of the last render>            (the render itself is a `user` recording line, by hash)
```

- **The `.song` text is the source of truth.** It is typable, diffable, and the same file `songrender.py` reads, so
  a song made in the plugin renders headlessly and the other way round. It names presets as `pack:Name` and keeps
  their DNA alongside, so it plays even when the pack has changed.
- **File menu.** Save Song... and Load Song... write and read a `.sng` zip holding `song.song`, `song.mid` and,
  optionally, the stems. That matches the `.b16` Save/Load buttons in the DNA row.
- **Size.** A song's text and MIDI are a few kilobytes. The mix is a recording: up to 8 MB is embedded, as with other
  recordings, and a longer song is kept by hash and re-rendered (bit-identically) when it is missing.

## 6. What building the renderer taught us

- **Pitch offsets.** Many system-sound presets sit about +50 to +58 cents sharp. `ringout`, `xpding` and `ding`
  have their own pitch between semitones. Next to a sampled piano or strings, that is audible.
  - `audition.py` measured all 1,385 presets (YIN on C3, C4 and C5).
  - `make_tuning.py` keeps the clean measurements: 133 presets with a stable offset of 10-90 cents.
  - The song applies them as a pitch bend at the start of the track, through the DNA's own bend range.

  The Song tab should do the same with a built-in table, and show it in the Tune column. It would be better still
  if the library builder tuned these presets' roots in a later pack update.
- **Octave registers vary by preset.** The demo phrases (`tools/sndrec-demo/phrases.py`) set each category's range:
  bass 41-57, lead 67-76, pads 41-64. The Song tab should show a track's range against its preset's.
- **Balance by loudness.** Balancing tracks by measured stem loudness (`lufs=` per track) gave sensible mixes
  without hand-tuned dB: kit -16 to -17, bass -19, lead -19 to -20, pads -24 to -26, effects -24 to -28. The tab's
  Vol column should default to "auto" (a loudness target per category) and let the user offset it.
- **Long holds.** A held sound longer than its sample (up to 30 s on the library disc) stops when the sample ends.
  `hold()` re-strikes long drones in pieces. The tab should warn when a note is longer than its preset's
  sample.
- **Same-pitch overlaps.** Two overlapping notes of the same pitch on one track: the second note-off may end the
  first. The importer should trim overlaps, as `compose.py` and the MIDI writer do (note-offs before note-ons on
  the same tick).
- **Kits and tuned keys.** The kits use General MIDI pads (36 kick, 38 snare, 42/44/46 hats, 41-50 pitched toms).
  The electromechanical kits also have a tuned octave (72-84 or 60-72), and that is enough for a tune. The note list
  should label pads with the kit's names.
- **Determinism.** The stems, the mix and the encodes are bit-identical across runs. The cache key is the hash of
  the engine, the machine snapshot, the DNA and the track's MIDI. The tab can keep stems between renders and
  re-render only the tracks that changed. A mix change alone re-renders nothing.

## 7. Work, in order

1. **Move the engine.** Move render311's loop into `plugin/SongEngine.h`; render311 then calls it. The code does
   not change, and render311's bit-identity tests keep passing.
2. **The song text.** `core/song.cpp` holds the `.song` parser and writer (a port of `songrender.py`'s) and the MIDI
   split. Round-trip tests against `songrender.py` on the 25 demo songs.
3. **The mixer.** The mixer in C++ (gain, pan, echo and reverb convolution, loudness, limiter). A test: the mix of a
   demo song's cached stems equals `songrender.py`'s WAV within 1 LSB at 24-bit.
4. **The Song tab.** The grid, transport, Render with engines on worker threads, and the result into My Recordings.
5. **Import and export.** Import MIDI, Save and Load Song, export the WAV, the state lines.
6. **Tests.**
   - A BasiliskHost `--song` run of the plugin's own Render, compared with `songrender.py --engine render311`.
   - pluginval.
   - A CPU check that a render with 4 engines leaves the instance's live playback without dropouts.

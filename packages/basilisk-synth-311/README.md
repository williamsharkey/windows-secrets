# SNDWAVE1993

**Executive Audiophile Edition.** Total sound solutions for globalized audio.

SNDWAVE1993 by William Sharkey is a sixteen-voice synthesizer built from real Sound Recorders. It is a VST3 and
CLAP instrument for Windows and macOS, and an Audio Unit for macOS. Each instance runs its own Windows for
Workgroups 3.11, and every note is played by a real SOUNDREC.EXE in it.

(The code, folders and file names in this package still use its working name, basilisk-synth-311.)

1. **Assembly.** Sixteen Sound Recorders lose their menus and title bars and line up into one synthesizer, with
   Clock, a panel, an envelope view and a Recorder. The strips are numbered 0 to F with Calculator's own hex keys,
   taken from a real Calculator. All this takes under 6 seconds after the plugin loads.
2. **Notes.** The plugin picks a recorder, Windows presses its Play button, and Sound Recorder's own buffer goes out
   through the emulated sound card into your DAW.
3. **The DNA.** A DNA string is a recipe of Sound Recorder commands (`../basilisk-synth/DNA.md`), for example
   `chimesE+;R900`. It is built inside Windows with Sound Recorder's own menus (volume, speed, echo, reverse, copy,
   paste, insert and mix files, delete before and after), and it also sets pools, harmony, unison, transpose, the
   envelope, layers, macros and the v3 genes below.

## Install

Nothing is signed with a developer identity. The macOS bundles are ad-hoc signed; the Windows files are unsigned.

**Windows**
- Copy `SNDWAVE1993.vst3` (the whole folder) to `C:\Program Files\Common Files\VST3`.
- For CLAP hosts, also copy `SNDWAVE1993.clap` to `C:\Program Files\Common Files\CLAP`. The CLAP uses the machine
  inside the installed `SNDWAVE1993.vst3`, so install both.
- Rescan plugins. It appears as an instrument, "SNDWAVE1993" by Algorithmic Industries.

**macOS**
- Copy `SNDWAVE1993.vst3` to `~/Library/Audio/Plug-Ins/VST3` (always: it carries the machine).
- Copy `SNDWAVE1993.component` to `~/Library/Audio/Plug-Ins/Components` and, for CLAP hosts, `SNDWAVE1993.clap` to
  `~/Library/Audio/Plug-Ins/CLAP`.
- Because the bundles are not notarized, run once in Terminal:
  `xattr -dr com.apple.quarantine ~/Library/Audio/Plug-Ins/*/SNDWAVE1993.*`
- Restart the DAW. In Logic, the AU is under AU Instruments > Algorithmic Industries.

**From SNDWAVE2000 (1.4 and earlier):** SNDWAVE1993 is the same plugin under its new name, with the same IDs. Remove
SNDWAVE2000.vst3 (and .component and .clap on macOS) before installing, so the host does not see two plugins with one
ID. Projects open as they were, and your recordings stay where they are (Documents/SNDWAVE2000 is used while it is the
only folder).

**Projects from BASILISK 16** (the name of versions up to 1.2.1) open as they were: the plugin keeps the same VST3
class, AU codes and CLAP id, the same state format and `.b16` files.

## What is new in 1.4.0

- **The Song tab.** A song is a MIDI file and its tracks. Each track takes its notes from a MIDI channel or file
  track, and its sound from a pack disc preset or a DNA. Each track also has transpose, fine tune, volume, pan, and
  sends to one echo and one reverb. The master has a loudness target and a true-peak ceiling. Render plays every
  track in its own Windows for Workgroups 3.11, on its own sixteen Sound Recorders, offline, and then mixes them.
  Play plays the mix through the plugin's output. Export WAV... writes it. Import MIDI..., Open... (`.mid`,
  `.song`, `.sng`) and Save... (`.sng`) use the host's file dialogs, and the project keeps the song.
- **Notes...** lists the selected track's notes (bar:beat:tick, note, velocity, length). Insert, Change and Delete
  edit them, so a song can be written on the tab as well as imported.
- **Measured tuning.** 132 pack presets sit between semitones; choosing one for a track sets its Tune to the
  correction.
- **Rainy Loft Collection**, the 26th pack disc (80 presets).
- **Faster.** While no editor shows the screen, Windows' frames are not drawn (the emulation is unchanged). Offline
  renders are up to twice as fast.
- **One machine for every computer.** Linux, Windows and macOS (Apple silicon and Intel) resume the same snapshot
  and render the same bytes.
- **render311 --song** renders a `.song` file (tools/songrender's format) as the Song tab does.
- Fixed: the Library tab and the sequencer kits (1.3.1).

## What is new in 1.3.1

- **The Library tab** opens the Library page. In 1.3.0 it opened the Save state dialog.
- **Sequencer kits** sound before the Mines tab has been opened. In 1.3.0, seven Kit Manager 98 kits that use the
  step sequencer stayed silent until then.

## What is new in 1.3.0

- **The name.** BASILISK 16 is now SNDWAVE1993. The title screen, the Program Manager group (SNDWAVE1993, 16
  Recorders, Voice Mixer, Read Me, Setup, Help), the About box (the window's system menu) and the help
  (C:\BS\SNDWAVE.HLP, F1) carry it.
- **Tabs** under the DNA line: Main, Voices, Playback, Scales, Rec, Mines and Library.
- **DNA v3** (PRESET-ENGINE-2): windows into the buffer (`W`), voice modes and stacks (`N`, `S`, `D`), humanize
  (`Y`), tape wow, flutter and scoop (`V`), key zones (`Z`, one sample per key range), grains (`G`), kits (`k`
  pads with chokes and velocity layers; the kit button opens a pad calculator), and the mine-grid sequencer (`x`).
- **Keys and scales.** Key, Scale, Use Preset Scale, Snap, Remap Keys, Remap Anchor and Key Labels are automatable
  parameters. The Scales page picks notes, imports Scala `.scl`/`.kbm` files, and the keyboard strip turns linear
  for remaps and tunings that are not 12-note.
- **Recording.** The plugin has a stereo sidechain input. The Recorder (an eighteenth Sound Recorder, in the header
  and on the Rec page) records it, or the synth's own output; File > Save As keeps the take in
  Documents/SNDWAVE1993/My Recordings, where every instance and project can use it (`u_name`). To slot N, To all
  16, per-strip takes (Record on a strip), Export and Import WAV. Projects carry the recordings they use (up to
  8 MB) and restore them by hash.
- **The mine-grid sequencer.** The Mines tab runs the real Minesweeper. Its board is the pattern: rows are notes of
  the scale, columns are steps, numbers play, flags accent, a lost game raises its columns an octave. The steps
  follow the host's transport.
- **The Library tab.** The pack discs are drive P:. Pick a disc, its presets, Insert or Eject; Read Me opens its
  notes. A preset that needs a disc's sounds inserts the disc itself. File Manager opens `.BSP` presets by
  double-click.
- **States.** Save... and Load... in the DNA row write and read `.b16` files through the host's file dialog.
- **Renders** are bit-identical run to run and across Linux, Windows and macOS, independent of the machine's load.

## Playing it

- **Pixels.** Windows' screen is drawn at a whole number of device pixels per Windows pixel, never smoothed; the
  editor is at least 1024x768 and centres the screen on Windows' grey at in-between sizes.
- **The editor is Windows 3.11.** Click Sound Recorder's buttons, type a DNA into the DNA line (Enter applies it,
  Esc puts it back), or use the header (presets, sounds, pan, offset, envelope points), the tabs, the keyboard
  strip (five octaves, bend, mod, Hold, computer keys `a w s e d f t g y h u j k`, `z`/`x` octave) and the strips'
  own buttons and Seek bars.
- **Programs.** 76 in the DAW's program list and in Windows' Preset drop-down; the pack discs add 1,300 more in the
  Library tab.
- **Automatable parameters.** Attack, Decay, Sustain, Release, Velocity, Bend Range, Output Gain, Transpose, Macro
  1-4 (the mod wheel adds to Macro 1), and the seven key and scale parameters.
- **Sounds.** `chimes chord ding tada ringin ringout` are the Windows 3.x files in C:\WINDOWS; XP's sounds are in
  C:\XPSOUNDS; the library disc (L:) has 510 more; the pack discs (P:) bring their own; your recordings are
  `u_` names.
- **Latency.** A fixed 2880 samples at 48 kHz (60 ms), plus host blocks over 512 samples; DAWs compensate it.
- **Rebuilds.** A new DNA is built in place, one recorder at a time, while the old sound keeps playing. Offline
  renders wait for every build, so a render comes out the same every time.

## How the sound gets out

```
MIDI -> plugin (voice allocation: packages/basilisk-synth/core, plugin/V3Alloc.h, V3Host.h)
     -> "on 3 44100 52000" + event id + DAC sample, in the BSYN card's mailbox
     -> SYNTH.EXE (in Windows): arms recorder 3's task with the id, presses Rewind, Play
     -> SOUNDREC.EXE: waveOutOpen / waveOutWrite (its own buffer, after its own effects)
     -> BSYNTH.DRV (a Windows 3.11 wave driver): one card voice per waveOutOpen
     -> BSYN card (dosbox-pure/bsynth.cpp): rate conversion, tape modulation, envelopes, 48 kHz DAC
     -> engine thread -> plugin output (resampled to the host rate)
```

- BSYN has 32 voices, so sixteen recorders play at once; notes start on their stamped DAC sample.
- The emulator is DOSBox Pure, patched with the card, in-process on a thread of each instance, from a private copy
  of the core. The build froze the machine with the recorders open; the plugin resumes from it in about 0.03 s.
- Offline, the card passes the host's events and replies only at emulated frame boundaries, and DOSBox Pure runs
  each frame to its end before returning, so renders do not depend on the wall clock.

## Batch rendering

```
render311 --machine DIR --core FILE --dna "DNA" (--midi in.mid | --score "t:note:vel:dur,...") --out out.wav
          [--tail S] [--bits 32] [--bpm BPM] [--key ..] [--scale ..] [--scala FILE.scl] [--grid "w h state cells"]
          [--user-dir DIR] [--lookahead MS]
render311 --machine DIR --core FILE --song SONG.song --out mix.wav [--jobs N] [--stems DIR] [--lookahead MS]
python3 tools/batch_render311.py JOBS.json --machine DIR [--render311 EXE] [--parallel K] [--out-dir OUT]
```

- DIR is the bundle's `Contents/Resources/machine`, given as an absolute path. The release has `render311.exe`
  (Windows) and `render311` (macOS, universal); renders are bit-identical on Linux, Windows and macOS.
- Every pack disc is inserted in a render.

## Tests

See PROGRESS.md for every number. For 1.3.0:
- pluginval at strictness 10: Windows VST3, macOS VST3 and AU pass; `auval -strict` passes; clap-validator 0.4.1:
  no failures.
- BasiliskHost `--test` (Windows VST3): offline repeats, state and `.vstpreset` reload bit-identical; a live
  program change alone 50/50 notes; two instances; no orphan processes.
- Renders repeat bit-identically; Windows and Linux give the same bytes; 1,306 of 1,318 library and pack presets
  pass their render checks on the release build.
- Recording: concurrent saves from four processes never tear the index; an 8 MB embedded state loads in 0.43 s.
- The 12 Kit Manager 98 electromech kits play in kit mode.

## Build

```
XP_IMAGE=.../base.qcow2 EXTRACTOR=.../archaeology/extract.py \
tools/build.sh WORKDIR        # Linux/WSL: guest (Open Watcom), DOSBox Pure + BSYN, the machine, the pack discs,
                              # the Windows VST3 and CLAP, and WORKDIR/macsrc for the Mac
tools/mac_build.sh WORKDIR    # on a Mac: universal VST3, AU and CLAP, snapshots per CPU
```

| Path | Contents |
|---|---|
| `guest/` | `SYNTH.EXE`, `SNDWAVE.EXE`, `SYNHOOK.DLL`, `BSYNTH.DRV` (Win16 C) |
| `dosbox-pure/` | the card and the patch, against `UPSTREAM.txt` |
| `engine/` | the engine thread and the shared-memory block |
| `plugin/` | the DPF plugin and editor; `dpf.patch` against `DPF_UPSTREAM.txt` |
| `tools/` | build scripts, test rigs, `render311.cpp`, `make_library311.py`, `make_packs311.py`, `make_presets311.py` |
| `presets/` | `b16.tsv`, SNDWAVE1993's own programs |
| `machine-extra/` | Windows 3.1's CHORD.WAV and TADA.WAV, copied into C:\WINDOWS |

## Licences

| Part | Licence |
|---|---|
| SNDWAVE1993 (this plugin, the guest programs, the card) | GPL-2.0-or-later. SNDWAVE1993 by William Sharkey. |
| DOSBox Pure | GPL-2.0-or-later. Source: https://codeberg.org/schelling/dosbox-pure, at the commit in `dosbox-pure/UPSTREAM.txt`, with `dosbox-pure.patch` and `bsynth.cpp`. |
| DPF | ISC |
| Windows for Workgroups 3.11, Windows 3.1's CHORD.WAV and TADA.WAV, Windows XP's sounds (C:\XPSOUNDS, extracted at build time) | Copyright © Microsoft Corporation. |
| Library and pack sounds | each sound's source and licence is in its disc's `\LIBRARY.TSV` (CC0 and public domain). |

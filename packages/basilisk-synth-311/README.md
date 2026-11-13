# BASILISK 16: Windows 3.11's Sound Recorder as an instrument

A VST3 instrument for Windows and macOS, and an Audio Unit for macOS. Each instance runs its own Windows for
Workgroups 3.11.

1. **Assembly.** Sixteen real Sound Recorders (SOUNDREC.EXE) lose their menus and title bars. They line up into
   one synthesizer, alongside Clock and a panel. The strips are numbered 0 to F with Calculator's own hex keys: a
   real Calculator opens in Scientific view and Hex, and its keys fly to the strips. Windows 3.1's Calculator
   paints its keys itself (they are not windows), so these are pixel copies of what it drew; it has no pressed look,
   so a key pressed (an audition of its recorder) or sounding is the same picture with its two colours swapped.
   All this takes under 6 seconds after the plugin loads.
2. **Notes.** Every MIDI note is played by Sound Recorder. The plugin picks a recorder, Windows presses its Play
   button, and Sound Recorder's own buffer goes out through the emulated sound card into your DAW.
3. **The DNA.** A DNA string is a recipe of Sound Recorder commands (`../basilisk-synth/DNA.md`), for example
   `chimesE+;R900`. The recipe is built inside Windows with Sound Recorder's own menus:
   - Increase/Decrease Volume, Increase/Decrease Speed, Add Echo and Reverse
   - Copy, Paste Insert and Paste Mix, Insert File and Mix with File
   - Delete Before/After

   The string also sets pools, harmony, unison, transpose and the envelope. The same DNA plays in the XP edition.
4. **DNA v2 (1.2.0).**
   - **Layers:** up to 8, each with its own start offset (`O`), pan (`Q`), and drawn amplitude and pan envelopes
     (`Ja`, `Jp`).
   - **Macros:** four, automatable, each mapped by the DNA onto layer genes.
   - **Collages:** steps at a time in ms (`@t500Mglass_ping`).
   - **The library disc:** 510 public-domain/CC0 sounds on drive L:, usable by name.

## Install

Nothing is signed with a developer identity, because none is available. The macOS bundles are ad-hoc signed, which
is the strongest free option, and the Windows plugin is unsigned. Hence the steps below.

**Windows**
- Copy `Basilisk16.vst3` (the whole folder) to `C:\Program Files\Common Files\VST3`.
- Rescan plugins in your DAW. It appears as an instrument, "BASILISK 16".

**macOS**
- Copy `Basilisk16.vst3` to `~/Library/Audio/Plug-Ins/VST3`.
- Copy `Basilisk16.component` to `~/Library/Audio/Plug-Ins/Components`.
- Because it isn't notarized, run this once in Terminal:
  `xattr -dr com.apple.quarantine ~/Library/Audio/Plug-Ins/VST3/Basilisk16.vst3 ~/Library/Audio/Plug-Ins/Components/Basilisk16.component`
- Restart the DAW. In Logic, the AU is under AU Instruments > William Sharkey.

## Playing it

- **Pixels.** Windows' screen is drawn at a whole number of device pixels per Windows pixel (1x1, 2x2, 3x3),
  never smoothed: the editor is at least 1024x768, snaps to whole multiples when resized, opens at 2x on a 200%
  display or a Retina Mac, and centres the screen on Windows' grey when the host forces an in-between size.
- **The editor is Windows 3.11.** Click Sound Recorder's buttons, type a DNA into the DNA line (Enter applies it,
  Esc puts it back), or use Windows' own controls:
  - **Header:**
    - Preset: a drop-down of all 72 programs, with < > to step.
    - Sound: every sound, meaning C:\WINDOWS's six and the library's 510.
    - The selected layer's Pan and Offset.
    - Env: the layer's drawn envelope. < > picks a point, + adds, - deletes; then the point's time and level.
    - Envelope: a seventeenth Sound Recorder whose green wave view draws that envelope.
  - **Panel:**
    - Sound: chimes, ding, ringin, ringout.
    - Effects: Sound Recorder's commands, appended to the DNA.
    - Undo and Clear.
    - Layers and Harmony.
    - Voices, Transpose, Unison and Level.
    - Attack, Decay, Sustain and Release.
    - Macro 1-4.
  - **Keyboard strip:**
    - Five octaves of keys (C2-C7). White keys are push buttons, black keys are black-rectangle statics.
    - Bend and Mod scrollbars.
    - Hold (latch).
    - Keys turns on the computer keyboard: `a w s e d f t g y h u j k` play, `z` and `x` change octave.
    - Click or drag over the keys to play. Incoming MIDI notes hold their keys down, and the wheels follow MIDI.

  Each change becomes the plugin's sound and is saved with your project. A change that Sound Recorder must build
  is built in front of you:
  - the recorder's row number lights up;
  - its own status field names each command as it runs (Open, Echo, Insert ding, Seek 500 ms...).
- **Programs.** There are 72 ("Category: Name"): BASILISK 16's own, then the shared library presets.
  `presets/overrides311.tsv` replaces a few shared presets in place with 3.11 versions (their XP sounds would play
  DING here). They appear in
  the DAW's preset list (a VST3 program list, AU factory presets) and in Windows' Preset drop-down. User presets are
  the host's own: they save the DNA.
- **Automatable parameters:**
  - Attack, Decay, Sustain, Release, Velocity, Bend Range, Output Gain and Transpose edit the DNA's globals.
  - Macro 1-4 move whatever the DNA maps them to (`m1L0,150`, `m12Q-100,100`, `m11Z50,200`, ...).
  - The mod wheel (CC1) adds to Macro 1. Pitch bend uses the DNA's range.
- **Sounds (DNA.md 2.4: one name, one file).**
  - `chimes chord ding tada ringin ringout` are the Windows 3.x files in C:\WINDOWS: WfW 3.11's CHIMES, DING,
    RINGIN and RINGOUT, plus Windows 3.1's CHORD and TADA, which WfW 3.11's disks had dropped.
  - Every XP sound plays XP's own file, from `C:\XPSOUNDS\X<nn>.WAV`, converted to PCM Sound Recorder 3.1 opens:
    `notify`, `startup`, `critstop`... and `chimesxp chordxp dingxp tadaxp`, XP's copies of the four.
  - The files come from your own XP image at build time (`tools/xpsounds311.py`, the sound-archaeology extractor);
    XP's audio is not in git.
  - The preset browser in Windows filters [All] [W3.11] [XP]: XP lists the presets that use an XP sound.
  - The library disc (drive L:, `library.zip`) holds the shared library's sounds converted to 22050 Hz 16-bit mono,
    which Sound Recorder 3.1 opens as they are. Sounds over 30 s are skipped.
  - A DNA names them like built-in ones: `marimba_c4E#16`, `piano_upright_cs4#10T-1/glass_ping#6T12O15Q40L50`.
- **Latency.** The plugin reports a fixed latency, which DAWs compensate for on playback. When you play live you
  hear it. It is 2880 samples at 48 kHz (60 ms) with blocks of up to 512 samples; larger host blocks add their
  length.
- **Rebuilds.** A new DNA is built in place, one recorder at a time, while the old sound keeps playing. Notes are
  served between recorders and come out at the right pitch. The new sound takes over when Windows is done, so
  playing is never interrupted.
  - Offline renders, where the host says so, wait for every build and for the assembly, so a render or a reloaded
    project comes out bit-identical every time.
  - Live playback never waits. It is silent for the few seconds Windows takes to assemble.
  - Idle recorders are rebuilt first. A recorder still sounding a note gets up to 1.5 s to finish it.
- **CPU.** Each instance is an emulated PC. Measured on the build PC (x86-64), as a share of one core:

  | | Editor closed | Editor open |
  |---|---|---|
  | Idle | 13 % | 18 % |
  | Playing | 33–38 % | |

  When Windows has nothing to do, the synth program tells the emulated card, which ends the CPU's millisecond
  slice, the way HLT does.

## How the sound gets out

```
MIDI -> plugin (voice allocator, packages/basilisk-synth/core)
     -> "on 3 44100 52000" + event id + DAC sample, in the BSYN card's mailbox
     -> SYNTH.EXE (in Windows): arms recorder 3's task with the id, presses Rewind, Play
     -> SOUNDREC.EXE: waveOutOpen / waveOutWrite (its own buffer, after its own effects)
     -> BSYNTH.DRV (a Windows 3.11 wave driver): one card voice per waveOutOpen
     -> BSYN card (dosbox-pure/bsynth.cpp): the voice's Hermite rate converter, envelope, 48 kHz DAC
     -> engine thread -> plugin output (resampled to the host rate)
```

- **Why a card of our own.** Windows 3.11's SB16 driver plays one sound at a time; a second recorder gets "device
  in use". BSYN has 32 voices, like a Gravis Ultrasound, so sixteen recorders play at once.
- **Pitch.** It is the card voice's playback rate, set at the start of each note. That costs one fixed-point step
  per output sample, with 4-point Hermite interpolation.
- **Timing.** Notes are stamped with a DAC sample number, so they start sample-accurately.
- **The emulator.** It is DOSBox Pure (a libretro core), patched with the card. It runs in-process on a thread of
  each instance, from a private copy of the core, so every instance has its own machine.
- **The snapshot.** The build froze the machine with the sixteen recorders open, and the plugin resumes from it.
  Resume takes about 0.03 s; the assembly then plays.

## Batch rendering

`tools/render311` renders a DNA plus notes to a WAV through the real machine, headless:
- the machine resumes, Sound Recorder builds the DNA (no assembly animation), and the notes play through the
  recorders exactly as the plugin plays them offline;
- it is not paced by a clock, so it runs faster than real time.

```
render311 --machine DIR --core FILE --dna "DNA" (--midi in.mid | --score "t:note:vel:dur,...") --out out.wav [--tail S] [--bits 32]
python3 tools/batch_render311.py JOBS.json --machine DIR [--render311 EXE] [--parallel K] [--out-dir OUT]
```

- JOBS.json is the XP edition's format: `[{"dna": "...", "score": "0:60:100:1.0,...", "out": "x.wav", "tail": 2}]`.
- DIR is the bundle's `Contents/Resources/machine`.
- The release has `render311.exe` (Windows) and `render311` (macOS, universal).
- Renders on Linux and Windows are bit-identical.

## Tests (what was checked, and how)

**Version 1.2.0 additions:** see PROGRESS.md for every number.
- **BasiliskHost** (`tools/basilisk-host`) `--test`, Windows VST3:
  - offline repeats bit-identical;
  - state and `.vstpreset` reload bit-identical;
  - real time: 50/50 notes heard, pitch within 2 cents;
  - live program change at normal PC load: 50/50 notes, none dropped;
  - two instances; no orphan processes.
- **The editor, driven by posted clicks** (`--editor-script`):
  - keys, a drag, Hold latching and releasing;
  - the < > preset button, after which the state holds the new DNA.
- **DNA v2 by measurement:**
  - `O300` starts 300 ms late;
  - `Q-100` and `Q100` are hard left and right;
  - a drawn `Ja` gives the expected gain curve (0.54 at 600 ms against 0.57);
  - a macro on `N` rebuilds.
- **Batch:** all 33 BASILISK 16 programs, 214.5 s of audio in 18.9 s (8 at once, Linux).
- **Assembly with the keyboard strip:** 5.37 s on Windows' clock.
- **pluginval at strictness 10:** 25/25 for Windows VST3, macOS VST3 and macOS AU; `auval -strict` passes.
- **render311:** bit-identical on Linux, Windows, macOS arm64 and macOS x86_64.
- **Live safety:** `process()` never waits in real time (slowest call 14 ms). No inheritable handles. No temporary
  folders left after unload.


**Version 1.1.0 additions**
- **REAPER 7.85** (Windows), running as a separate, isolated copy:
  - 16 presets are listed and selectable;
  - 77 parameters instead of 2093;
  - a saved project reloaded and rendered five times was bit-identical to the original, five out of five;
  - live, on the Dummy Audio device at 48 kHz, all 28 notes sounded across a preset change at 3.15 s, none late;
  - a DNA typed into the editor's Windows became the plugin's saved state.
- **The same MIDI render** was bit-identical on Windows, macOS arm64 and macOS x86_64 under Rosetta.
- **Two Plugalyzer runs** were bit-identical, with 0 late notes.

**Assembly**
- `tools/anim.py` captures frames of the assembly and builds a contact sheet. Each frame was checked by eye for
  glitches, trails and half-drawn parts.
- Time to ready: restore 0.03–0.07 s, plus `go` → `ready` 5.4–5.6 s.

**Pitch and timing**
- `tools/align.py`, plus a test rig driving the engine (`tools/bsdrv.py`).
- Pitch, as FFT peaks: 783.7 Hz at 22050 Hz, 1567.6 Hz at 44100 Hz, 391.7 Hz at 11025 Hz. That is exactly 2× and 0.5×.
- Note onsets fall within 2 samples of the stamped DAC sample.
- No armed start or stop arrived late (the card's `sched_late` counter).

**Plugin validators and hosts**
- pluginval at strictness 10, all 25 test groups:
  - Windows VST3: pass.
  - macOS VST3: pass.
  - macOS AU: pass.
- `auval -strict`: pass.
- REAPER 7.85 (Windows):
  - two instances with two factory programs render at the right times;
  - two renders of the same project are identical (largest difference 1.2e-7);
  - the saved project holds the DNA state.
- Plugalyzer renders on Windows, on macOS arm64 and on macOS x86_64 under Rosetta agree within 0.0003.

**Sound comes from the emulator**
- With `BASILISK16_TEST_STOP_EMULATOR=1` the output is silent; without it, the peak is 0.39.
- The output equals the card's DAC stream (`BASILISK16_TEST_DUMP_DAC`) to within one 16-bit step, shifted by
  exactly the reported latency.

## Build

```
XP_IMAGE=.../base.qcow2 EXTRACTOR=.../archaeology/extract.py \
tools/build.sh WORKDIR        # Linux/WSL: guest (Open Watcom), DOSBox Pure + BSYN, the machine, the Windows VST3
                              # (XP_IMAGE: your XP image, BASILISK SYNTH's; EXTRACTOR: branch feat/sound-archaeology)
tools/mac_build.sh WORKDIR    # on a Mac, with WORKDIR/macsrc from the above: universal VST3 + AU, snapshots per CPU
```

**Layout**

| Path | Contents |
|---|---|
| `guest/` | `SYNTH.EXE`, `SYNHOOK.DLL`, `BSYNTH.DRV` (Win16 C) |
| `dosbox-pure/` | the card and the patch, against `UPSTREAM.txt` |
| `engine/` | the engine thread and the shared-memory block |
| `plugin/` | DPF plugin and editor; `dpf.patch` against `DPF_UPSTREAM.txt` (VST3 program list, fewer MIDI-CC parameters, an offline-render flag for VST3 and AU) |
| `tools/` | build scripts, test rigs, `render311.cpp`, `batch_render311.py`, `make_library311.py`, `make_presets311.py` |
| `presets/` | `b16.tsv`, BASILISK 16's own programs |
| `machine-extra/` | Windows 3.1's CHORD.WAV and TADA.WAV, copied into C:\WINDOWS |

## Licences

| Part | Licence |
|---|---|
| DOSBox Pure | GPL-2.0-or-later. Source: https://codeberg.org/schelling/dosbox-pure, at the commit in `dosbox-pure/UPSTREAM.txt`, with `dosbox-pure.patch` and `bsynth.cpp`. |
| DPF | ISC |
| This plugin | GPL-2.0-or-later |
| Windows for Workgroups 3.11, Windows 3.1's CHORD.WAV and TADA.WAV, XP's sounds (C:\XPSOUNDS, extracted at build time) | © Microsoft, included as part of an art project, as in the BASILISK 3.11 download |
| Library sounds (`library.zip`) | each sound's licence and source is in `\LIBRARY.TSV` (CC0 and public domain; see `packages/basilisk-synth/library`) |

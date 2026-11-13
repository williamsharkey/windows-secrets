# BASILISK 16: Windows 3.11's Sound Recorder as an instrument

A VST3 instrument for Windows and macOS, and an Audio Unit for macOS. Each instance runs its own Windows for
Workgroups 3.11.

1. **Assembly.** Sixteen real Sound Recorders (SOUNDREC.EXE) lose their menus and title bars. They line up into
   one synthesizer, alongside Clock and a panel. This takes under 6 seconds after the plugin loads.
2. **Notes.** Every MIDI note is played by Sound Recorder. The plugin picks a recorder, Windows presses its Play
   button, and Sound Recorder's own buffer goes out through the emulated sound card into your DAW.
3. **The DNA.** A DNA string is a recipe of Sound Recorder commands (`../basilisk-synth/DNA.md`), for example
   `chimesE+;R900`. The recipe is built inside Windows with Sound Recorder's own menus:
   - Increase/Decrease Volume, Increase/Decrease Speed, Add Echo and Reverse
   - Copy, Paste Insert and Paste Mix, Insert File and Mix with File
   - Delete Before/After

   The string also sets pools, harmony, unison, transpose and the envelope. The same DNA plays in the XP edition.

## Install

The plugin is unsigned.

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

- **The editor is Windows 3.11.** Click Sound Recorder's buttons, or use the panel:
  - Sound: chimes, ding, ringin, ringout.
  - Effects: Sound Recorder's commands, appended to the DNA.
  - Undo and Clear.
  - Layers and Harmony.
  - Voices, Transpose, Unison and Level.
  - Attack, Decay, Sustain and Release.

  Each change rebuilds the recorders and becomes the plugin's sound, saved with your project.
- **Factory sounds.** There are 16, from the DAW's program list ("Current Program").
- **Automatable parameters:** Attack, Decay, Sustain, Release, Velocity, Bend Range, Output Gain and Transpose.
  They edit the DNA's globals.
- **Latency.** The plugin reports a fixed latency of 2560 samples at 48 kHz (53 ms). DAWs compensate for it on
  playback. When you play live you hear it.
- **Rebuilds.** A new DNA takes Windows a moment to rebuild. The plugin waits for it, so offline renders are exact;
  live, a preset change costs a moment of silence.
- **CPU.** Each instance is an emulated PC. Measured: about 10–18 % of one core on an Apple M-series Mac, and about
  20–40 % on the build PC (x86-64).

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

## Tests (what was checked, and how)

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
tools/build.sh WORKDIR        # Linux/WSL: guest (Open Watcom), DOSBox Pure + BSYN, the machine, the Windows VST3
tools/mac_build.sh WORKDIR    # on a Mac, with WORKDIR/macsrc from the above: universal VST3 + AU, snapshots per CPU
```

**Layout**

| Path | Contents |
|---|---|
| `guest/` | `SYNTH.EXE`, `SYNHOOK.DLL`, `BSYNTH.DRV` (Win16 C) |
| `dosbox-pure/` | the card and the patch, against `UPSTREAM.txt` |
| `engine/` | the engine thread and the shared-memory block |
| `plugin/` | DPF plugin and editor |
| `tools/` | build scripts and test rigs |

## Licences

| Part | Licence |
|---|---|
| DOSBox Pure | GPL-2.0-or-later. Source: https://codeberg.org/schelling/dosbox-pure, at the commit in `dosbox-pure/UPSTREAM.txt`, with `dosbox-pure.patch` and `bsynth.cpp`. |
| DPF | ISC |
| This plugin | GPL-2.0-or-later |
| Windows for Workgroups 3.11 | © 1993 Microsoft, included as part of an art project, as in the BASILISK 3.11 download |

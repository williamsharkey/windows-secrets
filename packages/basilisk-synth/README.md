BASILISK SYNTH - sixteen Windows XP Sound Recorders, as one instrument in your DAW
==================================================================================

A VST3 instrument for Windows and macOS, plus AU and CLAP on macOS. Every note you play is played by a real
`sndrec32.exe` inside a real Windows XP, through XP's own sound card. The plugin turns MIDI into instructions for
those Sound Recorders and passes on what XP plays. It never makes a sound of its own.

Open the editor and you watch the machine put itself together. Sixteen Sound Recorders sit on XP's desktop. Each
loses its menu bar, then its title bar. Its unused buttons drop off, then it glides into place as one strip of a
16-track tape machine: Play, Stop, Position, the green wave, Length and the slider. Task Manager's CPU and
page-file graphs and the Date and Time clock move in beside them, and a keyboard of real push buttons lays itself
out along the bottom, with Volume Control's sliders as the pitch bend, mod wheel and four macros.

Download
--------
https://github.com/williamsharkey/windows-secrets/releases/tag/basilisk-synth-v1.2.1

| File | Contents |
|---|---|
| `BASILISK-SYNTH-windows-x64.zip` (952 MB) | `BasiliskSynth.vst3`, with Windows XP inside it. Copy it to `C:\Program Files\Common Files\VST3`. |
| `BASILISK-SYNTH-macos.dmg` (932 MB) | `BasiliskSynth.vst3` (with Windows XP inside it), `.component` and `.clap`, universal (Apple Silicon and Intel). Copy them to `~/Library/Audio/Plug-Ins/VST3`, `Components` and `CLAP`; the AU and CLAP use the VST3's machine, so install the VST3 too. |

- **Complete:** Windows XP, its sixteen Sound Recorders and the library disc are inside the plugin. Nothing is
  downloaded on first use.
- **Writes only:** a per-instance overlay in the temp folder (removed when the instance goes), and a log plus the
  unpacked QEMU (Windows) in `%LOCALAPPDATA%\BASILISK SYNTH` or `~/Library/Caches/BASILISK SYNTH`.
- **Unsigned:** nothing is code-signed by Microsoft or Apple.
  - Windows: SmartScreen does not look at plugins, so there is nothing to click.
  - macOS: run `xattr -dr com.apple.quarantine ~/Library/Audio/Plug-Ins/*/BasiliskSynth.*` once, or your DAW will
    refuse to load it.

Playing it
----------
- MIDI notes, velocity, sustain pedal (CC64), pitch bend (applied when a note starts) and all-notes-off.
- **DAW parameters:** Gain, Attack, Decay, Sustain, Release, Velocity, Bend Range, Transpose and Macro 1-4. All
  are automatable. The mod wheel (CC1) adds to Macro 1.
- **Presets:** 39 factory programs named "Category: Name" (Keys, Bells, Pads, Bass, Plucks, Percussion, Collage,
  FX, Macro, Brass, Library), plus whatever the DAW saves. The whole sound is one DNA string kept in the plugin
  state, so DAW projects and preset files restore it exactly (a state saved, loaded and saved again is
  byte-identical).
- **Layers (DNA v2):** up to 8 layers, each on its own pool of recorders, each with an offset from the note
  (`O`), pan (`Q`, applied as the card's left/right volume for that recorder), level (`L`) and a drawn amplitude or
  pan envelope (`Ja`, `Jp`: up to 8 points, applied as the card's volume while the note plays). None of these
  rebuild the sound; the sound itself is still what the recorder made and plays.
- **Library disc:** the machine has a CD drive; the plugin puts the library disc in it after XP wakes. 510 public
  domain / CC0 sounds (tonal instruments, glass and bells, nature, machines, electromechanical, office, water) are names a DNA can use like XP's own
  (`kalimba_c4#10/glass_ping#6T12`).
- **Inside XP (the editor):**
  - Effects and Edit menus that are Sound Recorder's own commands
  - Voices: transpose, harmony and unison
  - Layers
  - a library browser: XP's 35 sounds, the disc's categories and its presets (double-click to use)
  - an envelope editor under the strips: eight upright trackbars (the selected layer's envelope), Length, Offset
    and Pan sliders, and the curve drawn the way Task Manager draws its history
  - Macros: four upright sliders (Tone, Body, Time, Motion = Macro 1-4)
  - the keyboard: 37 keys (C3-C6) that go down for the DAW's notes; the mouse plays them (drag to glide), Hold
    latches, "PC keys" turns on a w s e d f t g y h u j k (z/x octave, c/v velocity); Bend springs back, Mod stays
  - **you see the sounds being built:** while the editor is open, every step of a build is picked from that
    recorder's own File, Edit or Effects menu, which pops up on its strip and walks down to the command
  - a DNA box with Apply, Mutate and Undo
  - Play and Stop on any strip
  Every change is sent back to the DAW as the new DNA.

The DNA
-------
`packages/basilisk-synth/DNA.md` is the full spec, shared with the Windows 3.11 edition. A DNA lists layers, each
with a source sound, a chain of Sound Recorder operations and voice genes, then global settings. For example:

    chord#10/ding>>E#6;A2D300S70R250

This means:

- **Layer 1:** chord.wav on 10 recorders.
- **Layer 2:** ding.wav, Increase Speed twice, Add Echo, on 6 recorders.
- **Globals:** attack 2 ms, decay 300 ms, sustain 70%, release 250 ms.

Steps run in order, using Sound Recorder's real commands:

- **Effects menu:** Increase/Decrease Volume, Increase/Decrease Speed, Add Echo, Reverse.
- **Edit menu:** Copy, Paste Insert, Paste Mix, Insert File, Mix with File, Delete Before/After Current Position.
- **The position slider.**

Order matters, so the space of sounds is enormous.

How the sound gets out of XP
----------------------------
- **The sound card:** XP has an AC97 card. QEMU's `wav` audio backend writes what the card plays into a pipe
  instead of a file: a named pipe on Windows, a FIFO on macOS. The plugin reads that pipe, so the stream is exactly
  XP's output.
- **A continuous stream:** `synth.exe` keeps one silent `waveOut` stream open in XP so the mixer and the card never
  stop.
- **Playback:** the plugin delays the stream by a fixed latency it reports to the DAW, so delay compensation lines
  notes up. It resamples to the session rate with 4-point Hermite interpolation and a slow drift correction.
- **Pitch and shaping:** a small DLL injected into each Sound Recorder (`guest/srhook.c`) plays that recorder's
  own saved sound (its buffer, with its effects).
  - It streams the sound to a card handle opened once at 48 kHz stereo, 20 ms at a time, four chunks ahead.
  - Pitch is the step through the source: the file's rate times 2^(semitones/12), in 16.16 fixed point with
    linear interpolation.
  - Velocity, level, pan and the envelope (ADSR or the drawn `Ja`/`Jp`) are applied to the samples on the way.
    The envelope's clock is the sound itself, so it is exact.
  - Integer arithmetic only: x87 floating point is slow under the emulator.
  - Why not XP's own mixer and volume, as in 1.0-1.1: `waveOutSetVolume` is card-wide on this XP, so one voice's
    envelope moved all of them. Reopening the card at a new rate also cost a note up to 400 ms.
- **Voice allocation:** the voice allocator (`core/voices.cpp`) gives each note a free recorder from its layer's
  pool. If none is free, it takes the oldest, cutting it with a 5 ms fade.

Timing and tests (v1.2)
-----------------------
Measured through our own VST3 hosts (`tools/testhost` with `tools/run_tests.py`, and tools/basilisk-host's
harness; `tools/test-results-*.json`). The Windows PC was shared with other projects' emulators while it ran, so
its timing numbers are the worse of the two.

|                                              | Windows 11                         | macOS, Apple silicon          | v1.1 (Win / mac)        |
|----------------------------------------------|------------------------------------|-------------------------------|-------------------------|
| plugin load -> XP running and linked         | 1.9 s (first load ever: +3.5 s to unpack QEMU) | 0.3 s              | same                    |
| plugin load -> a new sound built, playable   | 4.3 s                              | 0.8 s                         |                         |
| editor: assembly finished                    | 4.1 s                              | (4.4-4.5 s in 1.1)            | 5.6-6.1 / 4.4-4.5 s     |
| reported latency                             | 150 ms (1.2.2; 100 ms before)     | 100 ms                        | 100 / 100 ms            |
| note timing after compensation               | median 3-12 ms, std 37-46 ms       | median -13 ms, std 10-12 ms   | std ~20 / ~5 ms         |
| harness: notes heard of 50 (offline / live)  | 50 / 50                            |                               | 34 / 22 (Windows)       |
| pitch, 10 notes over 3 octaves               | max 14 cents (harness: mean 11-12) | max 2-5 cents                 | 7 / 5.5 cents           |
| same DNA twice (envelope correlation)        | 0.85-0.98 (harness 0.77-0.88)      | 0.98-0.995                    | 0.98-0.99 / 0.995       |
| state saved -> reloaded                      | bytes identical; sound 0.70-0.97   | bytes identical; sound 0.98-0.995 |                     |
| clicks on voice steals                       | none                               | none                          | none                    |
| offline render, two instances, sleep/wake, QEMU killed -> silence, no orphans | pass | pass                    | pass                    |
| pluginval strictness 10                      | SUCCESS                            | SUCCESS (VST3); auval PASS (AU) | SUCCESS / SUCCESS     |

Version 2 of the DNA, measured on rendered audio (both systems):
- **Pan:** `Q-100` gives silence on the right and `Q100` silence on the left, per voice, with other voices sounding.
- **Offset:** `O500` starts its layer 450-500 ms after the first.
- **Drawn envelope:** `Ja0,0.500,100.1000,0` gives 46-51 % at 250 ms and nothing at 1100 ms.
- **Macro:** `m1=0m10L10,100` against `m1=100...` gives a level ratio of 0.10, live by automation too (Macro 1
  from 0 to 100 mid-score: 9.4-10.7x louder).
- **Library:** `kalimba_c4` at note 60 is 263-264 Hz (the sample's own tuning; C4 is 261.6 Hz).
- **Keyboard in XP:** through the editor, the PC key `a` and a mouse click on C4 each played a note
  (peaks 0.19 and 0.27), silent before and after.
- **Program change while notes play:** the new sound takes about 1.5 s to build in Windows. Live, notes in that
  time are not heard (the BasiliskHost harness counts 3-6). Offline renders wait for the build instead.
- **Batch rendering:** 4 jobs on 4 machines at once: 16.5 s of audio in 11.5 s, startup included.

Not reached: renders are not bit-identical from run to run (XP's timing is not sample-accurate, unlike the
3.11 edition), and a busy Windows machine still spreads note timing to about +-40 ms.

What changed for 1.2.1:
- **One name, one file, in both editions** (DNA.md 2.4). `chimes chord ding tada` are now the Windows 3.x
  recordings (3.11's CHIMES and DING, 3.1's CHORD and TADA), which XP carries in `C:\WINDOWS\Media\W31`. XP's own
  copies are `chimesxp chordxp dingxp tadaxp`, shown as `ding-xp` and so on. `ringin` and `ringout` are the same
  file in both Windows. Projects and presets saved by 1.2.0 or earlier are rewritten to the xp names when they
  load, so they sound as before, and the factory programs use them too. A new category, "Windows 3.x", has four
  programs. The browser in Windows filters presets by [All] [W3.11] [XP].
- **Program changes keep sounding:** while a new sound is built, each recorder goes on playing the sound it has
  loaded, so notes during a rebuild play the old preset instead of dropping.
- **Offline renders** wait for the machine to start (and start it again if it failed) and for every layer's sound
  to be built, after a program change too, so a take is never silent. Their note timing still depends on the
  PC being free: on a busy Windows PC offline notes can land up to 0.2 s off (1.2.0 behaves the same).
- **Live macro automation** now shows in Windows (the DNA box and Macros panel follow it).
- **Presets:** `[` and `]` at position 0 are skipped as refused steps, so Chord Thump sounds; Critical Bass trims
  critstop's lead-in so short notes sound.
- The editor draws XP's screen at whole-pixel scales only (this was already in the final 1.2.0 files).

What changed for 1.2:
- **Sound applied inside each Sound Recorder.** XP's `waveOutSetVolume` turned out to be one volume for the whole
  card, not one per voice, so 1.1's per-voice velocity and envelope were last-writer-wins. Each recorder's DLL now
  streams its own saved sound to a card handle opened once at 48 kHz, 4 x 20 ms ahead. It applies the pitch (a
  16.16 fixed-point step, linear interpolation), velocity, level, pan and envelope to the samples in integer
  arithmetic. A note never waits for the card to open (0-16 ms, was up to 400 ms).
- **DNA v2** (offsets, pan, drawn envelopes, collages, macros, the library disc), the keyboard and wheels,
  the macros panel, the envelope editor, the library browser, visible builds and 39 programs.
- **Built in:** the machine is inside the plugin; no first-use download.
- **Never hangs a host:** an offline render waits at most 60 s for the machine, then renders silence. A watchdog
  restarts a machine that goes silent while awake (up to 3 times). QEMU inherits only its log handle. Temp folders
  of crashed hosts are removed at the next start.
- **Forward compatibility:** unknown (later-version) DNA tokens are kept on save.
- **Sharp screen:** the editor draws XP's 1024x768 screen with nearest-neighbour sampling at a whole scale only
  (each XP pixel is exactly 1x1, 2x2, 3x3... device pixels). It opens at the integer scale nearest the system's
  (100-150 % -> 1x, 175-200 % and Retina -> 2x), never goes below 1x, and when a host forces an in-between size it
  centres the image at the largest whole scale on XP's panel colour. Checked in our host at 1024x768 (1x),
  1500x1125 (1x, centred) and 2048x1536 (2x: every 2x2 block exact wherever the window was on screen).

What changed for 1.1:
- **A fast play path inside each Sound Recorder.** Sound Recorder's own Play took 30-300 ms before it opened the card.
  Now srhook.dll keeps a card handle open per recorder and a time-critical thread starts the recorder's own sound
  (the file Sound Recorder saved and reopened: its buffer, its effects) the moment synth.exe sets the recorder's
  event; the handle is reopened only when the note's rate changes. The strip still shows the note: Play held down,
  slider, position and green wave following the sound.
- **QEMU's sound comes in 11 ms pieces, not 23** (96 kHz instead of 44.1 kHz; QEMU's wav writer buffers 4 KB), and
  Windows no longer throttles the windowless QEMU's timers (power throttling off for that process).
- **XP's idle loop halts.** XP's PoIdle finds no processor idle handler on this machine and returns, so the idle loop
  spun at full speed on every virtual CPU. The machine state is saved with PoIdle patched to `sti; hlt; ret` (what
  HalProcessorIdle does). With 2 vCPUs XP then woke a halted CPU only on the next clock tick, so the machine is now
  1 vCPU with single-threaded TCG, which is also the fastest for the assembly.
- **The assembly** is a quick wave (menu bar, frame, unused buttons) and then one strip at a time reshapes where it
  stands and glides whole into place; a moving strip carries its own pixels, so frames are not half drawn. At the
  end every strip is snapped exactly into place.
- The guest's COM1 is overlapped I/O (a stalled write no longer blocks reads).

The machine
-----------
- **One machine per instance:** each plugin instance runs its own QEMU as a hidden child process. It uses a
  throwaway overlay over the shared, read-only machine disk and its own sixteen recorders. Instances are independent
  and play at the same time.
- **Built in:** the machine ships inside the plugin, in `BasiliskSynth.vst3/Contents/Resources/machine`
  (`base.qcow2` with zstd-compressed clusters and its free space zeroed, `state.mig`, firmware and the library disc).
  QEMU reads the disk in place, read-only; each instance writes only to its own overlay in the temp folder, which
  is removed when the instance goes (and leftovers of crashed hosts are removed at the next start). Nothing is
  downloaded. On macOS the AU and CLAP use the VST3's copy, so install the VST3 too.
- **Fast resume:** QEMU resumes from the shipped machine state (a migration stream, streamed in over loopback) in
  about a second, with XP already logged in and the sixteen recorders open.
- **When it goes away:**
  - Removing the instance ends QEMU at once.
  - On Windows, a job object kills QEMU even if the DAW crashes.
  - On macOS, a watchdog does the same.
- **Sleep:** XP never truly idles under emulation; its idle loop spins about 75% of a core per virtual CPU. So the
  machine is paused after 4 quiet seconds (no note sounding, editor closed) and wakes for the next note.
- **Hardware:** the virtual machine has 1 vCPU, 512 MB, AC97 and no network to the outside (`restrict=on`).

What's inside
-------------
| Path | What it is |
|---|---|
| `plugin/` | The DPF plugin (https://github.com/DISTRHO/DPF, ISC licence, commit 4238e1c). `Machine.cpp` holds QEMU, the pipe, COM1 and VNC. `BasiliskSynthPlugin.cpp` holds MIDI and audio. `BasiliskSynthUI.cpp` shows XP's screen and passes on mouse and keys. |
| `core/` | DNA parsing, the voice allocator and the protocol. Shared with the 3.11 edition. |
| `guest/` | `synth.c` (the conductor in XP: animation, panels, COM1) and `srhook.c` (inside each Sound Recorder). Both are compiled in XP with tcc. |
| `tools/make_machine.py` | Builds the shipped machine from a prepared XP disk. |
| `tools/testhost/` | `bsynth-host`, a small VST3 host for the tests and for demos: render, offline, instances, state, automation (`--set NAME@T=V`, `program`), editor input (`--ui T:click:X:Y`, `key:C`), `--state-roundtrip`, `--timing`, editor frames (`--shots`). |
| `tools/batch_render.py` | DNA + score or MIDI -> WAV through the real machine, several VMs in parallel. |
| `tools/make_library.py`, `tools/make_presets.py` | The library disc (ISO 9660 + Joliet) and the programs (`presets_gen.h`, `PRESETS.TSV`) from `library/`. |
| `tools/run_tests.py` | The end-to-end checks. |

Batch rendering and demo capture
--------------------------------
**Batch rendering** (DNA.md 5.6): a job list in, one WAV per job out, each through its own plugin instance and its
own Windows XP. XP plays in real time, so throughput comes from running several machines at once.

    [{"dna": "kalimba_c4#10/glass_ping#6T12;R300", "score": "0:60:100:0.5,0.5:64:100:0.5", "out": "kalimba.wav", "tail": 2},
     {"dna": "chord#10/ding>>E#6;A2D300S70R250", "midi": "phrase.mid", "out": "chord-phrase.wav"}]

    python3 tools/batch_render.py jobs.json --host bsynth-host.exe --plugin BasiliskSynth.vst3 --parallel 4 --out-dir out

Scores are `t:note:velocity:duration` in seconds; `midi` takes a standard MIDI file (all tracks). Builds are not
shown during batch renders (`BSYNTH_VISIBLE_BUILD=0`). It writes `out/batch.json` with each job's length, peak and
wall time.

**Editor video with its audio** (Windows): `bsynth-host` opens the real editor, plays a score and saves a frame of
the editor every `--shots` seconds, named in order, next to the WAV of the same run:

    bsynth-host.exe BasiliskSynth.vst3 demo.wav --editor --shots 0.04 frames --warmup 10 --tail 3 ^
        --dna "kalimba_c4#10/glass_ping#6T12;R300" --score "0:60:100:0.5,0.5:64:100:0.5,1:67:100:1"
    ffmpeg -framerate 25 -i frames\%06d.bmp -i demo.wav -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest demo.mp4

Frame N is at N x 0.04 s of the same clock as the audio, from the moment the plugin loads (so the assembly is in
the video). `--ui T:click:X:Y`, `--ui T:key:a` and `--set "Macro 1@T=V"` script clicks, typing and automation
into the take. The window must stay visible on screen while it records.

Builds
------
- **Windows:** `make WINDOWS=true CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix` from Linux. Then put QEMU for Windows (Stefan Weil's build, as in packages/basilisk-xp), still zipped, at `BasiliskSynth.vst3/Contents/Resources/qemu-win64.zip` (the plugin unpacks it once into `%LOCALAPPDATA%\BASILISK SYNTH`, so no QEMU `.dll` sits in a VST folder for hosts to probe), and the machine (`tools/make_machine.py` output) in `Contents/Resources/machine`.
- **macOS:** `make MACOS=true` with universal `-arch` flags. Then put the Homebrew QEMU builds from
  packages/basilisk-xp in `Contents/Resources/qemu-arm64` and `qemu-x86_64`, the machine in the VST3's
  `Contents/Resources/machine`, and ad-hoc sign.

Windows XP is Microsoft's; its sounds and Sound Recorder are Microsoft's. QEMU is GPL v2 (source: qemu.org).
DPF is ISC.

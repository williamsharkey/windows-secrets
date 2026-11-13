BasiliskHost - a small VST3 host for testing BASILISK SYNTH and BASILISK 16
============================================================================

`BasiliskHost.exe` is one static Windows executable (1.8 MB, no DLLs beside it). It loads any VST3 instrument, runs
several instances at once with their own editors, plays them live through WASAPI, and has a command-line harness that
renders, compares and measures, writing a JSON report. It was made so the two BASILISK plugins can be tested without
REAPER. It never starts, looks for or touches REAPER, and it never ends a process by name: the orphan check only looks
at, and with `--kill-orphans` only ends, its own child processes by pid.

Download: https://github.com/williamsharkey/windows-secrets/releases/tag/basilisk-host-v1.0.0

The GUI
-------

    BasiliskHost.exe [PLUGIN.vst3 ...] [--sr 48000] [--block 512] [--device "Speakers"] [--env NAME=VALUE]

- **Instances.** *Load .vst3...* picks a plugin file. *Load bundle...* picks a `.vst3` bundle folder. You can also drop
  bundles or files on the window, or name them on the command line. *Duplicate* adds another instance of the selected
  plugin, *Remove* unloads it, and double-click (or *Editor*) opens its editor. Each instance has its own editor window,
  which is resizable when the plugin allows it (both BASILISKs do). The list shows each instance's reported latency.
- **Audio output (WASAPI).** Choose the device (or *Dummy*: no device, one block per block-length of wall clock, as
  REAPER's Dummy Audio), the sample rate (44.1, 48, 88.2 or 96 kHz) and the block size (64-2048
  frames, the size every `process()` call gets). Shared mode with Windows' own rate conversion, so any rate works on
  any device. The status line shows the WASAPI buffer, the plugin latency, the total output latency, DSP load,
  underruns and the output peak. *Record output* writes everything the host plays (before the volume slider) to a WAV.
- **MIDI.**
  - *MIDI in*: any winmm input device. Notes, CCs and pitch bend reach the plugin.
  - *Play all instances*: on, every instance gets the MIDI; off, only the selected one.
  - The on-screen keyboard (C2-C7): click and drag. The nearer the front of a key, the louder.
  - Computer keyboard: `A W S E D F T G Y H U J K O L P ; '` play a chromatic octave and a half; `Z`/`X` shift the
    octave (the orange bar under the keyboard shows the range); `C`/`V` lower and raise the velocity; hold `Space` for
    the sustain pedal. The keys play while the main window is active.
  - *Sustain* is CC64. *Bend* is the pitch wheel: it springs back to the middle when you let go.
    VST3 has no MIDI CC events, so CCs and bend go to the parameters the plugin maps them to (`IMidiMapping`).
  - *Play .mid...* plays a Standard MIDI File (type 0 or 1, with tempo changes). *Test pattern* plays the built-in
    pattern (below), *Save pattern .mid...* writes it as a MIDI file. *Stop* and *Panic* (all notes off).
- **Parameters** (one window per instance):
  - Every visible parameter has a slider and its value as the plugin prints it. Sliders follow changes made in the
    plugin's editor.
  - *Program* lists the plugin's factory programs (from `IUnitInfo`, or the program-change parameter). After them
    come the `.vstpreset` files in `Documents\VST3 Presets\<vendor>\<plugin>`. Picking one switches to it; `<` `>`
    step through.
  - *Save/Load .vstpreset...* use the standard VST3 preset format. *Save/Load state...* use the host's own `.bhstate`
    file, which holds the component and controller state and checks the plugin's class id on load.
  - **Automation.** Move a parameter's slider to choose it (it gets a `>`). Then:
    - *Rec*, move the slider (here or in the plugin's editor), *Rec* again: that becomes a curve.
    - *Play* loops the curve, sent to the processor every block, and the slider and editor follow it.
    - *Sine* and *Ramp* make a ready curve of the given length and play it.
    - *Clear* removes the curve; touching a playing parameter's slider stops its curve.

The test harness (no GUI)
-------------------------

    BasiliskHost.exe --test PLUGIN.vst3 [options]

It runs the checks, writes WAVs and `report.json` into the output folder, prints a summary and exits with 0 when every
check passes. It is a GUI-subsystem program: from `cmd.exe` use `start /wait`, or pipe it (`| more`). From PowerShell
or WSL it waits on its own.

| Option | Default | Meaning |
|---|---|---|
| `--out-dir DIR` | `bhtest-<date>-<time>` | where the WAVs, states and report go |
| `--report FILE` | `DIR\report.json` | the JSON report |
| `--tests LIST` | all but `editor` | any of `offline,realtime,repeat,state,preset,progchange,multi,editor,orphans` |
| `--pattern LIST` | `all` | sections of the test pattern: `scale,chords,repeats,sustain,bend` |
| `--midi FILE.mid` | | render a MIDI file instead |
| `--score "t:note:vel:dur,..."` | | or notes given inline (seconds), as `bsynth-host --score` |
| `--sr HZ` / `--block N` | 48000 / 512 | processing rate and block size |
| `--warmup S` / `--tail S` | 8 / 2 | silence before the score (the emulators start and assemble) and after it |
| `--render-timeout S` | 4x the render + 120 | give up on a render (a hung emulator) after S seconds; it is reported and fails |
| `--repeat N` | 2 | extra offline renders compared with the first |
| `--instances K` | 2 | instances in the multi-instance render (instance k gets program k) |
| `--multi-programs 0,2` | 0,1,... | programs of the multi-instance render's instances |
| `--program N` | | factory program for every render |
| `--state-program N` | 3 | program used for the state and .vstpreset round trips |
| `--load-state FILE` | | a `.bhstate`, `.vstpreset` or raw component state applied before rendering |
| `--automate "NAME:t=v;t=v"` | | an automation curve (seconds, normalized value) by parameter name or id; repeatable |
| `--change-at S` / `--change-program N` | middle / 3 | the `progchange` test: when (score seconds) and to which program |
| `--editor-script "STEP\|STEP..."` | wait 8, two shots | the `editor` test's steps, separated by `\|` (below) |
| `--editor-script-file FILE` | | the same, one step per line (`#` comments) |
| `--state-contains TEXT` | | `editor` test: the plugin's final state must contain TEXT |
| `--env NAME=VALUE` | | set before loading, e.g. `BSYNTH_MACHINE_DIR=D:\xp` |
| `--kill-orphans` | | end child processes still running after the check (own children, by pid) |

The tests:

- **offline**: render with `processMode = kOffline`, as fast as the plugin allows.
- **realtime**: the same, with `kRealtime`, and paced to the wall clock one block at a time. It is compared with
  the offline render, and the lateness of the slowest block is reported.
- **repeat**: N more offline renders, each in a fresh instance, compared with the first. The report has
  bit-identical (yes/no), max difference, sample correlation and loudness-envelope correlation (best over +-300 ms).
- **state**: render with program `--state-program`, save the state (and a `.bhstate` file), load it into a fresh
  instance, render again and compare. It also reports whether the reloaded instance gives back the same state bytes,
  and how far the program's render is from the default one (so a passing reload means something).
- **preset**: the same through a `.vstpreset` file.
- **progchange**: a real-time render in which every instance switches program in the middle of the score, as a
  preset change during playback. It reports the number of notes dropped (no onset found) before, after and within 3 s
  of the change, and lists them.
- **multi**: K instances processed side by side in real time, each with its own program. Each one's level, timing
  and pitch is reported, along with how different instances 0 and 1 are.
- **editor** (not run by default; it opens a window): a real-time render with instance 1's editor open in a window,
  driven by a script of window messages. The steps are:
  - `wait S`
  - `shot NAME` (a BMP of the editor in the output folder)
  - `click X Y`, `dblclick X Y`, `rclick X Y`, `move X Y`, `drag X1 Y1 X2 Y2` (the editor's client coordinates)
  - `type TEXT`
  - `key NAME`: `enter`, `esc`, `tab`, `backspace`, `delete`, arrows, `home`, `end`, `space`, `f1`.., or one
    character, with `ctrl+`, `shift+` and `alt+` prefixes
  - `program N`
  - `resize W H`
  - `state` (logs the state's text)

  Messages are posted with real timing (keys and clicks held 50 ms, 40 ms apart), with real scan codes, and with this
  thread's key state set for modifiers, because an emulated PC reads its keyboard and mouse once a frame. For
  example, this types a DNA into BASILISK 16's Windows and checks that it becomes the plugin's state:

      --tests editor --editor-script "wait 7|click 600 652|key end|key backspace|...|type chimesE+;R900|key enter|wait 3|shot after" --state-contains "chimesE+;R900"
- **orphans**: every child process of the host seen while plugins were loaded (QEMU, tar...), and any still running
  10 s after their instances were released and the modules unloaded.

Every render reports:
- the plugin's reported latency;
- peak and RMS (dBFS);
- per note: the onset (the loudness envelope's first rise) against the MIDI, raw and minus the reported latency, with
  median, mean, std, min, max and spread over the notes (jitter);
- FFT pitch for every single note: the FFT peak in Hz, and the interval to the first scale note measured as the shift
  of the log-frequency spectrum, against the MIDI interval in cents.

These are the same measures as `packages/basilisk-synth/tools/run_tests.py`. The onset is where the sound gets loud,
so a sample with a soft start reads a little late. Chords are timed but not pitched.

**The test pattern** (17.9 s, 50 notes):
- **scale:** C4 to C5, then C3 and C6, one note every 0.6 s;
- **chords:** I-IV-V-I triads, one a second;
- **repeats:** 12 repeats of G4 at 8 per second, then 12 of C5 at 16 per second;
- **sustain:** two short notes held by CC64;
- **bend:** pitch wheel up, a note, wheel back, the note again (both BASILISKs apply bend when a note starts).

Other modes:

    BasiliskHost.exe --write-pattern FILE.mid             the test pattern as a MIDI file
    BasiliskHost.exe --selftest DIR PLUGIN.vst3 [...]     a scripted GUI run (below)
    BasiliskHost.exe --audio-probe [--sr HZ] [--block N]  5 s of a quiet tone: how many frames/s the device really took

`--selftest` runs the GUI as a user would, then exits. It loads each plugin, plus a second instance of the first,
3 s apart, and opens every editor and parameter window. It starts audio, the output tap and a WASAPI loopback capture of the
device, and waits 12 s for the machines to assemble. Then it:
1. screenshots every window (`PrintWindow`);
2. resizes the first editor and screenshots again;
3. clicks C4 E4 G4 on the on-screen keyboard for each instance in turn;
4. plays with posted key presses (`A D G`, `X K Z`, Space as sustain);
5. bends the wheel;
6. presses *Test pattern* with all instances playing;
7. plays a sine automation curve on instance 1's first parameter.

It writes `tap.wav`, `loopback.wav` and `selftest.json` (levels per phase from the tap and the loopback, live
test-pattern timing, audio device facts, orphan check, log), and BMP screenshots.

Testing the two BASILISKs
-------------------------

BASILISK SYNTH looks for its XP machine in `%LOCALAPPDATA%\BASILISK SYNTH\machine-2` and fetches it (788 MB) on first
use. To test with a machine kept elsewhere, use `--env BSYNTH_MACHINE_DIR=<folder with base.qcow2, state.mig, fw\,
machine.ok>`. QEMU is unpacked into the folder above it. BASILISK 16 needs nothing.

    BasiliskHost.exe --test C:\VST3\Basilisk16.vst3 --out-dir C:\t\b16
    BasiliskHost.exe --env BSYNTH_MACHINE_DIR=C:\t\xp\machine-2 --test C:\VST3\BasiliskSynth.vst3 --out-dir C:\t\xp --warmup 10

Results on this PC (Windows 11, 2026-11-13, v1.1.0 of both plugins; full reports and screenshots in `results/`):

| | BASILISK 16 | BASILISK SYNTH |
|---|---|---|
| reported latency | 2880 samples (60 ms) | 4800 samples (100 ms) |
| offline render, test pattern | 50/50 notes heard, peak -4.6 dBFS | 34/50 heard (the 16-per-second repeats are lost) |
| onset error after latency (median, std) | +17 ms, 7 ms (a constant: where each sound gets loud) | +117 ms, 168 ms |
| FFT pitch: mean / max cents off the MIDI interval | 1.0 / 2.0 | 11.7 / 150 (a few notes measured an octave or fifth off) |
| 2 more offline renders | bit-identical | envelope correlation 0.29-0.36 |
| real time vs offline | bit-identical | (not repeatable) |
| state reload into a fresh instance | bit-identical, same state bytes | same state bytes; envelope correlation 0.22 |
| .vstpreset reload | bit-identical | envelope correlation 0.64 |
| program change while playing | 0 of 50 notes dropped (to "Reverse Ding Swell") | to "Ding Bells": the chord 0.5 s after the change dropped, as were most fast repeats |
| editor script | DNA typed into Windows 3.11 became the state | screenshots before and after a click on Play |
| 2 instances at once | both sound, different programs | both sound (programs 0 and 2) |
| child processes after unload | none were started | 23 seen, 0 left |

BASILISK SYNTH's timing on this PC is far from its README's (+-25 ms): a test run of the older `bsynth-host` on the same
scale gave onsets 108-385 ms late, so the cause is not this host.

Found while building this host (v1.1.0 plugins):
- **BASILISK 16 created while BASILISK SYNTH starts.** In one process, a BASILISK 16 instance created right after a
  BASILISK SYNTH instance is activated can fail with "cannot load the core": black editor, no sound. One at a time,
  seconds apart, both work, and so do separate processes. Likely cause: BASILISK SYNTH starts tar, qemu-img and QEMU
  with `bInheritHandles = TRUE`, so they inherit whatever inheritable handle the host holds at that moment. BASILISK 16
  writes its private copy of the DOSBox core with `fopen("wb")`, an inheritable handle. A child that inherited it
  holds the copy open for writing, and `LoadLibrary` then fails. Fix in either plugin: pass only the log handle
  (`PROC_THREAD_ATTRIBUTE_HANDLE_LIST`), or open the copy with `"wbN"`.
- **BASILISK SYNTH can hang on resume.** Once in about ten starts here, QEMU sat on `-incoming` and sent no audio.
  The plugin has no watchdog for that, so an offline render waits 30 s per block forever. The harness's
  `--render-timeout` now ends such a render and reports it.
- **BASILISK SYNTH program 1, "Tada Brass"** (`tada@20[]#16;A5S100R300`) builds a 15-frame layer: silent.
- **BASILISK 16 blocks in `process()` at start, even in real time** (4-7 s while Windows starts), which stalls a
  host's audio thread. The harness reports it as `max_block_late_ms`.
- **BASILISK SYNTH determinism**: the dense test pattern is not repeatable: notes start 0-500 ms late and the 16-per-
  second repeats are partly lost (see `results/`). The old `bsynth-host` gives the same picture on this PC.

Building
--------

    tools/basilisk-host/build.sh

It uses mingw-w64 (`x86_64-w64-mingw32-g++-posix`, GCC 14) from Linux or WSL, and links statically. It needs the VST3
SDK: `VST3SDK=...`, default `~/synth-build/vst3sdk`, otherwise it clones v3.8.1 from GitHub. Objects go in
`~/.cache/basilisk-host-build`.

| Path | What it is |
|---|---|
| `src/host.*` | loading modules, one instance: setup, process, queued events/parameters, MIDI mapping, programs, state, `.vstpreset`, `.bhstate`, automation lanes; child-process listing; WAV |
| `src/engine.*` | the live engine: instances, MIDI routing, sequencer, mixing, output tap |
| `src/audio.*` | WASAPI output and loopback capture |
| `src/midi.*` | Standard MIDI Files, the test pattern, winmm input |
| `src/analysis.*` | levels, onsets, FFT pitch, render comparison |
| `src/harness.cpp` | `--test` |
| `src/gui.cpp` | the Win32 GUI and `--selftest` |
| `src/main.cpp` | command line; `SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX)` so a DLL that fails to load is logged, never a modal box |

Built on `packages/basilisk-synth/tools/testhost/bsynth-host.cpp`. The VST3 SDK is MIT-licensed (Steinberg).

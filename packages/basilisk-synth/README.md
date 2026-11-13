BASILISK SYNTH - sixteen Windows XP Sound Recorders, as one instrument in your DAW
==================================================================================

A VST3 instrument for Windows and macOS, plus AU and CLAP on macOS. Every note you play is played by a real
`sndrec32.exe` inside a real Windows XP, through XP's own sound card. The plugin turns MIDI into instructions for
those Sound Recorders and passes on what XP plays. It never makes a sound of its own.

Open the editor and you watch the machine put itself together. Sixteen Sound Recorders sit on XP's desktop. Each
loses its menu bar, then its title bar. Its unused buttons drop off, then it glides into place as one strip of a
16-track tape machine: Play, Stop, Position, the green wave, Length and the slider. Task Manager's CPU and
page-file graphs and the Date and Time clock and calendar move in beside them.

Download
--------
https://github.com/williamsharkey/windows-secrets/releases/tag/basilisk-synth-v1.0.0

| File | Contents |
|---|---|
| `BASILISK-SYNTH-windows-x64.zip` (47 MB) | `BasiliskSynth.vst3`. Copy it to `C:\Program Files\Common Files\VST3`. |
| `BASILISK-SYNTH-macos.dmg` (95 MB) | `BasiliskSynth.vst3`, `.component` and `.clap`, universal (Apple Silicon and Intel). Copy them to `~/Library/Audio/Plug-Ins/VST3`, `Components` and `CLAP`. |
| `basilisk-synth-machine-1.tar.xz` | The XP machine. You don't download it yourself: the plugin fetches it once, on first use. |

- **First use:** the plugin downloads the machine (788 MB), checks its SHA-256 and unpacks it (930 MB). It uses the
  curl and tar that come with Windows 10/11 and macOS, and its editor shows the progress.
- **Where it lives:** `%LOCALAPPDATA%\BASILISK SYNTH` (Windows) or `~/Library/Application Support/BASILISK SYNTH`
  (macOS). Delete that folder to remove it.
- **Unsigned:** nothing is code-signed by Microsoft or Apple.
  - Windows: SmartScreen does not look at plugins, so there is nothing to click.
  - macOS: run `xattr -dr com.apple.quarantine ~/Library/Audio/Plug-Ins/*/BasiliskSynth.*` once, or your DAW will
    refuse to load it.

Playing it
----------
- MIDI notes, velocity, sustain pedal (CC64), pitch bend (applied when a note starts) and all-notes-off.
- **DAW parameters:** Gain, Attack, Decay, Sustain, Release, Velocity, Bend Range and Transpose. All are
  automatable.
- **Presets:** 12 factory presets, plus whatever the DAW saves. The whole sound is one DNA string kept in the plugin
  state, so DAW projects and preset files restore it exactly.
- **Inside XP (the editor):**
  - Effects and Edit menus that are Sound Recorder's own commands
  - Voices: transpose, harmony and unison
  - Layers
  - a sound list for picking each layer's source (35 of XP's sounds from `C:\WINDOWS\Media`)
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
- **Pitch:** XP's AC97 driver has no `waveOutSetPlaybackRate`; the call returns MMSYSERR_NOTSUPPORTED.
  - Instead, a small DLL injected into each Sound Recorder (`guest/srhook.c`) asks `waveOutOpen` for the file's rate
    times 2^(semitones/12).
  - XP's kernel mixer then resamples in hardware-driver fashion. No sample is touched by anyone but XP.
  - Measured: ±6 cents over five octaves. Rates from 2.7 kHz to 176 kHz were tested.
- **Note shaping:** each note's envelope and velocity are XP's per-stream `waveOutSetVolume`, ramped by the same
  DLL.
- **Voice allocation:** the voice allocator (`core/voices.cpp`) gives each note a free recorder from its layer's
  pool. If none is free, it takes the oldest, cutting it with a 5 ms fade.

Timing and tests
----------------
Measured through a real VST3 host (`tools/testhost`, `tools/run_tests.py`; results in `tools/test-results-*.json`):

|                                         | Windows 11 (QEMU 11.1)        | macOS, Apple silicon (QEMU 11.1) |
|-----------------------------------------|-------------------------------|----------------------------------|
| plugin load -> XP running               | 0.9 s                         | 0.12 s                           |
| plugin load -> ready for sound          | 1.2 s (guest answers on COM1) | 0.3 s                            |
| plugin load -> assembly finished        | 11.5 s                        | 11.3 s                           |
| reported latency                        | 370 ms                        | 200 ms                           |
| onset vs grid after compensation        | median +28 ms, std 82 ms      | median -42 ms, std 24 ms         |
| pitch error, 10 notes over 3 octaves    | max 5.2 cents                 | max 3.6 cents                    |
| clicks when 20 notes steal 2 recorders  | none                          | none                             |
| same DNA twice (envelope correlation)   | 0.986                         | 0.999                            |
| state saved -> reloaded (correlation)   | 0.992                         | 0.997                            |
| offline render, 15.1 s                  | 15.8 s, correct audio         | 15.2 s, correct audio            |
| two instances                           | both play, 2 QEMUs, 0 after   | both play, 2 QEMUs, 0 after      |
| sleep after 4 s, wake on a note         | yes                           | yes                              |
| QEMU killed mid-phrase                  | output silent from that moment| output silent from that moment   |
| pluginval, strictness 10                | SUCCESS (25 test groups)      | SUCCESS (25 test groups)         |

The last-but-one row is the proof that the sound is XP's: the plugin has no other source. Under the Linux QEMU 6.2
used to build the machine the same assembly takes 3.4 s and notes land within +-9 ms of each other (114 ms median);
QEMU 11 on Windows and macOS is slower at XP's window painting and much less regular in its audio timing. Inside XP,
Sound Recorder's own Play handling takes 30-300 ms before it opens the sound card (logged as `log open` lines).

The machine
-----------
- **One machine per instance:** each plugin instance runs its own QEMU as a hidden child process. It uses a
  throwaway overlay over the shared, read-only machine disk and its own sixteen recorders. Instances are independent
  and play at the same time.
- **Fast resume:** QEMU resumes from the shipped machine state (a migration stream, streamed in over loopback) in
  about a second, with XP already logged in and the sixteen recorders open.
- **When it goes away:**
  - Removing the instance ends QEMU at once.
  - On Windows, a job object kills QEMU even if the DAW crashes.
  - On macOS, a watchdog does the same.
- **Sleep:** XP never truly idles under emulation; its idle loop spins about 75% of a core per virtual CPU. So the
  machine is paused after 4 quiet seconds (no note sounding, editor closed) and wakes for the next note.
- **Hardware:** the virtual machine has 2 vCPUs, 512 MB, AC97 and no network to the outside (`restrict=on`).

What's inside
-------------
| Path | What it is |
|---|---|
| `plugin/` | The DPF plugin (https://github.com/DISTRHO/DPF, ISC licence, commit 4238e1c). `Machine.cpp` holds QEMU, the pipe, COM1 and VNC. `BasiliskSynthPlugin.cpp` holds MIDI and audio. `BasiliskSynthUI.cpp` shows XP's screen and passes on mouse and keys. |
| `core/` | DNA parsing, the voice allocator and the protocol. Shared with the 3.11 edition. |
| `guest/` | `synth.c` (the conductor in XP: animation, panels, COM1) and `srhook.c` (inside each Sound Recorder). Both are compiled in XP with tcc. |
| `tools/make_machine.py` | Builds the shipped machine from a prepared XP disk. |
| `tools/testhost/` | A small VST3 host used for the tests: render, offline, instances, state. |
| `tools/run_tests.py` | The end-to-end checks. |

Builds
------
- **Windows:** `make WINDOWS=true CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix` from Linux. Then put QEMU for Windows (Stefan Weil's build, as in packages/basilisk-xp), still zipped, at `BasiliskSynth.vst3/Contents/Resources/qemu-win64.zip`: the plugin unpacks it beside the machine on first use, so no QEMU `.dll` sits in a VST folder for hosts to probe.
- **macOS:** `make MACOS=true` with universal `-arch` flags. Then put the Homebrew QEMU builds from
  packages/basilisk-xp in `Contents/Resources/qemu-arm64` and `qemu-x86_64`, and ad-hoc sign.

Windows XP is Microsoft's; its sounds and Sound Recorder are Microsoft's. QEMU is GPL v2 (source: qemu.org).
DPF is ISC.

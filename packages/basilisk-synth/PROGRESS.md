# BASILISK SYNTH (XP lane): progress log

The instrument's sound is made inside Windows XP by 16 real `sndrec32.exe` processes, played through XP's AC97 card. The
plugin never synthesises notes (no reference mode is implemented yet; if one is added, it is for A/B listening only).

## Findings (measured)

### XP sound after a resume: works

The XP package lane saw XP's AC97 driver "hang after a snapshot resume". Here it does not, with any of the methods tried:

- **Linux QEMU 6.2, TCG:** cold boot with `-device AC97` plays. `savevm`/`loadvm` in the same process also plays, and so
  does a fresh process with `-loadvm`.
- **Windows QEMU 11.1** (the one the XP lane ships) loading the 6.2 snapshot: plays.
- **External migration stream** (what we ship): made by 6.2 and loaded by Windows QEMU 11.1 via `-incoming tcp:`
  (`file:` fails on Windows: "Failed to set FD nonblocking"). The stream loads in 0.33 s and sound plays afterwards.

Likely cause of the other lane's hang: host audio backends (dsound/coreaudio) or no card at snapshot time. We use the
`wav` audiodev, so the host's sound system is never touched.

### Audio transport: wav audiodev into a pipe

`-audiodev wav,path=<pipe>,out.frequency=44100,out.channels=2,out.format=s16` + `-device AC97`.

- **Windows:** the path is a named pipe the plugin creates (`\\.\pipe\bsynth-<pid>-<n>-audio`). Tested from Python:
  QEMU writes into it and data arrives.
- **macOS:** a FIFO (`mkfifo`). Not yet tested on the Mac.
- **Buffering:** QEMU's stdio buffers 4096 bytes, so audio arrives in 23 ms chunks.
- **Keepalive:** the wav backend writes only while XP plays. To fix both the gap problem and the "tail stuck in the
  stdio buffer" problem, `synth.exe` keeps a silent looping `waveOut` stream open forever. XP's mixer then never stops,
  the stream is continuous, and a note starts on a running card.
- **The plugin side:** reads the pipe on its own thread into a lock-free ring. It plays the ring back with a fixed
  jitter buffer (45 ms), 4-point Hermite resampling to the host rate, and slow drift correction.
- **Latency:** reports a fixed latency of 170 ms.

### Pitch inside real Sound Recorder

- `waveOutSetPlaybackRate` and `waveOutSetPitch` return `MMSYSERR_NOTSUPPORTED` (8) on XP's AC97 driver.
- `waveOutOpen` accepts any PCM rate because kmixer resamples. Per-handle `waveOutSetVolume` works.
- So `guest/srhook.dll` is injected into every `sndrec32.exe` by a `WH_GETMESSAGE` hook. It IAT-patches
  `winmm!waveOutOpen` to open at the note's rate.
- Measured with a 1 kHz sine file at 22050 Hz:

  | Rate requested (Hz) | Measured (Hz) | Expected (Hz) |
  |---|---|---|
  | 22050 | 1000 | 1000 |
  | 44100 | 2000 | 2000 |
  | 33075 | 1500 | 1500 |
  | 11025 | 500 | 500 |
  | 66150 | 3000 | 3000 |
  | 88200 | 4000 | 4000 |
  | 132300 | 6000 | 6000 |
  | 176400 | 7920 | 8000 |
  | 5512 | ≈250 | 250 |
  | 2756 | ≈125 | 125 |

- The same hook does the following:
  - per-voice volume and an ADSR envelope (per-handle volume, 5 ms steps; WRONG, see round 3: on this XP the
    Wave volume is one setting for the whole card, so this was measured one voice at a time only);
  - answers the Open/Save dialogs and message boxes, so DNA steps run Sound Recorder's real menu commands with no
    dialog ever shown;
  - runs the assembly animation inside each recorder.

### Note timing

- **Trigger to sound** (COM1 line → first audible sample in QEMU's capture): median 114 ms, std 8.8 ms, min 90,
  max 136, over 24 notes. This includes the 23 ms chunking.
- **Rebuilding a DNA** of two layers with three steps: about 1.2 s.

### CPU: XP never idles under TCG (found 2026-11-13)
XP's idle loop (KiIdleLoop -> PoIdle) returns without HLT here: every vCPU spins ~75-100% of a host core, on Linux and
Windows QEMU alike, whatever runs in the guest (all apps killed: same), with or without intelppm/Processor drivers, any
power scheme, 1 or 4 vCPUs. So: the machine is now 2 vCPUs (4 was not faster: assembly 3.6 s with 2 vs 4.5 s with 4 on
Linux), and the plugin pauses the VM (QMP stop) after 4 s with no sounding voice and no open editor; the next note
resumes it (QMP cont before the COM1 line, plus a `time` line). Idle CPU when paused: ~0.

### COM1 after a resume (found 2026-11-13)
After any snapshot/migration resume XP's serial.sys has lost the 16550's interrupts: guest->host bytes go out only when
a host->guest byte arrives, and the last received bytes wait for the next arrival. Fixes: XP's UART FIFO is off
(prep.bat: Serial\Parameters ForceFifoEnable=0), the host ends every write with an extra "\n" (an ignored empty
line), and while awake the host sends "\n" every 15 ms, which carries XP's pending output out. Stale replies queued
before the snapshot ("hi 1 xp wait", the boot build's "layer"/"built") arrive first and are harmless.

### Windows QEMU timing
Windows QEMU 11.1 (Stefan Weil build): trigger->sound median ~170 ms, std ~60 ms (Linux QEMU 6.2: 114 / 9). Values come
in 23 ms steps (stdio 4096-byte chunks). timer-period=2000 did not help. Reported latency set to 280 ms on Windows.
In the plugin (scale test, ding#16): pitch within 6 cents on all 10 notes; onset error vs reported latency median
+116 ms with ~250 ms spread before the latency constant was raised.

## Done

- `DNA.md`: format and protocol. The shared core is in `core/`, written by the 3.11 lane. It is used by this plugin.
- **`guest/`** (tcc in XP): `synth.exe`, `srhook.dll`, `synthshm.h` and `mm.h`.
  - 16 recorders tiled.
  - Date and Time and Task Manager (Performance tab) as donors.
  - Assembly on `go`, about 4.5 s with 4 vCPUs: menu goes, frame goes, `<< >> ●` drop off, each recorder glides into
    a strip.
  - Then the Task Manager CPU/PF graphs and the Date&Time page move in through "ports". Finally the DNA, Layers and
    Sounds panels appear.
  - Menus inside XP edit the DNA and send `edit` lines: Effects, Edit, Voices, Layers, Mutate, Undo.
- **`tools/make_machine.py`:** cold-boots the prepared disk with the plugin's exact devices, waits for
  `hi 1 xp wait`, then writes `state.mig` and `base.qcow2` and `fw/` into a `tar.xz`. It also writes
  `plugin/machine_info.h`.
  - Machine 1 built at `~/synth-build/machine-out`: 787,834,360 bytes, sha256 `c56f8ea5…4a55`.
  - Resumes with 16 recorders tiled.
- **`plugin/`** (DPF, ISC): `BasiliskSynthPlugin.cpp`, `BasiliskSynthUI.cpp`, `Machine.{hpp,cpp}`.
  - One QEMU per instance, on a throwaway overlay, killed by a job object (Windows) or a watchdog (macOS).
  - First-run fetch with curl/tar plus SHA-256.
  - VNC screen and input.
  - COM1 link.
  - The Windows VST3 builds with mingw (`~/synth-build/plugsync.sh`).
- **`tools/testhost/bsynth-host.cpp`:** a VST3 test host covering render, offline, instances and state. It builds with
  mingw (`~/synth-build/hostbuild`).

- pluginval strictness 10 on Windows: SUCCESS (25 test groups), no QEMU left afterwards (VC runtime DLLs copied
  app-locally next to pluginval.exe from EdgeCore, since the VC redist is not installed on this PC).
- First-run fetch tested on Windows with a file:// URL: fetch 2 s, sha256 2.4 s, unpack 6 s, then resume 0.8 s.
- macOS universal (arm64+x86_64) VST3/AU/CLAP build on primary-mac (~/bsynth), both QEMUs in Resources
  (qemu-arm64, qemu-x86_64), ad-hoc signed; test host built there too (~/bsynth/bsynth-host).

## Released 2026-11-13: basilisk-synth-v1.0.0
Windows zip (47 MB), macOS dmg (95 MB, universal VST3/AU/CLAP), machine-1 tar.xz (788 MB). Tests: README "Timing and
tests" and tools/test-results-{win,mac}.json; pluginval strictness 10 SUCCESS on both.

## Round 2 (v1.1.0) plan, 2026-11-13
No native/reference sound mode, ever (user). Targets: assembly <= 6 s on shipped Win/mac QEMU 11; latency and jitter
down (fast play path inside each sndrec32: a primed waveOut triggered by an event, Sound Recorder's own saved buffer as
the source, its UI driven by seeks); XP's idle loop halting (patch the running kernel's PoIdle before saving the state,
via the gdbstub); real-DAW tests in a separate portable REAPER (Windows: never touch the user's REAPER at
C:\Users\willi\BASILISK-plugins\REAPER, pid 8168); auval via a GUI-session launchctl asuser; no partial frames
(strips reshape in place, then glide as a whole with copied bits); ad-hoc signing stated plainly.

## Round 2 findings
- Idle: XP's PoIdle finds no idle handler and returns; KiIdleLoop spins. Patching PoIdle to "sti; hlt; ret" (in RAM,
  via the gdbstub, before the state is saved) takes idle from ~97% to ~8% of a core per vCPU. With 2 vCPUs the
  scheduler then wakes halted CPUs only on the next tick (it expects them to poll), so assembly got slower (6.6 s);
  with 1 vCPU there is no cross-CPU wake and the assembly is the fastest yet (3.0 s on Linux QEMU 6.2). -> 1 vCPU.
- Fast play path in srhook: an event per recorder wakes a TIME_CRITICAL thread that plays the recorder's own saved
  file on a card handle kept open (reopened only when the rate changes); the strip's Play button, slider, position and
  wave follow via TB_THUMBTRACK seeks. Linux: trigger -> sound 90 ms median (was 114), the rest in 20 ms steps = QEMU's
  4 KB wav buffer at 44.1 kHz s16 -> now 96 kHz s32 (5 ms per buffer) and a 25 ms jitter buffer.
- Choreography: a quick wave of menu/frame/button changes, then one strip at a time reshapes in place and glides whole
  (pure moves carry painted pixels; only one mover at a time). WS_EX_COMPOSITED broke Sound Recorder's statics: not used.
- Guest COM writer: a synchronous COM handle serializes reads and writes, so an endless write blocked reads (deadlock
  in make_machine); writes now time out at 40 ms and continue.

## Round 3 (v1.2.0) status (2026-11-13)
Done and measured in the real machine (machine-3):
- DNA v2 spec (DNA.md 5) + shared core (cd9bef9, d61652f). Keyboard wire lines as agreed with the 3.11 lane
  (`key`, `cc`, `bend` guest->host; `show`, `cc 1`, `bend` host->guest; CC1 adds to Macro 1). `vis 0|1`, `lib` added.
- Plugin: Macro 1-4 params; offsets held host-side; pan in `on`; `lenv`; effective DNA to the guest; 38 programs
  "Category: Name" (factory.tsv incl. a Library category); library names compiled in (presets_gen.h); the library
  disc inserted into XP's CD drive after resume (QMP blockdev-change-medium on `cdrom0`); XP keyboard/wheels through
  the voice allocator; "show" lines for DAW notes; visible builds only while an editor is open.
- Guest: v2 tokens (O Q Ja Jp @t, library names with `_`), pan, level and envelopes applied to the samples inside
  each Sound Recorder (see the streaming note below), drawn envelopes per layer from `lenv`, visible construction (each step picked from the
  recorder's own File/Edit/Effects menu popping up on its strip), library + preset browser (category combo +
  list), envelope editor of real trackbars + Task-Manager-style graph, Macros panel (4 Volume Control sliders,
  Tone/Body/Time/Motion), keyboard strip (37 BUTTON keys, BM_SETSTATE for held notes, mouse with glide, Hold,
  PC keys a w s e d f t g y h u j k / z x / c v), bend + mod trackbars; rows 41 -> 34 px, clock-only Time port.
- Machine 3: IDE CD-ROM (empty in the state), autorun off, library.iso shipped inside the plugin (510 sounds, 7 categories, 114 MB of audio).
- tools/make_library.py (ISO 9660 + Joliet), tools/make_presets.py, tools/batch_render.py (parallel VMs).
- bsynth-host gained --set NAME@T=V (automation, `program`), --ui T:click|down|up|move|key|keyup (posted to the
  editor window), --state-roundtrip, --timing. REAPER is not used any more (owner instruction); its folders removed
  (C:\Users\willi\bsynth-reaper is an empty folder Linux cannot remove: permission denied).
- Measured (Windows unless noted): XP keyboard through the editor: PC key 'a' -> peak 0.187, mouse on C4 -> 0.24,
  silent before and after; state round trip identical (259 bytes); macro level ratio 0.10 (Win and mac); library
  kalimba_c4 at 262.6-264.1 Hz (C4 261.6); assembly in the dev VM 2.6-3.5 s.
- **waveOutSetVolume is card-wide on this XP** (found by the PE2 lane: two handles, the second one's L/R setting
  moved the first one; it persists after the process exits). v1.0-1.1's per-voice velocity and ADSR and my first
  v1.2 pan were all that one volume, last writer wins. Fixed: srhook's fast path now streams the recorder's own
  saved PCM to its handle in 4 x 20 ms chunks (stereo 16-bit at the note's rate) and applies velocity, level,
  pan, ADSR / drawn envelope and release to the samples; the envelope clock is the source position (exact).
  Pitch is now done in the guest too: each recorder's handle is opened once at 48 kHz stereo when its sound
  loads and never reopened; a note's pitch is a 4-point Hermite step through the source (measured in the dev VM:
  note open 0-16 ms, was 16-400 ms with a reopen per new pitch; intervals -12..+19 st within ~5-10 cents of each
  other on an organ pipe, FFT over 370 ms).   Steals fade the queued audio in place from 3 ms past the play position (4 ms) before the reset. synth.exe sets
  the card volume to full once at startup; nothing calls waveOutSetVolume any more.
  Measured PER VOICE in the dev VM (two simultaneous voices, raw XP output): voice A hard left from 0 s, voice B
  hard right from 0.5 s: left channel = A only (12967..18642 while held, 0 after its release), right = B only
  (0 until 0.5 s); a 3-voice chord with one voice released at 1 s: total drops ~30000 -> ~20000 and the other two
  hold until their own release.
- Built-in machine (owner decision): Contents/Resources/machine in the Windows VST3 and the macOS VST3 (AU/CLAP
  use the VST3's). The downloader and SHA code are gone; logs and the unpacked QEMU live in %LOCALAPPDATA% /
  ~/Library/Caches. base.qcow2 has zstd clusters; zero-filling 3 GB of free space and trimming dllcache, driver
  cabs and the page file left it at 704 MB (no measurable gain: the image was already lean).
  Sizes: Windows zip 952 MB, macOS dmg 932 MB (ULMO). Load -> XP linked: Windows 1.9 s (first ever +3.5 s QEMU
  unpack), macOS 0.3 s; -> a new sound built: 4.3 s / 0.8 s.
- Robustness: offline render waits for the machine at most 60 s and for each build (program changes too) at
  most 15 s, paced within 20 ms of the clock; watchdog restarts a silent machine (x3); QEMU inherits only its log
  handle (PROC_THREAD_ATTRIBUTE_HANDLE_LIST); stale bsynth-<pid>-* temp folders of dead hosts removed at start.
- Library table cap: MAXSND 512 silently dropped 33 of 510 disc names (tonal ones, incl. kalimba_c4); now 2048.
- BasiliskHost harness, Windows (v1.1 -> v1.2): offline heard 34/50 -> 50/50, live 22/50 -> 50/50, onset median
  117 -> 12 ms (std 168 -> 37-52), pitch mean 11.7 / max 150 -> 11 / 16-19 cents, repeat envelope corr 0.29-0.36
  -> 0.77-0.88 (not bit-identical), state bytes identical (sound 0.70-0.74), no orphans, no render timeouts;
  live program change still drops the notes in the ~1.5 s rebuild (3-6 notes).
- Not done: bit-identical renders (XP is not sample-accurate); Windows pitch ~10 cents mean (the playout drift
  trim modulates speed under load); the layer table from ui-layouts.md (the Layers list stays); .vstpreset files.

## Round 2 status (2026-11-13, before -> after)
- Assembly, plugin load -> ready: Windows 11.5 s -> 5.6-6.1 s; macOS 11.3 s -> 4.4-4.5 s (1 vCPU, idle patch,
  single-threaded TCG tb-size 1024, sequential reshape+glide, "go" sent with the first COM1 lines, VNC <= 30 fps).
- Latency / spread (middle notes of a scale): Windows 370 ms / std 82 -> ~100 ms reported, spread ~+-25 ms;
  macOS 200 ms / std 24 -> 100 ms, spread ~+-8 ms. Path: event -> srhook note thread -> primed waveOut (open
  0-16 ms) -> AC97 -> QEMU wav at 96 kHz (192 kHz is silently capped at 96) -> 50/40 ms playout buffer.
- CPU of the emulator: idle awake Windows ~200% -> ~50%, macOS ~190% -> ~20%; playing ~1 core; asleep ~2-5%.
- Determinism (envelope corr): Windows 0.986 -> 0.982-0.992 (run to run), macOS 0.999 -> 0.995-0.996.
- pluginval strictness 10 SUCCESS on both; auval PASS via a GUI-session LaunchAgent (tools: ~/bsynth/guirun.sh).
- REAPER: Windows test aborted after my first launch ran inside the user's REAPER and quit it (REAPER forwards to a
  running instance unless -newinst; "start reaper.exe" may also resolve via App Paths to the user's install).
  Portable REAPER (own folder, full path, -newinst) then never scanned plugins; macOS portable REAPER never ran its
  startup script (probably a first-run dialog; a LaunchAgent cannot screenshot). Not achieved.
- Partial frames: much reduced (one mover at a time, pure moves), final state snapped and clean; mid-assembly frames
  under a CPU-bound guest still show strips being reshaped or not yet repainted on Windows.
- Bug found by the two-instance test: both instances drew the same VNC port (per-thread rand); fixed with ephemeral
  ports.

## Open (v1.0.0)
- Assembly takes ~11 s under QEMU 11 (Windows, macOS) vs 3.4 s under Linux QEMU 6.2; sound is ready after 0.3-1.2 s.
- Timing jitter on Windows (std ~80-95 ms); most of it is Sound Recorder's own Play path (30-300 ms before
  waveOutOpen) plus QEMU 11's audio timing. Ideas: keep each recorder's card open between notes of the same rate.
- auval could not be run over ssh (component not registered in that session); AU untested in a real host.
- XP never idles under TCG (~75%/vCPU); mitigated by sleeping after 4 s.
- No native "reference" mode.

## Paths

| What | Where |
|---|---|
| Dev VM with agent | `~/synth-build/vm/dev-agent.qcow2` |
| Shipped-prep disk | `~/synth-build/vm/dev.qcow2` |
| Helpers | `~/synth-build/vm.sh` (`SMP=4,sockets=1,cores=4`), `xr` (agent command), `com.py` (COM1 bridge), `shots.py`, `sheet.py`, `lat.py`, `capseg.py` |
| Agent server | `~/synth-build/agentsrv.py` (127.0.0.1:8765/8799) |
| Toolchains | DPF at `~/synth-build/dpf` (4238e1c); vst3sdk at `~/synth-build/vst3sdk`; LLVM and xwin in `~/synth-build` (unused so far) |

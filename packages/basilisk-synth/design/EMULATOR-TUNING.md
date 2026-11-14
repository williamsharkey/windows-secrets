# EMULATOR-TUNING: smoother XP screen and sound (2026-11-14)

What makes BASILISK SYNTH's emulated Windows XP look and sound smooth, measured rather than guessed. The machine is
the 1.2.2 hotfix machine (`machine-out-hf`: 1 vCPU, idle patch in the saved state, AC97 on the wav pipe). The bench
resumes the saved state with only stock QEMU options and drives the guest over COM1 exactly as the plugin does
(`hi 2`, then `go`, then `show` lines).

Tools: `tools/emubench/` — `bench.py` (one run, JSON line), `dbusdisplay.py` + `dbuswire.py` (a QEMU D-Bus display
listener), `matrix_mac.sh`, `audio_mac.sh` (the 1.2.2 tone gate through the real plugin per accel setting),
`matrix_win.bat`.

Metrics:
- **assembly**: `go` -> `ready`, the editor's build animation.
- **fps / still**: screen updates the client receives during the assembly; *still* = gaps between updates (max, p95).
- **react**: from a guest-visible change (`show <note> 100` on the keyboard strip) after 1.5 s of quiet to the first
  update the client receives. This is what "the editor feels laggy/jerky" is made of.
- **cpu**: QEMU process CPU (cores) while assembling and while idle-awake.
- **audio**: exact-silence gaps >= 5 ms in the plugin output and in XP's own stream (plugin counter), 60 s chord.

## 1. Results

### macOS, Apple M5 Max, shipped QEMU 11.1 (TCG), 3 runs each (2 for the display rows), medians

| Configuration | assembly | fps | still max / p95 | react median / max | asm cpu | idle cpu | audio gaps (out / XP stream) |
|---|---|---|---|---|---|---|---|
| **shipped**: tcg single tb 1024, VNC request every 33 ms after each reply | 3.90 s | 23.0 | 113 / 111 ms | 66 / 157 ms | 0.82 | 0.48 | 0 / 0 (2 takes) |
| tb-size 256 | 3.97 s | 23.7 | 112 / 111 ms | – | 0.78 | 0.51 | 0 / 0 |
| tb-size 4096 | 3.96 s | 23.2 | 113 / 111 ms | – | 0.79 | 0.50 | 0 / 0 |
| thread=multi (1 vCPU) | 3.96 s | 24.0 | 112 / 111 ms | – | 0.77 | 0.41 | 0 / 0 |
| `-icount shift=auto,sleep=on` | **never finishes** | – | – | – | – | 0.55 | – |
| no display client at all | 3.93 s | – | – | – | 0.83 | 0.42 | – |
| VNC **eager** (a request always outstanding) | 4.06 s | **31.5** | 111 / **31 ms** | 72 / 237 ms | 0.81 | 0.50 | – |
| **D-Bus display listener** (`-display dbus,p2p=yes`, console 0) | 3.96 s | 126 Update calls/s (several rects per frame) | **72 / 31 ms** | **13 / 32 ms** | 0.76 | 0.52 | – |

Notes:
- TCG knobs (tb-size, thread mode) are noise-level for this workload: the guest is GDI/UI bound, and the
  translation cache is already warm in the saved state. icount breaks the assembly (timers starve) — never use it.
- A display client does not slow the assembly (no-client run is the same 3.9 s).
- Audio: with the 1.2.2 srhook fix every TCG variant gave 0 output gaps and 0 gaps in XP's own stream on the Mac;
  playout buffer stayed 30–59 ms. Audio no longer separates the TCG settings.
- Background load during the Mac runs: two Android emulators (another project) were running; numbers are
  consistent across repeats, so they are usable as relative comparisons.

### Why the shipped VNC path stutters

The plugin's VNC loop sends one incremental request, waits for the reply, sleeps until 33 ms have passed, sends the
next. QEMU's VNC server only answers on its own refresh timer (30 ms base), and **backs that timer off by 50 ms per
idle tick up to 3 s** whenever nothing changed. Two effects follow:
1. During steady animation the request and the 30 ms tick beat against each other: every few frames a request
   arrives just after a tick and waits for the next, so the p95 gap is ~111 ms (3 ticks) though the guest drew every
   tick. Keeping a request always outstanding ("eager") removes this: p95 31 ms, 31.5 fps.
2. After any quiet stretch (between notes, between preset changes) the timer has backed off, so the first change is
   seen up to hundreds of ms late (react max 157–237 ms in both VNC modes). Eager requests cannot fix this — the
   backoff is inside QEMU. The site lane's "still runs of up to 0.37 s" are this.

The **D-Bus display** has no backoff: QEMU's console refresh runs at the 30 ms GUI interval and pushes each dirty
rectangle as an Update call (or, with the `Listener.Unix.Map` / `Win32.Map` interface, into shared memory). React
median 13 ms, max 32 ms; p95 still 31 ms. The plugin already opens a p2p D-Bus connection for recording input
(RECORDING.md X0), so the display rides on the same connection.

### Accelerators

| Accelerator | Status here | Snapshot (our fast start) | Verdict |
|---|---|---|---|
| TCG (shipped) | works everywhere | yes, portable (6.2-made state loads in 11.1) | keep |
| **WHPX** (Windows) | present on this PC (Ryzen 7 7840U, Win 11 25H2, HypervisorPresent=True, coexists with WSL2); only in Weil's `qemu-system-x86_64.exe`, **not** in the `-i386` binary we ship | **blocked**: `savevm` -> "State blocked due to missing dirty memory tracking support, And some system register/state save-restore" | ruled out for the shipped path: every start would be a cold boot + assembly, and a snapshot made under TCG cannot be loaded under another accelerator |
| HVF (Intel Mac) | not testable (no Intel Mac; Apple Silicon cannot run x86 under HVF) | QEMU's x86 HVF also lacks migration support in practice | ruled out |
| KVM (Linux) | works (WSL2 has /dev/kvm; sharkey has it) | only for KVM-made snapshots (PROGRESS: TCG state crashes under KVM) | BASILISK SYNTH ships no Linux build; not relevant now |

A cold-boot benchmark of WHPX vs TCG was not possible with the shipped disk: the disk alone does not start the
synth (the saved state does), and a cold boot of `base.qcow2` produced only 3 screen updates in 240 s on the Mac (it
stops early in boot, likely at a recovery/boot menu). Measuring WHPX would need a separate machine-build flow.

### QEMU versions

| Version | Result |
|---|---|
| 6.2 (Linux, WSL) | assembly 3.0–3.4 s (PROGRESS.md) |
| 8.2.2 (Ubuntu, sharkey) | resumes and answers `hi` in 1.5–2.4 s, but the assembly **never reports `ready`** (90 s timeout, 2/2 runs) and QEMU spins at 1.1 cores. Not investigated further; avoid 8.2 for this machine |
| 11.1 (shipped, macOS) | 3.9 s |
| 11.1 (shipped, Windows) | 5.6–6.1 s (1.2 release measurements); see Windows section |

## 2. Other emulators

| Emulator | Verdict | Why |
|---|---|---|
| 86Box / PCem | out | cycle-accurate, so XP needs a fast host just to run in real time; **no save states**, so no fast start; no headless library mode to embed |
| Bochs | out | interpreter, several times slower than QEMU TCG for XP; save/restore exists but the speed rules it out for 16 recorders |
| VirtualBox | out | needs its kernel driver installed system-wide (admin, not embeddable in a plugin bundle); on Windows with Hyper-V/WSL2 active it falls back to the slow NEM path; no x86 on Apple Silicon; GPLv3 7.x |
| VMware Workstation/Fusion | out | proprietary, not embeddable |
| UTM | = QEMU (same engine) | – |
| Box86/Box64, Rosetta | out | user-mode only, cannot run an OS |

On Apple Silicon there is no alternative to QEMU TCG for an x86 guest. On Windows the only faster engine (WHPX)
cannot snapshot. So the gains are in how we drive QEMU, not in replacing it.

## 3. Recommendations

| OS | Configuration | Expected gain |
|---|---|---|
| **All** | **Read the screen from QEMU's D-Bus display** (console 0 listener on the existing p2p connection; Unix.Map shared memory on macOS, Win32.Map on Windows) instead of VNC. Keep VNC only as a fallback. | react 66/157 ms -> 13/32 ms (median/max); steady 30 ms cadence; no 3 s backoff stalls; no 3 MB socket copies on QEMU's main thread |
| All (cheap interim, if D-Bus display slips) | VNC eager: send the next incremental request immediately after each reply (drop the 33 ms sleep-after-reply) | p95 still 111 -> 31 ms, 23 -> 31.5 fps during animation; does not fix post-idle lag |
| Windows (AMD/Intel) | Keep TCG `thread=single,tb-size=1024`, i386 binary, saved state. Keep the power-throttling opt-out and ABOVE_NORMAL priority (1.2.2). Do **not** ship WHPX. | – |
| macOS Apple Silicon | Same TCG settings (tb-size/thread changes measured as noise). | – |
| macOS Intel | Same as Apple Silicon (HVF cannot snapshot); runs under the x86_64 QEMU in the bundle. | – |
| All | Never use `-icount`; stay on QEMU 11.1 (8.2.2 fails the assembly). | – |

## 4. Risks

- D-Bus display on Windows needs the Win32 socket handover (`get-win32-socket`, AUTH ANONYMOUS) the X0 audio work
  already proved, plus the `Win32.Map` shared-memory interface; measure on Windows before switching.
- The D-Bus listener receives updates on QEMU's console refresh (30 ms); if QEMU's refresh is ever throttled when no
  listener is "visible", a periodic `RegisterListener` keep-alive or `SetUIInfo` may be needed.
- Update-call cost without shared memory is a full rect copy per call (126 calls/s here): use the Map interfaces.
- The cold-boot WHPX question stays open; only worth revisiting if a non-snapshot start became acceptable.

## 5. Migration steps for the XP lane (batched release)

1. In `Machine.cpp`, after the D-Bus p2p connection is up (already done for DBusIn), call `RegisterListener` on
   `/org/qemu/Display1/Console_0` with a second socketpair; answer `Properties.Get(Interfaces)` with
   `["org.qemu.Display1.Listener.Unix.Map"]` (macOS) / `["org.qemu.Display1.Listener.Win32.Map"]` (Windows).
2. Handle `ScanoutMap`/`UpdateMap` (blit the dirty rect from the mapped buffer into `fb_`) and the plain
   `Scanout`/`Update` fallback; cursor calls can be ignored (XP draws its own pointer in the framebuffer with
   usb-tablet).
3. Keep input on VNC or move it to the D-Bus `Keyboard`/`Mouse` interfaces (optional).
4. Until then: change the VNC loop to always keep one request outstanding (remove the post-reply 33 ms sleep).
5. Verify with `tools/emubench/bench.py --vnc-mode dbus` and the site lane's `xp_check.py` capture (unique frames/s,
   longest still run), plus the react metric; target react max <= 40 ms, p95 still <= 35 ms.

## 6. Windows measurements (Ryzen 7 7840U, Windows 11 25H2, exclusive window 2026-11-14 00:2x)

Shipped QEMU 11.1 (`qemu-system-i386.exe`, TCG) resuming the hotfix machine; WHPX/TCG cold boots with Weil's full
11.1 `qemu-system-x86_64.exe`. Two of four resume runs never received `ready` within 90 s (the guest answered `hi`;
likely the serial-reply quirk under host timing, not the display mode) — the completed runs:

| Configuration | load | assembly | fps | still max / p95 | react (6 probes) | asm cpu | idle cpu |
|---|---|---|---|---|---|---|---|
| shipped VNC loop | 0.78 s | 4.98 s | 25.7 | 131 / 111 ms | 134, 213, 38, 5, 209, 38 ms | 1.06 | 0.47 |
| VNC eager | 0.82 s | 4.39 s | 27.3 | 270 / 71 ms | 221, 49, 50, 183, 122, 110 ms | 1.08 | 0.48 |

| Cold boot of `base.qcow2` to a settled screen (8 s without updates) | time | cpu |
|---|---|---|
| TCG (x86_64 binary) | 37 s (first run 28 s) | 1.1 |
| **WHPX** | **53 s** (first run 20 s; run-to-run spread large) | 1.1 |

- WHPX is **not** faster for this guest: XP's UI traffic is MMIO-heavy (cirrus VGA, IDE), and every MMIO access is a
  hypervisor exit under WHPX; combined with the snapshot block, WHPX stays ruled out.
- Windows shows the same VNC pattern as the Mac: p95 still 111 ms with the shipped loop, and post-idle react up to
  ~220 ms in both VNC modes (QEMU's refresh backoff). The D-Bus display (no backoff) is the fix; the Mac shows react
  median 13 ms / max 32 ms with it.
- The intermittent missing `ready` (2/4) under the bench's 15 ms newline pinger should be re-checked with the
  plugin's own link before reading anything into it; the plugin has its own retry/watchdog.

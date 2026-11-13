# BASILISK 16: status

v1.1.0 is released (basilisk-synth-311-v1.1.0, commit 948ce56). There is still no plugin-made sound, by design.

## Round 2

| # | Item | Status |
|---|---|---|
| 2 | Presets in hosts | DONE in patched DPF (`plugin/dpf.patch`); AU factory presets verified with auval |
| 1 | A reloaded project must render like the original | DONE (4/5 bit-identical) |
| 3 | Seamless preset change | DONE (rolling in-place rebuild) |
| 4 | Assembly | DONE |
| 5 | Mac zip drive | DONE (DOSBox Pure UB fixed) |
| 6 | Typing into Windows | DONE |
| 7 | CPU | DONE |
| 8 | Signing | DONE: no identity; macOS ad-hoc, Windows unsigned, stated on the page and in the README |
| 9 | Harmony button | DONE |

**2. Presets in hosts.** The patched DPF VST3 wrapper:
- exposes IUnitInfo with a "Factory" program list, so REAPER lists 16 presets, `SetPresetByIndex` works, and the
  preset name shows in the FX window;
- lists only MIDI CC 64/120/123/129 × 16 channels as hidden parameters: 77 parameters instead of 2093.

AU factory presets are DPF's own. Mac AU verification is TODO.

**1. Reload.**
- Suspected cause: while the plugin blocks, either waiting for a rebuild or at start, the engine free-runs on its
  own clock. The first notes stamped afterwards then land in the past ("late").
- Fix: after any wait, and whenever the engine is ahead by more than `lead` + one frame, set `dacPos_` to
  `dac_w - lead`.

**3. Seamless preset change.**
- Plan:
  - 16 more SOUNDREC instances as spares;
  - rebuild into the spares while the old set keeps playing, then swap the sets;
  - the plugin keeps its old voices and layer info until `built`;
  - waits only when the host renders offline. VST3 `process_mode` needs a DPF patch; AU has OfflineRender.

**4. Assembly.** Two fixes: the first recorder overlaps the title, and the clock passes behind the recorders.
Then recheck dense frames, staying ≤ 6 s.

**5. Mac zip drive.** Debug the crash of the x86_64 Mac build on the zip drive, or justify the folder.

**6. Typing into Windows.** Test keys through the editor (engine keyboard callback) and fix.

**7. CPU.** Measure before and after. Ideas: dynamic core, fewer cycles when idle, no SB16, skip video copies.

**8. Signing.** No identity is available: ad-hoc on macOS, unsigned on Windows. Say so plainly.

**9. Harmony button.** It does not follow the DNA (panel_refresh).

## REAPER testing

- An isolated copy runs at `C:\Users\willi\bs311r2`: `reaper\`, `cfg\reaper.ini` via `-cfgfile`, `vst\`.
- `run_reaper.ps1` uses `-newinst`.
- `clicker.ps1` answers only our own REAPER's dialogs, by pid.
- `shotwin.ps1` captures with PrintWindow, by pid.
- The user's REAPER (pid 8168, `C:\Users\willi\BASILISK-plugins\REAPER`) and `AppData\Roaming\REAPER` are never touched.

## Round 2 results so far

**1. Reload.**
- Cause: the host-to-DAC mapping carried an arbitrary fractional phase at 44.1 kHz. On top of that, the engine
  free-ran on its own clock while another instance blocked the render.
- Fix:
  - an integer anchor, reset at transport start;
  - phase-preserving integer jumps;
  - offline: the engine is paced strictly by host_r plus a grant while the plugin waits.
- Result: reloads r1, r2 and r4 are bit-identical to the original. r3 differs by 0.007 for 3 ms (one run of 5).

**3. Seamless preset change.**
- A spare bank of 16 recorders was tried: Windows 3.11 GDI resources drop to 4% free with 32 SOUNDRECs. Rejected.
- Instead, the build runs in place, one recorder at a time, serving notes between recorders.
- A note on a recorder that is already rebuilt is rate-corrected to the host's old layer rate.
- The plugin keeps the old allocator until `built`. It waits only offline (DPF patch: `isProcessingOffline`, VST3
  process_mode and AU OfflineRender).
- Guest-level test: all 30 notes on time across a 0.45 s rebuild.
- REAPER realtime test (Dummy Audio): 28 of 28 notes sound across a preset change at 3.15 s, 0 late.

**9. Harmony button.** It now follows the DNA's H gene.

**Test-rig notes.**
- REAPER Dummy Audio is `[audioconfig] mode=4`. Set `promptendrec=0`.
- Record through a send to a second, armed track with `RECORD_PATH` set to the project directory. Otherwise
  recordings went to `Documents\REAPER Media`, which has been cleaned.

**1. Reload (final).**
- Five reloads were bit-identical to the original in REAPER.
- Plugalyzer renders were also identical twice.
- Further fixes:
  - offline waits for the assembly too;
  - events go straight to the card (no wait for an emulated frame);
  - the engine is paced by the host's heartbeat, not by its consumption;
  - latency = max(2560, block + 2 frames + 1024) samples at 48 kHz;
  - the frame-skip trick was dropped: it made DOSBox Pure emulate 10 frames per call.

**4. Assembly.**
- The title is drawn only after recorder 1 has left it.
- The clock flies HWND_TOPMOST, so it stays above the recorders.
- Timing is tighter: ready in 5.24 s, plus a 0.07 s resume.

**5. Mac zip drive.**
- Cause: in DBP_Mount, IMGMOUNT -t zip sets `ext = "ZIP"` (a literal); the drive-label code then subtracts it from
  a pointer into the path. That is undefined behaviour, and it crashed the x86_64 macOS build.
- Patched in `dosbox-pure.patch`. Both Mac arches now use drive.zip, built deterministically: the same md5 on Linux
  and on the Mac.

**6. Typing into Windows.**
- The core releases keys that `input_state(KEYBOARD)` doesn't report as held, so the engine now tracks held keys.
- The UI maps shifted characters to their base key.
- The DNA line is editable: Enter applies, Esc reverts.
- Verified in REAPER: messages posted to our own plugin window typed a DNA into Windows, and the plugin state took
  it (saved .rpp).

**7. CPU** (engine process, % of one core; this PC):

| Case | Before | After |
|---|---|---|
| Idle, editor closed | 55 | 13 |
| Idle, editor open | 55 | 18 |
| Playing a note every 100 ms | 63 | 33–38 |

How:
- the card's IDLE command ends the CPU slice, like HLT, when SYNTH.EXE has nothing to do;
- no video copy without an editor.

# BASILISK 16: status

- v1.2.0 is the release (basilisk-synth-311-v1.2.0). Round 3 is done; its record is below.
- v1.1.0 was basilisk-synth-311-v1.1.0, commit 948ce56.
- There is still no plugin-made sound, by design: every sound comes from the sixteen SOUNDREC.EXE in Windows 3.11.

## Round 3 (v1.2.0): DNA v2, library disc, keyboard strip, batch CLI

| Item | Status |
|---|---|
| DNA v2 (DNA.md §5): layers with offset `O`, pan `Q`, drawn envelopes `Ja`/`Jp`, `@t`, 4 macros, library NAMEs | DONE in guest, card, plugin, render311 |
| Library disc: drive L: (`library.zip`, `LIBRARY.TSV`, `PRESETS.TSV`) | DONE: 249 sounds in 6 categories, from basilisk-synth/library/sources |
| Programs: 71 ("Category: Name"), the same list as the browser in Windows | DONE (`presets/b16.tsv` + the shared presets; tools/make_presets311.py) |
| CHORD.WAV and TADA.WAV from Windows 3.1 in C:\WINDOWS (`chord`, `tada` play their own files) | DONE (machine-extra/) |
| Controls in Windows: preset browser with ◄ ►, every-sound picker, pan, offset, envelope points (◄ ► + −, time, level), 4 macros | DONE, mouse-tested in the emulator |
| Envelope display: a 17th Sound Recorder's wave view draws the selected layer's envelope | DONE (one sample per pixel: 129-sample buzz) |
| Sound construction visible: the recorder's own status field names each operation; its row number lights yellow | DONE |
| Keyboard strip (DNA.md §5.4): 5 octaves of 3.11 push buttons and black-rect statics, Bend and Mod scrollbars, Hold, Keys (a w s e d f t g y h u j k, z/x) | DONE in guest and plugin; guest tested by mouse, keys and host lines |
| CC1 → Macro 1, pitch bend, `show` for incoming MIDI | DONE in plugin (CC1 added to the VST3 MIDI mapping) |
| Assembly ≤ 6 s with the keyboard and new header | DONE: 5.37 s on Windows' clock, 5.42 s wall at normal load (was 7.09 s before batching the keys) |
| Batch CLI: `tools/batch_render311.py JOBS.json` (XP's job format) via `render311` | DONE on Linux: 33/33 presets, 214.5 s of audio in 18.9 s (11.3x real time, 8 at once) |
| Windows tests in BasiliskHost (`--test`, `--selftest`) | DONE, all pass (numbers below) |
| pluginval strictness 10, Windows | DONE: SUCCESS, 25 test groups including the editor |
| Mac build (VST3 + AU), auval, pluginval on Mac | DONE: auval pass; pluginval 25/25 for VST3 and AU |
| render311 for Windows and Mac in the release | DONE: bit-identical on Linux, Windows, macOS arm64 and x86_64 (`-ffp-contract=off` on Mac) |
| Plugin-window test in BasiliskHost (`--editor-script`): keys, drag, Hold, preset < > | DONE (a click queue in the engine lets instant posted clicks land at their own place) |
| Host-lane bugs: process() blocked 4–7 s; inheritable core-file handle; %TEMP% leftovers | DONE: live never waits; CopyFile/CreateFile; delete retry + sweep of dead processes' folders (0 left) |
| Live program change | idle recorders are rebuilt first, sounding ones get up to 1.5 s; 50/50 notes at normal load |
| README, download page, release v1.2.0, commit, push | DONE |

**Test rules (owner, 2026-11-13).**
- No REAPER, ever.
- Tests run in BasiliskHost (`tools/basilisk-host`) and bsynth-host (`packages/basilisk-synth/tools/testhost`). Missing features are built there.
- The REAPER copy used earlier in this round (`C:\Users\willi\bs311r3`) has been deleted.

### Measured

**render311**, all on Linux:
- Notes are 7–8.5x real time once the machine has resumed and built: 0.4–0.6 s, or 1.8 s for a 12 s collage.
- 0 late notes. 1 late note per render was fixed by moving the envelope-view redraw to idle time.

**DNA v2 checks** (headless renders):

| Gene | Expected | Measured |
|---|---|---|
| `O300` | right layer starts 300 ms after the left | 0.307 s vs 0.007 s |
| `Q-100` / `Q100` | hard left / hard right | hard L/R |
| `Ja0,0.300,100.1000,0` | gain rises to 1.0 at 300 ms, 0.57 at 600 ms | 1.0 at 300 ms, 0.54 at 600 ms (against the same DNA without `Ja`) |
| macro `N` | rebuilds with more echoes | 1.8 s build vs 0.5 s; different energy curve |

**BasiliskHost `--test`** (Windows VST3, test pattern, 50 notes):

| Check | Result |
|---|---|
| Offline repeats | bit-identical |
| State reload | bit-identical |
| `.vstpreset` reload | bit-identical (final build; an earlier build was within 7.5e-9) |
| Realtime | 50/50 notes, pitch within 2 cents, slowest process() 14 ms. Not bit-identical to offline any more: live never waits for Windows |
| Notes heard | 50/50 |
| Pitch | within 2 cents on all 36 measured notes |
| Onsets | median 17 ms after latency (DING's attack; notes are stamped sample-exact) |
| 2 instances | pass |
| Orphan processes | none |

**BasiliskHost `--selftest`** (GUI):
- Every phase is audible on the tap: on-screen keyboard, computer keyboard, bend, pattern, automation.
- 0 underruns.
- Editor 1023x767.

**Assembly** (Windows' clock), stages in ms:
- grow 369
- clock 681
- recorders 3997
- envelope 4228
- panel 5055
- ready 5420

### Known limits

- A 3.11 library sound is 22050 Hz 16-bit mono. Sounds over 30 s are skipped, the same rule as the 30 s buffer rule.
- `library.zip` is 93 MB of PCM, so the bundle grows by that much.
- Live processing never waits, so notes played before Windows has assembled (about 5.5 s after loading) are silent. Offline renders wait.
- The emulator needs about one core in real time. With the PC saturated by other lanes (load 11–21), the assembly took 9–10 s, and a live program-change run sometimes lost the chord 0.5 s after the change.
- The scratchpad shared by the lanes was wiped once mid-round. Release files are now staged in `~/bs311/rel`.
- REAPER lists the VST3 MIDI-mapping parameters (16 channels × 5 controllers) before the plugin's own parameters.

## Round 2 (v1.1.0), done

- Presets in hosts: IUnitInfo program list in patched DPF; AU factory presets.
- Reload bit-identical: integer DAC anchor, strict offline pacing.
- Seamless preset change: in-place rolling rebuild. A spare bank of 32 recorders runs out of GDI.
- Assembly blemishes fixed.
- Mac zip-drive crash: DOSBox Pure UB.
- Typing into Windows.
- CPU 55% → 13% idle.
- Ad-hoc signing, stated plainly.
- Harmony button follows the DNA.

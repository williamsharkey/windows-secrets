# BASILISK 16: status

- **Round 5 (in progress): Preset Engine 2, DNA v3** (`design/PRESET-ENGINE-2.md`, branch `design/preset-engine-2`).
  One release, 1.3.0, when every phase is solid; features are announced to the coordinator when usable locally.
- v1.2.1 is the release (basilisk-synth-311-v1.2.1): the fixes the sndrec demo renders found, below.
- v1.2.0 (basilisk-synth-311-v1.2.0) was round 3; its record is further down.
- v1.1.0 was basilisk-synth-311-v1.1.0, commit 948ce56.
- There is still no plugin-made sound, by design: every sound comes from the sixteen SOUNDREC.EXE in Windows 3.11.

## Round 5: Preset Engine 2 (DNA v3) on 3.11

| Phase | Status |
|---|---|
| Core merge | DONE: `core/dna3.*`, `engine3.*`, `recipe.*`, `scales.*` as new files (dna.cpp, voices.cpp untouched: v1/v2 identical by construction), now the PE2 branch's 1142d52 (section 18 keys and scales, `D` degree harmony, and the `W` time subkeys agreed with the PE2 lane: `Wo` offset to 30 s, `Wb` beat delay, `Wg` beat gate, `Wt` tempo sync, `Wr`/`Wp` looping drawn envelopes); `core/test_v3.sh`: 30,001 v3 checks, 20,000 fuzz x 3 forms 0 failures, 240,223 recipe checks. The fold into dna.cpp waits for the XP lane's 1.2.1. |
| 1 Windows, random, desktop, help | DONE locally (not released): `hi 3` -> `hi 3 311 <state> win,desk`; `W` start/end/length/velocity/tape (`Wm`) and `Y` detune/level/late/pan, decided host-side (seeded, renders repeat; `plugin/V3Voice.h`, shared with render311); the start is a scroll-bar seek to round(from x 10000 / frames), the end a stamped `cut`; desktop mode (minimize box, SOUNDREC's icon, `desk 0/1` both ways, strips re-laid on restore); F1 opens BASIL16.HLP; the help lane's installer puts the help and a "BASILISK 16" group on C: (Program Manager rewrites the new group once on a writable boot inside make_machine, else it stops on the read-only zip). Measured: windows start within 0.4 ms of the target (correlation 0.998 against the whole sound at that point) and last exactly their length; desktop/restore and F1 by screenshot. |
| 2 Rate by task, voice modes | IN PROGRESS. Card: `RATETASK` (cmd 30) changes every voice of a task (and its release ghosts) at a stamped DAC sample, gliding linear in cents, queued (8 per voice) because the host sends ahead; `regate` takes back a release (continue), `STOPTASK` (31) ends a voice a regate kept. Measured: the first differing sample is the stamp (24001 of a change at 24000), an octave up at the midpoint ends at exactly 24000 + rest/2 (38313). Guest: `rate <rec> <hz> [glide [regate]]`, caps `win,desk,rate,loop`. Host: `plugin/V3Alloc.h` (shared with render311) plays the layers with N/S/D (core gets a 0-recorder pool for them): poly limit, mono, legato, continue, glide, priority; round-robin/random intervals, random recorder, layer groups, strum, unison width; `D` degree chords; live bend for every sounding recorder. `tools/test/test_v3alloc.cpp`: 19 checks ok. Also W time: Wt/Wo/Wb/Wg host-side (bpm from the host, render311 `--bpm`), Wr/Wp on the card (`lenv ... <loop>`). Not yet measured in the machine (the XP lane's quiet window). |
| 3 Tab frame (Voices, Playback) | DONE locally: push-button tabs [Main] [Voices] [Playback] in the DNA row (the open one stays down; `tab <id>` both ways); Main is the panel of before, another page replaces the rows under the DNA row, made on open and destroyed on close (one repaint per switch: 51-60 ms). Voices: Poly / Mono / Legato / Continue, Notes (Np), Glide (Ng), priority; Round-robin, Random note, Random recorder, Group, Strum, Width; Detune, Level, Late, Pan, Per key. Playback: Start (and its random high end), End, Length, Velocity to start, Tape; Wow, Flutter, Scoop with their rates; Delay, Beat delay, Gate, Tempo sync, Loop amp, Loop pan. Each control edits the selected layer's v3 token in the DNA (kept as written otherwise); no rebuild. |
| 4 Tape keyboard | |
| 5 Kit mode | DONE locally (658211b): pads, velocity layers, round-robin, segments (`seg`), pitch tracking and range, cut groups and mutes (`choke`), one-shot / gated; the kit button (Calculator's icon, greyed by Windows unless the DNA is a kit) opens the pad calculator: a real Calculator with 16 pads over its keys (MPC order zxcv/asdf/qwer/1234, the note under each), lit by MIDI. Still to test: mouse and computer keys on the pads; the Kit tab (map editing). |
| 6 Grains | |
| 7 Mine sequencer, Library tab | |
| Scales (section 18) | IN PROGRESS (host side done): parameters Key, Scale (the 37-scale library), Use Preset Scale, Snap, Remap Keys, Remap Anchor, Key Labels (automatable, in the state as `key`/`keyopt` lines, render311 `--key --scale --use-preset-scale --snap --remap --anchor`); every pitch resolved on the host (`V3Alloc`: D degree chords in the key; remap and non-12 tunings map every note; a 12-note scale without remap leaves plain layers chromatic, so old presets sound the same). Windows: `Key [C v] Scale [Major v]` in the DNA row (grouped, separator rows), picks go back as `keyset`; the strip greys out-of-scale white keys (a click still plays) and shows labels (degrees, sargam, names, cents). FFT of rendered notes (chimes): 16-TET 0/75/225/300/375/525, 19-TET 0/126.3/189.5/315.8/379.1/505.4, 5-limit JI 0/0/203.9/386.4/386.4/498.2, pentatonic remap 0/200/400/700/900/1200 cents, all within 0.2 cent; 33 V3Alloc checks. Still to do: the linear strip layout for remap and non-12 tunings, Scala import. The Scales page (a 4th tab: Use the preset's scale, out-of-scale snap, labels, the 12 notes from the root as toggles = a custom scale (`keymask`, saved in the state), remap and its anchor) is built and tested in the machine (clicks reach the host as keyset / keyopt / keymask; check boxes, radio buttons and the 12 note toggles show their states). |
| Calculator digit keys 0-F (strip numbers) | DONE locally: at startup a real Calculator (Scientific, Hex) is opened and its keys 0-F copied from the screen (they are painted by Calculator, not windows; it has no pressed look, so pressed = the same pixels with the two colours swapped); hidden until its turn, it appears above BASILISK 16 and the keys fly to the strips (save-under drawing, no trails), then it closes. Owner-drawn buttons at native size (39x28) at x 4 (strips moved to x 44), a 3-px layer-colour bar left of each; held = audition at the root rate, pressed while the recorder sounds. Assembly 5.74 s on Windows' clock (recorder gap 160 -> 140 ms to make room). 8x crops: corners transparent to the panel grey, no clipped glyphs. |
| R1 Recording: ADC | DONE locally (TR4: File > New records 22050 Hz 8-bit mono; a fed 1 kHz tone plays back at 1000.0 Hz, clicks every 24000 samples exactly): card `BSC_IN*` (40-47) with the Hermite converter, source = the host's input or the card's own output; BSYNTH.DRV `widMessage` (one input, WIM_DATA from the timer); bshm v2 input ring; the plugin's stereo sidechain input, stamped on the DAC clock like the notes; `rsrc side/self` |
| R2 Recording core | core/userstore (names, sha1, zlib, .b16, index, user lines: 74 checks, Python zlib both ways); Save... / Load... of the state as .b16 through the host's file dialog (built; the dialog not yet tested). The R: drive, harvest and `user` lines to the guest: to do |
| R3-R5 Recording | queued (RECORDING.md section 6): the header Recorder and the Rec page next |
| Pointer drags | DONE (a9bd56b): a held scroll-bar thumb follows a drag (BSYNTH.DRV feeds the host pointer through USER's mouse_event at interrupt time); checked in the plugin through BasiliskHost (Macro 1 to 69, Macro 3 past the end to 100). SOUNDREC's Seek bar ignored presses (real or posted) while part of BASILISK 16; it obeys WM_HSCROLL, so its mouse is now done in BASILISK 16 (subclass) and Sound Recorder gets the scroll bar's own messages: drags, arrows and page clicks work (tested). |

## v1.2.1: fixes from the demo renders (tools/sndrec-demo)

| Finding | Fix | Measured (the demo's own phrases) |
|---|---|---|
| Chord Thump silent: after `<<` the position is 0, so `]` deleted the whole sound | `]` at position 0 is a refused step and is skipped (like `[` at 0); the 3.11 Chord Thump also uses one `<` and G18 | 16/16 note starts sound; peak -4.8 dBFS |
| Critical Bass, Hardware Sub: XP sounds fall back to DING, whose slowed lead-in hid 12 of 16 notes | `presets/overrides311.tsv`: 3.11 versions in place (CHORD, RINGIN/RINGOUT) with gain | 4/16 → 16/16 note starts; peaks -5.0 / -2.6 dBFS |
| Bowl Swell about -48 LUFS | `singing_bowl_c` is silent-ish for its first 6 s; Bowl Swell and Bowl Morph use `singing_bowl_commons_2` | gated RMS -47.5 → -20.1 dB |
| Echo Count, Macro Echoes: chords dropped offline when Macro 1 changes N | offline: a parameter change becomes the DNA before the block's notes are stamped, and only a change that needs Sound Recorder makes the render wait (non-rebuild changes no longer mark Windows busy) | 24/24 notes in all six macro programs (BasiliskHost, Macro 1 automated) |
| Peaks above 0 dBFS: Vibe Wide, Cello Breath, Organ Ring, Echo Count, Kit | G-2..G-4; 3.11 Kit with 3.11 sounds; render311 now applies G like the plugin (it did not) | all below 0 dBFS (-1.5 .. -4.1) |
| Telephone Choir: 3 late notes in 54 | not fixed: 9 voices per chord, mostly steals (Stop, Rewind, Play each); about a millisecond, not audible | 3 of 54 |
| Silence line below the centre of every wave display | Sound Recorder draws it 18 rows down from its native 35-row height whatever the size: the control keeps 35 rows, 4 rows above the strip, and a 1-row cover leaves 29 rows with the line on row 14 | silence on the middle row of all 16; a loud TADA symmetric (5/5, 4/4 rows) |
| Electromech and water sounds | the library disc scans every category | 510 sounds, 112 MB |

| XP's sounds (DNA.md 2.4: one name, one file) | `C:\XPSOUNDS\X<nn>.WAV` for every XP file of core `kSoundFiles311` (33), from the user's own XP image through the sound-archaeology extractor (`tools/xpsounds311.py`; no Microsoft audio in git); the guest follows the core's 39-name table and reads each file's rate and length from its header; the DING fallback is gone | 31 programs that played DING now play XP's sounds; all render, none over 0 dBFS, 0 late |
| Critical Bass on its real `critstop` | critstop's 42 ms lead-in, ×4 slower and an octave down, hid 12 of 16 notes (the same on XP): 3.11 override trims it (`critstop@t40[<<`) | 16/16 note starts; peak -2.7 dBFS |
| Preset browser filter | [All] [W3.11] [XP] buttons in Windows: XP = the DNA uses any XP file (sources and I/M sounds) | W3.11 lists BASILISK 16's own; XP lists the XP-sound presets |
| Integer pixel scaling | the editor draws Windows' screen at the largest whole scale k of its device-pixel size (GL viewport), nearest-neighbour, centred on the panel grey; minimum 1024x768; host resizes snap to multiples; opens at k = the display scale when it is 2 or more | Windows 1024x768: exact; 1536x1152: exact 1x centred at (256,192) on pure grey; 2048x1536: every 2x2 block one colour; Retina Mac (AU, backing 2.0): 2048x1536 device pixels, k 2, every 2x2 block one colour (GL readback, `BASILISK16_TEST_SHOT`) |
| "Wave" header's W cut | Windows 3.1's TextOut cuts what a glyph draws left of where the string starts (Arial's W reaches 1 px left): the headers are drawn after a space, moved left by its width | all headers and labels checked at 8x, during and after the assembly |
| Record button's mic "missing pixels" | none missing: SOUNDREC's bitmap 270 (17x17, 1-bit) is drawn greyed (Windows 3.11's 50% dither for a disabled button: our wave driver has no input, so Record is disabled), and an unmodified SOUNDREC draws exactly the same pixels; Rewind/Forward/Stop/Record glyphs identical to native, Play/Forward identical to their bitmaps | no change |
| render311 hung under Rosetta (macOS x86_64) on any DNA Windows must build | lines now go through the event ring (delivered by the engine thread), not into the card from render311's thread | Linux, Windows, macOS arm64 and x86_64 bit-identical again; the plugin itself was unaffected (x86_64 = arm64 renders) |

- A 29-row strip (gaps between strips) made every repaint slow: assembly 5.9 s, keys painted late. Strips stay 30 rows.
- The Sound drop-down is no longer sorted by Windows: LIBRARY.TSV is already in order, and a sorted insert of 516
  items blocked painting. It now fills in 54 ms, after `ready`.
- Assembly: 5.39 s on Windows' clock, 5.41 s wall.

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

# SNDWAVE2000: the multitimbral experiment (one Windows 3.11, many lanes)

The owner asked for this experiment: build a variant of SNDWAVE2000 with 16×4, 16×8, 16×16 or 16×32 Sound Recorders
in one emulated Windows, keep one waveform per lane, and find out whether the emulator and the host can carry that.
This is the record of the experiment. Branch `exp/multitimbral`; the code is in `packages/basilisk-synth-311/mt/`. It
is not merged.

**The answer in one paragraph.** Windows 3.11 cannot hold 512 Sound Recorders, and the limit is not CPU or memory.
Its 64 KB USER heap fills at 41 stock recorders. When the recorders are stripped in their own task, the ceiling is
165. So 16×32 and 16×16 are impossible, and 16×8 (128 recorders) and 10×16 (160) are the most that fit.

Within those limits, one Windows plays many lanes well:
- **Identity:** every lane's stem is bit-identical, or identical to float rounding (6e-8), to the same track rendered
  by its own emulator.
- **Offline:** 8 lanes take 6× less CPU than 8 separate engines.
- **Real time:** up to 10 lanes play with 0 late notes on about 21% of one core. 32 lanes play with 0 late notes once
  the emulated CPU gets 240,000 cycles.

Two optimisations found on the way make every headless engine about 1.75–2× faster, the 1.4 per-track design
included: skipping DOSBox Pure's video frame, and the dynamic core.

All numbers come from the build PC: 16 cores, x86-64, WSL2 Linux. "Quiet" means the coordinator had paused the
other lanes. The other runs shared the PC at load 9–25, so their wall times are pessimistic.

## 1. Predicted limits, and what was measured

Before measuring, I predicted the limits below from the code and from PROGRESS.md. The probe
(`mt/guest/probe.c`) then cold-booted WfW 3.11 (memsize 64), launched hidden SOUNDREC.EXE with DING.WAV until
Windows refused, and walked the heaps with ToolHelp.

| Resource | Prediction (and evidence) | Measured |
|---|---|---|
| USER heap (64 KB) | Every recorder is a dialog with 15 child windows plus a menu, about 1 KB each, so about 40–60 recorders | **Binding.** About 1.2 KB per recorder. WinExec fails (code 8) at **41** recorders with USER 9% free. |
| GDI heap (64 KB) | PROGRESS.md: "out of GDI at about 30 Sound Recorders, 4% free"; TR5: 19–21% free with 18 | About 770 B per recorder: 7 brushes, 6 bitmaps, 1 font, 1 DC (the wave display's), 1 region. 26% free at 41. It becomes binding at 67–123 once USER is stripped. |
| Conventional memory (< 640 KB) | A TDB and PSP per task, below 1 MB: a few hundred tasks | GT_TASK is about 0.55 KB per task. Windows still had 60–140 KB below 1 MB at 165 tasks. Not binding. |
| Task count | No fixed cap in 3.1, only memory | 167 tasks ran (165 recorders, PROBE, Program Manager). Not binding. |
| LDT selectors (8192, shared) | About 10–30 per recorder: DGROUP, TDB, PSP, queue, and a huge buffer takes one per 64 KB | 7760 free at boot; about 12 per recorder with DING. 5742 free at 165. Long sounds use more (one per 64 KB), but not binding here. |
| Extended memory (memsize 64) | Wave buffers: up to 1.3 MB each for 30 s sounds | 23–34 MB of SOUNDREC blocks for 10–20 real song lanes, out of 64 MB. Fine for real songs, and 88–91% of it is duplicate (section 5). |
| SOUNDREC data segment | NE header: DGROUP 1030 B + heap 1 KB + stack 8 KB, moveable | About 10 KB per recorder, anywhere in memory. Not binding. |
| Card voices, BSYNTH.DRV instances | 32 each (`BS_CH`, `MAXI`). With every recorder able to play, 32 voices cap total polyphony across lanes | Raised to 128 in the experiment's card and driver. No voice ran out in any song. |
| Card envelopes | `lenv` holds 8 layers and ENV one A/D/S, both global, so lanes would overwrite each other | Made per lane: 32 lanes × 8 layers of drawn envelopes, A/D/S per lane. |
| DOSBox CPU (fixed 60,000 cycles/ms) | One emulated CPU arms every lane's notes | **Binding in real time beyond 10 lanes:** late notes at lookahead 0 (section 4). Raising cycles to 240,000 fixes 32 lanes. |
| Message-queue throughput | Every note is SendMessage Stop/Rewind/Play into another task | This is what the cycles pay for: one Windows serialises every lane's Play. |
| Host mixing | Each voice is a 4-point Hermite per sample | BSYN_CallBack plus sample_at is about 6% of a 16-lane render. Not binding. |

### Stripping a recorder (MTHOOK.DLL)

- **The strip must run in Sound Recorder's own task.** Windows 3.11's DestroyWindow refuses another task's windows:
  the first strip attempt destroyed nothing. MTHOOK.DLL installs a system WH_GETMESSAGE hook. When the synth posts its
  registered message to a recorder, the recorder's own task destroys the menu, the frames, the buttons, the fields and
  (except on a lane's first recorder) the wave display, and blanks the title.
- **GDI objects.** The brushes, fonts, pens and bitmaps a hidden recorder made are deleted. They were found by
  diffing the GDI heap before and after its launch. A recorder that is never painted never needs them.
- **The recorders must stay "shown", off screen at (-3000, -3000).** A hidden (SW_HIDE) Sound Recorder ignores
  WM_DROPFILES, and its builds came out empty (length 0, 400 ms waits).
- **Missing fields come from the card or are borrowed.**
  - The card answers "is it playing" with TASKPLAYING (cmd 35): the task has the wave device open.
  - During a build, the synth briefly gives the recorder static controls of its own with ids 200, 201 and 202.
    Sound Recorder's SetDlgItemText finds them by id, so length and position read as before.
  - Seeks use the fixed scroll range 0..10000.

| Launch, shown off screen, GDI objects deleted | Recorders before WinExec fails |
|---|---|
| Stock (hidden, nothing stripped) | 41 (USER) |
| Menu and controls gone, keeps status, position, length, seek bar | 94 |
| Keeps length and seek bar | 124 |
| Keeps the seek bar | 147 |
| Keeps nothing (the experiment's worker recorders) | **165** |

Each lane's first recorder keeps its wave display (one DC and a region). These are the experiment's waveform per
lane: a 236×44 grid on MTSYNTH's window.

## 2. What was built

| Part | What it does |
|---|---|
| `mt/guest/mtsynth.c` (generated by `mt/tools/make_mtsynth.py` from `guest/synth.c` plus `mtsynth_head.c`/`_tail.c`) | SYNTH.EXE's sound engine with no GUI. DNA parsing, pools, `run_steps`, `play_rec`, the stops and the rates are copied line for line from synth.c, so a lane builds and plays exactly as an instance does. NB_LANES × LANE_RECS recorders. Lines are `@<lane> <line>`, and replies about a lane carry `@<lane>`. `cap <n>` sets a lane's recorder count. |
| `mt/guest/mthook.c` | MTHOOK.DLL: the in-task strip, plus an unused CBT veto. |
| `mt/guest/bsynth-mt.c` | BSYNTH.DRV with 128 instances. |
| `mt/card/bsynth-mt.cpp` | The card: 128 voices, 512 arms, per-lane envelopes and A/D/S (the arm's layer encodes lane × 8 + layer), TASKPLAYING, and a **per-lane bus**, so every lane comes out as its own stem (`bsyn_host_read_lane`). Also buffer statistics (`bsyn_host_bufstats`) and no-video (`bsyn_host_video`, or env BSYN_NOVIDEO). |
| `mt/card/novideo.patch`, `novideo-card.patch` | DOSBox Pure's GFX_StartUpdate skips the frame when the card says nobody watches, and still counts it. |
| `mt/tools/mtrender.cpp` | render311's loop (plugin/SongEngine.h) with one NoteHost per lane on one machine. Writes per-lane stems and the mix. Options: `--realtime 1` paces blocks to the wall clock and counts missed deadlines; `--cap 1` sizes each lane's recorders to its track; `--until`. |
| `mt/tools/song2lanes.py` | A songs-lane `.song` becomes an mtrender job: each track's DNA and its MIDI, exactly what songrender hands render311. |
| `mt/tools/sep_render.py` | The baseline: every lane through its own render311, K at a time, compared stem by stem. |
| `mt/tools/probe_run.py`, `mt/guest/probe.c` | The limit probe. |

The workload is the songs lane's *After Midnight Dubplate*: 10 tracks, 112.8 s, 134 bpm. It is repeated ×4 for 20
and 32 lanes. Kits, pads and leads have 4–1560 events per track.

## 3. Offline results

### 3.1 First sweep: today's engine (normal core, video drawn), PC loaded (load 9–25)

| Lanes × recorders | Up | USER free | Build | Play (wall) | CPU, all | Late |
|---|---|---|---|---|---|---|
| 4 × 16 | 64 | 61% | 15 s | 75 s (1.5× rt) | 79 s | 0 / 1654 |
| 8 × 16 | 128 | 28% | 19 s | 93 s (1.21×) | 102 s | 0 / 2985 |
| 10 × 16 | 160 | 12% | 22 s | 101 s (1.12×) | 115 s | 0 / 3063 |
| 16 × 8 | 128 | 28% | 30 s | 146 s (0.78×) | 184 s | 0 / 6503 |
| 20 × 8 | 160 | 12% | 35 s | 196 s (0.58×) | 224 s | 0 / 7096 |
| 32 × 4 | 128 | 28% | 34 s | 226 s (0.50×) | 248 s | 11 / 13054 (max 11 ms) |

### 3.2 The profile, and two fixes

perf of a 16 × 8 render (30 s of the song), normal core:

| Where | Share |
|---|---|
| CPU_Core_Normal_Run (the interpreter) | 61% |
| **Normal1x_16_32_L: scaling video nobody sees (vid_want = 0)** | **18%** |
| Segment loads (Descriptor::Load, CPU_SetSegGeneral) | 2.5% |
| BSYN_CallBack + sample_at (card mixing) | 2.7% |
| The renderer's own loop | 0.5% |

- **No video.** DOSBox Pure renders every frame whatever the frontend wants. `frameskip=10` in the conf changed
  nothing. The patch makes GFX_StartUpdate return false and still count the frame; without the count, retro_run
  spins forever.
- **Dynamic core.** `core=dynamic` in w31.conf. The existing normal-core snapshot resumes into it.

| 16 × 8, 30 s, PC loaded | Build | Play CPU |
|---|---|---|
| Normal core, video | 30 s | 32 s |
| Normal core, frameskip 10 | 31 s | 33 s |
| Normal core, no video | 14 s | 23 s |
| Dynamic core, video | 15 s | 25 s |
| **Dynamic core, no video** | **9 s** | **17.5 s** |
| Dynamic, no video, cycles 30,000 / 120,000 | 10 / 9 s | 16 / 17 s |

- Building gains the most: Sound Recorder repaints while it edits, and every repaint was scaled.
- **render311** (one track: the kit, 112 s) took 92 s stock, 69 s with no video, 87 s with the dynamic core, and
  **53 s with both**.
- On the songs lane's own render311-la (1.3.1, the wobble track): **40.1 s became 19.7 s**, bit-identical,
  0 late notes.

**Determinism.** Two runs of the same configuration give bit-identical stems, for both the normal and the dynamic
core. Across configurations (video on or off, normal or dynamic, frameskip) stems differ by at most 6e-8 (−144 dBFS).
The cause is the float summation order in the card's mix: which card channel a voice lands on can change. It is
never a different note.

### 3.3 Second sweep: dynamic core, no video, quiet (the full 112 s song)

| Lanes × recorders | Boot | Build | Play wall | CPU, all | Late | Duplicate buffers | Peak RSS |
|---|---|---|---|---|---|---|---|
| 4 × 16 | 2.0 s | 4.1 s | 28 s (4.0× rt) | 26 s | 0 | 88% | 404 MB |
| 8 × 16 | 1.5 s | 2.3 s | 21 s (5.3×) | **18 s** | 0 / 2985 | 88% | 580 MB |
| 10 × 16 (loaded) | 2.4 s | 3.3 s | 30 s (3.7×) | 30 s | 0 / 3063 | 88% | 671 MB |
| 16 × 8 | 1.8 s | 3.8 s | 35 s (3.3×) | 34 s | 0 / 6511 | 91% | 923 MB |
| 32 × 4 | 1.9 s | 3.7 s | 44 s (2.6×) | 45 s | 12 / 13055 (max 12 ms) | 90% | 1.6 GB |

Peak RSS is mostly the stems, held as float in memory (43 MB per lane-song). The engine itself is about 150 MB.

## 4. Real time

`mtrender --realtime 1 --lookahead 0` runs the first 60 s of the song with dynamic core and no video, quiet. Blocks of
512 samples come at the wall clock's pace, as a DAW's would. A block whose samples are not ready by its time plus the
plugin's fixed 60 ms (kLat) is a dropout. Live playing cannot look ahead, so the lookahead is 0.

| Lanes × recorders | CPU per real-time second | Missed blocks | Late notes |
|---|---|---|---|
| 1 × 16 (= one instance) | 10–13% of a core | 0 / 6005 | 0 |
| 1 × 16, normal core with video (today's plugin) | 22% | 0 | 0 |
| 4 × 16 | 16% | 0 | 0 |
| 8 × 16 | 20% | 0 | 0 / 1483 |
| 8 × 16, normal core with video | 33% | 0 | 0 |
| 10 × 16 | 21% | 0 | 0 / 1486 |
| 16 × 8 | 30% | 0 | 50 / 3274 (max 31 ms) |
| 16 × 8, normal core, no video | 42% | 0 | 55 |
| 20 × 8 | 33% | 0 | 109 / 3438 (max 58 ms) |
| 32 × 4 | 40% | 0 | 603 / 6223 (max 68 ms) |

- **The DAC never misses.** Even 32 lanes produce audio faster than real time on one core.
- **Late notes are an emulated-CPU budget, not a host one.** The guest presses Stop, Rewind and Play for every
  lane's notes through one Windows. At 60,000 cycles per emulated millisecond, the notes of a dense moment queue up
  past their stamp.
- The late count does not depend on the host's speed: an offline run at lookahead 0 gives the same 604.
- Raising the emulated CPU fixes it (32 × 4, lookahead 0, first 60 s):

| Cycles | Late notes | CPU (loaded PC) |
|---|---|---|
| 60,000 (today) | 604 / 6223 | 48 s |
| 120,000 | 22 (max 10 ms) | 59 s |
| **240,000** | **0** | 55 s |

**The cost per lane is small.** One lane costs 10–13% of a core and 8 lanes cost 20%. An idle Windows (timers,
the scheduler, the DAC) is most of an instance's cost, and lanes share it.

## 5. Memory: duplicates and reclaiming unused recorders (the owner's question)

**Duplicates.** The card hashes (FNV-1a) the last buffer each recorder's task wrote. In every configuration, 88–91%
of the bytes the recorders played are duplicates:

| Lanes × recorders | Recorders that played | Their buffers | Distinct | Duplicate |
|---|---|---|---|---|
| 4 × 16 | 53 | 11.6 MB | 1.4 MB | 88% |
| 8 × 16 | 109 | 17.9 MB | 2.1 MB | 88% |
| 16 × 8 | 129 | 26.3 MB | 2.3 MB | 91% |
| 32 × 4 | 129 | 22.9 MB | 2.3 MB | 90% |

Almost all of it is one cause: a pool. A layer's 4–16 recorders all hold the same built sound, because that is what
gives polyphony. The rest is the same preset on two lanes.

**Sharing guest memory is not possible without changing Sound Recorder.**
- Each SOUNDREC owns its GlobalAlloc'd buffer.
- Windows 3.11 has no copy-on-write sharing between tasks, and Sound Recorder edits its buffer in place.
- On the host side, the card copies the buffer per WRITE into the voice's own vector. That is host memory only while
  a voice plays: a few MB, and too little to matter (read_guest does not appear in the profile).
- A hash-consed card buffer (shared_ptr by hash) would remove those copies, but it is not worth its complexity now.

**Reclaiming works and costs nothing.** Most recorders of a pool are never needed. Core's allocator goes round-robin,
so a mono bass line touches all 16 recorders in turn, but 2 of them would do. `mtrender --cap 1` counts a track's
peak overlapping notes (note-on to note-off plus the release) and multiplies by each layer's harmony and unison. It
then tells the lane `cap N` before its DNA. dna_parse gives the pools only N recorders, and the host learns the pools
from the `layer` replies as usual.

| | Recorders built | SOUNDREC memory | Guest memory used | Build CPU | Stems |
|---|---|---|---|---|---|
| 4 lanes, 16 each | 64 | 12.8 MB | 14.4 MB | 3.6 s | — |
| 4 lanes, capped (16, 2, 2, 2) | 22 | **4.1 MB (−68%)** | 5.7 MB | **1.0 s** | lanes 1–3 bit-identical, lane 0 within 6e-8 |
| 10 lanes, 16 each | 160 | 22.9 MB | 24.7 MB | 3.3 s | — |
| 10 lanes, capped | **61** | **11.3 MB (−51%)** | 13.0 MB | 2.3 s | 0 late |

- The cap also attacks the real limit, the USER heap. The 10-track song needs 61 recorders, not 160.
- With recorders launched lazily to each lane's cap (not done here: the experiment launches LANE_RECS per lane), a
  16-track song would fit in one Windows with room to spare.
- **Stale buffers after a rebuild:** Sound Recorder frees the old buffer when it loads the new file, and freepages
  went back as expected.
- **Undo or edit copies:** Sound Recorder 3.1 keeps none in memory. Revert reads the file again.
- **The clipboard:** it holds one copy of the last Copy (C/P genes), one per Windows, not one per recorder.
- **Empty File > New buffers:** never made (the recorders start with DING.WAV, 11 KB).

## 6. One Windows against N Windows

The same 8 tracks, quiet, on the same fast engine (dynamic core, no video):

| | One Windows, 8 lanes | 8 render311s, 4 at a time |
|---|---|---|
| CPU | **18 s** | 108 s |
| Wall | **25 s** (one thread) | 50 s (4 cores) |
| Memory | one engine (~150 MB) plus stems | ~211 MB per engine |
| Determinism | bit-identical run to run | bit-identical run to run |
| Sound | stems identical to render311 (bit-identical, or ≤ 6e-8) | reference |
| Real time, per real-time second | 20% of a core for all 8 | 8 × 10–13% ≈ 0.8–1.0 core |

Before the fixes, on the loaded PC, the same comparison was 101 s against 393 s CPU.

**Sound identity.** The first 4 tracks rendered as lanes and through render311 on the 1.3.0 machine compare as follows:
- Lanes 1–3: every sample identical.
- Lane 0 (the kit): 99.9% of frames identical; the rest differ by at most 6e-8, which is summation order.
- Every note is played by a real SOUNDREC.EXE. The card only resamples, envelopes and sums, as it does today.

## 7. Practical lane counts

| | On this PC (16 cores) | Estimate: a typical 8-core laptop (about 0.6–0.7× the single-thread speed) |
|---|---|---|
| Real time, today's 60,000 cycles | **8–10 lanes × 16** in one Windows: 0 late notes, ~20% of a core | the same 8–10 lanes (late notes are emulated-time), ~30–35% of a core |
| Real time, 240,000 cycles | 32 lanes × 4 with 0 late notes; offline it was ~0.9 core on the loaded PC, so it needs a real-time check | probably 16 lanes; 32 lanes would be tight on one core |
| Offline (Song tab render) | 16 × 8 at 3.3× real time in one thread; several Windows in parallel scale with cores | 16 × 8 at ~2× real time per engine |
| Hard ceiling | 165 recorders per Windows (USER heap); 10 × 16 or 16 × 8, more with caps | same (it is Windows', not the PC's) |

## 8. Recommendation

1. **Now (1.4): keep per-track engines, and take the two fixes.**
   - Apply the no-video patch and core=dynamic to render311 and to the Song tab's engines. They are about 2× faster,
     need no design change, and their stems match within 1e-7.
   - Also apply no-video to the plugin's own engine whenever the editor is closed (vid_want = 0).
   - The songs lane is A/B-testing this on 4 songs.
2. **Later (1.5): a hybrid.**
   - **Light lanes share one Windows.** These are lanes whose track needs few recorders (bass, leads, pads, effects):
     about 61 recorders for a 10-track song, against 165 available. One Windows does them at 6× less CPU than
     separate engines, with identical stems.
   - **Heavy lanes get their own Windows.** These are kits and dense chords that need 16 recorders and many notes per
     second. They are the ones that make a shared Windows late in real time.
   - Run the groups on parallel engines. For offline renders this beats per-track engines on CPU and matches them on
     wall time with fewer cores.
3. **A live multitimbral instrument (16 MIDI channels in one SNDWAVE2000) is possible** with 8–10 lanes per Windows,
   or 16+ with cycles raised to 240,000. Its cost is the 165-recorder ceiling.
   - What it needs:
     - this card (lanes, 128 voices, lane buses);
     - an MTSYNTH-style guest beside SYNTH.EXE;
     - recorders capped to each lane's track;
     - lazy launching.
   - The full GUI (strips, Calculator keys, assembly) cannot be had for every lane. Each lane's GUI would be one
     waveform, as here.
   - **Not done in this experiment:** BasiliskHost. The plugin was not changed. Real time was measured with
     mtrender's wall-clock pacing, which is the same loop as the plugin's offline path, with blocks timed like a DAW's.

## 9. How to repeat it

```
# the machine: a copy of the 3.11 lane's drive folder (C:), run=C:\MT\MTSYNTH.EXE, Wave=bsynth.drv (the 128-voice one),
# TADA.WAV/CHORD.WAV and XPSOUNDS in place; P: and L: as in the release machine; w31.conf = engine/w31-folder.conf.in
# (core=dynamic for the fast runs)
python3 mt/tools/make_mtsynth.py
wcl -bt=windows -l=windows -ml -zm -zc -k16384 -DNB_LANES=8 -DLANE_RECS=16 -DKEEP_WORK=0x8000 -DKEEP_LEAD=0x8008 \
    -fe=MTSYNTH.EXE mt/guest/mtsynth.c mmsystem.lib toolhelp.lib shell.lib
# the core: dosbox-pure as tools/build.sh makes it, with mt/card/bsynth-mt.cpp as src/hardware/bsynth.cpp and mt/card/novideo.patch
python3 mt/tools/song2lanes.py SONG.song MACHINE131 jobs/x      # one lane per track
mtrender --machine M --core CORE.so --job jobs/x/job.txt --out-dir out --lookahead 150 [--cap 1] [--realtime 1 --lookahead 0]
python3 mt/tools/sep_render.py jobs/x/job.txt render311 MACHINE131 out/r311 --parallel 4 --compare out
```

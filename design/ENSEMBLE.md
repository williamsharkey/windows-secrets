# SNDWAVE2000 Ensemble (1.5 experiment)

One plugin instance, one Windows 3.11, ten MIDI channels. Each channel is a lane, with its own preset built by its
own real Sound Recorders. It builds on the multitimbral experiment (`design/MULTITIMBRAL-EXPERIMENT.md`, branch
`exp/multitimbral`). Branch `exp/ensemble`; code in `packages/basilisk-synth-311/ensemble/`. SNDWAVE2000 itself is
unchanged; the one shared file touched, `tools/make_machine.py`, only gained options (`--run`, `--guest-extra`,
`--conf`) whose defaults give the same machine as before.

Every note still comes from a real SOUNDREC.EXE. The plugin chooses the recorder and stamps the DAC sample, and the
card resamples, envelopes and sums, exactly as in SNDWAVE2000.

## 1. What it is

| Part | What it does |
|---|---|
| `guest/ensemble.c` (made by `tools/make_ens.py` from `guest/synth.c`, `ens_head.c` and `ens_tail.c`) | ENSEMBLE.EXE: SYNTH.EXE's build and play code, copied verbatim, plus the mixer, the waveforms, the track view and the assembly. Ten lanes. Lines carry their lane (`@3 on 2 22050 ...`). |
| `guest/mthook.c` | MTHOOK.DLL: strips each Sound Recorder in its own task (menu, title, controls; hides its OLE server window). |
| `guest/bsynth-ens.c` | BSYNTH.DRV with 128 voices. Its done-buffer timer runs from before the snapshot. |
| `card/bsynth-ens.cpp` | The BSYN card: 128 voices, per-lane envelopes and A/D/S, per-lane stem buses (`bsyn_host_read_lane`), each lane's waveform (`PEAKS`), and "is this task playing" (`TASKPLAYING`). It includes main's no-video hook. |
| `plugin/EnsemblePlugin.cpp`, `EnsembleUI.cpp` | The DPF plugin: MIDI channel k+1 to lane k, one SNDWAVE2000 note host per lane (`V3Host.h`), the lanes' buses mixed with level, pan, mute and solo. It has 10 aux stereo outputs (post-fader), a state with each lane's pack, preset and DNA, and the 1,437 pack presets behind each lane's < >. The editor is SNDWAVE2000's (Windows' screen). |
| `machine/w31.conf.in` | The machine's settings (64 MB, normal core, 60,000 cycles). |
| `tools/` | `song2ens.py` turns a songs-lane `.song` into a test. `shots.py` and `dbg.py` drive the machine. `compare.py` and `cmplanes.py` compare renders. `sep_render.py` is the per-track render311 baseline. |

Identity: VST3 class "SNDWAVE2000 Ensemble", brand Wshk, unique id `B3En`, CLAP id
`com.williamsharkey.sndwave2000-ensemble`, version 1.5.0. It installs beside SNDWAVE2000 and shares nothing at run time.

## 2. The layout

A mixer, in Windows 3.11's own controls, inside the SNDWAVE2000 look:

```
 SNDWAVE2000 Ensemble
 [ Ch 1 ][ Ch 2 ] ... [ Ch 10 ]           MIDI channel; a click auditions the lane (C4)
  preset    preset      preset            the lane's preset (pack presets, < > step through them)
 [<][>]   [<][>]  ...
 |wave|#  |wave|#                         the lane's waveform, vertical, with a yellow playhead; # = level fader
 |    |#  |    |#
   100      100                           level 0..127 (100 = unity)
 [<-|->]  [<-|->]                         pan, L64..C..R63
   C        C
 [x]Mute [x]Solo
  16 rec   12 rec                         the lane's Sound Recorders (its cap)
 Track view
 1 Loft Tine Br |  .  ..  . .  ..  .  .   every lane's notes, at their pitch, scrolling left (a beat line a second)
 2 Rubber Taxi  | . . . .  . . . . .
 ...
 10 lanes, 124 Sound Recorders. Free resources: user 24%, gdi 52%. Free memory 7904 KB.
```

The density follows a sequencer's LCD: ten strips of about 100 pixels, and below them a track screen. These are the
QY700's track view and mixer as inspiration only, with no names, logos or screens copied. Every control is a stock
Win16 one: push buttons, statics, scroll bars and check boxes. The waveform and the track view are two small window
classes that draw with Windows' own pens.

Screenshots in `design/ensemble/`:
- `playing-citypop09.png`: the plugin's editor in BasiliskHost, 60 s into CITYPOP 09.
- `assembly-in-plugin.png`: the editor from resume through assembly to playing.
- `assembly-sheet.png`: the assembly in the machine, with the rotating waveforms.
- `pixel-rotation-30deg.png`: Sound Recorder's own wave display turned 30 degrees, pixel by pixel.

## 3. The assembly, and turning the waveforms

The lanes start as the Sound Recorders' own horizontal wave displays: each lane's first recorder, stacked in two
columns where the track view will be. Lane by lane, 140 ms apart:
1. The lane's waveform takes over from its recorder's display, in place, at 0 degrees.
2. It flies up to its strip while it turns to 90 degrees and grows from 133 x 35 to 46 x 236, eased.
3. The strip's controls fly in from the edges after it: the channel button from the top, < and > from the sides, the
   fader and pan from below.

On Windows' clock, 10 lanes take 3.1 s at 38–70 ms a frame, with no trails (the children clip their siblings).

How a waveform turns:

| Way | How | Cost (emulated CPU) | Verdict |
|---|---|---|---|
| Vector (used) | The card reduces the buffer the lane's recorder last handed to waveOutWrite to 64 min/max pairs (PEAKS). The guest draws them Sound Recorder's way (green on black, the silence line) along any angle, with an integer sin table. | All ten lanes turn in the same frame: 38–70 ms a frame for the whole assembly, window moves included. | Smooth at any angle, cheap, and it shows the whole sound with a playhead. |
| Pixels | BitBlt Sound Recorder's painted wave display (133 x 35, 16-bit colour), then map every destination pixel back through the rotation, nearest neighbour. | 49 ms per frame for one lane (140 x 140). | Works, and keeps Sound Recorder's own pixels and frame. Too slow for ten lanes at once, and it is only Sound Recorder's zoomed view of the sound. A 90-degree copy costs the same loop. |

The `rotbench` guest command measures the pixel way. Screenshots: rot30 (Sound Recorder's display turned 30 degrees),
and the assembly sheets.

## 4. Measured

The workload is CITYPOP DEPROGRAMMED track 09, *Couch Fort Disco*: 186 s, 118 bpm, 11 parts. "room" (an ambience at
-36 LUFS) was left out for 10 lanes. That is about 27,000 card notes: the clavinet alone has 6,900 and the kit 5,000.
BasiliskHost 1.0.0, Windows VST3, 48 kHz, block 512. The PC was shared with other lanes at load 4–8.

### 4.1 Offline: identical to per-track render311

- Each lane's own output (ENSEMBLE_DUMP_DIR) against the same track rendered by render311 (1.4 machine, no
  lookahead, as a plugin cannot look ahead): all 10 lanes match. Max diff is 9e-8, float summation order; one lane is
  bit-identical throughout.
- Two things had to be right for that:
  - **The test's note times.** BasiliskHost rounds a note's time to the nearest sample and render311 floors it. The test
    MIDI (`song2ens.py --grid`) puts every event a quarter-sample after a sample, so both agree. With the album's own
    MIDI, notes land one sample apart, and the residual is -30 dB for the bass and -2 dB for the kit, with no audible
    difference.
  - **Kits get all 16 recorders.** A kit's pads round-robin over the pool. With a smaller pool a pad steals a ringing
    recorder and the sound changes (the percussion lane at 8.5 s). Kits are now detected from the DNA's v3 pads.
- Windows' replies are read on the audio thread at the start of every offline block, while the machine stands still,
  so the voice allocation sees every recorder's end at the same emulated time.
- **Repeat renders** are identical to 1e-7, not bit-identical: 0.3–1% of samples differ by at most 9e-8 between two
  runs. That is the card's summation order: which card channel a voice lands on varies with when some lines reach
  Windows. SNDWAVE2000 itself repeats bit for bit; making the Ensemble do so is open (section 6).

| Offline, the whole track | One Ensemble | 10 render311s, 2 at a time |
|---|---|---|
| CPU | about 264 s (BasiliskHost's whole process, analysis included) | 650 s |
| Wall | 166 s for 210 s of audio | 399 s |
| Late notes | 0 of 27,866 | 0 |

### 4.2 Real time (BasiliskHost's realtime test, paced to the wall clock)

A 60 s warm-up lets every lane build before the song. Dropouts are blocks where the machine was behind the host after
the builds (the plugin counts them). Late notes are notes the card started after their stamp.

| Lanes | Cycles | Latency | Late notes | Dropout blocks after the builds | CPU (whole host) |
|---|---|---|---|---|---|
| 1 | 60,000 | 60 ms | 0 | 47 of 22,232 (0.2%) | 23% of a core |
| 4 | 60,000 | 60 ms | 0 | 337 of 20,572 (1.6%) | 34% |
| 6 | 60,000 | 60 ms | 0 | 628 of 20,356 (3.1%) | 41% |
| 8 | 60,000 | 60 ms | 183 (1.0%, max 15 ms) | about 900 | 45% |
| 10 | 60,000 | 60 ms | 482 (1.8%, max 21 ms) | about 2,000 | 59% |
| 10 | 120,000 | 60 ms | 0 | about 6,000 | 63% |
| 10 | 240,000 | 60 ms (20 s warm-up) | 0 | most of the first 45 s (the builds) | 74% |
| **6** | 60,000 | **103 ms** | **0** | **1 of 20,358** | 41% |
| 10 | 60,000 | 103 ms | 495 (1.8%, max 25 ms) | 30 of 18,099 (0.2%) | 61% |
| 10 | 120,000 | 103 ms | 0 | 240 of 19,144 (1.3%) | 62% |

(The latency is the plugin's reported latency: 2,880 samples at the default lead of 1,024, and 4,928 with
ENSEMBLE_LEAD=3072.)

- **Two limits trade against each other.**
  - Notes come late when Windows cannot press Play for every lane in time. That is the emulated CPU, so more cycles
    fix it: 0 late at 120,000.
  - Dropouts come when the host cannot emulate fast enough to stay ahead. More cycles make that worse, and a longer
    lead fixes it.
  - Dense ten-part material needs both, more than this shared PC gives.
- **Honest limits at the current build:**
  - Up to 6 dense lanes play live with nothing late and no dropouts at about 100 ms latency.
  - At 60 ms, 4–6 lanes have 0 late notes but 1.6–3% dropout blocks.
  - 10 dense lanes play live with about 2% late notes (up to 25 ms) or about 1% dropouts, depending on the cycles.
  - Offline, 10 lanes are exact.
  - Light material (pads, sparse leads) leaves more room than CITYPOP's clavinet and kit.
- Builds: launching up to 124 recorders and building 10 presets takes about 20–45 s of real time at load. Live, the old
  sound plays until each lane's build is done.

### 4.3 Memory and Windows' resources

| Lanes | Recorders (caps) | Free USER | Free GDI | Windows memory free (of 64 MB) |
|---|---|---|---|---|
| 1 | 25 | 67% | 52% | 57.8 MB |
| 4 | 54 | 54% | 52% | 37.8 MB |
| 6 | 76 | 44% | 52% | 30.4 MB |
| 8 | 94 | 36% | 50% | 25.2 MB |
| 10 | 124 | 24% | 52% | 7.9 MB |

- With 10 CITYPOP presets (long samples) Windows is nearly out of memory: 7.9 MB free.
- memsize=128 does not help: Windows 3.11 still sees 64 MB (61 MB free at boot).
- Caps come from the preset: kits 16, others 4 x layers x harmony x unison, up to 16. The budget is 130 recorders for
  all lanes (USER holds about 165 bare recorders, and the mixer's windows need room).

## 5. What was found on the way (fixed)

- A snapshot taken right after the multimedia timers start leaves the resumed machine never returning a played buffer.
  The guest now waits 1.5 s before it asks for the snapshot.
- Pressing Stop at once after Play hangs a stripped recorder, so the silent first play is left to run out.
- Sound Recorder's OLE server window (SrvrWndClass) is the first top-level window of its instance. Finding "the
  recorder" by instance alone strips the wrong window and leaves a "Srvr" box at 0, 0.
- Lane lines that arrive while another lane builds: only `dna` waits. Everything else touches only its own lane, the
  card or a strip, and goes at once. An early version deferred everything, overflowed its queue and hung offline
  renders.
- Kit detection, the replies' timing, and the test MIDI's sample grid: section 4.1.

## 6. Not done

- Bit-identical repeats (they agree to 1e-7, section 4.1).
- pluginval: strictness 10 passes, with GUI tests skipped (11 stereo output buses, all enabled and disabled cleanly).
  The editor itself was exercised in BasiliskHost (the screenshots).

- macOS builds (VST3, AU, CLAP).
- The multi-out buses are declared (10 stereo aux outputs) but not tested in a host that reads them; BasiliskHost
  reads the main bus only.
- Live preset changes during playback were not measured. Lanes build one at a time and the old sound plays meanwhile.
- 11–16 lanes: the guest and card take up to 32 lanes, but USER and memory (section 4.3) make 10 the practical maximum
  with full presets.
- Performance work that would move the real-time limits: less guest work per note (each note is a Stop, a Rewind and a
  Play sent to another task), and a lead that adapts to load.

## 7. Repeat it

```
# guest, card, machine (WSL): see ~/ens/bguest.sh and ~/ens/mkm.sh (make_machine.py --conf ensemble/machine/w31.conf.in --run ENSEMBLE.EXE --guest-extra MTHOOK.DLL)
# the Windows core: DOSBox Pure at UPSTREAM.txt + dosbox-pure.patch + ensemble/card/bsynth-ens.cpp, DISABLE_DYNAREC, make platform=windows
# the plugin: cd ensemble/plugin && make DPF_PATH=<DPF with dpf.patch> WINDOWS=true CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++ vst3
python3 ensemble/tools/song2ens.py SONG.song MACHINE OUT --grid [--skip part] [--until S]     # lanes.txt, ens.mid, per-track MIDI
BasiliskHost.exe --test SNDWAVE2000-Ensemble.vst3 --tests offline --midi OUT\ens.mid --env ENSEMBLE_LANES=OUT\lanes.txt --env ENSEMBLE_DUMP_DIR=DIR
python3 ensemble/tools/sep_render.py OUT/job.txt render311 MACHINE OUT/r311 --lookahead 0; python3 ensemble/tools/cmplanes.py DIR OUT/r311 10
```

Test switches (environment):
- `ENSEMBLE_LANES`: lanes from a file.
- `ENSEMBLE_DUMP_DIR`: each lane's output, the lines sent, and the stats.
- `ENSEMBLE_CAP`, `ENSEMBLE_BUDGET`: recorders.
- `ENSEMBLE_LEAD`: latency headroom.
- `ENSEMBLE_LOG`: the engine's log.

# /citypop-ens/: the whole album on one SNDWAVE1993 Ensemble, live in the browser

williamsharkey.com/citypop-ens/ (linked from nowhere). One DOSBox Pure (wasm, in a worker) runs Windows for Workgroups
3.11 with ENSEMBLE.EXE and plays CITYPOP1993, all twelve tracks back to back (2,495 s), from one schedule: every note
goes to Windows ahead of time, stamped with the DAC sample it sounds at; between parts a lane switches preset, and
Windows builds the new sound with Sound Recorder's own menus while that lane is silent. Nothing is pre-rendered: the
AudioWorklet reads the lane card's DAC ring out of the worker's shared memory.

## Round 2: every part (sixteen lanes)

The first round fitted the album into ten lanes and left parts out. Now no part of any track is cut: up to sixteen
lanes (track 12 uses fifteen), 134 segments, 49,661 notes (99,919 note events).

What made room, and what made it fast enough:

| | |
|---|---|
| **Recorders, not lanes, are the budget** | Windows' USER heap (64 KB) holds every window: each Sound Recorder and each strip control. A sixteen-lane build (`-DNB_LANES=16`) draws its strip labels (channel, name, level, pan, recorders) itself instead of making them windows, and has no preset arrows: 7 fewer windows a strip, USER 73 % free with the strips up (60 % before). |
| **Exact pools** | `album_ens.py` gives every layer of every part as many recorders as that part plays at once on that layer: its keys (zones), chords and unison (H, U), the sustain pedal, the release tail; drum kits count a hit as 1.2 s. Then at most 10 a part (the biggest pools give first): strings, ep, kits and choir steal a voice now and then. Ambience is 1-2. |
| **Idle lanes give back** | A lane whose part is over and whose next build is 20 s off or more closes its recorders (`trim`); at every build a lane closes what its new preset does not use. |
| **Sound cache** | Every sound Sound Recorder builds is saved on R: under the hash of its recipe (source and steps, C*.WAV); a lane that needs it again, on any track, loads the file instead of building it. 28 cache hits over the album. |
| **The first track is built in the snapshot** | The page's snapshot is taken with the first track's twelve presets on their recorders (and the lanes' silent first plays over: a play in progress never finishes after a resume, and it had cost 60 % more CPU). 38 MB of machine, 6.6 MB packed: the recorders hold many copies of the same sounds, which LZMA with a 64 MB window takes almost for free (gzip: 30 MB). The worker unpacks it (LZMA SDK decoder in the wasm, 0.6 s). |
| **Fewer frames** | Windows' screen is rendered 6 times a second, only when asked for (DOSBox draws no frame in between), and the strips and the track view are drawn less often in the page (`ui 120 100`). |
| **16 s in hand** | A DAC ring of 21.8 s; the emulator keeps 16 s ahead of the speakers. The first beat is set 4 s after where the speakers are when the presets are ready, and the speakers jump to it. |

Where the time goes (native, `perf`, then a sampler in the card that names the guest module under the CPU every
emulated millisecond): the emulated CPU is 75 % of the host's work, the card's mix 13 %, the S3 drawing 5 %. Inside
Windows the CPU is idle 65 % of the time; of the rest the most is KERNEL's scheduler walking 100-odd tasks, then
ENSEMBLE, USER and GDI. Fewer recorders is the main saving; the drawing matters most in the browser.

### Results (one full album each)

| track | lanes | switches | built | building (s) | late for a switch | recorders (max) | USER free (min) | memory free (min) |
|---|---|---|---|---|---|---|---|---|
| 1 Theme: Rain on the Loft Window | 12 | 12 | 12 (in the snapshot) | - | 0 | 97 | 39 % | 20.9 MB |
| 2 Var. I: Espresso, Two Sugars | 11 | 12 | 12 | 6.8 | 2 | 100 | 37 % | 20.3 MB |
| 3 Var. II: Taxi Lights on Wet Asphalt | 11 | 11 | 9 | 5.5 | 0 | 99 | 37 % | 20.0 MB |
| 4 Var. III: Elevator to the 23rd Floor | 10 | 10 | 8 | 8.9 | 0 | 91 | 42 % | 21.0 MB |
| 5 Var. IV: Answering Machine, 1:12 a.m. | 10 | 11 | 10 | 6.3 | 0 | 91 | 40 % | 25.9 MB |
| 6 Var. V: Neon Waltz | 10 | 10 | 10 | 4.3 | 0 | 108 | 34 % | 24.1 MB |
| 7 Var. VI: Paganini Takes the Last Train | 10 | 11 | 10 | 6.1 | 0 | 116 | 31 % | 16.9 MB |
| 8 Var. VII: The Loft, Inverted | 11 | 11 | 10 | 6.3 | 0 | 127 | 26 % | 7.1 MB |
| 9 Var. VIII: Couch Fort Disco | 11 | 11 | 11 | 8.9 | 0 | 102 | 36 % | 10.5 MB |
| 10 Var. IX: Steam and Static | 9 | 9 | 8 | 5.4 | 0 | 99 | 37 % | 14.2 MB |
| 11 Var. X: Last Call at the Listening Bar | 10 | 10 | 9 | 9.6 | 0 | 109 | 34 % | 11.3 MB |
| 12 Finale: Dawn over the Bay | 15 | 16 | 13 | 8.8 | 0 | 103 | 36 % | 14.0 MB |
| **album** | | **134** | **122** (28 from the cache, 12 kept their preset) | | **2** | **127** | **26 %** | **7.1 MB** |

(Headless Chrome on the page; the native `albumrender` run of the same schedule gives the same counts.)

- **Notes:** all 99,919 note events played, none dropped. 2 notes of track 2 come late for a switch (they start before
  their part's build is done). Notes that reach the card after their stamp while Windows is busy: native 231 of
  224,376 events (worst 1.2 s), browser 53.
- **Audio:** **0 gaps** over the whole album in headless Chrome; Windows was never less than 15.5 s ahead of the speakers.
  Two earlier full runs had gaps: one in the first seconds (the music started before Windows was ahead: fixed, the
  first beat now waits 4 s), one when the test browser, at nice 10 on a machine loaded by other jobs, was given a
  third of a core for some seconds and the 8 s it had in hand ran out (the lead is now 16 s).
- **CPU, this PC** (Ryzen 7 PRO 7840U, 2023 laptop): native 1.93x real time, 0.46 of a core; browser 0.70 of a core in
  all (p95 0.97), the emulator busy a median 33 % of real time (p95 78 %).
- **Start, from Play, live on williamsharkey.com:** about 30 MB is fetched first (the machine, 18 MB, and the second
  track's sounds, 11.5 MB: they build while the first track plays, and a piece Windows has to wait for stops the
  emulator); the snapshot is unpacked and resumed at about 8 s and the first note comes at about 14 s (the speakers
  wait 4 s for Windows to get ahead). Locally, with nothing to download, the first note is at about 5 s. Starting from
  any other track, that track's sounds are fetched and its presets built first: 10-15 s more.
- **Typical laptop:** not measured. The emulator needs about a third of this PC's core on average and nearly all of it
  for seconds at a time while Windows builds; the 16 s in hand covers that here. A 2020-or-later laptop should play it
  through; one with half this single-thread speed would run at about two thirds busy and could run dry where builds
  and dense passages meet; phones are not expected to keep up.
- **Downloads:** about 55 MB in all over the album (the Rainy Loft disc 32 MB, in pieces, a track ahead).
- **Plugin:** the Ensemble plugin (now SNDWAVE1993 Ensemble, same URI and ids) with this guest: offline identical to
  render311 on CITYPOP 09 (30 s, all lanes within 9e-8), pluginval strictness 10 SUCCESS.

Screenshots: `design/citypop-ens/loft16.png` (Rainy Loft colours, sixteen strips).


## Round 1 (ten lanes)
## Pieces

| | |
|---|---|
| `ensemble/tools/album_ens.py` | the schedule (`album.ens`): per track, parts to lanes (at most ten), the switches, every note |
| `ensemble/player/AlbumPlayer.h` | the player, shared by the page (wasm) and `albumrender` (native): switches, held notes, stats |
| `ensemble/guest/ens_tail.c` | build pooling (one recorder per layer is built, Saved As, the rest load the file), lane mix, `colors 0/1` (SetSysColors, the Rainy Loft scheme), recorders closed when a preset needs fewer |
| `tools/citypop-ens-web/` | the wasm host (`ens_host.cpp`), the worker (`worker-main.js`), the worklet, data prep, snapshot, staging |
| `site/citypop-ens/` | the page: the /citypop/ night (its scene and life modules) behind one Windows window, Play/Stop, track list, Rainy Loft colours |

## Fitting the album into ten lanes

Sixteen-part tracks are cut to ten: parts that never overlap share a lane (05 phone/bell, 12 synth/bell, 02 cafe/spoon,
07 crossing/train); then the quietest ambience goes (one stays), then the doublings, then hand percussion. Left out:
01 vinyl, pad; 02 cafe; 03 synth lead; 08 choir; 09 synth; 12 harbour, rain, choir, perc, dawn. Mix gains from the
album's own mix (pads, choir and bells 2 dB down); no echo or reverb.

A lane keeps its preset when the next track uses the same one; otherwise the part goes to the lane that falls silent
earliest, and the build starts as soon as the lane's previous part has rung out.

## Switches (one full album, native `albumrender`, and headless Chrome on the live page code)

| track | switches | built in Sound Recorder | seconds building (native / browser) | notes late for a switch |
|---|---|---|---|---|
| 1 Theme: Rain on the Loft Window | 10 | 10 (before the first note) | - | 0 |
| 2 Var. I: Espresso, Two Sugars | 10 | 7 | 7.9 / 6.5 | 0 |
| 3 Var. II: Taxi Lights on Wet Asphalt | 10 | 8 | 7.6 / 6.3 | 0 |
| 4 Var. III: Elevator to the 23rd Floor | 10 | 8 | 8.2 / 6.6 | 0 |
| 5 Var. IV: Answering Machine, 1:12 a.m. | 11 | 9 | 6.1 / 5.3 | 0 |
| 6 Var. V: Neon Waltz | 10 | 9 | 7.2 / 6.0 | 0 |
| 7 Var. VI: Paganini Takes the Last Train | 11 | 8 | 8.3 / 6.9 | 0 |
| 8 Var. VII: The Loft, Inverted | 10 | 9 | 10.9 / 9.7 | 0 |
| 9 Var. VIII: Couch Fort Disco | 10 | 10 | 14.1 / 11.8 | 0 |
| 10 Var. IX: Steam and Static | 9 | 9 | 23.8 / 21.2 | 0 |
| 11 Var. X: Last Call at the Listening Bar | 10 | 10 | 10.8 / 8.4 | 0 |
| 12 Finale: Dawn over the Bay, Deprogrammed | 11 | 8 | 10.8 / 9.9 | 0 |
| **album** | **122** | **105** (17 kept the preset) | | **0** |

Every one of the 95,511 note events was played (69,194 note lines to Windows), none dropped, none held for a build: the
gaps between parts were always long enough. "Seconds building" is the sum of the track's builds (each 0.5 to 4 s).

What the switching does change, as charm rather than error: a few notes reach the card after their stamp when Windows is
busy building. Native, notes sent 0.6 s ahead: 485 of 192,719 card events late (0.25 %), the worst 1.6 s, in a
build-heavy moment. The page now sends notes 1.0 s ahead: 27 late over the whole album in the browser.

## A bug the album found

The first full run stopped switching at track 5: a lane never closed recorders when its new preset needed fewer, so by
track 4 Windows held 156 Sound Recorders (USER heap 11 %, 4.5 MB free) and builds hung. The guest now closes a lane's
surplus recorders at each build (its first, which draws the strip, stays): 97 at track 4, 22 MB free.

## Speed

This PC: AMD Ryzen 7 PRO 7840U (a 2023 laptop chip), headless Chrome 141.

- Native `albumrender`, whole album: 2.09x real time, 0.42 of a core per real-time second.
- Browser (wasm, threads), whole album: about 1.3 cores in total (mean 1.32, p95 1.69; worker, engine threads, worklet,
  canvas). The emulator's own busy share of real time: median 33 %, p95 96 %: it saturates for a second or two at
  most builds.
- Start, live from williamsharkey.com: the snapshot resumes in 1.4 s, ENSEMBLE is ready at 5.7 s, and the first
  track's presets (10 or 11 builds, the pack pieces fetched as Windows reads them) put the first note at 25 to 30 s
  after Play. About 18 MB is fetched at Play; the pack disc (28.5 MB) comes in pieces, a track ahead.

In the first full browser run (with the native run and an upload going on beside it) the emulator saturated twice for
30 to 40 s, at 2:35 into track 4 and at the end of track 7, and the 2 s the emulator kept in hand ran out: 2 s and 3 s
of audio missing, as fades. The emulator now keeps 8 s ahead of the speakers; at the first beat the speakers jump
forward to the music (keeping at least 6 s in hand), and Stop or a new track skips what is in hand, so the long lead
costs no waiting. Second full browser run, whole album: **0 audio gaps**, never less than 7.0 s in hand, 122 switches,
0 notes late for a switch, 27 card-late notes. A live run of track 5 from williamsharkey.com: 0 gaps.

A typical laptop is not measured. Judging by single-thread speed, a 2020-or-later laptop (Apple M1, Intel 11th gen)
should play it like this one; a 2017-2019 laptop (i5-8250U class, about half the single-thread speed) will put the
emulator near 70 % busy and likely run dry in the dense build-heavy moments; phones are not expected to keep up.

## Screenshots

`design/citypop-ens/loft.png` (Rainy Loft colours, track 4, headless Chrome) and `design/citypop-ens/stock.png`
(Windows' own colours, track 5, live site). The colours are Windows' own system colours (SetSysColors, as Control
Panel's Color does), switched live by the checkbox; the page frame around it is /citypop/'s palette either way.

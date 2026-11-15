# /citypop-ens/: the whole album on one SNDWAVE2000 Ensemble, live in the browser

williamsharkey.com/citypop-ens/ (linked from nowhere). One DOSBox Pure (wasm, in a worker) runs Windows for Workgroups
3.11 with ENSEMBLE.EXE: ten lanes, each lane a preset on its own Sound Recorders. The page plays CITYPOP DEPROGRAMMED,
all twelve tracks back to back (2,493 s), from one schedule: every note goes to Windows ahead of time, stamped with the
DAC sample it sounds at; between parts a lane switches preset, and Windows builds the new sound with Sound Recorder's
own menus while that lane is silent. Nothing is pre-rendered: the AudioWorklet reads the lane card's DAC ring out of the
worker's shared memory.

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
forward to the music (keeping at least 3 s in hand), and Stop or a new track skips what is in hand, so the long lead
costs no waiting. Second full browser run, whole album: **0 audio gaps**, never less than 7.0 s in hand, 122 switches,
0 notes late for a switch, 27 card-late notes. A live run of track 5 from williamsharkey.com: 0 gaps.

A typical laptop is not measured. Judging by single-thread speed, a 2020-or-later laptop (Apple M1, Intel 11th gen)
should play it like this one; a 2017-2019 laptop (i5-8250U class, about half the single-thread speed) will put the
emulator near 70 % busy and likely run dry in the dense build-heavy moments; phones are not expected to keep up.

## Screenshots

`design/citypop-ens/loft.png` (Rainy Loft colours, track 4, headless Chrome) and `design/citypop-ens/stock.png`
(Windows' own colours, track 5, live site). The colours are Windows' own system colours (SetSysColors, as Control
Panel's Color does), switched live by the checkbox; the page frame around it is /citypop/'s palette either way.

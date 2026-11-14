# Preset library builder: progress

The goal is 1000+ kept presets in packs for BASILISK 16 (3.11) and BASILISK SYNTH (XP), every one rendered through
the real emulated Windows and passing the automatic checks. The pack plan is `research/pack-plan.md`.

## Pipeline (this folder)

| Step | File | What it does |
|---|---|---|
| Sources | `analyze_sources.py` -> `data/sources.json` | Measures every NAME from the machine's own files: drive.zip (C:\WINDOWS, C:\XPSOUNDS) and library.zip (L:). It records the root (harmonic-sum pitch; a note in the name wins), note segments by onset, lead-in, decay, brightness, noisiness and role. 549 sources. |
| Categories | `catdefs.py` | Twenty scoring categories. Each has a kind (probe and phrase), descriptor ranges, tuning tolerance, pools and companion roles. |
| Packs | `packs.py` | The plan's 15 packs and their groups and counts, plus the 3 researched packs. |
| Generate | `gen.py` | `compose`: builds a DNA from a pool and puts it in tune from the measured roots (speed steps toward the register, then K; companion T relative to K). `mutate`: changes envelope, level, pan, offset, unison, harmony, swap/add/drop layer, steps (E + - R C@50X @0CP), trims, drawn Ja, velocity, and v3 W/Y. Also `retune`, `humanize` (v3 twin) and the research seeds. |
| Render | `render.py` | Runs render311 under `nice` (K at once) and analyses each render (`analyze.py`) at once. The analysis is cached by (DNA, score, tail). PIDs go in `$LIBBUILD/run/render.pids`. |
| Score | `score.py` | Hard rejects, then a score from the descriptor fit, tuning, evenness and width; also a retune hint and the loudness for G. |
| Evolve | `evolve.py` | Per target, lineages follow the plan's growth rules: hero (+ auto-root), 2 source swaps from `alternates`, the W3.11 twin, a register/character twin and a v3 twin. Round 0 renders them; rounds 1-2 mutate or retune each lineage's best and repair the failed ones. Fills are template compositions with the pack's palette. |
| Curate | `curate.py` -> `data/selection.json` | Takes the best passing candidate per lineage, heroes first. A near-duplicate (feature distance) in the same pack is rejected, and the same DNA anywhere. Each group is capped at the plan's count; v3 presets count against the v3 share. Researched packs get one preset per target. Names, tags and badges are added. |
| Finalize | `finalize.py` -> `data/library.json` | Sets G from the loudness, renders the demo phrase (tools/sndrec-demo/phrases.py kinds) through the machine, and checks it again. It re-renders when G moves 2 dB or more, then encodes the MP3 and adds the recipe (recipe_cli). |
| Review | `review.py` | Writes `Desktop/sndrec-library/review.html` and the audio. |
| Ship | `ship.py` -> `out/` | Per-edition TSVs per pack, packs.json, library.json, .vstpreset. See INTEGRATION.md. |

Work files are on the Linux side in `$LIBBUILD` (default `~/libbuild`): renders, feature cache, state and MP3s.
Nothing audio goes in git.

## Machine and renderer

- render311 and the machine are pinned copies of the BASILISK 16 local build at main 4bda617 (DNA v3 W and Y), in
  `$LIBBUILD/v3/`.
- A v2 DNA renders bit-identically to the 1.2.1 release machine (md5 of a 3-note render, checked). So one
  renderer serves the v2 presets (both editions) and the v3 W/Y presets (3.11-only for now).
- sharkey-server renders bit-identically too (same md5) when `--machine` is an absolute path. A relative path fails
  the snapshot restore ("does not fit this engine").

## Log

- 2026-11-13 14:50. Started. render311 1.2.1 was found in `~/sndrec-demo/bin`, and the Linux machine (1.2.1) in
  `~/bs311/machine3` (the release's Windows snapshot does not restore with the Linux core). Copies are in
  `~/libbuild`.
- 15:05. Coordinator: v3 W/Y usable (4bda617). Switched to pinned copies of that build. Checked that v2 output
  is identical. W/Y were added to the DNA model, a `v3` mutation was added (pads, textures, drones, lo-fi, FX,
  choir), and `humanize` makes v3 twins. v3 presets are marked 3.11-only.
- 15:10. Coordinator: genres.json, modern-favorites.json and pack-plan.md landed. The builder now follows the
  pack plan (15 packs + 3 researched packs). Kits (Kit Manager 98, the drums roles) and the v3 sequencer, glide,
  wow and grains are not built; they are in `data/v3-ideas.json`.
- 15:12. Library names: `piano_upright_c#2..6` and `bass_guitar_g#` were renamed to `..cs2..6` and `bass_guitar_gs` in
  catalog/tonal.json and library/sources. `tools/build_library.py` now refuses non-DNA-safe ids. Both discs
  already carried the s-names, because make_library*.py turn `#` into `s`. BASILISK 16's L: list and XP's are
  the same 510 names, so library presets ship to both.
- 15:25. Coordinator: local renders paused for the XP lane's 1.2.1 window. Bulk rendering moved to sharkey
  (`/root/libbuild-lane`, venv with numpy, nice, 4 jobs). The 974 cached analyses were copied there.
  PYTHONHASHSEED=0 makes the run reproducible.
- Throughput: locally about 1.1 renders/s with 7-8 jobs while other lanes loaded the PC (median 5.6 s per
  render). A probe is 4-10 s of audio, and builds of long library sources with echo take up to 35 s.
- 15:40. Scoring fixes found in the first shard: DC is the 3.x files' 8-bit offset (reject only above 0.08 of the
  RMS). Overs above the G full scale are float, not card clipping, and G removes them. Fixed-pitch layers skip
  the tuning check. The pitch class may land on an H interval (H0,7: the fifth). A note that decays before the
  hold ends had a sustain of -240 dB and was over-penalised. Drones keep their long release. `curate.py --rescore`
  re-checks every candidate from the cached analyses, so threshold changes need no new renders.
- 16:15. Coordinator: the XP window is over; at most 2 local render311 at a time. Shards 3 and 4 ran locally
  with 2 jobs; shards 0-2 and the v3 pass ran on sharkey with 3 and 1 jobs.
- 16:20. Coordinator: 15040db (N voice modes, S stacks, D, W time Wo/Wb/Wg/Wt/Wr/Wp, --bpm). Pinned in
  `$LIBBUILD/v3b`; v2 and W/Y renders are bit-identical to 4bda617's. The v3 pass (`evolve.py --v3pass`) covers
  the plan's v3 slots from the genre and favorite seeds:
  - v3-glide: Nl/Nm/Nc with g, on basses and leads
  - v3-strum: Ss over H chords
  - v3-gate: a beat gate, Ja looped by Wr, tempo-synced by Wt
  - v3-sync: the offset echo layers as Wb beat taps, replacing the tempo twins
  - humanize: Y twins

  Tempo-synced presets render with `--bpm` at the pack's tempo. All are 3.11-only.
- 17:20. Coordinator: the .vstpreset state layout is NUL-separated and ends 0xFE 0x00. Fixed and checked in
  BasiliskHost: a `G-40` preset loads in BASILISK 16 (peak 0.006 against 0.496) and in BASILISK SYNTH 1.2.1 (0.002).
  The Windows class-id string matches BasiliskHost's.
- 17:30. Main run done: 5 shards and the v3 pass. A deficit-driven fill wave (`--deficits`, 586 template targets)
  covers the pack groups still short. A repair wave (`--repair`, 105 researched targets with no passing
  lineage) restarts from each target's best candidate.
- 18:00. Final curation over all states (main shards 0-4, v3 pass, two fill halves, repair): 7521 candidates,
  4031 pass after the rescore, 1618 lineages with a keeper, and 1074 selected. Researched packs accept a fit score
  of 20 or more and reject only near-copies.
- 19:20. Finalize: the demo phrase of each preset was rendered through the machine, with G aimed at -18 LUFS and
  peaks kept between -6 and -1 dBFS. A preset was re-rendered when G moved 2 dB or more. This took 1725 renders
  (4.5 h of audio), split between local (2 jobs) and sharkey (3 jobs). 1039 kept and 35 dropped: 15 DC, 14 with
  notes not heard in the phrase, 6 still sounding at the end. All 1039 recipes round-trip.
- 19:40. XP check: my first XP copy was a pre-release zip in which the xp-form names and tada were silent
  (0/120). Switched to the released 1.2.1 and aligned on the first onset (XP renders start about 3 s late).
- 20:00. Coordinator: XP 1.2.1 has 10 ms streaming gaps (1.2.2 fixes them). The XP check now counts only silent
  takes, missing notes or layers and wrong pitch, compared against the 3.11 render's MP3 (chroma and band levels).
  All XP-badge presets are checked; failures ship 3.11-only, and every check is flagged for a re-render on 1.2.2.
- 2026-11-14 05:30. Resumed with two jobs.
  - Job A: the XP re-check on the released BASILISK SYNTH 1.2.2 (sha 16a990ae, pinned in
    C:\Users\willi\libbuild-xp122). It covers all 1007 v2 presets that ship to XP, including those held back
    after 1.2.1. It runs 3 VMs, batch_render under nice -n 10 and QEMU at BelowNormal, in chunks of 60; touch
    ~/libbuild/xp-pause to hold it. 1.2.1 results move to `xp_check_history`. No preset is removed. The
    reference is the review page's MP3 of each 3.11 render (the Linux work folder ~/libbuild had been emptied).
  - Job B: `make_discs.py`, the packs as 3.11 disc images with the owner's ratings, for the Library tab.
    `out/library.json` also carries rating, verdict and favourite.
  - tools/build_library.py: guards so a NaN pitch never reaches the manifest (empty median set in yin_f0,
    non-finite prominence, any non-finite float written as null).
- 2026-11-14 06:00-10:30. XP re-check on 1.2.2. 12 of the first 63 presets had passed on 1.2.1 and failed on
  1.2.2: spectrum 10-23 dB off the 3.11 render, notes missing. I reported them to the XP lane. Their cause: the
  machine woke with its default sound still building, and 1.2.2 took that late "built" for the DNA's build, so
  notes went to the default sound. On their 1.2.3 candidate, 11 of the 12 match 3.11 closely (chroma 0.91-1.00,
  bands 0.1-2.9 dB). Silent Orb sits about 10 dB off on every build, its own layer balance.
- The full run moved to the candidate (1 or 2 VMs, as the XP lane asked; paused twice for their windows) and
  stopped when XP development ended (BASILISK SYNTH 1.3.0 is the last XP release). 672 presets were checked on
  1.2.3c, 647 pass.
- The XP verdict in `out/library.json` (`xp_check`) is the 1.2.3c check where it ran, otherwise 1.2.1's, because
  1.2.2's results are meaningless after its regression. `xp_checks` keeps every version. 946 presets ship to XP; 93
  ship to 3.11 only (32 v3, 61 failing on XP). No preset was removed. All XP copies and scratch are deleted
  (Linux side, then fstrim).
- Job B: `out/discs311/` holds 18 discs: the 17 packs plus Kit Manager 98 with the packs lane's 39 kits as they are,
  27 for 3.11 and XP and 12 electromech kits XP-only. `DISCS.TSV` indexes them and `XP-ONLY.TSV` lists the 12 kits.
  152 favourites, from the owner's 152 keeps.

# Handoff: BASILISK, SNDWAVE1993 and CITYPOP1993 as Ruffian projects

For the Ruffian coordinator. Written 2026-11-15 by the Claude Code coordinator that has run this repo's work so far.

The owner wants three projects in this repo to become first-class Ruffian projects: hosted on Ruffian git, worked on by
a group of people and agents, shown on Build TV, with pages on ruffian.app. They also want the background agents
that are running now to keep running, and to resume this work inside the Ruffian desktop app on Windows. This document
says what exists, how the work is organised, and what Ruffian needs to support before the switch.

Nothing has been moved yet. The repo is still `github.com/williamsharkey/windows-secrets` (public, branch `main`).

## 1. The three projects

| Project | What it is | Where it lives in the repo | Live today |
|---|---|---|---|
| **SNDWAVE1993** | A free VST3/AU/CLAP synth (Windows, macOS). Inside it runs a real emulated Windows for Workgroups 3.11 (DOSBox Pure); every note is played by Microsoft Sound Recorder 3.1 (SOUNDREC.EXE, dated 8 Nov 1993). Formerly BASILISK 16, then SNDWAVE2000; renamed for 1.5. 26 sound-pack discs, 1,437 presets, Song tab, recording, kits, scales, grains, Minesweeper sequencer. | `packages/basilisk-synth-311/` (plugin, guest, tools), `packages/basilisk-synth/core/` (shared DNA engine), `packages/basilisk-synth/library/` (sounds, presets, packs, songs), `design/brand/sndwave1993/`, `tools/songrender/`, `tools/basilisk-host/` (test host), `tools/basilisk16-web/` (web edition) | williamsharkey.com/sndwave1993/ (home, `packs/` media player with 1,437 previews and 156 songs, `play/` in-browser edition). Releases on GitHub: tags `sndwave2000-v1.3.0`, `-v1.3.1`, `-v1.4.0` (latest). 1.5 in progress. |
| **CITYPOP1993** | A 12-track, 41-minute lo-fi city-pop album (theme and variations), every note rendered on SNDWAVE1993, plus its sound pack (Rainy Loft Collection) and a listening site with a high-resolution animated Onomichi night scene and Windows 3.1 player. Experiment: `citypop-ens`, the whole album played live in the browser by one multi-lane emulator. | `packages/basilisk-synth/library/albums/citypop-deprogrammed/` (scores, pack, tools; folder name kept), `site/citypop/` (page, scene/, life/) | williamsharkey.com/citypop1993/ (old /citypop/ redirects). /citypop-ens/ (unlisted experiment). |
| **BASILISK** | The original art pieces: Claude Code clients built from real Windows XP and 3.11 UI (BASILISK III, the 3.11 suite, live VM stages), plus the archived XP synth (BASILISK SYNTH 1.3.0, final). | `packages/basilisk-311/`, `packages/basilisk-xp/`, `packages/basilisk-synth/` (XP synth, archived), `puppetry/`, `site/basilisk*`, `site/xp-live*`, `site/sndrec-xp.html` | williamsharkey.com/basilisk*.html, /sndrec-xp.html; live VM stages on the owner's server. |

Brand note: the three keep their own deadpan voices (SNDWAVE1993 is sold by the fictional "Algorithmic Industries";
copy never says "fictional"). Keep them visually separate from the Ruffian brand; a plain "Built together on Ruffian"
line is fine.

## 2. How the work is organised today

Work is done by parallel Claude Code agent **lanes**, each owning a set of folders, coordinated by one coordinator
session. All run in WSL (Debian) on the owner's Windows PC. Lanes that exist now:

| Lane | Owns | State at handoff |
|---|---|---|
| 3.11 / plugin | `packages/basilisk-synth-311/`, releases | 1.5 in progress: SNDWAVE1993 rename, 1993 clock, CITYPOP1993.EXE, now building a card-game sound-breeding program. Uncommitted WIP in `guest/` and `plugin/`. |
| Library | `packages/basilisk-synth/library/` builder, previews | Idle after the 1.5 re-emit. |
| Packs | `library/packs/` (makers, box art via Blender, help, PDFs, ISOs) | Rebuilding all 26 discs for 1.5 into `out/discs-1.5`. |
| Songs | `tools/songrender/`, `library/songs/` | Done: 156 demo songs live. |
| Site | `site/sndwave1993/`, `tools/sndrec-demo/` | Idle; queued: swap home-page demos for the new video after owner review. |
| Web edition | `tools/basilisk16-web/`, `site/sndwave1993/play/` | Rebuilding on the renamed 1.5 machine with the 1993 clock. |
| Album | album scores, Rainy Loft pack | Done; idle. |
| Album UI / scene / life | `site/citypop/` | Done; idle. |
| Ensemble / multitimbral | branches `exp/multitimbral`, `exp/ensemble`, `/citypop-ens/` | Round 2 running: fit every part of every album track in one browser emulator. |
| Video | `tools/demo-video/` | Making a 2-minute infomercial-style demo (Kokoro TTS, procedural presenter, ffmpeg on the owner's Mac). Rough cut next. |

Lane rules (they came from real incidents; please make them project policy):
- Shared checkout: never `git stash`/`--autostash`; commit only your own files with explicit paths
  (`git commit -m ... -- <paths>`) and check `git show --stat HEAD` before pushing. Don't leave files staged.
  (Better: one worktree per lane pushing proposals.)
- Ask the owning lane before deleting its folders. Other projects on the same PC are off-limits.
- In WSL, delete from Linux, then `fstrim`. Disk on the PC is tight (C: about 25-30 GB free).
- Batch releases: one release per feature set; no asset republish for small fixes. The owner decides releases.
- Every note must come from a real emulated Sound Recorder: no native synthesis, no pre-rendered fakes (build-time
  renders by the same engine are allowed and labelled).
- Public-domain or CC0 sources only, with proof URLs; no real trademarks; deadpan tone.
- No REAPER for testing; use BasiliskHost and render311.
- Deploy only committed files; diff the live site before deploying.

## 3. Infrastructure and constraints

- **Builds** need: Linux (WSL), a Windows toolchain (mingw, Open Watcom for the guest), the owner's Mac for macOS
  builds and validators (pluginval, auval, clap-validator), Blender for pack art, DOSBox Pure (native and wasm),
  and, for the XP-era BASILISK pieces, the owner's XP image. Emulator renders are CPU-heavy (one core per engine).
- **Deploys** go to williamsharkey.com through the owner's own jump server. Live VM stages run on that server too.
- **Ruffian's own servers must not carry this project's builds or renders** (owner's standing rule: Ruffian needs
  them). Use separate runners.
- **Large files:** releases are 250-550 MB zips; the web edition reads a 112 MB sound library with range requests;
  the album is 94 MB of audio; the songs are 514 MB.
- **Microsoft material:** the repo and releases distribute Windows for Workgroups 3.11 files and sounds (the owner
  accepted this risk for an art project). Hosting on a company platform needs a decision (see section 6).
- **Determinism:** renders are byte-identical across Linux, Windows and macOS from one machine snapshot, so golden
  hash tests are a cheap, strong CI check.

## 4. What Ruffian needs before the switch

Priority P0 blocks the move; P1 should follow soon after.

**Keep the agents running and resume in the Ruffian desktop app (Windows)**
- P0: attach to an existing Claude Code session running in WSL on this PC (the coordinator session and its
  background subagents) from the Ruffian desktop app, without restarting it: view its transcript, send it messages,
  see each subagent lane's status, and receive their notifications. The owner will give you the session ID.
- P0: lanes keep their working folders and processes on this PC; Ruffian shows and controls them, it doesn't need
  to host them.
- P1: a lanes board (one row or window per agent: owner folders, state, last message, last commit).

**Hosting**
- P0: Ruffian git for this repo with a GitHub push mirror (GitHub stays as a read-only mirror; old release URLs must
  keep working forever).
- P0: a large-file policy: either LFS, or keep binaries out of git in an artifact store (preferred).
- P0: an artifact/release store for 1 GB files with range requests, checksums and permanent URLs, plus a GPL
  source-archive download per release tag (DOSBox Pure is GPL).
- P0: pages on ruffian.app with a per-project cross-origin isolation switch (COOP/COEP/CORP) for the wasm pages,
  files over 10 MiB served from the artifact store with range support, simple redirects, and correct types for
  `.wasm`, `.opus`, `.state`, `.jsdos`.
- P1: per-project roles (maintainer, release manager), project secrets released only to jobs (deploy keys), never
  to boxes or outside proposals.

**Builds and Build TV**
- P0: build runners that run on machines the project provides (the owner's PC and Mac first, a dedicated build box
  later), with labels (linux, windows, macos, emulator, blender), job claims and log streaming. Not on Ruffian's
  core servers.
- P1: CI status on proposals with required checks (fast tests, Windows and Mac builds, validators, cross-OS render
  hashes).
- P1: Build TV panels that runners and lanes can post to: progress bars, images (emulator screenshots), audio
  clips (renders, previews), checklists (validators), hashes. The project's Windows 3.1 look can style its panels.
  Hosts choose what goes public.

**Repo work on this side (the agents can do it once you say go)**
- Add LICENSE (GPL-2.0-or-later for SNDWAVE1993), THIRD_PARTY.md, CONTRIBUTING.md and AGENTS.md (the lane rules).
- Move hard-coded hosts and personal paths into config; make build inputs cached, hash-addressed artifacts so a
  fresh clone builds without the owner's folders or XP image.
- Add CI entry scripts (`ci/fast.sh`, `build-win.sh`, `build-mac.sh`, `validate-*.sh`, `golden.sh`, `release.sh`).

## 5. Suggested order

1. Ruffian: session attach in the desktop app; git + GitHub mirror; pages pilot (move `site/windows-secrets/` and
   `site/sndwave1993/` home and packs first; they fit today's limits).
2. This repo: licence and policy files, config cleanup.
3. Ruffian: runners and artifact store; then CI on proposals; then Build TV panels.
4. Cut over: Ruffian git becomes origin; GitHub becomes the push mirror. Releases stay on GitHub until the artifact
   store exists. williamsharkey.com stays canonical; pages move with redirects only once ruffian.app serves them fully.
5. Public Build TV shows (release nights, "a sound pack in an hour") after the owner's decisions below.

## 6. Decisions the owner still owns

1. Microsoft assets on Ruffian: ship them from Ruffian, keep them on GitHub only, or bring-your-own-image for
   anything Ruffian serves (branch `feat/byo-image` has a start).
2. Rewrite git history to drop large binaries, or only stop adding them.
3. Public or private on Ruffian; who may contribute; under which account or org.
4. Whether a public show and a "Built on Ruffian" line fit Ruffian's rule against externally facing publishing.
5. Whether the owner's PC and Mac serve as runners, and the budget for a dedicated build box.
6. Licences for contributions and for the owner's own instrument samples.

A full audit (feature table with evidence, repo findings, legal list) exists as a private page; the coordinator who
wrote it can share it on request.

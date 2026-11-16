# Handoff: moving BASILISK, SNDWAVE1993 and CITYPOP1993 to a Ruffian-owned project

For the Ruffian coordinator. Updated 2026-11-16 by the Claude Code coordinator that has run this repo so far.

**Owner on Ruffian: william@ruffian.ai.** The project should be created under that account (or an org it owns),
and the owner's other accounts should only be collaborators.

Goal: make this repo a first-class Ruffian project that several people and agents work on together, with
Ruffian git as the origin, builds shown on Build TV, and pages on ruffian.app, while the agent lanes that are
running on the owner's PC keep running and can be followed and resumed from the Ruffian desktop app.

The repo today: `github.com/williamsharkey/windows-secrets` (public, branch `main`). Nothing has been moved yet.

## 1. What is in the repo

| Project | What it is | Where | Live / released |
|---|---|---|---|
| **SNDWAVE1993** | Free VST3/AU/CLAP synth. A real Windows for Workgroups 3.11 runs inside it (DOSBox Pure); every note is played by Microsoft Sound Recorder 3.1. Steps sequencer, Song tab, Gene Pool (card-table sound breeding), recording, 26 pack discs / 1,437 presets, CITYPOP1993.EXE, a 1993 clock, zero-crossing cuts. | `packages/basilisk-synth-311/` (plugin, guest, tools), `packages/basilisk-synth/core/`, `packages/basilisk-synth/library/`, `design/brand/sndwave1993/`, `tools/songrender/`, `tools/basilisk-host/`, `tools/basilisk16-web/` | williamsharkey.com/sndwave1993/ (home, demo video, packs player with previews and 156 songs, in-browser edition). GitHub release `sndwave1993-v1.5.0` (Latest). Older: `sndwave2000-v1.3.0/1.3.1/1.4.0`. |
| **SNDWAVE1993 Ensemble** | Experimental multi-timbral version: one Windows 3.11, up to 16 MIDI channels, each with its own preset. | branch `exp/ensemble`, `design/ENSEMBLE.md`, `design/MULTITIMBRAL-EXPERIMENT.md` | GitHub pre-release `sndwave1993-ensemble-v0.1.0-beta` (Windows VST3). Live demo: williamsharkey.com/citypop-ens/ (whole album played live in the browser by one Ensemble). |
| **CITYPOP1993** | 12-track album made on SNDWAVE1993, its pack (Rainy Loft Collection) and an animated listening site. | `packages/basilisk-synth/library/albums/citypop-deprogrammed/`, `site/citypop/` (page, scene/, life/) | williamsharkey.com/citypop1993/ |
| **BASILISK** | The original art pieces: Claude Code clients built from real Windows XP and 3.11 UI, live VM stages, and the archived XP synth. | `packages/basilisk-311/`, `packages/basilisk-xp/`, `packages/basilisk-synth/`, `puppetry/`, `site/basilisk*` | williamsharkey.com/basilisk*.html; XP synth archived at its final release. |

Brand: deadpan. SNDWAVE1993 is sold by "Algorithmic Industries"; copy never calls anything fictional. Keep the
projects visually separate from the Ruffian brand; a plain "Built together on Ruffian" line is fine.

## 2. What the owner's PC has today (checked 2026-11-16)

**Ruffian desktop app** (`%LOCALAPPDATA%\Programs\Ruffian`): `Start Ruffian.exe` (the WebView2 chat app),
`ruffian.exe` (the classic terminal, also the app's terminal tabs, WSL by default), `ruf.exe` (the CLI).
Settings and sessions live in `%LOCALAPPDATA%\Ruffian\`.
- The terminal already follows running Claude Code sessions: its `rc.bash --claude-ids` lists every running
  Claude Code's session id so a tab can be restored to it. That is the hook to build "follow and resume this
  project's agents" on.
- `ruf` can already: `ruf login`, `ruf whoami`, `ruf git-setup` (then `git push/clone ruf:NAME` with the
  git.ruffian.ai credential helper), `ruf github` (the account's GitHub sign-in), `ruf remote` and
  `ruf ssh DEVICE` (remote control of the owner's other devices through the relay), `ruf --host` (let ruf work on
  this computer with approval per write or command).
- The desktop app is currently signed in with a different (personal) account. It must be signed in as
  **william@ruffian.ai** before the move (`ruf logout`, `ruf login`).

**Agent lanes** run as Claude Code background subagents inside one coordinator session in WSL (Debian) on this PC.
The owner will give you the coordinator's session id. Lanes and their state:

| Lane | Owns | State |
|---|---|---|
| Plugin (3.11) | `packages/basilisk-synth-311/`, releases | 1.5.0 released. Open: the macOS Audio Unit was not re-validated (the test Mac's AU registry needs a log-out or reboot). |
| Ensemble | `exp/ensemble`, `/citypop-ens/` | Beta released; open: macOS build, Windows CLAP. |
| Library | `packages/basilisk-synth/library/` | Re-rendering the 806 previews whose presets use cuts, on 1.5. |
| Packs | `library/packs/` (makers, Blender art, help, PDFs, ISOs) | Idle; 1.5 discs done (incl. WAULOPHONE). |
| Songs | `tools/songrender/`, `library/songs/` | Done: 156 demo songs live. |
| Site | `site/sndwave1993/`, `tools/sndrec-demo/` | Adding the Ensemble section and the new previews. |
| Web edition | `tools/basilisk16-web/`, `site/sndwave1993/play/` | Idle; 1.5 rebuild done. |
| Album, album UI, scene, life | `site/citypop/`, album folder | Done; idle. |
| Video | `tools/demo-video/` | Refreshing the live demo video on the final 1.5 build. |

Lane rules (from real incidents; please make them project policy, e.g. in an AGENTS.md):
- Shared checkout: never `git stash` or `--autostash`; commit only your own files with explicit paths
  (`git commit -m ... -- <paths>`); check `git show --stat HEAD` before pushing; don't leave files staged.
- Ask the owning lane before deleting its folders; other projects on the PC are off-limits.
- In WSL, delete from Linux; the owner compacts the disk. C: is tight (single-digit to ~20 GB free).
- Batch releases: one release per feature set; the owner decides releases.
- Every note comes from a real emulated Sound Recorder; build-time renders by the same engine are allowed and labelled.
- Public-domain or CC0 sources with proof URLs; no real trademarks; deadpan tone.
- Deploy only committed files; diff the live site before deploying.

## 3. Constraints

- **Builds are heavy and three-OS:** Linux (WSL), Windows toolchains (mingw, Open Watcom), the owner's Mac for
  macOS builds and validators (pluginval, auval, clap-validator), Blender for pack art, DOSBox Pure (native and
  wasm). Emulator renders are CPU-bound. **They must not run on Ruffian's own servers** (owner's standing rule).
- **Large files:** release zips 270-935 MB; the web edition's sound library ~112 MB with range requests; album
  audio ~94 MB; songs ~514 MB; previews ~120 MB.
- **Microsoft material:** the repo and releases distribute Windows for Workgroups 3.11 files and sounds (the owner
  accepted this for an art project). Decide how Ruffian hosts it (section 6).
- **Determinism:** renders are byte-identical across Linux, Windows and macOS, so render-hash golden tests are a
  cheap, strong CI check.

## 4. Features Ruffian needs (P0 before the move, P1 soon after)

**Following and resuming the agents from the desktop app**
- P0: adopt an existing Claude Code session running in WSL on this PC into the desktop app (the terminal already
  knows the ids), without restarting it: show its transcript, send it messages, see its background subagent lanes
  and their notifications.
- P0: a lanes board: one row per agent with owned folders, state, last message, last commit, and a send box.
- P1: lane work moves from one shared checkout to one worktree per lane that pushes proposals to Ruffian git.

**Hosting**
- P0: project under william@ruffian.ai with Ruffian git as origin and a GitHub push mirror (old GitHub release URLs
  must keep working forever). `ruf git-setup` + `git push ruf:<name>` is the starting point; all branches and tags.
- P0: large files: keep binaries out of git in an artifact store (preferred), or LFS on the git daemon.
- P0: artifact/release store for 1 GB files with range requests, checksums and permanent URLs, plus a GPL
  source-archive download per release tag (DOSBox Pure is GPL).
- P0: pages on ruffian.app with a per-project cross-origin-isolation switch (COOP/COEP/CORP) for the wasm pages,
  large files served from the artifact store with range support, redirects, correct types (`.wasm`, `.opus`,
  `.state`, `.jsdos`).
- P1: roles (maintainer, release manager), project secrets released only to jobs (deploy keys).

**Builds and Build TV**
- P0: runners on machines the project provides: the owner's PC (WSL) and Mac first, reachable through
  `ruf remote` devices, later a dedicated build box. Labels: linux, windows, macos, emulator, blender. Job claims,
  log streaming, and a priority/"quiet window" control (timing tests need an otherwise idle machine).
- P1: CI on proposals: fast tests, Windows and Mac builds, validators, cross-OS render hashes.
- P1: Build TV panels that runners and lanes post to: progress bars (render queues), images (emulator
  screenshots), audio clips (renders, previews), checklists (validators), hashes; hosts choose what goes public.

**Repo work on this side (the lanes can do it once you say go)**
- LICENSE (GPL-2.0-or-later), THIRD_PARTY.md, CONTRIBUTING.md, AGENTS.md (the lane rules).
- Move hard-coded hosts and personal paths into config; cache build inputs as hash-addressed artifacts so a fresh
  clone builds without the owner's folders or XP image.
- CI entry scripts (`ci/fast.sh`, `build-win.sh`, `build-mac.sh`, `validate-*.sh`, `golden.sh`, `release.sh`).

## 5. Suggested order

1. Sign the desktop app in as william@ruffian.ai; create the project; `ruf git-setup`; push all branches and tags;
   GitHub becomes a mirror.
2. Session adoption + lanes board in the desktop app, so the running lanes move over without a restart.
3. Pages pilot: `site/windows-secrets/`, then `site/sndwave1993/` home and packs (they fit today's limits).
4. Repo hygiene (licences, AGENTS.md, config), then runners and the artifact store, then CI, then Build TV panels.
5. Releases stay on GitHub until the artifact store exists; williamsharkey.com stays canonical until ruffian.app
   serves pages fully, then redirects.

## 6. Decisions the owner still owns

1. Microsoft assets on Ruffian: ship from Ruffian, keep on GitHub only, or bring-your-own-image for anything
   Ruffian serves (branch `feat/byo-image` has a start).
2. Rewrite git history to drop large binaries, or only stop adding them.
3. Public or private on Ruffian, and who may contribute.
4. Whether a public Build TV show and a "Built on Ruffian" line fit Ruffian's rule against externally facing
   publishing.
5. Runner hardware and budget (the owner's PC and Mac first?).
6. Licences for contributions and for the owner's own instrument samples.

Bring your own image (BYO): BASILISK SYNTH and BASILISK 16 without a Windows inside
====================================================================================

What this is
------------
- **An added build of each instrument.** The BYO build ships no Windows. On first use it builds the machine from
  install media the person brings. The shipped-image builds stay exactly as they are; the BYO build is a separate
  download (`BASILISK-SYNTH-BYO-*`, `BASILISK-16-BYO-*`).
- **The result is the same machine.** Its files and layout are what the plugin already loads: for 3.11,
  `drive.zip`, `w31.state` and `w31.conf`; for XP, `base.qcow2`, `state.mig` and `fw/`. After the build, the BYO
  plugin behaves like the shipped one.
- **The prototype** is `byo/` (Python, stdlib only):
  - `install.py`: the pipeline.
  - `media_id.py`: recognizing media.
  - `known_media.json`: the media table.
  - `answers.py`: the answer files.
  - `floppy.py`: a FAT12 floppy writer.
  - `test_byo.py`: offline tests.

  The plugin does the same steps in C++, described below under "Integration".

Status (2026-11-13)
-------------------
| | 3.11 (BASILISK 16) | XP (BASILISK SYNTH) |
|---|---|---|
| Media recognized by hash | yes: archive.org floppy set, SHA-1 and SHA-256 pinned | yes, table only: no XP media was fetched |
| Unattended install | **tested end to end**: under a minute on the build PC | written; only the QEMU launch, the floppy and the failure path were tested |
| Guest setup | tested: SYNTH.EXE, SYNHOOK.DLL, BSYNTH.DRV, INI edits | written, untested |
| Snapshot | tested: the package's `make_machine.py` | written, untested |
| Resumed and played | tested: assembly in 6.9 s; notes at 783.7, 1567.6 and 391.7 Hz, as the shipped build | no |

The 3.11 test used the WfW 3.11 floppy set from archive.org (`wfw311-disk`, the 1.44 MB set). install.py
downloaded it itself, and the SHA-1 matched both the item's metadata and `known_media.json`.

The person's side (the plugin UI hook)
--------------------------------------
The editor normally shows the guest's screen. Until a machine exists, the BYO build shows one panel in that space,
drawn in the guest's own style (3.11 dialog grey, or an XP Luna dialog).

```
+-----------------------------------------------------------------+
| BASILISK 16 needs Windows for Workgroups 3.11                   |
|                                                                 |
| This edition does not include Windows. It installs Windows from |
| your own copy, once, in about a minute.                         |
|                                                                 |
| [ Download from archive.org and install ]                       |
|                                                                 |
| or a link or file:                                              |
| [ https://...                                   ] [Browse...]   |
|                                                [ Install ]      |
|                                                                 |
| [x] I own a license for Windows for Workgroups 3.11.            |
+-----------------------------------------------------------------+
```

- **The button.** It installs from the first `mirrors` entry of the edition's preferred `known_media.json` row:
  - 3.11: `wfw311-en-144-set-zip`.
  - XP: none. XP needs the person's product key, so the XP panel has a key field and no one-click button (see
    below).
- **The link box** accepts:
  - an `https://` URL whose host is `archive.org`, `microsoft.com` or a subdomain of either (`ia*.us.archive.org`,
    `download.microsoft.com`);
  - a local file path (Browse...).

  Every redirect must stay on the allowlist (`install.allowed()`), and anything else is refused before any byte is
  fetched. For an archive.org link, the plugin first reads the item's metadata (`/metadata/<item>`), compares the
  published size and SHA-1, and only then downloads.
- **The checkbox** is required. The plugin does not judge licenses. It records the person's statement and the media
  SHA-256 in `byo.json` next to the machine.
- **The XP panel** has the same parts, plus:
  - a "Product key" field (five groups of five);
  - a note: "Setup takes 15 minutes to 3 hours, depending on your computer. You can keep working; the instrument
    is silent until it is done."

  The key goes only onto the answer floppy image, which is deleted when Setup ends. It is never logged or kept.
- **Progress.** The panel becomes a progress bar plus the current `msg`, fed by the stage lines (below). The overall
  bar weights the stages:
  - 3.11: fetch 10, identify 5, prepare 5, install 60, guest 5, snapshot 15.
  - XP: fetch 15, install 75, snapshot 10.

  The stage names are shown as a checklist: Download, Check, Unpack, Windows Setup, BASILISK, Snapshot.
- **Watching Setup.** While the install stage runs, a small live view of the guest's screen is shown. Setup draws
  its own progress, and it reassures the person that something is happening.
- **Done.** The panel goes away, and the normal first-load path runs (resume and assembly).
- **Errors.** The panel shows the message and a "Try again" button. A download resumes. For an `install-*` error, a
  "Show Setup's screen" link opens the last screenshot.

Progress lines (install.py stdout, and the plugin's internal events)
--------------------------------------------------------------------
Each line is one JSON object: `{"stage": S, "pct": 0-100, "msg": "..."}`. There are two terminal forms:

- `{"stage": "done", "out": DIR, "machine": {file: bytes}, "media_sha256": "..."}`
- `{"stage": "error", "code": C, "msg": "..."}`, with exit status 2.

| code | When | Message shown (install.py's text) |
|---|---|---|
| `url-not-allowed` | Not https, or the host or a redirect is off the allowlist | Only https links to archive.org or microsoft.com are accepted. |
| `fetch-failed` / `fetch-short` / `fetch-size` | Network trouble, a truncated download, or a size different from archive.org's listing | The download did not start / stopped at N of M bytes. Try again to resume it. |
| `hash-mismatch` | The SHA-1 differs from archive.org's published SHA-1 | The file does not match the SHA-1 archive.org publishes for it. Download it again. |
| `media-wrong` | Install media for the other edition, or not install media at all | This is not Windows for Workgroups 3.11 install media (it looks like: ...). |
| `media-unsuitable` | XP x64, or XP before SP2 | (from media_id: needs 32-bit, SP2 or later) |
| `media-incomplete` | A floppy set is missing disks | Disks are missing from the set: 3, 5. |
| `media-missing` | No file at the path | There is no file at ... |
| `key-missing` / `key-invalid` | XP without a key, or a malformed key | Windows XP Setup needs your product key. |
| `install-stalled` | Setup wrote nothing for 4 minutes | Windows Setup stopped making progress (screenshot saved). |
| `install-crashed` / `install-timeout` / `install-incomplete` | The emulator died, Setup took too long (1 h for 3.11, 4 h for XP), or files are missing | ... |
| `guest-failed` | XP: BSYNTH.CMD did not report on COM1 | XP Setup ended, but BASILISK SYNTH was not set up in it. |
| `snapshot-failed` | synth.exe never said hello | BASILISK 16 did not start in the new Windows: ... |
| `tools-missing` | The build lacks a piece | The plugin is missing ... |

Media
-----
`known_media.json` lists media by size, SHA-1 and MD5, as archive.org publishes them. For the XP Mode package, the
Wayback Machine's capture of Microsoft's own URL also gives the hashes. SHA-256 is pinned once a maintainer has
fetched a listed mirror and checked it against the published SHA-1; so far that is done for the 3.11 floppy set
only.

A file can also be accepted when it is not in the table but `media_id.py` recognizes its contents:

- an XP CD: the `WIN51*` tag files and `I386\SETUPP.INI`;
- a WfW 3.11 disk 1: `SETUP.EXE`, `SETUP.INF`, `WFWSETUP.DL_` and `KRNL386.EX_`.

The plugin then shows "Unverified media" with the SHA-256 and lets the person continue. Hash matching is for
recognition and integrity. It is not a license check.

Licensing
---------
The plugin never ships, caches for others or uploads Windows. It installs the copy the person brings, for the
person, on their computer. The checkbox text and the `license` field of each `known_media.json` row are what the
person is told. For example, XP Mode's EULA ties it to a licensed Windows 7 Professional or better, and WfW 3.11
needs a licensed copy. Whether a given archive.org item is a legitimate source is the owner's decision. The
allowlist encodes it, and it is the one place to change it.

The 3.11 pipeline (`install.py 311 MEDIA OUT`)
----------------------------------------------
1. **fetch** (for a URL): allowlist, archive.org metadata, resumable download into `OUT.media/`.
2. **identify**: SHA-1, MD5 and SHA-256, the `known_media.json` match, and the content check.
3. **prepare**: read each 1.44 MB / 1.2 MB disk image's FAT12 directly (no tools) and copy disks 1-8 into one
   folder. Setup then needs no disk swaps.
   - The archive.org set also holds 720 KB display-driver disks. Their files share names with the main set but
     differ, so they are skipped.
   - `SETUP.SHH` comes from `answers.py`.
4. **install**: the engine (DOSBox Pure with BSYN, the same core as the plugin) runs a conf whose autoexec does:
   ```
   mount c OUT.work\c
   mount d <setup files>
   setup /i /h:d:\setup.shh
   expand d:\svga256.dr_ c:\windows\system\svga256.drv   (and vddsvga.38_, vgadib.3g_)
   echo ok> c:\byodone.txt
   ```
   Progress is the growth of C: (about 15 MB in all). Setup took 17 s at `cycles=max` on the build PC.
5. **guest**:
   - SYSTEM.INI: `[drivers] Wave=bsynth.drv`, and Super VGA 1024x768 / 256 colors / small fonts, written as
     SETUP.INF's `[svga768s]` would write it.
   - PROGMAN.INI: `display.drv=svga256.drv`.
   - SYNTH.EXE, SYNHOOK.DLL and BSYNTH.DRV.
6. **snapshot**: the package's own `tools/make_machine.py`, unchanged:
   - it copies the drive and writes WIN.INI `run=` and the `[sounds]` section;
   - it zips C: with fixed dates;
   - it boots, waits for synth.exe's hello and saves `w31.state`.

   It runs from a copy of `tools/` beside a copy of `engine/*.conf.in`, with the adapter line swapped (next
   section), so a change to make_machine.py on main is picked up as is.

Findings from the test install. Each is now handled by install.py:

| Problem | What happened | Fix |
|---|---|---|
| Network-card detection | Setup's Windows part hangs DOSBox ("Setup will attempt to detect what network card you have...") even with `network = nonet`. | Setup runs with `/i` (no hardware detection). The answers name every device. |
| Display during Setup | Setup's Windows part cannot start with SVGA256.DRV ("An error occurred while trying to initialize the video adapter"). | Setup installs with `display = vga`. The Super VGA files are expanded afterwards with Setup's own EXPAND.EXE: they are KWAJ-compressed, which Python does not read. |
| Display under S3 | Microsoft's SVGA256.DRV hangs Windows on DOSBox's S3 adapter at any resolution: 1024x768, 800x600, with VDDSVGA or with *vddvga. It also hangs on Paradise. It runs on **Tseng ET4000**. | The BYO machine's `w31.conf` says `machine=svga_et4000`. The shipped machine keeps `svga_s3` with S3's own 64K-color driver, which is not on Microsoft's disks. |
| Group files | Program Manager rewrites every group file after a display change and complains that the zip-mounted C: is write-protected. | PROGMAN.INI `display.drv` is set to the new driver. |
| Missing sounds | `[dontinstall] bitmaps` also drops CHIMES, DING, RINGIN and RINGOUT.WAV (SETUP.INF `[win.bmps]`), so the recorders cannot open DING.WAV. | Bitmaps are installed. install.py checks for the four sounds. |

The XP pipeline (`install.py xp MEDIA OUT --key-file K`)
-------------------------------------------------------
1. **fetch** and **identify**: as for 3.11. The media must be 32-bit and SP2 or later; SP3 is recommended.
2. **prepare**: a fresh 64 GB qcow2, plus a 1.44 MB floppy (`floppy.py`) holding:
   - `WINNT.SIF` (answers.py: full unattended, auto-logon as Administrator, 1024x768x16, no games or MSN, the
     person's key, `[GuiRunOnce] A:\BSYNTH.CMD`);
   - `BSYNTH.CMD`;
   - `PREP.BAT` (guest/prep.bat);
   - `SYNTH.EXE` and `SRHOOK.DLL`: the binaries built in XP with tcc for the shipped machine. They are our own
     GPL code, so a BYO build carries them, and no compiler is needed in the person's XP.
3. **install**: QEMU with the plugin's own devices (Machine.cpp) plus the CD and the floppy, `-boot once=d`.
   - Text-mode Setup reads `A:\WINNT.SIF`, GUI Setup follows, and the first logon runs `BSYNTH.CMD`. That puts the
     programs in `C:\synth`, runs prep.bat (no event sounds, no screen saver, no power saving, synth.exe in Run,
     COM1 without FIFO), writes `BSYNTH-GUEST-OK` to COM1 and shuts down.
   - The floppy, which holds the key, is deleted as soon as QEMU ends.
4. **snapshot**: `packages/basilisk-synth/tools/make_machine.py` as it is (cold boot, "hi 1 xp wait", the PoIdle
   patch, migrate to `state.mig`, `qemu-img convert`).

Open points for XP:

- **The PoIdle patch** checks the bytes of the shipped kernel (`POIDLE_WAS`) and stops on a mismatch. Media with a
  different ntoskrnl build (an SP2 CD, or a localized one) need either the patch located by a pattern search, or
  the patch skipped: XP would then idle at about 75% of a core.
- **The time.** It is 1-3 hours under TCG. The plugin should use the host's accelerator for the install only (WHPX
  on Windows, HVF on macOS) and TCG for the snapshot, which must load everywhere (make_machine.py's rule).
- **Activation.** Retail and OEM media need activation within 30 days, and Microsoft's activation servers for XP
  are gone. The snapshot is always resumed from the same moment, so the guest clock is restored with it; the
  plugin still sets the clock on resume (`synth.c`). This has not been tested beyond the snapshot. Volume license
  media do not activate.
- **XP Mode** (`WindowsXPMode_en-us.exe`, Microsoft's file, mirrored on archive.org) is the keyless path: a
  sysprepped XP SP3 VHD. It needs a CAB/LZX extractor and a sysprep answer in the VHD, which is not written yet.

Where files live
----------------
- **The machine**: the same folder the downloading build uses, with `-byo` added to the machine name. It is
  `%LOCALAPPDATA%\BASILISK SYNTH\machine-byo-<n>` on Windows and `~/Library/Application Support/BASILISK
  SYNTH/machine-byo-<n>` on macOS, and the same pattern under `BASILISK 16`.
- **`byo.json`** sits beside it. It records:
  - the media SHA-256 and `known_media` id;
  - the license statement and date;
  - the plugin version that built it.
- **Scratch**: `<machine>.work`, deleted on success; kept on failure until the next try.
- **The download**: kept in `<machine>.media` until success, so a retry does not fetch it again. The person can
  choose to delete it then.
- **Rebuilds.** When a plugin update changes the guest (a new SYNTH.EXE), the BYO build re-runs the guest and
  snapshot stages from the installed C: (3.11) or the installed disk (XP). It does not install Windows again, so
  installs keep a pristine copy:
  - 3.11: `c.zip`, 15 MB;
  - XP: `installed.qcow2`, about 1.5 GB.

Integration (for the plugin lanes, after v1.2)
----------------------------------------------
**Both plugins**

1. Add a build flag, `BYO=1`. The bundle then has no machine (`Resources/machine` for 3.11; `BSYNTH_MACHINE_URL`
   for XP), and `byo/known_media.json` becomes a resource.
2. In the editor, when no machine is found and `BYO=1`, draw the panel above, not the guest's screen. Run the
   pipeline on a worker thread and feed the panel with the stage events.
3. Port to C++, stdlib-level only:
   - the allowlist check;
   - the archive.org metadata check;
   - a SHA-1/SHA-256 hasher;
   - the FAT12 reader (`media_id.Fat12`, 60 lines);
   - the FAT12 writer (`floppy.make`, XP only);
   - the INI setter (`install.ini_set`).

   Downloads use the curl the XP build already uses.

**BASILISK 16 (3.11)**

4. Run Setup with the plugin's own engine thread and core: the conf text from `install_311`, with `cycles=max`.
   Poll for `C:\BYODONE.TXT`, and use the engine's framebuffer for the live view and for the stall screenshot.
5. Write the guest files and INI edits. Zip C: with fixed dates: compression is optional, and the stored method is
   enough.
6. Make the state with the engine's `--make-state` path (what `make_machine.py` drives). The conf must say
   `machine=svga_et4000`. Write `w31.conf` with that line, so the resume uses the same adapter.
7. Load as usual. The machine folder replaces `Resources/machine`. The core DLL stays in the bundle. The library
   disc (`library.zip`, our CC0 sounds) is still shipped with the BYO build, because it is ours.

**BASILISK SYNTH (XP)**

8. In Machine.cpp, add an "install" launch: the qcow2, the CD, the floppy, `-boot once=d`, and the host
   accelerator. Wait for QEMU to exit, then check `BSYNTH-GUEST-OK` in the COM1 output.
9. Port `make_machine.py`'s steps to the existing QMP and gdbstub code: boot, hello, settle, PoIdle, migrate,
   `qemu-img convert`.
10. Carry `SYNTH.EXE` and `SRHOOK.DLL` from the shipped build as resources: the tools folder's `xp/`.

Tests
-----
- **`python3 -I test_byo.py`**: 9 offline tests (the ISO test is skipped without pycdlib). They cover:
  - the floppy round trip and overflow;
  - disk 1 recognition, a zip set, and the flatten with display-driver disks skipped and a missing disk refused;
  - the allowlist, including look-alike hosts and plain http;
  - the INI setter;
  - the known-media table.
- **The 3.11 end-to-end run**:
  ```
  install.py 311 'https://archive.org/download/wfw311-disk/Microsoft%20Windows%20for%20Workgroups%203.11%20(3.5-1.44mb).zip' OUT
  ```
  Then resume `OUT/w31.state` with `tools/bsdrv.py`, send `go` (ready after 6.9 s), apply the DNA `ding#16;R120`,
  and play three notes at 22050, 44100 and 11025 Hz. The FFT peaks were 783.7, 1567.6 and 391.7 Hz, the shipped
  build's README figures exactly.
- **XP**: a smoke test only. install_xp ran with a stand-in CD and key. The checks were:
  - QEMU accepted the command line and showed the qcow2, the CD and the floppy;
  - the floppy held WINNT.SIF, BSYNTH.CMD, PREP.BAT, SYNTH.EXE and SRHOOK.DLL;
  - when QEMU ended without the COM1 line, the run failed with `guest-failed` and the floppy was deleted.

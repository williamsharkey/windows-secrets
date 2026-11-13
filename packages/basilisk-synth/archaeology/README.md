# Sound archaeology

This folder lists the sounds inside classic Windows systems, for use as sources in BASILISK SYNTH (XP) and
BASILISK 16 (Windows for Workgroups 3.11). It covers more than `C:\WINDOWS\Media`: it also lists sounds inside
programs, drivers, installers, help files, Flash files, videos and the GS wavetable.

**No Microsoft file and no extracted audio is in git.** The catalog holds only metadata: path, place, offset, size,
sha1 and measurements. `extract.py` takes the sounds from the user's own image the first time they are needed.

## Files

| File | Contents |
|---|---|
| `catalog.csv` | **The single, deduplicated catalog.** It holds every sound in our XP and 3.11 images, merged with the 1,223 entries of `library/research/windows-sounds.json` (the prior list). |
| `extract.py` | The first-use extractor. It reads an image or a folder and writes PCM WAVs that Sound Recorder can open. |
| `sound_archaeology.py` | The scanner (`scan`) and the extraction engine (`extract`). `extract.py` calls it. |
| `merge.py` | Builds `catalog.csv` from the scans and the prior list. |
| `xp.csv`, `w311.csv` | The raw scans. Every copy has its own row, and `dup_of` points to the first copy. |
| `swfprobe.py` | A debugging aid that lists the sound tags in a Flash file. |

### `catalog.csv` columns

- `id`: the scan id, such as `xp-00263`. Entries that are only in the prior list get `prior-NNNN`.
- `status`: one of these:
  - `new`: not in the prior list.
  - `new (single instrument wave inside gm.dls ...)`: one wave from inside `gm.dls`. The prior list counts the whole of `gm.dls` as a single entry.
  - `prior`: in the prior list and found in our image.
  - `prior, not in our images`: measured or researched from other Windows versions.
  - `prior, listed as in our images but not found by this scan`: two of these are programs (`narrator.exe`, `mslwvtts.dll`), not sound data.
- `os`: `xp`, `w311` or `other`.
- `path`, `where`, `offset`, `bytes`, `sha1`: the location that `extract.py` uses.
  - `where` is one of `file`, `embedded` (a RIFF at an offset), `res TYPE/NAME`, `swf DefineSound N`, or `file dls-wave NAME`.
  - A path that contains `|` points to a member inside a `.cab`, `.msi` or `.chm` file.
- `copies`, `also_at`: byte-identical copies that were merged into the row (from dllcache, WinSxS, driver.cab, or the three 3.11 trees). `path` is the copy most likely to be on a user's disk.
- Measurements: `format`, `rate`, `bits`, `ch`, `duration`, `f0`, `note` (pitch with cents), `clarity` (autocorrelation, 0 to 1), `centroid`, `attack_ms`, `peak`, and `character` (a description generated from the measurements).
  - For DLS waves, `root_midi` and `loop` come from the `wsmp` chunk.
- `decodable`: `True` means this tool decodes the sound to PCM. It handles PCM, MS ADPCM and IMA ADPCM itself, and uses ffmpeg for TrueSpeech, MP3 and WMA.
- `sndrec_xp`, `sndrec_311`: whether Sound Recorder on each OS can open the sound as stored, or after `extract.py`.
- Prior-list fields: `category`, `tonal`, `root`, `usefulness`, `synth_class`, `dna_name`, `prior_character`, `prior_os`.
- `notes`: names and notes checked by spectrum. For example, the TAPI tones are named by their two DTMF frequencies.

## Counts

Our images:
- XP: `~/synth-build/machine-out/base.qcow2`, machine 3, sha1 `3ca3250a…d319440`.
- 3.11: `site/basilisk-31-browser/w31.jsdos`, BASILISK 16's `drive.zip` (`~/bs311/machine3`) and the golden WfW tree (`~/b311build/tree/golden`).

| OS | Kind | New | Prior, found in image | Total distinct |
|---|---|---|---|---|
| XP | WAVE (files, resources, embedded, cab/msi members, AVI audio) | 38 | 204 | 242 |
| XP | single instrument waves in `gm.dls` | 495 | (gm.dls itself: 1) | 496 |
| XP | Flash `DefineSound` (MP3, XP tour) | 142 | 0 | 142 |
| XP | WMA / WMV audio | 6 | 3 | 9 |
| XP | MIDI | 0 | 4 | 4 |
| XP | private format (`PINBALL2.MID`) | 0 | 1 | 1 |
| XP | speech voice (`sam.spd`) | 0 | 1 | 1 |
| **XP** | **all** | **681** | **214** | **895** (1,475 copies on disk) |
| 3.11 | WAVE | 3 | 6 | 9 |
| 3.11 | MIDI | 0 | 1 | 1 |
| 3.11 | FM patch table (`SB16FM.DRV`) | 1 | 0 | 1 |
| **3.11** | **all** | **4** | **7** | **11** |
| other | prior list only (other Windows versions, Plus! packs) | | 1,002 | 1,002 |

`catalog.csv` has 1,910 rows. 888 of the XP rows and 9 of the 3.11 rows decode to PCM. The ones that do not decode are:
- the MIDI files,
- `gm.dls` as a whole (its 495 waves each have their own row),
- `sam.spd`,
- `PINBALL2.MID`,
- `SB16FM.DRV`.

## The most interesting new finds for the synth

| # | Sound | Where | What it is |
|---|---|---|---|
| 1 | TAPI DTMF digits 0-9 * # A-D (16 sounds) | `system32\tapi3.dll` WAVE 601-616 | Real dual-tone keypad tones (697/770/852/941 + 1209/1336/1477/1633 Hz), 0.16-0.2 s, 8 kHz. |
| 2 | TAPI dial tone | tapi3.dll WAVE 617 | 350 + 440 Hz, 0.1 s. A loopable drone source. |
| 3 | TAPI busy tone | tapi3.dll WAVE 618 | 480 + 620 Hz, 0.1 s. Loopable. |
| 4 | TAPI ringback | tapi3.dll WAVE 620 | 440 + 480 Hz beating pair, 0.1 s. Loopable. |
| 5 | TAPI tone 621 | tapi3.dll WAVE 621 | A 1400/2060/2450/2600 Hz cluster. Metallic. |
| 6 | TAPI tone 622 | tapi3.dll WAVE 622 | 0.9 s decaying 1285/1624/3368 Hz bell-like tone. |
| 7 | RTC ringback | WinSxS `rtcdll.dll` WAVE 619 | 2.0 s, 440 + 480 Hz. Windows Messenger's voice-call ring. |
| 8 | RTC tone 617 | rtcdll.dll WAVE 617 | 1.05 s, 593/889/1778 Hz: a fifth plus an octave, swells. Pad-like. |
| 9 | RTC tone 618 | rtcdll.dll WAVE 618 | 0.4 s, 308/488/554 Hz, near E3. |
| 10 | RTC blip | rtcdll.dll WAVE 616 | 60 ms, 800 + 2400 Hz. A percussive tick. |
| 11 | clock.avi alarm beeps | `WINDOWS\clock.avi` (TrueSpeech audio stream) | 800 Hz beep once a second for 12 s. The only TrueSpeech sound on the disk. |
| 12 | On-Screen Keyboard click | `system32\osk.exe` WAVE 179 | 57 ms key click. |
| 13 | On-Screen Keyboard short click | osk.exe WAVE 180 | 31 ms tick: a hi-hat or rim source. |
| 14 | On-Screen Keyboard tone | osk.exe WAVE 182 | 0.25 s, harmonic 222/445/666 Hz (A3). A clean pluck. |
| 15 | DirectX Diagnostic test sound | `system32\dxdiagn.dll` WAVE 7000 | dxdiag's 1.6 s stereo DirectSound test sound. |
| 16 | Search Companion sound | `system32\srchui.dll` WAVE 101 | 0.17 s MS ADPCM pluck near A#3. |
| 17 | ir_begin.wav | `Driver Cache\i386\driver.cab` | The infrared transfer start sound. The prior list called it "not on the disk", but it is inside driver.cab. |
| 18 | ir_inter.wav | driver.cab | 0.86 s dark swell near A1. |
| 19 | ir_end.wav | driver.cab | 0.48 s bright burst. |
| 20 | MSN Messenger 6 newemail | `MSN9Components\msnmsgs.msi` > MsgrCore.cab | 8-bit, 1.65 s sustained tone, G2. A different file from Windows Messenger's newemail.wav. |
| 21 | MSN Messenger 6 online | msnmsgs.msi | 1.4 s sustained tone, D3. |
| 22 | MSN Messenger 6 type | msnmsgs.msi | 0.66 s soft tone, A4. |
| 23 | MSN Messenger 6 newalert | msnmsgs.msi | 0.67 s swell. |
| 24 | XP tour stings (DefineSound 3, 7, 27, 32, 38, 45) | `Help\Tours\mmTour\segment5.swf` | 1.6-2.0 s sustained-tone clips (A#3, B3, D4, A#3, C#4, E3). Audition them: some may be short narration. |
| 25 | XP tour music beds (DefineSound 46, 51-53) | segment5.swf | 8-10 s stereo music. The prior list said the XP tour music is not on the disk, but it is inside the Flash files. |
| 26 | GS single-cycle oscillators SQUAR60, SINE_52, SAW__B2A | `drivers\gm.dls` | Looped square, sine and saw waves. Use `--loop-seconds` to get a playable length. |
| 27 | GS voices CHOIR65A, POPVX71A, FMVOX66A/86A | gm.dls | Choir "aah" (root 68, long loop) and pop and FM voice waves. |
| 28 | GS bells and mallets CALLI84, VIBE_88A, GLKN285/385/585, WRMPD72A | gm.dls | Calliope, vibraphone, glockenspiel, and a warm pad (5,380-sample loop). |
| 29 | GS sound effects DOGBW60, CREAK64, SCREM64A, HELI_60, THUND64, BIRD_60, APPLS64A, O_HIT68 | gm.dls | Dog, door creak, scream, helicopter, thunder, bird, applause and orchestra hit. These are the GS SFX set as raw waves. |
| 30 | WfW 3.11 Mail new-mail sound, Hearts 401/402, SB16FM.DRV | `MSMAIL.EXE` res 1502/1031; `MSHEARTS.EXE` WAVE 401/402; `SYSTEM\SB16FM.DRV` | The first 3.11 sounds found outside `C:\WINDOWS\*.WAV`. All are 8-bit 22 kHz, so they play in 3.11 Sound Recorder as stored. SB16FM.DRV holds the OPL3 General MIDI patch table: FM instruments, not samples. |

Smaller new items:
- the WMP tour videos' WMA audio (mostly quiet; `nuskin.wmv` and `intro.wmv` measure as silence),
- 142 XP tour narration clips. They are the most voice material on the disk after Sam.

## What was searched (coverage)

| Source type | How | Result |
|---|---|---|
| Every file of every partition (NTFS, FAT; qcow2/raw, folder, zip/jsdos) | dissect, read-only | XP: 10,329 files. 3.11: 601 + 358 + 456 files. |
| Loose `.wav .mid .rmi .dls .voc .au .snd .aif .sgt .sty` | RIFF/SMF parser | No VOC, AU, AIFF or DirectMusic content exists on either image. |
| PE and NE resources of every type | pefile, own NE parser | WAVE, custom and RCDATA types are scanned. A header-less resource that looks like 8-bit PCM also gets a row; none was found. |
| RIFF / MThd / VOC / AIFF at any offset in any binary | signature scan | Finds Agent `.acs` sounds and the AVI audio. The `cdfs.sys` RIFF header template is rejected. |
| `.cab` (driver.cab, sp3.cab, pchealth) | cabextract | ir_*.wav, and the pchealth ding.wav (a copy). |
| SZDD `*.??_` | built-in expander | None on either image: the 3.11 trees have no setup files. |
| `.chm` (240), `.msi` (5) | 7-Zip | CHM: no audio. msnmsgs.msi: MSN Messenger 6 sounds and rtcdll copies. |
| `.hlp` (151) | raw signature scan | No embedded audio. |
| Flash `.swf` (7) | DefineSound parser | 142 MP3 clips. |
| WMA / WMV / ASF / MP3 | ffmpeg | 9 tracks. |
| AVI audio streams | RIFF parser | clock.avi (TrueSpeech). |
| DLS collections | wave pool parser | 495 waves with root note and loop. |
| ACM formats | own decoders | PCM, MS ADPCM and IMA ADPCM are decoded here; TrueSpeech and MP3 go through ffmpeg. |
| Speech voices | listed, not decoded | `sam.spd` is diphone data for SAPI. Get audio by having SAPI speak, inside XP. |
| FM synth drivers (3.11) | listed | `SB16FM.DRV`. Render notes through DOSBox's OPL emulation. |

The 3.11 parts that have no audio:
- SOUNDREC, MPLAYER, SND.CPL, MMSYSTEM, MIDIMAP, SB16SND.DRV, MCIWAVE and MCISEQ.
- MMSYSTEM's RCDATA resources are MCI command tables.
- SB16SND.DRV's `KENSHODATA` resource is not PCM.

## Changes from the first pass

These are the fixes made in this second pass:
- The scanner module (`sound_archaeology.py`) had never been committed. It now lives here, and the throwaway `walk.py` and `cat_file.py` were removed.
- CHM and MSI scanning is built in. The old `chmcheck.py` called a 7z wrapper that could not run.
- New scanning: WMA, WMV and ASF audio, speech voices, FM drivers, and sound files in a private format.
- `cdfs.sys` is no longer a false positive.
- A negative-pitch bug in the measurements is fixed.
- **3.11 dedupe.** The old `w311.csv` had 16 rows for 8 sounds, because the same tree was scanned twice. A scan now merges identical rows across sources (`found_in`), and the merge collapses byte-identical copies.
- **3.11 coverage.** It now covers all three 3.11 trees, so it adds TADA, CHORD, the Mail sound and the FM driver.
- **Prior-list matching.** XP's `chimes.wav` and Vista's `chimes.wav` share a path in the prior list. The match now prefers the entry that is in our image.
- **The extractor.** It now resamples for 3.11 and checks the sha1 of every sound.

## First-use extraction

```
pip install numpy pefile dissect.ntfs dissect.fat dissect.hypervisor      # plus ffmpeg, cabextract, 7z on PATH
python3 extract.py base.qcow2 --os xp   --target both --out ~/bsynth-sounds --loop-seconds 1.5 --max-seconds 30
python3 extract.py drive.zip  --os w311 --target 311 --bits 8 --out ~/b16-sounds
python3 extract.py base.qcow2 --ids picks.txt --target 311 --out ~/b16-xp-sounds    # XP sounds for BASILISK 16
```

The command takes these options:
- `--target xp`: PCM 16-bit, at the source rate and channel count. XP's Sound Recorder opens any PCM rate.
- `--target 311`: PCM mono, 8- or 16-bit (`--bits`). Sources at or below 11,025 Hz go to 11,025 Hz; all others go to 22,050 Hz. The resampling is band-limited (FFT).
- `--ids`: a file of `ID [NAME]` lines, to extract only those sounds.
- `--force`: write a sound even when its sha1 does not match. Without it, the sound is skipped, because a different Windows build is in the image.
- `--report`: write a CSV of the files written.

Each file is checked after it is written. The check covers the RIFF header, PCM format, and the channel count, bit depth and rate that the target accepts.

**Test results** (outputs went to a scratch dir and were deleted):
- **XP** (`base.qcow2`, read-only copy, `--target both`):
  - 888 of 888 decodable rows were written for each target, and 0 were skipped. 888 passed the header check for XP and 888 for 3.11.
  - The run took 63 s and wrote 104 MB (XP) and 96 MB (3.11), with WMA cut to 30 s.
  - Of 256 pitched sounds, 252 kept their measured pitch within 50 cents after resampling for 3.11. The other 4 are DTMF dual tones, where the pitch tracker picks either partial.
- **3.11** (golden tree + `drive.zip`, `--target both`):
  - 9 of 9 written for each target, all passing the header check.
  - With `--bits 8`, DING.WAV's output data is byte-for-byte the original's.
- **Error paths:**
  - A catalog sha1 that does not match is reported and skipped.
  - A sound whose file is not in the given source is reported as missing. For example, `MSMAIL.EXE` is not in `w31.jsdos`.

Not yet tested: loading the outputs in a running Sound Recorder. The header check uses the documented rules: 3.11 Sound Recorder opens 8- and 16-bit PCM at 11, 22 and 44 kHz.

## Rebuilding the catalog

```
export SA_TMP=/some/scratch SA_7Z=/path/to/7z
python3 sound_archaeology.py scan base.qcow2 --label xp --csv xp.csv            # about 10 minutes
python3 sound_archaeology.py scan w31.jsdos drive.zip golden/ --label w311 --csv w311.csv
python3 merge.py --prior ../library/research/windows-sounds.json --out catalog.csv xp.csv w311.csv
```

Licence of the tools: CC0. The sounds belong to Microsoft.

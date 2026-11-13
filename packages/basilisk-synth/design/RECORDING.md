# RECORDING: your own sounds, recorded by the real Sound Recorder (both editions)

Status: **design, for review (2026-11-13)**. Nothing here is built yet. "XP" is BASILISK SYNTH
(`packages/basilisk-synth`). "3.11" is BASILISK 16 (`packages/basilisk-synth-311`). PE2 is
`design/PRESET-ENGINE-2.md` (branch `design/preset-engine-2`).

The owner's request, in one line: a global Record button by the envelope, recording the DAW's audio input. The
real Sound Recorder's menus (Effects, Edit, record again) edit the take. You name it in Save As and it appears in
the sound picker. You can load it into one slot or all 16, and save or export it. Each strip's own Record button
records for that slot alone, which is useful for kits and layering. Keep it familiar and uncluttered.

The rule of the product does not change: **the plugin never makes or edits a sound.** The DAW's audio becomes
the emulated card's capture input. The real SOUNDREC.EXE or sndrec32.exe records it through `waveIn`, edits it
with its own menus and saves it with its own Save As. The plugin only moves bytes: audio in, and finished WAV
files out to the host disk.

---

## 1. Audio path

### 1.1 The plugin's input bus

| Option | Hosts | Verdict |
|---|---|---|
| Main stereo input on an instrument | Many hosts hide it or treat the plugin as an effect. Logic and Live give no way to feed it. | No |
| **Stereo sidechain (aux) input** | VST3 aux bus, AU input element 1, CLAP non-main port. Live 11.1+, Logic (side chain menu on instruments), Cubase, Bitwig, Studio One and FL 20+ route sidechains into instruments. | **Yes** |

- DPF already supports this: `DISTRHO_PLUGIN_NUM_INPUTS 2`, with both ports hinted `kAudioPortIsSidechain`. The
  main output stays 2 channels, so nothing changes for hosts that ignore the input.
- **Two sources, chosen in Windows:** *DAW input* (the sidechain), and *Synth output* (resampling: the plugin's
  own output fed back in, like a sound card's "Stereo Mix"). The second needs no routing, so it works in every
  host.
- **Fallback when the host cannot route audio into an instrument: Import WAV** (§2.6). It goes into Sound
  Recorder through the real File > Open.
- **No monitoring in the plugin.** You hear the source on its own DAW track. Passing the input through would
  double it.
- **Real time only.** Recording runs in live processing, both while the transport plays and while it is stopped
  (instruments are processed while stopped; the source track must be monitoring). During an offline render the
  input is ignored, and a Record already running is stopped with `recstop` (§4.3). XP's machine stays awake
  while anything records: the 4 s sleep rule waits.

### 1.2 XP: QEMU AC97 capture

```
DAW sidechain -> plugin process() -> drift-corrected ring -> pipe "bsynth-<pid>-<n>-in" (s16 48 kHz stereo)
  -> QEMU wav audiodev, input side (our patch) -> AC97 PCM-in DMA -> XP ac97 driver -> kmixer -> waveIn
  -> sndrec32.exe Record
```

- **QEMU's `wav` driver has no input voices.** Its capture is silence, so this needs a patch, which is the one
  hard dependency. About 150 lines in `audio/wavaudio.c` add `in.path=<pipe>`: the driver reads the pipe
  without blocking, and an underrun becomes silence plus a counter.
  - It means **we build QEMU ourselves** for Windows (mingw cross, as QEMU's own CI does) and macOS (universal),
    instead of shipping Stefan Weil's and Homebrew's builds.
  - Check first whether an upstream backend with input works with a private pipe on both OSes (for example `dbus`
    in p2p mode). If none does, patch.
  - Do not use dsound, coreaudio or SDL: they would take the user's real microphone and touch the host's sound
    system, which 1.2 avoids on purpose.
- **XP mixer:** set in the machine build. Record select is Line In at 0 dB, with mic boost and AGC off. QEMU's
  AC97 feeds both PCM-in and mic-in from the same backend input.
- **srhook:** nothing changes on the record path. sndrec32 calls `waveInOpen` itself. srhook already answers
  dialogs during DNA builds, but while the Recorder is visible it must let them through: Save As is the user's
  dialog. It must also not intercept `waveInOpen`.
- **Drift:** QEMU takes input on the virtual clock and the DAW gives it on its own clock. The ring uses the
  output's slow trim, capped at ±0.2 %, plus a 40 ms cushion.

### 1.3 3.11: the BSYN card gets an ADC (not the Sound Blaster)

- **Why not the Sound Blaster.** DOSBox's SB16 has no host input (DSP input commands give silence). Windows
  3.11's SB driver also allows one device at a time.
- **BSYN is ours,** so it gets one capture channel:
  - **Card (`bsynth.cpp`):** new commands `BSC_INOPEN` (rate, bits, channels), `BSC_INADD` (linear address,
    length, header), `BSC_INSTART`, `BSC_INSTOP`, `BSC_INRESET`, `BSC_INPOLL` and `BSC_INGETPOS`.
    - The card fills guest buffers with `mem_writeb_checked`, mirroring how `BSC_WRITE` reads them.
    - It converts the 48 kHz float input to 8- or 16-bit PCM at 11025, 22050 or 44100 Hz with the Hermite
      converter it already has. That is the card's ADC, not the plugin editing sound.
  - **Driver (`BSYNTH.DRV`):** exports `widMessage`: GETNUMDEVS (1), GETDEVCAPS, OPEN, CLOSE, ADDBUFFER, START,
    STOP, RESET and GETPOS. WIM_DATA callbacks come from the existing timer `drain()`. A second open returns
    `MMSYSERR_ALLOCATED`.
    - Once `waveInGetNumDevs` is 1, **SOUNDREC enables its Record button by itself.** The greyed microphone
      on all 16 strips (PROGRESS 1.2.1) wakes up.
  - **Engine (`bshm.h` v2):** an input ring (`in_ring`, `in_w`, `in_r`) beside the DAC ring. Input samples are
    stamped on the DAC clock, so on 3.11 a take's first sample is known to the host sample. A later "snap the take
    to the bar" is therefore possible, but it is not in v1.
- **Formats:**
  - SOUNDREC 3.1 records in the format of the file it has open: 8 or 16 bit, 11, 22 or 44 kHz, mono or stereo.
  - **Measure (TR4)** what format File > New gets. If it is fixed, the Rec page's *Quality* list opens a blank
    template in the chosen format (`C:\BSREC\CD.WAV`, `RADIO.WAV`, `PHONE.WAV`), and SOUNDREC records into it,
    following its own rule.
  - On XP, quality is the real File > Properties > Convert (Telephone, Radio or CD Quality). The machine's
    default record format is set to CD Quality.
- **One recording at a time** in both editions (one ADC). While one recorder records, `synth` greys every other
  Record button.

### 1.4 Length

- XP's sndrec32 stops at 60 s.
- **A sound used by the synth is at most 30 s,** the DNA's buffer rule (DNA.md 2.1), which 3.11's library also
  follows.
- So you may record up to Sound Recorder's own limit, but saving into *My recordings* refuses anything over 30 s,
  with a message: "Over 30 seconds. Trim it with Edit > Delete After Current Position." You fix it with the
  program's own command.

---

## 2. UX (recommendation: one Recorder, two views, and the strips' own Record buttons)

**Decision: a dedicated extra Sound Recorder, the Recorder. Its compact form is always on screen, and its full,
familiar form is on a Recorder tab.**

- XP: a 17th sndrec32. 3.11: an 18th SOUNDREC, because the 17th draws the envelope.
- It does not share the envelope's display. The envelope view keeps meaning one thing.
- **Opening the Recorder tab:** the compact Recorder un-assembles. Its menu bar and buttons come back, and it
  glides into the tab page as a whole Sound Recorder. Closing the tab runs the assembly in reverse.
  - This is the product's signature animation applied to recording.
  - It is also honest: one real program in two places.

### 2.1 3.11: the header (the owner's sketch)

The envelope view moves 112 px left (ENVX 262 -> 150). The Recorder's wave view takes the space it frees, with
SOUNDREC's own Record, Stop and Play buttons under it. Captions move under the views.

```
 BASILISK 16  [/\envelope__]  [~~recorder~~]  [All][W3.11][XP][Preset ........v][<][>]  Sound [........v]
              Envelope        [●] [■] [▶]     Pan <-[]-> -20  Offset <[]--> 0  Env [<][>][+][-] A/D/S <[]> <[]>
```

- Click ●: it records from the DAW input. ■ stops. ▶ plays the take.
- Click the Recorder's wave view: the Rec page opens (the same as the [Rec] tab button).
- **The Rec page** (PE2 8.2: the panel rows under the DNA row, y 580-682, 1024 x 102) holds the whole SOUNDREC.
  The keyboard strip stays below.

```
 DNA [u_vox#8>E;R300                         ]  [Main][Voices][Play][Kit][Lib][Rec]
 File  Edit  Effects  Help                                     <- the Recorder's own menu bar
 R  Recorded  [~~~~~~~wave~~~~~~~]  1.20 s  2.40 s  <|||||[]|||||||||>  [<<] [>>] [▶] [■] [●]
 Input [DAW input  v]  Quality [CD 44 kHz v]   [Save As...]  My recordings [vox         v] [Open]
 [To slot 3] [To all 16]   [Export...] [Import WAV...]   Status: Input -12 dB, 0 dropouts
```

### 2.2 XP: a seventeenth strip and a Recorder tab

- XP has no envelope in its header (the envelope editor is under the strips), so the place "near the
  envelope" is **a 17th strip, `R`, directly above the envelope editor.**
- Strips go from 34 to 32 px, which frees 32 px for it.
- It looks like the other 16 (Play, Stop, **Record**, Position, wave, Length, slider), with a grey label instead
  of a layer colour, so you know it at once.
- **XP strips keep their Record button.** Today it drops off in the assembly (srhook: "Record first, then >>,
  then <<"). From now on only << and >> drop off, and the slider shortens by 28 px to make room.

```
 15 [▶][■][●] Position: 0.00  [~~~~~~~~~]  Length: 0.38  |----[]---------|
 16 [▶][■][●] Position: 0.00  [~~~~~~~~~]  Length: 0.38  |----[]---------|
  R [▶][■][●] Position: 1.20  [~~~vox~~~]  Length: 2.40  |---------[]----|   <- the Recorder
 +- Layer 1 envelope ---------------------------------------------------------------+
```

The Recorder tab joins PE2's tab strip on the right column (id `rec`), at x 606-1016:

```
 [ Main | Voices | Playback | Kit | Library | Recorder ]
 +- Sound Recorder ---------------------------------------+
 | File  Edit  Effects  Help                              |   <- real sndrec32: menus, all five buttons
 | Position: 1.20 sec.  [~~~~~~~ wave ~~~~~~~]  Length: 2.40 sec.
 | |----------[]-------------------------------|          |
 | [<<] [>>] [ ▶ ] [ ■ ] [ ● ]                            |
 +--------------------------------------------------------+
 Input: [DAW input (sidechain) v]   -12 dB, no dropouts
 [Save As...]   [To slot 3]   [To all 16]
 +- My recordings (ListView, Details) ---------------------+
 | Name      Length   Format              Saved          |
 | vox       2.40 s   44 kHz 16-bit mono  13 Nov 14:02    |
 | clap1     0.31 s   22 kHz 8-bit mono   13 Nov 14:05    |
 +--------------------------------------------------------+
 [Open]  [Rename]  [Export...]  [Import WAV...]  [Delete]
```

- **No level meter** in either edition. Sound Recorder's own wave view draws the input while it records, and one
  status text gives the input level and dropouts, so the screen stays calm.
- **Until the tab frame exists** (PE2 phase 3), the XP Recorder tab shows as a window over the right column,
  opened from the R strip's label.

### 2.3 Editing before saving: all real

Everything runs on the Recorder with its own menus, as in 1995 and 2001:

- **Effects:** Increase or Decrease Volume, Increase or Decrease Speed, Add Echo, Reverse.
- **Edit:** Delete Before or After Current Position, Copy, Paste Insert, Paste Mix, Insert File, Mix with File.
  Insert and Mix list *My recordings* and the library too.
- **Record again:** Record at the end appends. Record at a position records there, exactly as the program does.

Nothing is translated into DNA. What you save is the file Sound Recorder wrote. After you load it into slots,
the DNA's steps work on it like on any sound.

### 2.4 Saving and naming

- **File > Save As** is the real dialog. It saves to the *My Recordings* drive (§3.2). On XP it is
  `U:` ("My Recordings", a removable disk); on 3.11 it is `R:`.
  - The guest reports `rec saved`. The host checks the file and publishes it, and the sound then appears under
    **"My recordings"** at the top of every sound list: the 3.11 Sound combo, the XP library combo, and the
    Insert and Mix lists.
  - **Autosave:** each Stop also saves the take to `~TAKE.WAV` with a real, hidden Save. An unsaved take
    therefore survives a project save (§3.3).
- **Name rules:**
  - DNA name = `u_` + the file's stem, lowercased, with every character outside `[a-z0-9_]` turned into `_`
    and runs of `_` collapsed. At most 24 characters after the prefix.
  - On 3.11 the stem is 8.3, so names made there are 8 characters at most. That is authentic and good enough.
  - `u_` is reserved: built-in and library names never start with it (`make_library` checks).
  - Lists show the name without `u_`. The DNA uses it: `u_vox#8>E;R300`.
- **Collisions:** the same name with the same SHA-1 is the same sound. The same name with different content
  brings up a real MessageBox:

  > "vox already exists (2.40 s, 13 Nov). Replace it? Projects that use the old one keep their copy."

  [Yes] replaces it. [No] saves as `vox_2`. Old versions are kept by hash (§3.1), so nothing that used them
  breaks.
- **Only PCM** (8 or 16 bit, 11/22/44 kHz, mono or stereo) is published, because both editions open that.
  - XP's Save As "Format: Change..." can choose ADPCM or 48 kHz. That is refused, with "Use File > Properties >
    Convert Now: PCM, 44 kHz".

### 2.5 Into the slots, and per-slot Record

- **[To slot N]** (N is the selected strip, or the last strip clicked) gives strip N a one-recorder layer of
  its own, with the recording as its source: `u_vox#1B3`.
  - `B` binds the layer to recorder 3 (§4.1). The recorder loads the file with its real File > Open, as every
    source does.
  - If strip N is already a bound one-recorder layer, only its source changes.
  - At 8 layers the button refuses, with "8 layers: free one first".
- **[To all 16]:** one layer `u_vox#16`. The globals are kept.
- **Insert or mix into a layer:** the existing Edit menu, Insert File or Mix with File, with *My recordings* in the
  list. These are DNA steps (`Iu_vox`, `Mu_vox`), so it is real layering.
- **Per-slot Record:** Record on strip N records into that real recorder.
  - The voice allocator first excludes recorder N (`rec start N`).
  - At position 0 it is a new take (File > New first). At any other position it is Sound Recorder's own record
    at that position.
  - On Stop, the guest saves the strip's buffer as a take, `u_take01`, `u_take02` and so on. The host publishes
    it and the guest sends `edit` with the bound layer `u_take01#1B<N>`.
  - Rename it later from the Recorder tab ([Open], then Save As). References in the current DNA follow the new
    name.
  - **In kit mode** (PE2 15), the take also gets a pad on the next free note from 36, or on the note **Learn**
    catches.
  - So a kit is made by clicking Record on strips 1 to 8.

### 2.6 Export and import

- **[Export...]** sends `rec export <name>`. The plugin opens the host's own save dialog (DPF file browser) and
  writes the exact bytes Sound Recorder saved.
- **[Import WAV...]** opens the host's open dialog.
  - The plugin converts only what Sound Recorder cannot open: float, 24-bit or other rates become 16-bit PCM at
    44.1 kHz.
  - It puts the file on the My Recordings drive under `\IMPORT\` and the guest **opens it in the Recorder with
    File > Open.**
  - You trim it with the real commands and Save As, as with a recording. Imports over 30 s are allowed in the
    Recorder, so you can cut them down.

---

## 3. Storage and recall

### 3.1 One shared folder, written only by the plugin

- **Where:** `Documents/BASILISK/My Recordings/` on both OSes. It is visible and backed up, and both editions
  share it.
- **Layout:** `<name>.wav`, plus `index.tsv` with the columns name, sha1, file, ms, format, saved and edition
  made.
- **Old versions:** `.versions/<sha1>.wav`.
- **The plugin process is the only writer.** It takes a lock file, writes to a temporary file, renames it into
  place, then rewrites the index under the same lock.
- **Emulators never write into the folder.** Many instances in many DAWs can run at once, and a DOSBox or XP
  write cache inside the shared folder would be a corruption risk.

### 3.2 What each machine sees: a My Recordings drive per instance

| | XP | 3.11 |
|---|---|---|
| Drive | `U:`, "My Recordings": a **USB stick** (`usb-storage`, FAT32 image in the instance's temp folder), hot-plugged after resume with QMP `device_add` | `R:`, a DOSBox folder mount of a per-instance folder (`mount r @RECDIR@`, as `mount d @MACHINE@` today) |
| Contents | the recordings this project needs (pinned versions) and the latest of the rest, `\MYREC.TSV` (name, path, ms, the same form as LIBRARY.TSV), `\IMPORT\` | the same, with 8.3 files (`U0001.WAV`) |
| Guest writes | Save As writes straight to it. XP's removable-disk policy is write-through. synth.exe then sends `rec saved` | Save As writes straight to it, then `rec saved` |
| Host reads | the image, read-only, with FatFs (BSD-1 licence), after `rec saved` | the folder |
| Refresh (an import, or another instance published) | Eject: synth.exe's real Safely Remove. The plugin rebuilds the image, then `device_add` again. Never while recording. Only when needed: an import, a preset that needs a missing sound, or the user opening My recordings | the plugin copies files in. The engine flushes DOSBox's directory cache (a patch: `EmptyCache` on R:) |

- **XP:** the USB controller must be in the snapshot, so it needs a machine rebuild, which is due in the next XP
  feature release anyway. A USB stick also leaves the IDE slots free for PE2 16's pack drives.
- **Fallback if hot-plugging in XP proves unreliable after resume (TR2):**
  - an IDE CD for reading, an ISO the plugin builds (as `make_library`, ported to C++);
  - an IDE disk for writing.
- **Ejecting:** a recorder's built buffer survives an eject. A rebuild waits until the drive is back (PE2 16.5).

### 3.3 Recall in DAW projects and presets

- **The state stores a hash, and by default the audio too.** For each `u_` name the DNA uses, the state stores
  `user <name> <sha1> <bytes>` plus the WAV, deflated and base64-encoded.
  - This applies only while the total stays under 8 MB. A 30 s take at 44.1 kHz 16-bit mono is 2.6 MB.
  - Above the cap, only the name and hash are stored, and the plugin log warns.
  - A setting, "Embed recordings in projects", can turn it off, for people who keep stems separately.
- **The scratch take:** the unsaved Recorder take (`~TAKE.WAV`) is embedded too, under the same cap, so closing
  the project does not lose it.
- **Loading a project:** each name resolves by hash in this order:
  1. the folder's current file;
  2. `.versions/`;
  3. the embedded copy, which is then written into the folder. It is added under its name if the name is free,
     otherwise it goes into `.versions` only, pinned for this project.
  4. If nothing is found, the layer is silent, as for any unknown name (DNA.md 2.5). The DNA keeps the name.
     Windows shows "Missing recording: vox", and the log names it.
- **Portability:**
  - `.vstpreset` files, AU presets and host presets carry the state, audio included, so they travel.
  - A bare DNA string (copied, or from the website) refers by name only. It plays on a machine that has that
    recording.
  - Factory presets never use `u_`.
- **The packs-as-discs model (PE2 16):** My Recordings is the one **writable** "pack", always inserted, never
  ejectable from the Library tab.
  - It has no `PACK.INF`, and its sounds are not part of any pack.
  - Explorer (XP) and File Manager (3.11) show it like any drive, so you can also manage files with the real shell.
    The plugin re-reads `MYREC.TSV` against the folder when the guest reports a change.

---

## 4. DNA and spec changes (DNA.md 7, "User recordings")

### 4.1 DNA

- **NAME resolution** (DNA.md 5.2) adds a third table: built-in, then library, then **user** (`u_` names).
  Origin `user` does not count towards a DNA's edition, just as the library does not
  (`core::dnaOrigins`). A `u_` DNA is therefore `w31` or `xp` by its other sounds, and plays in both editions
  when both share the folder.
- **New v3 layer gene `B`r: bind.** This layer's pool starts at recorder r (1-16).
  - Bound layers are granted first. Unbound layers then fill the free recorders in order, so their pools may skip
    a bound recorder.
  - **Core change:** pools become a 16-bit mask instead of first and count (`core/voices.cpp`, `dna3`). The
    `layer` line gains a trailing `<mask>`; old parsers read first and count.
  - A v2 machine keeps `B` as an unknown token (5.7) and ignores it, so the binding is lost and the sound is
    still right.
- No DNA token names a file, a pack or a hash. The state carries those (§3.3).

### 4.2 State keys

`user <name> <sha1> <bytes> [<deflated base64 WAV>]` (repeated), `scratch <sha1> <base64>`, and `embedrec 0|1`.

### 4.3 Wire (v3, only to a guest whose `hi 3` caps include `rec`)

| Direction | Line | Meaning |
|---|---|---|
| host -> guest | `rin <src> <rate> <ch> <peak_db>` | the input's state, at most 5 per second: `src` is `none`, `side` or `self` |
| guest -> host | `rsrc <side\|self>` | the visitor chose the input |
| guest -> host | `rec start <rec\|R>` / `rec stop <rec\|R> <ms>` | a recording runs: keep the machine awake and keep the allocator off that recorder |
| host -> guest | `recstop` | stop recording now (offline render, unload) |
| guest -> host | `rec saved <path> [take <rec>]` | Save As finished (or a take was saved). The host checks it, then publishes it |
| host -> guest | `user <name> <path> <ms> <fmt>` / `user - <name>` | a catalogue entry was added or removed on the drive |
| host -> guest | `rec refused <path> <reason>` | `long`, `format`, `name` or `full`: the guest shows the message from §1.4 or §2.4 |
| host -> guest | `rec ask <name> <ms> <date>` / guest -> host `rec answer <replace\|keep>` | the collision question |
| guest -> host | `rec export <name>` / `rec import` | open the host's file dialog |
| host -> guest | `rec open <path>` | open this file in the Recorder (after an import) |
| both | `udisk <0\|1>` | XP: the stick was ejected or plugged in |
| guest -> host | `edit <DNA>` | (v2) To slot, To all 16 and takes are plain DNA edits |

### 4.4 Tools

- `render311` and `batch_render*.py` gain `--user-dir DIR`.
- BasiliskHost and bsynth-host gain `--input WAV`, which feeds the sidechain, so recording is tested in our own
  hosts (test rule: no REAPER).

---

## 5. Risks and measurements (made first, in this order)

| # | What | Pass |
|---|---|---|
| TR1 | XP: the patched wav audiodev input, from the pipe to a sndrec32 recording of a 1 kHz sine and a click track | a correctly pitched recording (sample rate within 0.2 %), 0 dropouts in 60 s, input latency measured (expected 60-150 ms), noise floor no worse than 16-bit |
| TR2 | XP: USB stick hot-plug after a snapshot resume under TCG (plug time, 50 eject and plug cycles, Save As then FatFs read) | plug in under 5 s, no "drive not ready" dialog left open, the harvested bytes equal the guest's file. If not: the IDE fallback (§3.2) |
| TR3 | Hosts with the sidechain bus, from vendor documents, then in our hosts (`--input`), plus pluginval 10, auval and CLAP validation with the aux bus | the validators pass, and the matrix goes into the README. Hosts that cannot route are pointed to Import and Synth output |
| TR4 | 3.11: BSYN capture and `widMessage`. SOUNDREC Record enabled. The New format and the 3.1 record limit | a sample-exact take at 11, 22 and 44 kHz, 8 and 16 bit, with the take's start known on the DAC clock |
| TR5 | 3.11 GDI with an 18th SOUNDREC and the Rec page | at least 10 % free (30 recorders left 4 %) |
| TR6 | Concurrency: 4 instances (2 per edition) save and import into one folder at once, and the same name twice | an index that is never torn, no lost file, the collision question shown |
| TR7 | State size: a project with 8 MB embedded, saved, reloaded and undone in our hosts | load under 1 s more than today. Note any host that keeps states for undo |
| TR8 | Machine sleep, program change and offline render during a recording | the machine stays awake, the recording stops cleanly on `recstop`, and renders stay bit-identical on 3.11 |

The main risks, in order:

1. **Building and shipping our own QEMU** (TR1). It is new build infrastructure on two OSes.
2. **XP USB hot-plug after resume** (TR2). This edition already lost UART interrupts after a resume.
3. **Hosts that do not route audio into instruments** (TR3). Import and Synth output make sure no user is left
   without a way in.
4. **The pool mask** in the shared core. It touches the voice allocator, so it needs the full v1/v2/v3 test
   corpus.

---

## 6. Phases

The shared parts go into `core/` once, written by the 3.11 lane because it ships first:

- user store, names, hashing, embedding and resolution (`core/userstore.*`);
- `B` and the pool mask;
- the `rec` caps and lines.

**BASILISK 16, 1.3.0 (round 5).** Recording is phase R, and it sits next to PE2's phases:

| Phase | Content | After |
|---|---|---|
| R1 | TR4. Card ADC, `widMessage`, bshm v2 input ring, plugin sidechain bus, the Synth output source. **Record works on all 16 strips** (SOUNDREC's own: record, edit and play inside the strip, not yet saved as a sound) | now: independent of PE2 phase 2 |
| R2 | `core/userstore`, the `R:` mount, harvest, `user` lines, name rules, `u_` resolution, state embedding, `--user-dir`, `--input` | R1 |
| R3 | The header Recorder (18th SOUNDREC, ENVX 150) and the Rec page. To slot, To all 16, per-slot takes with `B`, Export and Import, the collision question | R2, PE2 phase 3 (tab frame) |
| R4 | Takes as kit pads, through Learn | PE2 phase 5 (kit) |
| R5 | TR3, TR5, TR6, TR7, TR8, README and help pages | before the 1.3.0 release |

**BASILISK SYNTH, the next feature release after 1.2.1.**

| Phase | Content | After |
|---|---|---|
| X0 | TR1: our own QEMU builds (Windows and macOS) with the wav-in patch. Release decision on the measurements | 1.2.1 shipped. Start now: it is the long pole |
| X1 | Machine rebuild: the USB controller, Line-In record defaults, CD Quality default, Record kept on the strips. Plugin input pipe and drift ring | X0 |
| X2 | TR2. The U: stick (FatFs image), harvest and replug. The shared `core/userstore` from R2 | X1, R2 |
| X3 | The R strip (rows 32 px), the Recorder tab (a window until PE2's tab frame), My recordings in the library browser and Insert or Mix lists, To slot, To all 16, per-slot takes, Export and Import | X2, PE2 phase 0 (streamed srhook, already in 1.2) |
| X4 | TR3, TR6, TR7, TR8 on Windows and macOS, pluginval, auval and CLAP validation, README | X3 |

**Not in the first release:**

- snapping takes to the DAW's bar (3.11 can do it exactly; later);
- a recorder input from the host's own microphone (it touches the host's sound system);
- dragging WAVs between Windows and the DAW;
- multi-track or overdub recording. Sound Recorder never had it: layering is Mix with File and layers.

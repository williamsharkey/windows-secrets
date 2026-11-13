# BASILISK SYNTH: the DNA format and the guest protocol (spec v1)

BASILISK SYNTH is an instrument plugin (VST3 on Windows and macOS, plus AU on macOS). Its sound comes from
real Windows Sound Recorders running inside an emulated Windows machine. This file is the contract between:

- the plugin (host side: VST3/AU, voice allocator, QEMU, audio capture),
- the guest program in Windows XP (`synth.exe` plus `srhook.dll`),
- the Windows 3.11 edition, which must accept the same DNA and speak the same protocol.

Anything not written here is an implementation detail. Version: `2` (section 5 lists what v2 adds; v1 strings are unchanged in meaning). Both sides announce it in `hi`.

## 1. The machine

- **Recorders:** 16 real Sound Recorder instances, numbered 0 to 15:
  - XP: `sndrec32.exe`
  - 3.11: `SOUNDREC.EXE`
- **Where the sound comes from:** the recorders play into the guest's own sound card. The emulator hands that
  audio to the plugin.
- **Plugin's role:** it does not synthesise, filter or resample any note.
  - It decides which recorder plays.
  - It sends the guest the playback rate and volume for each note.
  - It delays the captured stream by a fixed, reported latency.
- **Reference mode:** the plugin has a "reference" mode that renders the same DNA natively. It is only for A/B
  listening and is not the product.

## 2. DNA

A DNA is one line of printable ASCII, at most 1024 bytes, with no spaces. It is applied left to right, so
order matters.

Example: `ding>E/tada<<R+#4H0,12U2~9;A5R350`

```
DNA     := LAYER ( '/' LAYER )*  [ ';' GLOBAL* ]
LAYER   := SOURCE ( STEP | VOICE )*
SOURCE  := NAME                      a sound from the Windows Media folder (table below)
NAME    := [a-z0-9]+                 longest match; it always ends at the next non-[a-z0-9] character
INT     := ['-'|'+']? [0-9]+
```

### 2.1 Steps

Steps are Sound Recorder's own commands, run on that layer's buffer in order. Each step is the real menu
command, executed by the real program.

| Step | Sound Recorder command | Notes |
|---|---|---|
| `+` | Effects > Increase Volume (by 25%) | |
| `-` | Effects > Decrease Volume | |
| `>` | Effects > Increase Speed (by 100%) | half the length, an octave up |
| `<` | Effects > Decrease Speed | twice the length, an octave down |
| `E` | Effects > Add Echo | |
| `R` | Effects > Reverse | |
| `@NN` | move the position slider to NN % of the current length | 00 to 99; `@0` is the start |
| `[` | Edit > Delete Before Current Position | |
| `]` | Edit > Delete After Current Position | |
| `C` | Edit > Copy | copies the whole buffer to this layer's clipboard |
| `P` | Edit > Paste Insert | inserts the clipboard at the position |
| `X` | Edit > Paste Mix | mixes the clipboard in at the position |
| `I`NAME | Edit > Insert File... | inserts that Media sound at the position |
| `M`NAME | Edit > Mix with File... | mixes that Media sound in at the position |

Rules for steps:

- The position starts at 0 when the source is loaded. Every step except `@` leaves it where Sound Recorder
  leaves it.
- If `P` or `X` comes before any `C` in the layer, the clipboard is the layer's source as it was first
  loaded.
- **Length limit:** if a step would make the buffer longer than 30 s, it is skipped. Both sides must skip it.
- A step that Sound Recorder refuses is also skipped, for example Delete Before at position 0.

### 2.2 Voice genes

Voice genes say how that layer's recorders are played. They may appear anywhere after SOURCE, and the last one
of each kind wins.

| Gene | Meaning | Default |
|---|---|---|
| `#N` | number of recorders in this layer's pool, 1 to 16 | an even share of what is left |
| `TN` | transpose, in semitones (-48 to +48) | `T0` |
| `Ha,b,...` | harmony: each note plays one voice per interval, in semitones. `H0,12,-12` is the note plus an octave each side; `H0,4,7` is a major triad. Up to 8 intervals. | `H0` |
| `UN~C` | unison: each harmony voice becomes N voices (1 to 8), spread evenly over ±C cents (0 to 100) | `U1~0` |
| `F` | fixed pitch: the layer ignores the note number and always plays at the file's own rate | key-tracked |
| `LN` | layer level in % (0 to 400). It is multiplied into the voice volume; it is not a buffer edit. | `L100` |

### 2.3 Globals

Globals follow `;`. Within that section the letters have these meanings:

| Global | Meaning | Default |
|---|---|---|
| `AN` | attack, in ms | `A0` |
| `DN` | decay, in ms | `D0` |
| `SN` | sustain level, in % | `S100` |
| `RN` | release, in ms | `R120` |
| `BN` | pitch-bend range, in semitones | `B2` |
| `VN` | velocity sensitivity, in % (0 means every note at full volume) | `V100` |
| `KN` | root MIDI note, the one that plays at the file's own rate | `K60` |
| `GN` | output gain in dB, applied by the plugin | `G0` |

### 2.4 Sounds

Each NAME stands for a file in `C:\WINDOWS\Media\` on XP.

| NAME | File | NAME | File |
|---|---|---|---|
| chimes | chimes.wav | hwin | Windows XP Hardware Insert.wav |
| chord | chord.wav | hwout | Windows XP Hardware Remove.wav |
| ding | ding.wav | infobar | Windows XP Information Bar.wav |
| notify | notify.wav | logoff | Windows XP Logoff Sound.wav |
| recycle | recycle.wav | logon | Windows XP Logon Sound.wav |
| ringin | ringin.wav | menu | Windows XP Menu Command.wav |
| ringout | ringout.wav | minimize | Windows XP Minimize.wav |
| start | start.wav | xpnotify | Windows XP Notify.wav |
| tada | tada.wav | popup | Windows XP Pop-up Blocked.wav |
| balloon | Windows XP Balloon.wav | print | Windows XP Print complete.wav |
| batcrit | Windows XP Battery Critical.wav | xprecycle | Windows XP Recycle.wav |
| batlow | Windows XP Battery Low.wav | restore | Windows XP Restore.wav |
| critstop | Windows XP Critical Stop.wav | xpringin | Windows XP Ringin.wav |
| default | Windows XP Default.wav | xpringout | Windows XP Ringout.wav |
| xpding | Windows XP Ding.wav | shutdown | Windows XP Shutdown.wav |
| error | Windows XP Error.wav | startup | Windows XP Startup.wav |
| exclaim | Windows XP Exclamation.wav | xpstart | Windows XP Start.wav |
| hwfail | Windows XP Hardware Fail.wav | | |

**One name, one file, in both editions** (from BASILISK SYNTH 1.2.1 and BASILISK 16 1.2.1). Both editions carry
every file, so a DNA sounds the same in both.

- `chimes`, `chord`, `ding` and `tada` are the **Windows 3.x recordings**: 3.11's CHIMES.WAV and DING.WAV, and
  3.1's CHORD.WAV and TADA.WAV (3.11's disks dropped those two).
- XP's own copies of those four are different recordings, newer, 16-bit stereo (measured: cross-correlation 0.19 to
  0.48 against the 3.x files). They are `chimesxp`, `chordxp`, `dingxp` and `tadaxp` in a DNA, and are shown as
  `chimes-xp`, `chord-xp`, `ding-xp` and `tada-xp` in the readable recipe and on the website. The DNA cannot use
  `-` there, because `-` is the Decrease Volume step.
- `ringin` and `ringout` are byte-identical in Windows 3.11 and XP (same SHA-1), so each is one file with no xp form.
- Every other name in the table above is an XP-only file and keeps its name (`xpding` is "Windows XP Ding.wav").

| NAME | File (XP: C:\WINDOWS\Media\...) | File (3.11) |
|---|---|---|
| chimes chord ding tada | `W31\CHIMES.WAV`, `W31\CHORD.WAV`, `W31\DING.WAV`, `W31\TADA.WAV` (the 3.x files as they are) | `C:\WINDOWS\CHIMES.WAV` ... `TADA.WAV` |
| chimesxp chordxp dingxp tadaxp | `chimes.wav`, `chord.wav`, `ding.wav`, `tada.wav` | `C:\XPSOUNDS\X35.WAV` ... `X38.WAV` |
| ringin ringout | `ringin.wav`, `ringout.wav` | `C:\WINDOWS\RINGIN.WAV`, `RINGOUT.WAV` (the same bytes) |
| every other name | its XP file | `C:\XPSOUNDS\X`*nn*`.WAV`: XP's file converted to PCM that SOUNDREC opens (8 or 16 bit, 11/22/44 kHz); *nn* is the name's index |

`core/dna.cpp` holds the tables (`kSoundNames`, `kSoundFilesXP`, `kSoundFiles311`). Indices 0-34 are the names
above in table order, and 35-38 are `chimesxp chordxp dingxp tadaxp`. New names are only ever appended. The old
3.11 fallback (an unknown name played DING) is gone. `core::displayName` and `core::dnaName` convert between
`dingxp` and `ding-xp`.

**Migration.** Up to BASILISK SYNTH 1.2.0, XP's bare `chimes chord ding tada` meant XP's own files. 1.2.1 stores
its version in the plugin state (key `ver`). A state without it, from XP's plugin, has those four names renamed to
their xp forms when it loads (`core::migrateXp120`, for layer sources and `I`/`M` sounds), so it sounds as it did.
XP's factory presets are written with the xp names. BASILISK 16's states need no change: its bare names were
always the 3.x files.

**Edition metadata and filters.** Each name has an origin: *3.x* (`chimes chord ding tada`), *both* (`ringin
ringout`), *XP* (the xp forms and every XP-only name) or *library* (the disc, 5.5). A DNA's origins are those of
every layer source and every `I`/`M` sound (`core::dnaOrigins`). Its **edition** is `xp` when it uses any XP file,
and `w31` otherwise (`core::dnaEdition`); library sounds do not count. It is derived from the DNA, never stored, so
it cannot disagree with the sound. Both editions' preset browsers have the filters **[All] [W3.11] [XP]**, which
show all presets, the `w31` ones, or the `xp` ones.

### 2.5 Parsing

- **Errors are skipped:**
  - an unknown NAME, which makes the whole layer silent and empty;
  - an unknown character, which is skipped;
  - a number out of range, which is clamped.
- **Limits:** at most 8 layers and 64 steps per layer.
- **Pool sizes:** fixed `#N` values are granted in layer order, each clamped to between 1 and what is left minus
  one recorder for every non-empty layer after it and every earlier layer without `#`. Layers without `#` then
  split what is left evenly, the earlier layers taking the remainder. So every non-empty layer gets at least one
  recorder (8 layers always fit in 16), e.g. `ding/chord#16` gives ding recorder 0 and chord recorders 1 to 15.
- **Canonical form:** the plugin rewrites a DNA to its canonical form. That is the same text with unknown
  characters removed and numbers written without a `+`. The canonical form is what is stored in presets and
  shown in the UI.
- **Size of the space:** 35 sources × 13 kinds of step, in any order, up to 64 steps per layer, × up to 8
  layers, × the voice genes. That is far beyond millions of distinct sounds.

## 3. Pitch inside XP

XP's AC97 driver does not implement `waveOutSetPlaybackRate` or `waveOutSetPitch`; both return
`MMSYSERR_NOTSUPPORTED`. It does accept `waveOutOpen` at any PCM rate, because the kernel mixer (kmixer)
resamples, and it supports per-handle `waveOutSetVolume`.

So the guest's `srhook.dll` is loaded into every Sound Recorder and patches its import of `winmm!waveOutOpen`:

- When the recorder opens the sound card to play, the requested `nSamplesPerSec` and `nAvgBytesPerSec` are
  multiplied by that recorder's current pitch ratio.
- Sound Recorder's buffer, position display and wave display are unchanged: the same samples, consumed faster
  or slower.
- The cost is one integer multiply per note, and kmixer's resampler does the rest.

The host sends the rate in Hz directly:

```
rate = layer_rate * 2^((note - K + T + harmony + bend) / 12 + detune_cents / 1200)
```

It is clamped to the range 2000–192000 Hz. Notes outside that range sound at the clamp.

## 4. The guest link

- **Transport:** XP's COM1, an emulated 16550A UART. QEMU connects it to a private local socket owned by the
  plugin.
- **Format:** 7-bit ASCII lines ending in `\n`; a `\r` before the `\n` is ignored. Fields are separated by one
  space. Numbers are decimal.
- **Unknown lines** are ignored by both sides.
- **3.11:** the same lines travel over that machine's COM1.

### Host → guest

| Line | Meaning |
|---|---|
| `hi 1` | Hello. The guest answers `hi 1 <edition> <state>`, where state is `wait` (the snapshot, not yet assembled) or `ready`. |
| `go` | Run the assembly animation now. The guest answers `ready` when the synth is whole. The guest may still accept `on` before it is whole. |
| `dna <DNA>` | Rebuild every layer with Sound Recorder's commands. The guest answers `layer <i> <first> <count> <rate> <frames>` once per layer, then `built <ms>`. Here first and count are the layer's recorders, and rate is the layer file's sample rate. Notes that arrive while it is building are dropped. |
| `on <rec> <rate> <vol>` | Recorder rec (0 to 15) plays from the start of its buffer at rate Hz. vol is the per-voice peak volume, 0 to 65535. A recorder that is already playing is stopped and restarted. |
| `env <a> <d> <s> <r>` | Envelope times in ms and sustain in %. The guest's hook ramps each voice's waveOut volume through it, in about 10 ms steps. |
| `off <rec>` | Release: the volume ramps to 0 over the release time, then the recorder stops. |
| `cut <rec>` | Stop at once, after a 5 ms ramp. Used when a voice is stolen. |
| `panic` | Every recorder stops. |
| `sel <i>` | Show layer i in the XP editor panels. |
| `time Y M D h m s` | Set the guest clock (local time), sent after a resume because the snapshot's clock is stale. |

### Guest → host

| Line | Meaning |
|---|---|
| `hi 1 xp <state>` | The answer to `hi`. |
| `ready` | Assembly finished. |
| `layer ...` and `built ...` | See `dna` above. |
| `end <rec>` | Recorder rec reached the end of its buffer and stopped on its own. |
| `edit <DNA>` | The visitor changed the DNA from inside XP: an Effects menu, a sound pick or a voice control. The host adopts it as the plugin's DNA, which counts as a parameter change. It does not echo a `dna` line back; the guest has already rebuilt. |
| `log <text>` | Diagnostics, written to the plugin's log. |

### Host-side rules

- **Voice allocation:**
  - Each voice of a note takes a recorder from its layer's pool.
  - It takes the free one with the oldest finish. If none is free, it takes the oldest playing one, which is
    first stopped with `cut`.
- **Timing:**
  - The plugin sends `on` as soon as the audio callback sees the note.
  - Every line costs a few hundred microseconds on the link.
  - The plugin reports a fixed latency to the host and delays the captured XP audio by that latency minus the
    measured trigger time, so notes line up in the DAW.

## 5. DNA v2 (round 3): layering, offsets, pan, drawn envelopes, macros, collages, libraries

v2 only adds; every v1 string means exactly what it meant before. Both sides announce `hi 2` / `hi 2 <edition>
<state>` once they speak v2; a v1 peer simply ignores what it does not know (DNA.md 2.5: unknown characters are
skipped), so a v2 DNA on a v1 machine plays as its v1 subset.

### 5.1 More layering: up to 6 recorders per note

A "sound" is still the whole DNA; each layer is one part of it. A note sounds every layer at once (each layer: one
voice per harmony interval per unison voice, from its own pool), so one note can sound 1 to 16 recorders. The new
genes make layers independent parts rather than copies:

| Gene | Meaning | Range | Default |
|---|---|---|---|
| `O`N | start offset: this layer starts N ms after the note | 0..4000 | `O0` |
| `Q`N | pan, -100 (left) .. 0 .. 100 (right); applied as the voice's left/right volume, never baked into the buffer | -100..100 | `Q0` |
| `L`N | (v1) level %; never baked in | 0..400 | `L100` |
| `Ja`t,l.t,l... | amplitude envelope: up to 8 breakpoints, time ms from the voice's start (after its offset) and level 0..100 %. Linear between points; the last level holds while the key is held; then the global release R ramps to 0. A layer with `Ja` ignores the global A, D and S. | t 0..20000 | none |
| `Jp`t,l.t,l... | pan envelope, breakpoints as above with l = -100..100, added to `Q` (clamped) | | none |

Breakpoint times must not decrease (a smaller one is raised to the previous); more than 8 points: the rest are
ignored. Canonical form: `Ja0,0.30,100.400,60` (no `+` signs, no repeated points).

### 5.2 Positions, collages and library sounds

| Step | Meaning |
|---|---|
| `@t`N | move the position slider to N ms (clamped to the length); v1 `@NN` (percent) stays |
| `I`NAME, `M`NAME | (v1) Insert File / Mix with File at the position; NAME may now be a library sound |

NAME is now `[a-z0-9_]+` (v1 names never contain `_`). Resolution: the edition's built-in sound table (2.4) first,
then the library catalogue of the machine's library disc (5.5). Unknown names: as v1 (layer silent / step skipped).
Collages are just steps: `tada@t300Mding@t900Ichimes>` loads tada, mixes ding in at 300 ms, inserts chimes at
900 ms, then doubles the speed of the whole result.

### 5.3 Macros: four per sound, automatable

Globals (after `;`) gain lowercase `m` tokens:

| Token | Meaning |
|---|---|
| `m`K`=`V | macro K (1..4) is at V % (0..100); the plugin's "Macro K" parameter (automatable) |
| `m`K`L`P`min,max` | macro K moves parameter P of layer L (1..8, or 0 = every layer) linearly from min (macro 0 %) to max (100 %) |

P is one of: `O` offset ms, `Q` pan, `L` level %, `T` transpose (semitones, rounded), `C` unison spread cents,
`Z` envelope time scale % (100 = as written; scales every `Ja`/`Jp` time), `N` repeat count of the layer's last
step (0..8; changes the buffer, so the guest rebuilds that layer - the host waits 300 ms after the last change).
Any number of mappings; several on one parameter add up (each contributes its value minus its min, the first one
its min). A mapped value replaces the written gene while the macro is mapped. Example:
`chord#8/ding>E#8O120Q40;m1=0m11Z50,300m12Q-100,100` - macro 1 slows chord's envelope and swings ding's pan.

### 5.4 Wire additions (guest link)

Host -> guest:

| Line | Meaning |
|---|---|
| `hi 2` | as `hi 1`, announcing v2 |
| `on <rec> <rate> <vol> [<pan> [<delay_ms> [<layer>]]]` | optional trailing fields; old parsers read the first three. pan -100..100 (default 0); delay_ms: start this many ms later (an edition may also let the host do the waiting and send 0); layer: which layer's envelope applies (default: the recorder's layer) |
| `lenv <layer> <a\|p> <t,l.t,l...>` | the effective envelope of a layer after macros (`-` = none). Sent after each `dna` and whenever a macro changes one; the guest uses the latest. |
| `lib <path>` | (optional) the library disc was (re)inserted at <path>; the guest rereads its catalogue |
| `vis <0\|1>` | (optional) 1 (default): after the assembly, builds are shown step by step (each command is picked from the recorder's own menu, which pops up on its strip); 0: builds run unseen and faster (batch renders) |

Guest -> host: `edit` carries v2 DNA when the visitor edits envelopes, offsets, pan or macros in Windows;
`lib <n> <path>` (optional) reports a catalogue of n sounds read from the disc at <path>.

**The keyboard strip (both editions):** a piano keyboard, a mod wheel and a pitch bend built from real Windows
controls along the bottom of the synth. It plays through the host (the same voice allocator as MIDI) and shows what
the host plays.

| Direction | Line | Meaning |
|---|---|---|
| guest -> host | `key <note> <vel>` | the visitor played a key in Windows (mouse, or the computer keyboard): a note-on, vel 1..127; vel 0 = note-off |
| guest -> host | `cc <n> <v>` | a controller moved in Windows; the mod wheel is `cc 1 <0..127>` |
| guest -> host | `bend <v>` | the pitch bend in Windows, -8192..8191 (0 = centre; it springs back to 0 when let go) |
| host -> guest | `show <note> <vel>` | display only: an incoming MIDI note holds its key down (vel 0 lets it up) |
| host -> guest | `cc 1 <v>`, `bend <v>` | display only: the wheels follow incoming MIDI |

Host rules: display lines are never echoed back. CC1 (from MIDI or from Windows) adds to Macro 1:
effective macro 1 = clamp(Macro 1 parameter + CC1 * 100 / 127, 0, 100), so a DNA gives the mod wheel a job with
`m1...` mappings (a mapped `N` is not rebuilt from the wheel; it follows the parameter only). Pitch bend uses the
DNA's B range. Hold (latch) and the computer-keyboard toggle (a w s e d f t g y h u j k = C..C, z / x = octave down /
up) live in Windows: with Hold on, Windows sends the note-offs when Hold is released.

### 5.5 The library disc

Extra sounds and the preset library ride on a disc image the plugin inserts after the machine resumes (XP: an
ISO 9660 + Joliet image in the virtual CD drive, QMP `blockdev-change-medium`; 3.11: its own extra drive). Layout:

```
\LIBRARY.TSV          one line per sound:  name <TAB> category <TAB> path-on-disc <TAB> seconds <TAB> source/licence
\PRESETS.TSV          one line per preset: category <TAB> name <TAB> DNA
\<category>\<name>.WAV
```

Names are unique across the disc; categories are free text (`Bells`, `Voices`, `Machines`, ...). The same
PRESETS.TSV feeds the plugin's program list ("Category: Name") and the browser inside Windows.

### 5.6 Batch rendering

`tools/batch_render.py JOBS.json --plugin <bundle> --parallel K` renders DNA + MIDI score -> WAV through the real
machine (a VST3 host per job, the plugin's own VM). Jobs: `[{"dna": "...", "score": "t:note:vel:dur,...",
"out": "x.wav", "seconds": 4}]`. Rendering is real time per VM (the emulated sound card runs on the virtual clock);
throughput comes from K VMs in parallel (default: cores / 2, at most 6 on this PC).

### 5.7 Forward compatibility (unknown tokens are kept)

A parser keeps what it cannot read, so saving a later version's DNA does not lose it:

- **In a layer:** an unknown uppercase letter followed by lowercase subkeys, digits, `.`, `,` and `~` is one token.
  It is kept verbatim, in place, and written back; it has no effect.
- **In the globals:** an unknown letter followed by the same characters (but not `m`, which always starts a macro)
  is kept the same way.
- **A macro token this version cannot read** (`m`K outside 1..4, a layer outside 0..8, a parameter letter outside
  `O Q L T C Z N`) is consumed whole (K, `=` or L and P, then digits `, . ~ -`) and kept verbatim. Its letters are
  never read again as globals: `m11S50` does not set sustain.
- Guests skip unknown characters as before; their globals react only to `A D S R B V K G`.

Checked with the preset-engine-2 fuzz test (20,000 mixed v2/v3 strings): the v2 meaning is unchanged and every v3
token survives a save.

## 6. DNA v3 (Preset Engine 2): additive tokens

DNA v3 is specified in `design/PRESET-ENGINE-2.md` (branch `design/preset-engine-2`), sections 2 and 3. Its code
is in `core/` as its own files: `dna3.*` (the tokens: `parse3`, `canonical3`, `strip3`, `applyMacros3`),
`engine3.*` (windows, voice modes, stacking, zones, grains, the mine grid, kit pads, the v3 wire) and `recipe.*`
(the DNA in words). Those files read v2 through `dna.cpp`/`dna.h` and do not change them.

- v3 only adds:
  - layer tokens start with `W N S Y V Z G`;
  - global tokens start with `q`, `x` or `k`;
  - v3 macro parameters are `W E Y P I X U F H J`.

  Token boundaries are 5.7's, so every v1/v2 string keeps its meaning and every v3 token survives a v2 save.
- Proof: `core/test_v3.sh` checks 20,000 random mixed v2/v3 strings against this core, plus the recipe round trips.
- The v3 wire (`hi 3 <edition> <state> <caps>`, `on` with a window, `rate`, `lmod`, `lgrain`, `desk`, `choke`,
  `kit`, `tab`, ...) is sent only to a guest that answered `hi 3`, and only for the features in its caps.

## Appendix: the Windows 3.11 edition (BASILISK 16, packages/basilisk-synth-311)

The DNA, pools, voice allocator, parameters and preset state are the same code (`core/`), so a DNA or a preset
file from one edition plays in the other. The differences are in the machine.

- **Sounds (from 1.2.1):** one name, one file, as in 2.4. `chimes chord ding tada ringin ringout` are its own files
  (CHORD and TADA from Windows 3.1). The xp forms and every XP-only name play XP's files, converted to PCM in
  `C:\XPSOUNDS`. Before 1.2.1, every XP-only name played DING.
- **Recorders:** 16 SOUNDREC.EXE. Its menus have the same commands as §2.1:
  - Copy, Paste Insert and Paste Mix
  - Insert File and Mix with File
  - Delete Before / After
  - the six Effects
- **Sound card:**
  - Windows 3.11's SB16 driver plays one sound at a time.
  - So the emulator (DOSBox Pure) has an extra card: BSYN, 32 wave voices.
  - Its Win16 driver BSYNTH.DRV opens one voice per waveOutOpen.
  - Each voice plays the PCM Sound Recorder hands to waveOutWrite through its own 4-point Hermite rate converter into a 48 kHz DAC. The plugin takes that DAC.
- **Pitch (§3):**
  - The `on` rate is the voice's playback rate on the card: the same idea as XP's `nSamplesPerSec` hook, done by the card.
  - waveOutSetPlaybackRate is also implemented by the driver.
- **Transport (§4):** the same lines, carried in the card's mailbox ports (0x2C0–0x2C5) instead of COM1.
  - Each host line may carry an event id with a DAC sample number.
  - The guest arms the voice it is about to Play or Stop with that id.
  - The card then starts it, or fades it, exactly at that sample.
  - So 3.11 notes start sample-accurately, at a fixed latency of 2560 samples at 48 kHz.
- **Envelope:** `env` sets the card's per-voice ADSR. `off` and `cut` fade over R ms and 5 ms on the card.

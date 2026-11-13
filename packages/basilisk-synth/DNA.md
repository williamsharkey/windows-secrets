# BASILISK SYNTH: the DNA format and the guest protocol (spec v1)

BASILISK SYNTH is an instrument plugin (VST3 on Windows and macOS, plus AU on macOS). Its sound comes from
real Windows Sound Recorders running inside an emulated Windows machine. This file is the contract between:

- the plugin (host side: VST3/AU, voice allocator, QEMU, audio capture),
- the guest program in Windows XP (`synth.exe` plus `srhook.dll`),
- the Windows 3.11 edition, which must accept the same DNA and speak the same protocol.

Anything not written here is an implementation detail. Version: `1`. Both sides announce it in `hi`.

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

On Windows 3.11, the names `chimes chord ding tada` map to `C:\WINDOWS\*.WAV`. Every other NAME falls back to
`ding` there. That edition documents its own extra names.

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

## Appendix: the Windows 3.11 edition (BASILISK 16, packages/basilisk-synth-311)

The DNA, pools, voice allocator, parameters and preset state are the same code (`core/`), so a DNA or a preset
file from one edition plays in the other. The differences are in the machine.

- **Sounds:**
  - C:\WINDOWS holds only CHIMES, DING, RINGIN and RINGOUT, so those NAMEs map to their own files.
  - Every other NAME, `chord` and `tada` included, plays DING.WAV, per §2.4.
  - The edition has no extra NAMEs.
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

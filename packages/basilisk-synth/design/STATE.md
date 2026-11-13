# STATE: the `.b16` state file, shared by the plugin and the try-online page

Status: agreed by the 3.11 lane and the web lane (2026-11-13). The plugin loads and saves it in BASILISK 16 1.3.0 (R2/R3).

## 1. What a state is

A state is exactly the text the plugin keeps as its DPF state `state` key, which is also what a `.vstpreset`, an AU
preset or a DAW project carries. There is one format and no second one:

```
BASILISK-SYNTH 1
dna <canonical DNA, v1/v2/v3 tokens, globals and macros included>
reference 0
<key> <value>            (zero or more extra lines, core/state.h `extra`, sorted by key)
```

- **Parameters** are in the DNA: Attack, Decay, Sustain, Release, Velocity, Bend Range, Output Gain, Transpose are its
  globals (`A D S R V B G` and the transpose gene); the four macros are `m1=..m4=`.
- **Key and scale** (PRESET-ENGINE-2.md section 18): extra lines `key <root 0-11> <scale id 0-999>`, `keyopt <use
  preset scale 0|1> <snap 0-4> <remap 0|1> <labels 0-4>`, and for a custom or Scala tuning `tuning <scales.h
  tuningText>`. Absent lines mean the defaults (C major, preset scale off, snap nearest, no remap, labels off).
- **User recordings** (RECORDING.md 3.3, 4.2): one line per `u_` name the DNA uses,
  `user <name> <sha1> <bytes> [<base64 of the zlib-deflated WAV>]`, plus `scratch <sha1> <base64>` for the unsaved
  take and `embedrec 0|1`. The audio is there while the total stays under 8 MB; above that only name and hash.
- Readers ignore lines they do not know and keep them when they write the state again (as DNA.md 5.7 does for
  tokens). No emulator snapshot is ever part of a state.

## 2. The `.b16` file

| Offset | Size | Content |
|---|---|---|
| 0 | 4 | magic `B16S` (ASCII) |
| 4 | 2 | version, little-endian: 1 |
| 6 | 2 | flags: bit 0 = the payload is zlib (RFC 1950, deflate) compressed; 0 = stored |
| 8 | 4 | the payload's uncompressed length in bytes, little-endian |
| 12 | 4 | CRC-32 (IEEE, as zlib's `crc32`) of the uncompressed payload |
| 16 | n | the payload: the state text of section 1, UTF-8 with `\n` line ends |

- Writers compress (flag 1). Readers accept both. The browser has `CompressionStream('deflate')` and
  `DecompressionStream('deflate')`, which are this zlib format; the plugin uses the same (miniz in core, MIT).
- A reader refuses a file whose magic, version or CRC is wrong, with a message, and changes nothing.
- File name: anything, extension `.b16`. MIME type for downloads: `application/x-basilisk16-state`.

## 3. Where it is loaded and saved

- **Plugin:** `Save state...` and `Load state...` in Windows (BASILISK 16's File menu on the Rec page in R3, until
  then the header's preset row), which send `state save` / `state load` to the host; the host opens its own file
  dialog (DPF file browser) and writes or reads the file. Loading goes through the same path as a DAW restoring a
  project (`setState`), so a `.b16` and a `.vstpreset` of the same state sound the same.
- **`.vstpreset`:** carries the same text as its component state, so a state made online opens in the DAW by
  converting `.b16` to `.vstpreset` is not needed: the plugin loads `.b16` directly, and the page can export a
  `.vstpreset` too if it wants (the VST3 preset container around the same text).
- **Try online:** the page saves and loads `.b16` with the browser's download and file picker, and keeps slots in
  its own storage as `.b16` bytes.

## 4. The ADC for the browser's microphone (R1)

The card's ADC takes its input from the host by DAC sample, the same call the plugin's sidechain uses (through the
engine's shared ring):

```c
void bsyn_host_input(uint64_t at, const float *lr, int n);   /* n stereo frames, 48 kHz float, frame k at DAC sample at + k */
void bsyn_host_insrc(int src);                               /* 0 the host's input (the mic), 1 the synth's own output */
int  bsyn_host_instate(uint64_t *start, uint32_t *bytes, uint32_t *overruns);   /* 1 while Sound Recorder records */
uint64_t bsyn_host_dac(void);                                /* the DAC sample the card has reached */
```

- Feed each block of microphone audio stamped ahead of the card: `at = bsyn_host_dac() + 2400` (50 ms) for the
  first block, then contiguously (`at += n`). The card reads the input when its DAC reaches each sample; what it
  has not been given is silence. Mono microphones: the same samples in L and R.
- The card keeps 2 s of input. Resample to 48 kHz first (the AudioContext rate may be 44.1 kHz).
- Sound Recorder (File > New) records at 22050 Hz, 8-bit mono; the card converts with its Hermite converter.

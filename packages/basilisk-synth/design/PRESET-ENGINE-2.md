# PRESET ENGINE 2: a DNA v3 proposal for both editions

Status: **proposal**. Branch `design/preset-engine-2`. This file does not change `DNA.md` or `core/`.

- DNA v2 is live on `main` and still changes. This proposal is a layer on top of v2.
- Do not merge any part of it into `DNA.md` or `core/` until both v1.2 releases ship.
- The prototypes are in `design/proto/`. They use `core/` read-only.
- "XP" is BASILISK SYNTH (`packages/basilisk-synth`). "3.11" is BASILISK 16 (`packages/basilisk-synth-311`).

The rule of the product stays the same: a real Sound Recorder plays every note. The plugin only sends
instructions. Each section below maps each wish to a thing that Sound Recorder, its sound card handle or the 3.11
BSYN card can really do. It also gives the timing accuracy.

Contents:

1. What the recorders can really do
2. DNA v3: compatibility rules and token grammar
3. Wire v3: new guest-link lines
4. Wish 1: start and end points, with random ranges
5. Wish 2: voice modes, unison, stacking
6. Wish 3: the tape keyboard category
7. Wish 4: the granular category
8. Wish 5: tabs in the editor
9. Wish 6: the mine-grid sequencer and arpeggiator
10. Wish 7: desktop mode (minimize and restore)
11. Effort, risks and phase order
12. Measurements to make first
13. The prototypes
14. Notes for the v2 lane
15. Wish 8: kit mode (percussion kits)

---

## 1. What the recorders can really do

Every design choice below rests on this table. "Exact" means sample-exact.

| Ability | XP (sndrec32 + srhook fast path) | 3.11 (SOUNDREC + BSYN card) |
|---|---|---|
| Start a note | Fast path: a primed waveOut handle in the recorder writes the recorder's own saved PCM. Trigger to sound: ~100 ms reported latency. Spread: about +-25 ms (Windows host), +-8 ms (macOS host). | Play pressed in SOUNDREC. The card starts the voice at an exact DAC sample. Latency: 2560 samples at 48 kHz. |
| Start at a point | Fast path: the write starts at a byte offset into the PCM. Exact to one frame. Slow path: seek the position slider, then Play (Sound Recorder plays from the position). | Seek SOUNDREC's scroll bar, then Play. The step size of that scroll bar is not measured yet (test T1). |
| End at a point | Fast path: the buffer length ends the write. Exact. Slow path: Stop, about +-10 ms (5 ms envelope tick plus a posted message). | `ARMSTOP` at an exact DAC sample, with a fade of at least 1 ms. |
| Change the pitch of a sounding voice | No live rate on AC97 (`waveOutSetPlaybackRate` is not supported). A rate change needs a new handle at the new rate: open 0-16 ms. See the handle swap in 5.3. | `waveOutSetPlaybackRate` works on the card (`BSC_SETRATE`). The change applies at the next sample. Smooth. |
| Read the play position | `waveOutGetPosition` on the handle (bytes). | `BSC_GETPOS` (frames). |
| Level and pan | Per-handle `waveOutSetVolume` (left and right), 5 ms steps. | Per-voice card volume. |
| Envelope | srhook ramps the handle volume in 5 ms steps. | The card's per-voice ADSR, per sample. |
| Buffer edits | The real Effects and Edit menu commands (DNA steps). A rebuild takes about 1 s. | The same commands in SOUNDREC. |
| Voices | 16 recorders. One recorder process can open more than one handle (not used yet). | 16 recorders, 32 card voices. About 30 SOUNDREC windows exhaust GDI. |
| Host link | COM1 text lines. Each line costs a few hundred microseconds. Keep it below about 300 lines per second. | Card mailbox ports. Each line can carry an event id with a DAC sample number. |

Two consequences:

- **Positions and lengths are cheap and exact on XP.** The fast path already writes the recorder's own buffer. A
  window is only a different start address and a different length.
- **Live pitch changes are the hard part on XP.** They need a new handle. 3.11 does them for free.

---

## 2. DNA v3: compatibility rules and token grammar

### 2.1 Rules

1. v3 only adds. Every v1 and v2 string keeps its meaning.
2. A v3 layer token starts with one of the letters `W N S Y V Z G`. No v1 or v2 layer token uses them.
3. A v3 global token starts with `q` or `x`. No v1 or v2 global token uses them.
4. **Token boundaries are DNA.md 5.7's** (the v2 lane's "unknown tokens are kept" rule, now on `main`), so v2,
   v3 and later parsers cut a string into the same tokens:
   - a layer token is an uppercase letter, then lowercase letters, digits, `.`, `,` and `~`;
   - a global token is a letter, then the same characters except `m` (`m` always starts a macro). In v3 the
     global letters `q`, `x` and `k` also always start a new token;
   - inside a v3 token a lowercase letter starts a subkey, and its value is the digits, `.`, `,` and `~` after it.
     A subkey that v3 does not know is **kept in its token** (so a v4 subkey survives a v3 save);
   - **no sign characters** (`+` `-` are v2 steps in a layer) and **no uppercase inside a token** (an uppercase
     letter is a v2 step, gene or global). Signed values use two subkeys (`t` up / `b` down) or an offset (`h`
     pan 0..200).
   - This replaces the earlier "closed set of subkeys per letter". The bug that rule fixed (a macro `m21L0,200`
     right after `q0` read as part of it) is fixed by the `m` boundary, as in 5.7.
5. The position of a v3 token in a layer has no meaning. v3 tokens are genes, not steps. The canonical form writes
   them after the layer's v2 tokens, in the order `W N S Y V Z G`, one token per letter. In each token, the last
   value of a subkey wins.
6. Fractions are written as the owner writes them: `0`, `1`, `.25`, `0.2`. Resolution: 1/10000.
7. **Proof:** `design/v3/test_v3.sh` gives 20,000 random mixed v2/v3 DNAs (and pure v1/v2 ones) to core's v2
   parser, once with this branch's core and once with `main`'s core (5.7). In every case the v2 meaning equals the
   v2 meaning of the string without its v3 tokens; with the 5.7 core every v3 token also survives a v2 save; and
   for a v1/v2 string the v3 canonical form is exactly core's. The guest parsers
   (`guest/synth.c` in both editions) skip unknown characters in the same way. Their global parsers react only to
   `A D S R B V K G`, which v3 tokens never contain.

**Known loss:** a v2 plugin rewrites a DNA to its canonical form, and that form drops v3 tokens. So a v2 plugin
that saves a v3 preset loses the v3 part. Rule for v3 core: keep any unknown token of the shape in rule 4 as it is.
This rule protects v4.

**Macros (v2 5.3) gain parameters.** A v3 macro parameter letter must not be `A D S R B V K G` or `m`. The reason:
when v2 core rejects an unknown parameter letter, it reads that letter again as a global. Proposed letters:

| Letter | Parameter | Unit |
|---|---|---|
| `W` | window start | 1/1000 |
| `E` | window end | 1/1000 |
| `Y` | window length | 1/1000 |
| `P` | grain position | 1/1000 |
| `I` | grain spray | 1/1000 |
| `X` | grain size | ms |
| `U` | grain density | grains per second |
| `F` | scan speed | 1/1000 of real time |
| `H` | wow depth | cents |
| `J` | glide time | ms |

Example: `m1 1 W 200,400` written as `m11W200,400` moves layer 1's start from 0.2 to 0.4 with macro 1.

### 2.2 Layer tokens

| Token | Subkeys | Meaning |
|---|---|---|
| `W` window | `s`F[`~`F] start, `e`F[`~`F] end, `l`F[`~`F] length, `v`F velocity to start, `m`ms real-time cap | Section 4 |
| `N` voice mode | `p`[n] poly (at most n notes), `m` mono, `l` legato, `c` continue, `g`ms glide, `k`(`n`\|`h`\|`l`) note priority | Section 5 |
| `S` stack | `r` round-robin, `x` random interval, `p` random recorder, `g`n[`x`] layer group, `s`ms strum, `d`n diatonic chord, `w`F unison pan width | Section 5 |
| `Y` random | `d`c detune +-cents, `l`% level down, `t`ms late start, `q`n pan +-, `k` seed per key, `r` seed per recorder | Sections 5, 6 |
| `V` rate modulation | `w`c`,`dHz wow (depth cents, rate in 0.1 Hz), `f`c`,`Hz flutter, `s`c`,`ms start scoop | Section 6 |
| `Z` key zone | lo`,`hi[`,`root] (MIDI notes) | Section 6 |
| `G` grains | `p` position, `j` spray, `z`ms[`~`ms] size, `n` density, `c` pitch spread, `o`% octave chance, `e` shape 0-3, `s` scan speed, `b` backward, `f` freeze, `v` streams, `w` pan width, `y` beat sync | Section 7 |

F is a fraction as in rule 6. A range `a~b` means "a new random value in [a, b] for each voice".

### 2.3 Global tokens

| Token | Subkeys | Meaning |
|---|---|---|
| `q`id[`r`pc] | id 0-12, `r` root pitch class 0-11 | Scale for `Sd` and the sequencer: 0 major, 1 minor, 2 dorian, 3 phrygian, 4 lydian, 5 mixolydian, 6 locrian, 7 harmonic minor, 8 major pentatonic, 9 minor pentatonic, 10 whole tone, 11 blues, 12 chromatic. Without `r`, the root is the lowest held note. |
| `x` | `d`n[`t`] division (4, 8, 16, 32, `t` triplet), `g`% gate, `s`% swing, `n`n kind (0 field, 1 count, 2 arp), `p`n notes per step, `a`n auto-dig cells, `o`n octaves, `l`n steps used, `b`bpm free tempo, `f` free run, `h` latch | Section 9 |

Example (the owner's pad): `logon<#8Ws.2~.4l.1~.3;A400R900`. Each voice starts at a random point from 0.2 to
0.4 of the buffer and plays a random 0.1 to 0.3 of it.

---

## 3. Wire v3: new guest-link lines

The host sends a v3 line only to a guest that answered `hi 3`. A v2 guest gets v2 lines only. New fields go at the
end of a line, so old parsers read the fields they know.

`hi 3` is answered with `hi 3 <edition> <state> <caps>`. caps is a comma list, for example
`win,rate,swap4,grain,grid,desk`. The host uses only the features in the list.

### Host to guest

| Line | Meaning |
|---|---|
| `on <rec> <rate> <vol> <pan> <delay> <layer> <from> <to>` | v2 `on` plus a window in frames of the layer's buffer, `[from, to)`. `0 0` = the whole buffer. |
| `rate <rec> <hz> [<glide_ms> [<regate>]]` | Change the rate of a sounding voice. Keep its position. glide_ms: ramp time. regate 1: the voice was in its release; hold it again at the sustain level. If the recorder is silent, ignore the line. |
| `lmod <layer> <wow_c> <wow_dhz> <flu_c> <flu_hz> <scoop_c> <scoop_ms>` | The layer's rate modulation after macros. The guest runs it for each voice (section 6.3). |
| `lgrain <layer> <pos> <spray> <size_lo> <size_hi> <density> <cents> <oct> <shape> <scan> <flags> <streams> <width>` | The layer's grain settings after macros. Fractions in 1/10000. flags: b backward, f freeze, y sync. |
| `tempo <bpm_x100> <ppq_x1000> <playing>` | The host transport, for beat-synced grains. At most 10 per second. |
| `step <col>` | The sequencer playhead, for display only. The host sends it when the step is heard, so after the latency. |
| `newgame <dig>` | Start a new board in the mine game and dig `dig` safe cells (section 9.5). |
| `board <w> <h> <mines> <cells>` | Restore a saved board (section 9.7). |
| `desk <0\|1>` | Show the Windows desktop (1) or the synth (0) (section 10). |
| `choke <rec> <fade_ms>` | Kit mode: end this recorder's hit with a fade (cut and mute groups, section 15.3). Sent before the `on` that caused it. |
| `kit <0\|1>` | Kit mode on or off (the Kit tab follows; section 15.4). |

### Guest to host

| Line | Meaning |
|---|---|
| `hi 3 <edition> <state> <caps>` | Answer to `hi 3`. |
| `grid <w> <h> <state> <cells>` | The mine board changed (section 9.4). |
| `seg <layer> <f1> <f2> ...` | After a build: where each segment of the layer's buffer starts, in frames (the source at 0, then each Insert File; section 15.1). |
| `desk <0\|1>` | The visitor changed the desktop mode inside Windows. |

Link load: `rate` lines come at note rate. `lmod` and `lgrain` come only after a `dna` or a macro move. Wow and
grains run inside the guest, so they cost no link lines on XP.

---

## 4. Wish 1: start and end points, with random ranges

### 4.1 DNA

`W` with `s` start, `e` end, `l` length, each a fraction of the layer's buffer after its steps. Because the values
are fractions, a sample swap (a new source NAME) keeps the same relative window.

| Example | Meaning |
|---|---|
| `Ws.25e.75` | Play the middle half. |
| `Ws.2~.4l.1~.3` | Start from 0.2 to 0.4, play 0.1 to 0.3 (random for each voice). |
| `Ws.5~.9Yk` | A random start for each key, but the same start each time that key plays. |
| `Ws.3v1` | Start at 0.3 at velocity 0; harder notes start earlier, velocity 127 starts at 0. |
| `Wm8000` | Release the voice after 8000 ms of real time (the tape length of section 6). |

Rules:

- If `l` is given, the end is the start plus the length, but never past `e`.
- The shortest window is 10 ms. The volume ramp then still has two 5 ms steps.
- The host picks the random values. The guest gets frames only. So both editions play the same window for the
  same seed, and batch renders repeat.
- **Bake** (a button on the Playback tab) changes a fixed window into real Sound Recorder steps: Delete After
  Current Position at the end, then Delete Before Current Position at the start. Example: `Ws.25e.75` on a 1.000 s
  buffer bakes to `@t750]@t250[`. Then the strip's green wave and Length show the trimmed sound. A random window
  cannot be baked.

### 4.2 Guest

- **XP** (`srhook.c`, note thread): the `on` line puts from/to in the slot. The note thread writes
  `pcm + from * nBlockAlign` with length `(to - from) * nBlockAlign`. The visual timer shows the position as
  `from + played`, so the strip's slider moves inside the window. The slow path (no PCM loaded) seeks the slider to
  `from`, presses Play without Rewind, and posts Stop when `to` is reached.
- **3.11** (`synth.c`, `play_rec`): seek the scroll bar to `from` instead of pressing Rewind. Then arm the stop with
  `bs_armstop` at the DAC sample of `(to - from) / rate` after the start. If test T1 shows that the scroll bar
  steps are coarser than 10 ms, add a card-side window: a `BSC_ARM` variant with skip and limit frames. The card
  then trims what SOUNDREC hands it, the same idea as the XP fast path.

### 4.3 Timing accuracy

| | XP fast path | XP slow path | 3.11 |
|---|---|---|---|
| Start point | exact (1 frame) | slider unit (T1) | scroll unit (T1), or exact with the card window |
| End point | exact | +-10 ms | exact, with a fade of at least 1 ms |
| Note onset | unchanged (~100 ms latency, +-25 ms / +-8 ms spread) | unchanged | exact |

### 4.4 Plugin and UI

- Core: `W` parse; `window()` per voice (prototype: `engine3.cpp`); `on` with from/to; `Wm` releases the voice.
- Playback tab (section 8). Effort: **S** (2-3 days for both editions). Risk: low. On 3.11, the scroll unit is
  unknown.

---

## 5. Wish 2: voice modes, unison, stacking

### 5.1 DNA

| Token | Mode |
|---|---|
| none, or `Np` | Poly, as v2. The pool limits it. |
| `Np4` | Poly, at most 4 notes in this layer. The oldest note is stolen. |
| `Nm` | Mono. Each new note stops the old one and starts again from the window start. |
| `Nmg60` | Mono with portamento: the new note starts at the old pitch and glides in 60 ms. |
| `Nlg80` | Legato. An overlapped note glides in 80 ms and keeps the position: no new attack. A detached note starts again. |
| `Ncg40` | **Continue.** A new note never starts the sample again while the recorder still sounds. This includes the release. The sound goes on from where it is, at the new rate. |
| `kh` / `kl` / `kn` | Note priority: highest, lowest, newest (default). Example: `Nlkh`. |

Mono modes work per layer. A mono bass layer can sit under a poly pad layer. Each mono note still sounds
harmony x unison recorders (`H`, `U`).

### 5.2 How "continue" works

Sound Recorder's buffer and position do not change. Only the rate of the card handle changes.

1. The host's `MonoPlan` (prototype: `engine3.cpp`) decides: `Rate` when the recorder still sounds, else `On`.
2. The host sends `rate <rec> <hz> <glide> <regate>` to each recorder of the note.
3. 3.11: the guest calls `BSC_SETRATE` with the new ratio. For a glide, the guest steps the ratio every 10 ms, or
   the card ramps it (one new card command, ramp target and frames). The position stays exact.
4. XP: the handle swap of 5.3.

If the buffer ends before the next note, the voice ends as usual. The next note then starts with `On` from the
window start.

### 5.3 XP: the handle swap

XP's AC97 path has no live rate. So srhook keeps more than one card handle per recorder:

1. Read the position of the playing handle A (`waveOutGetPosition`).
2. Take handle B at the new rate from a small cache (up to 4 open handles per recorder, keyed by rate). If B is not
   in the cache, open it (0-16 ms, measured).
3. Write the PCM from the position, plus the frames that A plays while B starts, to B at volume 0.
4. Ramp A down and B up over 10 ms (two envelope ticks). Then reset A and keep it in the cache.

A glide is a staircase of swaps, one swap every 30 ms. Each step is at most 1/12 of the interval, so a fifth in
100 ms is 4 steps. The cache makes repeated pitches (arpeggios) open no new handles.

Risks: the 10 ms crossfade can comb if the two positions do not match (test T3). kmixer CPU grows with open
handles (test T4).

### 5.4 Unison, detune and stacking

v2 already has `H` (harmony intervals) and `U` (unison count and spread). v3 adds the ways to choose:

| Token | Meaning |
|---|---|
| `Sr` | Round-robin: each note takes the next interval of `H` only. `H0,12,7Sr` plays root, octave, fifth in turn. |
| `Sx` | Each note takes one random interval of `H`. |
| `Sp` | Random recorder pick: a random free recorder of the pool, not the oldest. With `Yr` each recorder has its own small level and detune offset, so the pick is audible. |
| `Sg1` / `Sg1x` | Layer group: the layers with the same group number take turns, one layer per note. `x`: a random layer of the group. This is round-robin samples: for example `ding>#4Sg1/ding>E#4Sg1`. On a v2 machine both layers sound together. |
| `Ss30` | Strum: harmony voice k starts k x 30 ms later. This uses the v2 `on` delay field, so it needs no new wire. |
| `Sd3` | A 3-note chord in thirds of the global scale `q`. It replaces `H`. `Sd4` is a seventh chord. |
| `Sw.6` | Unison voices spread over +-0.6 of the pan range. |
| `Yd6` | Random detune of +-6 cents for each voice. |

Octave stacks, fifth stacks and chord stacks need no new syntax. The Voices tab offers them as `H` presets:
octave `H0,12`, two octaves `H0,12,24`, fifth `H0,7`, stacked fifths `H0,7,14,21`, power `H0,7,12`, major
`H0,4,7`, minor `H0,3,7`, sus4 `H0,5,7`, add9 `H0,4,7,14`.

### 5.5 Live pitch bend (a side effect)

v2 applies bend only at note start. With `rate`, the host can send the bent rate to held voices. Limit: 50 lines
per second per layer on XP (each line is a handle swap). 3.11: smooth.

### 5.6 Effort and risk

| Part | Effort | Risk |
|---|---|---|
| `N` modes in core (host only) | S | low |
| `rate` on 3.11 (`BSC_SETRATE` exists) | S | low |
| `rate` on XP (handle swap and cache in srhook) | M (4-6 days) | medium: crossfade quality, CPU |
| `S` and `Y` (host only, except `Ss`, which is the v2 delay field) | S | low |

---

## 6. Wish 3: the tape keyboard category

### 6.1 What to copy from a tape-replay keyboard

A tape-replay keyboard has one strip of tape per key. A key press pulls the tape across a head. The tape runs out
after about 8 s and does not loop. Names in the product: category "Tape Keyboard", presets "Tape Strings" and
so on. No brand or model names.

| Tape behavior | How the recorders do it | Token |
|---|---|---|
| One recording per key | Key zones: each layer plays only its zone, from its own root. The rate ratio stays near 1. | `Z` |
| About 8 s per key, no loop | The library sounds are 8 s long. `Wm8000` releases the voice after 8 s of real time. The fast path never loops. | `Wm` |
| Higher keys run out sooner | They play faster. Zones of a fifth or less keep this small. | `Z` |
| Key click at the start | A short click layer at a low level: `menu` (30 ms) or `xpstart` (50 ms), fixed pitch. | `F L Wm` |
| The tape starts late | The tone layer starts 10-20 ms after the click. | `O` (v2) |
| Pitch scoop at the start (the capstan gets up to speed) | Start 15-25 cents flat, reach pitch in 50-80 ms. | `Vs` |
| Wow (slow speed drift) | A slow rate wobble, 4-8 cents at 0.5-0.8 Hz. | `Vw` |
| Flutter (fast speed drift) | 3.11: a real 8-12 Hz rate wobble. XP: too fast for handle swaps, so a 2-voice unison at 2-3 cents (`U2~3`) gives the beating instead. | `Vf`, `U` |
| Small level and tuning differences between keys | Random level and detune with a per-key seed: each key always has the same offset. | `Yl Yd Yk` |
| Fast release when the key lifts | The pad lifts off the tape: release 80-150 ms. | `R` (v2) |
| Three sounds on one tape (track select) | One buffer holds three sounds in a row (`I` steps). The window picks a third; a macro moves the start. | `W`, `m..W` |

The Sound Recorder character stays: 22 kHz mono sources on XP, 8-bit sources on 3.11, kmixer resampling, the
Effects menu (`E` echo is the tape room).

### 6.2 Presets (first set)

The tonal sources are the library disc's 8 s samples (VSCO 2 CE, CC0; `library/catalog/tonal.json`). The roots
of `choir_aah` and `crowd_sing_aah_f` are estimates; measure them before the release. Pool sizes total 16.

| Preset | DNA |
|---|---|
| Tape Strings | `violin_section_sus_c4#7Z55,127,60Wm8000Vs15,80Vw6,6Yl6d4k/cello_section_sus_c3#7Z0,54,48Wm8000Vs15,80Vw6,6Yl6d4k/menu#2FL25Wm40;A40R140V60` |
| Tape Cello | `cello_section_sus_c3#7Z43,127,48Wm8000Vs20,70Vw7,5Yl6d4k/cello_section_sus_g1#7Z0,42,31Wm8000Vs20,70Vw7,5Yl6d4k/menu#2FL20Wm40;A30R120V60` |
| Tape Flute | `flute_vib_c5#14Z0,127,72O12Wm8000Vs25,50Vw5,7Yl5d3k/menu#2FL20Wm30;A50R110V50` |
| Tape Choir | `choir_aah#14Z0,127,57O15Wm8000Vs10,90Vw5,5U2~3Yl6d5k/menu#2FL15Wm40;A120R180V40` |
| Tape Voices | `crowd_sing_aah_f#14Z0,127,53O15Wm8000Vs12,80Vw6,6Yl8d6k/menu#2FL15Wm40;A90R160V40` |
| Tape Brass | `trumpet_sus_c4#6Z60,127,60Wm8000Vs20,50Vw5,7Yl6k/trombone_sus_c3#6Z0,59,48Wm8000Vs20,50Vw5,7Yl6k/horn_sus_c3#2Z48,72,48L50Wm8000/menu#2FL25Wm40;A25R100V70` |
| Tape Bells | `glockenspiel_g4#7Z0,74,67Wm8000Vw4,6Yl5k/glockenspiel_c6#7Z75,127,84Wm8000Vw4,6Yl5k/menu#2FL20Wm30;A0R400V90` |
| Tape Three-Track | `flute_vib_c5@t30000Iviolin_section_sus_c4@t30000Icello_section_sus_c3#14Ws0e.333Wm8000Vw6,6Yl6k/menu#2FL20Wm40;A40R140m11W0,667m1=0`. `@t30000` moves to the end (the value is clamped to the length), so each Insert File adds the next track at the end. Macro 1 moves the start from track 1 to track 3; the UI snaps it to three positions. The three sources have roots an octave apart, so the tracks sound in three registers, as on some real tapes. |

On v2 machines these presets play their v2 subset: the same layers and zones become full-range layers that all
sound. So the tape category ships only with v3 (rule: a preset category has a minimum DNA version).

**3.11:** the library sounds are not on the 3.11 drive yet. Until its extra drive lands, the 3.11 tape set uses
`ringout` (a near-sine) for flute and organ shapes and `chimes` for bells, with the same `W V Y Z` genes.

### 6.3 Guest: wow, flutter and scoop

- **3.11:** a 100 Hz guest timer (or a card-side LFO, one new card command) sets each sounding voice's rate.
  Smooth.
- **XP:** srhook runs the wow as handle swaps (5.3), one swap every 40-60 ms. That gives 12-25 steps per wow cycle.
  The next rate is known in advance, so the cache opens its handle early: no open delay. Flutter on XP becomes the
  static unison of 6.1. The scoop is a glide from the start rate.

### 6.4 Effort and risk

Effort: **M** after phases 1-2 (presets, zones in core, `lmod` in both guests, sound checks). Risk: medium. The
sound quality of XP wow by swaps is not proven (test T3). Without wow, the presets still work.

---

## 7. Wish 4: the granular category

### 7.1 Controls and their mapping

A grain is a short part of a layer's buffer, played by one recorder, with its own pitch, level and pan.

| Control | Token | What the recorder does |
|---|---|---|
| Position | `Gp` | The grain read point, a fraction of the window (`W`). |
| Spray (jitter) | `Gj` | A random +- offset to the position for each grain. |
| Grain size | `Gz60~120` | The length of each grain in ms (real time, after the rate). |
| Density | `Gn40` | Grains per second per note, shared by the streams. |
| Pitch spread | `Gc30`, `Go20` | Random +-cents per grain; a 20 % chance of +12 semitones. |
| Shape | `Ge0`-`Ge3` | The volume envelope of each grain: rectangle, triangle, smooth, percussive. Made with handle volume steps (XP) or the card envelope (3.11). |
| Freeze | `Gf` | The position does not move. |
| Scan rate | `Gs1`, `Gs.5`, `Gb` | The position moves at 1x (or 0.5x) of real time. This keeps the length of the sound at any pitch: time-stretch. `Gb`: backward. |
| Streams | `Gv6` | How many recorders (or handles) of the pool one note uses. |
| Pan width | `Gw.7` | A random pan for each grain. |
| Beat sync | `Gy` | Density counts grains per beat and places them on the host beat grid. |

Example: `startup#12Gp.4j.15z80~160n50c20e2s.25v6Gw.6;A300R1500q0` is a slow cloud through the XP startup sound.

### 7.2 Guest

- **XP:** each recorder of a note runs its own grain loop in srhook, in a time-critical thread with
  `timeBeginPeriod(1)`. For each grain the loop picks a position, a size and a rate. Then it writes that part of
  the recorder's own PCM to a free handle of the cache and steps the handle volume through the shape. Off releases
  the loop. The rates come from a small set per note (at most 4 per recorder), so the cache holds them all and no
  grain waits for an open. The strip's slider jumps to each grain's position, so the strips show the cloud.
- **3.11:** the host schedules each grain as an `on` line with an event id and a DAC sample. The card starts it
  exactly. But each grain is one Play in SOUNDREC, and that Win16 path is slow (the code logs plays over 30 ms). So
  the 3.11 grain rate is low (test T6). A card-side window (4.2) lets one Play feed several grains; that is phase
  6b.

### 7.3 Limits

| Limit | XP | 3.11 |
|---|---|---|
| Shortest shaped grain | 20 ms (four 5 ms volume steps) | 2 ms (the card envelope is per sample) |
| Shortest hard-edged grain | 5 ms (it clicks) | 1 ms |
| Grain start jitter | +-2 to +-8 ms (Sleep(1), kmixer start; test T5) | exact |
| Most grains at once | pool x handles per recorder, at most 32 streams in kmixer (test T4) | 32 card voices |
| Most grains per second | about 300 (12 recorders, 2 handles, 80 ms grains) | low; test T6 |
| Pitch spread | per grain, from up to 4 rates per recorder | free |

### 7.4 Effort and risk

Effort: **L** (XP 6-8 days; 3.11 3 days for the simple path). Risk: high on XP CPU under TCG and on grain start
jitter. A grain layer can take the whole pool. The UI shows the stream count beside the pool.

---

## 8. Wish 5: tabs in the editor

The whole editor is the inside of Windows. So the tabs are real Windows controls in `synth.exe`.

- **XP:** a real Tab control (`SysTabControl32`) on top of the right-hand column (x 606-1016). The 16 strips stay
  on the left on every tab: they show the voices, the grains and the sequencer notes. The Main tab is the column of
  today without change. The column moves down 22 px for the tab row; there is room (it ends at y 742 of 768).
- **3.11:** Windows 3.11 has no tab control. A row of push buttons acts as the tabs; the button of the open page
  stays down (`BM_SETSTATE`), as in some 3.11 Control Panel dialogs. The pages use the 3.11 controls: buttons,
  check boxes, edit fields and horizontal scroll bars as sliders. The pages live in the panel under the strips
  (y 620-768).

### 8.1 XP mockups (the right-hand column, 410 x 740 px)

```
 [ Main | Voices | Playback | Grains | Sequencer | Library ]
 Main (as today)
 +- DNA ----------------------------------------+
 | ding>E/tada<<R+#4H0,12U2~9;A5R350    [Apply] |
 | [Mutate] [Undo]                              |
 +- Layers -------------------------------------+
 +- Sounds -------------------------------------+
 +- (Task Manager CPU graph) -------------------+
 +- (Date and Time clock and calendar) ---------+
```

```
 [ Main | Voices | Playback | Grains | Sequencer | Library ]
 Layer: [ 1 chimes      v]
 +- Voice mode ---------------------------------+
 | (o) Poly  Notes: [ 8 ]^v                     |
 | ( ) Mono  ( ) Legato  ( ) Continue           |
 | Glide   Short |-------[]--------| Long  80 ms|
 | Priority: [ Newest v]                        |
 +- Stack --------------------------------------+
 | Intervals: [ Octave        v]  H0,12         |
 | [x] Round-robin  [ ] Random interval         |
 | [ ] Random recorder   Group: [ 0 ]^v [ ] Rnd |
 | Strum    0 |---[]-----------| 200 ms  30 ms  |
 | Chord in scale: [ Off v]                     |
 +- Unison -------------------------------------+
 | Voices [ 2 ]^v  Detune |--[]-----| +-9 cents |
 | Pan width |------[]----| 0.60                |
 +- Random --------------------------------------+
 | Detune +-[ 6 ]  Level -[ 6 ]%  Late [ 0 ] ms |
 | Seed: (o) Each note ( ) Each key ( ) Recorder|
 +----------------------------------------------+
```

```
 [ Main | Voices | Playback | Grains | Sequencer | Library ]
 Layer: [ 2 logon       v]       Length: 2.16 sec.
 +- Start / End (selection = random range) -----+
 | Start  |====[######]============| .20 - .40  |
 |         [x] Random   From [.20]  To [.40]    |
 | End    |========================[]| 1.0      |
 | Length |==[####]================| .10 - .30  |
 |         [x] Use length                       |
 | Velocity moves start |[]----------| 0         |
 | Tape length  [ 8000 ] ms   [ ] Off           |
 |                         [Bake into buffer]   |
 +- Pitch drift (tape) -------------------------+
 | Wow     |---[]-------| 6 cents  |--[]--| 0.6 Hz |
 | Flutter |-[]---------| 2 cents  |-[]---| 11 Hz  |
 | Scoop   |--[]--------| 15 cents |--[]--| 80 ms  |
 +- Key zone -----------------------------------+
 | Low [C2  v]  High [B3  v]  Root [C3  v]      |
 +----------------------------------------------+
```

The Start, End and Length rows are XP trackbars with a selection range (`TBS_ENABLESELRANGE`). The blue selection
bar shows the random range, and the thumb shows the last value used.

```
 [ Main | Voices | Playback | Grains | Sequencer | Library ]
 Layer: [ 1 startup     v]   [x] Grains on
 +- Cloud ---------------------------------------+
 | Position |------[]--------| .40  [ ] Freeze   |
 | Spray    |-[]------------| .15               |
 | Size     |---[]----------| 80 - 160 ms       |
 | Density  |-----[]--------| 50 /s  [ ] Beat   |
 | Pitch    |--[]-----------| +-20 cents        |
 | Octave up|[]-------------| 0 %               |
 | Scan     |---[]----------| 0.25 x  [ ] Back  |
 | Pan width|-------[]------| .60               |
 | Shape  (o) Smooth ( ) Triangle ( ) Rect ( ) Hit|
 | Streams [ 6 ]^v of 12 recorders              |
 +- Grains now (Task Manager CPU graph) --------+
 |  grains per second, last 60 s               |
 +----------------------------------------------+
```

```
 [ Main | Voices | Playback | Grains | Sequencer | Library ]
 [x] Sequencer on   Kind: [ Field v]  Scale: [ Minor v]
 Step [1/16 v] [ ] Triplet   Gate [80]%   Swing [ 0]%
 Notes per step [4]   Octaves [2]   Steps used [16]
 +- (the real mine game window, Intermediate) ---+
 |  Game  Help                                   |
 |  [040]        (:)                      [000]  |
 |  ......1.......................                |
 |  ..2.11........................                |
 |  .F...?...                     (16 x 16 cells) |
 |  ...                                           |
 +-----------------------------------------------+
 Playhead |-------[]---------------------| step 7
 Dig after New Game: [3]   [x] Latch   [ ] Free run 120 bpm
 Left click: dig (more notes).  Right click: a note (flag).
 Right click again: tie (?).  New Game: a new pattern.
```

```
 [ Main | Voices | Playback | Grains | Sequencer | Library ]
 +- Presets -------------------------------------+
 | Category        Name                   Layers |
 | Tape Keyboard   Tape Strings              3   |
 | Tape Keyboard   Tape Flute                2   |
 | Grains          Startup Cloud             1   |
 | ...  (a ListView in Details view)             |
 +- Library disc (TreeView of D:\) --------------+
 | [+] Bells  [+] Machines  [+] Tonal  [+] Voices |
 +-----------------------------------------------+
 [Load] [Audition] [Save As...]
```

The Library tab holds the v2 browser that the v2 lane builds now. This proposal only moves it into a tab.

### 8.2 3.11 page sketch (panel, 1024 x 148 px)

```
 [Main] [Voices] [Playback] [Grains] [Sequencer] [Library]     <- push buttons; the open one stays down
 Playback  Layer [<] 2 [>]
 Start  <|||||[]||||||||>  .20  [x] Random to <||||||[]|||||>  .40
 End    <||||||||||||||[]>  1.0  Length <|||[]||||||> .10-.30   Tape [8000] ms
 Wow    <||[]||||||||||||>  6 c  Rate <||[]|||> 0.6 Hz        Scoop <|[]|||> 15 c
```

The 3.11 Sequencer page needs room for the game. On that page the strips get narrower (the seek scroll bar and the
status text get shorter), and the mine game sits to the right of them.

### 8.3 Effort and risk

Effort: **M** for the frame on each edition (tab control, page switching, a shared page model), then **S** per page.
Risk: low on XP (the tab control needs comctl32 v6 visual styles: a manifest for `synth.exe`). Risk on 3.11:
medium, because GDI resources are tight (section 1) and each page adds windows. Create the pages only when they
open.

---

## 9. Wish 6: the mine-grid sequencer and arpeggiator

### 9.1 What exists

| Edition | Game | Where |
|---|---|---|
| XP | the mine game, `winmine.exe` | `C:\WINDOWS\system32\winmine.exe` on English XP SP3. Confirm on our `base.qcow2` in a dev VM of our own (test T7). Italian builds of XP do not include it. |
| 3.11 | the mine game, `WINMINE.EXE` | `C:\WINDOWS\WINMINE.EXE`. Windows 3.1 made it a standard part, so the Entertainment Pack is not needed. It is in `site/basilisk-31-browser/w31.jsdos`, which `tools/make_machine.py` copies whole. Solitaire (`SOL.EXE`) is there too. |

The game runs as itself. `synth.exe` makes its window a child of the synth window, as it does today with Task
Manager's Performance page. The game draws its own cells. Nothing is copied.

### 9.2 The musical map (kind 0, "Field", the default)

```
 rows    = notes: the bottom row is the root, each row up is the next degree of the scale
 columns = steps: the playhead moves left to right, one column per step, and loops
 a cell  = what the player sees in it
```

| Cell | Meaning |
|---|---|
| hidden | silence |
| open, blank (0) | silence (open ground is a rest) |
| open, number 1-8 | a note. The number sets the velocity: 1 soft ... 8 loud. |
| flag (one right click) | a note with an accent. This is how the player places a note directly. |
| question mark (two right clicks) | a tie: the note to its left in the same row holds through this step |
| mine shown after a loss | that column plays one octave up (a fill) |
| wrong flag shown after a loss | that column is a rest |

- The scale comes from `q`. The root is the lowest held note; with no note held, it is `K`. A 7-note scale over
  `xo2` octaves gives 14 lanes; rows above that wrap.
- The board size is the pattern size. Beginner: 9 steps x 9 notes. Intermediate: 16 x 16. Expert: 30 x 16.
  Custom: any size from 9 x 9 to 30 x 24. `xl` uses only the first n columns, so a 9-wide board can play 8 steps.
- At most `xp` notes sound in one step. Accents come first, then the loudest, then the lowest.
- Numbers come in clusters near mines, and most numbers are 1 or 2. So a dug board gives a natural rhythm: busy
  near mines, quiet in open ground.

Other kinds:

| Kind | Rows | Number n |
|---|---|---|
| `xn1` count | octave band (one band per octave of `xo`, the bottom row is the lowest) | scale degree n of the scale (1 = root) |
| `xn2` arp | octave band (as `xn1`) | held note n, counted from the lowest; it wraps to the next octave |

`xn2` is the arpeggiator: only held notes sound, in the order the board gives.

### 9.3 How to play it

1. Open the Sequencer tab. Hold a chord.
2. Click the smiley face. The game starts a new board, and the synth digs 3 safe cells for you. Numbers appear.
   That is a new pattern.
3. Left-click hidden cells to dig. Each dig opens numbers, so more notes.
4. Right-click a hidden cell to place a note (flag). Right-click again for a tie (?). Once more clears it.
5. Choose Game > Beginner, Intermediate or Expert to change the pattern length.
6. If you dig a mine, you lose: the mines show and their columns jump an octave. Click the smiley for a new game.

The legend under the game says the same in four lines (section 8.1 mockup).

### 9.4 Reading the board from the guest

| Method | XP | 3.11 | Notes |
|---|---|---|---|
| Memory | `ReadProcessMemory` of the game's board (community-documented address `0x01005340`, rows of 32 bytes, width at `0x01005334`, height at `0x01005338`). Check the border bytes (`0x10`); if the check fails, scan the image's data pages for the bordered grid. Prototype: `design/proto/winmine_probe.c` (builds, not run yet). | Win16 has one shared address space. The game's data segment selector is its instance handle (`GetWindowWord(hwnd, GWW_HINSTANCE)`). Scan that segment once for the bordered grid, then read it with a far pointer. | Exact and cheap: about 900 bytes, 20 times a second. It also knows the mines, which the auto-dig needs. |
| Window pixels | `PrintWindow` or `BitBlt` of the game into a DIB, then sample each 16 x 16 cell. The digit colors differ (1 blue, 2 green, 3 red, 4 navy, ...). | `BitBlt` from the game's DC. | Shows only what the player sees. Works with any build of the game. Breaks if the game is covered (XP `PrintWindow` avoids that). |
| Input replay | Record the clicks. | Same. | Cannot know the result of a click. Use it only to restore a game. |

Recommendation: memory first, pixels as the check in tests and as the fallback if the memory check fails.

The guest polls 20 times a second and sends `grid <w> <h> <state> <cells>` only when something changed. Cells are
row by row, top row first: `.` hidden, `0`-`8` open, `F` flag, `?` question mark, `*` mine shown, `X` the mine that
was hit, `x` wrong flag. State: `n` new, `p` playing, `w` won, `l` lost. At most 30 x 24 = 720 cells, so a line
fits in the 1024-byte limit.

### 9.5 New Game is "randomize"

A new board is all hidden, so it is silent. So after New Game the guest digs `xa` safe cells (default 3). With the
memory method it knows the mines, so it clicks only safe cells: it posts the same mouse messages a click makes.
With the pixel method it digs only once: the game's first click is always safe. The plugin's "Randomize" parameter
(automatable) sends `newgame <xa>`.

### 9.6 Clock

The sequencer runs in the plugin, not in Windows:

- The plugin reads the host transport (`getTimePosition()`: bpm, ppq position, playing). Each step is a sample
  position in the block. The step's notes go into the same voice path as MIDI notes. So they get the same
  latency compensation, and they land on the DAW grid.
- Swing delays every second step by `xs` % of a step.
- When the transport stops: with `xf`, the sequencer runs at `xb` bpm; without it, it stops.
- The guest only holds the pattern. Its timing does not matter.
- Accuracy: as for MIDI notes. XP: +-25 ms (Windows host), +-8 ms (macOS host). 3.11: exact.
- The playhead: a real XP trackbar under the game (no drawing on the game). The host sends `step <col>` after the
  latency, so the thumb moves when the step is heard.

### 9.7 Saving the pattern

A board does not fit in a DNA (720 cells, 1024 bytes in all). The plugin keeps it as its own state key `grid`, next
to the DNA. On load, the host sends `board <w> <h> <mines> <cells>` with the mine positions. The guest writes the
board into the game's memory, sets the game's counters (mines left, cells to open), and repaints the game. This is
the riskiest part (the counters must match the game's own rules). So it comes last; before it exists, a reload
gives a new board.

### 9.8 Effort and risk

Effort: **L** (8-10 days for both editions). Risks:

- The board address and cell codes are from community notes. The probe confirms them first (test T7).
- 3.11's data segment scan is new work in Win16.
- The game must fit: Expert is about 500 px wide, and the XP column is 410 px wide. Up to 24 columns fit in the
  column. Expert opens a wide layout that covers strips 9-16 while that tab is open.
- If the player loses, the game stops taking clicks until New Game. That is a game rule, and the legend says it.

---

## 10. Wish 7: desktop mode (minimize and restore)

Today `synth.exe` is a 1024 x 768 popup at the bottom of the window order, and it hides the taskbar (`EV_TRAY`).

### 10.1 Guest

- **XP:**
  - A menu item "View > Windows Desktop" (and `desk 1` from the host) shows the taskbar (`Shell_TrayWnd`) and
    minimizes the synth window. The synth window gets `WS_EX_APPWINDOW`, so it has a taskbar button titled
    "BASILISK SYNTH".
  - A tray icon (`Shell_NotifyIcon`) has "Restore BASILISK SYNTH".
  - Restore: the window goes back to (0, 0, 1024, 768) at the bottom of the order, and the taskbar hides again.
    Then each strip gets `SYO_SNAP`, so each strip is exactly in place.
  - The strips and donor pages are children of the synth window, so they come back with it.
  - Win+D (Show Desktop) minimizes the synth too. The synth treats `SIZE_MINIMIZED` as desktop mode.
- **3.11:** the synth window gets `WS_MINIMIZEBOX` and a system menu. Minimized, it is an icon on the desktop, in
  front of Program Manager. A double click restores it, and `layout_strip` runs for each recorder.

### 10.2 What the visitor must know (the Help text says it)

- Notes still play while the synth is minimized. The sound path does not use the windows.
- Anything Windows plays goes into the DAW track. The event sounds are off ("No Sounds" scheme), so clicks are
  silent. A media file that the visitor plays in Windows goes into the track too.
- Programs that the visitor runs use the emulated CPU, so note timing gets less steady.
- A reload of the plugin starts again from the saved machine. Files made in Windows are lost then (the disk is a
  throwaway overlay).
- 3.11: other programs use the same small GDI heap as the 16 recorders. Opening many programs can stop the synth
  from drawing.

### 10.3 Effort and risk

Effort: **S** (1-2 days). Risk: low. It is independent of the DNA, so it can go first.

---

## 11. Effort, risks and phase order

| Phase | Content | Needs | Effort | Risk |
|---|---|---|---|---|
| 0 | This spec and the prototypes (done on this branch) | - | - | - |
| 1 | Desktop mode (section 10); `W` window and `Y` random (section 4, 5.4); `on` from/to; `hi 3` caps | both v1.2 releases shipped | S + S | low |
| 2 | `rate` primitive: 3.11 `BSC_SETRATE`, XP handle swap and cache; `N` modes; live bend; `S` stacks | phase 1 | M | medium (XP crossfade) |
| 3 | Tab frame on both editions; Voices and Playback pages | phase 1 | M | low (XP), medium (3.11 GDI) |
| 4 | Tape keyboard: `Z` zones, `V` wow and scoop (`lmod`), the preset category | phases 2, 3, library disc | M | medium |
| 5 | Mine-grid sequencer: probe, board reader, `grid` line, host sequencer, Sequencer page, New Game dig | phase 3 | L | medium |
| 6 | Grains: XP grain loop in srhook, 3.11 host scheduler, Grains page; 6b: the 3.11 card window | phases 2, 3 | L | high (XP CPU and jitter) |
| 7 | Pattern recall (`board`), Library tab move, v3 core forward rule (keep unknown tokens) | phase 5 | M | medium |

Why this order:

- Phase 1 is cheap, exact on XP, and every later phase uses the window.
- Phase 2 is the only new hard primitive. Tape, glide and grains all need it, so it must be proven early.
- Tabs come before the big features, so each feature has a page when it lands.
- The sequencer comes before grains: it only adds notes to the existing voice path, so its risk is lower.

---

## 12. Measurements to make first

Do these in a dev VM of our own, never in a machine that another session runs.

| Test | What | Why |
|---|---|---|
| T1 | The step size of the position control: XP sndrec32 trackbar range, 3.11 SOUNDREC scroll range, for 1 s and 8 s sounds | Start accuracy of the slow paths |
| T2 | XP fast path with a byte offset: onset and end against a click track | Confirm "exact" |
| T3 | XP handle swap: click and comb level of the 10 ms crossfade; time from `rate` to the new pitch | Phase 2 quality gate |
| T4 | XP kmixer CPU with 16, 32 and 48 open handles under TCG | Handle cache size, grain streams |
| T5 | XP grain start jitter with `Sleep(1)` | Section 7.3 |
| T6 | 3.11 SOUNDREC Play rate: plays per second, one recorder and 16 | 3.11 grain rate |
| T7 | `winmine_probe.exe` on our XP image: address, cell codes, all game states | Section 9.4 |
| T8 | 3.11 `WINMINE.EXE` data segment scan | Section 9.4 |
| TK1 | Choke fade: XP streamed software gain (5, 10, 20 ms) against waveOutReset (hard cut); 3.11 card release (1, 5, 10 ms): click level | Section 15.3 |
| TK2 | Retrigger of a stolen (sounding) recorder: XP reset + write on the same handle, 3.11 Stop + Play; time to sound and its spread | Section 15.3 |
| TK3 | Segment boundaries: Insert File points as reported by the guest against the real buffer, both editions | Section 15.1 |
| TK4 | XP multi-out: does our XP image have working drivers for a second emulated card (ES1370, SB16), each to its own audiodev? | Section 15.5 |
| TK5 | Stress: 16th-note hats at 180 bpm with choke, plus kick and snare, for 60 s: link lines per second, missed or late hits | Section 15.3 |

---

## 13. The code (`design/v3/`) and the probes (`design/proto/`)

`design/v3/` is tested code, ready to fold into `core/` after the v1.2 releases. It does not touch `core/`,
`guest/`, `plugin/` or the 3.11 package; it compiles a `core/dna.cpp` in, read-only.

| File | Content |
|---|---|
| `dna3.h`, `dna3.cpp` | The v3 tokens (W N S Y V Z G, q x k, v3 macro letters): `parse3()`, `canonical3()` (core's canonical form plus the v3 tokens; idempotent; equals core's for v1/v2), `strip3()` (the v2 subset), `applyMacros3()`. Unknown subkeys are kept. |
| `engine3.h`, `engine3.cpp` | `window()`, `bakeSteps()`, `MonoPlan` (poly, mono, mono + portamento, legato, continue; priority; repeated note-ons), stacking (`noteIntervals` for `Sr Sx Sd`, `unisonPan`, `strumDelayMs`, `groupPick`, `humanize`, `voiceSeed`), zones and `modCents`/`xpStaircase` (wow, flutter, scoop; the XP swap plan), `Grid`/`stepNotes`/`stepPpq` (the mine grid), kit mode (`pickPad`, `padCents`, `padGain`, `chokeTargets`, `padWindow`), and the wire (`parseHi3`, `onLine`, `rateLine`, `lmodLine`, `lgrainLine`). |
| `test_v3.cpp`, `test_v3.sh` | About 29,900 checks, including the 20,000-string fuzz. `test_v3.sh [main checkout]` runs them against this branch's core and against `main`'s core (DNA.md 5.7). |

Run (builds go to `~/pe2-build`):

```
packages/basilisk-synth/design/v3/test_v3.sh /mnt/c/Users/willi/github/williamsharkey/windows-secrets
```

Folding in: `dna3.cpp` goes into `core/dna.cpp` (`Layer` and `Globals` get the v3 fields; `canonical3` becomes
`parse().canonical`), `engine3.cpp` into `core/voices.cpp`.

`design/proto/` holds the measurement tools (section 12): `xp_swaptest.c` and `xp_stream.c` (waveOut tests in
XP), `sr_probe.c` (XP Sound Recorder: trackbar, Add Echo, lengths, speed round trips), `winmine_probe.c` (the XP
board reader and the T7 scenario), and `xp_analyze.py` (the analysis of QEMU's wav recordings).

---

## 14. Notes for the v2 lane

These came up while this proposal was written. None of them blocks v2.

1. v2 core drops unknown characters from the canonical form. So a v2 plugin that saves a v3 preset loses its v3
   part (section 2.1). If v1.2 can still take a small change: keep unknown tokens that match rule 4 of 2.1 as they
   are. That protects every later version.
2. In the v2 globals, a macro token with an unknown parameter letter does not consume that letter. The letter is
   then read again as a global. Example: `m11S50` sets sustain to 50. That is why v3 macro letters avoid
   `A D S R B V K G` (2.1). A v2 fix: skip the whole bad macro token.
3. The XP guest's `dna_parse` reads `@` as a percent only. `@t300` gives `@0`. The v2 lane has this on its list
   ("Guest: v2 tokens").

---

## 15. Wish 8: kit mode (percussion kits)

Owner request (2026-11-13): kit-based presets where not every note follows pitch (some pads can, in a limited
range), with the standard drum-sampler features: cut groups and the rest, and a tab where a check box turns kit
mode on and helps to map it. Real Sound Recorders still play every hit.

**Status:** format fixed (other lanes write kit maps against it, for example
`library/research/electromech-presets.json`); parser, pad choice, pitch, velocity, choke and slice logic are
tested code in `design/v3/` (`Pad`, `pickPad`, `padCents`, `padGain`, `chokeTargets`, `padWindow`). Guest work
and the Kit tab come after v1.2, in phase 5b (section 11).

### 15.1 The model

- A **pad** maps a note or a note range to a **layer** of the DNA. The layer is the pad's sound: its source, its
  Sound Recorder chain (steps), its genes (`#`, `L`, `Q`, `O`, `J`, `W`, `Y` ...). Several pads can use one layer.
- A DNA with at least one pad is a **kit**. In a kit, notes sound only through pads. A note with no pad is silent.
  Layers that no pad uses are silent too.
- **Two ways to give a pad recorders.**
  - *Reserved:* the pad has a layer of its own, with its own pool (`#N`). It can have its own chain. At most 8
    layers per DNA, so at most 8 reserved sounds.
  - *Shared (kit strip):* many pads share one layer whose buffer is several sounds in a row, built with real
    Insert File steps: `kick_808@t30000Isnare_808@t30000Ihat_closed@t30000Ihat_open#8`. Each pad plays one
    **segment** of that buffer (`j`). Every recorder of the layer holds every sound, so the pads share the pool
    (any free recorder plays any of them). This is the tape-keyboard track trick (6.2) used for drums. The chain
    steps after the inserts apply to the whole strip.
- **Segments:** after a build the guest reports where each segment starts: `seg <layer> <f1> <f2> ...` (frames:
  the source starts at 0, then each Insert File's insert point; scaled if later steps change the length). The
  host uses frames only, so the window of a pad is exact on both editions (XP: the fast path writes those bytes;
  3.11: the card window of 4.2).
- v2 machines keep the pad tokens (DNA.md 5.7) but do not read them: there, every layer sounds on every note. So
  kit presets ship only for v3 (as the tape category, 6.2: a category has a minimum DNA version).

### 15.2 DNA: the `k` global token

One `k` token per pad, in the globals. The token follows DNA.md 5.7 (a letter, then lowercase subkeys, digits,
`.` `,` `~`; `m` ends it). In v3 the global letters `q`, `x` and `k` always start a new token, so they are never
subkeys of another global token. That is why the sequencer's kind is `xn` (it was `xk`).

`k`lo[`,`hi] then subkeys. All are optional; the defaults make a one-shot, fixed-pitch, full-length pad on layer 1.

| Subkey | Meaning | Default |
|---|---|---|
| `l`n | layer 1..8 | 1 |
| `j`n | segment of the layer's buffer: 0 the whole buffer, 1 the source as loaded, 2.. each Insert File in order | 0 |
| `s`F[`~`F], `e`F[`~`F] | start and end inside the segment (fractions, random ranges as `W`) | 0, 1 |
| `r`n | root note: plays at the buffer's own rate | lo |
| `p`n | pitch tracking %: 0 fixed (drums), 100 full (pitched percussion), between: less | 0 |
| `w`n | pitch range: at most n semitones from the root (limited-range pitched percussion); 0 = no limit | 0 |
| `t`c / `b`c | tune up / down, in cents (no sign characters in v3 tokens) | 0 |
| `i`n | level % (0..400) | 100 |
| `h`n | pan 0..200, 100 = centre (no sign characters) | 100 |
| `v`n | velocity curve: 0 linear, 1 soft (quiet hits come up), 2 hard, 3 fixed | 0 |
| `a`n | velocity amount % | the global `V` |
| `y`lo`,`hi | velocity window: the pad answers only these velocities (velocity layers) | 1,127 |
| `g` | gated: note-off releases the pad (default one-shot: it plays to its end, R still shapes the tail) | off |
| `c`n | cut (choke) group 1..16: a hit stops every sounding hit of that group, its own pad included | none |
| `f`ms | choke fade | 10 |
| `u`n[`,`n...] | mute groups: a hit stops the groups listed, one way (the muted pads do not stop this one) | none |
| `n`n | voices for this pad: 1 = a new hit cuts its last one; 0 = the layer's pool decides | 0 |
| `o`n | output pair 1..8 (15.5); 1 on editions without buses | 1 |
| `z` | random choice among the pads that match a hit (default: round-robin) | off |

A `k` token with no note is kit-wide: `kd` = kit off (the map stays in the DNA, the DNA plays as layers). The Kit
tab's check box writes it. Unknown subkeys are kept in their token.

**Round-robin and velocity layers** need no extra syntax: when several pads match a note and its velocity, they
take turns, one per hit (`z` on any of them: a random one). Pads with the same notes and different `y` windows are
velocity layers.

Example: a small kit, with one strip of hats (shared pool) and reserved kick, snare and toms.

```
kick#2/snare#4/hats@t30000Ihat_closed@t30000Ihat_pedal@t30000Ihat_open#6/tom#4;A0R300V90
k36 k38l2y1,90 k38l2i120y91,127 k42l3j2e.9c1 k44l3j3c1f20 k46l3j4c1 k47,53l4r50p100w3b15h70
```

(spaces added here for reading; the DNA has none). Kick on 36. Snare on 38 in two velocity layers, the hard one
20 % louder. Closed, pedal and open hat are segments 2, 3, 4 of the hat strip, all in cut group 1, so each stops
the others (the pedal hat with a 20 ms fade). Toms on 47..53, root 50, following pitch but at most 3 semitones
either way, 15 cents flat, panned to 70 (left of centre).

Canonical form: pad tokens in written order (order is meaningful: it is the round-robin order), after `q` and `x`;
inside a pad the subkeys in the table's order, defaults left out.

### 15.3 How the editions play it

| Feature | XP | 3.11 |
|---|---|---|
| Pad window (segment, start, end) | fast path: write those frames. Exact. | card window (4.2, `BSC_ARM` with skip and limit). Exact. Until it exists: scroll bar seek (T1) |
| Fixed pitch / tracking / range | the handle's open rate (as today) | `BSC_SETRATE` at the start |
| One-shot vs gated | one-shot ignores `off` (the release still applies at the end of the window); gated: `off` as today | the same; `ARMSTOP` at the window end |
| Choke fade | needs per-voice gain: the streamed software gain of 5.3 (T3 found waveOutSetVolume is global). Fade 10 ms (two 5 ms chunks) or more. Without it: waveOutReset, a hard cut (a click) | the card's per-voice release: exact, from 1 ms |
| Retrigger of a stolen recorder | reset + write on the same handle (TK2) | Stop + Play in SOUNDREC (T6) |
| Mute groups | as choke, one way | as choke |
| Output pairs | not with one AC97 stream; possible with more emulated cards (TK4) | the card mixes per voice: per-voice buses in `bsynth.cpp`, a multi-out plugin |

Host rules: a hit first chokes its targets (`chokeTargets`): for each sounding voice of those pads it sends
`choke <rec> <fade_ms>`. Then it starts the pad. The order on the wire is choke first, so the guest never runs out
of recorders because of a choked voice. Retriggering the same pad with `n1`: choke own pad, same order.

### 15.4 The Kit tab

The tab joins the tab strip of section 8 (id `kit`).

**XP (real common controls, comctl32 v6):**

```
 [x] Kit mode          Bank [ 36-51  v]      [GM drum map]  [Auto-map...]  [Learn]  [Audition]
 +- Pads (16 BUTTONs, 4 x 4, push-like) --+  +- Pad 42: Closed hat ------------------------------+
 | [49 Crash ][50 Tom H ][51 Ride ][  -  ] |  | Sound  [hats: segment 2       v]  (Library tree) |
 | [44 Ped.H1][45 Tom L ][46 Op.H 1][47 ..]|  | Pitch  (o) Fixed ( ) Follow ( ) Range +-[ 3 ]^v  |
 | [40 Snr 2 ][41 Tom F ][42 Cl.H 1][43 ..]|  | Tune   |-------[]-------| -15 c   Level |---[]-| |
 | [36 Kick  ][37 Rim   ][38 Snare ][39 ..]|  | Pan    |-----[]---------| L 30                   |
 +-----------------------------------------+  | Start/End  |==[#####]=====|  (trackbar selection)  |
 +- Map (ListView, Report) -------------------| Velocity [Linear v] Amount |---[]| From [1] To [127]|
 | Note Name     Layer Seg Pitch Cut Mode Out|| Play (o) One-shot ( ) Gated   Voices [0]^v        |
 | 36   Kick     1     -   fixed  -  shot  1 || Cut group [1 v] Fade |-[]---| 15 ms  Mutes [ ] ... |
 | 42   Cl.hat   3     2   fixed  1  shot  1 || Output [1-2 v]  Recorders (o) Reserved ( ) Shared   |
 +-------------------------------------------++--------------------------------------------------+
```

- Pads: 16 push-like BUTTONs; the text is note, short name and the cut group number, so choke groups are
  visible at a glance; the Map list repeats them in a `Cut` column.
- Click a pad, or a key of the keyboard strip (DNA.md 5.4) while the tab is open: that pad is selected.
- Sound: a combo with the library categories, and a TreeView of the library disc (the Library tab's browser).
- **Auto-map:** pick a library category (or a folder of the disc) and a first key; its sounds fill the next keys,
  as segments of one strip (shared) or as layers (reserved, at most 8).
- **GM drum map:** names the keys 35..81 by the General MIDI percussion map and fills the common ones from the
  library by category (kick 36, snare 38, closed hat 42 / pedal 44 / open 46 in cut group 1, crash 49, ride 51,
  toms 41..50). It is a starting point, not a rule.
- **Learn:** the next note from the DAW (it arrives as a `show` line, DNA.md 5.4) moves the selected pad to that
  note. No new wire line.
- **Audition:** plays the pad through the host (`key` line), like a key of the keyboard strip.

**3.11 (no ListView, TreeView, trackbar or up-down control):** the panel area (y 550-682, 1024 x 132 px):
16 push buttons in a 4 x 4 block (40 x 24 px each) on the left; a LISTBOX with tab stops as the map (columns
Note, Name, Layer, Seg, Pitch, Cut, Mode); the selected pad's settings as COMBOBOXes (sound, curve, cut group,
output), radio buttons (Fixed/Follow/Range, One-shot/Gated), horizontal SCROLLBARs as sliders (tune, level, pan,
start, end, fade) and EDIT fields for numbers. Buttons: GM map, Auto-map, Learn, Audition. The 3.11 kit uses the
3.11 sounds and the 3.11 library drive.

### 15.5 Output pairs

The plugin gets up to 8 stereo outputs (DPF: more audio outputs; the main pair stays output 1, so a host that
ignores the others hears everything).
- **3.11:** the BSYN card already renders each voice. It can sum voices into up to 8 buses and hand them to the
  plugin. Needs a card command (bus per voice) and a wider audio path from the core. Feasible.
- **XP:** QEMU sends one stereo stream (AC97). More buses need more emulated sound cards, each with its own
  audiodev pipe, and XP drivers for them (TK4). Until then `o` is kept but plays on output 1.

### 15.6 Effort and risk

Effort: **M** for the core and host (pads, choke, segments, buses on the plugin side); **S** per guest for `seg`
and `choke`; **M** for the Kit tab on each edition. Risks: XP choke fades depend on the streamed gain path (5.3);
3.11 retrigger speed (T6); multi-out on XP (TK4).

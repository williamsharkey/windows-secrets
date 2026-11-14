# Preset targets: the most loved sounds in synth and sampler history, rebuilt with Sound Recorder

This is a research note for the BASILISK SYNTH preset library. It lists **198 targets**: famous factory presets,
benchmark sounds for each instrument category, and three aesthetics (Frutiger Aero, vaporwave/mallsoft, and Y2K
corporate audio). For each target it gives:

- what makes the sound loved;
- a starting DNA that is valid in spec v1 (`../../DNA.md`);
- the steps that need the planned features;
- the Windows sounds that suit it.

`14` entries are cross-listed: the same sound filed under a second heading, such as *Koto* in both Yamaha and World.

- **Machine-readable copy:** `preset-targets.json`. Each entry has these fields:
  - `id`, `category`, `name`, `inspired_by`, `character`, `recipe_steps`, `suggested_sources` and `priority` (1 means
    build first);
  - `rank` (1 to 30, set only for priority 1);
  - `dna`: the canonical spec-v1 start;
  - `cross_listed`;
  - `works_on_311`: true when every NAME used exists on Windows 3.11 (`chimes ding ringin ringout`).
- **The DNAs have been checked.** Every `dna` was run through the real parser (`core/dna.cpp`, `parse()`), and each one:
  - parses to every layer it was meant to have, with no unknown NAME;
  - is already in canonical form.

  Nobody has listened to them yet. Treat each one as a starting point to tune by ear in reference mode, and then on
  the real machine.
- **Sources are described from memory.** The other research lane's `windows-sounds.json` did not exist when this was
  written, so the descriptions of what each Windows sound contains (pitch, length, where the stable part sits) come
  from memory of the XP and 3.1 files. Where a recipe says `@20[@40]` ("the steady middle"), check the real envelope
  in `windows-sounds.json` once it lands and move the percentages.
- **Pitch is not tuned yet.** None of the Windows sounds is tuned to C. Every preset needs `K` (root) or `T` set from
  the measured pitch of its main source.

---

## 1. Toolbox idioms

Sound Recorder has no filter, no LFO, no loop points and no pitch envelope. Nearly all of those can be
approximated from the 13 commands. These idioms recur through the recipes below, so they are named once here.

| Idiom | DNA | What it does | Used for |
|---|---|---|---|
| **TRIM-ATTACK** | `@NN]` | Keeps only the first NN%: a transient, strike or pluck. | Plucks, perc, kalimba, pizz, organ click |
| **TRIM-BODY** | `@NN[` | Throws the attack away and keeps the tail. | Bowed/soft onsets, pad bodies |
| **GRAIN** | `@a[@b]` | Keeps a slice from a% to roughly a+(100-a)·b%. `@` is relative to the *current* length, so the second number refers to what is left. | Getting a steady chunk of a sound |
| **LOOP-OSC** | GRAIN, then `@0CP` × k | Doubles the slice k times (2^k copies). The seams repeat at the slice period, so a short, steady slice becomes a sustained tone, and an ~5–20 ms slice becomes a **pitched buzz at 1/slice-length Hz**. This is the closest thing to a wavetable oscillator. 30 s cap. | Organ, supersaw core, square/chip leads, reese, drones, tremolo strings |
| **CLIP** | `+` × 2–4 | Each step adds +25% with hard clipping, which squares the waveform off. | Saw/square-ish buzz, 808 distortion, hoover, house organ bark |
| **DECIMATE** | `><`, `>><<`, `>>><<<` | *Hypothesis*: Increase Speed drops samples with no anti-alias filter, and Decrease Speed interpolates them back. If so, a round trip is a sample-rate reduction at the original pitch and length. **Verify** in reference mode against XP. | Mirage, MT-32, SP-1200 and lo-fi grit |
| **REQUANTIZE** | `----++++` | *Hypothesis*: on 8-bit sources, each `-` loses resolution and `+` restores the level, so the result is bit-crushed. | Lo-fi, chip |
| **COMB** | `EE>`, `EEE>>` | Echo, then speed up: the echo delay shrinks into a few ms and becomes a comb resonance. | Koto sawari, sitar jawari, steel pan, harpsichord |
| **LONG-ECHO** | `<E>`, `<<E>>` | Slow down, echo, speed up: the echo delay comes out 2× or 4× longer, at the original pitch. | Trance pluck delays, Aero bubble echoes |
| **BLUR-DOWN** | `<E<E` | Alternates slowing down and echo, so each echo is longer and lower. | Vaporwave, slowed + reverb |
| **SWELL** | `R`, `RE` | Plays the sound backwards, so it grows out of silence. | Swell pads, reverse cymbal, glass swells |
| **PRE-VERB** | `RER` | Reverse, echo, reverse: the echo lands *before* the note (reverse reverb). | Shimmer plucks, halos |
| **SELF-FLANGE** | `C@03X` | Mixes a copy of the buffer over itself a few % later, which gives a static comb or hollow sound. | K2000 hollow pads, phasey textures |
| **OCT-BAKE** | `C>@0X` / `C<@0X` | Bakes an octave above or below into one buffer, saving recorders. | Pool-efficient stacks |
| **SPLICE-SEQ** | `I`a`I`b`I`c… | Insert File chains several sounds, so the timbre changes over the note. | Wavestation wave sequences, VFX transwaves, glitch, modem |
| **MIX-TRANSIENT** | `M`click | Mixes a click into a body to give it attack. | Kalimba, organ key-click, slap |

The voice genes do the rest:

- `H` gives drawbars, octave stacks and chords.
- `U` gives chorus, supersaw, reese beating and tape wow.
- `F` turns a layer into unpitched perc or noise.
- `L` sets the balance between layers.

### Proposed notation for the planned features

These features are not in spec v1. The recipes describe them in prose, tagged `[planned ...]`. Each one is
needed by this many targets:

- **`[planned offsets]` (1 to 6 recorders per sound, each with its own start offset).** 12 targets. It unlocks:
  - tempo delays: taps at 0, 187 and 375 ms with falling volume;
  - harp and strum glissandi: 20 ms steps;
  - flams and Haas width;
  - staged entry of layers (Absynth);
  - a fake tape-stop: speeds ×1, ½, ¼ and ⅛ cascaded.
- **`[planned pan]` and non-baked volume.** 11 targets need pan to give chorus width, Leslie and tremolo
  motion, and ping-pong echoes. Non-baked volume is also how a macro crossfades layers.
- **`[planned env graph]` (multi-segment drawn envelopes).** 20 targets. It gives:
  - the M1 Organ 2 bark (a fast drop to 35%);
  - chiff overshoots on flute, pan flute and shakuhachi;
  - trance gates and wobbles drawn as a graph;
  - Absynth-style staggered peaks, one per layer;
  - attack shapes that differ per layer (the D-50 Fantasia bell-to-pad crossfade).
- **`[planned macro]` (M1 to M4).** 16 targets. The common mappings are:

  | Macro | Typical role |
  |---|---|
  | M1 | Brightness or timbre: crossfade a dull `<<` layer into a bright `>` layer |
  | M2 | Motion: unison spread, tremolo depth |
  | M3 | Space: level of an echo layer, or a dry/wet pair |
  | M4 | Character: clip-layer level, or crumple and noise level |

  Suggested convention: **every factory preset assigns M1 brightness, M2 motion, M3 space, M4 character**, so the four
  knobs mean the same thing in every preset.

### What the toolbox can't do (and the workaround)

- **No pitch envelope or glide.**
  - Bake pitch motion into the source. `hwin` and `hwout` rise and fall, `minimize` and `restore` sweep.
  - Use `B12` for manual bends.
  - Fake glides with recorder offsets at staggered speeds.
- **No filter.**
  - Use speed as a filter: `<` darkens (Nyquist halves relative to the content), and so does DECIMATE.
  - Crossfade dull and bright layers with a macro.
  - Swap in a duller source.
- **No loop.**
  - LOOP-OSC builds a long sustained buffer, up to 30 s.
  - The natural buffer end is a feature for Mellotron-style tape stops.
- **Pool budget.** A note costs `len(H) × U` recorders per layer.
  - A 3-voice harmony at `U2` costs 6 recorders, so one note in a 16-pool can hold two such layers.
  - Chord-heavy presets (M1 Piano, house organ) should use `U1`, and OCT-BAKE instead of `H`.

---

## 2. Which Windows sound for which job

The descriptions are from memory and need checking against `windows-sounds.json`.

| Job | Best sources | Why |
|---|---|---|
| Sine-ish sustained tone (flute, organ, sub, Rhodes body, ooh) | `ringout`, `xpringout`, `batlow`, `batcrit` | Steady electronic tones with few partials |
| Bell / tine / glass | `xpding`, `chimes`, `ding`, `print`, `xpnotify` | Real struck-metal and FM-like inharmonic spectra |
| Mallet / wood | `default`, `xpringin` (front), `exclaim` | Soft mallet "bong" and marimba-like ringtone |
| Pluck | `xpringin@5]`, `xpding@15]`, `default@30]` | Short fronts of melodic sounds |
| Warm pad bed | `startup`, `logon`, `logoff`, `shutdown` | XP's only long, lush, reverberant material |
| Choir / vowel | `notify` (slowed), `xpnotify`, `ringout` (oo) | Mid-range tones that read as vowels when slowed and detuned |
| Brass / orchestral hit | `tada`, `critstop`, `chord` | A real fanfare chord, and a dramatic low chord |
| Piano-ish chord | `chord` | Struck chord with a quick bloom |
| Low / bass / doom | `error`, `critstop`, `batlow` slowed | Low two-tone, dark chord |
| Noise: breath, bow, hats, surf, crackle | `recycle`, `xprecycle` | Paper crumple, broadband |
| Air / sweep / riser | `minimize`, `restore` | Whooshes down and up |
| Bubble / bloop / Aero | `balloon`, `hwin`, `hwout` | Round pops, rising and falling bloops |
| Click / transient / tick | `start`, `xpstart`, `menu`, `popup`, `infobar` | IE nav click and UI ticks |
| Meme / identity | `error`, `critstop`, `exclaim`, `tada`, `startup`, `shutdown` | Recognizable as themselves |

**The 3.11 edition only has `chimes`, `ding`, `ringin` and `ringout`**, all 8-bit. It does best at:

- bells: `chimes` and `ding`;
- sine tones: `ringout`;
- trills and chirps: `ringin`;
- and, for free, anything Mirage-, Emulator I- or MT-32-gritty.

Targets that use only those four NAMEs are flagged "plays on 3.11 too".

---

## 3. Counts

| Category | Targets | P1 | P2 | P3 |
|---|---:|---:|---:|---:|
| E-mu (Emulator I/II/III, Proteus 1/2/3, World, Planet Phatt, Orbit, Vintage Keys, Mo'Phatt) | 14 | 4 | 8 | 2 |
| Roland (D-50, U-20/U-220, JV/XV, Sound Canvas, MT-32, JD, Alpha Juno) | 17 | 4 | 10 | 3 |
| Korg (M1, Wavestation, Triton) | 10 | 4 | 3 | 3 |
| Yamaha (DX7, TX81Z, SY77, Motif) | 10 | 2 | 3 | 5 |
| Kurzweil and Ensoniq (Mirage, ESQ-1, VFX, EPS, K250/K2000) | 7 | 0 | 2 | 5 |
| Pad and texture soft synths (Absynth, Omnisphere, Alchemy, Massive, Serum, Spire, Sylenth, Nexus, Zebra, Kontakt, Ethno World) | 16 | 2 | 11 | 3 |
| Bass | 10 | 2 | 7 | 1 |
| Keys | 10 | 0 | 6 | 4 |
| Arps and plucks | 8 | 1 | 5 | 2 |
| Pads | 10 | 1 | 7 | 2 |
| Vocal choir | 7 | 1 | 4 | 2 |
| Bells and mallets | 8 | 1 | 5 | 2 |
| Strings | 6 | 0 | 3 | 3 |
| Brass and stabs | 6 | 0 | 6 | 0 |
| Leads | 7 | 0 | 2 | 5 |
| World | 10 | 2 | 5 | 3 |
| Drones | 5 | 0 | 3 | 2 |
| Risers and FX | 8 | 0 | 6 | 2 |
| Lo-fi and vaporwave | 8 | 2 | 5 | 1 |
| Aesthetic: Frutiger Aero | 10 | 2 | 7 | 1 |
| Aesthetic: Y2K, web portal and corporate | 11 | 2 | 8 | 1 |
| **Total** | **198** | **30** | **116** | **52** |

## 4. The 30 to build first

These are ranked by how iconic the original is, weighted by how well our means can capture what people love
about it. The deciding factor is the attack/decay shape and the motion, not the exact timbre. Several have
Windows-native identity (Aero Startup Swell, Windows Error Choir), and those are the brand.

| # | Target | Inspired by | Start DNA |
|---:|---|---|---|
| 1 | M1 Piano 16' | Korg M1 'Piano 16'' (house piano: Robin S, Crystal Waters, Black Box, 90s house) | `chord@5[@45]#10H0,12/xpding@20]#6L40;A0D1200S15R250V60` |
| 2 | DX7 E.PIANO 1 | Yamaha DX7 ROM1A 'E.PIANO 1' (the most used preset of the 80s: Whitney, Lionel Richie, every ballad) | `xpding@20]#6H0,24/ringout@25[@35]#8L80;A0D1600S25R350V90` |
| 3 | Emulator Orchestra Hit | Fairlight CMI ORCH5 (Stravinsky Firebird) via the E-mu Emulator and every ROM after it | `tada@25]++E#10H0,12/critstop@10]<#6L80;A0D300S0R200V70` |
| 4 | Fantasia | Roland D-50 preset 'Fantasia' (the most famous D-50 sound; Jean-Michel Jarre, 'Wonderful Life' era) | `xpding@30]#6H0,12/startup@25[@40]<#8U3~10L70;A0D900S55R1500` |
| 5 | TX81Z Lately Bass | Yamaha TX81Z preset 'LatelyBass' (Stevie Wonder 'Lately'; 90s house and R&B, everywhere) | `error<@25]++#8/hwin<@20]#4L60;A0D250S40R70V90` |
| 6 | M1 Organ 2 | Korg M1 'Organ 2' (Robin S 'Show Me Love', 1993: the most famous rompler organ) | `ringout@20[@30]@0CP@0CP@0CP#8H0,12,19/start>#4FL70;A0D220S35R90` |
| 7 | Aero Startup Swell | Windows XP/Vista startup sounds (Brian Eno 95 / XP / Vista 'Aero' startup) | `startup#10U2~6/chimes>R#6L50;A200S90R2500` |
| 8 | SC-55 Choir Aahs | Roland Sound Canvas GM 53 'Choir Aahs' (and every GM module since) | `notify<#8U3~12/xpnotify<<@20[#6U2~10L60;A300S90R900V40` |
| 9 | Shakuhachi Hammer | E-mu Emulator II 'Shakuhachi' (Peter Gabriel 'Sledgehammer' intro; also Fairlight SHAKUHACHI) | `ringout@30[@40]#3U1~0/recycle>>@8]#2F;A15D400S70R250V80` |
| 10 | Glassy Speed Bell | Glassy FM bell (DX7 'E.BELL', M1 'Bell', 'glass bell' trope) | `chimes>>#6H0,12,19U2~5;A0D3000S0R1500` |
| 11 | Vaporwave Slowed Pad | Vaporwave ('Floral Shoppe', 'Eccojams' slowed, reverbed) | `startup<E<E#8U2~12/logon<E#8L60;A300S95R3000` |
| 12 | Mellotron Choir | Mellotron M400 '8-Voice Choir' (Bowie 'Space Oddity', Genesis, King Crimson, Radiohead) | `notify<<-#8U3~16/logon<<@25[#6U2~12L50/recycle<<<#2FL10;A350S95R700` |
| 13 | Reese Bass | Kevin Saunderson 'Just Want Another Chance' Reese (DnB/jungle benchmark) | `error<<@10[@30]@0CP@0CP@0CP+++#16U2~18;A5S100R150` |
| 14 | 808 Sub Boom | Roland TR-808 kick-as-bass (trap and hip-hop 808, sub-bass category benchmark) | `ringout@20[@40]<<<#8/start<#2FL50;A0D2500S40R200` |
| 15 | M1 Universe | Korg M1 'Universe' (space pad: glassy bells over a wide airy pad) | `startup@20[<#8U3~12/chimes>R#6U2~8L60;A700S90R2500` |
| 16 | Water Droplet Pluck | Frutiger Aero water drop (Vista/Windows 7 'notify', Apple 'Drip', 2000s UI) | `balloon@40]#10/hwin>@20]#4L40;A0D200S0R150` |
| 17 | Digital Native Dance | Roland D-50 'Digital Native Dance' (looped PCM percussion pad) | `start>@0CP@0CP@0CP@0CPE#6F/logon<@30[#8U2~8L70;A20S90R900` |
| 18 | Wavestation Glass Pad | Korg Wavestation 'Glass Mountain'/'Spectrum' vector pads (Wave Sequencing) | `chimes@40]IxpdingIchimes>Iprint@0CP#8U2~6/logon<#8L50;A80S90R1600` |
| 19 | Vintage Keys Rhodes | E-mu Vintage Keys 'Suitcase' / 'Stage 73' Rhodes | `default@50]#8/ringout@30[@30]<#6L60;A2D1800S30R400V90` |
| 20 | XV Supersaw Pad | Roland XV-5080 / JP-8000 'Supersaw' trance pad and lead (late-90s trance) | `chord@20[@30]@0CP@0CP@0CP++#16U8~35;A20S95R700` |
| 21 | Trance Pluck | Classic trance pluck (Sylenth 'Pluck' / Nexus 'Pluck' / Gaia-style) | `xpding@15]#8U2~10/xpding@15]<<E>>#4L40;A0D150S0R200` |
| 22 | Warm Analog Pad | Oberheim OB-X / Juno-60 strings-pad (warm pad benchmark) | `startup@20[<#10U3~14/logoff@30[<#6U2~10L60;A600S90R1800` |
| 23 | Proteus World Kalimba | E-mu Proteus World / Planet Earth 'Kalimba' (also Alchemy and Omnisphere kalimbas) | `xpding@25]#10/start>#4FL50;A0D600S0R250` |
| 24 | Pan Flute | Pan flute (Zamfir; GM 76; Korg M1 'PanFlute') | `ringout@25[@40]#8U2~7/minimize>@15]#3FL35;A40S90R600` |
| 25 | Steel Drum | Steel drum / steelpan (GM 115; Proteus World; tropical house) | `xpding@20]EE>#8/default@30]#4L60;A0D700S0R300` |
| 26 | Mallsoft Atrium | Mallsoft (Disconscious, 'Hologram Plaza'; '猫 シ Corp') | `chord<<EEE#8U2~10/recycle<<<#4FL15/logon<<#4L50;A600S90R3500` |
| 27 | Corporate Logo Sting | 2000s corporate intro stings (Intel bong, PowerPoint templates, 'Microsoft Sound') | `tada#8H0,12/chimes>#4L50/startup@20[#4L40;A0D1800S30R2000` |
| 28 | Windows Error Choir | Windows-error remixes (YouTube 'Windows sounds' meme music) | `error#8/critstop#4L60/exclaim#4L50;A0D600S30R300` |
| 29 | Absynth Evolving Atmosphere | NI Absynth factory atmospheres ('Aetherizer'-style granular, multi-segment envelope pads) | `startup<<#4U2~20/logon<R#4/chimes>>R#4/recycle<<<#4FL20;A1500S80R4000` |
| 30 | Omnisphere Evolving Pad | Spectrasonics Omnisphere ('Analog Pad Dreams', 'Hardware Library', and the 'Coldplay pad' type) | `startup@15[<#8U3~14/logoff<R#4L60/minimize<<#4FL25;A900S90R3000` |

## 5. All targets by category

## E-mu (Emulator I/II/III, Proteus 1/2/3, World, Planet Phatt, Orbit, Vintage Keys, Mo'Phatt)

### Shakuhachi Hammer (P1, rank 9)

- **Inspired by:** E-mu Emulator II 'Shakuhachi' (Peter Gabriel 'Sledgehammer' intro; also Fairlight SHAKUHACHI)
- **Character:** Breathy chiff burst then a hollow, almost-sine flute tone that bends up into pitch; the whole charm is the noisy overblown attack and a short, slightly falling tail. Mono, dry, 8-bit-era grit.
- **Start DNA:** `ringout@30[@40]#3U1~0/recycle>>@8]#2F;A15D400S70R250V80`
- **Sources:** `ringout`, `xpringout`, `recycle`, `minimize`
- **Recipe:**
  - Layer 1: a steady chunk of ringout (sine-ish ringback tone) is the hollow body; trim to its stable middle with @30[@40].
  - Layer 2: the first 8% of recycle (paper crumple) at x4 speed is the breath chiff; F keeps it unpitched.
  - [planned env graph] pitch is not available, so fake the 'scoop' with a volume graph: 0 to 100% in 15 ms, a 60 ms dip to 80%, then hold. That reads as an overblown attack.
  - [planned offsets] start the chiff recorder 0 ms and the body 25 ms later, so the breath is heard first.
  - [planned macro] M1 = chiff level (layer-2 vol 0 to 150%).

### Emulator Choir Arr (P2)

- **Inspired by:** E-mu Emulator I/II choir and the Fairlight ARR1 'Aah' (the 80s sampled choir)
- **Character:** Dark, lo-fi 'aah' with a slow swell, little top end and a grainy 8-bit sheen; vibrato comes from the ensemble, not an LFO.
- **Start DNA:** `notify<-#8U3~14/logon<<@20[#8U2~9L60;A350S90R1100V50`
- **Sources:** `notify`, `logon`, `chimes`, `xpnotify`
- **Recipe:**
  - notify slowed an octave and turned down sits in the vocal formant range; three-voice unison at +/-14 cents makes it a section.
  - logon two octaves down, with its attack cut off, adds a breathy wash.
  - Keep the 8-bit grit: on the 3.11 edition, build it from chimes<< with ><, the decimation round trip.
  - [planned env graph] a 350 ms S-curve attack and a 1.1 s release with a small hump, like breath.

### Emulator Marcato Strings (P2)

- **Inspired by:** E-mu Emulator II 'Marcato Strings' / Emulator III Strings
- **Character:** Short bowed attack with rosin noise, fast 200 ms decay into a sustained but dark body; slightly stepped, low-sample-rate texture.
- **Start DNA:** `logoff@30[#10U3~10/recycle>>>@5]#2FL40;A20D250S60R400`
- **Sources:** `logoff`, `shutdown`, `recycle`
- **Recipe:**
  - Middle of logoff (string shimmer) as the sustained body, unison x3 for section width.
  - A tiny x8 crumple transient gives the bow noise.
  - [planned env graph] fast 20 ms rise, 250 ms drop to 60%, hold. That is the 'marcato' accent.
  - [planned pan] spread unison voices L40/C/R40.

### Proteus Pizzicato (P2)

- **Inspired by:** E-mu Proteus/1 and Proteus/2 'Pizzicato' (90s TV and game score staple)
- **Character:** A very short plucked attack, 150 to 250 ms decay, no sustain; woody, mid-heavy, with a small room tail.
- **Start DNA:** `xpringin@10]E#8U2~6;A0D200S0R120`
- **Sources:** `xpringin`, `default`, `exclaim`
- **Recipe:**
  - Keep only the first 10% of xpringin (marimba-like ring phrase) as one plucked note.
  - One echo adds the 'section in a room' smear.
  - [planned offsets] 2 recorders 0 / 9 ms apart for a section flam.
  - Also try default@15] (XP Default's mallet bong).

### Proteus/2 Orchestral Tutti (P2)

- **Inspired by:** E-mu Proteus/2 Orchestral 'Tutti' / 'Strings+Brass' and the stacked-orchestra presets
- **Character:** Strings, brass and timpani in one big octave-stacked chord. Slow-ish attack, broad stereo, and a long hall release.
- **Start DNA:** `tada@10[#6H0,12U2~8/logoff@30[#6H0,-12U2~10/critstop<@5]#2FL60;A80S90R1400`
- **Sources:** `tada`, `logoff`, `critstop`, `startup`
- **Recipe:**
  - tada with its first transient cut off acts as the brass section; harmony gives octaves.
  - Mid-logoff an octave below is the string bed.
  - The critstop low hit, slowed, is the timpani/bass drum on the downbeat.
  - [planned macro] M1 = brass vs strings crossfade.

### Proteus World Kalimba (P1, rank 23)

- **Inspired by:** E-mu Proteus World / Planet Earth 'Kalimba' (also Alchemy and Omnisphere kalimbas)
- **Character:** A thumb-pluck click, then a clean, slightly inharmonic tine tone. 400 to 700 ms decay with a soft woody body; very 'Aero'.
- **Start DNA:** `xpding@25]#10/start>#4FL50;A0D600S0R250`
- **Sources:** `xpding`, `xpnotify`, `balloon`, `start`
- **Recipe:**
  - The front of xpding gives a bright tine.
  - The start.wav click at x2 speed is the thumb.
  - Mix them in one buffer instead: xpding@25]Mstart, if you want a single-recorder voice.
  - [planned offsets] click at 0 ms, tine at 3 ms.
  - Play an octave higher with T12 for music-box shimmer.

### Planet Phatt Hip-Hop Kit (P3)

- **Inspired by:** E-mu Planet Phatt / Mo'Phatt drum kits (90s hip-hop and R&B ROM)
- **Character:** Punchy, slightly crunchy drums: a boomy kick, a short snare crack and tight hats. The drums are mono and up front, with some 12-bit sampler bite.
- **Start DNA:** `critstop<<@6]++#4F/recycle>>@4]#6F/start>>#6F;A0R80`
- **Sources:** `critstop`, `error`, `recycle`, `start`, `menu`
- **Recipe:**
  - Layer 1: the attack of critstop at -2 octaves, clipped with ++, gives the kick boom.
  - Layer 2: a crumple grain at x4 is the snare and hat noise.
  - Layer 3: start.wav at x4 is the rim/hat tick.
  - Velocity at full (V100); every layer F, so each sound stays at one pitch. Map them to keys via the future per-key split, or play each layer alone.
  - Use >< (the decimation round trip) for SP-1200 grit.

### Mo'Phatt Fat Bass (P2)

- **Inspired by:** E-mu Mo'Phatt / Orbit 'Phat bass' presets
- **Character:** A round, sub-heavy, slightly distorted synth bass with a quick 'thump' decay into a sustained tone. Mono.
- **Start DNA:** `error<<@40]+++#8/error<<<@40]#4L70;A2D180S75R90V90`
- **Sources:** `error`, `critstop`, `batlow`
- **Recipe:**
  - The front of XP Error two octaves down is the low two-note, cut to the first tone.
  - +++ hard-clips it into a fat square-ish wave.
  - A third octave down mixed under it is the sub.
  - [planned env graph] 180 ms decay to 75% gives the 'thump'.

### Orbit Dance Stab (P2)

- **Inspired by:** E-mu Orbit 9090 dance stabs and hits (late-90s rave and big beat)
- **Character:** A short, loud, chordal hit with a bright transient and some noisy rave grit. It decays in 250 ms.
- **Start DNA:** `chord@35]++E#12H0,7;A0D250S0R150`
- **Sources:** `chord`, `tada`, `exclaim`
- **Recipe:**
  - The first third of chord.wav, clipped with ++ and echoed once, gives the stab.
  - H0,7 adds a fifth for the rave power-chord.
  - [planned macro] M1 = clip amount (0 to 3 '+').

### Vintage Keys Rhodes (P1, rank 19)

- **Inspired by:** E-mu Vintage Keys 'Suitcase' / 'Stage 73' Rhodes
- **Character:** Bell-like tine on top of a warm, sine-ish body. It barks a little when you play hard, sustains long, and has a gentle stereo tremolo.
- **Start DNA:** `default@50]#8/ringout@30[@30]<#6L60;A2D1800S30R400V90`
- **Sources:** `default`, `ringout`, `xpnotify`
- **Recipe:**
  - XP Default's soft mallet is the tine strike.
  - A steady ringout chunk an octave down is the sine body.
  - [planned pan] stereo tremolo: alternate recorders L60 and R60 at the same volume and use the planned volume automation on M1 for the tremolo.
  - [planned macro] M2 = bark (adds a ++ clipped copy layer at high velocity).

### Vintage Keys Mellotron Flute (P2)

- **Inspired by:** E-mu Vintage Keys 'Mellotron Flute' ('Strawberry Fields Forever')
- **Character:** Warbly tape flute with a soft breathy attack, slight pitch wow and a hard 8-second tape cutoff. Lo-fi, mid-range.
- **Start DNA:** `ringout@20[@50]#8U2~12/recycle>>@5]#4FL25;A60S95R300`
- **Sources:** `ringout`, `xpringout`, `recycle`
- **Recipe:**
  - The sine-like ringout middle is the flute.
  - Unison +/-12 cents acts as tape wow.
  - Crumple breath sits underneath.
  - No tape cutoff is needed: Sound Recorder's buffer end is the 8-second stop.

### Emulator III Grand (P3)

- **Inspired by:** E-mu Emulator III / Proteus 'Grand Piano' (90s 'pop piano')
- **Character:** A clean, bright, compressed piano with a hammer knock and a long decay. Not much body, but it cuts through a mix.
- **Start DNA:** `chord@8[@60]#8/default@10]#4FL40;A0D2500S20R500`
- **Sources:** `chord`, `default`, `exclaim`
- **Recipe:**
  - chord.wav has a piano-ish attack: trim the very first click and keep the bloom.
  - XP Default's front is the hammer knock.
  - For the Korg house piano, see 'M1 Piano 16''.

### Proteus 3 Ethnic Gamelan (P2, plays on 3.11 too)

- **Inspired by:** E-mu Proteus/3 World 'Gamelan' and 'Bonang'
- **Character:** Metallic, slightly detuned pairs of struck bronze tones that beat against each other, with a long shimmering decay.
- **Start DNA:** `chimes@20]#8U2~22/chimes@20]>#6U2~18L60;A0D2000S0R900`
- **Sources:** `chimes`, `ding`, `xpding`
- **Recipe:**
  - The first strike of chimes gives the gong-chime partials.
  - Gamelan's paired-tuning shimmer is a wide unison: +/-22 cents.
  - An octave-up copy adds the bonang ring.
  - [planned pan] voice pairs hard L/R so the beating rotates.

### Emulator Orchestra Hit (P1, rank 3)

- **Inspired by:** Fairlight CMI ORCH5 (Stravinsky Firebird) via the E-mu Emulator and every ROM after it
- **Character:** THE stab: a full-orchestra chord in one 300 ms hit. Huge transient, brassy mid, quick decay and lo-fi bite. Usually played in octaves.
- **Start DNA:** `tada@25]++E#10H0,12/critstop@10]<#6L80;A0D300S0R200V70`
- **Sources:** `tada`, `critstop`, `exclaim`, `chord`
- **Recipe:**
  - The first fanfare hit of tada.wav is already an orchestral stab: keep the first 25%.
  - ++ for bite, E for the hall.
  - Play H0,12 (octaves), like 'Owner of a Lonely Heart' and Art of Noise.
  - critstop slowed an octave adds the low brass/timpani weight.
  - On 3.11, tada falls back to ding. There, use chimes<@15]++ as a thinner hit.


## Roland (D-50, U-20/U-220, JV/XV, Sound Canvas, MT-32, JD, Alpha Juno)

### Fantasia (P1, rank 4)

- **Inspired by:** Roland D-50 preset 'Fantasia' (the most famous D-50 sound; Jean-Michel Jarre, 'Wonderful Life' era)
- **Character:** A bright, bell-like attack transient (a PCM 'chiff' plus a synth bell) layered on a soft, warm, chorused pad that swells in behind. Wide chorus, plenty of reverb. Sparkle on top, warmth below.
- **Start DNA:** `xpding@30]#6H0,12/startup@25[@40]<#8U3~10L70;A0D900S55R1500`
- **Sources:** `xpding`, `startup`, `logon`, `xpnotify`
- **Recipe:**
  - Layer 1: the front of xpding, with an octave above, is the bell strike.
  - Layer 2: the middle of the XP Startup pad an octave down, U3 at +/-10 cents, is the warm chorused bed.
  - [planned env graph] layer 1 starts at 100% and decays in 900 ms; layer 2 rises over 600 ms and holds. That crossfade is the D-50 'LA' trick.
  - [planned pan] layer 2's unison voices at L50/C/R50 imitate the D-50 chorus.
  - [planned macro] M1 = bell vs pad balance.

### Digital Native Dance (P1, rank 17)

- **Inspired by:** Roland D-50 'Digital Native Dance' (looped PCM percussion pad)
- **Character:** A rhythmic, looping PCM transient pattern (a kind of 'tick-tock' tribal motion) running under a sustained pad. The motion comes from the loop itself, with no LFO.
- **Start DNA:** `start>@0CP@0CP@0CP@0CPE#6F/logon<@30[#8U2~8L70;A20S90R900`
- **Sources:** `start`, `menu`, `xpstart`, `popup`, `logon`
- **Recipe:**
  - Layer 1: build a rhythmic loop by doubling start.wav four times with @0CP (16 repeats), plus echo for syncopation. F keeps it at fixed tempo.
  - Layer 2: the logon pad, slowed, for the harmonic bed.
  - Variation: mix a crumple grain into the loop: start>@0CP@0CPMrecycle@0CP@0CP.
  - [planned offsets] start a second loop recorder 1/3 of the click period late for polyrhythm.

### Staccato Heaven (P2)

- **Inspired by:** Roland D-50 'Staccato Heaven' (bright staccato chime-pad)
- **Character:** Short glassy staccato chime attacks on every note, over a shimmering airy sustain. Strongly 'synth-pop heaven': bright, chorused, reverberant.
- **Start DNA:** `chimes>@20]E#8H0,12/logon@40[#8U2~9L55;A0D400S40R1200`
- **Sources:** `chimes`, `logon`, `print`, `xpnotify`
- **Recipe:**
  - chimes at x2, front 20%, echoed: a glass staccato.
  - The airy tail of logon as the heavenly sustain.
  - [planned env graph] fast decay on layer 1, slow rise on layer 2.

### D-50 Pizzagogo (P3)

- **Inspired by:** Roland D-50 'Pizzagogo' (pizzicato-plus-bell)
- **Character:** Plucky pizzicato with a bell overtone. Very short, bouncy, made for ostinatos.
- **Start DNA:** `xpringin@8]#8/xpding@15]>#4L50;A0D180S0R120`
- **Sources:** `xpringin`, `xpding`, `default`
- **Recipe:**
  - The front of xpringin is the pluck; the octave-up xpding front is the bell overtone.

### D-50 Breathy Chiffer (P2)

- **Inspired by:** Roland D-50 'Breathy Chiffer' (pan-flute-ish)
- **Character:** A breathy noise chiff into a pure tone with gentle vibrato; ethereal, 'new age'.
- **Start DNA:** `ringout@25[@40]#8U2~7/minimize>@15]#3FL35;A40S90R600`
- **Sources:** `ringout`, `minimize`, `recycle`
- **Recipe:**
  - The ringout middle is the tone; the start of the minimize whoosh is the chiff.

### U-20 Piano/Strings (P3)

- **Inspired by:** Roland U-20 / U-220 'Piano & Strings' split-layer combis (early-90s rompler)
- **Character:** A bright 'RS-PCM' piano attack layered with a lush slow string pad. Thin, clean and very early-90s ballad.
- **Start DNA:** `chord@5[@50]#8/logoff@30[#8U3~10L60;A0D1500S40R1200`
- **Sources:** `chord`, `logoff`, `startup`
- **Recipe:**
  - chord.wav bloom for the piano; mid-logoff for the strings with a slow attack (planned env on layer 2 only).

### JV-1080 Velo Strings (P2)

- **Inspired by:** Roland JV-1080/2080 strings ('Velo Strings', 'Symphonic Str') plus SR-JV80-02 Orchestral
- **Character:** Big, smooth, high-res string section: a slow attack, a wide stereo hall and an ensemble shimmer. Bright when played hard.
- **Start DNA:** `logoff@25[#10U3~12/shutdown@30[<#6U2~8L50;A250S95R1500V60`
- **Sources:** `logoff`, `shutdown`, `startup`
- **Recipe:**
  - logoff and shutdown both have soft string-like shimmer; their attack transients are deleted.
  - [planned env graph] attack time follows velocity, and M1 ('expression') scales volume.

### JV Pulse Arp (P3)

- **Inspired by:** Roland JV-1080 'Pulse Pad'/'Ambient' sequenced presets and the XP-50 'Arp' patches
- **Character:** A tight, gated, ticking pad, a pulsing 16th-note motion baked into one held note.
- **Start DNA:** `logon@20[@40]@0CP@0CP#8U2~6/start>>#4FL30;A5S80R300`
- **Sources:** `logon`, `startup`, `start`
- **Recipe:**
  - Cut a short chunk of logon and paste-insert copies of it: the seam at each copy boundary gives a rhythmic 'gate' pulse.
  - A click layer marks the beats.
  - [planned env graph] draw a gate shape (steps).

### Sound Canvas Fantasia/Halo (P2)

- **Inspired by:** Roland SC-55 GM 'Fantasia' (program 89 'Pad 1 New Age') and 'Halo Pad'
- **Character:** The GM-sized Fantasia: thinner and grainier than the D-50 original. Instantly recognizable 'MIDI file' nostalgia.
- **Start DNA:** `xpding@30]#6H0,12/notify<@20[#8U2~8L60;A0D700S50R900`
- **Sources:** `xpding`, `notify`, `chimes`
- **Recipe:**
  - Same idea as Fantasia, with a smaller unison and a shorter release: GM ROM economy is part of the charm.

### SC-55 Choir Aahs (P1, rank 8)

- **Inspired by:** Roland Sound Canvas GM 53 'Choir Aahs' (and every GM module since)
- **Character:** A soft, slightly nasal 'aah' section with a 200 to 400 ms swell, a little vibrato and a gentle loop. Low top end.
- **Start DNA:** `notify<#8U3~12/xpnotify<<@20[#6U2~10L60;A300S90R900V40`
- **Sources:** `notify`, `xpnotify`, `logon`
- **Recipe:**
  - Slowed notify and xpnotify give vowel-like mid-range tones; unison makes the choir.
  - [planned env graph] a slight dip at 400 ms gives the GM loop-point feel.

### SC-55 Voice Oohs (P2)

- **Inspired by:** Roland Sound Canvas GM 54 'Voice Oohs'
- **Character:** A rounder, darker, almost-sine 'ooh' with a slower onset than Aahs. Breathy and intimate.
- **Start DNA:** `ringout@20[@50]<#8U3~9/recycle>@5]#2FL15;A400S90R1100V40`
- **Sources:** `ringout`, `xpringout`, `notify`
- **Recipe:**
  - ringout gives a sine-ish 'oo'; a whisper of crumple adds breath.

### SC-55 Square Lead / GM Ocarina (P2)

- **Inspired by:** Roland Sound Canvas GM 81 'Square Lead' and GM 80 'Ocarina'
- **Character:** Pure hollow square/sine lead with instant attack: 'video game MIDI' melody voice.
- **Start DNA:** `batlow@5[@20]@0CP@0CP@0CP+++#8;A5S100R150`
- **Sources:** `batlow`, `batcrit`, `ringout`
- **Recipe:**
  - Grab a tiny steady chunk of XP Battery Low, multiply it with @0CP into a sustained tone, then +++ clip it square.

### MT-32 Fantasy Bell (P2, plays on 3.11 too)

- **Inspired by:** Roland MT-32 / CM-32L 'Fantasy' & game-music bells (Sierra, LucasArts soundtracks)
- **Character:** Crunchy LA-synthesis bell with a PCM attack. 15-bit grit, a short reverb tail and a slightly aliased top.
- **Start DNA:** `chimes@30]><#8H0,12/ding><#4L50;A0D1200S0R600`
- **Sources:** `chimes`, `ding`, `xpding`
- **Recipe:**
  - The >< round trip decimates (drops every other sample, then doubles), for MT-32-ish aliasing at the same pitch. Verify in reference mode.
  - Layer chimes and ding for the PCM 'ting'.

### MT-32 Slap Bass (P2)

- **Inspired by:** Roland MT-32 'SlapBass 1' (Monkey Island, King's Quest)
- **Character:** A thumb-slap transient into a short, buzzy, nasal bass. Unmistakably DOS-game.
- **Start DNA:** `error<@15]++#8/start<#4FL60;A0D300S30R80`
- **Sources:** `error`, `start`, `critstop`
- **Recipe:**
  - The XP Error tone, slowed and clipped, gives the buzzy bass; start.wav slowed down is the slap click.

### XV Supersaw Pad (P1, rank 20)

- **Inspired by:** Roland XV-5080 / JP-8000 'Supersaw' trance pad and lead (late-90s trance)
- **Character:** Seven detuned saws: a bright buzzy spectrum, a wide stereo and a constantly beating chorus motion.
- **Start DNA:** `chord@20[@30]@0CP@0CP@0CP++#16U8~35;A20S95R700`
- **Sources:** `chord`, `error`, `tada`
- **Recipe:**
  - Make a looped steady tone from chord.wav (@0CP doubling), clip it with ++ toward a saw-like buzz.
  - U8~35 gives eight unison voices over +/-35 cents. That beating IS the supersaw.
  - [planned pan] alternate unison voices L/R across the field.

### JD-800 Glass Voices (P2)

- **Inspired by:** Roland JD-800/JD-990 'Glass Voices' and 'Digital Native' style PCM-choir pads
- **Character:** A high, glassy choir with a crystalline top and slow evolving shimmer. 90s 'digital heaven'.
- **Start DNA:** `chimes>R#6U2~10/notify<#8U3~10L70;A500S90R1500`
- **Sources:** `chimes`, `notify`, `logon`
- **Recipe:**
  - Reversed chimes at x2 for a crystalline glass swell, over the notify choir.

### Alpha Juno 'Hoover' (P2)

- **Inspired by:** Roland Alpha Juno 2 'What The' / the Hoover (Joey Beltram 'Mentasm', 1991)
- **Character:** A huge, detuned, pulse-width-modulated, chorused buzz with a downward pitch swoop. Aggressive and seasick.
- **Start DNA:** `error@10[@40]@0CP@0CP@0CP+++#16U8~60;A10S100R400B12`
- **Sources:** `error`, `critstop`, `restore`
- **Recipe:**
  - A looped error tone, hard-clipped for the buzz.
  - U8~60 gives the extreme detune.
  - B12 so the pitch bend gives the swoop. Without automation, pre-bake the swoop by adding a reversed 'restore' whoosh layer.


## Korg (M1, Wavestation, Triton)

### M1 Piano 16' (P1, rank 1)

- **Inspired by:** Korg M1 'Piano 16'' (house piano: Robin S, Crystal Waters, Black Box, 90s house)
- **Character:** A bright, clangy, mid-forward piano, layered with an octave so the chord stabs ring. The decay is fast. It is compressed, almost metallic, and made to stab offbeats.
- **Start DNA:** `chord@5[@45]#10H0,12/xpding@20]#6L40;A0D1200S15R250V60`
- **Sources:** `chord`, `xpding`, `exclaim`, `default`
- **Recipe:**
  - chord.wav (it already sounds like a struck chord) with the click trimmed; H0,12 adds the 16' octave doubling.
  - A bit of xpding for metallic clang.
  - Play chords: each note gives 2 voices, so the 16-recorder pool allows ~5-note chords per layer split. Recommend #10/#6.
  - [planned macro] M1 = brightness (an xpding level).

### M1 Organ 2 (P1, rank 6)

- **Inspired by:** Korg M1 'Organ 2' (Robin S 'Show Me Love', 1993: the most famous rompler organ)
- **Character:** A percussive organ 'bark': a sharp, pitched click attack, then a short, round, hollow tone that decays to a low sustain. Played as a syncopated bass riff.
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CP#8H0,12,19/start>#4FL70;A0D220S35R90`
- **Sources:** `ringout`, `xpringout`, `start`, `menu`
- **Recipe:**
  - Make a sustained sine-ish organ tone from a steady ringout chunk doubled with @0CP.
  - H0,12,19 = 8', 4' and 2 2/3' drawbars.
  - The x2 start.wav click is the key-click percussion.
  - [planned env graph] 220 ms drop to 35%: that decay IS the M1 Organ 2 bark.

### M1 Universe (P1, rank 15)

- **Inspired by:** Korg M1 'Universe' (space pad: glassy bells over a wide airy pad)
- **Character:** A huge, slowly evolving space pad: a soft digital bell attack, a glassy upper partial band and a long, wide stereo tail.
- **Start DNA:** `startup@20[<#8U3~12/chimes>R#6U2~8L60;A700S90R2500`
- **Sources:** `startup`, `logon`, `chimes`, `shutdown`
- **Recipe:**
  - Slowed XP Startup without its intro is the evolving universe wash.
  - Reversed, sped-up chimes shimmer in on every note.
  - [planned pan] wide; [planned macro] M1 = shimmer level.

### M1 Fretless (P2)

- **Inspired by:** Korg M1 'Fretless' bass (90s pop/R&B)
- **Character:** A smooth, singing fretless bass: round, sine-heavy, with a gentle 'mwah' attack. Sustained.
- **Start DNA:** `ringout@20[@40]<<#8/default<<@10]#4L40;A15D500S70R150`
- **Sources:** `ringout`, `default`, `batlow`
- **Recipe:**
  - Two-octave-down ringout chunk = sine bass, XP Default front for the finger 'mwah'.

### M1 Lore / Choir (P2)

- **Inspired by:** Korg M1 'Lore' and 'Choir' (PCM choir, ambient 90s)
- **Character:** A breathy digital choir with a long reverb and a slightly hollow loop. Ethereal.
- **Start DNA:** `notify<R#8U3~10/notify<#6U2~8L70;A600S90R1800`
- **Sources:** `notify`, `logon`, `xpnotify`
- **Recipe:**
  - A reversed slowed notify gives the 'breath-in' swell, with a forward notify for body.

### Wavestation Glass Pad (P1, rank 18)

- **Inspired by:** Korg Wavestation 'Glass Mountain'/'Spectrum' vector pads (Wave Sequencing)
- **Character:** A pad that never sits still: short PCM fragments crossfade in sequence, making a rhythmic, shimmering, glassy motion inside one held note.
- **Start DNA:** `chimes@40]IxpdingIchimes>Iprint@0CP#8U2~6/logon<#8L50;A80S90R1600`
- **Sources:** `chimes`, `xpding`, `print`, `logon`, `xpnotify`
- **Recipe:**
  - Wave sequencing = Insert File chain: chimes, then xpding, then chimes x2, then print, all spliced in one buffer.
  - Copy-paste doubles the sequence.
  - The logon pad underneath is the vector-blend bed.
  - [planned macro] M1/M2 = vector X/Y: crossfade 4 recorder layers (A/B/C/D) with the planned non-baked volume.

### Wavestation 'Ocean Bed' (P3)

- **Inspired by:** Korg Wavestation noise/ambient vector pads
- **Character:** A slow-moving, filtered-noise wash that sounds like breaking surf, with tonal glints.
- **Start DNA:** `recycle<<<EE#6F/minimize<<R#4F/xpnotify<@20[#6L40;A1200S90R2500`
- **Sources:** `recycle`, `xprecycle`, `minimize`, `restore`, `xpnotify`
- **Recipe:**
  - Crumple at -3 octaves sounds like surf; minimize/restore whooshes slowed and reversed are swells; a soft tone gives pitch.

### Triton Pop Piano / Strings (P3)

- **Inspired by:** Korg Triton 'Dance Piano' and 'Str Ensemble' (Y2K pop and R&B)
- **Character:** A crisp, glossy, stereo piano with a modern bright sheen, often layered with a soft string pad. Very Y2K TRL.
- **Start DNA:** `chord@5[@50]#8H0,12U2~4/logoff@30[#8U2~10L50;A0D1800S30R900`
- **Sources:** `chord`, `logoff`, `exclaim`
- **Recipe:**
  - Like M1 Piano 16', but with a slight unison and a string pad underneath.

### Triton Hip-Hop Pluck (P2)

- **Inspired by:** Korg Triton 'Pluck'/'Koto' & pizzicato presets (2000s hip-hop: Timbaland, Swizz Beatz)
- **Character:** A dry, short, exotic-sounding pluck (koto- or harp-like) with a clean digital attack, cutting through a sparse beat.
- **Start DNA:** `xpringin@6]#12;A0D160S0R80V80`
- **Sources:** `xpringin`, `default`, `exclaim`
- **Recipe:**
  - The front of the XP Ringin marimba phrase is the dry pluck.
  - [planned offsets] for a harp gliss feel, chain recorders 15 ms apart.

### Korg M1 Bell / 'Pole' (P3)

- **Inspired by:** Korg M1 'Bell'/'Tines' family and Triton 'Pole Bells'
- **Character:** A pure, bright bell attack with a long, singing decay. Classic 90s ballad sparkle.
- **Start DNA:** `xpding>#8H0,12/chimes@20]#4L50;A0D2500S0R1200`
- **Sources:** `xpding`, `chimes`, `print`
- **Recipe:**
  - xpding up an octave rings like a pole bell; the chimes front adds the clang.


## Yamaha (DX7, TX81Z, SY77, Motif)

### DX7 E.PIANO 1 (P1, rank 2)

- **Inspired by:** Yamaha DX7 ROM1A 'E.PIANO 1' (the most used preset of the 80s: Whitney, Lionel Richie, every ballad)
- **Character:** A glassy FM 'tine' attack transient, with a sharp metallic bell harmonic, over a pure sine-like body. Hard playing brings out more bell. Long, clean decay, mild chorus, no real hammer noise.
- **Start DNA:** `xpding@20]#6H0,24/ringout@25[@35]#8L80;A0D1600S25R350V90`
- **Sources:** `xpding`, `ringout`, `xpnotify`, `default`
- **Recipe:**
  - Layer 1: the xpding front with two octaves up (H0,24) is the metallic tine bell.
  - Layer 2: a sine-ish ringout chunk is the body.
  - Velocity matters: [planned macro] M1 tied to velocity adds layer-1 level (bell on hard hits).
  - [planned pan] 2 recorders per note with +/-6 cents and L30/R30 for the classic chorus.

### DX7 BASS 1 / Solid Bass (P2)

- **Inspired by:** Yamaha DX7 'BASS 1' / 'SOLID BASS' (80s FM bass: a-ha, Kenny Loggins)
- **Character:** A snappy FM pluck with a percussive 'thwack' of upper harmonics. They decay in 100 ms, leaving a round, solid low tone.
- **Start DNA:** `error<<@30]+#8/xpding<<@8]#4L60;A0D350S50R80`
- **Sources:** `error`, `xpding`, `critstop`
- **Recipe:**
  - The XP Error low tone two octaves down is the body; a very short xpding front, slowed, is the FM 'thwack'.

### DX7 TUB BELLS (P2, plays on 3.11 too)

- **Inspired by:** Yamaha DX7 'TUB BELLS' and 'E.BELL'/'GLOCKEN' (inharmonic FM bells)
- **Character:** Inharmonic metallic partials, a strong strike and a very long, slowly beating decay. Cold and crystalline.
- **Start DNA:** `chimes@25]#8U2~15/ding>#6L60;A0D4000S0R2000`
- **Sources:** `chimes`, `ding`, `xpding`
- **Recipe:**
  - chimes and ding have real inharmonic bell spectra; a wide unison gives the FM beating.
  - Try EE> after the chimes trim for an extra metallic comb ring.

### DX7 Koto (P2)

- **Inspired by:** Yamaha DX7 ROM 'KOTO' (80s 'exotic' pluck, also Emulator 'Koto')
- **Character:** A twangy, bright pluck with a fast pitch-drop 'ping', then a short nasal decay with metallic string buzz.
- **Start DNA:** `xpringin@5]EE>#10/start>>#4FL30;A0D500S0R250`
- **Sources:** `xpringin`, `xpding`, `start`
- **Recipe:**
  - Echo then speed-up makes a short comb: the koto's buzzing 'sawari' resonance.
  - Play pentatonic (In scale) for the trope.

### TX81Z Lately Bass (P1, rank 5)

- **Inspired by:** Yamaha TX81Z preset 'LatelyBass' (Stevie Wonder 'Lately'; 90s house and R&B, everywhere)
- **Character:** A punchy FM bass. A bright, squelchy, rubbery attack drops fast into a hollow, nasal, slightly woody tone. The attack has a 'pluck', like a filter blip.
- **Start DNA:** `error<@25]++#8/hwin<@20]#4L60;A0D250S40R70V90`
- **Sources:** `error`, `hwin`, `critstop`, `balloon`
- **Recipe:**
  - Clipped XP Error an octave down is the hollow tone.
  - The front of Hardware Insert (a rising 'bloop'), slowed, gives the rubbery squelch on the attack.
  - [planned env graph] 250 ms decay to 40%, a quick 70 ms release.

### TX81Z / FB-01 'Wood Piano' (P3)

- **Inspired by:** Yamaha TX81Z/FB-01 'WoodPiano' & 4-op keys (DOS game and 90s budget-studio sound)
- **Character:** A dull, woody, bell-tinged 4-op keyboard: thin, but warm and nostalgic.
- **Start DNA:** `default@40]#10/xpnotify@20]#4L40;A0D900S20R200`
- **Sources:** `default`, `xpnotify`
- **Recipe:**
  - XP Default's mallet; a touch of xpnotify.

### SY77 / SY99 'Pacific Rim' (P3)

- **Inspired by:** Yamaha SY77/SY99 AFM+AWM pads and 'Pacific Rim'-style breathy pads
- **Character:** A digital FM shimmer layered over sampled breath: wide, modern-1990, almost choral.
- **Start DNA:** `logon@20[#8U3~10/chimes>R#4L50/recycle<<#4FL20;A500S90R1800`
- **Sources:** `logon`, `chimes`, `recycle`
- **Recipe:**
  - Logon pad, reversed glass, and slowed crumple air.

### DX7 Harmonica / Flute 1 (P3)

- **Inspired by:** Yamaha DX7 'HARMONICA' and 'FLUTE 1' (FM wind with vibrato)
- **Character:** A reedy, slightly buzzy FM tone with a breathy onset and natural vibrato motion.
- **Start DNA:** `batcrit@10[@20]@0CP@0CP@0CP+#8U2~10;A50S95R180`
- **Sources:** `batcrit`, `batlow`, `ringout`
- **Recipe:**
  - A steady chunk of XP Battery Critical (a sine-ish alert), looped and lightly clipped, gives the reed.

### Motif/Montage 'Full Grand' sparkle (P3)

- **Inspired by:** Yamaha Motif 'Full Concert Grand' (2000s workstation piano)
- **Character:** A wide, glossy, modern stereo piano: clear attack, long bloom.
- **Start DNA:** `chord@5[#8H0,12U2~3/exclaim@15]#4L35;A0D3000S20R700`
- **Sources:** `chord`, `exclaim`
- **Recipe:**
  - Same base as M1 Piano, but a slower decay and less clang.

### DX7 'Rhodes + Strings' ballad (P3)

- **Inspired by:** Yamaha DX7 E.PIANO layered with strings (the 80s power ballad combination)
- **Character:** An FM EP strike with a soft string wash fading in behind it.
- **Start DNA:** `xpding@20]#6H0,24/ringout@25[@35]#5L70/logoff@30[#5U2~10L50;A0D1500S40R1200`
- **Sources:** `xpding`, `ringout`, `logoff`
- **Recipe:**
  - E.PIANO 1 plus a mid-logoff string bed. [planned env graph] the string layer rises slowly.


## Kurzweil and Ensoniq (Mirage, ESQ-1, VFX, EPS, K250/K2000)

### Mirage Grit Piano (P2)

- **Inspired by:** Ensoniq Mirage (8-bit sampler, 1984) factory piano and strings
- **Character:** Low-res, aliased, noisy-but-musical samples, with a resonant analog filter and short loops. Charming crunch.
- **Start DNA:** `chord><><#8/chord><><>#4L40;A0D1200S30R300`
- **Sources:** `chord`, `chimes`, `ding`
- **Recipe:**
  - Repeated >< decimation round trips (hypothesis: naive sample-dropping) for 8-bit/low-rate grit.
  - The 3.11 edition's native 8-bit 11 kHz WAVs (chimes/ding) are already Mirage-grade.

### ESQ-1 Digital Pad (P3)

- **Inspired by:** Ensoniq ESQ-1 / SQ-80 'Digital waves' pads (hybrid digital waves through analog filter)
- **Character:** Thin-edged digital waves, warmed by detune. The movement comes from wave crossfades. Metallic but cozy.
- **Start DNA:** `notify@20[@30]@0CP@0CP@0CP#8U3~14/chimes@30]<#4L40;A300S85R900`
- **Sources:** `notify`, `chimes`, `ringout`
- **Recipe:**
  - A looped notify chunk is the 'digital wave'; detune warms it; a chimes ping on each attack.

### VFX 'Digital Piano'/'Ice' (P2)

- **Inspired by:** Ensoniq VFX/SD-1 'Transwaves' presets ('Ice' and glassy evolving waves)
- **Character:** Transwave scanning: the timbre sweeps across a set of waveforms during the note, a glassy morph from dull to bright.
- **Start DNA:** `ringout@30[@20]IxpdingIchimes>Iprint>#8U2~8;A80S90R1200`
- **Sources:** `ringout`, `xpding`, `chimes`, `print`
- **Recipe:**
  - A transwave approximated as a time-ordered splice from dull (ringout) to bright (x2 print) with Insert File.
  - Because it plays through, the timbre 'scans' over the note.

### Kurzweil K2000 'Hollow Pad'/'Pad Glass' (P3)

- **Inspired by:** Kurzweil K2000/K2500 VAST pads (and the K250's famous 'Stereo Grand')
- **Character:** Deep, hollow, resonant pads with phasey, comb-like motion. Very 90s film and ambient.
- **Start DNA:** `logon@20[C@3X#8U2~8/shutdown<@20[#6L60;A600S90R2000`
- **Sources:** `logon`, `shutdown`, `startup`
- **Recipe:**
  - Mixing a copy of itself at a 3% offset (C@03X) gives a static comb: the VAST 'hollow' resonance.

### Kurzweil K250 Stereo Grand (P3)

- **Inspired by:** Kurzweil K250 (1984) 'Grand Piano', the first convincing sampled piano
- **Character:** A bright, punchy, fairly short-looped grand with a strong hammer.
- **Start DNA:** `chord@4[#8/default@8]#4L50;A0D2200S15R400`
- **Sources:** `chord`, `default`
- **Recipe:**
  - chord bloom plus a mallet knock.

### Mirage 'Choir' (P3)

- **Inspired by:** Ensoniq Mirage / EPS choir disks (Depeche Mode era)
- **Character:** A gritty, short-looped choir with an audible loop pulse. Melancholic 80s.
- **Start DNA:** `notify<><@20[@40]@0CP@0CP#8U2~12;A250S90R800`
- **Sources:** `notify`, `logon`
- **Recipe:**
  - Decimated slowed notify, chunk-looped so the loop pulse is audible: authentically Mirage.

### EPS 'Orchestra Stab' (P3)

- **Inspired by:** Ensoniq EPS / ASR-10 hip-hop stabs (90s boom bap)
- **Character:** A chopped, gritty orchestral stab with crate-digging dust.
- **Start DNA:** `tada@20]><++#12H0,12;A0D350S0R150`
- **Sources:** `tada`, `critstop`
- **Recipe:**
  - Orch hit with decimation and clip.


## Pad and texture soft synths (Absynth, Omnisphere, Alchemy, Massive, Serum, Spire, Sylenth, Nexus, Zebra, Kontakt, Ethno World)

### Absynth Evolving Atmosphere (P1, rank 29)

- **Inspired by:** NI Absynth factory atmospheres ('Aetherizer'-style granular, multi-segment envelope pads)
- **Character:** A pad that keeps changing for 10+ seconds: multi-segment envelopes, granular flicker, drifting pitch shimmer. Cinematic and alien.
- **Start DNA:** `startup<<#4U2~20/logon<R#4/chimes>>R#4/recycle<<<#4FL20;A1500S80R4000`
- **Sources:** `startup`, `logon`, `chimes`, `recycle`, `shutdown`
- **Recipe:**
  - Four layers, each a different timescale: startup at -2 octaves (very slow wash), reversed logon (swells), reversed x4 chimes (glints), and slowed crumple (grain flicker).
  - [planned env graph] multi-segment, one per layer, at staggered peaks (2 s, 4 s, 7 s): the core of the Absynth feel.
  - [planned offsets] staggered recorder start times so the layers enter one after another.
  - [planned macro] M1 = 'evolution' (scales the env graph time).

### Omnisphere Evolving Pad (P1, rank 30)

- **Inspired by:** Spectrasonics Omnisphere ('Analog Pad Dreams', 'Hardware Library', and the 'Coldplay pad' type)
- **Character:** A warm analog-ish pad core, a granular/texture layer moving over it, a slow filter breathing, a huge stereo and long tails.
- **Start DNA:** `startup@15[<#8U3~14/logoff<R#4L60/minimize<<#4FL25;A900S90R3000`
- **Sources:** `startup`, `logoff`, `minimize`, `restore`
- **Recipe:**
  - A warm core, a reversed swell and a slowed whoosh as the 'texture layer'.
  - [planned macro] M1 = texture amount, M2 = motion (detune spread).

### Omnisphere 'Glass Harp' (P2)

- **Inspired by:** Omnisphere glass/psaltery family and 'Crystal Pad' types
- **Character:** Plucked glass with ringing high partials and a soft bowed swell behind it.
- **Start DNA:** `xpding>@30]#8U2~5/chimes>R#8L50;A0D1500S30R2000`
- **Sources:** `xpding`, `chimes`, `print`
- **Recipe:**
  - A sped-up xpding pluck, with a reversed sped-up chime swell behind it.

### Alchemy 'Spectral' Pad (P2)

- **Inspired by:** Apple/Camel Alchemy additive and spectral resynthesis pads
- **Character:** Smeared, frozen, resynthesized timbres: partials hang in time with a glassy, slightly phasey shimmer.
- **Start DNA:** `logon@30[@20]@0CP@0CP@0CP@0CPEE#8U2~8;A700S95R2500`
- **Sources:** `logon`, `startup`, `notify`
- **Recipe:**
  - A 'spectral freeze': take a short chunk, repeat it 16 times, then add echo to smear the seams.

### Massive Growl/Reese (P2)

- **Inspired by:** NI Massive (dubstep and DnB growls and reese basses)
- **Character:** A thick, detuned, distorted low buzz with a slow phasing motion; mono low end and gritty mids.
- **Start DNA:** `error<<@10[@30]@0CP@0CP@0CP++++#12U4~25;A5S100R200`
- **Sources:** `error`, `critstop`
- **Recipe:**
  - A clipped looped tone at -2 octaves; U4~25 gives the slow phasing beat.

### Serum Supersaw Pluck (P2)

- **Inspired by:** Xfer Serum future-bass and EDM plucks ('Future Bass Chord', 'Pluck Basic')
- **Character:** A detuned saw stack with a fast filter-pluck envelope: bright attack, a 300 ms decay into a soft sustain, a wide stereo field.
- **Start DNA:** `chord@20[@30]@0CP@0CP@0CP++#16U6~25;A0D300S20R400`
- **Sources:** `chord`, `tada`
- **Recipe:**
  - The supersaw core with a pluck envelope.
  - Future-bass chords: H0,4,7,11 (maj7) with #16. Each note eats 4 voices, so play one note.

### Spire Trance Lead (P2)

- **Inspired by:** Reveal Sound Spire (trance and big-room leads, 'Hypersaw')
- **Character:** A bright, wide, octave-stacked hypersaw lead that cuts and sings.
- **Start DNA:** `chord@20[@30]@0CP@0CP@0CP++#16H0,12U4~22;A5S100R300`
- **Sources:** `chord`, `error`
- **Recipe:**
  - The supersaw core plus an octave; pair it with an echo layer for the trance delay.

### Sylenth Classic Trance Pluck (P2)

- **Inspired by:** LennarDigital Sylenth1 ('Pluck' and 'Arp' factory presets, 2000s trance and progressive house)
- **Character:** A short, round-but-bright pluck with a hint of detune and a 1/8-dotted delay tail. Made for arps.
- **Start DNA:** `xpding@15]#8U2~10/xpding@15]<E>#4L45;A0D220S0R180`
- **Sources:** `xpding`, `default`, `balloon`
- **Recipe:**
  - Layer 2 uses <E> (slow down, echo, speed up) for a delay that is twice as long, at the original pitch.
  - [planned offsets] better: 3 recorders at 0 / 187 / 375 ms (dotted 1/8 at 120 bpm), at 100 / 50 / 25% volume, panned C/L/R.

### Nexus 'Trance Pad' (P3)

- **Inspired by:** reFX Nexus ROM ('Trance Pad', 'Hands Up' and 'Euro' supersaw pads)
- **Character:** A bright supersaw pad with a long release: euphoric, wall-of-sound.
- **Start DNA:** `chord@20[@30]@0CP@0CP@0CP+#16U8~30;A400S95R1500`
- **Sources:** `chord`
- **Recipe:**
  - Supersaw core with a slow attack.

### Zebra 'Dark Zebra' Cinematic (P2)

- **Inspired by:** u-he Zebra2 / Dark Zebra (Hans Zimmer cinematic pads and drones)
- **Character:** A dark, low, ominous drone pad with a slow, grinding metallic motion.
- **Start DNA:** `critstop<<#6U3~18/shutdown<<R#6L60/recycle<<<#4FL20;A1500S100R4000`
- **Sources:** `critstop`, `shutdown`, `recycle`
- **Recipe:**
  - critstop at -2 octaves is a doom bed; a reversed slow shutdown swells; slowed crumple adds grinding texture.

### Kontakt Factory 'Bowed Glass' (P2, plays on 3.11 too)

- **Inspired by:** Kontakt factory 'Synth Pads' and bowed-glass/waterphone FX (2000s scoring)
- **Character:** Glass bowed into a slow, eerie swell with pitchy shimmer and dissonant partials.
- **Start DNA:** `chimes>REE#8U2~25/ding>R#4L50;A800S90R2000`
- **Sources:** `chimes`, `ding`
- **Recipe:**
  - Reversed glassy chimes with echo smear and a wide detune for eeriness.

### Kontakt Factory 'Music Box' (P2)

- **Inspired by:** Kontakt factory 'Music Box' / celesta (and every lullaby in 2000s media)
- **Character:** A tiny tine pluck at a high register with a fast decay and a mechanical, slightly out-of-tune charm.
- **Start DNA:** `xpding@20]>#12U2~7;A0D900S0R400`
- **Sources:** `xpding`, `print`, `xpnotify`
- **Recipe:**
  - xpding up an octave; slight detune.

### Ethno World Duduk (P2)

- **Inspired by:** Best Service Ethno World duduk (Gladiator-style; 2000s film)
- **Character:** A mournful, nasal, reedy double-reed tone with breath, a slow swell and expressive vibrato.
- **Start DNA:** `batcrit@10[@20]@0CP@0CP@0CP<#8U2~9/recycle<@5]#2FL15;A250S95R600`
- **Sources:** `batcrit`, `notify`, `recycle`
- **Recipe:**
  - A looped sine-ish alert tone, slowed for a lower nasal register, plus breath.

### Ethno World Ethnic Vox (P3)

- **Inspired by:** Ethno World / Ethno Vocal chants ('Ethnic female vox', 'Lisa Gerrard' style)
- **Character:** Wordless, exotic, melismatic vocal wail with a long reverb and melancholy.
- **Start DNA:** `notify<<#6U2~10/xpnotify<R#4L60;A400S85R2000`
- **Sources:** `notify`, `xpnotify`
- **Recipe:**
  - A low notify vocal formant with a reversed swell.

### Omnisphere 'Pluck Box' Shimmer Arp (P2)

- **Inspired by:** Omnisphere/Keyscape arpeggiated shimmer plucks
- **Character:** A soft bell pluck with a long reverse-reverb shimmer tail building between notes.
- **Start DNA:** `xpding@20]#8/xpding@20]RER#4L50;A0D800S0R1500`
- **Sources:** `xpding`, `chimes`
- **Recipe:**
  - RER = reverse, echo, reverse: a pre-echo/reverse-reverb that swells into the note.

### Serum 'Granular Air' Pad (P3)

- **Inspired by:** Serum/Vital noise-wavetable airy pads
- **Character:** Breathy, hissy air with a tonal center: wind through a tube, a modern 'airy' top.
- **Start DNA:** `minimize<#4F/restore<#4F/ringout@20[@40]#8U2~8L60;A900S90R2500`
- **Sources:** `minimize`, `restore`, `ringout`
- **Recipe:**
  - Slowed minimize/restore whooshes as air (fixed pitch), over a sine-ish tone.


## Bass

### 808 Sub Boom (P1, rank 14)

- **Inspired by:** Roland TR-808 kick-as-bass (trap and hip-hop 808, sub-bass category benchmark)
- **Character:** A nearly pure sine at 40 to 60 Hz with a short click, a pitch drop at the start and a long decay. All weight, no top.
- **Start DNA:** `ringout@20[@40]<<<#8/start<#2FL50;A0D2500S40R200`
- **Sources:** `ringout`, `xpringout`, `start`, `batlow`
- **Recipe:**
  - ringout chunk at -3 octaves (sine-ish).
  - The slowed start.wav click is the 808 knock.
  - [planned env graph] a long decay.
  - Saturate with ++ for 'distorted 808'.

### Reese Bass (P1, rank 13)

- **Inspired by:** Kevin Saunderson 'Just Want Another Chance' Reese (DnB/jungle benchmark)
- **Character:** Two detuned saws beating against each other: a slow, menacing phasing motion with mono weight and a hollow, buzzy mid.
- **Start DNA:** `error<<@10[@30]@0CP@0CP@0CP+++#16U2~18;A5S100R150`
- **Sources:** `error`, `critstop`, `chord`
- **Recipe:**
  - U2~18 = exactly two voices +/-18 cents: the classic two-saw beat.
  - A clipped looped tone is the saw.
  - Lower the cents for a slower roll.

### FM Slap Bass (P2)

- **Inspired by:** Yamaha DX7 'SLAP BASS' / Korg M1 'SlapBass' (80s funk pop)
- **Character:** A metallic, percussive pop transient into a short, bright, twangy bass with a fast decay.
- **Start DNA:** `error<@20]++#8/start#4FL70;A0D220S20R60`
- **Sources:** `error`, `start`, `critstop`
- **Recipe:**
  - A clipped error front plus the start.wav click for the slap.

### Moog-style Deep Sub (P2)

- **Inspired by:** Minimoog / Model D bass (70s-80s funk, synth-pop)
- **Character:** A fat, round, warm low tone with a soft attack and a slight filter 'thump'.
- **Start DNA:** `error<<@40]+#8U2~5/ringout@20[@40]<<<#4L70;A5D300S70R120`
- **Sources:** `error`, `ringout`
- **Recipe:**
  - Error tone plus sine sub, lightly detuned.

### Acid 303 Squelch (P2)

- **Inspired by:** Roland TB-303 (acid house, benchmark squelch bass)
- **Character:** A resonant, rubbery, squelchy saw with an envelope-swept filter 'yow' and accents.
- **Start DNA:** `hwin<@10[@40]+++#8/hwout<@10[@40]++#8L80;A0D200S50R80`
- **Sources:** `hwin`, `hwout`, `balloon`
- **Recipe:**
  - Hardware Insert/Remove have rising/falling 'bloops' that act like a filter sweep; slowed and clipped they become the squelch.
  - Layer 1 = 'yow up', layer 2 = 'down'.
  - [planned macro] M1 = crossfade between them (cutoff), M2 = clip (resonance feel).

### Wobble Bass (P3)

- **Inspired by:** Dubstep LFO wobble (Massive/Serum, 2009-2012)
- **Character:** A sub plus a mid growl whose filter/volume pulses rhythmically (1/4 to 1/16 note).
- **Start DNA:** `error<<@10[@30]@0CP@0CP@0CP++++#8U2~12/error<<@10[@30]@0CP@0CP#8;A0S100R100`
- **Sources:** `error`, `critstop`
- **Recipe:**
  - The growl core.
  - [planned env graph] draw a looping volume graph at tempo (wub).
  - [planned macro] M1 = wobble rate, automatable.

### Lo-fi Upright Thump (P2)

- **Inspired by:** Upright/acoustic bass in lo-fi hip-hop (sampled jazz bass)
- **Character:** A woody, muted, short thump with a round low and finger noise.
- **Start DNA:** `default<<@20]#8/start<<#2FL40;A0D500S10R100`
- **Sources:** `default`, `start`
- **Recipe:**
  - XP Default at -2 octaves is a woody body.

### Pluck Bass (Synth-pop) (P2)

- **Inspired by:** Juno-106 / SH-101 plucked bass (synthwave and 80s synth-pop)
- **Character:** A short, bright, filter-plucked bass. Eighth-note sequencer staple.
- **Start DNA:** `batlow@5[@20]@0CP@0CP@0CP++<<#8;A0D180S10R60`
- **Sources:** `batlow`, `error`
- **Recipe:**
  - A looped clipped alert tone at -2 octaves with a short decay.

### Korg M1 'House Bass' / Organ Bass (P2)

- **Inspired by:** Korg M1 organ bass and 90s house bass presets
- **Character:** A rounded, slightly clicky, sine-plus-octave bass that bounces.
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CP<<#8H0,12/start>#4FL50;A0D200S45R70`
- **Sources:** `ringout`, `start`
- **Recipe:**
  - The M1 Organ 2 recipe, two octaves down.

### Critical Doom Sub (P2)

- **Inspired by:** Cinematic sub-drop / 'braam' low end (Inception-era trailers)
- **Character:** A colossal, slowly growing low brass-bass blast with grit.
- **Start DNA:** `critstop<<<#8U3~12++/critstop<<#8L60;A200S100R2500`
- **Sources:** `critstop`, `shutdown`
- **Recipe:**
  - critstop at -3 octaves is the braam; clip it for snarl.


## Keys

### Rhodes Mk I Suitcase (P2, cross-listed)

- **Inspired by:** Fender Rhodes (Stevie Wonder, neo-soul, lo-fi: the EP benchmark)
- **Character:** A bell-like tine attack with a warm, sine-ish body, a long sustain, a bark when played hard and a stereo tremolo.
- **Start DNA:** `default@50]#8/ringout@30[@30]<#6L60;A2D2000S30R400V90`
- **Sources:** `default`, `ringout`
- **Recipe:**
  - See 'Vintage Keys Rhodes'.
  - [planned pan] tremolo = per-recorder pan alternation driven by M1.

### Wurlitzer 200A (P2)

- **Inspired by:** Wurlitzer electric piano (Supertramp, Ray Charles, indie)
- **Character:** A reedy, nasal, slightly overdriven bark, shorter and edgier than a Rhodes, with tremolo.
- **Start DNA:** `default@40]+++#8/batcrit@10[@20]@0CP@0CP+#4L50;A0D1400S25R250`
- **Sources:** `default`, `batcrit`
- **Recipe:**
  - A clipped mallet with a reedy looped alert tone.

### Tonewheel Drawbar Organ (P2)

- **Inspired by:** Hammond B3 (+ Leslie): the organ benchmark
- **Character:** Additive sine drawbars, a key-click, percussion and a Leslie swirl (doppler and amp motion).
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CP#12H0,12,19,24U2~6/start>>#4FL40;A5S100R60`
- **Sources:** `ringout`, `xpringout`, `start`
- **Recipe:**
  - Looped sine chunk; drawbars via H0,12,19,24 (8', 4', 2 2/3', 2').
  - U2~6 is the Leslie chorus.
  - [planned pan] slow L/R alternation for the rotor.

### Gospel Organ 'Full' (P3, plays on 3.11 too)

- **Inspired by:** Hammond full-drawbar gospel/rock organ
- **Character:** Every drawbar out, overdriven, Leslie fast: a thick, gritty roar.
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CP++#16H0,7,12,19U2~10;A5S100R60`
- **Sources:** `ringout`
- **Recipe:**
  - Clip for tube overdrive.

### Clavinet D6 Funk (P2)

- **Inspired by:** Hohner Clavinet ('Superstition': the clav benchmark)
- **Character:** A bright, percussive, plucked-string bite with a quick decay and a nasal 'wah' honk. Very funky, very short.
- **Start DNA:** `xpringin@5]++EE>#10/start>>#4FL40;A0D250S15R60`
- **Sources:** `xpringin`, `start`, `error`
- **Recipe:**
  - A pluck front, clipped, with an EE> comb for the string nasality.

### FM EP 'DX Tine' (90s) (P2)

- **Inspired by:** Yamaha DX7II 'Full Tines' / Korg M1 'E.Piano' (90s R&B)
- **Character:** A softer FM EP: rounder bell, more chorus, a lush ballad tone.
- **Start DNA:** `xpding@20]#6H0,12U2~6/ringout@25[@35]#8L80;A0D1800S30R500`
- **Sources:** `xpding`, `ringout`
- **Recipe:**
  - E.PIANO 1, but less high bell, more chorus.

### Harpsichord (P3)

- **Inspired by:** Harpsichord (baroque; also M1/JV 'Harpsi' presets)
- **Character:** A bright, buzzy, jangly pluck with a sharp attack and a metallic sheen. No dynamics.
- **Start DNA:** `xpringin@4]EEE>>#12H0,12;A0D700S0R200V0`
- **Sources:** `xpringin`, `chimes`
- **Recipe:**
  - A comb ring from echo then speed-up gives the jangle; V0 for no dynamics.

### Toy Piano / Celesta (P3)

- **Inspired by:** Celesta and toy piano (Danny Elfman, Y2K whimsy)
- **Character:** A tiny bell-hammer pluck, very high and sweet, with a short metallic ping.
- **Start DNA:** `xpding>@20]#10/default>@20]#4L50;A0D700S0R300`
- **Sources:** `xpding`, `default`
- **Recipe:**
  - Both up an octave.

### Vaporwave EP (slowed DX) (P2)

- **Inspired by:** DX7 EP slowed and drenched (Macintosh Plus 'リサフランク420' sound)
- **Character:** A woozy, pitched-down electric piano: smeared transients, washed-out reverb, thick and dreamy.
- **Start DNA:** `xpding@20]<E<E#6/ringout@25[@35]<#8U2~15L70;A40D2500S40R2500`
- **Sources:** `xpding`, `ringout`, `chord`
- **Recipe:**
  - Two octaves down with echo between each slow-down: the echoes grow longer and blurrier.
  - Wide detune for tape wobble.

### Pipe/Church Organ (P3, plays on 3.11 too)

- **Inspired by:** Pipe organ (cathedral full organ)
- **Character:** Stacked flue pipes, slow 'speak' onset, an immense reverb. Awe.
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CPEE#16H0,12,-12,19;A120S100R2200`
- **Sources:** `ringout`, `xpringout`
- **Recipe:**
  - Octave stacking plus echo for the cathedral.


## Arps and plucks

### Trance Pluck (P1, rank 21)

- **Inspired by:** Classic trance pluck (Sylenth 'Pluck' / Nexus 'Pluck' / Gaia-style)
- **Character:** A clean bright pluck with a 150 ms decay, a wide stereo and an echo tail. It arpeggiates beautifully.
- **Start DNA:** `xpding@15]#8U2~10/xpding@15]<<E>>#4L40;A0D150S0R200`
- **Sources:** `xpding`, `balloon`, `default`
- **Recipe:**
  - Layer 2 uses <<E>> for an echo 4x longer at the original pitch.
  - [planned offsets] true tempo delay: 3 recorders 0/250/500 ms.

### Bubble Arp (P2)

- **Inspired by:** Aero 'bubble' arps (MSN-era, Frutiger Aero aesthetic) / Massive 'Bubbles'
- **Character:** Round 'bloop' plucks with an upward pitch flick. Wet, playful and watery.
- **Start DNA:** `balloon#8/balloon>#4L50;A0D300S0R200`
- **Sources:** `balloon`, `hwin`, `xpding`
- **Recipe:**
  - XP Balloon (a soft pop) is the source of all Aero bubbles.
  - An octave-up copy adds fizz.
  - Arpeggiate at 1/16.

### Marimba Arp (P2)

- **Inspired by:** Marimba/kalimba arpeggios (Nexus, Steve Reich, 2000s ringtones)
- **Character:** A woody mallet pluck with a fast decay and a warm resonator.
- **Start DNA:** `default@30]#10/xpringin@8]#6L50;A0D500S0R200`
- **Sources:** `default`, `xpringin`
- **Recipe:**
  - XP Default and the XP Ringin front.

### Harp Gliss (P2)

- **Inspired by:** Concert harp (JV-1080 'Harp', Proteus/2 harp)
- **Character:** A soft, round pluck that rings long; glissandi are the iconic gesture.
- **Start DNA:** `xpringin@6]E#12;A0D1800S0R1000`
- **Sources:** `xpringin`, `default`
- **Recipe:**
  - [planned offsets] strum: a chord voiced across 6 recorders with offsets 0/20/40/60/80/100 ms is the gliss.

### Guitar-ish Nylon Pluck (P3)

- **Inspired by:** GM 25 'Nylon Guitar' / JV 'Nylon Gtr'
- **Character:** A soft thumb pluck: warm mids, short body.
- **Start DNA:** `xpringin@7]<#10/start<#2FL30;A0D900S0R200`
- **Sources:** `xpringin`, `start`
- **Recipe:**
  - Slowed ringin front.

### Pizzicato Ostinato (P3, cross-listed)

- **Inspired by:** Proteus/JV 'Pizzicato' (90s scoring ostinatos)
- **Character:** A short, bouncy string pluck.
- **Start DNA:** `xpringin@8]E#8U2~6;A0D200S0R120`
- **Sources:** `xpringin`, `default`
- **Recipe:**
  - See 'Proteus Pizzicato'.

### Glass Pluck Delay (P2, plays on 3.11 too)

- **Inspired by:** Modern 'glass pluck' (Future garage, chillstep)
- **Character:** A crystalline, very bright pluck with ping-pong echoes.
- **Start DNA:** `chimes>>@20]#8/chimes>>@20]<<E>>#4L40;A0D300S0R300`
- **Sources:** `chimes`, `xpding`, `print`
- **Recipe:**
  - Chimes at x4 front, plus a long echo copy.
  - [planned pan] echo layer hard R.

### 8-bit Chiptune Arp (P2)

- **Inspired by:** NES/Game Boy pulse arps (chiptune, Y2K Flash games)
- **Character:** A buzzy pulse wave, rapid arpeggios, no reverb, instant attack and release.
- **Start DNA:** `batlow@5[@15]@0CP@0CP@0CP@0CP++++#8;A0S100R20V0`
- **Sources:** `batlow`, `batcrit`
- **Recipe:**
  - A looped clipped alert tone gives the pulse.
  - Play fast arps.


## Pads

### Warm Analog Pad (P1, rank 22)

- **Inspired by:** Oberheim OB-X / Juno-60 strings-pad (warm pad benchmark)
- **Character:** A detuned saw/pulse pad with a slow attack, a filter softness, chorus and a long release. Warm, soft-focus.
- **Start DNA:** `startup@20[<#10U3~14/logoff@30[<#6U2~10L60;A600S90R1800`
- **Sources:** `startup`, `logoff`, `logon`
- **Recipe:**
  - XP Startup's middle plus logoff, both slowed: the warmest Windows audio.

### Glass Pad (P2)

- **Inspired by:** Glass/crystal pads (Wavestation, JD-800, Nexus 'Glass')
- **Character:** Bright, cold, high-partial shimmer with a soft attack and glittery motion.
- **Start DNA:** `chimes>R#8U2~10/xpding>R#4L60/logon@30[#4L40;A600S85R2200`
- **Sources:** `chimes`, `xpding`, `logon`, `print`
- **Recipe:**
  - Reversed glassy sources.

### Evolving Motion Pad (P2)

- **Inspired by:** Wavestation/Omnisphere-style motion pads
- **Character:** Timbre and rhythm change over the length of the note.
- **Start DNA:** `logon@20[IchimesIstartupIxpdingEE#10U2~8/startup<#6L50;A400S90R2500`
- **Sources:** `logon`, `chimes`, `startup`, `xpding`
- **Recipe:**
  - A spliced sequence with echo smearing; the note plays through the splice for movement.

### Choir Pad (P2)

- **Inspired by:** Choir pads (M1 'Choir', JV 'Vox Pad', Omnisphere 'Choir Pad')
- **Character:** A breathy vowel 'aah' blended with synth pad.
- **Start DNA:** `notify<#8U3~12/startup@20[<#8L50;A500S90R1800`
- **Sources:** `notify`, `startup`
- **Recipe:**
  - notify choir plus startup pad.

### Swell Pad (Reverse) (P2)

- **Inspired by:** Reverse-reverb swells (shoegaze, ambient)
- **Character:** Sound grows out of silence into the note, then cuts. Sucking, hypnotic.
- **Start DNA:** `logon<RE#8U2~8/chordRE#8L50;A50S100R400`
- **Sources:** `logon`, `chord`, `startup`, `tada`
- **Recipe:**
  - Reverse plus echo: the 'swell pad' idiom.
  - The env attack can stay short: the swell is baked in.

### Strings Machine Pad (P2)

- **Inspired by:** ARP Solina / Logan String Melody (Jarre, Joy Division)
- **Character:** A buzzy, ensemble-chorused string synth pad with heavy triple-chorus motion. Thin, but iconic.
- **Start DNA:** `logoff@30[@20]@0CP@0CP@0CP#16U4~22;A300S95R1000`
- **Sources:** `logoff`, `startup`
- **Recipe:**
  - A looped chunk with U4~22 for the ensemble effect.

### Dark Ambient Pad (P2)

- **Inspired by:** Dark ambient (Brian Eno 'Music for Airports' / Biosphere)
- **Character:** Deep, slow, slightly unstable tones. Long fades, very little high end.
- **Start DNA:** `startup<<#8U2~10/shutdown<<#8U2~8L70;A2000S100R5000`
- **Sources:** `startup`, `shutdown`
- **Recipe:**
  - Two octaves down.

### Shimmer Pad (P2)

- **Inspired by:** Shimmer reverb pads (Eventide 'Shimmer', U2/The Edge, ambient guitar)
- **Character:** Octave-up reverb cascade: the note grows a sparkling halo an octave and two octaves above.
- **Start DNA:** `logon@20[#8/logon@20[>E>E#4L50/logon@20[>>RER#4L30;A400S90R2500`
- **Sources:** `logon`, `startup`
- **Recipe:**
  - Layers at +12 and +24 baked by speed-up with echo between, so the higher echoes cascade.

### Sweep Pad (P3)

- **Inspired by:** Filter-sweep pads (Prophet-5, trance breakdowns)
- **Character:** A pad whose brightness slowly opens and closes.
- **Start DNA:** `minimize<<R#4F/startup@20[<#8U2~10/restore<<#4FL40;A600S90R2000`
- **Sources:** `startup`, `minimize`, `restore`
- **Recipe:**
  - Whoosh layers give a noise-band sweep.
  - [planned macro] M1 = 'cutoff', crossfading a dull layer (<<) into a bright layer (>).

### PWM Pad (P3)

- **Inspired by:** Juno-106 PWM pad
- **Character:** A hollow pulse with a slow pulse-width modulation: a constant, gentle chorus warble.
- **Start DNA:** `batlow@5[@20]@0CP@0CP@0CP++#12U3~9;A400S90R1500`
- **Sources:** `batlow`, `batcrit`
- **Recipe:**
  - A clipped pulse loop; unison beat simulates the PWM.


## Vocal choir

### Mellotron Choir (P1, rank 12)

- **Inspired by:** Mellotron M400 '8-Voice Choir' (Bowie 'Space Oddity', Genesis, King Crimson, Radiohead)
- **Character:** A haunting, dusty tape choir with a slow onset, wow and flutter, a mid-focused 'ah' and an 8-second tape length. Eerie, melancholy, unrealistic in the best way.
- **Start DNA:** `notify<<-#8U3~16/logon<<@25[#6U2~12L50/recycle<<<#2FL10;A350S95R700`
- **Sources:** `notify`, `logon`, `recycle`
- **Recipe:**
  - notify at -2 octaves, slightly quieter, gives the low choir formant.
  - Wide unison gives tape wow.
  - Slowed crumple is the tape hiss.
  - The natural buffer end (no loop) is the tape stop, authentically Mellotron.

### GM Choir Aahs (P3, cross-listed)

- **Inspired by:** GM 53 'Choir Aahs' (SC-55/88, every MIDI file)
- **Character:** See 'SC-55 Choir Aahs'.
- **Start DNA:** `notify<#8U3~12/xpnotify<<@20[#6U2~10L60;A300S90R900V40`
- **Sources:** `notify`, `xpnotify`
- **Recipe:**
  - Same as 'SC-55 Choir Aahs'; a duplicate entry in the category list.

### Fairlight 'Arr1' Choir Hit (P2)

- **Inspired by:** Fairlight CMI ARR1 (Kate Bush, Tears for Fears 'Mad World')
- **Character:** A short, breathy sampled 'aah' stab: lo-fi, dramatic, 80s.
- **Start DNA:** `notify<@40]><#10U2~8;A20D500S40R400`
- **Sources:** `notify`
- **Recipe:**
  - A front-trimmed, decimated notify.

### Gregorian Monks (P2)

- **Inspired by:** Male choir chant ('Enigma' 'Sadeness', 90s new age)
- **Character:** A low, sustained male unison 'oo' with a church reverb.
- **Start DNA:** `ringout@20[@40]<<EE#10U3~10/notify<<<#4L50;A500S95R2000`
- **Sources:** `ringout`, `notify`
- **Recipe:**
  - Two octaves down, sine-ish, with an echo hall.

### Ethereal Female 'Ooh' (P2)

- **Inspired by:** Enya / Lisa Gerrard airy vocal pads (new age)
- **Character:** A high, breathy, floaty 'ooh' with a huge reverb.
- **Start DNA:** `ringout@20[@40]>#8U3~10/minimize<#2FL20;A600S90R2500`
- **Sources:** `ringout`, `minimize`
- **Recipe:**
  - ringout up an octave, with air.

### Vox Chop (P3)

- **Inspired by:** Vocal chops (future bass, deep house)
- **Character:** A short, pitched vocal syllable, chopped and rhythmic.
- **Start DNA:** `notify@30]E#12;A0D200S0R100`
- **Sources:** `notify`, `xpnotify`
- **Recipe:**
  - A short notify front.

### Space Choir 'Aah' (Vangelis) (P2)

- **Inspired by:** Yamaha CS-80 + choir / Vangelis 'Blade Runner' vox
- **Character:** A huge, slow, brassy-vocal pad with a big reverb.
- **Start DNA:** `notify<#8U3~14/startup<@20[#8U2~10L60;A800S95R3000`
- **Sources:** `notify`, `startup`
- **Recipe:**
  - Choir plus warm pad.


## Bells and mallets

### Glassy Speed Bell (P1, rank 10, plays on 3.11 too)

- **Inspired by:** Glassy FM bell (DX7 'E.BELL', M1 'Bell', 'glass bell' trope)
- **Character:** Pure, bright, inharmonic shimmer: an instant strike and a long ringing decay, stacked an octave and a fifth for sparkle.
- **Start DNA:** `chimes>>#6H0,12,19U2~5;A0D3000S0R1500`
- **Sources:** `chimes`, `xpding`, `ding`
- **Recipe:**
  - Speed x2 twice on chimes for the glassy bell.
  - 3 harmony voices at the root, octave and octave+fifth.
  - Slight detune.
  - [planned env graph] a slow-attack version for a 'bowed' glass bell.

### Vibraphone (P2)

- **Inspired by:** Vibraphone (jazz, ambient; JV 'Vibes')
- **Character:** A soft mallet onto a sine-like bar, with a long ring and motor tremolo.
- **Start DNA:** `default@40]#8/ringout@25[@35]>#6L60;A0D2500S10R800`
- **Sources:** `default`, `ringout`
- **Recipe:**
  - A mallet plus a sine tail.
  - [planned macro] M1 = tremolo depth via volume automation.

### Glockenspiel (P2)

- **Inspired by:** Glockenspiel (film whimsy, GM 10)
- **Character:** A very bright, high, metallic strike with a short ring.
- **Start DNA:** `xpding>>@25]#10;A0D1200S0R500`
- **Sources:** `xpding`, `chimes`
- **Recipe:**
  - xpding up two octaves.

### Tubular Bells (P2, plays on 3.11 too)

- **Inspired by:** Tubular bells (Mike Oldfield; orchestral chimes)
- **Character:** A heavy strike with deep inharmonic partials and a long decay.
- **Start DNA:** `chimes<@30]#8U2~10/ding<#4L60;A0D5000S0R2500`
- **Sources:** `chimes`, `ding`
- **Recipe:**
  - Slowed chimes and ding.

### Marimba (P2)

- **Inspired by:** Marimba (GM 13; Reich)
- **Character:** A woody mallet with a short resonant decay and warm low partials.
- **Start DNA:** `default@30]#10;A0D600S0R200`
- **Sources:** `default`, `xpringin`
- **Recipe:**
  - XP Default's soft 'bong'.

### Steel Gamelan Bell (P3, cross-listed, plays on 3.11 too)

- **Inspired by:** Balinese gamelan bell / gong (Proteus World)
- **Character:** Paired-detune shimmer: metallic, long.
- **Start DNA:** `chimes@20]#8U2~22;A0D3000S0R1500`
- **Sources:** `chimes`
- **Recipe:**
  - See 'Proteus 3 Ethnic Gamelan'.

### Music Box (P3, cross-listed)

- **Inspired by:** Cylinder music box (lullaby trope)
- **Character:** A tiny tine with a mechanical pluck, high register and a slightly sour tuning.
- **Start DNA:** `xpding@20]>#12U2~8/start>>#2FL30;A0D900S0R400`
- **Sources:** `xpding`, `start`
- **Recipe:**
  - See 'Kontakt Factory Music Box'.

### Crystal Bowl / Singing Glass (P2, plays on 3.11 too)

- **Inspired by:** Singing bowls (wellness, ambient)
- **Character:** A soft rub onset, then a pure, beating, endlessly sustained tone.
- **Start DNA:** `ding@30[@30]@0CP@0CP@0CP#8U2~4/dingR#4L40;A700S100R3000`
- **Sources:** `ding`, `xpding`
- **Recipe:**
  - The ring tail of ding, looped.
  - U2~4 gives a slow beat.


## Strings

### String Ensemble (Lush) (P2, cross-listed)

- **Inspired by:** JV-1080 'Velo Strings' / Proteus/2 'Strings' (the 90s lush section)
- **Character:** Slow attack, warm mids, ensemble shimmer, wide hall.
- **Start DNA:** `logoff@25[#10U3~12/shutdown@30[<#6U2~8L50;A250S95R1500`
- **Sources:** `logoff`, `shutdown`
- **Recipe:**
  - See 'JV-1080 Velo Strings'.

### Staccato Strings (P2)

- **Inspired by:** Short staccato strings (spiccato, scoring ostinatos)
- **Character:** A short bowed bite, 150 ms, a woody room.
- **Start DNA:** `logoff@10[@15]#12U2~8/recycle>>>@3]#2FL30;A0D150S0R120`
- **Sources:** `logoff`, `recycle`
- **Recipe:**
  - A short logoff chunk with a bow-noise tick.

### Tremolo Strings (P2)

- **Inspired by:** Tremolo strings (horror and suspense)
- **Character:** Rapid bow repetition: shivering motion.
- **Start DNA:** `logoff@30[@5]@0CP@0CP@0CP@0CP@0CP#12U3~10;A150S95R800`
- **Sources:** `logoff`
- **Recipe:**
  - A tiny chunk repeated 32x: the paste seams give a fast re-bow tremolo.

### Solo Cello (P3)

- **Inspired by:** Solo cello (Ethno World, Kontakt)
- **Character:** A rich, woody, nasal low bowed tone with vibrato.
- **Start DNA:** `logoff@30[<<#8U2~6/critstop<<@20[#4L30;A200S95R600`
- **Sources:** `logoff`, `critstop`
- **Recipe:**
  - logoff two octaves down.

### Synth Strings 1 (GM 51) (P3)

- **Inspired by:** GM 'SynthStrings 1' (SC-55, every 90s MIDI)
- **Character:** A slightly brassy, buzzy synth string with a soft attack.
- **Start DNA:** `logoff@30[@20]@0CP@0CP@0CP+#12U3~12;A250S95R900`
- **Sources:** `logoff`
- **Recipe:**
  - A looped string chunk.

### Disco Strings Rise (P3)

- **Inspired by:** Disco string runs (Salsoul, French house samples)
- **Character:** A bright, glossy section with an upward sweep before the hit.
- **Start DNA:** `logoff@25[#8U3~10/restore#4FL60;A40S95R800`
- **Sources:** `logoff`, `restore`
- **Recipe:**
  - The restore whoosh up gives the rise.


## Brass and stabs

### Orchestra Hit (P2, cross-listed)

- **Inspired by:** Fairlight ORCH5 / Emulator orch hit (Art of Noise, Yes, 'Owner of a Lonely Heart'; everywhere since)
- **Character:** See 'Emulator Orchestra Hit': a full chord in one transient.
- **Start DNA:** `tada@25]++E#10H0,12/critstop@10]<#6L80;A0D300S0R200V70`
- **Sources:** `tada`, `critstop`
- **Recipe:**
  - See 'Emulator Orchestra Hit'.

### Brass Stab (Jump) (P2)

- **Inspired by:** Oberheim OB-Xa brass stab (Van Halen 'Jump') / Prophet brass
- **Character:** A bright, punchy, detuned saw brass chord with a quick 'blat' attack.
- **Start DNA:** `tada@10[@20]@0CP@0CP@0CP++#16U3~14;A15D300S70R200`
- **Sources:** `tada`, `chord`
- **Recipe:**
  - A looped tada chunk, clipped and detuned, gives the synth brass.

### Synth Brass Pad (Vangelis) (P2)

- **Inspired by:** Yamaha CS-80 brass (Vangelis 'Chariots of Fire')
- **Character:** A slow, swelling, warm brass pad with expressive brightness.
- **Start DNA:** `tada@10[<#8U3~12/startup@20[<#6L50;A350S95R1500`
- **Sources:** `tada`, `startup`
- **Recipe:**
  - tada slowed into a warm brass bed.

### Real Horn Section Stab (P2)

- **Inspired by:** Horn stab (JV/Proteus 'Brass Section', funk/soul)
- **Character:** A tight 3-horn 'baap' with a brassy rip and a fast decay.
- **Start DNA:** `tada@20]+#10H0,4,7;A0D200S20R150`
- **Sources:** `tada`
- **Recipe:**
  - The tada front, triad voiced.

### French Horns (Epic) (P2)

- **Inspired by:** Epic horn swell (Hans Zimmer, trailer)
- **Character:** Massed, round, dark horns with a slow crescendo.
- **Start DNA:** `tada@10[<<#8U3~10/critstop<@20[#6L60;A600S100R2000`
- **Sources:** `tada`, `critstop`
- **Recipe:**
  - tada and critstop slowed.

### Rave Stab (P2)

- **Inspired by:** Rave/hardcore stab (Korg M1 'Organ 2'/Mentasm/Orch hits)
- **Character:** A short, loud, chordal, minor stab with grit.
- **Start DNA:** `chord@30]+++#12H0,3,7;A0D200S0R100`
- **Sources:** `chord`, `tada`
- **Recipe:**
  - Clipped chord front, minor triad.


## Leads

### Supersaw Lead (P2, cross-listed)

- **Inspired by:** Roland JP-8000 supersaw (trance benchmark)
- **Character:** See 'XV Supersaw Pad', with a shorter attack and an octave.
- **Start DNA:** `chord@20[@30]@0CP@0CP@0CP++#16H0,12U4~25;A5S100R300`
- **Sources:** `chord`
- **Recipe:**
  - The supersaw core.

### Sync Lead (P3)

- **Inspired by:** Oscillator-sync lead (Cars 'Let's Go', Prophet-5)
- **Character:** A tearing, vocal, metallic lead with a sweeping formant.
- **Start DNA:** `hwin@10[@40]@0CP@0CP+++#8/hwout@10[@40]@0CP@0CP++#4L50;A5S100R200`
- **Sources:** `hwin`, `hwout`
- **Recipe:**
  - A looped bloop chunk, clipped: the rising formant reads as 'sync'.

### Square Lead (Chip / GM 81) (P3, cross-listed)

- **Inspired by:** GM Square Lead / pulse leads
- **Character:** A hollow square: video-game melody.
- **Start DNA:** `batlow@5[@20]@0CP@0CP@0CP+++#8;A5S100R150`
- **Sources:** `batlow`
- **Recipe:**
  - See 'SC-55 Square Lead'.

### Sine Whistle Lead (P2, plays on 3.11 too)

- **Inspired by:** Moog/Theremin-ish sine lead (G-funk whistle: Dr. Dre)
- **Character:** A pure, high, singing sine with portamento and vibrato.
- **Start DNA:** `ringout@20[@40]>#8U2~6;A60S100R300B12`
- **Sources:** `ringout`, `xpringout`
- **Recipe:**
  - A sine-ish ringout up an octave.
  - B12 for expressive bends (G-funk glides).

### Mono Saw Lead (Minimoog) (P3)

- **Inspired by:** Minimoog lead (Jan Hammer, prog)
- **Character:** A fat, slightly detuned, warm saw lead.
- **Start DNA:** `chord@20[@30]@0CP@0CP@0CP+++#8U2~8;A10S100R250`
- **Sources:** `chord`, `error`
- **Recipe:**
  - The saw core, mono feel, small detune.

### Pan-Flute Lead (Zamfir) (P3, cross-listed)

- **Inspired by:** Pan flute lead (see world)
- **Character:** See 'Pan Flute'.
- **Start DNA:** `ringout@25[@40]#8U2~7/minimize>@15]#3FL35;A40S90R600`
- **Sources:** `ringout`, `minimize`
- **Recipe:**
  - See 'D-50 Breathy Chiffer'.

### Distorted Hoover Lead (P3, cross-listed)

- **Inspired by:** Hoover as lead (gabber and rave)
- **Character:** See 'Alpha Juno Hoover'.
- **Start DNA:** `error@10[@40]@0CP@0CP@0CP+++#16U8~60;A10S100R400B12`
- **Sources:** `error`
- **Recipe:**
  - See 'Alpha Juno Hoover'.


## World

### Koto (P2, cross-listed)

- **Inspired by:** Koto (DX7, Emulator, Proteus World)
- **Character:** See 'DX7 Koto': a twang with a pitch drop and a buzzing resonance.
- **Start DNA:** `xpringin@5]EE>#10/start>>#4FL30;A0D500S0R250`
- **Sources:** `xpringin`, `xpding`
- **Recipe:**
  - See 'DX7 Koto'.

### Shakuhachi (P2, cross-listed)

- **Inspired by:** Shakuhachi (E-II 'Sledgehammer', Fairlight, Proteus World)
- **Character:** See 'Shakuhachi Hammer'.
- **Start DNA:** `ringout@30[@40]#3/recycle>>@8]#2F;A15D400S70R250V80`
- **Sources:** `ringout`, `recycle`
- **Recipe:**
  - See 'Shakuhachi Hammer'.

### Sitar (P2)

- **Inspired by:** Sitar (Ravi Shankar; 60s psych; Proteus World 'Sitar')
- **Character:** A bright, buzzy, sweeping 'jawari' resonance, sympathetic string drones and a nasal twang.
- **Start DNA:** `xpringin@6]EEE>>#8/xpringin@6]EEE>>R#4L30/ringout@20[@40]<#4L30;A0D1500S20R800`
- **Sources:** `xpringin`, `chimes`, `ringout`
- **Recipe:**
  - The EEE>> comb gives the jawari buzz.
  - A reversed copy is the sympathetic-string swell.
  - The sine drone layer underneath is the tanpura.

### Kalimba (P2, cross-listed)

- **Inspired by:** Kalimba / mbira (Proteus World, Alchemy, Earth Wind & Fire)
- **Character:** See 'Proteus World Kalimba'.
- **Start DNA:** `xpding@25]#10/start>#4FL50;A0D600S0R250`
- **Sources:** `xpding`, `start`
- **Recipe:**
  - See 'Proteus World Kalimba'.

### Pan Flute (P1, rank 24)

- **Inspired by:** Pan flute (Zamfir; GM 76; Korg M1 'PanFlute')
- **Character:** A breathy, hollow, airy tone with a strong 'chiff' and gentle vibrato. Very 90s 'relaxing'.
- **Start DNA:** `ringout@25[@40]#8U2~7/minimize>@15]#3FL35;A40S90R600`
- **Sources:** `ringout`, `minimize`, `recycle`
- **Recipe:**
  - A sine-ish body plus a whoosh chiff.
  - [planned env graph] a small overshoot at 60 ms for the chiff.

### Steel Drum (P1, rank 25)

- **Inspired by:** Steel drum / steelpan (GM 115; Proteus World; tropical house)
- **Character:** A bright, metallic, round strike with characteristic inharmonic 'boing' partials and a medium decay. Happy and tropical.
- **Start DNA:** `xpding@20]EE>#8/default@30]#4L60;A0D700S0R300`
- **Sources:** `xpding`, `default`, `exclaim`
- **Recipe:**
  - The xpding strike's EE> comb gives the 'pan' ring.
  - XP Default's mallet gives the round body.

### Ocarina (P2)

- **Inspired by:** Ocarina (Zelda; GM 80)
- **Character:** A pure, round, hollow tone with a breathy onset.
- **Start DNA:** `ringout@25[@40]>#8/recycle>>@5]#2FL15;A30S95R300`
- **Sources:** `ringout`, `recycle`
- **Recipe:**
  - ringout plus breath.

### Tabla / Hand Drums (P3)

- **Inspired by:** Tabla/hand percussion (Ethno World; Proteus World)
- **Character:** A pitched drum 'dha' with a resonant bend and a dry slap.
- **Start DNA:** `default<@20]#8/start<#4F;A0D300S0R100`
- **Sources:** `default`, `start`
- **Recipe:**
  - A slowed mallet plus a slap click.

### Erhu (P3)

- **Inspired by:** Erhu (Chinese fiddle; Ethno World)
- **Character:** A nasal, expressive, sliding bowed tone.
- **Start DNA:** `batcrit@10[@20]@0CP@0CP@0CP#8U2~10;A120S95R400B12`
- **Sources:** `batcrit`, `logoff`
- **Recipe:**
  - A looped nasal tone with a wide bend.

### Didgeridoo (P3)

- **Inspired by:** Didgeridoo (Ethno World, ambient)
- **Character:** A low, growling, rhythmic formant drone.
- **Start DNA:** `error<<<@10[@30]@0CP@0CP@0CP@0CPE#8F;A300S100R1000`
- **Sources:** `error`, `critstop`
- **Recipe:**
  - A looped low error tone with echo.


## Drones

### Tanpura Drone (P2, plays on 3.11 too)

- **Inspired by:** Tanpura (Indian classical drone)
- **Character:** Constantly shimmering overtones on a fixed root and fifth.
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CP@0CPEE#8H0,7,12U2~6;A1500S100R4000`
- **Sources:** `ringout`
- **Recipe:**
  - A looped sine tone, root/fifth/octave, plus echo shimmer.

### Deep Space Drone (P2)

- **Inspired by:** Ambient space drone (Stars of the Lid, Brian Eno)
- **Character:** Very slow, dense, dark, gently beating tones.
- **Start DNA:** `startup<<<#8U3~15/shutdown<<<R#8;A3000S100R6000`
- **Sources:** `startup`, `shutdown`
- **Recipe:**
  - Three octaves down.

### Machine Hum Drone (P3)

- **Inspired by:** Industrial hum (server room, 50/60 Hz)
- **Character:** Steady, buzzy low hum with harmonic grit.
- **Start DNA:** `batlow@5[@15]@0CP@0CP@0CP@0CP++<<<#8F;A1000S100R2000`
- **Sources:** `batlow`, `error`
- **Recipe:**
  - A clipped looped tone, low, fixed.

### Eerie Bowed Metal (P2, plays on 3.11 too)

- **Inspired by:** Bowed cymbal / waterphone (horror)
- **Character:** A metallic, dissonant, screeching sustain.
- **Start DNA:** `chimes<REE#8U3~30;A1500S100R3000`
- **Sources:** `chimes`, `ding`
- **Recipe:**
  - Reversed, slowed chimes with echo; wide detune for dissonance.

### Organ Drone (Cathedral) (P3, plays on 3.11 too)

- **Inspired by:** Church organ drone (Arvo Part, ambient)
- **Character:** A pure, immovable stack.
- **Start DNA:** `ringout@20[@30]@0CP@0CP@0CP@0CP#12H0,12,-12;A2000S100R4000`
- **Sources:** `ringout`
- **Recipe:**
  - Looped sine-ish tone in octaves.


## Risers and FX

### White Noise Riser (P2)

- **Inspired by:** EDM noise riser/sweep (Nexus FX, Massive)
- **Character:** Noise rising in pitch and brightness over 4 to 8 bars.
- **Start DNA:** `restore<<#8F/minimizeR<<#8F;A3000S100R500`
- **Sources:** `restore`, `minimize`, `recycle`
- **Recipe:**
  - restore is an upward whoosh; reversed minimize also rises.
  - << stretches them.
  - [planned env graph] a long exponential ramp.

### Reverse Cymbal (P2)

- **Inspired by:** Reverse cymbal swell (pop and hip-hop transitions)
- **Character:** A shimmering noise swell into the downbeat.
- **Start DNA:** `recycleRE#8F/chimesR#4FL50;A0S100R200`
- **Sources:** `recycle`, `xprecycle`, `chimes`
- **Recipe:**
  - Reversed crumple and chimes.

### Downlifter / Impact (P2)

- **Inspired by:** Downlifter and trailer impact (sub drop)
- **Character:** A big hit, then a falling noise and pitch tail.
- **Start DNA:** `critstop<<#8F/minimize<#8F;A0S100R2000`
- **Sources:** `critstop`, `minimize`, `shutdown`
- **Recipe:**
  - A low critstop hit plus a downward whoosh.

### Laser Zap (P2)

- **Inspired by:** Laser 'pew' (Y2K, retro FX)
- **Character:** A fast falling-pitch zap.
- **Start DNA:** `hwout>>#8/balloon>>#4L50;A0D150S0R80`
- **Sources:** `hwout`, `balloon`
- **Recipe:**
  - The descending Hardware Remove at x4 speed.

### Glitch Stutter (P2)

- **Inspired by:** Glitch FX (Autechre, 2000s IDM; Massive 'Stutter')
- **Character:** Rapid-fire, chopped, repeating fragments.
- **Start DNA:** `xpding@5]@0CP@0CP@0CPImenu@0CP#8F;A0S100R80`
- **Sources:** `xpding`, `menu`, `start`
- **Recipe:**
  - Repeat a tiny chunk with an Insert-File click inside the loop.

### Sci-fi Computer Babble (P3)

- **Inspired by:** Sci-fi computer bleeps (Star Trek, 70s/80s)
- **Character:** Random, rapid, pitched bleeps.
- **Start DNA:** `batcrit>IbatlowIhwin>IhwoutIprint>#8F;A0S100R100`
- **Sources:** `batcrit`, `batlow`, `hwin`, `hwout`, `print`
- **Recipe:**
  - Splice alert tones into a sequence of bleeps.

### Underwater Bubbles (P2)

- **Inspired by:** Bubble FX (Frutiger Aero aquariums; Massive 'Bubbles')
- **Character:** A random cascade of round 'blips' with a watery resonance.
- **Start DNA:** `balloon>IballoonIballoon>>Iballoon<E#8F;A0S100R300`
- **Sources:** `balloon`, `hwin`
- **Recipe:**
  - Splice balloon pops at varied speeds; echo for water.

### Tape Stop (P3)

- **Inspired by:** Tape stop/slowdown (vaporwave, hip-hop)
- **Character:** The sound grinds down in pitch to a halt.
- **Start DNA:** `startup<<<@50]#8F;A0S100R1000`
- **Sources:** `startup`, `tada`, `chord`
- **Recipe:**
  - Can't glide pitch, so fake it as a cascade.
  - [planned offsets] 4 recorders at speed x1, /2, /4, /8 with offsets 0/150/300/450 ms and falling volume.


## Lo-fi and vaporwave

### Vaporwave Slowed Pad (P1, rank 11)

- **Inspired by:** Vaporwave ('Floral Shoppe', 'Eccojams' slowed, reverbed)
- **Character:** Pitched down 30%-plus (here an octave), heavy reverb, smeared, thick and nostalgic. The pad is a corporate sound remembered half-asleep.
- **Start DNA:** `startup<E<E#8U2~12/logon<E#8L60;A300S95R3000`
- **Sources:** `startup`, `logon`, `chord`, `tada`
- **Recipe:**
  - Slow, then echo, then slow, then echo: each echo comes out longer and lower (the step order is the effect).
  - [planned env graph] a long fade.

### Mallsoft Atrium (P1, rank 26)

- **Inspired by:** Mallsoft (Disconscious, 'Hologram Plaza'; '猫 シ Corp')
- **Character:** Muzak in an empty mall: distant, reverberant, muffled and endless.
- **Start DNA:** `chord<<EEE#8U2~10/recycle<<<#4FL15/logon<<#4L50;A600S90R3500`
- **Sources:** `chord`, `logon`, `recycle`, `startup`
- **Recipe:**
  - Many echoes give distance.
  - Slowed crumple is the crowd/HVAC murmur.
  - [planned pan] wide.
  - [planned macro] M1 = distance (echo layer vs dry).

### Eccojam Loop (P2)

- **Inspired by:** Daniel Lopatin 'Eccojams' (looped slowed pop fragments)
- **Character:** A short phrase looped hypnotically, slowed and echoed.
- **Start DNA:** `startup<@20[@20]@0CP@0CP@0CPE#8F;A50S100R1500`
- **Sources:** `startup`, `logon`, `tada`
- **Recipe:**
  - A chunk looped with @0CP and echoed, played at a fixed pitch.

### Lo-fi Tape Keys (P2)

- **Inspired by:** Lo-fi hip-hop keys (ChilledCow era)
- **Character:** A warm, wobbly, dusty EP with a soft attack and noise.
- **Start DNA:** `default@50]><#8U2~14/ringout@30[@30]<#6L60/recycle<<<#2FL10;A10D2000S30R700`
- **Sources:** `default`, `ringout`, `recycle`
- **Recipe:**
  - A Rhodes recipe with decimation, wide wow and dust.

### Bitcrushed Chiptune Pad (P2)

- **Inspired by:** 8-bit lo-fi texture
- **Character:** Aliasing, quantization noise, stepped tone.
- **Start DNA:** `chord>>><<<----++++#8;A200S90R800`
- **Sources:** `chord`, `chimes`
- **Recipe:**
  - A >>><<< round trip (decimate by 8) plus a ----++++ requantize (hypothesis: loses bits on 8-bit sources).

### VHS Warble (P2)

- **Inspired by:** VHS tape warble pads (synthwave, chillwave)
- **Character:** A wobbly pitch, a dull top and soft saturation.
- **Start DNA:** `logon<><#8U4~20+/startup@20[<#4L50;A400S90R1800`
- **Sources:** `logon`, `startup`
- **Recipe:**
  - Wide unison for warble, decimation for the dull top.

### Vinyl Crackle Bed (P3)

- **Inspired by:** Lo-fi vinyl noise layer
- **Character:** Crackle and hiss as a texture under everything.
- **Start DNA:** `recycle>>><@0CP@0CP@0CP#4F;A0S100R500G-12`
- **Sources:** `recycle`, `xprecycle`
- **Recipe:**
  - Crumple chopped and looped into crackle.
  - Use it as a layer under keys.

### Slowed + Reverb Chord (P2)

- **Inspired by:** 'Slowed + reverb' YouTube edits (2017-2020)
- **Character:** A chord stab slowed into a vast dreamy wash.
- **Start DNA:** `chord<EE<E#10U2~8;A100S95R3000`
- **Sources:** `chord`, `tada`
- **Recipe:**
  - Interleave < and E so the echoes grow longer.


## Aesthetic: Frutiger Aero

### Aero Startup Swell (P1, rank 7)

- **Inspired by:** Windows XP/Vista startup sounds (Brian Eno 95 / XP / Vista 'Aero' startup)
- **Character:** A glossy, optimistic swell: a bright pad bloom, sparkle notes, a big airy reverb. Pure 2001-2009 'future'.
- **Start DNA:** `startup#10U2~6/chimes>R#6L50;A200S90R2500`
- **Sources:** `startup`, `logon`, `chimes`
- **Recipe:**
  - XP Startup itself, playable chromatically, with a reversed glass shimmer.
  - This is the brand preset: the source sound IS the aesthetic.

### Water Droplet Pluck (P1, rank 16)

- **Inspired by:** Frutiger Aero water drop (Vista/Windows 7 'notify', Apple 'Drip', 2000s UI)
- **Character:** A tiny round bloop with a rising pitch flick, very short, plus a watery resonance.
- **Start DNA:** `balloon@40]#10/hwin>@20]#4L40;A0D200S0R150`
- **Sources:** `balloon`, `hwin`, `xpding`
- **Recipe:**
  - The balloon front plus a short rising Hardware Insert bloop.

### Bubbly Aero Arp (P2)

- **Inspired by:** Frutiger Aero bubbles (MSN Messenger, 'Aqua' UI, Wii menus)
- **Character:** Bouncy, rounded, glossy plucks with soft echoes, like bubbles in an aquarium.
- **Start DNA:** `balloon#8/balloon<<E>>#4L40;A0D300S0R300`
- **Sources:** `balloon`
- **Recipe:**
  - Balloon plus a long-echo copy.

### Glassy Aqua Pad (P2)

- **Inspired by:** Frutiger Aero glassy pads (Vista 'Aurora', 2000s tech commercials)
- **Character:** Clean, bright, transparent pad with sparkly top, slow shimmer.
- **Start DNA:** `logon@20[#8U2~8/xpding>R#4L50/chimes>>R#4L30;A500S90R2500`
- **Sources:** `logon`, `xpding`, `chimes`
- **Recipe:**
  - Logon body with reversed bright sparkle layers.

### Airy Breath Pad (P2)

- **Inspired by:** Aero airy pads (Vista/Win7 'Windows Calendar' etc.)
- **Character:** Breathy air over a soft sine chord.
- **Start DNA:** `ringout@20[@40]#8H0,7U2~6/minimize<#4FL30;A800S90R2500`
- **Sources:** `ringout`, `minimize`
- **Recipe:**
  - A sine-ish fifth with air.

### MSN Nudge Boing (P2)

- **Inspired by:** MSN Messenger nudge/sign-in style blips (2000s chat)
- **Character:** A playful, rubbery boing with a quick pitch wobble.
- **Start DNA:** `hwin#8U2~15/balloon#4L50;A0D300S0R200`
- **Sources:** `hwin`, `balloon`, `xpnotify`
- **Recipe:**
  - Hardware Insert's bloop plus balloon.

### Aero Keyboard Chime (P2)

- **Inspired by:** Windows Vista / 7 chord chimes (Windows 7 'Windows Background', 'Notify')
- **Character:** A soft glassy chord pluck with a long gentle decay.
- **Start DNA:** `xpnotify#8H0,7,12/print#4L40;A0D1500S0R1000`
- **Sources:** `xpnotify`, `print`, `xpding`
- **Recipe:**
  - XP Notify, voiced as an open chord.

### Aquarium Ambience (P3)

- **Inspired by:** Aero aquariums, screensavers ('Aquarium', 'Windows Media visualizations')
- **Character:** Water movement, bubbles and a soft pad: calm, glossy.
- **Start DNA:** `recycle<<#4F/balloon<IballoonIballoon>E#4F/logon<#8L60;A1200S90R3000`
- **Sources:** `recycle`, `balloon`, `logon`
- **Recipe:**
  - Slowed crumple = water; balloon splice = bubbles; logon = calm pad.

### Vista Sparkle Glissando (P2)

- **Inspired by:** Vista 'Windows Startup' / iPod-era sparkles
- **Character:** A rising cascade of crystalline notes.
- **Start DNA:** `chimes>R@0CP#8/print#4L50;A0D2000S0R1500`
- **Sources:** `chimes`, `print`
- **Recipe:**
  - Reversed x2 chimes repeated.
  - [planned offsets] harmony H0,4,7,12 voices with 40 ms offsets each = an upward gliss.

### Liquid Glass Bell (P2)

- **Inspired by:** Aero-style glass bell (Apple 'Glass', 'Crystal' alert sounds)
- **Character:** A pure, bright, glassy single tone with a soft halo.
- **Start DNA:** `xpding>#8U2~5/xpding>RER#4L30;A0D1800S0R1500`
- **Sources:** `xpding`, `chimes`
- **Recipe:**
  - The bell, with a reverse-reverb halo.


## Aesthetic: Y2K, web portal and corporate

### Corporate Logo Sting (P1, rank 27)

- **Inspired by:** 2000s corporate intro stings (Intel bong, PowerPoint templates, 'Microsoft Sound')
- **Character:** Three to five bright, confident notes, then a big shiny chord bloom with reverb. Sounds like 'innovation'.
- **Start DNA:** `tada#8H0,12/chimes>#4L50/startup@20[#4L40;A0D1800S30R2000`
- **Sources:** `tada`, `chimes`, `startup`
- **Recipe:**
  - tada fanfare, chime sparkle, startup bloom.
  - Play a I-V chord.

### Web Portal Click (P2)

- **Inspired by:** 2000s web-portal UI clicks (Internet Explorer 'navigation start' click, Yahoo! / MSN portals)
- **Character:** A crisp, dry, pitched tick.
- **Start DNA:** `start#16F;A0S100R30V50`
- **Sources:** `start`, `xpstart`, `menu`, `popup`
- **Recipe:**
  - start.wav: the actual IE navigation click.
  - Drop F for a pitched percussion kit.

### Hold Music Muzak Keys (P2)

- **Inspired by:** 2000s on-hold music / corporate training video (Kevin MacLeod-era stock)
- **Character:** Bland, bright, slightly chorused EP and strings: inoffensive, glossy.
- **Start DNA:** `xpding@20]#6H0,24/ringout@25[@35]#5L70/logoff@30[#5U2~10L40;A0D1500S40R1200`
- **Sources:** `xpding`, `ringout`, `logoff`
- **Recipe:**
  - The DX EP plus strings combination, mixed polite.

### Dial-up Handshake Texture (P2)

- **Inspired by:** 56k modem handshake (Y2K internet)
- **Character:** Screeching tones, noise bursts and pitched beeps in a sequence.
- **Start DNA:** `ringout>IrecycleIbatcrit>>Irecycle>>IringinE#8F;A0S100R200`
- **Sources:** `ringout`, `ringin`, `recycle`, `batcrit`
- **Recipe:**
  - A tone-noise-tone splice.
  - Try ringin's chirp.

### Nokia-style Ringtone Lead (P2)

- **Inspired by:** Early-2000s monophonic ringtones
- **Character:** A pure square-ish tone, staccato, high and cheerful.
- **Start DNA:** `batlow@5[@20]@0CP@0CP@0CP++>#8;A0D200S60R40`
- **Sources:** `batlow`, `batcrit`
- **Recipe:**
  - A looped clipped alert tone, up an octave.

### Tech Presentation Pad (P2)

- **Inspired by:** Corporate keynote background pads (2000s product launch)
- **Character:** A bright, optimistic, wide synth-pad bed with a gentle pulse.
- **Start DNA:** `logon@20[#8U2~8/start>@0CP@0CP@0CP@0CP#4FL20;A400S90R2000`
- **Sources:** `logon`, `startup`, `start`
- **Recipe:**
  - The logon pad with a quiet ticking clock layer.

### Y2K Trance Gate (P2)

- **Inspired by:** Y2K trance-gate pads (ATB '9PM', Darude)
- **Character:** A pad chopped into a 16th-note rhythmic gate.
- **Start DNA:** `chord@20[@15]@0CP@0CP@0CP@0CP#12U4~20;A0S100R100`
- **Sources:** `chord`, `logon`
- **Recipe:**
  - Seams of paste-insert copies give the rhythmic gate.
  - [planned env graph] a draw-a-gate pattern.

### Windows Error Choir (P1, rank 28)

- **Inspired by:** Windows-error remixes (YouTube 'Windows sounds' meme music)
- **Character:** Error and critical sounds as playable instruments: comic and nostalgic.
- **Start DNA:** `error#8/critstop#4L60/exclaim#4L50;A0D600S30R300`
- **Sources:** `error`, `critstop`, `exclaim`, `batcrit`
- **Recipe:**
  - The source sounds as they are, layered and chromatically playable. That is the meme.

### Flash Intro Whoosh-Hit (P2)

- **Inspired by:** 2000s Flash website intros (whoosh, then bright hit)
- **Character:** A fast noise sweep, then a sparkly impact chord.
- **Start DNA:** `restore#4F/tada@20]#8H0,12/chimes>#4L50;A0D800S0R1000`
- **Sources:** `restore`, `tada`, `chimes`
- **Recipe:**
  - [planned offsets] whoosh at 0 ms, hit at 250 ms.

### CD-ROM Encyclopedia Pad (P3)

- **Inspired by:** 90s/Y2K edutainment (Encarta, MS Plus! themes)
- **Character:** A gentle, clean, wondering digital pad with bell plinks.
- **Start DNA:** `logon@20[#8U2~6/chimes@20]>#4L40;A300S90R1800`
- **Sources:** `logon`, `chimes`
- **Recipe:**
  - The logon pad with chime plinks.

### Shutdown Fall (P2)

- **Inspired by:** Windows XP Shutdown as a falling cadence instrument
- **Character:** A descending melancholic cadence, played chromatically.
- **Start DNA:** `shutdown#10U2~6/logoff#6L50;A0S100R2000`
- **Sources:** `shutdown`, `logoff`
- **Recipe:**
  - The source, layered with logoff.

# Modern and classic favorites: what is loved, and our versions

The favorite presets and categories of 15 soft synths, libraries and drum machines, and 41 targets that answer them with Sound Recorders. Machine-readable copy: `modern-favorites.json`. Genre targets are in `genres.md`.

- **Status:** research only. Nothing here is committed, and no core, DNA.md or plugin file was changed.
- **Checks:** Every dna and v3_dna was parsed by core/dna.cpp parse() on main (library catalogue loaded) and by design/v3 canonical3() on preset-engine-2: no unknown NAME, no empty layer, at most 1024 bytes; stored in canonical form. Every recipe is design/v3 toRecipe(OneLine) and parses back (fromRecipe) to the same canonical DNA. K is computed from the measured root of the first key-tracked layer (windows-sounds.json, library note names), other tonal layers get T to the nearest octave. Nobody has listened to them yet.
- **Inputs:** `../../DNA.md` (DNA v2), `preset-targets.md` (198 classic targets; this file does not repeat them),
  `~/ws-aes/.../AESTHETIC-PRESETS.md` (vaporwave and Frutiger Aero, 101 presets; not repeated),
  `~/ws-pe2/.../PRESET-ENGINE-2.md` (v3: windows `W`, voice modes `N`, stacks `S`, random `Y`, tape `V`/`Z`,
  grains `G`, kits `k` (section 15), the mine-grid sequencer `x`/`q` (section 9), recipes (section 17)),
  `windows-sounds.json` (measured roots), `../catalog/*.json` (library disc).
- **Names:** every preset name is original. No brand, trademark, artist, label or song name is used in a name.
  `inspired_by` names the source for research only.

**How to read "iconic".** Where a vendor publishes a library or preset count it is cited. Individual factory preset names were not verified one by one, so targets are written against preset *categories* and well-documented sounds (the supersaw, the 808 boom, the trancegate, the felt piano), not against a named factory patch. Already covered elsewhere and not repeated: the Omnisphere evolving pad and "Pluck Box", Massive growl, Serum supersaw pluck and granular air, Spire and Sylenth trance, Nexus trance pad, Kontakt "Bowed Glass" and "Music Box" (preset-targets.md, section "Pad and texture soft synths").

## Counts

| Favorite | bass | lead | pad | chord | pluck | keys | strings | brass | bell | mallet | arp | perc | drums | Total | P1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Serum (Xfer Records) | 2 |  |  | 1 | 1 |  |  |  |  |  |  |  |  | 4 | 2 |
| Vital (Matt Tytel) |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  | 2 | 1 |
| Pigments (Arturia) |  |  | 1 |  |  |  |  |  |  |  | 1 |  |  | 2 | 1 |
| Diva (u-he) | 1 |  |  |  |  |  |  | 1 |  |  |  |  |  | 2 | 1 |
| Massive and Massive X (Native Instruments) | 2 |  |  |  |  |  |  |  |  |  |  |  |  | 2 | 1 |
| Sylenth1 (LennarDigital) |  | 1 |  |  | 1 |  |  |  |  |  |  |  |  | 2 | 1 |
| Spire (Reveal Sound) |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 1 | 1 |
| Omnisphere (Spectrasonics) |  |  | 1 |  | 1 |  |  |  |  |  |  |  |  | 2 | 1 |
| Keyscape (Spectrasonics) |  |  |  |  |  | 3 |  |  |  |  |  |  |  | 3 | 1 |
| Kontakt factory and famous libraries (Native Instruments and others) |  |  |  |  |  |  | 1 |  |  |  |  | 1 |  | 2 | 1 |
| Arturia V Collection: Jupiter-8 V, Prophet V, Mini V, CS-80 V |  | 1 | 1 |  |  |  |  | 2 |  |  |  |  |  | 4 | 2 |
| Nexus (reFX) |  |  | 1 |  |  |  |  |  |  |  |  |  |  | 1 | 1 |
| Battery and the drum machines (808, 909, 707, LinnDrum, SP-1200, MPC) |  |  |  |  |  |  |  |  |  |  |  |  | 6 | 6 | 6 |
| LABS (Spitfire Audio) |  |  |  |  |  | 2 | 1 | 1 |  |  |  |  |  | 4 | 2 |
| Ableton Live factory instruments | 1 |  |  |  |  |  |  |  | 1 | 1 |  | 1 |  | 4 | 2 |
| **Total** | **6** | **4** | **5** | **1** | **3** | **5** | **2** | **4** | **1** | **1** | **1** | **2** | **6** | **41** | **24** |

## Serum (Xfer Records)

- **Kind:** wavetable synth, 2014; Serum 2 in 2025
- **Loved for:** Visual wavetable editing and warp modes, clean (alias-free) oscillators, the drag-and-drop workflow, and the third-party preset economy around it. It defined the sound of 2010s EDM and future bass.
- **Iconic categories:** future-bass supersaw chords with pitch-bend wobble and sidechain pump; growl/neuro basses from warped wavetables; clean sub plus mid-bass layers; bright plucks for house and progressive; formant "vowel" basses; Third-party packs dominate; Splice lists its most popular Serum presets; Syntorial reports Serum as the second most-shared synth on Presetshare.
- **Note:** Factory preset names were not verified one by one; targets are by category.
- **Sources:** [Xfer Records: Serum preset packs](https://xferrecords.com/preset_packs/serum), [Splice blog: 22 of the most popular Serum presets](https://splice.com/blog/?p=24081), [Syntorial: best Serum presets (Serum second on Presetshare)](https://www.syntorial.com/highlights/best-serum-presets/)

#### Bent Future Chord (chord, P1, XP badge)

- **Inspired by:** future-bass supersaw chords (Serum era, 2014-2018)
- **Character:** Supersaw-like major-7 chord with a pitch-bend dip and a pumping envelope.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP#12H0,4,7,11U2~25Ja0,10.60,100.214,70.428,10.440,100;A0R300B2K60`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 12rec notes +0 +4 +7 +11 unison 2 +-25c amp 0:10,60:100,214:70,428:10,440:100 | atk 0ms rel 300ms bend +-2 root C4`
- **DNA v3 (later):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP#12H0,4,7,11U2~25Ja0,10.60,100.214,70.428,10.440,100Sd4Vs40,120;A0R300B2K60q0`
  - Features: scale (q), stack (round-robin, strum, diatonic chords, groups), tape wow/flutter/scoop
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: chord, chordxp, xpding; library: epiano_yamaha_vibe, harp_c5
- **Sound Recorder feel:** The "wobble" is a v3 scoop (40 cents up from below over 120 ms); v2 uses the bend wheel.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workstation-classics. Notes before stealing: 1.

#### Warp Growl (bass, P1, XP badge)

- **Inspired by:** warped wavetable growl bass
- **Character:** A bell slice looped, clipped and self-flanged, three octaves down.
- **DNA v2 (now):** `default@t40[@t20]@25]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP+++C@3X<<#16U2~15;A0R120K31`
  - Recipe: `default cut before 40ms cut after 20ms cut after 25% double x9 louder x3 copy at 3% mix paste slower x2 16rec unison 2 +-15c | atk 0ms rel 120ms root G1`
- **DNA v3 (later):** `default@t40[@t20]@25]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP+++C@3X<<#16U2~15Nmg20;A0R120K31`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `default`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, balloon, xpding; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workstation-classics. Notes before stealing: 8.

#### Glass Pluck Plus (pluck, P2, XP badge)

- **Inspired by:** clean Serum pluck (progressive house)
- **Character:** XP default bell trimmed, octave stack, long echo.
- **DNA v2 (now):** `default@15]#8H0,12/default@15]<E>#6L35O250;A0D350S0R250K75`
  - Recipe: `default cut after 15% 8rec notes +0 +12 / default cut after 15% slower echo faster 6rec level 35% offset 250ms | atk 0ms dec 350ms sus 0% rel 250ms root D#5`
- **Sounds used:** `default`
- **Swap candidates:** Windows: xpding, ding, dingxp, chimes, balloon; library: kalimba_c4, guzheng_a3, harp_c5, drip_short
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 4.

#### Vowel Mid Bass (bass, P2, W3.11 badge)

- **Inspired by:** formant/vowel mid basses
- **Character:** The 1961 vowel looped and clipped with sub under it.
- **DNA v2 (now):** `ems_704_vowel_a3@30[@20]@0CP@0CP@0CP@0CP++<#10/ringout@20[@40]@0CP@0CP@0CP<<#6L60;A0R100K45`
  - Recipe: `ems_704_vowel_a3 cut before 30% cut after 20% double x4 louder x2 slower 10rec / ringout cut before 20% cut after 40% double x3 slower x2 6rec level 60% | atk 0ms rel 100ms root A2`
- **DNA v3 (later):** `ems_704_vowel_a3@30[@20]@0CP@0CP@0CP@0CP++<#10Nm/ringout@20[@40]@0CP@0CP@0CP<<#6L60Nm;A0R100K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`; library: `ems_704_vowel_a3`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workstation-classics. Notes before stealing: 6.

## Vital (Matt Tytel)

- **Kind:** spectral-warping wavetable synth, free tier, 2020
- **Loved for:** Free, with the full engine; spectral warp modes; text-to-wavetable; a factory bank of 75 presets in the free tier; ultra-visual modulation.
- **Iconic categories:** spectral-warp leads that morph; text-to-wavetable "speech" oscillators; clean modern basses and pads in the factory set
- **Sources:** [MusicTech: Vital, a free wavetable synth with spectral warping](https://www.musictech.net/news/matt-tytel-vital-free-synth/), [MusicRadar: Fantastic free plugins, Vital](https://www.musicradar.com/music-tech/plugins/fantastic-free-plugins-and-how-to-use-them-vital)

#### Spoken Wavetable (lead, P1, W3.11 badge)

- **Inspired by:** Vital text-to-wavetable
- **Character:** A word from a Prelinger narration looped as an oscillator.
- **DNA v2 (now):** `prelinger_information_machine_a@40[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#10;A5R200K59`
  - Recipe: `prelinger_information_machine_a cut before 40% cut after 20ms cut after 20% double x9 10rec | atk 5ms rel 200ms root B3`
- **Sounds used:** none; library: `prelinger_information_machine_a`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Speech becomes a wavetable the way Vital's text-to-wavetable does: one 4 ms slice of a voice, looped.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: workstation-classics. Notes before stealing: 10.

#### Spectral Morph Pad (pad, P2, XP badge)

- **Inspired by:** spectral warp pads
- **Character:** Two slices of startup crossfaded by macro 1.
- **DNA v2 (now):** `startup@20[@30]<#8U2~10/startup@70[@30]<#8U2~10L0;A600S90R1500m11L100,0m12L0,100m1=0K56`
  - Recipe: `startup cut before 20% cut after 30% slower 8rec unison 2 +-10c / startup cut before 70% cut after 30% slower 8rec unison 2 +-10c level 0% | atk 600ms sus 90% rel 1.5s m1 L1 level 100-0 m1 L2 level 0-100 m1 0% root G#3`
- **Sounds used:** `startup`
- **Swap candidates:** Windows: logon, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 4.

## Pigments (Arturia)

- **Kind:** multi-engine synth (VA, wavetable, sample/granular, harmonic, modal)
- **Loved for:** Colour-coded modulation, granular sample engine (from v2), additive harmonic engine (v3), sequencer-driven presets; reviewers call it a true power synth.
- **Iconic categories:** granular cinematic pads from samples; sequenced arps with macro sweeps; additive bells
- **Sources:** [MusicRadar: Arturia Pigments review](https://www.musicradar.com/reviews/arturia-pigments), [Sound on Sound: Arturia Pigments 4 review](https://www.soundonsound.com/reviews/arturia-pigments-4)

#### Lobby Grain Field (pad, P1, W3.11 badge)

- **Inspired by:** Pigments granular sample pads
- **Character:** Hotel lobby ambience as a grain cloud.
- **DNA v2 (now):** `hotel_lobby_open_plan<#12;A1000S90R3000`
  - Recipe: `hotel_lobby_open_plan slower 12rec | atk 1s sus 90% rel 3s`
- **DNA v3 (later):** `hotel_lobby_open_plan<#12Gp.3j.3z60~200n30c20s.1v6w.8;A1000S90R3000`
  - Features: grains
- **Sounds used:** none; library: `hotel_lobby_open_plan`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, chord; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 grains: ~100/s sample-exact on 3.11; XP after phase 6. Pack: workstation-classics. Notes before stealing: 12.

#### Colour Sequence Arp (arp, P2, XP badge)

- **Inspired by:** Pigments sequencer presets
- **Character:** Bell pluck arped from the mine grid.
- **DNA v2 (now):** `default@12]#8/xpding@15]<#6L40T4;A0D300S0R200K75`
  - Recipe: `default cut after 12% 8rec / xpding cut after 15% slower 6rec level 40% transpose +4 | atk 0ms dec 300ms sus 0% rel 200ms root D#5`
- **DNA v3 (later):** `default@12]#8/xpding@15]<#6L40T4;A0D300S0R200K75q4xg45n2`
  - Features: mine-grid sequencer/arp (x), scale (q)
- **Sounds used:** `default`, `xpding`
- **Swap candidates:** Windows: ding, chimes; library: kalimba_g5, glockenspiel_g4
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 6.

## Diva (u-he)

- **Kind:** virtual analog with circuit-modelled filters and oscillators
- **Loved for:** The filters and oscillators of classic polysynths and monosynths modelled at component level; "Divine" accuracy mode; reviewers single out the filters and the presets.
- **Iconic categories:** fat monosynth basses; poly brass; warm poly pads; self-oscillating filter sweeps
- **Sources:** [Sound on Sound: u-he Diva review](https://www.soundonsound.com/reviews/uhe-diva), [MusicRadar: u-he Diva review (filters, "terrific presets")](https://www.musicradar.com/reviews/tech/u-he-diva-542059)

#### Ladder Mono Bass (bass, P1, W3.11 badge)

- **Inspired by:** Diva-style monosynth bass
- **Character:** Three detuned buzzes clipped two octaves down; mono glide.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#5/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<+#5L50/ringout@20[@40]@0CP@0CP@0CP<<<#4U2~8L60T2;A0D500S60R100K35`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 slower x2 louder 5rec / ringout cut before 150ms cut after 20ms cut after 20% double x9 slower louder 5rec level 50% / ringout cut before 20% cut after 40% double x3 slower x3 4rec unison 2 +-8c level 60% transpose +2 | atk 0ms dec 500ms sus 60% rel 100ms root B1`
- **DNA v3 (later):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#5Nmg40/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<+#5L50Nmg40/ringout@20[@40]@0CP@0CP@0CP<<<#4U2~8L60T2Nmg40;A0D500S60R100K35`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workstation-classics. Notes before stealing: 2.

#### Poly Brass Circuit (brass, P2, XP badge)

- **Inspired by:** analog poly brass
- **Character:** Fanfare loop with a slow brass attack and swell.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP#12U2~12Ja0,0.80,100.400,75;A0R250K60`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 12rec unison 2 +-12c amp 0:0,80:100,400:75 | atk 0ms rel 250ms root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, critstop; library: trumpet_sus_c4, trombone_sus_c3, horn_sus_c3, tuba_sus_f1
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 6.

## Massive and Massive X (Native Instruments)

- **Kind:** wavetable synth, 2007 / 2019
- **Loved for:** Defined DnB and the dubstep explosion; wavetables like Carbon, Multiplex and Square-Saw were early-dubstep favourites; routing Osc 3 around the filter as the sub; performer LFO wobbles.
- **Iconic categories:** wobble basses with tempo-synced LFO; reese and growl; big-room leads
- **Sources:** [Native Instruments blog: Massive, past presets and future (dubstep wavetables)](https://blog.native-instruments.com/massive-past-presets-future/)

#### Performer Wobble (bass, P1, XP badge)

- **Inspired by:** Massive performer-LFO wobble
- **Character:** A stepped, drawn wobble pattern over a clipped sine stack.
- **DNA v2 (now):** `xpringout@20[@40]@0CP@0CP@0CP+++<<<#16U2~12Ja0,100.107,10.160,100.214,10.321,100.375,30.428,100;A0R100m21Z100,33m2=0K33`
  - Recipe: `xpringout cut before 20% cut after 40% double x3 louder x3 slower x3 16rec unison 2 +-12c amp 0:100,107:10,160:100,214:10,321:100,375:30,428:100 | atk 0ms rel 100ms m2 L1 envtime 100-33 m2 0% root A1`
- **Sounds used:** `xpringout`
- **Swap candidates:** Windows: ringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 8.

#### Square Saw Sub Route (bass, P2, W3.11 badge)

- **Inspired by:** Massive square-saw plus routed sub
- **Character:** Buzz mid and sine sub, both mono.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#8/ringout@20[@40]@0CP@0CP@0CP<<<#8L80T2;A0R100K35`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 slower x2 louder 8rec / ringout cut before 20% cut after 40% double x3 slower x3 8rec level 80% transpose +2 | atk 0ms rel 100ms root B1`
- **DNA v3 (later):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#8Nm/ringout@20[@40]@0CP@0CP@0CP<<<#8L80T2Nm;A0R100K35`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workstation-classics. Notes before stealing: 8.

## Sylenth1 (LennarDigital)

- **Kind:** virtual analog, 2007
- **Loved for:** Fat, CPU-light trance and EDM sound; its factory bank has been used everywhere; the go-to for trance leads, plucks and supersaw stacks.
- **Iconic categories:** trance plucks with delay; supersaw stacks; trance basses
- **Sources:** [Loopmasters: the best Sylenth1 presets (factory bank "used and abused")](https://www.loopmasters.com/articles/4316-The-Best-Sylenth1-Presets-in-the-World-including-free-ones)

#### Arena Pluck (pluck, P1, XP badge)

- **Inspired by:** Sylenth trance pluck
- **Character:** Fanfare blast trimmed to a pluck, unison and long echo.
- **DNA v2 (now):** `tadaxp@6]#8U3~18/tadaxp@6]<E>#6L35O326;A0D250S0R250K60`
  - Recipe: `tada-xp cut after 6% 8rec unison 3 +-18c / tada-xp cut after 6% slower echo faster 6rec level 35% offset 326ms | atk 0ms dec 250ms sus 0% rel 250ms root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: default, xpding, ding, dingxp, chimes, balloon; library: kalimba_c4, guzheng_a3, harp_c5, drip_short
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 2.

#### Four Osc Saw Stack (lead, P2, XP badge)

- **Inspired by:** Sylenth four-oscillator lead
- **Character:** Four fanfare loops: unison, octave, fifth.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP#6U3~20/tadaxp@40[@20]@0CP@0CP@0CP@0CP>#4L40/tadaxp@40[@20]@0CP@0CP@0CP@0CP#4T7L30;A10R300K60`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 6rec unison 3 +-20c / tada-xp cut before 40% cut after 20% double x4 faster 4rec level 40% / tada-xp cut before 40% cut after 20% double x4 4rec transpose +7 level 30% | atk 10ms rel 300ms root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 2.

## Spire (Reveal Sound)

- **Kind:** hybrid VA/wavetable, 2013
- **Loved for:** Big-room and trance leads, supersaws with many voices, efficient; a staple of EDM, trance and synthwave.
- **Iconic categories:** big-room leads; hyper-saw pads; EDM plucks
- **Sources:** [Bedroom Producers Blog: Reveal Sound Spire review](https://bedroomproducersblog.com/2015/10/20/reveal-sound-spire-review/)

#### Festival Main Lead (lead, P1, XP badge)

- **Inspired by:** Spire big-room lead
- **Character:** Fanfare loop, octave up, clipped, nine voices.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP>++#12U4~28/tadaxp@40[@20]@0CP@0CP@0CP@0CP#4L50;A0R250K72`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 faster louder x2 12rec unison 4 +-28c / tada-xp cut before 40% cut after 20% double x4 4rec level 50% | atk 0ms rel 250ms root C5`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 3.

## Omnisphere (Spectrasonics)

- **Kind:** hybrid sample/synth workstation
- **Loved for:** Huge psychoacoustic sample library (burned pianos, bowed and struck objects), deep layering, "Hardware Library" patches; used on hit records, games and film.
- **Iconic categories:** evolving textures from unusual sources; cinematic pads; plucked-object arps; the ILIO Fame Series recreates famous sounds in it
- **Sources:** [Spectrasonics: Omnisphere](https://www.spectrasonics.net/products/omnisphere/), [ILIO: The Fame Series, Classic Sounds for Omnisphere](https://www.ilio.com/the-fame-series-classic-sounds)

#### Burnt Chord Texture (pad, P1, XP badge)

- **Inspired by:** Omnisphere psychoacoustic textures (sampled destroyed instruments)
- **Character:** The 3.1 chord reversed, slowed and echoed, with crumple noise as the burning.
- **DNA v2 (now):** `chord<RE<E#10U2~10/recycle<<E#4FL30;A1200S90R3000K31`
  - Recipe: `chord slower reverse echo slower echo 10rec unison 2 +-10c / recycle slower x2 echo 4rec fixed level 30% | atk 1.2s sus 90% rel 3s root G1`
- **Sounds used:** `chord`, `recycle`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: instruments-archive. Notes before stealing: 4.

#### Object Pluck Arp (pluck, P2, W3.11 badge)

- **Inspired by:** plucked objects (Omnisphere arp patches)
- **Character:** Glass and drip plucks round-robin.
- **DNA v2 (now):** `glass_tap#8/drip_short#8;A0R400`
  - Recipe: `glass_tap 8rec / drip_short 8rec | atk 0ms rel 400ms`
- **DNA v3 (later):** `glass_tap#8Sg1/drip_short#8Sg1;A0R400q8xg50n2`
  - Features: mine-grid sequencer/arp (x), scale (q), stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** none; library: `glass_tap`, `drip_short`
- **Swap candidates:** Windows: default, xpding, ding, dingxp, chimes, balloon; library: kalimba_c4, guzheng_a3, harp_c5
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 8.

## Keyscape (Spectrasonics)

- **Kind:** keyboard collection: 36 instruments, 465 patches
- **Loved for:** Deeply sampled pianos and electromechanical keys, including rare ones (Clavinet-Pianet duo, Pianet T/N/M, CP-70, Wurlitzer 140B/200A, Rhodes Mark I, toy pianos).
- **Iconic categories:** tine e-pianos; reed e-pianos; electric grand; toy piano and celesta
- **Sources:** [Spectrasonics: Keyscape library (36 instruments, 465 patches)](https://www.spectrasonics.net/products/keyscape/keyscape-library.php), [MusicRadar: Spectrasonics Keyscape review](https://www.musicradar.com/reviews/tech/spectrasonics-keyscape-643857)

#### Reed Classroom Piano (keys, P1, XP badge)

- **Inspired by:** reed e-piano (Wurlitzer-style)
- **Character:** Ringout loop clipped a little: reedy.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP+#10/xpding@20]#6L40T-2;A0D1500S35R300K69`
  - Recipe: `ringout cut before 20% cut after 40% double x2 louder 10rec / xpding cut after 20% 6rec level 40% transpose -2 | atk 0ms dec 1.5s sus 35% rel 300ms root A4`
- **Sounds used:** `ringout`, `xpding`
- **Swap candidates:** Windows: print, default, ding, chord; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: instruments-archive. Notes before stealing: 6.

#### Stage Tine Suitcase (keys, P2, XP badge)

- **Inspired by:** tine e-piano (Rhodes-style)
- **Character:** Epiano bell sample with sine body.
- **DNA v2 (now):** `epiano_bell_c3#8/print@10[@50]<#6L35T2;A0D2500S30R600K48`
  - Recipe: `epiano_bell_c3 8rec / print cut before 10% cut after 50% slower 6rec level 35% transpose +2 | atk 0ms dec 2.5s sus 30% rel 600ms root C3`
- **Sounds used:** `print`; library: `epiano_bell_c3`
- **Swap candidates:** Windows: xpding, default, ding, chord, ringout; library: epiano_yamaha_vibe, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 6.

#### Toy Recital (keys, P2, W3.11 badge)

- **Inspired by:** toy piano
- **Character:** Music box and glockenspiel, short.
- **DNA v2 (now):** `music_box_note#8/glockenspiel_c6#6L40;A0R800K84`
  - Recipe: `music_box_note 8rec / glockenspiel_c6 6rec level 40% | atk 0ms rel 800ms root C6`
- **Sounds used:** none; library: `music_box_note`, `glockenspiel_c6`
- **Swap candidates:** Windows: xpding, print, default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 6.

## Kontakt factory and famous libraries (Native Instruments and others)

- **Kind:** sampler platform
- **Loved for:** The platform for orchestral, cinematic and keyboard libraries: factory vintage organs, retro machines, orchestral; famous third-party: felt and upright pianos, scored strings, cinematic percussion, vocal-texture engines.
- **Iconic categories:** felt piano; cinematic hits and impacts; ostinato strings; vintage organs; retro machines (string machines, tape keyboards)
- **Sources:** [Wikipedia: Native Instruments (Kontakt, Massive, Battery)](https://en.wikipedia.org/wiki/Native_Instruments)

#### Trailer Impact (perc, P1, XP badge)

- **Inspired by:** cinematic impact libraries
- **Character:** Critical stop, thunder and balloon boom slowed.
- **DNA v2 (now):** `critstop<<E#6/thunder_rumble@5[@15]#4FL60/balloon<<<#4FL70;A0R3000K24`
  - Recipe: `critstop slower x2 echo 6rec / thunder_rumble cut before 5% cut after 15% 4rec fixed level 60% / balloon slower x3 4rec fixed level 70% | atk 0ms rel 3s root C1`
- **Sounds used:** `critstop`, `balloon`; library: `thunder_rumble`
- **Swap candidates:** Windows: menu, xpstart, infobar, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 4.

#### Ostinato Section (strings, P2, W3.11 badge)

- **Inspired by:** scored-strings ostinato
- **Character:** Violin section cut short (spiccato), round-robin pair.
- **DNA v2 (now):** `violin_section_sus_c4@5]#8/violin_section_sus_c4@6]><#8;A0D200S0R120K60`
  - Recipe: `violin_section_sus_c4 cut after 5% 8rec / violin_section_sus_c4 cut after 6% faster slower 8rec | atk 0ms dec 200ms sus 0% rel 120ms root C4`
- **DNA v3 (later):** `violin_section_sus_c4@5]#8Sg1/violin_section_sus_c4@6]><#8Sg1;A0D200S0R120K60`
  - Features: stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** none; library: `violin_section_sus_c4`
- **Swap candidates:** Windows: startup, logon, logoff; library: cello_section_sus_c3, erhu_d3
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 8.

## Arturia V Collection: Jupiter-8 V, Prophet V, Mini V, CS-80 V

- **Kind:** modelled classic synths
- **Loved for:** Faithful models of the classic polysynths and the Minimoog: Jupiter pads and arps, Prophet brass and sync, Minimoog bass and lead glide, CS-80 brass with expressive swells.
- **Iconic categories:** Jupiter-8 lush pads and sequenced arps; Prophet-5 brass and sync leads; Minimoog bass and glide lead; CS-80 brass swells (Blade Runner-era)
- **Sources:** [Arturia: V Collection](https://www.arturia.com/products/software-instruments/v-collection/overview), [Wikipedia: Roland Jupiter-8](https://en.wikipedia.org/wiki/Roland_Jupiter-8), [Wikipedia: Sequential Circuits Prophet-5](https://en.wikipedia.org/wiki/Sequential_Circuits_Prophet-5), [Wikipedia: Minimoog](https://en.wikipedia.org/wiki/Minimoog), [Wikipedia: Yamaha CS-80](https://en.wikipedia.org/wiki/Yamaha_CS-80)

#### Eight Voice Silk Pad (pad, P1, XP badge)

- **Inspired by:** Jupiter-8 pad
- **Character:** Logon and startup slices with wide unison.
- **DNA v2 (now):** `logon<@15[#8U3~12/startup@20[@40]<#8U2~10L50;A700S90R1600K44`
  - Recipe: `logon slower cut before 15% 8rec unison 3 +-12c / startup cut before 20% cut after 40% slower 8rec unison 2 +-10c level 50% | atk 700ms sus 90% rel 1.6s root G#2`
- **Sounds used:** `logon`, `startup`
- **Swap candidates:** Windows: logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: instruments-archive. Notes before stealing: 2.

#### Five Voice Brass (brass, P2, XP badge)

- **Inspired by:** Prophet-5 brass
- **Character:** Fanfare loop with brass swell envelope.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP+#12U2~10Ja0,0.60,100.300,70;A0R200K60`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 louder 12rec unison 2 +-10c amp 0:0,60:100,300:70 | atk 0ms rel 200ms root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, critstop; library: trumpet_sus_c4, trombone_sus_c3, horn_sus_c3, tuba_sus_f1
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: instruments-archive. Notes before stealing: 6.

#### Mono Glide Lead (lead, P1, W3.11 badge)

- **Inspired by:** Minimoog lead with glide
- **Character:** Three buzzes, mono with glide.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP+#6/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#5T12L50/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#5T7L30;A5R150K59`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 louder 6rec / ringout cut before 150ms cut after 20ms cut after 20% double x9 5rec transpose +12 level 50% / ringout cut before 150ms cut after 20ms cut after 20% double x9 5rec transpose +7 level 30% | atk 5ms rel 150ms root B3`
- **DNA v3 (later):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP+#6Nlg90/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#5T12L50Nlg90/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#5T7L30Nlg90;A5R150K59`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: tadaxp, tada, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: instruments-archive. Notes before stealing: 5.

#### Ribbon Brass Swell (brass, P2, XP badge)

- **Inspired by:** CS-80 brass with swell
- **Character:** Trumpet and fanfare swelling with wide unison.
- **DNA v2 (now):** `trumpet_sus_c4<#8U2~15/tadaxp@40[@20]@0CP@0CP@0CP<#6L50;A400R900B12K48`
  - Recipe: `trumpet_sus_c4 slower 8rec unison 2 +-15c / tada-xp cut before 40% cut after 20% double x3 slower 6rec level 50% | atk 400ms rel 900ms bend +-12 root C3`
- **Sounds used:** `tadaxp`; library: `trumpet_sus_c4`
- **Swap candidates:** Windows: tada, critstop; library: trombone_sus_c3, horn_sus_c3, tuba_sus_f1
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 4.

## Nexus (reFX)

- **Kind:** ROM-style preset player
- **Loved for:** Instant, mix-ready trance and EDM: trancegate pads (52 gate presets ship with it), supersaws, pianos and strings; expansions per genre.
- **Iconic categories:** trancegate pads; big supersaw leads; dance pianos
- **Sources:** [reFX: Nexus expansion Trance Elements](https://refx.com/nexus/expansion/trance-elements/), [MusicRadar: reFX Nexus2 review](https://www.musicradar.com/reviews/tech/refx-nexus2-173279)

#### Club Gate Stack (pad, P1, XP badge)

- **Inspired by:** Nexus trancegate pad
- **Character:** Logoff sustained, 1/16 gate at 140 drawn.
- **DNA v2 (now):** `logoff@20[@50]<#12U2~10Ja0,100.53,100.54,0.107,0.108,100.160,100.161,0.214,0;A0R200K51`
  - Recipe: `logoff cut before 20% cut after 50% slower 12rec unison 2 +-10c amp 0:100,53:100,54:0,107:0,108:100,160:100,161:0,214:0 | atk 0ms rel 200ms root D#3`
- **Sounds used:** `logoff`
- **Swap candidates:** Windows: startup, logon, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workstation-classics. Notes before stealing: 6.

## Battery and the drum machines (808, 909, 707, LinnDrum, SP-1200, MPC)

- **Kind:** drum samplers and classic machines
- **Loved for:** 808: the long boom kick, snappy snare, cowbell and claps; 909: punchy kick and sampled hats/cymbals; 707: bright, simple digital kit; LinnDrum: the 80s pop snare and claps; SP-1200: 12-bit 26.04 kHz grit; MPC: swing and pads. Battery has kits built around these machines.
- **Iconic categories:** 808 boom kick; 909 kick and open hat; 707 bright kit; LinnDrum snare; SP-1200 grit; MPC swing
- **Sources:** [Wikipedia: Roland TR-808](https://en.wikipedia.org/wiki/Roland_TR-808), [Wikipedia: Roland TR-909](https://en.wikipedia.org/wiki/Roland_TR-909), [Wikipedia: Roland TR-707](https://en.wikipedia.org/wiki/Roland_TR-707), [Wikipedia: LinnDrum](https://en.wikipedia.org/wiki/LinnDrum), [Wikipedia: E-mu SP-1200 (12-bit, 26.04 kHz)](https://en.wikipedia.org/wiki/E-mu_SP-1200), [Wikipedia: Akai MPC](https://en.wikipedia.org/wiki/Akai_MPC), [KVR forum: favorite 80s kits from Battery (606/707/808/909/DMX/LinnDrum kits)](https://www.kvraudio.com/forum/viewtopic.php?p=7574006), [MusicRadar: Native Instruments Battery 4 review](https://musicradar.com/reviews/tech/native-instruments-battery-4-575148)

#### Long Boom Kit (drums, P1, XP badge)

- **Inspired by:** TR-808 kit
- **Character:** Long sine boom, snappy crumple, cowbell from the default bell.
- **DNA v2 (now):** `ringout@20[@40]@0CP<<<Ja0,100.100,60.900,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double slower x3 amp 0:100,100:60,900:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP<<<Ja0,100.100,60.900,0#3F/recycle>@30]+#4F/xprecycle>>>@40]#5F/default>@8]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `recycle`, `xprecycle`, `default`
- **Swap candidates:** Windows: balloon, menu, xpstart, start, infobar, critstop; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Punch Kick Kit (drums, P1, XP badge)

- **Inspired by:** TR-909 kit
- **Character:** Punchy clipped kick, echo clap, long crumple open hat.
- **DNA v2 (now):** `ringout@20[@40]@0CP<<<+Ja0,100.40,70.300,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double slower x3 louder amp 0:100,40:70,300:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP<<<+Ja0,100.40,70.300,0#3F/recycle>>@50]E#4F/xprecycle>>@60]#5F/xpstart>#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: balloon, menu, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Bright Digital Kit (drums, P1, XP badge)

- **Inspired by:** TR-707 kit
- **Character:** Brighter, shorter, cleaner.
- **DNA v2 (now):** `balloon<<@40]#16F;A0R150V90`
  - Recipe: `balloon slower x2 cut after 40% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<@40]#3F/recycle>>@30]#4F/xprecycle>>>@30]#5F/infobar#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `infobar`
- **Swap candidates:** Windows: menu, xpstart, start, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Pop Studio Kit (drums, P1, XP badge)

- **Inspired by:** LinnDrum kit
- **Character:** Fat snare with echo, mallet toms.
- **DNA v2 (now):** `balloon<<<@40]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 40% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@40]#3F/recycle>@40]+E#4F/xprecycle>>>@40]#5F/hwfail<@30]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `hwfail`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Twelve-Bit Crate Kit (drums, P1, W3.11 badge)

- **Inspired by:** SP-1200 kit
- **Character:** Only Windows 3.x sounds (ding kick, struck-chord snare, ringin hats), every one round-tripped through speed steps: aliasing as character.
- **DNA v2 (now):** `ding<<<@35]><#16F;A0R150V90`
  - Recipe: `ding slower x3 cut after 35% faster slower 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ding<<<@35]><#3F/chord>>@15]+E><#4F/ringin>>@12]><#5F/ding>>@4]><#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ding`, `chord`, `ringin`
- **Swap candidates:** Windows: balloon, recycle, xprecycle, menu, xpstart, start; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Swing Pad Kit (drums, P1, XP badge)

- **Inspired by:** MPC60 kit with swing
- **Character:** Soft kit with 60 % swing on the grid.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/recycle>@30]+E#4F/xprecycle>>>@40]#5F/xpstart>#4;R200V90xs60k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

## LABS (Spitfire Audio)

- **Kind:** free sample instruments, 2018-
- **Loved for:** Free, simple, beautiful: Soft Piano (called the world's most popular piano plug-in by Spitfire), Strings, Frozen Strings (dry, textured; the spark for a paid library), Glass Piano, Trumpet Fields, Electric Piano, Drums.
- **Iconic categories:** soft felt piano; frozen (airy, textured) strings; glass piano; trumpet fields
- **Sources:** [Rekkerd: Spitfire Audio launches LABS (Soft Piano, Strings)](https://rekkerd.org/spitfire-audio-launches-labs-with-soft-piano-strings-free-instruments/), [AudioTechnology: LABS Frozen Strings](https://audiotechnology.com/?p=78223)

#### Hush Felt Keys (keys, P1, XP badge)

- **Inspired by:** LABS Soft Piano (felt piano)
- **Character:** XP ding slowed and softened with a sine body.
- **DNA v2 (now):** `xpding@30]<#8/print@10[@50]<<#6L30T1;A15D3000S20R1200V60K47`
  - Recipe: `xpding cut after 30% slower 8rec / print cut before 10% cut after 50% slower x2 6rec level 30% transpose +1 | atk 15ms dec 3s sus 20% rel 1.2s vel 60% root B2`
- **Sounds used:** `xpding`, `print`
- **Swap candidates:** Windows: default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: instruments-archive. Notes before stealing: 6.

#### Frost Section (strings, P1, XP badge)

- **Inspired by:** LABS Frozen Strings
- **Character:** Violin section with paper-noise air, dry.
- **DNA v2 (now):** `violin_section_sus_c4#10/xprecycle<<#4FL20;A200S90R800K60`
  - Recipe: `violin_section_sus_c4 10rec / xprecycle slower x2 4rec fixed level 20% | atk 200ms sus 90% rel 800ms root C4`
- **Sounds used:** `xprecycle`; library: `violin_section_sus_c4`
- **Swap candidates:** Windows: startup, logon, logoff; library: cello_section_sus_c3, erhu_d3
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 4.

#### Field Trumpets (brass, P2, W3.11 badge)

- **Inspired by:** LABS Trumpet Fields
- **Character:** Trumpet slowed with echo, wide.
- **DNA v2 (now):** `trumpet_sus_c4<E#10U3~14;A500S90R2000K48`
  - Recipe: `trumpet_sus_c4 slower echo 10rec unison 3 +-14c | atk 500ms sus 90% rel 2s root C3`
- **Sounds used:** none; library: `trumpet_sus_c4`
- **Swap candidates:** Windows: tadaxp, tada, critstop; library: trombone_sus_c3, horn_sus_c3, tuba_sus_f1
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 3.

#### Glass Practice Piano (keys, P2, W3.11 badge)

- **Inspired by:** LABS Glass Piano
- **Character:** Wine glass ping with a ding body.
- **DNA v2 (now):** `wine_glass_small_ping#8/ding@20]#6L40;A0D2500S0R1200K79`
  - Recipe: `wine_glass_small_ping 8rec / ding cut after 20% 6rec level 40% | atk 0ms dec 2.5s sus 0% rel 1.2s root G5`
- **Sounds used:** `ding`; library: `wine_glass_small_ping`
- **Swap candidates:** Windows: xpding, print, default, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 6.

## Ableton Live factory instruments

- **Kind:** Operator, Wavetable, Drift, Simpler/Sampler, Collision, Tension, Electric, Drum Rack
- **Loved for:** Operator FM (bells, basses; 20 years of presets curated by its designer), Wavetable, Drift (in every edition), Simpler slicing, physical models of mallets (Collision), strings (Tension) and e-piano (Electric); drum-machine core kits in Drum Racks.
- **Iconic categories:** Operator FM bells and basses; Simpler-sliced loops; Collision mallets; Drift analog basses and pads
- **Sources:** [Ableton blog: 20 years of Operator](https://www.ableton.com/en/blog/20-years-of-operator/), [Sound on Sound: Ableton Live Drift synthesizer](https://www.soundonsound.com/techniques/ableton-live-drift-synthesizer), [MusicRadar: Ableton Drift guide](https://www.musicradar.com/news/ableton-drift-guide)

#### Four Operator Bell (bell, P1, XP badge)

- **Inspired by:** Operator FM bell
- **Character:** Print bell with a slowed chimes partial.
- **DNA v2 (now):** `print#8/chimes<#6L30T3;A0D3000S0R1500K82`
  - Recipe: `print 8rec / chimes slower 6rec level 30% transpose +3 | atk 0ms dec 3s sus 0% rel 1.5s root A#5`
- **Sounds used:** `print`, `chimes`
- **Swap candidates:** Windows: ding, default, error, exclaim, xpnotify; library: wine_glass_medium_ping, crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6, music_box_note; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: instruments-archive. Notes before stealing: 6.

#### Struck Bar Mallet (mallet, P2, XP badge)

- **Inspired by:** Collision modelled mallet
- **Character:** Relay marimba with a click.
- **DNA v2 (now):** `ems_relay_marimba_c4#12/menu#4FL30;A0R700K60`
  - Recipe: `ems_relay_marimba_c4 12rec / menu 4rec fixed level 30% | atk 0ms rel 700ms root C4`
- **Sounds used:** `menu`; library: `ems_relay_marimba_c4`
- **Swap candidates:** Windows: xpding, hwfail, default; library: marimba_c4, xylophone_c5, vibraphone_c_low
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 4.

#### Drift Bass (bass, P2, W3.11 badge)

- **Inspired by:** Drift analog bass
- **Character:** Short buzz with sine sub, mono.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<#8/ringout@20[@40]@0CP@0CP@0CP<<<#6L60T2;A0D400S50R80K35`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 slower x2 8rec / ringout cut before 20% cut after 40% double x3 slower x3 6rec level 60% transpose +2 | atk 0ms dec 400ms sus 50% rel 80ms root B1`
- **DNA v3 (later):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<#8Nm/ringout@20[@40]@0CP@0CP@0CP<<<#6L60T2Nm;A0D400S50R80K35`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** 
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: instruments-archive. Notes before stealing: 6.

#### Key Slice Loop (perc, P1, W3.11 badge)

- **Inspired by:** Simpler slicing
- **Character:** Hold-music loop sliced by key (v3 window).
- **DNA v2 (now):** `holdmusic_fs_hold_music#12;A0R100`
  - Recipe: `holdmusic_fs_hold_music 12rec | atk 0ms rel 100ms`
- **DNA v3 (later):** `holdmusic_fs_hold_music#12Ws0~.95l.02Yk;A0R100`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `holdmusic_fs_hold_music`
- **Swap candidates:** Windows: menu, xpstart, infobar, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** 
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: instruments-archive. Notes before stealing: 12.


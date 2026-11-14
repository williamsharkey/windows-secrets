# Pack plan: 1,200 presets in 15 packs (plus the 351 already researched)

A plan for BASILISK SYNTH (XP) and BASILISK 16 (3.11): pack names in the alternate-1999 corporate style, categories, counts per pack and category, and which edition ships what. The seeds are the 215 targets in `genres.md` / `genres.json` and `modern-favorites.md` / `.json`; each pack grows from its seeds by the rules in section 3.

- **Status:** plan only. Not committed. No code or format change is proposed here except the three v3 proposals in genres.md 1.2 and the library renames in section 5.
- **Total new presets:** 1204, of which 308 need v3 (kits, sequencer, windows, glide, wow, grains) and 896 play on v2 today.
- **With the research already done:** preset-targets.md (198), the aesthetic presets (101) and the electromech instruments and kits (52) are scheduled as three more packs (section 2.2), for about 1555 in all.

## 1. Principles

1. **One pack, one disc.** A pack is a library disc (PRESET-ENGINE-2.md section 16): `\PRESETS.TSV` plus any new sounds. XP shows it in Explorer, 3.11 in File Manager. Program names stay "Category: Name".
2. **Both editions by default.** Since 1.2.1 every built-in name plays on both machines, so a preset ships to both unless it needs the library disc (XP until the 3.11 library drive lands) or a v3 feature that one edition gets first (glide, wow and grains are smooth on 3.11 first; kits are exact on 3.11 first).
3. **The badge is derived, never chosen.** [W3.11] = only `chimes chord ding tada ringin ringout` (library sounds do not count); everything else is [XP]. Caveat: a preset made only of library sounds also gets [W3.11] (genres.md 1.1); until the 3.11 library drive ships, the 3.11 browser should hide those. Target: at least 30 % W3.11 per genre pack, so the BASILISK 16 browser with its own filter on still has a full genre pack.
4. **Standard categories** (the program-list prefix): Bass, Sub, Lead, Pad, Keys, Organ, Stab, Chord, Pluck, Bell, Mallet, Strings, Brass, Vocal, Arp, FX, Texture, Drone, Perc, Kit. Pack tables below use finer working groups (Wobble, Growl, Reese) that map to these.
5. **Macros mean the same everywhere:** M1 brightness (mod wheel), M2 motion, M3 space, M4 character.

## 2. The packs

| # | Pack | Box blurb | Genres / sources | Presets | of them v3 | Seeds researched (pure 3.x, with v3) | Ships |
|---:|---|---|---|---:|---:|---|---|
| 1 | **Workgroup House Edition** | "Four-on-the-floor productivity for the whole department." | deep, classic and French house | 100 | 17 | 20 (3, 7) | both; about 25 W3.11 (chord, tada, ding, ringout house) |
| 2 | **Techno Server 4.0** | "Mission-critical repetition, now with dub delay." | Detroit, minimal and dub techno | 80 | 10 | 16 (4, 3) | both; about 15 W3.11 |
| 3 | **Trance Connectivity Kit 2000** | "Connects your hands to the ceiling." | trance (uplifting, progressive, hard) | 70 | 16 | 7 (0, 3) | both; about 10 W3.11 (tada saws) |
| 4 | **Breakbeat Resource Kit** | "Every break your network will ever need." | drum and bass, jungle, breakbeat, big beat, electro, footwork | 110 | 33 | 23 (5, 12) | both; strips and chops v3 |
| 5 | **Bass Enterprise Edition** | "Low-end infrastructure for medium and large businesses." | dubstep, UK garage and 2-step, speed garage, reese and sub for every genre | 80 | 22 | 10 (1, 6) | both; glide presets on 3.11 first (smooth card rate), XP after phase 0 |
| 6 | **Beat Management Console** | "Centralised administration of the boom and the bap." | boom bap, lo-fi hip-hop, trap, downtempo and trip-hop | 120 | 34 | 20 (1, 12) | both; tape-wow keys on 3.11 first; rain/room beds need the library disc |
| 7 | **Retro Display Properties** | "Adjust your colour depth to 1985." | synthwave and outrun, chillwave, city pop | 90 | 22 | 16 (1, 7) | both; arps (sequencer) v3 |
| 8 | **Ambient Screen Saver Collection** | "Protects your monitor and your nervous system." | ambient, drone, new age and Fourth World | 100 | 18 | 18 (2, 2) | XP first for the nature/water beds (library); grains v3 (3.11 first) |
| 9 | **Experimental Diagnostics Suite** | "Finds errors. Plays them back in time." | IDM and glitch, hyperpop | 70 | 18 | 12 (0, 3) | both |
| 10 | **Leisure Accessories Pack** | "For the executive lounge." | exotica (and lounge) | 40 | 0 | 7 (0, 0) | XP first (library) |
| 11 | **Game Port Sound Set** | "Joystick not included." | video-game chiptune | 50 | 14 | 4 (4, 2) | BASILISK 16 first: about 40 of 50 are W3.11 (ding, chimes, ringin buzzes) |
| 12 | **Kit Manager 98** | "Map any drum to any key. Restart not required." | one kit per genre (27), the classic machines (6), velocity and round-robin variants, W3.11 twins | 64 | 64 | 27 (2, 27) | v3 only (kit mode, section 15); exact on 3.11 now-ish, XP after phase-0 streamed gain |
| 13 | **Professional Workstation Classics** | "The sounds of the leading software, re-engineered for your desktop." | favorites: wavetable and VA synths (Serum, Vital, Pigments, Diva, Massive, Sylenth1, Spire, Nexus) | 90 | 28 | 16 (2, 7) | both; mono/glide basses 3.11 first |
| 14 | **Studio Instruments Archive** | "Every keyboard in the building, catalogued." | favorites: Keyscape, Kontakt libraries, LABS, Arturia V Collection, Omnisphere, Ableton instruments | 80 | 8 | 19 (2, 5) | XP first (most use the library disc); piano presets wait for the # rename |
| 15 | **Windows 3.x Heritage Edition** | "Sixteen bits of history. Eight of them audible." | every genre, using only chimes, chord, ding, tada, ringin and ringout | 60 | 4 | 27 pure 3.x seeds across all packs | BASILISK 16 flagship; plays on both |
| | **Total** | | | **1204** | **308** | 215 | |

### 2.1 Categories and counts per pack

- **Workgroup House Edition** (100): Bass 14 (3 v3), Keys 10, Organ 6, Stab 18 (4 v3), Pad 8, Strings 4, Lead 6 (2 v3), Vocal 12 (8 v3), Pluck 6, FX 10, Perc 6.
- **Techno Server 4.0** (80): Bass 12 (4 v3), Stab 16 (6 v3), Pad 10, Lead 6, Perc 16, FX 10, Texture 10.
- **Trance Connectivity Kit 2000** (70): Lead 16, Pad 14 (6 v3), Pluck 12, Bass 8 (4 v3), Chord 8 (4 v3), FX 8 (2 v3), Keys 4.
- **Breakbeat Resource Kit** (110): Bass 24 (8 v3), Drums 10 (10 v3), Vocal 14 (10 v3), Pad 12, Keys 8, Stab 12, Lead 8 (3 v3), FX 12, Perc 10 (2 v3).
- **Bass Enterprise Edition** (80): Wobble 16, Growl 14 (6 v3), Sub 12 (4 v3), Organ bass 12 (4 v3), Reese 10 (4 v3), Stab 6, Vocal 6 (4 v3), FX 4.
- **Beat Management Console** (120): Keys 22 (12 v3), Bass 808 18 (10 v3), Bell 10 (2 v3), Pluck 4, Lead 10 (4 v3), Pad 12, Vocal 10 (6 v3), Texture 14, Strings brass 10, FX 10.
- **Retro Display Properties** (90): Pad 16 (4 v3), Keys 16, Lead 14 (4 v3), Bass 14 (6 v3), Brass strings 10, Arp 8 (8 v3), Snare tom 6, FX 6.
- **Ambient Screen Saver Collection** (100): Pad 26 (4 v3), Drone 18, Bell mallet 16, Texture 20, Lead 10 (4 v3), Grain cloud 10 (10 v3).
- **Experimental Diagnostics Suite** (70): Glitch FX 16 (4 v3), Perc 14, Bell 10 (4 v3), Lead 10, Pad grain 10 (6 v3), Vocal 10 (4 v3).
- **Leisure Accessories Pack** (40): Mallet 10, Texture 8, Keys 6, Strings 6, Perc 6, Lead 4.
- **Game Port Sound Set** (50): Lead 14, Bass 8 (4 v3), Arp 10 (10 v3), Drums 8, FX 10.
- **Kit Manager 98** (64): Genre kits 27 (27 v3), Machine kits 6 (6 v3), Variants 19 (19 v3), W311 kits 12 (12 v3).
- **Professional Workstation Classics** (90): Lead 18 (4 v3), Bass 22 (10 v3), Pad 14 (2 v3), Pluck 12, Chord 10 (4 v3), FX 6, Arp 8 (8 v3).
- **Studio Instruments Archive** (80): Keys 24, Strings 12 (2 v3), Brass 10, Pad 12 (2 v3), Bell mallet 10, Perc impact 6 (2 v3), Bass 6 (2 v3).
- **Windows 3.x Heritage Edition** (60): Bell 10, Keys 8, Pad 10, Bass 8 (2 v3), Lead 8 (2 v3), Stab hit 8, Perc 8.

### 2.2 Packs from earlier research (already designed)

| Pack | Source | Presets | Ships |
|---|---|---:|---|
| **ROM Reference Library** ("The great workstations, archived.") | preset-targets.md: E-mu, Roland, Korg, Yamaha, Kurzweil/Ensoniq, soft synths, and the category benchmarks | 198 | both; 14 cross-listed |
| **Lifestyle Aesthetics Pack** ("Mall. Lobby. Aquarium. Startup.") | AESTHETIC-PRESETS.md: vaporwave, Frutiger Aero and neighbours | 101 | both; XP identity |
| **Electromechanical Heritage** ("Relays, typewriters, telephones.") | electromech-presets.json: 40 instruments, 12 kits | 52 | instruments both; kits v3 |
| Factory programs (shipping) | factory.tsv (XP) and b16.tsv (3.11) | 39 + 76 | as now |

## 3. From 215 seeds to 1204 presets: how a pack grows

Every seed ships as the hero preset. Variants are made only by these rules; a variant ships only if an A/B in reference mode shows it is clearly different (a new source, a new envelope class or a new tempo). A macro position alone is never a new preset.

| Rule | What changes | Applies to | Yield per seed |
|---|---|---|---:|
| **Source swap** | the main layer's source, from the target's `alternates` (same role, same trim idea) | every role | 1-2 |
| **Edition twin** | a W3.11 version from the six 3.x sounds (for example a deep-house stab from `chord` instead of `xpding`) | bass, keys, pad, stab, bell, lead, perc | 0-1 |
| **Tempo twin** | offsets, drawn gates, pumps and wobbles recomputed for the genre's standard tempi (house 120/124, techno 128/132, trance 138, dubstep 140, DnB 174, hip-hop 90) | presets with DUB-TAPS, DRAWN-GATE, PUMP, DRAWN-WOBBLE | 1-2 |
| **Register / character twin** | a speed step (octave) plus a different envelope class (pluck, sustain, swell) | pads, keys, leads, bass | 0-1 |
| **v3 upgrade** | the same preset with its v3 genes (glide, window chop, grains, sequencer) as its own program in the v3 category | presets with a v3_dna | 0-1 |

Expected: about 4.5 presets per seed (215 x 4.5 = about 967), plus hand-designed fills where a category in 2.1 has fewer seeds than its count (most needed: Perc, FX, Texture, Pluck and Arp, which have few seeds now).

**Tempo twins will disappear** if the v3 beat-relative time proposal (genres.md 1.2) lands: then one preset serves every tempo and those slots go to new sounds.

## 4. Which edition gets what

| | BASILISK SYNTH (XP) | BASILISK 16 (3.11) |
|---|---|---|
| v2 presets with only built-in names | all | all (XP files are in C:\XPSOUNDS) |
| W3.11-badge presets | all | all; shown first; the Heritage Edition is the flagship pack |
| Library-disc presets | all | when the 3.11 library drive lands (PRESET-ENGINE-2.md 6.2, 16) |
| Kits (Kit Manager 98, break strips) | after phase-0 streamed gain (choke fades) | first: card windows and per-voice fades are exact |
| Mono/glide, tape wow | after phase 0 (planned staircase handovers, 40 ms steps) | first: smooth card rate |
| Grains | after phase 6 | first: about 100 grains/s sample-exact |
| Sequencer / arp presets (mine grid) | phase with section 9 | same phase (WINMINE.EXE is on the 3.11 image) |

## 5. Library-disc work the packs need

1. **Rename the `#` sounds:** `piano_upright_c#2..6` -> `piano_upright_cs2..6`, `bass_guitar_g#` -> `bass_guitar_gs`. A DNA cannot name them today (`#` starts a pool gene). Every piano preset waits for this.
2. **Add sounds that are already in our XP image** (windows-sounds.json top 50): Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (tight thump) and bumper (metallic hit), NetMeeting Blip and TestSnd, Messenger online and newemail (convert MS-ADPCM to PCM), Agent merlin #22 and qmark #06 (clean tones and swells), and the 130 Microsoft Sam phrases of `sam_phrases.txt` (vocal chops and robot voices for house, electro, footwork, hyperpop). They are Windows sounds, so they keep the identity better than any new sample.
3. **Measure roots** of the library tonal sounds that have no note in their name (`epiano_yamaha_vibe`, `vibraphone_c_low`, `music_box_note`, `choir_aah`, `crowd_sing_aah_f`): K in the targets uses estimates.

## 6. Quality bar before a preset ships

1. Parses to its canonical form with no unknown name, at most 1024 bytes; its recipe round-trips (as checked for every seed here).
2. K (or T) set from the measured root on the real machine, in both editions.
3. Listened to in reference mode, then on the real machine; compared by ear with the genre role it claims.
4. Polyphony: pads, keys and stabs hold at least 2 notes before stealing (field `notes_before_stealing`); bass and leads may be mono, and say so.
5. Level: batch-render peak between -6 and -1 dBFS (tools/batch_render.py).
6. The Windows source is audible somewhere (genres.md section 2), and the strips show at least one visible edit.
7. Macros follow M1-M4; the mod wheel does something.
8. Name: original, at most three words, no brand, trademark, artist, label or song name.

## 7. The top 40 to build first

Ranked by how central the role is to its genre, weighted by how well Sound Recorder can give what producers look for, and spread over genres and both editions.

| # | Name | Genre / favorite | Role | Badge | Needs | DNA (v2, canonical) |
|---:|---|---|---|---|---|---|
| 1 | Warehouse Piano Stack | classic-house | keys | W3.11 | v2 | `chord@5[@40]#10H0,12/ding@15]#6L35;A0D1100S20R250V70K55` |
| 2 | Sevenfold Anthem Lead | trance | lead | XP | v2 | `tadaxp@40[@20]@0CP@0CP@0CP@0CP+#10U5~25/tadaxp@40[@20]@0CP@0CP@0CP@0CP>#6U1~0L40;A5R400V60K60` |
| 3 | Ringback Twin Saw | dnb-jungle | bass | XP | v2 (+v3: voice mode) | `xpringout@20[@40]@0CP@0CP@0CP+++<<<#16U2~18;A5S100R150K33` |
| 4 | Long Boom Glide | trap | bass | XP | v2 (+v3: voice mode) | `balloon<<<+#8/ringout@20[@40]@0CP@0CP@0CP<<<#6L60;A0D3000S40R300K45` |
| 5 | Feedback Chain Stab | dub-techno | stab | XP | v2 (+v3: scale, stack) | `xpding@20]E#4H0,3,7,10/xpding@20]EE#4H0,3,7,10L45O375Q-50/xpding@20]EE<>#4H0,3,7,10L28O750Q50/xpding@20]EEE<>#4H0,3,7,10L16O1125Q-30;A0D400S10R1200V70m32L0,90m33L0,56m34L0,32m3=50K59` |
| 6 | Velvet Minor Nine | deep-house | stab | XP | v2 (+v3: scale, stack) | `xpding@25]<#6H0,3,7,10,14/xpding@25]<E#5H0,3,7,10L30O375Q-45/xpding@25]<#5H0,3,7L18O750Q45;A0D700S20R450V80K47` |
| 7 | Organ Bass 2-Step | ukg-2step | bass | XP | v2 (+v3: voice mode) | `ringout@20[@40]@0CP@0CP@0CP+<<#10H0,12/xpstart#2FL45;A0D300S60R70V90K45` |
| 8 | Quarter Wobble | dubstep | bass | XP | v2 | `xpringout@20[@40]@0CP@0CP@0CP+++<<<#16U2~10Ja0,100.107,15.214,100.321,15.428,100.535,15.642,100;A0R120m21Z100,50m2=0K33` |
| 9 | Acid Accent Line | classic-house | bass | XP | v2 (+v3: voice mode) | `default@3]<<+++#8Ja0,100.40,60.220,25/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#8L50T4;A0R60V100K51` |
| 10 | Rainy Study Keys | lofi-hiphop | keys | W3.11 | library (+v3: per-voice randomness, tape wow/flutter/scoop) | `epiano_yamaha_vibe#12U2~8/rain_on_window#4FL15;A10D2500S40R700V70K60` |
| 11 | Night Drive Chorus Pad | synthwave | pad | XP | v2 (+v3: stack) | `logon<@15[#10U3~16/logon<@15[#6U2~10Q60L50;A700S90R1500K44` |
| 12 | Gated Neon Snare | synthwave | snare | XP | v2 | `recycle>@40]+EEE#12FJa0,100.200,90.220,0;A0R10V90` |
| 13 | Pulse Twelve Lead | chiptune | lead | W3.11 | v2 | `ding@t60[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#12;A0R60K59` |
| 14 | Shiny Tine Plaza | city-pop | keys | XP | v2 | `default@10]#6U2~6Q-20/print@5[@60]#6U2~6Q20L60T5;A0D2500S25R600V85K75` |
| 15 | Startup Cloud | ambient | pad | XP | v2 (+v3: grains) | `startup<<#12U2~8;A1500S90R4000K44` |
| 16 | Motor City Strings | detroit-techno | pad | XP | v2 | `startup@20[@50]<#10U3~14/logon<@20[#6U2~8L35;A600S90R1500K56` |
| 17 | Menu Click Perc | minimal-techno | perc | XP | v2 | `menu#16;A0R40V100K60` |
| 18 | Chromatic Kick Bass | footwork | bass | XP | v2 | `balloon<<<@60]#16;A0R100V100K45` |
| 19 | Sixteenth Gate Pad | trance | pad | XP | v2 (+v3: mine-grid sequencer/arp, window) | `startup@25[@50]<#12U2~10Ja0,100.54,100.55,0.108,0.109,100.162,100.163,0.216,0;A0S100R200K56` |
| 20 | Stutter Copy Paste | idm-glitch | fx | XP | v2 | `tadaxp@30[@4]@0CP@0CP@0CP@0CP@0CP#10;A0R60K60` |
| 21 | Error Growl | dubstep | bass | XP | v2 (+v3: voice mode) | `error@5]+++C@2XC@4X<<<@0CP@0CP#16U2~20;A0R100K51` |
| 22 | Sped-Up R&B Chop | ukg-2step | vocal | W3.11 | library (+v3: per-voice randomness, window) | `crowd_sing_aah_f>@10[@12]#10;A2D250S50R150K65` |
| 23 | Dusty Crate Kit | boom-bap | drums | XP | v3 kit | `ding<<<@35]><#3F/recycle>@30]+><E#4F/ringin>>@12]><#5F/xpstart><#4;R200V90xs60k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7` |
| 24 | Airport Loop Phasing | ambient | pad | XP | v2 | `logon<@10[@60]E#5/logon<@30[@40]E#5O700Q-40/logon<@50[@50]E#5O1300Q40;A900S90R3000K44` |
| 25 | Thirty Second Ring | drone | drone | W3.11 | v2 | `ringout@20[@40]@0CP@0CP@0CP@0CP@0CP@0CP@0CP#12H0,12,-12U2~3;A4000S100R6000K69` |
| 26 | Robot Workgroup Voice | electro | vocal | W3.11 | library | `ems_704_vowel_a3@0CP#8/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#6L35T-2;A10R200K57` |
| 27 | Lagoon Vibes | exotica | bell | W3.11 | library | `vibraphone_c_low#10Ja0,100.120,60.240,100.360,60.480,100;A0R1200K48` |
| 28 | Half-Speed Mockingbird | exotica | texture | W3.11 | library | `bird_american_robin<E#6F;A0R1500` |
| 29 | Plastic Sevenfold | hyperpop | lead | XP | v2 | `tadaxp@40[@20]@0CP@0CP@0CP@0CP>+++#12U4~30;A0R200K72` |
| 30 | Tokyo Slap | city-pop | bass | XP | v2 (+v3: voice mode) | `xpding@20]<<+++#8/balloon<#4FL50;A0D350S40R80V95K35` |
| 31 | Ether Wire Lead | downtempo-triphop | lead | XP | v2 (+v3: tape wow/flutter/scoop, voice mode) | `print@15[@50]@0CP@0CP@0CP#8;A80R400B12K82` |
| 32 | Filtered Disco Loop Chord | french-house | stab | XP | v2 (+v3: stack) | `chordxp@5[@60]C@3X<#10H0,5Ja0,10.40,100.240,60.484,10.524,100.724,60/xprecycle>>>@30]#2FL15;A0R300V60K43` |
| 33 | Bent Future Chord | serum | chord | XP | v2 (+v3: scale, stack, tape wow/flutter/scoop) | `tadaxp@40[@20]@0CP@0CP@0CP@0CP#12H0,4,7,11U2~25Ja0,10.60,100.214,70.428,10.440,100;A0R300B2K60` |
| 34 | Spoken Wavetable | vital | lead | W3.11 | library | `prelinger_information_machine_a@40[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#10;A5R200K59` |
| 35 | Hush Felt Keys | labs | keys | XP | v2 | `xpding@30]<#8/print@10[@50]<<#6L30T1;A15D3000S20R1200V60K47` |
| 36 | Long Boom Kit | drum-machines | drums | XP | v3 kit | `ringout@20[@40]@0CP<<<Ja0,100.100,60.900,0#3F/recycle>@30]+#4F/xprecycle>>>@40]#5F/default>@8]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7` |
| 37 | Punch Kick Kit | drum-machines | drums | XP | v3 kit | `ringout@20[@40]@0CP<<<+Ja0,100.40,70.300,0#3F/recycle>>@50]E#4F/xprecycle>>@60]#5F/xpstart>#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7` |
| 38 | Twelve-Bit Crate Kit | drum-machines | drums | W3.11 | v3 kit | `ding<<<@35]><#3F/chord>>@15]+E><#4F/ringin>>@12]><#5F/ding>>@4]><#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7` |
| 39 | Mono Glide Lead | arturia-v | lead | W3.11 | v2 (+v3: voice mode) | `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP+#6/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#5T12L50/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#5T7L30;A5R150K59` |
| 40 | Burnt Chord Texture | omnisphere | pad | XP | v2 | `chord<RE<E#10U2~10/recycle<<E#4FL30;A1200S90R3000K31` |

11 of the 40 carry the W3.11 badge (6 of those also use library sounds, so they reach 3.11 with its library drive); 6 need the library disc; 4 are v3 kits.

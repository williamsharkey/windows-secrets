# Genres: what matters in each, and recipes for BASILISK SYNTH and BASILISK 16

Research for the 1000-preset plan (`pack-plan.md`). It covers 27 genre entries and 174 targets. Machine-readable copy: `genres.json`; the classic synths and libraries are in `modern-favorites.md`.

- **Status:** research only. Nothing here is committed, and no core, DNA.md or plugin file was changed.
- **Checks:** Every dna and v3_dna was parsed by core/dna.cpp parse() on main (library catalogue loaded) and by design/v3 canonical3() on preset-engine-2: no unknown NAME, no empty layer, at most 1024 bytes; stored in canonical form. Every recipe is design/v3 toRecipe(OneLine) and parses back (fromRecipe) to the same canonical DNA. K is computed from the measured root of the first key-tracked layer (windows-sounds.json, library note names), other tonal layers get T to the nearest octave. Nobody has listened to them yet.
- **Inputs:** `../../DNA.md` (DNA v2), `preset-targets.md` (198 classic targets; this file does not repeat them),
  `~/ws-aes/.../AESTHETIC-PRESETS.md` (vaporwave and Frutiger Aero, 101 presets; not repeated),
  `~/ws-pe2/.../PRESET-ENGINE-2.md` (v3: windows `W`, voice modes `N`, stacks `S`, random `Y`, tape `V`/`Z`,
  grains `G`, kits `k` (section 15), the mine-grid sequencer `x`/`q` (section 9), recipes (section 17)),
  `windows-sounds.json` (measured roots), `../catalog/*.json` (library disc).
- **Names:** every preset name is original. No brand, trademark, artist, label or song name is used in a name.
  `inspired_by` names the source for research only.

Contents: 1 Idioms and limits; 2 Sound Recorder feel; 3 Counts; 4 Genres (each: what matters, then its targets); 5 Sources.

## 1. New toolbox idioms (added to preset-targets.md section 1)

The idioms of `preset-targets.md` (TRIM-ATTACK, GRAIN, LOOP-OSC, CLIP, DECIMATE, COMB, LONG-ECHO, BLUR-DOWN,
SWELL, PRE-VERB, SELF-FLANGE, OCT-BAKE, SPLICE-SEQ, MIX-TRANSIENT) are used as they are. Genre work needed these
too:

| Idiom | DNA | What it does | Used for |
|---|---|---|---|
| **TUNED-BUZZ** | `src@tA[@t20]@P]` then `@0CP` x9 | Two-stage trim: first cut a 20 ms piece, then keep P % of it, so the slice is P x 0.2 ms long, exact to 0.02 ms (a one-stage `@t4]` on a 300 ms buffer is only exact to 0.3 ms, a 7 % pitch error). Nine doublings give a 2 s buzz at 1000 / slice-ms Hz: `@20]` = 4 ms = 250 Hz (K59), `@25]` = 5 ms = 200 Hz (K55). The source decides the wave shape: `ringout` round, `ding` (3.11) bright and gritty, `default` glassy, speech vowels vocal. | Pulse/chip leads, acid, saws for mono basses, "text-to-wavetable" |
| **DUB-TAPS** | the same layer two to four times, `O375`, `O750`... with falling `L`, alternating `Q`, and an extra `E` or a speed round trip `<>` on each later tap | A tempo delay with feedback made of real recorders: each tap starts later, is quieter, darker and on the other side. Offsets are milliseconds, so a preset is tied to a tempo (dotted 8th: 375 ms at 120, 326 at 138). | Dub techno, deep house stabs, trance plucks |
| **DRAWN-GATE** | `Ja0,100.54,100.55,0.108,0...` | A 1/16 trancegate drawn as breakpoints (54 ms at 138 BPM). Only 8 points, so it draws two on/off pairs and then holds; the v3 sequencer retriggers it on the grid. | Trancegate pads, sidechain pump |
| **DRAWN-WOBBLE** | `Ja0,100.107,15.214,100...` plus `m2..Z100,50` | An LFO wobble drawn as a level envelope. Macro 2 scales the envelope time (`Z`), so 100 % = 1/8 and 50 % = 1/16. | Dubstep, speed garage, neuro |
| **PUMP** | `Ja0,10.40,100.240,60.484,10...` | Sidechain ducking drawn on the beat (484 ms = one beat at 124 BPM). | French house, future bass |
| **SPEED-FILTER** | `<>` / `><` | A speed round trip: the DECIMATE hypothesis of preset-targets.md. Used as a low-pass on later delay taps and as SP-1200-like grit on hip-hop sounds. Still to be verified by ear on both editions. | Dub taps, boom-bap, lo-fi |
| **BOOM** | `balloon<<<` (A5 pop to A2) or a sine loop `<<<` with `Ja` decay | A long kick-bass from a tiny pop. Key-tracked, it is a chromatic 808. | Trap, footwork, electro |
| **CRUMPLE KIT** | `recycle>@30]+` (snare), `recycle>>@50]E` (clap: the echo is the flam), `xprecycle>>>@40]` (hat) | Paper crumple as the noise source of a drum machine. | Every kit |
| **SPEECH-CHOP** | `speech@NN[@2]` (v2), `Ws.1~.9l.01~.02Yk` (v3) | v2: one syllable of a narration. v3: every key gets its own random syllable, the same each time (seed per key). | Vocal chops (house, UKG, jungle, footwork) |
| **GATED-ECHO** | `EEE` then `Ja0,100.200,90.220,0` | Echo for the room, a drawn envelope that slams shut: the 80s gated-reverb snare. | Synthwave, city pop |
| **STRIP** | `a@t30000Ib@t30000Ic...` plus `k` pads with `j` | A break or a kit in one buffer (Insert File at the end each time). v3 pads play its segments: a chopped break. | Jungle, glitch, kits |

### 1.1 Limits found while writing the recipes

- **Library names with `#` cannot be used in a DNA.** `piano_upright_c#2..6` and `bass_guitar_g#` parse as
  `piano_upright_c` plus a pool gene `#4` (checked with `parse()`: the layer is empty). The disc's only piano and
  bass guitar are unusable. Rename them (`piano_upright_cs4`, `bass_guitar_gs`) before any piano preset ships. Until
  then the piano targets here use `harp_c5` or Windows bells.
- **v2 offsets stop at 4000 ms.** A staged riser can last about two bars (3.48 s at 138, 3.87 s at 124). Longer
  builds (8 to 16 bars) need v3 (tape length `Wm`, or a tempo-relative offset; see 1.2).
- **Envelopes have 8 breakpoints.** A drawn gate or wobble shows two or three cycles and then holds. Proposal 1.2.
- **Everything timed is in milliseconds.** Delays, gates, pumps and wobbles are tied to one tempo. Packs ship tempo
  twins (pack-plan.md) until a beat unit exists.
- **Kit presets need v3.** On v2 a kit's layers all sound together, so the v2 DNA of a kit target here is its kick
  alone.
- **The derived badge counts a library-only preset as W3.11.** `core::dnaEdition` ignores library sounds, so a
  preset made only of disc sounds (a flute, a vibraphone, rain) shows under [W3.11] although BASILISK 16 cannot
  load the disc yet. Either the 3.11 library drive ships first, or the 3.11 browser hides presets whose origins
  include *library* until it does. In this file such presets say "library disc" under Ships.
- **3.11 sources are few.** Only `chimes chord ding tada ringin ringout` give the W3.11 badge. Bass, kick and pad
  roles are still possible with them (the ringout sine, `ding<<<` as a kick, `chord`/`tada` slowed), and they are
  the identity of BASILISK 16.

### 1.2 Proposals for v3 (from this research; not designed here)

- **Beat-relative time:** let `O`, `Ja`/`Jp` times and `Wm` be written in beats (for example `O.75b`) and follow the
  host tempo. This removes the tempo twins and makes every delay, gate and wobble preset tempo-proof.
- **Looping envelopes:** a `Ja` flag that repeats the drawn points while the key is held (an LFO made of
  breakpoints). Gates and wobbles would then run for the whole note.
- **Riser length:** allow offsets up to 30000 ms (the buffer cap) so a 16-bar riser can be staged.

## 2. Keeping the Sound Recorder feel while serving the genre

1. **The source stays audible.** A listener who knows Windows should be able to name the sound in at least one
   register or at one macro position. Ding, tada, chord, startup and the crumple are features, not raw material to
   hide.
2. **The effect is a menu command.** Delay is `E` or a later recorder, filter is a speed step or a duller source,
   distortion is `+`, chorus is `U` and `Q`. Never fake a plugin effect the program does not have.
3. **Edits are visible.** Prefer recipes whose strips show something: a cut edge, a doubled loop, a stutter, a
   strip of inserted files. The recipe (one line, ASCII) should read like a Sound Recorder session.
4. **8-bit and 22 kHz grit is the period colour.** Hip-hop, chip and lo-fi lean into it; trance and city pop use
   the cleanest sources (`print`, `default`, XP `ding`) instead of hiding the grit.
5. **Macros mean the same in every preset:** M1 brightness, M2 motion, M3 space, M4 character (the
   preset-targets.md convention). The mod wheel drives M1.
6. **Names sound like 1999 software, not like the genre's marketing.** A deep house stab is "Velvet Minor Nine",
   not a producer's name.

## 3. Counts per genre and role

| Genre | bass | sub | lead | pad | stab | chord | pluck | keys | organ | strings | brass | bell | mallet | arp | vocal | fx | texture | drone | perc | snare | drums | Total | P1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Deep house | 1 |  |  | 1 | 1 |  |  | 1 | 1 |  |  |  |  |  | 1 | 1 |  |  |  |  | 1 | 8 | 2 |
| Classic (Chicago) house | 1 |  |  |  | 1 |  |  | 1 | 1 | 1 |  |  |  |  | 1 | 1 |  |  |  |  | 1 | 8 | 3 |
| French house (filter house) | 1 |  | 1 |  | 1 |  |  | 1 |  | 1 |  |  |  |  |  | 1 |  |  |  |  | 1 | 7 | 1 |
| Detroit techno | 1 |  | 1 | 1 | 1 |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  | 1 | 6 | 2 |
| Minimal techno and microhouse | 1 |  |  |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 1 |  | 3 |  | 1 | 7 | 1 |
| Dub techno | 1 |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  | 1 | 6 | 1 |
| Trance | 1 |  | 1 | 1 |  | 1 | 1 | 1 |  |  |  |  |  |  |  | 1 |  |  |  |  |  | 7 | 2 |
| Drum and bass and jungle | 3 |  |  | 1 |  |  |  | 1 |  |  |  |  |  |  | 1 | 1 |  |  |  |  | 1 | 8 | 3 |
| UK garage and 2-step | 2 |  |  |  | 1 |  |  | 1 |  |  |  |  |  |  | 1 |  |  |  |  |  | 1 | 6 | 3 |
| Dubstep (UK and brostep) | 2 | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  | 1 | 6 | 2 |
| Hip-hop (boom bap) | 1 |  |  |  | 1 |  |  | 1 |  |  |  |  |  |  | 1 | 1 |  |  |  |  | 1 | 6 | 2 |
| Lo-fi hip-hop |  |  |  |  |  |  |  | 2 |  |  |  | 1 |  |  |  |  | 2 |  |  |  | 1 | 6 | 2 |
| Trap | 1 |  | 1 | 1 |  |  |  |  |  |  |  | 1 |  |  | 1 |  |  |  |  |  | 2 | 7 | 3 |
| Synthwave and outrun | 1 |  | 1 | 1 |  |  |  | 1 |  |  |  |  |  |  |  | 1 |  |  |  | 1 | 1 | 7 | 3 |
| Chillwave |  |  | 1 | 1 |  |  |  | 1 |  |  |  |  |  |  | 1 |  |  |  |  |  | 1 | 5 | 1 |
| Ambient |  |  |  | 3 |  |  |  |  |  |  |  | 1 |  |  |  |  | 2 |  |  |  | 1 | 7 | 2 |
| Drone |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 | 5 |  |  |  | 6 | 2 |
| IDM and glitch |  |  | 1 | 1 |  |  |  |  |  |  |  | 1 |  |  |  | 1 |  |  | 1 |  | 1 | 6 | 2 |
| Breakbeat and big beat | 2 |  |  |  | 1 |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  | 1 | 6 | 1 |
| Electro | 1 |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  |  |  | 1 | 6 | 2 |
| Downtempo and trip-hop | 1 |  | 1 |  |  |  |  | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  | 1 | 5 | 2 |
| Footwork and juke | 1 |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  | 1 |  |  |  | 1 |  | 1 | 6 | 2 |
| Hyperpop | 1 |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  | 1 | 1 |  |  | 1 |  | 1 | 7 | 2 |
| City pop | 1 |  | 1 | 1 |  |  |  | 1 |  | 1 | 1 |  |  |  |  |  |  |  |  |  | 1 | 7 | 2 |
| New age and Fourth World |  |  | 2 | 1 |  |  |  |  |  |  |  | 1 | 1 |  |  |  | 1 |  |  |  |  | 6 | 2 |
| Exotica |  |  |  |  |  |  |  | 1 |  | 1 |  | 1 | 1 |  |  |  | 1 |  | 2 |  |  | 7 | 2 |
| Video-game chiptune | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  | 1 |  | 1 |  |  |  |  | 1 | 5 | 3 |
| **Total** | **25** | **1** | **14** | **17** | **11** | **1** | **1** | **14** | **2** | **5** | **1** | **6** | **2** | **1** | **11** | **15** | **9** | **5** | **8** | **1** | **24** | **174** | **55** |

- W3.11 badge (derived; includes library-only presets): 69. Uses the library disc: 60. Has a v3 version: 78 (of which kits, v3 only: 21).

## 4. Genres

### Deep house

| | |
|---|---|
| Family | House |
| Tempo | 118-124 BPM, light 16th swing |
| Keys and harmony | Minor keys (A, F, D, E minor); minor 7th and 9th voicings, two-chord vamps; maj7 colour |
| What producers look for in a preset | Chords that sit (no energy below ~100 Hz so the bass has room), a bass that is felt more than heard, presets that are ready to swing, and macro filter sweeps. |
| Sound Recorder feel | Let Sound Recorder echo (E) be the dub delay on the stabs and keep the stab short with a hard Delete After: the cut edge is the click of a gated sampler. Keep XP's marimba ding audible as the tine. |
| Sources | [Wikipedia: Deep house](https://en.wikipedia.org/wiki/Deep_house), [Native Instruments blog: How to make a deep house track](https://www.native-instruments.com/blogs/blog/how-to-make-a-deep-house-track), [Mode Audio: Deep House, 5 production essentials](https://modeaudio.com/magazine/deep-house-5-production-essentials), [Berklee Online: Create authentic house music (chords, bass lines, melody)](https://online.berklee.edu/takenote/?p=14419) |

Signature sounds and roles:

- minor 7th/9th organ or e-piano chord stabs on the off-beat, often with a dotted-8th delay
- round sine or nearly-sine sub bass following the chord roots in two-bar lines
- soft hats and shakers with swing, rim shots, a muted clap
- short spoken or sung vocal fragments, filtered
- warm, low-contrast pads; filter sweeps as the main FX

#### Velvet Minor Nine (stab, P1, XP badge)

- **Inspired by:** deep house organ/EP minor-9 stabs (90s New York and Chicago deep house)
- **Character:** Short minor-9 chord with a soft bell tine, pushed back by dotted-8th echo taps that pan left and right.
- **DNA v2 (now):** `xpding@25]<#6H0,3,7,10,14/xpding@25]<E#5H0,3,7,10L30O375Q-45/xpding@25]<#5H0,3,7L18O750Q45;A0D700S20R450V80K47`
  - Recipe: `xpding cut after 25% slower 6rec notes +0 +3 +7 +10 +14 / xpding cut after 25% slower echo 5rec notes +0 +3 +7 +10 level 30% offset 375ms pan L45 / xpding cut after 25% slower 5rec notes +0 +3 +7 level 18% offset 750ms pan R45 | atk 0ms dec 700ms sus 20% rel 450ms vel 80% root B2`
- **DNA v3 (later):** `xpding@25]<#6H0,3,7,10,14Sd4/xpding@25]<E#5H0,3,7,10L30O375Q-45Sd4/xpding@25]<#5H0,3,7L18O750Q45Sd3;A0D700S20R450V80K47q2`
  - Features: scale (q), stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `xpding`
- **Swap candidates:** Windows: chord, chordxp, tada, tadaxp, default, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Three copies of one trimmed ding: the delay taps are layer offsets (O375, O750 at 120 BPM), not a plugin.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 1.

#### Round Floor Sub (bass, P1, XP badge)

- **Inspired by:** filtered-saw-to-sine deep house bass (two-bar root lines)
- **Character:** A short, round sub pluck with a soft felt click; decays to a low hum so long notes still breathe.
- **DNA v2 (now):** `xpringout@20[@40]@0CP@0CP@0CP<<#6/balloon<<@40]#2FL35;A0D450S35R120V90K45`
  - Recipe: `xpringout cut before 20% cut after 40% double x3 slower x2 6rec / balloon slower x2 cut after 40% 2rec fixed level 35% | atk 0ms dec 450ms sus 35% rel 120ms vel 90% root A2`
- **DNA v3 (later):** `xpringout@20[@40]@0CP@0CP@0CP<<#6Nlg40/balloon<<@40]#2FL35;A0D450S35R120V90K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `xpringout`, `balloon`
- **Swap candidates:** Windows: ringout, batlow, critstop, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** The ringback tone's two beating sines give the slow movement a filter envelope would.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workgroup-house. Notes before stealing: 2.

#### Dorian Drawbar Bark (organ, P2, XP badge)

- **Inspired by:** deep/garage house organ (drawbars with a percussive bark)
- **Character:** Octave-and-fifth drawbar tone, a fast drop to 40 % after the key click: the classic organ bark.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP+#10H0,12,19Ja0,100.60,45.300,38/xpstart>#2FL40;R90V70K69`
  - Recipe: `ringout cut before 20% cut after 40% double x3 louder 10rec notes +0 +12 +19 amp 0:100,60:45,300:38 / xpstart faster 2rec fixed level 40% | rel 90ms vel 70% root A4`
- **Sounds used:** `ringout`, `xpstart`
- **Swap candidates:** Windows: xpringout, print; library: organ_hammond_m100_flute_c, organ_pipe_open_31, ems_ferranti_hoot_c4
- **Sound Recorder feel:** Let Sound Recorder echo (E) be the dub delay on the stabs and keep the stab short with a hard Delete After: the cut edge is the click of a gated sampler. Keep XP's marimba ding audible as the tine.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 2.

#### Afterhours Tine (keys, P2, XP badge)

- **Inspired by:** tine e-piano in late-night deep house
- **Character:** Marimba-like XP ding for the tine, a slowed pure sine bell under it for the body, gentle unison chorus.
- **DNA v2 (now):** `xpding@25]#6/print@5[@60]<#6L50U2~6Q-20T1;A0D1800S30R500V85m11L20,90m1=40K59`
  - Recipe: `xpding cut after 25% 6rec / print cut before 5% cut after 60% slower 6rec level 50% unison 2 +-6c pan L20 transpose +1 | atk 0ms dec 1.8s sus 30% rel 500ms vel 85% m1 L1 level 20-90 m1 40% root B3`
- **Sounds used:** `xpding`, `print`
- **Swap candidates:** Windows: default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Macro 1 brings up the body layer: the "tone" knob of a suitcase piano.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 3.

#### Smoke Room Pad (pad, P2, XP badge)

- **Inspired by:** warm minor pad under deep house chords
- **Character:** The XP logoff phrase slowed into a dark bed with a sine-loop floor; slow attack, long release.
- **DNA v2 (now):** `logoff<@20[#10U3~10/ringout@20[@40]@0CP@0CP@0CP<#6U2~8L45T-6;A900S90R1800K51`
  - Recipe: `logoff slower cut before 20% 10rec unison 3 +-10c / ringout cut before 20% cut after 40% double x3 slower 6rec unison 2 +-8c level 45% transpose -6 | atk 900ms sus 90% rel 1.8s root D#3`
- **Sounds used:** `logoff`, `ringout`
- **Swap candidates:** Windows: startup, logon, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Let Sound Recorder echo (E) be the dub delay on the stabs and keep the stab short with a hard Delete After: the cut edge is the click of a gated sampler. Keep XP's marimba ding audible as the tine.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 3.

#### Lobby Courtesy Chop (vocal, P2, W3.11 badge)

- **Inspired by:** chopped spoken vocal hooks in deep house
- **Character:** A syllable of 1952 office-courtesy narration, echoed once; v3 gives every key its own syllable.
- **DNA v2 (now):** `prelinger_office_courtesy@37[@2]E#8;A5D300S60R200V80`
  - Recipe: `prelinger_office_courtesy cut before 37% cut after 2% echo 8rec | atk 5ms dec 300ms sus 60% rel 200ms vel 80%`
- **DNA v3 (later):** `prelinger_office_courtesy@37[@2]E#8Ws.05~.9l.008~.015Yk;A5D300S60R200V80`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `prelinger_office_courtesy`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, crowd_sing_aah_f, ems_704_vowel_a3, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Speech from a training film, cut with Delete Before/After: the edit is the hook.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: workgroup-house. Notes before stealing: 8.

#### Low-Pass Sweep Wash (fx, P2, XP badge)

- **Inspired by:** filter-sweep noise transitions
- **Character:** The XP restore whoosh slowed two octaves and echoed, under a paper-crumple air layer.
- **DNA v2 (now):** `restore<<E#8/xprecycle<<<E#8FL40;A1200S100R2500`
  - Recipe: `restore slower x2 echo 8rec / xprecycle slower x3 echo 8rec fixed level 40% | atk 1.2s sus 100% rel 2.5s`
- **Sounds used:** `restore`, `xprecycle`
- **Swap candidates:** Windows: minimize, xpringin, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Let Sound Recorder echo (E) be the dub delay on the stabs and keep the stab short with a hard Delete After: the cut edge is the click of a gated sampler. Keep XP's marimba ding audible as the tine.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 8.

#### Shuffle Basement Kit (drums, P2, XP badge)

- **Inspired by:** deep house drum machine kits (909/707-era hats, soft clap, rim)
- **Character:** Soft pop-kick, echo clap, crumple hats with a short choke, a click rim and mallet toms.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/recycle>>@50]E#4F/xprecycle>>>@40]#5F/xpstart>#4;R200V90xs58k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Pads fire Sound Recorder strips; the hat strip shows the choke as the green wave stopping.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Classic (Chicago) house

| | |
|---|---|
| Family | House |
| Tempo | 118-126 BPM, straight or lightly swung |
| Keys and harmony | Major and minor; piano riffs on I-IV or vi-IV-V; organ and piano stabs in root position |
| What producers look for in a preset | Instantly playable piano/organ stabs that cut through, raw drum machines, and an acid line with accent and slide. |
| Sound Recorder feel | Use the 3.x CHORD.WAV as the struck house-piano chord and TADA as the stab: they are period-correct ROM-age samples already. |
| Sources | [Wikipedia: Chicago house](https://en.wikipedia.org/wiki/Chicago_house), [Sound on Sound: Secrets of House & Trance (2004)](https://www.soundonsound.com/techniques/secrets-house-trance) |

Signature sounds and roles:

- house piano chords (a bright rompler piano, root plus octave)
- squelchy 303-style acid lines (acid house) or a punchy organ/rompler bass
- drum-machine kits: 909 kick and hats, 808/909 clap
- orchestra hits and string stabs from ROMs
- diva vocal samples, short shouts

#### Warehouse Piano Stack (keys, P1, W3.11 badge)

- **Inspired by:** the rompler house piano of late-80s/early-90s Chicago and New York house
- **Character:** The Windows 3.1 struck chord trimmed to its strike, root plus octave, a bright ding on top for the hammer.
- **DNA v2 (now):** `chord@5[@40]#10H0,12/ding@15]#6L35;A0D1100S20R250V70K55`
  - Recipe: `chord cut before 5% cut after 40% 10rec notes +0 +12 / ding cut after 15% 6rec level 35% | atk 0ms dec 1.1s sus 20% rel 250ms vel 70% root G3`
- **Sounds used:** `chord`, `ding`
- **Swap candidates:** Windows: xpding, print, default, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Pure Windows 3.x sounds: this plays with the W3.11 badge on both editions.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 5.

#### Acid Accent Line (bass, P1, XP badge)

- **Inspired by:** Roland TB-303 acid line (Phuture, acid house)
- **Character:** A clipped bell-attack buzz with a fast decaying envelope; velocity opens it, mono slide in v3.
- **DNA v2 (now):** `default@3]<<+++#8Ja0,100.40,60.220,25/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#8L50T4;A0R60V100K51`
  - Recipe: `default cut after 3% slower x2 louder x3 8rec amp 0:100,40:60,220:25 / ringout cut before 150ms cut after 20ms cut after 20% double x9 slower x2 louder 8rec level 50% transpose +4 | atk 0ms rel 60ms vel 100% root D#3`
- **DNA v3 (later):** `default@3]<<+++#8Ja0,100.40,60.220,25Nlg50/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<<+#8L50T4Nlg50;A0R60V100K51`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `default`, `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, exclaim; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** There is no filter: the squelch is the clip steps (+++) plus a drawn envelope; the slide is v3 glide.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workgroup-house. Notes before stealing: 8.

#### Shout Hit (stab, P2, W3.11 badge)

- **Inspired by:** house/hip-house orchestra-and-vocal stab
- **Character:** The 3.1 TADA fanfare cut to its first blast, slowed one octave, doubled at the octave.
- **DNA v2 (now):** `tada@20]<+#10H0,12/chord@10]#6L50T5;A0D400S0R200V80K48`
  - Recipe: `tada cut after 20% slower louder 10rec notes +0 +12 / chord cut after 10% 6rec level 50% transpose +5 | atk 0ms dec 400ms sus 0% rel 200ms vel 80% root C3`
- **Sounds used:** `tada`, `chord`
- **Swap candidates:** Windows: chordxp, tadaxp, xpding, default, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Use the 3.x CHORD.WAV as the struck house-piano chord and TADA as the stab: they are period-correct ROM-age samples already.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 5.

#### Jack Organ (organ, P2, W3.11 badge)

- **Inspired by:** Chicago/garage organ riffs (M1-style organ in house)
- **Character:** 3.11 version: the ringout sine loop with octave/fifth drawbars and a ding click.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP+#12H0,12,19/ding>>@5]#4FL40;A0D250S45R90V70K69`
  - Recipe: `ringout cut before 20% cut after 40% double x3 louder 12rec notes +0 +12 +19 / ding faster x2 cut after 5% 4rec fixed level 40% | atk 0ms dec 250ms sus 45% rel 90ms vel 70% root A4`
- **Sounds used:** `ringout`, `ding`
- **Swap candidates:** Windows: xpringout, print; library: organ_hammond_m100_flute_c, organ_pipe_open_31, ems_ferranti_hoot_c4
- **Sound Recorder feel:** Use the 3.x CHORD.WAV as the struck house-piano chord and TADA as the stab: they are period-correct ROM-age samples already.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 4.

#### Disco Sweep Strings (strings, P2, XP badge)

- **Inspired by:** house string stabs and rising string swells from disco
- **Character:** Logon swell slowed with wide unison, a reverse-chime rise on the attack.
- **DNA v2 (now):** `logon<@15[#10U3~14/chimes>R#6L40T1;A150D800S80R700K44`
  - Recipe: `logon slower cut before 15% 10rec unison 3 +-14c / chimes faster reverse 6rec level 40% transpose +1 | atk 150ms dec 800ms sus 80% rel 700ms root G#2`
- **Sounds used:** `logon`, `chimes`
- **Swap candidates:** Windows: startup, logoff; library: violin_section_sus_c4, cello_section_sus_c3, erhu_d3
- **Sound Recorder feel:** Use the 3.x CHORD.WAV as the struck house-piano chord and TADA as the stab: they are period-correct ROM-age samples already.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 3.

#### Soul Vowel Stab (vocal, P2, W3.11 badge)

- **Inspired by:** sampled soul-diva "ah" in house
- **Character:** A crowd "aah" from the library disc, trimmed to a stab and echoed, plus the 1961 computer vowel underneath.
- **DNA v2 (now):** `crowd_sing_aah_f@10[@15]E#10/ems_704_vowel_a3@20[@30]#6L30T-4;A5D500S40R300K53`
  - Recipe: `crowd_sing_aah_f cut before 10% cut after 15% echo 10rec / ems_704_vowel_a3 cut before 20% cut after 30% 6rec level 30% transpose -4 | atk 5ms dec 500ms sus 40% rel 300ms root F3`
- **Sounds used:** none; library: `crowd_sing_aah_f`, `ems_704_vowel_a3`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Use the 3.x CHORD.WAV as the struck house-piano chord and TADA as the stab: they are period-correct ROM-age samples already.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: workgroup-house. Notes before stealing: 6.

#### Warehouse Siren (fx, P2, XP badge)

- **Inspired by:** rave/house siren FX
- **Character:** The XP synth phone trill slowed and repeated: a rising-falling alarm that sits in key.
- **DNA v2 (now):** `xpringin<<@0CP@0CPE#8;A50S100R600B12K62`
  - Recipe: `xpringin slower x2 double x2 echo 8rec | atk 50ms sus 100% rel 600ms bend +-12 root D4`
- **Sounds used:** `xpringin`
- **Swap candidates:** Windows: restore, minimize, xprecycle, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Use the 3.x CHORD.WAV as the struck house-piano chord and TADA as the stab: they are period-correct ROM-age samples already.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 8.

#### Jack Box Kit (drums, P1, XP badge)

- **Inspired by:** Roland TR-909 and TR-808 house kits
- **Character:** Punchy sine kick with a click, crumple snare, echo clap, hats from paper noise, cowbell from the XP default bell.
- **DNA v2 (now):** `ringout@20[@40]@0CP<<<Ja0,100.60,70.350,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double slower x3 amp 0:100,60:70,350:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP<<<Ja0,100.60,70.350,0#3F/recycle>@30]+#4F/xprecycle>>>@40]#5F/default>@8]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `recycle`, `xprecycle`, `default`
- **Swap candidates:** Windows: balloon, menu, xpstart, start, infobar, critstop; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** The 909 kick is a two-octave-down beating sine cut by a drawn envelope.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### French house (filter house)

| | |
|---|---|
| Family | House |
| Tempo | 120-126 BPM |
| Keys and harmony | Major-key disco loops; 7th and 9th chords lifted from 70s/80s funk and disco |
| What producers look for in a preset | Loop-like chord stabs with a phaser sweep, funky basses, a talkbox-like vowel lead, and a pump they can feel without a compressor. |
| Sound Recorder feel | Make the pump a drawn amplitude envelope (Ja) per beat; make the phaser a SELF-FLANGE (C@3X) baked into the buffer, so the strip shows the comb. |
| Sources | [Wikipedia: French house](https://en.wikipedia.org/wiki/French_house) |

Signature sounds and roles:

- a filtered disco sample loop that opens and closes (the filter IS the arrangement)
- heavy pumping sidechain compression
- phaser/flanger on guitars and keys
- talkbox and vocoder leads
- slap and funk bass

#### Filtered Disco Loop Chord (stab, P1, XP badge)

- **Inspired by:** filtered disco-sample house (late 90s Paris)
- **Character:** A chord-xp cluster self-flanged and slowed, with a ducking envelope drawn on the beat at 124 BPM.
- **DNA v2 (now):** `chordxp@5[@60]C@3X<#10H0,5Ja0,10.40,100.240,60.484,10.524,100.724,60/xprecycle>>>@30]#2FL15;A0R300V60K43`
  - Recipe: `chord-xp cut before 5% cut after 60% copy at 3% mix paste slower 10rec notes +0 +5 amp 0:10,40:100,240:60,484:10,524:100,724:60 / xprecycle faster x3 cut after 30% 2rec fixed level 15% | atk 0ms rel 300ms vel 60% root G2`
- **DNA v3 (later):** `chordxp@5[@60]C@3X<#10H0,5Ja0,10.40,100.240,60.484,10.524,100.724,60Sw.5/xprecycle>>>@30]#2FL15;A0R300V60K43`
  - Features: stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `chordxp`, `xprecycle`
- **Swap candidates:** Windows: chord, tada, tadaxp, xpding, default, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** The comb is Paste Mix of the buffer onto itself 3 % later.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 2.

#### Slap Disco Bass (bass, P2, XP badge)

- **Inspired by:** disco/funk slap bass in French house
- **Character:** XP ding trimmed and clipped two octaves down with a balloon pop for the thumb.
- **DNA v2 (now):** `xpding@30]<<++#8/balloon<@30]#4FL60;A0D300S50R80V95K35`
  - Recipe: `xpding cut after 30% slower x2 louder x2 8rec / balloon slower cut after 30% 4rec fixed level 60% | atk 0ms dec 300ms sus 50% rel 80ms vel 95% root B1`
- **DNA v3 (later):** `xpding@30]<<++#8Nmg25/balloon<@30]#4FL60;A0D300S50R80V95K35`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `xpding`, `balloon`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Make the pump a drawn amplitude envelope (Ja) per beat; make the phaser a SELF-FLANGE (C@3X) baked into the buffer, so the strip shows the comb.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workgroup-house. Notes before stealing: 4.

#### Robot Mouth Lead (lead, P2, W3.11 badge)

- **Inspired by:** talkbox / vocoder leads in filter house
- **Character:** The 1961 vowel synthesis sustained with LOOP-OSC and a short scoop; velocity adds the buzz layer.
- **DNA v2 (now):** `ems_704_vowel_a3@30[@30]@0CP@0CP@0CP@0CP#8/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#4L30T-2;A20R150V80K57`
  - Recipe: `ems_704_vowel_a3 cut before 30% cut after 30% double x4 8rec / ringout cut before 150ms cut after 20ms cut after 20% double x9 4rec level 30% transpose -2 | atk 20ms rel 150ms vel 80% root A3`
- **DNA v3 (later):** `ems_704_vowel_a3@30[@30]@0CP@0CP@0CP@0CP#8Nlg70Vs20,60/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#4L30T-2Nlg70;A20R150V80K57`
  - Features: tape wow/flutter/scoop, voice mode (mono/legato/glide)
- **Sounds used:** `ringout`; library: `ems_704_vowel_a3`
- **Swap candidates:** Windows: tadaxp, tada, print, xpringin, notify, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Make the pump a drawn amplitude envelope (Ja) per beat; make the phaser a SELF-FLANGE (C@3X) baked into the buffer, so the strip shows the comb.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: workgroup-house. Notes before stealing: 4.

#### Phased Clav Chop (keys, P2, XP badge)

- **Inspired by:** phased funky keys stabs
- **Character:** The XP marimba ding cut very short and self-flanged twice: a percussive, phased chop.
- **DNA v2 (now):** `xpding@12]C@2XC@5X+#10H0,7;A0D200S0R120V90K59`
  - Recipe: `xpding cut after 12% copy at 2% mix paste copy at 5% mix paste louder 10rec notes +0 +7 | atk 0ms dec 200ms sus 0% rel 120ms vel 90% root B3`
- **Sounds used:** `xpding`
- **Swap candidates:** Windows: print, default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Make the pump a drawn amplitude envelope (Ja) per beat; make the phaser a SELF-FLANGE (C@3X) baked into the buffer, so the strip shows the comb.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 5.

#### Sampled Strings Swell (strings, P2, W3.11 badge)

- **Inspired by:** disco string swells looped in filter house
- **Character:** Violin-section sustain from the library, slowed with echo and a pumping envelope.
- **DNA v2 (now):** `violin_section_sus_c4@10[E#10U2~10Ja0,20.300,100.484,30.540,100;A0R600K60`
  - Recipe: `violin_section_sus_c4 cut before 10% echo 10rec unison 2 +-10c amp 0:20,300:100,484:30,540:100 | atk 0ms rel 600ms root C4`
- **Sounds used:** none; library: `violin_section_sus_c4`
- **Swap candidates:** Windows: startup, logon, logoff; library: cello_section_sus_c3, erhu_d3, cello_section_sus_c3
- **Sound Recorder feel:** Make the pump a drawn amplitude envelope (Ja) per beat; make the phaser a SELF-FLANGE (C@3X) baked into the buffer, so the strip shows the comb.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: workgroup-house. Notes before stealing: 5.

#### Two Bar Sweep 124 (fx, P2, XP badge)

- **Inspired by:** filter-up risers in French house
- **Character:** Restore whoosh at four speeds, staged by offsets: a two-bar rise at 124 BPM (3.87 s).
- **DNA v2 (now):** `restore<<<#4/restore<<#4O1800L70/restore<#4O3000L50/restore#4O3800L40;A3000S100R800`
  - Recipe: `restore slower x3 4rec / restore slower x2 4rec offset 1.8s level 70% / restore slower 4rec offset 3s level 50% / restore 4rec offset 3.8s level 40% | atk 3s sus 100% rel 800ms`
- **Sounds used:** `restore`
- **Swap candidates:** Windows: minimize, xprecycle, xpringin, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** v2 offsets stop at 4000 ms, so a v2 riser is at most about two bars; longer builds need v3.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: workgroup-house. Notes before stealing: 4.

#### Pumping Disco Kit (drums, P3, XP badge)

- **Inspired by:** disco breaks re-cut on a drum machine
- **Character:** Pop kick, flam snare, open/closed crumple hats, a tambourine from ringin.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/recycle>@30]+E#4F/xprecycle>>>@40]#5F/ringin>@15]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `ringin`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Make the pump a drawn amplitude envelope (Ja) per beat; make the phaser a SELF-FLANGE (C@3X) baked into the buffer, so the strip shows the comb.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Detroit techno

| | |
|---|---|
| Family | Techno |
| Tempo | 125-135 BPM |
| Keys and harmony | Minor and modal (Dorian, Aeolian); string-pad chords with sus and minor-7 colour |
| What producers look for in a preset | Soulful pads and stabs over machine drums; sequences that groove; an optimistic, space-age tone colour. |
| Sound Recorder feel | The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens. |
| Sources | [Wikipedia: Detroit techno](https://en.wikipedia.org/wiki/Detroit_techno) |

Signature sounds and roles:

- lush, futurist string pads and chords
- rubbery synth bass sequences
- TR-909 drums with claps and open hats
- sequenced bell and synth-brass stabs
- sci-fi FX and vocoded voices

#### Motor City Strings (pad, P1, XP badge)

- **Inspired by:** Detroit techno string pads (late 80s second wave)
- **Character:** XP startup sustained middle slowed, wide unison; a quiet logon layer adds air.
- **DNA v2 (now):** `startup@20[@50]<#10U3~14/logon<@20[#6U2~8L35;A600S90R1500K56`
  - Recipe: `startup cut before 20% cut after 50% slower 10rec unison 3 +-14c / logon slower cut before 20% 6rec unison 2 +-8c level 35% | atk 600ms sus 90% rel 1.5s root G#3`
- **Sounds used:** `startup`, `logon`
- **Swap candidates:** Windows: logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 3.

#### Eastside Minor Stab (stab, P2, XP badge)

- **Inspired by:** Detroit minor-7 synth stab sequences
- **Character:** A minor-7 stack of a trimmed default bell, octave-down copy as body, short release.
- **DNA v2 (now):** `default@15]<#8H0,3,7,10/default@15]<<#4H0,7L60;A0D350S0R180V85K63`
  - Recipe: `default cut after 15% slower 8rec notes +0 +3 +7 +10 / default cut after 15% slower x2 4rec notes +0 +7 level 60% | atk 0ms dec 350ms sus 0% rel 180ms vel 85% root D#4`
- **DNA v3 (later):** `default@15]<#8H0,3,7,10Sd4/default@15]<<#4H0,7L60Sd3;A0D350S0R180V85K63q2`
  - Features: scale (q), stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `default`
- **Swap candidates:** Windows: chord, chordxp, tada, tadaxp, xpding, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 2.

#### Rubber Sequence Bass (bass, P1, XP badge)

- **Inspired by:** rubbery synth-bass sequences of early techno
- **Character:** Short ringback-loop bass with a drawn snap and a click; mono in v3 for overlapping 16ths.
- **DNA v2 (now):** `xpringout@20[@40]@0CP@0CP@0CP<<+#8Ja0,100.30,70.180,30/xpstart#2FL30;A0R70V90K45`
  - Recipe: `xpringout cut before 20% cut after 40% double x3 slower x2 louder 8rec amp 0:100,30:70,180:30 / xpstart 2rec fixed level 30% | atk 0ms rel 70ms vel 90% root A2`
- **DNA v3 (later):** `xpringout@20[@40]@0CP@0CP@0CP<<+#8Ja0,100.30,70.180,30Nmg15/xpstart#2FL30;A0R70V90K45q2xg60`
  - Features: mine-grid sequencer/arp (x), scale (q), voice mode (mono/legato/glide)
- **Sounds used:** `xpringout`, `xpstart`
- **Swap candidates:** Windows: ringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: techno-server. Notes before stealing: 2.

#### Starfield Sync Lead (lead, P2, W3.11 badge)

- **Inspired by:** hard-sync style leads in Detroit techno
- **Character:** Two LOOP-OSC buzzes a fifth apart through clip steps: a nasal sync-like tone.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP++#6/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP>+#6T-5L40;A5R200K59`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 louder x2 6rec / ringout cut before 150ms cut after 20ms cut after 20% double x9 faster louder 6rec transpose -5 level 40% | atk 5ms rel 200ms root B3`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: tadaxp, tada, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 6.

#### Transmission Voice (fx, P2, W3.11 badge)

- **Inspired by:** vocoded / spoken sci-fi voices in techno
- **Character:** A NASA go-for-TLI call, cut to a phrase and slowed one octave with echo.
- **DNA v2 (now):** `nasa_apollo8_go_for_tli@20[@40]<E#6;A20R600`
  - Recipe: `nasa_apollo8_go_for_tli cut before 20% cut after 40% slower echo 6rec | atk 20ms rel 600ms`
- **Sounds used:** none; library: `nasa_apollo8_go_for_tli`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, popup, hwin; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: techno-server. Notes before stealing: 6.

#### Assembly Line Kit (drums, P2, XP badge)

- **Inspired by:** TR-909 techno kits
- **Character:** Punch kick, crumple snare, echo clap, open hat ring, relay rim.
- **DNA v2 (now):** `ringout@20[@40]@0CP<<<+Ja0,100.50,60.300,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double slower x3 louder amp 0:100,50:60,300:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP<<<+Ja0,100.50,60.300,0#3F/recycle>>@50]E#4F/xprecycle>>>@40]#5F/em_relay_click_a#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `recycle`, `xprecycle`; library: `em_relay_click_a`
- **Swap candidates:** Windows: balloon, menu, xpstart, start, infobar, critstop; library: ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap, relay_click; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** The XP startup is literally a futurist string swell: slow it, unison it, and let its four-note figure come through when the macro opens.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Minimal techno and microhouse

| | |
|---|---|
| Family | Techno |
| Tempo | 122-130 BPM |
| Keys and harmony | Often atonal or one-note; when tonal, minor and static |
| What producers look for in a preset | Perfect, tiny one-shots: clicks with pitch, wooden and metallic perc, short sub hits. Space between sounds matters more than size. |
| Sound Recorder feel | This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw. |
| Sources | [Wikipedia: Minimal techno](https://en.wikipedia.org/wiki/Minimal_techno) |

Signature sounds and roles:

- clicks, ticks and very short percussive blips
- one-note dub chords
- micro-edited samples (microhouse)
- deep, short kicks
- tiny metallic hits and wooden perc

#### Menu Click Perc (perc, P1, XP badge)

- **Inspired by:** minimal techno click percussion
- **Character:** The 30 ms XP menu click, pitched chromatically: a tuned tick from a desktop menu.
- **DNA v2 (now):** `menu#16;A0R40V100K60`
  - Recipe: `menu 16rec | atk 0ms rel 40ms vel 100% root C4`
- **Sounds used:** `menu`
- **Swap candidates:** Windows: xpstart, infobar, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** Raw. The original 30 ms file, nothing else.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 16.

#### Balloon Blip Tom (perc, P2, XP badge)

- **Inspired by:** microhouse pitched blips
- **Character:** The XP balloon pop down one octave, echoed: a tiny round tom.
- **DNA v2 (now):** `balloon<E#16;A0R80V100K69`
  - Recipe: `balloon slower echo 16rec | atk 0ms rel 80ms vel 100% root A4`
- **Sounds used:** `balloon`
- **Swap candidates:** Windows: menu, xpstart, infobar, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 16.

#### Relay Wood Tick (perc, P2, XP badge)

- **Inspired by:** woodblock/clave ticks in minimal
- **Character:** A relay pull and an infobar click layered: a woody, electrical tick.
- **DNA v2 (now):** `ems_relay_pull#8F/infobar#8;A0R50V100K67`
  - Recipe: `ems_relay_pull 8rec fixed / infobar 8rec | atk 0ms rel 50ms vel 100% root G4`
- **Sounds used:** `infobar`; library: `ems_relay_pull`
- **Swap candidates:** Windows: menu, xpstart, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: techno-server. Notes before stealing: 8.

#### Dot Sub (bass, P2, W3.11 badge)

- **Inspired by:** minimal techno short sub hits
- **Character:** A 150 ms slice of the sine loop two octaves down; a dot of low end.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<@15]#12;A0R40V90K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x2 cut after 15% 12rec | atk 0ms rel 40ms vel 90% root A2`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 12.

#### One-Finger Dub Chord (stab, P2, W3.11 badge)

- **Inspired by:** minimal dub chord stabs
- **Character:** A short minor triad from the 3.x ding dropped two octaves, single echo.
- **DNA v2 (now):** `ding@10]<<E#12H0,3,7;A0D200S0R150V80K55`
  - Recipe: `ding cut after 10% slower x2 echo 12rec notes +0 +3 +7 | atk 0ms dec 200ms sus 0% rel 150ms vel 80% root G3`
- **Sounds used:** `ding`
- **Swap candidates:** Windows: chord, chordxp, tada, tadaxp, xpding, default; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 4.

#### Office HVAC Bed (texture, P2, W3.11 badge)

- **Inspired by:** micro-texture beds (microhouse)
- **Character:** Office ambience slowed two octaves: a soft air bed under clicks.
- **DNA v2 (now):** `office_ambience_01<<#4F;A2000S100R3000`
  - Recipe: `office_ambience_01 slower x2 4rec fixed | atk 2s sus 100% rel 3s`
- **Sounds used:** none; library: `office_ambience_01`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: rain_on_window, creek_loop, hdd_conner_spin, insect_crickets_mojave, hdd_conner_spin, em_hum_mains_loop
- **Sound Recorder feel:** This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: techno-server. Notes before stealing: 4.

#### Click Server Kit (drums, P2, XP badge)

- **Inspired by:** minimal techno kits
- **Character:** Pop kick, menu-click snare, short hats, relay rim.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/menu<+#4F/xprecycle>>>@40]#5F/ems_relay_tiny#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `menu`, `xprecycle`; library: `ems_relay_tiny`
- **Swap candidates:** Windows: recycle, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** This is Sound Recorder's home ground: the shortest Windows sounds (menu, xpstart, infobar, balloon) are already minimal-techno percussion. Present them nearly raw.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Dub techno

| | |
|---|---|
| Family | Techno |
| Tempo | 115-125 BPM |
| Keys and harmony | Minor; one chord (minor or minor-7) for minutes |
| What producers look for in a preset | A chord stab with a long, evolving delay tail; a hiss bed; space. |
| Sound Recorder feel | Dub delay is exactly what layer offsets plus Sound Recorder echo give: each tap is a real recorder starting later, each echo a real Add Echo. |
| Sources | [Wikipedia: Dub techno](https://en.wikipedia.org/wiki/Dub_techno) |

Signature sounds and roles:

- a single chord stab drenched in tape delay and reverb, filtered over minutes
- deep sub bass, very soft
- hiss and vinyl-like noise beds
- soft kicks and rimshots

#### Feedback Chain Stab (stab, P1, XP badge)

- **Inspired by:** dub techno chord stab with feedback delay (Berlin, early 90s)
- **Character:** Minor-7 stab from the XP ding at 0/375/750/1125 ms, each tap darker (slowed copies) and wider.
- **DNA v2 (now):** `xpding@20]E#4H0,3,7,10/xpding@20]EE#4H0,3,7,10L45O375Q-50/xpding@20]EE<>#4H0,3,7,10L28O750Q50/xpding@20]EEE<>#4H0,3,7,10L16O1125Q-30;A0D400S10R1200V70m32L0,90m33L0,56m34L0,32m3=50K59`
  - Recipe: `xpding cut after 20% echo 4rec notes +0 +3 +7 +10 / xpding cut after 20% echo x2 4rec notes +0 +3 +7 +10 level 45% offset 375ms pan L50 / xpding cut after 20% echo x2 slower faster 4rec notes +0 +3 +7 +10 level 28% offset 750ms pan R50 / xpding cut after 20% echo x3 slower faster 4rec notes +0 +3 +7 +10 level 16% offset 1125ms pan L30 | atk 0ms dec 400ms sus 10% rel 1.2s vel 70% m3 L2 level 0-90 m3 L3 level 0-56 m3 L4 level 0-32 m3 50% root B3`
- **DNA v3 (later):** `xpding@20]E#4H0,3,7,10Sd4/xpding@20]EE#4H0,3,7,10L45O375Q-50Sd4/xpding@20]EE<>#4H0,3,7,10L28O750Q50Sd4/xpding@20]EEE<>#4H0,3,7,10L16O1125Q-30Sd4;A0D400S10R1200V70m32L0,90m33L0,56m34L0,32m3=50K59q1`
  - Features: scale (q), stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `xpding`
- **Swap candidates:** Windows: chord, chordxp, tada, tadaxp, default, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Macro 3 (space) is the feedback knob. The darker taps use a speed round-trip (<>) as the filter.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 1.

#### Tape Hiss Fog (texture, P2, XP badge)

- **Inspired by:** hiss and noise beds in dub techno
- **Character:** Paper crumple slowed three octaves and echoed twice: a fog of hiss.
- **DNA v2 (now):** `xprecycle<<<EE#6F/recycle<<<E#4FL60;A1500S100R3000`
  - Recipe: `xprecycle slower x3 echo x2 6rec fixed / recycle slower x3 echo 4rec fixed level 60% | atk 1.5s sus 100% rel 3s`
- **Sounds used:** `xprecycle`, `recycle`
- **Swap candidates:** Windows: startup; library: rain_on_window, creek_loop, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Dub delay is exactly what layer offsets plus Sound Recorder echo give: each tap is a real recorder starting later, each echo a real Add Echo.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 4.

#### Felt Sub (bass, P2, W3.11 badge)

- **Inspired by:** soft dub techno sub
- **Character:** A slow-attack sine sub; barely there.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<#8;A30D0S100R250V60K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x2 8rec | atk 30ms dec 0ms sus 100% rel 250ms vel 60% root A2`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Dub delay is exactly what layer offsets plus Sound Recorder echo give: each tap is a real recorder starting later, each echo a real Add Echo.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 8.

#### Fog Chord Pad (pad, P2, XP badge)

- **Inspired by:** chord pads that stay in dub techno
- **Character:** The stab idea sustained: logon slowed with echo and wide unison.
- **DNA v2 (now):** `logon<E#10U3~12;A1200S90R3000K44`
  - Recipe: `logon slower echo 10rec unison 3 +-12c | atk 1.2s sus 90% rel 3s root G#2`
- **Sounds used:** `logon`
- **Swap candidates:** Windows: startup, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Dub delay is exactly what layer offsets plus Sound Recorder echo give: each tap is a real recorder starting later, each echo a real Add Echo.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: techno-server. Notes before stealing: 3.

#### Echo Chamber Kit (drums, P3, XP badge)

- **Inspired by:** dub techno kits
- **Character:** Soft sine kick, rim with echo, soft hats.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<<Ja0,100.80,40.300,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x3 amp 0:100,80:40,300:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP@0CP@0CP<<<Ja0,100.80,40.300,0#3F/xpstart>EE#4F/xprecycle>>>@40]#5F/balloon<E#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `xpstart`, `xprecycle`, `balloon`
- **Swap candidates:** Windows: recycle, menu, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Dub delay is exactly what layer offsets plus Sound Recorder echo give: each tap is a real recorder starting later, each echo a real Add Echo.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Spring Tank Hit (fx, P2, W3.11 badge)

- **Inspired by:** dub spring-reverb hits
- **Character:** A spring-like karplus sound with echo.
- **DNA v2 (now):** `ems_ks_spring_g3EE#8;A0R1500K55`
  - Recipe: `ems_ks_spring_g3 echo x2 8rec | atk 0ms rel 1.5s root G3`
- **Sounds used:** none; library: `ems_ks_spring_g3`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, popup, hwin; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Dub delay is exactly what layer offsets plus Sound Recorder echo give: each tap is a real recorder starting later, each echo a real Add Echo.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: techno-server. Notes before stealing: 8.

### Trance

| | |
|---|---|
| Family | Trance |
| Tempo | 132-140 BPM (progressive 126-132) |
| Keys and harmony | Minor keys, epic i-VI-III-VII progressions; anthem breakdowns |
| What producers look for in a preset | Wide, bright supersaws; 1/16 trancegate patterns; plucks with tempo delay; risers that build over 8-16 bars. |
| Sound Recorder feel | The fanfare (TADA) is the supersaw: sustain it with LOOP-OSC and spread it with U7. Draw the trancegate as an amplitude envelope; keep its steps on the 1/16 grid. |
| Sources | [Wikipedia: Trance music](https://en.wikipedia.org/wiki/Trance_music), [Wikipedia: Roland JP-8000 (supersaw, anthem trance)](https://en.wikipedia.org/wiki/Roland_JP-8000), [Perfect Circuit: Super saw history](https://www.perfectcircuit.com/signal/super-saw-history), [reFX: Nexus expansion Trance Elements](https://refx.com/nexus/expansion/trance-elements/) |

Signature sounds and roles:

- supersaw leads and chords (seven detuned saws)
- gated pads (trancegate)
- off-beat rolling basses
- delayed plucks and arps
- white-noise risers and downlifters
- big piano or string breakdowns

#### Sevenfold Anthem Lead (lead, P1, XP badge)

- **Inspired by:** Roland JP-8000 supersaw anthem trance lead
- **Character:** The fanfare's sustained middle looped, seven-voice unison at 25 cents, an octave layer over it.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP+#10U5~25/tadaxp@40[@20]@0CP@0CP@0CP@0CP>#6U1~0L40;A5R400V60K60`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 louder 10rec unison 5 +-25c / tada-xp cut before 40% cut after 20% double x4 faster 6rec unison 1 level 40% | atk 5ms rel 400ms vel 60% root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Unison over a looped fanfare slice: the beating is real recorders playing a hair apart.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: trance-connectivity. Notes before stealing: 2.

#### Sixteenth Gate Pad (pad, P1, XP badge)

- **Inspired by:** trancegate pads (rompler and VA presets)
- **Character:** Startup pad chopped by a drawn 1/16 gate at 138 BPM (108 ms steps).
- **DNA v2 (now):** `startup@25[@50]<#12U2~10Ja0,100.54,100.55,0.108,0.109,100.162,100.163,0.216,0;A0S100R200K56`
  - Recipe: `startup cut before 25% cut after 50% slower 12rec unison 2 +-10c amp 0:100,54:100,55:0,108:0,109:100,162:100,163:0,216:0 | atk 0ms sus 100% rel 200ms root G#3`
- **DNA v3 (later):** `startup@25[@50]<#12U2~10Ja0,100.54,100.55,0.108,0.109,100.162,100.163,0.216,0Wm8000;A0S100R200K56xg50`
  - Features: mine-grid sequencer/arp (x), window (start/end, random, tape length)
- **Sounds used:** `startup`
- **Swap candidates:** Windows: logon, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Eight breakpoints only: the gate holds its last open/close pair. The sequencer (v3) retriggers it on the grid.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: trance-connectivity. Notes before stealing: 6.

#### Echo Pluck 138 (pluck, P2, XP badge)

- **Inspired by:** trance pluck with dotted-8th delay
- **Character:** A trimmed default bell, echoed twice slowed; offset taps at 326 ms (dotted 8th at 138).
- **DNA v2 (now):** `default@12]#6U2~8/default@12]<E>#5L40O326Q-40/default@12]<E>#5L22O652Q40;A0D300S0R250V80K75`
  - Recipe: `default cut after 12% 6rec unison 2 +-8c / default cut after 12% slower echo faster 5rec level 40% offset 326ms pan L40 / default cut after 12% slower echo faster 5rec level 22% offset 652ms pan R40 | atk 0ms dec 300ms sus 0% rel 250ms vel 80% root D#5`
- **Sounds used:** `default`
- **Swap candidates:** Windows: xpding, ding, dingxp, chimes, balloon; library: kalimba_c4, guzheng_a3, harp_c5, drip_short
- **Sound Recorder feel:** The fanfare (TADA) is the supersaw: sustain it with LOOP-OSC and spread it with U7. Draw the trancegate as an amplitude envelope; keep its steps on the 1/16 grid.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: trance-connectivity. Notes before stealing: 3.

#### Offbeat Roller (bass, P2, XP badge)

- **Inspired by:** rolling off-beat trance bass
- **Character:** Short clipped sine loop with a click, mono so 16ths do not overlap.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<++#8Ja0,100.50,50.110,0/xpstart#2FL30;A0R40V90K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x2 louder x2 8rec amp 0:100,50:50,110:0 / xpstart 2rec fixed level 30% | atk 0ms rel 40ms vel 90% root A2`
- **DNA v3 (later):** `ringout@20[@40]@0CP@0CP@0CP<<++#8Ja0,100.50,50.110,0Nm/xpstart#2FL30;A0R40V90K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`, `xpstart`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** The fanfare (TADA) is the supersaw: sustain it with LOOP-OSC and spread it with U7. Draw the trancegate as an amplitude envelope; keep its steps on the 1/16 grid.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: trance-connectivity. Notes before stealing: 2.

#### Two Bar Noise Riser (fx, P2, XP badge)

- **Inspired by:** white-noise risers
- **Character:** Crumple noise at three speeds and a restore whoosh, staged over two bars at 138 (3.48 s).
- **DNA v2 (now):** `xprecycle<<<E#4F/xprecycle<<E#4FO1300L70/xprecycle<E#4FO2600L50/restore#4O3300;A3000S100R800`
  - Recipe: `xprecycle slower x3 echo 4rec fixed / xprecycle slower x2 echo 4rec fixed offset 1.3s level 70% / xprecycle slower echo 4rec fixed offset 2.6s level 50% / restore 4rec offset 3.3s | atk 3s sus 100% rel 800ms`
- **Sounds used:** `xprecycle`, `restore`
- **Swap candidates:** Windows: minimize, xpringin, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** v2 offsets stop at 4000 ms: two bars at 138 BPM is the longest staged v2 riser.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: trance-connectivity. Notes before stealing: 4.

#### Breakdown Grand (keys, P2, XP badge)

- **Inspired by:** emotional piano breakdowns in trance
- **Character:** The upright piano from the library is unusable in a DNA today (its name has #). Until renamed: harp plus a soft ding.
- **DNA v2 (now):** `harp_c5#10/xpding@30]#6L30T1;A0D2500S20R800K72`
  - Recipe: `harp_c5 10rec / xpding cut after 30% 6rec level 30% transpose +1 | atk 0ms dec 2.5s sus 20% rel 800ms root C5`
- **Sounds used:** `xpding`; library: `harp_c5`
- **Swap candidates:** Windows: print, default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, organ_hammond_m100_flute_c, music_box_note, piano_upright_c#4 (rename to piano_upright_cs4); in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** The fanfare (TADA) is the supersaw: sustain it with LOOP-OSC and spread it with U7. Draw the trancegate as an amplitude envelope; keep its steps on the 1/16 grid.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: trance-connectivity. Notes before stealing: 6.

#### Hands Up Stab (chord, P2, XP badge)

- **Inspired by:** hands-up / uplifting chord stabs
- **Character:** Short supersaw-like triad stab from the fanfare.
- **DNA v2 (now):** `tadaxp@10]+#12H0,4,7U2~20;A0D350S0R200K60`
  - Recipe: `tada-xp cut after 10% louder 12rec notes +0 +4 +7 unison 2 +-20c | atk 0ms dec 350ms sus 0% rel 200ms root C4`
- **DNA v3 (later):** `tadaxp@10]+#12H0,4,7U2~20Sd3;A0D350S0R200K60q0`
  - Features: scale (q), stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: chord, chordxp, xpding; library: epiano_yamaha_vibe, harp_c5
- **Sound Recorder feel:** The fanfare (TADA) is the supersaw: sustain it with LOOP-OSC and spread it with U7. Draw the trancegate as an amplitude envelope; keep its steps on the 1/16 grid.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: trance-connectivity. Notes before stealing: 2.

### Drum and bass and jungle

| | |
|---|---|
| Family | Breakbeat |
| Tempo | 160-176 BPM (jungle 160-170, DnB 172-176) |
| Keys and harmony | Minor; bass carries the harmony; often one key centre (F, E, G minor) |
| What producers look for in a preset | A reese that moves on its own; deep sub; breaks that can be chopped and pitched; atmos pads for liquid. |
| Sound Recorder feel | The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer. |
| Sources | [Wikipedia: Drum and bass](https://en.wikipedia.org/wiki/Drum_and_bass), [Wikipedia: Jungle music](https://en.wikipedia.org/wiki/Jungle_music), [Wikipedia: Amen break](https://en.wikipedia.org/wiki/Amen_break), [Attack Magazine: Reese bass (history: sampled for jungle)](https://www.attackmagazine.com/technique/video-tutorials/reese-bass/), [Native Instruments blog: Reese bass (two saws and a low-pass)](https://www.native-instruments.com/blogs/blog/reese-bass), [EDMProd: How to make jungle music](https://www.edmprod.com/how-to-make-jungle-music/) |

Signature sounds and roles:

- chopped breakbeats (the Amen and other funk breaks), time-stretched and pitched
- reese bass (two detuned saws, slow beating), and sub
- jungle: sound-system sub and dub sirens, ragga vocal stabs
- liquid: Rhodes, pads, soulful vocals
- neuro: growls

#### Ringback Twin Saw (bass, P1, XP badge)

- **Inspired by:** the reese bass (jungle, techstep, neurofunk)
- **Character:** Ringback's beating sines clipped square and dropped three octaves, two unison voices: slow phasing growl.
- **DNA v2 (now):** `xpringout@20[@40]@0CP@0CP@0CP+++<<<#16U2~18;A5S100R150K33`
  - Recipe: `xpringout cut before 20% cut after 40% double x3 louder x3 slower x3 16rec unison 2 +-18c | atk 5ms sus 100% rel 150ms root A1`
- **DNA v3 (later):** `xpringout@20[@40]@0CP@0CP@0CP+++<<<#16U2~18Nlg30;A5S100R150K33`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `xpringout`
- **Swap candidates:** Windows: ringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Different source from the preset-targets reese (error-based): this one beats by itself.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 8.

#### Sound System Sub (bass, P1, XP badge)

- **Inspired by:** jungle sub bass with a long tail
- **Character:** A pure sine sub (slowed print bell sustain) with a slight pitch-like drop drawn in level.
- **DNA v2 (now):** `print@15[@50]@0CP@0CP@0CP<<<#8Ja0,100.400,85.2000,70;A0R300V80K46`
  - Recipe: `print cut before 15% cut after 50% double x3 slower x3 8rec amp 0:100,400:85,2000:70 | atk 0ms rel 300ms vel 80% root A#2`
- **DNA v3 (later):** `print@15[@50]@0CP@0CP@0CP<<<#8Ja0,100.400,85.2000,70Nmg80;A0R300V80K46`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `print`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, balloon, xpding; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 8.

#### Neuro Growl (bass, P2, XP badge)

- **Inspired by:** neurofunk growls (Massive/Serum era)
- **Character:** The reese idea with a self-flanged comb and a drawn wobble at 1/16.
- **DNA v2 (now):** `xpringout@20[@40]@0CP@0CP@0CP+++C@2X<<<#16U2~25Ja0,100.43,40.86,100.129,40.172,100;A0R120K33`
  - Recipe: `xpringout cut before 20% cut after 40% double x3 louder x3 copy at 2% mix paste slower x3 16rec unison 2 +-25c amp 0:100,43:40,86:100,129:40,172:100 | atk 0ms rel 120ms root A1`
- **DNA v3 (later):** `xpringout@20[@40]@0CP@0CP@0CP+++C@2X<<<#16U2~25Ja0,100.43,40.86,100.129,40.172,100Nmg20;A0R120K33`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `xpringout`
- **Swap candidates:** Windows: ringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 8.

#### Break Chop Strip (drums, P1, XP badge)

- **Inspired by:** chopped breakbeats in jungle (Amen-style chops)
- **Character:** A strip of kick, snare, ghost snare and ride made from Windows sounds; v3 pads play it as chops.
- **DNA v2 (now):** `balloon<<<@40]@t30000Irecycle@t30000Ixprecycle@t30000Iprint>#16;A0R150V100K57`
  - Recipe: `balloon slower x3 cut after 40% at 30s insert recycle at 30s insert xprecycle at 30s insert print faster 16rec | atk 0ms rel 150ms vel 100% root A3`
- **DNA v3 (later):** `balloon<<<@40]@t30000Irecycle@t30000Ixprecycle@t30000Iprint>#16;A0R150V100K57k36j1k38j2k40j2t50i60k42j3e.2k46j3k51j4`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `print`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Four Insert File steps build one break strip; the pads play segments of it (kit strip, section 15).
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: breakbeat-resource. Notes before stealing: 16.

#### Liquid Atmos (pad, P2, XP badge)

- **Inspired by:** liquid DnB atmospheric pads
- **Character:** Logon and a singing bowl slowed with echo; a slow swell.
- **DNA v2 (now):** `logon<E#10U3~12/singing_bowl_long<#6L45;A1200S90R2500K44`
  - Recipe: `logon slower echo 10rec unison 3 +-12c / singing_bowl_long slower 6rec level 45% | atk 1.2s sus 90% rel 2.5s root G#2`
- **Sounds used:** `logon`; library: `singing_bowl_long`
- **Swap candidates:** Windows: startup, logoff, shutdown, notify, chord, tada; library: choir_aah, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: breakbeat-resource. Notes before stealing: 3.

#### Liquid Tine (keys, P2, XP badge)

- **Inspired by:** Rhodes in liquid DnB
- **Character:** XP ding tine with a sine body and slow chorus unison.
- **DNA v2 (now):** `xpding@25]#6U2~7/ringout@20[@40]@0CP@0CP@0CP#6L45T2;A0D2000S35R600V85K59`
  - Recipe: `xpding cut after 25% 6rec unison 2 +-7c / ringout cut before 20% cut after 40% double x3 6rec level 45% transpose +2 | atk 0ms dec 2s sus 35% rel 600ms vel 85% root B3`
- **Sounds used:** `xpding`, `ringout`
- **Swap candidates:** Windows: print, default, ding, chord; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 3.

#### Dub Siren (fx, P2, XP badge)

- **Inspired by:** jungle dub siren
- **Character:** XP ringin trill slowed, looped and bent up an octave.
- **DNA v2 (now):** `xpringin<@0CP@0CPE#8;A20S100R900B12K74`
  - Recipe: `xpringin slower double x2 echo 8rec | atk 20ms sus 100% rel 900ms bend +-12 root D5`
- **DNA v3 (later):** `xpringin<@0CP@0CPE#8Vw40,30;A20S100R900B12K74`
  - Features: tape wow/flutter/scoop
- **Sounds used:** `xpringin`
- **Swap candidates:** Windows: restore, minimize, xprecycle, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 8.

#### MC Countdown Stab (vocal, P2, W3.11 badge)

- **Inspired by:** ragga/MC vocal stabs in jungle
- **Character:** One word of a NASA countdown, echo; v3 gives each key a different word.
- **DNA v2 (now):** `nasa_apollo8_countdown_liftoff@30[@3]E#8;A2R200`
  - Recipe: `nasa_apollo8_countdown_liftoff cut before 30% cut after 3% echo 8rec | atk 2ms rel 200ms`
- **DNA v3 (later):** `nasa_apollo8_countdown_liftoff@30[@3]E#8Ws.1~.9l.01~.02Yk;A2R200`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `nasa_apollo8_countdown_liftoff`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, crowd_sing_aah_f, ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** The XP ringback tone is two sines that already beat: that is the reese motion for free. For breaks, the kit strip (v3) is literally a chopped break in one buffer.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: breakbeat-resource. Notes before stealing: 8.

### UK garage and 2-step

| | |
|---|---|
| Family | Garage |
| Tempo | 130-138 BPM, heavy swing |
| Keys and harmony | Minor 7th and 9th chords; R&B harmony; organ bass on roots |
| What producers look for in a preset | An organ bass with a click; chopped vocals that can be pitched up 2-5 semitones; stabs with swing; a punchy kit with rim. |
| Sound Recorder feel | Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in. |
| Sources | [Wikipedia: UK garage](https://en.wikipedia.org/wiki/UK_garage), [Wikipedia: 2-step garage](https://en.wikipedia.org/wiki/2-step_garage), [Native Instruments blog: UK garage music (about 130 BPM)](https://www.native-instruments.com/blogs/blog/uk-garage-music), [MusicRadar: How to make a UK garage beat (organ bass patch)](https://musicradar.com/how-to/uk-garage-tutorial), [Reason Studios: How to make UK garage (broken kick on steps 1 and 11)](https://www.reasonstudios.com/news/post/how-to-make-uk-garage) |

Signature sounds and roles:

- skippy 2-step drums (kick on 1 and the "and" of 3, shuffled hats)
- organ bass and subby "wobbly" basses (speed garage)
- chopped, pitched-up R&B vocals
- R&B chord stabs
- rimshots and claps

#### Organ Bass 2-Step (bass, P1, XP badge)

- **Inspired by:** UK garage organ bass
- **Character:** Ringout drawbar loop down two octaves with a key click.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP+<<#10H0,12/xpstart#2FL45;A0D300S60R70V90K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 louder slower x2 10rec notes +0 +12 / xpstart 2rec fixed level 45% | atk 0ms dec 300ms sus 60% rel 70ms vel 90% root A2`
- **DNA v3 (later):** `ringout@20[@40]@0CP@0CP@0CP+<<#10H0,12Nm/xpstart#2FL45;A0D300S60R70V90K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`, `xpstart`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: bass-enterprise. Notes before stealing: 2.

#### Wobbly Speed Sub (bass, P2, W3.11 badge)

- **Inspired by:** speed garage "wobble/Reese" bass
- **Character:** Sine loop down three octaves with a drawn 1/8 wobble at 135 BPM.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP++<<<#12Ja0,100.111,30.222,100.333,30.444,100;A0R100K33`
  - Recipe: `ringout cut before 20% cut after 40% double x3 louder x2 slower x3 12rec amp 0:100,111:30,222:100,333:30,444:100 | atk 0ms rel 100ms root A1`
- **DNA v3 (later):** `ringout@20[@40]@0CP@0CP@0CP++<<<#12Ja0,100.111,30.222,100.333,30.444,100Nmg30;A0R100K33`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: bass-enterprise. Notes before stealing: 12.

#### Sped-Up R&B Chop (vocal, P1, W3.11 badge)

- **Inspired by:** pitched-up chopped vocals in 2-step
- **Character:** A crowd "aah" doubled in speed (one octave up, half length) then trimmed: a bright chopped vowel.
- **DNA v2 (now):** `crowd_sing_aah_f>@10[@12]#10;A2D250S50R150K65`
  - Recipe: `crowd_sing_aah_f faster cut before 10% cut after 12% 10rec | atk 2ms dec 250ms sus 50% rel 150ms root F4`
- **DNA v3 (later):** `crowd_sing_aah_f>@10[@12]#10Ws.05~.6l.03~.06Yk;A2D250S50R150K65`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `crowd_sing_aah_f`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: bass-enterprise. Notes before stealing: 10.

#### Two-Step Minor Stab (stab, P2, XP badge)

- **Inspired by:** R&B chord stabs in UKG
- **Character:** XP notify bell cut short, minor-9 stack, echo.
- **DNA v2 (now):** `xpnotify@8]E#10H0,3,7,14;A0D300S0R200V80K70`
  - Recipe: `xpnotify cut after 8% echo 10rec notes +0 +3 +7 +14 | atk 0ms dec 300ms sus 0% rel 200ms vel 80% root A#4`
- **DNA v3 (later):** `xpnotify@8]E#10H0,3,7,14Sd4;A0D300S0R200V80K70q1`
  - Features: scale (q), stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `xpnotify`
- **Swap candidates:** Windows: chord, chordxp, tada, tadaxp, xpding, default; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: bass-enterprise. Notes before stealing: 2.

#### Skip Shuffle Kit (drums, P1, XP badge)

- **Inspired by:** 2-step garage kits (swung hats, rim, clap)
- **Character:** Pop kick, rim, echo clap, short hats; swing on the grid.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/recycle>>@50]E#4F/xprecycle>>>@40]#5F/xpstart>#4;R200V90xs62k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Garage Organ Stab (keys, P2, XP badge)

- **Inspired by:** garage house organ stab
- **Character:** Short chord-xp stab with a clipped drawbar loop.
- **DNA v2 (now):** `chordxp@10]#8/ringout@20[@40]@0CP@0CP+#6H0,12L40T-2;A0D250S0R100K55`
  - Recipe: `chord-xp cut after 10% 8rec / ringout cut before 20% cut after 40% double x2 louder 6rec notes +0 +12 level 40% transpose -2 | atk 0ms dec 250ms sus 0% rel 100ms root G3`
- **Sounds used:** `chordxp`, `ringout`
- **Swap candidates:** Windows: xpding, print, default, ding, chord; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Pitched-up vocal chops are what Sound Recorder's Increase Speed does: a real chipmunk from a real speed-up. Leave the artefacts in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: bass-enterprise. Notes before stealing: 3.

### Dubstep (UK and brostep)

| | |
|---|---|
| Family | Bass music |
| Tempo | 138-142 BPM, half-time feel |
| Keys and harmony | Minor, Phrygian; often E or F minor; sparse |
| What producers look for in a preset | Wobbles locked to tempo (1/4, 1/8, triplets), a clean sub, growls with movement, impacts. |
| Sound Recorder feel | Draw the wobble in the amplitude envelope; use macro N to change the repeat count of the buffer's last step (the rhythm of the chop). |
| Sources | [Wikipedia: Dubstep](https://en.wikipedia.org/wiki/Dubstep), [Native Instruments blog: Massive, past presets and future (dubstep wavetables)](https://blog.native-instruments.com/massive-past-presets-future/) |

Signature sounds and roles:

- sub bass and LFO wobble bass (UK), growl/"talking" basses (brostep)
- half-time drums: snare on beat 3
- dark pads and dub sirens
- vocal samples, risers and impacts

#### Quarter Wobble (bass, P1, XP badge)

- **Inspired by:** UK dubstep LFO wobble bass (2006-2009)
- **Character:** Clipped beating sine three octaves down, drawn 1/8 wobble at 140 BPM; macro 2 doubles the rate.
- **DNA v2 (now):** `xpringout@20[@40]@0CP@0CP@0CP+++<<<#16U2~10Ja0,100.107,15.214,100.321,15.428,100.535,15.642,100;A0R120m21Z100,50m2=0K33`
  - Recipe: `xpringout cut before 20% cut after 40% double x3 louder x3 slower x3 16rec unison 2 +-10c amp 0:100,107:15,214:100,321:15,428:100,535:15,642:100 | atk 0ms rel 120ms m2 L1 envtime 100-50 m2 0% root A1`
- **Sounds used:** `xpringout`
- **Swap candidates:** Windows: ringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Macro 2 scales envelope time: 100 % = 1/8, 50 % = 1/16.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: bass-enterprise. Notes before stealing: 8.

#### Error Growl (bass, P1, XP badge)

- **Inspired by:** brostep growl / talking bass
- **Character:** XP error bell clipped hard, self-flanged twice, down three octaves; vowel-like comb motion.
- **DNA v2 (now):** `error@5]+++C@2XC@4X<<<@0CP@0CP#16U2~20;A0R100K51`
  - Recipe: `error cut after 5% louder x3 copy at 2% mix paste copy at 4% mix paste slower x3 double x2 16rec unison 2 +-20c | atk 0ms rel 100ms root D#3`
- **DNA v3 (later):** `error@5]+++C@2XC@4X<<<@0CP@0CP#16U2~20Nmg15;A0R100K51`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `error`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, balloon, xpding; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Draw the wobble in the amplitude envelope; use macro N to change the repeat count of the buffer's last step (the rhythm of the chop).
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: bass-enterprise. Notes before stealing: 8.

#### Half-Step Sub (sub, P2, XP badge)

- **Inspired by:** clean dubstep sub
- **Character:** Pure sine sub from the print bell sustain.
- **DNA v2 (now):** `print@15[@50]@0CP@0CP@0CP<<<#8;A5S100R150K46`
  - Recipe: `print cut before 15% cut after 50% double x3 slower x3 8rec | atk 5ms sus 100% rel 150ms root A#2`
- **DNA v3 (later):** `print@15[@50]@0CP@0CP@0CP<<<#8Nm;A5S100R150K46`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `print`
- **Swap candidates:** Windows: ringout, xpringout, batlow; library: ems_mains_hum, organ_pedal_25
- **Sound Recorder feel:** Draw the wobble in the amplitude envelope; use macro N to change the repeat count of the buffer's last step (the rhythm of the chop).
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: bass-enterprise. Notes before stealing: 8.

#### Impact Doom (fx, P2, XP badge)

- **Inspired by:** dubstep impacts and downlifters
- **Character:** Critical stop two octaves down with echo, a balloon boom and a falling minimize.
- **DNA v2 (now):** `critstop<<E#6/balloon<<<#4FL80/minimize<<#4FL60;A0R1500K24`
  - Recipe: `critstop slower x2 echo 6rec / balloon slower x3 4rec fixed level 80% / minimize slower x2 4rec fixed level 60% | atk 0ms rel 1.5s root C1`
- **Sounds used:** `critstop`, `balloon`, `minimize`
- **Swap candidates:** Windows: restore, xprecycle, xpringin, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Draw the wobble in the amplitude envelope; use macro N to change the repeat count of the buffer's last step (the rhythm of the chop).
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: bass-enterprise. Notes before stealing: 4.

#### Dark Warehouse Pad (pad, P2, XP badge)

- **Inspired by:** dark dubstep pads
- **Character:** Battery-low tones slowed with echo and unison.
- **DNA v2 (now):** `batlow<E@0CP#10U3~12;A800S90R2000K31`
  - Recipe: `batlow slower echo double 10rec unison 3 +-12c | atk 800ms sus 90% rel 2s root G1`
- **Sounds used:** `batlow`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, chord; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Draw the wobble in the amplitude envelope; use macro N to change the repeat count of the buffer's last step (the rhythm of the chop).
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: bass-enterprise. Notes before stealing: 3.

#### Half-Time Kit (drums, P2, XP badge)

- **Inspired by:** dubstep kits
- **Character:** Deep kick, big echo snare (on 3), short hats.
- **DNA v2 (now):** `ringout@20[@40]@0CP<<<+Ja0,100.80,50.400,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double slower x3 louder amp 0:100,80:50,400:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP<<<+Ja0,100.80,50.400,0#3F/recycle@20]+E#4F/xprecycle>>>@40]#5F/critstop<@10]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `recycle`, `xprecycle`, `critstop`
- **Swap candidates:** Windows: balloon, menu, xpstart, start, infobar, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Draw the wobble in the amplitude envelope; use macro N to change the repeat count of the buffer's last step (the rhythm of the chop).
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Hip-hop (boom bap)

| | |
|---|---|
| Family | Hip-hop |
| Tempo | 84-96 BPM, swung 16ths |
| Keys and harmony | Minor and jazz-derived; loops from soul and jazz records; chopped chords |
| What producers look for in a preset | Dusty drums that knock, chops with grit and swing, 12-bit colour, horn stabs. |
| Sound Recorder feel | Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up. |
| Sources | [Wikipedia: Boom bap](https://en.wikipedia.org/wiki/Boom_bap), [Wikipedia: E-mu SP-1200 (12-bit, 26.04 kHz)](https://en.wikipedia.org/wiki/E-mu_SP-1200), [Rossum Electro-Music: SP-1200 (aliasing from authentic pitch shifting)](https://www.rossum-electro.com/products/sp-1200/), [LANDR blog: SP-1200, the sampler that changed hip-hop](https://blog.landr.com/sp-1200), [FACT: 15 samplers that shaped modern music](https://factmag.com/2016/09/15/15-samplers-that-shaped-modern-music), [Wikipedia: Akai MPC](https://en.wikipedia.org/wiki/Akai_MPC) |

Signature sounds and roles:

- hard sampled drums from breaks, 12-bit grit (SP-1200, MPC60)
- chopped soul/jazz samples, often slowed or sped up
- filtered bass (low-passed sample) or upright bass
- scratches, horn stabs, vocal phrases

#### Dusty Crate Kit (drums, P1, XP badge)

- **Inspired by:** SP-1200/MPC60 boom-bap kits
- **Character:** Crunchy kick, snare with echo crack, 8-bit hats.
- **DNA v2 (now):** `ding<<<@35]#16F;A0R150V90`
  - Recipe: `ding slower x3 cut after 35% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ding<<<@35]><#3F/recycle>@30]+><E#4F/ringin>>@12]><#5F/xpstart><#4;R200V90xs60k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `ding`, `recycle`, `ringin`, `xpstart`
- **Swap candidates:** Windows: balloon, xprecycle, menu, start, infobar, critstop; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Soul Loop Chop (keys, P1, W3.11 badge)

- **Inspired by:** chopped soul keys sample
- **Character:** Library e-piano sample, decimated (><), slight wow.
- **DNA v2 (now):** `epiano_yamaha_vibe><#10;A0D1500S40R300K60`
  - Recipe: `epiano_yamaha_vibe faster slower 10rec | atk 0ms dec 1.5s sus 40% rel 300ms root C4`
- **DNA v3 (later):** `epiano_yamaha_vibe><#10Yd5l6kVw8,5;A0D1500S40R300K60`
  - Features: per-voice randomness, tape wow/flutter/scoop
- **Sounds used:** none; library: `epiano_yamaha_vibe`
- **Swap candidates:** Windows: xpding, print, default, ding, chord, ringout; library: epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note, epiano_bell_c3; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 10.

#### Horn Stab Crate (stab, P2, W3.11 badge)

- **Inspired by:** sampled horn stabs
- **Character:** The 3.1 fanfare trimmed, decimated, with a brass layer.
- **DNA v2 (now):** `tada@15]><+#10/trumpet_sus_c4@5]#6L40;A0D300S0R150K60`
  - Recipe: `tada cut after 15% faster slower louder 10rec / trumpet_sus_c4 cut after 5% 6rec level 40% | atk 0ms dec 300ms sus 0% rel 150ms root C4`
- **Sounds used:** `tada`; library: `trumpet_sus_c4`
- **Swap candidates:** Windows: chord, chordxp, tadaxp, xpding, default, critstop; library: crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 6.

#### Upright Thump (bass, P2, W3.11 badge)

- **Inspired by:** upright/filtered bass in boom bap
- **Character:** Contrabass pizz, decimated, short.
- **DNA v2 (now):** `contrabass_pizz_e1><#10;A0D600S20R150K28`
  - Recipe: `contrabass_pizz_e1 faster slower 10rec | atk 0ms dec 600ms sus 20% rel 150ms root E1`
- **DNA v3 (later):** `contrabass_pizz_e1><#10Nm;A0D600S20R150K28`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** none; library: `contrabass_pizz_e1`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, balloon, xpding; library: tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 10.

#### Desk Scratch (fx, P2, XP badge)

- **Inspired by:** turntable scratch FX
- **Character:** A reversed crumple and a speed-swept restore; bend +-12.
- **DNA v2 (now):** `recycle>R#6F/restore>#6;A0R80B12`
  - Recipe: `recycle faster reverse 6rec fixed / restore faster 6rec | atk 0ms rel 80ms bend +-12`
- **DNA v3 (later):** `recycle>R#6FNlg30/restore>#6Nlg30;A0R80B12`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `recycle`, `restore`
- **Swap candidates:** Windows: minimize, xprecycle, xpringin, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 6.

#### Lecture Hook (vocal, P2, W3.11 badge)

- **Inspired by:** vocal phrase hooks (spoken samples)
- **Character:** A line from a 1982 computing lecture, decimated: a found-sound hook.
- **DNA v2 (now):** `hopper_1982_information_flow@20[@10]><#8;A2R200`
  - Recipe: `hopper_1982_information_flow cut before 20% cut after 10% faster slower 8rec | atk 2ms rel 200ms`
- **DNA v3 (later):** `hopper_1982_information_flow@20[@10]><#8Ws.1~.8l.02~.05Yk;A2R200`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `hopper_1982_information_flow`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, crowd_sing_aah_f, ems_704_vowel_a3, prelinger_office_courtesy, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Sound Recorder IS a 1990s PC sampler: 8-bit 11 kHz sources and Increase/Decrease Speed round trips give SP-1200-like aliasing for free. Do not clean it up.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 8.

### Lo-fi hip-hop

| | |
|---|---|
| Family | Hip-hop |
| Tempo | 70-90 BPM, lazy swing |
| Keys and harmony | Jazz chords: maj7, min9, 7#9; ii-V; often Db, Eb, F |
| What producers look for in a preset | Warm keys with tape wow, vinyl noise, soft kits, and a "study" mood with rain. |
| Sound Recorder feel | Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed. |
| Sources | [Wikipedia: Lo-fi hip hop](https://en.wikipedia.org/wiki/Lo-fi_hip_hop) |

Signature sounds and roles:

- detuned, wobbly keys (e-piano, felt piano)
- vinyl crackle and tape hiss
- soft, side-chained drums with low-passed kicks
- jazz guitar or vibes samples
- rain, room and nature ambiences

#### Rainy Study Keys (keys, P1, W3.11 badge)

- **Inspired by:** lo-fi detuned e-piano
- **Character:** E-piano vibe sample, wow and per-key detune; a rain bed rides on top.
- **DNA v2 (now):** `epiano_yamaha_vibe#12U2~8/rain_on_window#4FL15;A10D2500S40R700V70K60`
  - Recipe: `epiano_yamaha_vibe 12rec unison 2 +-8c / rain_on_window 4rec fixed level 15% | atk 10ms dec 2.5s sus 40% rel 700ms vel 70% root C4`
- **DNA v3 (later):** `epiano_yamaha_vibe#12U2~8Yd6l6kVw9,5s15,60/rain_on_window#4FL15;A10D2500S40R700V70K60`
  - Features: per-voice randomness, tape wow/flutter/scoop
- **Sounds used:** none; library: `epiano_yamaha_vibe`, `rain_on_window`
- **Swap candidates:** Windows: xpding, print, default, ding, chord, ringout; library: epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 4.

#### Felt Ding Piano (keys, P2, XP badge)

- **Inspired by:** felt piano in lo-fi
- **Character:** XP ding slowed with echo and wow: a soft felt hammer.
- **DNA v2 (now):** `xpding@30]<E#10U2~6;A5D2200S25R800V70K47`
  - Recipe: `xpding cut after 30% slower echo 10rec unison 2 +-6c | atk 5ms dec 2.2s sus 25% rel 800ms vel 70% root B2`
- **DNA v3 (later):** `xpding@30]<E#10U2~6Vw6,6;A5D2200S25R800V70K47`
  - Features: tape wow/flutter/scoop
- **Sounds used:** `xpding`
- **Swap candidates:** Windows: print, default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 5.

#### Crackle Paper (texture, P1, XP badge)

- **Inspired by:** vinyl crackle bed
- **Character:** Paper crumple at speed, echoed: crackle that never loops audibly.
- **DNA v2 (now):** `recycle>>E#4F/xprecycle>>>E#4FL60;A100S100R500`
  - Recipe: `recycle faster x2 echo 4rec fixed / xprecycle faster x3 echo 4rec fixed level 60% | atk 100ms sus 100% rel 500ms`
- **Sounds used:** `recycle`, `xprecycle`
- **Swap candidates:** Windows: startup; library: rain_on_window, creek_loop, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: beat-management. Notes before stealing: 4.

#### Window Rain Room (texture, P2, W3.11 badge)

- **Inspired by:** rain and room ambience
- **Character:** Window rain slowed with echo.
- **DNA v2 (now):** `rain_on_window<E#4F;A2000S100R3000`
  - Recipe: `rain_on_window slower echo 4rec fixed | atk 2s sus 100% rel 3s`
- **Sounds used:** none; library: `rain_on_window`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: creek_loop, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 4.

#### Study Vibes (bell, P2, W3.11 badge)

- **Inspired by:** vibraphone samples in lo-fi
- **Character:** Vibraphone with slow tremolo drawn in level.
- **DNA v2 (now):** `vibraphone_c_low#10Ja0,100.250,70.500,100.750,70.1000,100;A0R900K48`
  - Recipe: `vibraphone_c_low 10rec amp 0:100,250:70,500:100,750:70,1000:100 | atk 0ms rel 900ms root C3`
- **Sounds used:** none; library: `vibraphone_c_low`
- **Swap candidates:** Windows: ding, chimes, print, default, error, exclaim; library: wine_glass_medium_ping, crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6, music_box_note, epiano_bell_c3; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 10.

#### Bedroom Tape Kit (drums, P2, XP badge)

- **Inspired by:** lo-fi kits (soft kicks, rim, brushes)
- **Character:** Soft kick, rim, brush-like crumple.
- **DNA v2 (now):** `balloon<<<@45]<>#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% slower faster 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]<>#3F/recycle>@35]E#4F/xprecycle>>>@40]<>#5F/xpstart#4;R250V80xs60k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Tape wow (v3 V) on a real Sound Recorder playback is the most honest lo-fi there is; the library's rain and room sounds make the bed.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Trap

| | |
|---|---|
| Family | Hip-hop |
| Tempo | 130-170 BPM in half-time (felt as 65-85) |
| Keys and harmony | Minor, Phrygian and harmonic minor; dark bells and plucks; 808 carries the bass line |
| What producers look for in a preset | An 808 that is in tune, long, with glide and saturation; bell/flute melodies; hats that roll. |
| Sound Recorder feel | Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono. |
| Sources | [Wikipedia: Trap music](https://en.wikipedia.org/wiki/Trap_music), [Wikipedia: Roland TR-808](https://en.wikipedia.org/wiki/Roland_TR-808) |

Signature sounds and roles:

- long, tuned 808 kick-bass with glide and distortion
- hi-hat rolls (1/16, 1/32, triplets)
- dark bells, plucks and flute loops
- claps/snares on 3
- vocal tags

#### Long Boom Glide (bass, P1, XP badge)

- **Inspired by:** trap 808 bass with glide
- **Character:** Balloon pop three octaves down, clipped, long tail; v3 glide.
- **DNA v2 (now):** `balloon<<<+#8/ringout@20[@40]@0CP@0CP@0CP<<<#6L60;A0D3000S40R300K45`
  - Recipe: `balloon slower x3 louder 8rec / ringout cut before 20% cut after 40% double x3 slower x3 6rec level 60% | atk 0ms dec 3s sus 40% rel 300ms root A2`
- **DNA v3 (later):** `balloon<<<+#8Nmg70/ringout@20[@40]@0CP@0CP@0CP<<<#6L60Nmg70;A0D3000S40R300K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `balloon`, `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 6.

#### Dark Ding Bell (bell, P1, XP badge)

- **Inspired by:** trap bell melodies
- **Character:** XP error bell, harmonic minor colour, echo.
- **DNA v2 (now):** `error@5]E#10/default@10]<#6L40;A0D1500S10R600K87`
  - Recipe: `error cut after 5% echo 10rec / default cut after 10% slower 6rec level 40% | atk 0ms dec 1.5s sus 10% rel 600ms root D#6`
- **DNA v3 (later):** `error@5]E#10/default@10]<#6L40;A0D1500S10R600K87q7`
  - Features: scale (q)
- **Sounds used:** `error`, `default`
- **Swap candidates:** Windows: ding, chimes, print, exclaim, xpnotify; library: wine_glass_medium_ping, crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6, music_box_note; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: beat-management. Notes before stealing: 6.

#### Flute Loop Lead (lead, P2, XP badge)

- **Inspired by:** trap flute loops
- **Character:** Library flute with breath from paper noise.
- **DNA v2 (now):** `flute_vib_c5#12/recycle>>@8]#4FL25;A30R250K72`
  - Recipe: `flute_vib_c5 12rec / recycle faster x2 cut after 8% 4rec fixed level 25% | atk 30ms rel 250ms root C5`
- **DNA v3 (later):** `flute_vib_c5#12Vs15,50/recycle>>@8]#4FL25;A30R250K72`
  - Features: tape wow/flutter/scoop
- **Sounds used:** `recycle`; library: `flute_vib_c5`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 4.

#### Roll Hat (drums, P1, XP badge)

- **Inspired by:** trap hi-hat (rolls)
- **Character:** One very short crumple hat for rolls: play 1/32 from the grid.
- **DNA v2 (now):** `xprecycle>>>@40]#16F;A0R30V100`
  - Recipe: `xprecycle faster x3 cut after 40% 16rec fixed | atk 0ms rel 30ms vel 100%`
- **DNA v3 (later):** `xprecycle>>>@40]#16F;A0R30V100xd32g40`
  - Features: mine-grid sequencer/arp (x)
- **Sounds used:** `xprecycle`
- **Swap candidates:** Windows: balloon, recycle, menu, xpstart, start, infobar; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: beat-management. Notes before stealing: 16.

#### Half Time 808 Kit (drums, P2, XP badge)

- **Inspired by:** trap kits
- **Character:** Boom kick, clap with echo, roll hats, rim.
- **DNA v2 (now):** `balloon<<<+#16F;A0R150V90`
  - Recipe: `balloon slower x3 louder 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<+#3F/recycle>>@50]E#4F/xprecycle>>>@40]#5F/xpstart>#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Countdown Tag (vocal, P2, W3.11 badge)

- **Inspired by:** producer tags
- **Character:** An airport PA phrase decimated and echoed.
- **DNA v2 (now):** `airport_gatwick_pa_announcements@30[@8]><E#8;A0R300`
  - Recipe: `airport_gatwick_pa_announcements cut before 30% cut after 8% faster slower echo 8rec | atk 0ms rel 300ms`
- **Sounds used:** none; library: `airport_gatwick_pa_announcements`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, crowd_sing_aah_f, ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 8.

#### Night Choir Pad (pad, P2, W3.11 badge)

- **Inspired by:** dark choir pads in trap
- **Character:** Choir aah slowed, harmonic minor root.
- **DNA v2 (now):** `choir_aah<E#10U2~8;A600S90R1800K45`
  - Recipe: `choir_aah slower echo 10rec unison 2 +-8c | atk 600ms sus 90% rel 1.8s root A2`
- **Sounds used:** none; library: `choir_aah`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, chord; library: singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Make the 808 a slowed Windows boom: balloon<<< is an 808 tail. Glide is v3 mono.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 5.

### Synthwave and outrun

| | |
|---|---|
| Family | Retro |
| Tempo | 80-118 BPM (outrun 100-118) |
| Keys and harmony | Minor (A, D, E minor); i-VI-III-VII; arpeggiated chords |
| What producers look for in a preset | Chorus-wide pads, a gated snare, a tight 16th bass arp, a soaring lead. |
| Sound Recorder feel | Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus. |
| Sources | [Wikipedia: Synthwave](https://en.wikipedia.org/wiki/Synthwave), [Mode Audio: Synthwave, 5 production essentials](https://modeaudio.com/magazine/synthwave-5-production-essentials), [EDMProd: How to make synthwave](https://www.edmprod.com/how-to-make-synthwave/), [MusicTech: dreamy synths and retro drums (synthwave guide)](https://www.musictech.com/guides/essential-guide/produce-dreamy-synths-retro-drums-like-com-truise/) |

Signature sounds and roles:

- chorused poly pads (Juno-style)
- gated-reverb snare
- 16th-note arpeggiated bass
- bright brass and sync leads
- FM bells and e-pianos
- sidechain pump

#### Night Drive Chorus Pad (pad, P1, XP badge)

- **Inspired by:** Juno-style chorused synthwave pad
- **Character:** Logon slowed, wide unison, pan width.
- **DNA v2 (now):** `logon<@15[#10U3~16/logon<@15[#6U2~10Q60L50;A700S90R1500K44`
  - Recipe: `logon slower cut before 15% 10rec unison 3 +-16c / logon slower cut before 15% 6rec unison 2 +-10c pan R60 level 50% | atk 700ms sus 90% rel 1.5s root G#2`
- **DNA v3 (later):** `logon<@15[#10U3~16Sw.8/logon<@15[#6U2~10Q60L50;A700S90R1500K44`
  - Features: stack (round-robin, strum, diatonic chords, groups)
- **Sounds used:** `logon`
- **Swap candidates:** Windows: startup, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 3.

#### Gated Neon Snare (snare, P1, XP badge)

- **Inspired by:** 80s gated-reverb snare
- **Character:** Crumple snare with three echoes, cut hard at 220 ms.
- **DNA v2 (now):** `recycle>@40]+EEE#12FJa0,100.200,90.220,0;A0R10V90`
  - Recipe: `recycle faster cut after 40% louder echo x3 12rec fixed amp 0:100,200:90,220:0 | atk 0ms rel 10ms vel 90%`
- **Sounds used:** `recycle`
- **Swap candidates:** Windows: xprecycle; library: key_spacebar, em_stamp_a
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 12.

#### Sixteenth Highway Bass (bass, P1, W3.11 badge)

- **Inspired by:** synthwave 16th arpeggiated bass
- **Character:** A short clipped buzz, octave down, mono; v3 arp from the grid.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<+#8Ja0,100.80,40.110,0;A0R40V80K47`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 slower louder 8rec amp 0:100,80:40,110:0 | atk 0ms rel 40ms vel 80% root B2`
- **DNA v3 (later):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<+#8Ja0,100.80,40.110,0Nm;A0R40V80K47q1xg55n2o1`
  - Features: mine-grid sequencer/arp (x), scale (q), voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: retro-display. Notes before stealing: 8.

#### Chrome Brass Lead (lead, P2, XP badge)

- **Inspired by:** synthwave brass lead
- **Character:** Fanfare loop with a slow attack and wide pan.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP#10U3~18;A60R350B2K60`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 10rec unison 3 +-18c | atk 60ms rel 350ms bend +-2 root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 3.

#### FM Sunset Bell (keys, P2, XP badge)

- **Inspired by:** FM e-piano/bell in synthwave
- **Character:** Print sine bell and XP ding together.
- **DNA v2 (now):** `print#6/xpding@25]#6L60T-1;A0D2200S20R700K82`
  - Recipe: `print 6rec / xpding cut after 25% 6rec level 60% transpose -1 | atk 0ms dec 2.2s sus 20% rel 700ms root A#5`
- **Sounds used:** `print`, `xpding`
- **Swap candidates:** Windows: default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 6.

#### Laser Grid Sweep (fx, P2, XP badge)

- **Inspired by:** synthwave FX sweeps
- **Character:** Restore whoosh reversed and echoed into a downward minimize.
- **DNA v2 (now):** `restore<RE#6/minimize<#6;A200R900`
  - Recipe: `restore slower reverse echo 6rec / minimize slower 6rec | atk 200ms rel 900ms`
- **Sounds used:** `restore`, `minimize`
- **Swap candidates:** Windows: xprecycle, xpringin, popup, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 6.

#### Gated Cassette Kit (drums, P2, XP badge)

- **Inspired by:** LinnDrum/808 synthwave kits
- **Character:** Pop kick, gated snare, hats, tom from hwfail.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/recycle>@40]+EEEJa0,100.200,90.220,0#4F/xprecycle>>>@40]#5F/hwfail<@30]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `hwfail`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Echo plus a drawn envelope that cuts it is a gated reverb. Wide U and pan are the chorus.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Chillwave

| | |
|---|---|
| Family | Retro |
| Tempo | 80-110 BPM |
| Keys and harmony | Major 7th and add9; hazy, nostalgic; often a semitone off concert |
| What producers look for in a preset | Warm, washed-out keys and pads that wobble; reverb-soaked vocal textures. |
| Sound Recorder feel | Slow, echo and wow everything; prefer the XP startup family for the "summer" colour. |
| Sources | [Wikipedia: Chillwave](https://en.wikipedia.org/wiki/Chillwave) |

Signature sounds and roles:

- heavily filtered, washed-out synths and samples
- tape saturation and wow
- reverb-drenched vocals
- simple drum machine beats
- sunny, lo-fi 80s pop colour

#### Beach Tape Pad (pad, P1, XP badge)

- **Inspired by:** chillwave washed pads
- **Character:** Startup sustained with echo and wow.
- **DNA v2 (now):** `startup@20[@60]<E#10U2~12;A800S95R2500K56`
  - Recipe: `startup cut before 20% cut after 60% slower echo 10rec unison 2 +-12c | atk 800ms sus 95% rel 2.5s root G#3`
- **DNA v3 (later):** `startup@20[@60]<E#10U2~12Vw12,4;A800S95R2500K56`
  - Features: tape wow/flutter/scoop
- **Sounds used:** `startup`
- **Swap candidates:** Windows: logon, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Slow, echo and wow everything; prefer the XP startup family for the "summer" colour.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: retro-display. Notes before stealing: 5.

#### Faded Postcard Keys (keys, P2, XP badge)

- **Inspired by:** chillwave keys
- **Character:** XP ding plus default bell slowed, wow.
- **DNA v2 (now):** `xpding@30]<E#8/default@20]<<#6L40T-4;A20D2000S40R900K47`
  - Recipe: `xpding cut after 30% slower echo 8rec / default cut after 20% slower x2 6rec level 40% transpose -4 | atk 20ms dec 2s sus 40% rel 900ms root B2`
- **DNA v3 (later):** `xpding@30]<E#8Vw10,5/default@20]<<#6L40T-4Vw10,5;A20D2000S40R900K47`
  - Features: tape wow/flutter/scoop
- **Sounds used:** `xpding`, `default`
- **Swap candidates:** Windows: print, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Slow, echo and wow everything; prefer the XP startup family for the "summer" colour.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: retro-display. Notes before stealing: 6.

#### Haze Choir (vocal, P2, W3.11 badge)

- **Inspired by:** reverb-soaked vocal textures
- **Character:** Choir aah slowed with echo.
- **DNA v2 (now):** `choir_aah<E#10U2~10;A600S90R2500K45`
  - Recipe: `choir_aah slower echo 10rec unison 2 +-10c | atk 600ms sus 90% rel 2.5s root A2`
- **Sounds used:** none; library: `choir_aah`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: crowd_sing_aah_f, ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Slow, echo and wow everything; prefer the XP startup family for the "summer" colour.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: retro-display. Notes before stealing: 5.

#### Sun Glare Lead (lead, P2, XP badge)

- **Inspired by:** filtered lead in chillwave
- **Character:** A slowed print sine, wide.
- **DNA v2 (now):** `print@10[@60]@0CP@0CP#10U2~14;A40R500K82`
  - Recipe: `print cut before 10% cut after 60% double x2 10rec unison 2 +-14c | atk 40ms rel 500ms root A#5`
- **DNA v3 (later):** `print@10[@60]@0CP@0CP#10U2~14Nlg60Vw8,5;A40R500K82`
  - Features: tape wow/flutter/scoop, voice mode (mono/legato/glide)
- **Sounds used:** `print`
- **Swap candidates:** Windows: tadaxp, tada, ringout, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Slow, echo and wow everything; prefer the XP startup family for the "summer" colour.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: retro-display. Notes before stealing: 5.

#### Sun-Faded Kit (drums, P3, XP badge)

- **Inspired by:** simple drum machines in chillwave
- **Character:** Soft kick, snare with long echo, soft hats.
- **DNA v2 (now):** `balloon<<<@45]<>#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% slower faster 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]<>#3F/recycle>@35]EE#4F/xprecycle>>>@40]#5F/xpstart#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Slow, echo and wow everything; prefer the XP startup family for the "summer" colour.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Ambient

| | |
|---|---|
| Family | Ambient |
| Tempo | free, or 60-90 BPM |
| Keys and harmony | Major/lydian or static modal; long single chords |
| What producers look for in a preset | Pads that evolve on their own; long releases; motion without rhythm; field recordings. |
| Sound Recorder feel | Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud. |
| Sources | [Wikipedia: Ambient music](https://en.wikipedia.org/wiki/Ambient_music) |

Signature sounds and roles:

- evolving pads and swells
- bells and glass
- field recordings (water, birds, wind)
- tape loops of different lengths (phasing)
- granular clouds

#### Airport Loop Phasing (pad, P1, XP badge)

- **Inspired by:** tape-loop ambient (loops of different lengths)
- **Character:** Three slowed slices of logon of different lengths at offsets: they drift apart like tape loops.
- **DNA v2 (now):** `logon<@10[@60]E#5/logon<@30[@40]E#5O700Q-40/logon<@50[@50]E#5O1300Q40;A900S90R3000K44`
  - Recipe: `logon slower cut before 10% cut after 60% echo 5rec / logon slower cut before 30% cut after 40% echo 5rec offset 700ms pan L40 / logon slower cut before 50% cut after 50% echo 5rec offset 1.3s pan R40 | atk 900ms sus 90% rel 3s root G#2`
- **Sounds used:** `logon`
- **Swap candidates:** Windows: startup, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: screen-saver. Notes before stealing: 5.

#### Startup Cloud (pad, P1, XP badge)

- **Inspired by:** granular ambient pad
- **Character:** v2: startup slowed twice; v3: a frozen-free grain cloud.
- **DNA v2 (now):** `startup<<#12U2~8;A1500S90R4000K44`
  - Recipe: `startup slower x2 12rec unison 2 +-8c | atk 1.5s sus 90% rel 4s root G#2`
- **DNA v3 (later):** `startup<<#12U2~8Gp.4j.15z80~160n40c15s.2v6w.6;A1500S90R4000K44`
  - Features: grains
- **Sounds used:** `startup`
- **Swap candidates:** Windows: logon, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 grains: ~100/s sample-exact on 3.11; XP after phase 6. Pack: screen-saver. Notes before stealing: 6.

#### Singing Bowl Halo (pad, P2, W3.11 badge)

- **Inspired by:** bowl drones
- **Character:** Singing bowl slowed with PRE-VERB.
- **DNA v2 (now):** `singing_bowl_long<RER#8U2~6;A400S100R4000`
  - Recipe: `singing_bowl_long slower reverse echo reverse 8rec unison 2 +-6c | atk 400ms sus 100% rel 4s`
- **Sounds used:** none; library: `singing_bowl_long`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, chord; library: choir_aah, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 4.

#### Glass Garden Bell (bell, P2, W3.11 badge)

- **Inspired by:** ambient glass bells
- **Character:** Wine glass ping plus slowed chimes reversed under it.
- **DNA v2 (now):** `wine_glass_medium_ping#8/chimes<R#6L40;A0D4000S0R3000K67`
  - Recipe: `wine_glass_medium_ping 8rec / chimes slower reverse 6rec level 40% | atk 0ms dec 4s sus 0% rel 3s root G4`
- **Sounds used:** `chimes`; library: `wine_glass_medium_ping`
- **Swap candidates:** Windows: ding, print, default, error, exclaim, xpnotify; library: crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6, music_box_note; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 6.

#### Creek Bed (texture, P2, W3.11 badge)

- **Inspired by:** field-recording beds
- **Character:** Creek loop slowed.
- **DNA v2 (now):** `creek_loop<#4F;A2000S100R3000`
  - Recipe: `creek_loop slower 4rec fixed | atk 2s sus 100% rel 3s`
- **Sounds used:** none; library: `creek_loop`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: rain_on_window, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 4.

#### Thrush Morning (texture, P2, W3.11 badge)

- **Inspired by:** birdsong in ambient
- **Character:** Hermit thrush, with echo.
- **DNA v2 (now):** `bird_hermit_thrushE#4`
  - Recipe: `bird_hermit_thrush echo 4rec`
- **Sounds used:** none; library: `bird_hermit_thrush`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: rain_on_window, creek_loop, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 4.

#### Rain Clock Kit (drums, P3, XP badge)

- **Inspired by:** ambient percussion (clicks, drips, wood)
- **Character:** Drip kick, glass snare, crumple hat, relay rim.
- **DNA v2 (now):** `drop_single_a<<#16F;A0R150V90`
  - Recipe: `drop_single_a slower x2 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `drop_single_a<<#3F/glass_tap#4F/xprecycle>>>@30]#5F/ems_relay_tiny#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `xprecycle`; library: `drop_single_a`, `glass_tap`, `ems_relay_tiny`
- **Swap candidates:** Windows: balloon, recycle, menu, xpstart, start, infobar; library: em_relay_click_a, key_mechanical_hard, floppy_seek_clunk; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Loops of different lengths are layers of different lengths: each recorder ends on its own. Grains (v3) let the XP startup become an endless cloud.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Drone

| | |
|---|---|
| Family | Ambient |
| Tempo | none |
| Keys and harmony | One pitch or one chord; just intonation colour; fifths |
| What producers look for in a preset | Infinite sustain, slow beating, overtones that move. |
| Sound Recorder feel | LOOP-OSC builds 30 s buffers; held notes play to the end. Machines (hum, motors) are drones. |
| Sources | [Wikipedia: Drone music](https://en.wikipedia.org/wiki/Drone_music) |

Signature sounds and roles:

- sustained tones for minutes
- slow beating between close pitches
- organ, bowed metal, tanpura
- noise and hum beds

#### Mains Hum Fifth (drone, P1, W3.11 badge)

- **Inspired by:** electrical hum drones
- **Character:** Mains hum and motor drone a fifth apart.
- **DNA v2 (now):** `ems_mains_hum@0CP@0CP#8/ems_motor_drone_c3#8H0,7;A3000S100R5000K48`
  - Recipe: `ems_mains_hum double x2 8rec / ems_motor_drone_c3 8rec notes +0 +7 | atk 3s sus 100% rel 5s root C3`
- **Sounds used:** none; library: `ems_mains_hum`, `ems_motor_drone_c3`
- **Swap candidates:** Windows: ringout, startup, shutdown, batlow; library: em_hum_tube_loop, organ_pedal_25, singing_bowl_long
- **Sound Recorder feel:** LOOP-OSC builds 30 s buffers; held notes play to the end. Machines (hum, motors) are drones.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 4.

#### Thirty Second Ring (drone, P1, W3.11 badge)

- **Inspired by:** sustained beating sines
- **Character:** Ringout looped to 30 s, three octaves, slow beating.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP@0CP@0CP@0CP@0CP#12H0,12,-12U2~3;A4000S100R6000K69`
  - Recipe: `ringout cut before 20% cut after 40% double x7 12rec notes +0 +12 -12 unison 2 +-3c | atk 4s sus 100% rel 6s root A4`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: startup, shutdown, batlow; library: ems_mains_hum, em_hum_tube_loop, organ_pedal_25, singing_bowl_long
- **Sound Recorder feel:** The longest buffer allowed (30 s); the beating is the source's own.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: screen-saver. Notes before stealing: 2.

#### Bowed Glass Drone (drone, P2, W3.11 badge)

- **Inspired by:** bowed metal/glass drones
- **Character:** Wine glass singing slowed with echo.
- **DNA v2 (now):** `wine_glass_singing_half_full<E@0CP@0CP#10U2~4;A3000S100R5000`
  - Recipe: `wine_glass_singing_half_full slower echo double x2 10rec unison 2 +-4c | atk 3s sus 100% rel 5s`
- **Sounds used:** none; library: `wine_glass_singing_half_full`
- **Swap candidates:** Windows: ringout, startup, shutdown, batlow; library: ems_mains_hum, em_hum_tube_loop, organ_pedal_25, singing_bowl_long
- **Sound Recorder feel:** LOOP-OSC builds 30 s buffers; held notes play to the end. Machines (hum, motors) are drones.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 5.

#### Organ Pedal Ground (drone, P2, W3.11 badge)

- **Inspired by:** church organ drones
- **Character:** Pedal organ with a fifth.
- **DNA v2 (now):** `organ_pedal_25#10H0,7;A1500S100R4000`
  - Recipe: `organ_pedal_25 10rec notes +0 +7 | atk 1.5s sus 100% rel 4s`
- **Sounds used:** none; library: `organ_pedal_25`
- **Swap candidates:** Windows: ringout, startup, shutdown, batlow; library: ems_mains_hum, em_hum_tube_loop, singing_bowl_long
- **Sound Recorder feel:** LOOP-OSC builds 30 s buffers; held notes play to the end. Machines (hum, motors) are drones.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 5.

#### Tanpura Ringout (drone, P2, W3.11 badge)

- **Inspired by:** tanpura-like drone (3.11 sources only)
- **Character:** Ringout loop at root, fifth and octave, slow beating.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP@0CP@0CP@0CP#12H0,7,12U2~2;A2000S100R5000K69`
  - Recipe: `ringout cut before 20% cut after 40% double x6 12rec notes +0 +7 +12 unison 2 +-2c | atk 2s sus 100% rel 5s root A4`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: startup, shutdown, batlow; library: ems_mains_hum, em_hum_tube_loop, organ_pedal_25, singing_bowl_long
- **Sound Recorder feel:** LOOP-OSC builds 30 s buffers; held notes play to the end. Machines (hum, motors) are drones.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: screen-saver. Notes before stealing: 2.

#### Server Room Air (texture, P2, W3.11 badge)

- **Inspired by:** machine-room drones
- **Character:** Hard disk spin and switch-room drone slowed.
- **DNA v2 (now):** `hdd_conner_spin<#6F/emh_switchroom_drone<#6;A3000S100R4000`
  - Recipe: `hdd_conner_spin slower 6rec fixed / emh_switchroom_drone slower 6rec | atk 3s sus 100% rel 4s`
- **Sounds used:** none; library: `hdd_conner_spin`, `emh_switchroom_drone`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: rain_on_window, creek_loop, office_ambience_01, insect_crickets_mojave
- **Sound Recorder feel:** LOOP-OSC builds 30 s buffers; held notes play to the end. Machines (hum, motors) are drones.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 6.

### IDM and glitch

| | |
|---|---|
| Family | Experimental |
| Tempo | 80-170 BPM, often irregular |
| Keys and harmony | Free; detuned bells, microtonal colour; melody from FM and toy sounds |
| What producers look for in a preset | Glitches that are musical, stutters in time, unusual percussion, broken bells. |
| Sound Recorder feel | Sound Recorder's editing commands are glitch tools: repeated @0CP stutters, Insert File splices, Delete Before/After cuts. Show them; the strip display shows the edit. |
| Sources | [Wikipedia: Intelligent dance music](https://en.wikipedia.org/wiki/Intelligent_dance_music), [Wikipedia: Glitch (music)](https://en.wikipedia.org/wiki/Glitch_(music)) |

Signature sounds and roles:

- hyper-edited drums (micro-chopped breaks)
- clicks, skips and digital errors
- detuned bells, music boxes, toy sounds
- granular stutters
- FM and bit-crushed tones

#### Stutter Copy Paste (fx, P1, XP badge)

- **Inspired by:** glitch stutter
- **Character:** A 40 ms slice of tada doubled five times: a buzzing stutter.
- **DNA v2 (now):** `tadaxp@30[@4]@0CP@0CP@0CP@0CP@0CP#10;A0R60K60`
  - Recipe: `tada-xp cut before 30% cut after 4% double x5 10rec | atk 0ms rel 60ms root C4`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, popup, hwin; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** A stutter made of Copy and Paste Insert, nothing else.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: diagnostics. Notes before stealing: 10.

#### Broken Music Box (bell, P1, W3.11 badge)

- **Inspired by:** detuned music box (IDM)
- **Character:** Music box with per-key random detune and a decimated echo.
- **DNA v2 (now):** `music_box_note><E#10;A0D3000S0R1500K84`
  - Recipe: `music_box_note faster slower echo 10rec | atk 0ms dec 3s sus 0% rel 1.5s root C6`
- **DNA v3 (later):** `music_box_note><E#10Yd25l10k;A0D3000S0R1500K84`
  - Features: per-voice randomness
- **Sounds used:** none; library: `music_box_note`
- **Swap candidates:** Windows: ding, chimes, print, default, error, exclaim; library: wine_glass_medium_ping, crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** Sound Recorder's editing commands are glitch tools: repeated @0CP stutters, Insert File splices, Delete Before/After cuts. Show them; the strip display shows the edit.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: diagnostics. Notes before stealing: 10.

#### Splice Break (drums, P2, XP badge)

- **Inspired by:** micro-edited drums
- **Character:** Insert File splices of clicks and pops into one buffer.
- **DNA v2 (now):** `balloon<<@20]Imenu@t40Ixpstart@t90Ipopup@t140Irecycle#12;A0R100K57`
  - Recipe: `balloon slower x2 cut after 20% insert menu at 40ms insert xpstart at 90ms insert popup at 140ms insert recycle 12rec | atk 0ms rel 100ms root A3`
- **Sounds used:** `balloon`, `menu`, `xpstart`, `popup`, `recycle`
- **Swap candidates:** Windows: xprecycle, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Sound Recorder's editing commands are glitch tools: repeated @0CP stutters, Insert File splices, Delete Before/After cuts. Show them; the strip display shows the edit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: diagnostics. Notes before stealing: 12.

#### Floppy Seek Perc (perc, P2, W3.11 badge)

- **Inspired by:** computer-noise percussion
- **Character:** Floppy seek and mouse clicks pitched.
- **DNA v2 (now):** `floppy_seek_clunk#8/mouse_click@40]#8;A0R80`
  - Recipe: `floppy_seek_clunk 8rec / mouse_click cut after 40% 8rec | atk 0ms rel 80ms`
- **Sounds used:** none; library: `floppy_seek_clunk`, `mouse_click`
- **Swap candidates:** Windows: menu, xpstart, infobar, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, bubble_pop_a, glass_tap, key_mechanical_hard; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** Sound Recorder's editing commands are glitch tools: repeated @0CP stutters, Insert File splices, Delete Before/After cuts. Show them; the strip display shows the edit.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: diagnostics. Notes before stealing: 8.

#### Grain Error Pad (pad, P2, XP badge)

- **Inspired by:** granular glitch pads
- **Character:** Error bell slowed; v3 sprays grains of it.
- **DNA v2 (now):** `error<<E#12U2~10;A500S90R2000K63`
  - Recipe: `error slower x2 echo 12rec unison 2 +-10c | atk 500ms sus 90% rel 2s root D#4`
- **DNA v3 (later):** `error<<E#12U2~10Gp.5j.4z20~60n80c40o20e3v8w.9;A500S90R2000K63`
  - Features: grains
- **Sounds used:** `error`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, chord; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Sound Recorder's editing commands are glitch tools: repeated @0CP stutters, Insert File splices, Delete Before/After cuts. Show them; the strip display shows the edit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 grains: ~100/s sample-exact on 3.11; XP after phase 6. Pack: diagnostics. Notes before stealing: 6.

#### Modem Lead (lead, P2, W3.11 badge)

- **Inspired by:** digital, FSK-like leads
- **Character:** Bell 103 FSK tone as a lead.
- **DNA v2 (now):** `ems_fsk_bell103_orig@20[@20]@0CP@0CP@0CP#10;A5R200`
  - Recipe: `ems_fsk_bell103_orig cut before 20% cut after 20% double x3 10rec | atk 5ms rel 200ms`
- **Sounds used:** none; library: `ems_fsk_bell103_orig`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3, em_modem1200; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Sound Recorder's editing commands are glitch tools: repeated @0CP stutters, Insert File splices, Delete Before/After cuts. Show them; the strip display shows the edit.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: diagnostics. Notes before stealing: 10.

### Breakbeat and big beat

| | |
|---|---|
| Family | Breakbeat |
| Tempo | 120-140 BPM |
| Keys and harmony | Blues and rock riffs, minor pentatonic; acid lines; one-chord riffs |
| What producers look for in a preset | Fat breaks, distorted riffs, sirens, shout hits, big risers. |
| Sound Recorder feel | Clip steps (+) are the distortion; the 3.x fanfare is the brass. |
| Sources | [Wikipedia: Breakbeat](https://en.wikipedia.org/wiki/Breakbeat), [Wikipedia: Big beat](https://en.wikipedia.org/wiki/Big_beat) |

Signature sounds and roles:

- big, compressed funk breaks
- acid basses and distorted riffs
- rock guitar and brass stabs
- sirens, vocal shouts
- massive build-ups and drops

#### Stadium Riff Stab (stab, P1, XP badge)

- **Inspired by:** big beat brass/guitar stab
- **Character:** Fanfare blast clipped hard with a crumple attack.
- **DNA v2 (now):** `tadaxp@15]+++#10H0,12/recycle>@15]#4FL50;A0D300S0R150K60`
  - Recipe: `tada-xp cut after 15% louder x3 10rec notes +0 +12 / recycle faster cut after 15% 4rec fixed level 50% | atk 0ms dec 300ms sus 0% rel 150ms root C4`
- **Sounds used:** `tadaxp`, `recycle`
- **Swap candidates:** Windows: chord, chordxp, tada, xpding, default, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Clip steps (+) are the distortion; the 3.x fanfare is the brass.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 4.

#### Fuzz Riff Bass (bass, P2, XP badge)

- **Inspired by:** distorted big beat riff bass
- **Character:** The default bell buzz clipped, octave down.
- **DNA v2 (now):** `default@3]<<++++@0CP@0CP@0CP#10;A0R100K51`
  - Recipe: `default cut after 3% slower x2 louder x4 double x3 10rec | atk 0ms rel 100ms root D#3`
- **DNA v3 (later):** `default@3]<<++++@0CP@0CP@0CP#10Nm;A0R100K51`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `default`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, balloon, xpding; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Clip steps (+) are the distortion; the 3.x fanfare is the brass.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 10.

#### Acid Rock Line (bass, P2, XP badge)

- **Inspired by:** acid lines in big beat
- **Character:** Clipped default bell attack, mono slide.
- **DNA v2 (now):** `default@3]<<+++#8Ja0,100.40,50.250,20;A0R60V100K51`
  - Recipe: `default cut after 3% slower x2 louder x3 8rec amp 0:100,40:50,250:20 | atk 0ms rel 60ms vel 100% root D#3`
- **DNA v3 (later):** `default@3]<<+++#8Ja0,100.40,50.250,20Nlg40;A0R60V100K51`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `default`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, balloon, xpding; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Clip steps (+) are the distortion; the 3.x fanfare is the brass.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 8.

#### Block Party Siren (fx, P2, W3.11 badge)

- **Inspired by:** siren FX
- **Character:** Ringin trill looped, bent.
- **DNA v2 (now):** `ringin<@0CP@0CPE#8;A10S100R500B7K80`
  - Recipe: `ringin slower double x2 echo 8rec | atk 10ms sus 100% rel 500ms bend +-7 root G#5`
- **Sounds used:** `ringin`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, popup, hwin; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Clip steps (+) are the distortion; the 3.x fanfare is the brass.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 8.

#### Big Break Kit (drums, P2, XP badge)

- **Inspired by:** compressed funk breaks
- **Character:** Kick, clipped snare, crumple ride.
- **DNA v2 (now):** `balloon<<<++#16F;A0R150V90`
  - Recipe: `balloon slower x3 louder x2 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<++#3F/recycle>@30]++E#4F/xprecycle>>@50]#5F/critstop<@10]+#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `critstop`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Clip steps (+) are the distortion; the 3.x fanfare is the brass.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Megaphone Shout (vocal, P2, W3.11 badge)

- **Inspired by:** shouted vocal hooks in big beat
- **Character:** An airport PA word clipped hard.
- **DNA v2 (now):** `airport_gatwick_pa_announcements@40[@4]+++#8;A0R200`
  - Recipe: `airport_gatwick_pa_announcements cut before 40% cut after 4% louder x3 8rec | atk 0ms rel 200ms`
- **DNA v3 (later):** `airport_gatwick_pa_announcements@40[@4]+++#8Ws.1~.9l.01~.03Yk;A0R200`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `airport_gatwick_pa_announcements`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, crowd_sing_aah_f, ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Clip steps (+) are the distortion; the 3.x fanfare is the brass.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: breakbeat-resource. Notes before stealing: 8.

### Electro

| | |
|---|---|
| Family | Breakbeat |
| Tempo | 120-135 BPM |
| Keys and harmony | Minor, often one key centre; robotic, staccato |
| What producers look for in a preset | 808 kit, robotic voice, staccato bass, zaps. |
| Sound Recorder feel | Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc. |
| Sources | [Wikipedia: Electro (music)](https://en.wikipedia.org/wiki/Electro_(music)), [Wikipedia: Roland TR-808](https://en.wikipedia.org/wiki/Roland_TR-808) |

Signature sounds and roles:

- TR-808 drums (snappy snare, toms, cowbell)
- vocoder voices
- staccato synth bass
- sci-fi zaps and arps

#### Robot Workgroup Voice (vocal, P1, W3.11 badge)

- **Inspired by:** vocoder robot voice
- **Character:** The 1961 vowel synthesis plus a buzz carrier.
- **DNA v2 (now):** `ems_704_vowel_a3@0CP#8/ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#6L35T-2;A10R200K57`
  - Recipe: `ems_704_vowel_a3 double 8rec / ringout cut before 150ms cut after 20ms cut after 20% double x9 6rec level 35% transpose -2 | atk 10ms rel 200ms root A3`
- **Sounds used:** `ringout`; library: `ems_704_vowel_a3`
- **Swap candidates:** Windows: notify, xpnotify; library: choir_aah, crowd_sing_aah_f, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: breakbeat-resource. Notes before stealing: 6.

#### Staccato Electro Bass (bass, P2, W3.11 badge)

- **Inspired by:** electro staccato bass
- **Character:** Short clipped buzz.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP<+#10Ja0,100.60,0;A0R30K47`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 slower louder 10rec amp 0:100,60:0 | atk 0ms rel 30ms root B2`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 10.

#### Zap Gun (fx, P2, XP badge)

- **Inspired by:** electro zaps
- **Character:** Popup blip with bend.
- **DNA v2 (now):** `popup<E#8;A0R100B24K80`
  - Recipe: `popup slower echo 8rec | atk 0ms rel 100ms bend +-24 root G#5`
- **Sounds used:** `popup`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, hwin, hwout; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 8.

#### Breaker Box Kit (drums, P1, XP badge)

- **Inspired by:** TR-808 electro kits
- **Character:** Boom kick, snappy snare, cowbell from default.
- **DNA v2 (now):** `ringout@20[@40]@0CP<<<Ja0,100.100,60.700,0#16F;A0R150V90`
  - Recipe: `ringout cut before 20% cut after 40% double slower x3 amp 0:100,100:60,700:0 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ringout@20[@40]@0CP<<<Ja0,100.100,60.700,0#3F/recycle>@30]+#4F/xprecycle>>>@40]#5F/default>@8]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ringout`, `recycle`, `xprecycle`, `default`
- **Swap candidates:** Windows: balloon, menu, xpstart, start, infobar, critstop; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Freestyle Square (lead, P2, W3.11 badge)

- **Inspired by:** electro/freestyle square lead
- **Character:** Buzz with octave stack and short glide.
- **DNA v2 (now):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#8H0,12;A0R120K59`
  - Recipe: `ringout cut before 150ms cut after 20ms cut after 20% double x9 8rec notes +0 +12 | atk 0ms rel 120ms root B3`
- **DNA v3 (later):** `ringout@t150[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#8H0,12Nlg30;A0R120K59`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: tadaxp, tada, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: breakbeat-resource. Notes before stealing: 4.

#### Breaker Orchestra Hit (stab, P2, W3.11 badge)

- **Inspired by:** orchestra hits in electro
- **Character:** The 3.1 fanfare blast with the chord strike.
- **DNA v2 (now):** `tada@15]+#8H0,12/chord@8]#6L60T5;A0D300S0R200K60`
  - Recipe: `tada cut after 15% louder 8rec notes +0 +12 / chord cut after 8% 6rec level 60% transpose +5 | atk 0ms dec 300ms sus 0% rel 200ms root C4`
- **Sounds used:** `tada`, `chord`
- **Swap candidates:** Windows: chordxp, tadaxp, xpding, default, critstop; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Use Microsoft Sam (in our XP image) for the robot voice once it is rendered to the disc.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 4.

### Downtempo and trip-hop

| | |
|---|---|
| Family | Downtempo |
| Tempo | 70-100 BPM |
| Keys and harmony | Minor; film-noir harmony; Dorian |
| What producers look for in a preset | Cinematic strings, dusty Rhodes, dub bass, a noir lead. |
| Sound Recorder feel | Slow down, add echo, keep the vinyl crumble in. |
| Sources | [Wikipedia: Trip hop](https://en.wikipedia.org/wiki/Trip_hop), [Wikipedia: Downtempo](https://en.wikipedia.org/wiki/Downtempo) |

Signature sounds and roles:

- slow, heavy breakbeats with vinyl noise
- cinematic strings and Rhodes
- dub bass
- scratches, theremin-like leads
- smoky vocal samples

#### Noir Strings (strings, P1, W3.11 badge)

- **Inspired by:** cinematic sampled strings in trip-hop
- **Character:** Cello and violin sections slowed with echo.
- **DNA v2 (now):** `cello_section_sus_c3<E#8/violin_section_sus_c4<#6L60;A400S90R1500K36`
  - Recipe: `cello_section_sus_c3 slower echo 8rec / violin_section_sus_c4 slower 6rec level 60% | atk 400ms sus 90% rel 1.5s root C2`
- **Sounds used:** none; library: `cello_section_sus_c3`, `violin_section_sus_c4`
- **Swap candidates:** Windows: startup, logon, logoff; library: erhu_d3
- **Sound Recorder feel:** Slow down, add echo, keep the vinyl crumble in.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: beat-management. Notes before stealing: 6.

#### Ether Wire Lead (lead, P1, XP badge)

- **Inspired by:** theremin-like lead
- **Character:** Print sine sustained with wide bend and v3 glide.
- **DNA v2 (now):** `print@15[@50]@0CP@0CP@0CP#8;A80R400B12K82`
  - Recipe: `print cut before 15% cut after 50% double x3 8rec | atk 80ms rel 400ms bend +-12 root A#5`
- **DNA v3 (later):** `print@15[@50]@0CP@0CP@0CP#8Nlg120Vw25,55;A80R400B12K82`
  - Features: tape wow/flutter/scoop, voice mode (mono/legato/glide)
- **Sounds used:** `print`
- **Swap candidates:** Windows: tadaxp, tada, ringout, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Slow down, add echo, keep the vinyl crumble in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 8.

#### Smoke Tine (keys, P2, XP badge)

- **Inspired by:** dusty Rhodes
- **Character:** XP ding slowed, decimated.
- **DNA v2 (now):** `xpding@25]<><E#10;A0D2200S30R700K47`
  - Recipe: `xpding cut after 25% slower faster slower echo 10rec | atk 0ms dec 2.2s sus 30% rel 700ms root B2`
- **Sounds used:** `xpding`
- **Swap candidates:** Windows: print, default, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Slow down, add echo, keep the vinyl crumble in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: beat-management. Notes before stealing: 10.

#### Dub Cellar Bass (bass, P2, W3.11 badge)

- **Inspired by:** dub bass
- **Character:** Sine sub with a soft attack.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<#8;A20R250K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x2 8rec | atk 20ms rel 250ms root A2`
- **DNA v3 (later):** `ringout@20[@40]@0CP@0CP@0CP<<#8Nm;A20R250K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Slow down, add echo, keep the vinyl crumble in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: beat-management. Notes before stealing: 8.

#### Slow Dust Kit (drums, P2, XP badge)

- **Inspired by:** trip-hop break kits
- **Character:** Heavy kick, snare with echo, crumple hats.
- **DNA v2 (now):** `balloon<<<@45]><#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% faster slower 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]><#3F/recycle@25]+E#4F/xprecycle>>>@40]><#5F/xpstart<#4;R250V90xs55k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpstart`
- **Swap candidates:** Windows: menu, start, infobar, critstop, ding, ringin; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Slow down, add echo, keep the vinyl crumble in.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### Footwork and juke

| | |
|---|---|
| Family | Bass music |
| Tempo | ~160 BPM |
| Keys and harmony | Free; chopped samples set the key; 808 kicks played chromatically |
| What producers look for in a preset | A kick that can be played chromatically, tight claps, chopped vocal loops. |
| Sound Recorder feel | Kicks pitched by sample rate (no pitch-shifter): exactly what each recorder does. |
| Sources | [Wikipedia: Footwork (genre) (about 160 BPM, TR-808)](https://en.wikipedia.org/wiki/Footwork_(genre)), [MusicRadar / Computer Music: juke-style pitched 808 kick pattern](https://www.musicradar.com/tuition/tech/how-to-make-a-juke-style-pitched-808-kick-pattern-554083), [DJ TechTools: Footwork, what is it and how do you make it](https://djtechtools.com/2014/04/24/footwork-what-is-it-and-how-do-you-make-it/) |

Signature sounds and roles:

- pitched 808 kicks as melody
- triplet and polyrhythmic hats and claps
- repeated vocal phrases chopped short
- sparse sub stabs

#### Chromatic Kick Bass (bass, P1, XP badge)

- **Inspired by:** pitched 808 kicks in juke/footwork
- **Character:** Balloon boom playable chromatically, short.
- **DNA v2 (now):** `balloon<<<@60]#16;A0R100V100K45`
  - Recipe: `balloon slower x3 cut after 60% 16rec | atk 0ms rel 100ms vel 100% root A2`
- **Sounds used:** `balloon`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Every note is the same file at another rate, as on a sampler.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 16.

#### Battle Phrase Loop (vocal, P1, W3.11 badge)

- **Inspired by:** repeated vocal phrases in footwork
- **Character:** A two-word phrase repeated with copy/paste.
- **DNA v2 (now):** `prelinger_world_at_your_call@30[@3]@0CP@0CP#8;A0R100`
  - Recipe: `prelinger_world_at_your_call cut before 30% cut after 3% double x2 8rec | atk 0ms rel 100ms`
- **DNA v3 (later):** `prelinger_world_at_your_call@30[@3]@0CP@0CP#8Ws.1~.8l.02~.04Yk;A0R100`
  - Features: per-voice randomness, window (start/end, random, tape length)
- **Sounds used:** none; library: `prelinger_world_at_your_call`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: choir_aah, crowd_sing_aah_f, ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Kicks pitched by sample rate (no pitch-shifter): exactly what each recorder does.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: breakbeat-resource. Notes before stealing: 8.

#### Triplet Clap (perc, P2, XP badge)

- **Inspired by:** footwork claps
- **Character:** Echo clap, tight.
- **DNA v2 (now):** `recycle>>@50]E#16F;A0R60`
  - Recipe: `recycle faster x2 cut after 50% echo 16rec fixed | atk 0ms rel 60ms`
- **DNA v3 (later):** `recycle>>@50]E#16F;A0R60xd16tg40`
  - Features: mine-grid sequencer/arp (x)
- **Sounds used:** `recycle`
- **Swap candidates:** Windows: menu, xpstart, infobar, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** Kicks pitched by sample rate (no pitch-shifter): exactly what each recorder does.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 16.

#### Battle Circle Kit (drums, P2, XP badge)

- **Inspired by:** footwork kits (808 kick, rapid hats, claps, triplet toms)
- **Character:** Short boom kick, echo clap, tiny hats, mallet toms for triplet rolls.
- **DNA v2 (now):** `balloon<<<@60]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 60% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@60]#3F/recycle>>@50]E#4F/xprecycle>>>@40]#5F/xpding<@30]#4;R150V100xd16tk36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k), mine-grid sequencer/arp (x)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `xpding`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Kicks pitched by sample rate (no pitch-shifter): exactly what each recorder does.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Sub Stab Juke (stab, P2, W3.11 badge)

- **Inspired by:** sparse sub stabs in juke
- **Character:** A 200 ms sine sub stab, played chromatically.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<@20]#12;A0R60V100K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x2 cut after 20% 12rec | atk 0ms rel 60ms vel 100% root A2`
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: chord, chordxp, tada, tadaxp, xpding, default; library: trumpet_sus_c4, crowd_sing_aah_f, ems_ringmod_relay_bell
- **Sound Recorder feel:** Kicks pitched by sample rate (no pitch-shifter): exactly what each recorder does.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 12.

#### Night Bus Pad (pad, P2, XP badge)

- **Inspired by:** soulful pad samples under footwork
- **Character:** Logoff slowed one octave, short echo.
- **DNA v2 (now):** `logoff<E#10U2~8;A400S90R1200K51`
  - Recipe: `logoff slower echo 10rec unison 2 +-8c | atk 400ms sus 90% rel 1.2s root D#3`
- **Sounds used:** `logoff`
- **Swap candidates:** Windows: startup, logon, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Kicks pitched by sample rate (no pitch-shifter): exactly what each recorder does.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: breakbeat-resource. Notes before stealing: 5.

### Hyperpop

| | |
|---|---|
| Family | Pop |
| Tempo | 140-170 BPM (or half-time) |
| Keys and harmony | Bright major or pop minor; exaggerated pop progressions |
| What producers look for in a preset | Glossy plastic sounds, pitched vocal stacks, distorted supersaws, bubbly perc. |
| Sound Recorder feel | Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces. |
| Sources | [Wikipedia: Hyperpop](https://en.wikipedia.org/wiki/Hyperpop), [MusicRadar: extreme hyperpop textures](https://musicradar.com/tutorials/music-production-tutorials/how-to-craft-extreme-hyperpop-textures-to-make-sophie-style-tunes), [Native Instruments blog: Hyperpop](https://blog.native-instruments.com/hyperpop) |

Signature sounds and roles:

- pitched-up, formant-shifted vocals
- distorted supersaws and 808s
- glossy, plasticky percussion (metallic, bubbly)
- trance and chiptune references
- sudden FX and glitches

#### Plastic Sevenfold (lead, P1, XP badge)

- **Inspired by:** distorted supersaw in hyperpop
- **Character:** Fanfare loop, octave up, clipped.
- **DNA v2 (now):** `tadaxp@40[@20]@0CP@0CP@0CP@0CP>+++#12U4~30;A0R200K72`
  - Recipe: `tada-xp cut before 40% cut after 20% double x4 faster louder x3 12rec unison 4 +-30c | atk 0ms rel 200ms root C5`
- **Sounds used:** `tadaxp`
- **Swap candidates:** Windows: tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: diagnostics. Notes before stealing: 3.

#### Helium Choir Stack (vocal, P1, W3.11 badge)

- **Inspired by:** pitched-up vocal stacks
- **Character:** Crowd "aah" and choir sped up, stacked +12.
- **DNA v2 (now):** `crowd_sing_aah_f>#8H0,12/choir_aah>#6L60T-4;A10R300K65`
  - Recipe: `crowd_sing_aah_f faster 8rec notes +0 +12 / choir_aah faster 6rec level 60% transpose -4 | atk 10ms rel 300ms root F4`
- **Sounds used:** none; library: `crowd_sing_aah_f`, `choir_aah`
- **Swap candidates:** Windows: notify, xpnotify, ringout; library: ems_704_vowel_a3, prelinger_office_courtesy, hopper_1982_information_flow, nasa_apollo8_countdown_liftoff, airport_gatwick_pa_announcements; in our XP image, not yet on the disc: Microsoft Sam renders (library/sam_phrases.txt, 130 phrases)
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: diagnostics. Notes before stealing: 4.

#### Bubble Wrap Perc (perc, P2, XP badge)

- **Inspired by:** glossy bubble percussion
- **Character:** Bubble pops and balloon pitched.
- **DNA v2 (now):** `bubble_pop_a#8/balloon>#8;A0R80K93`
  - Recipe: `bubble_pop_a 8rec / balloon faster 8rec | atk 0ms rel 80ms root A6`
- **Sounds used:** `balloon`; library: `bubble_pop_a`
- **Swap candidates:** Windows: menu, xpstart, infobar, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, glass_tap, soap_bubbles_pop; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: diagnostics. Notes before stealing: 8.

#### Clipped Boom (bass, P2, XP badge)

- **Inspired by:** distorted 808
- **Character:** Balloon boom clipped hard.
- **DNA v2 (now):** `balloon<<<++++#12;A0D2000S40R200K45`
  - Recipe: `balloon slower x3 louder x4 12rec | atk 0ms dec 2s sus 40% rel 200ms root A2`
- **DNA v3 (later):** `balloon<<<++++#12Nmg50;A0D2000S40R200K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `balloon`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: diagnostics. Notes before stealing: 12.

#### Glossy Clatter Kit (drums, P2, XP badge)

- **Inspired by:** hyperpop kits (metallic, bubbly, distorted)
- **Character:** Clipped boom kick, glass-tap snare, bubble hats, glass clink perc.
- **DNA v2 (now):** `balloon<<<+++#16F;A0R150V90`
  - Recipe: `balloon slower x3 louder x3 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<+++#3F/glass_tap>+#4F/bubble_pop_a>>#5F/glass_clink#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`; library: `glass_tap`, `bubble_pop_a`, `glass_clink`
- **Swap candidates:** Windows: recycle, xprecycle, menu, xpstart, start, infobar; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Shatter Transition (fx, P2, W3.11 badge)

- **Inspired by:** hyperpop glitch transitions
- **Character:** A glass hit stuttered by copy/paste and sped up.
- **DNA v2 (now):** `wine_glass_hit_hard@10]@0CP@0CP@0CP@0CP>#8;A0R200`
  - Recipe: `wine_glass_hit_hard cut after 10% double x4 faster 8rec | atk 0ms rel 200ms`
- **Sounds used:** none; library: `wine_glass_hit_hard`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, popup, hwin; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: diagnostics. Notes before stealing: 8.

#### Candy Trance Pad (pad, P2, XP badge)

- **Inspired by:** trance-pad references in hyperpop
- **Character:** Startup sped up an octave, wide, bright.
- **DNA v2 (now):** `startup@20[@50]>#12U3~20;A200S90R900K80`
  - Recipe: `startup cut before 20% cut after 50% faster 12rec unison 3 +-20c | atk 200ms sus 90% rel 900ms root G#5`
- **Sounds used:** `startup`
- **Swap candidates:** Windows: logon, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Speed up (>) is the formant shift; the Aero/bubble sounds give the glossy plastic surfaces.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: diagnostics. Notes before stealing: 4.

### City pop

| | |
|---|---|
| Family | Pop |
| Tempo | 95-120 BPM |
| Keys and harmony | Major 7, 9, 11, 13; ii-V-I; modulations; jazz-funk harmony |
| What producers look for in a preset | Glassy FM e-piano and bass with chorus; tight brass; lush strings. |
| Sound Recorder feel | XP's glassy bells are FM-like already: print, default and xpding are the e-piano. |
| Sources | [Wikipedia: City pop](https://en.wikipedia.org/wiki/City_pop), [Lavengood (2019): What makes it sound '80s? The Yamaha DX7 electric piano sound](https://meganlavengood.com/wp-content/uploads/2019/09/Lavengood-2019-%E2%80%9CWhat-Makes-It-Sound-%E2%80%9980s%E2%80%9D-The-Yamaha-DX7-Electr.pdf), [Reverb Machine: Exploring the Yamaha DX7, part 2: songs](https://reverbmachine.com/blog/exploring-the-yamaha-dx7-pt2/), [Yamaha Synth 50th: Japanese pop music and Yamaha synthesizers](https://th.yamaha.com/th/musical-instruments/keyboards/explore/synth-50th/anecdotes/012.html) |

Signature sounds and roles:

- DX7-style FM e-piano (bright, glassy, chorused)
- slap and FM basses
- brass sections
- clean funk guitar
- lush strings
- gated drum machines

#### Shiny Tine Plaza (keys, P1, XP badge)

- **Inspired by:** DX7 FM e-piano in city pop
- **Character:** Default bell attack, print sine body, chorus unison.
- **DNA v2 (now):** `default@10]#6U2~6Q-20/print@5[@60]#6U2~6Q20L60T5;A0D2500S25R600V85K75`
  - Recipe: `default cut after 10% 6rec unison 2 +-6c pan L20 / print cut before 5% cut after 60% 6rec unison 2 +-6c pan R20 level 60% transpose +5 | atk 0ms dec 2.5s sus 25% rel 600ms vel 85% root D#5`
- **Sounds used:** `default`, `print`
- **Swap candidates:** Windows: xpding, ding, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, harp_c5, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 3.

#### Tokyo Slap (bass, P1, XP badge)

- **Inspired by:** FM slap bass
- **Character:** XP ding clipped two octaves down with balloon thumb.
- **DNA v2 (now):** `xpding@20]<<+++#8/balloon<#4FL50;A0D350S40R80V95K35`
  - Recipe: `xpding cut after 20% slower x2 louder x3 8rec / balloon slower 4rec fixed level 50% | atk 0ms dec 350ms sus 40% rel 80ms vel 95% root B1`
- **DNA v3 (later):** `xpding@20]<<+++#8Nm/balloon<#4FL50;A0D350S40R80V95K35`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `xpding`, `balloon`
- **Swap candidates:** Windows: ringout, xpringout, batlow, critstop, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: retro-display. Notes before stealing: 4.

#### Highrise Brass (brass, P2, XP badge)

- **Inspired by:** city pop brass section
- **Character:** Trumpet and trombone with fanfare attack.
- **DNA v2 (now):** `trumpet_sus_c4#6/trombone_sus_c3#6/tadaxp@8]#4L40;A20R200K60`
  - Recipe: `trumpet_sus_c4 6rec / trombone_sus_c3 6rec / tada-xp cut after 8% 4rec level 40% | atk 20ms rel 200ms root C4`
- **Sounds used:** `tadaxp`; library: `trumpet_sus_c4`, `trombone_sus_c3`
- **Swap candidates:** Windows: tada, critstop; library: horn_sus_c3, tuba_sus_f1
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: retro-display. Notes before stealing: 4.

#### Night Window Strings (strings, P2, XP badge)

- **Inspired by:** lush strings
- **Character:** Violin section with logon air.
- **DNA v2 (now):** `violin_section_sus_c4#10U2~8/logon<#6L30T4;A250S90R1200K60`
  - Recipe: `violin_section_sus_c4 10rec unison 2 +-8c / logon slower 6rec level 30% transpose +4 | atk 250ms sus 90% rel 1.2s root C4`
- **Sounds used:** `logon`; library: `violin_section_sus_c4`
- **Swap candidates:** Windows: startup, logoff; library: cello_section_sus_c3, erhu_d3
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: retro-display. Notes before stealing: 5.

#### Harbor Lights Pad (pad, P2, XP badge)

- **Inspired by:** lush city pop synth pads
- **Character:** Logon with print sine shimmer and chorus.
- **DNA v2 (now):** `logon@10[#8U2~10/print@10[@50]#6U2~8L35T-2;A500S90R1500K56`
  - Recipe: `logon cut before 10% 8rec unison 2 +-10c / print cut before 10% cut after 50% 6rec unison 2 +-8c level 35% transpose -2 | atk 500ms sus 90% rel 1.5s root G#3`
- **Sounds used:** `logon`, `print`
- **Swap candidates:** Windows: startup, logoff, shutdown, notify, chord, tada; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: retro-display. Notes before stealing: 3.

#### Rooftop Sax Lead (lead, P2, W3.11 badge)

- **Inspired by:** city pop sax/synth lead
- **Character:** Trumpet with clip for reed bite and a scoop.
- **DNA v2 (now):** `trumpet_sus_c4+#10;A30R250K60`
  - Recipe: `trumpet_sus_c4 louder 10rec | atk 30ms rel 250ms root C4`
- **DNA v3 (later):** `trumpet_sus_c4+#10Nlg60Vs30,80;A30R250K60`
  - Features: tape wow/flutter/scoop, voice mode (mono/legato/glide)
- **Sounds used:** none; library: `trumpet_sus_c4`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: flute_vib_c5, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: retro-display. Notes before stealing: 10.

#### Bubble Economy Kit (drums, P3, XP badge)

- **Inspired by:** gated 80s drum machines in city pop
- **Character:** Pop kick, gated snare, crisp hats, tom.
- **DNA v2 (now):** `balloon<<<@45]#16F;A0R150V90`
  - Recipe: `balloon slower x3 cut after 45% 16rec fixed | atk 0ms rel 150ms vel 90%`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `balloon<<<@45]#3F/recycle>@40]+EEJa0,100.180,90.200,0#4F/xprecycle>>>@40]#5F/hwfail<@30]#4;R200V90k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `balloon`, `recycle`, `xprecycle`, `hwfail`
- **Swap candidates:** Windows: menu, xpstart, start, infobar, critstop, ding; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** XP's glassy bells are FM-like already: print, default and xpding are the e-piano.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

### New age and Fourth World

| | |
|---|---|
| Family | Ambient |
| Tempo | free or 60-100 BPM |
| Keys and harmony | Pentatonic and modal; drones; just-intonation colour |
| What producers look for in a preset | Breathy leads, bells, nature, and processed acoustic colour; calm and clean. |
| Sound Recorder feel | Clean sources, little clip; the echo is the space. Water and birds from the disc. |
| Sources | [Wikipedia: New-age music](https://en.wikipedia.org/wiki/New-age_music), [Wikipedia: Jon Hassell (Fourth World)](https://en.wikipedia.org/wiki/Jon_Hassell), [Ableton blog: Jon Hassell, Possible Musics](https://www.ableton.com/en/blog/jon-hassell-possible-musics/) |

Signature sounds and roles:

- breathy pan-flute and ocarina leads
- FM bells and marimbas
- water and nature sounds
- processed trumpet (Fourth World: world traditions plus electronics)
- gamelan-like metal

#### Distant Horizon Horn (lead, P1, XP badge)

- **Inspired by:** Fourth World processed trumpet
- **Character:** Trumpet slowed and echoed, flute breath, wow.
- **DNA v2 (now):** `trumpet_sus_c4<E#8U2~12/recycle>>@8]#4FL20;A120R900K48`
  - Recipe: `trumpet_sus_c4 slower echo 8rec unison 2 +-12c / recycle faster x2 cut after 8% 4rec fixed level 20% | atk 120ms rel 900ms root C3`
- **DNA v3 (later):** `trumpet_sus_c4<E#8U2~12Vw15,4/recycle>>@8]#4FL20;A120R900K48`
  - Features: tape wow/flutter/scoop
- **Sounds used:** `recycle`; library: `trumpet_sus_c4`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: flute_vib_c5, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Clean sources, little clip; the echo is the space. Water and birds from the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands; v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: screen-saver. Notes before stealing: 4.

#### Breath Flute (lead, P1, XP badge)

- **Inspired by:** new age breathy flute
- **Character:** Flute with paper-noise chiff.
- **DNA v2 (now):** `flute_vib_c5#12/recycle>>@8]#4FL30;A40R400K72`
  - Recipe: `flute_vib_c5 12rec / recycle faster x2 cut after 8% 4rec fixed level 30% | atk 40ms rel 400ms root C5`
- **Sounds used:** `recycle`; library: `flute_vib_c5`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** Clean sources, little clip; the echo is the space. Water and birds from the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 4.

#### Temple Metal (bell, P2, W3.11 badge)

- **Inspired by:** gamelan-like metal
- **Character:** Bucket droplet and chimes, comb.
- **DNA v2 (now):** `bucket_droplet_metal#8/chimesEE>#6L40;A0R2000K91`
  - Recipe: `bucket_droplet_metal 8rec / chimes echo x2 faster 6rec level 40% | atk 0ms rel 2s root G6`
- **Sounds used:** `chimes`; library: `bucket_droplet_metal`
- **Swap candidates:** Windows: ding, print, default, error, exclaim, xpnotify; library: wine_glass_medium_ping, crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6, music_box_note; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** Clean sources, little clip; the echo is the space. Water and birds from the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 6.

#### Ocean Shelf (texture, P2, W3.11 badge)

- **Inspired by:** nature beds
- **Character:** Ocean waves slowed.
- **DNA v2 (now):** `nps_ocean_waves<#4F;A2000S100R3000`
  - Recipe: `nps_ocean_waves slower 4rec fixed | atk 2s sus 100% rel 3s`
- **Sounds used:** none; library: `nps_ocean_waves`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: rain_on_window, creek_loop, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Clean sources, little clip; the echo is the space. Water and birds from the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 4.

#### Water Marimba (mallet, P2, W3.11 badge)

- **Inspired by:** new age marimba and water
- **Character:** Marimba with a drop layered on the attack.
- **DNA v2 (now):** `marimba_c4#10/drop_single_a#6FL40;A0R900K60`
  - Recipe: `marimba_c4 10rec / drop_single_a 6rec fixed level 40% | atk 0ms rel 900ms root C4`
- **Sounds used:** none; library: `marimba_c4`, `drop_single_a`
- **Swap candidates:** Windows: xpding, hwfail, default; library: xylophone_c5, ems_relay_marimba_c4, vibraphone_c_low
- **Sound Recorder feel:** Clean sources, little clip; the echo is the space. Water and birds from the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 6.

#### Crystal Bowl Field (pad, P2, W3.11 badge)

- **Inspired by:** crystal bowl pads
- **Character:** Two crystal bowls slowed with echo.
- **DNA v2 (now):** `crystal_bowl_g4<E#8/crystal_bowl_fs3<#8L60T1;A1500S100R4000K55`
  - Recipe: `crystal_bowl_g4 slower echo 8rec / crystal_bowl_fs3 slower 8rec level 60% transpose +1 | atk 1.5s sus 100% rel 4s root G3`
- **Sounds used:** none; library: `crystal_bowl_g4`, `crystal_bowl_fs3`
- **Swap candidates:** Windows: startup, logon, logoff, shutdown, notify, chord; library: choir_aah, singing_bowl_long, violin_section_sus_c4, glass_harp_singing, emh_switchroom_drone; in our XP image, not yet on the disc: NetMeeting TestSnd.wav (swelling chime phrase), Pinball SOUND50 (bonus swell), OOBE qmark #06 (3.2 s clean swell)
- **Sound Recorder feel:** Clean sources, little clip; the echo is the space. Water and birds from the disc.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: screen-saver. Notes before stealing: 8.

### Exotica

| | |
|---|---|
| Family | Lounge |
| Tempo | 70-120 BPM |
| Keys and harmony | Major 6, maj7; Latin and lounge harmony |
| What producers look for in a preset | Vibes, marimba, birdsong, gongs, island perc. |
| Sound Recorder feel | Slow the birds down by octaves, the way exotica records did. |
| Sources | [Wikipedia: Exotica](https://en.wikipedia.org/wiki/Exotica), [Wikipedia: Martin Denny (bird calls, vibraphone)](https://en.wikipedia.org/wiki/Martin_Denny), [Wikipedia: Quiet Village (slowed bird call)](https://en.wikipedia.org/wiki/Quiet_Village) |

Signature sounds and roles:

- vibraphone and marimba
- bird and animal calls (often slowed)
- Latin and island percussion
- lush strings, piano, gongs

#### Lagoon Vibes (bell, P1, W3.11 badge)

- **Inspired by:** exotica vibraphone
- **Character:** Vibraphone with a drawn tremolo.
- **DNA v2 (now):** `vibraphone_c_low#10Ja0,100.120,60.240,100.360,60.480,100;A0R1200K48`
  - Recipe: `vibraphone_c_low 10rec amp 0:100,120:60,240:100,360:60,480:100 | atk 0ms rel 1.2s root C3`
- **Sounds used:** none; library: `vibraphone_c_low`
- **Swap candidates:** Windows: ding, chimes, print, default, error, exclaim; library: wine_glass_medium_ping, crystal_bell_bb5, glockenspiel_c6, ems_fm_register_bell_c6, music_box_note; in our XP image, not yet on the disc: NetMeeting Blip.wav, Messenger online.wav
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: leisure. Notes before stealing: 10.

#### Half-Speed Mockingbird (texture, P1, W3.11 badge)

- **Inspired by:** slowed bird calls
- **Character:** A robin slowed one octave with echo.
- **DNA v2 (now):** `bird_american_robin<E#6F;A0R1500`
  - Recipe: `bird_american_robin slower echo 6rec fixed | atk 0ms rel 1.5s`
- **Sounds used:** none; library: `bird_american_robin`
- **Swap candidates:** Windows: xprecycle, recycle, startup; library: rain_on_window, creek_loop, office_ambience_01, hdd_conner_spin, insect_crickets_mojave
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: leisure. Notes before stealing: 6.

#### Island Marimba (mallet, P2, W3.11 badge)

- **Inspired by:** exotica marimba
- **Character:** Marimba with a soft echo.
- **DNA v2 (now):** `marimba_c4E#10;A0R600K60`
  - Recipe: `marimba_c4 echo 10rec | atk 0ms rel 600ms root C4`
- **Sounds used:** none; library: `marimba_c4`
- **Swap candidates:** Windows: xpding, hwfail, default; library: xylophone_c5, ems_relay_marimba_c4, vibraphone_c_low
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: leisure. Notes before stealing: 10.

#### Gong Ceremony (perc, P2, W3.11 badge)

- **Inspired by:** gongs
- **Character:** Crossbar gong slowed.
- **DNA v2 (now):** `emh_crossbar_gong_c3<#8;A0R3000K36`
  - Recipe: `emh_crossbar_gong_c3 slower 8rec | atk 0ms rel 3s root C2`
- **Sounds used:** none; library: `emh_crossbar_gong_c3`
- **Swap candidates:** Windows: menu, xpstart, infobar, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: leisure. Notes before stealing: 8.

#### Bamboo Shaker (perc, P2, XP badge)

- **Inspired by:** island percussion
- **Character:** Paper crumple at speed, echo.
- **DNA v2 (now):** `recycle>>@20]E#16F;A0R80`
  - Recipe: `recycle faster x2 cut after 20% echo 16rec fixed | atk 0ms rel 80ms`
- **Sounds used:** `recycle`
- **Swap candidates:** Windows: menu, xpstart, infobar, balloon, popup, default; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, mouse_click, bubble_pop_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick, Pinball bumper (SOUND12), NetMeeting Blip.wav
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: leisure. Notes before stealing: 16.

#### Tiki Lounge Piano (keys, P2, W3.11 badge)

- **Inspired by:** cocktail piano in exotica
- **Character:** Harp pluck with a ding sparkle (piano until the disc names are fixed).
- **DNA v2 (now):** `harp_c5#10/ding@20]#6L30T5;A0D2000S20R700K72`
  - Recipe: `harp_c5 10rec / ding cut after 20% 6rec level 30% transpose +5 | atk 0ms dec 2s sus 20% rel 700ms root C5`
- **Sounds used:** `ding`; library: `harp_c5`
- **Swap candidates:** Windows: xpding, print, default, chord, ringout; library: epiano_yamaha_vibe, epiano_bell_c3, organ_hammond_m100_flute_c, music_box_note; in our XP image, not yet on the disc: Messenger newemail.wav (mallet arpeggio), online.wav
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: leisure. Notes before stealing: 6.

#### Volcano Strings (strings, P2, W3.11 badge)

- **Inspired by:** lush exotica strings
- **Character:** Violin and cello sections, slow swell, echo.
- **DNA v2 (now):** `violin_section_sus_c4E#8/cello_section_sus_c3#6L60;A500S90R1500K60`
  - Recipe: `violin_section_sus_c4 echo 8rec / cello_section_sus_c3 6rec level 60% | atk 500ms sus 90% rel 1.5s root C4`
- **Sounds used:** none; library: `violin_section_sus_c4`, `cello_section_sus_c3`
- **Swap candidates:** Windows: startup, logon, logoff; library: erhu_d3
- **Sound Recorder feel:** Slow the birds down by octaves, the way exotica records did.
- **Ships:** library disc: XP now; BASILISK 16 when its library drive lands. Pack: leisure. Notes before stealing: 6.

### Video-game chiptune

| | |
|---|---|
| Family | Retro |
| Tempo | 120-180 BPM |
| Keys and harmony | Major and minor; fast arpeggios stand in for chords |
| What producers look for in a preset | Clean pulse leads with duty choices, triangle bass, noise drums, fast arps. |
| Sound Recorder feel | LOOP-OSC buzzes ARE pulse waves made of a looped slice; a 3.11 8-bit source adds the grit. |
| Sources | [Wikipedia: Chiptune](https://en.wikipedia.org/wiki/Chiptune), [NESdev wiki: APU basics (pulse duty 12.5/25/50/75 %, triangle, noise)](https://www.nesdev.org/wiki/APU_basics), [DDRKirby: NES chiptunes in Unlock Everything](https://ddrkirby.com/articles/nes-chiptunes-unlock-everything/nes-chiptunes-unlock-everything.html) |

Signature sounds and roles:

- pulse waves at 12.5/25/50 % duty
- a triangle bass
- noise-channel drums
- fast arpeggios as chords
- duty-cycle and volume envelopes per note

#### Pulse Twelve Lead (lead, P1, W3.11 badge)

- **Inspired by:** NES pulse lead (12.5 % duty)
- **Character:** A 4 ms slice of ding looped: a thin, bright buzz.
- **DNA v2 (now):** `ding@t60[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#12;A0R60K59`
  - Recipe: `ding cut before 60ms cut after 20ms cut after 20% double x9 12rec | atk 0ms rel 60ms root B3`
- **Sounds used:** `ding`
- **Swap candidates:** Windows: tadaxp, tada, ringout, print, xpringin, notify; library: flute_vib_c5, trumpet_sus_c4, ems_ferranti_hoot_c4, ems_fm_bell103_lead, erhu_d3; in our XP image, not yet on the disc: Agent merlin #22 (2 s clean tone)
- **Sound Recorder feel:** LOOP-OSC buzzes ARE pulse waves made of a looped slice; a 3.11 8-bit source adds the grit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: game-port. Notes before stealing: 12.

#### Triangle Floor (bass, P1, W3.11 badge)

- **Inspired by:** NES triangle bass
- **Character:** Sine loop down two octaves, hard on/off.
- **DNA v2 (now):** `ringout@20[@40]@0CP@0CP@0CP<<#8;A0R20V0K45`
  - Recipe: `ringout cut before 20% cut after 40% double x3 slower x2 8rec | atk 0ms rel 20ms vel 0% root A2`
- **DNA v3 (later):** `ringout@20[@40]@0CP@0CP@0CP<<#8Nm;A0R20V0K45`
  - Features: voice mode (mono/legato/glide)
- **Sounds used:** `ringout`
- **Swap candidates:** Windows: xpringout, batlow, critstop, balloon, xpding, default; library: contrabass_pizz_e1, tuba_sus_f1, ems_motor_drone_c3, em_hum_mains_loop, ems_ks_wire_c3
- **Sound Recorder feel:** LOOP-OSC buzzes ARE pulse waves made of a looped slice; a 3.11 8-bit source adds the grit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 glide/wow: smooth on 3.11 (card rate), a planned staircase on XP after phase 0. Pack: game-port. Notes before stealing: 8.

#### Fast Arp Chord (arp, P1, W3.11 badge)

- **Inspired by:** chiptune arpeggio chords
- **Character:** Pulse buzz played as a fast arp from the grid.
- **DNA v2 (now):** `ding@t60[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#8;A0R30K59`
  - Recipe: `ding cut before 60ms cut after 20ms cut after 20% double x9 8rec | atk 0ms rel 30ms root B3`
- **DNA v3 (later):** `ding@t60[@t20]@20]@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP@0CP#8;A0R30K59q0xd32n2o1`
  - Features: mine-grid sequencer/arp (x), scale (q)
- **Sounds used:** `ding`
- **Swap candidates:** Windows: default, xpding, chimes; library: kalimba_g5, glockenspiel_g4
- **Sound Recorder feel:** LOOP-OSC buzzes ARE pulse waves made of a looped slice; a 3.11 8-bit source adds the grit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: game-port. Notes before stealing: 8.

#### Noise Channel Kit (drums, P2, W3.11 badge)

- **Inspired by:** NES noise drums
- **Character:** Hats and snare from ringin noise; kick from a dropping ding.
- **DNA v2 (now):** `ding<<<@35]#16F;A0R80`
  - Recipe: `ding slower x3 cut after 35% 16rec fixed | atk 0ms rel 80ms`
  - v2 DNA is the kick on its own (a tunable kick preset); the kit needs v3 kit mode.
- **DNA v3 (later):** `ding<<<@35]#3F/ringin<@20]+#4F/ringin>>@12]#5F/ding>>@5]#4;R100V100k36k35i80k38l2k39l2s.3i90k40l2t40k42l3e.12c1k44l3e.05i70c1k46l3c1k37l4k41,50l4r45p100w7`
  - Features: kit pads (k)
- **Sounds used:** `ding`, `ringin`
- **Swap candidates:** Windows: balloon, recycle, xprecycle, menu, xpstart, start; library: em_relay_click_a, ems_relay_tiny, key_mechanical_hard, floppy_seek_clunk, drop_single_a, glass_tap; in our XP image, not yet on the disc: Minesweeper tick (woodblock) and explosion (boom), Pinball flipper (SOUND104, tight thump) and bumper (SOUND12, metallic hit)
- **Sound Recorder feel:** LOOP-OSC buzzes ARE pulse waves made of a looped slice; a 3.11 8-bit source adds the grit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1); v3 kit: exact on 3.11; XP choke fades need phase-0 streamed gain. Pack: kit-manager. Notes before stealing: 16.

#### Coin Jingle (fx, P2, W3.11 badge)

- **Inspired by:** game coin / power-up FX
- **Character:** Ding sped up twice with an octave insert.
- **DNA v2 (now):** `ding>>@30]Iding>>>#12;A0R100K127`
  - Recipe: `ding faster x2 cut after 30% insert ding faster x3 12rec | atk 0ms rel 100ms root G9`
- **Sounds used:** `ding`
- **Swap candidates:** Windows: restore, minimize, xprecycle, xpringin, popup, hwin; library: whoosh_in, whoosh_away, crt_degauss, modem_dialup_a, thunder_rumble, splash_big; in our XP image, not yet on the disc: Pinball mission complete (SOUND9)
- **Sound Recorder feel:** LOOP-OSC buzzes ARE pulse waves made of a looped slice; a 3.11 8-bit source adds the grit.
- **Ships:** both editions (every built-in name plays on both since 1.2.1). Pack: game-port. Notes before stealing: 12.

## 5. Sources

- [Wikipedia: Deep house](https://en.wikipedia.org/wiki/Deep_house)
- [Native Instruments blog: How to make a deep house track](https://www.native-instruments.com/blogs/blog/how-to-make-a-deep-house-track)
- [Mode Audio: Deep House, 5 production essentials](https://modeaudio.com/magazine/deep-house-5-production-essentials)
- [Berklee Online: Create authentic house music (chords, bass lines, melody)](https://online.berklee.edu/takenote/?p=14419)
- [Wikipedia: Chicago house](https://en.wikipedia.org/wiki/Chicago_house)
- [Sound on Sound: Secrets of House & Trance (2004)](https://www.soundonsound.com/techniques/secrets-house-trance)
- [Wikipedia: French house](https://en.wikipedia.org/wiki/French_house)
- [Wikipedia: Detroit techno](https://en.wikipedia.org/wiki/Detroit_techno)
- [Wikipedia: Minimal techno](https://en.wikipedia.org/wiki/Minimal_techno)
- [Wikipedia: Dub techno](https://en.wikipedia.org/wiki/Dub_techno)
- [Wikipedia: Trance music](https://en.wikipedia.org/wiki/Trance_music)
- [Wikipedia: Roland JP-8000 (supersaw, anthem trance)](https://en.wikipedia.org/wiki/Roland_JP-8000)
- [Perfect Circuit: Super saw history](https://www.perfectcircuit.com/signal/super-saw-history)
- [reFX: Nexus expansion Trance Elements](https://refx.com/nexus/expansion/trance-elements/)
- [Wikipedia: Drum and bass](https://en.wikipedia.org/wiki/Drum_and_bass)
- [Wikipedia: Jungle music](https://en.wikipedia.org/wiki/Jungle_music)
- [Wikipedia: Amen break](https://en.wikipedia.org/wiki/Amen_break)
- [Attack Magazine: Reese bass (history: sampled for jungle)](https://www.attackmagazine.com/technique/video-tutorials/reese-bass/)
- [Native Instruments blog: Reese bass (two saws and a low-pass)](https://www.native-instruments.com/blogs/blog/reese-bass)
- [EDMProd: How to make jungle music](https://www.edmprod.com/how-to-make-jungle-music/)
- [Wikipedia: UK garage](https://en.wikipedia.org/wiki/UK_garage)
- [Wikipedia: 2-step garage](https://en.wikipedia.org/wiki/2-step_garage)
- [Native Instruments blog: UK garage music (about 130 BPM)](https://www.native-instruments.com/blogs/blog/uk-garage-music)
- [MusicRadar: How to make a UK garage beat (organ bass patch)](https://musicradar.com/how-to/uk-garage-tutorial)
- [Reason Studios: How to make UK garage (broken kick on steps 1 and 11)](https://www.reasonstudios.com/news/post/how-to-make-uk-garage)
- [Wikipedia: Dubstep](https://en.wikipedia.org/wiki/Dubstep)
- [Native Instruments blog: Massive, past presets and future (dubstep wavetables)](https://blog.native-instruments.com/massive-past-presets-future/)
- [Wikipedia: Boom bap](https://en.wikipedia.org/wiki/Boom_bap)
- [Wikipedia: E-mu SP-1200 (12-bit, 26.04 kHz)](https://en.wikipedia.org/wiki/E-mu_SP-1200)
- [Rossum Electro-Music: SP-1200 (aliasing from authentic pitch shifting)](https://www.rossum-electro.com/products/sp-1200/)
- [LANDR blog: SP-1200, the sampler that changed hip-hop](https://blog.landr.com/sp-1200)
- [FACT: 15 samplers that shaped modern music](https://factmag.com/2016/09/15/15-samplers-that-shaped-modern-music)
- [Wikipedia: Akai MPC](https://en.wikipedia.org/wiki/Akai_MPC)
- [Wikipedia: Lo-fi hip hop](https://en.wikipedia.org/wiki/Lo-fi_hip_hop)
- [Wikipedia: Trap music](https://en.wikipedia.org/wiki/Trap_music)
- [Wikipedia: Roland TR-808](https://en.wikipedia.org/wiki/Roland_TR-808)
- [Wikipedia: Synthwave](https://en.wikipedia.org/wiki/Synthwave)
- [Mode Audio: Synthwave, 5 production essentials](https://modeaudio.com/magazine/synthwave-5-production-essentials)
- [EDMProd: How to make synthwave](https://www.edmprod.com/how-to-make-synthwave/)
- [MusicTech: dreamy synths and retro drums (synthwave guide)](https://www.musictech.com/guides/essential-guide/produce-dreamy-synths-retro-drums-like-com-truise/)
- [Wikipedia: Chillwave](https://en.wikipedia.org/wiki/Chillwave)
- [Wikipedia: Ambient music](https://en.wikipedia.org/wiki/Ambient_music)
- [Wikipedia: Drone music](https://en.wikipedia.org/wiki/Drone_music)
- [Wikipedia: Intelligent dance music](https://en.wikipedia.org/wiki/Intelligent_dance_music)
- [Wikipedia: Glitch (music)](https://en.wikipedia.org/wiki/Glitch_(music))
- [Wikipedia: Breakbeat](https://en.wikipedia.org/wiki/Breakbeat)
- [Wikipedia: Big beat](https://en.wikipedia.org/wiki/Big_beat)
- [Wikipedia: Electro (music)](https://en.wikipedia.org/wiki/Electro_(music))
- [Wikipedia: Trip hop](https://en.wikipedia.org/wiki/Trip_hop)
- [Wikipedia: Downtempo](https://en.wikipedia.org/wiki/Downtempo)
- [Wikipedia: Footwork (genre) (about 160 BPM, TR-808)](https://en.wikipedia.org/wiki/Footwork_(genre))
- [MusicRadar / Computer Music: juke-style pitched 808 kick pattern](https://www.musicradar.com/tuition/tech/how-to-make-a-juke-style-pitched-808-kick-pattern-554083)
- [DJ TechTools: Footwork, what is it and how do you make it](https://djtechtools.com/2014/04/24/footwork-what-is-it-and-how-do-you-make-it/)
- [Wikipedia: Hyperpop](https://en.wikipedia.org/wiki/Hyperpop)
- [MusicRadar: extreme hyperpop textures](https://musicradar.com/tutorials/music-production-tutorials/how-to-craft-extreme-hyperpop-textures-to-make-sophie-style-tunes)
- [Native Instruments blog: Hyperpop](https://blog.native-instruments.com/hyperpop)
- [Wikipedia: City pop](https://en.wikipedia.org/wiki/City_pop)
- [Lavengood (2019): What makes it sound '80s? The Yamaha DX7 electric piano sound](https://meganlavengood.com/wp-content/uploads/2019/09/Lavengood-2019-%E2%80%9CWhat-Makes-It-Sound-%E2%80%9980s%E2%80%9D-The-Yamaha-DX7-Electr.pdf)
- [Reverb Machine: Exploring the Yamaha DX7, part 2: songs](https://reverbmachine.com/blog/exploring-the-yamaha-dx7-pt2/)
- [Yamaha Synth 50th: Japanese pop music and Yamaha synthesizers](https://th.yamaha.com/th/musical-instruments/keyboards/explore/synth-50th/anecdotes/012.html)
- [Wikipedia: New-age music](https://en.wikipedia.org/wiki/New-age_music)
- [Wikipedia: Jon Hassell (Fourth World)](https://en.wikipedia.org/wiki/Jon_Hassell)
- [Ableton blog: Jon Hassell, Possible Musics](https://www.ableton.com/en/blog/jon-hassell-possible-musics/)
- [Wikipedia: Exotica](https://en.wikipedia.org/wiki/Exotica)
- [Wikipedia: Martin Denny (bird calls, vibraphone)](https://en.wikipedia.org/wiki/Martin_Denny)
- [Wikipedia: Quiet Village (slowed bird call)](https://en.wikipedia.org/wiki/Quiet_Village)
- [Wikipedia: Chiptune](https://en.wikipedia.org/wiki/Chiptune)
- [NESdev wiki: APU basics (pulse duty 12.5/25/50/75 %, triangle, noise)](https://www.nesdev.org/wiki/APU_basics)
- [DDRKirby: NES chiptunes in Unlock Everything](https://ddrkirby.com/articles/nes-chiptunes-unlock-everything/nes-chiptunes-unlock-everything.html)

Many tutorial sources are vendor blogs. Tempo and key ranges are the consensus of several; where they disagree (UK garage 130 vs 134-140 BPM), the table gives the range.

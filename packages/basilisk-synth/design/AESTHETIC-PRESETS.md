# Aesthetic presets: vaporwave, Frutiger Aero and their neighbors

Design draft for BASILISK SYNTH (XP edition) and BASILISK 16 (3.11 edition). Branch `design/aesthetic-presets`.

- **Status:** design only. No code, DNA.md or core file changes on this branch.
- **Machine-readable draft:** [`aesthetic-presets.json`](aesthetic-presets.json), 101 presets in 10 sections.
- **Checks:** every draft DNA was parsed by `parse()` in `core/dna.cpp` on main (`d61652f`, DNA v2). Each one is
  canonical and has no unknown NAME (library names are counted as known; see section 6). Nobody has listened to
  them yet. Treat each one as a start for tuning by ear.
- **Inputs:** `library/research/windows-sounds.json` (1,223 sounds), `library/research/preset-targets.md`
  (198 targets), `library/research/ui-layouts.md`, the library-disc catalog `library/catalog/*.json`, and
  `library/sam_phrases.txt`. These files are in the main working tree of the library lane and are not on main yet.
- **Relation to earlier work:** `preset-targets.md` already has 29 targets in "Lo-fi and vaporwave",
  "Aesthetic: Frutiger Aero" and "Aesthetic: Y2K, web portal and corporate". This draft keeps those targets and their
  names. The presets here are new and use different names. The toolbox idioms (GRAIN, LOOP-OSC, BLUR-DOWN,
  PRE-VERB, LONG-ECHO, COMB, DECIMATE, OCT-BAKE, MIX-TRANSIENT, SPLICE-SEQ) are the ones defined in
  `preset-targets.md` section 1.
- **Relation to the preset-engine-2 lane** (`design/preset-engine-2`): that lane designs start and end points, voice
  modes, the tape keyboard and granular presets. This draft does not design those features. Where a preset here
  would sound better with one of them, the preset says "engine-2" and does not propose a gene.

Contents:

1. Culture map
2. Techniques mapped to Sound Recorder
3. Windows sounds for each genre
4. Preset sections and the top 10
5. Style guide
6. Library-disc additions
7. v3 proposals
8. Sources

---

## 1. Culture map

Artist and album names are references for research only. No preset uses a sample of a copyrighted record. No
preset name uses an artist name, a brand or a trademark.

### 1.1 Vaporwave and its sub-genres

Vaporwave started on the internet in the early 2010s. It came out of chillwave and hypnagogic pop. Its relation to
consumer capitalism is ironic or ambiguous. It looks back at the media, technology and advertising of the 1980s and
1990s [W-vw]. The name is a pun on "vaporware" [W-vw]. The writer David Keenan called the parent style,
hypnagogic pop, "pop music refracted through the memory of a memory" [W-hyp]. Writers such as Simon Reynolds and
Mark Fisher connected that scene to "hauntology" [W-hyp].

The common sources are smooth jazz, elevator and corporate mood music, R&B, lounge music and 1980s-1990s dance
music. The common techniques are slowed samples, chopped-and-screwed editing, pitch shift, repetition and heavy
reverb [W-vw].

| Style | Meaning | Typical sources | Techniques | Tempo, key, harmony | References (research only) |
|---|---|---|---|---|---|
| **Eccojams** | The first template. A short fragment of a pop song is looped, slowed and drowned in echo until it turns strange [BC]. The maker called it a folk art that anyone can join [W-ecco]. | 1980s pop hooks, a few seconds long. | Loop, slow down, echo. The method comes from DJ Screw's chopped-and-screwed style [W-ecco]. | Slowed by 2 semitones up to an octave (typical of the style; not measured). Harmony is whatever the fragment holds. | *Chuck Person's Eccojams Vol. 1* (2010) [W-ecco]. |
| **Classic vaporwave** | Commerce remembered half asleep. | Smooth jazz, R&B, lounge, mood music. | Slowed, chopped, pitch-shifted, reverbed. | Often maj7 and min9 color from the sources. | *Floral Shoppe* (Macintosh Plus, 2011) is the usual first full example [W-vw]. |
| **Mallsoft** | The shopping mall as an empty, soulless space of consumerism [W-vw]. The listener wanders with no aim [BC]. | Muzak, easy listening, bossa nova, smooth jazz, mall field recordings [BC][BCamp-pm]. | Very spacious echo; the music sounds as if it comes from another floor [BC]. | Slow; lounge harmony (maj7, 6/9). | *Palm Mall* (猫 シ Corp., 2014) [BCamp-pm]; *Hologram Plaza* (Disconscious) [BC]. |
| **Utopian virtual** | Crisp, clean computer and commerce sounds of the 1990s and 2000s. They show a post-Cold-War optimism that now feels hollow [BC]. | Startup themes, chat-client sounds, preset synth sounds, GarageBand loops [BC][DiS]. The template album used sounds that recall Skype, Windows XP and the Wii [W-vw]. | Clean, dry or lightly reverbed. Not slowed. Presets left as they are. | Bright major keys; simple, glossy. | *Far Side Virtual* (James Ferraro, 2011) [W-fsv]. |
| **Late-night lo-fi** | Lonely nights, styled after old 4:3 TV broadcasts [W-vw][BC]. | Slowed 1980s pop and jazz, synth strings, saxophone [BC]. | Slowed, lo-fi, muffled. **VHS pop** is a brighter, richer version [W-vw]. | 70-90 BPM (typical; not cited). min9, maj7. | *moods* (luxury elite) [BC]. |
| **Barber beats** | Smooth jazz, lounge and R&B from the 1980s to the early 2000s, slowed down [W-vw]. | As stated. | Slowed loops. | Slow. Jazz harmony. | Haircuts for Men, Macroblank [W-vw]. |
| **Signalwave / broken transmission** | Channel-surfing: old radio and TV clips cut together fast. Disorientation and a critique of consumerism [BC]. | Commercials, station idents, jingles, weather reports, shortwave, number stations, test signals [MG-sig]. The Weather Channel's "Local on the 8s" smooth jazz is a common source [W-vw][Wired]. | Short loops with little change; distortion, static, tape warble; echo for distance; speech treated as music [MG-sig]. | No fixed tempo. | *Computer Death* (Infinity Frequencies) [MG-sig]. |
| **Slushwave** | Vaporwave at a crawl. Long, smeared pads; little or no percussion [MG-slush]. | Ambient synths, nostalgic samples. | Extreme time-stretch, heavy reverb and echo [MG-slush]. Tracks of more than 10 minutes are common [W-vw]. | Very slow. One chord for minutes. | *Virtual Dream Plaza* (t e l e p a t h) [MG-slush]. |
| **Dreampunk** | Atmospheric offshoot: vaporwave textures with ambient, techno and cyberpunk film-score influence [S-dp]. | Film-score pads, rain, city noise. | Big reverb, slow drones, dark pads. | Minor, modal. | The Dream Catalogue label (2014) and the duo 2814 [S-dp]. |
| **Future funk** | Hedonistic and upbeat. Disco and Japanese city pop, sped up, with a French-house feel [W-vw][SF]. | 1970s-80s disco, soul, city pop [BC][SF]. | Filtered loops, added kicks, sidechain-like pumping. | 110-130 BPM [SF][NI]. Major 7th and dominant 9th chords from disco. | Saint Pepsi, Macross 82-99, Night Tempo [W-vw]. |
| **Vaportrap / vaporhop** | Vaporwave samples over trap or hip-hop beats [BC]. "Vaporhop" is a community name for the hip-hop side; it has no stable definition in the sources found. | Vaporwave samples, 808s. | Skittering hi-hats, long 808 subs, spacey synths [BC]. | 60-75 BPM half-time feel (typical; not cited). | *Blank Banshee 0* [BC]. |
| **Hardvapour** | A harder, club-oriented reaction against vaporwave [BC]. | Gabber and speedcore drums, Eastern European imagery [W-vw][BC]. | Distorted kicks, harsh leads. | Fast (150 BPM and more; typical, not cited). | Sandtimer, DJ ALINA [BC]. |
| **"Windows 95 / 98 / XP" nostalgia** | The operating system itself as a memory. Startup and error sounds become instruments; remix memes play them as songs. | Startup, logon, shutdown, error and chime sounds. | Slowed and reverbed startup sounds; chromatic error-sound melodies. | The XP startup is in Ab major (measured root G#4). | The Windows 95 startup sound was made by Brian Eno [FarOut]. The Vista startup was made by Robert Fripp, Tucker Martine and Steve Ball over 18 months [RCP]. |
| **Liminal / backrooms ambience** | Empty, transitional spaces: an office or a pool room with nobody in it. | Fluorescent hum, HVAC, distant muzak, slowed songs. | Cavernous reverb, slow drones, long attacks, ticking pulses [Verge][Itch]. The community uses "slowed + reverb" songs as a symbol of loneliness [Verge]. | Static harmony. | Fan media; no single canon. |

**Slowed + reverb and chopped and screwed.** DJ Screw's Houston "screwed" style slows tracks to about 60-70
quarter-note BPM and adds beat skips, scratches and stop-time. The "chop" repeats a word or a beat with a one-beat
delay between two copies of the same record [W-cs]. "Slowed + reverb" is a later, simpler YouTube and TikTok edit
of the same idea; critics call it a weaker copy of chopped and screwed [W-cs]. Credit the Houston origin in any
preset description that uses the word "screw".

### 1.2 Frutiger Aero and related aesthetics

Frutiger Aero is a design style of about 2004-2013. It began in user interfaces and spread to advertising, game
consoles and interior design. Its name joins the Frutiger typeface and Windows Aero. It was also called "Web 2.0
gloss". Sofi Xian of the Consumer Aesthetics Research Institute named it in 2018 [W-fa]. Its motifs are glossy and
reflective surfaces, 3D, bright color, blue skies, grass, aurorae, lens flares, bokeh, water, tropical fish,
bubbles and skeuomorphic icons [W-fa]. Flat design replaced it from about 2012 [W-fa]. It came back as a nostalgia
trend in 2023 and 2024 [W-fa].

The style has no fixed music genre. Fans name soft, calm, jazz-leaning music and early-2000s synth music;
mid-tempo; heavy reverb; orchestral strings or bells played on synths; and held 7th chords [FAA][Last]. A sample
pack for the style names "translucent reverbs, pristine delays, glossy modulation effects" [Cradle].

| Style | Meaning | Typical sounds | Techniques | Harmony | References |
|---|---|---|---|---|---|
| **Frutiger Aero** | Humanist, optimistic technology: nature and glass together [W-fa]. | Glass bells, water drops, bubbles, airy pads, clean electric pianos, startup swells. | Clean (not lo-fi), wide stereo, long bright reverb, delay. | maj7, maj9, add9, sus2; bright major keys. | The Vista startup [RCP]. |
| **Frutiger Metro** | The flat, tiled step after Aero, named after Windows 8's Metro design language [Skeuoss]. | Short, clean clicks and plucks; less reverb. | Dry, crisp, minimal. | Simple triads. | Fan definitions only. |
| **Frutiger Eco** | Aero with renewable energy, sustainability and nature: solar panels, water, earth [Gurl]. | Birds, wind chimes, streams, rain, pan flute. | Natural recordings under clean synths. | Major, pentatonic. | Fan definitions only. |
| **Y2K futurism / skeuomorph** | The style before Aero: blobs, chrome and metal; edgier and more sci-fi [Gurl]. | Bloops, whooshes, metallic hits, modem sounds, Flash-intro risers. | Bright, compressed, short echoes. | Major and suspended. | `preset-targets.md` "Y2K, web portal and corporate". |
| **"Vista aesthetic" / Aero Glass** | The glossy window frames and startup orb of 2006-2009. | A swelling startup chord; glass chimes; soft notification chords. | Long swells, reversed bells, wide chorus. | Major with 9ths. | [RCP]. |
| **Console-channel / plaza jazz** | The bossa and jazz of game-console menus and shop channels, remembered as calm and slightly strange [Vape][Vice]. | Vibraphone, nylon guitar, soft drums, clean electric piano. | Dry or light room; bouncy swing. | Jazz ii-V-I, maj7, 6/9. | The shop-channel tune by Kazumi Totaka is called a jazz standard of game music [W-tot]. |
| **Aquarium / screensaver** | Fish-tank calm on a CRT screensaver. | Bubbles, water movement, soft pads, glass bowls. | Slow, wet, rounded. | Modal major. | [W-fa]. |
| **Corporate stock music ("corporate Memphis" era and before)** | The upbeat, faceless music of training videos and explainer videos. | Clean electric piano, ukulele or nylon pluck, claps, glockenspiel, synth strings. | Bright, dry, compressed. | I-V-vi-IV, add9. | `preset-targets.md` "Hold Music Muzak Keys". |

### 1.3 Other related styles

- **Hypnagogic pop / hauntology** (2009-): the parent of vaporwave; memory of 1980s media [W-hyp]. Presets in the
  "Slush" section serve it.
- **Weather / forecast nostalgia ("weatherwave")**: hours of old forecast broadcasts with smooth jazz [Wired][AAJ].
  Presets in "Signal" and "Late Night" serve it.
- **Simpsonwave**: cartoon clips with vaporwave tracks [W-vw]. No special sound.
- **Synthwave / chillwave**: neighbors, not part of this draft. `preset-targets.md` covers their pads and leads.
- **Excluded:** "fashwave" is a far-right offshoot [W-vw]. No preset, name or description refers to it.

---

## 2. Techniques mapped to Sound Recorder

The instrument has 13 Sound Recorder steps, the voice genes and the v2 genes (offset `O`, pan `Q`, drawn envelopes
`Ja`/`Jp`, macros `m`). The table maps each genre technique to them.

| Genre technique | Instrument method | DNA | Notes |
|---|---|---|---|
| **Slowed (tape speed)** | Play below the root key. The rate falls, so pitch and tempo fall together, as on tape. | `T-2` to `T-5`, or play lower keys | `T-4` is 0.79x speed. This is the vaporwave slowdown. Choose `K` so the usual playing range is the speed you want. |
| **Slowed by octaves** | Effects > Decrease Speed. | `<`, `<<` | Each `<` doubles the length. The result is baked in: the buffer is longer. |
| **Reverb** | Add Echo, repeated; echo between slow-downs. | `E`, `EE`, `<E<E` (BLUR-DOWN) | Sound Recorder has no reverb. Several echoes, spread by speed changes, read as a room. |
| **Long echo tail** | Slow, echo, speed up. | `<E>` (LONG-ECHO) | The echo delay comes out 2x longer at the same pitch. |
| **Echo with room to ring** | Add silence after the sound, then echo. | `R@0Isilence_1000RE` | Needs the `silence_*` library sounds (section 6). Verify whether Add Echo extends the buffer; if it does, this is not needed. |
| **Reverse reverb / swell** | Reverse, echo, reverse. | `RER` (PRE-VERB), `R` | The shimmer before a note. |
| **Loop (eccojam)** | Keep a slice; double it with Copy and Paste Insert. | `@a[@b]@0CP@0CP` | Each `@0CP` doubles the loop. 30 s cap. The seam is not smoothed; trim at zero crossings by ear. |
| **Stutter / chop** | Repeat a very short slice, then continue. | `@a[@b]@0CP@0CP@0CP@99Isource` | The DJ Screw "chop" repeats a beat [W-cs]. |
| **Screw down / tape stop** | Layers with offsets, each one octave lower. | `/x<#5O350/x<<#5O1050` | Sound Recorder cannot slow only part of a buffer. Offsets do it. Engine-2 may add a better tape stop. |
| **Lo-pass / muffled** | Speed as a filter: down and up again; or a duller source. | `><`, `>><<` (DECIMATE) | Hypothesis from `preset-targets.md`: verify by measurement on XP. |
| **Bitcrush** | Down and up three times; volume down and up on 8-bit sources. | `>>><<<`, `----++++` | Both are hypotheses. The 8-bit sources (ringin, ringout, the 3.11 set, Pinball) crush most. |
| **Detune / chorus** | Unison. | `U2~6` to `U3~14` | Up to 8 voices. Cost: one recorder per voice. |
| **Wow and flutter** | Wide unison spread; macro on spread. | `U3~18`, `m2...C8,40` | Unison is static detune, not moving wow. See v3 `W`. |
| **Tape hiss, dust, crackle** | Crumple sounds decimated and looped, fixed pitch, quiet. | `recycle>>><<<@0CP@0CP-#2FL10` | A layer under keys. |
| **Saturation / clip** | Increase Volume clips hard at full scale. | `+` to `++++` | Hard clip; square-like. Good for hardvapour. |
| **Sidechain pump** | Drawn amplitude envelope. | `Ja0,0.200,100.254,10...` | Eight points only. See v3 envelope loop. |
| **Ping-pong delay** | Same layer three times, offsets on the beat, panned. | `O500Q-70L60`, `O1000Q70L35` | 500 ms is a quarter at 120 BPM. See v3 tempo sync. |
| **Collage / channel surf** | Insert File chain. | `IaIbIc` (SPLICE-SEQ) | Any Media or library sound. |
| **Ambience bed** | A fixed-pitch layer of a long library recording. | `mall_ambience_shopping_centre-#2FL40` | It restarts on every note. Use it in "hold one key" presets, or set its pool to 1 or 2. |
| **Jazz chords on one key** | Harmony gene. | `H0,4,7,11` (maj7), `H0,3,7,10,14` (min9), `H0,4,7,11,14` (maj9), `H0,4,10,14` (9), `H0,2,7` (sus2), `H0,4,7,9,14` (6/9) | One key, one chord. Each interval costs one recorder per unison voice. |

**The key rule: register follows speed.** On this instrument a key plays the buffer faster or slower. The key `K`
plays the buffer at its built speed. A pad built with `<<` sounds two octaves low, and it sounds slowed only near
`K`. If the player plays it two octaves higher, it runs at the original speed again. The generator for the draft
sets `K` to the main layer's estimated root after its steps. So every main layer is in tune and sounds where it
is. Other layers get a `T` that corrects only the pitch class, so they keep their own register (a `<<` sub layer
stays two octaves down).

**Verify on the real machine before tuning:**

1. The delay time and repeat count of Add Echo in `sndrec32.exe` (XP) and `SOUNDREC.EXE` (3.11).
2. Whether Add Echo, Paste Mix and Mix with File extend the buffer.
3. Whether Increase Speed drops samples without a filter (DECIMATE) and what `----++++` does to 16-bit sources.
4. The click at each `@0CP` seam.

---

## 3. Windows sounds for each genre

Sounds in our images first. "Media" means the 35 DNA names of DNA.md 2.4. Roots are the estimates in
`windows-sounds.json`.

| Genre | Media sounds (DNA name, root) | Other sounds in the XP image (need a library-disc copy) | Library catalog sounds |
|---|---|---|---|
| Mallsoft | `xpding` B3 (EP), `default` D#5 (felt piano), `print` A#5 (vibes), `notify` D5 (PA chime: a fourth), `logon`, `logoff`, `shutdown` (strings), `chord` G3 | Messenger `newemail.wav` (mallet arpeggio), WMP tour beds `wmpaud1`-`9` (music beds, MS-ADPCM), gm.dls alto sax, vibes, nylon | `mall_ambience_*`, `hotel_lobby_open_plan`, `office_elevator_ride`, `airport_gatwick_pa_announcements`, `holdmusic_*` (public domain 78s and CC0 loops) |
| Eccojams | `startup` G#4 (4.8 s, the longest), `logon`, `logoff`, `shutdown`, `tada` C4, `notify`, `xpringout` | WMP tour beds; Pinball `SOUND1` (5 s light show); XP setup music `title.wma` (not a WAV: render to PCM) | `holdmusic_*` |
| Late-night lo-fi, barber beats | `xpding`, `ringout` A4 (sine body), `logoff`, `error` D#6 (bass when slowed), `recycle` (dust), `chimes` | gm.dls tenor sax, fretless, electric piano 1/2, strings | `rain_on_window`, `epiano_bell_c3`, `vibraphone_c_low` |
| Signalwave | `ringout` (test tone), `xpringout`, `batcrit`, `notify`, `chimes`, `recycle` | Microsoft Sam (SAPI 5.1, render phrases), Messenger `type.wav`, OOBE `clickerx.wav` | `prelinger_*`, `newsreel_*`, `nasa_*`, `crt_*`, `modem_*`, `dtmf_*`, `phone_dial_tone_us`, `fax_teletype_loop` |
| Utopian virtual | `hwin`/`hwout` (bloops), `balloon`, `batlow` (ringtone), `start`/`xpstart` (clicks) | Messenger `online`, `newalert`, `newemail`; NetMeeting `Blip.wav` (D#6 bell), `TestSnd.wav`; gm.dls kalimba, steel drum, new-age pad, synth brass; Agent `merlin` #22, qmark #06 | `mouse_click`, `typewriter_keys` |
| Frutiger Aero / glass | `print`, `xpnotify` A#4 (falling bell), `default`, `chimes`, `ding` G5, `logon`, `restore` (riser), `balloon` | Agent `qmark` #02/#04/#06, Backgammon #3/#4 (bells), gm.dls voice oohs, crystal, halo pad | `crystal_*`, `glass_*`, `wine_glass_*`, `ui_glass_ping`, `soft_wind`, `whoosh_*` |
| Aquarium / eco | `balloon` A5, `hwout`, `xpding`, `print`, `ringout`, `restore`, `logon` | gm.dls seashore, birds, pan flute, kalimba | `drop_*`, `droplet_*`, `bubble*`, `underwater_*`, `fountain_*`, `nps_ocean_waves`, `creek_loop`, `bird_*`, `wind_chime_*`, `kalimba_c4` |
| Startup nostalgia | `startup`, `logon`, `logoff`, `shutdown`, `tada`, `chimes`, `ding`, `error`, `critstop` | Pinball launch `SOUND22`/`SOUND21`, bonus `SOUND50`, mission `SOUND9`; OOBE `title.wma` | `pc_286_startup`, `pc_old_desktop_boot`, `hdd_conner_spin`, `floppy_*`, `crt_on_off_degauss` |
| Slush, dreampunk, liminal | `startup` (slowed 3x = 19 s), `chord`, `shutdown`, `xpnotify`, `logon`, `ringout` (hum) | WMP tour beds slowed | `office_ambience_01`, `rain_on_window`, `choir_aah`, `phone_dial_tone_us`, `droplet_echoed`, `thunder_rumble` |
| Future funk, vaportrap, hardvapour | `chord` (stab), `tada` (hit), `critstop` C3 (kick), `ringout` (808), `menu`/`popup` (hats), `recycle` (snare), `batcrit` (alarm lead) | gm.dls slap bass, jazz guitar, drum kit (kick, snare, clap, hats, crash) | `relay_click` |

**3.11 edition.** Only `chimes`, `ding`, `ringin` and `ringout` exist there; every other NAME plays DING.WAV
(DNA.md appendix). Five presets in this draft play the same on 3.11: Reverse Ding Loop, Barber Chair Organ, Test
Pattern Tone, Sparkle Cascade and Sixteen-Bit Chimes. Their 8-bit grit suits late-night lo-fi and signalwave.

**Extra sources in the XP image worth a library-disc copy** (all are already in the shipped image; the guest or the
library tool must convert compressed ones to PCM, because `srhook.c` retunes PCM only):

- **Windows Messenger 4.7** (`C:\Program Files\Messenger`): `online.wav` (two-note chime, C5), `newalert.wav` (G5),
  `newemail.wav` (mallet arpeggio, D4), `type.wav`. The most "utopian virtual" sounds on the disk.
- **NetMeeting 3.01**: `Blip.wav` (bright bell, D#6, 0.9 s), `TestSnd.wav` (swelling chime phrase).
- **3D Pinball**: 60 sounds, 8-bit 11 kHz. Best: `SOUND50` (bonus, G#4), `SOUND9` (mission, C4), `SOUND1`
  (light show, 5 s), `SOUND21`/`SOUND22` (launch), `SOUND136`/`SOUND240`/`SOUND999` (unused struck tones).
- **Windows Media Player tour** (`...\Tours\WindowsMediaPlayer\Audio\Wav`): nine music beds of 3.9-15.9 s, around
  F#2-C#3. Ideal raw material for eccojam loops and slushwave pads.
- **MS Agent and Search Companion characters** (`merlin.acs`, `qmark.acs`, `rover.acs`, `earl.acs`): qmark #06 is a
  3.2 s welcoming swell (F#4); merlin #22 a 2 s sparkle (D5).
- **Game WAVE resources**: Backgammon #3/#4/#5/#8 (bells and struck tones), Hearts #1 (A#2 struck tone).
- **gm.dls** (Roland GS set, 235 instruments): the General MIDI sound of the 1990s and 2000s. Render single notes
  inside XP (section 6). The GM pads, EPs, vibes, sax and kits are the core sounds of utopian virtual and late-night
  lo-fi.
- **Microsoft Sam** (SAPI 5.1): the robot voice of signalwave and corporate-slogan presets. `library/sam_phrases.txt`
  already lists the phrases.
- **XP setup music** `title.wma`: an ambient welcome piece. It is WMA; render it to PCM in the guest first.

---

## 4. Preset sections and the top 10

Ten sections, 101 presets. Each preset has an intent, its sources, its chain, a voice idea and a draft DNA. The
status column says what it needs:

- **v2**: plays on main today with the 35 built-in sounds.
- **v2+library**: needs library-disc sounds. "lib" names are in the library lane's catalog already. "new" names are
  proposed in section 6.
- **v3**: a note in the chain column describes a v3 gene that would improve the preset. The DNA works in v2 now.

Macros follow the `preset-targets.md` convention: M1 brightness, M2 motion, M3 space, M4 character. The mod wheel
adds to M1 (DNA.md 5.4).

### 4.1 The top 10 (build and tune first; all v2)

| # | Preset | Section | Why first | DNA |
|---:|---|---|---|---|
| 1 | **Startup Loop Half Speed** | Eccojam | The startup figure, looped and slowed: the genre in one key. Lower keys screw it further. | `startup@55[@40]@0CP@0CP<E#8;A20S100R1500K56` |
| 2 | **Atrium Keys** | Mall | Soft EP chords from three shops away; the mallsoft core sound. | `xpding@25]<E#8U2~9Q-20/default@30]<<E#6U2~6L45O20Q25T-4;A8D1800S30R1400V70K47` |
| 3 | **Midnight Tines** | Late Night | A dusty EP for min9 chords, with VHS dullness and dust. | `xpding@20]#6U2~10/ringout@25[@35]><#6L70U2~12T2/recycle<<<#2FL10;A5D2000S30R700V80K59` |
| 4 | **Rounded Corner Chord** | Glass | A one-finger maj7 notification chord: the Aero optimism. | `xpnotify#12H0,4,7,11;A0D1500S0R1100K70` |
| 5 | **Glossy Bloom** | Glass | A glass pad with reversed sparkle, panned wide. | `logon@20[#8U2~8/xpding>>R#4L35Q-50T-3/chimes>R#4L30Q50O200T1;A600S90R2500K56` |
| 6 | **Paging Chime** | Mall | Notify's fourth is a store PA chime when slowed. Instantly recognizable. | `notify<E#8U2~4;A0R1500V60K62` |
| 7 | **Tank Bubbles** | Aqua | Rounded bloops for bouncy arpeggios. | `balloon<E>#8/hwout>@30]#4L40T-3;A0D400S0R300K81` |
| 8 | **Memory Of A Memory** | Slush | Startup slowed three octaves: a 19-second ghost drone. | `startup<<<E#12U3~18;A2000S100R6000K32` |
| 9 | **Chord Screw Down** | Eccojam | A stab that falls an octave twice, like a tape stop. | `chord@60]#6/chord@60]<#5O350L80/chord@60]<<#5O1050L60;A0S100R600K55` |
| 10 | **Disco Ball Stab** | Funk & Hard | A future-funk stab; macro 1 is a "filter" between a dull and a bright copy. | `chord@40]+#6/chord@40]<<>>#6;A0D350S20R150m1=50m11L0,120m12L120,0K55` |

Runners-up: **Lobby Vibes** (vibraphone tremolo drawn with `Ja`), **Sixteen-Bit Chimes** (plays on 3.11 too).

### 4.2 All sections

| Section | Serves | Count |
|---|---|---:|
| Mall | mallsoft, muzak, lounge, hotel lobby | 11 |
| Eccojam | eccojams, chopped-and-screwed loops, stutters | 10 |
| Late Night | late-night lo-fi, VHS pop, barber beats, forecast jazz | 10 |
| Signal | signalwave, broken transmission, idents, test tones, robot voices | 10 |
| Utopia | utopian virtual, GM presets, ringtones, chat-client sounds | 10 |
| Glass | Frutiger Aero, Aero Glass, "Vista aesthetic", Frutiger Metro | 10 |
| Aqua | aquarium, water, eco, plaza and console-channel jazz | 10 |
| Startup | operating-system nostalgia, Pinball, setup wizard | 10 |
| Slush | slushwave, dreampunk, liminal and backrooms ambience, hypnagogic | 10 |
| Funk & Hard | future funk, vaportrap and vaporhop, hardvapour | 10 |

### Mall

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Atrium Keys** | Soft electric-piano chords that sound three shops away. | Trim the bell strike, slow it one octave, echo it; a quieter, brighter copy enters 20 ms late. Two layers, slight unison wow, left/right split. | `xpding@25]<E#8U2~9Q-20/default@30]<<E#6U2~6L45O20Q25T-4;A8D1800S30R1400V70K47` | v2 |
| **Food Court Nylon** | A bossa-nova nylon pluck for one-finger comping. | COMB idiom: echo twice, then speed up, so the echo becomes a string resonance; slowed after. Pluck plus a quiet fixed click for the fingernail. | `default@20]EE><#10/menu<#4FL30;A0D900S0R300V90K75` | v2 |
| **Escalator Ascent** | A slow string pad that rises and drifts left to right, like riding up past a skylight. | Drop the attack, slow two octaves, echo; drawn envelope and pan envelope. One wide unison layer. | `logoff@30[<<E#12U3~10Ja0,0.900,100.4000,85Jp0,-60.6000,60;R3500K39` | v2 |
| **Empty Concourse** | Hold one key: distant shoppers under a slowed startup chord. A bed for a whole track. | The ambience is quiet and fixed; the startup bloom is slowed twice and echoed. Bed layer (fixed pitch) plus a pitched pad. | `mall_ambience_shopping_centre-#2FL40/startup<<E#12U2~12Ja0,0.2500,100;R4000V0K44` | v2+library: lib `mall_ambience_shopping_centre` |
| **Lobby Vibes** | Vibraphone with motor tremolo, the sound of a hotel-lobby jazz trio. | The sine-like Print bell, slowed and echoed. The tremolo is an 8-point drawn amplitude envelope. H0 only, so 12 voices of polyphony. **v3:** A looping amplitude envelope (repeat the last N points) would keep the tremolo going past 1 s. | `print<E#12Ja0,100.150,65.300,95.450,62.600,90.750,58.900,85.1050,55;R900V80K70` | v2 |
| **Paging Chime** | The two-tone public-address chime that comes before an announcement. | Notify already alternates a fourth; slowed once and echoed it is a store PA chime. Unison 2 for a cheap speaker chorus. | `notify<E#8U2~4;A0R1500V60K62` | v2 |
| **Department Strings** | Lush, polite string pad for the cosmetics floor. | Logon body slowed once; shutdown body slowed twice, quieter, entering later. Two layers, wide unison, pan apart. | `logon@20[<#8U3~14Q-35/shutdown@30[<<#8U2~10L50O150Q35;A600S90R2500K44` | v2 |
| **Elevator Alto** | A smooth-jazz alto sax line, slowed into a dream (needs the GM render). | A GM alto sax note rendered in Windows, slowed one octave and echoed. Mono lead with light unison. | `gm_alto_sax_c4<E#6U2~5;A40S85R700B5K48` | v2+library: new `gm_alto_sax_c4` |
| **Closing Announcement** | Last call: a falling cadence with pre-echo, then the lights go off. | PRE-VERB idiom (reverse, echo, reverse) after a slow-down, so echo arrives before the note. Big pool, chorus. | `shutdown<RER#12U2~8;A0S100R3000K44` | v2 |
| **Fountain Coins** | Bright bell plinks with a long, wet echo, as coins hit a fountain. | Ding with LONG-ECHO (slow, echo, speed up); a soft droplet mixed into the attack. Bell layer plus droplet layer, offset 10 ms. | `ding<E>#10/droplet_soft#4FL50O10;A0D2500S0R1800K79` | v2+library: lib `droplet_soft` |
| **Atrium Marimba** | Warm wood mallet for lounge riffs. | The Ding body is a soft marimba; slowed chord adds a quiet low bloom. Two layers. | `xpding#10/chord@10]<<#4L25T4;A0D700S0R400V90K59` | v2 |

### Eccojam

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Startup Loop Half Speed** | The last figure of the startup sound looped four times; lower keys screw it slower. | GRAIN (keep a slice), double it twice with @0CP, slow one octave, echo. Key-tracked on purpose: tape-style speed, so pitch and tempo fall together. | `startup@55[@40]@0CP@0CP<E#8;A20S100R1500K56` | v2 |
| **Logon Stutter** | A one-beat stutter: the same short slice repeated eight times, then the phrase continues. | Copy a short slice, paste it in front of itself three times (8 hits), then Insert the full logon after. One layer, fixed root. | `logon@10[@15]@0CP@0CP@0CP@99Ilogon<#8;A5S100R800K44` | v2 |
| **Chord Screw Down** | A chopped-and-screwed stab: the chord, then the same chord an octave down, then two. | Sound Recorder cannot slow only part of a buffer, so three layers do it: each one is slower and starts later. Three layers at O0 / O350 / O1050, each one octave lower; a tape-stop feel. | `chord@60]#6/chord@60]<#5O350L80/chord@60]<<#5O1050L60;A0S100R600K55` | v2 |
| **Reverse Ding Loop** | A backwards bell fragment looped into a hypnotic swell. | Reverse, keep the swell part, loop it 4x, echo. One layer. | `dingR@40[@0CP@0CPE#10;A10S100R1200K79` | v2; plays on 3.11 |
| **Fanfare Fragment** | The middle of the ta-da fanfare as a slowed four-beat loop. | GRAIN on the brass middle, loop 4x, slow, echo twice. Pool of 8, unison wow. | `tada@30[@50]@0CP@0CP<EE#8U2~10;A30S100R1500K48` | v2 |
| **Ringback Lullaby** | A phone ringback tone looped and slowed into a pulsing drone. | Loop 8x, slow twice; the beating of the two tones becomes a slow tremolo. One layer. | `xpringout@0CP@0CP@0CP<<E#8U2~6;A300S100R2000K45` | v2 |
| **Gate Echo Startup** | The whole startup slowed with echoes between, then cut into a chopped gate by Delete. | BLUR-DOWN (slow, echo, slow, echo) with a delete-after at 60 % to end on the bloom. Big pool; a bed key. | `startup<E<E@60]#12U2~10;A100S100R3500K44` | v2 |
| **Hold Music Loop** | A public-domain hold-music excerpt cut to one bar and looped (library sound). | GRAIN of about 2 s, loop 4x, echo; tune by ear (no measured root). Fixed pitch until tuned. | `holdmusic_lunar_hold_music@20[@10]@0CP@0CPE#6F;A20S100R800` | v2+library: lib `holdmusic_lunar_hold_music` |
| **Notify Ping-Pong** | A two-note chime looped, then echoed left and right on the beat. | Loop 2x; three offset layers make a tempo delay (500 ms = 120 BPM quarter). Taps at 0/500/1000 ms, panned L/R/L, falling level. **v3:** Tempo-synced offsets (O in beats) would follow the DAW tempo. | `notify@0CP<#6/notify@0CP<#5O500Q-70L60/notify@0CP<#5O1000Q70L35;A0S100R900K62` | v2 |
| **Shutdown Ascending** | The falling shutdown cadence played backwards, looped twice: the screw-up. | Reverse, loop 2x, slow, echo. One layer. | `shutdownR@0CP<E#10U2~8;A0S100R2500K44` | v2 |

### Late Night

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Midnight Tines** | A dusty electric piano for maj7 and min9 voicings at 70 BPM. | DX-style tine (xpding strike) over a looped ringout body; DECIMATE round trip on the body for VHS dullness; crumple dust. Three layers; dust is fixed pitch and quiet. | `xpding@20]#6U2~10/ringout@25[@35]><#6L70U2~12T2/recycle<<<#2FL10;A5D2000S30R700V80K59` | v2 |
| **News Break Strings** | Synth strings from a 1980s local news break, slightly out of tune. | Body only, slowed, decimated (><), wide unison. One layer, wide chorus. | `logoff@30[<><#12U4~18;A400S90R1800K51` | v2 |
| **Velvet Fretless** | A round fretless-bass slide sound for walking lines (GM render). | GM fretless, unchanged; a quiet slowed rising bloop under it gives the slide. Bend range 12 so the wheel slides. | `gm_fretless_c2#6/hwin<<@40]#2L30;A5D1200S60R250B12K36` | v2+library: new `gm_fretless_c2` |
| **Tape Sax** | A tenor sax note slowed and smeared, as on a worn VHS (GM render). | Slow, decimate, echo. Wide wow unison; macro 2 (motion) opens the wow from 8 to 40 cents. | `gm_tenor_sax_c3<><E#6U2~8;A50S85R900B4m2=0m21C8,40K36` | v2+library: new `gm_tenor_sax_c3` |
| **Rainy Window Keys** | Soft keys and rain on the glass, for a sleepy hook. | Default bell trimmed and slowed for a felt piano; rain is a fixed bed. Keys layer plus fixed rain layer. | `default@40]<#10U2~6/rain_on_window-#2FL30;A5D1600S20R900K63` | v2+library: lib `rain_on_window` |
| **Weather Map Pad** | A warm synth pad for a forecast scroll at 2 a.m. | Startup body slowed with echo; logon slowed twice behind it. Two layers, panned. | `startup@30[<E#8U2~8Q-25/logon<<#8U2~12L50Q25;A700S95R2500K56` | v2 |
| **Barber Chair Organ** | A soft drawbar organ for slowed smooth-jazz loops. | LOOP-OSC on ringout, then octave and fifth by harmony. H0,12,19 at U1 keeps chords possible. | `ringout@20[@30]@0CP@0CP@0CP#12H0,12,19;A20D300S70R150K69` | v2; plays on 3.11 |
| **VHS Bell Pad** | A bright bell-pad hybrid with tape wow, the brighter VHS-pop color. | Reversed chime sparkle, a wow-heavy logon body. Two layers. | `logon@20[<><#10U3~20/chimesR#6U2~15L60T1;A250S90R2000K44` | v2 |
| **Slow Jam Bass** | A soft synth bass for slowed R&B. | The error tone slowed twice and trimmed, a little clip for body. Mono feel: pool 4. | `error<<@30]+#4;A2D500S60R180V80K63` | v2 |
| **Static Lullaby** | Music box through a cheap TV speaker. | Chimes front decimated hard (>>><<<), print bell under it. Two layers. | `chimes@30]>>><<<#8/print#6L50T-3;A0D1500S0R1200K79` | v2 |

### Signal

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Channel Surf** | Each key jumps to another "channel": a chime ident, a tone, a crumple, a voice. | SPLICE-SEQ: Insert File chains short pieces into one 3-second strip. Fixed pitch, so every key starts the same strip; velocity sets level. | `notify@40]IringoutIrecycleIsam_welcomeIchimes#8F;A0S100R200` | v2+library: new `sam_welcome` |
| **Test Pattern Tone** | The color-bars test tone: a steady sine, with a slow fade at the end of the night. | LOOP-OSC on the steadiest slice; no unison, no echo. One layer. | `ringout@30[@20]@0CP@0CP@0CP@0CP#8;A30S100R300K69` | v2; plays on 3.11 |
| **Station Ident** | A three-note TV station logo: chime, fanfare tail, a voice. | Three layers enter at 0/300/900 ms: an ident sequence on one key. Pitched chime and fanfare; fixed voice. | `chimes#4/tada@40[#6O300T-5/sam_system_ready#2FO900L80;A0S100R1200K79` | v2+library: new `sam_system_ready` |
| **Forecast Voice** | A slowed robot forecaster, for spoken hooks (Sam render). | Slowed once and echoed; key-tracked so lower keys are lower and slower. One layer. | `sam_forecast<E#6;A0S100R400` | v2+library: new `sam_forecast` |
| **Broken Transmission** | Speech and tone torn into pieces: a chopped, reversed, decimated strip. | Delete-after/before cut the voice; reverse half; decimate; mix the battery tone at 50 %. Fixed pitch. | `sam_portal@20[@50]R>><<@50Mbatcrit#6F;A0S100R150` | v2+library: new `sam_portal` |
| **Degauss Swell** | The CRT degauss thump as a dark, pitched swell (library sound). | Slowed once, reversed for a swell, echoed. Tune by ear; key-tracked. | `crt_degaussR<E#6;A0S100R1500` | v2+library: lib `crt_degauss` |
| **Modem Choir** | Dial-up handshake slowed two octaves into an eerie chord. | Slow twice; the 30 s cap skips a step if the excerpt is too long, so trim first. Wide unison. | `modem_handshake_early@40]<<#8U3~20;A800S90R2500` | v2+library: lib `modem_handshake_early` |
| **Number Station** | A voice reading numbers over a tone, for the eerie end of signalwave (Sam render). | Voice fixed; the ringback tone looped underneath as a carrier. Two layers. | `sam_numbers#4F/xpringout@0CP@0CP@0CP#6L40;A0S100R300K69` | v2+library: new `sam_numbers` |
| **Off-Air Hiss** | Tape and TV hiss as a texture layer under everything. | Crumple decimated and looped into hiss; volume down. Fixed, quiet. | `recycle>>><<<@0CP@0CP@0CP@0CP-#4F/xprecycle<<@0CP@0CP-#2FL60;A400S100R800G-10` | v2 |
| **Satellite Bulletin** | A 1960 newsreel voice cut to one phrase and echoed (library sound). | Keep a 2-3 s slice; echo; fixed pitch. One layer. | `newsreel_tiros_ii_satellite_1960@10[@12]E#4F;A0S100R600` | v2+library: lib `newsreel_tiros_ii_satellite_1960` |

### Utopia

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Contact Online** | The two-note "a contact is online" chime as a melodic instrument (Messenger render). | As it is, slight echo; the source is the meaning. One layer, chorus. | `msgr_online#10U2~4E;A0R700K72` | v2+library: new `msgr_online` |
| **Conference Blip** | A bright, short call-client bell, for arpeggios (NetMeeting). | Front only, long-echo. One layer. | `netm_blip@50]<E>#10;A0D600S0R500K87` | v2+library: new `netm_blip` |
| **Polyphonic Ringtone** | An early-2000s polyphonic ringtone lead: bright, square-ish, cheerful. | LOOP-OSC on a short slice, CLIP twice, one octave up. Pool 8; staccato envelope. | `batlow@5[@20]@0CP@0CP@0CP++>#8;A0D180S55R40K55` | v2 |
| **Fantasy Module Pad** | The General MIDI "new age" pad, made glossier with a reversed chime halo. | GM pad as it is; chimes reversed and quiet. Two layers. | `gm_newage_c5#10U2~6/chimesR#6L35T5;A300S90R2200K72` | v2+library: new `gm_newage_c5` |
| **Sushi Bar Kalimba** | A clean, cheerful GM kalimba with a 16th-note echo. | Long-echo; three taps by offset at 125 ms (120 BPM 16ths). Three layers, panned. | `gm_kalimba_c5#6/gm_kalimba_c5#5O125Q-60L55/gm_kalimba_c5#5O250Q60L30;A0D800S0R400K72` | v2+library: new `gm_kalimba_c5` |
| **Virtual Lobby Steel Drum** | GM steel drum for tropical demo-disc riffs. | COMB (EE>) bakes in a metallic ring; then slow back. One layer. | `gm_steeldrum_c5EE><#10;A0D900S0R500K72` | v2+library: new `gm_steeldrum_c5` |
| **Synergy Pad** | A sung corporate word under a glossy pad: hold one key for a slogan bed (Sam render). | Voice slowed into a vowel smear; logon pad under it. Two layers. | `sam_synergy<<E#4F/logon<#10U2~8L80;A400S95R2500K44` | v2+library: new `sam_synergy` |
| **New Mail Arp** | A soft mallet arpeggio from the mail alert, playable (Messenger render). | As it is, plus a quiet octave baked in (OCT-BAKE). One layer. | `msgr_emailC>@0X#10;A0R600K74` | v2+library: new `msgr_email` |
| **Bubble Sign-In** | A rising bloop then a two-note alert: the "you are signed in" moment. | Bloop at 0 ms, alert at 180 ms. Two layers. | `hwin>#6/msgr_alert#6O180T5;A0S100R500` | v2+library: new `msgr_alert` |
| **Demo Disc Brass** | A glossy synth-brass stab from a 1990s demo disc (GM render). | GM synth brass plus the ta-da attack for bite. Two layers. | `gm_synbrass_c4#8U2~8/tada@15]#4L40;A5D600S60R300` | v2+library: new `gm_synbrass_c4` |

### Glass

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Crystal Taskbar** | A clean glass-bell pluck with a long, bright halo. | Print bell with a PRE-VERB halo (reverse, echo, reverse); the crystal bell is quiet under it. Two layers. | `printRER#8/crystal_bell_bb5@30]#6L40O5;A0D2500S0R2000K82` | v2+library: lib `crystal_bell_bb5` |
| **Glossy Bloom** | A pad that opens like a window fading in: soft attack, bright top, gentle shimmer. | Logon body; reversed bright bells as sparkle. Three layers, shimmer panned out. | `logon@20[#8U2~8/xpding>>R#4L35Q-50T-3/chimes>R#4L30Q50O200T1;A600S90R2500K56` | v2 |
| **Sparkle Cascade** | One key plays a rising four-note glass glissando. | Reversed chimes; harmony gives the chord, offsets give the strum. Four layers at 0/45/90/135 ms. **v3:** A strum gene (each harmony voice O ms later) would do this in one layer. | `chimesR#3/chimesR#3O45T4/chimesR#3O90T7/chimesR#3O135T12;A0D1800S0R1500K79` | v2; plays on 3.11 |
| **Rounded Corner Chord** | A soft major-7th chord pluck, the confident "notification" of 2007. | XP Notify voiced as maj7 (H0,4,7,11). One finger, one chord; pool 12. | `xpnotify#12H0,4,7,11;A0D1500S0R1100K70` | v2 |
| **Aurora Glass Pad** | A singing glass rim, slowed and wide, for slow keynotes. | Slowed once, echo; tune by ear. Wide unison. | `wine_glass_singing_half_full<E#10U3~10;A900S95R3000` | v2+library: lib `wine_glass_singing_half_full` |
| **Lens Flare Riser** | An upward whoosh and a reversed bell meet on the downbeat. | Restore slowed into a long rise; reversed ding ends with the hit. Two layers. | `restore<<#4F/dingR#8;A0S100R600K79` | v2 |
| **Glass Keyboard** | Clean digital EP with a glass edge, for hopeful chord progressions. | Default bell strike over a ringout body. Two layers. | `default@25]#8/ringout@25[@35]#8L60T-6;A0D1600S30R700K75` | v2 |
| **Tray Balloon Bell** | A tiny pop plus a soft bell, the sound of a system-tray balloon tip. | Balloon mixed into the xpding attack (MIX-TRANSIENT). One layer. | `xpdingMballoon#12;A0D900S0R500K59` | v2 |
| **Clear Sky Choir** | An airy "ooh" pad that sounds clean, not dark (GM render). | GM voice oohs; soft wind under it. Two layers. | `gm_oohs_c4#10U2~8/soft_wind-#2FL30;A700S95R2500` | v2+library: new `gm_oohs_c4`; lib `soft_wind` |
| **Reflection Ping** | A glass ping with a ping-pong echo, panned left then right. | Three offset taps. Three layers. | `ui_glass_ping#6Q-40/ui_glass_ping#5O300Q70L55/ui_glass_ping#5O600Q-70L30;A0S100R600` | v2+library: lib `ui_glass_ping` |

### Aqua

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Tank Bubbles** | Rounded bloops for bouncy arpeggios. | Balloon with long-echo; a quiet falling bloop for body. Two layers. | `balloon<E>#8/hwout>@30]#4L40T-3;A0D400S0R300K81` | v2 |
| **Reef Pad** | Hold one key: water movement and a calm pad. | Underwater ambience fixed and quiet; logon slowed. Two layers. | `underwater_movement-#2FL40/logon<#10U2~8;A1200S90R3500V0K44` | v2+library: lib `underwater_movement` |
| **Droplet Marimba** | A wood mallet with a water drop on every strike. | MIX-TRANSIENT: the plink mixed at the start. One layer. | `xpdingMdrop_plink#12;A0D800S0R400K59` | v2+library: lib `drop_plink` |
| **Plaza Bossa Keys** | Cheerful jazzy keys for a shop channel, in a bright room (GM render). | GM vibes and GM nylon guitar at equal level. Two layers. | `gm_vibes_c4#8/gm_nylon_c4#6L70O8;A0D1200S20R500` | v2+library: new `gm_nylon_c4`, `gm_vibes_c4` |
| **Eco Wind Chimes** | Wind chimes and birds, the solar-panel brochure sound. | Chime pitched; bird enters later, fixed. Two layers. | `wind_chime_528hz#8/bird_hermit_thrush-#2FO400L40;A0D2500S0R2000K72` | v2+library: lib `bird_hermit_thrush`, `wind_chime_528hz` |
| **Fishbowl Glass** | A bright, short glass-bowl tone with a watery echo. | Front kept, long-echo. One layer. | `crystal_bowl_g4@40]<E>#10;A0D2000S0R1500K67` | v2+library: lib `crystal_bowl_g4` |
| **Lagoon Flute** | A breathy pan flute over waves (GM render). | GM pan flute; ocean fixed and quiet. Two layers. | `gm_panflute_c5#8U2~5/nps_ocean_waves-#2FL25;A80S85R700K72` | v2+library: new `gm_panflute_c5`; lib `nps_ocean_waves` |
| **Bubble Sweep** | Bubbles slowed into a rising wash. | Bubbles slowed twice; restore whoosh. Two fixed layers. | `tiny_bubbles<<#4F/restore<#4FO100L60;A300S100R1500` | v2+library: lib `tiny_bubbles` |
| **Hydro Kalimba** | Kalimba with a water drop and a bowl ring. | Kalimba as it is; droplet at 5 ms. Two layers. | `kalimba_c4#10/droplet_soft#4FO5L45;A0D900S0R500` | v2+library: lib `droplet_soft`, `kalimba_c4` |
| **Aquarium Screensaver** | Slow glass bells over a filter hum, for a fish-tank screensaver. | Print slowed, PRE-VERB; ringout slowed twice as a hum. Two layers. | `print<RER#10/ringout<<#4L30T1;A400S90R2500K70` | v2 |

### Startup

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Power-On Ceremony** | Hold one key: power hum, a seek clunk, then the startup bloom. | Three layers at 0/600/1400 ms. Fixed hum and clunk; pitched bloom. | `hdd_conner_spin-#2F/floppy_seek_clunk#2FO600/startup#10O1400;A0S100R3000V0K68` | v2+library: lib `floppy_seek_clunk`, `hdd_conner_spin` |
| **Login Wish** | The logon phrase as a soft, playable pad with chorus. | As it is, slowed once; chorus. Pool 12. | `logon<#12U2~8;A100S95R2500K44` | v2 |
| **Goodbye Pad** | The logoff phrase stretched into a slow, sad string line. | Slow twice, echo. One layer. | `logoff<<E#12U2~10;A400S95R3000K39` | v2 |
| **Ninety-Five Bloom** | A legacy-style Ab major bloom built from parts, for a short ceremony chord. | Startup body; chimes sparkle; ta-da attack under it. Three layers. | `startup@20[#8U2~6/chimes>R#4L40T1/tada@15]#4L30T-4;A20S90R2500K68` | v2 |
| **Sixteen-Bit Chimes** | The original 8-bit chimes, slowed and echoed; plays on the 3.11 edition too. | Slow once, echo, long-echo. One layer. | `chimes<E<E>#12;A0D2500S0R2000K67` | v2; plays on 3.11 |
| **Hyperspace Launch** | The pinball launch ramp as a pitched riser and hit (Pinball render). | Launch at 0 ms, bonus chord at 700 ms. Two layers. | `pin_hyper#6/pin_bonus#6O700T-4;A0S100R1200K40` | v2+library: new `pin_bonus`, `pin_hyper` |
| **Mission Complete Pad** | The pinball mission tone slowed into a triumphant pad. | Slow once, echo, chorus. One layer. | `pin_mission<E#12U2~8;A300S95R2000K48` | v2+library: new `pin_mission` |
| **Setup Wizard Swell** | The question-mark assistant swell, gentle and welcoming. | As it is with chorus. One layer. | `qmark_swell#12U2~6;A200S95R2000K66` | v2+library: new `qmark_swell` |
| **Shutdown Choir** | Shutdown, slowed, reversed then forward: it rises before it falls. | Copy, reverse, then Paste Insert the forward copy at the end. One layer. | `shutdown<CR@99P#12U2~6;A0S100R3000K44` | v2 |
| **Boot Beep Bass** | A short tone stack as a sub bass: the click of a power switch on top. | Battery tone slowed; relay click at the start. Two layers. | `batlow<@30]#6/relay_click#2FL60;A0D600S50R150K31` | v2+library: lib `relay_click` |

### Slush

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Ten Minute Chord** | A chord stretched four times and echoed: hold it for a whole track. | BLUR-DOWN twice (slow, echo, slow, echo). Pool 12; very long release. | `chord<E<E#12U2~12;A1500S100R6000K31` | v2 |
| **Fluorescent Hum** | The empty-office buzz: a decimated low tone and office air. | LOOP-OSC on ringout, slowed two octaves, CLIP once; office ambience fixed. Two layers. | `ringout@30[@20]@0CP@0CP@0CP@0CP<<+#4/office_ambience_01-#2FL25;A800S100R2000V0K45` | v2+library: lib `office_ambience_01` |
| **Carpet Corridor** | A distant, heavily echoed muzak chord from another room. | Slow twice, echo three times, volume down. One layer. | `xpnotify<<EEE--#12U2~10;A600S90R5000K46` | v2 |
| **Neon Rain Pad** | Dreampunk: a cold, wide pad with a rain bed, after the film scores. | Shutdown slowed twice, reversed, echo; rain fixed. Two layers. | `shutdown<<RE#12U3~16/rain_on_window-#2FL25;A1500S95R5000K32` | v2+library: lib `rain_on_window` |
| **Memory Of A Memory** | Hypnagogic: startup slowed three times, a ghost of itself. | Slow three times (19 s), echo once. Wide chorus. | `startup<<<E#12U3~18;A2000S100R6000K32` | v2 |
| **Liminal Pool Room** | Wet, tiled-room echo on a single water drop, for still scenes. | Slow, echo twice. Fixed pitch. | `droplet_echoed<EE#8F;A0S100R3000` | v2+library: lib `droplet_echoed` |
| **Sleep Mode** | A soft swell that breathes in and out, drawn by an envelope. | Logon slowed; a 5-point breathing envelope; pan envelope. One layer. | `logon<<#12U2~8Ja0,0.2000,100.4000,35.6000,90.8000,30Jp0,-40.8000,40;R3000K32` | v2 |
| **Dial Tone Drone** | A phone dial tone slowed into a deep, eerie drone. | Slow twice; echo. Tune by ear (350 + 440 Hz source). | `phone_dial_tone_us@50]<<E#8U2~6;A1000S100R3000` | v2+library: lib `phone_dial_tone_us` |
| **Faraway Choir** | A choir behind a wall: slowed, muffled, echoed. | Slow once, decimate, echo twice. Wide unison. | `choir_aah<><EE#10U2~12;A1200S95R4000K45` | v2+library: lib `choir_aah` |
| **Ambient Elevator** | An elevator ride slowed into a long, falling drone (library sound). | Slow once (if under 15 s), echo. Fixed pitch. | `office_elevator_ride<E#4F;A500S100R3000V0` | v2+library: lib `office_elevator_ride` |

### Funk & Hard

| Preset | Intent | Chain and voices | Draft DNA | Status |
|---|---|---|---|---|
| **Disco Ball Stab** | A filtered-house chord stab for future funk at 118 BPM. | Chord front, CLIP once; ta-da attack. Speed is the filter: macro 1 fades a dull copy into a bright copy. Two layers; macro 1 = brightness. | `chord@40]+#6/chord@40]<<>>#6;A0D350S20R150m1=50m11L0,120m12L120,0K55` | v2 |
| **City Pop Bass** | A slap-style bass for octave-jumping disco lines (GM render). | As it is, CLIP once for bite. Mono-ish: pool 4. | `gm_slap_c2+#4;A0D400S50R100V100K36` | v2+library: new `gm_slap_c2` |
| **Sidechain Pad** | A pad that ducks on every beat, drawn by the envelope (118 BPM eighths). | Logon looped; the envelope gates it eight times. One layer. **v3:** A loop flag on Ja would repeat the duck for as long as the key is held. | `logon@20[@0CP#12U2~10Ja0,0.200,100.254,10.454,100.508,10.708,100.762,10.962,100;R300K56` | v2 |
| **Vapor Sub Boom** | A long sub for vaporhop / vaportrap beats; wheel bends a fifth. | 808 Sub idiom: ringout body slowed three octaves; a click on top. Two layers; bend range 7. | `ringout@20[@40]<<<#6/start<#2FL50;A0D2500S40R200B7K33` | v2 |
| **Lazy Trap Hat** | A tiny closed hat for skittering hi-hats. | Menu click and popup burst, fixed. Two fixed layers; velocity matters. | `menu#4F/popup>#4FL40;A0S100R30V100` | v2 |
| **Gabber Brick** | A distorted hardvapour kick: clipped, short, tuned low. | Front only, slowed twice, CLIP four times. Mono. | `critstop@20]<<++++#4;A0D250S0R80V100K36` | v2 |
| **Hoover Alarm** | A harsh, detuned alarm lead for hardvapour drops. | LOOP-OSC on the warning tone, clip, wide unison. U4 on a pool of 8. | `batcrit@10[@20]@0CP@0CP@0CP+++#8U4~25;A0S100R200K48` | v2 |
| **Funk Guitar Chop** | A muted jazz-guitar chop for disco upstrokes (GM render). | Keep the first 25 %; an octave-up copy 30 ms later makes an upstroke. Two layers. | `gm_jazzgtr_c4@25]#6/gm_jazzgtr_c4@25]#6O30T12L50;A0D200S0R60` | v2+library: new `gm_jazzgtr_c4` |
| **Anime Sparkle Hit** | A bright crash-and-chime hit for the start of a future-funk loop. | Ta-da attack, chimes high, a GM crash fixed. Three layers. | `tada@25]#6/chimes>#4L50T5/gm_crash#2FL60;A0D900S0R700` | v2+library: new `gm_crash` |
| **Screwed Kit** | A drum kit made of Windows clicks, slowed down: kick, snare, hat in one key-range. | Kick, snare and hat layers; key-tracked so each key is another tuning. Three layers. | `critstop@15]<<#4/recycle@30]<#4FL70/menu<#4FL50;A0S100R80K48` | v2 |

---

## 5. Style guide

Rules for building presets in these genres with this instrument.

### 5.1 Every genre

1. **Start from a source that already means something.** The startup, logon, shutdown, notify and chime sounds
   carry the memory. Change them enough to play, not enough to hide them.
2. **Choose the speed with `K`, not only with `<`.** `K` is the key that plays the buffer at its built speed. Put
   `K` in the range the player uses. Use `T-2` to `T-5` for the classic "a little slowed" feel. Use `<` only for
   octave-sized slowdowns.
3. **Register follows speed.** A `<<` layer is two octaves low and stays there. To keep its slowed character, play it
   where it sounds. Do not transpose it back up with `T+24`: that cancels the slowdown.
4. **Tune each layer to its pitch class.** Main layer: `K` = its root after its steps. Other layers: `T` corrects
   the pitch class only (`-6..+5`). Check bell roots by ear; bells have inharmonic partials.
5. **Count recorders.** One note uses (harmony intervals x unison) recorders per layer. Keep the total per note at
   6 or less for playable chords; use 8 or more only in "hold one key" presets.
6. **Macros mean the same thing in every preset:** M1 brightness (crossfade a `><` or `<<>>` copy against a clean
   copy), M2 motion (unison spread `C`, pan), M3 space (level of an echo layer), M4 character (clip or noise layer
   level).
7. **Name presets by place, time or object**, never by artist, album, brand or product. Good: "Atrium Keys",
   "Paging Chime". Bad: any name that contains an artist, a company or a product.
8. **Write a one-line intent.** Say where the sound lives (a mall, a forecast, a fish tank) and what to play.

### 5.2 Vaporwave family (Mall, Eccojam, Late Night, Signal, Slush)

- **Slow, then echo, then slow again** (`<E<E`). The order is the effect: echoes come out longer and lower.
- **Echo is the reverb.** Use two or three `E` steps. Add room with `silence_*` inserts when the echo is cut short.
- **Loops are key-tracked.** In an eccojam preset each key is a different screw amount. Use `F` only for spoken
  words and beds.
- **Keep seams.** A loop seam that clicks is part of the style. Trim at a quiet point when the click is too loud.
- **Dirt goes on its own layer:** crumple dust, hiss, `><` dullness. Keep it at `L10` to `L30` so the player can
  turn it off with a macro.
- **Harmony:** maj7 (`H0,4,7,11`), min9 (`H0,3,7,10,14`), 6/9 (`H0,4,7,9,14`). Play ii-V-I with single notes on
  an EP preset, or with one-finger chord presets.
- **Tempo:** eccojams and slushwave have no beat or a slow one; late-night lo-fi about 70-90 BPM; screwed edits at
  60-70 BPM [W-cs].
- **Long release.** `R1500` to `R6000`. Slushwave pads also need `A1000` or more.

### 5.3 Frutiger Aero family (Glass, Aqua, Utopia, Startup)

- **Clean, not dirty.** No `><`, no clip. Use full-band sources: `print`, `xpnotify`, `chimes`, `ding`, `logon`,
  glass and water library sounds.
- **Gloss = reversed sparkle.** Add a quiet `R` or `RER` copy of a bright bell one or two octaves up, panned away
  from the body.
- **Width:** pan layers apart (`Q-50`/`Q50`) and use `Jp` slow pan on pads.
- **Water is a transient.** Mix a drop or bubble into the attack (`Mdrop_plink`) instead of a separate layer, to save
  recorders.
- **Echo on the beat.** Aero delays are clean and tempo-based: use offset layers (`O250`, `O500`) with falling level.
- **Harmony:** maj7, maj9 (`H0,4,7,11,14`), sus2 (`H0,2,7`), add9. Bright major keys. Mid-tempo.
- **Utopian virtual leaves presets as they are.** The GM sound, the ringtone or the chat chime is the point. Do not
  slow it down.

### 5.4 Funk and hard

- **Future funk:** short stabs (`@40]`), little release (`R100`-`R200`), macro 1 as the filter sweep, `Ja` gates for
  the pumping sidechain feel. 110-130 BPM [SF][NI].
- **Vaportrap and vaporhop:** long 808 subs (`ringout ... <<<`), bend range 7 or 12, tiny hats from `menu` and
  `popup`.
- **Hardvapour:** clip four times (`++++`), short decay, low `K` for kicks.

### 5.5 Before a preset ships

1. Run it through `parse()` (canonical, no unknown NAME).
2. Render it with `tools/batch_render.py` or the custom test host (`tools/testhost`). Do not use a commercial DAW
   for the check.
3. Listen at three keys: `K`, `K-12`, `K+12`. Fix `K` if the useful range is not where a player expects it.
4. Check that one held chord does not steal its own voices.

---

## 6. Library-disc additions

The presets marked "new" need these sounds on the library disc (DNA.md 5.5). Names use `_`, so they never clash
with built-in names. Each one comes from our own XP image, from a render made inside it, or is generated.

| Name(s) | Source | How to make | Root |
|---|---|---|---|
| `silence_250`, `silence_1000`, `silence_4000` | generated | PCM 22050 Hz 16-bit mono zeros. For the "echo with room to ring" method (section 2); no draft preset needs them yet. | - |
| `msgr_online`, `msgr_alert`, `msgr_email`, `msgr_type` | `C:\Program Files\Messenger\{online,newalert,newemail,type}.wav` | MS-ADPCM to PCM (type.wav is PCM) | C5, G5, D4, - |
| `netm_blip`, `netm_tune` | `C:\Program Files\NetMeeting\{Blip,TestSnd}.wav` | copy | D#6, G#6 |
| `pin_launch`, `pin_hyper`, `pin_bonus`, `pin_mission`, `pin_start`, `pin_bell`, `pin_low` | Pinball `SOUND22`, `21`, `50`, `9`, `1`, `136`, `999` | copy (8-bit 11 kHz PCM) | F3, E2, G#4, C4, D4, G4, E2 |
| `oobe_click` | `system32\oobe\images\clickerx.wav` | copy | - |
| `qmark_swell`, `qmark_ding`, `merlin_sparkle` | `qmark.acs` #06, #04; `merlin.acs` #22 | carve from the .acs, then PCM | F#4, D4, D5 |
| `bgm_bell`, `bgm_low` | Internet Backgammon WAVE #4, #5 | carve, copy | A5, A3 |
| `wmp_bed1`, `wmp_bed6` | WMP tour `wmpaud1.wav`, `wmpaud6.wav` | MS-ADPCM to PCM | C#3, F#2 |
| `gm_*`: 14 used by the draft (`gm_vibes_c4`, `gm_nylon_c4`, `gm_alto_sax_c4`, `gm_tenor_sax_c3`, `gm_fretless_c2`, `gm_slap_c2`, `gm_jazzgtr_c4`, `gm_synbrass_c4`, `gm_oohs_c4`, `gm_newage_c5`, `gm_kalimba_c5`, `gm_steeldrum_c5`, `gm_panflute_c5`, `gm_crash`); 23 more proposed in `library_proposals` of the JSON (EPs, strings, choir, pads, kit) | `system32\drivers\gm.dls` through the Microsoft GS Wavetable synth | In XP: play one note (velocity 100, 2-4 s, release included) on the named GM program and record it with Sound Recorder at 22050 Hz 16-bit. Drums: GM channel 10 notes 35-49. | as named |
| `sam_*` (`sam_welcome`, `sam_synergy`, `sam_portal`, `sam_forecast`, `sam_system_ready`, `sam_numbers`, ...) | Microsoft Sam, SAPI 5.1 | Speak the phrase from `library/sam_phrases.txt` and record it, as that file says. `sam_forecast`: "your local forecast". `sam_numbers`: "four. seven. two. nine." | - |

**Licensing note.** Every source above is part of Windows XP as it is in our shipped image, or a render made by
software in it. That is the same status as the 35 Media sounds. The library lane decides whether renders go on the
disc or are made on first use.

---

## 7. v3 proposals

These genes would help the genres here. None is in DNA v2. Each one is outside the preset-engine-2 scope (start and
end points, voice modes, tape keyboard, granular). If engine-2 covers one of them, engine-2 wins.

| Gene | Meaning | Why | Feasibility |
|---|---|---|---|
| `W`N | wow: each new note gets a random detune in ±N cents (host side) | Tape wobble that changes from note to note. Unison is static. | Easy: the host already computes the rate per note. |
| `Ja` loop flag, e.g. `Ja!3` | after the last point, repeat the last 3 points while the key is held | Vibraphone tremolo, sidechain pump, trance gates without the 8-point limit. | Host and guest: the envelope ramp already runs in steps of about 10 ms. |
| `O`Nb | offset in beats (N/16 of a quarter) instead of ms | Tempo-synced echoes and strums that follow the DAW tempo. | Host only: the plugin knows the tempo. |
| strum `Hs`N | each harmony voice starts N ms after the previous one | Glass glissandi and guitar strums in one layer (saves layers). | Host only: the `on` line already has a delay field. |
| round robin `Y` | the layer's NAME list `a|b|c` is used in turn, one per note | Varied water drops, clicks and hats. | Guest must build several buffers per layer; pool cost. |

---

## 8. Sources

- [W-vw] Wikipedia, "Vaporwave": https://en.wikipedia.org/wiki/Vaporwave
- [W-ecco] Wikipedia, "Chuck Person's Eccojams Vol. 1": https://en.wikipedia.org/wiki/Chuck_Person%27s_Eccojams_Vol._1
- [W-fsv] Wikipedia, "Far Side Virtual": https://en.wikipedia.org/wiki/Far_Side_Virtual
- [DiS] Drowned in Sound, review of *Far Side Virtual*: https://drownedinsound.com/articles/4143929
- [W-hyp] Wikipedia, "Hypnagogic pop": https://en.wikipedia.org/wiki/Hypnagogic_pop
- [W-cs] Wikipedia, "Chopped and screwed": https://en.wikipedia.org/wiki/Chopped_and_screwed
- [BC] Bandcamp Daily, S. Chandler, "Genre As Method: The Vaporwave Family Tree, From Eccojams to Hardvapour" (2016): https://daily.bandcamp.com/lists/vaporwave-genres-list
- [BCamp-pm] 猫 シ Corp., *Palm Mall*, Bandcamp: https://noproblematapes.bandcamp.com/album/palm-mall
- [MG-sig] Microgenre Music, "What is Signalwave?": https://microgenremusic.com/articles/what-is-signalwave/
- [MG-slush] Microgenre Music, "What is Slushwave?": https://microgenremusic.com/articles/what-is-slushwave/
- [S-dp] Wikipedia, "Dreampunk": https://en.wikipedia.org/wiki/Dreampunk
- [SF] Stereofox, "Future Funk: genre origin, history": https://www.stereofox.com/articles/future-funk-genre-origin-history-playlists/
- [NI] Native Instruments blog, "Future funk music": https://blog.native-instruments.com/future-funk-music/
- [Wired] Wired, lo-fi Weather Channel videos (mirror): https://wirednews.pages.dev/story/vaporwave-weatherwave-youtube-climate-change
- [AAJ] All About Jazz, "The Weather Channel's smooth jazz strikes chord with viewers": https://news.allaboutjazz.com/the-weather-channels-smooth-jazz-strikes-chord-with-viewers.php
- [W-fa] Wikipedia, "Frutiger Aero": https://en.wikipedia.org/wiki/Frutiger_Aero
- [FAA] Frutiger Aero Archive forum, "What makes Frutiger Aero music sound like Frutiger Aero?": https://forum.frutigeraeroarchive.org/viewtopic.php?t=550
- [Last] Last.fm, tag "frutiger aero": https://www.last.fm/tag/frutiger+aero/wiki
- [Cradle] Cradle, "State Machine: Frutiger Aero" sample pack: https://cradle.app/products/state-machine-frutiger-aero
- [Skeuoss] Skeuoss, "Frutiger Metro aesthetic": https://skeuoss.net/blogs/aesthetics/frutiger-metro
- [Gurl] Gurlworld, "Frutiger Aero, the iconic 2000s tech and corporation aesthetic and its sub-genres": https://gurlworld.com/frutiger-aero-the-iconic-2000s-tech-and-corporation-aesthetic-and-its-sub-genres/
- [W-tot] Wikipedia, "Kazumi Totaka": https://en.wikipedia.org/wiki/Kazumi_Totaka
- [Vice] Vice, "Replaying the pretty synthwave tunes of the Wii channels": https://www.vice.com/en/article/replaying-the-pretty-synthwave-tunes-of-the-wii-channels
- [Vape] "The Wii's biggest, weirdest legacy is its music": https://vapingunderground.com/threads/the-wiis-biggest-weirdest-legacy-is-its-music.764587
- [FarOut] Far Out, "How Brian Eno created the Microsoft Windows 95 startup sound": https://faroutmagazine.co.uk/how-brian-eno-created-the-microsoft-windows-95-startup-sound/
- [RCP] Redmond/RCP Magazine, "Long Process Leads to Short Vista Sound" (2006): https://rcpmag.com/Articles/2006/11/13/Long-Process-Leads-to-Short-Vista-Sound.aspx
- [Verge] Verge Magazine, "Eerie, disturbing, iconic Backrooms songs": https://vergemagazine.co.uk/eerie-disturbing-iconic-backrooms-songs-that-echo-through-endless-empty-hallways/
- [Itch] "Liminal Worlds Music & Ambience Pack": https://captnphantom.itch.io/liminal-worlds

Fan forums, wikis and commercial sample packs describe taste, not fact. The doc uses them only for the Frutiger
family, which has no scholarly sources yet.

# Sound sources, round 2: public-domain and CC0 audio for new packs

Round 2 of source collection for BASILISK 16 / BASILISK SYNTH. The owner asked for a deeper search for public-domain sound from the era, and from defunct software, to mine for new preset packs. Everything here is **public domain or CC0 with a proof URL per file**. Anything that was doubtful is left out and listed in section 4.

- **Catalogs** (one per theme, the same format as `aero.json`): `catalog/tape.json`, `instruments.json`, `fm.json`, `synth80s.json`, `chip.json`, `signals.json`, `ocean.json`, `pcera.json`.
- **Audio** (gitignored): the originals are in `sources-raw/<theme>/` and the converted 22050 Hz 16-bit mono files in `sources/<theme>/`. To rebuild one theme, run `python3 -E -P tools/build_library.py --only <theme> --no-manifest`. The `--no-manifest` flag leaves the tracked `sources/manifest.json` alone. Use `-E -P` rather than `-I`, because numpy is in the user site-packages and `-I` hides it. `-P` still keeps the script and current directories off `sys.path`, and the downloaded audio is only ever read by ffmpeg.
- **Downloads:** about 520 MB in all, well under the 2 GB budget.

## 1. Themes and counts

| Theme (category) | Sounds | Tonal | Length after conversion | Sources |
|---|---:|---:|---:|---|
| `tape`: tape-replay sustains (flutes, strings, brass, reeds, recorders, organs, choir, theremin) | 94 | 94 | 13.5 min | VSCO 2 CE 55, VCSL 32, Freesound 6, Commons 1 |
| `instruments`: plucked, struck and world instruments, plus effects | 92 | 65 | 9.9 min | VCSL 79, VSCO 2 CE 13 |
| `fm`: Yamaha TX81Z (1987 FM synth) | 24 | 24 | 2.2 min | VCSL |
| `synth80s`: vintage analog synths and the Roland VP-330 choir and strings | 54 | 54 | 8.7 min | Freesound (modularsamples 39, Elektrik_Musik VP-330 15) |
| `chip`: 8-bit game SFX | 80 | 0 | 0.9 min | OpenGameArt (Juhani Junkala) |
| `signals`: US military bugle calls, NASA Quindar, siren | 18 | 17 | 3.5 min | Commons (US Army and USMC 15, own-work PD 1), nasa.gov 2 |
| `ocean`: NOAA hydrophone (Bloop, Upsweep, whales, ships, ice) | 26 | 17 | 7.1 min | NOAA PMEL |
| `pcera`: era PC and AV hardware (floppy, HDD, CRT, PC speaker, VHS, datasette) | 36 | 4 | 10.5 min | Freesound |
| **Total** | **424** | **275** | **56 min** | |

Sustained notes are cut to at most 12 s (`dur`), and the build caps tonal sounds at 15 s. Each `labelled_note` comes from the source's file name. The builder's YIN estimate (`est_root_note` in the manifest) is the one to trust. VCSL's TX81Z labels read about two octaves below the estimate, and modularsamples' titles about one octave above it. These are naming conventions, not errors.

**Octave convention and ID renames (after review by the library lane).** The VSCO-derived and VCSL-derived note names in `tape`, `instruments` (and round 1's `tonal`) use the **C3 = middle C** convention. They read one octave low in scientific pitch (C4 = 261.6 Hz); for example, `tape_flute_vib_c4` sounds at 523 Hz. Sound IDs in `synth80s` and `fm` have been renamed to **brand-neutral family names with the measured scientific-pitch root**: `poly78` (Jupiter-4), `poly82` (Juno-6), `poly83` (JX-3P), `poly84` (AX80), `poly85` (JX-8P), `mono77` (CS-30L), `mono79` (SH-2), `vocoder_*` (VP-330) and `fm87_*` (TX81Z). The model stays in `description` and `source_url`. The old-to-new map is in `research/round2-id-renames.json`. Each root in an ID is the builder's YIN estimate and can still be an octave off for bass-heavy patches, so measure the audio before key-mapping. Future catalogs should state the convention, or put scientific pitch in the ID.


### Licence breakdown (all themes)

| Licence | Sounds |
|---|---:|
| CC0-1.0 (Versilian, Freesound, OpenGameArt) | 379 |
| Public domain, US federal government work (NOAA PMEL 26, NASA 2) | 28 |
| Public domain on Commons (US Army and USMC bugle calls 15; own work released as PD 2) | 17 |

Every entry has `source_url`, `author`, `license` and `license_proof_url`, plus a `note` saying where the licence statement is.

## 2. What was found, by source

### Versilian Studios: VSCO 2 Community Edition and VCSL (CC0)
`github.com/sgossner/VSCO-2-CE` and `github.com/sgossner/VCSL`: both repos carry a CC0 1.0 `LICENSE` file, and the GitHub licence API reports `CC0-1.0`. They are by far the best PD-clean instrument source, with orchestral sections, solo winds and brass, keyboards, world instruments and percussion, all as single labelled notes. Round 1 took 27 files from VSCO for `tonal`. Round 2 adds 203:
- **tape** (tape-replay): sustained notes, 2 to 6 per instrument, spread over the range. The instruments are flute (with vibrato and plain), piccolo, violin, viola and cello sections, solo violin, contrabass, violin tremolo, oboe, clarinet, bassoon, horn, trombone, trumpet (open and harmon mute), tuba, quiet pipe organ, four baroque recorders, a Renaissance chamber organ (8' and full), saxello, chromatic harmonica, bowed psaltery, bowed vibraphone and ocarina. Each note is cut to at most 12 s (the build cap for tonal sounds is 15 s), so a builder can add the tape character, wow and start-of-tape attack in Sound Recorder.
- **instruments**: plucked and struck notes (harpsichord, folk harp, dan tranh, strumstick, psaltery, five kalimbas and mbiras, balafon, vibraphone, tubular bells, hand chimes, tubular glockenspiel and a Yamaha upright) plus about 34 one-shots and effects (flexatone, mark tree, gong and gong scrape, didgeridoo, toy train whistle, siren whistle, Nepalese bells, ocean drum, dan tranh glisses, temple bowls, bowed cymbal, glock glisses, spring-drum zaps and the organ blower motor).
- **fm**: VCSL's **Yamaha TX81Z** (1987 FM) multisamples. These are three patches (Clavisynth, FM Piano and Piano 1), C1 to C6 loud plus C2 and C4 soft, 24 notes in all. This is real late-80s FM hardware, recorded by Versilian and released CC0.

### Freesound: vintage synths and the Roland VP-330 (CC0)
- `modularsamples` released whole multisampled CC0 packs of Roland Jupiter-4, JX-3P, JX-8P, Juno-6 and SH-2, Yamaha CS-30L and Akai AX80. Each pack has one file per semitone, and Freesound IDs run down one per semitone from C7, so C3 is the C7 ID minus 48 where a pack is contiguous. The repo's `fetch.py` re-checks CC0 for each sound, and each title's note was read back into `labelled_note`.
- `Elektrik_Musik` released the **Roland VP-330 Vocoder Plus** "Human Voice" (male, female and both ensembles) and "Strings" as chromatic runs, CC0. That is the classic late-70s choir and string machine. Three single notes per run were excerpted (`start`/`dur`, with onsets found by ffmpeg `silencedetect`). They suit a tape or choir pack well.
- These are **synth80s** (54 entries).

### OpenGameArt: Juhani Junkala, "512 Sound Effects (8-bit style)" (CC0)
The OGA page's licence field is CC0, and the pack's own `INFO.txt` says "These sound effects have been released under CC0 creative commons license". Eighty were taken across the folders: alarms, blips, coins, menus, power-ups, weird and mechanical sounds, lasers, fanfares, pauses, errors, explosions, portals, robot and android death screams, jumps, falls, interactions, impacts, vehicles and a grenade whistle. This is **chip**, for the planned "Game Port Sound Set".

### Wikimedia Commons: US-government signals (PD)
Only items whose author is a US federal body (Army, Marine Band, NASA, FEMA, NOAA/NWS, NPS), or whose uploader released their own work as PD, were chosen. The Commons API checks returned 48 PD/CC0 files, and their credit lines were reviewed.
- **Collected (signals 18, tape 1):**
  - 15 US Army and Marine Band bugle calls (Adjutant's Call, Assembly, Attention, Call to Quarters, Church, Drill, Fire, First, Mail, Mess, Officers, Recall, School, Sick, Tattoo)
  - a civil-defence siren (own work, PD)
  - NASA Quindar tones ×2, fetched direct from nasa.gov
  - a theremin phrase (own work, PD)
- **Pending: 23 files are verified PD but not downloaded.** After about 18 files, `upload.wikimedia.org` began answering 429 "does not comply with our robot policy". The policy wants a contact address in the User-Agent, and the owner's details are not to be sent to outside services. The pending files are the EAS attention signal, EAS SAME headers (FEMA), NOAA SAME burst, NWR 1050 Hz tone, EBS two-tone, five NOAA Weather Radio synthetic-voice broadcasts, Taps, the Sputnik beep (NASA), Morse ×3, sirens ×4, the CC0 humpback, the ARP Solina ensemble ×2 and the Bach theremin. All of them are in `research/round2-pending-commons.json` as ready jobs (URL, licence, author, proof and note). A later run can fetch them with `tools/fetch.py commons` once the block lifts, or from a client with a compliant User-Agent. The EAS, SAME, 1050 Hz and Morse tones are fully specified signals, so `tools/synth_sources.py` could also synthesize them.
- **NPS Glacier Bay hydrophone** (humpback and killer whales, vessels, underwater rain; about 40 NPS recordings from 2000–2002, PD). The original nps.gov folder is gone, and the Wayback Machine has the index page but not the mp3s (they came back as HTML and were discarded). Commons has 6 of them (killer whale ×3, humpback moo and wheeze-blow), which are pending with the rest.

### NOAA PMEL Acoustics Program (public)
`pmel.noaa.gov/acoustics`. Its Credits section says: "Unless otherwise noted (copyrighted material for example), information presented on the PMEL Acoustics Program webpage is considered public information and may be distributed freely". No item page carries a copyright notice. The program is NOAA, partly staffed through Oregon State University's cooperative institute. NOAA publishes these sounds as public, and that statement is recorded in each entry's `note`.
- **ocean** (26): the "Bloop", "Upsweep", "Whistle", volcanic and harmonic tremor, iceberg calving, an undersea earthquake T-phase, airgun pulses, ship noise (the Ronald H. Brown arriving, a ship passing overhead, a small ship), a calibrated sound source, Challenger Deep acoustic-modem pings, damselfish, and blue, fin, minke, humpback (two with ship noise, one Alaska song) and "52 Hz"-type whale calls. Most are sped up 3 to 20 times, so they land in the audible, tonal range.

### Freesound: era PC and AV hardware (CC0)
- **pcera**:
  - floppy drives (access, insert, read, eject)
  - hard drives (spin up and down, head alignment, a 10K drive, one captured with an inductor mic)
  - CRT degauss, on/off and flyback hum
  - PC-speaker beeps and GSM buzz
  - an old PC boot and a server power cycle
  - CD-ROM seeks and a pickup-coil capture
  - fan coil whine and server-room fans
  - VCR and VHS hiss and hum, and tape decks
  - Commodore datasette data tones
  - an OPL3 FM snare

  This round avoided overlap with `electromech`, which already has modems, dot-matrix printers, typewriters and relays.

## 3. Themes that could become packs

| Proposed pack | Draws on | Sounds available | Fit with pack-plan.md |
|---|---|---:|---|
| **Tape Replay Console** (Mellotron-style, no trademarks: flute, three violins, cello, brass, choir, organ) | tape, plus VP-330 from synth80s, plus `tonal` choir_aah | 94 + 12 | new pack; also feeds Retro Display, Ambient and Beat Management keys |
| **Vintage Synthesizer Archive** (Jupiter-4, Juno-6, JX-3P, JX-8P, SH-2, CS-30L, AX80, TX81Z) | synth80s, fm | 78 | Professional Workstation Classics, Retro Display Properties, Trance |
| **World and Chamber Instruments** (harpsichord, kalimbas, mbiras, balafon, dan tranh, harps, bells) | instruments | 92 | Leisure Accessories (exotica), Studio Instruments Archive, Ambient |
| **Game Port Sound Set** extension | chip | 80 | Game Port Sound Set (pack 11), Experimental Diagnostics |
| **Hardware Diagnostics** (drives, CRTs, PC speaker, tape) | pcera, with electromech | 36 (+ about 260 electromech) | Experimental Diagnostics Suite, Techno textures |
| **Deep Ocean Monitoring Station** (Bloop, Upsweep, whales, ships, ice) | ocean, with water and nature | 26 | Ambient Screen Saver Collection |
| **Emergency Broadcast / Signal Corps** (bugles, Quindar, sirens; EAS and NWR pending) | signals | 18 (+ 19 pending) | small FX pack, or FX slots in other packs |

## 4. Rejected or uncertain (left out), with reasons

**The general rule** is that defunct is not public domain. "Abandonware" shareware and CD sound folders stay copyrighted unless the rights holder released them. An Internet Archive `licenseurl` is chosen by the uploader and is often wrong, so it never counted as proof by itself.

| Source | Verdict | Why |
|---|---|---|
| archive.org "Windows XP Sounds", "Windows 95 Sounds", "Windows 12 Sounds" and similar (marked PD/CC0) | rejected | Microsoft's copyrighted system sounds. The uploader's licence mark is not a release by the rights holder. |
| archive.org "Toy Story 1 & 2: Isolated Sound FX", "When the Wind Blows (1986) M&E track", "BrainPOP Sound Effects" (marked CC0) | rejected | Commercial film and product audio, uploaded by third parties. |
| archive.org Kurzweil K2000 "SF2 Samples" (marked CC0) | rejected | Rips of Kurzweil ROM samples. The rights belong to Kurzweil, not the uploader. |
| archive.org "Sound effects from the MMO game Glitch by Tiny Speck" (marked CC0, 209 mp3s) | uncertain | Tiny Speck did release Glitch's **art and code** under CC0 (the `github.com/tinyspeck/*` READMEs). Those repos hold almost no audio, so the sounds can't be traced to that release. The official client repo's two mp3s include *Prisencolinensinainciusol*, a commercial Adriano Celentano song, which shows that even an official CC0 dump can contain third-party audio. |
| archive.org Electronic Rhythm Archive (Bedsit Audio), Keio DoncaMatic DE 20, KW 6106, Rhythm Ace loops (PD mark) | uncertain | The recordings are released by their recordists, but they play the manufacturers' factory rhythm patterns. Single drum hits recorded from these machines would be fine. Full patterns were not collected. |
| archive.org "The Designer's Choice SFX Collection" (CC0) | uncertain | Its origin could not be verified with the original author. |
| archive.org SFXR synth sample packs (PD mark) | not collected | Plausibly fine (sfxr output made by the uploader), but generic. The Junkala pack covers the same ground with a clear CC0 statement. |
| archive.org pdsounds.org archive (PD) | small, mostly skipped | Genuinely PD: pdsounds.org required a PD dedication on upload, and the site went down in 2009. The item holds only 10 sounds. One pdsounds sound (a police siren) came in via Commons. |
| Amiga ST-xx sample disks, tracker sample packs | rejected | Most of the samples were lifted from commercial records and synth ROMs. No PD release by the rights holders was found. |
| Philharmonia Orchestra samples | rejected | Custom licence (no resale as samples). Not CC0. |
| University of Iowa Musical Instrument Samples | uncertain | "May be downloaded and used for any projects, without restrictions", but there is no explicit PD or CC0 dedication. |
| Sonatina Symphonic Orchestra | rejected | CC Sampling Plus 1.0, not CC0. |
| Salamander Grand Piano | uncertain | Originally CC-BY 3.0. A later PD relicensing was not verified this round. Pianos are covered by VCSL anyway. |
| Library of Congress Citizen DJ | uncertain | "Free-to-use for your remixing needs" / "for creating new music" is a use grant, not a PD dedication, and the rights notes vary per collection. |
| Library of Congress National Jukebox | rejected | Streaming only, under licence from Sony Music and others. Pre-1926 US recordings are PD in the US since the Music Modernization Act, but the Jukebox offers no downloads. Commons and Internet Archive cylinder transfers are the route if an "early recording" pack is wanted (see section 5). |
| Musopen recordings | not collected | Musopen's own recordings are PD, but full performances are a poor fit for single-note sustains. Could serve a texture pack later. |
| NASA/JPL/Caltech and University of Iowa space sounds (Cassini RPWS, Saturn radio emissions, Mars microphone, InSight) | uncertain | JPL is run by Caltech and the plasma-wave instruments by the University of Iowa. Commons tags them PD-NASA, but authorship is mixed. Only NASA-authored items (Quindar, Sputnik) were taken. |
| Voyager Golden Record greetings | uncertain | Commons says PD, but the recordings were made at Cornell, and the rights in the speakers' performances are unclear. |
| Numbers-station recordings (Commons, PD/CC0 tags) | rejected | Foreign-government broadcasts. The PD claims rest on uploader assertions about content they didn't author. |
| Freesound "Game Boy Classic - Startup Sound", "Mac Mini Startup", "Apple iMac G3 Screen Turn On", "Pokémon UI Select" (CC0) | rejected | Nintendo's and Apple's copyrighted sounds. An uploader can't CC0 someone else's work. |
| Freesound "cartridge-sounds2600", "Atari 2600 Beat", "Fantaisie-Impromptu Retro-Style" and similar | rejected | Recorded game audio or arrangements of uncertain origin. |
| NIST WWV/WWVH | not found | No NIST-hosted download. The Commons recording's licence wasn't confirmed, and the shortwave-archive and "At the Tone" CD copies are not PD. |
| Real Mellotron, Chamberlin and Streetly tape sets (M-Tron etc.) | rejected | Copyrighted, and "Mellotron" is a trademark. Raw PD/CC0 sustained notes (tape, synth80s, VP-330) were collected instead. |

## 5. Next leads (not collected this round)
- **Kenney.nl** audio packs (Interface, Digital Audio, Sci-fi, Impact, UI, Casino, RPG; CC0 with a licence file in every zip). Clean, but modern-sounding. Good for a UI or "workgroup" pack.
- **Pre-1926 recordings** (wax cylinders, early discs) on Commons and in the UCSB cylinder archive via Internet Archive, for crackle, horn-recording textures and old vocal snippets. US-PD since the MMA (pre-1926 as of 2026). Check each item's rights. Corporate already has a few 1904–1920 hold-music pieces.
- **VCSL and VSCO** still hold much more: Steinway, Kawai, more harpsichords, timpani, full drum kits, harmonicas, recorders, and Upright Nr1. A full chromatic tape set per instrument is possible if the builder wants more than 2 to 6 roots.
- **NPS Sound Gallery** (round 1 used nature) also has machinery and historic-site sounds credited to NPS.

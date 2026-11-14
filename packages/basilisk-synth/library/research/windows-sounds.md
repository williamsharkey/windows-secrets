# Pure Windows sounds: an inventory for BASILISK SYNTH and BASILISK 16

Research for building "pure Windows" sample categories: every sound that shipped with Windows 3.0 to 7, the Plus! packs, the built-in programs and games, and the iconic early-Windows software around them. Each sound is rated as a synth source, and its presence in our two machines is checked against the real images (read-only).

Machine-readable list: [`windows-sounds.json`](windows-sounds.json) (1223 entries, schema at the top of the file).

## How this was made

- **Our images were read directly, read-only.**
  - XP: `~/synth-build/machine-out/base.qcow2` (the disk `packages/basilisk-synth/tools/make_machine.py` produces), converted to a scratch raw copy and walked with an NTFS reader. Embedded sounds were carved out of `.acs` agent characters and game executables.
  - 3.11: `site/basilisk-31-browser/w31.jsdos`, the WfW 3.11 C: drive that `packages/basilisk-synth-311/tools/make_machine.py` turns into BASILISK 16's `drive.zip` (the build trees in `~/bs311` and `~/b311build` hold the same files).
- **Other versions and the Plus! packs were measured too, where a copy could be fetched:** install media and CAB/INF listings from discmaster.textfiles.com and archive.org (Windows 3.0 MME, 3.1, WfW 3.11, NT 4, 95, 98, 98 SE/ME, XP, 7; Plus! 95, Plus! for Kids, Plus! 98, Plus! XP, Plus! DME). Anything only known from documentation is marked *research (not measured)* in the JSON (`measured: false`).
- **Measurements** (format, duration, attack, spectral flatness, autocorrelation pitch, three strongest spectral peaks) come from a decoder for PCM, MS-ADPCM and IMA-ADPCM (mono). IMA stereo (Plus! 98 Horror Channel) and MP3-in-WAV (Windows 7 schemes) were not decoded; their durations come from the header.
- **Character text.** Curated for the sounds in our images that matter most (the Media folders, Messenger, NetMeeting, the 3.x set, the startup sounds). The rest is generated from the measurements and marked *(auto)*; treat it as a first sort to audition, not a description from listening.
- **Root notes** are estimates: the strongest stable partial or the autocorrelation pitch, to the nearest semitone. Bells have inharmonic partials, so check by ear before setting `K` in a preset. Cents offsets are in the JSON (`root_detail`, `peaks`).

## What is in our machines

### Windows XP (BASILISK SYNTH, `packages/basilisk-synth`)

The disk is the BASILISK III XP machine (XP SP3) with `C:\synth` added. Sound files found:

| Location | Files | Notes |
|---|---|---|
| `C:\WINDOWS\Media` | 35 WAV + 3 MID | Exactly the 35 sounds in DNA.md section 2.4 (9 legacy names, which are the Windows 98 re-recordings, plus 26 "Windows XP *.wav"), and flourish/onestop/town.mid. ringin.wav and ringout.wav are byte-identical to the 3.11 files. |
| `C:\Program Files\Windows NT\Pinball` | 60 WAV + 2 MID | 3D Pinball Space Cadet. SOUND2, 37, 44, 52, 59 and 62 are referenced by PINBALL.DAT but absent, as on stock XP. |
| `C:\Program Files\Messenger` | 4 WAV | Windows Messenger 4.7: newalert, newemail, online (MS-ADPCM), type. |
| `C:\Program Files\NetMeeting` | 2 WAV | Blip.wav, TestSnd.wav (also on the Windows 98 CD). |
| `C:\WINDOWS\Help\Tours\WindowsMediaPlayer\Audio\Wav` | 9 WAV | WMP tour music beds, 3.9-15.9 s, MS-ADPCM. There is no `WindowsXPTour` folder: the XP tour music is not on this disk (mmTour is Flash only). |
| `C:\WINDOWS\system32\oobe\images` | clickerx.wav, title.wma, qmark.acs | title.wma is the XP setup welcome music. |
| `C:\WINDOWS\msagent\chars\merlin.acs`, `C:\WINDOWS\srchasst\chars\{rover,earl,courtney}.acs` | 32 + 10 + 22 + 4 + 7 (qmark) embedded WAVs | MS Agent / Search Companion character sounds. |
| winmine.exe, mshearts.exe, spider.exe, bckgres.dll | 3 + 2 + 6 + 11 embedded WAVE resources | Minesweeper, Hearts, Spider (one is a copy of tada.wav, one of Menu Command), Internet Backgammon. sol.exe, freecell.exe, sndrec32.exe and the other Zone games have none. |
| `C:\WINDOWS\system32\drivers\gm.dls` | 1 | Microsoft GS Wavetable SW Synth: Roland GS set, 235 instruments, 495 samples, 3.44 MB. |
| `...\SpeechEngines\Microsoft\TTS\1033\sam.spd` | 1 | Microsoft Sam (SAPI 5.1), with narrator.exe. No Mike/Mary, no L&H TruVoice engine. |
| `C:\Documents and Settings\All Users\Documents\My Music\Sample Music` | 2 WMA | Beethoven 9 (Scherzo), New Stories (Highway Blues). |
| Templates `sndrec.wav` | 4 copies | 58-byte empty WAV (Sound Recorder's New > Wave Sound). |

Not on the disk, though stock on some XP builds: the IE7 sounds (Windows Feed Discovered, Navigation Start, ...), ir_begin/ir_end/ir_inter.wav, the Utopia scheme (optional component, not installed), the David Byrne promo track, Tablet and Media Center extras.

### Windows for Workgroups 3.11 (BASILISK 16, `packages/basilisk-synth-311`)

`C:\WINDOWS` holds **CHIMES.WAV, DING.WAV, RINGIN.WAV, RINGOUT.WAV** (8-bit mono) and **CANYON.MID**. Nothing else in the 601-file drive is audio. CHORD.WAV and TADA.WAV are missing because the WfW 3.11 disks themselves dropped them (Microsoft's WFWADD download restored them), not because of our build. Adding the 3.1 CHORD and TADA would let `chord` and `tada` resolve to real files instead of falling back to DING (DNA.md appendix).

### Flags for the synth

- **Compressed WAVs.** `srhook.c` only retunes a `waveOutOpen` with `wFormatTag == 1` (PCM), and `load_pcm` rejects anything else. Sources in MS-ADPCM (start.wav, the Messenger sounds, the WMP tour, most Agent sounds, all of Plus! 95 and Plus! for Kids), IMA-ADPCM (Horror Channel) or MP3-in-WAV (Windows 7 schemes) need a PCM copy first. Check that the guest already converts start.wav, since it is in the DNA table.
- **WfW 3.11 Sound Recorder** opens PCM only (no ACM), so anything added to BASILISK 16 must be 8- or 16-bit PCM.
- **MIDI, WMA, DLS and SAPI are not Sound Recorder sources.** They would need rendering to WAV inside the guest (for example Sam speaking a vowel, or a GS instrument note recorded through the mixer) to count as "real Windows" material.

## Counts per category

One entry per distinct file (byte-identical copies are merged; the Windows 7 schemes are one entry per scheme of 20 files). "Tonal FX" is large because most Plus! theme sounds are classified automatically, and anything pitched but not clean (mixed partials, sweeps, sound effects with a tone in them) lands there. Audition it before trusting the split.

| Category | All entries | Measured | In our images |
|---|---|---|---|
| Tonal FX | 477 | 404 | 55 |
| Bells & tones | 219 | 201 | 46 |
| Whooshes & textures | 142 | 140 | 27 |
| Motifs & phrases | 98 | 83 | 19 |
| Clicks & percussion | 80 | 64 | 26 |
| Noise & foley | 75 | 72 | 17 |
| Pads & swells | 51 | 47 | 3 |
| Music (MIDI/WMA/beds) | 42 | 15 | 19 |
| Unmeasured | 15 | 15 | 0 |
| Chords & fanfares | 14 | 11 | 3 |
| Speech & voice | 9 | 1 | 3 |
| Empty/none | 1 | 1 | 1 |
| **Total** | **1223** | **1054** | **219** |

By synth class: texture 661 (101 in images), tonal 382 (71 in images), percussive 80 (26 in images), noise 75 (17 in images), unknown 15 (0 in images), speech 9 (3 in images), none 1 (1 in images).

By source: Plus! 98 377, Plus! for Kids 180, Plus! 95 165, Plus! XP 85, MS Agent / Search Companion characters 73, 3D Pinball Space Cadet 62, Windows 95 sound schemes 55, Windows Vista / 7 Media 44, Windows Media folder 35, Games 23, General MIDI files 20, Windows 7 sound schemes 13, Windows XP extras 12, Windows 95 Media 10, Windows Media Player tour 9, Windows 3.0 MME system sounds 9, Speech 7, Sample Music 6, Plus! DME 6, Other software 6, Windows 98 Media 5, Windows Messenger 4.7 4, Windows 3.x system sounds 4, Office assistants 3, XP setup 2, NetMeeting 3.01 2, Windows NT Media 2, Windows ME / 2000 Media 2, Synth sample sets 1, Messenger 1.

## The 50 most synth-useful sounds

Ranked for BASILISK: clean pitch first, then the iconic swells and chords, then the percussion a kit needs. 46 of them are already in our images; the last 4 would have to be added.

| # | Sound | Version | s | Root | Category | In image | Why |
|---|---|---|---|---|---|---|---|
| 1 | ding.wav | Windows XP SP3 | 0.92 | G5 | Bells & tones | xp | Cleanest pitched bell on either disk: plays straight across 3 octaves |
| 2 | DING.WAV | Windows for Workgroups 3.11 | 0.52 | G5 | Bells & tones | 311 | 3.11 original: 8-bit grit, same pitch as the XP one |
| 3 | Windows XP Default.wav | Windows XP SP3 | 0.56 | D#5 | Bells & tones | xp | Glassy FM-like bell; trims to a mallet with @/] |
| 4 | Windows XP Print complete.wav | Windows XP SP3 | 0.99 | A#5 | Bells & tones | xp | Near-sine bell, long: the best "pure tone" lead |
| 5 | Windows XP Ding.wav | Windows XP SP3 | 0.39 | B3 | Bells & tones | xp | Soft round marimba hit; a natural low/mid keys source |
| 6 | Windows XP Exclamation.wav | Windows XP SP3 | 0.96 | G#5 | Bells & tones | xp | Two-note glass bell; cut after note 1 for a single tone |
| 7 | Windows XP Error.wav | Windows XP SP3 | 1.00 | D#6 | Bells & tones | xp | Two-note bell Eb-Bb; fifths are free harmony |
| 8 | Windows XP Hardware Fail.wav | Windows XP SP3 | 0.83 | C3 | Bells & tones | xp | Single sustained low mallet: bass keys |
| 9 | chimes.wav | Windows XP SP3 | 0.63 | G5 | Motifs & phrases | xp | Descending chime figure; reversed (R) it is a swell |
| 10 | CHIMES.WAV | Windows for Workgroups 3.11 | 0.72 | G5 | Motifs & phrases | 311 | 3.11 8-bit chime figure |
| 11 | ringout.wav | Windows XP SP3 | 0.47 | A4 | Bells & tones | 311, xp | Two detuned sines: a ready-made chorus/organ tone, both images |
| 12 | Windows XP Ringout.wav | Windows XP SP3 | 0.50 | A4 | Bells & tones | xp | Softer XP ringback: sustained, loopable-feeling |
| 13 | Windows XP Startup.wav | Windows XP SP3 | 4.81 | G#4 | Pads & swells | xp | The XP swell: a 4.8 s pad; F (fixed) or key-tracked for chords |
| 14 | Windows XP Shutdown.wav | Windows XP SP3 | 3.20 | G#3 | Pads & swells | xp | 3.2 s falling pad |
| 15 | Windows XP Logon Sound.wav | Windows XP SP3 | 2.16 | G#3 | Motifs & phrases | xp | 2.2 s rising pad/bell phrase |
| 16 | Windows XP Logoff Sound.wav | Windows XP SP3 | 2.04 | D#4 | Motifs & phrases | xp | 2 s falling phrase |
| 17 | tada.wav | Windows XP SP3 | 1.94 | C4 | Chords & fanfares | xp | C major fanfare stab: chord instrument (play with F or harmony H0) |
| 18 | chord.wav | Windows XP SP3 | 1.10 | G3 | Chords & fanfares | xp | Struck chord with fast decay: chord-stab/house-piano role |
| 19 | notify.wav | Windows XP SP3 | 1.35 | D5 | Motifs & phrases | xp | Two-note chime in fourths; @50 splits it into two sources |
| 20 | Windows XP Notify.wav | Windows XP SP3 | 1.11 | A#4 | Motifs & phrases | xp | Three-note falling bell |
| 21 | Windows XP Hardware Insert.wav | Windows XP SP3 | 0.83 | C3 | Bells & tones | xp | Rising mallet fifth C-G |
| 22 | Windows XP Hardware Remove.wav | Windows XP SP3 | 0.83 | C3 | Bells & tones | xp | Falling mallet fifth G-C |
| 23 | Windows XP Battery Low.wav | Windows XP SP3 | 1.22 | G2 | Bells & tones | xp | Soft low sine tones: sub-bass after < (octave down) |
| 24 | Windows XP Battery Critical.wav | Windows XP SP3 | 0.84 | C3 | Bells & tones | xp | Low warning tones: bass/drone |
| 25 | Windows XP Critical Stop.wav | Windows XP SP3 | 0.89 | C3 | Chords & fanfares | xp | Dark low chord stinger: orchestral hit |
| 26 | Blip.wav | Windows XP SP3 | 0.93 | D#6 | Bells & tones | xp | NetMeeting: short bright bell, very clean |
| 27 | TestSnd.wav | Windows XP SP3 | 0.87 | G#6 | Motifs & phrases | xp | NetMeeting: swelling chime phrase (pad-ish reversed) |
| 28 | online.wav | Windows XP SP3 | 1.63 | C5 | Bells & tones | xp | Messenger chime F5-C5 (MS-ADPCM: convert to PCM first) |
| 29 | newemail.wav | Windows XP SP3 | 1.61 | D4 | Bells & tones | xp | Messenger mallet arpeggio on D (MS-ADPCM) |
| 30 | Windows XP Ringin.wav | Windows XP SP3 | 0.88 | D6 | Tonal FX | xp | Synth phone trill: built-in tremolo lead |
| 31 | ringin.wav | Windows XP SP3 | 0.91 | G#6 | Tonal FX | 311, xp | Old phone bell trill (identical in both images) |
| 32 | Windows XP Balloon.wav | Windows XP SP3 | 0.14 | A5 | Clicks & percussion | xp | Tiny pop: pluck/pizzicato at low pitches |
| 33 | Windows XP Pop-up Blocked.wav | Windows XP SP3 | 0.17 | G#6 | Clicks & percussion | xp | High blip: chiptune-ish lead/arp |
| 34 | Windows XP Menu Command.wav | Windows XP SP3 | 0.03 |  | Clicks & percussion | xp | 30 ms click: hi-hat/rimshot |
| 35 | start.wav | Windows XP SP3 | 0.05 |  | Clicks & percussion | xp | Navigation click: closed hat (MS-ADPCM) |
| 36 | recycle.wav | Windows XP SP3 | 0.57 |  | Noise & foley | xp | Paper crumple: snare/brush noise |
| 37 | Windows XP Minimize.wav | Windows XP SP3 | 0.51 |  | Whooshes & textures | xp | Down-whoosh: riser/fall FX, reversed = riser |
| 38 | Minesweeper sound #0 | Windows XP SP3 | 0.06 |  | Clicks & percussion | xp | Minesweeper tick: woodblock/clave |
| 39 | Minesweeper sound #2 | Windows XP SP3 | 1.16 |  | Tonal FX | xp | Minesweeper explosion: kick/noise boom pitched down |
| 40 | SOUND104.WAV | Windows XP SP3 | 0.10 |  | Clicks & percussion | xp | Pinball flipper up: tight thump |
| 41 | SOUND12.WAV | Windows XP SP3 | 0.38 |  | Tonal FX | xp | Pinball pop bumper: metallic hit |
| 42 | SOUND9.WAV | Windows XP SP3 | 1.81 | C4 | Bells & tones | xp | Pinball mission complete: tonal swell |
| 43 | SOUND50.WAV | Windows XP SP3 | 1.08 | G#4 | Bells & tones | xp | Pinball bonus: pitched slow swell, pad-like |
| 44 | Agent merlin sound #22 | Windows XP SP3 | 1.97 | D5 | Bells & tones | xp | Merlin.acs: 2 s clean tone (ac 0.97) |
| 45 | Agent qmark sound #06 | Windows XP SP3 | 3.23 | F#4 | Bells & tones | xp | OOBE qmark.acs: 3.2 s clean swell, a pad |
| 46 | Microsoft Sam (SAPI 5.1) | Windows XP |  |  | Speech & voice | xp | Speech: render vowels/words inside XP as new sources |
| 47 | The Microsoft Sound.wav | Windows 95 (retail and OSR2) | 6.12 | F3 | Pads & swells | - | Eno 95 startup (8-bit, ~45 c flat of F): THE pad to add |
| 48 | BLOCKS.WAV | Windows 3.0 with Multimedia Extensions 1.0 (OEM, 1991) | 0.43 | A#5 | Bells & tones | - | 3.0 MME woodblock: pitched percussion to add |
| 49 | CHORD.WAV | Windows 3.1 / NT 3.x / NT 4.0 | 1.13 | A2 | Chords & fanfares | - | 3.1 chord: missing from our 3.11 image, the obvious add |
| 50 | TADA.WAV | Windows 3.1 / NT 3.x / NT 4.0 | 1.26 | C3 | Chords & fanfares | - | 3.1 ta-da: missing from our 3.11 image, the obvious add |

## Category tables: sounds in our images

### Windows Media folder (35)

DNA names from DNA.md section 2.4 are given in brackets.

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| Windows XP Battery Low.wav [`batlow`] | 1.22 | PCM 22050 Hz 16-bit mono | tonal | G2 | 5 | xp | low two-tone warning, soft sine-like, G2/C3 |
| Windows XP Ding.wav [`xpding`] | 0.39 | PCM 22050 Hz 16-bit mono | tonal | B3 | 5 | xp | soft round marimba-like ding, B3 |
| Windows XP Exclamation.wav [`exclaim`] | 0.96 | PCM 22050 Hz 16-bit mono | tonal | G#5 | 5 | xp | two-note glassy bell, Ab5 then Eb6 |
| Windows XP Hardware Fail.wav [`hwfail`] | 0.83 | PCM 22050 Hz 16-bit mono | tonal | C3 | 5 | xp | single sustained low mallet/bell tone, C3 |
| Windows XP Print complete.wav [`print`] | 0.99 | PCM 22050 Hz 16-bit mono | tonal | A#5 | 5 | xp | pure sine-like bell, Bb, long-ish |
| Windows XP Ringout.wav [`xpringout`] | 0.50 | PCM 22050 Hz 16-bit mono | tonal | A4 | 5 | xp | soft ringback tone, A4/B4 beating |
| ding.wav [`ding`] | 0.92 | PCM 22050 Hz 16-bit stereo | tonal | G5 | 5 | xp | single clean bell ding, long ring; the cleanest pitched source on the disk |
| ringout.wav [`ringout`] | 0.47 | PCM 11025 Hz 8-bit mono | tonal | A4 | 5 | 311, xp | telephone ringback tone, two near-unison sines beating around A4/A#4 (identical to WfW 3.11) |
| Windows XP Battery Critical.wav [`batcrit`] | 0.84 | PCM 22050 Hz 16-bit mono | tonal | C3 | 4 | xp | low descending warning tones (C/G), dull |
| Windows XP Default.wav [`default`] | 0.56 | PCM 22050 Hz 16-bit mono | tonal | D#5 | 4 | xp | the XP "default beep": bright glassy bell, Eb5 with F/Bb partials |
| Windows XP Error.wav [`error`] | 1.00 | PCM 22050 Hz 16-bit mono | tonal | D#6 | 4 | xp | two-note bell, Eb6 then Bb6, the XP error |
| Windows XP Hardware Insert.wav [`hwin`] | 0.83 | PCM 22050 Hz 16-bit mono | tonal | C3 | 4 | xp | rising two-note mallet motif C3 to G3 |
| Windows XP Hardware Remove.wav [`hwout`] | 0.83 | PCM 22050 Hz 16-bit mono | tonal | C3 | 4 | xp | falling two-note mallet motif G3 to C3 |
| Windows XP Critical Stop.wav [`critstop`] | 0.89 | PCM 22050 Hz 16-bit mono | tonal (tonal-chord) | C3 | 3 | xp | low thud chord C/G, ominous short stinger |
| Windows XP Shutdown.wav [`shutdown`] | 3.20 | PCM 22050 Hz 16-bit stereo | tonal (pad) | G#3 | 3 | xp | descending four-note pad swell, Ab/Eb, 3.2 s |
| Windows XP Startup.wav [`startup`] | 4.81 | PCM 22050 Hz 16-bit stereo | tonal (pad) | G#4 | 3 | xp | the XP startup: 4.8 s orchestral/pad swell then 4-note figure, Ab major, long tail |
| chord.wav [`chord`] | 1.10 | PCM 22050 Hz 16-bit stereo | tonal (tonal-chord) | G3 | 3 | xp | Win95-era struck chord, fast decay, notes B5/A4/G3 (G-based cluster) |
| tada.wav [`tada`] | 1.94 | PCM 22050 Hz 16-bit stereo | tonal (tonal-chord) | C4 | 3 | xp | "ta-da" brass/synth fanfare, C major, bright |
| Windows XP Logoff Sound.wav [`logoff`] | 2.04 | PCM 22050 Hz 16-bit stereo | tonal (tonal-phrase) | D#4 | 2 | xp | descending four-note pad/bell phrase, Eb |
| Windows XP Logon Sound.wav [`logon`] | 2.16 | PCM 22050 Hz 16-bit stereo | tonal (tonal-phrase) | G#3 | 2 | xp | ascending pad/bell phrase, Ab/Eb |
| Windows XP Notify.wav [`xpnotify`] | 1.11 | PCM 22050 Hz 16-bit mono | tonal (tonal-phrase) | A#4 | 2 | xp | three-note falling bell Bb6, Eb5, Bb4 |
| chimes.wav [`chimes`] | 0.63 | PCM 22050 Hz 16-bit stereo | tonal (tonal-phrase) | G5 | 2 | xp | descending chime figure G6-D6-C6-G5, bright bell partials |
| notify.wav [`notify`] | 1.35 | PCM 22050 Hz 16-bit stereo | tonal (tonal-phrase) | D5 | 2 | xp | alternating two-note chime A5/D5 (fourth), repeated |
| Windows XP Balloon.wav [`balloon`] | 0.14 | PCM 22050 Hz 16-bit mono | percussive | A5 | 2 | xp | tiny soft pop/blip, 140 ms |
| Windows XP Information Bar.wav [`infobar`] | 0.11 | PCM 44100 Hz 16-bit stereo | percussive | G4 | 2 | xp | IE information-bar click-tone, very short (44.1 kHz stereo) |
| Windows XP Menu Command.wav [`menu`] | 0.03 | PCM 22050 Hz 16-bit mono | percussive |  | 2 | xp | tiny click, 30 ms |
| Windows XP Pop-up Blocked.wav [`popup`] | 0.17 | PCM 44100 Hz 16-bit stereo | percussive | G#6 | 2 | xp | short high blip-burst (44.1 kHz) |
| Windows XP Ringin.wav [`xpringin`] | 0.88 | PCM 22050 Hz 16-bit mono | texture (tonal-fx) | D6 | 2 | xp | modern synth phone trill, D6 |
| Windows XP Start.wav [`xpstart`] | 0.05 | PCM 22050 Hz 16-bit mono | percussive |  | 2 | xp | IE navigation click, 50 ms |
| ringin.wav [`ringin`] | 0.91 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) | G#6 | 2 | 311, xp | telephone bell trill (8-bit 11 kHz, identical to WfW 3.11 RINGIN.WAV) |
| start.wav [`start`] | 0.05 | MS-ADPCM 22050 Hz 4-bit stereo | percussive |  | 2 | xp | IE/Explorer navigation click, MS-ADPCM, ~50 ms Note: MS-ADPCM stereo; check the guest converts it to PCM (srhook only retunes PCM). |
| Windows XP Minimize.wav [`minimize`] | 0.51 | PCM 22050 Hz 16-bit mono | texture |  | 1 | xp | downward whoosh with faint tone |
| Windows XP Recycle.wav [`xprecycle`] | 0.52 | PCM 22050 Hz 16-bit mono | noise |  | 1 | xp | paper crumple / rustle |
| Windows XP Restore.wav [`restore`] | 0.44 | PCM 22050 Hz 16-bit mono | texture |  | 1 | xp | upward whoosh/swell |
| recycle.wav [`recycle`] | 0.57 | PCM 22050 Hz 16-bit mono | noise |  | 1 | xp | crumpled paper into bin: broadband rustle |

### Windows 3.x system sounds (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| DING.WAV | 0.52 | PCM 22050 Hz 8-bit mono | tonal | G5 | 5 | 311 | 3.1 original single bell ding, 8-bit, bright |
| CHIMES.WAV | 0.72 | PCM 22050 Hz 8-bit mono | tonal (tonal-phrase) | G5 | 2 | 311 | 3.1 original chime figure G6-D6-C6-G5 then G4, 8-bit |

### Windows Messenger 4.7 (4)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| newalert.wav | 1.63 | MS-ADPCM 11025 Hz 4-bit mono | tonal | G5 | 4 | xp | Windows Messenger 4.7 alert: two-note marimba/bell "bloop" Note: MS-ADPCM: needs conversion to PCM before the rate hook applies (srhook only rewrites wFormatTag 1). |
| newemail.wav | 1.61 | MS-ADPCM 22050 Hz 4-bit mono | tonal | D4 | 4 | xp | Windows Messenger new mail: soft mallet arpeggio, D Note: MS-ADPCM: needs conversion to PCM before the rate hook applies (srhook only rewrites wFormatTag 1). |
| online.wav | 1.63 | MS-ADPCM 11025 Hz 4-bit mono | tonal | C5 | 4 | xp | Windows Messenger contact-online: two-note chime F5 then C5 Note: MS-ADPCM: needs conversion to PCM before the rate hook applies (srhook only rewrites wFormatTag 1). |
| type.wav | 0.40 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | Windows Messenger typing tick/knock (8-bit) |

### NetMeeting 3.01 (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| Blip.wav | 0.93 | PCM 11025 Hz 16-bit mono | tonal | D#6 | 5 | xp | NetMeeting blip: short bright bell, Eb |
| TestSnd.wav | 0.87 | PCM 22050 Hz 16-bit stereo | tonal (tonal-phrase) | G#6 | 2 | xp | NetMeeting audio-tuning test: swelling chime phrase, Ab/Eb |

### XP setup (OOBE) (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| clickerx.wav | 0.06 | PCM 22050 Hz 16-bit mono | percussive |  | 2 | xp | OOBE wizard mouse click, 60 ms |
| title.wma (XP OOBE welcome music) |  | WMA, 2.6 MB | texture (music) |  | 1 | xp | "Velkommen" by Stan LePard (reportedly; VGMdb also credits Bill Brown); ambient piano/pad welcome loop Note: WMA: Sound Recorder cannot open it; a converted excerpt would be a new file. |

### Windows Media Player tour (9)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| wmpaud1.wav | 15.88 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | C#3 | 0 | xp | WMP 9 tour music bed: long tonal cue/music, 15.9 s (C#3-14/C3+32) *(auto)* |
| wmpaud2.wav | 3.85 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F2 | 0 | xp | WMP 9 tour music bed: pitched slow swell around F2+49 *(auto)* |
| wmpaud3.wav | 7.71 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F#2 | 0 | xp | WMP 9 tour music bed: long tonal cue/music, 7.7 s (F#2-15/F2+13) *(auto)* |
| wmpaud4.wav | 3.85 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F#2 | 0 | xp | WMP 9 tour music bed: multi-note tonal phrase/chord, 3.9 s (F#2-15/F2+10/G2-32) *(auto)* |
| wmpaud5.wav | 3.85 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) |  | 0 | xp | WMP 9 tour music bed: tonal swell/sweep, mixed pitches (F2+46/F#3-14) *(auto)* |
| wmpaud6.wav | 15.38 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F#2 | 0 | xp | WMP 9 tour music bed: long tonal cue/music, 15.4 s (F#2-12/G2+37) *(auto)* |
| wmpaud7.wav | 15.38 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F2 | 0 | xp | WMP 9 tour music bed: long tonal cue/music, 15.4 s (F2+46/G2-32) *(auto)* |
| wmpaud8.wav | 7.71 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F#2 | 0 | xp | WMP 9 tour music bed: long tonal cue/music, 7.7 s (F#2-12/G2-32) *(auto)* |
| wmpaud9.wav | 7.71 | MS-ADPCM 22050 Hz 4-bit stereo | texture (music) | F#2 | 0 | xp | WMP 9 tour music bed: long tonal cue/music, 7.7 s (F#2-18/C#4-13) *(auto)* |

### Games (20)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| Internet Backgammon sound #4 | 1.55 | PCM 11025 Hz 16-bit mono | tonal | A5 | 5 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: pitched struck tone, decaying around A5-8 *(auto)* |
| Internet Backgammon sound #5 | 1.88 | PCM 11025 Hz 16-bit mono | tonal | A3 | 5 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: pitched struck tone, decaying around A3+4 *(auto)* |
| Hearts sound #1 | 1.52 | PCM 22050 Hz 8-bit mono | tonal | A#2 | 4 | xp | Hearts (XP) embedded WAVE: pitched struck tone, decaying around A#2+50 *(auto)* |
| Internet Backgammon sound #3 | 1.74 | PCM 11025 Hz 16-bit mono | tonal | E6 | 4 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: pitched slow swell around E6+4 *(auto)* |
| Internet Backgammon sound #8 | 1.75 | PCM 11025 Hz 16-bit mono | tonal | A2 | 4 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: pitched struck tone, decaying around A2+6 *(auto)* |
| Spider Solitaire sound #3 | 0.26 | PCM 22050 Hz 8-bit mono | tonal | G#6 | 4 | xp | Spider Solitaire (XP) embedded WAVE: pitched sustained tone around G#6-45 *(auto)* |
| Internet Backgammon sound #2 | 2.37 | PCM 11025 Hz 16-bit mono | tonal (tonal-phrase) | C6 | 2 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: multi-note tonal phrase/chord, 2.4 s (C6+1/G6+3/E6-13) *(auto)* |
| Internet Backgammon sound #6 | 2.26 | PCM 11025 Hz 16-bit mono | tonal (tonal-phrase) | C#3 | 2 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: multi-note tonal phrase/chord, 2.3 s (C#3+27/E6-13/C5+1) *(auto)* |
| Internet Backgammon sound #7 | 2.43 | PCM 11025 Hz 16-bit mono | tonal (tonal-phrase) | C#3 | 2 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: multi-note tonal phrase/chord, 2.4 s (C#3+15/C6+1/G6+3) *(auto)* |
| Minesweeper sound #1 | 1.72 | PCM 22050 Hz 8-bit mono | tonal (tonal-phrase) | A2 | 2 | xp | Minesweeper (XP) embedded WAVE: win jingle (likely); multi-note tonal phrase/chord, 1.7 s (A2+14/E3+23/A3+21) *(auto)* |
| Spider Solitaire sound #2 | 1.86 | PCM 22050 Hz 8-bit mono | tonal (tonal-phrase) | A#3 | 2 | xp | Spider Solitaire (XP) embedded WAVE: multi-note tonal phrase/chord, 1.9 s (A#3+23/G#4+20/A#4+22) *(auto)* |
| Internet Backgammon sound #0 | 0.41 | PCM 11025 Hz 16-bit mono | texture (tonal-fx) |  | 2 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: tonal fx, mixed pitches (D#4+36/D#5+36) *(auto)* |
| Internet Backgammon sound #1 | 0.03 | PCM 11025 Hz 16-bit mono | percussive |  | 2 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: short click/tick *(auto)* |
| Minesweeper sound #0 | 0.06 | PCM 22050 Hz 8-bit mono | percussive |  | 2 | xp | Minesweeper (XP) embedded WAVE: tick (clock); short click/tick *(auto)* |
| Minesweeper sound #2 | 1.16 | PCM 22050 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Minesweeper (XP) embedded WAVE: explosion (likely); tonal fx, mixed pitches (F#2+44/G2+45) *(auto)* |
| Spider Solitaire sound #1 | 0.03 | PCM 22050 Hz 16-bit mono | percussive |  | 2 | xp | Spider Solitaire (XP) embedded WAVE: short click/tick *(auto)* |
| Spider Solitaire sound #4 | 0.01 | PCM 22050 Hz 16-bit mono | percussive |  | 2 | xp | Spider Solitaire (XP) embedded WAVE: short click/tick *(auto)* |
| Hearts sound #0 | 0.49 | PCM 22050 Hz 8-bit mono | texture |  | 1 | xp | Hearts (XP) embedded WAVE: noisy fx with some pitch (D8+18/D8-34) *(auto)* |
| Internet Backgammon sound #10 | 0.36 | PCM 11025 Hz 16-bit mono | texture |  | 1 | xp | Internet Backgammon (XP, MSN Zone) embedded WAVE: noisy fx with some pitch (F3-10/F4-10) *(auto)* |
| Spider Solitaire sound #0 | 0.14 | PCM 22050 Hz 8-bit mono | noise |  | 1 | xp | Spider Solitaire (XP) embedded WAVE: noisy burst (foley/whoosh/hit) *(auto)* |

### 3D Pinball Space Cadet (62)

Event names come from parsing PINBALL.DAT against the decompiled source (k4zmu2a/SpaceCadetPinball `control.cpp`). The sounds are 8-bit 11 kHz mono, (c) Cinematronics 1995.

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| SOUND50.WAV | 1.08 | PCM 11025 Hz 8-bit mono | tonal | G#4 | 5 | xp | bonus collected; pitched slow swell around G#4+49 *(auto)* |
| SOUND999.WAV | 0.60 | PCM 11025 Hz 8-bit mono | tonal | E2 | 5 | xp | not referenced by PINBALL.DAT (unused); pitched struck tone, decaying around E2-50 *(auto)* |
| SOUND136.WAV | 1.73 | PCM 11025 Hz 8-bit mono | tonal | G4 | 4 | xp | not referenced by PINBALL.DAT (unused); pitched struck tone, decaying around G4-20 *(auto)* |
| SOUND21.WAV | 0.82 | PCM 11025 Hz 8-bit mono | tonal | E2 | 4 | xp | launch ramp / hyperspace level 1; pitched slow swell around E2-50 *(auto)* |
| SOUND22.WAV | 0.66 | PCM 11025 Hz 8-bit mono | tonal | F3 | 4 | xp | plunger released (launch); pitched slow swell around F3+30 *(auto)* |
| SOUND240.WAV | 1.31 | PCM 11025 Hz 8-bit mono | tonal | E4 | 4 | xp | not referenced by PINBALL.DAT (unused); pitched struck tone, decaying around E4-7 *(auto)* |
| SOUND34.WAV | 0.12 | PCM 11025 Hz 8-bit mono | tonal | D3 | 4 | xp | ball hits drain blocker; pitched struck tone, decaying around D3-34 *(auto)* |
| SOUND9.WAV | 1.81 | PCM 11025 Hz 8-bit mono | tonal | C4 | 4 | xp | mission complete; pitched slow swell around C4-26 *(auto)* |
| SOUND1.WAV | 5.02 | PCM 11025 Hz 8-bit mono | tonal (pad) | D4 | 3 | xp | new game / player start light show; long tonal cue/music, 5.0 s (D4+26/C#4+37) *(auto)* |
| SOUND181.WAV | 2.47 | PCM 11025 Hz 8-bit mono | tonal (tonal-phrase) | D#5 | 2 | xp | not referenced by PINBALL.DAT (unused); multi-note tonal phrase/chord, 2.5 s (D#5+34/F5-49/D7-34) *(auto)* |
| SOUND27.WAV | 1.82 | PCM 11025 Hz 8-bit mono | tonal (tonal-phrase) | F#2 | 2 | xp | drain with ball save (re-deploy); multi-note tonal phrase/chord, 1.8 s (F#2-22/E2-28/G#2+22) *(auto)* |
| SOUND3.WAV | 2.06 | PCM 11025 Hz 8-bit mono | tonal (tonal-phrase) | F#2 | 2 | xp | skill shot; game end with high score; multi-note tonal phrase/chord, 2.1 s (F#2+35/E2+42/F#2-28) *(auto)* |
| SOUND30.WAV | 2.03 | PCM 11025 Hz 8-bit mono | tonal (tonal-phrase) | A#2 | 2 | xp | launch ramp, no lights; multi-note tonal phrase/chord, 2.0 s (A#2+30/A2+3/B2-5) *(auto)* |
| SOUND4.WAV | 1.49 | PCM 11025 Hz 8-bit mono | tonal (tonal-phrase) | G5 | 2 | xp | ball fed to plunger lane; multi-note tonal phrase/chord, 1.5 s (G5+40/F3-23/D5-12) *(auto)* |
| SOUND42.WAV | 2.63 | PCM 11025 Hz 8-bit mono | tonal (tonal-phrase) | C4 | 2 | xp | not referenced by PINBALL.DAT (unused); multi-note tonal phrase/chord, 2.6 s (C4+12/C4-41/C#4-37) *(auto)* |
| SOUND104.WAV | 0.10 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | flipper up; short click/tick *(auto)* |
| SOUND105.WAV | 0.17 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | flipper down; tonal fx, mixed pitches (C#3-17/E3-21) *(auto)* |
| SOUND111.WAV | 0.06 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | one-way gates; short click/tick *(auto)* |
| SOUND112.WAV | 0.06 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | not referenced by PINBALL.DAT (unused); short click/tick *(auto)* |
| SOUND12.WAV | 0.38 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | pop bumpers; tonal fx, mixed pitches (E3+8/F3+3) *(auto)* |
| SOUND13.WAV | 0.71 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal fx, mixed pitches (F3-23/E3+22) *(auto)* |
| SOUND131.WAV | 0.10 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | spinners; short click/tick *(auto)* |
| SOUND14.WAV | 0.26 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | hazard spot targets; skill-shot gates; tonal fx, mixed pitches (B5-7/G#6+2) *(auto)* |
| SOUND16.WAV | 0.08 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | drain blocker up/down; short click/tick *(auto)* |
| SOUND18.WAV | 0.35 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | target variant; tonal fx, mixed pitches (C3+14/D3+30) *(auto)* |
| SOUND19.WAV | 0.46 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | launch ramp level 2-3; tonal fx, mixed pitches (C#4+13/G#4+25) *(auto)* |
| SOUND20.WAV | 0.77 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | hyperspace level 2-3; tonal swell/sweep, mixed pitches (D#5+34/F5-49) *(auto)* |
| SOUND243.WAV | 1.86 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal swell/sweep, mixed pitches (G2-11/E4-24) *(auto)* |
| SOUND29.WAV | 0.93 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | multiball start / hyperspace top level; tonal fx, mixed pitches (F#3+4/G3-8) *(auto)* |
| SOUND36.WAV | 3.06 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | hyperspace kickout, 1 arrow; tonal fx, mixed pitches (A#3+14/F#3+29) *(auto)* |
| SOUND38.WAV | 1.17 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | hyperspace kickout, 3 arrows; tonal swell/sweep, mixed pitches (B5+11/F#6-7) *(auto)* |
| SOUND39.WAV | 2.55 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | hyperspace kickout, 4 arrows; tonal fx, mixed pitches (G#3-15/A3+8) *(auto)* |
| SOUND43.WAV | 2.06 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | ball captured by sink hole; tonal swell/sweep, mixed pitches (E4-48/E4+10) *(auto)* |
| SOUND45.WAV | 0.87 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | booster targets (jackpot/bonus/flags); tonal swell/sweep, mixed pitches (E2-50/E2+49) *(auto)* |
| SOUND528.WAV | 0.79 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal fx, mixed pitches (C5+3/G5+1) *(auto)* |
| SOUND54.WAV | 1.64 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | rank promotion; time warp; tonal fx, mixed pitches (B5+10/F5+34) *(auto)* |
| SOUND560.WAV | 2.61 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal swell/sweep, mixed pitches (D#5+25/A#4+4) *(auto)* |
| SOUND6.WAV | 0.38 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal fx, mixed pitches (D#3-1/C3+5) *(auto)* |
| SOUND7.WAV | 2.39 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | gravity well kickout; tonal swell/sweep, mixed pitches (F3+41/A3-30) *(auto)* |
| SOUND713.WAV | 1.31 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal fx, mixed pitches (A#2-2/G#2-20) *(auto)* |
| SOUND8.WAV | 0.18 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | ramp-lane rollovers; tonal fx, mixed pitches (D4-2/F#4+44) *(auto)* |
| SOUND827.WAV | 4.27 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | not referenced by PINBALL.DAT (unused); tonal fx, mixed pitches (B4-19/F#4+31) *(auto)* |
| PINBALL.MID |  |  | texture (music) |  | 1 | xp | Space Cadet soundtrack (5 tracks, programs 38/11/28 + drums); long looping sequence |
| PINBALL2.MID |  |  | texture (music) |  | 1 | xp | second Space Cadet tune (RMID container) |
| SOUND108.WAV | 0.68 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | tilt; noisy fx with some pitch (A#5+47/A#3+47) *(auto)* |
| SOUND17.WAV | 0.18 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | outlane kickbacks; noisy fx with some pitch (D4-10/F#3+32) *(auto)* |
| SOUND24.WAV | 1.08 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | launch ramp top level; noisy fx with some pitch (G#5+49/A#5-22) *(auto)* |
| SOUND25.WAV | 2.32 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | bonus lane rollover (unlit); fuel target; noisy fx with some pitch (A5+22/B5+48) *(auto)* |
| SOUND26.WAV | 0.65 | PCM 11025 Hz 8-bit mono | noise |  | 1 | xp | lane rollovers; outlane drain; noisy burst (foley/whoosh/hit) *(auto)* |
| SOUND28.WAV | 0.77 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | extra ball awarded; noisy fx with some pitch (F4+20/F4-34) *(auto)* |
| SOUND35.WAV | 1.76 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | hyperspace kickout, 2 arrows (default); noisy fx with some pitch (F#6+21/F6+35) *(auto)* |
| SOUND49.WAV | 0.16 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | target hits; noisy fx with some pitch (D3+14/C3-21) *(auto)* |
| SOUND49D.WAV | 0.29 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | fuel/hazard/mission secondary target; noisy fx with some pitch (F#3+7/F#2+32) *(auto)* |
| SOUND5.WAV | 0.27 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | slingshots/rebounders; noisy fx with some pitch (C3+14/C3-40) *(auto)* |
| SOUND53.WAV | 0.80 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | not referenced by PINBALL.DAT (unused); noisy fx with some pitch (E6+3/A3+11) *(auto)* |
| SOUND55.WAV | 1.97 | PCM 11025 Hz 8-bit mono | noise |  | 1 | xp | rollover/target variant; noisy burst (foley/whoosh/hit) *(auto)* |
| SOUND563.WAV | 2.18 | PCM 11025 Hz 8-bit mono | noise |  | 1 | xp | not referenced by PINBALL.DAT (unused); noisy burst (foley/whoosh/hit) *(auto)* |
| SOUND57.WAV | 2.75 | PCM 11025 Hz 8-bit mono | noise |  | 1 | xp | kickout holes eject ball; noisy burst (foley/whoosh/hit) *(auto)* |
| SOUND58.WAV | 0.29 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | not referenced by PINBALL.DAT (unused); noisy fx with some pitch (D#4-39/D4+6) *(auto)* |
| SOUND65.WAV | 1.59 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | not referenced by PINBALL.DAT (unused); noisy fx with some pitch (G#2-32/A2-34) *(auto)* |
| SOUND68.WAV | 2.92 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | not referenced by PINBALL.DAT (unused); noisy fx with some pitch (A#3-33/A3+14) *(auto)* |
| SOUND735.WAV | 2.46 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | not referenced by PINBALL.DAT (unused); noisy fx with some pitch (B7+22/A#6+27) *(auto)* |

### MS Agent / Search Companion characters (73)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| Agent earl sound #04 | 0.32 | MS-ADPCM 44100 Hz 4-bit stereo | tonal | E6 | 5 | xp | Search Companion "Earl" surfer: pitched sustained tone around E6+6 *(auto)* |
| Agent merlin sound #04 | 1.31 | MS-ADPCM 11025 Hz 4-bit mono | tonal | B5 | 5 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched struck tone, decaying around B5+36 *(auto)* |
| Agent merlin sound #14 | 0.30 | PCM 11025 Hz 16-bit mono | tonal | A#4 | 5 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched struck tone, decaying around A#4+33 *(auto)* |
| Agent merlin sound #22 | 1.97 | MS-ADPCM 22050 Hz 4-bit mono | tonal | D5 | 5 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched sustained tone around E6-5 *(auto)* |
| Agent qmark sound #02 | 0.44 | PCM 22050 Hz 16-bit stereo | tonal | E4 | 5 | xp | OOBE "question mark" assistant (qmark.acs): pitched struck tone, decaying around E4+11 *(auto)* |
| Agent qmark sound #04 | 0.82 | PCM 22050 Hz 16-bit stereo | tonal | D4 | 5 | xp | OOBE "question mark" assistant (qmark.acs): pitched struck tone, decaying around D4+6 *(auto)* |
| Agent qmark sound #06 | 3.23 | PCM 22050 Hz 16-bit stereo | tonal | F#4 | 5 | xp | OOBE "question mark" assistant (qmark.acs): pitched slow swell around F3+22 *(auto)* |
| Agent merlin sound #10 | 0.69 | MS-ADPCM 8000 Hz 4-bit mono | tonal | A3 | 4 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched struck tone, decaying around A3-33 *(auto)* |
| Agent merlin sound #11 | 0.18 | PCM 8000 Hz 16-bit mono | tonal | G3 | 4 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched sustained tone around G3+11 *(auto)* |
| Agent merlin sound #19 | 0.64 | MS-ADPCM 11025 Hz 4-bit mono | tonal | F#3 | 4 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched sustained tone around F#3-31 *(auto)* |
| Agent merlin sound #20 | 0.40 | PCM 8000 Hz 16-bit mono | tonal | G#3 | 4 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched sustained tone around G#3+11 *(auto)* |
| Agent merlin sound #21 | 0.15 | PCM 22050 Hz 16-bit mono | tonal | E2 | 4 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched struck tone, decaying around E2+22 *(auto)* |
| Agent merlin sound #28 | 1.70 | MS-ADPCM 22050 Hz 4-bit mono | tonal |  | 4 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): pitched struck tone, decaying around G7+1 *(auto)* |
| Agent rover sound #09 | 0.37 | MS-ADPCM 44100 Hz 4-bit stereo | tonal | G#4 | 4 | xp | Search Companion "Rover" dog: pitched sustained tone around G#4+19 *(auto)* |
| Agent merlin sound #09 | 1.28 | MS-ADPCM 22050 Hz 4-bit mono | tonal (tonal-phrase) | D#5 | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): multi-note tonal phrase/chord, 1.3 s (D#5+2/D#6+5/C5+1) *(auto)* |
| Agent courtney sound #00 | 0.46 | MS-ADPCM 22050 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Courtney": tonal fx, mixed pitches (D6+22/A5+50) *(auto)* |
| Agent courtney sound #02 | 0.22 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Courtney": tonal fx, mixed pitches (G#4+13/C7+1) *(auto)* |
| Agent courtney sound #03 | 0.02 | PCM 22050 Hz 16-bit mono | percussive |  | 2 | xp | Search Companion "Courtney": short click/tick *(auto)* |
| Agent earl sound #01 | 0.68 | PCM 22050 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (F#5+22/F5+27) *(auto)* |
| Agent earl sound #02 | 0.15 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (C#6-8/C6-6) *(auto)* |
| Agent earl sound #03 | 1.70 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal swell/sweep, mixed pitches (A#5-7/C4-37) *(auto)* |
| Agent earl sound #07 | 0.28 | MS-ADPCM 22050 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (C5+32/E2-35) *(auto)* |
| Agent earl sound #08 | 0.23 | PCM 22050 Hz 16-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (F#8-22/F8+23) *(auto)* |
| Agent earl sound #09 | 0.51 | PCM 22050 Hz 16-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (D#8+22/E8+17) *(auto)* |
| Agent earl sound #12 | 0.18 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (D7-23/G5+25) *(auto)* |
| Agent earl sound #13 | 0.35 | MS-ADPCM 22050 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (F#3+7/G4+34) *(auto)* |
| Agent earl sound #15 | 0.56 | MS-ADPCM 22050 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (C#5-25/B4+42) *(auto)* |
| Agent earl sound #17 | 0.16 | PCM 11025 Hz 8-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (A5+19/G#5+11) *(auto)* |
| Agent earl sound #18 | 0.50 | MS-ADPCM 22050 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (A3-43/E5+34) *(auto)* |
| Agent earl sound #20 | 0.24 | MS-ADPCM 44100 Hz 4-bit stereo | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (G#7+36/A7+23) *(auto)* |
| Agent earl sound #21 | 0.29 | MS-ADPCM 44100 Hz 4-bit stereo | texture (tonal-fx) |  | 2 | xp | Search Companion "Earl" surfer: tonal fx, mixed pitches (G#7+36/A7+23) *(auto)* |
| Agent merlin sound #00 | 0.68 | MS-ADPCM 11025 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal fx, mixed pitches (F#6+6/G#6+16) *(auto)* |
| Agent merlin sound #03 | 0.95 | MS-ADPCM 11025 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal fx, mixed pitches (F#4+42/D5-50) *(auto)* |
| Agent merlin sound #06 | 2.12 | MS-ADPCM 8000 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal swell/sweep, mixed pitches (C4+44/D#4+6) *(auto)* |
| Agent merlin sound #07 | 2.12 | MS-ADPCM 8000 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal swell/sweep, mixed pitches (G#3-47/G#3+45) *(auto)* |
| Agent merlin sound #12 | 0.27 | PCM 11025 Hz 16-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal fx, mixed pitches (A#4-2/F6-35) *(auto)* |
| Agent merlin sound #15 | 0.07 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): short click/tick *(auto)* |
| Agent merlin sound #16 | 0.07 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): short click/tick *(auto)* |
| Agent merlin sound #17 | 0.06 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): short click/tick *(auto)* |
| Agent merlin sound #18 | 0.06 | PCM 11025 Hz 8-bit mono | percussive |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): short click/tick *(auto)* |
| Agent merlin sound #26 | 0.73 | MS-ADPCM 11025 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal swell/sweep, mixed pitches (B4-24/A#4+18) *(auto)* |
| Agent merlin sound #30 | 0.50 | MS-ADPCM 11025 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): tonal fx, mixed pitches (D3+6/A#2-12) *(auto)* |
| Agent qmark sound #00 | 1.32 | PCM 22050 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | xp | OOBE "question mark" assistant (qmark.acs): tonal fx, mixed pitches (E4+8/E6+9) *(auto)* |
| Agent qmark sound #03 | 1.59 | PCM 22050 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | xp | OOBE "question mark" assistant (qmark.acs): tonal swell/sweep, mixed pitches (F#4+8/F#6+9) *(auto)* |
| Agent qmark sound #05 | 1.97 | PCM 22050 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | xp | OOBE "question mark" assistant (qmark.acs): tonal swell/sweep, mixed pitches (A#3+8/A#5+10) *(auto)* |
| Agent rover sound #00 | 0.09 | MS-ADPCM 44100 Hz 4-bit mono | percussive |  | 2 | xp | Search Companion "Rover" dog: short click/tick *(auto)* |
| Agent rover sound #02 | 0.23 | MS-ADPCM 44100 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Rover" dog: tonal fx, mixed pitches (C5+5/C#5-21) *(auto)* |
| Agent rover sound #03 | 0.09 | MS-ADPCM 11025 Hz 4-bit mono | percussive |  | 2 | xp | Search Companion "Rover" dog: short click/tick *(auto)* |
| Agent rover sound #04 | 0.09 | MS-ADPCM 11025 Hz 4-bit mono | percussive |  | 2 | xp | Search Companion "Rover" dog: short click/tick *(auto)* |
| Agent rover sound #05 | 0.23 | MS-ADPCM 44100 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Rover" dog: tonal fx, mixed pitches (F#5-3/G5-38) *(auto)* |
| Agent rover sound #06 | 0.28 | MS-ADPCM 44100 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Rover" dog: tonal fx, mixed pitches (F#2+32/B6+11) *(auto)* |
| Agent rover sound #07 | 0.28 | MS-ADPCM 44100 Hz 4-bit mono | texture (tonal-fx) |  | 2 | xp | Search Companion "Rover" dog: tonal fx, mixed pitches (C6+27/C#6-4) *(auto)* |
| Agent rover sound #08 | 0.01 | PCM 22050 Hz 8-bit mono | percussive |  | 2 | xp | Search Companion "Rover" dog: short click/tick *(auto)* |
| Agent courtney sound #01 | 0.31 | PCM 22050 Hz 8-bit mono | noise |  | 1 | xp | Search Companion "Courtney": noisy burst with slow swell (foley/whoosh/hit) *(auto)* |
| Agent earl sound #05 | 0.19 | MS-ADPCM 44100 Hz 4-bit stereo | noise |  | 1 | xp | Search Companion "Earl" surfer: noisy burst (foley/whoosh/hit) *(auto)* |
| Agent earl sound #06 | 0.18 | MS-ADPCM 44100 Hz 4-bit stereo | noise |  | 1 | xp | Search Companion "Earl" surfer: noisy burst (foley/whoosh/hit) *(auto)* |
| Agent earl sound #10 | 0.53 | PCM 11025 Hz 16-bit mono | texture |  | 1 | xp | Search Companion "Earl" surfer: noisy fx with some pitch (D7+24/C7-14) *(auto)* |
| Agent earl sound #11 | 0.53 | PCM 11025 Hz 16-bit mono | texture |  | 1 | xp | Search Companion "Earl" surfer: noisy fx with some pitch (D7+24/A#5+47) *(auto)* |
| Agent earl sound #14 | 0.88 | PCM 11025 Hz 8-bit mono | noise |  | 1 | xp | Search Companion "Earl" surfer: noisy burst (foley/whoosh/hit) *(auto)* |
| Agent earl sound #16 | 0.81 | MS-ADPCM 22050 Hz 4-bit mono | texture |  | 1 | xp | Search Companion "Earl" surfer: noisy fx with some pitch (G#6-5/C7-17) *(auto)* |
| Agent earl sound #19 | 0.41 | MS-ADPCM 22050 Hz 4-bit mono | noise |  | 1 | xp | Search Companion "Earl" surfer: noisy burst with slow swell (foley/whoosh/hit) *(auto)* |
| Agent merlin sound #01 | 3.00 | MS-ADPCM 8000 Hz 4-bit mono | texture |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy fx with some pitch (A#4+24/B4+6) *(auto)* |
| Agent merlin sound #02 | 0.62 | MS-ADPCM 8000 Hz 4-bit mono | texture |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy fx with some pitch (A2-49/G#2-5) *(auto)* |
| Agent merlin sound #05 | 0.14 | PCM 11025 Hz 8-bit mono | texture |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy fx with some pitch (C#4-42/D4-10) *(auto)* |
| Agent merlin sound #13 | 1.04 | MS-ADPCM 11025 Hz 4-bit mono | noise |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy burst (foley/whoosh/hit) *(auto)* |
| Agent merlin sound #24 | 0.45 | MS-ADPCM 11025 Hz 4-bit mono | noise |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy burst with slow swell (foley/whoosh/hit) *(auto)* |
| Agent merlin sound #25 | 0.38 | PCM 11025 Hz 16-bit mono | noise |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy burst (foley/whoosh/hit) *(auto)* |
| Agent merlin sound #27 | 0.15 | PCM 22050 Hz 16-bit mono | noise |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy burst (foley/whoosh/hit) *(auto)* |
| Agent merlin sound #29 | 0.54 | MS-ADPCM 11025 Hz 4-bit mono | noise |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy burst with slow swell (foley/whoosh/hit) *(auto)* |
| Agent merlin sound #31 | 1.10 | MS-ADPCM 22050 Hz 4-bit mono | texture |  | 1 | xp | MS Agent "Merlin" character (C:\WINDOWS\msagent\chars\merlin.acs): noisy fx with some pitch (C#8+12/C8-16) *(auto)* |
| Agent qmark sound #01 | 0.27 | PCM 22050 Hz 16-bit stereo | texture |  | 1 | xp | OOBE "question mark" assistant (qmark.acs): noisy fx with some pitch (A#4+33/G4-20) *(auto)* |
| Agent rover sound #01 | 0.14 | MS-ADPCM 44100 Hz 4-bit mono | texture |  | 1 | xp | Search Companion "Rover" dog: noisy fx with some pitch (E2-35/E2+22) *(auto)* |
| Agent earl sound #00 | 0.15 | PCM 11025 Hz 8-bit mono | none |  | 0 | xp | Search Companion "Earl" surfer: silent/empty *(auto)* |

### General MIDI files (4)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| CANYON.MID | 124.00 | SMF type 0, 33,883 bytes | texture (music) |  | 1 | 311 | George Stone, "Trip Through the Grand Canyon" (Passport Designs/Music Data Co., 1990); GM sequence, ~2:04 Note: Not playable by Sound Recorder; would need rendering through a synth to WAV first. |
| flourish.mid | 87.50 | SMF type 1 | texture (music) |  | 1 | xp | Nathan Grigg (attrib.), orchestral GM piece; also DxDiag DirectMusic test |
| onestop.mid | 247.40 | SMF type 1 | texture (music) |  | 1 | xp | David Yackley, 4-min GM jam (the famous "onestop") |
| town.mid | 79.00 | SMF type 1 | texture (music) |  | 1 | xp | Nathan Grigg (attrib.), small-town GM piece |

### Synth sample sets (1)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| gm.dls (Microsoft GS Wavetable SW Synth) |  | DLS level 1 | texture (music) |  | 2 | xp | Roland GS Sound Canvas sample set: 235 instruments, 495 wave samples, 3.44 MB; "Copyright 1996 Roland Corporation U.S." Note: Playable only via MIDI (kmixer/swmidi), not via Sound Recorder. |

### Speech (3)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| Microsoft Sam (SAPI 5.1) |  | SAPI 5.1 engine data, 1.7 MB | speech |  | 2 | xp | Microsoft Sam diphone TTS voice (the XP default voice; used by Narrator) Note: Could render any word/phoneme into a WAV inside the guest (e.g. a vowel "aaah" as a pitched vocal source); narrator.exe and sapi.cpl present. |
| Narrator |  |  | speech |  | 1 | xp | screen reader speaking with Microsoft Sam |
| MS Agent L&H TruVoice bridge |  |  | speech |  | 0 | xp | MS Agent bridge to the Lernout & Hauspie TruVoice TTS; the TruVoice engine itself (tv_enua.exe) is NOT installed in our image |

### Sample Music (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | In image | Character |
|---|---|---|---|---|---|---|---|
| Beethoven's Symphony No. 9 (Scherzo).wma |  | WMA | texture (music) |  | 0 | xp | orchestral recording (third-party licensed) |
| New Stories (Highway Blues).wma |  | WMA | texture (music) |  | 0 | xp | jazz/blues recording (third-party licensed) |

## Category tables: other Windows versions (not in our images)

### Version by version

| Version | What shipped (C:\WINDOWS or \MEDIA) | New / notable |
|---|---|---|
| 3.0 (1990) | No sounds (no wave support). | - |
| 3.0 + Multimedia Extensions 1.0 (OEM, 1991) | BELLS, BLOCKS, CLOCK, GONG, JAWHARP, LASER, OHOH, SIREN, WATER (22 kHz 8-bit mono); Passport "Media Music" MIDI (ALMONDS, SEASONS, BRNDNBRG, CANYON, DREAMY, METBLAST, PASSPORT, SOMEBAND, STOMP) | A whole forgotten set, tonal and FX |
| 3.1 (1992) | CHIMES, CHORD, DING, TADA (22 kHz 8-bit mono); CANYON.MID | The first four "Windows sounds"; TADA is the startup |
| WfW 3.11 (1993) | CHIMES, DING, RINGIN, RINGOUT (11 kHz 8-bit, for Chat); CANYON.MID | CHORD and TADA dropped (WFWADD restores them) |
| NT 3.1 / 3.5 / 3.51 | CHIMES, CHORD, DING, RINGIN, RINGOUT, TADA; CANYON.MID | Same files as 3.1/WfW |
| 95 retail / OSR2 | The Microsoft Sound (Brian Eno), CHIMES/CHORD/DING/TADA (3.1 audio re-saved), CANYON/PASSPORT.MID, 7 Midisoft RMIs, Jungle/Musica/Robotz/Utopia schemes (13-16 events each) | Eno startup; the four schemes |
| NT 4.0 | Windows NT Logon/Logoff Sound (10 s, 8-bit stereo), The Microsoft Sound, the 3.1 originals, ringin/ringout, MIDI/RMI, schemes | Two long NT swells |
| 98 / 98 SE | New "Microsoft Sound 98" (Ken Kato, 7.9 s), logoff.wav, re-recorded 16-bit chimes/chord/ding/tada, new notify, recycle, start (IE); MIDI/RMI; schemes; Plus! 95 and Kids themes | These 98 files are the ones still in XP's Media folder |
| ME | New logon (5.5 s) and logoff (3.9 s); flourish/onestop/town.mid new; canyon, passport, RMIs removed | - |
| 2000 | Windows Logon/Logoff Sound (ME audio), The Microsoft Sound (Eno), 98 legacy sounds, ir_*.wav, canyon/passport, RMIs, Utopia | - |
| XP | 26 "Windows XP *.wav" (Bill Brown with Tom Ozanich) + the 98 legacy nine; ir_*; flourish/onestop/town; SP2 adds Information Bar and Pop-up Blocked; IE7 adds 4 more | Our image |
| XP Tablet 2005 / MCE 2004-2005 | Tablet: SpMicOn/SpMicOff/SpRec/SpUnrec in tabletpc.cab. MCE: no Media-folder WAVs found. | Unverified install location |
| Vista | 28 "Windows *.wav" + 5 Speech + legacy names remade at 44.1 kHz; boot sound inside imageres.dll (Fripp / Martine / Ball) | Startup.wav in Media is a 0.2 s blip, not the boot sound |
| 7 | Vista names (4 remade), plus 13 scheme folders x 20 files (MP3-in-WAV) | Afternoon ... Sonata |

### Windows 3.0 MME system sounds (9)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| BELLS.WAV | 2.56 | PCM 22050 Hz 8-bit mono | texture (tonal-fx) |  | 2 | peal of bells, bright inharmonic partials (default SystemStart) |
| BLOCKS.WAV | 0.43 | PCM 22050 Hz 8-bit mono | tonal | A#5 | 5 | woodblock knock, pitched ~A#5 (default beep) |
| CLOCK.WAV | 3.53 | PCM 22050 Hz 8-bit mono | tonal (tonal-phrase) | G5 | 2 | clock chime phrase with swell (hourly chime) |
| GONG.WAV | 3.85 | PCM 22050 Hz 8-bit mono | texture (tonal-fx) |  | 2 | gong, long inharmonic ring (alarm) |
| JAWHARP.WAV | 1.88 | PCM 22050 Hz 8-bit mono | tonal | D2 | 4 | jaw-harp twang, buzzy drone (question) |
| LASER.WAV | 0.79 | PCM 22050 Hz 8-bit mono | texture (tonal-fx) |  | 2 | laser zap, falling pitch sweep (critical stop) |
| OHOH.WAV | 0.52 | PCM 22050 Hz 8-bit mono | speech | D5 | 1 | voice: "uh-oh" (exclamation) |
| SIREN.WAV | 2.68 | PCM 22050 Hz 8-bit mono | texture (tonal-fx) |  | 2 | siren, wailing sweep around Eb6-F6 |
| WATER.WAV | 1.92 | PCM 22050 Hz 8-bit mono | noise |  | 1 | running/pouring water, noise (exit) |

### Windows 3.x system sounds (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| CHORD.WAV | 1.13 | PCM 22050 Hz 8-bit mono | tonal (tonal-chord) | A2 | 3 | 3.1 original synth chord stab, A-based (A2/E4/A4), 8-bit |
| TADA.WAV | 1.26 | PCM 22050 Hz 8-bit mono | tonal (tonal-chord) | C3 | 3 | 3.1 original brass "ta-da", C, 8-bit (the 3.1 / NT startup) |

### Windows 95 Media (10)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| The Microsoft Sound.wav | 6.12 | PCM 22050 Hz 8-bit mono | tonal (pad) | F3 | 3 | Brian Eno startup: 6.1 s shimmering ambient swell, F major (F3/C4/F4), 8-bit mono |
| Win95 scheme sound (unidentified #10) | 1.57 | PCM 22050 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | tonal fx, mixed pitches (E4-5/G4-18) |
| TADA.WAV (95 re-save) | 1.25 | PCM 22050 Hz 8-bit mono | tonal (tonal-chord) | C3 | 3 | 3.1 ta-da re-saved for 95 |
| Jungle Windows Start.wav | 5.35 | PCM 22050 Hz 16-bit stereo | texture |  | 1 | jungle ambience startup: birds/animals over noise bed, 5.3 s |
| Musica Windows Start.wav | 2.13 | PCM 22050 Hz 8-bit mono | tonal (pad) | D4 | 4 | Musica startup: soft sustained D-based synth chord swell, 2.1 s |
| Robotz Windows Start.wav | 3.10 | PCM 22050 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Robotz startup: metallic robotic sweep, G/D, 3.1 s |
| Utopia Windows Start.wav | 3.51 | PCM 22050 Hz 16-bit mono | tonal (tonal-chord) | G3 | 4 | Utopia startup: struck G chord with long ring, 3.5 s |
| Win95 scheme sound (unidentified #7) | 0.18 | PCM 22050 Hz 16-bit mono | tonal | G5 | 5 | pitched struck tone, decaying around G5+4 |
| Win95 scheme sound (unidentified #8) | 0.19 | PCM 22050 Hz 8-bit mono | tonal | G5 | 5 | pitched sustained tone around G5+10 |
| Win95 scheme sound (unidentified #9) | 0.48 | PCM 22050 Hz 16-bit stereo | tonal | A4 | 5 | pitched struck tone, decaying around A4+0 |

### Windows 95 sound schemes (55)

File list from KB Q177517 and the 95 install media; only the four *Windows Start* files were measured (see "Windows 95 Media").

| Scheme | Events | Files |
|---|---|---|
| Jungle | 13 | Asterisk, Close, Default, Exclamation, Maximize, Menu Command, Menu Popup, Minimize, Open, Question, Recycle, Restore Down, Windows Exit |
| Musica | 13 | Asterisk, Close, Default, Exclamation, Maximize, Menu Command, Menu Popup, Minimize, Open, Question, Recycle, Restore Down, Windows Exit |
| Robotz | 13 | Asterisk, Close, Default, Exclamation, Maximize, Menu Command, Menu Popup, Minimize, Open, Question, Recycle, Restore Down, Windows Exit |
| Utopia | 16 | Asterisk, Close, Default, Exclamation, Maximize, Menu Command, Menu Popup, Minimize, Open, Question, Recycle, Restore Down, Windows Exit, Critical Stop, Error, Restore Up |

### Windows NT Media (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| Windows NT Logoff Sound.wav | 9.97 | PCM 22050 Hz 8-bit stereo | tonal (pad) | G2 | 2 | NT4 logoff: 10 s pad swell around G, 8-bit stereo |
| Windows NT Logon Sound.wav | 9.97 | PCM 22050 Hz 8-bit stereo | tonal (pad) |  | 2 | NT4 logon: 10 s slow orchestral/pad swell, 8-bit stereo |

### Windows 98 Media (5)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| chord.wav (98 re-recording) | 1.10 | PCM 22050 Hz 16-bit stereo | tonal (tonal-chord) | G3 | 3 | same file as our XP chord.wav |
| logoff.wav (98) | 3.55 | PCM 22050 Hz 16-bit stereo | tonal (pad) | F3 | 3 | 98 shutdown: 3.6 s soft swell, F (F2/C3/C4/F4) |
| The Microsoft Sound.wav (98, "The Microsoft Sound 98") | 7.86 | PCM 22050 Hz 16-bit stereo | tonal (pad) | C3 | 3 | Windows 98 startup by Ken Kato: 7.9 s swelling orchestral/synth chord, C/G/D |
| welcom98.wav | 13.29 | MS-ADPCM 44100 Hz 4-bit mono | texture (music) |  | 0 | Welcome to Windows 98 tour music, 13 s (in this copy), ADPCM |
| Windows 98 welcom98 / blip.wav / testsnd.wav |  |  | texture (tonal-fx) |  | 0 | blip.wav and testsnd.wav are the NetMeeting files also in our XP image |

### Windows ME / 2000 Media (2)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| logoff.wav (ME) = Windows Logoff Sound.wav (2000) | 3.90 | PCM 22050 Hz 16-bit stereo | tonal (pad) | D#4 | 3 | ME/2000 logoff: 3.9 s falling chord, Eb (Eb4/Bb3/F5) |
| The Microsoft Sound.wav (ME) = Windows Logon Sound.wav (2000) | 5.51 | PCM 22050 Hz 16-bit stereo | tonal (pad) | A#3 | 3 | ME/2000 logon: 5.5 s bright rising chord, Bb (Bb5/F5/C5) |

### Windows XP extras (12)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| Windows Navigation Start.wav (IE7) | 0.06 | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | IE7 navigation click, 44.1 kHz |
| ir_begin/ir_end/ir_inter.wav (one of) | 0.71 | MS-ADPCM 22050 Hz 4-bit stereo | texture (tonal-fx) |  | 2 | infrared transfer blip, F-ish tonal swell, ADPCM |
| ir_begin.wav |  |  | texture (tonal-fx) |  | 1 | infrared-transfer blips (ADPCM) |
| ir_end.wav |  |  | texture (tonal-fx) |  | 1 | infrared-transfer blips (ADPCM) |
| ir_inter.wav |  |  | texture (tonal-fx) |  | 1 | infrared-transfer blips (ADPCM) |
| Windows Feed Discovered.wav |  |  | percussive |  | 2 | IE7 UI blips (44.1 kHz) |
| Windows Information Bar.wav |  |  | percussive |  | 2 | IE7 UI blips (44.1 kHz) |
| Windows Pop-up Blocked.wav |  |  | percussive |  | 2 | IE7 UI blips (44.1 kHz) |
| SpMicOn.wav |  |  | percussive |  | 2 | speech-recognition mic on/off/recognised/unrecognised blips (location after install unverified) |
| SpMicOff.wav |  |  | percussive |  | 2 | speech-recognition mic on/off/recognised/unrecognised blips (location after install unverified) |
| SpRec.wav |  |  | percussive |  | 2 | speech-recognition mic on/off/recognised/unrecognised blips (location after install unverified) |
| SpUnrec.wav |  |  | percussive |  | 2 | speech-recognition mic on/off/recognised/unrecognised blips (location after install unverified) |

### Windows Vista / 7 Media (44)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| Garden\Windows Ding.wav | 1.06 | PCM 44100 Hz 16-bit stereo | tonal | A6 | 4 | Garden scheme ding: bright bell A6, PCM |
| Garden\Windows Logon Sound.wav | 1.78 | MP3-in-WAV 44100 Hz stereo | unknown |  | 0 | Garden scheme logon, MP3-in-WAV (not decodable by Sound Recorder without the MP3 ACM) |
| Windows Logon Sound.wav (7) | 0.89 | PCM 44100 Hz 16-bit stereo | tonal (tonal-chord) | E5 | 4 | Windows 7 logon: short (0.9 s) bright A/E chime-chord |
| chord.wav (Vista/7 remake) | 0.65 | PCM 44100 Hz 16-bit stereo | tonal (tonal-chord) | E4 | 3 | 44.1 kHz remake of chord, E-based (E5/G4/B5), shorter |
| tada.wav (Vista/7 remake) | 1.62 | PCM 44100 Hz 16-bit stereo | tonal (tonal-chord) | D3 | 4 | 44.1 kHz remake of tada, D/A fanfare |
| Windows Balloon.wav |  | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Battery Critical.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-chord) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Battery Low.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Critical Stop.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-chord) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Default.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Ding.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Error.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Exclamation.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Feed Discovered.wav |  | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Hardware Fail.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-phrase) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Hardware Insert.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-phrase) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Hardware Remove.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-phrase) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Information Bar.wav |  | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Logoff Sound.wav |  | PCM 44100 Hz 16-bit stereo | tonal (pad) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Logon Sound.wav |  | PCM 44100 Hz 16-bit stereo | tonal (pad) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Menu Command.wav |  | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Minimize.wav |  | PCM 44100 Hz 16-bit stereo | texture |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Navigation Start.wav |  | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Notify.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Pop-up Blocked.wav |  | PCM 44100 Hz 16-bit stereo | percussive |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Print complete.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Recycle.wav |  | PCM 44100 Hz 16-bit stereo | noise |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Restore.wav |  | PCM 44100 Hz 16-bit stereo | texture |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Ringin.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Ringout.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Shutdown.wav |  | PCM 44100 Hz 16-bit stereo | tonal (pad) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Startup.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-phrase) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows User Account Control.wav |  | PCM 44100 Hz 16-bit stereo | tonal (tonal-chord) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Speech Disambiguation.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Speech Misrecognition.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Speech Off.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Speech On.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Speech Sleep.wav |  | PCM 44100 Hz 16-bit stereo | texture (tonal-fx) |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| chimes.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| ding.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| notify.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| recycle.wav |  | PCM 44100 Hz 16-bit stereo | noise |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| ringout.wav |  | PCM 44100 Hz 16-bit stereo | tonal |  | 2 | Vista/7 44.1 kHz system sound (Steve Ball et al.); class inferred from the event name, unverified |
| Windows Vista boot sound | 4.00 |  | tonal (pad) |  | 3 | 4 s boot sound: Robert Fripp melody, Tucker Martine rhythm, Steve Ball orchestration; plays at boot, not a Media file |

### Windows 7 sound schemes (13)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| Windows 7 "Afternoon" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Afternoon scheme: 12-string guitars Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Calligraphy" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Calligraphy scheme: East Asian solo instruments Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Characters" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | texture (tonal-fx) |  | 2 | Characters scheme: synthesized cartoon-ish Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Cityscape" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Cityscape scheme: retro jazz club Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Delta" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Delta scheme: blues/roots Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Festival" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Festival scheme: samba/mariachi Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Garden" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Garden scheme: gentle bells/nature (undescribed by Microsoft) Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Heritage" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Heritage scheme: Spanish classical guitar Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Landscape" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Landscape scheme: Copland-style pastoral orchestra Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Quirky" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | texture (tonal-fx) |  | 2 | Quirky scheme: synthesized, quirky Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Raga" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Raga scheme: Indian instruments (sitar/tabla) Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Savanna" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Savanna scheme: African percussion and kalimba Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |
| Windows 7 "Sonata" scheme (20 files) |  | MP3-in-WAV 44.1 kHz stereo (Windows Ding.wav is PCM) | tonal (tonal-phrase) |  | 2 | Sonata scheme: Vivaldi-style strings Note: Files: Windows Balloon.wav, Windows Battery Critical.wav, Windows Battery Low.wav, Windows Critical Stop.wav, Windows Default.wav, Windows Ding.wav, Windows Error.wav, Windows Exclamation.wav, Windows Feed Discovered.wav, Windows Hardware Fail.wav, Windows Hardware Insert.wav, Windows Hardware Remove.wav, Windows Information Bar.wav, Windows Logoff Sound.wav, Windows Logon Sound.wav, Windows Navigation Start.wav, Windows Notify.wav, Windows Pop-up Blocked.wav, Windows Print complete.wav, Windows User Account Control.wav. MP3-in-WAV must be decoded to PCM before Sound Recorder can edit it. |

### General MIDI files (16)

| Sound | s | Format | Synth class | Root | Use 0-5 | Character |
|---|---|---|---|---|---|---|
| ALMONDS.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| SEASONS.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| BRNDNBRG.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| DREAMY.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| METBLAST.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| PASSPORT.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| SOMEBAND.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| STOMP.MID |  |  | texture (music) |  | 0 | Passport Designs "Media Music" MIDI sequence |
| Bach's Brandenburg Concerto No. 3.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| Beethoven's 5th Symphony.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| Beethoven's Fur Elise.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| Dance of the Sugar-Plum Fairy.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| Debussy's Claire de Lune.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| In the Hall of the Mountain King.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| Mozart's Symphony No. 40.rmi |  |  | texture (music) |  | 0 | Midisoft GM arrangement of a classical piece (RMID) |
| PASSPORT.MID |  |  | texture (music) |  | 0 | "Passport Please" (Music Data Co.) GM sequence |

## Category tables: Plus! packs (not in our images)

Every Plus! theme sound below was measured from the original media. The JSON has all 813 files; here each theme is one row.

| Pack: theme | Files | Format(s) | Startup s | Startup root | Tonal / perc / noise / texture | Best tonal sources (root) | Flags |
|---|---|---|---|---|---|---|---|
| Plus! 95: Dangerous Creatures | 13 | MS-ADPCM | 4.07 | C#5 | 7 / 0 / 0 / 6 | default sound (F#2); empty recycle bin (A2); menu command (F3) |  |
| Plus! 95: Leonardo da Vinci | 15 | MS-ADPCM | 1.10 |  | 10 / 0 / 0 / 5 | exclamation (G5); minimize (G5); restore down (F#5) |  |
| Plus! 95: The Golden Era | 14 | MS-ADPCM | 1.10 |  | 2 / 1 / 2 / 9 | exclamation (G#5); exit windows (E2) |  |
| Plus! 95: Mystery | 14 | MS-ADPCM | 2.78 | A#3 | 4 / 0 / 0 / 10 | menu command (D#3); menu popup (A2); startup (A#3) |  |
| Plus! 95: Nature | 16 | MS-ADPCM | 3.24 |  | 6 / 1 / 1 / 8 | critical stop (D#6); default sound (F#6); exclamation (A5) |  |
| Plus! 95: Inside Your Computer | 16 | MS-ADPCM | 2.14 | G5 | 6 / 2 / 2 / 6 | asterisk (D#6); beep (E5); startup (G5) |  |
| Plus! 95: Science | 16 | MS-ADPCM | 0.78 |  | 4 / 0 / 3 / 9 | asterisk (F3); exclamation (C#4); exit windows (E3) |  |
| Plus! 95: Sports | 14 | MS-ADPCM | 2.34 |  | 3 / 0 / 0 / 11 | asterisk (E3); empty recycle bin (G#4) |  |
| Plus! 95: The 60's USA | 16 | MS-ADPCM | 2.88 |  | 4 / 2 / 0 / 10 | beep (A5); exclamation (C4); default sound (E4) |  |
| Plus! 95: Travel | 16 | MS-ADPCM | 0.96 |  | 1 / 1 / 0 / 14 | critical stop (A#2) |  |
| Plus! 95: Windows 95 / More Windows | 15 | MS-ADPCM, PCM |  |  | 7 / 0 / 1 / 7 | beep (E3); default sound (D#3); asterisk (B5) |  |
| Plus! 98: Lose Your Marbles | 54 | PCM |  |  | 5 / 7 / 7 / 35 | DISTORT.WAV (F5); VICTORY.WAV (D#6); WINDOUT1.WAV (B2) |  |
| Plus! 98: Architecture | 18 | PCM | 9.96 | D3 | 4 / 0 / 1 / 13 | exit windows (D3); startup (D3) |  |
| Plus! 98: Corbis Photography | 18 | MS-ADPCM | 4.98 | C4 | 5 / 0 / 8 / 5 | ring in (C#5); ring out (F#4); empty recycle bin (A4) | Corbis licence |
| Plus! 98: Cityscape | 19 | PCM | 12.42 | F4 | 7 / 0 / 0 / 12 | asterisk (C#5); exit windows (B5); new mail (A#6) |  |
| Plus! 98: Cathy | 14 | PCM, MS-ADPCM | 2.94 | C3 | 6 / 3 / 2 / 3 | critical stop (D5); menu command (A4); maximize (F#4) | licensed comic |
| Plus! 98: Doonesbury | 14 | PCM, MS-ADPCM | 4.81 | A4 | 4 / 2 / 0 / 8 | maximize (A#3); menu command (A4); restore down (A#3) | licensed comic; WAV tags "Kaboom! Factory" SFX library |
| Plus! 98: Fashion | 18 | PCM | 10.40 | D3 | 3 / 1 / 1 / 13 | exit windows (G4); startup (D3) |  |
| Plus! 98: Falling Leaves | 19 | PCM | 6.08 | F5 | 4 / 0 / 2 / 13 | asterisk (E3); exit windows (C5); startup (F5) |  |
| Plus! 98: FoxTrot | 14 | PCM, MS-ADPCM | 4.77 | C#5 | 7 / 0 / 1 / 6 | menu command (A4); asterisk (B3); exclamation (B3) | licensed comic |
| Plus! 98: Garfield | 19 | PCM | 7.08 | D3 | 3 / 1 / 2 / 13 | ring out (F4); startup (D3); exit windows (F#5) | licensed comic |
| Plus! 98: Geometry | 19 | PCM | 10.14 | C4 | 5 / 0 / 0 / 14 | exit windows (F4); startup (C4) |  |
| Plus! 98: Horror Channel | 24 | IMA-ADPCM | 10.92 |  | 4 / 0 / 1 / 5 | menu popup (E2); scrm2 (B5) |  |
| Plus! 98: Jazz | 18 | PCM | 3.26 | A#2 | 4 / 0 / 0 / 14 | default sound (A6); startup (A#2); exit windows (D3) |  |
| Plus! 98: PhotoDisc | 18 | PCM | 7.96 | C4 | 8 / 1 / 0 / 9 | exclamation (A4); question (C5); critical stop (C5) | PhotoDisc licence |
| Plus! 98: Peanuts | 18 | PCM | 17.66 | G#2 | 10 / 0 / 0 / 8 | mailb (A#5); default sound (A#5); question (E4) | licensed comic (Peanuts) |
| Plus! 98: Rock-n-Roll | 18 | PCM | 11.12 |  | 6 / 0 / 0 / 12 | new mail (G3); empty recycle bin (B3); critical stop (E3) |  |
| Plus! 98: Science Fiction | 18 | PCM | 11.97 | F4 | 4 / 1 / 0 / 13 | program error (F#4); default sound (D#4); exit windows (A3) |  |
| Plus! 98: Windows 98 | 19 | PCM | 7.86 | C3 | 11 / 0 / 1 / 7 | asterisk (G3); new mail (B5); ring in (B6) | exit sound (c) Panther Modern LLC (Stan LePard) |
| Plus! 98: World Traveler | 18 | PCM | 6.25 | F3 | 5 / 0 / 2 / 11 | asterisk (B4); exit windows (C4); startup (F3) |  |
| Plus! for Kids: Horses | 18 | MS-ADPCM | 1.61 | G6 | 8 / 0 / 1 / 9 | defbep (G3); defsnd (G3); startw (G6) |  |
| Plus! for Kids: Bugs | 18 | MS-ADPCM | 3.14 |  | 3 / 0 / 2 / 13 |  |  |
| Plus! for Kids: Baseball | 18 | MS-ADPCM | 4.23 | A4 | 3 / 0 / 1 / 14 | startw (A4) |  |
| Plus! for Kids: Underwater | 18 | MS-ADPCM | 4.54 | C3 | 4 / 0 / 5 / 9 | exclam (A5); maxmiz (F3); startw (C3) |  |
| Plus! for Kids: Treehouse | 18 | MS-ADPCM | 3.58 |  | 6 / 0 / 1 / 11 | astrix (D5); defsnd (B4); exitwd (B2) |  |
| Plus! for Kids: Space | 18 | MS-ADPCM | 0.81 |  | 4 / 0 / 5 / 9 | astrix (E4); crtstp (B5); questn (F3) |  |
| Plus! for Kids: Snowboarding | 18 | MS-ADPCM | 4.80 | A4 | 9 / 0 / 0 / 9 | defsnd (A2); exclam (D4); startw (A4) |  |
| Plus! for Kids: RE-man | 18 | MS-ADPCM | 7.99 | G2 | 4 / 0 / 0 / 14 | exclam (G#5); startw (G2); closp (B3) |  |
| Plus! for Kids: Messy Room | 18 | MS-ADPCM, PCM | 2.23 | A#2 | 3 / 0 / 0 / 15 | enucmd (F#6); mpopup (A#6); startw (A#2) |  |
| Plus! for Kids: Jungle | 18 | MS-ADPCM | 0.77 |  | 6 / 0 / 0 / 12 | defsnd (A6); minimz (G#4); proger (D4) |  |
| Plus! XP: Aquarium | 21 | PCM | 2.81 | B2 | 9 / 1 / 1 / 10 | Error (F5); Open (E4); Asterisk (A4) | Sound Ideas-style library names inside (inferred) |
| Plus! XP: Nature | 20 | PCM | 2.90 |  | 6 / 6 / 0 / 8 | Question (D#4); Recycle (C#6); SysExit (C#6) |  |
| Plus! XP: Space | 21 | PCM | 6.48 | G4 | 9 / 5 / 1 / 6 | MSpeakOK (C#6); MP3Done (D5); PDJ (D5) |  |
| Plus! XP: daVinci | 21 | PCM | 3.37 | E3 | 15 / 0 / 0 / 6 | Close (B4); Minimize (B4); Open (B4) |  |
| Plus! XP: Voice Command | 2 | PCM |  |  | 0 / 2 / 0 / 0 |  |  |
| Plus! DME: Alarm Clock | 6 | WMA |  |  | 6 / 0 / 0 / 0 |  |  |

Notes on the packs:

- **Plus! 95** (11 themes, 165 sounds): `XX_EVENT.WAV` plus a mono `.WA8` copy for 256-colour installs, renamed on install to "<Theme> <event>.wav" in `Program Files\Plus!\Themes`. MS-ADPCM 22 kHz throughout. Windows 98 shipped these themes too. 3D Pinball first shipped here (42 WAVs, (c) Cinematronics).
- **Plus! for Kids** (1997, 10 themes x 18): RE-man, Messy Room, Jungle, Space, Treehouse, Baseball, Horses, Bugs, Underwater, Snowboarding. Jungle, Space, Baseball and Underwater are also on the Windows 98 CD. MS-ADPCM.
- **Plus! 98** (18 themes, 323 sounds, all new): mostly 16-bit PCM, long startups (up to 17.7 s for Peanuts). Sound design largely by Bill Wolford; "The Microsoft Sound 98" theme startup by Ken Kato; the Windows 98 theme exit by Stan LePard (c) Panther Modern LLC. Lose Your Marbles adds about 50 game WAVs.
- **Plus! XP** (Aquarium, da Vinci, Nature, Space; 21 events each, Nature 20): 16-bit PCM installed into `C:\WINDOWS\Media` as "<Theme> <Event>.wav", by Stan LePard. Nature is real birdsong (mockingbird, thrush). Labyrinth has 27 WAVs; HyperBowl and Russian Square pack their audio in data files.
- **Plus! Digital Media Edition** (2003): only the Alarm Clock WMAs (3 alarms, 3 hourly chimes). **Plus! SuperPack** (2004) repackages XP + DME.

## Built-in programs, games, speech and other software (not in our images)

| Sound | Synth class | Character | Distribution |
|---|---|---|---|
| Hover! sounds and music | texture (tonal-fx) | hovercraft hits/pickups WAVs + per-maze MIDI (.MUZ); music by Stan LePard | Windows 95 CD extras; not in our images |
| Minesweeper (3.1) sounds | percussive | 3.1 Minesweeper tick/boom (Sound=3 in winmine.ini); our 3.11 WINMINE.EXE is present but silent unless enabled (unverified) | Bundled with 3.1; not in our images |
| Vista/7 games sounds (Chess Titans, Mahjong Titans, Purble Place, InkBall, Solitaire...) | percussive | short UI SFX packed as resources (Oberon Media titles) | Bundled with Vista/7 Home Premium+; not in our images |
| Windows 7 sample music: Kalimba, Maid with the Flaxen Hair, Sleep Away | texture (music) | MP3 recordings (Mr. Scruff, Richard Stoltzman, Bob Acri) | Bundled with 7; LICENSE FLAG third-party; not in our images |
| Vista sample music (Amanda, Despertar, Din Din Wo, ...) | texture (music) | WMA recordings, ~11 tracks | Bundled with Vista; LICENSE FLAG third-party; not in our images |
| David Byrne "Like Humans Do" (XP promo) | texture (music) | licensed pop track | XP promo; LICENSE FLAG; not in our images |
| Windows 95 CD FUNSTUFF videos (Buddy Holly, Good Times) | texture (music) | music videos | Win95 CD; LICENSE FLAG third-party; not in our images |
| MSN Messenger 7+ nudge.wav (and later phone/vimdone) | noise | nudge: rattling buzz-shake | MSN Messenger 7.0+ download; not in our images |
| Office 97 assistants (Clippit, The Dot, Hoverbot, Office Logo, Mother Nature, Power Pup, Scribble, Will, The Genius) | texture (tonal-fx) | cartoon SFX embedded per animation (boings, whistles, paper rustles) | Office 97 retail; not in our images |
| Office 2000/XP assistants (Clippit, Links, Rocky, F1, The Dot, Office Logo, Merlin, Mother Nature, Genius) | texture (tonal-fx) | MS Agent .acs with embedded SFX (Merlin.acs is the same character as in our XP image) | Office 2000/XP retail; not in our images |
| Office Sounds add-on (Sounds.exe / sounds97.exe / sounds.msi) | percussive | short clicks, whooshes, chimes for Word/Excel/Outlook | free download (Office 97-2013); not in our images |
| Encarta / MindMaze | texture (music) | MIDI game music, speech, music clips and instrument samples | retail CD; licensed content; not in our images |
| Microsoft Bob (Rover etc.) | texture (tonal-fx) | guide character sounds and occasional speech (no file list found) | retail 1995; not in our images |
| 3D Movie Maker sound library | texture (tonal-fx) | SFX, music and voice clips inside content files; source code MIT (2022), asset licence unclear | retail 1995; not in our images |
| Microsoft Music Producer 1.0 | texture (music) | style/personality MIDI generator through the GS synth | Visual Studio 97 CD; not in our images |
| Microsoft Musical Instruments | tonal | 203 instrument samples (with Dorling Kindersley) - a real acoustic sample library | retail 1992; DK co-owned content (LICENSE FLAG); not in our images |
| Windows Sound System 2.0 ProofReader voice | speech | recorded human voice reading numbers (~170 words) | shipped with the MS sound card; not in our images |
| Sound Blaster demos (Dr. Sbaitso, Talking Parrot, SB demo VOC/MID) | speech | Creative TTS and demo clips | (c) Creative; not Microsoft (LICENSE FLAG); not in our images |
| Microsoft Mike / Mary (SAPI 4/5) | speech | alternative TTS voices; Mike/Mary come with Reader or SAPI 5 merge modules | free/Reader; not in our image; not in our images |
| L&H Michael / Michelle, TruVoice | speech | Lernout & Hauspie TTS for Office XP and MS Agent | free download; LICENSE FLAG L&H; not in our images |
| Microsoft Anna | speech | Vista/7 default voice | Bundled with Vista/7; not in our images |

Also worth knowing:

- **canyon.mid** is George Stone's "Trip Through the Grand Canyon" (Passport Designs, 1990). It shipped from the 3.0 MME through Windows 2000 and is the only MIDI file in our 3.11 image. **onestop.mid** is by David Yackley; flourish.mid and town.mid are attributed to Nathan Grigg (one source).
- **The XP setup music** (`title.wma`, in our image) is "Velkommen", credited to Stan LePard (VGMdb also lists Bill Brown). The XP tour music is not on our disk.
- **Hover!** (Windows 95 CD, `\FUNSTUFF\HOVER`) has WAV effects and MIDI music (.MUZ) by Stan LePard. Windows 3.1 and XP Minesweeper have sounds; 98 only a faint tick.

## Licensing and distribution

- **Already shipped by us (in our images):** everything marked xp or 311 above. It is ordinary Windows content, so it carries the same risk the user has already accepted.
- **Would have to be added:** every other entry. The ones worth adding first are the 3.1 CHORD/TADA for BASILISK 16, the Eno startup, the 3.0 MME set, the NT4/98/ME/2000 logon and logoff swells, and the best Plus! tonal sounds. Each would be a new file copied into an image we redistribute.
- **Unusual flags:**
  - **Roland GS (`gm.dls`, in our XP image).** It is (c) 1996 Roland and licensed to Microsoft for OS use. It is already on the disk we ship, but extracting or re-recording its samples as our own sources is a step beyond shipping Windows.
  - **3D Pinball** is (c) Cinematronics 1995, licensed to Microsoft. It is in our image.
  - **Licensed recordings:** XP sample-music WMAs (in our image), Vista/7 sample music, the David Byrne track and the Windows 95 FUNSTUFF videos. These are third-party music, not Windows sound design, so avoid them.
  - **Plus! 98 themes:** the comic themes (Cathy, Doonesbury, FoxTrot, Garfield, Peanuts) are licensed properties, and Doonesbury's WAVs are tagged with the "Kaboom! Factory" consumer SFX library. Corbis and PhotoDisc are stock-photo licensors. The Windows 98 theme exit is (c) Panther Modern LLC (Stan LePard).
  - **Plus! XP Aquarium** embeds library file names that look like Sound Ideas numbering (inferred).
  - **Speech:** the L&H TruVoice / Michael / Michelle voices are Lernout & Hauspie licensed and are not in our image. Microsoft Sam is in it. Creative's Sound Blaster demos and Dr. Sbaitso are Creative, not Microsoft.
  - **Windows Sound System ProofReader** is a recorded human voice. Microsoft Musical Instruments is co-owned with Dorling Kindersley.

## Sources

- Our images: `~/synth-build/machine-out/base.qcow2` (XP, made by packages/basilisk-synth/tools/make_machine.py), `site/basilisk-31-browser/w31.jsdos` (WfW 3.11; packages/basilisk-synth-311/tools/make_machine.py).
- KB Q177517, Windows 95 Media files: https://jeffpar.github.io/kbarchive/kb/177/Q177517
- KB Q83783, Windows 3.1 sound events: https://jeffpar.github.io/kbarchive/kb/083/Q83783 . KB Q137646 (Plus! floppy listing): https://jeffpar.github.io/kbarchive/kb/137/Q137646
- Windows 3.0 MME (IBM UCD): https://discmaster.textfiles.com/browse/13501/IBM_UCD_101.ISO/winmme/mmdata . Toastytech MME: http://toastytech.com/guis/win3mme.html
- Windows 3.1 (Tandy Sensation II): https://discmaster.textfiles.com/browse/4696/Tandy%20Sensation%20II%20System.iso/mwin
- WfW 3.11 disk 6: https://discmaster.textfiles.com/browse/43408/Applications/311WFW.ZIP/Disk06.img . WFWADD: https://discmaster.textfiles.com/browse/13162/gold.zip/gold/INFORMAT/WFWADD.ZIP
- NT 3.x sounds: https://techshelps.github.io/MSDN/DNWINNT/HTML/D1E/S837F.HTM . NT 4.0 LAYOUT.INF: https://discmaster.textfiles.com/browse/34667/winwpro96_4.zip/winwpro96_4/WINNT4/WKS
- Windows 95 retail / OSR2 installed Media: https://discmaster.textfiles.com/browse/34906/ and https://discmaster.textfiles.com/browse/34877/
- Windows 98 / 98 SE CABs: https://discmaster.textfiles.com/browse/38148/98CD05.iso/win98 , https://discmaster.textfiles.com/browse/38129/WIN98_SE.iso/win98 ; Windows ME: https://discmaster.textfiles.com/browse/39189/
- Windows 2000 Media: https://discmaster.textfiles.com/browse/34901/ ; XP Media: https://discmaster.textfiles.com/browse/43401/ ; XP Tablet 2005: https://discmaster.textfiles.com/browse/41760/TWILIGHT_090_DVD3.iso/APPS/0031/CD2/XPTPE25B.BIN/cmpnents
- Vista install.wim Media: https://discmaster.textfiles.com/browse/40745/Soft_Maximator_2007.iso/sources/install.wim/1/Windows/Media ; Windows 7: https://archive.org/download/windows-7-default-sound-schemes_202503 , https://archive.org/download/windows-7-sounds
- Windows 7 schemes (Microsoft blog): https://blogs.windows.com/windowsexperience/2011/01/10/your-pc-is-alivewith-the-sound-of-windows/
- Startup sound history: https://winhistory.de/more/winstart/winstart_en.htm ; Vista/Fripp: https://redmondmag.com/articles/2006/11/13/long-process-leads-to-short-vista-sound.aspx , https://istartedsomething.com/20070118/microsoft-startup-sound/ ; VGMdb Windows 95: https://vgmdb.net/release/23694 ; 20k.org: https://20k.org/episodes/tadaitswindows
- onestop.mid: https://devblogs.microsoft.com/oldnewthing/20130212-00/?p=5263 ; canyon.mid: https://kotaku.com/this-gloriously-cheesy-midi-file-was-windows-greatest-h-5949071 , https://forum.codeproject.com/post/516260
- Plus! 95: https://archive.org/details/microsoft-plus-95-and-plus-for-kids ; Plus! 98: https://archive.org/details/PLUS98_201905 ; Plus! for Kids: https://archive.org/details/mpfkdesktopthemes ; Plus! XP: https://archive.org/details/en_plus_retail_20010906 ; Plus! DME: https://archive.org/details/msplus-dme ; SuperPack: https://archive.org/details/plussuperpack ; https://en.wikipedia.org/wiki/Microsoft_Plus!
- 3D Pinball: https://github.com/k4zmu2a/SpaceCadetPinball , https://archive.org/details/3-d-pinball-space-cadet-from-windows-xp-32-bit
- Hover!: https://en.wikipedia.org/wiki/Hover! , https://tcrf.net/Hover!_(1995) ; Minesweeper: https://www.tcrf.net/Minesweeper_(Windows,_1990)/en
- XP setup music: https://tildes.net/~tech/vrb/title_wma_the_origins_of_windows_xps_welcome_music , https://vgmdb.net/release/23697 ; David Byrne: https://news.microsoft.com/source/2001/08/01/david-byrne-to-provide-promotional-music-for-windows-xp/
- Office assistants / sounds: https://techshelps.github.io/MSDN/KB/Source/office/q163027.htm , https://www.microsoft.com/en-us/download/details.aspx?id=7015
- GS synth: https://news.microsoft.com/1996/10/22/microsoft-licenses-sound-canvas-sounds-from-industry-leader-roland-corp/ , https://dtm.noyu.me/wiki/Microsoft_GS_Wavetable_Synth
- Speech: https://en.wikipedia.org/wiki/Microsoft_text-to-speech_voices , https://learn.microsoft.com/en-us/windows/win32/lwef/accessing-a-speech-engine-in-your-code
- Other software: https://github.com/microsoft/Microsoft-3D-Movie-Maker , https://en.wikipedia.org/wiki/Microsoft_Bob , https://hackaday.com/2025/08/14/rediscovering-microsofts-oddball-music-generator-from-the-1990s , https://en.wikipedia.org/wiki/Microsoft_Musical_Instruments , https://en.wikipedia.org/wiki/Encarta_MindMaze , https://dosdays.co.uk/topics/windows_sound_system.php
- BetaWiki (betawiki.net) was behind a Cloudflare challenge during this research and could not be read; nothing here is cited from it.

# songrender: multitrack song demos through the real Windows 3.11 machine

`songrender.py` renders a song (a Standard MIDI File plus a track table) headlessly. Each track is its own engine,
one `render311` run, that is one emulated Windows for Workgroups 3.11 with its 16 Sound Recorders, playing only that
track's notes. This is the same as a DAW with one SNDWAVE2000 instance per track. The stems are then mixed to stereo:

- volume and pan;
- a send to a shared echo and to a shared reverb;
- mute and solo;
- a master loudness gain and a look-ahead true-peak limiter.

Every note is played by Sound Recorder. The mixer only scales, delays and sums the recorders' own output; the echo
and the reverb are convolutions of the rendered stems.

```
songrender.py SONG.song [SONG.song ...] [--out-dir DIR] [--jobs 6] [--stems] [--no-wav] [--dry]
              [--render311 EXE] [--machine DIR] [--cache DIR]
songrender.py SONG.song --engine host --host BasiliskHost.exe --plugin SNDWAVE2000.vst3   (through the real plugin)
```

The command writes these files to `DIR`:

| File | Contents |
|---|---|
| `<song>.wav` | 48 kHz 24-bit stereo |
| `<song>.ogg` | Opus, 64 kbps |
| `<song>.mp3` | 128 kbps, 44.1 kHz |
| `<song>.json` | the song's metadata, every track's preset and DNA, levels, loudness and the files' SHA-256 |

Several songs in one call share one pool of engines. Never more than 6 run at once, at `nice -n 10`, because the PC
is shared.

Defaults: `render311` is `~/songs/build/render311`, the machine is `~/songs/machine` (a copy of a release's
`Contents/Resources/machine`), and the stem cache is `~/songs/cache`. The environment variables
`SONGRENDER_RENDER311`, `SONGRENDER_MACHINE` and `SONGRENDER_CACHE` override them.

## The song file (`.song`)

A plain text file: `key = value` lines, then sections. `#` starts a comment.

```
title    = The Leaning Cloister Galliard
pack     = courtyard-chapel            # the pack whose presets the tracks name
midi     = galliard-leaning-cloister.mid
kind     = original                    # original | world | chiptune
composer = ...
source   = ...                         # for a public-domain piece: what it is, where the score came from
licence  = ...
proof    = https://...                 # where the licence can be checked
tail     = 4                           # seconds rendered after the last MIDI event (default 4)

[master]
loudness = -16      # LUFS (BS.1770, gated) the mix is brought to
ceiling  = -1.0     # dBFS true peak (4x oversampled) the limiter holds
gain     = 0        # dB on top of the loudness gain
fadeout  = 1.5      # seconds of fade at the very end

[echo]              # one shared echo
time     = 3/16     # a note value in whole notes (3/16 = dotted eighth) at the MIDI's first tempo, or 375ms
feedback = 0.35
tone     = 3500     # Hz: each repeat is darker
pingpong = yes
level    = 0        # dB, the return
lowcut   = 180

[reverb]            # one shared reverb (a seeded, decaying noise impulse response: deterministic)
size     = 2.0      # seconds to -60 dB
predelay = 18       # ms
tone     = 5500
level    = -6
seed     = 3110

[tracks]
# name   source  preset                 mix
lead     ch1     "Slate Pick"           vol=-2 pan=8 echo=0.05 verb=0.3
bass     ch4     "Kinetic Harp"         vol=-5 tr=-12
kit      ch10    "kit-manager:Card Room" vol=-6
pad      ch2+ch3 'dna:chimesE+;R900'    vol=-10 mute
```

A track line has three columns, then any number of `key=value` settings:

1. **NAME**: the stem's name.
2. **SOURCE**: the MIDI events the track plays.
   - `chN` is MIDI channel N (1 to 16).
   - `trN` is MIDI track N (0 is the first).
   - Join several with `+`; `ch2+tr3` means both must match. `all` takes every event.
   - The events go to the engine on channel 1, with the file's tempo map.
3. **PRESET**: one of these.
   - A preset name in the song's pack, in quotes. `Category/Name` also works.
   - `pack-id:Name` names a preset in another pack.
   - `'dna:...'` gives a DNA directly.

   Presets resolve against the machine's own pack discs (`machine/packs/*/PRESETS.TSV`), which hold what the
   engine can play.

The settings:

| Setting | Meaning | Default |
|---|---|---|
| `vol=` | dB | 0 |
| `pan=` | -100 (left) to 100 (right), constant power | 0 |
| `echo=` | send to the echo, 0 to 1 | 0 |
| `verb=` | send to the reverb, 0 to 1 | 0 |
| `tr=` | transpose in semitones, applied to the MIDI notes | 0 |
| `tune=` | cents, sent as a pitch bend at the start, through the plugin's own bend range (the DNA's `B`, 2 by default): a sample a little sharp or flat is corrected by the recorders' playback rate | 0 |
| `vel=` | velocity scale | 1.0 |
| `hp=` / `lp=` | high- and low-pass on the stem, in Hz | off |
| `width=` | stereo width of the stem (0 is mono) | 1.0 |
| `mute` / `solo` | | |

## Determinism and the cache

Each stem is cached under `--cache` as 24-bit FLAC. That is render311's own WAV depth, so nothing is lost. The cache
key is a hash of render311, the machine (snapshot, settings, pack list), the DNA, the track's MIDI bytes, the tail and
the tempo. Changing the mix never re-renders; changing a track's notes re-renders only that track. The same inputs
give bit-identical stems, WAV, Opus and MP3 (ffmpeg runs with `-bitexact`, and the reverb's noise is seeded).

## Through the real plugin (`--engine host`)

`--engine host` renders each track through the SNDWAVE2000 VST3 in BasiliskHost (`tools/basilisk-host`), offline,
one track at a time. For each track it:

1. writes a raw VST3 component state holding the plugin's state text, with the track's DNA and every pack disc
   inserted;
2. runs `BasiliskHost --test PLUGIN --tests offline --midi TRACK.mid --load-state STATE`;
3. cuts the host's warmup and the plugin's reported latency off the output.

The mix is the same. `host_song.py` has the details; PROGRESS notes in the songs folder record the comparison with
render311.

## Arranging aids

- `audition.py` measures every preset of the pack discs: the pitch heard at C3, C4 and C5 against the note asked,
  the level, the attack, and how much is left after 300 ms and 1 s; kits get each pad's level. The results go to
  `~/songs/audition/<pack>.json`. A song uses `tune=` from these numbers.
- `compose.py` is a small Python toolkit for writing the MIDI: a melody notation, chord symbols with voice leading,
  bass patterns, drum grids, and seeded humanising. The songs in `packages/basilisk-synth/library/songs/<pack>/`
  are each one script that writes its `.mid` and `.song`.

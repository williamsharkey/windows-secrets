sndrec.html demos
=================

The preset demos and videos on https://williamsharkey.com/sndrec.html. All the sound is the plugins' own output:
no demo audio is made any other way. The audio and video files (about 22 MB) are not in git; this is how to make them
again. Work in a Linux folder (here `W=~/sndrec-demo`), not on C:.

| File | What it does |
|---|---|
| `phrases.py` | One deterministic MIDI phrase per factory preset, chosen by the preset's job (pads: slow chords, basses: a bassline, plucks: an arpeggio, bells: a melody...). Writes `mid/*.mid`, `jobs.json` (the batch renderers' format) and `presets.json`. |
| `macro_bh.py` | The macro presets: renders their phrase through the real VST3 in BasiliskHost (`--test`, offline) with Macro 1 automated, replacing the static render. |
| `encode.py` | Checks every render (silent, over full scale, length, every note onset heard, renderer's late notes, very quiet), levels it to -16 LUFS (gain, plus a -1 dBFS limiter only when the gain would clip), fades the last 0.4 s, encodes MP3 96 kbps (mono when L = R), and writes `manifest.json` with a 64-bar waveform. |
| `review-<edition>.json` | Listening notes: explanations shown on the page, and automatic flags that listening showed to be false alarms. |
| `site_data.py` | Merges the editions' manifests into `site/sndrec/presets.json`, which the page reads. |
| `demo311.cpp` | The video capture for BASILISK 16: `render311` with the screen on. Same engine, snapshot and shared core; it plays the plugin's part (hello and assembly, `dna`, stamped notes, `show` for the keys, `cc 1` for the mod wheel, a preset change that keeps the old sound until `built`) and grabs the emulated screen every 1/30 s of DAC time, so picture and sound stay in step. |
| `videos/*.txt` | The four video scripts (`MID` stands for the folder of `phrases.py`'s MIDI files). |
| `encode_videos.sh` | Lossless capture -> H.264 MP4 (4:2:0, CRF 8) and VP9 WebM (4:4:4, crisp pixels), audio levelled to -16 LUFS. |

BASILISK 16 (1.2.0)
-------------------

```
R=packages/basilisk-synth-311 T=basilisk-synth-311-v1.2.0
gh release download $T -p BASILISK-16-windows-x64.zip -D $W/rel311      # unzip into $W/rel311/x
M=$W/rel311/x/Basilisk16.vst3/Contents/Resources/machine                  # the release's machine
# render311 and the Linux DOSBox Pure core: from tools/build.sh of the same tag (render311 is bit-identical on every OS)
git show $T:$R/plugin/presets_gen.h > $W/presets311.h
python3 tools/sndrec-demo/phrases.py $W/presets311.h $W/b16
python3 $W/rel311/x/batch/batch_render311.py $W/b16/jobs.json --machine $M --core CORE.so --render311 render311 --parallel 6 --out-dir $W/b16
python3 tools/sndrec-demo/macro_bh.py $W/b16 /mnt/c/SOMEWHERE              # BasiliskHost.exe + Basilisk16.vst3 copied there
python3 tools/sndrec-demo/encode.py $W/b16 $W/site/sndrec/audio/b16 b16 --review tools/sndrec-demo/review-b16.json
# recipes: build recipe_cli.cpp with the converter from branch design/preset-engine-2 (design/v3/recipe.{h,cpp}, dna3, engine3)
g++ -std=c++17 -O2 -Ipackages/basilisk-synth/core -I$V3 tools/sndrec-demo/recipe_cli.cpp $V3/{recipe,dna3,engine3}.cpp packages/basilisk-synth/core/dna.cpp -o recipe_cli
python3 tools/sndrec-demo/site_data.py site/sndrec/presets.json b16=$W/b16@$M --recipe-cli ./recipe_cli   # @machine: drive.zip, library.zip for the badges
```

Videos: build `demo311` against the tag's sources (the includes are relative to a checkout root):

```
g++ -std=c++17 -O2 -o demo311 tools/sndrec-demo/demo311.cpp packages/basilisk-synth/core/{dna,voices}.cpp engine.o -ldl -lpthread
#   engine.o: gcc -O2 -c packages/basilisk-synth-311/engine/engine.c
for s in assembly play change macro; do
  sed "s#MID#$W/b16/mid#" tools/sndrec-demo/videos/$s.txt > $s.txt
  demo311 --machine $M --core CORE.so --script $s.txt --video $s.mkv --audio $s.wav
done
OUT=$W/site/sndrec/video tools/sndrec-demo/encode_videos.sh b16 assembly play change macro
```

The posters (`site/sndrec/video/*.png`, in git) are frame 400 of assembly and frame 60 of the others.

Deploy: copy `site/sndrec.html` and `site/sndrec/` to the web host's `html/live/`, then compare md5 over HTTPS.

Findings from the BASILISK 16 1.2.0 renders
-------------------------------------------
- **Chord Thump** is silent on 3.11: `chord<<]` deletes the whole sound (the position is at the start after `<<`).
- **Critical Bass**, **Hardware Sub**: XP names fall back to DING; slowed by `<<`, its lead-in is about 0.4 s of
  silence, so short notes never sound.
- **Bowl Swell** is very quiet (-48 LUFS before levelling).
- **Echo Count**, **Macro Echoes**: when Macro 1 changes the echo count (N), Windows rebuilds, and chords that land
  during the rebuild are dropped even offline (2 of 8 chords in each demo).
- Vibe Wide, Cello Breath, Organ Ring, Echo Count and Kit peak above 0 dBFS (+0.4 to +1.5; float output).

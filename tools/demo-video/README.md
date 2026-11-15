SNDWAVE1993 tour video
======================

"Computing at Your Pace: SNDWAVE1993": a deadpan home-learning-tape tour of the plugin, hosted by Clement Ashby, the
invented host of an invented public-access show, drawn from code. Two cuts come from the same edit list: `spot` (about 2:20, for X) and `long`
(about 3:00, for the home page). The media is not in git; this folder makes it again.

| File | What it does |
|---|---|
| `shoot.py` | The footage. Each scene is an offline render of the real plugin (VST3) in BasiliskHost (`--tests editor --editor-offline`: paced to the wall clock, so the plugin's audio has no dropouts whatever the PC's load, frames stamped with their audio time), with the editor open, driven by window messages. The assembly and the Program Manager tour come from earlier real-time captures (picture only: the plugin assembles before an offline render's audio starts). The `rec` step records the editor's frames to a `.bhrc` file (the harness's own capture, `tools/basilisk-host`), and the plugin's output goes to `editor.wav`. MIDI comes from `phrases.py`. Scenes: `cold` (assembly, Ding Piano), `proof` (Program Manager, Accessories, Sound Recorder, About), `packs1`/`packs2` (Library tab presets), `vibe` (wow, flutter), `kits` (pad calculator), `mines` (Minesweeper sequencer), `rec` (the Recorder), `song` (Song tab: open, render, play), `citypop` (CITYPOP1993 on the desktop, from a 1.5 test build). |
| `bhrc.py` | Reads a `.bhrc` capture: the frame on screen at any audio time. |
| `peek.py` | Contact sheet and loudness of a capture. |
| `script.py`, `tts.py`, `tiktok_tts.py` | The narration, read by Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0), run locally. Host: am_michael at 0.95; announcer: am_onyx. At the owner's request the announcer's opening and closing lines use TikTok's text-to-speech voice (en_us_001), fetched once through a public no-login proxy and cached (`tiktok_tts.py`). |
| `presenter.py` | Clement Ashby, drawn in Pillow (an original character): visemes from the narration, blinks, eyebrows, gestures (point, diskette, wave, thumbs-up); his set has a ficus and the WORLD'S OKAYEST USER mug. `python3 presenter.py sheet OUT.png`. |
| `dropouts.py` | Checks a soundtrack for buffer underruns (5-80 ms digital-silence cuts inside sustained sound) and clicks away from note onsets (`--notes`: compose.py writes the edit's note times). Target 0. |
| `edit.py` | The edit list: shots, narration placement, the host's position, overlays, music. |
| `compose.py` | Renders the edit: frames (Windows screen at whole-number scales, nearest neighbour), the host box with its motion trail (16 copies kept, the 17th cleared), wipes (star, iris, page, blinds), tinted bars, captions; the mix (ducked under the voice, -14 LUFS, -1 dBTP); the `.srt`. |
| `stage.sh` | Copies the inputs to the machine that renders (`~/sw2000-video`). |
| `webcap.js` | Captures the web edition (williamsharkey.com/sndwave1993/play/) in headless Chromium (playwright-core), recorded to video. |
| `scene1993.py`, `keyboard101.py`, `kbd_texture.py`, `dump_frames.py`, `post1993.py` | The establishing shot: an early-90s desk built in Blender from code (generic shapes, no badges; a 101-key keyboard with lettered caps from `keyboard101.py`/`kbd_texture.py`), the camera pushing past the keyboard into the CRT, whose convex glass sits flush in the bezel and shows the real capture (`dump_frames.py`); `--night --reverse` for the sign-off. `post1993.py` gives it the period look: one 128-colour palette per sequence, 4x4 ordered dither, 3x nearest-neighbour upscale. |
| `pixelize.py` | Pixel art from a picture with Pillow/numpy: box downscale, VGA16 / Windows 256 / brand / adaptive palettes, Floyd-Steinberg or Bayer dither, outline, whole-number upscale. |
| `pixel_ai.py` | The Grok stills as pixel art with PixelOE (github.com/KohakuBlueleaf/PixelOE, Apache-2.0), 24 colours. Compared on the host still with `pixelize.py` and pyxelate (github.com/sedthh/pyxelate, MIT): PixelOE's contrast-aware downscale kept the face cleanest. |

```
# Windows side (WSL): BasiliskHost.exe and the plugin bundle in SW (default /mnt/c/Users/willi/video-sw93)
python3 tools/demo-video/shoot.py cold proof packs1 packs2 vibe kits mines rec song citypop
~/video/kvenv/bin/python tools/demo-video/tts.py ~/video/work/tts          # venv: kokoro, soundfile, torch (CPU)
tools/demo-video/stage.sh primary-mac cold proof packs1 packs2 vibe kits mines rec song citypop
# the establishing shots (Blender 5.x)
python3 tools/dump_frames.py cap/cold/cap.bhrc blender/scr_day 0 7.5; python3 tools/dump_frames.py cap/citypop/cap.bhrc blender/scr_night 40 7.5
Blender -b -P tools/scene1993.py -- --screen blender/scr_day --out blender/day --frames 210
Blender -b -P tools/scene1993.py -- --screen blender/scr_night --out blender/night --frames 210 --night --reverse
python3 tools/post1993.py blender/day blender/day_px --colors 128; python3 tools/post1993.py blender/night blender/night_px --colors 128
# the web edition: node tools/webcap.js web; ffmpeg -ss 38 -i web/*.webm -vf fps=30 web/frames/%05d.png  (WEB0=90)
# the renderer (any machine with python3 + numpy, pillow, soundfile, and ffmpeg)
DEMO_ROOT=~/sw2000-video python3 tools/compose.py ~/sw2000-video out/sndwave1993-tour.mp4 --cut spot --jobs 10
DEMO_ROOT=~/sw2000-video python3 tools/compose.py ~/sw2000-video out/sndwave1993-tour-long.mp4 --cut long --jobs 10
#   --frames 1,5,9 --sheet out/sheet.png    a contact sheet instead of the video
#   HOST_STYLE=ai                           the alternative take with the Grok Imagine stills (grok/; see below)
```

Credits. All plugin footage is the real plugin in BasiliskHost (CITYPOP1993.EXE: a 1.5 test build, labelled so; its sound and the Song tab's playback are the same pieces' offline renders, CITYPOP1993 track 1 and Aquarium (Level 3), which match the players sample for sample), and
the web edition in Chromium. The desk is a Blender scene made by `scene1993.py`. Music: SNDWAVE1993 pack demo songs
(Atrium Level B2, Aquarium (Level 3), Fax Machine Fanfare) and CITYPOP1993 tracks 1 and 12, all made on the plugin. Voices: Kokoro-82M; the two announcer lines that open and close the video: TikTok's TTS voice (en_us_001). Fonts: DejaVu. The host, cards and
transitions are drawn by these scripts. In the `HOST_STYLE=ai` take only, the host stills (grok_clement/) and the backdrop (grok/) were made
with Grok Imagine (image_gen / image_edit) from text prompts describing an invented character, then turned into pixel art
(`pixel_ai.py`); the prompts are in each folder's manifest.txt.

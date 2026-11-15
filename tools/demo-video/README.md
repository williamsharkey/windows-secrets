SNDWAVE1993 tour video
======================

"Getting Started with SNDWAVE1993": a deadpan home-learning-tape tour of the plugin, hosted by Harlan Pettibone, an
invented retiree drawn from code. Two cuts come from the same edit list: `spot` (about 2:20, for X) and `long`
(about 3:00, for the home page). The media is not in git; this folder makes it again.

| File | What it does |
|---|---|
| `shoot.py` | The footage. Each scene is a real-time render of the real plugin (VST3) in BasiliskHost (`--tests editor`), with the editor open, driven by window messages. The `rec` step records the editor's frames to a `.bhrc` file (the harness's own capture, `tools/basilisk-host`), and the plugin's output goes to `editor.wav`. MIDI comes from `phrases.py`. Scenes: `cold` (assembly, Ding Piano), `proof` (Program Manager, Accessories, Sound Recorder, About), `packs1`/`packs2` (Library tab presets), `vibe` (wow, flutter), `kits` (pad calculator), `mines` (Minesweeper sequencer), `rec` (the Recorder), `song` (Song tab: open, render, play), `citypop` (CITYPOP1993 on the desktop, from a 1.5 test build). |
| `bhrc.py` | Reads a `.bhrc` capture: the frame on screen at any audio time. |
| `peek.py` | Contact sheet and loudness of a capture. |
| `script.py`, `tts.py` | The narration, read by Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0), run locally. Host: am_michael + am_santa blended; announcer: am_onyx. |
| `presenter.py` | Harlan Pettibone, drawn in Pillow: visemes from the narration, blinks, eyebrows, gestures (point, diskette, wave, thumbs-up). `python3 presenter.py sheet OUT.png`. |
| `edit.py` | The edit list: shots, narration placement, the host's position, overlays, music. |
| `compose.py` | Renders the edit: frames (Windows screen at whole-number scales, nearest neighbour), the host box with its motion trail (16 copies kept, the 17th cleared), wipes (star, iris, page, blinds), tinted bars, captions; the mix (ducked under the voice, -14 LUFS, -1 dBTP); the `.srt`. |
| `stage.sh` | Copies the inputs to the machine that renders (`~/sw2000-video`). |
| `webcap.js` | Captures the web edition in headless Chromium (playwright-core). |

```
# Windows side (WSL): BasiliskHost.exe and the plugin bundle in SW (default /mnt/c/Users/willi/video-sw93)
python3 tools/demo-video/shoot.py cold proof packs1 packs2 vibe kits mines rec song citypop
~/video/kvenv/bin/python tools/demo-video/tts.py ~/video/work/tts          # venv: kokoro, soundfile, torch (CPU)
tools/demo-video/stage.sh primary-mac cold proof packs1 packs2 vibe kits mines rec song citypop
# the renderer (any machine with python3 + numpy, pillow, soundfile, and ffmpeg)
DEMO_ROOT=~/sw2000-video python3 tools/compose.py ~/sw2000-video out/sndwave1993-tour.mp4 --cut spot --jobs 10
DEMO_ROOT=~/sw2000-video python3 tools/compose.py ~/sw2000-video out/sndwave1993-tour-long.mp4 --cut long --jobs 10
#   --frames 1,5,9 --sheet out/sheet.png    a contact sheet instead of the video
#   HOST_STYLE=ai                           the alternative take with the Grok Imagine stills (grok/; see below)
```

Credits. All footage is the real plugin in BasiliskHost. Music: SNDWAVE pack demo songs (Atrium Level B2, Aquarium
(Level 3)) and CITYPOP1993 track 12, all made on the plugin. Voices: Kokoro-82M. Fonts: DejaVu. The host, cards and
transitions are drawn by these scripts. In the `HOST_STYLE=ai` take only, the host stills and the backdrop were made
with Grok Imagine (image_gen / image_edit) from text prompts describing an invented character; the prompts are in
`grok/manifest.txt` beside the files.

# BASILISK 16 in the browser ("Try it online", sndrec.html)

The plugin's own engine, compiled to WebAssembly with Emscripten:
- DOSBox Pure with the BSYN card, patched exactly as for the plugin (`packages/basilisk-synth-311/dosbox-pure`);
- the plugin's engine thread, unchanged (`engine/engine.c`, wrapped by `web_engine.c` for static linking);
- the shared core (DNA parser, voice allocator) and the plugin's host logic (`host.cpp`);
- the same Windows for Workgroups 3.11 guest (`SYNTH.EXE`, `SYNHOOK.DLL`, `BSYNTH.DRV`).

Every sound comes from the sixteen Sound Recorders through the emulated card, as in the plugin.

## How it runs

| Part | Where |
|---|---|
| Windows 3.11 (engine thread + DOSBox thread) | pthreads (Web Workers sharing memory) |
| Host tick, MIDI, keys, screen | the worker that loads the module (`worker-main.js`, appended to `b16-worker.js`) |
| Audio | an AudioWorklet (`audio-worklet.js`) reading the card's DAC ring straight out of the shared memory; its play position paces the emulator, as a DAW's audio thread does |
| Screen | ImageBitmaps from the worker, drawn by the page's `sndrec/pxfit.js`: exactly k×k device pixels per Windows pixel, or an exact 1/n reduction (with a note) where k = 1 does not fit |
| Page | `b16-try.js` + the block in `section.html`: nothing is fetched until the button is pressed; watchdog, Stop, Web MIDI, presets |

- **Shared memory.** It needs a cross-origin isolated page: sndrec.html is served with COOP/COEP (`site/.htaccess`),
  and `sndrec/try/.htaccess` marks the files.
- **The snapshot** (`w31web.state`) is taken by the web engine itself, under node (`make_snapshot.cjs`). It is taken
  after the assembly and the default DNA are done, so the browser resumes straight to a ready synth.
- **C: (`drive.zip`)** holds only what Windows uses. That is the files in `drive-keep.txt`, recorded with a traced
  build while booting, assembling, building every factory preset and using the controls, plus every settings, driver,
  font and sound file (`make_drive.py`).
- **The library disc (`library.zip`)** is never downloaded whole. Windows' reads become 256 KB HTTP range requests
  (`fs.cpp`, `lazyfile.js`).
- **Screen scaling.** The screen is a pxfit picture, sized inline before the first paint. The poster is a lossless
  PNG.
- **Dragging.** The engine moves Windows' pointer through the guest program (SetCursorPos). That program does not run
  inside Windows' own modal loops, such as dragging a scroll-bar thumb. So while the left button is held, the motion
  also goes to the emulated mouse as relative motion (`web_engine.c`, `host.cpp`). WIN.INI gets `MouseSpeed=0`, so
  that motion is 1:1.

## Build and deploy

```
XPSOUNDS=<plugin machine/drive.zip or xpsounds311.py folder> OW=<open-watcom> NODE=<node 22> \
  tools/basilisk16-web/build.sh ~/b16web [LIBRARY_DIR]      # -> ~/b16web/site
python3 tools/basilisk16-web/insert_section.py site/sndrec.html <version from site/b16-try.js>
```

- **Not in git:** `b16.wasm`, `w31web.state`, `drive.zip` and `library.zip` are build outputs. They are large, and
  the drive and the library hold Microsoft's and the library's audio. `build.sh` remakes them.
- **Copy to the server:** copy `~/b16web/site/*` and `.htaccess` to `html/live/sndrec/try/`, and `site/.htaccess` to
  `html/live/`.
- **Tests** (scratch, not in git): a node run of every preset through the recorders, and Playwright end-to-end
  checks: nothing loads before the click, no layout shift, pitch, keys, watchdog, phone width, and k×k pixels at
  DPR 1, 2 and 3.

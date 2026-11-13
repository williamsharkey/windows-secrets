# BASILISK 3.11 in the browser, on DOSBox Pure

https://williamsharkey.com/basilisk-31-browser.html

Since 2026-11-13 the in-browser BASILISK 3.11 runs on the DOSBox Pure WebAssembly engine of BASILISK 16's "Try it
online" (`tools/basilisk16-web`) instead of js-dos/DOSBox-X, which sometimes trapped on start ("unreachable").
The page resumes a snapshot taken just after the suite (`puppetry/w31suite`) assembled, so Windows is ready about
1-3 s after Start.

| Part | File |
|---|---|
| Engine thread | `web_engine.c`: a copy of the web lane's wrapper around `packages/basilisk-synth-311/engine/engine.c` (unchanged) |
| Host (this page's link) | `host31.cpp`: BASILISK.EXE's lines out of the BSYN card's reports, the page's lines in as events; pointer, buttons, keys, frames |
| Worker | `worker31.js` (appended to the Emscripten output): fetches the engine, the snapshot and C:, unpacks C: into WasmFS, resumes, draws, carries lines |
| C: | `make_drive31.py`: the last js-dos bundle's tree (git `5b29743:site/basilisk-31-browser/w31.jsdos`) without the file mailbox, with BASILISK.EXE built and started by WIN.INI |
| Snapshot | `make_snapshot31.cjs` (node): boot, assemble, freeze 3 emulated seconds after `R assembled`, then write C: again as Windows left it |
| Page | `site/basilisk-31-browser.html` (pxfit screen, watchdog, Start), `stage31.py` puts the files in `site/basilisk-31-browser/web/` |

The link is the BSYN card's packet ports (0x2C0-0x2C4), the same ones BASILISK 16's guest uses: `BASILISK.C` picks
it when the card answers its magic (else COM2 for the server version, or the js-dos file mailbox). Pointer moves
arrive as the engine's 0x0600 packets and BASILISK.EXE calls SetCursorPos; clicks and keys are the emulated mouse
and keyboard. The sliders borrowed from Control Panel report a real click to its hidden dialog, so BASILISK.EXE
drives them itself from the button state on the Settings card.

Build: `build31.sh WORKDIR` (emsdk, node 22+, Pillow; `libdbp.a` from `tools/basilisk16-web/core.mk`;
Open Watcom via `OW=` or on sharkey-server). The outputs (`b31.wasm`, `b31-worker.js`, `w31web.state`,
`drive.bin.gz`, `poster.png`, and `.htaccess` from `htaccess`) are not in git, as in the web lane: copy
`site/basilisk-31-browser/web/` to `html/live/basilisk-31-browser/web/`. `site/.htaccess` serves the page with
COOP/COEP (SharedArrayBuffer).

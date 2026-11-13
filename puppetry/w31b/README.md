# BASILISK 3.11, in your browser

> Since 2026-11-12 the client is the five-card suite in `puppetry/w31suite` (shared with the server version):
> `BASILISK.C` + `PARTS.C` + `B3BOOT.C` there; this directory keeps the server (`server.py`, now with
> `todo_write`, permission prompts, settings, `/compact`, CLAUDE.MD and usage messages), the bundle builder and the
> notes below. `link.h` and `basilisk.c`/`b3boot.c` here are the earlier single-window client.

https://williamsharkey.com/basilisk-31-browser.html

Windows for Workgroups 3.11 runs inside the visitor's browser (js-dos 8: DOSBox-X compiled to WebAssembly,
self-hosted under `site/basilisk-31-browser/`). On load it builds BASILISK.EXE the way the server version does
(`puppetry/w31`): B3BOOT pours `BASILISK.C` into Notepad, saves it, compiles it with Open Watcom in a DOS window,
and starts it, all inside the page, about 20 s after "Start Windows". Only the conversation with Claude crosses
the network.

## Parts

| Part | Taken from | Role |
|---|---|---|
| Transcript, scrollback | Notepad's edit (Fixedsys) | Claude's words, tool calls and their output |
| Input bar | Notepad's own Find dialog, made a child strip | Find What = your words, Find Next = Send, Cancel = Stop |
| Clock | CLOCK.EXE, analog | the face in the corner |
| Status | a Cardfile card | model, tokens, cost, what it's doing |
| Bill | Calculator's display | the session's cost |

(The server version uses Terminal as the transcript, fed over COM1. js-dos's DOSBox-X has serial ports but no way
for the page to feed one - its nullmodem needs a "modem support" build - so here the transcript is Notepad.)

## The cable: two files on C:

`link.h`: Windows appends messages to `C:\B3\TOJS.TXT`; the page rewrites `C:\B3\TOWIN.TXT` with everything it
has sent and Windows reads from where it stopped. The page reaches DOSBox-X's files directly through Emscripten's
FS (`ci.transport.module.FS`, synchronous; js-dos's async `fsReadFile` hangs on repeated reads). Polled every 30-40 ms
on both sides. `32BitFileAccess=off` in SYSTEM.INI so Windows never serves the mailbox from a cache.

Messages page -> Windows: `G` build (B3BOOT), `A` append text, `B n` take back n chars, `K` clear, `V` scroll,
`Z` submit the Find box, `T` set it (history), `P` paste, `Y` busy, `X` Esc, `F` focus, `S` status card,
`C` bill, `R/G/W id ...` run / read / write. Windows -> page: `H`, `S`, `D`, `E` (build), `R assembled`,
`U text` (what you typed), `O id status text` (tool results).

## Keys

Typing is local: each printable key becomes one press on the emulated US keyboard (`ci.sendKeyEvent`, shift taken
from the character, so any layout works); Enter/Esc/PgUp/PgDn/Up/Down are handled by the page and sent as link
messages. Measured in headless Chromium, keydown to changed pixels in the Find box: ~25 ms.

## Server

`server.py` on sharkey-server (127.0.0.1:8785, Caddy `live.williamsharkey.com/w31b/*` via the
`basilisk-origin.internal` site): holds each visitor's conversation, runs the claude-haiku-5-5 tool loop (effort
low, streaming, eager_input_streaming, validated inputs, prompt caching) and sends tool calls to the page. No
emulator, so idle cost is nil. Own ledger `/root/w31b/data/spend.json`, $10/month cap, $1 per IP per day,
60 turns per IP per hour, 4 sockets per IP. Key from `/root/stage/.env`, never printed. Unit: `systemd/`.

## Building the bundle

The C: tree (WfW 3.11 from `/root/w31/golden`, trimmed: no swap file, Mail/Schedule+/fax/tutorial/Lotus files;
Open Watcom trimmed to wcl/wcc/wlink + 16-bit DOS and Windows libraries; `B3\BASILISK.SRC` = `basilisk.c` with
CRLF, `B3\LINK.H`, `B3\B3BOOT.EXE` built from `b3boot.c` with host Open Watcom, empty `B3\TOWIN.TXT`) is kept on
sharkey at `/root/w31b/c`. `python3 mkbundle.py <dir containing c/ and www/>` writes the js-dos bundle
(`w31.jsdos`, ~11 MB, zip with directory entries and `.jsdos/dosbox.conf`).

## What didn't work (for the record)

v86 with FreeDOS: WfW 3.11's 386-enhanced mode refuses FreeDOS ("ERROR: Unsupported MS-DOS version" from
WIN386.EXE's DOS manager) even with `VERSION=` and a resident shim answering INT 21h 30h/3306h as IBM DOS 6.22 or
3.31; it depends on MS-DOS internals. No MS-DOS media was downloaded, so DOSBox-X (whose built-in DOS WfW accepts)
in js-dos it is.

# BASILISK III

A working Claude Code client assembled from Windows XP's own parts, driven from
https://williamsharkey.com/basilisk-term.html (server: `live.williamsharkey.com/term/*`).

## The parts (every one is still drawn by the program that made it)

| Part | Taken from | Role |
|---|---|---|
| Transcript, scrollback | Notepad's edit control (Lucida Console 10) | everything Claude and you say; tool calls and folded output |
| Input bar | Notepad's own Find dialog, made a child strip along the bottom | Find what = the prompt, Find Next = Send, Cancel = Stop |
| Clock, calendar | the Date and Time page from `timedate.cpl`, whole, as the sidebar | the analog clock and the month |
| Meter | Calculator's display | what the session has cost |

`basilisk.c` finds and assembles them (SetParent, styles, our own word wrap so wrapped lines keep their
indent), runs the four tools inside XP (`run` via `cmd /c` with captured output, `read_file`,
`write_file`, `edit_file`), and talks to the host over HTTP on 10.0.2.2:8765 (the VM's only network
path). A low-level keyboard hook gives Enter / Esc / PgUp / PgDn / history their meanings.

## A session

1. Visitor presses Start (`/ws`). The server restores snapshot `term-desk` (`loadvm`, 0.4 s).
2. The snapshot holds `puppet.exe b3wait` waiting for Ctrl+Alt+Shift+F12. The server presses it through
   QMP: no network involved, so nothing stranded by the restore delays it.
3. The puppet double-clicks Notepad on the desktop, drops in the 48 KB source in about 3.5 s, saves
   `basilisk.c` to the desktop, opens Command Prompt from its icon, compiles with tcc
   (`C:\tcc\tcc.exe basilisk.c -luser32 -lgdi32 -Wl,-subsystem=windows`) and starts it. About 24 s.
4. The client assembles itself, calls `/b3/hello` (which also hands it the UTC time; a restored
   snapshot wakes at the hour it was saved), and the visitor drives: keys go page -> `/ws` -> QMP
   `input-send-event` (second QMP socket, held open) -> XP's keyboard -> the Find box.
5. The screen goes back through `/vnc`: QEMU's VNC, proxied VIEW-ONLY (the proxy drops every client
   KeyEvent/PointerEvent/ClientCutText and rewrites SetEncodings to lossless ones). noVNC is self-hosted
   under `site/basilisk-term/novnc/`.

Measured from a browser over the internet (headless Chromium, keydown to changed canvas pixels in the
input box): median 62 ms, p90 180-195 ms (the tail is QEMU's VNC refresh backing off on a quiet screen).

## Model and money

Claude Haiku 5.5 by default (`/model sonnet` switches), effort low, streamed, tools with
`eager_input_streaming` and validated inputs, sequential tool execution (a compile must not race the
write before it), automatic prompt caching. Own ledger in `/root/term/data/spend.json`: $25/month cap,
$0.60 per session, $1.50 per IP per day. One driver at a time: ten minutes when someone waits,
otherwise until 4 idle minutes; 45 s grace for a reload.

## Files

- `basilisk.c` the client (tcc-compatible; also compiles with mingw for checking)
- `server.py` host side (aiohttp; guest 127.0.0.1:8771, public 127.0.0.1:8781)
- `../scene_b3.h` the build performance (in puppet.exe)
- `agent-b3.c` the guest agent with a 2.5 s socket timeout (maintenance only)
- `ops/term-vm.sh` QEMU command line; `ops/resnap.sh` refresh `C:\p\basilisk3.c` inside the snapshot;
  `ops/prep.vbs` desktop shortcuts; `ops/latency-probe.py` the measurement above
- `systemd/` term.target, term-vm.service, term-server.service (on catenary-core)

Lessons that cost time, kept here: QMP serves one client per socket; a themed property page moved
while visible leaves stale copies of its controls (lay it out hidden, then show once); the XP clock
draws its hands with XOR, so never force-repaint it; a tool thread must PostMessage (not Send) to the
GUI thread, or its message is handled in the middle of the GUI thread's own cross-process calls; keys
typed after `start basilisk.exe` land in whatever has focus (Date and Time's OK button, once).

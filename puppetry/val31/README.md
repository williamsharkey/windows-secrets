# VALENTINE 3.11

A visitor types a valentine on williamsharkey.com/valentine-31.html. Windows for Workgroups 3.11 (DOSBox-X,
headless on Xvfb :41, catenary-core) types it onto a real Cardfile card inside a heart of Solitaire's hearts
(drawn by CARDS.DLL), next to a real Clock, and the host photographs the screen.

- `val.c` - VAL.EXE, the 16-bit composer. Host build: Open Watcom v2 at /root/val31/ow,
  `wcl -q -bt=windows -l=windows -ml val.c`; copied to `/root/snap/dosbox-x/common/val31/run/VAL/VAL.EXE`
  (DOSBox-X's autoexec runs `WIN.COM C:\VAL\VAL.EXE`).
- `server.py` - host side: COM1 null-modem line on 127.0.0.1:8774 (DOSBox-X dials it once at start; a
  watchdog restarts Windows if the line stays silent), public 127.0.0.1:8784 (`POST /make`, `GET /job/<id>`,
  `GET /img/<id>.png`, `GET /state`). Job queue, per-IP limits (6/hour, 20/day), cp1252 checks, a short
  kind-words blocklist, private results kept 24 h.
- `dbx.sh` - start/stop/restart/shot (uses systemd when installed). `rt.sh` - build + one-shot test.
- `systemd/` - val31.target = val31-x (Xvfb :41) + val31-server + val31-dosbox.
- Public URL (needs the Caddy route): https://live.williamsharkey.com/val31/ -> 127.0.0.1:8784 (handle_path).

Wire protocol (cp1252, CRLF): host `JOB id`, `T:to`, `M:line\x01line...`, `F:`, `S:0|1|2`, `END`;
guest `HELLO` at start, `READY id` once everything has repainted, `DBG ...` diagnostics.

Lessons (all found in screenshots): a Win16 message queue holds 8 messages, so characters are typed with
SendMessage, not PostMessage; Cardfile ignores WM_SETTEXT on its card, so the card is typed; focus is
dropped (SetFocus(NULL)) so no caret is photographed, and WM_NCACTIVATE keeps Cardfile's caption active;
cards more than half behind Cardfile are not dealt, so no slivers show; 16-bit int math overflowed the
gradient; the Index dialog clips names by pixel width, so the host measures names first.

# XP VALENTINE

A visitor writes a valentine on `site/valentine-xp.html`; a real Windows XP VM assembles it from
XP's own parts and the server sends back the picture.

- **valentine.c** (`valentine.exe <jobfile>`, built with mingw: `i686-w64-mingw32-gcc -O2 -mwindows -s -o valentine.exe valentine.c -lgdi32 -luser32 -ladvapi32`).
  Rose desktop, taskbar and icons hidden. Calculator (Scientific) is opened out of sight; its push keys are lifted out with
  `SetParent` and stood on a heart curve in mirror pairs (pairs that would touch another key, the letter or the colour box
  are left out; the pair just above the tip stands shoulder to shoulder). Notepad holds the letter (Times New Roman italic,
  16/14/13 pt by length, word wrap, scrollbars removed, height fitted to the text, caret dropped with `WM_KILLFOCUS`).
  When the letter leaves room, Paint's colour box joins it with red picked. Every part is placed while hidden, shown at
  once, then the screen is repainted and left 1.2 s to settle - no part moves on screen, so nothing smears.
- **server.py** (aiohttp; venv /root/valxp/venv with aiohttp + pillow). Guest side 127.0.0.1:8773 (the VM's
  10.0.2.2:8765: agent.exe `/next` `/out`, files from www/). Public side 127.0.0.1:8783: `POST /make {to,from,msg}`,
  `GET /job/<id>`, `GET /img/<id>.png`, `GET /state`. One job at a time: `loadvm val-ready`, agent fetches job.txt,
  runs valentine.exe, QMP `screendump`, crop (80,64)-(944,768) to PNG, then QMP `stop`: between jobs the VM is
  paused and costs ~0 CPU (re-paused every 2 min if it ever comes back running). ~8 s per valentine on an idle host,
  ~16 s on a busy one. Runs on sharkey-server (/root/valxp).
  Text: NFC, control/bidi chars stripped, only what XP's Times New Roman draws (Latin, Greek, Cyrillic, punctuation, ♥;
  heart emoji -> ♥), to/from <= 40, letter <= 240, a small whole-word blocklist with a kind refusal. 6/hour and 20/day per
  IP, queue max 30. Results are private (unguessable id) and deleted after 24 h; no gallery.
- **valxp-vm.sh**: QEMU (`-name valxp -machine pc-i440fx-jammy` so a newer QEMU can load the snapshot, restrict=on, guestfwd 10.0.2.2:8765 -> 127.0.0.1:8773, QMP /tmp/valxp-qmp.sock,
  monitor /tmp/valxp-mon.sock, VNC /tmp/valxp-vnc.sock); starts from snapshot `val-ready` when present.
- **systemd/**: valxp.target = valxp-vm + valxp-server (enabled); share.conf drop-ins (Nice=10, CPUWeight=25).
- Caddy (production file, applied by hand): in the `live.williamsharkey.com` block,
  `handle_path /valxp/* { reverse_proxy 127.0.0.1:8783 }`. The page calls `https://live.williamsharkey.com/valxp`
  (override with `?api=` for local testing; `http://localhost:8000` is an allowed origin).
- Re-snapshot after changing valentine.exe: boot fresh, wait for the agent, copy the exe to C:\p, `savevm val-ready`.

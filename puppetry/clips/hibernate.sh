#!/bin/bash
# Clip: XP's hidden Hibernate button, fetched from (-20396,-16706) and pressed.
X() { xprun "$@"; }
K() { echo "$1" > /tmp/qrec-cmd; sleep 0.4; }
W='C:\p\wp.exe'
X "$W cursor 1010 700 0" >/dev/null
python3 /root/qrec.py start hibernate 25; sleep 1.5
K "sendkey ctrl-esc"; sleep 1.2
K "sendkey u"; sleep 2.5
D=$(X "$W list" | awk '$3=="#32770"{print $1; exit}' | tr -d '\r')
B=$(X "$W find $D 20106" | tr -d '\r')
K "sendkey shift 2500"; sleep 3.5
X "$W tween $B 140 128 33 33 3200" >/dev/null; sleep 2.5
X "$W tween $B 116 128 82 33 900" >/dev/null; sleep 2
read BX BY BW BH < <(X "$W screenpos $B" | tr -d '\r')
X "$W cursor $((BX+41)) $((BY+16)) 1300" >/dev/null; sleep 0.8
X "$W click $B" >/dev/null
sleep 25
python3 /root/qrec.py stop hibernate

#!/bin/bash
# Boot Windows for Workgroups 3.11 in DOSBox-X on a headless X server and
# start one program.   w311.sh start PROGRAM.EXE | key <xdotool keys...> |
#                      type "text" | shot out.png | stop
export DISPLAY=:7
case "$1" in
start)
  pgrep -f "Xvfb :7" >/dev/null || (Xvfb :7 -screen 0 1024x800x24 >/dev/null 2>&1 &) ; sleep 1
  pkill -f "dosbox-x -conf /root/w311.conf"; sleep 1
  cat > /root/w311.conf <<CONF
[sdl]
autolock=false
output=surface
showmenu=false
[dosbox]
memsize=64
quit warning=false
[cpu]
cputype=pentium
core=normal
cycles=max
[render]
scaler=none
[autoexec]
mount c /root/w311
c:
SET TEMP=C:\\WINDOWS\\TEMP
SET PATH=C:\\WINDOWS
cd \\WINDOWS
WIN.COM $2
CONF
  (dosbox-x -conf /root/w311.conf >/root/w311.log 2>&1 &) ; sleep ${3:-25} ;;
key)  shift; W=$(xdotool search --name "DOSBox" | head -1); xdotool windowactivate --sync $W 2>/dev/null; for k in "$@"; do xdotool key --window $W $k; sleep 0.3; done ;;
type) W=$(xdotool search --name "DOSBox" | head -1); xdotool type --window $W --delay 80 "$2" ;;
shot) W=$(xdotool search --name "DOSBox" | head -1); import -window $W "$2" ;;
stop) pkill -f "dosbox-x -conf /root/w311.conf"; pkill -f "Xvfb :7" ;;
esac

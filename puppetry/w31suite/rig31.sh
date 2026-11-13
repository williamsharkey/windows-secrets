#!/bin/bash
# rig31.sh (local helper): the server-version test rig on sharkey, beside the live one
#   /root/w31test/s31 (golden = live golden + suite B3BOOT/BASILISK.SRC/PARTS.SRC), lab DOSBox-X on :61
#   COM1 8776, COM2 8798, public 127.0.0.1:8799, x11vnc 5961; units w31test-s31, w31test-vnc
set -e
D=$(cd "$(dirname "$0")" && pwd); H=root@165.227.95.55
scp -q "$D/b3boot.c" "$D/basilisk.c" "$D/parts.c" $H:/root/w31/labboot/
scp -q "$D/../w31/server.py" $H:/root/w31test/s31server.py
ssh -n $H 'set -e; cd /root/w31/labboot; export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:$PATH INCLUDE=/root/w31/dl/ow/h:/root/w31/dl/ow/h/win
  rm -f b3boot.exe; wcl -q -bt=windows -l=windows -ml -k16384 -fe=b3boot.exe b3boot.c >/dev/null; [ -f b3boot.exe ]
  B=/root/w31test/s31/golden/B3; cp b3boot.exe $B/B3BOOT.EXE; sed "s/\$/\r/" basilisk.c > $B/BASILISK.SRC; sed "s/\$/\r/" parts.c > $B/PARTS.SRC
  L=/root/snap/dosbox-x/common/w31s; sed -i "/^serial[12]=/d; s#^\[serial\]\$#[serial]\nserial1=nullmodem server:127.0.0.1 port:8776 transparent:1\nserial2=nullmodem server:127.0.0.1 port:8798 transparent:1#" $L/w31s.conf
  sed -i "s#^run=.*#run=C:\\\\B3\\\\B3BOOT.EXE#" /root/w31test/s31/golden/WINDOWS/WIN.INI; chown -R root:root /root/w31test/s31
  systemctl stop w31test-s31 2>/dev/null || true; systemctl reset-failed w31test-s31 2>/dev/null || true; /root/w31/lab.sh stop
  systemctl is-active -q w31test-vnc || systemd-run -q --unit=w31test-vnc --nice=10 /usr/bin/x11vnc -display :61 -rfbport 5961 -localhost -viewonly -shared -forever -nopw -nocursor -wait 5 -defer 5 -threads -quiet
  systemd-run -q --unit=w31test-s31 --nice=10 --setenv=W31_ROOT=/root/w31test/s31 --setenv=W31_SNAPC=/root/snap/dosbox-x/common/w31s \
    --setenv=W31_DBX=/root/w31test/dbx-lab.sh --setenv=W31_DISPLAY=:61 --setenv=W31_COM1=8776 --setenv=W31_COM2=8798 \
    --setenv=W31_PUBLIC=8799 --setenv=W31_VNC=5961 --setenv=W31_ORIGINS=http://127.0.0.1:8077 /root/w31/venv/bin/python /root/w31test/s31server.py
  for i in $(seq 90); do curl -s 127.0.0.1:8799/state | grep -q "\"ready\"" && break; sleep 1; done; curl -s 127.0.0.1:8799/state | head -c 120; echo'

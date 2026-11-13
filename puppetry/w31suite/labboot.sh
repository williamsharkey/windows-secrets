#!/bin/bash
# labboot.sh (local helper): the whole in-Windows build in the lab machine, browser link (files):
#   B3BOOT.EXE pours BASILISK.SRC + PARTS.SRC into Notepad, saves, compiles with Open Watcom in Windows, runs it.
set -e
D=$(cd "$(dirname "$0")" && pwd); H=root@165.227.95.55
SP=${SP:-/tmp}
ssh -n $H mkdir -p /root/w31/labboot
scp -q "$D/b3boot.c" "$D/basilisk.c" "$D/parts.c" $H:/root/w31/labboot/
ssh -n $H 'cd /root/w31/labboot && export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:$PATH INCLUDE=/root/w31/dl/ow/h:/root/w31/dl/ow/h/win && \
  rm -f b3boot.exe && wcl -q -bt=windows -l=windows -ml -k16384 -fe=b3boot.exe b3boot.c 2>&1 | head -5; [ -f b3boot.exe ]; \
  L=/root/snap/dosbox-x/common/w31s/run; cp b3boot.exe $L/B3/B3BOOT.EXE; sed "s/\$/\r/" basilisk.c > $L/B3/BASILISK.SRC; sed "s/\$/\r/" parts.c > $L/B3/PARTS.SRC; \
  rm -f $L/B3/BASILISK.EXE $L/B3/BASILISK.C $L/B3/PARTS.C $L/B3/*.OBJ; : > $L/B3/TOJS.TXT; : > $L/B3/TOWIN.TXT; \
  sed -i "s#^run=.*#run=C:\\\\B3\\\\B3BOOT.EXE#" $L/WINDOWS/WIN.INI; chown -R root:root /root/snap/dosbox-x/common/w31s; \
  /root/w31/lab.sh stop; /root/w31/lab.sh start; for i in $(seq 60); do grep -aq Hboot $L/B3/TOJS.TXT && break; sleep 1; done; \
  T0=$(date +%s.%N); /root/w31/labsend G; sleep 6; /root/w31/lab.sh shot /root/w31/b1.png; \
  for i in $(seq 150); do grep -aq "D.uilt\|Ebuild\|Ecompile\|Eno" $L/B3/TOJS.TXT && break; sleep 0.5; done; echo "G->built $(echo "$(date +%s.%N) - $T0" | bc) s"; \
  for i in $(seq 120); do grep -aq "Rassembled" $L/B3/TOJS.TXT && break; sleep 0.5; done; echo "G->assembled $(echo "$(date +%s.%N) - $T0" | bc) s"; \
  cat -v $L/B3/TOJS.TXT; echo; /root/w31/lab.sh shot /root/w31/b2.png'
scp -q $H:/root/w31/b1.png $H:/root/w31/b2.png $SP/

#!/bin/bash
# lab.sh (local helper): build a Win16 program on sharkey, put it in the lab machine, boot it, wait, fetch files
#   lab.sh prog.c [wait-seconds] [extra files to fetch from C:\B3 ...]
set -e
SRC=$1; W=${2:-20}; shift 2 || true
H=root@165.227.95.55
scp -q "$SRC" $H:/root/w31/lab-src.c; [ -f "$(dirname $SRC)/parts.c" ] && scp -q "$(dirname $SRC)/parts.c" $H:/root/w31/parts.c
ssh -n $H "cd /root/w31 && export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:\$PATH INCLUDE=/root/w31/dl/ow/h:/root/w31/dl/ow/h/win && \
  rm -f lab-src.exe && wcl -q -bt=windows -l=windows -ml -k16384 -fe=lab-src.exe lab-src.c 2>&1 | grep -v '^$' | head -20; \
  L=/root/snap/dosbox-x/common/w31s/run; [ -f lab-src.exe ] || exit 1; cp lab-src.exe \$L/B3/LAB.EXE; rm -f \$L/B3/SPY.TXT; : > \$L/B3/TOJS.TXT; : > \$L/B3/TOWIN.TXT; \
  sed -i 's#^run=.*#run=C:\\\\B3\\\\LAB.EXE#' \$L/WINDOWS/WIN.INI; chown -R root:root /root/snap/dosbox-x/common/w31s; \
  /root/w31/lab.sh stop; /root/w31/lab.sh start; sleep $W; /root/w31/lab.sh shot /root/w31/lab.png"
scp -q $H:/root/w31/lab.png ${SP:-/tmp}/lab.png
ssh -n $H "cat /root/snap/dosbox-x/common/w31s/run/B3/SPY.TXT 2>/dev/null" | tr -d '\r' > ${SP:-/tmp}/spy.txt || true

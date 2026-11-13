#!/bin/bash
# ship.sh (local helper): put the suite on both live 3.11 stages (sharkey-server), keeping backups.
#   server version:  /root/w31/golden/B3 (+ WINFILE.INI opens on C:\B3\WORK), /root/w31/server.py, restart w31-server
#   browser version: /root/w31b/c/B3 (the bundle's tree), /root/w31b/server.py, restart w31b-server
# The pages and the bundle (site/basilisk-31-browser/w31.jsdos) are published separately.
set -e
D=$(cd "$(dirname "$0")" && pwd); H=root@165.227.95.55
ssh -n $H 'curl -s 127.0.0.1:8782/state' | grep -q '"phase": "\(ready\|dark\)"' || { echo "someone is using BASILISK 3.11 now; try later"; exit 1; }
ssh -n $H 'curl -s 127.0.0.1:8785/state' | grep -q '"visitors": 0' || { echo "someone is in the browser version now; try later"; exit 1; }
scp -q "$D/b3boot.c" "$D/basilisk.c" "$D/parts.c" $H:/root/w31/labboot/
scp -q "$D/../w31/server.py" $H:/root/w31/server.py.new
scp -q "$D/../w31b/server.py" $H:/root/w31b/server.py.new
ssh -n $H 'set -e; cd /root/w31/labboot; export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:$PATH INCLUDE=/root/w31/dl/ow/h:/root/w31/dl/ow/h/win
  rm -f b3boot.exe; wcl -q -bt=windows -l=windows -ml -k16384 -fe=b3boot.exe b3boot.c >/dev/null; [ -f b3boot.exe ]
  K=/root/w31/backup-$(date +%Y%m%d-%H%M%S); mkdir -p $K/golden-B3 $K/w31b-B3
  cp -a /root/w31/golden/B3/. $K/golden-B3/; cp -a /root/w31/golden/WINDOWS/WINFILE.INI $K/ 2>/dev/null || true
  cp -a /root/w31b/c/B3/. $K/w31b-B3/; cp /root/w31/server.py $K/w31-server.py; cp /root/w31b/server.py $K/w31b-server.py
  for B in /root/w31/golden/B3 /root/w31b/c/B3; do
    cp b3boot.exe $B/B3BOOT.EXE; sed "s/\$/\r/" basilisk.c > $B/BASILISK.SRC; sed "s/\$/\r/" parts.c > $B/PARTS.SRC
    rm -f $B/LINK.H $B/BASILISK.C $B/PARTS.C $B/BASILISK.EXE $B/*.OBJ $B/TABS.CRD
  done
  for F in /root/w31/golden/WINDOWS/WINFILE.INI /root/w31b/c/WINDOWS/WINFILE.INI; do
    [ -f $F ] && sed -i "s#^dir1=.*#dir1=0,0,522,249,-1,-1,1,0,201,1905,174,C:\\\\B3\\\\WORK\\\\*.*#" $F || printf "[Settings]\r\ndir1=0,0,522,249,-1,-1,1,0,201,1905,174,C:\\\\B3\\\\WORK\\\\*.*\r\n" > $F
  done
  /root/w31/venv/bin/python -W error -m py_compile /root/w31/server.py.new /root/w31b/server.py.new
  mv /root/w31/server.py.new /root/w31/server.py; mv /root/w31b/server.py.new /root/w31b/server.py
  systemctl restart w31b-server; systemctl restart w31-server
  sleep 3; systemctl is-active w31-server w31b-server; echo "backup: $K"'

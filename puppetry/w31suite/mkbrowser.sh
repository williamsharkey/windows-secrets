#!/bin/bash
# mkbrowser.sh (local helper): the in-browser bundle with the suite, on sharkey:
#   /root/w31b/suite/c = /root/w31b/c + suite B3BOOT/BASILISK.SRC/PARTS.SRC + File Manager opening on C:\B3\WORK
#   -> /root/w31b/suite/www/w31.jsdos   (copy it to site/basilisk-31-browser/ to ship)
set -e
D=$(cd "$(dirname "$0")" && pwd); H=root@165.227.95.55
scp -q "$D/b3boot.c" "$D/basilisk.c" "$D/parts.c" "$D/../w31b/mkbundle.py" $H:/root/w31/labboot/
ssh -n $H 'set -e; cd /root/w31/labboot; export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:$PATH INCLUDE=/root/w31/dl/ow/h:/root/w31/dl/ow/h/win
  rm -f b3boot.exe; wcl -q -bt=windows -l=windows -ml -k16384 -fe=b3boot.exe b3boot.c >/dev/null; [ -f b3boot.exe ]
  wcl -q -bt=windows -l=windows -ml -k16384 -fe=check.exe basilisk.c >/dev/null; rm -f check.exe *.o *.obj
  S=/root/w31b/suite; rm -rf $S; mkdir -p $S/www; cp -a /root/w31b/c $S/c; B=$S/c/B3
  cp b3boot.exe $B/B3BOOT.EXE; sed "s/\$/\r/" basilisk.c > $B/BASILISK.SRC; sed "s/\$/\r/" parts.c > $B/PARTS.SRC; rm -f $B/LINK.H
  sed -i "s#^dir1=.*#dir1=0,0,522,249,-1,-1,1,0,201,1905,174,C:\\\\B3\\\\WORK\\\\*.*#" $S/c/WINDOWS/WINFILE.INI
  python3 mkbundle.py $S'

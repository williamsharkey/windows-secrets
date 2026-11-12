#!/bin/bash
# rt.sh NAME : build VAL.EXE, restart Win 3.11, send the t1 job, screenshot to /root/val31/NAME.png
cd /root/val31 || exit 1
export WATCOM=/root/val31/ow PATH=/root/val31/ow/binl64:$PATH INCLUDE=/root/val31/ow/h:/root/val31/ow/h/win
wcl -q -bt=windows -l=windows -ml val.c 2>&1 | grep -v "^$" | tail -8
C=/root/snap/dosbox-x/common/val31
cp val.exe $C/run/VAL/VAL.EXE && chown root:root $C/run/VAL/VAL.EXE
./dbx.sh stop; pkill -f "^python3 t1.py"; sleep 0.5
(setsid python3 t1.py > t1.log 2>&1 &); sleep 0.5
./dbx.sh start
for i in $(seq 1 60); do grep -q READY t1.log && break; sleep 1; done
sleep 1.5
cat t1.log
./dbx.sh shot /root/val31/$1.png

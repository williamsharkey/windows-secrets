#!/bin/bash
# runscene.sh NAME "puppet args" [fps] - record a puppet scene start to finish
NAME=$1; ARGS=$2; FPS=${3:-20}
xprun "del C:\\p\\puppet.log" >/dev/null
python3 /root/qrec.py start $NAME $FPS; sleep 1
xprun "spawn C:\\p\\puppet.exe $ARGS" >/dev/null
for i in $(seq 1 600); do
  sleep 2
  if xprun "type C:\\p\\puppet.log" 2>/dev/null | grep -q "puppet end"; then break; fi
done
sleep 1
python3 /root/qrec.py stop $NAME
xprun "type C:\\p\\puppet.log"

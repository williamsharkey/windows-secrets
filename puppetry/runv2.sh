#!/bin/bash
# runv2.sh - BASILISK V2 in one take: the prophecy typed and compiled (v2), then BASILISK itself,
# with XP's real audio captured by QEMU in sync with the framebuffer recording.
xprun "del C:\\p\\puppet.log & del C:\\p\\ans*.wav & del C:\\p\\ans*.txt" >/dev/null
rm -f /root/rec-v2take.wav
python3 /root/qrec.py start v2take 20; sleep 1
echo "wavcapture /root/rec-v2take.wav snd0 22050 16 2" > /tmp/qrec-cmd
xprun "spawn C:\\p\\puppet.exe v2" >/dev/null
for i in $(seq 1 900); do
  sleep 2
  n=$(xprun "type C:\\p\\puppet.log" 2>/dev/null | grep -c "puppet end")
  [ "$n" -ge 2 ] && break
done
sleep 2
echo "stopcapture 0" > /tmp/qrec-cmd; sleep 1
python3 /root/qrec.py stop v2take
xprun "type C:\\p\\puppet.log"
ls -la /root/rec-v2take.wav
xprun "type C:\\p\\puppet.log" > /root/v2take.log
SIZES=$(xprun "dir C:\\p\\ans*.wav" | tr -d '\r' | awk '{for(i=2;i<=NF;i++) if($i ~ /^ans[0-9]+\.wav$/){x=$(i-1); gsub(",","",x); printf "%s ", x}}')
echo "answer sizes: $SIZES"
python3 /root/placeaudio.py /root/v2take.log /root/rec-v2take.wav "$SIZES" /root/rec-v2take-placed.wav 1.5 v2
ffmpeg -loglevel error -y -i /root/rec-v2take.mp4 -i /root/rec-v2take-placed.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -shortest /root/rec-v2take-av.mp4 && echo muxed

#!/bin/bash
# runbasilisk.sh - one continuous take: the curious user (intro), then BASILISK itself,
# with XP's real audio captured by QEMU in sync with the framebuffer recording.
xprun "del C:\\p\\puppet.log & del C:\\p\\ans*.wav & del C:\\p\\ans*.txt" >/dev/null
rm -f /root/rec-basilisk.wav
python3 /root/qrec.py start basilisk 20; sleep 1
echo "wavcapture /root/rec-basilisk.wav snd0 22050 16 2" > /tmp/qrec-cmd
xprun "spawn C:\\p\\puppet.exe intro" >/dev/null
for i in $(seq 1 900); do
  sleep 2
  n=$(xprun "type C:\\p\\puppet.log" 2>/dev/null | grep -c "puppet end")
  [ "$n" -ge 2 ] && break
done
sleep 2
echo "stopcapture 0" > /tmp/qrec-cmd; sleep 1
python3 /root/qrec.py stop basilisk
xprun "type C:\\p\\puppet.log"
ls -la /root/rec-basilisk.wav
xprun "type C:\\p\\puppet.log" > /root/basilisk.log
SIZES=$(xprun "dir C:\\p\\ans*.wav" | tr -d '\r' | awk '{for(i=2;i<=NF;i++) if($i ~ /^ans[0-9]+\.wav$/){x=$(i-1); gsub(",","",x); printf "%s ", x}}')
echo "answer sizes: $SIZES"
python3 /root/placeaudio.py /root/basilisk.log /root/rec-basilisk.wav "$SIZES" /root/rec-basilisk-placed.wav 1.5
ffmpeg -loglevel error -y -i /root/rec-basilisk.mp4 -i /root/rec-basilisk-placed.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -shortest /root/rec-basilisk-av.mp4 && echo muxed

#!/bin/sh
# encode_videos.sh PREFIX NAME...: NAME.mkv (demo311's lossless frames) + NAME.wav -> OUT/PREFIX-NAME.{mp4,webm,png}
set -e
P=$1; shift; OUT=${OUT:-../site/sndrec/video}
for s in "$@"; do
  I=$(ffmpeg -hide_banner -nostats -i $s.wav -af ebur128 -f null - 2>&1 | grep -oP 'I:\s+\K-?[\d.]+(?= LUFS)' | tail -1)
  PK=$(python3 -c "
import numpy as np;d=open('$s.wav','rb').read();i=d.find(b'data');a=np.frombuffer(d[i+8:],dtype='<f4');print(20*np.log10(abs(a).max()))")
  G=$(python3 -c "print(round(-16-($I),2))")
  L=$(python3 -c "print(',alimiter=limit=0.891:level=disabled' if $PK+$G>-1 else '')")
  AF="volume=${G}dB$L"
  ffmpeg -hide_banner -loglevel error -y -i $s.mkv -i $s.wav -map 0:v -map 1:a -c:v libx264 -preset slow -tune animation -crf 8 -pix_fmt yuv420p -profile:v high -movflags +faststart -af "$AF" -c:a aac -b:a 128k -shortest $OUT/$P-$s.mp4
  ffmpeg -hide_banner -loglevel error -y -i $s.mkv -i $s.wav -map 0:v -map 1:a -c:v libvpx-vp9 -pix_fmt yuv444p -profile:v 1 -crf 20 -b:v 0 -row-mt 1 -deadline good -cpu-used 2 -af "$AF" -c:a libopus -b:a 128k -shortest $OUT/$P-$s.webm
  echo "$P-$s: I $I LUFS, gain $G dB $L"
done

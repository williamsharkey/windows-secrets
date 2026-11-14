#!/bin/sh
# songview.sh SONG.ogg|wav [OUT.png]: a spectrogram and waveform picture of a rendered song, for a quick look
in="$1"; out="${2:-${1%.*}.png}"
ffmpeg -nostdin -v error -y -i "$in" -filter_complex \
  "[0:a]aformat=channel_layouts=mono,showspectrumpic=s=1400x360:legend=0:scale=log:fscale=log[s];[0:a]aformat=channel_layouts=mono,showwavespic=s=1400x120:colors=white[w];[s][w]vstack" \
  -frames:v 1 "$out" && echo "$out"

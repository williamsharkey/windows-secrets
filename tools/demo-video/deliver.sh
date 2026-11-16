#!/bin/bash
# The hand-off files for one render: a poster frame, a web copy (smaller, +faststart) and a contact sheet.
#   deliver.sh OUT.mp4 [POSTER_SECONDS] [MIX.wav]   (MIX: the web copy's sound from the mix, one AAC generation)
set -e
F=$1; T=${2:-16}; M=${3:-}; B=${F%.mp4}
ffmpeg -v error -y -ss $T -i $F -frames:v 1 $B-poster.png
if [ -n "$M" ]; then
  ffmpeg -v error -y -i $F -i $M -map 0:v -map 1:a -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -c:a aac -b:a 160k -shortest -movflags +faststart $B-web.mp4
else
  ffmpeg -v error -y -i $F -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart $B-web.mp4
fi
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $F)
ffmpeg -v error -y -i $F -vf "fps=24/$D,scale=480:270,tile=6x4" -frames:v 1 $B-sheet.png
ls -la $B*

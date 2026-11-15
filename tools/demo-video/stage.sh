#!/bin/bash
# Copy the edit's inputs to the machine that assembles the video (here: the owner's Mac, `primary-mac`), into
# ~/sw2000-video: the tools, fonts, art, music, narration and the captures (gzip in transit).
#   tools/demo-video/stage.sh HOST [SCENE ...]      (no scenes: everything but the captures)
set -e
H=${1:-primary-mac}; shift || true
R=$(cd "$(dirname "$0")/../.." && pwd)
D=sw2000-video
SW=${SW:-/mnt/c/Users/willi/video-sw}
T=$(mktemp -d)
mkdir -p $T/tools $T/fonts $T/art $T/music
cp "$R"/tools/demo-video/*.py $T/tools/
cp "$R"/design/brand/sndwave1993/fonts/DejaVuSans*.ttf $T/fonts/
cp /usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf $T/fonts/
cp "$R"/design/brand/sndwave1993/screens/title-640.png "$R"/design/brand/sndwave1993/box/box-3d-render.png \
   "$R"/design/brand/sndwave1993/album/citypop1993-lockup-horizontal.png "$R"/design/brand/sndwave1993/album/citypop1993-lockup-stacked.png $T/art/
cp ~/songs/site/songs/lifestyle-aesthetics/atrium-level-b2.mp3 $T/music/
cp "$R"/site/citypop/audio/12.mp3 $T/music/citypop-12.mp3
cp -r ~/video/work/tts $T/tts
ssh $H "mkdir -p ~/$D/cap"
tar -C $T -cf - . | ssh $H "tar -C ~/$D -xf -"
rm -rf $T
for s in "$@"; do
  tar -C $SW/cap -cf - $s/cap.bhrc $s/editor.wav | gzip -1 | ssh $H "rm -rf ~/$D/cap/$s; tar -C ~/$D/cap -xzf -"
  echo staged $s
done

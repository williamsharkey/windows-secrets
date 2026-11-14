#!/bin/bash
# BASILISK SYNTH 1.2.2 re-render for sndrec.html: run only when the PC window is ours. One VM at a time.
W=/mnt/c/Users/willi/sndrec-xp; T=/mnt/c/Users/willi/github/williamsharkey/windows-secrets/tools/sndrec-demo; cd ~/sndrec-demo
log() { echo "$(date +%T) load $(cut -d' ' -f1 /proc/loadavg): $*"; }
log "1/3 the 43 programs"
python3 $T/xp_render.py xp122 --host $W/bsynth-host.exe --plugin $W/BasiliskSynth.vst3 --work $W/rounds --parallel 1 --tries 4 --warmup 8 --latency 7200 > xp122/render.log 2>&1; grep -E 'presets;' xp122/render.log
mkdir -p xp122m/wav; python3 - <<'PY'
import json; B='/home/wm/sndrec-demo/'
rows=[r for r in json.load(open(B+'xp122/presets.json')) if r['kind']=='macro']
json.dump(rows,open(B+'xp122m/presets.json','w'))
PY
rm -rf xp122m/mid; cp -r xp122/mid xp122m/
python3 $T/xp_macro.py xp122m --host $W/bsynth-host.exe --plugin $W/BasiliskSynth.vst3 --work $W/macro --tries 4 --latency 7200 2>&1 | tail -3
log "2/3 the owner's picks on XP"
python3 $T/xp_render.py libxp --host $W/bsynth-host.exe --plugin $W/BasiliskSynth.vst3 --work $W/rounds2 --parallel 1 --tries 4 --warmup 8 --latency 7200 > libxp/render.log 2>&1; grep -E 'presets;' libxp/render.log
rm -rf $W/rounds $W/rounds2 $W/macro
log "3/3 editor clips (encoded and deleted take by take: C: is short of space)"
mkdir -p pxv122
for c in assembly play change macro; do
  st=9.5; [ $c = assembly ] && st=0
  for take in 1 2 3; do
    rm -rf $W/v; python3 $T/xp_video.py xp122 $W/v --host $W/bsynth-host-timed.exe --plugin $W/BasiliskSynth.vst3 $c > /dev/null 2>&1
    log "$c take $take"
    if python3 $T/xp_check.py $W/v $c --start $st; then
      s0=$(python3 -c "print(int(round($st*30)))")
      python3 $T/pxv.py encode $W/v/$c pxv122 xp-$c --start $s0 --poster $([ $c = assembly ] && echo 420 || echo 120) && python3 $T/pxv.py verify pxv122 xp-$c $W/v/$c --start $s0
      n=$(ls $W/v/$c/*.bmp | wc -l); dur=$(python3 -c "print(($n-$s0)/30)"); ss=$(python3 -c "print($st+7200/48000)")
      ffmpeg -v error -y -ss $ss -t $dur -i $W/v/$c.wav -c:a pcm_f32le pxv122/xp-$c.wav
      echo "   KEPT $c take $take"; break
    fi
  done
  rm -rf $W/v
done
log "done"

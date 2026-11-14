#!/bin/bash
# audio_mac.sh: the 1.2.2 tone gate (organ chord held for 60 s, live) through the real plugin, per QEMU accel setting
cd ~/bsynth; mkdir -p emuaudio
SC=$(python3 -c "print(','.join('%g:%d:90:6'%(3*k,[48,55,60,64][k%4]) for k in range(20)))")
LOG="$HOME/Library/Caches/BASILISK SYNTH/plugin.log"
take(){ # label accel
  BSYNTH_ACCEL="$2" ./bsynth-host hf/BasiliskSynth.vst3 emuaudio/$1.wav --warmup 8 --dna "organ_pipe_open_31#16;A20R300" --score $SC --tail 2 --timing > emuaudio/$1.txt 2>&1
  grep -a "audio:" "$LOG" | tail -1 >> emuaudio/$1.txt
  grep -a "guest: log underruns" "$LOG" | tail -1 >> emuaudio/$1.txt
}
for i in 1 2; do
  take base$i  "tcg,thread=single,tb-size=1024"
  take tb256_$i "tcg,thread=single,tb-size=256"
  take tb4096_$i "tcg,thread=single,tb-size=4096"
  take multi$i "tcg,thread=multi,tb-size=1024"
done
echo done > emuaudio/DONE

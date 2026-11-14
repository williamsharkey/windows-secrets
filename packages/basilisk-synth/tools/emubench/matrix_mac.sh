#!/bin/bash
# matrix_mac.sh: TCG and VNC-client variants of the shipped machine on the Mac's bundled QEMU 11.1 (3 runs each)
cd ~/bsynth; R=hf/BasiliskSynth.vst3/Contents/Resources/qemu-arm64; M=hf/BasiliskSynth.vst3/Contents/Resources/machine
run(){ python3 emubench.py --qemu $R/bin/qemu-system-i386 --machine $M --share $R/share/qemu --idle 4 --out emu-mac.jsonl "$@" >/dev/null 2>&1; }
for i in 1 2 3; do
  run --label base
  run --label eager --vnc-mode eager
  run --label tb256 --accel tcg,thread=single,tb-size=256
  run --label tb4096 --accel tcg,thread=single,tb-size=4096
  run --label multi --accel tcg,thread=multi,tb-size=1024
  run --label novnc --vnc-mode none
  run --label icount --accel tcg,thread=single,tb-size=1024 --extra "-icount shift=auto,sleep=on"
done
echo done

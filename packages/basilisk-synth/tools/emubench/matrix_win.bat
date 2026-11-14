@echo off
rem matrix_win.bat: the shipped machine on Windows - bundled QEMU 11.1 TCG (resume), and WHPX (cold boot, x86_64 binary)
set PY=C:\Users\willi\AppData\Local\Programs\Python\Python313\python.exe
set B=C:\Users\willi\github\williamsharkey\windows-secrets\packages\basilisk-synth\tools\emubench\bench.py
set M=C:\Users\willi\bsynth-hf\BasiliskSynth.vst3\Contents\Resources\machine
set Q=C:\Users\willi\AppData\Local\BASILISK SYNTH\qemu-11.1-1\qemu
set W=C:\Users\willi\emubench-qemu
set O=C:\Users\willi\emubench-qemu\emu-win.jsonl
for %%i in (1 2) do (
  "%PY%" %B% --qemu "%Q%\qemu-system-i386.exe" --machine %M% --share "%Q%\share" --label win-tcg-plugin --idle 4 --out %O%
  "%PY%" %B% --qemu "%Q%\qemu-system-i386.exe" --machine %M% --share "%Q%\share" --label win-tcg-eager --vnc-mode eager --idle 4 --out %O%
)
"%PY%" %B% --qemu "%W%\qemu-system-x86_64.exe" --machine %M% --share "%W%\share" --label win-tcg-cold --cold --timeout 300 --idle 4 --out %O%
"%PY%" %B% --qemu "%W%\qemu-system-x86_64.exe" --machine %M% --share "%W%\share" --label win-whpx-cold --cold --accel whpx --timeout 300 --idle 4 --out %O%
echo done> C:\Users\willi\emubench-qemu\DONE

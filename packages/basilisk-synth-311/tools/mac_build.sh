#!/bin/sh
# On a Mac: build the core (universal), the plugin (VST3 and AU; universal) and stage the machine into each bundle.
#   mac_build.sh WORKDIR    (WORKDIR holds: dosbox-pure/ (patched), DPF/, pkg/ (this package), core/ (shared core),
#                            wfw/ (the WfW 3.11 C: drive), gout/ (the guest binaries from guest/build.sh),
#                            library.zip + library.names.txt (tools/make_library311.py))
set -e
# -ffp-contract=off everywhere: arm64 compilers fuse a*b+c into one rounding by default, which changes the card's
# mix in the last bit; without it, macOS arm64, x86_64, Windows and Linux render bit-identically.
W=$(cd "$1" && pwd)
cd "$W"
for a in arm64 x86_64; do
  rm -rf "dbp-$a"; cp -R dosbox-pure "dbp-$a"
  (cd "dbp-$a" && rm -rf build && make -j"$(sysctl -n hw.ncpu)" CXX="c++ -arch $a -mmacosx-version-min=10.15 -ffp-contract=off" STRIP="strip" >"../dbp-$a.log" 2>&1)
done
lipo -create dbp-arm64/dosbox_pure_libretro.dylib dbp-x86_64/dosbox_pure_libretro.dylib -output dosbox_pure_libretro.dylib
codesign --force -s - dosbox_pure_libretro.dylib
mkdir -p basilisk-synth/core basilisk-synth-311
rm -rf basilisk-synth/core basilisk-synth-311; mkdir -p basilisk-synth; cp -R core basilisk-synth/core; cp -R pkg basilisk-synth-311
cd basilisk-synth-311/plugin
make DPF_PATH="$W/DPF" DPF_TARGET_DIR="$W/out" DPF_BUILD_DIR="$W/obj" \
  CFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -ffp-contract=off" CXXFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -ffp-contract=off" \
  LDFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15" -j"$(sysctl -n hw.ncpu)" vst3 au >"$W/plugin.log" 2>&1
# the snapshots: made here, one per CPU, by the engine built for that CPU (tools/make_machine.py)
cd "$W"
for a in arm64 x86_64; do
  cc -O2 -arch $a -o "engine-$a" basilisk-synth-311/engine/engine.c basilisk-synth-311/engine/engine_main.c -Ibasilisk-synth-311/engine
  cc -O2 -arch $a -o "offs-$a" -Ibasilisk-synth-311/engine basilisk-synth-311/tools/offs.c
  BS311_ENGINE="$W/engine-$a" BS311_OFFS="$W/offs-$a" arch -$a /usr/bin/python3 basilisk-synth-311/tools/make_machine.py \
    "$W/wfw" "$W/gout" "$W/dosbox_pure_libretro.dylib" "$W/machine-$a" --library "$W/library.zip" --xpsounds "$W/xpsounds" --help "$W/BASIL16.HLP"
done
cmp machine-arm64/drive.zip machine-x86_64/drive.zip
# render311 (tools/render311.cpp): the batch renderer, universal
cc -O2 -ffp-contract=off -arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -c -o "$W/engine-r.o" basilisk-synth-311/engine/engine.c -Ibasilisk-synth-311/engine
c++ -std=c++17 -O2 -ffp-contract=off -arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -o "$W/render311" basilisk-synth-311/tools/render311.cpp \
  basilisk-synth/core/dna.cpp basilisk-synth/core/voices.cpp basilisk-synth/core/dna3.cpp basilisk-synth/core/engine3.cpp basilisk-synth/core/scales.cpp "$W/engine-r.o"
codesign --force -s - "$W/render311"
cd "$W/out"
for b in Basilisk16.vst3 Basilisk16.component; do
  M="$b/Contents/Resources/machine"
  rm -rf "$M"; mkdir -p "$M"
  cp "$W/dosbox_pure_libretro.dylib" "$M/"
  cp "$W/machine-arm64/w31.conf" "$M/"
  cp "$W/machine-arm64/w31.state" "$M/w31-arm64.state"
  cp "$W/machine-x86_64/w31.state" "$M/w31-x86_64.state"
  cp "$W/machine-arm64/drive.zip" "$W/machine-arm64/library.zip" "$W/machine-arm64/library.names.txt" "$M/"
  codesign --force --deep -s - "$b"
done
ls -la "$W/out"

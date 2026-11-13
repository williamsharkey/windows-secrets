#!/bin/sh
# On a Mac: build the core (universal), the plugin (VST3 and AU; universal) and stage the machine into each bundle.
#   mac_build.sh WORKDIR    (WORKDIR holds: dosbox-pure/ (patched), DPF/, pkg/ (this package), core/ (shared core),
#                            wfw/ (the WfW 3.11 C: drive), gout/ (the guest binaries from guest/build.sh))
set -e
W=$(cd "$1" && pwd)
cd "$W"
for a in arm64 x86_64; do
  rm -rf "dbp-$a"; cp -R dosbox-pure "dbp-$a"
  (cd "dbp-$a" && rm -rf build && make -j"$(sysctl -n hw.ncpu)" CXX="c++ -arch $a -mmacosx-version-min=10.15" STRIP="strip" >"../dbp-$a.log" 2>&1)
done
lipo -create dbp-arm64/dosbox_pure_libretro.dylib dbp-x86_64/dosbox_pure_libretro.dylib -output dosbox_pure_libretro.dylib
codesign --force -s - dosbox_pure_libretro.dylib
mkdir -p basilisk-synth/core basilisk-synth-311
rm -rf basilisk-synth/core basilisk-synth-311; mkdir -p basilisk-synth; cp -R core basilisk-synth/core; cp -R pkg basilisk-synth-311
cd basilisk-synth-311/plugin
make DPF_PATH="$W/DPF" DPF_TARGET_DIR="$W/out" DPF_BUILD_DIR="$W/obj" \
  CFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15" CXXFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15" \
  LDFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15" -j"$(sysctl -n hw.ncpu)" vst3 au >"$W/plugin.log" 2>&1
# the snapshots: made here, one per CPU, by the engine built for that CPU (tools/make_machine.py)
cd "$W"
for a in arm64 x86_64; do
  cc -O2 -arch $a -o "engine-$a" basilisk-synth-311/engine/engine.c basilisk-synth-311/engine/engine_main.c -Ibasilisk-synth-311/engine
  cc -O2 -arch $a -o "offs-$a" -Ibasilisk-synth-311/engine basilisk-synth-311/tools/offs.c
  BS311_ENGINE="$W/engine-$a" BS311_OFFS="$W/offs-$a" arch -$a /usr/bin/python3 basilisk-synth-311/tools/make_machine.py \
    "$W/wfw" "$W/gout" "$W/dosbox_pure_libretro.dylib" "$W/machine-$a" --folder
done
diff -r machine-arm64/drive machine-x86_64/drive
cd "$W/out"
for b in Basilisk16.vst3 Basilisk16.component; do
  M="$b/Contents/Resources/machine"
  rm -rf "$M"; mkdir -p "$M"
  cp "$W/dosbox_pure_libretro.dylib" "$M/"
  cp "$W/machine-arm64/w31.conf" "$M/"
  cp "$W/machine-arm64/w31.state" "$M/w31-arm64.state"
  cp "$W/machine-x86_64/w31.state" "$M/w31-x86_64.state"
  cp -R "$W/machine-arm64/drive" "$M/drive"
  codesign --force --deep -s - "$b"
done
ls -la "$W/out"

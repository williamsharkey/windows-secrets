#!/bin/sh
# On a Mac: build the core (universal), the plugin (VST3 and AU; universal) and stage the machine into each bundle.
#   mac_build.sh WORKDIR    (WORKDIR holds: dosbox-pure/ (patched), DPF/, pkg/ (this package), core/ (shared core),
#                            wfw/ (the WfW 3.11 C: drive), gout/ (the guest binaries from guest/build.sh),
#                            library.zip + library.names.txt (tools/make_library311.py), machine/ (tools/build.sh's machine:
#                            its w31.state is the one snapshot for every OS and CPU))
set -e
# -ffp-contract=off everywhere: arm64 compilers fuse a*b+c into one rounding by default, which changes the card's
# mix in the last bit; without it, macOS arm64, x86_64, Windows and Linux render bit-identically.
W=$(cd "$1" && pwd)
cd "$W"
for a in arm64 x86_64; do
  rm -rf "dbp-$a"; cp -R dosbox-pure "dbp-$a"
  (cd "dbp-$a" && rm -rf build && make -j"$(sysctl -n hw.ncpu)" CXX="c++ -arch $a -mmacosx-version-min=10.15 -ffp-contract=off -DDISABLE_DYNAREC=1" CC="cc -arch $a -mmacosx-version-min=10.15 -DDISABLE_DYNAREC=1" STRIP="strip" >"../dbp-$a.log" 2>&1)
done
lipo -create dbp-arm64/dosbox_pure_libretro.dylib dbp-x86_64/dosbox_pure_libretro.dylib -output dosbox_pure_libretro.dylib
codesign --force -s - dosbox_pure_libretro.dylib
mkdir -p basilisk-synth/core basilisk-synth-311
rm -rf basilisk-synth/core basilisk-synth-311; mkdir -p basilisk-synth/help; cp -R core basilisk-synth/core; cp -R pkg basilisk-synth-311
rm -rf basilisk-synth/help/install; cp -R helpinstall basilisk-synth/help/install   # (make_machine.py's help installer)
cd basilisk-synth-311/plugin
make DPF_PATH="$W/DPF" DPF_TARGET_DIR="$W/out" DPF_BUILD_DIR="$W/obj" \
  CFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -ffp-contract=off" CXXFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -ffp-contract=off" \
  LDFLAGS="-arch x86_64 -arch arm64 -mmacosx-version-min=10.15" -j"$(sysctl -n hw.ncpu)" vst3 au clap >"$W/plugin.log" 2>&1
cd "$W"
# the machine: the one tools/build.sh made (machine/: one snapshot for every OS and CPU, the cores have no dynamic recompiler)
# render311 (tools/render311.cpp): the batch renderer, universal
cc -O2 -ffp-contract=off -arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -c -o "$W/engine-r.o" basilisk-synth-311/engine/engine.c -Ibasilisk-synth-311/engine
c++ -std=c++17 -O2 -ffp-contract=off -arch x86_64 -arch arm64 -mmacosx-version-min=10.15 -o "$W/render311" basilisk-synth-311/tools/render311.cpp \
  basilisk-synth/core/dna.cpp basilisk-synth/core/voices.cpp basilisk-synth/core/dna3.cpp basilisk-synth/core/engine3.cpp basilisk-synth/core/scales.cpp basilisk-synth/core/userstore.cpp "$W/engine-r.o"
codesign --force -s - "$W/render311"
cd "$W/out"
for b in SNDWAVE2000.vst3 SNDWAVE2000.component; do
  M="$b/Contents/Resources/machine"
  rm -rf "$M"; mkdir -p "$M"
  cp "$W/dosbox_pure_libretro.dylib" "$M/"
  cp "$W/machine/w31.conf" "$W/machine/w31.state" "$M/"
  cp "$W/machine/drive.zip" "$W/machine/library.zip" "$W/machine/library.names.txt" "$M/"
  cp -R "$W/machine/packs" "$W/machine/citypop" "$M/"
  codesign --force --deep -s - "$b"
done
codesign --force --deep -s - SNDWAVE2000.clap   # (the CLAP uses the machine of the SNDWAVE2000.vst3 installed beside it)
ls -la "$W/out"

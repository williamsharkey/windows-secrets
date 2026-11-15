#!/bin/sh
# Build BASILISK 16 from source on Linux/WSL: the guest (Open Watcom), DOSBox Pure with the BSYN card (Linux for the
# snapshot, Windows by mingw cross-compile), the machine (drive.zip + snapshot), and the Windows VST3.
# The macOS build runs on a Mac: tools/mac_build.sh (this script prepares its inputs in $W/macsrc).
#   tools/build.sh WORKDIR
set -e
PKG=$(cd "$(dirname "$0")/.." && pwd)
REPO=$(cd "$PKG/../.." && pwd)
W=${1:?workdir}; mkdir -p "$W"; W=$(cd "$W" && pwd)
DBP_COMMIT=$(cat "$PKG/dosbox-pure/UPSTREAM.txt")
DPF_COMMIT=$(cat "$PKG/plugin/DPF_UPSTREAM.txt")

# --- tools and sources
[ -d "$W/ow" ] || { mkdir -p "$W/ow"; (cd "$W/ow" && gh release download Current-build -R open-watcom/open-watcom-v2 -p ow-snapshot.tar.xz && tar xf ow-snapshot.tar.xz && rm ow-snapshot.tar.xz); }
[ -d "$W/dosbox-pure" ] || { git clone -q https://codeberg.org/schelling/dosbox-pure.git "$W/dosbox-pure"; (cd "$W/dosbox-pure" && git checkout -q "$DBP_COMMIT" && git apply "$PKG/dosbox-pure/dosbox-pure.patch"); }
cp "$PKG/dosbox-pure/bsynth.cpp" "$W/dosbox-pure/src/hardware/bsynth.cpp"
[ -d "$W/DPF" ] || { git clone -q --recursive https://github.com/DISTRHO/DPF.git "$W/DPF"; (cd "$W/DPF" && git checkout -q $DPF_COMMIT && git submodule update -q --init --recursive && git apply "$PKG/plugin/dpf.patch"); }

# --- the guest
sh "$PKG/guest/build.sh" "$W/ow" "$W/gout"

# --- DOSBox Pure: Linux (makes the snapshot) and Windows
# no dynamic recompiler (DISABLE_DYNAREC): the saved state then has one layout on every OS and CPU, and one snapshot serves all
(cd "$W/dosbox-pure" && make -j"$(nproc)" CC="gcc -DDISABLE_DYNAREC=1" CXX="g++ -DDISABLE_DYNAREC=1" >/dev/null)
rm -rf "$W/dbp-win"; cp -r "$W/dosbox-pure" "$W/dbp-win"; rm -rf "$W/dbp-win/build" "$W/dbp-win"/*.so
(cd "$W/dbp-win" && make platform=windows CC="x86_64-w64-mingw32-gcc -DDISABLE_DYNAREC=1" CXX="x86_64-w64-mingw32-g++ -DDISABLE_DYNAREC=1" STRIP=x86_64-w64-mingw32-strip \
  LDFLAGS="-Wl,--gc-sections -fno-ident -O2 -shared -static -static-libgcc -static-libstdc++" -j"$(nproc)" >/dev/null)

# --- the engine as a test process, and the machine
gcc -O2 -o "$W/engine" "$PKG/engine/engine.c" "$PKG/engine/engine_main.c" -I"$PKG/engine" -ldl -lpthread
gcc -O2 -o "$W/offs" -I"$PKG/engine" "$PKG/tools/offs.c"
rm -rf "$W/wfw"; mkdir -p "$W/wfw"
git -C "$REPO" show HEAD:site/basilisk-31-browser/w31.jsdos > "$W/w31.jsdos"
python3 -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$W/w31.jsdos" "$W/wfw"
rm -rf "$W/wfw/.jsdos"
# the library disc (drive L:): packages/basilisk-synth/library/sources, converted for Sound Recorder 3.1
python3 "$PKG/tools/make_library311.py" "$W/library.zip"
# XP's sounds for C:\XPSOUNDS, from your own XP image (XP_IMAGE: BASILISK SYNTH's base.qcow2) through the sound-archaeology
# extractor (EXTRACTOR: packages/basilisk-synth/archaeology/extract.py)
python3 "$PKG/tools/xpsounds311.py" "${XP_IMAGE:?XP_IMAGE}" "$W/xpsounds" --extractor "${EXTRACTOR:?EXTRACTOR}"
sh "$PKG/../basilisk-synth/help/build.sh"   # the help: SNDWAVE.HLP
# the pack discs (drive P:, the Library tab): the packs lane's final set (PACKS_DIR, default its out/discs)
python3 "$PKG/tools/make_packs311.py" "${PACKS_DIR:-$PKG/../basilisk-synth/library/packs/out/discs}" "$W/packs"
# the brand kit (title screen, Program Manager icons); TITLE.BMP made here (the Mac may lack Pillow)
rm -rf "$W/brand"; cp -r "$REPO/design/brand/sndwave2000" "$W/brand"
python3 -c "from PIL import Image;import sys;Image.open(sys.argv[1]).convert('RGB').quantize(colors=16,dither=0).save(sys.argv[2])" "$W/brand/screens/title-640.png" "$W/brand/TITLE.BMP"
BS311_ENGINE="$W/engine" BS311_OFFS="$W/offs" python3 "$PKG/tools/make_machine.py" "$W/wfw" "$W/gout" "$W/dosbox-pure/dosbox_pure_libretro.so" "$W/machine" --library "$W/library.zip" --xpsounds "$W/xpsounds" --packs "$W/packs" --brand "$W/brand" --help "$PKG/../basilisk-synth/help/out/SNDWAVE.HLP"

# --- the Windows plugin (its program list: tools/make_presets311.py)
python3 "$PKG/tools/make_presets311.py"
python3 "$PKG/tools/make_tuning311.py"   # the Song tab's measured tuning (plugin/tuning_gen.h)
(cd "$PKG/plugin" && make DPF_PATH="$W/DPF" DPF_TARGET_DIR="$W/win" DPF_BUILD_DIR="$W/obj-win" WINDOWS=true \
  CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++ -j"$(nproc)" vst3 >/dev/null)
M="$W/win/SNDWAVE2000.vst3/Contents/Resources/machine"
rm -rf "$M"; mkdir -p "$M"
cp "$W/dbp-win/dosbox_pure_libretro.dll" "$W/machine/w31.conf" "$W/machine/w31.state" "$W/machine/drive.zip" "$M/"
cp "$W/machine/library.zip" "$W/machine/library.names.txt" "$M/"; cp -r "$W/machine/packs" "$M/"; cp -r "$W/machine/citypop" "$M/"   # (CITYPOP.EXE's album)

# --- inputs for the Mac build
rm -rf "$W/macsrc"; mkdir -p "$W/macsrc"
cp -r "$W/dosbox-pure" "$W/macsrc/dosbox-pure"; rm -rf "$W/macsrc/dosbox-pure/build" "$W/macsrc/dosbox-pure"/*.so "$W/macsrc/dosbox-pure/.git"
cp -r "$W/DPF" "$W/macsrc/DPF"; rm -rf "$W/macsrc/DPF/build" "$W/macsrc/DPF/.git"
cp -r "$PKG" "$W/macsrc/pkg"; cp -r "$PKG/../basilisk-synth/core" "$W/macsrc/core"
cp -r "$W/wfw" "$W/macsrc/wfw"; cp -r "$W/gout" "$W/macsrc/gout"; cp "$W/library.zip" "$W/library.names.txt" "$W/macsrc/"; cp -r "$W/xpsounds" "$W/macsrc/xpsounds"
cp -r "$W/packs" "$W/macsrc/packs"; cp -r "$W/brand" "$W/macsrc/brand"; cp "$PKG/../basilisk-synth/help/out/SNDWAVE.HLP" "$W/macsrc/"
cp -r "$PKG/../basilisk-synth/help/install" "$W/macsrc/helpinstall"
mkdir -p "$W/macsrc/machine"; cp "$W/machine/w31.conf" "$W/machine/w31.state" "$W/machine/drive.zip" "$W/machine/library.zip" "$W/machine/library.names.txt" "$W/macsrc/machine/"; cp -r "$W/machine/packs" "$W/machine/citypop" "$W/macsrc/machine/"   # the one snapshot
echo "built: $W/win (Windows), $W/macsrc (copy to a Mac, run pkg/tools/mac_build.sh there)"

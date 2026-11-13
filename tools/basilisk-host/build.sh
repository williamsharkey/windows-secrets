#!/bin/bash
# Build BasiliskHost.exe with mingw-w64 from Linux/WSL: one static executable, no DLLs beside it.
#   tools/basilisk-host/build.sh            (VST3SDK=path/to/vst3sdk, default ~/synth-build/vst3sdk;
#                                             fetched from GitHub at v3.8.1 when missing)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
S="${VST3SDK:-$HOME/synth-build/vst3sdk}"
B="${BUILD_DIR:-$HOME/.cache/basilisk-host-build}"
CXX="${CXX:-x86_64-w64-mingw32-g++-posix}"
WINDRES="${WINDRES:-x86_64-w64-mingw32-windres}"
if [ ! -f "$S/pluginterfaces/base/funknown.h" ]; then
    S="$B/vst3sdk"
    if [ ! -f "$S/pluginterfaces/base/funknown.h" ]; then
        mkdir -p "$B"
        git clone --depth 1 --branch v3.8.1 https://github.com/steinbergmedia/vst3sdk.git "$S"
        (cd "$S" && git submodule update --init --depth 1 base pluginterfaces public.sdk)
    fi
fi
mkdir -p "$B/obj"
SDK="public.sdk/source/vst/hosting/module.cpp public.sdk/source/vst/hosting/module_win32.cpp
 public.sdk/source/vst/hosting/hostclasses.cpp public.sdk/source/vst/hosting/plugprovider.cpp
 public.sdk/source/vst/hosting/processdata.cpp public.sdk/source/vst/hosting/eventlist.cpp
 public.sdk/source/vst/hosting/parameterchanges.cpp public.sdk/source/vst/hosting/connectionproxy.cpp
 public.sdk/source/vst/hosting/pluginterfacesupport.cpp public.sdk/source/vst/vstpresetfile.cpp
 public.sdk/source/common/memorystream.cpp public.sdk/source/vst/utility/stringconvert.cpp
 public.sdk/source/vst/vstinitiids.cpp public.sdk/source/common/commonstringconvert.cpp
 public.sdk/source/common/threadchecker_win32.cpp pluginterfaces/base/coreiids.cpp pluginterfaces/base/funknown.cpp
 pluginterfaces/base/ustring.cpp base/source/fobject.cpp base/source/fdebug.cpp base/source/updatehandler.cpp
 base/source/fstring.cpp base/source/fbuffer.cpp base/source/baseiids.cpp base/thread/source/flock.cpp"
FLAGS="-std=c++17 -O2 -DRELEASE=1 -DUNICODE -D_UNICODE -DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_USE_MATH_DEFINES -D_WIN32_WINNT=0x0A00 -I$S -I$HERE/src"
objs=()
pids=()
for f in $SDK; do
    o="$B/obj/sdk_$(basename "$f" .cpp).o"
    objs+=("$o")
    if [ ! -f "$o" ] || [ "$S/$f" -nt "$o" ]; then $CXX $FLAGS -w -c "$S/$f" -o "$o" & pids+=($!); fi
done
for f in "$HERE"/src/*.cpp; do
    o="$B/obj/$(basename "$f" .cpp).o"
    objs+=("$o")
    $CXX $FLAGS -Wall -Wno-unused-function -Wno-missing-braces -c "$f" -o "$o" & pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait $p || fail=1; done
[ $fail = 0 ] || { echo "compile failed"; exit 1; }
(cd "$HERE/res" && $WINDRES app.rc -O coff -o "$B/obj/app.res.o")
OUT="${OUT:-$HERE/BasiliskHost.exe}"
$CXX -o "$OUT" "${objs[@]}" "$B/obj/app.res.o" -static -mwindows -municode -s \
    -lole32 -luuid -lshell32 -lgdi32 -luser32 -lcomctl32 -lcomdlg32 -lwinmm -lavrt -loleaut32 -lpropsys
ls -la "$OUT"

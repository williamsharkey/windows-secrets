#!/bin/sh
# On a Mac: turn BASILISK-macos-<arch>.app.tar into BASILISK-macos-<arch>.dmg (stub compiled, ad-hoc signed).
#   mac_finish.sh BASILISK-XP-macos-arm64.app.tar basilisk-mac.c arm64
set -e
TAR="$1"; STUB="$2"; ARCH="$3"
W="$(mktemp -d)"
APP="BASILISK XP.app"
tar -xf "$TAR" -C "$W"
mkdir -p "$W/$APP/Contents/MacOS"
MIN=11.0; [ "$ARCH" = x86_64 ] && MIN=10.15
clang -O2 -arch "$ARCH" -mmacosx-version-min=$MIN "$STUB" -o "$W/$APP/Contents/MacOS/BASILISK"
xattr -cr "$W/$APP"
# sign inside-out: every Mach-O, then the app
find "$W/$APP/Contents/Resources" -type f \( -name '*.dylib' -o -name '*.so' -o -perm -u+x \) | while read f; do
  file "$f" | grep -q Mach-O && codesign -f -s - "$f" 2>/dev/null || true
done
codesign -f -s - --entitlements /dev/stdin "$W/$APP/Contents/Resources/qemu/bin/qemu-system-i386" <<'EOF' || true
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.hypervisor</key><true/></dict></plist>
EOF
codesign -f -s - "$W/$APP"
codesign -v "$W/$APP" && echo "signed (ad hoc)"
mkdir "$W/dmg"
mv "$W/$APP" "$W/dmg/"
ln -s /Applications "$W/dmg/Applications"
OUT="$(dirname "$TAR")/$(basename "$TAR" .app.tar).dmg"
rm -f "$OUT"
hdiutil create -volname "BASILISK XP" -srcfolder "$W/dmg" -ov -format UDZO -imagekey zlib-level=9 "$OUT" >/dev/null
rm -rf "$W"
ls -l "$OUT"

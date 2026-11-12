#!/usr/bin/env python3
"""Turn build.py's staged folders into what people download.

  python3 packages/basilisk-311/package.py [--out DIR] [--only windows-x64,macos-arm64,macos-x64,linux-x64]

  windows-x64  BASILISK-3.11-windows-x64.zip   a folder with "BASILISK 3.11.exe" (no console; adds a Start menu
                                               shortcut on first run)
  macos-*      BASILISK-3.11-macos-*.dmg       "BASILISK 3.11.app" (made, ad-hoc signed and imaged on a Mac over ssh:
                                               set BASILISK_MAC=<ssh host>; codesign and hdiutil only exist there)
  linux-x64    BASILISK-3.11-linux-x64.AppImage
"""
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402

ZIG = os.environ.get('ZIG', os.path.expanduser('~/b311build/zig/ziglang/zig'))
APPIMAGE_RUNTIME = 'https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64'
BUNDLE_ID = 'com.williamsharkey.basilisk311'


def zipdir(folder, zpath, top):
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, dirs, files in os.walk(folder):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(root, name)
                if os.path.islink(full):
                    continue
                arc = top + '/' + os.path.relpath(full, folder).replace(os.sep, '/')
                info = zipfile.ZipInfo(arc, date_time=(2026, 11, 12, 0, 0, 0))
                exe = bool(os.stat(full).st_mode & 0o111)
                info.external_attr = ((0o100755 if exe else 0o100644) << 16)
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(full, 'rb') as f:
                    z.writestr(info, f.read())


def windows(st, out):
    exe = os.path.join(st, 'BASILISK 3.11.exe')
    subprocess.run([ZIG, 'cc', '-target', 'x86_64-windows-gnu', '-municode', '-Os', '-Wl,--subsystem,windows',
                    os.path.join(HERE, 'win', 'launcher.c'), os.path.join(HERE, 'win', 'launcher.rc'), '-o', exe],
                   check=True, cwd=os.path.join(HERE, 'win'))
    for junk in ('BASILISK 3.11.pdb', 'BASILISK 3.11.lib'):
        if os.path.exists(os.path.join(st, junk)):
            os.remove(os.path.join(st, junk))
    shutil.copy(os.path.join(HERE, 'README.txt'), os.path.join(st, 'README.txt'))
    z = os.path.join(out, 'BASILISK-3.11-windows-x64.zip')
    zipdir(st, z, 'BASILISK 3.11')
    return z


def mac_app(st, target):
    """BASILISK 3.11.app: a launcher script (no Dock icon of its own) + the engine app, which is what you see"""
    app = os.path.join(os.path.dirname(st), 'mac-' + target, 'BASILISK 3.11.app')
    shutil.rmtree(os.path.dirname(app), ignore_errors=True)
    res = os.path.join(app, 'Contents', 'Resources')
    os.makedirs(os.path.join(app, 'Contents', 'MacOS'))
    shutil.copytree(st, res, symlinks=True)
    shutil.copy(os.path.join(HERE, 'assets', 'basilisk.icns'), os.path.join(res, 'basilisk.icns'))
    with open(os.path.join(app, 'Contents', 'MacOS', 'basilisk'), 'w') as f:
        f.write('#!/bin/sh\n# BASILISK 3.11: start the local server; it opens the window\n'
                'R="$(cd "$(dirname "$0")/../Resources" && pwd)"\n'
                'exec "$R/runtime/python/bin/python3.12" -I "$R/app/basilisk.py" "$@"\n')
    os.chmod(os.path.join(app, 'Contents', 'MacOS', 'basilisk'), 0o755)
    with open(os.path.join(app, 'Contents', 'Info.plist'), 'wb') as f:
        plistlib.dump({'CFBundleName': 'BASILISK 3.11', 'CFBundleDisplayName': 'BASILISK 3.11',
                       'CFBundleIdentifier': BUNDLE_ID, 'CFBundleVersion': build.VERSION,
                       'CFBundleShortVersionString': build.VERSION, 'CFBundlePackageType': 'APPL',
                       'CFBundleExecutable': 'basilisk', 'CFBundleIconFile': 'basilisk.icns',
                       'LSUIElement': True, 'LSMinimumSystemVersion': '11.0', 'NSHighResolutionCapable': True}, f)
    # the engine app is the one in the Dock: our name and icon
    eng = os.path.join(res, 'engine', 'BASILISK 3.11.app', 'Contents')
    pl = os.path.join(eng, 'Info.plist')
    with open(pl, 'rb') as f:
        info = plistlib.load(f)
    info.update({'CFBundleName': 'BASILISK 3.11', 'CFBundleDisplayName': 'BASILISK 3.11',
                 'CFBundleIdentifier': BUNDLE_ID + '.engine', 'CFBundleIconFile': 'basilisk.icns',
                 'CFBundleGetInfoString': 'BASILISK 3.11 (DOSBox-X 2026.10.01 engine)'})
    info.pop('CFBundleIconName', None)
    with open(pl, 'wb') as f:
        plistlib.dump(info, f)
    shutil.copy(os.path.join(HERE, 'assets', 'basilisk.icns'), os.path.join(eng, 'Resources', 'basilisk.icns'))
    shutil.copy(os.path.join(HERE, 'README.txt'), os.path.join(os.path.dirname(app), 'README.txt'))
    return app


def mac_dmg(app, target, out, host):
    """ad-hoc sign + hdiutil on the Mac (temp folder, removed after)"""
    folder = os.path.dirname(app)
    tgz = folder + '.tgz'
    with tarfile.open(tgz, 'w:gz') as t:
        t.add(folder, arcname='dmgroot')
    rdir = subprocess.run(['ssh', host, 'mktemp -d /tmp/b311pkg.XXXXXX'], capture_output=True, text=True, check=True).stdout.strip()
    name = 'BASILISK-3.11-%s.dmg' % target
    try:
        subprocess.run(['scp', '-q', tgz, '%s:%s/in.tgz' % (host, rdir)], check=True)
        script = ('cd %s && tar xzf in.tgz && cd dmgroot && '
                  'codesign --force --deep -s - "BASILISK 3.11.app/Contents/Resources/engine/BASILISK 3.11.app" && '
                  'codesign --force -s - "BASILISK 3.11.app" && '
                  'codesign --verify --deep "BASILISK 3.11.app/Contents/Resources/engine/BASILISK 3.11.app" && '
                  'ln -s /Applications Applications && cd .. && '
                  'hdiutil create -quiet -volname "BASILISK 3.11" -srcfolder dmgroot -ov -format UDZO %s' % (rdir, name))
        subprocess.run(['ssh', host, script], check=True)
        subprocess.run(['scp', '-q', '%s:%s/%s' % (host, rdir, name), os.path.join(out, name)], check=True)
    finally:
        subprocess.run(['ssh', host, 'rm -rf ' + rdir])
        os.remove(tgz)
    return os.path.join(out, name)


def linux(st, out, cache):
    appdir = os.path.join(os.path.dirname(st), 'BASILISK.AppDir')
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(st, os.path.join(appdir, 'usr', 'lib', 'basilisk-3.11'), symlinks=True)
    with open(os.path.join(appdir, 'AppRun'), 'w') as f:
        f.write('#!/bin/sh\nR="$(dirname "$(readlink -f "$0")")/usr/lib/basilisk-3.11"\n'
                'exec "$R/runtime/python/bin/python3.12" -I "$R/app/basilisk.py" "$@"\n')
    os.chmod(os.path.join(appdir, 'AppRun'), 0o755)
    with open(os.path.join(appdir, 'basilisk-3.11.desktop'), 'w') as f:
        f.write('[Desktop Entry]\nType=Application\nName=BASILISK 3.11\nComment=Claude Code on Windows for Workgroups 3.11\n'
                'Exec=AppRun\nIcon=basilisk-3.11\nCategories=Development;\nStartupWMClass=basilisk-3.11\nTerminal=false\n')
    shutil.copy(os.path.join(HERE, 'assets', 'basilisk.png'), os.path.join(appdir, 'basilisk-3.11.png'))
    shutil.copy(os.path.join(HERE, 'assets', 'basilisk.png'), os.path.join(appdir, '.DirIcon'))
    # an AppImage is the type-2 runtime followed by a squashfs of the AppDir
    runtime = build.fetch(APPIMAGE_RUNTIME, cache)
    img = os.path.join(os.path.dirname(st), 'basilisk.squashfs')
    if os.path.exists(img):
        os.remove(img)
    subprocess.run(['mksquashfs', appdir, img, '-root-owned', '-noappend', '-comp', 'zstd', '-quiet'], check=True,
                   stdout=subprocess.DEVNULL)
    dst = os.path.join(out, 'BASILISK-3.11-linux-x64.AppImage')
    with open(dst, 'wb') as f:
        f.write(open(runtime, 'rb').read())
        f.write(open(img, 'rb').read())
    os.chmod(dst, 0o755)
    os.remove(img)
    return dst


def main():
    args = sys.argv[1:]
    out = os.path.abspath(args[args.index('--out') + 1]) if '--out' in args else os.path.join(os.path.expanduser('~'), 'b311build')
    only = args[args.index('--only') + 1].split(',') if '--only' in args else list(build.TARGETS)
    dist = os.path.join(out, 'dist')
    os.makedirs(dist, exist_ok=True)
    for target in only:
        st = os.path.join(out, 'stage', target)
        if target.startswith('windows'):
            p = windows(st, dist)
        elif target.startswith('macos'):
            p = mac_dmg(mac_app(st, target), target, dist, os.environ.get('BASILISK_MAC', 'primary-mac'))
        else:
            p = linux(st, dist, os.path.join(out, 'cache'))
        print('%s  %.1f MB' % (p, os.path.getsize(p) / 1e6))


if __name__ == '__main__':
    main()

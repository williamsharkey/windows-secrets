#!/usr/bin/env python3
"""Assemble BASILISK for each OS.

    python3 tools/build_bundles.py BUILD_DIR [windows-x64 macos-arm64 macos-x86_64 linux-x64]

BUILD_DIR holds the inputs (see README.md, "Building"):
    py/cpython-3.12.*-<triple>-install_only.tar.gz    python-build-standalone
    wheels/{win,macarm,macx86,linux}/                 aiohttp anthropic certifi pygame-ce, per platform
    qemu-win64.zip, qemu-macos-{arm64,x86_64}.tar.gz, qemu-linux/   trimmed QEMU per OS
    BASILISK.exe                                      launcher/basilisk-win.c, built with mingw
    icons/                                            tools/make_icon.py
    machine.json                                      {"sha256", "xz_size", "size"} of the machine image
and writes BUILD_DIR/out/:
    BASILISK-windows-x64.zip                          unzip, run BASILISK.exe
    BASILISK-macos-<arch>.app.tar                     finished on a Mac by tools/mac_finish.sh (.dmg)
    BASILISK-linux-x64.AppDir/                        made into an AppImage by appimagetool
"""
import glob
import io
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import zipfile

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = {
    'windows-x64': ('x86_64-pc-windows-msvc', 'win', 'qemu-win64.zip'),
    'macos-arm64': ('aarch64-apple-darwin', 'macarm', 'qemu-macos-arm64.tar.gz'),
    'macos-x86_64': ('x86_64-apple-darwin', 'macx86', 'qemu-macos-x86_64.tar.gz'),
    'linux-x64': ('x86_64-unknown-linux-gnu', 'linux', 'qemu-linux'),
}
APP_FILES = ['basilisk.py', 'ui.py', 'machine.py', 'vnc.py', 'server_local.py', 'relay.py', 'icon.png',
             'fonts/Inter-Regular.ttf', 'fonts/Inter-SemiBold.ttf', 'fonts/OFL-Inter.txt']
SKIP_PY = ('/test/', '/tests/', '/idlelib/', '/tkinter/', '/turtledemo/', '/__pycache__/', '/ensurepip/',
           '/lib2to3/', '/pydoc_data/', '/tcl', '/tk8', '/Tix', '/include/', '/share/man/', '/pip/',
           '/_tkinter', 'tcl86', 'tk86')
SKIP_SITE = ('/__pycache__/', '/pygame/examples/', '/pygame/docs/', '/pygame/tests/', '/pygame/__pyinstaller')


class Entry:
    def __init__(self, name, data=None, mode=0o644, link=None):
        self.name, self.data, self.mode, self.link = name, data, mode, link


def from_tar(path, prefix, strip, skip=()):
    out = []
    with tarfile.open(path) as t:
        for m in t.getmembers():
            if not m.name.startswith(strip):
                continue
            rel = m.name[len(strip):].lstrip('/')
            if not rel or m.isdir() or any(s in '/' + rel for s in skip):
                continue
            if m.issym():
                out.append(Entry(prefix + rel, link=m.linkname, mode=0o777))
            elif m.isfile():
                out.append(Entry(prefix + rel, t.extractfile(m).read(), (m.mode & 0o777) or 0o644))
    return out


def from_zip(path, prefix, strip):
    out = []
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            if i.is_dir() or not i.filename.startswith(strip):
                continue
            out.append(Entry(prefix + i.filename[len(strip):], z.read(i),
                             0o755 if i.filename.endswith(('.exe', '.dll')) else 0o644))
    return out


def from_dir(path, prefix, skip=()):
    out = []
    for root, dirs, files in os.walk(path):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, path).replace(os.sep, '/')
            if any(s in '/' + rel for s in skip):
                continue
            if os.path.islink(p):
                out.append(Entry(prefix + rel, link=os.readlink(p), mode=0o777))
                continue
            with open(p, 'rb') as fh:
                out.append(Entry(prefix + rel, fh.read(), 0o755 if os.access(p, os.X_OK) else 0o644))
    return out


def write_zip(path, entries):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for e in entries:
            zi = zipfile.ZipInfo(e.name, (2026, 11, 12, 0, 0, 0))
            zi.create_system = 3
            if e.link is not None:
                zi.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(zi, e.link, zipfile.ZIP_STORED)
            else:
                zi.external_attr = (stat.S_IFREG | e.mode) << 16
                z.writestr(zi, e.data, zipfile.ZIP_DEFLATED)


def write_tar(path, entries):
    with tarfile.open(path, 'w') as t:
        for e in entries:
            ti = tarfile.TarInfo(e.name)
            ti.mtime = 1794441600
            if e.link is not None:
                ti.type, ti.linkname, ti.mode = tarfile.SYMTYPE, e.link, 0o777
                t.addfile(ti)
            else:
                ti.size, ti.mode = len(e.data), e.mode
                t.addfile(ti, io.BytesIO(e.data))


def write_dir(path, entries):
    if os.path.exists(path):
        shutil.rmtree(path)
    for e in entries:
        p = os.path.join(path, e.name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if e.link is not None:
            os.symlink(e.link, p)
        else:
            with open(p, 'wb') as f:
                f.write(e.data)
            os.chmod(p, e.mode)


def app_entries(prefix, machine):
    out = []
    for a in APP_FILES:
        with open(os.path.join(PKG, 'app', a), 'rb') as f:
            data = f.read()
        if a == 'basilisk.py' and machine:
            s = data.decode()
            s = re.sub(r"MACHINE_SHA256 = ''", "MACHINE_SHA256 = '%s'" % machine['sha256'], s)
            s = re.sub(r"MACHINE_XZ_SIZE = 0", "MACHINE_XZ_SIZE = %d" % machine['xz_size'], s)
            s = re.sub(r"MACHINE_SIZE = 0", "MACHINE_SIZE = %d" % machine['size'], s)
            data = s.encode()
        out.append(Entry(prefix + 'app/' + a, data))
    return out


INFO_PLIST = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>BASILISK XP</string>
  <key>CFBundleDisplayName</key><string>BASILISK XP</string>
  <key>CFBundleIdentifier</key><string>com.williamsharkey.basilisk-xp</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>BASILISK</string>
  <key>CFBundleIconFile</key><string>basilisk</string>
  <key>LSMinimumSystemVersion</key><string>%s</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.developer-tools</string>
  <key>NSHumanReadableCopyright</key><string>BASILISK by William Sharkey. Windows XP is Microsoft's. QEMU is GPL v2.</string>
</dict>
</plist>
'''

DESKTOP = '''[Desktop Entry]
Type=Application
Name=BASILISK XP
Comment=Claude Code in Windows XP
Exec=BASILISK
Icon=basilisk
Categories=Development;
StartupWMClass=basilisk-xp
Terminal=false
'''

APPRUN = '''#!/bin/sh
D="$(dirname "$(readlink -f "$0")")"
export BASILISK_BUNDLE="$D" PYTHONPATH="$D/runtime/site:$D/app" PYTHONNOUSERSITE=1
exec "$D/runtime/python/bin/python3" "$D/app/basilisk.py" "$@"
'''


def main():
    build = sys.argv[1]
    only = sys.argv[2:]
    out = os.path.join(build, 'out')
    os.makedirs(out, exist_ok=True)
    machine = None
    mj = os.path.join(build, 'machine.json')
    if os.path.exists(mj):
        with open(mj) as f:
            machine = json.load(f)
    with open(os.path.join(PKG, 'README.md'), 'rb') as f:
        readme = f.read()
    for name, (triple, wheels, qemu) in TARGETS.items():
        if only and name not in only:
            continue
        if name.startswith('windows'):
            top = 'BASILISK XP/'
        elif name.startswith('macos'):
            top = 'BASILISK XP.app/Contents/Resources/'
        else:
            top = ''
        e = app_entries(top, machine)
        e += from_dir(os.path.join(build, 'qemu-linux', 'share'), top + 'app/firmware/')
        py = glob.glob(os.path.join(build, 'py', 'cpython-3.12.*-%s-install_only.tar.gz' % triple))[0]
        e += from_tar(py, top + 'runtime/python/', 'python', SKIP_PY)
        e += from_dir(os.path.join(build, 'wheels', wheels), top + 'runtime/site/', SKIP_SITE)
        q = os.path.join(build, qemu)
        if q.endswith('.zip'):
            e += from_zip(q, top + 'qemu/', 'qemu/')
        elif q.endswith('.tar.gz'):
            e += from_tar(q, top + 'qemu/', 'qemu')
        else:
            e += from_dir(q, top + 'qemu/')
        if name.startswith('windows'):
            with open(os.path.join(build, 'BASILISK.exe'), 'rb') as f:
                e.append(Entry(top + 'BASILISK XP.exe', f.read(), 0o755))
            e.append(Entry(top + 'README.txt', readme.replace(b'\n', b'\r\n')))
            path = os.path.join(out, 'BASILISK-XP-windows-x64.zip')
            write_zip(path, e)
        elif name.startswith('macos'):
            c = 'BASILISK XP.app/Contents/'
            e.append(Entry(c + 'Info.plist', (INFO_PLIST % ('11.0' if 'arm' in name else '10.15')).encode()))
            with open(os.path.join(build, 'icons', 'basilisk.icns'), 'rb') as f:
                e.append(Entry(c + 'Resources/basilisk.icns', f.read()))
            e.append(Entry(c + 'Resources/README.txt', readme))
            path = os.path.join(out, 'BASILISK-XP-%s.app.tar' % name)
            write_tar(path, e)
        else:
            e.append(Entry('AppRun', APPRUN.encode(), 0o755))
            e.append(Entry('basilisk.desktop', DESKTOP.encode()))
            with open(os.path.join(build, 'icons', 'icon-256.png'), 'rb') as f:
                e.append(Entry('basilisk.png', f.read()))
            e.append(Entry('README.txt', readme))
            path = os.path.join(out, 'BASILISK-XP-linux-x64.AppDir')
            write_dir(path, e)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        print('%-62s %6.1f MB  %d files' % (path, size / 2 ** 20, len(e)))


if __name__ == '__main__':
    main()

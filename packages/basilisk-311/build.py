#!/usr/bin/env python3
"""Build BASILISK 3.11, local edition (native: DOSBox-X runs Windows for Workgroups 3.11 in its own window).

  python3 packages/basilisk-311/build.py [--out DIR] [--only windows-x64,macos-arm64,macos-x64,linux-x64] [--stage-only]

Stages one folder per target (then build-*.sh / package steps turn them into the .zip / .dmg / .AppImage):
  app/basilisk.py, app/w31_server.py, app/lib/   the local Claude/tool server (+ anthropic, aiohttp)
  drive/                                         Windows for Workgroups 3.11's C: (with Open Watcom)
  engine/                                        DOSBox-X: an official build, with the window title and app name
                                                 changed to BASILISK (byte patches listed in engine/SOURCE.txt)
  runtime/python/                                relocatable CPython (python-build-standalone)

Sources: puppetry/w31/server.py and basilisk.c from the last commit, patched here (each patch asserts its anchor, so
an upstream change stops the build instead of shipping something half-patched); the WfW tree and Open Watcom from
site/basilisk-31-browser/w31.jsdos (last commit); B3BOOT.EXE + B3.TRM (the COM-port build of puppetry/w31) from
drive-b3/. DOSBox-X: the 2026.10.01 release zips for Windows and macOS; for Linux the dosbox-x snap (2026.08.31,
core22) with the libraries it needs that a desktop may lack (GL, X11, Wayland and audio come from the host).
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
VERSION = '1.0.0'
PBS_TAG, PY = '20261110', '3.12.16'
PBS = 'https://github.com/astral-sh/python-build-standalone/releases/download/%s/cpython-%s+%s-%%s-install_only_stripped.tar.gz' % (PBS_TAG, PY, PBS_TAG)
DBX_TAG = 'dosbox-x-v2026.10.01'
DBX = 'https://github.com/joncampbell123/dosbox-x/releases/download/%s/%%s' % DBX_TAG
TARGETS = {   # name -> (python-build-standalone triple, pip platform tags, DOSBox-X source)
    'windows-x64': ('x86_64-pc-windows-msvc', ['win_amd64'], 'dosbox-x-vsbuild-win64-2026.10.01-portable.zip'),
    'macos-arm64': ('aarch64-apple-darwin', ['macosx_11_0_arm64', 'macosx_10_9_universal2', 'macosx_10_13_universal2', 'macosx_11_0_universal2'],
                    'dosbox-x-macosx-arm64-2026.10.01.zip'),
    'macos-x64': ('x86_64-apple-darwin', ['macosx_10_9_x86_64', 'macosx_10_12_x86_64', 'macosx_10_13_x86_64', 'macosx_11_0_x86_64',
                                          'macosx_10_9_universal2', 'macosx_10_13_universal2'], 'dosbox-x-macosx-x86_64-2026.10.01.zip'),
    'linux-x64': ('x86_64-unknown-linux-gnu', ['manylinux2014_x86_64', 'manylinux_2_17_x86_64', 'manylinux_2_28_x86_64'], 'snap'),
}
DEPS = ['anthropic', 'aiohttp']
PRUNE = {'test', 'tests', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip', 'lib2to3', '__pycache__', 'Tools', 'include', 'share'}
HOST_LIBS = r'^(libGL|libGLX|libGLdispatch|libEGL|libdrm|libgbm|libwayland|libva|libvdpau|libOpenCL|libasound|libpulse|libjack|libX11\.|libX11-xcb|libxcb|libXau|libXdmcp|libdecor|libxkbcommon)'
CORE22_DEBS = ['http://archive.ubuntu.com/ubuntu/pool/main/n/ncurses/libncurses6_6.3-2ubuntu0.3_amd64.deb',
               'http://archive.ubuntu.com/ubuntu/pool/main/n/ncurses/libtinfo6_6.3-2ubuntu0.3_amd64.deb',
               'http://archive.ubuntu.com/ubuntu/pool/main/libu/libunistring/libunistring2_1.0-1_amd64.deb']
# DOSBox-X always appends its own name to the window title ("<title> - DOSBox-X"); these two same-length byte
# patches make the title just the configured one ("BASILISK 3.11"). The second "%s%s%s" is physfs's path join,
# which this program never uses (no zip mounts).
TITLE_PATCHES = [(b'%s%s%s\x00', b'%s\x00\x00\x00\x00\x00', 2)]


def git(path):
    return subprocess.run(['git', '-C', REPO, 'show', 'HEAD:' + path], check=True, capture_output=True).stdout


def sub(text, old, new, count=1):
    n = text.count(old)
    if n != count:
        sys.exit('build: patch anchor found %d times (wanted %d): %r' % (n, count, old[:90]))
    return text.replace(old, new)


def bpatch(data, what):
    for old, new, count in TITLE_PATCHES:
        assert len(old) == len(new)
        n = data.count(old)
        if n != count:
            sys.exit('build: %s: byte patch found %d times (wanted %d)' % (what, n, count))
        data = data.replace(old, new)
    return data


# ---------------------------------------------------------------- the server: same code, local switches
def patch_server(s):
    s = sub(s, "ROOT = '/root/w31'", "ROOT = os.environ.get('W31_ROOT', '/root/w31')")
    s = sub(s, "for path in ('/root/stage/.env', os.path.join(ROOT, '.env')):", "for path in (os.path.join(ROOT, '.env'),):")
    s = sub(s, "PRICES = {", "EXTRA = lambda model: {}      # local edition: per-model request extras (refusal fallbacks)\nPRICES = {")
    s = sub(s, "model=cfg('W31_MODEL'), max_tokens=4000,", "model=cfg('W31_MODEL'), max_tokens=16000,")
    s = sub(s, "output_config={'effort': cfg('W31_EFFORT')}) as st:",
            "output_config={'effort': cfg('W31_EFFORT')}, **EXTRA(cfg('W31_MODEL'))) as st:")
    s = sub(s, "t.para('Something went wrong on the line (%s). Try again.' % type(e).__name__, BUL + ' ')",
            "t.para('Something went wrong on the line (%s: %s). Try again.' % (type(e).__name__, str(e)[:300]), BUL + ' ')")
    s = sub(s, "            t.para('The line to Claude is quiet for the rest of the month (its budget is spent). '\n"
               "                   'The machine still works; come back next month to talk.', BUL + ' ')",
            "            t.para('BASILISK is not signed in to Claude yet. Copy your Anthropic API key (console.anthropic.com, '\n"
            "                   'API keys), then type /login. Or run ant auth login on your computer and type /login.', BUL + ' ')")
    s = sub(s, "'cost    $%.5f  (see Calculator)' % u['usd'],", "'cost    $%.5f  (your account)' % u['usd'],")
    s = sub(s, "lines = ['model   %s' % cfg('W31_MODEL'),", "lines = ['model   %s (%s)' % (cfg('W31_MODEL'), cfg('W31_EFFORT')),")
    s = sub(s, "- The machine is reset for every visitor, so nothing you do persists.",
            "- This copy runs on the person's own computer. C:\\\\B3\\\\WORK is kept between runs. Drive D: is a folder on \\\n"
            "their real computer (shared both ways): save things there when they want to keep or open them outside.")
    return s


# ---------------------------------------------------------------- BASILISK.C: keys from the keyboard you have
KEYPROC = r"""
/* ---------------------------------------------------------------- local edition: the input line */
/* An edit line of our own under Terminal's pane: you type there (our task, our message loop);
   Enter sends the line to the host on COM2 ('U'), Esc interrupts, Up/Down ask the host for history,
   PgUp/PgDn scroll the transcript. The host answers 'T' (put this text in the line). */
FARPROC oldEditProc, editThunk;
HFONT hFixed;

long FAR PASCAL __export EditProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_KEYDOWN) {
        switch (w) {
        case VK_RETURN: {
            static char line[1024];
            GetWindowText(h, line, sizeof line);
            Send('U', line, NULL, NULL);
            SetWindowText(h, "");
            return 0; }
        case VK_ESCAPE: Send('K', "c27", NULL, NULL); return 0;
        case VK_UP: Send('K', "Up", NULL, NULL); return 0;
        case VK_DOWN: Send('K', "Down", NULL, NULL); return 0;
        case VK_PRIOR: SendMessage(hText, WM_VSCROLL, SB_PAGEUP, 0L); return 0;
        case VK_NEXT: SendMessage(hText, WM_VSCROLL, SB_PAGEDOWN, 0L); return 0;
        }
    }
    if (m == WM_CHAR && (w == 13 || w == 27 || w == 9)) return 0;     /* no beeps */
    return CallWindowProc(oldEditProc, h, m, w, l);
}

void InputLine(void)
{
    if (hEdit) return;
    hEdit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL,
                         0, ClientH - EDITH, TextW, EDITH, hTerm, (HMENU)777, hInst, NULL);
    hFixed = GetStockObject(SYSTEM_FIXED_FONT);
    SendMessage(hEdit, WM_SETFONT, (WPARAM)hFixed, 0L);
    SendMessage(hEdit, EM_LIMITTEXT, 1000, 0L);
    editThunk = MakeProcInstance((FARPROC)EditProc, hInst);
    oldEditProc = (FARPROC)GetWindowLong(hEdit, GWL_WNDPROC);
    SetWindowLong(hEdit, GWL_WNDPROC, (LONG)editThunk);
    SetFocus(hEdit);
}

void HideProgman(void)
{
    HWND pm = FindWindow("Progman", NULL);
    if (pm) ShowWindow(pm, SW_HIDE);
}

"""


def patch_basilisk(s):
    s = s.replace('\r\n', '\n')
    s = sub(s, "long FAR PASCAL __export HostProc(HWND h, UINT m, WPARAM w, LPARAM l)\n",
            KEYPROC + "long FAR PASCAL __export HostProc(HWND h, UINT m, WPARAM w, LPARAM l)\n")
    s = sub(s, "        RunCheck();\n",
            "        RunCheck();\n"
            "        if (hEdit && GetActiveWindow() == hTerm && GetFocus() != hEdit) SetFocus(hEdit);   /* typing goes to the input line */\n")
    s = sub(s, "    Send('H', \"basilisk\", NULL, NULL);\n\n    Assemble();\n",
            "    Send('H', \"basilisk\", NULL, NULL);\n\n    HideProgman();\n    Assemble();\n    HideProgman();\n    InputLine();\n")
    s = sub(s, " *  wcl -q -bt=windows -l=windows -ml basilisk.c\n",
            " *  wcl -q -bt=windows -l=windows -ml basilisk.c\n *\n"
            " *  (local edition: packages/basilisk-311/build.py adds the keyboard link, KeyProc below)\n")
    s = sub(s, "    MoveWindow(hText, 0, 0, TextW, ClientH, TRUE);\n",
            "    MoveWindow(hText, 0, 0, TextW, ClientH - EDITH, TRUE);\n"
            "    if (hEdit) MoveWindow(hEdit, 0, ClientH - EDITH, TextW, EDITH, TRUE);\n")
    s = sub(s, "    case 'W': if (b && c) Write(a, b, c); break;           /* id, path, text */\n",
            "    case 'W': if (b && c) Write(a, b, c); break;           /* id, path, text */\n"
            "    case 'T': if (hEdit) { SetWindowText(hEdit, p); SendMessage(hEdit, EM_SETSEL, 0, MAKELPARAM(32767, 32767)); } break;\n")
    # declarations the moved Layout needs come before it
    s = sub(s, "#define CARDH 224", "#define EDITH 24\nHWND hEdit;\n#define CARDH 224")
    # a quicker assembly (the pauses were sized for a busy shared server)
    s = sub(s, "    Pump(300);\n    Layout();\n", "    Pump(120);\n    Layout();\n")
    s = sub(s, "    Pump(200);\n    SetMenu(hClock, NULL);\n", "    Pump(80);\n    SetMenu(hClock, NULL);\n")
    s = sub(s, "    Pump(250);\n    Type(Kid(d, \"Edit\"), text);\n", "    Pump(80);\n    Type(Kid(d, \"Edit\"), text);\n")
    s = sub(s, "MAKELPARAM(GetDlgItem(d, IDOK), BN_CLICKED)); Pump(300); }", "MAKELPARAM(GetDlgItem(d, IDOK), BN_CLICKED)); Pump(120); }")
    return s.replace('\n', '\r\n')


def fetch(url, cache):
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, url.rsplit('/', 1)[1].replace('%2B', '+'))
    if not os.path.exists(path):
        print('  fetching', url)
        with urllib.request.urlopen(url, timeout=600) as r, open(path + '.part', 'wb') as f:
            shutil.copyfileobj(r, f)
        os.replace(path + '.part', path)
    return path


def wheels(target, tags, dest, cache):
    lib = os.path.join(cache, 'lib-' + target)
    if not os.path.isdir(lib):
        cmd = [sys.executable, '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '--target', lib + '.part',
               '--python-version', '3.12', '--implementation', 'cp', '--abi', 'cp312', '--only-binary=:all:']
        for t in tags:
            cmd += ['--platform', t]
        shutil.rmtree(lib + '.part', ignore_errors=True)
        subprocess.run(cmd + DEPS, check=True)
        os.replace(lib + '.part', lib)
    shutil.copytree(lib, dest, ignore=shutil.ignore_patterns('__pycache__', 'bin'))      # dist-info stays (metadata, licences)


def runtime(triple, dest, cache):
    tgz = fetch(PBS % triple, cache)
    with tarfile.open(tgz) as t:
        t.extractall(dest, filter='data')
    py = os.path.join(dest, 'python')
    exe = os.path.join(py, 'bin', 'python3.12')
    static = os.path.exists(exe) and b'libpython3' not in open(exe, 'rb').read()
    for root, dirs, files in os.walk(py):
        for f in files:
            low = f.lower()
            if (low.startswith(('libtcl', 'libtk', 'tcl8', 'tk8', 'tcl9', 'tk9', '_tkinter', 'python3.12-config', 'python3-config'))
                    or (static and low.startswith('libpython'))
                    or (os.path.basename(root) == 'bin' and f not in ('python3.12', 'python3'))):
                os.remove(os.path.join(root, f))
        for d in list(dirs):
            if d in ('site-packages', 'pydoc_data', 'pkgconfig') or d.startswith(('tcl', 'tk', 'itcl', 'thread', 'config-3')) or d in PRUNE:
                shutil.rmtree(os.path.join(root, d))
                dirs.remove(d)


def deb_extract(deb, dest):
    data = open(deb, 'rb').read()
    assert data[:8] == b'!<arch>\n'
    i = 8
    while i < len(data):
        h = data[i:i + 60]
        name, size = h[:16].decode().strip().rstrip('/'), int(h[48:58])
        body = data[i + 60:i + 60 + size]
        i += 60 + size + (size % 2)
        if name.startswith('data.tar'):
            if name.endswith('.zst'):
                import zstandard
                body = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(body)).read()
            tarfile.open(fileobj=io.BytesIO(body), mode='r:*').extractall(dest, filter='data')


def linux_engine(dest, cache):
    snapfile = os.path.join(cache, 'dosbox-x.snap')
    if not os.path.exists(snapfile):
        sys.exit('build: put the dosbox-x snap (amd64, core22) at %s' % snapfile)
    sq = os.path.join(cache, 'snap-x')
    if not os.path.isdir(sq):
        subprocess.run(['unsquashfs', '-q', '-d', sq, snapfile], check=True, stdout=subprocess.DEVNULL)
    core = os.path.join(cache, 'core22-libs')
    if not os.path.isdir(core):
        for u in CORE22_DEBS:
            deb_extract(fetch(u, cache), core)
    dirs = sorted({r for base in (sq, core) for r, _, fs in os.walk(base) if any('.so' in f for f in fs)})
    binary = os.path.join(sq, 'usr', 'bin', 'dosbox-x')
    out = subprocess.run(['ldd', binary], capture_output=True, text=True, env=dict(os.environ, LD_LIBRARY_PATH=':'.join(dirs))).stdout
    if 'not found' in out:
        sys.exit('build: dosbox-x has unresolved libraries:\n' + out)
    os.makedirs(os.path.join(dest, 'lib'))
    with open(os.path.join(dest, 'basilisk-engine'), 'wb') as f:
        f.write(bpatch(open(binary, 'rb').read(), 'linux engine'))
    os.chmod(os.path.join(dest, 'basilisk-engine'), 0o755)
    for line in out.splitlines():
        m = re.match(r'\s*(\S+) => (/\S+)', line)
        if m and (m.group(2).startswith(sq) or m.group(2).startswith(core)) and not re.match(HOST_LIBS, m.group(1)):
            shutil.copy(os.path.realpath(m.group(2)), os.path.join(dest, 'lib', m.group(1)))
    with open(os.path.join(dest, 'COPYING.txt'), 'wb') as f:      # GPLv2, as in every DOSBox-X release
        f.write(zipfile.ZipFile(fetch(DBX % TARGETS['macos-x64'][2], cache)).read('dosbox-x-sdl2/COPYING.txt'))
    with open(os.path.join(dest, 'SOURCE.txt'), 'w') as f:
        f.write('basilisk-engine is DOSBox-X 2026.08.31 from the dosbox-x snap (revision 1598, base core22).\n'
                'Changes: the window-title format string "%s%s%s" is byte-patched to "%s" (twice; the second copy is\n'
                'physfs\'s path join, unused here), so the title is only BASILISK 3.11. Nothing else is changed.\n'
                'DOSBox-X source: https://github.com/joncampbell123/dosbox-x/releases/tag/dosbox-x-v2026.08.31\n'
                'Snap recipe: https://github.com/snapcrafters/dosbox-x\n'
                'lib/ holds Ubuntu 22.04 libraries as shipped in that snap (sources: https://launchpad.net/ubuntu/jammy).\n')


def engine(target, src, dest, cache):
    if src == 'snap':
        return linux_engine(dest, cache)
    z = zipfile.ZipFile(fetch(DBX % src, cache))
    os.makedirs(dest)
    if target.startswith('windows'):
        pre = 'bin/x64/Release SDL2/'
        with open(os.path.join(dest, 'basilisk-engine.exe'), 'wb') as f:
            f.write(bpatch(z.read(pre + 'dosbox-x.exe'), 'windows engine'))
        with open(os.path.join(dest, 'inpoutx64.dll'), 'wb') as f:
            f.write(z.read(pre + 'inpoutx64.dll'))
        with open(os.path.join(dest, 'COPYING.txt'), 'wb') as f:
            f.write(z.read('COPYING'))
    else:
        pre = 'dosbox-x-sdl2/dosbox-x.app/'
        skip = ('SarasaGothicFixed.ttf', 'wqy_11pt.bdf', 'wqy_12pt.bdf', '/_CodeSignature/CodeResources')
        app = os.path.join(dest, 'BASILISK 3.11.app')
        for i in z.infolist():
            if not i.filename.startswith(pre) or i.is_dir() or i.filename.endswith(skip):
                continue
            p = os.path.join(app, i.filename[len(pre):])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            data = z.read(i)
            if i.filename.endswith('Contents/MacOS/dosbox-x'):
                data = bpatch(data, 'mac engine')
            with open(p, 'wb') as f:
                f.write(data)
            mode = (i.external_attr >> 16) & 0o777
            os.chmod(p, mode or (0o755 if '/Contents/MacOS/' in i.filename else 0o644))
        with open(os.path.join(dest, 'COPYING.txt'), 'wb') as f:
            f.write(z.read('dosbox-x-sdl2/COPYING.txt'))
    with open(os.path.join(dest, 'SOURCE.txt'), 'w') as f:
        f.write('The engine is DOSBox-X 2026.10.01, the official build (%s).\n'
                'Changes: the window-title format string "%%s%%s%%s" is byte-patched to "%%s" (twice; the second copy is\n'
                'physfs\'s path join, unused here), so the title is only BASILISK 3.11; on macOS the app bundle\'s name and\n'
                'icon are ours and it is re-signed (ad hoc). Nothing else is changed.\n'
                'Source: https://github.com/joncampbell123/dosbox-x/releases/tag/%s\n' % (src, DBX_TAG))


def drive(dest):
    """C: = the WfW 3.11 tree with Open Watcom (from the browser bundle) + the COM-port BASILISK build"""
    z = zipfile.ZipFile(io.BytesIO(git('site/basilisk-31-browser/w31.jsdos')))
    for i in z.infolist():
        n = i.filename
        if n.startswith('.jsdos/') or n.upper().startswith('B3/') or i.is_dir():
            continue
        p = os.path.join(dest, *n.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(z.read(i))
    b3 = os.path.join(dest, 'B3')
    os.makedirs(os.path.join(b3, 'WORK'))
    for f in os.listdir(os.path.join(HERE, 'drive-b3')):
        shutil.copy(os.path.join(HERE, 'drive-b3', f), b3)
    src = patch_basilisk(git('puppetry/w31/basilisk.c').decode('latin-1'))
    import hashlib
    with open(os.path.join(dest, '.stamp'), 'w') as f:      # the launcher re-copies C: only when this changes
        f.write('%s %s' % (VERSION, hashlib.md5(git('site/basilisk-31-browser/w31.jsdos') + src.encode('latin-1')).hexdigest()))
    with open(os.path.join(b3, 'BASILISK.SRC'), 'wb') as f:
        f.write(src.encode('latin-1'))


def stage(target, out, cache, server, golden):
    triple, tags, dsrc = TARGETS[target]
    st = os.path.join(out, 'stage', target)
    shutil.rmtree(st, ignore_errors=True)
    app = os.path.join(st, 'app')
    os.makedirs(app)
    print(target)
    runtime(triple, os.path.join(st, 'runtime'), cache)
    wheels(target, tags, os.path.join(app, 'lib'), cache)
    engine(target, dsrc, os.path.join(st, 'engine'), cache)
    shutil.copytree(golden, os.path.join(st, 'drive'))
    shutil.copy(os.path.join(HERE, 'app', 'basilisk.py'), app)
    with open(os.path.join(app, 'w31_server.py'), 'w') as f:
        f.write(server)
    with open(os.path.join(app, 'VERSION'), 'w') as f:
        f.write(VERSION)
    for a in os.listdir(os.path.join(HERE, 'assets')):
        shutil.copy(os.path.join(HERE, 'assets', a), app)
    return st


def main():
    args = sys.argv[1:]
    out = os.path.abspath(args[args.index('--out') + 1]) if '--out' in args else os.path.join(os.path.expanduser('~'), 'b311build')
    only = args[args.index('--only') + 1].split(',') if '--only' in args else list(TARGETS)
    cache = os.path.join(out, 'cache')
    server = patch_server(git('puppetry/w31/server.py').decode('utf-8'))
    compile(server, 'w31_server.py', 'exec')
    compile(open(os.path.join(HERE, 'app', 'basilisk.py')).read(), 'basilisk.py', 'exec')
    golden = os.path.join(out, 'drive')
    shutil.rmtree(golden, ignore_errors=True)
    drive(golden)
    for target in only:
        stage(target, out, cache, server, golden)


if __name__ == '__main__':
    main()

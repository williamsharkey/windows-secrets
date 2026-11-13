#!/usr/bin/env python3
"""First-use installer for the bring-your-own-image builds: the person's own Windows media in, a machine out.

    install.py 311 MEDIA OUT [--work DIR] [--tools DIR]
    install.py xp  MEDIA OUT --key-file FILE [--work DIR] [--tools DIR] [--qemu-linux DIR]

MEDIA is a local file or an https URL on the allowlist (archive.org, microsoft.com). OUT receives the same files the
shipped build carries, so the plugin resumes it exactly like a downloaded machine:

    (OUT is emptied first; the scratch folder is OUT.work and a download is kept in OUT.media)
    311: OUT/drive.zip, OUT/w31.state, OUT/w31.conf     (packages/basilisk-synth-311/tools/make_machine.py)
    xp:  OUT/base.qcow2, OUT/state.mig, OUT/fw/          (packages/basilisk-synth/tools/make_machine.py)

Progress goes to stdout, one JSON object per line, for the plugin's editor (see DESIGN.md):

    {"stage": "install", "pct": 41, "msg": "Windows Setup is copying files"}
    {"stage": "error", "code": "media-unknown", "msg": "..."}             (then exit status 2)
    {"stage": "done", "pct": 100, "out": "...", "machine": {...}}

Stages, in order: fetch, identify, prepare, install, guest, snapshot, done. Nothing here changes the person's media;
the work folder is deleted at the end (pass --keep to keep it). No product key is printed or logged.

Tools (--tools DIR, default $BYO_TOOLS): what the plugin already carries for the shipped machine.
    311: engine, offs (the engine test process and its offsets helper, built by basilisk-synth-311/tools/build.sh),
         dosbox_pure_libretro.so (the BSYN core) and SYNTH.EXE, SYNHOOK.DLL, BSYNTH.DRV (the guest build).
    xp:  xp/SYNTH.EXE and xp/SRHOOK.DLL (built in XP with tcc for the shipped machine), and the QEMU 6.2 for
         Linux (--qemu-linux) that packages/basilisk-synth/tools/make_machine.py uses.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
PKG311 = os.path.join(os.path.dirname(PKG), 'basilisk-synth-311')
sys.path.insert(0, HERE)
import answers   # noqa: E402
import floppy    # noqa: E402
import media_id  # noqa: E402

UA = 'basilisk-byo-install/0.1'
ALLOW = ('archive.org', 'microsoft.com')     # the host or any subdomain (iaNNNNNN.us.archive.org, download.microsoft.com)


class Fail(Exception):
    def __init__(self, code, msg):
        Exception.__init__(self, msg)
        self.code = code


def emit(stage, pct=None, msg='', **kw):
    d = {'stage': stage}
    if pct is not None:
        d['pct'] = int(max(0, min(100, pct)))
    if msg:
        d['msg'] = msg
    d.update(kw)
    sys.stdout.write(json.dumps(d) + '\n')
    sys.stdout.flush()


def allowed(url):
    p = urllib.parse.urlparse(url)
    h = (p.hostname or '').lower()
    return p.scheme == 'https' and any(h == a or h.endswith('.' + a) for a in ALLOW)


# ---------------------------------------------------------------- fetch

def fetch(url, dest):
    """download with resume; the URL and every redirect must stay on the allowlist"""
    if not allowed(url):
        raise Fail('url-not-allowed', 'Only https links to archive.org or microsoft.com are accepted.')
    expect = None
    try:
        ia = media_id.archive_org_sha1(url)
        if ia:
            expect = ia
    except Exception:
        pass
    have = os.path.getsize(dest + '.part') if os.path.exists(dest + '.part') else 0
    req = urllib.request.Request(url, headers={'User-Agent': UA, **({'Range': 'bytes=%d-' % have} if have else {})})
    try:
        r = urllib.request.urlopen(req, timeout=60)
    except Exception as e:
        raise Fail('fetch-failed', 'The download did not start: %s' % e)
    if not allowed(r.geturl()):
        raise Fail('url-not-allowed', 'The link redirected to %s, which is not on the allowlist.' % urllib.parse.urlparse(r.geturl()).hostname)
    if have and r.status != 206:
        have = 0
    total = have + int(r.headers.get('Content-Length', 0) or 0)
    if expect and total and total != expect['size']:
        raise Fail('fetch-size', 'The server sends %d bytes; archive.org lists %d for this file.' % (total, expect['size']))
    got, last = have, 0
    with open(dest + '.part', 'ab' if have else 'wb') as f:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            f.write(b)
            got += len(b)
            if time.time() - last > 0.5:
                last = time.time()
                emit('fetch', 100.0 * got / total if total else None, 'Downloading %.1f of %.1f MB' % (got / 1e6, total / 1e6))
    if total and got != total:
        raise Fail('fetch-short', 'The download stopped at %d of %d bytes. Try again to resume it.' % (got, total))
    os.replace(dest + '.part', dest)
    emit('fetch', 100, 'Downloaded %.1f MB' % (got / 1e6))
    return expect


# ---------------------------------------------------------------- identify

def identify(path, edition, published=None):
    emit('identify', 0, 'Checking the media')
    h = media_id.file_hashes(path)
    size = os.path.getsize(path)
    known = media_id.match_known(size, h['sha1'])
    if published and published.get('sha1') and published['sha1'] != h['sha1']:
        raise Fail('hash-mismatch', 'The file does not match the SHA-1 archive.org publishes for it. Download it again.')
    r = media_id.identify(path)
    kind = (known or {}).get('kind') or r.get('kind')
    ed = (known or {}).get('edition') or ('311' if kind and kind.startswith('wfw311') else 'xp' if kind in ('windows-xp-cd',) else None)
    if ed != edition:
        raise Fail('media-wrong', 'This is not %s install media (it looks like: %s).' %
                   ('Windows for Workgroups 3.11' if edition == '311' else 'Windows XP', kind or 'unknown'))
    if r.get('problems'):
        raise Fail('media-unsuitable', '; '.join(r['problems']))
    emit('identify', 100, 'Recognized: %s' % (known['file'] if known else kind), known=(known or {}).get('id'),
         kind=kind, sha256=h['sha256'], verified=bool(known))
    return {'kind': kind, 'known': known, 'hashes': h, 'detail': r}


# ---------------------------------------------------------------- Windows for Workgroups 3.11

DISK_RE = re.compile(r'DISK(\d+)$')


def wfw_files(path, kind, dest):
    """the setup files of disks 1..n in one folder (Setup reads them all from one place, so no disk swaps).
    Only the main 1.44 MB / 1.2 MB set: the set also carries 720 KB display-driver disks whose files differ."""
    os.makedirs(dest, exist_ok=True)
    z = zipfile.ZipFile(path) if zipfile.is_zipfile(path) else None
    if kind == 'wfw311-flat-files':
        for i in z.infolist():
            if not i.is_dir():
                open(os.path.join(dest, os.path.basename(i.filename).upper()), 'wb').write(z.read(i))
        return
    images = []
    if z:
        for i in z.infolist():
            if i.file_size in (1474560, 1228800):
                images.append(media_id.BytesSource(i.filename, z.read(i)))
    else:
        images.append(media_id.LocalSource(path))
    disks = {}
    for src in images:
        try:
            fat = media_id.Fat12(src)
        except ValueError:
            continue
        names = {f['name'].upper() for f in fat.files}
        n = 1 if media_id.WFW_DISK1 <= names else None
        for nm in names:
            m = DISK_RE.match(nm.split('.')[0])
            if m and n is None:
                n = int(m.group(1))
        if n:
            disks[n] = fat
    if 1 not in disks:
        raise Fail('media-incomplete', 'Disk 1 of Windows for Workgroups 3.11 is missing.')
    missing = [n for n in range(1, max(disks) + 1) if n not in disks]
    if missing or max(disks) < 8:
        raise Fail('media-incomplete', 'Disks are missing from the set: %s.' % ', '.join(map(str, missing or range(max(disks) + 1, 9))))
    for n in sorted(disks):
        for f in disks[n].files:
            open(os.path.join(dest, f['name'].upper()), 'wb').write(disks[n].read(f))


# Microsoft's Super VGA driver from the same disks (SETUP.INF [display] 8vga768s): the engine's screen is 1024x768
BYO_311_ADAPTER = 'svga_et4000'
SVGA_FILES = (('svga256.dr_', 'svga256.drv'), ('vddsvga.38_', 'vddsvga.386'), ('vgadib.3g_', 'vgadib.3gr'))


def ini_set(b, section, key, value):
    """set key=value in [section] of an INI file's bytes (CRLF), adding the key or the section if missing"""
    sec = re.search(rb'(?im)^\[' + re.escape(section) + rb'\]\r?\n', b)
    line = key + b'=' + value + b'\r\n'
    if not sec:
        return b.rstrip(b'\r\n\x1a') + b'\r\n\r\n[' + section + b']\r\n' + line
    end = re.compile(rb'(?m)^\[').search(b, sec.end())
    end = end.start() if end else len(b)
    body = b[sec.end():end]
    k = re.search(rb'(?im)^' + re.escape(key) + rb'=[^\r\n]*\r?\n', body)
    body = body[:k.start()] + line + body[k.end():] if k else line + body
    return b[:sec.end()] + body + b[end:]


def svga_1024(sysini):
    """what Windows Setup writes for "Super VGA (1024x768, 256 colors, small fonts)" (SETUP.INF [svga768s])"""
    b = open(sysini, 'rb').read()
    b = ini_set(b, b'boot', b'display.drv', b'svga256.drv')
    b = ini_set(b, b'boot', b'386grabber', b'vgadib.3gr')
    b = ini_set(b, b'boot.description', b'display.drv', b'Super VGA (1024x768, 256 colors, small fonts)')
    b = ini_set(b, b'386Enh', b'display', b'vddsvga.386')
    b = ini_set(b, b'svga256.drv', b'resolution', b'3')
    b = ini_set(b, b'svga256.drv', b'dpi', b'96')
    open(sysini, 'wb').write(b)


def du(top):
    n = 0
    for r, _, fs in os.walk(top):
        for f in fs:
            try:
                n += os.path.getsize(os.path.join(r, f))
            except OSError:         # Setup's temporary files come and go
                pass
    return n


def shot(e, path):
    try:                    # needs Pillow; a picture for the error report only
        e.shot(path)
    except Exception:
        pass


def tool(tools, name):
    p = os.path.join(tools, name)
    if not os.path.exists(p):
        raise Fail('tools-missing', 'The plugin is missing %s.' % name)
    return p


def install_311(media, work, out, tools, name='BASILISK'):
    setup = os.path.join(work, 'setup')
    drive = os.path.join(work, 'c')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(drive)
    emit('prepare', 0, 'Unpacking the setup disks')
    wfw_files(media['path'], media['kind'], setup)
    shh = answers.W311_SHH.format(name=name).replace('\n', '\r\n')
    open(os.path.join(setup, 'SETUP.SHH'), 'w', newline='').write(shh)
    emit('prepare', 100, '%d setup files ready' % len(os.listdir(setup)))

    sys.path.insert(0, os.path.join(PKG311, 'tools'))
    os.environ['BS311_ENGINE'] = tool(tools, 'engine')
    os.environ['BS311_OFFS'] = tool(tools, 'offs')
    core = tool(tools, 'dosbox_pure_libretro.so')
    from bsdrv import Engine
    head = open(os.path.join(PKG311, 'engine', 'w31-folder.conf.in')).read().split('[autoexec]')[0]
    conf = os.path.join(work, 'setup.conf')
    # /i: no hardware detection. Without it, Setup's network-card detection hangs DOSBox ("If Setup halts at this
    # point...") even with network = nonet. The answers name every device instead.
    open(conf, 'w').write(head.replace('cycles=fixed 60000', 'cycles=max') +
                          '[autoexec]\nmount c "%s"\nmount d "%s"\nd:\nsetup /i /h:d:\\setup.shh\n' % (drive, setup) +
                          ''.join('expand d:\\%s c:\\windows\\system\\%s\n' % x for x in SVGA_FILES) +
                          'echo ok> c:\\byodone.txt\n')
    emit('install', 0, 'Windows Setup is starting')
    e = Engine(conf, core=core, name='byo311-%d' % os.getpid(), log=os.path.join(work, 'setup-engine.log'))
    open(os.path.join(work, 'engine.pid'), 'w').write(str(e.p.pid))
    expect = 15e6          # an installed WfW 3.11 C:\WINDOWS with these answers is about 15 MB
    t0 = last_t = time.time()
    last_size = -1
    try:
        while True:
            time.sleep(2)
            if os.path.exists(os.path.join(drive, 'BYODONE.TXT')):
                break
            if e.p.poll() is not None:
                raise Fail('install-crashed', 'The emulator stopped during Windows Setup.')
            size = du(drive)
            if size != last_size:
                last_size, last_t = size, time.time()
            if time.time() - last_t > 240:
                shot(e, os.path.join(work, 'setup-stalled.png'))
                raise Fail('install-stalled', 'Windows Setup stopped making progress (see %s).' % os.path.join(work, 'setup-stalled.png'))
            if time.time() - t0 > 3600:
                raise Fail('install-timeout', 'Windows Setup took more than an hour.')
            emit('install', 95.0 * size / expect, 'Windows Setup is copying files (%.1f MB)' % (size / 1e6))
        shot(e, os.path.join(work, 'setup-end.png'))
    finally:
        e.close()
    os.remove(os.path.join(drive, 'BYODONE.TXT'))
    win = os.path.join(drive, 'WINDOWS')
    for f in ('WIN.COM', 'SYSTEM.INI', 'WIN.INI', 'SOUNDREC.EXE', 'CLOCK.EXE', os.path.join('SYSTEM', 'MMSYSTEM.DLL'),
              'CHIMES.WAV', 'DING.WAV', 'RINGIN.WAV', 'RINGOUT.WAV'):
        if not os.path.exists(os.path.join(win, f)):
            raise Fail('install-incomplete', 'Windows Setup finished without %s.' % f)
    emit('install', 100, 'Windows for Workgroups 3.11 is installed (%.0f s)' % (time.time() - t0))

    for _, f in SVGA_FILES:
        if not os.path.exists(os.path.join(win, 'SYSTEM', f.upper())):
            raise Fail('install-incomplete', 'Microsoft\'s Super VGA driver (%s) could not be expanded.' % f)
    svga_1024(os.path.join(win, 'SYSTEM.INI'))
    # Program Manager rewrites every group file when the display driver differs from the one it last saw, and C:
    # is a read-only zip in the plugin ("Program-group file ... is write-protected"): tell it the driver is unchanged
    pm = os.path.join(win, 'PROGMAN.INI')
    open(pm, 'wb').write(ini_set(open(pm, 'rb').read(), b'Settings', b'display.drv', b'svga256.drv'))

    # --- the synth's guest setup: what the shipped drive has beyond a plain install
    emit('guest', 0, 'Installing BASILISK 16 in Windows')
    sysini = os.path.join(win, 'SYSTEM.INI')
    b = open(sysini, 'rb').read()
    # BSYNTH.DRV is the BSYN card's wave driver; make_machine.py swaps it in for the SB16 driver the shipped drive
    # had, so here it goes straight into [drivers]
    open(sysini, 'wb').write(ini_set(b, b'drivers', b'Wave', b'bsynth.drv'))
    gout = os.path.join(work, 'gout')
    os.makedirs(gout)
    for f in ('SYNTH.EXE', 'SYNHOOK.DLL', 'BSYNTH.DRV'):
        shutil.copy(tool(tools, f), gout)
    emit('guest', 100, 'BASILISK 16 is installed')

    # --- the snapshot: the package's own make_machine.py, as for the shipped build
    emit('snapshot', 0, 'Starting Windows and opening the sixteen Sound Recorders')
    # make_machine.py as it is, beside a copy of the engine's .conf.in files with the adapter swapped (it reads them
    # from ../engine): Microsoft's SVGA256.DRV hangs Windows on DOSBox's S3 at any resolution but runs on its Tseng
    # ET4000 at 1024x768, 256 colors. The shipped drive has S3's own driver, which is not on Microsoft's disks.
    mk = os.path.join(work, 'mk')
    os.makedirs(os.path.join(mk, 'engine'))
    shutil.copytree(os.path.join(PKG311, 'tools'), os.path.join(mk, 'tools'), ignore=shutil.ignore_patterns('__pycache__'))
    for f in ('w31.conf.in', 'w31-folder.conf.in'):
        c = open(os.path.join(PKG311, 'engine', f)).read()
        if 'machine=svga_s3' not in c:
            raise Fail('tools-missing', 'The engine configuration has changed (%s); install.py needs updating.' % f)
        open(os.path.join(mk, 'engine', f), 'w').write(c.replace('machine=svga_s3', 'machine=' + BYO_311_ADAPTER))
    mm = subprocess.run([sys.executable, os.path.join(mk, 'tools', 'make_machine.py'), drive, gout, core, out],
                        capture_output=True, text=True, env=os.environ)
    if mm.returncode != 0 or not os.path.exists(os.path.join(out, 'w31.state')):
        raise Fail('snapshot-failed', 'BASILISK 16 did not start in the new Windows: %s' % (mm.stderr.strip()[-300:] or mm.stdout.strip()[-300:]))
    emit('snapshot', 100, 'Snapshot taken')
    return {f: os.path.getsize(os.path.join(out, f)) for f in os.listdir(out) if os.path.isfile(os.path.join(out, f))}


# ---------------------------------------------------------------- Windows XP

XP_INSTALL_CMD = r"""@echo off
rem BASILISK SYNTH guest setup, run once at XP's first logon (WINNT.SIF [GuiRunOnce]) from the answer floppy
mkdir C:\synth
copy /y A:\SYNTH.EXE C:\synth\
copy /y A:\SRHOOK.DLL C:\synth\
copy /y A:\PREP.BAT C:\synth\
if not exist C:\synth\srhook.dll goto fail
call C:\synth\prep.bat > C:\synth\prep.log 2>&1
del C:\synth\prep.bat
echo BSYNTH-GUEST-OK > COM1
shutdown -s -t 5 -f
goto end
:fail
echo BSYNTH-GUEST-FAIL > COM1
shutdown -s -t 5 -f
:end
"""


def xp_floppy(key, guest):
    """WINNT.SIF, the guest programs and prep.bat on one 1.44 MB floppy (about 250 KB used)"""
    sif = answers.XP_SIF.format(key=key, name='BASILISK').replace('\n', '\r\n').encode('ascii')
    files = [('WINNT.SIF', sif), ('BSYNTH.CMD', XP_INSTALL_CMD.replace('\n', '\r\n').encode('ascii')),
             ('PREP.BAT', open(os.path.join(PKG, 'guest', 'prep.bat'), 'rb').read())]
    for f in ('SYNTH.EXE', 'SRHOOK.DLL'):
        files.append((f, open(guest[f], 'rb').read()))
    return floppy.make(files, 'BSYNTH')


def install_xp(media, work, out, tools, key_file, qemu_linux):
    """Text-mode and GUI Setup from the person's CD with WINNT.SIF on a floppy; at the first logon BSYNTH.CMD from
    the same floppy puts synth.exe and srhook.dll in C:\\synth, runs guest/prep.bat and shuts XP down; then the
    package's make_machine.py makes the snapshot. synth.exe and srhook.dll are the ones built for the shipped
    machine (tcc in XP), carried by the plugin in its tools folder as xp/SYNTH.EXE and xp/SRHOOK.DLL.
    Under TCG this takes 1-3 hours; with KVM, WHPX or HVF about 15 minutes."""
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    emit('prepare', 0, 'Writing the answer floppy')
    guest = {f: tool(tools, os.path.join('xp', f)) for f in ('SYNTH.EXE', 'SRHOOK.DLL')}
    key = open(key_file).read().strip().upper()
    if not re.match(r'^[0-9A-Z]{5}(-[0-9A-Z]{5}){4}$', key):
        raise Fail('key-invalid', 'A product key is five groups of five letters and digits.')
    flp = os.path.join(work, 'answers.img')
    open(flp, 'wb').write(xp_floppy(key, guest))
    del key
    q = qemu_linux
    lib = os.path.join(q, 'lib')
    pre = [os.path.join(lib, 'ld-linux-x86-64.so.2'), '--library-path', lib]
    env = dict(os.environ, QEMU_MODULE_DIR=os.path.join(lib, 'modules'))
    disk = os.path.join(work, 'disk.qcow2')
    subprocess.check_call(pre + [os.path.join(q, 'bin', 'qemu-img'), 'create', '-q', '-f', 'qcow2', disk, '64G'], env=env)
    emit('prepare', 100, 'A new 64 GB disk (it grows as XP fills it)')
    com = os.path.join(work, 'com1.log')
    accel = 'kvm' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'tcg,thread=multi,tb-size=256'
    # the plugin's machine (Machine.cpp: 1 vCPU, 512 MB, cirrus, AC97, rtl8139 with restrict=on) plus the CD and the
    # floppy; boot the CD once, then the disk for GUI Setup and the first logon
    args = pre + [os.path.join(q, 'bin', 'qemu-system-i386'), '-nodefaults', '-no-user-config',
                  '-M', 'pc-i440fx-6.2', '-m', '512', '-smp', '1', '-cpu', 'qemu32',
                  '-drive', 'file=%s,format=qcow2,if=ide,index=0,cache=writeback' % disk,
                  '-drive', 'file=%s,format=raw,if=ide,index=2,media=cdrom,readonly=on' % media['path'],
                  '-drive', 'file=%s,format=raw,if=floppy,index=0' % flp,
                  '-vga', 'cirrus', '-device', 'rtl8139,netdev=n0,mac=52:54:00:12:34:56',
                  '-netdev', 'user,id=n0,restrict=on,net=10.0.2.0/24',
                  '-usb', '-device', 'usb-tablet', '-rtc', 'base=localtime', '-display', 'none',
                  '-boot', 'once=d,menu=off', '-L', os.path.join(q, 'share'), '-accel', accel,
                  '-audiodev', 'none,id=snd0', '-device', 'AC97,audiodev=snd0',
                  '-serial', 'file:%s' % com, '-qmp', 'unix:%s,server=on,wait=off' % os.path.join(work, 'qmp.sock')]
    p = subprocess.Popen(args, env=env, stdout=open(os.path.join(work, 'qemu.log'), 'w'), stderr=subprocess.STDOUT)
    open(os.path.join(work, 'qemu.pid'), 'w').write(str(p.pid))
    t0 = time.time()
    expect = 1.6e9      # an installed XP SP3 is about 1.5 GB of disk
    try:
        while p.poll() is None:
            time.sleep(5)
            used = os.path.getsize(disk)
            emit('install', 95.0 * used / expect, 'Windows XP Setup (%.0f MB written, %d min)' % (used / 1e6, (time.time() - t0) / 60))
            if time.time() - t0 > 4 * 3600:
                raise Fail('install-timeout', 'Windows XP Setup took more than four hours.')
    finally:
        if p.poll() is None:
            p.kill()
        os.remove(flp)                    # the key is on it
    log = open(com, 'rb').read() if os.path.exists(com) else b''
    if b'BSYNTH-GUEST-OK' not in log:
        raise Fail('guest-failed', 'XP Setup ended, but BASILISK SYNTH was not set up in it%s.' %
                   (' (synth.exe was not copied)' if b'BSYNTH-GUEST-FAIL' in log else ' (Setup did not reach the first logon)'))
    emit('guest', 100, 'BASILISK SYNTH is installed in XP')
    emit('snapshot', 0, 'Starting XP and opening the sixteen Sound Recorders')
    mm = subprocess.run([sys.executable, os.path.join(PKG, 'tools', 'make_machine.py'), disk, out, '--qemu-linux', q],
                        capture_output=True, text=True)
    if mm.returncode != 0:
        raise Fail('snapshot-failed', (mm.stderr.strip() or mm.stdout.strip())[-300:])
    emit('snapshot', 100, 'Snapshot taken')
    return {f: os.path.getsize(os.path.join(out, f)) for f in os.listdir(out) if os.path.isfile(os.path.join(out, f))}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edition', choices=['311', 'xp'])
    ap.add_argument('media', help='a local file, or an https URL on archive.org or microsoft.com')
    ap.add_argument('out')
    ap.add_argument('--work', help='scratch folder (default OUT.work; deleted at the end)')
    ap.add_argument('--cache', help='where a downloaded medium is kept for a retry (default OUT.media)')
    ap.add_argument('--tools', default=os.environ.get('BYO_TOOLS'))
    ap.add_argument('--key-file')
    ap.add_argument('--qemu-linux', default=os.path.expanduser('~/basilisk-build/qemu-linux'))
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()
    out = os.path.abspath(a.out).rstrip(os.sep)
    work = a.work or out + '.work'      # never inside OUT: make_machine.py empties OUT before it writes the machine
    cache = a.cache or out + '.media'
    try:
        if not a.tools:
            raise Fail('tools-missing', 'No tools folder (--tools or BYO_TOOLS).')
        published = None
        if re.match(r'https?://', a.media):
            os.makedirs(cache, exist_ok=True)
            path = os.path.join(cache, os.path.basename(urllib.parse.unquote(urllib.parse.urlparse(a.media).path)) or 'media')
            if not os.path.exists(path):
                published = fetch(a.media, path)
        else:
            path = a.media
            if not os.path.exists(path):
                raise Fail('media-missing', 'There is no file at %s.' % path)
        m = identify(path, a.edition, published)
        m['path'] = path
        if a.edition == '311':
            files = install_311(m, work, out, a.tools)
        else:
            if not a.key_file:
                raise Fail('key-missing', 'Windows XP Setup needs your product key.')
            files = install_xp(m, work, out, a.tools, a.key_file, a.qemu_linux)
        if not a.keep:
            shutil.rmtree(work, ignore_errors=True)
        emit('done', 100, 'Ready', out=out, machine=files, media_sha256=m['hashes']['sha256'])
    except Fail as e:
        emit('error', code=e.code, msg=str(e))
        sys.exit(2)


if __name__ == '__main__':
    main()

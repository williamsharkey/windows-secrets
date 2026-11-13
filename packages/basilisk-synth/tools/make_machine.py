#!/usr/bin/env python3
"""Make the machine every BASILISK SYNTH resumes: base.qcow2 + state.mig (+ the firmware it was made with).

    make_machine.py PREPARED.qcow2 OUTDIR [--qemu-linux DIR] [--settle 25]

PREPARED.qcow2 is the XP disk with C:\\synth built (guest/*.c compiled there with tcc), prepared by guest/prep.bat
(no system sounds, no screen saver, synth.exe in HKCU\\...\\Run) and with nothing else in Startup, shut down cleanly.

This boots it cold under TCG with exactly the devices the plugin gives it (Machine.cpp: launch), waits until synth.exe
answers "hi" on COM1 with its sixteen Sound Recorders open and the default DNA built, lets XP settle, then pauses it and
writes the machine state as a migration stream. The disk as it is at that moment becomes base.qcow2. Run it with the
QEMU 6.2 the XP lane ships for Linux, like packages/basilisk-xp/tools/make_ready.py: a TCG stream with plain qemu32
CPUs loads in the QEMU 11 of Windows and macOS.

Then OUTDIR/basilisk-synth-machine-1.tar.xz and plugin/machine_info.h are written.
"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'machine-1'


def qmp(path, cmd, args=None, timeout=600):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(timeout)
    s.connect(path)
    f = s.makefile('rw')
    f.readline()
    f.write('{"execute":"qmp_capabilities"}\n'); f.flush(); f.readline()
    f.write(json.dumps({'execute': cmd, **({'arguments': args} if args else {})}) + '\n'); f.flush()
    while True:
        r = json.loads(f.readline())
        if 'return' in r or 'error' in r:
            s.close()
            return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('disk')
    ap.add_argument('out')
    ap.add_argument('--qemu-linux', default=os.path.expanduser('~/basilisk-build/qemu-linux'))
    ap.add_argument('--settle', type=float, default=25)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    work = os.path.join(a.out, 'work')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    q = a.qemu_linux
    lib = os.path.join(q, 'lib')
    pre = [os.path.join(lib, 'ld-linux-x86-64.so.2'), '--library-path', lib]
    env = dict(os.environ, QEMU_MODULE_DIR=os.path.join(lib, 'modules'))
    disk = os.path.join(work, 'disk.qcow2')
    shutil.copyfile(a.disk, disk)
    qmps, coms = os.path.join(work, 'qmp.sock'), os.path.join(work, 'com1.sock')
    # the plugin's devices, exactly (Machine.cpp); only the host ends differ
    args = pre + [os.path.join(q, 'bin', 'qemu-system-i386'), '-name', 'BASILISK SYNTH', '-nodefaults', '-no-user-config',
                  '-M', 'pc-i440fx-6.2', '-m', '512', '-smp', '2', '-cpu', 'qemu32',
                  '-drive', 'file=%s,format=qcow2,if=ide,index=0,cache=writeback' % disk,
                  '-vga', 'cirrus', '-device', 'rtl8139,netdev=n0,mac=52:54:00:12:34:56',
                  '-netdev', 'user,id=n0,restrict=on,net=10.0.2.0/24',
                  '-usb', '-device', 'usb-tablet', '-rtc', 'base=localtime', '-display', 'none', '-boot', 'menu=off',
                  '-L', os.path.join(q, 'share'), '-accel', 'tcg,thread=multi,tb-size=256',
                  '-audiodev', 'wav,id=snd0,path=%s,out.frequency=44100,out.channels=2,out.format=s16' % os.path.join(work, 'boot.wav'),
                  '-device', 'AC97,audiodev=snd0',
                  '-chardev', 'socket,id=ser0,path=%s,server=on,wait=off' % coms, '-serial', 'chardev:ser0',
                  '-vnc', 'unix:%s' % os.path.join(work, 'vnc.sock'),
                  '-qmp', 'unix:%s,server=on,wait=off' % qmps]
    log = open(os.path.join(work, 'qemu.log'), 'w')
    p = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
    t0 = time.time()
    for _ in range(100):
        if os.path.exists(coms):
            break
        time.sleep(0.1)
    c = socket.socket(socket.AF_UNIX)
    c.connect(coms)
    c.settimeout(1)
    buf = b''
    state = None
    while time.time() - t0 < 1200:
        if p.poll() is not None:
            sys.exit('QEMU stopped')
        c.sendall(b'hi 1\n')
        try:
            buf += c.recv(4096)
        except socket.timeout:
            pass
        for line in buf.split(b'\n')[:-1]:
            print('  guest:', line.decode('latin1'), flush=True)
            if line.startswith(b'hi 1 xp'):
                state = line.decode().split()[-1]
            if line.startswith(b'built'):
                built = True
        buf = buf.split(b'\n')[-1]
        if state == 'wait':
            break
        time.sleep(2)
    if state != 'wait':
        sys.exit('synth.exe never answered')
    print('synth.exe answered after %.0fs; settling %.0fs' % (time.time() - t0, a.settle), flush=True)
    time.sleep(a.settle)
    qmp(qmps, 'screendump', {'filename': os.path.join(a.out, 'machine-before-go.ppm')})
    c.close()
    state_path = os.path.join(a.out, 'state.mig')
    qmp(qmps, 'stop')
    r = qmp(qmps, 'migrate', {'uri': 'exec:cat > %s' % state_path})
    while True:
        r = qmp(qmps, 'query-migrate')['return']
        if r.get('status') in ('completed', 'failed', 'cancelled'):
            break
        time.sleep(0.2)
    if r['status'] != 'completed':
        sys.exit('migration %s' % r['status'])
    qmp(qmps, 'quit')
    p.wait(60)
    print('state: %d bytes' % os.path.getsize(state_path), flush=True)
    base = os.path.join(a.out, 'base.qcow2')
    subprocess.check_call(pre + [os.path.join(q, 'bin', 'qemu-img'), 'convert', '-c', '-O', 'qcow2', disk, base], env=env)
    fw = os.path.join(a.out, 'fw')
    shutil.rmtree(fw, ignore_errors=True)
    shutil.copytree(os.path.join(q, 'share'), fw, ignore=shutil.ignore_patterns('keymaps'))
    tarball = os.path.join(a.out, 'basilisk-synth-%s.tar.xz' % NAME)
    subprocess.check_call(['tar', '-C', a.out, '-cf', '-', 'base.qcow2', 'state.mig', 'fw'],
                          stdout=open(tarball + '.tar', 'wb'))
    subprocess.check_call(['xz', '-6', '-T0', '-f', tarball + '.tar'])
    os.replace(tarball + '.tar.xz', tarball)
    h = hashlib.sha256()
    with open(tarball, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    unpacked = os.path.getsize(base) + os.path.getsize(state_path) + sum(
        os.path.getsize(os.path.join(fw, x)) for x in os.listdir(fw))
    info = os.path.join(PKG, 'plugin', 'machine_info.h')
    with open(info, 'w') as f:
        f.write('// the Windows XP machine this build of BASILISK SYNTH resumes (written by tools/make_machine.py)\n#pragma once\n')
        f.write('#define BSYNTH_MACHINE_NAME "%s"\n' % NAME)
        f.write('#define BSYNTH_MACHINE_URL "https://github.com/williamsharkey/windows-secrets/releases/download/'
                'basilisk-synth-v1.0.0/basilisk-synth-%s.tar.xz"\n' % NAME)
        f.write('#define BSYNTH_MACHINE_BYTES %dLL\n' % os.path.getsize(tarball))
        f.write('#define BSYNTH_MACHINE_UNPACKED %dLL\n' % unpacked)
        f.write('#define BSYNTH_MACHINE_SHA256 "%s"\n' % h.hexdigest())
    print('wrote %s (%d bytes, sha256 %s) and %s' % (tarball, os.path.getsize(tarball), h.hexdigest(), info))
    shutil.rmtree(work)


if __name__ == '__main__':
    main()

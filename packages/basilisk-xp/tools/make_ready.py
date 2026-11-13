#!/usr/bin/env python3
"""Make the shipped machine: boot the base disk cold, let BASILISK build itself, then save the snapshot
'ready' that every BASILISK loads in a second or two.

    make_ready.py BASE.qcow2 OUT.qcow2 [--accel tcg] [--shots DIR]

Run it with the QEMU the app ships for Linux (BASILISK_BUNDLE pointing at a folder with qemu/), TCG, so the
snapshot holds plain qemu32 CPUs that every platform's QEMU (6.2 and later) can load.
"""
import argparse
import os
import shutil
import sys
import threading
import time

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PKG, 'app'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('out')
    ap.add_argument('--accel', default='tcg')
    ap.add_argument('--shots')
    ap.add_argument('--settle', type=float, default=20)
    ap.add_argument('--port', type=int, default=8765)
    a = ap.parse_args()
    work = os.path.dirname(os.path.abspath(a.out))
    cfg = a.out + '.config'
    os.makedirs(cfg, exist_ok=True)
    os.environ.update({'TERM_ROOT': cfg, 'BASILISK_CONFIG': cfg, 'TERM_GUEST_PORT': str(a.port)})
    os.environ.pop('ANTHROPIC_API_KEY', None)
    import machine
    import server_local as S
    S.LOCAL['quiet'] = True

    shutil.copyfile(a.base, a.out)
    hello = threading.Event()
    S.LOCAL['listeners'].append(lambda kind, kv: kind == 'hello' and hello.set())
    threading.Thread(target=S.serve, daemon=True).start()
    q = machine.Qemu()
    m = machine.Machine(q, a.out, a.out + '.qemu.log', a.port, accel=a.accel)
    t0 = time.time()
    m.start(paused=False)

    def shot(name):
        if a.shots:
            m.cmd('screendump', {'filename': os.path.join(a.shots, os.path.basename(a.out) + '-' + name + '.ppm')})

    while not hello.wait(10):
        if not m.alive():
            sys.exit('QEMU stopped')
        if time.time() - t0 > 1500:
            shot('timeout')
            sys.exit('no hello after 25 minutes')
        print('  %4.0fs waiting for the client' % (time.time() - t0), flush=True)
    print('hello after %.0fs; settling %.0fs' % (time.time() - t0, a.settle), flush=True)
    time.sleep(a.settle)
    shot('ready-before')
    S.call(S.go_dark())       # XP's event thread now sleeps 2 s: save it there, with nothing in flight
    m.cmd('stop')
    r = m.savevm('ready')
    print('savevm:', r, flush=True)
    m.quit()
    print('done in %.0fs: %s' % (time.time() - t0, a.out))
    print(q.snapshots(a.out))


if __name__ == '__main__':
    main()

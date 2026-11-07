#!/usr/bin/env python3
"""Record a QEMU guest's real framebuffer through the HMP monitor.
   qrec.py start NAME [fps]   - begin grabbing frames to /dev/shm/qrec-NAME
   qrec.py stop NAME          - stop and encode /root/rec-NAME.mp4 (true timing)
SDL/VNC front ends can miss dirty regions; screendump always renders the
whole surface, so this is slower but exact."""
import socket, sys, os, time, signal, subprocess, glob

MON = '/tmp/studio-mon.sock'


def grab(name, fps):
    d = '/dev/shm/qrec-' + name
    os.makedirs(d, exist_ok=True)
    for f in glob.glob(d + '/*'):
        os.remove(f)
    s = socket.socket(socket.AF_UNIX)
    s.connect(MON)
    s.settimeout(5)
    buf = b''

    def wait_prompt():
        nonlocal buf
        while b'(qemu) ' not in buf:
            buf += s.recv(65536)
        buf = buf.split(b'(qemu) ', 1)[1]

    wait_prompt()
    stop = {'v': False}
    signal.signal(signal.SIGTERM, lambda *a: stop.update(v=True))
    times = open(d + '/times.txt', 'w')
    i, t0 = 0, time.time()
    while not stop['v']:
        t = time.time()
        f = '%s/%06d.ppm' % (d, i)
        try:
            if os.path.exists('/tmp/qrec-cmd'):
                # monitor commands injected while recording (e.g. sendkey)
                for c in open('/tmp/qrec-cmd').read().splitlines():
                    s.sendall((c + '\n').encode())
                    wait_prompt()
                os.remove('/tmp/qrec-cmd')
            s.sendall(('screendump %s\n' % f).encode())
            wait_prompt()
        except Exception:
            break  # the VM went away (e.g. it hibernated)
        times.write('%06d %.4f\n' % (i, t - t0))
        times.flush()
        i += 1
        nxt = t0 + i / fps
        while time.time() < nxt and not stop['v']:
            time.sleep(0.002)
    times.close()


def encode(name):
    d = '/dev/shm/qrec-' + name
    rows = [l.split() for l in open(d + '/times.txt') if l.strip()]
    with open(d + '/list.txt', 'w') as L:
        for k, (idx, t) in enumerate(rows):
            nxt = float(rows[k + 1][1]) if k + 1 < len(rows) else float(t) + 0.04
            if not os.path.exists('%s/%s.ppm' % (d, idx)):
                continue
            L.write("file '%s/%s.ppm'\nduration %.4f\n" % (d, idx, nxt - float(t)))
        L.write("file '%s/%s.ppm'\n" % (d, rows[-1][0]))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', d + '/list.txt',
                    '-vf', 'fps=30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
                    '/root/rec-%s.mp4' % name], check=True)
    print('frames', len(rows), 'duration %.1fs' % float(rows[-1][1]))


if __name__ == '__main__':
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == 'start':
        if os.fork() == 0:
            os.setsid()
            open('/tmp/qrec-%s.pid' % name, 'w').write(str(os.getpid()))
            grab(name, float(sys.argv[3]) if len(sys.argv) > 3 else 25)
            os._exit(0)
    elif cmd == 'stop':
        pid = int(open('/tmp/qrec-%s.pid' % name).read())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        time.sleep(1)
        encode(name)

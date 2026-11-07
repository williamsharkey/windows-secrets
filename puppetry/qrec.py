#!/usr/bin/env python3
"""Record a QEMU guest's real framebuffer through the HMP monitor.
   qrec.py start NAME [fps]   - begin grabbing frames, streamed into ffmpeg
   qrec.py stop NAME          - stop; /root/rec-NAME.mp4 is ready when this returns
SDL/VNC front ends can miss dirty regions; screendump always renders the whole
surface.  Frames are piped straight to the encoder at a constant frame rate
(the latest frame is repeated when a screendump runs slow), so nothing piles
up in memory.  Monitor commands written to /tmp/qrec-cmd are injected between
frames, e.g. "sendkey shift 2000" or "wavcapture /root/a.wav snd0"."""
import socket, sys, os, time, signal, subprocess

MON = '/tmp/studio-mon.sock'


def grab(name, fps):
    tmp = '/dev/shm/qrec-%s.ppm' % name
    out = '/root/rec-%s.mp4' % name
    enc = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps),
                            '-c:v', 'ppm', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16',
                            '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    buf = b''
    s = None

    def wait_prompt():
        nonlocal buf
        while b'(qemu) ' not in buf:
            d = s.recv(65536)
            if not d:
                raise ConnectionError('monitor closed')
            buf += d
        buf = buf.split(b'(qemu) ', 1)[1]

    def connect():
        nonlocal s, buf
        s = socket.socket(socket.AF_UNIX)
        s.connect(MON)
        s.settimeout(60)
        buf = b''
        wait_prompt()

    connect()
    errors = 0
    errlog = open('/tmp/qrec-%s.err' % name, 'w')
    stop = {'v': False}
    signal.signal(signal.SIGTERM, lambda *a: stop.update(v=True))
    t0, written, last = time.time(), 0, None
    while not stop['v']:
        try:
            if os.path.exists('/tmp/qrec-cmd'):
                for c in open('/tmp/qrec-cmd').read().splitlines():
                    s.sendall((c + '\n').encode())
                    wait_prompt()
                os.remove('/tmp/qrec-cmd')
            s.sendall(('screendump %s\n' % tmp).encode())
            wait_prompt()
            last = open(tmp, 'rb').read()
        except socket.timeout:
            pass
        except Exception as e:
            errlog.write('%.1f %r\n' % (time.time() - t0, e)); errlog.flush()
            errors += 1
            if errors > 20:
                break  # the VM really went away (e.g. it hibernated)
            try:
                time.sleep(0.5); connect()
            except Exception:
                pass
        due = int((time.time() - t0) * fps) + 1
        while last and written < due:
            enc.stdin.write(last)
            written += 1
        nxt = t0 + written / fps
        while time.time() < nxt and not stop['v']:
            time.sleep(0.002)
    enc.stdin.close()
    enc.wait()
    open('/tmp/qrec-%s.done' % name, 'w').write('%d frames, %.1fs\n' % (written, written / fps))
    try:
        os.remove(tmp)
    except OSError:
        pass


if __name__ == '__main__':
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == 'start':
        try:
            os.remove('/tmp/qrec-%s.done' % name)
        except OSError:
            pass
        if os.fork() == 0:
            os.setsid()
            open('/tmp/qrec-%s.pid' % name, 'w').write(str(os.getpid()))
            grab(name, float(sys.argv[3]) if len(sys.argv) > 3 else 25)
            os._exit(0)
    elif cmd == 'stop':
        try:
            os.kill(int(open('/tmp/qrec-%s.pid' % name).read()), signal.SIGTERM)
        except (ProcessLookupError, FileNotFoundError):
            pass
        for _ in range(600):
            if os.path.exists('/tmp/qrec-%s.done' % name):
                break
            time.sleep(0.5)
        print(open('/tmp/qrec-%s.done' % name).read().strip() if os.path.exists('/tmp/qrec-%s.done' % name) else 'no recording')

#!/usr/bin/env python3
"""BASILISK LIVE streamer: the stage VM's real framebuffer + sound -> low-latency HLS.

One encode, shared by every viewer.  Video comes from HMP `screendump` on the
stage's own monitor (/tmp/stage-mon.sock - this process is its only client),
written to ffmpeg at a constant frame rate (the latest frame repeats when a
screendump runs slow, e.g. during loadvm).  Sound comes from the private
PulseAudio null sink "stage" (QEMU -audiodev pa) through parec, which delivers
a gap-free stream: silence when XP is quiet, so audio never stalls the muxer.

Output: /dev/shm/stage-hls/{live.m3u8, init.mp4, seg*.m4s, poster.jpg}
        /dev/shm/stage-hls/stats.json  (fps actually grabbed, for server.py)
Only pixels and samples leave this process; nothing else from Windows does.
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time

MON = os.environ.get('STAGE_MON', '/tmp/stage-mon.sock')
PULSE = os.environ.get('STAGE_PULSE', 'unix:/root/stage/pulse/native')
OUT = os.environ.get('STAGE_HLS', '/dev/shm/stage-hls')
FPS = float(os.environ.get('STAGE_FPS', '15'))
VBR = os.environ.get('STAGE_VBITRATE', '1500k')    # peak cap (motion); a still desktop costs ~0.4 Mbps
GOP = float(os.environ.get('STAGE_GOP', '2'))      # seconds per keyframe = per HLS segment
TMP = '/dev/shm/stage-frame.ppm'

stop = {'v': False}
signal.signal(signal.SIGTERM, lambda *a: stop.update(v=True))
signal.signal(signal.SIGINT, lambda *a: stop.update(v=True))


class Monitor:
    def __init__(self, path):
        self.path, self.s, self.buf = path, None, b''

    def connect(self):
        self.close()
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(10)
        s.connect(self.path)
        self.s, self.buf = s, b''
        self._prompt()

    def close(self):
        if self.s:
            try:
                self.s.close()
            except OSError:
                pass
        self.s = None

    def _prompt(self):
        while b'(qemu) ' not in self.buf:
            d = self.s.recv(65536)
            if not d:
                raise ConnectionError('monitor closed')
            self.buf += d
        self.buf = self.buf.split(b'(qemu) ', 1)[1]

    def cmd(self, c):
        if not self.s:
            raise ConnectionError('not connected')
        self.s.sendall((c + '\n').encode())
        self._prompt()


def start_encoder():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)
    rd, wr = os.pipe()
    parec = subprocess.Popen(['parec', '--server=' + PULSE, '-d', 'stage.monitor', '--raw',
                              '--format=s16le', '--rate=44100', '--channels=2', '--latency-msec=40'],
                             stdout=wr, stderr=subprocess.DEVNULL)
    os.close(wr)
    g = str(int(FPS * GOP))   # Bliss keyframes are ~100 KB: GOP length is the bitrate/latency knob
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-nostdin',
           '-thread_queue_size', '64', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'ppm', '-i', 'pipe:0',
           '-thread_queue_size', '2048', '-f', 's16le', '-ar', '44100', '-ac', '2', '-i', 'pipe:%d' % rd,
           '-map', '0:v', '-map', '1:a',
           '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency', '-profile:v', 'main', '-level', '3.1',
           '-pix_fmt', 'yuv420p', '-g', g, '-keyint_min', g, '-sc_threshold', '0',
           '-crf', '26', '-maxrate', VBR, '-bufsize', os.environ.get('STAGE_VBUF', '3000k'),   # roomy: a starved keyframe gets 'repaired' by fat P-frames
           '-c:a', 'aac', '-b:a', '64k',
           '-f', 'hls', '-hls_time', str(GOP), '-hls_list_size', '5',
           '-hls_flags', 'delete_segments+independent_segments+omit_endlist+temp_file',
           '-hls_segment_type', 'fmp4', '-hls_fmp4_init_filename', 'init.mp4',
           '-hls_segment_filename', OUT + '/seg%d.m4s', OUT + '/live.m3u8']
    # (no second "poster" output here: a slow fps=1/4 output gates the whole muxer
    #  and makes HLS segments arrive in pairs, adding seconds of latency)
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, pass_fds=(rd,))
    os.close(rd)
    return parec, enc


def poster(frame):
    """a small JPEG of the latest frame for page posters / no-video fallback"""
    if not frame:
        return
    try:
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-c:v', 'ppm', '-i', '-',
                        '-vf', 'scale=512:-2', '-q:v', '6', OUT + '/poster.tmp.jpg'],
                       input=frame, timeout=5, check=True)
        os.replace(OUT + '/poster.tmp.jpg', OUT + '/poster.jpg')
    except (subprocess.SubprocessError, OSError):
        pass


def main():
    mon = Monitor(MON)
    while not stop['v']:
        try:
            mon.connect()
            break
        except OSError:
            time.sleep(1)
    parec, enc = start_encoder()
    t0, written, last, grabbed, errors = time.time(), 0, None, 0, 0
    stat_t, stat_n = time.time(), 0
    while not stop['v']:
        try:
            mon.cmd('screendump ' + TMP)
            with open(TMP, 'rb') as f:
                last = f.read()
            grabbed += 1
            errors = 0
        except (OSError, ConnectionError, socket.timeout) as e:
            errors += 1
            sys.stderr.write('monitor: %r\n' % e)
            time.sleep(0.5)
            try:
                mon.connect()
            except OSError:
                pass
        if enc.poll() is not None or parec.poll() is not None:
            sys.stderr.write('encoder or parec exited; restarting\n')
            break
        due = int((time.time() - t0) * FPS) + 1
        try:
            while last and written < due:
                enc.stdin.write(last)
                written += 1
        except BrokenPipeError:
            break
        now = time.time()
        if now - stat_t >= 5:
            try:
                with open(OUT + '/stats.tmp', 'w') as f:
                    json.dump({'grab_fps': round((grabbed - stat_n) / (now - stat_t), 1), 'out_fps': FPS,
                               't': now}, f)
                os.replace(OUT + '/stats.tmp', OUT + '/stats.json')
            except OSError:
                pass
            stat_t, stat_n = now, grabbed
            poster(last)
        nxt = t0 + written / FPS
        while time.time() < nxt and not stop['v']:
            time.sleep(0.003)
    for p in (parec,):
        p.terminate()
    try:
        enc.stdin.close()
    except OSError:
        pass
    try:
        enc.wait(5)
    except subprocess.TimeoutExpired:
        enc.kill()
    mon.close()
    return 0 if stop['v'] else 1     # non-zero -> systemd restarts us


def run():
    # children die with us, however we die (systemd's cgroup kill covers SIGKILL)
    try:
        return main()
    finally:
        subprocess.run(['pkill', '-P', str(os.getpid())], check=False)


if __name__ == '__main__':
    sys.exit(run())

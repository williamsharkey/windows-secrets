#!/usr/bin/env python3
"""Make /root/term/bin/qemu-system-i386-vnc30: Ubuntu's QEMU 8.2.2 (1:8.2.2+ds-0ubuntu1.18) with ONE byte changed so
QEMU's VNC server never backs off its refresh interval (ui/vnc.c vnc_refresh: interval += 50 up to 3000 ms on every
refresh that sent nothing). With the backoff the first change after a quiet moment could wait 100-3000 ms; patched,
the server samples every 30 ms whenever a client is connected (a paused VM has nothing dirty, so idle stays ~free).
The instruction `add $0x32,%rax` (48 83 c0 32) right before `mov $0xbb8,%edx` becomes `add $0x0,%rax`.
Run on sharkey-server; re-run (and re-check the pattern) after any QEMU package upgrade."""
import subprocess
SRC, DST, VA = '/usr/bin/qemu-system-i386', '/root/term/bin/qemu-system-i386-vnc30', 0x48eb36
off = None
for l in subprocess.run(['readelf', '-lW', SRC], capture_output=True, text=True).stdout.splitlines():
    f = l.split()
    if f and f[0] == 'LOAD':
        o, v, fs = int(f[1], 16), int(f[2], 16), int(f[4], 16)
        if v <= VA < v + fs:
            off = o + (VA - v)
data = bytearray(open(SRC, 'rb').read())
assert data[off:off + 9] == bytes.fromhex('4883c032bab80b0000'), 'pattern not found: different QEMU build, find the site again'
data[off + 3] = 0
open(DST, 'wb').write(data)
print('wrote', DST)

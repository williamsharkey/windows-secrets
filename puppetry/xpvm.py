#!/usr/bin/env python3
"""Drive the XP QEMU VM through its monitor socket.
   xpvm.py shot out.png | key ctrl-e [key ...] | text "notepad" | sleep 1"""
import socket, sys, time, subprocess
SOCK = __import__('os').environ.get('XPSOCK', '/tmp/ws-mon.sock')
def mon(cmd):
    s = socket.socket(socket.AF_UNIX); s.connect(SOCK); s.settimeout(3)
    try: s.recv(4096)
    except Exception: pass
    s.sendall((cmd + '\n').encode()); time.sleep(0.25)
    try: s.recv(65536)
    except Exception: pass
    s.close()
KEYS = {'%': 'shift-5', '(': 'shift-9', ')': 'shift-0', '=': 'equal', '>': 'shift-dot', '<': 'shift-comma', '"': 'shift-apostrophe', '&': 'shift-7', '|': 'shift-backslash', ',': 'comma', ';': 'semicolon', '+': 'shift-equal', ' ': 'spc', '.': 'dot', '\\': 'backslash', '/': 'slash', ':': 'shift-semicolon', '-': 'minus', '_': 'shift-minus'}
args = sys.argv[1:]
while args:
    a = args.pop(0)
    if a == 'shot':
        p = args.pop(0); mon('screendump /tmp/xpvm.ppm'); time.sleep(0.5)
        subprocess.run(['python3', '-c', f"from PIL import Image; Image.open('/tmp/xpvm.ppm').save('{p}')"], check=False)
        if not __import__('os').path.exists(p): subprocess.run(['convert', '/tmp/xpvm.ppm', p])
    elif a == 'key':
        while args and args[0] not in ('shot', 'key', 'text', 'sleep'): mon('sendkey ' + args.pop(0)); time.sleep(0.15)
    elif a == 'text':
        for ch in args.pop(0):
            mon('sendkey ' + (KEYS.get(ch) or (('shift-' + ch.lower()) if ch.isupper() else ch))); time.sleep(0.08)
    elif a == 'sleep':
        time.sleep(float(args.pop(0)))

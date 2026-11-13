"""Test rig (Linux/macOS): CONF = a machine conf with paths filled in; CORE optional (tools/bsdrv.py). See README."""
"""Boot, say go, grab frames as fast as possible until ready; write frames + a contact sheet."""
import sys, time, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsdrv import *
import numpy as np
from PIL import Image
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
state = sys.argv[2] if len(sys.argv) > 2 else '-'
e = Engine(os.environ['CONF'], state=state)
frames = []
try:
    if state == '-': e.wait_packet(2, 90)
    else:
        while e.state() < 2: time.sleep(0.01)
        print('restored at', round(time.time() - e.t0, 2))
    e.line('hi 1'); e.wait_text('hi 1 311', 10)
    e.line('go'); t1 = time.time()
    while time.time() - t1 < 10:
        s = e.u32('vid_seq')
        if not s & 1:
            px = bytes(e.m[OFF['vid']:OFF['vid'] + 1024 * 768 * 4])
            if e.u32('vid_seq') == s: frames.append((time.time() - t1, px))
        e.poll()
        if 'ready' in e.texts: break
        time.sleep(0.03)
    print('ready after %.2f s, %d frames' % (time.time() - t1, len(frames)))
    time.sleep(0.3); e.shot(out + '/ready.png')
finally:
    e.close()
ims = []
for i, (t, px) in enumerate(frames):
    im = Image.frombuffer('RGBX', (1024, 768), px, 'raw', 'BGRX').convert('RGB')
    im.save('%s/f%03d_%05.2f.png' % (out, i, t)); ims.append(im)
pick = [ims[int(k * (len(ims) - 1) / 11)] for k in range(12)] if ims else []
W, H = 512, 384
sheet = Image.new('RGB', (W * 4, H * 3))
for i, im in enumerate(pick): sheet.paste(im.resize((W, H)), ((i % 4) * W, (i // 4) * H))
sheet.save(out + '/sheet.png')

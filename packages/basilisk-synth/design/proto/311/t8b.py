import rig, time, json, numpy as np
e = rig.start(); dumps = {}; X0 = Y0 = None
def dump(tag):
    s = rig.pr(e, 'pr mine seg', 'pr mine seg'); size = int(s.split('size ')[1].split()[0])
    n0 = len(e.texts); rig.pr(e, 'pr mine dump 0 %d' % size, 'pr mine dumped', timeout=60)
    b = bytearray(size)
    for t in e.texts[n0:]:
        if t.startswith('pr hx '):
            _, _, off, hx = t.split(' ', 3); off = int(off); b[off:off + len(hx) // 2] = bytes.fromhex(hx)
    dumps[tag] = dict(seg=s, hex=bytes(b).hex()); json.dump(dumps, open('/home/wm/pe2-evidence/311/t8_dumps.json', 'w')); print('dumped', tag); e.shot('/home/wm/pe2-evidence/311/t8_%s.png' % tag); return bytes(b)
def click(col, row, btn=0):
    rig.pr(e, 'pr mine click %d %d %d' % (X0 + 16 * (col - 1) + 8, Y0 + 16 * (row - 1) + 8, btn), 'pr mine click'); time.sleep(0.15)
def board(b, w, h): return [[b[0x440 + 32 * r + c] for c in range(w + 2)] for r in range(h + 2)]
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    print(rig.pr(e, 'pr mine start', 'pr mine', timeout=20)); time.sleep(0.5)
    c = rig.pr(e, 'pr mine c2s', 'pr mine c2s'); cx, cy = map(int, c.split()[3:5]); print(c)
    e.shot('/home/wm/pe2-311/work/m0.png')
    from PIL import Image
    im = Image.open('/home/wm/pe2-311/work/m0.png').convert('RGB')
    # first grid line: scan right from client origin along a row 100 px down for the (255,255,255) cell highlight after a dark edge
    y = cy + 100; xs = [x for x in range(cx, cx + 60) if im.getpixel((x, y)) == (255, 255, 255)]
    yv = [yy for yy in range(cy, cy + 120) if im.getpixel((cx + 30, yy)) == (255, 255, 255)]
    print('white x', xs[:6], 'white y', yv[:12])
    X0 = xs[0] - cx; 
    # board top: the first white run after the counters panel: find rows where the white top edge of cells repeat every 16
    for yy in yv:
        if all(im.getpixel((cx + 30, yy + 16 * k)) == (255, 255, 255) for k in range(4)): Y0 = yy - cy; break
    X0, Y0 = 12, 55; print('board origin in client (from the screenshot grid)', X0, Y0)
    rig.pr(e, 'pr mine cmd 521', 'pr mine cmd'); time.sleep(0.3); b = dump('b_new')
    B = board(b, 9, 9)
    mines = [(c_, r) for r in range(1, 10) for c_ in range(1, 10) if B[r][c_] & 0x80]
    safe = [(c_, r) for r in range(1, 10) for c_ in range(1, 10) if not B[r][c_] & 0x80]
    print('mines', mines)
    click(*safe[0]); dump('b_open1')
    nm = next(p for p in safe[1:] if not (board(bytes.fromhex(dumps['b_open1']['hex']), 9, 9)[p[1]][p[0]] & 0x40))
    click(*nm, 1); dump('b_flag_safe')         # a flag on a safe cell (becomes a wrong flag at the loss)
    click(*mines[0], 1); dump('b_flag_mine')
    click(*mines[0], 1); dump('b_q_mine')       # second right click: ? (if Marks on)
    click(*mines[1], 1); click(*mines[1], 1); click(*mines[1], 1); dump('b_cycle3')   # flag, ?, hidden
    click(*mines[2]); dump('b_lost')
    # a won game
    rig.pr(e, 'pr mine cmd 510', 'pr mine cmd'); time.sleep(0.5); b = dump('b_new2'); B2 = board(b, 9, 9)
    for r in range(1, 10):
        for c_ in range(1, 10):
            if not (B2[r][c_] & 0x80): click(c_, r)
    time.sleep(1.0); dump('b_won'); e.tap('enter'); time.sleep(0.5); e.shot('/home/wm/pe2-311/work/afterwon.png')
    for lvl, w, h, tag in ((522, 16, 16, 'i'), (523, 30, 16, 'x')):
        rig.pr(e, 'pr mine cmd %d' % lvl, 'pr mine cmd'); time.sleep(0.3); dump(tag + '_new')
        click(1, 1); dump(tag + '_open')
except Exception as ex:
    print('EXC', ex); e.shot('/home/wm/pe2-311/work/fail.png'); print([t for t in e.texts[-6:]])
finally: e.close()
dumps.pop('tmp', None)
json.dump(dumps, open('/home/wm/pe2-evidence/311/t8_dumps.json', 'w'))

#!/usr/bin/env python3
"""Install SNDWAVE1993 Help on a Windows for Workgroups 3.11 C: drive (a folder), before the machine is packed.

    install311.py DRIVE [HLP]        HLP defaults to ../out/SNDWAVE.HLP

It does what Setup programs of 1993 did, but from the host, so it needs no run inside Windows:
  - copies the help file to DRIVE\\BS\\SNDWAVE.HLP (beside SYNTH.EXE);
  - writes a Program Manager group, DRIVE\\WINDOWS\\SNDWAVE.GRP, "SNDWAVE1993", with one item,
    "SNDWAVE1993 Help" = WINHELP.EXE C:\\BS\\SNDWAVE.HLP, with WINHELP.EXE's own icon;
  - adds it to PROGMAN.INI ([Groups] GroupN=, [Settings] Order=), so Program Manager shows it.
Running it again replaces the files and does not add a second group.

The group file follows the Windows 3.1 format (PMCC): a header, one item, its icon in the display's format, and the
3.1 tag section. Program Manager compares the group's icon format with the display's; when they differ it takes the
icons again from the programs. So the icon is stored as a 32x32 monochrome image and Program Manager draws WINHELP.EXE's
real icon (checked on WfW 3.11 with the S3 64K-colour driver).
"""
import os
import re
import shutil
import struct
import sys

GROUP_NAME = 'SNDWAVE1993'
ITEM_NAME = 'SNDWAVE1993 Help'
ITEM_CMD = r'WINHELP.EXE C:\BS\SNDWAVE.HLP'
ICON_PATH = r'C:\WINDOWS\WINHELP.EXE'
GRP = 'SNDWAVE.GRP'


def find(d, name):
    """case-insensitive lookup of name in folder d (the drive may come from a case-sensitive file system)"""
    for n in os.listdir(d):
        if n.upper() == name.upper():
            return os.path.join(d, n)
    return os.path.join(d, name)


def group_file(items=None):
    """items: [(name, command, icon path)]; the default is the Help item alone"""
    items = items or [(ITEM_NAME, ITEM_CMD, ICON_PATH)]
    def sz(s):
        return s.encode('cp1252') + b'\0'
    n_items = len(items)
    hdr_len = 34 + 2 * n_items
    name_off = hdr_len
    body = bytearray(sz(GROUP_NAME))
    if (hdr_len + len(body)) % 2: body += b'\0'
    offs = []
    for k, (name, cmd, icon) in enumerate(items):
        # an item, then its strings and icon (32x32: AND mask 128 bytes, XOR image 128 bytes at 1 bit per pixel)
        item_off = hdr_len + len(body)
        offs.append(item_off)
        p = item_off + 24
        p_name = p; p += len(sz(name))
        p_cmd = p; p += len(sz(cmd))
        p_icon = p; p += len(sz(icon))
        if p % 2: p += 1
        p_hdr = p; p += 12
        p_and = p; p += 128
        p_xor = p; p += 128
        x, y = 21 + 75 * (k % 5), 0 + 70 * (k // 5)
        item = struct.pack('<hhHHHHHHHHHH', x, y, 0, 12, 128, 128, p_hdr, p_and, p_xor, p_name, p_cmd, p_icon)
        data = bytearray(item) + sz(name) + sz(cmd) + sz(icon)
        if (item_off + len(data)) % 2: data += b'\0'
        data += struct.pack('<HHHHHBB', 16, 16, 32, 32, 4, 1, 1)
        data += b'\0' * 128            # AND mask: all of it drawn
        data += b'\xff' * 128          # XOR: white (Program Manager replaces it with the icon file's own)
        body += data
    cb_group = hdr_len + len(body)
    tags = struct.pack('<HHH', 0x8000, 0xFFFF, 10) + b'PMCC' + struct.pack('<HHH', 0xFFFF, 0xFFFF, 0)
    head = b'PMCC' + struct.pack('<HHH', 0, cb_group, 1)          # checksum filled below; nCmdShow SW_SHOWNORMAL
    head += struct.pack('<hhhh', 60, 60, 460, 260)                # rcNormal
    head += struct.pack('<hh', -1, -1)                            # ptMin: Program Manager places the icon
    head += struct.pack('<HHHBBHH', name_off, 32, 32, 1, 1, 0, n_items)
    for o in offs: head += struct.pack('<H', o)
    f = bytearray(head + body + tags)
    if len(f) % 2: f += b'\0'
    s = sum(struct.unpack('<%dH' % (len(f) // 2), f)) & 0xFFFF
    struct.pack_into('<H', f, 4, (-s) & 0xFFFF)                    # all words of the file sum to 0, as in WfW's own
    return bytes(f)


def edit_progman(path):
    b = open(path, 'rb').read().decode('cp1252')
    nl = '\r\n'
    lines = b.replace('\r\n', '\n').split('\n')
    grp_line = 'C:\\WINDOWS\\' + GRP
    groups = {}
    for ln in lines:
        m = re.match(r'(?i)group(\d+)=(.*)', ln.strip())
        if m:
            groups[int(m.group(1))] = m.group(2).strip()
    have = [k for k, v in groups.items() if v.upper() == grp_line.upper()]
    if have:
        num = have[0]
    else:
        num = max(groups or {0: ''}) + 1
        for i, ln in enumerate(lines):
            if ln.strip().lower() == '[groups]':
                j = i + 1
                while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('['):
                    j += 1
                lines.insert(j, 'Group%d=%s' % (num, grp_line))
                break
        else:
            lines += ['[Groups]', 'Group%d=%s' % (num, grp_line)]
    for i, ln in enumerate(lines):          # Order= lists groups back to front: the last one is the active window
        m = re.match(r'(?i)order=(.*)', ln.strip())
        if m:
            order = [x for x in m.group(1).split() if x != str(num)]
            lines[i] = 'Order= ' + ' '.join(order + [str(num)])
    out = nl.join(lines)
    open(path, 'wb').write(out.encode('cp1252'))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    drive = sys.argv[1]
    hlp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out',
                                                                'SNDWAVE.HLP')
    win = find(drive, 'WINDOWS')
    if not os.path.isfile(find(win, 'WINHELP.EXE')):
        sys.exit('install311: %s has no WINDOWS\\WINHELP.EXE' % drive)
    bs = find(drive, 'BS')
    os.makedirs(bs, exist_ok=True)
    shutil.copyfile(hlp, os.path.join(bs, 'SNDWAVE.HLP'))
    items = None
    if os.path.isfile(find(bs, 'SNDWAVE.ICO')):   # the brand kit's icons (make_machine.py copies them): the whole group
        items = [('SNDWAVE1993', r'C:\BS\SNDWAVE.EXE', r'C:\BS\SNDWAVE.ICO'),
                 ('16 Recorders', r'C:\BS\SNDWAVE.EXE /recorders', r'C:\BS\RECORDRS.ICO'),
                 ('Voice Mixer', r'C:\BS\SNDWAVE.EXE /voices', r'C:\BS\MIXER.ICO'),
                 ('Read Me', r'NOTEPAD.EXE C:\BS\README.TXT', r'C:\BS\README.ICO'),
                 ('Setup', r'C:\BS\SNDWAVE.EXE /setup', r'C:\BS\SETUP.ICO'),
                 ] + ([('CITYPOP1993', r'C:\BS\CITYPOP.EXE', r'C:\BS\CITYPOP.ICO')] if os.path.isfile(find(bs, 'CITYPOP.ICO')) else []) + [
                 (ITEM_NAME, ITEM_CMD, ICON_PATH)]
    open(os.path.join(win, GRP), 'wb').write(group_file(items))
    edit_progman(find(win, 'PROGMAN.INI'))
    print('install311: SNDWAVE.HLP in %s, group %s' % (bs, GRP))


if __name__ == '__main__':
    main()

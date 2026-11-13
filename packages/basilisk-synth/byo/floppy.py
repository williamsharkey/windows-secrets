#!/usr/bin/env python3
"""Write a 1.44 MB FAT12 floppy image with files in its root folder (no tools needed on the host).

    floppy.py OUT.img FILE [FILE ...] [--label NAME]

The XP build puts WINNT.SIF on such a floppy: XP Setup, booted from the CD, reads A:\\WINNT.SIF and runs unattended
("the Winnt.sif answer file must be available on a floppy disk", Microsoft, Deploying Windows XP Part II). The ISO
the person brings is never changed. The 3.11 build can carry SETUP.SHH the same way.
"""
import argparse
import os
import struct
import time

SECTORS, BPS, SPC, RES, NFATS, ROOT, SPF, SPT, HEADS = 2880, 512, 1, 1, 2, 224, 9, 18, 2


def short_name(name):
    base, _, ext = os.path.basename(name).upper().rpartition('.')
    if not base:
        base, ext = ext, ''
    if len(base) > 8 or len(ext) > 3 or not base:
        raise ValueError('not an 8.3 name: %s' % name)
    return base.ljust(8).encode('ascii') + ext.ljust(3).encode('ascii')


def make(files, label='BSYNTH'):
    """files: list of (name, bytes). Returns the image bytes."""
    img = bytearray(SECTORS * BPS)
    bs = bytearray(512)
    bs[0:3] = b'\xEB\x3C\x90'
    bs[3:11] = b'BSYNTH  '
    struct.pack_into('<HBHBHHBHHHII', bs, 11, BPS, SPC, RES, NFATS, ROOT, SECTORS, 0xF0, SPF, SPT, HEADS, 0, 0)
    bs[36] = 0
    bs[38] = 0x29
    struct.pack_into('<I', bs, 39, int(time.time()) & 0xFFFFFFFF)
    bs[43:54] = label.upper()[:11].ljust(11).encode('ascii')
    bs[54:62] = b'FAT12   '
    bs[510:512] = b'\x55\xAA'
    img[0:512] = bs
    fat = bytearray(SPF * BPS)

    def setfat(c, v):
        o = c * 3 // 2
        if c & 1:
            fat[o] = (fat[o] & 0x0F) | ((v << 4) & 0xF0)
            fat[o + 1] = (v >> 4) & 0xFF
        else:
            fat[o] = v & 0xFF
            fat[o + 1] = (fat[o + 1] & 0xF0) | ((v >> 8) & 0x0F)
    setfat(0, 0xFF0)
    setfat(1, 0xFFF)
    root_off = (RES + NFATS * SPF) * BPS
    data_off = root_off + ROOT * 32
    root = bytearray(ROOT * 32)
    ent = 0
    lab = bytearray(32)
    lab[0:11] = label.upper()[:11].ljust(11).encode('ascii')
    lab[11] = 0x08
    root[0:32] = lab
    ent = 1
    cluster = 2
    t = time.localtime()
    dtime = (t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2)
    ddate = ((t.tm_year - 1980) << 9) | (t.tm_mon << 5) | t.tm_mday
    for name, data in files:
        n = (len(data) + BPS * SPC - 1) // (BPS * SPC)
        first = cluster if n else 0
        if data_off + (cluster + n - 2) * BPS * SPC > len(img) or ent >= ROOT:
            raise ValueError('files do not fit on a 1.44 MB floppy')
        for i in range(n):
            setfat(cluster + i, cluster + i + 1 if i < n - 1 else 0xFFF)
            off = data_off + (cluster + i - 2) * BPS * SPC
            chunk = data[i * BPS * SPC:(i + 1) * BPS * SPC]
            img[off:off + len(chunk)] = chunk
        cluster += n
        e = bytearray(32)
        e[0:11] = short_name(name)
        e[11] = 0x20
        struct.pack_into('<HHH', e, 22, dtime, ddate, first)
        struct.pack_into('<I', e, 28, len(data))
        root[ent * 32:ent * 32 + 32] = e
        ent += 1
    for i in range(NFATS):
        img[(RES + i * SPF) * BPS:(RES + (i + 1) * SPF) * BPS] = fat
    img[root_off:root_off + len(root)] = root
    return bytes(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('files', nargs='+')
    ap.add_argument('--label', default='BSYNTH')
    a = ap.parse_args()
    data = make([(f, open(f, 'rb').read()) for f in a.files], a.label)
    open(a.out, 'wb').write(data)


if __name__ == '__main__':
    main()

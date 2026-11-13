#!/usr/bin/env python3
"""Recognize Windows install media that a person brings to BASILISK SYNTH (XP) or BASILISK 16 (3.11).

    media_id.py PATH_OR_URL [--hash] [--json]

A prototype for design/BYO-IMAGE.md. The plugin is to do the same in C++. The rules:

  - Known media are recognized by size + SHA-1 (+ MD5) from known_media.json. SHA-1 and MD5 are what Microsoft's
    MSDN listings and archive.org publish; the plugin computes SHA-256 too and stores it beside the build.
  - Unknown media are recognized by their contents, not by their container: an ISO 9660 CD is read for its volume
    label and the XP tag files (WIN51, WIN51IP, WIN51IP.SP3, ...) and I386\\SETUPP.INI (the Pid gives the channel:
    retail, OEM or volume license). A FAT12 floppy image is read for its label and root directory (WfW 3.11 disk 1
    has SETUP.EXE, SETUP.SHH, WFWSETUP.DL_, KRNL386.EX_ ...). A .zip of floppy images or of flat setup files is
    opened and each member is read the same way.
  - A URL is read with HTTP range requests only (a few kilobytes), so the editor can say what a link is before it
    downloads hundreds of megabytes. archive.org links are also checked against the item's published SHA-1.

Nothing here writes to the media. No product key is read, stored or printed.
"""
import argparse
import hashlib
import io
import json
import os
import re
import struct
import sys
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
UA = 'basilisk-byo-media-id/0.1'


# ---------------------------------------------------------------- byte sources: a local file or an HTTP range reader

class LocalSource:
    def __init__(self, path):
        self.name = path
        self.f = open(path, 'rb')
        self.size = os.path.getsize(path)

    def read(self, off, n):
        self.f.seek(off)
        return self.f.read(n)


class HttpSource:
    """reads byte ranges of a URL; counts what it fetched so a probe stays small"""
    def __init__(self, url, budget=1 << 20):
        self.name = url
        self.url = url
        self.fetched = 0
        self.budget = budget
        self.cache = {}
        r = self._get(0, 0)
        cr = r.headers.get('Content-Range', '')
        m = re.match(r'bytes \d+-\d+/(\d+)', cr)
        if r.status != 206 or not m:
            raise IOError('the server does not answer range requests (HTTP %d); the plugin can still download it, '
                          'but cannot check it first or resume it' % r.status)
        self.size = int(m.group(1))
        self.final_url = r.url

    def _get(self, a, b):
        req = urllib.request.Request(self.url, headers={'Range': 'bytes=%d-%d' % (a, b), 'User-Agent': UA})
        r = urllib.request.urlopen(req, timeout=60)
        r.body = r.read()
        self.fetched += len(r.body)
        return r

    def read(self, off, n):
        if n <= 0 or off >= self.size:
            return b''
        n = min(n, self.size - off)
        key = (off, n)
        if key not in self.cache:
            if self.fetched + n > self.budget:
                raise IOError('probe budget exceeded (%d bytes)' % self.budget)
            self.cache[key] = self._get(off, off + n - 1).body
        return self.cache[key]


class BytesSource:
    def __init__(self, name, data):
        self.name, self.data, self.size = name, data, len(data)

    def read(self, off, n):
        return self.data[off:off + n]


# ---------------------------------------------------------------- ISO 9660

class Iso:
    SECTOR = 2048

    def __init__(self, src):
        self.src = src
        pvd = src.read(16 * self.SECTOR, self.SECTOR)
        if len(pvd) < 2048 or pvd[0] != 1 or pvd[1:6] != b'CD001':
            raise ValueError('not an ISO 9660 image')
        self.volume = pvd[40:72].decode('latin1').strip()
        self.blocks = struct.unpack_from('<I', pvd, 80)[0]
        self.created = pvd[813:827].decode('latin1')
        self.root = self._rec(pvd[156:190])

    @staticmethod
    def _rec(b):
        lba, ln = struct.unpack_from('<I', b, 2)[0], struct.unpack_from('<I', b, 10)[0]
        flags, nl = b[25], b[32]
        name = b[33:33 + nl].decode('latin1')
        return {'lba': lba, 'len': ln, 'dir': bool(flags & 2), 'name': name.split(';')[0].rstrip('.')}

    def listdir(self, d):
        data = self.src.read(d['lba'] * self.SECTOR, d['len'])
        out, i = [], 0
        while i < len(data):
            n = data[i]
            if n == 0:          # records never cross a sector: skip to the next one
                i = (i // self.SECTOR + 1) * self.SECTOR
                continue
            r = self._rec(data[i:i + n])
            if r['name'] not in ('\x00', '\x01'):
                out.append(r)
            i += n
        return out

    def find(self, path):
        cur = self.root
        for part in path.upper().strip('/').split('/'):
            hit = [e for e in self.listdir(cur) if e['name'].upper() == part]
            if not hit:
                return None
            cur = hit[0]
        return cur

    def read_file(self, path, limit=1 << 16):
        e = self.find(path)
        if not e or e['dir']:
            return None
        return self.src.read(e['lba'] * self.SECTOR, min(e['len'], limit))


# Pid in I386\SETUPP.INI: the first five digits are the product, the last three the channel (Microsoft's own
# convention as documented by the unattended-install community; "OEM" is literal in OEM media).
def xp_channel(pid):
    if 'OEM' in pid.upper():
        return 'oem'
    tail = pid[-3:]
    return {'000': 'retail', '270': 'volume', '335': 'retail-upgrade'}.get(tail, 'unknown (%s)' % tail)


def identify_iso(src):
    iso = Iso(src)
    r = {'container': 'iso9660', 'volume': iso.volume, 'created': iso.created}
    top = {e['name'].upper(): e for e in iso.listdir(iso.root)}
    tags = sorted(n for n in top if n.startswith('WIN51'))
    if 'I386' not in top or not tags:
        r['kind'] = 'unknown-cd'
        r['note'] = 'not a Windows XP CD (no I386 folder or WIN51 tag files)'
        return r
    r['kind'] = 'windows-xp-cd'
    r['tags'] = tags
    r['edition'] = 'professional' if any(t.startswith('WIN51IP') for t in tags) else \
                   'home' if any(t.startswith('WIN51IC') for t in tags) else 'other (%s)' % ','.join(tags)
    sp = [t.rsplit('.', 1)[-1] for t in tags if '.SP' in t]
    r['service_pack'] = max(sp) if sp else 'SP0'
    ini = iso.read_file('I386/SETUPP.INI', 4096)
    if ini:
        m = re.search(rb'Pid=(\w+)', ini)
        if m:
            r['pid'] = m.group(1).decode()
            r['channel'] = xp_channel(r['pid'])
    r['x64'] = 'AMD64' in top
    problems = []
    if r['x64']:
        problems.append('x64 media: BASILISK SYNTH needs 32-bit (x86) Windows XP')
    if r['service_pack'] < 'SP2':
        problems.append('Service Pack 2 or later is needed (Sound Recorder plays the SP2 sounds, e.g. '
                        '"Windows XP Information Bar.wav"); SP3 media is recommended')
    r['problems'] = problems
    return r


# ---------------------------------------------------------------- FAT12 floppy images

FLOPPY_SIZES = {368640: '360K', 737280: '720K', 1228800: '1.2M', 1474560: '1.44M', 1720320: 'DMF 1.68M',
                1763328: 'DMF 1.72M', 2949120: '2.88M'}


class Fat12:
    def __init__(self, src):
        self.src = src
        b = src.read(0, 512)
        if len(b) < 512:
            raise ValueError('too small for a floppy')
        bps, spc, res, nf, ne = struct.unpack_from('<HBHBH', b, 11)
        spf = struct.unpack_from('<H', b, 22)[0]
        if bps not in (512, 1024) or spc == 0 or nf not in (1, 2) or spf == 0:
            raise ValueError('no FAT12 boot sector')
        self.bps, self.spc, self.res, self.nf, self.ne, self.spf = bps, spc, res, nf, ne, spf
        self.oem = b[3:11].decode('latin1').strip()
        self.fat = src.read(res * bps, spf * bps)
        self.root_off = (res + nf * spf) * bps
        self.data_off = self.root_off + ((ne * 32 + bps - 1) // bps) * bps
        self.label, self.files = None, []
        root = src.read(self.root_off, ne * 32)
        for i in range(ne):
            e = root[32 * i:32 * i + 32]
            if len(e) < 32 or e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] == 0x0F:
                continue
            base, ext = e[:8].decode('latin1').rstrip(), e[8:11].decode('latin1').rstrip()
            if e[11] & 0x08:
                self.label = (base + ext).strip()
                continue
            if e[11] & 0x10:
                continue
            self.files.append({'name': base + ('.' + ext if ext else ''), 'cluster': struct.unpack_from('<H', e, 26)[0],
                               'size': struct.unpack_from('<I', e, 28)[0]})

    def _next(self, c):
        o = c * 3 // 2
        v = self.fat[o] | (self.fat[o + 1] << 8)
        return (v >> 4) if c & 1 else (v & 0xFFF)

    def read(self, f):
        out, c, csz = bytearray(), f['cluster'], self.bps * self.spc
        while 2 <= c < 0xFF0 and len(out) < f['size']:
            out += self.src.read(self.data_off + (c - 2) * csz, csz)
            c = self._next(c)
        return bytes(out[:f['size']])


WFW_DISK1 = {'SETUP.EXE', 'SETUP.INF', 'WFWSETUP.DL_', 'KRNL386.EX_'}


def identify_floppy(src):
    fat = Fat12(src)
    names = {f['name'].upper() for f in fat.files}
    r = {'container': 'fat12', 'format': FLOPPY_SIZES.get(src.size, '%d bytes' % src.size), 'label': fat.label,
         'files': len(names)}
    marker = [n for n in names if re.match(r'DISK\d+$', n.split('.')[0])]
    if WFW_DISK1 <= names:
        r['kind'] = 'wfw311-disk1'
        inf = fat.read([f for f in fat.files if f['name'].upper() == 'SETUP.INF'][0])
        m = re.search(rb'(Windows for Workgroups[^\r\n"]*3\.11[^\r\n"]*)', inf)
        r['setup_inf_title'] = m.group(1).decode('latin1') if m else None
        r['has_setup_shh'] = 'SETUP.SHH' in names
        r['has_svga256'] = 'SVGA256.DR_' in names
    elif marker:
        r['kind'] = 'setup-floppy'
        r['disk'] = marker[0]
    else:
        r['kind'] = 'unknown-floppy'
    r['names'] = sorted(names)
    return r


# ---------------------------------------------------------------- zip (floppy set or flat folder)

def identify_zip(path):
    z = zipfile.ZipFile(path)
    members = [i for i in z.infolist() if not i.is_dir()]
    r = {'container': 'zip', 'members': len(members), 'disks': []}
    flat = {os.path.basename(i.filename).upper() for i in members}
    for i in members:
        if i.file_size in FLOPPY_SIZES and i.filename.lower().endswith(('.img', '.ima', '.vfd', '.flp')):
            try:
                d = identify_floppy(BytesSource(i.filename, z.read(i)))
                d['member'] = i.filename
                d.pop('names', None)
                r['disks'].append(d)
            except ValueError:
                pass
    if any(d['kind'] == 'wfw311-disk1' for d in r['disks']):
        r['kind'] = 'wfw311-floppy-set'
    elif WFW_DISK1 <= flat:
        r['kind'] = 'wfw311-flat-files'
    else:
        r['kind'] = 'unknown-zip'
    return r


# ---------------------------------------------------------------- known media table and hashing

def load_known():
    return json.load(open(os.path.join(HERE, 'known_media.json')))['media']


def match_known(size, sha1=None, md5=None):
    for m in load_known():
        if m['size'] == size and (sha1 is None or m.get('sha1') == sha1) and (md5 is None or m.get('md5') == md5):
            return m
    return None


def file_hashes(path):
    h = {'sha1': hashlib.sha1(), 'md5': hashlib.md5(), 'sha256': hashlib.sha256()}
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            for x in h.values():
                x.update(b)
    return {k: v.hexdigest() for k, v in h.items()}


def archive_org_sha1(url):
    """https://archive.org/download/<item>/<file> -> the item's published size and SHA-1 for that file"""
    p = urllib.parse.urlparse(url)
    if p.hostname not in ('archive.org', 'www.archive.org'):
        return None
    parts = urllib.parse.unquote(p.path).split('/')
    if len(parts) < 4 or parts[1] != 'download':
        return None
    item, name = parts[2], '/'.join(parts[3:])
    req = urllib.request.Request('https://archive.org/metadata/%s' % urllib.parse.quote(item), headers={'User-Agent': UA})
    meta = json.load(urllib.request.urlopen(req, timeout=60))
    for f in meta.get('files', []):
        if f.get('name') == name:
            return {'item': item, 'file': name, 'size': int(f.get('size', 0)), 'sha1': f.get('sha1'), 'md5': f.get('md5')}
    return None


# ---------------------------------------------------------------- top level

def identify(target, do_hash=False):
    r = {'input': target}
    remote = re.match(r'https?://', target) is not None
    if remote:
        p = urllib.parse.urlparse(target)
        if p.scheme != 'https':
            r['warning'] = 'not https: the plugin accepts plain http only with a known hash'
        src = HttpSource(target)
        ia = archive_org_sha1(target)
        if ia:
            r['archive_org'] = ia
            k = match_known(ia['size'], ia['sha1'])
            if k:
                r['known'] = k
    else:
        src = LocalSource(target)
    r['size'] = src.size
    if not remote and do_hash:
        r['hashes'] = file_hashes(target)
        k = match_known(src.size, r['hashes']['sha1'])
        if k:
            r['known'] = k
    if 'known' not in r:
        cand = [m for m in load_known() if m['size'] == src.size]
        if cand:
            r['size_matches'] = [m['id'] for m in cand]
    lower = target.lower().split('?')[0]
    try:
        if lower.endswith('.zip') and not remote:
            r.update(identify_zip(target))
        elif src.size in FLOPPY_SIZES:
            r.update(identify_floppy(src))
        else:
            head = src.read(0, 2)
            if head == b'MZ':
                r['container'] = 'pe-exe'
                r['kind'] = r.get('known', {}).get('kind', 'unknown-exe')
            elif src.read(src.size - 512, 8) == b'conectix' or head == b'co':
                r['container'] = 'vhd'
                r['kind'] = 'vhd'
            else:
                r.update(identify_iso(src))
    except (ValueError, struct.error) as e:
        r['kind'] = 'unrecognized'
        r['note'] = str(e)
    if remote:
        r['probe_bytes'] = src.fetched
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--hash', action='store_true', help='hash a local file in full (SHA-1, MD5, SHA-256)')
    a = ap.parse_args()
    print(json.dumps(identify(a.target, a.hash), indent=1))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""sound_archaeology.py - find and extract the sounds inside a classic Windows image.

The tool reads YOUR OWN machine image. It never writes to that image.
It finds these sounds:

- loose sound files (.wav .mid .rmi .dls .voc .au .snd .aif),
- WAVE / MIDI / RIFF blobs inside resources of PE (32-bit) and NE (16-bit) programs,
- RIFF / MIDI / VOC blobs at any offset in any file (data files, help files, drivers),
- the same inside .cab archives and MS-COMPRESS (SZDD, "*.??_") files,
- the separate instrument waves inside DLS collections (gm.dls).

Sources (any mix):
    qcow2 or raw disk images with NTFS or FAT partitions   (needs: pip install dissect.ntfs dissect.fat dissect.hypervisor)
    a folder tree (for example the Windows 3.11 drive folder)
    a .zip / .jsdos bundle

Commands:
    scan    SOURCE... --label xp --csv out.csv       write the catalog
    extract SOURCE... --csv out.csv --ids ids.txt --out DIR
                                                     write the chosen sounds as plain PCM .wav files
                                                     that both Sound Recorders can open

Other tools: cabextract on PATH for .cab files (optional).
Licence: CC0 (the tool). The sounds belong to their owners: do not commit them.
"""
import argparse, csv, hashlib, io, math, os, re, shutil, struct, subprocess, sys, tempfile, zipfile

try:
    import numpy as np
except ImportError:  # the measurements need numpy; the scan still runs without it
    np = None

# --------------------------------------------------------------------------- sources

class Entry:
    __slots__ = ("path", "size", "_read")
    def __init__(self, path, size, read):
        self.path, self.size, self._read = path, size, read
    def read(self):
        return self._read()


def _partitions(stream, disk_size):
    stream.seek(0)
    mbr = stream.read(512)
    parts = []
    if mbr[510:512] == b"\x55\xaa":
        for i in range(4):
            e = mbr[446 + 16 * i: 462 + 16 * i]
            ptype = e[4]
            lba, cnt = struct.unpack("<II", e[8:16])
            if ptype and cnt:
                parts.append((lba * 512, cnt * 512, ptype))
    if not parts:
        parts.append((0, disk_size, 0))
    return parts


class _Sub(io.RawIOBase):
    """A window [start, start+size) onto a seekable stream."""
    def __init__(self, base, start, size):
        self.base, self.start, self.sz, self.pos = base, start, size, 0
    def readable(self): return True
    def seekable(self): return True
    def seek(self, o, w=0):
        self.pos = o if w == 0 else self.pos + o if w == 1 else self.sz + o
        return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.sz - self.pos
        n = max(0, min(n, self.sz - self.pos))
        self.base.seek(self.start + self.pos)
        d = self.base.read(n)
        self.pos += len(d)
        return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


def _disk_stream(path):
    f = open(path, "rb")
    head = f.read(4); f.seek(0)
    if head == b"QFI\xfb":
        from dissect.hypervisor.disk import qcow2
        q = qcow2.QCow2(f)
        return q.open(), q.size
    f.seek(0, 2); size = f.tell(); f.seek(0)
    return f, size


def walk_ntfs(sub):
    from dissect.ntfs import NTFS
    fs = NTFS(sub)
    stack, seen = [("", fs.mft.get("\\"))], set()
    while stack:
        path, d = stack.pop()
        groups = {}
        for name, e in d.listdir().items():
            if name in (".", "..") or (path == "" and name.startswith("$")):
                continue
            try:
                seg = e.dereference().segment
            except Exception:
                continue
            if seg not in groups or len(name) > len(groups[seg][0]):
                groups[seg] = (name, e)   # keep the long name, drop the 8.3 alias
        for seg, (name, e) in groups.items():
            if seg in seen:
                continue
            seen.add(seg)
            try:
                r = e.dereference()
                p = path + "\\" + name
                if r.is_dir():
                    stack.append((p, r))
                else:
                    yield Entry(p, r.size(), (lambda r=r: r.open().read()))
            except Exception as ex:
                print("warn: %s\\%s: %s" % (path, name, ex), file=sys.stderr)


def walk_fat(sub):
    from dissect.fat import FATFS
    fs = FATFS(sub)
    def rec(d, path):
        for e in d.iterdir():
            n = e.name
            if n in (".", ".."):
                continue
            p = path + "\\" + n
            if e.is_directory():
                yield from rec(e, p)
            else:
                yield Entry(p, e.size, (lambda e=e: e.open().read()))
    yield from rec(fs.root, "")


def walk_disk(path):
    base, size = _disk_stream(path)
    for start, length, ptype in _partitions(base, size):
        sub = _Sub(base, start, length)
        sub.seek(0); boot = sub.read(512)
        if boot[3:11] == b"NTFS    ":
            yield from walk_ntfs(sub)
        elif b"FAT" in boot[0x36:0x3e] or b"FAT32" in boot[0x52:0x5a]:
            yield from walk_fat(sub)


def walk_dir(root):
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for n in sorted(fn):
            full = os.path.join(dp, n)
            rel = "\\" + os.path.relpath(full, root).replace("/", "\\")
            try:
                sz = os.path.getsize(full)
            except OSError:
                continue
            yield Entry(rel, sz, (lambda full=full: open(full, "rb").read()))


def walk_zip(path):
    z = zipfile.ZipFile(path)
    for i in z.infolist():
        if i.is_dir():
            continue
        yield Entry("\\" + i.filename.replace("/", "\\"), i.file_size, (lambda i=i: z.read(i)))


def walk_source(src):
    if os.path.isdir(src):
        return walk_dir(src)
    if zipfile.is_zipfile(src):
        return walk_zip(src)
    return walk_disk(src)

# --------------------------------------------------------------------------- containers

def szdd_expand(data):
    """MS-COMPRESS 'SZDD' (the EXPAND.EXE format of *.??_ files on Windows 3.x / 9x / NT disks)."""
    if data[:8] != b"SZDD\x88\xf0\x27\x33":
        return None
    out_len = struct.unpack("<I", data[10:14])[0]
    win = bytearray(b" " * 4096); wp = 4096 - 16
    out = bytearray(); i = 14; n = len(data)
    while i < n and len(out) < out_len:
        ctl = data[i]; i += 1
        for bit in range(8):
            if i >= n or len(out) >= out_len:
                break
            if ctl & (1 << bit):
                c = data[i]; i += 1
                out.append(c); win[wp] = c; wp = (wp + 1) & 4095
            else:
                if i + 1 >= n:
                    i = n; break
                a, b = data[i], data[i + 1]; i += 2
                pos = a | ((b & 0xF0) << 4); ln = (b & 0x0F) + 3
                for k in range(ln):
                    c = win[(pos + k) & 4095]
                    out.append(c); win[wp] = c; wp = (wp + 1) & 4095
    return bytes(out)


def _sevenz():
    for n in (os.environ.get("SA_7Z"), "7z", "7zz", "7za"):
        if n and shutil.which(n):
            return shutil.which(n)
    return None


def sevenz_members(data, suffix):
    """Yield (name, bytes) for every member of a CHM / MSI / other 7-Zip readable archive."""
    z = _sevenz()
    if not z:
        print("warn: 7z not on PATH; %s skipped" % suffix, file=sys.stderr)
        return
    with tempfile.TemporaryDirectory(dir=os.environ.get("SA_TMP")) as td:
        arc = os.path.join(td, "x" + suffix)
        open(arc, "wb").write(data)
        out = os.path.join(td, "o")
        r = subprocess.run([z, "x", "-y", "-bd", "-o" + out, arc], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.unlink(arc)
        if r.returncode and not os.path.isdir(out):
            print("warn: 7z failed on %s member: %s" % (suffix, r.stderr.decode(errors="replace")[:200].strip()),
                  file=sys.stderr)
        for dp, dn, fn in os.walk(out):
            for n in sorted(fn):
                full = os.path.join(dp, n)
                yield os.path.relpath(full, out).replace("/", "\\"), open(full, "rb").read()
                os.unlink(full)


def zip_members(data):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        for i in z.infolist():
            if not i.is_dir() and i.file_size < 64 << 20:
                yield i.filename.replace("/", "\\"), z.read(i)
    except Exception:
        return


def cab_members(data):
    """Yield (name, bytes) for every member of a .cab, through cabextract."""
    if not shutil.which("cabextract"):
        print("warn: cabextract not on PATH; .cab skipped", file=sys.stderr)
        return
    with tempfile.TemporaryDirectory(dir=os.environ.get("SA_TMP")) as td:
        cab = os.path.join(td, "x.cab")
        open(cab, "wb").write(data)
        out = os.path.join(td, "o")
        subprocess.run(["cabextract", "-q", "-d", out, cab], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.unlink(cab)
        for dp, dn, fn in os.walk(out):
            for n in sorted(fn):
                full = os.path.join(dp, n)
                yield os.path.relpath(full, out).replace("/", "\\"), open(full, "rb").read()
                os.unlink(full)

# --------------------------------------------------------------------------- resources

RT_NAMES = {1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU", 5: "DIALOG", 6: "STRING", 7: "FONTDIR", 8: "FONT",
            9: "ACCELERATOR", 10: "RCDATA", 11: "MESSAGETABLE", 12: "GROUP_CURSOR", 14: "GROUP_ICON",
            16: "VERSION", 23: "HTML", 24: "MANIFEST"}


def pe_resources(data):
    """List of (type, name, lang, offset, size) for a PE file, or None."""
    try:
        import pefile
    except ImportError:
        return None
    try:
        pe = pefile.PE(data=data, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    except Exception:
        return None
    out = []
    root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    if not root:
        return out
    def nm(e):
        return str(e.name) if e.name is not None else (RT_NAMES.get(e.id, str(e.id)) if e is not None else "?")
    for t in root.entries:
        tname = str(t.name) if t.name is not None else RT_NAMES.get(t.id, str(t.id))
        for n in getattr(t, "directory", None) and t.directory.entries or []:
            nname = str(n.name) if n.name is not None else str(n.id)
            for l in getattr(n, "directory", None) and n.directory.entries or []:
                ds = l.data.struct
                try:
                    off = pe.get_offset_from_rva(ds.OffsetToData)
                except Exception:
                    continue
                out.append((tname, nname, l.id, off, ds.Size))
    return out


def ne_resources(data):
    """List of (type, name, 0, offset, size) for a 16-bit NE file, or None."""
    if data[:2] != b"MZ" or len(data) < 0x40:
        return None
    ne = struct.unpack("<I", data[0x3c:0x40])[0]
    if ne + 0x40 > len(data) or data[ne:ne + 2] != b"NE":
        return None
    rt = ne + struct.unpack("<H", data[ne + 0x24:ne + 0x26])[0]
    rn_end = ne + struct.unpack("<H", data[ne + 0x26:ne + 0x28])[0]
    if rt >= rn_end:
        return []
    shift = struct.unpack("<H", data[rt:rt + 2])[0]
    p = rt + 2; out = []
    def rname(v):
        if v & 0x8000:
            return None, v & 0x7FFF
        q = rt + v
        ln = data[q] if q < len(data) else 0
        return data[q + 1:q + 1 + ln].decode("latin-1"), None
    while p + 8 <= len(data):
        tid, cnt = struct.unpack("<HH", data[p:p + 4]); p += 8
        if tid == 0:
            break
        ts, ti = rname(tid)
        tname = ts if ts is not None else RT_NAMES.get(ti, str(ti))
        for k in range(cnt):
            if p + 12 > len(data):
                break
            off, ln, fl, rid = struct.unpack("<HHHH", data[p:p + 8]); p += 12
            ns, ni = rname(rid)
            out.append((tname, ns if ns is not None else str(ni), 0, off << shift, ln << shift))
    return out

# --------------------------------------------------------------------------- signatures

FMT_NAMES = {1: "PCM", 2: "MS ADPCM", 3: "IEEE float", 6: "A-law", 7: "mu-law", 0x11: "IMA ADPCM",
             0x22: "TrueSpeech", 0x31: "GSM 6.10", 0x40: "G.721", 0x55: "MP3", 0x130: "ACELP.net",
             0x160: "WMA1", 0x161: "WMA2", 0x200: "Creative ADPCM", 0xFFFE: "extensible"}
XP_ACM = {1, 2, 6, 7, 0x11, 0x22, 0x31, 0x55, 0x130, 0x160, 0x161}   # codecs a stock XP SP3 has

SIG = re.compile(rb"RIFF|MThd\x00\x00\x00\x06|Creative Voice File\x1a|FORM....AIF[FC]", re.S)


def riff_chunks(blob, start, end):
    p = start
    while p + 8 <= end:
        cid = blob[p:p + 4]; ln = struct.unpack("<I", blob[p + 4:p + 8])[0]
        yield cid, p + 8, min(ln, end - p - 8)
        p += 8 + ln + (ln & 1)


def parse_wave(blob, off, end):
    """Return dict(fmt...) for RIFF WAVE at off, or None."""
    fmt = data = None
    for cid, p, ln in riff_chunks(blob, off + 12, end):
        if cid == b"fmt " and ln >= 14:
            fmt = blob[p:p + ln]
        elif cid == b"data":
            data = (p, ln)
    if not fmt or not data:
        return None
    tag, ch, rate, avg, align = struct.unpack("<HHIIH", fmt[:14])
    bits = struct.unpack("<H", fmt[14:16])[0] if len(fmt) >= 16 else 8
    if tag == 0xFFFE and len(fmt) >= 26:
        tag = struct.unpack("<H", fmt[24:26])[0]
    if not (1 <= ch <= 8 and 1000 <= rate <= 200000):
        return None
    dur = data[1] / avg if avg else 0.0
    return dict(tag=tag, ch=ch, rate=rate, bits=bits, align=align, avg=avg, fmtraw=bytes(fmt),
                data_off=data[0], data_len=data[1], dur=dur)


def find_blobs(blob, base_label, region=None):
    """Yield dicts for every sound blob in blob[region]."""
    lo, hi = region or (0, len(blob))
    for m in SIG.finditer(blob, lo, hi):
        o = m.start(); s = m.group(0)
        if s == b"RIFF" and o + 12 <= hi:
            ln = struct.unpack("<I", blob[o + 4:o + 8])[0]
            form = blob[o + 8:o + 12]
            end = min(o + 8 + ln, hi)
            if ln >= 0xF0000000:
                continue   # a header template in code (cdfs.sys writes RIFF/CDXA headers with length -8)
            if ln < 4 or o + 8 + ln > hi + 1:   # a 1-byte overhang is common (pad byte)
                if form != b"WAVE":
                    continue
            if form == b"WAVE":
                w = parse_wave(blob, o, end)
                if w:
                    yield dict(kind="wave", off=o, end=end, **w)
            elif form == b"RMID":
                yield dict(kind="rmid", off=o, end=end)
            elif form == b"DLS ":
                yield dict(kind="dls", off=o, end=end)
            elif form in (b"DMSG", b"DMST", b"DMBD", b"DMCS", b"DMPT", b"DMTG"):
                yield dict(kind="directmusic-" + form.decode(), off=o, end=end)
            elif form == b"AVI ":
                w = avi_audio(blob, o, end)
                if w:
                    yield dict(kind="wave", off=o, end=end, avi=True, **w)
        elif s.startswith(b"MThd"):
            fmt_, ntrk, div = struct.unpack(">HHH", blob[o + 8:o + 14])
            if fmt_ <= 2 and 1 <= ntrk <= 256 and blob[o + 14:o + 18] == b"MTrk":
                p = o + 14
                for _ in range(ntrk):
                    if blob[p:p + 4] != b"MTrk":
                        break
                    p += 8 + struct.unpack(">I", blob[p + 4:p + 8])[0]
                yield dict(kind="midi", off=o, end=min(p, hi), ntrk=ntrk)
        elif s.startswith(b"Creative"):
            yield dict(kind="voc", off=o, end=hi)
        elif s.startswith(b"FORM"):
            ln = struct.unpack(">I", blob[o + 4:o + 8])[0]
            yield dict(kind="aiff", off=o, end=min(o + 8 + ln, hi))


def avi_audio(blob, off, end):
    """Audio stream of an AVI as a wave dict with a 'chunks' list of (offset, length) data pieces."""
    fmt = None; sidx = -1; idx = 0; pieces = []
    def walk(p, e, depth):
        nonlocal fmt, sidx, idx
        for cid, q, ln in riff_chunks(blob, p, e):
            if cid == b"LIST":
                t = blob[q:q + 4]
                if t == b"strl":
                    sh = sf = None
                    for c2, q2, l2 in riff_chunks(blob, q + 4, q + ln):
                        if c2 == b"strh": sh = blob[q2:q2 + 4]
                        elif c2 == b"strf": sf = blob[q2:q2 + l2]
                    if sh == b"auds" and sf and fmt is None:
                        fmt, sidx = sf, idx
                    idx += 1
                elif depth < 3:
                    walk(q + 4, q + ln, depth + 1)
            elif fmt is not None and cid == b"%02dwb" % sidx:
                pieces.append((q, ln))
    walk(off + 12, end, 0)
    if not fmt or not pieces or len(fmt) < 14:
        return None
    tag, ch, rate, avg, align = struct.unpack("<HHIIH", fmt[:14])
    bits = struct.unpack("<H", fmt[14:16])[0] if len(fmt) >= 16 else 8
    total = sum(l for _, l in pieces)
    return dict(tag=tag, ch=ch, rate=rate, bits=bits, align=align, avg=avg, fmtraw=bytes(fmt), data_off=pieces[0][0],
                data_len=total, dur=total / avg if avg else 0, chunks=pieces)


SWF_RATES = [5512, 11025, 22050, 44100]
SWF_FMT = {0: "PCM (native order)", 1: "Flash ADPCM", 2: "MP3", 3: "PCM", 4: "Nellymoser 16k", 5: "Nellymoser 8k",
           6: "Nellymoser", 11: "Speex"}


def swf_sounds(blob):
    """Yield wave-like dicts for each DefineSound in a Flash file (FWS / CWS)."""
    import zlib
    d = blob
    if d[:3] == b"CWS":
        try:
            d = d[:8] + zlib.decompress(d[8:])
        except Exception:
            return
    elif d[:3] != b"FWS":
        return
    nb = d[8] >> 3; p = 8 + (5 + 4 * nb + 7) // 8 + 4
    while p + 2 <= len(d):
        cl = struct.unpack("<H", d[p:p + 2])[0]; p += 2
        code, ln = cl >> 6, cl & 63
        if ln == 63:
            ln = struct.unpack("<I", d[p:p + 4])[0]; p += 4
        if code == 14 and ln > 7:
            sid, fl, n = struct.unpack("<HBI", d[p:p + 7])
            f, rate, bits, ch = fl >> 4, SWF_RATES[(fl >> 2) & 3], 16 if fl & 2 else 8, 2 if fl & 1 else 1
            body = d[p + 7:p + ln]
            if f == 2:
                body = body[2:]   # SeekSamples
            yield dict(sid=sid, swf_fmt=f, rate=rate, bits=bits, ch=ch, samples=n, body=bytes(body),
                       dur=n / rate)
        p += ln
        if code == 0:
            break


def mp3_in_wav(mp3, rate, ch, samples):
    """WAV with WAVE_FORMAT_MPEGLAYER3 (0x55): XP's Sound Recorder opens it through its MP3 ACM codec."""
    avg = max(1, int(len(mp3) / max(samples / rate, 0.01)))
    fmt = struct.pack("<HHIIHHHHIHHH", 0x55, ch, rate, avg, 1, 0, 12, 1, 2, 1152 if rate >= 32000 else 576, 1, 1393)
    fact = b"fact" + struct.pack("<II", 4, samples)
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt + fact + b"data" + struct.pack("<I", len(mp3)) + mp3
    if len(mp3) & 1:
        body += b"\0"
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body


def ffmpeg_decode(data, rate):
    """Decode any container (MP3-in-WAV, ...) with ffmpeg, if present. Return int16 array [n, ch] or None."""
    if np is None or not shutil.which("ffmpeg"):
        return None
    r = subprocess.run(["ffmpeg", "-v", "quiet", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(rate), "pipe:1"],
                       input=data, capture_output=True)
    if r.returncode or not r.stdout:
        return None
    return np.frombuffer(r.stdout, "<i2").reshape(-1, 1)


ASF_GUID = bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")


def ffmpeg_file(data, suffix):
    """Decode the first audio stream of any file ffmpeg reads (WMA, WMV, ASF, MP3).
    Return (int16 array [n, 1], rate, ch, codec text) or None."""
    if np is None or not shutil.which("ffmpeg"):
        return None
    with tempfile.TemporaryDirectory(dir=os.environ.get("SA_TMP")) as td:
        f = os.path.join(td, "x" + suffix)
        open(f, "wb").write(data)
        info = subprocess.run(["ffmpeg", "-hide_banner", "-i", f], capture_output=True, text=True, errors="replace").stderr
        m = re.search(r"Audio: ([^,\n]+), (\d+) Hz, ([^,\n]+)", info)
        if not m:
            return None
        rate = int(m.group(2)); chs = m.group(3).strip()
        ch = 1 if chs == "mono" else 2 if chs == "stereo" else int(re.match(r"\d+", chs).group(0)) if chs[:1].isdigit() else 2
        r = subprocess.run(["ffmpeg", "-v", "quiet", "-i", f, "-vn", "-f", "s16le", "-ac", "1", "-ar", str(rate), "pipe:1"],
                           capture_output=True)
        if r.returncode or not r.stdout:
            return None
        return np.frombuffer(r.stdout, "<i2").reshape(-1, 1), rate, ch, m.group(1).split(" (")[0]


def dls_waves(blob, off, end):
    """Yield (name, wave dict) for each wave in a DLS wave pool."""
    names = []
    def walk(p, e, depth):
        for cid, q, ln in riff_chunks(blob, p, e):
            if cid in (b"LIST", b"RIFF") and ln >= 4:
                typ = blob[q:q + 4]
                if typ == b"wave":
                    fmt = data = None; nm = None; unity = None; loop = None
                    for c2, q2, l2 in riff_chunks(blob, q + 4, q + ln):
                        if c2 == b"wsmp" and l2 >= 20:
                            cb, unity, fine, gain, opt, nl = struct.unpack("<IHhiII", blob[q2:q2 + 20])
                            if nl and l2 >= cb + 16:
                                lcb, ltype, lstart, llen = struct.unpack("<IIII", blob[q2 + cb:q2 + cb + 16])
                                loop = (lstart, llen)
                        if c2 == b"fmt ": fmt = blob[q2:q2 + l2]
                        elif c2 == b"data": data = (q2, l2)
                        elif c2 == b"LIST" and blob[q2:q2 + 4] == b"INFO":
                            for c3, q3, l3 in riff_chunks(blob, q2 + 4, q2 + l2):
                                if c3 == b"INAM": nm = blob[q3:q3 + l3].split(b"\0")[0].decode("latin-1")
                    if fmt and data:
                        tag, ch, rate, avg, align, bits = struct.unpack("<HHIIHH", fmt[:16])
                        yield nm, dict(kind="wave", off=q - 8, end=q + ln, tag=tag, ch=ch, rate=rate, bits=bits,
                                       align=align, avg=avg, fmtraw=bytes(fmt[:16]), data_off=data[0],
                                       data_len=data[1], dur=data[1] / avg if avg else 0, unity=unity, loop=loop)
                elif depth < 4:
                    yield from walk(q + 4, q + ln, depth + 1)
    yield from walk(off + 12, end, 0)

# --------------------------------------------------------------------------- decoding and measuring

def _ulaw_table():
    t = []
    for i in range(256):
        u = ~i & 0xFF; s = u & 0x80; e = (u >> 4) & 7; m = u & 0x0F
        v = ((m << 3) + 0x84) << e; v -= 0x84
        t.append(-v if s else v)
    return t

def _alaw_table():
    t = []
    for i in range(256):
        a = i ^ 0x55; s = a & 0x80; e = (a >> 4) & 7; m = a & 0x0F
        v = (m << 4) + 8
        if e: v = (v + 0x100) << (e - 1)
        t.append(v if s else -v)
    return t

_ULAW, _ALAW = _ulaw_table(), _alaw_table()
_IMA_STEP = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97,
             107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724,
             796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026,
             4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500,
             20350, 22385, 24623, 27086, 29794, 32767]
_IMA_IDX = [-1, -1, -1, -1, 2, 4, 6, 8]
_MS_ADAPT = [230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230]
_MS_COEF = [(256, 0), (512, -256), (0, 0), (192, 64), (240, 0), (460, -208), (392, -232)]


def decode(blob, w):
    """Return (int16 list per channel interleaved as numpy array [n, ch]) or None."""
    if np is None:
        return None
    if w.get("chunks"):
        raw = b"".join(blob[q:q + l] for q, l in w["chunks"])
    else:
        raw = blob[w["data_off"]:w["data_off"] + w["data_len"]]
    tag, ch, bits, align = w["tag"], w["ch"], w["bits"], w["align"] or 1
    if tag == 1 and bits == 8:
        a = (np.frombuffer(raw, np.uint8).astype(np.int16) - 128) * 256
    elif tag == 1 and bits == 16:
        a = np.frombuffer(raw[:len(raw) // 2 * 2], "<i2").astype(np.int16)
    elif tag == 1 and bits == 24:
        b = np.frombuffer(raw[:len(raw) // 3 * 3], np.uint8).reshape(-1, 3).astype(np.int32)
        a = ((b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)) << 8 >> 16).astype(np.int16)
    elif tag == 7:
        a = np.array(_ULAW, np.int16)[np.frombuffer(raw, np.uint8)]
    elif tag == 6:
        a = np.array(_ALAW, np.int16)[np.frombuffer(raw, np.uint8)]
    elif tag == 0x11 and bits == 4:
        a = _ima(raw, ch, align)
    elif tag == 2 and bits == 4:
        a = _msadpcm(raw, ch, align, w["fmtraw"])
    else:
        return None
    n = len(a) // ch
    return np.asarray(a[:n * ch], np.int16).reshape(n, ch)


def _ima(raw, ch, align):
    out = []
    for b0 in range(0, len(raw) - 4 * ch + 1, align):
        blk = raw[b0:b0 + align]
        pred, idx = [], []
        for c in range(ch):
            p, i = struct.unpack("<hB", blk[4 * c:4 * c + 3]); pred.append(p); idx.append(min(i, 88))
        chans = [[] for _ in range(ch)]
        body = blk[4 * ch:]
        for g in range(0, len(body) - 4 * ch + 1, 4 * ch):
            for c in range(ch):
                for byte in body[g + 4 * c:g + 4 * c + 4]:
                    for nib in (byte & 15, byte >> 4):
                        st = _IMA_STEP[idx[c]]; d = st >> 3
                        if nib & 4: d += st
                        if nib & 2: d += st >> 1
                        if nib & 1: d += st >> 2
                        pred[c] = max(-32768, min(32767, pred[c] - d if nib & 8 else pred[c] + d))
                        idx[c] = max(0, min(88, idx[c] + _IMA_IDX[nib & 7]))
                        chans[c].append(pred[c])
        for k in range(len(chans[0])):
            for c in range(ch):
                out.append(chans[c][k])
    return out


def _msadpcm(raw, ch, align, fmt):
    coefs = _MS_COEF
    if len(fmt) >= 22:
        nc = struct.unpack("<H", fmt[20:22])[0]
        cs = [struct.unpack("<hh", fmt[22 + 4 * k:26 + 4 * k]) for k in range(nc) if 26 + 4 * k <= len(fmt)]
        if cs: coefs = cs
    out = []
    for b0 in range(0, len(raw) - 7 * ch + 1, align):
        blk = raw[b0:b0 + align]
        p = 0
        pr = list(blk[p:p + ch]); p += ch
        dl = [struct.unpack("<h", blk[p + 2 * c:p + 2 * c + 2])[0] for c in range(ch)]; p += 2 * ch
        s1 = [struct.unpack("<h", blk[p + 2 * c:p + 2 * c + 2])[0] for c in range(ch)]; p += 2 * ch
        s2 = [struct.unpack("<h", blk[p + 2 * c:p + 2 * c + 2])[0] for c in range(ch)]; p += 2 * ch
        for c in range(ch): out.append(s2[c])
        for c in range(ch): out.append(s1[c])
        c = 0
        for byte in blk[p:]:
            for nib in (byte >> 4, byte & 15):
                c1, c2 = coefs[min(pr[c], len(coefs) - 1)]
                pred = (s1[c] * c1 + s2[c] * c2) >> 8
                sn = nib - 16 if nib & 8 else nib
                v = max(-32768, min(32767, pred + sn * dl[c]))
                s2[c], s1[c] = s1[c], v
                dl[c] = max(16, (_MS_ADAPT[nib] * dl[c]) >> 8)
                out.append(v)
                c = (c + 1) % ch
    return out


NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def hz_to_note(f):
    if not f or f <= 0:
        return ""
    m = 69 + 12 * math.log2(f / 440.0); n = int(round(m))
    return "%s%d%+d" % (NOTE[n % 12], n // 12 - 1, int(round((m - n) * 100)))


def measure(pcm, rate):
    """Return dict with peak, rms, attack, f0, clarity, centroid, and a short description."""
    if pcm is None or len(pcm) < 16:
        return {}
    x = pcm.astype(np.float64).mean(axis=1) / 32768.0
    x = x - x.mean()
    peak = float(np.max(np.abs(x))) or 1e-9
    n = len(x); dur = n / rate
    hop = max(1, int(rate * 0.005))
    env = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, n, hop)]) if n >= hop else np.array([peak])
    emax = env.max() or 1e-9
    ipk = int(env.argmax())
    attack = ipk * hop / rate
    above = np.where(env > emax * 0.1)[0]
    active = (above[-1] - above[0] + 1) * hop / rate if len(above) else 0
    tail = env[ipk:]
    t50 = (np.argmax(tail < emax * 0.5) if (tail < emax * 0.5).any() else len(tail)) * hop / rate
    # pitch: autocorrelation on the loudest 80 ms
    w = int(rate * 0.08); c0 = max(0, min(n - w, ipk * hop + int(rate * 0.01)))
    seg = x[c0:c0 + w] if n > w else x
    f0 = clar = 0.0
    if len(seg) > 64 and np.any(seg):
        seg = seg * np.hanning(len(seg))
        sp = np.fft.rfft(seg, 2 * len(seg))
        ac = np.fft.irfft(np.abs(sp) ** 2)[:len(seg)]
        ac /= ac[0] or 1
        lo, hi = int(rate / 2000), min(len(ac) - 1, int(rate / 40))
        if hi > lo + 2:
            k = lo + int(np.argmax(ac[lo:hi])); clar = float(ac[k])
            if k <= lo or k >= hi - 1:
                clar = min(clar, 0.5)   # the peak sits on the edge of the search range: no pitch
            if 0 < k < len(ac) - 1:
                a, b, c = ac[k - 1], ac[k], ac[k + 1]; d = (a - c) / (2 * (a - 2 * b + c) or 1)
                if not -1 < d < 1:
                    d = 0.0   # flat or non-peaked autocorrelation: keep the integer lag
                f0 = rate / (k + d) if k + d > 0 else 0.0
        mag = np.abs(np.fft.rfft(seg))
        fr = np.fft.rfftfreq(len(seg), 1 / rate)
        cen = float((mag * fr).sum() / (mag.sum() or 1))
    else:
        cen = 0.0
    if clar <= 0.5:
        f0 = 0.0
    # pitch track: 40 ms frames over the active part; speech and melodies move, notes stay
    track = []
    fl = int(rate * 0.04)
    if fl > 64 and len(above):
        a0, a1 = above[0] * hop, min(n, (above[-1] + 1) * hop)
        lo, hi = int(rate / 1000), int(rate / 60)
        for st in range(a0, max(a0 + 1, a1 - fl), fl):
            fr = x[st:st + fl]
            if len(fr) < fl or np.sqrt(np.mean(fr ** 2)) < emax * 0.2:
                track.append(0.0); continue
            fr = fr * np.hanning(fl)
            ac = np.fft.irfft(np.abs(np.fft.rfft(fr, 2 * fl)) ** 2)[:fl]
            ac /= ac[0] or 1
            if hi < fl - 1:
                k = lo + int(np.argmax(ac[lo:hi]))
                track.append(rate / k if ac[k] > 0.6 else 0.0)
    voiced = [t for t in track if t]
    vfrac = len(voiced) / len(track) if track else 0.0
    spread = float(np.std(12 * np.log2(np.array(voiced) / np.median(voiced)))) if len(voiced) > 4 else 0.0
    gaps = sum(1 for i in range(1, len(track)) if track[i - 1] and not track[i])
    zc = float(np.mean(np.abs(np.diff(np.sign(seg))) > 0)) if len(seg) > 1 else 0
    return dict(peak=peak, attack=attack, active=active, t50=t50, f0=f0, clarity=clar,
                centroid=cen, zcr=zc, dur=dur, spread=spread, vfrac=vfrac,
                desc=describe(dur, attack, active, t50, clar, cen, f0, peak, spread, vfrac, gaps / max(active, 0.1)))


def describe(dur, attack, active, t50, clar, cen, f0, peak, spread=0.0, vfrac=0.0, gap_rate=0.0):
    if peak < 0.003:
        return "silence"
    if active > 1.0 and vfrac > 0.2 and spread > 1.5:
        what = "speech-like (pitch moves, many gaps)" if gap_rate > 1.5 else "melody or moving pitch"
        return "%s, pitch spread %.1f semitones, %.1f s" % (what, spread, active)
    length = "very short" if active < 0.12 else "short" if active < 0.6 else "medium" if active < 2.5 else "long"
    bright = "dark" if cen < 600 else "warm" if cen < 1500 else "bright" if cen < 4000 else "hissy"
    if clar > 0.8 and active > 0.4 and attack > 0.03:
        kind = "sustained tone"
    elif clar > 0.8:
        kind = "pitched pluck" if t50 < 0.25 else "ringing tone"
    elif clar > 0.5:
        kind = "partly pitched sound"
    else:
        kind = "click" if active < 0.08 else "noise burst" if active < 0.6 else "noisy texture"
    shape = "slow swell" if attack > 0.25 else "soft attack" if attack > 0.04 else "hard attack"
    note = (" near " + re.sub(r"[+-]\d+$", "", hz_to_note(f0))) if f0 else ""
    return "%s %s %s, %s%s" % (length, bright, kind, shape, note)


def to_pcm_wav(pcm, rate):
    """PCM 16-bit WAV bytes; keep mono/stereo; both Sound Recorders open it (3.11 needs 11025/22050/44100 Hz)."""
    ch = pcm.shape[1] if pcm.ndim == 2 else 1
    if ch > 2:
        pcm = pcm[:, :2]; ch = 2
    data = pcm.astype("<i2").tobytes()
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, ch, rate,
            rate * ch * 2, ch * 2, 16) + b"data" + struct.pack("<I", len(data))
    return hdr + data

# --------------------------------------------------------------------------- scanning

MEDIA_EXT = (".wav", ".mid", ".midi", ".rmi", ".dls", ".voc", ".au", ".snd", ".aif", ".aiff", ".sgt", ".sty")
SKIP_EXT = (".ttf", ".fon", ".bmp", ".jpg", ".gif", ".png", ".ico", ".cur", ".ani", ".inf", ".pnf", ".txt", ".htm",
            ".html", ".xml", ".css", ".js", ".ini", ".reg", ".log")
SKIP_PATH = ("\\pagefile.sys", "\\hiberfil.sys")


STD_RT = ("ICON", "CURSOR", "BITMAP", "GROUP_ICON", "GROUP_CURSOR", "DIALOG", "MENU", "STRING", "VERSION", "MANIFEST",
          "MESSAGETABLE", "FONT", "FONTDIR", "ACCELERATOR", "HTML", "REGISTRY", "REGINST", "TYPELIB", "AVI", "MUI",
          "241", "PNG", "GIF", "JPEG", "JPG", "XML", "XSL", "CSS", "JS", "TEXT", "UIFILE", "XMLFILE", "MOFDATA")
SOUNDY_RT = ("WAVE", "WAV", "SOUND", "SOUNDS", "SND", "MIDI", "AUDIO", "TUNE", "SAMPLE", "SAMPLES", "VOICE", "NOISE")
MEDIA_FFMPEG = (".wma", ".wmv", ".asf", ".mp3", ".wm")
VOICE_EXT = {".spd": "SAPI 5 TTS voice data (Microsoft Sam): diphone units, rendered by SAPI, not a wave file",
             ".vce": "SAPI 4 / L&H TTS voice data",
             ".avc": "MS Agent / TruVoice voice data"}
FM_DRIVERS = {"sb16fm.drv": "OPL3 FM synth driver: General MIDI instrument patch table (Sound Blaster 16)",
              "msadlib.drv": "OPL2 FM synth driver: General MIDI instrument patch table (AdLib)",
              "sbfm.drv": "OPL2 FM synth driver: instrument patch table (Sound Blaster)",
              "msopl.drv": "OPL3 FM synth driver: instrument patch table"}
SEVENZ_EXT = (".chm", ".msi", ".msp", ".mst", ".cab7")


def raw_pcm_guess(blob, off, size):
    """True if a header-less resource looks like 8-bit unsigned PCM (centred on 128, smooth)."""
    if np is None or size < 2048:
        return False
    a = np.frombuffer(blob[off:off + min(size, 65536)], np.uint8).astype(np.float64)
    if len(a) < 2048:
        return False
    m, sd = a.mean(), a.std()
    if not (112 < m < 144 and 2 < sd < 64):
        return False
    return float(np.mean(np.abs(np.diff(a)))) < 0.5 * sd and np.mean(a == 0) < 0.05


def scan_blob(blob, path, label, rows, depth=0):
    low = path.lower()
    ext = os.path.splitext(low.split("|")[-1])[1]
    res = None
    if blob[:2] == b"MZ":
        res = pe_resources(blob)
        if res is None:
            res = ne_resources(blob)
    seen = set()
    for (tname, rname, lang, off, size) in res or []:
        if tname.upper() in STD_RT:
            continue
        hit = False
        for b in find_blobs(blob, path, (off, min(len(blob), off + size))):
            hit = True; seen.add(b["off"])
            add_row(rows, blob, b, label, path, "res %s/%s" % (tname, rname))
        if hit or size <= 0:
            continue
        soundy = tname.upper() in SOUNDY_RT
        if soundy or raw_pcm_guess(blob, off, size):
            rows.append(dict(source=label, path=path, where="res %s/%s" % (tname, rname), offset=off, bytes=size,
                             kind="headerless", sha1=hashlib.sha1(blob[off:off + size]).hexdigest()[:16],
                             format="raw resource of type %s (no RIFF header)" % tname, decodable=False,
                             sndrec_xp="no: needs a header (guess 8-bit unsigned PCM)", sndrec_311="no",
                             notes="looks like 8-bit unsigned PCM" if not soundy else "sound-named type without RIFF"))
    for b in find_blobs(blob, path):
        if b["off"] in seen:
            continue
        where = "file" if b["off"] == 0 else "embedded"
        add_row(rows, blob, b, label, path, where)
    if blob[:3] in (b"FWS", b"CWS"):
        for snd in swf_sounds(blob):
            add_swf_row(rows, snd, label, path)
    if blob[:16] == ASF_GUID or ext in MEDIA_FFMPEG:
        add_media_row(rows, blob, label, path, ext or ".asf")
    if ext in VOICE_EXT:
        rows.append(dict(source=label, path=path, where="file", offset=0, bytes=len(blob), kind="speech-voice",
                         format=VOICE_EXT[ext], sha1=hashlib.sha1(blob).hexdigest()[:16], decodable=False,
                         sndrec_xp="no: speak text through SAPI (Narrator, or a script) and record the output",
                         sndrec_311="no (no SAPI on 3.11)"))
    if ext in MEDIA_EXT and not any(r["path"] == path for r in rows):
        rows.append(dict(source=label, path=path, where="file", offset=0, bytes=len(blob), kind="unknown-media",
                         format="not RIFF / SMF / VOC: header %s" % blob[:8].hex(), decodable=False,
                         sha1=hashlib.sha1(blob).hexdigest()[:16], sndrec_xp="no", sndrec_311="no",
                         notes="a sound file in a private format of its program"))
    base = low.split("\\")[-1]
    if base in FM_DRIVERS and blob[:2] == b"MZ":
        rows.append(dict(source=label, path=path, where="file", offset=0, bytes=len(blob), kind="fm-patches",
                         format=FM_DRIVERS[base], sha1=hashlib.sha1(blob).hexdigest()[:16], decodable=False,
                         sndrec_xp="no", sndrec_311="no: play notes through the OPL driver (DOSBox OPL emulation) "
                         "and record them with Sound Recorder's line-in, or render offline with an OPL emulator",
                         notes="FM instrument definitions, not samples: sounds encoded as OPL register settings"))
    if depth < 2:
        if blob[:4] == b"MSCF":
            for name, data in cab_members(blob):
                scan_blob(data, path + "|" + name, label, rows, depth + 1)
        elif blob[:4] == b"SZDD":
            x = szdd_expand(blob)
            if x:
                scan_blob(x, path + "|expanded", label, rows, depth + 1)
        elif blob[:4] == b"PK\x03\x04" and ext in (".zip", ".wmz", ".kmz", ".jar", ".xpi"):
            for name, data in zip_members(blob):
                scan_blob(data, path + "|" + name, label, rows, depth + 1)
        elif ext in SEVENZ_EXT or blob[:4] == b"ITSF":
            for name, data in sevenz_members(blob, ext or ".chm"):
                if name.lower().endswith(SKIP_EXT) or len(data) == 0:
                    continue
                scan_blob(data, path + "|" + name, label, rows, depth + 1)


def add_media_row(rows, blob, label, path, ext):
    r = dict(source=label, path=path, where="file", offset=0, bytes=len(blob), kind="media",
             sha1=hashlib.sha1(blob).hexdigest()[:16])
    got = ffmpeg_file(blob, ext)
    if not got:
        r.update(format="ASF/MP3 file (no ffmpeg, or no audio stream)", decodable=False,
                 sndrec_xp="no", sndrec_311="no")
        rows.append(r); return
    pcm, rate, ch, codec = got
    r.update(format="%s %d Hz %s (%s)" % (codec.upper(), rate, "mono" if ch == 1 else "stereo", ext.lstrip(".")),
             rate=rate, ch=ch, decodable=True,
             sndrec_xp="no (Sound Recorder does not open %s): extract as PCM" % ext,
             sndrec_311="no: extract as PCM")
    m = measure(pcm, rate)
    if m:
        r.update(duration=round(m["dur"], 3), peak=round(m["peak"], 3), f0=round(m["f0"], 1), note=hz_to_note(m["f0"]),
                 clarity=round(m["clarity"], 2), centroid=int(m["centroid"]), attack_ms=int(m["attack"] * 1000),
                 character=m["desc"])
    _capture(r, pcm, rate)
    rows.append(r)


def add_row(rows, blob, b, label, path, where):
    kind = b["kind"]
    base = dict(source=label, path=path, where=where, offset=b["off"], bytes=b["end"] - b["off"], kind=kind)
    base["sha1"] = hashlib.sha1(blob[b["off"]:b["end"]]).hexdigest()[:16]
    if kind == "wave":
        if b.get("avi"):
            base["where"] = where + " (AVI audio stream: extract to open it)"
        rows.append(wave_row(blob, b, base))
    elif kind == "dls":
        base["format"] = "DLS instrument collection"
        rows.append(base)
        for nm, w in dls_waves(blob, b["off"], b["end"]):
            r = dict(base, kind="dls-wave", offset=w["off"], bytes=w["end"] - w["off"], where=where + " dls-wave " + (nm or "?"))
            r["sha1"] = hashlib.sha1(blob[w["data_off"]:w["data_off"] + w["data_len"]]).hexdigest()[:16]
            r = wave_row(blob, w, r)
            if w.get("unity") is not None:
                r["root_midi"] = w["unity"]
            if w.get("loop"):
                r["loop"] = "%d+%d" % w["loop"]
                r["character"] = (r.get("character") or "") + "; loop sample (one-shot is only the attack)"
            rows.append(r)
    elif kind == "midi":
        base["format"] = "Standard MIDI file, %d tracks" % b.get("ntrk", 0)
        base["sndrec_xp"] = "no (MIDI): render through the GS synth first"
        base["sndrec_311"] = "no (MIDI)"
        rows.append(base)
    else:
        base["format"] = kind
        rows.append(base)


_CAPTURE = None   # set by extract: (path, where, offset) -> (pcm, rate, loop, native_bytes)


def _capture(r, pcm, rate, loop=None, native=None):
    if _CAPTURE is not None:
        _CAPTURE[(r["path"].lower(), r["where"], str(r["offset"]))] = (pcm, rate, loop, native, r.get("sha1"))


def add_swf_row(rows, snd, label, path):
    f = snd["swf_fmt"]
    r = dict(source=label, path=path, where="swf DefineSound %d" % snd["sid"], offset=snd["sid"], bytes=len(snd["body"]),
             kind="swf-sound", format="%s %d Hz %d-bit %s" % (SWF_FMT.get(f, str(f)), snd["rate"], snd["bits"],
                                                            "mono" if snd["ch"] == 1 else "stereo"),
             rate=snd["rate"], bits=snd["bits"], ch=snd["ch"], duration=round(snd["dur"], 3),
             sha1=hashlib.sha1(snd["body"]).hexdigest()[:16])
    pcm = None
    if f == 2:
        r["sndrec_xp"] = "yes, as MP3-in-WAV (XP MP3 ACM codec); Convert Now makes PCM"
        pcm = ffmpeg_decode(mp3_in_wav(snd["body"], snd["rate"], snd["ch"], snd["samples"]), snd["rate"])
    elif f in (0, 3) and snd["bits"] == 16 and np is not None:
        pcm = np.frombuffer(snd["body"][:len(snd["body"]) // 2 * 2], "<i2").reshape(-1, 1)
        r["sndrec_xp"] = "after extract (PCM)"
    else:
        r["sndrec_xp"] = "no: needs a Flash decoder"
    r["sndrec_311"] = "after extract as PCM (needs ffmpeg on the host for MP3)" if f == 2 else "after extract (PCM)"
    m = measure(pcm, snd["rate"]) if pcm is not None else {}
    if m:
        r.update(duration=round(m["dur"], 3), peak=round(m["peak"], 3), f0=round(m["f0"], 1), note=hz_to_note(m["f0"]),
                 clarity=round(m["clarity"], 2), centroid=int(m["centroid"]), attack_ms=int(m["attack"] * 1000),
                 character=m["desc"])
    r["decodable"] = pcm is not None
    _capture(r, pcm, snd["rate"], None, mp3_in_wav(snd["body"], snd["rate"], snd["ch"], snd["samples"]) if f == 2 else None)
    rows.append(r)


def native_wav(blob, w):
    """The sound in its own codec, as a plain RIFF WAVE (for AVI audio and DLS waves, which are not files)."""
    if w.get("chunks"):
        data = b"".join(blob[q:q + l] for q, l in w["chunks"])
    else:
        data = blob[w["data_off"]:w["data_off"] + w["data_len"]]
    fmt = w["fmtraw"]
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt + (b"\0" if len(fmt) & 1 else b"") + \
        b"data" + struct.pack("<I", len(data)) + data + (b"\0" if len(data) & 1 else b"")
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body


def wave_row(blob, w, base):
    tag = w["tag"]
    base.update(format="%s %d Hz %d-bit %s" % (FMT_NAMES.get(tag, "0x%04x" % tag), w["rate"], w["bits"],
                                                "mono" if w["ch"] == 1 else "stereo" if w["ch"] == 2 else "%dch" % w["ch"]),
                tag=tag, rate=w["rate"], bits=w["bits"], ch=w["ch"], duration=round(w["dur"], 3))
    pcm = None
    try:
        pcm = decode(blob, w)
    except Exception:
        pcm = None
    native = None
    if w["tag"] != 1 or w.get("chunks"):
        native = native_wav(blob, w)
        if pcm is None:
            pcm = ffmpeg_decode(native, w["rate"])
    m = measure(pcm, w["rate"]) if pcm is not None else {}
    if m:
        base.update(duration=round(m["dur"], 3), peak=round(m["peak"], 3), f0=round(m["f0"], 1),
                    note=hz_to_note(m["f0"]), clarity=round(m["clarity"], 2), centroid=int(m["centroid"]),
                    attack_ms=int(m["attack"] * 1000), character=m["desc"])
    base["sndrec_xp"] = "yes" if tag == 1 else "yes (ACM codec)" if tag in XP_ACM else "no: extract as PCM"
    std = w["rate"] in (11025, 22050, 44100)
    base["sndrec_311"] = "yes" if tag == 1 and w["bits"] in (8, 16) and std else (
        "after extract --target 311 (PCM, %d Hz resampled to 11025/22050)" % w["rate"] if pcm is not None else "no")
    base["decodable"] = pcm is not None
    _capture(base, pcm, w["rate"], w.get("loop"), native)
    return base


COLS = ["id", "source", "path", "where", "offset", "bytes", "kind", "format", "rate", "bits", "ch", "duration",
        "peak", "f0", "note", "clarity", "centroid", "attack_ms", "character", "sndrec_xp", "sndrec_311", "decodable",
        "root_midi", "loop", "sha1", "dup_of", "found_in", "notes"]


def cmd_scan(a):
    """Scan every source; rows from several sources of one label (for example the 3.11 jsdos bundle and the
    BASILISK 16 drive.zip) are merged when path, place and content are the same: found_in lists the sources."""
    rows, keyed = [], {}
    for src in a.sources:
        label = a.label or os.path.basename(src)
        for e in walk_source(src):
            low = e.path.lower()
            if low.endswith(SKIP_EXT) or low in SKIP_PATH or e.size == 0 or e.size > a.max_mb * 1 << 20:
                continue
            try:
                data = e.read()
            except Exception as ex:
                print("warn: read %s: %s" % (e.path, ex), file=sys.stderr); continue
            got = []
            scan_blob(data, e.path, label, got)
            for r in got:
                k = (r["source"], r["path"].lower(), r["where"], str(r["offset"]), r.get("sha1"))
                if k in keyed:
                    fi = keyed[k]["found_in"].split(";")
                    if os.path.basename(src) not in fi:
                        keyed[k]["found_in"] += ";" + os.path.basename(src)
                    continue
                r["found_in"] = os.path.basename(src)
                keyed[k] = r; rows.append(r)
            if a.verbose and got:
                print("%5d %s" % (len(got), e.path), file=sys.stderr)
    first = {}
    for i, r in enumerate(rows):
        r["id"] = "%s-%05d" % (r["source"], i)
        h = r.get("sha1")
        if h:
            if h in first: r["dup_of"] = first[h]
            else: first[h] = r["id"]
    with open(a.csv, "w", newline="") as f:
        wr = csv.DictWriter(f, COLS, extrasaction="ignore"); wr.writeheader(); wr.writerows(rows)
    print("%d rows (%d unique) -> %s" % (len(rows), len(first), a.csv))


TARGET_311_RATES = (11025, 22050)


def resample(pcm, src, dst):
    """Band-limited resampling by FFT (both directions); int16 [n, ch] in and out."""
    if src == dst or len(pcm) == 0:
        return pcm
    x = pcm.astype(np.float64)
    n = len(x); m = max(1, int(round(n * dst / src)))
    pad = 1 << int(math.ceil(math.log2(max(n, 16))))   # pad to limit wrap-around ringing
    X = np.fft.rfft(x, pad, axis=0)
    mp = int(round(pad * dst / src))
    Y = np.zeros((mp // 2 + 1, x.shape[1]), complex)
    k = min(len(X), len(Y)); Y[:k] = X[:k]
    y = np.fft.irfft(Y, mp, axis=0)[:m] * (mp / pad)
    return np.clip(np.round(y), -32768, 32767).astype(np.int16)


def for_target(pcm, rate, target, bits):
    """Make the PCM Sound Recorder ready: xp keeps the rate (XP's Sound Recorder opens any PCM rate);
    311 downmixes to mono and resamples to 11025 or 22050 Hz (the nearest at or above the source, max 22050)."""
    if target == "311":
        if pcm.shape[1] > 1:
            pcm = pcm.astype(np.int32).mean(axis=1, keepdims=True).astype(np.int16)
        dst = 11025 if rate <= 11025 else 22050
        pcm = resample(pcm, rate, dst); rate = dst
    elif pcm.shape[1] > 2:
        pcm = pcm[:, :2]
    return pcm, rate, bits


def to_pcm_wav_bits(pcm, rate, bits):
    if bits == 16:
        return to_pcm_wav(pcm, rate)
    ch = pcm.shape[1]
    data = ((pcm.astype(np.int32) + 32768 + 128) >> 8).clip(0, 255).astype(np.uint8).tobytes()
    pad = b"\0" if len(data) & 1 else b""
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data) + len(pad)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, ch, rate,
            rate * ch, ch, 8) + b"data" + struct.pack("<I", len(data))
    return hdr + data + pad


def _safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:80] or "sound"


def cmd_extract(a):
    """First-use extraction: re-find each catalog row in the user's own image by path + place + offset, check its
    sha1, decode it and write a plain PCM WAV that the target Sound Recorder opens.

    --ids FILE: lines "ID [NAME]"; NAME becomes NAME.wav. Without --ids: every decodable, non-duplicate row of the
    catalog whose source matches --source (xp or w311).
    --target xp|311: xp = PCM 16-bit, source rate; 311 = PCM mono 8- or 16-bit (--bits) at 11025 or 22050 Hz.
    --loop-seconds S: a DLS loop sample is written as its attack plus its loop repeated up to S seconds.
    --native: write MP3/ADPCM/TrueSpeech sounds in their own codec (XP only; XP decodes them through ACM).
    """
    global _CAPTURE
    rows = {r["id"]: r for r in csv.DictReader(open(a.csv))}
    names = {}
    if a.ids:
        for l in open(a.ids):
            p = l.split()
            if p and not p[0].startswith("#") and p[0] in rows:
                names[p[0]] = p[1] if len(p) > 1 else p[0]
    else:
        src = a.source or ("w311" if a.target == "311" else "xp")
        for i, r in rows.items():
            if (r.get("os") or r.get("source")) == src and r.get("decodable") == "True" and not r.get("dup_of") \
                    and r.get("kind") in ("wave", "dls-wave", "swf-sound", "media"):
                names[i] = "%s_%s" % (i, _safe(r["path"].split("\\")[-1].split("|")[-1].rsplit(".", 1)[0]))
    need = {}
    for i in names:
        r = rows[i]
        need.setdefault(r["path"].split("|")[0].lower(), []).append(r)
    os.makedirs(a.out, exist_ok=True)
    done, bad, report = 0, 0, []
    for src in a.sources:
        for e in walk_source(src):
            key = e.path.lower()
            if key not in need:
                continue
            _CAPTURE = {}
            scan_blob(e.read(), e.path, "x", [])
            for r in need.pop(key):
                got = _CAPTURE.get((r["path"].lower(), r["where"], r["offset"]))
                if not got:
                    print("warn: %s not found again in %s" % (r["id"], e.path), file=sys.stderr); bad += 1; continue
                pcm, rate, loop, native, sha = got
                if r.get("sha1") and sha != r["sha1"] and not a.force:
                    print("warn: %s sha1 %s != catalog %s (different build?); skipped" % (r["id"], sha, r["sha1"]),
                          file=sys.stderr); bad += 1; continue
                out = os.path.join(a.out, names[r["id"]] + ".wav")
                if a.native and native and a.target == "xp":
                    open(out, "wb").write(native); done += 1; continue
                if pcm is None:
                    print("warn: %s cannot be decoded here" % r["id"], file=sys.stderr); bad += 1; continue
                if loop and a.loop_seconds > 0:
                    st, ln = loop
                    if 0 < ln and st + ln <= len(pcm):
                        reps = max(0, int((a.loop_seconds * rate - st) / ln))
                        pcm = np.concatenate([pcm[:st + ln]] + [pcm[st:st + ln]] * reps)
                if a.max_seconds and len(pcm) > a.max_seconds * rate:
                    pcm = pcm[:int(a.max_seconds * rate)]
                pcm2, rate2, bits = for_target(pcm, rate, a.target, a.bits)
                open(out, "wb").write(to_pcm_wav_bits(pcm2, rate2, bits))
                report.append((r["id"], os.path.basename(out), rate2, bits, pcm2.shape[1], len(pcm2) / rate2))
                done += 1
            _CAPTURE = None
        if not need:
            break
    for k, rs in need.items():
        for r in rs:
            print("warn: %s: %s not in this source" % (r["id"], r["path"]), file=sys.stderr); bad += 1
    if a.report:
        with open(a.report, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["id", "file", "rate", "bits", "ch", "seconds"]); w.writerows(report)
    print("%d files -> %s (%d skipped)" % (done, a.out, bad))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan"); s.add_argument("sources", nargs="+"); s.add_argument("--label")
    s.add_argument("--csv", required=True); s.add_argument("--max-mb", type=int, default=128)
    s.add_argument("-v", "--verbose", action="store_true")
    x = sp.add_parser("extract"); x.add_argument("sources", nargs="+"); x.add_argument("--csv", required=True)
    x.add_argument("--ids"); x.add_argument("--out", required=True)
    x.add_argument("--loop-seconds", type=float, default=0.0); x.add_argument("--native", action="store_true")
    x.add_argument("--target", choices=("xp", "311"), default="xp"); x.add_argument("--bits", type=int, choices=(8, 16),
                   default=16); x.add_argument("--source", help="catalog source label (xp, w311)")
    x.add_argument("--force", action="store_true", help="write even when the sha1 differs")
    x.add_argument("--max-seconds", type=float, default=0.0, help="cut long sounds (WMA music) to this length")
    x.add_argument("--report", help="write a CSV of the files written")
    a = ap.parse_args()
    {"scan": cmd_scan, "extract": cmd_extract}[a.cmd](a)


if __name__ == "__main__":
    main()

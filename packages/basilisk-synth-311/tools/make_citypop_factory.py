#!/usr/bin/env python3
"""CITYPOP.EXE's track 1, prepared at the factory (design: the album starts at once; tracks 2-12 render live while it
plays). render311 --song renders the album's first .song on the release machine, every part on Sound Recorder, exactly
as the plugin would; the mix is kept as 16-bit (rounded, no dither) in MACHINE/citypop/factory-01.wav.
    make_citypop_factory.py RENDER311 MACHINE [--jobs N]"""
import glob, os, subprocess, sys, tempfile, struct
r311, machine = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
jobs = sys.argv[sys.argv.index('--jobs') + 1] if '--jobs' in sys.argv else '4'
song = sorted(glob.glob(os.path.join(machine, 'citypop', '01-*.song')))[0]
core = [c for c in ('dosbox_pure_libretro.so', 'dosbox_pure_libretro.dylib', 'dosbox_pure_libretro.dll') if os.path.exists(os.path.join(machine, c))][0]
with tempfile.TemporaryDirectory() as tmp:
    wav = os.path.join(tmp, 'mix.wav')
    subprocess.run([r311, '--machine', machine, '--core', os.path.join(machine, core), '--song', song, '--out', wav, '--jobs', jobs],
                   check=True, env=dict(os.environ, TMPDIR=tmp))
    d = open(wav, 'rb').read()
    body = d[44:]
    out = bytearray()
    for i in range(0, len(body) - 2, 3):
        s = int.from_bytes(body[i:i + 3], 'little', signed=True)
        v = (s + 128) >> 8 if s >= 0 else -((-s + 128) >> 8)   # 24 -> 16 bits, rounded half away from zero
        out += struct.pack('<h', max(-32768, min(32767, v)))
hdr = b'RIFF' + struct.pack('<I', 36 + len(out)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 2, 48000, 48000 * 4, 4, 16) + b'data' + struct.pack('<I', len(out))
open(os.path.join(machine, 'citypop', 'factory-01.wav'), 'wb').write(hdr + bytes(out))
print('factory-01.wav: %d bytes from %s' % (len(hdr) + len(out), os.path.basename(song)))

#!/usr/bin/env python3
"""Offline tests for the BYO prototype: python3 -I test_byo.py (stdlib only; uses pycdlib for the ISO test if present).

Online checks (range reads of published media, a few hundred KB) are in design/BYO-IMAGE.md, appendix B."""
import io
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import floppy      # noqa: E402
import media_id    # noqa: E402
import answers     # noqa: E402


def test_floppy_roundtrip():
    sif = answers.XP_SIF.format(key='AAAAA-BBBBB-CCCCC-DDDDD-EEEEE', name='T').encode()
    big = os.urandom(5000)
    img = floppy.make([('WINNT.SIF', sif), ('BIG.BIN', big), ('EMPTY.TXT', b'')], 'BSYNTH')
    assert len(img) == 1474560
    f = media_id.Fat12(media_id.BytesSource('a.img', img))
    assert f.label == 'BSYNTH'
    got = {e['name']: f.read(e) for e in f.files}
    assert got == {'WINNT.SIF': sif, 'BIG.BIN': big, 'EMPTY.TXT': b''}, got.keys()


def test_floppy_full():
    try:
        floppy.make([('A.BIN', b'x' * 1500000)])
    except ValueError:
        return
    raise AssertionError('an oversize file was accepted')


def fake_wfw_disk1():
    names = ['SETUP.EXE', 'SETUP.INF', 'SETUP.SHH', 'WFWSETUP.DL_', 'KRNL386.EX_', 'SVGA256.DR_', 'DISK1']
    files = [(n, b'[setup]\r\n"Windows for Workgroups 3.11"\r\n' if n == 'SETUP.INF' else b'x') for n in names]
    return floppy.make(files, 'MSWFWUPG1')


def test_wfw_disk1():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'Disk01.img')
        open(p, 'wb').write(fake_wfw_disk1())
        r = media_id.identify(p)
        assert r['kind'] == 'wfw311-disk1', r
        assert r['label'] == 'MSWFWUPG1' and r['has_setup_shh'] and r['has_svga256']
        assert r['setup_inf_title'] == 'Windows for Workgroups 3.11'


def test_wfw_zip_set():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'set.zip')
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('Disk01.img', fake_wfw_disk1())
            z.writestr('Disk02.img', floppy.make([('DISK2', b'')], 'DISK2'))
        r = media_id.identify(p)
        assert r['kind'] == 'wfw311-floppy-set', r
        assert [x['kind'] for x in r['disks']] == ['wfw311-disk1', 'setup-floppy']


def test_known_table():
    k = media_id.load_known()
    ids = [m['id'] for m in k]
    assert len(ids) == len(set(ids))
    for m in k:
        assert len(m['sha1']) == 40 and m['size'] > 0 and m['edition'] in ('xp', '311'), m['id']
    assert media_id.match_known(492597008, 'bf9ae7899a332c083676d7d973a4ab68ea4143b1')['id'] == 'xpmode-en-us'


def test_xp_iso():
    try:
        import pycdlib
    except ImportError:
        print('  (pycdlib not installed: ISO test skipped)')
        return
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident='GRTMPVOL_EN')
    for n, data in [('/WIN51.;1', b'x'), ('/WIN51IP.;1', b'x'), ('/WIN51IP.SP3;1', b'x')]:
        iso.add_fp(io.BytesIO(data), len(data), n)
    iso.add_directory('/I386')
    ini = b'[Pid]\r\nExtraData=x\r\nPid=76487270\r\n'
    iso.add_fp(io.BytesIO(ini), len(ini), '/I386/SETUPP.INI;1')
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'xp.iso')
        iso.write(p)
        r = media_id.identify(p)
    assert r['kind'] == 'windows-xp-cd' and r['edition'] == 'professional', r
    assert r['service_pack'] == 'SP3' and r['channel'] == 'volume' and not r['problems'], r


if __name__ == '__main__':
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            n += 1
            print('ok', name)
    print('%d tests passed' % n)

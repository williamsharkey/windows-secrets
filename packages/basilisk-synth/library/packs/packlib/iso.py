"""The pack's disc image: ISO 9660 level 1 (8.3 names, which MSCDEX and File Manager on Windows 3.11 read) plus a
Joliet tree (long names, which Explorer on XP shows). Files are given as (iso_path, joliet_path, bytes)."""
import calendar
import datetime
import io

import pycdlib


def build(out_path, volume_id, joliet_volume, entries, date):
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1, joliet=3, vol_ident=volume_id.upper()[:32], sys_ident='BASILISK', app_ident_str='',
            pub_ident_str='', preparer_ident_str='')
    # pycdlib stamps "now"; the volume dates are set to the pack date below
    made = set()
    for iso_path, joliet_path, data in sorted(entries, key=lambda e: e[0]):
        parts = iso_path.strip('/').split('/')
        jparts = joliet_path.strip('/').split('/')
        for i in range(1, len(parts)):
            d = '/' + '/'.join(parts[:i])
            if d not in made:
                iso.add_directory(d, joliet_path='/' + '/'.join(jparts[:i]))
                made.add(d)
        iso.add_fp(io.BytesIO(data), len(data), iso_path + ';1', joliet_path=joliet_path)
    # Joliet volume label (long form, up to 16 UCS-2 characters)
    jv = joliet_volume[:16].encode('utf-16-be')
    iso.joliet_vd.volume_identifier = jv + ' '.encode('utf-16-be') * ((32 - len(jv)) // 2)
    _set_dates(iso, date)
    # file dates: the day the maker pressed the disc (File Manager and Explorer show them)
    for path in ['/' + '/'.join(p.strip('/').split('/')[:i + 1]) for e in entries for p in [e[0]] for i in range(len(p.strip('/').split('/')))]:
        for kw in ({'iso_path': path + (';1' if '.' in path.split('/')[-1] else '')},):
            try:
                rec = iso.get_record(**kw)
            except Exception:
                continue
            _stamp(rec, date)
    for e in entries:
        jp = e[1]
        parts = jp.strip('/').split('/')
        for i in range(len(parts)):
            try:
                _stamp(iso.get_record(joliet_path='/' + '/'.join(parts[:i + 1])), date)
            except Exception:
                pass
    iso.write(out_path)
    iso.close()


def _stamp(rec, date):
    d = rec.date
    d.years_since_1900, d.month, d.day_of_month = date.year - 1900, date.month, date.day
    d.hour, d.minute, d.second, d.gmtoffset = 12, 0, 0, 0


def _set_dates(iso, date):
    try:
        from pycdlib import dates
        t = calendar.timegm(datetime.datetime(date.year, date.month, date.day, 12, 0).timetuple())
        for vd in [iso.pvd] + ([iso.joliet_vd] if iso.joliet_vd else []):
            for attr in ('volume_creation_date', 'volume_modification_date'):
                v = dates.VolumeDescriptorDate()
                v.new(t)
                setattr(vd, attr, v)
    except Exception:
        pass

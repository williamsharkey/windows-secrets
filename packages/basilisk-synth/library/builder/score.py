"""Automatic checks and the fitness of one probe render for a category.

check -> (ok, score, reasons, info). Hard rejects: render failed, silence, a note not heard, DC, card clipping,
too short, still sounding at the end of the render, out of tune or not key-tracking (tonal categories), very
uneven across the keyboard. The score (about 0..110) rewards the category's descriptor ranges, tuning, evenness
and a little stereo width; info carries the suggested retune (cents) and the loudness for the G gene.
"""
import math
import numpy as np
from catdefs import CATS

TARGET_LOUD = -18.0      # gated loudness the G gene aims the probe at (the phrase render re-checks it)


def _out(v, lo, hi):
    return 0.0 if lo <= v <= hi else (lo - v if v < lo else v - hi)


def fold(c):
    return (c + 600) % 1200 - 600


def check(r, cat, kind=None):
    c = CATS[cat]
    kind = kind or c['kind']
    why = []
    if not r or not r.get('ok'):
        return False, 0, ['render failed'], {}
    notes = r.get('notes') or []
    if r['peak_db'] < -45: why.append('silent')
    if r['heard'] < r['onsets']: why.append('%d of %d notes not heard' % (r['onsets'] - r['heard'], r['onsets']))
    if notes and not all(n.get('heard') for n in notes): why.append('a single note not heard')
    # DC: the 3.x files are 8-bit with an offset that Increase Volume amplifies; reject only an audible share
    if r['dc'] > 0.08: why.append('DC %.3f' % r['dc'])
    # the card's float output is not clamped: samples over the G full scale are overs that the G gene removes
    # (finalize keeps peaks under -1 dBFS); flat tops inside Sound Recorder (Increase Volume) are the recipe's sound
    endlim = {'drone': -3, 'fx': -6, 'pad': -10}.get(kind, -24)
    if r['end_rel_db'] > endlim: why.append('still sounding at the end (%.0f dB)' % r['end_rel_db'])
    info = {}
    score = 100.0
    mid = notes[len(notes) // 2] if notes else None
    if mid and mid.get('heard'):
        if mid['dec20'] < 0.03 and kind != 'perc': why.append('too short')
        # descriptors
        a = mid['attack']
        lo, hi = c['attack']
        if a < lo: score -= 15 * (math.log2((lo + 0.01) / (a + 0.01)))
        elif a > hi: score -= 25 * (math.log2((a + 0.01) / (hi + 0.01)))
        score -= 0.5 * _out(max(-80.0, mid['sus_db']), max(-80, c['sus'][0]), c['sus'][1])   # -240: silent before the hold ended
        d = mid['dec20']; lo, hi = c['dec20']
        if d < lo: score -= 15 * math.log2(lo / max(d, 0.01))
        elif d > hi: score -= 10 * math.log2(d / hi)
        cen = r.get('centroid', 1000) or 1
        lo, hi = c['cen']
        if cen < lo: score -= 12 * math.log2(lo / max(cen, 1))
        elif cen > hi: score -= 12 * math.log2(cen / hi)
        if r.get('flatness', 0) > c['flat_max']:
            score -= 60 * (r['flatness'] - c['flat_max'])
            if c['tonal'] and r['flatness'] > 2.5 * c['flat_max']: why.append('noisy for a tonal category')
    heard = [n for n in notes if n.get('heard')]
    if len(heard) >= 2:
        pk = [n['peak_db'] for n in heard]
        spread = max(pk) - min(pk)
        if spread > 24: why.append('uneven across the keyboard (%.0f dB)' % spread)
        score -= 1.2 * max(0, spread - 10)
    # tuning
    tonal = c['tonal'] and kind not in ('fx', 'perc')
    offs = [0]
    if r.get('dna'):
        from common import DNA
        d = DNA.parse(r['dna'])
        keyed = [L for L in d.layers if not L.genes.get('F')]
        if not keyed: tonal = False            # fixed-pitch layers only: nothing tracks the keyboard by design
        else:
            # the pitch class may land on any interval the first key-tracked layer stacks (H0,7: the fifth)
            offs = sorted(set([0] + [h % 12 for h in keyed[0].genes.get('H', [0])]))
    errs = [n for n in heard if 'err' in n]

    def near(e):
        return min((fold(e - 100 * o) for o in offs), key=abs)
    if tonal and errs:
        e1 = [near(n['err']) for n in errs]
        e2 = [near(n['spk_err']) for n in errs if n.get('spk_err') is not None]
        best = e1
        if len(e2) == len(e1) and np.mean(np.abs(e2)) < np.mean(np.abs(e1)): best = e2
        med = float(np.median(best)); spread = float(np.max(best) - np.min(best))
        info['tune_cents'] = round(med, 1); info['tune_spread'] = round(spread, 1)
        if abs(med) >= 45 and spread < 150: info['retune'] = med
        conf = sorted(n.get('conf', 0) for n in errs)
        info['pitch_conf'] = conf[len(conf) // 2]
        if abs(med) > c['tol']: why.append('out of tune (%+.0f cents)' % med)
        elif spread > max(60, 2 * c['tol']): why.append('does not track the keyboard (%.0f cents spread)' % spread)
        score -= 0.6 * max(0, abs(med) - 8) + 0.15 * max(0, spread - 20)
        if info['pitch_conf'] < 0.45: score -= 15
    w = r.get('width', 0)
    if 0.06 < w < 0.8: score += 4
    info['loud'] = r.get('loud')
    info['peak_db'] = r.get('peak_db')
    return (not why), round(score, 1), why, info


def gain_for(loud, peak_db, g0=0, target=TARGET_LOUD):
    """the G gene that brings a render (made with G=g0) to the target loudness, peaks kept under -1 dBFS"""
    if loud is None or loud < -90: return g0
    g = g0 + (target - loud)
    g = min(g, g0 + (-1.0 - peak_db))
    return int(max(-60, min(24, math.floor(g))))


def features(r):
    """novelty vector: 16 band levels, 30-point envelope shape, log centroid, flatness, attack, sustain"""
    if not r or 'bands' not in r: return None
    b = np.array(r['bands'], float); b = (b - b.max()) / 20.0
    sh = np.array(r['shape'], float)
    notes = r.get('notes') or [{}]
    mid = notes[len(notes) // 2]
    extra = [math.log2(max(r.get('centroid', 1000), 50) / 1000) / 2, r.get('flatness', 0) * 5,
             math.log2(mid.get('attack', 0) + 0.01) / 4, mid.get('sus_db', -60) / 60, r.get('width', 0)]
    return np.concatenate([b, sh * 0.8, np.array(extra) * 1.5])

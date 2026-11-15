"""The Leaning Cloister Galliard: an original Renaissance-style galliard in D Dorian, 3/4, with the hemiola cadences
of the dance. Psaltery tune over harpsichord continuo, folk harp, strumstick bass, a didgeridoo bourdon, hand-chime
bells and a balafon tabor."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

BPM = 104
S = Score(bpm=BPM, seed=7)
mel = S.part('psaltery', 1)
hpsi = S.part('harpsichord', 2)
harp = S.part('harp', 3)
bass = S.part('strumstick', 4)
drone = S.part('drone', 5)
bell = S.part('bells', 6)
tabor = S.part('tabor', 7)
fx = S.part('swoosh', 8)

A_MEL = 'h D5 q F5 | q E5 D5 C5 | q D5 E5 F5 | h. G5 | h A5 q G5 | q F5 E5 D5 | h G5 E5 D5'
A_MEL2 = 'q D5 e E5 F5 q F5 | e E5 F5 q D5 C5 | e D5 C5 D5 E5 F5 G5 | h G5 e A5 G5 | h A5 q G5 | e F5 G5 q E5 D5 | h G5 !E5 D5'
A_CH = ['Dm', 'C', 'Dm', 'G', 'F', 'C', 'G:2', 'A:2', 'Dm:2']
B_MEL = 'q A5 C6 A5 | h Bb5 q A5 | q A5 G5 F5 | h. G5 | q F5 A5 D6 | q C6 A5 E5 | h D5 E5 F5'
B_CH = ['F', 'Bb', 'F', 'C', 'Dm', 'Am', 'Bb:2', 'C:2', 'F:2']
BAR = 3


def continuo(at, chs, vel=70):
    """oom-pah-pah: the bass on one, the chord on two and three; a hemiola chord of 2 beats gets bass + chord"""
    t, prev = at, None
    for sym in chs:
        b = BAR
        if ':' in sym:
            sym, b = sym.split(':'); b = float(b)
        ns = voice_lead(prev, chord(sym, 4), 57, 72); prev = ns
        r = root_of(sym, 3)
        hpsi.note(t, r, 0.9, vel + 6)
        if b == 3:
            for k in (1, 2):
                for n in ns:
                    hpsi.note(t + k, n, 0.8, vel - 4 * k)
        else:
            for n in ns:
                hpsi.note(t + 1, n, 0.9, vel)
        t += b
    return t


def harp_arp(at, chs, vel=64):
    t, prev = at, None
    for sym in chs:
        b = BAR
        if ':' in sym:
            sym, b = sym.split(':'); b = float(b)
        ns = voice_lead(prev, chord(sym, 4), 62, 76); prev = ns
        seq = [ns[0] - 12, ns[0], ns[1], ns[2], ns[1] + 12 if len(ns) > 1 else ns[0] + 12, ns[2] if len(ns) > 2 else ns[0]]
        for k in range(int(b * 2)):
            harp.note(t + k * 0.5, seq[k % len(seq)], 0.9, vel - (0 if k % 2 == 0 else 10))
        t += b
    return t


def strum_bass(at, chs, vel=88):
    t = at
    for sym in chs:
        b = BAR
        if ':' in sym:
            sym, b = sym.split(':'); b = float(b)
        r = root_of(sym, 3)
        if b == 3:   # the galliard's long-short: dotted quarter, eighth, quarter
            bass.note(t, r, 1.4, vel); bass.note(t + 1.5, r + 7 if r + 7 < 60 else r - 5, 0.45, vel - 14); bass.note(t + 2, r, 0.9, vel - 8)
        else:
            bass.note(t, r, 1.8, vel)
        t += b
    return t


def tabor_bars(at, bars, vel=80):
    for k in range(bars):
        t = at + k * BAR
        tabor.note(t, 43, 0.3, vel + 10); tabor.note(t + 1.5, 50, 0.2, vel - 20); tabor.note(t + 2, 50, 0.2, vel - 10)


def section_len(chs):
    return sum(float(c.split(':')[1]) if ':' in c else BAR for c in chs)


t = 0.0
# intro: the bourdon, a swoosh of glockenspiel, continuo alone
fx.note(t, 74, 4.0, 80)
drone.note(t, 50, 4 * BAR * 2 - 0.5, 72)
continuo(t, ['Dm', 'C', 'Dm', 'A'])
bell.note(t + 3 * BAR, 69, 2.5, 70)
t += 4 * BAR

# A: the psaltery alone over the continuo, with the drone
L = section_len(A_CH)
mel.mel(A_MEL, at=t, vel=92); continuo(t, A_CH); strum_bass(t, A_CH)
drone.note(t + 4 * BAR, 50, L - 4 * BAR - 0.5, 66)
t += L
# A again: the tune ornamented, the harp joins, the tabor
mel.mel(A_MEL2, at=t, vel=94); continuo(t, A_CH, 66); harp_arp(t, A_CH); strum_bass(t, A_CH); tabor_bars(t, 8)
bell.note(t + L - 2, 62, 2.0, 74); bell.note(t + L - 2, 74, 2.0, 66)
t += L
# B: the bells take the tune an octave down, the psaltery answers on the hemiola
L = section_len(B_CH)
bell.mel(B_MEL, at=t, vel=84, tr=-12)
mel.mel('h. r | h. r | h. r | q r G5 A5 | h. r | h. r | h D5 E5 F5', at=t, vel=88)
continuo(t, B_CH, 64); strum_bass(t, B_CH); harp_arp(t, B_CH, 58)
t += L
# B again, everyone, the tabor back
mel.mel(B_MEL, at=t, vel=96); bell.mel('h. F5 | h. D5 | h. C5 | h. E5 | h. F5 | h. E5 | h D5 C5 A4', at=t, vel=62)
continuo(t, B_CH, 70); strum_bass(t, B_CH); harp_arp(t, B_CH, 62); tabor_bars(t, 8)
t += L
# interlude: drone, bells, harp alone, slowing nothing (a dance keeps time)
fx.note(t, 72, 3.0, 70)
drone.note(t, 50, 4 * BAR - 0.3, 70); drone.note(t, 57, 4 * BAR - 0.3, 56)
harp_arp(t, ['Dm', 'Am', 'C', 'Dm'], 60)
bell.mel('h. D5 | h. E5 | h. G5 | h. A5', at=t, vel=70)
t += 4 * BAR
# A, full: the tune doubled by bells an octave up on the long notes
L = section_len(A_CH)
mel.mel(A_MEL2, at=t, vel=98); continuo(t, A_CH, 72); harp_arp(t, A_CH, 64); strum_bass(t, A_CH, 92); tabor_bars(t, 8, 86)
bell.mel('h. D5 | h. C5 | h. D5 | h. G5 | h. A5 | h. E5 | h G5 E5 D5', at=t, vel=58)
drone.note(t, 50, L - 0.5, 62)
t += L
# coda: a last cadence, held
continuo(t, ['G', 'A', 'Dm'], 74); strum_bass(t, ['G', 'A'], 90); bass.note(t + 6, 50, 3.0, 90)
mel.mel('h. B5 | h. A5 | h. D5', at=t, vel=92)
bell.note(t + 6, 62, 4.0, 80); bell.note(t + 6, 69, 4.0, 70); bell.note(t + 6, 74, 4.0, 66)
drone.note(t, 50, 3 * BAR + 2, 70)
tabor.note(t + 6, 43, 0.4, 96)

S.humanize(ms=7, vel=5)
finish(__file__, S, {
    'title': 'The Leaning Cloister Galliard',
    'pack': 'courtyard-chapel',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE1993)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A galliard in D Dorian, 3/4, with hemiola cadences: psaltery, harpsichord continuo, folk harp, strumstick, '
            'didgeridoo bourdon, hand-chime and tubular bells, balafon tabor.',
}, [
    ('psaltery', 'ch1', 'Amber Ticks', dict(lufs=-19, pan=8, echo=0.05, verb=0.32)),
    ('harpsi', 'ch2', 'Brass Ballad', dict(lufs=-22, pan=-28, verb=0.22)),
    ('harp', 'ch3', 'Glass Spool', dict(lufs=-24, pan=34, echo=0.12, verb=0.3)),
    ('strum', 'ch4', 'Floor Harp', dict(lufs=-23, pan=-8, verb=0.15)),
    ('drone', 'ch5', 'Hotel Uplink', dict(lufs=-28, pan=0, verb=0.35)),
    ('bells', 'ch6', 'Pewter Gong', dict(lufs=-24, pan=22, echo=0.15, verb=0.45)),
    ('tabor', 'ch7', 'Field Carillon', dict(lufs=-25, pan=-36, verb=0.25)),
    ('swoosh', 'ch8', 'Polished Dive', dict(lufs=-28, pan=0, echo=0.3, verb=0.5)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 3000, 'level': -4},
   reverb={'size': 2.6, 'predelay': 24, 'tone': 5000, 'level': -3})

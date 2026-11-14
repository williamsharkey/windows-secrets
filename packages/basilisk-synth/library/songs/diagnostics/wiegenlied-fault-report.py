"""Wiegenlied (Johannes Brahms, Op. 49 No. 4, 1868), arranged for DIAGNOSTICS: the lullaby on a broken music box,
three verses. The first alone over an error pad, the second over a beat of stamps and floppy seeks with an erhu
counter-line, the third with the choir and stutters; then the box winds down."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'LullabyBrahms-C.mid'))
BPM = 76
S = Score(bpm=BPM, seed=1868)
box = S.part('musicbox', 1)
pad = S.part('errorpad', 2)
cello = S.part('cello', 3)
erhu = S.part('erhu', 4)
choir = S.part('choir', 5)
bells = S.part('bells', 6)
thud = S.part('thud', 7)
snare = S.part('snare', 8)
tick = S.part('tick', 9)
seek = S.part('seek', 11)
stut = S.part('stutter', 12)
glass = S.part('glass', 13)

L = src.bars() * src.bar          # one verse, pickup included
mel = src.tracks[0]; acc = src.tracks[1]


def verse(at, box_vel=84, beat=False, counter=False, full=False):
    put(box, beats(mel, 0, L, at), tr=12, vel=box_vel)
    arrange(src, 0, L, at, pad=pad if not full else choir, rh_track=1, lh_track=1, pad_step=3.0,
            pad_range=(52, 67) if not full else (55, 72), vel=54 if not full else 62)
    if beat or full:
        arrange(src, 0, L, at, bass=cello, rh_track=1, lh_track=1, bass_range=(36, 52), vel=72)
        nb = int(L // 3)
        for k in range(1, nb):
            b = at + 1 + 3 * (k - 1)   # bars start after the one-beat pickup
            thud.note(b, 36, 0.4, 100)
            snare.note(b + 1.5, 60, 0.3, 80 if k % 2 else 64)
            tick.drums({60: 'x.x.x.x.x.x.'}, at=b, bars=1, beats_per_bar=3.0, vel={'x': 58})
            if k % 4 == 3:
                seek.note(b + 2, 46, 0.5, 82)
    if counter:
        # the erhu sings the accompaniment's top line an octave down, a beat late
        put(erhu, [(b + 1, p, d, v) for b, p, d, v in skyline(beats(acc, 0, L, at))], tr=0, vel=72, lo=60, hi=79)
    if full:
        for k in range(3, int(L // 3), 4):
            for i in range(8):
                stut.note(at + 1 + 3 * k + 2 + i * 0.125, 72 + (i % 2) * 12, 0.1, 86 - 3 * i)
    return at + L


t = 0.0
glass.note(0, 89, 1, 80)
hold(pad, 1, 60, 4, 50)
t = 4.0
t = verse(t, 80)
glass.note(t - 0.5, 89, 1, 70)
t = verse(t, 84, beat=True, counter=True)
t = verse(t, 88, full=True, counter=True)
# the box winds down: the last phrase again, slowing, then one bell
S.tempo(t, BPM * 0.85); S.tempo(t + 6, BPM * 0.7); S.tempo(t + 10, BPM * 0.55)
put(box, beats(mel, L - 13, L, t), tr=12, vel=74)
arrange(src, L - 13, L, t, pad=pad, rh_track=1, lh_track=1, pad_step=3.0, pad_range=(52, 67), vel=50)
t += 13
bells.note(t, pitch('C6'), 4, 70); glass.note(t + 2, 89, 1, 60)

S.humanize(ms=4, vel=4, parts=['musicbox', 'erhu'])
finish(__file__, S, {
    'title': 'Wiegenlied (Fault Report)',
    'pack': 'diagnostics',
    'kind': 'world',
    'composer': 'Johannes Brahms (1833-1897)',
    'source': 'Wiegenlied, Op. 49 No. 4 (1868). Score: The Mutopia Project, "Cancion de Cuna" for recorder and guitar.',
    'licence': 'The work: public domain (published 1868; the composer died 1897). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=481',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The lullaby three times on a broken music box: over an error pad; over a beat of critical-stop thuds, '
            'stamps and floppy seeks with an erhu counter-line; with the choir and stutters. Then it winds down.',
    'tail': 5,
}, [
    ('musicbox', 'ch1', 'Broken Music Box', dict(lufs=-19, pan=-8, echo=0.25, verb=0.35)),
    ('errorpad', 'ch2', 'Digital Veil', dict(lufs=-26, verb=0.4, width=1.4)),
    ('cello', 'ch3', 'Copper Veil', dict(lufs=-24, pan=10, verb=0.3)),
    ('erhu', 'ch4', 'Hollow Song', dict(lufs=-22, pan=14, echo=0.15, verb=0.35)),
    ('choir', 'ch5', 'Inland Cantor', dict(lufs=-24, verb=0.5)),
    ('bells', 'ch6', 'Noble Bell', dict(lufs=-24, pan=20, verb=0.5)),
    ('thud', 'ch7', 'Echo Click', dict(lufs=-21)),
    ('snare', 'ch8', 'Electric Snare', dict(lufs=-24, verb=0.2)),
    ('tick', 'ch9', 'Lunar Tick', dict(lufs=-29, pan=26)),
    ('seek', 'ch11', 'Floppy Seek Perc', dict(lufs=-25, pan=-26, echo=0.2)),
    ('stutter', 'ch12', 'Stutter Copy Paste', dict(lufs=-27, pan=-20, echo=0.3)),
    ('glass', 'ch13', 'Shatter Transition', dict(lufs=-25, verb=0.5)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '1/4', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 2.6, 'predelay': 20, 'tone': 5000, 'level': -4})

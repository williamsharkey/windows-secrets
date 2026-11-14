"""Burbank Session Reel: an original late-80s workstation pop-fusion piece, 108 bpm, E-flat major. A gamelan pluck
and drone open; then piano and tines, a slap of brass, organ, string swells, a vocal pad and a soaring lead."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=108, seed=1994)
kit = S.part('kit', 10)
bass = S.part('bass', 2)
piano = S.part('piano', 3)
tines = S.part('tines', 4)
gamelan = S.part('gamelan', 5)
lead = S.part('lead', 6)
brass = S.part('brass', 7)
organ = S.part('organ', 8)
strings = S.part('strings', 9)
vox = S.part('vox', 11)
drone = S.part('drone', 12)
harp = S.part('harp', 13)

A = 'Ebmaj7 Fm7 Gm7 Abmaj7 Fm7 Gm7 Abmaj7 Bb7sus4:2 Bb7:2'
B = 'Cm7 Abmaj7 Bb6 Gm7 Cm7 Abmaj7 Fm7 Bb7'
MEL = ('q. G5 e Bb5 q D6 Bb5 | h C6 q Ab5 F5 | q. G5 e Bb5 q D6 F6 | h. Eb6 q C6 | '
       'q. Ab5 e C6 q Eb6 C6 | h Bb5 q G5 Bb5 | q. C6 e Bb5 q Ab5 G5 | h F5 q G5 Bb5')
BMEL = 'h. Eb6 q D6 | h C6 Eb6 | h. D6 q Bb5 | w G5 | h. Eb6 q F6 | h G6 Eb6 | h. C6 q Ab5 | w Bb5'
SOLO = ('e G5 Bb5 C6 D6 q Eb6 e D6 Bb5 | q C6 e Ab5 F5 h C5 | e D5 F5 G5 Bb5 q D6 e C6 Bb5 | h. G5 e Bb5 C6 | '
        'e Eb6 D6 C6 Bb5 q Ab5 e G5 F5 | q G5 e Bb5 D6 h F6 | e Eb6 D6 C6 Bb5 Ab5 G5 F5 Eb5 | h F5 q G5 Bb5')


def band(at, prog, drums=True, fill=True, vel=96):
    n = int(prog_len(prog) // 4)
    if drums:
        groove(kit, 'synthpop', at, n, fill=fill, extra={OHH: '..............x.'})
    bass.bass(prog, at=at, beats=4, pattern=[(0, 0, 0.7), (0.75, 0, 0.2), (1.5, '8', 0.3), (2.5, 0, 0.5), (3.25, '5', 0.3), (3.5, '8', 0.4)], vel=vel)


def comp(part, at, prog, vel=62):
    part.chords(prog, at=at, beats=4, style='block', vel=vel, lo=55, hi=72, rhythm=[(0, 0.9), (1.5, 0.4), (2.5, 1.2)])


t = 0.0
# intro (4)
hold(drone, 0, 51, 16, 70)
gamelan.chords('Ebmaj7:8 Abmaj7:8', at=0, style='arpud', vel=66, lo=63, hi=82, rhythm=0.5)
t = 16
# A (8): piano and tines, gamelan
band(t, A); comp(piano, t, A)
gamelan.chords(A, at=t, beats=4, style='arp', vel=56, lo=63, hi=82, rhythm=0.5)
tines.mel(MEL, at=t, vel=76, tr=-12)
t += 32
# A (8): the lead
band(t, A); comp(piano, t, A, 58)
lead.mel(MEL, at=t, vel=92, tr=-12)
vox.chords(A, at=t, beats=4, style='pad', vel=54, lo=55, hi=70)
t += 32
# B (8): brass stabs, strings swell
band(t, B)
brass.chords(B, at=t, beats=4, style='block', vel=78, lo=55, hi=72, rhythm=[(0, 0.4), (1.5, 0.3), (2.0, 0.4), (3.5, 0.3)])
strings.mel(BMEL, at=t, vel=86, tr=-12)
strings.chords(B, at=t, beats=4, style='pad', vel=52, lo=50, hi=64)
harp.chords(B, at=t, beats=4, style='arp', vel=52, lo=60, hi=79, rhythm=0.25)
t += 32
# A (8): lead and organ
band(t, A); comp(organ, t, A, 64)
lead.mel(MEL, at=t, vel=96, tr=-12)
tines.chords(A, at=t, beats=4, style='arp', vel=52, lo=63, hi=82, rhythm=0.5)
t += 32
# solo (8): the tines take a solo over the A changes
band(t, A); comp(piano, t, A, 60)
tines.mel(SOLO, at=t, vel=88, tr=-12)
vox.chords(A, at=t, beats=4, style='pad', vel=50, lo=55, hi=70)
t += 32
# B + A out (16)
band(t, B); brass.chords(B, at=t, beats=4, style='block', vel=82, lo=55, hi=72, rhythm=[(0, 0.4), (1.5, 0.3), (2.0, 0.4), (3.5, 0.3)])
strings.mel(BMEL, at=t, vel=90, tr=-12); lead.mel(BMEL, at=t + 16, vel=84, tr=-12)
t += 32
band(t, A, fill=False); comp(piano, t, A); comp(organ, t, A, 56)
lead.mel(MEL, at=t, vel=98, tr=-12)
strings.chords(A, at=t, beats=4, style='pad', vel=56, lo=55, hi=70)
gamelan.chords(A, at=t, beats=4, style='arp', vel=54, lo=63, hi=82, rhythm=0.5)
t += 32
# end (4)
for p, v in ((piano, 70), (organ, 58), (strings, 62), (vox, 56)):
    p.chords('Ebmaj7:12', at=t, style='pad', vel=v, lo=55, hi=74)
bass.note(t, pitch('Eb2'), 8, 96); kit.note(t, KICK, 1, 104); kit.note(t, CRASH, 3, 104)
gamelan.chords('Ebmaj7:8', at=t, style='arpud', vel=56, lo=63, hi=87, rhythm=0.25)
hold(drone, t, 51, 14, 64)

S.humanize(ms=4, vel=4, parts=['piano', 'tines', 'lead', 'organ', 'strings'])
finish(__file__, S, {
    'title': 'Burbank Session Reel',
    'pack': 'rom-reference',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Late-80s workstation pop-fusion in E-flat, 108 bpm: gamelan pluck and drone, piano, tines, slap bass line, '
            'brass stabs, organ, string swells, a vocal pad, harp runs and a lead. Drums: Kit Manager 98 '
            '(Breaker Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-17, verb=0.12)),
    ('bass', 'ch2', 'Neon Basement', dict(lufs=-19)),
    ('piano', 'ch3', 'Lagoon Piano', dict(lufs=-21, pan=-18, verb=0.3)),
    ('tines', 'ch4', 'Jade Tines', dict(lufs=-22, pan=14, echo=0.2, verb=0.3)),
    ('gamelan', 'ch5', 'Hazy Gamelan', dict(lufs=-25, pan=-26, echo=0.3, verb=0.3)),
    ('lead', 'ch6', 'Cathode Lead', dict(lufs=-19, pan=4, echo=0.25, verb=0.35)),
    ('brass', 'ch7', 'Lunar Brass', dict(lufs=-22, pan=16, verb=0.25)),
    ('organ', 'ch8', 'Pastel Bark', dict(lufs=-25, pan=24, verb=0.2)),
    ('strings', 'ch9', 'Blue Swell', dict(lufs=-22, pan=-10, verb=0.4, width=1.3)),
    ('vox', 'ch11', 'Slate Vox', dict(lufs=-26, verb=0.45, width=1.3)),
    ('drone', 'ch12', 'Daylight Continuum', dict(lufs=-28, verb=0.4)),
    ('harp', 'ch13', 'Copper Harp', dict(lufs=-26, pan=30, echo=0.2, verb=0.35)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3500, 'level': -4},
   reverb={'size': 2.6, 'predelay': 20, 'tone': 6000, 'level': -4})

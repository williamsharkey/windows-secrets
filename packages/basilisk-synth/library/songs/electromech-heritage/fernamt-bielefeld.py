"""Fernamt Bielefeld: an original electro piece, 112 bpm, A minor. A motor drone and relay rain, then a relay
groove, a Ferranti hoot sequencer bass, relay-marimba arpeggios, the 1961 vowel singing, a CSIRAC pulse hook and the
exchange ringers."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=112, seed=1961)
kit = S.part('kit', 10)
bass = S.part('hootbass', 2)
marimba = S.part('marimba', 3)
vowel = S.part('vowel', 4)
pulse = S.part('pulse', 5)
ringer = S.part('ringer', 6)
organ = S.part('organ', 7)
motor = S.part('motor', 8)
rain = S.part('rain', 9)
party = S.part('party', 11)
news = S.part('news', 12)
tbell = S.part('typebell', 13)
sounder = S.part('sounder', 14)

PROG = 'Am Am F G'
SEQ = {'Am': 'A2 A2 A3 A2 C3 A2 G2 A2', 'F': 'F2 F2 F3 F2 A2 F2 E2 F2', 'G': 'G2 G2 G3 G2 B2 G2 D3 G2'}
VOWEL = 'h E5 D5 | w C5 | h A4 C5 | w B4 | h E5 G5 | w A5 | h G5 F5 | w E5'
HOOK = 'e A5 r A5 C6 r A5 G5 E5 | e A5 r A5 C6 r A5 G5 E5 | e F5 r F5 A5 r F5 E5 C5 | e G5 r G5 B5 r G5 F5 D5'


def seqbass(at, bars, vel=100):
    for k in range(bars):
        notes = SEQ[PROG.split()[k % 4]].split()
        for i in range(16):
            bass.note(at + 4 * k + i * 0.25, pitch(notes[i % 8]) + 12, 0.2, vel - (0 if i % 4 == 0 else 12))


def arps(at, bars, vel=62):
    t, prev = at, None
    for k in range(bars):
        ns = voice_lead(prev, chord(PROG.split()[k % 4], 4), 60, 76); prev = ns
        for i in range(8):
            marimba.note(t + i * 0.5, [ns[0], ns[2], ns[1], ns[2]][i % 4] + (12 if i >= 4 else 0), 0.4, vel)
        t += 4


def electro(at, bars, fill=True):
    groove(kit, 'synthpop', at, bars, fill=fill, extra={CLAP: '....x.......x...'})


t = 0.0
# intro (8): the motor room, relay rain, the dial-tone organ
hold(motor, 0, 48, 32, 80)
rain.note(0, 60, 8, 70); rain.note(16, 60, 8, 76)
organ.chords('Am:8 F:4 G:4 Am:8 F:4 G:4', at=0, style='pad', vel=56, lo=57, hi=72)
seqbass(24, 2, 80)
t = 32
# A (16): the groove, the sequencer, the marimba
electro(t, 16); seqbass(t, 16); arps(t + 16, 12)
ringer.note(t, pitch('A4'), 2, 80)
sounder.chords(' '.join([PROG] * 4), at=t + 32, beats=4, style='block', vel=58, lo=57, hi=72, rhythm=[(0, 0.3), (1.5, 0.3), (3, 0.3)])
t += 64
# B (8): the vowel sings
electro(t, 8); seqbass(t, 8, 94)
vowel.mel(VOWEL, at=t, vel=90)
organ.chords(' '.join([PROG] * 2), at=t, beats=4, style='pad', vel=52, lo=57, hi=72)
tbell.note(t + 28, pitch('A5'), 2, 72)
t += 32
# C (16): the CSIRAC hook, the ringers, everything
ringer.note(t, pitch('A4'), 2, 86)
electro(t, 16); seqbass(t, 16, 104); arps(t, 16, 58)
for k in range(4):
    pulse.mel(HOOK, at=t + 16 * k, vel=90, tr=-12)
vowel.mel(VOWEL, at=t + 32, vel=84)
for k in range(0, 16, 4):
    tbell.note(t + 4 * k + 3.5, pitch('E6'), 1, 66)
t += 64
# break (4): a party line, the newsroom teleprinter
party.note(t, 35, 8, 86); news.note(t + 6, 60, 6, 80)
hold(motor, t, 48, 16, 74)
kit.drums({CHH: 'x.x.x.x.x.x.x.x.'}, at=t + 8, bars=2)
t += 16
# outro (8)
electro(t, 4, fill=False); seqbass(t, 8, 92); arps(t, 8, 54)
pulse.mel(HOOK, at=t, vel=84, tr=-12)
organ.chords('Am:8 F:4 G:4 Am:16', at=t, style='pad', vel=54, lo=57, hi=72)
t += 32
ringer.note(t, pitch('A4'), 3, 80); kit.note(t, KICK, 1, 100); bass.note(t, pitch('A3'), 1, 100)

S.humanize(ms=1, vel=2, parts=['vowel', 'organ'])
finish(__file__, S, {
    'title': 'Fernamt Bielefeld',
    'pack': 'electromech-heritage',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'Electro in A minor, 112 bpm: motor drone, relay rain, dial-tone organ, a Ferranti-hoot sequencer bass, '
            'relay-marimba arpeggios, the 1961 vowel, a CSIRAC pulse hook, exchange ringers, a party line and the '
            'newsroom teleprinter. Drums: Kit Manager 98 (Exchange).',
}, [
    ('kit', 'ch10', 'kit-manager:Exchange', dict(lufs=-17, verb=0.08)),
    ('hootbass', 'ch2', 'Ferranti Hoot', dict(lufs=-19)),
    ('marimba', 'ch3', 'Relay Marimba', dict(lufs=-23, pan=-22, echo=0.2, verb=0.2)),
    ('vowel', 'ch4', '1961 Vowel', dict(lufs=-20, pan=4, echo=0.15, verb=0.35)),
    ('pulse', 'ch5', 'CSIRAC Pulse', dict(lufs=-21, pan=12, echo=0.25, verb=0.15)),
    ('ringer', 'ch6', 'Exchange Ringer', dict(lufs=-24, pan=-10, verb=0.4)),
    ('organ', 'ch7', 'Dial Tone Organ', dict(lufs=-26, pan=18, verb=0.3)),
    ('motor', 'ch8', 'Motor Room', dict(lufs=-29, verb=0.2)),
    ('rain', 'ch9', 'Relay Rain', dict(lufs=-28, pan=-30, verb=0.3)),
    ('party', 'ch11', 'Party Line', dict(lufs=-26, verb=0.3)),
    ('news', 'ch12', 'Newsroom', dict(lufs=-26, pan=20)),
    ('typebell', 'ch13', 'Typewriter Bell Keys', dict(lufs=-26, pan=30, echo=0.3, verb=0.4)),
    ('sounder', 'ch14', 'Sounder Keys', dict(lufs=-25, pan=-16, verb=0.2)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 1.8, 'predelay': 15, 'tone': 5000, 'level': -6})

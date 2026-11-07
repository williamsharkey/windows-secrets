#!/usr/bin/env python3
"""Put XP's captured audio back on the film's timeline.
QEMU's wavcapture only records while the guest is producing sound, so the
capture is the voice clips back to back with the silences squeezed out.
puppet.exe logs every Play press; the answer WAV sizes give each clip's length
(reversed preview = L, final slowed playback = 2L).  This cuts the capture at
those lengths and places each clip at its press time.

  placeaudio.py puppet.log capture.wav "size0 size1 ..." out.wav [lead_seconds] [first_scene]
"""
import sys, wave, re, struct

log, cap, sizes, out = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split()], sys.argv[4]
lead = float(sys.argv[5]) if len(sys.argv) > 5 else 1.5   # recording starts this long before the first scene
first = sys.argv[6] if len(sys.argv) > 6 else 'intro'      # the scene the recording starts with

lines = open(log, encoding='latin-1').read().splitlines()
t_intro = next(float(l.split()[0]) for l in lines if "puppet start: '%s'" % first in l)
plays = [float(l.split()[0]) - t_intro + lead for l in lines if l.strip().endswith('PLAY')]

w = wave.open(cap)
rate, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
data = w.readframes(w.getnframes())
bpf = ch * sw                                        # bytes per frame

clips, k = [], 0
for i, sz in enumerate(sizes):
    L = max(0.0, (sz - 44) / 44100.0)                # 22050 Hz, 16-bit mono source
    for dur in (L, 2 * L):                           # reversed preview, then slowed final
        n = int(dur * rate) * bpf
        clips.append(data[k:k + n]); k += n

total = (max(plays) if plays else 0) + 30
outbuf = bytearray(int(total * rate) * bpf)
for t, clip in zip(plays, clips):
    o = int(t * rate) * bpf
    outbuf[o:o + len(clip)] = clip[:max(0, len(outbuf) - o)]
o = wave.open(out, 'wb')
o.setnchannels(ch); o.setsampwidth(sw); o.setframerate(rate)
o.writeframes(bytes(outbuf))
o.close()
print('placed %d clips at %s' % (min(len(plays), len(clips)), ', '.join('%.1fs' % t for t in plays)))

"""voices: how many recorders one note of a DNA starts (every layer's harmony intervals x unison voices), and the
most a track asks for at one instant (notes starting together x that)."""
import re


def per_note(dna):
    lay = dna.split(';', 1)[0]
    total = 0
    for L in re.split(r'/(?=[a-z])', lay):
        hs = re.findall(r'(?<![A-Za-z])H(-?\d+(?:,-?\d+)*)', L)
        h = len(hs[-1].split(',')) if hs else 1
        us = re.findall(r'(?<![A-Za-z])U(\d+)', L)
        u = int(us[-1]) if us else 1
        total += h * u
    return max(1, total)


def peak_onset(midi_bytes_or_events, window_ticks=10):
    """most note-ons within a few ticks of each other"""
    from collections import Counter
    c = Counter()
    for t in midi_bytes_or_events:
        c[t // window_ticks] += 1
    return max(c.values()) if c else 0

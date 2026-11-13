// BasiliskHost - analysis of rendered audio: levels, onsets against the MIDI, FFT pitch, render comparison
#pragma once
#include "midi.h"
#include <string>
#include <vector>

struct Level { double peak = 0, rms = 0, peakDb = -200, rmsDb = -200; };
Level level(const std::vector<float> &lr, size_t from = 0, size_t to = (size_t)-1);   // frames

struct NoteResult {
    NoteRec n;
    double expectedS = 0;     // where the note should appear in the file: warmup + t + reported latency
    bool heard = false;
    double onsetRawMs = 0;    // onset - (warmup + t): what a host without delay compensation sees
    double onsetErrMs = 0;    // onset - expected: the error after compensating the reported latency
    double hz = 0;            // FFT peak
    double intervalCents = 0; // measured interval to the reference note (log-spectrum shift)
    double centsOff = 0;      // intervalCents minus the MIDI interval
    bool pitched = false;
    double peak = 0, rmsDb = -200;
};

struct NotesSummary {
    int notes = 0, heard = 0, timed = 0, pitched = 0;
    double medianErrMs = 0, meanErrMs = 0, stdErrMs = 0, minErrMs = 0, maxErrMs = 0;
    double maxAbsCents = 0, meanAbsCents = 0;
    int refNote = -1;
};

std::vector<NoteResult> analyze_notes(const std::vector<float> &lr, int sr, double warmup, const Score &s, double latencyS,
                                      NotesSummary &sum);

struct Compare {
    bool identical = false;
    double maxAbsDiff = 0, sampleCorr = 0, envCorr = 0;
    int envShiftMs = 0;
    double diffRmsDb = -200;
};
Compare compare(const std::vector<float> &a, const std::vector<float> &b, int sr);

double peak_hz(const std::vector<float> &mono, size_t from, size_t len, int sr);

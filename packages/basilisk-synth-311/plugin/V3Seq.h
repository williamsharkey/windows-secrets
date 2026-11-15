// BASILISK 16: the mine-grid sequencer and arpeggiator (PRESET-ENGINE-2 section 9) on the host, for the plugin and
// render311. Windows only holds the pattern: the real Minesweeper's board, sent as `grid <w> <h> <state> <cells>`.
// The clock is the host's (its transport: ppq and tempo), or `xb` when the transport stops and `xf` is on. Every
// step's notes go through NoteHost like MIDI notes, stamped on the DAC clock, so they land on the DAW's grid.
// While the DNA has a sequencer (x tokens), the notes played in only choose the root and, for the arpeggiator, the
// notes; they do not sound themselves.
#pragma once
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>
#include "V3Host.h"
#include "../../basilisk-synth/core/engine3.h"

namespace b16v3 {

class Sequencer {
public:
    bool active(const bsynth3::Dna3 &d3) const { return d3.g.x.on; }
    void setGrid(const std::string &line) { bsynth3::Grid g; if (g.parse(line)) { grid_ = g; have_ = true; } }
    bool haveGrid() const { return have_; }
    const bsynth3::Grid &grid() const { return grid_; }
    // a note played in (it chooses the root, or the notes of the arpeggiator); returns true if the sequencer took it
    bool input(uint8_t status, uint8_t d1, uint8_t d2, const bsynth3::Seq &x)
    {
        if (!x.on || (!have_ && !x.hasPattern())) return false;   // no board yet (the Mines tab never opened, a render without --grid): notes play
        const uint8_t st = status & 0xF0;
        if (st == 0x90 && d2 > 0) { if (std::find(held_.begin(), held_.end(), d1) == held_.end()) held_.push_back(d1); std::sort(held_.begin(), held_.end()); latched_.clear(); return true; }
        if (st == 0x80 || st == 0x90) {
            if (x.latch) { latched_ = held_; }
            held_.erase(std::remove(held_.begin(), held_.end(), d1), held_.end());
            return true;
        }
        return false;
    }
    // One block. stamp0: the DAC stamp of the block's first sample (latency included), len: its length in DAC samples,
    // playing/ppq0/bpm: the host transport at the block start. Sends each step's notes through `host`.
    void block(NoteHost &host, const bsynth3::Dna3 &d3, int K, uint64_t stamp0, uint64_t len, bool playing, double ppq0, double bpm,
               const NoteHost::Sink &sink, int scaleId, int rootPc)
    {
        const bsynth3::Seq &x = d3.g.x;
        flushOffs(host, stamp0 + len, sink);
        const bool pat = x.hasPattern();   // 1.5: the DNA's own step pattern (the Steps tab); else an old Minesweeper board
        if (!x.on || (!pat && (!have_ || grid_.w <= 0))) { stopAll(host, stamp0, sink); return; }
        double ppq = ppq0, tempo = bpm;
        if (!playing) {
            if (!x.freeRun) { stopAll(host, stamp0, sink); freePpq_ = -1; return; }
            tempo = x.bpm > 0 ? x.bpm : 120;
            if (freePpq_ < 0) freePpq_ = 0;
            ppq = freePpq_;
        } else freePpq_ = -1;
        if (tempo <= 0) tempo = 120;
        const double spq = 48000.0 * 60.0 / tempo;   // DAC samples per quarter note
        const double ppqEnd = ppq + (double)len / spq;
        const double stepQ = bsynth3::stepPpq(x, 2) / 2.0;   // a step, in quarters (no swing)
        long k = (long)std::floor(ppq / stepQ) - 1;
        if (k < 0) k = 0;
        for (;; k++) {
            const double pk = bsynth3::stepPpq(x, k);
            if (pk >= ppqEnd) break;
            if (pk < ppq || k == lastStep_) continue;
            lastStep_ = k;
            const uint64_t at = stamp0 + (uint64_t)std::llround((pk - ppq) * spq);
            const int L = pat ? patternLength(x) : x.len > 0 ? std::min(x.len, grid_.w) : grid_.w;
            const int col = (int)(k % std::max(1, L));
            const std::vector<int> &held = held_.empty() ? latched_ : held_;
            for (const bsynth3::StepNote &s : pat ? patternNotes(d3, col, L, scaleId, rootPc, held, K) : bsynth3::stepNotes(grid_, col, x, scaleId, rootPc, held, K)) {
                host.midi(0x90, (uint8_t)s.note, (uint8_t)s.vel, at, sink);
                const double lenQ = stepQ * s.lengthSteps * x.gate / 100.0;
                offs_.push_back({at + (uint64_t)std::max(48.0, lenQ * spq), s.note});
            }
            stepCol_ = col; stepAt_ = at;
        }
        if (!playing) freePpq_ = ppqEnd;
    }
    // the pattern's length: xl, else its longest row (16 when empty)
    static int patternLength(const bsynth3::Seq &x)
    {
        if (x.len > 0) return x.len;
        size_t n = x.mel.size(); for (auto &r : x.drums) n = std::max(n, r.size());
        return n ? (int)std::min<size_t>(n, 32) : 16;
    }
    // The notes of step col of the DNA's pattern (Steps tab, help "The Steps Tab"):
    //   melody (xc, a digit per step): 1-8 the scale degree from the root (the held note, transposing like a 303,
    //   else the root K), 9 ties the note before it on, 0 a rest; xu per step: 1 accent, 2/3 an octave up/down,
    //   4/5 accent and an octave up/down;
    //   drums (xe rows, a kit's pads in ascending note order): 1 a hit, 2 an accented hit.
    static std::vector<bsynth3::StepNote> patternNotes(const bsynth3::Dna3 &d3, int col, int L, int scaleId, int rootPc, const std::vector<int> &held, int K)
    {
        const bsynth3::Seq &x = d3.g.x;
        std::vector<bsynth3::StepNote> out;
        auto at = [&](const std::string &r, int c) { return c >= 0 && c < (int)r.size() ? r[(size_t)c] : '0'; };
        const char d = at(x.mel, col);
        if (d >= '1' && d <= '8') {
            int base = held.empty() ? K : held.front();
            if (rootPc >= 0) base -= ((base - rootPc) % 12 + 12) % 12;
            const char m = at(x.mod, col);
            int note = base + bsynth3::degreeToSemis(scaleId < 0 || scaleId >= bsynth3::kScaleCount ? 0 : scaleId, d - '1');
            if (m == '2' || m == '4') note += 12;
            if (m == '3' || m == '5') note -= 12;
            const bool acc = m == '1' || m == '4' || m == '5';
            int steps = 1;
            for (int c = col + 1; c < col + L && at(x.mel, c % L) == '9'; c++) steps++;   // ties hold it on
            out.push_back({std::max(0, std::min(127, note)), acc ? 127 : 96, steps});
        }
        if (!x.drums.empty()) {
            std::vector<int> notes;   // the kit's pad notes, ascending, one row each
            for (auto &p : d3.g.pads) if (std::find(notes.begin(), notes.end(), p.lo) == notes.end()) notes.push_back(p.lo);
            std::sort(notes.begin(), notes.end());
            for (size_t r = 0; r < x.drums.size(); r++) {
                const char c = at(x.drums[r], col);
                const int note = r < notes.size() ? notes[r] : 36 + (int)r;
                if (c == '1' || c == '2') out.push_back({note, c == '2' ? 127 : 100, 1});
            }
        }
        return out;
    }
    int stepCol() const { return stepCol_; }
    uint64_t stepAt() const { return stepAt_; }

private:
    struct Off { uint64_t at; int note; };
    bsynth3::Grid grid_;
    bool have_ = false;
    std::vector<int> held_, latched_;
    std::vector<Off> offs_;
    long lastStep_ = -1;
    double freePpq_ = -1;
    int stepCol_ = -1; uint64_t stepAt_ = 0;
    void flushOffs(NoteHost &host, uint64_t upTo, const NoteHost::Sink &sink)
    {
        std::stable_sort(offs_.begin(), offs_.end(), [](const Off &a, const Off &b) { return a.at < b.at; });
        size_t n = 0;
        for (; n < offs_.size() && offs_[n].at < upTo; n++) host.midi(0x80, (uint8_t)offs_[n].note, 0, offs_[n].at, sink);
        offs_.erase(offs_.begin(), offs_.begin() + (long)n);
    }
    void stopAll(NoteHost &host, uint64_t at, const NoteHost::Sink &sink)
    {
        for (const Off &o : offs_) host.midi(0x80, (uint8_t)o.note, 0, at, sink);
        offs_.clear();
        lastStep_ = -1;
    }
};

}  // namespace b16v3

// PRESET ENGINE 2 prototype: the host-side logic behind the v3 PROPOSAL, as pure functions (no guest, no core edits).
//   - window():   one voice's playback window in frames (owner wish 1)
//   - MonoPlan:   what a mono/legato/continue layer sends for each key event (owner wish 2)
//   - Grid:       the mine-grid board as the guest reports it, and the notes of one step (owner wish 6)
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "dna3.h"

namespace bsynth3 {

// A small deterministic random source. Seeds: per note-on (default), per key (Yk), per recorder (Yr).
struct Rng {
    uint32_t s;
    explicit Rng(uint32_t seed) : s(seed ? seed : 0x9E3779B9u) {}
    uint32_t next() { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return s; }
    int in(int lo, int hi) { return hi <= lo ? lo : lo + (int)(next() % (uint32_t)(hi - lo + 1)); }
};

// ---------------------------------------------------------------- 1. the playback window
struct Span { uint32_t from = 0, to = 0; };   // frames of the layer's built buffer, [from, to)
// frames: the layer's length (the guest's `layer` reply). rate: its sample rate. vel 1..127. minMs: the shortest
// window allowed (XP: 10 ms, so the per-handle volume ramp has at least two steps).
Span window(const Window &w, uint32_t frames, int rate, int vel, Rng &rng, int minMs = 10);
// The XP fast path plays bytes [from * blockAlign, to * blockAlign) of the recorder's own PCM.
inline uint32_t byteOf(uint32_t frame, int blockAlign) { return frame * (uint32_t)blockAlign; }
// "Bake": a fixed window as Sound Recorder steps (@t, [, ]) on the buffer. Empty when the window is random.
std::string bakeSteps(const Window &w, uint32_t frames, int rate);

// ---------------------------------------------------------------- 2. mono, legato, continue
// One mono layer's decisions. The caller turns them into wire lines (on / rate / off / cut).
struct Action {
    enum Kind { On, Rate, Off, Cut } kind;
    int note;          // the pitch it sounds (On, Rate) or the note it ends
    int glideMs = 0;   // Rate: ramp time
    bool regate = false;   // Rate: the voice was releasing; hold it again
};
class MonoPlan {
public:
    explicit MonoPlan(const VoiceMode &m) : m_(m) {}
    // t: time in ms. soundingUntil: when the current voice's buffer ends at its current rate (from the host's
    // finish estimate); after that a Rate is useless and an On is sent instead.
    std::vector<Action> keyDown(int note, double t, double soundingUntil);
    std::vector<Action> keyUp(int note, double t, double soundingUntil);
    int sounding() const { return cur_; }
private:
    VoiceMode m_;
    std::vector<int> held_;   // in press order
    int cur_ = -1;            // the pitch the layer sounds now (-1: silent)
    bool gated_ = false;
    int pick() const;         // the note priority (k) among held_
};

// ---------------------------------------------------------------- 6. the mine grid
// The guest's `grid <w> <h> <state> <cells>` line. cells: row-major, top row first:
//   '.' hidden  '0'..'8' revealed  'F' flag  '?' question mark  '*' mine shown  'X' exploded mine  'x' wrong flag
struct Grid {
    int w = 0, h = 0;
    char state = 'n';             // n new, p playing, w won, l lost
    std::string cells;
    bool parse(const std::string &line);   // false: not a grid line, or the sizes do not match
    char at(int col, int rowFromBottom) const { return cells[(size_t)((h - 1 - rowFromBottom) * w + col)]; }
};
struct StepNote { int note, vel; int lengthSteps; };
// The notes of step `col`. held: the notes held now, sorted low to high (the root is held[0], or K when empty).
std::vector<StepNote> stepNotes(const Grid &g, int col, const Seq &x, int scale, int rootPc, const std::vector<int> &held, int K);

}  // namespace bsynth3

// DNA v3 host-side logic (design/PRESET-ENGINE-2.md sections 3-9), as pure functions: no guest, no core edits.
// Status: tested code, ready to fold into core/voices.cpp once both v1.2 releases ship.
//   - window():      one voice's playback window in frames (wish 1)
//   - MonoPlan:      what a mono / legato / continue layer sends for each key event (wish 2)
//   - stacking:      round-robin / random intervals, strum, layer groups, humanize (wish 2); degree chords: scales.h
//   - zones, rate modulation (wow, flutter, scoop) and its XP staircase (wish 3)
//   - Grid:          the mine-grid board as the guest reports it, and the notes of one step (wish 6)
//   - wire:          the v3 guest-link lines (section 3)
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
// The seed of one voice's random draws (W ranges, Y humanize, Sx, Sp): per key with Yk, per recorder with Yr
// (both: key and recorder), else a running note counter. A DNA-wide salt keeps two presets apart.
uint32_t voiceSeed(const Human &y, int note, int rec, uint32_t noteCounter, uint32_t salt);

// ---------------------------------------------------------------- 1. the playback window
struct Span { uint32_t from = 0, to = 0; };   // frames of the layer's built buffer, [from, to)
// frames: the layer's length (the guest's `layer` reply). rate: its sample rate. vel 1..127. minMs: the shortest
// window allowed (10 ms: two of the guest's 5 ms gain steps).
Span window(const Window &w, uint32_t frames, int rate, int vel, Rng &rng, int minMs = 10);
// "Bake": a fixed window as Sound Recorder steps (@t, [, ]) on the buffer. Empty when the window is random.
// Note: the guests seek in 1/1000 of the length (DNA.md @t), so a bake is exact to 1/1000 of the length.
std::string bakeSteps(const Window &w, uint32_t frames, int rate);

// ---------------------------------------------------------------- 2. mono, legato, continue
struct Action {
    enum Kind { On, Rate, Off, Cut } kind;
    int note;              // the pitch it sounds (On, Rate) or the note it ends
    int glideMs = 0;       // Rate: ramp time
    bool regate = false;   // Rate: the voice was releasing; hold it again
};
class MonoPlan {
public:
    explicit MonoPlan(const VoiceMode &m) : m_(m) {}
    // t: time in ms. soundingUntil: when the current voice's buffer (or window) ends at its current rate, from the
    // host's finish estimate; after that a Rate is useless and an On is sent instead.
    std::vector<Action> keyDown(int note, double t, double soundingUntil);
    std::vector<Action> keyUp(int note, double t, double soundingUntil);
    int sounding() const { return cur_; }
    bool gated() const { return gated_; }
    void reset() { held_.clear(); cur_ = -1; gated_ = false; }
private:
    VoiceMode m_;
    std::vector<int> held_;   // in press order, each note once
    int cur_ = -1;            // the pitch the layer sounds now (-1: silent)
    bool gated_ = false;
    int pick() const;         // the note priority (k) among held_
    void moveTo(int n, bool alive, std::vector<Action> &a);
};

// ---------------------------------------------------------------- 3. stacking and humanize
// The harmony intervals one note sounds: all of H (default), the next one (Sr, counter = notes so far), one at
// random (Sx). Degree harmony (the D token) is resolved by scales.h voiceOffsets, in cents.
std::vector<int> noteIntervals(const Stack &s, const std::vector<int> &H, uint32_t counter, Rng &rng);
// Strum: the start delay of harmony voice k (the v2 `on` delay field).
inline int strumDelayMs(const Stack &s, int k) { return s.strumMs * k; }
// Unison voice u of n: pan offset (-100..100) when Sw spreads them.
int unisonPan(const Stack &s, int u, int n);
// Layer groups (Sg): which layer of group g sounds for this note. groupLayers: the layers with that group number,
// in layer order. counter: the group's notes so far (round-robin) or rng (Sgx).
int groupPick(const std::vector<int> &groupLayers, bool random, uint32_t counter, Rng &rng);
struct HumanDraw { int cents = 0, levelPct = 100, lateMs = 0, pan = 0; };
HumanDraw humanize(const Human &y, Rng &rng);

// ---------------------------------------------------------------- 4. zones and rate modulation
inline bool inZone(const Zone &z, int note) { return note >= z.lo && note <= z.hi; }
// The note that plays at the buffer's own rate in this zone: the zone root, else the DNA's K.
inline int zoneRoot(const Zone &z, int K) { return z.root >= 0 ? z.root : K; }
// The pitch offset in cents at t ms after the voice started (wow + flutter + scoop). phase: the voice's random
// starting phase (0..1), so voices do not wobble together.
double modCents(const Mod &m, double tMs, double phase);
// XP plays rate changes as handle swaps (5.3). The staircase for a voice: one entry per swap, at most one swap
// every stepMs, cents quantized to qCents; flutter is left out (too fast for swaps: XP uses unison instead).
struct RateStep { int tMs; int cents; };
std::vector<RateStep> xpStaircase(const Mod &m, int durMs, double phase, int stepMs = 40, int qCents = 2);

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
// The sample position of step k in a block, from the host transport: ppq of the block start, samples per quarter.
// Returns the step index and its offset in samples from ppq0 (swing delays odd steps by x.swing % of a step).
double stepPpq(const Seq &x, long k);

// ---------------------------------------------------------------- 15. kit mode
// The pad that sounds for this note and velocity: among the pads whose notes and velocity window hold it, the
// next in turn (counter: hits of this note so far) or a random one (any matching pad has z). -1: none (silence).
int pickPad(const std::vector<Pad> &pads, int note, int vel, uint32_t counter, Rng &rng);
// The pad's pitch in cents from the buffer's own rate: (note - root) * p %, held within +-w semitones, plus tune.
double padCents(const Pad &p, int note);
// The pad's gain for a velocity, 0..1: curve (0 linear, 1 soft, 2 hard, 3 fixed) and amount % (-1: globalV).
double padGain(const Pad &p, int vel, int globalV);
// The pads a hit of pad i silences, with their fade: every pad of i's cut group (i itself too) and every pad of
// the groups i mutes.
std::vector<int> chokeTargets(const std::vector<Pad> &pads, int i);
// The guest's `seg <layer> <f0> <f1> ...` reply: where each segment of a kit strip starts, in frames, plus the
// end. The frames [from, to) of a pad's window inside its segment (j = 0: the whole buffer).
Span padWindow(const Pad &p, const std::vector<uint32_t> &segStarts, uint32_t frames, int rate, Rng &rng);

// ---------------------------------------------------------------- the v3 wire (section 3)
// `hi 3 <edition> <state> <caps>` -> the caps (comma list). Empty when the line is not a v3 hello.
std::vector<std::string> parseHi3(const std::string &line, std::string *edition = nullptr);
bool hasCap(const std::vector<std::string> &caps, const std::string &c);
std::string onLine(int rec, int rate, int vol, int pan, int delayMs, int layer, Span w);
std::string rateLine(int rec, int hz, int glideMs, bool regate);
std::string lmodLine(int layer, const Mod &m);
std::string lgrainLine(int layer, const Grain &g);

}  // namespace bsynth3

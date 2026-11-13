// PRESET ENGINE 2 prototype: the DNA v3 PROPOSAL tokens (design/PRESET-ENGINE-2.md section 2).
// This file does NOT change the shared core. It reads the v3 tokens out of a DNA string next to core's v2 parse,
// and it removes them (strip3) so a test can prove that a v2 parser hears exactly the v2 subset.
// Dependency-free C++17.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace bsynth3 {

// A fraction 0..1 of the layer's built buffer, stored in 1/10000 (DNA text: "0", "1", ".25", "0.2", "1.0").
constexpr int kOne = 10000;
struct Range { int lo = 0, hi = 0; bool random() const { return hi != lo; } };

// W: the playback window of each voice (owner wish 1)
struct Window {
    Range s{0, 0};            // Ws  start
    Range e{kOne, kOne};      // We  end (a cap when Wl is given)
    Range l{-1, -1};          // Wl  length (-1: not given; end = e)
    int vel = 0;              // Wv  velocity moves the start toward 0, 0..kOne (kOne: velocity 127 starts at 0)
    int maxMs = 0;            // Wm  real-time cap in ms (tape length); 0 = none
    bool given = false;
};
// N: voice mode (owner wish 2)
struct VoiceMode {
    char mode = 'p';          // p poly, m mono (retrigger), l legato, c continue
    int poly = 0;             // Np<n>: at most n notes at once in this layer (0: the pool decides)
    int glideMs = 0;          // g<ms>
    char prio = 'n';          // k: n newest, h highest, l lowest
    bool given = false;
};
// S: stacking (owner wish 2)
struct Stack {
    bool roundRobin = false;  // Sr  each note takes the next H interval only
    bool randomPick = false;  // Sx  each note takes one random H interval
    bool randomRec = false;   // Sp  a random free recorder of the pool, not the oldest
    int group = 0;            // Sg<n> layers with the same n take turns, one layer per note
    bool groupRandom = false; // Sgn then 'x' flag is written as Sg<n>x: a random layer of the group
    int strumMs = 0;          // Ss<ms> harmony voice k starts k*ms later
    int diatonic = 0;         // Sd<n> n-note chord in thirds of the global scale q (replaces H)
    int width = 0;            // Sw<frac> unison voices spread over +-width pan
    bool given = false;
};
// Y: per-note random (humanize) and its seed (owner wishes 2, 3)
struct Human {
    int detune = 0, level = 0, timeMs = 0, pan = 0;   // Yd cents (+-), Yl % (down), Yt ms (later), Yq pan (+-)
    bool perKey = false, perRec = false;              // Yk: seed = note number; Yr: seed = recorder
    bool given = false;
};
// V: rate modulation (owner wish 3: wow, flutter, start scoop)
struct Mod {
    int wowCents = 0, wowDeciHz = 0;     // Vw<c>,<0.1 Hz>
    int fluCents = 0, fluHz = 0;         // Vf<c>,<Hz>
    int scoopCents = 0, scoopMs = 0;     // Vs<c>,<ms>  start flat by c cents, reach pitch in ms
    bool given = false;
};
// Z: key zone (owner wish 3: tape keyboards are one tape per key; zones keep the rate ratio small)
struct Zone { int lo = 0, hi = 127, root = -1; bool given = false; };
// G: grains (owner wish 4)
struct Grain {
    bool on = false;
    int pos = 0;              // Gp<frac> position in the window
    int spray = 0;            // Gj<frac> random +- position
    int sizeMs = 80, sizeHiMs = 80;   // Gz<ms>[~<ms>]
    int density = 20;         // Gn<grains per second per note>
    int cents = 0;            // Gc<cents> random +- pitch
    int octPct = 0;           // Go<%> chance of +12
    int shape = 2;            // Ge<0..3> rect, triangle, smooth, percussive
    int scan = 0;             // Gs<x> position speed as a multiple of real time, in 1/10000 (kOne = 1x)
    bool back = false;        // Gb  scan backward
    bool freeze = false;      // Gf  position holds
    int streams = 4;          // Gv<n> recorders (streams) per note
    int width = 0;            // Gw<frac> random pan width
    bool sync = false;        // Gy  density counts grains per beat, on the beat grid
};
struct Layer3 {
    Window w; VoiceMode n; Stack s; Human y; Mod v; Zone z; Grain g;
    std::vector<std::string> tokens;   // canonical v3 tokens of this layer, in letter order W N S Y V Z G
};
// q: scale; x: the mine-grid sequencer (owner wish 6)
struct Seq {
    bool on = false;
    int div = 16; bool triplet = false;   // xd<4|8|16|32>[t]
    int gate = 80, swing = 0;             // xg<%>, xs<%>
    int kind = 0;                         // xk<0|1|2>: field, count, arp
    int poly = 4;                         // xp<n> notes per step at most
    int autodig = 3;                      // xa<n> cells the guest digs after New Game
    int octaves = 2;                      // xo<n>
    int len = 0;                          // xl<n> steps used (0: board width)
    int bpm = 120; bool freeRun = false;  // xb<bpm>, xf: run on bpm when the host transport stops
    bool latch = false;                   // xh
};
struct Globals3 { int scale = -1, rootPc = -1; Seq x; std::vector<std::string> tokens; };
struct Dna3 { std::vector<Layer3> layers; Globals3 g; };

// The v3 token letters. Layer: W N S Y V Z G (never used in a v1/v2 layer). Global: q x (never used in v1/v2).
bool isLayerLetter(char c);
bool isGlobalLetter(char c);
// Read the v3 tokens. Layers are split exactly as core splits them ('/' between layers, ';' before globals).
Dna3 parse3(const std::string &dna);
// The DNA with every v3 token removed: what a v1/v2 parser effectively reads.
std::string strip3(const std::string &dna);
// The canonical v3 tokens of a layer / of the globals (for the UI and for "Bake").
std::string layerTokens(const Layer3 &L);
std::string globalTokens(const Globals3 &g);
// Fraction text helpers
int readFrac(const std::string &s, size_t &p);     // "0" "1" ".25" "0.2" "1.0" -> 0..kOne (clamped)
std::string fracText(int v);                         // 2500 -> ".25", 0 -> "0", 10000 -> "1"

// Scales for q, Sd and the sequencer: semitone steps from the root. Index = q id.
struct Scale { const char *name; int n; int step[8]; };
extern const Scale kScales[];
constexpr int kScaleCount = 13;
int degreeToSemis(int scale, int degree);           // degree 0.. (wraps into octaves)

}  // namespace bsynth3

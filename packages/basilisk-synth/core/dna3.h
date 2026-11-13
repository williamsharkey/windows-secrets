// DNA v3 (design/PRESET-ENGINE-2.md section 2): the tokens that v3 adds to a v2 DNA.
//
// Merged into core/ as its own files (2026-11-13), next to dna.cpp, which it does not change: it reads
// the v3 tokens next to core's v2 parse (bsynth::parse), and builds the v3 canonical form on top of core's.
//
// Token boundaries are exactly DNA.md 5.7's (the v2 "keep unknown tokens" rule), so v2 core, v3 and later
// versions all cut a string into the same tokens:
//   - a layer token is an uppercase letter, then lowercase letters, digits, '.', ',' and '~';
//   - a global token is a letter, then the same characters except 'm' (which always starts a macro);
//     in v3, the lowercase letters 'q' and 'x' also start a new global token (they are v3 global letters);
//   - a macro token is 'm', then K, then '=' or a layer digit and a parameter letter, then digits , . ~ -.
// Inside a v3 token, a lowercase letter starts a subkey; its value is the digits , . ~ that follow. A subkey that
// v3 does not know is kept verbatim (forward compatibility, so a v4 subkey survives a v3 save).
// Dependency: core/dna.h (only for canonical3 and the v2 macro value rule).
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
};
// N: voice mode (owner wish 2)
struct VoiceMode {
    char mode = 'p';          // p poly, m mono (retrigger), l legato, c continue
    int poly = 0;             // Np<n>: at most n notes at once in this layer (0: the pool decides)
    int glideMs = 0;          // g<ms>
    char prio = 'n';          // k<n|h|l>: newest, highest, lowest
};
// S: stacking (owner wish 2)
struct Stack {
    bool roundRobin = false;  // Sr  each note takes the next H interval only
    bool randomPick = false;  // Sx  each note takes one random H interval
    bool randomRec = false;   // Sp  a random free recorder of the pool, not the oldest
    int group = 0;            // Sg<n> layers with the same n take turns, one layer per note
    bool groupRandom = false; // Sg<n>x: a random layer of the group
    int strumMs = 0;          // Ss<ms> harmony voice k starts k*ms later
    int diatonic = 0;         // Sd<n> n-note chord in thirds of the global scale q (replaces H)
    int width = 0;            // Sw<frac> unison voices spread over +-width of the pan range
};
// Y: per-note random (humanize) and its seed (owner wishes 2, 3)
struct Human {
    int detune = 0, level = 0, timeMs = 0, pan = 0;   // Yd cents (+-), Yl % (down), Yt ms (later), Yq pan (+-)
    bool perKey = false, perRec = false;              // Yk: seed = note number; Yr: seed = recorder
};
// V: rate modulation (owner wish 3: wow, flutter, start scoop)
struct Mod {
    int wowCents = 0, wowDeciHz = 0;     // Vw<c>,<0.1 Hz>
    int fluCents = 0, fluHz = 0;         // Vf<c>,<Hz>
    int scoopCents = 0, scoopMs = 0;     // Vs<c>,<ms>  start flat by c cents, reach pitch in ms
};
// Z: key zone (owner wish 3)
struct Zone { int lo = 0, hi = 127, root = -1; };
// G: grains (owner wish 4)
struct Grain {
    int pos = 0;              // Gp<frac> position in the window
    int spray = 0;            // Gj<frac> random +- position
    int sizeMs = 80, sizeHiMs = 80;   // Gz<ms>[~<ms>]
    int density = 20;         // Gn<grains per second per note>
    int cents = 0;            // Gc<cents> random +- pitch
    int octPct = 0;           // Go<%> chance of +12
    int shape = 2;            // Ge<0..3> rect, triangle, smooth, percussive
    int scan = 0;             // Gs<x> position speed as a multiple of real time, in 1/10000 (kOne = 1x), 0..4x
    bool back = false;        // Gb  scan backward
    bool freeze = false;      // Gf  position holds
    int streams = 4;          // Gv<n> recorders (streams) per note
    int width = 0;            // Gw<frac> random pan width
    bool sync = false;        // Gy  density counts grains per beat, on the beat grid
};
// The v3 layer letters, in canonical order.
constexpr char kLayerLetters[] = "WNSYVZG";
struct Layer3 {
    Window w; VoiceMode n; Stack s; Human y; Mod v; Zone z; Grain g;
    bool has[7] = {false, false, false, false, false, false, false};   // a token of letter kLayerLetters[i] was read
    std::string extra[7];      // unknown subkeys of each letter, verbatim, in written order
    bool grains() const { return has[6]; }
    std::string tokens() const; // canonical v3 tokens of this layer, in letter order W N S Y V Z G
};
// q: scale; x: the mine-grid sequencer (owner wish 6)
struct Seq {
    bool on = false;
    int div = 16; bool triplet = false;   // xd<4|8|16|32>[t]
    int gate = 80, swing = 0;             // xg<%>, xs<%>
    int kind = 0;                         // xn<0|1|2>: field, count, arp (n, not k: k starts a kit pad)
    int poly = 4;                         // xp<n> notes per step at most
    int autodig = 3;                      // xa<n> cells the guest digs after New Game
    int octaves = 2;                      // xo<n>
    int len = 0;                          // xl<n> steps used (0: board width)
    int bpm = 120; bool freeRun = false;  // xb<bpm>, xf: run on bpm when the host transport stops
    bool latch = false;                   // xh
};
// v3 macro parameters (section 2.1): mK L P lo,hi with P one of these letters
//   W start, E end, Y length (1/1000); P grain position, I spray (1/1000); X grain size (ms); U density (/s);
//   F scan (1/1000 of real time); H wow depth (cents); J glide (ms)
constexpr char kMacroParams3[] = "WEYPIXUFHJ";
struct MacroMap3 { int macro = 1, layer = 0; char param = 'W'; int lo = 0, hi = 0; };
// k: one kit pad (section 15). A DNA with at least one pad is a kit: notes sound only through pads.
//   k<lo>[,<hi>]  the notes;  l layer 1..8;  j segment of the layer's buffer (0 whole, 1 the source, 2.. each
//   Insert File);  s, e start/end in the segment (fractions, ~ ranges);  r root;  p pitch tracking %;  w pitch
//   range +- semitones (0: no limit);  t / b tune up / down in cents;  i level %;  h pan 0..200 (100 centre);
//   v velocity curve 0 linear 1 soft 2 hard 3 fixed;  a velocity amount % (-1: the global V);  y velocity window
//   lo,hi;  g gated;  c cut group 1..16;  f choke fade ms;  u mutes group(s) n[,n..];  n voices (0: the layer's
//   pool);  o output pair 1..8;  z random among matching pads (else round-robin).
// A k token with no note is kit-wide: d = kit off (the map is kept, the DNA plays as layers).
struct Pad {
    int lo = 0, hi = 0, layer = 1, seg = 0;
    Range s{0, 0}, e{kOne, kOne};
    int root = -1, pitchPct = 0, rangeSemis = 0, tuneCents = 0, level = 100, pan = 0;
    int curve = 0, velAmount = -1, velLo = 1, velHi = 127;
    bool gated = false, random = false;
    int cut = 0, fadeMs = 10, voices = 0, out = 1;
    std::vector<int> mutes;
    std::string extra;
    std::string token() const;
};
struct Globals3 {
    int scale = -1, rootPc = -1;          // q<id>[r<pc>]
    Seq x;
    std::vector<MacroMap3> maps;
    std::vector<Pad> pads;                // k tokens, in written order
    bool kitOff = false;                  // kd
    std::string qExtra, xExtra, kExtra;   // unknown subkeys, verbatim
    bool hasQ = false;
    bool kit() const { return !pads.empty() && !kitOff; }
    std::string tokens() const;           // canonical: q, x, the kit (kit-wide token, then pads in order), the v3 macro maps
};
struct Dna3 { std::vector<Layer3> layers; Globals3 g; };

bool isLayerLetter(char c);
bool isGlobalLetter(char c);
bool isMacroParam3(char c);
// Read the v3 tokens. Layers are split exactly as core splits them ('/' between layers, ';' before globals, at
// most 8 layers, 1024 bytes, no spaces or control characters).
Dna3 parse3(const std::string &dna);
// The DNA with every v3 token (layer, global and v3 macro) removed: what a v1/v2 parser should mean.
std::string strip3(const std::string &dna);
// The v3 canonical form: core's canonical form of the v2 part, each layer followed by its v3 tokens, the globals
// followed by the v3 global tokens. Idempotent. For a string without v3 tokens it equals bsynth::canonical.
std::string canonical3(const std::string &dna);
// The DNA as it sounds with the v3 macro maps applied (macro values: core's Globals.macro, effective values
// after the mod wheel). Mapped fields are replaced; several maps on one field add up as in v2 (DNA.md 5.3).
Dna3 applyMacros3(const Dna3 &d, const int macro[4]);

// Fraction text helpers
int readFrac(const std::string &s, size_t &p);     // "0" "1" ".25" "0.2" "1.0" -> 0..4*kOne
std::string fracText(int v);                         // 2500 -> ".25", 0 -> "0", 10000 -> "1"

// Scales for q, Sd and the sequencer: semitone steps from the root. Index = q id.
struct Scale { const char *name; int n; int step[12]; };
constexpr int kScaleCount = 13;
extern const Scale kScales[kScaleCount];
int degreeToSemis(int scale, int degree);           // degree 0.. (negative and large degrees wrap into octaves)

}  // namespace bsynth3

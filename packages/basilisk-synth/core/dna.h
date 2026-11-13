// BASILISK SYNTH shared core: the DNA (DNA.md section 2). Dependency-free C++17, shared by the XP and 3.11 plugins.
#pragma once
#include <string>
#include <vector>

namespace bsynth {

constexpr int kRecorders = 16, kMaxLayers = 8, kMaxSteps = 64, kMaxHarmony = 8, kMaxDnaBytes = 1024;
constexpr int kMaxBufferMs = 30000;   // a step that would make a buffer longer than this is skipped (both sides)

// The Media sounds (section 2.4), in table order. index 0..34.
extern const char *const kSoundNames[];
extern const char *const kSoundFilesXP[];
constexpr int kSoundCount = 35;
int soundIndex(const std::string &name);          // -1 if unknown
// Windows 3.11 edition: only chimes, ding, ringin, ringout exist in C:\WINDOWS; every other NAME plays ding.
const char *soundFile311(int index);               // "C:\\WINDOWS\\DING.WAV" etc.

struct Step {
    char op = 0;          // + - > < E R @ [ ] C P X I M
    int arg = 0;          // @: percent 0..99
    int sound = -1;       // I, M: sound index
};

struct Layer {
    int source = -1;                 // sound index; -1 = unknown NAME: silent and empty
    std::vector<Step> steps;         // in order (at most kMaxSteps)
    int pool = 0;                    // #N as written (0 = not given)
    int transpose = 0;               // T
    std::vector<int> harmony{0};     // H
    int unison = 1, spreadCents = 0; // U N ~ C
    bool fixed = false;              // F
    int level = 100;                 // L, percent 0..400
    std::vector<std::string> tokens; // canonical text of each step/gene, in written order (source first)
    // filled by assignPools():
    int first = 0, count = 0;
    bool valid() const { return source >= 0; }
};

struct Globals {
    int attack = 0, decay = 0, sustain = 100, release = 120, bendRange = 2, velocity = 100, root = 60, gainDb = 0;
    std::vector<std::string> tokens;   // canonical global tokens in written order
};

struct Dna {
    std::vector<Layer> layers;
    Globals g;
    std::string canonical;
    // the part that needs Sound Recorder to rebuild (layers only; globals never need a rebuild)
    std::string layersText() const;
};

Dna parse(const std::string &text);       // never fails; pools assigned; canonical filled
std::string canonical(const std::string &text);
void assignPools(Dna &d);

// Edit a global (letter A D S R B V K G) and return the new canonical DNA (replaces its last occurrence, or appends).
std::string setGlobal(const std::string &dna, char letter, int value);
// Edit layer i's voice gene (letter T L U F #) the same way. For 'U', value = N, value2 = cents.
std::string setLayerGene(const std::string &dna, int layer, char letter, int value, int value2 = 0);
// Replace layer i's source NAME.
std::string setLayerSource(const std::string &dna, int layer, const std::string &name);
// Append a step to layer i (op, plus arg/sound name as needed).
std::string appendStep(const std::string &dna, int layer, char op, int arg = 0, const std::string &name = "");

// Clamp ranges used by the parser.
int clampGlobal(char letter, int v);

}  // namespace bsynth

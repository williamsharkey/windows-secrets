// Keys, scales and tunings (design/PRESET-ENGINE-2.md section 18): the scale library, 12-note masks, equal
// temperaments, just intonation, Scala .scl/.kbm import, degree harmony, snapping and the keyboard remap.
// Everything is resolved on the host (deterministic renders): the guest only ever gets rates.
// Pitches are in cents; MIDI note n is 100 n cents in 12-TET (C-1 = 0).
#pragma once
#include <string>
#include <vector>

namespace bsynth3 {

// A tuning: the steps of one period, in cents from the root, steps[0] == 0, ascending, all < period.
struct Tuning {
    std::string name;
    double period = 1200;
    std::vector<double> steps{0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100};
    int refNote = 60;            // .kbm: the anchor key (remap) and the reference note
    double refHz = 261.6255653;  // .kbm: its frequency (not needed for 12-TET-relative playing; kept for export)
    int size() const { return (int)steps.size(); }
    bool twelve() const;         // a subset of 12-TET (a mask): the piano layout applies
};

// The built-in library. Ids are stable (they are written in DNAs as q<id>): 0-12 are the v3 sequencer's scales.
struct LibScale { int id; const char *word; const char *category; const char *label; };
const std::vector<LibScale> &scaleLibrary();
bool libraryTuning(int id, Tuning &t);           // false: no such id
int libraryId(const std::string &word);          // "minor" -> 1; -1 if unknown
// 12-note masks: bit k = pitch class k above the root (bit 0 = the root, always on)
Tuning maskTuning(unsigned mask, const std::string &name = "custom");
unsigned tuningMask(const Tuning &t);            // 0 if not a 12-TET subset
Tuning edo(int n);                               // n equal steps per octave
// Scala: .scl text -> tuning (false and a message on an error); .kbm: the anchor (middle note) and reference
bool parseScl(const std::string &text, Tuning &t, std::string *err = nullptr);
bool parseKbm(const std::string &text, Tuning &t, std::string *err = nullptr);
// The compact state form: "t1;name;period;c1,c2,...;refNote;refHz" (cents to 3 decimals)
std::string tuningText(const Tuning &t);
bool tuningFromText(const std::string &s, Tuning &t);

// Snapping a played note that is not in the scale
enum Snap { SnapDefault = 0, SnapNearest = 1, SnapDown = 2, SnapUp = 3, SnapOff = 4 };   // Off: chromatic pass-through

// The effective key: root pitch class (0 = C) and tuning; remap: consecutive keys walk consecutive steps from anchor
struct Key {
    int root = 0;
    Tuning tuning;               // default: C major (library id 0)
    bool remap = false;
    int anchor = 60;             // remap: this key plays the root (in the octave of the anchor)
    int snap = SnapNearest;      // the global default for presets that do not choose
    Key();
};

// Degree harmony (the v3 D token): degrees counted in scale steps, 1 = the played note
struct Degrees {
    std::vector<int> up{1};      // h: 1, 3, 5 ... (8 = an octave up in a 7-note scale)
    std::vector<int> down;       // b: 5 = the fifth degree below (a fourth down in major) ...
    int inversion = 0;           // i: the lowest n chord notes go up a period
    int snap = SnapDefault;      // s: 1 nearest, 2 down, 3 up, 4 off
    bool given = false;
};

// The pitch of one played key: cents (absolute, 12-TET scale: 100 per semitone) and its step in the tuning.
struct Played { double cents; long step; bool inScale; };
Played playKey(const Key &k, int note, int snap);
// The voices of one note: absolute cents of each degree (sorted low to high, inversion applied)
std::vector<double> degreeVoices(const Key &k, const Degrees &d, int note, int snapDefault);
// Offsets in cents from the played note's 12-TET pitch (what core adds to its rate): one per voice
std::vector<double> voiceOffsets(const Key &k, const Degrees &d, int note, int snapDefault);
// Labels for the keyboard strip (ASCII): 0 none, 1 degree numbers, 2 sargam, 3 note names, 4 cents
std::string stepLabel(const Key &k, long step, int mode);

}  // namespace bsynth3

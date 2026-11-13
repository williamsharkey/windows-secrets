// BasiliskHost - MIDI: Standard MIDI Files, the built-in test pattern, winmm input
#pragma once
#include "host.h"
#include <functional>
#include <string>
#include <vector>

// a note as the analysis sees it
struct NoteRec {
    double t, dur;
    int note, vel;
    std::string section;    // "scale", "chords", "repeats", "sustain", "bend", "file"
    bool single = true;     // the only note starting at t (pitch can be measured)
};

struct Score {
    std::vector<MidiMsg> msgs;   // sorted by t (seconds)
    std::vector<NoteRec> notes;
    double length = 0;           // last event time
};

bool read_midi_file(const std::string &path, Score &out, std::string &err);
bool write_midi_file(const std::string &path, const Score &s);
// sections: any of scale,chords,repeats,sustain,bend (comma separated) or "all"
Score test_pattern(const std::string &sections = "all");
// "t:note:vel:dur,..." (seconds), as bsynth-host --score
Score parse_score(const std::string &spec);
void finish_score(Score &s);   // sort, derive notes, length

// winmm MIDI input
std::vector<std::string> midi_in_devices();
class MidiIn {
public:
    ~MidiIn() { close(); }
    bool open(int device, std::function<void(const MidiMsg &)> cb, std::string &err);
    void close();
    int device = -1;
    std::function<void(const MidiMsg &)> cb;
private:
    void *h = nullptr;
};

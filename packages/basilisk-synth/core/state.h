// BASILISK SYNTH shared core: plugin state (DAW projects and preset files). Edition-independent, versioned text:
//
//   BASILISK-SYNTH 1
//   dna <canonical DNA>
//   reference 0|1
//   <key> <value>            (future keys; unknown keys are kept and written back)
//
// A preset written by the XP plugin opens in the 3.11 plugin and the other way round: the DNA is the sound.
#pragma once
#include <map>
#include <sstream>
#include <string>
#include "dna.h"

namespace bsynth {

constexpr const char *kDefaultDna = "ding#16;R120";

struct State {
    int version = 1;
    std::string dna = kDefaultDna;
    bool reference = false;
    std::map<std::string, std::string> extra;

    std::string write() const
    {
        std::ostringstream o;
        o << "BASILISK-SYNTH " << version << "\n" << "dna " << canonical(dna) << "\n" << "reference " << (reference ? 1 : 0) << "\n";
        for (auto &kv : extra) o << kv.first << " " << kv.second << "\n";
        return o.str();
    }
    // Accepts the text above; a bare DNA line is accepted too (a preset can be just a DNA string).
    bool read(const std::string &text)
    {
        std::istringstream in(text);
        std::string line;
        if (!std::getline(in, line)) return false;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.rfind("BASILISK-SYNTH ", 0) != 0) {
            if (line.empty()) return false;
            dna = canonical(line); reference = false; extra.clear();
            return true;
        }
        State s;
        s.version = std::atoi(line.c_str() + 15);
        while (std::getline(in, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            auto sp = line.find(' ');
            std::string k = line.substr(0, sp), v = sp == std::string::npos ? "" : line.substr(sp + 1);
            if (k == "dna") s.dna = canonical(v);
            else if (k == "reference") s.reference = v == "1";
            else if (!k.empty()) s.extra[k] = v;
        }
        *this = s;
        return true;
    }
};

}  // namespace bsynth

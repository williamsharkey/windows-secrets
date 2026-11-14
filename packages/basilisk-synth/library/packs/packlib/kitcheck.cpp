// Build: g++ -std=c++17 -O1 -I../../../core kitcheck.cpp ../../../core/{dna3,engine3,scales,dna}.cpp -o ~/packwork/kitcheck/kitcheck
// (make_packs.py finds it through KITCHECK, default ~/packwork/kitcheck/kitcheck)
// kitcheck: reads DNAs (one per line) and prints pads, kit?, canonical-equal, layers for each.
#include "dna3.h"
#include <iostream>
#include <string>
int main() {
    std::string s;
    while (std::getline(std::cin, s)) {
        if (s.empty()) continue;
        bsynth3::Dna3 d = bsynth3::parse3(s);
        std::string c = bsynth3::canonical3(s);
        std::cout << d.g.pads.size() << '\t' << (d.g.kit() ? 1 : 0) << '\t' << (c == s ? 1 : 0) << '\t' << d.layers.size() << '\t' << c << '\n';
    }
}

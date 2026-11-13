// recipe_cli: DNA -> recipe for sndrec.html, with the tested converter (packages/basilisk-synth/design/v3/recipe.{h,cpp},
// PRESET-ENGINE-2.md section 17, branch design/preset-engine-2). One DNA per stdin line; per DNA one JSON line out:
//   {"dna": ..., "lines": [multi-line form, one string per line], "one": one-line form, "ok": round-trips}
// "ok" checks fromRecipe(toRecipe(dna)) for both forms against the one-line form's own parse, as the branch's tests do.
//   g++ -std=c++17 -O2 -I<core> -I<v3> recipe_cli.cpp <v3>/{recipe,dna3,engine3}.cpp <core>/dna.cpp -o recipe_cli
//   recipe_cli [library.names.txt] < dnas.txt
#include "recipe.h"
#include "dna.h"
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static std::string js(const std::string &s)
{
    std::string o = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += (char)c; }
        else if (c == '\n') o += "\\n";
        else if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += (char)c;
    }
    return o + "\"";
}

int main(int argc, char **argv)
{
    if (argc > 1) {
        std::ifstream in(argv[1]); std::vector<std::string> names; std::string l;
        while (std::getline(in, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
        bsynth::setLibrary(names);
    }
    std::string dna;
    while (std::getline(std::cin, dna)) {
        if (dna.empty()) continue;
        const std::string lines = bsynth3::toRecipe(dna, bsynth3::RecipeForm::Lines);
        const std::string one = bsynth3::toRecipe(dna, bsynth3::RecipeForm::OneLine);
        std::string a, b;
        const bool ok = bsynth3::fromRecipe(lines, a) && bsynth3::fromRecipe(one, b) && a == b;
        std::cout << "{\"dna\":" << js(dna) << ",\"lines\":[";
        size_t p = 0; bool first = true;
        while (p <= lines.size()) {
            size_t q = lines.find('\n', p); if (q == std::string::npos) q = lines.size();
            if (q > p) { std::cout << (first ? "" : ",") << js(lines.substr(p, q - p)); first = false; }
            p = q + 1;
        }
        std::cout << "],\"one\":" << js(one) << ",\"canonical\":" << js(b) << ",\"ok\":" << (ok ? "true" : "false") << "}\n";
    }
    return 0;
}

// canonical() is a fixed point: canonical(canonical(x)) == canonical(x), over 20,000 random mixed strings
// (v1/v2 tokens, later-version tokens, stray separators and junk).
//   g++ -std=c++17 test_canon.cpp dna.cpp -o /tmp/tcanon && /tmp/tcanon
#include "dna.h"
#include <cstdio>
#include <random>
#include <string>
using namespace bsynth;
int main()
{
    const char *names[] = {"ding", "chord", "tada", "chimes", "xpding", "kalimba_c4", "nosuch", ""};
    const char *steps[] = {"+", "-", ">", "<", "E", "R", "[", "]", "C", "P", "X", "@30", "@t250", "Ichimes", "Mding", "#4",
                           "T-12", "L80", "U3~9", "F", "H0,4,7", "O120", "Q-40", "Ja0,0.30,100", "Jp0,-50.500,50",
                           "Ws.2~.4", "Nlg80", "Sg2x", "Gf", "Vw4,6", "Z36,60,48", "/", "//", "Y", "~", ",", "."};
    const char *glob[] = {"A5", "D300", "S70", "R250", "B2", "V80", "K60", "G-3", "m1=50", "m11Z50,300", "m22Q-100,100",
                          "m11S50", "m9=5", "m15W2", "q0", "q9r4", "xd8tg60", "A", "m", ";", "Z"};
    std::mt19937 rng(20261113);
    int bad = 0;
    for (int n = 0; n < 20000; n++) {
        std::string s;
        int nl = rng() % 5;
        for (int l = 0; l < nl; l++) {
            if (l) s += '/';
            s += names[rng() % 8];
            int ns = rng() % 7;
            for (int k = 0; k < ns; k++) s += steps[rng() % (sizeof steps / sizeof *steps)];
        }
        if (rng() % 2) {
            s += ';';
            int ng = rng() % 5;
            for (int k = 0; k < ng; k++) s += glob[rng() % (sizeof glob / sizeof *glob)];
        }
        std::string a = canonical(s), b = canonical(a);
        if (a != b && bad++ < 10) std::printf("NOT FIXED: %s\n  -> %s\n  -> %s\n", s.c_str(), a.c_str(), b.c_str());
    }
    std::printf("canonical fixed point: %d of 20000 failed\n", bad);
    return bad ? 1 : 0;
}

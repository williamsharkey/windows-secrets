// DNA v2 checks: g++ -std=c++17 test_v2.cpp dna.cpp voices.cpp && ./a.out
#include "dna.h"
#include "voices.h"
#include "proto.h"
#include <cassert>
#include <iostream>
using namespace bsynth;
int main() {
    // v1 strings keep their meaning
    assert(canonical("chord#10/ding>>E#6;A2D300S70R250") == "chord#10/ding>>E#6;A2D300S70R250");
    Dna d = parse("tada@t300Mding@t900Ichimes>#4O120Q-40Ja0,0.30,100.400,60.400,60Jp0,-50.500,50/ding;m1=50m11Z50,300m12Q-100,100m10L0,200");
    std::cout << d.canonical << "\n";
    assert(d.layers[0].offset == 120 && d.layers[0].pan == -40 && d.layers[0].envA.size() == 3 && d.layers[0].envP.size() == 2);
    assert(d.layers[0].steps.size() == 5 && d.layers[0].steps[0].ms == 300 && d.layers[0].steps[1].name == "ding");
    assert(d.g.macro[0] == 50 && d.g.maps.size() == 3);
    Dna m = applyMacros(d);
    std::cout << "scaled env " << envText(m.layers[0].envA) << " pan1 " << m.layers[1].pan << " level0 " << m.layers[0].level << "\n";
    assert(m.layers[1].pan == 0 && m.layers[0].level == 100 && m.layers[1].level == 100);
    assert(m.layers[0].envA[1].first == (int)(30 * 1.75 + 0.5));
    // library names
    setLibrary({"dog_bark"});
    Dna l = parse("dog_bark>/ding Mdog_bark");
    assert(l.layers[0].valid() && l.layers[0].lib && l.layers[1].steps.size() == 1);
    // N: repeat count of the last step
    Dna n = applyMacros(parse("ding>E;m1=100m11N0,3"));
    std::cout << n.layersText() << "\n";
    assert(n.layersText() == "ding>EEE");
    // voices carry pan/offset/layer
    Voices v(48000); Cmd c[kMaxCmds];
    v.setDna(m, c); v.setLayerInfo(0, 0, 4, 22050, 22050); v.setLayerInfo(1, 4, 12, 22050, 22050);
    int k = v.noteOn(60, 100, 0, c);
    char b[96]; proto::cmd(b, sizeof b, c[0]); std::cout << b;
    assert(c[0].delayMs == 120 && c[0].pan == -40 && c[0].layer == 0);
    std::cout << setLayerEnv("ding", 0, 'a', {{0,0},{20,100}}) << " " << setMacro("ding", 2, 70) << "\n";
    std::cout << "ok " << k << "\n";
}

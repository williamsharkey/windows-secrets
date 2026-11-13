// g++ -std=c++17 -O1 test_core.cpp dna.cpp voices.cpp -o test_core && ./test_core
#include <cassert>
#include <cstdio>
#include "dna.h"
#include "voices.h"
#include "proto.h"
#include "state.h"
using namespace bsynth;
int main()
{
    Dna d = parse("ding>E/tada<<R+#4H0,12U2~9;A5R350");
    std::printf("%s | layers %zu\n", d.canonical.c_str(), d.layers.size());
    assert(d.canonical == "ding>E/tada<<R+#4H0,12U2~9;A5R350");
    assert(d.layers[0].count == 12 && d.layers[1].count == 4 && d.layers[1].first == 12);
    assert(d.layers[1].harmony.size() == 2 && d.layers[1].unison == 2 && d.layers[1].spreadCents == 9);
    assert(d.g.attack == 5 && d.g.release == 350);
    assert(canonical("ding ?+T+3") == "ding+T3");
    assert(canonical("nope+/ding") == "nope+/ding");
    Dna e = parse("nope+/ding");
    assert(e.layers[0].count == 0 && e.layers[1].count == 16);
    assert(canonical("ding@150T99") == "ding@99T48");
    assert(parse("ding#16/chimes").layers[1].count == 0 || parse("ding#16/chimes").layers[1].count == 1);
    Dna f = parse("ding#16/chimes");
    std::printf("pools %d %d\n", f.layers[0].count, f.layers[1].count);
    Dna f2 = parse("ding/chord#16");
    assert(f2.layers[0].count == 1 && f2.layers[0].first == 0 && f2.layers[1].count == 15 && f2.layers[1].first == 1);
    assert(f.layers[0].count == 15 && f.layers[1].count == 1);
    Dna g = parse("a/b/c/ding/chimes/ringin");
    std::printf("unk pools %d %d %d\n", g.layers[3].count, g.layers[4].count, g.layers[5].count);
    assert(g.layers[3].count == 6 && g.layers[4].count == 5 && g.layers[5].count == 5);
    assert(setGlobal("ding;A5", 'R', 400) == "ding;A5R400");
    assert(setGlobal("ding;A5R1", 'A', 7) == "ding;A7R1");
    assert(setLayerGene("ding", 0, 'T', -12) == "ding T-12" || setLayerGene("ding", 0, 'T', -12) == "dingT-12");
    assert(appendStep("ding", 0, 'I', 0, "chimes") == "dingIchimes");
    assert(Voices::rateFor(22050, 12, 0) == 44100);
    assert(Voices::rateFor(22050, -48, 0) == 2000);
    // allocator
    Voices v(48000); Cmd c[kMaxCmds];
    Dna h = parse("ding#2H0,12");
    v.setDna(h, c);
    v.setLayerInfo(0, 0, 2, 22050, 11554);
    int n = v.noteOn(60, 127, 0, c);
    assert(n == 2 && c[0].kind == Cmd::On && c[0].rateHz == 22050 && c[1].rateHz == 44100 && c[0].vol == 65535);
    n = v.noteOn(62, 127, 100, c);     // both busy: steals, cut before on
    std::printf("steal n=%d kinds %d %d %d %d\n", n, c[0].kind, c[1].kind, c[2].kind, c[3].kind);
    assert(n == 4 && c[0].kind == Cmd::Cut && c[1].kind == Cmd::On);
    n = v.noteOff(62, 200, c);
    assert(n == 2 && c[0].kind == Cmd::Off);
    char b[64];
    proto::on(b, 64, 3, 44100, 65535); assert(std::string(b) == "on 3 44100 65535\n");
    auto r = proto::parse("layer 1 12 4 22050 11554\r\n");
    assert(r.kind == proto::Reply::Layer && r.first == 12 && r.frames == 11554);
    State s; s.dna = "ding>"; s.extra["x"] = "1";
    State t; assert(t.read(s.write()) && t.dna == "ding>" && t.extra["x"] == "1");
    assert(t.read("chimes<<") && t.dna == "chimes<<");
    std::printf("core ok\n");
}

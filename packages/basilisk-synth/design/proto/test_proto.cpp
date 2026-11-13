// PRESET ENGINE 2 prototype tests. Uses the shared core READ-ONLY (it is compiled in, not changed).
//   g++ -std=c++17 -O1 -Wall -I../../core test_proto.cpp dna3.cpp engine3.cpp ../../core/dna.cpp -o /tmp/pe2 && /tmp/pe2
#include "dna3.h"
#include "engine3.h"
#include "dna.h"
#include <cassert>
#include <cstdio>
#include <iostream>
using namespace bsynth3;

static int fails = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

// v2's parse of a v3 string must equal v2's parse of the same string with the v3 tokens taken out
static void degrade(const std::string &v3, const std::string &v2)
{
    std::string a = bsynth::parse(v3).canonical, b = bsynth::parse(v2).canonical, s = strip3(v3);
    if (s != v2 || a != b) {
        std::printf("FAIL degrade\n  v3    %s\n  strip %s\n  want  %s\n  core(v3) %s\n  core(v2) %s\n", v3.c_str(), s.c_str(), v2.c_str(), a.c_str(), b.c_str());
        fails++;
    }
}

int main()
{
    // ---- fractions
    size_t p = 0; CHECK(readFrac(".25", p) == 2500);
    p = 0; CHECK(readFrac("0.2", p) == 2000);
    p = 0; CHECK(readFrac("1", p) == kOne);
    CHECK(fracText(2500) == ".25" && fracText(0) == "0" && fracText(kOne) == "1" && fracText(15000) == "1.5");

    // ---- the owner's example: a pad starts at a random point 0.2..0.4 and plays a random 0.1..0.3 of the length
    Dna3 d = parse3("logon<#8Ws.2~.4l.1~.3NpYd6k;A400R900");
    CHECK(d.layers.size() == 1);
    CHECK(d.layers[0].w.s.lo == 2000 && d.layers[0].w.s.hi == 4000 && d.layers[0].w.l.lo == 1000 && d.layers[0].w.l.hi == 3000);
    std::printf("tokens: %s\n", d.layers[0].tokens.empty() ? "" : d.layers[0].tokens[0].c_str());
    {
        Rng rng(7);
        uint32_t frames = 47546;   // logon.wav slowed an octave: 2.156 s * 22050 * 2 / 2 (an example length)
        for (int i = 0; i < 2000; i++) {
            Span s = window(d.layers[0].w, frames, 22050, 100, rng);
            CHECK(s.from >= frames * 2 / 10 && s.from <= frames * 4 / 10);
            uint32_t len = s.to - s.from;
            CHECK(len >= frames / 10 - 1 && len <= frames * 3 / 10 + 1);
            CHECK(s.to <= frames);
        }
    }
    // a fixed window bakes into Sound Recorder steps; a random one does not
    {
        Dna3 f = parse3("dingWs.25e.75");
        std::string b = bakeSteps(f.layers[0].w, 22050, 22050);   // 1.000 s
        std::printf("bake: %s\n", b.c_str());
        CHECK(b == "@t750]@t250[");
        CHECK(bakeSteps(d.layers[0].w, 22050, 22050).empty());
    }
    // the shortest window: 10 ms
    {
        Dna3 f = parse3("dingWs.5e.5");
        Rng rng(1);
        Span s = window(f.layers[0].w, 22050, 22050, 100, rng);
        CHECK(s.to - s.from == 220);
    }

    // ---- every v3 letter, canonical round trip
    {
        std::string t = "chord#6NlYd4l6kSs25rVw6,7f2,11s20,60Z36,60,48Gp.3j.1z60~120n40c25e2s1v4/ding;A2R300q1r9xd16g70s12k2p3a4";
        Dna3 a = parse3(t);
        std::string l0 = a.layers[0].tokens[0], g = a.g.tokens[0];
        std::printf("layer0: %s\nglobals: %s\n", l0.c_str(), g.c_str());
        CHECK(a.layers[0].n.mode == 'l' && a.layers[0].s.strumMs == 25 && a.layers[0].s.roundRobin);
        CHECK(a.layers[0].v.wowCents == 6 && a.layers[0].v.wowDeciHz == 7 && a.layers[0].v.scoopMs == 60);
        CHECK(a.layers[0].z.lo == 36 && a.layers[0].z.hi == 60 && a.layers[0].z.root == 48);
        CHECK(a.layers[0].g.on && a.layers[0].g.sizeMs == 60 && a.layers[0].g.sizeHiMs == 120 && a.layers[0].g.scan == kOne);
        CHECK(a.g.scale == 1 && a.g.rootPc == 9 && a.g.x.on && a.g.x.kind == 2 && a.g.x.swing == 12);
        Dna3 b = parse3("ding" + l0 + ";" + g);
        CHECK(b.layers[0].tokens[0] == l0 && b.g.tokens[0] == g);
        degrade(t, "chord#6/ding;A2R300");
    }

    // ---- v1/v2 parsers hear the v2 subset: hand-made cases with every v2 token next to v3 tokens
    degrade("dingWs.2~.4>E#4Ws.1", "ding>E#4");
    degrade("tada@t300MdingWl.5@t900Ichimes>#4O120Q-40Ja0,0.30,100.400,60Jp0,-50.500,50NcSgxYk/dingGf;m1=50m11Z50,300xh",
            "tada@t300Mding@t900Ichimes>#4O120Q-40Ja0,0.30,100.400,60Jp0,-50.500,50/ding;m1=50m11Z50,300");
    degrade("ringout@30[@40]#3U1~0Vw4,6/recycle>>@8]#2FWm40;A15D400S70R250V80q8",
            "ringout@30[@40]#3U1~0/recycle>>@8]#2F;A15D400S70R250V80");
    degrade("chimesH0,7,12Sr/chordU3~12Sw.8Yq30", "chimesH0,7,12/chordU3~12");

    // ---- fuzz: random v2 strings with random v3 tokens inserted at token boundaries
    {
        const char *v2tok[] = {"+", "-", ">", "<", "E", "R", "[", "]", "C", "P", "X", "@30", "@t250", "Iding", "Mchimes",
                               "#4", "T-12", "H0,4,7", "U3~9", "F", "L80", "O120", "Q-40", "Ja0,0.30,100", "Jp0,-50.500,50"};
        const char *v3tok[] = {"Ws.2~.4l.1~.3", "We.9", "Wv.5m8000", "Np4", "Nm", "Nlg80", "Ncg200kh", "Sr", "Sx", "Sp",
                               "Sg2x", "Ss30", "Sd3", "Sw.5", "Yd8l6t12q20kr", "Vw8,6", "Vf2,12s30,80", "Z0,59,48",
                               "Gp.5j.2z40~90n60c30o20e3s.5bv6w.7y", "Gf"};
        const char *v2glob[] = {"A10", "D300", "S70", "R250", "B12", "V80", "K48", "G-6", "m1=40", "m21L0,200", "m30Z50,200"};
        const char *v3glob[] = {"q0", "q9r4", "x", "xd8tg60s20k1p6a5o3l12b96fh"};
        const char *src[] = {"ding", "chord", "tada", "logon", "ringout"};
        Rng r(12345);
        for (int n = 0; n < 20000; n++) {
            std::string v3, v2;
            int layers = r.in(1, 4);
            for (int l = 0; l < layers; l++) {
                if (l) { v3 += "/"; v2 += "/"; }
                std::string s = src[r.in(0, 4)];
                v3 += s; v2 += s;
                int k = r.in(0, 8);
                for (int i = 0; i < k; i++) {
                    if (r.in(0, 2) == 0) v3 += v3tok[r.in(0, 19)];
                    else { std::string t = v2tok[r.in(0, 24)]; v3 += t; v2 += t; }
                }
            }
            if (r.in(0, 1)) {
                v3 += ";"; v2 += ";";
                int k = r.in(0, 6);
                for (int i = 0; i < k; i++) {
                    if (r.in(0, 2) == 0) v3 += v3glob[r.in(0, 3)];
                    else { std::string t = v2glob[r.in(0, 10)]; v3 += t; v2 += t; }
                }
            }
            int before = fails;
            degrade(v3, v2);
            if (fails > before + 3) break;
        }
        std::printf("fuzz: 20000 mixed DNAs checked\n");
    }

    // ---- mono / legato / continue
    {
        VoiceMode m; m.mode = 'c'; m.glideMs = 50;
        MonoPlan c(m);
        auto a = c.keyDown(60, 0, 1e9);
        CHECK(a.size() == 1 && a[0].kind == Action::On && a[0].note == 60);
        a = c.keyUp(60, 100, 1e9);
        CHECK(a.size() == 1 && a[0].kind == Action::Off);
        a = c.keyDown(64, 300, 1e9);   // released but still sounding: continue at the new pitch, hold it again
        CHECK(a.size() == 1 && a[0].kind == Action::Rate && a[0].note == 64 && a[0].regate && a[0].glideMs == 50);
        a = c.keyUp(64, 400, 1e9);
        a = c.keyDown(67, 5000, 1000);  // the buffer ran out: a new note from the window start
        CHECK(a.size() == 1 && a[0].kind == Action::On);

        VoiceMode lm; lm.mode = 'l'; lm.glideMs = 80;
        MonoPlan l(lm);
        l.keyDown(60, 0, 1e9);
        a = l.keyDown(62, 10, 1e9);      // overlapped: glide
        CHECK(a.size() == 1 && a[0].kind == Action::Rate && a[0].note == 62 && !a[0].regate);
        a = l.keyUp(62, 20, 1e9);        // back to the note still held
        CHECK(a.size() == 1 && a[0].kind == Action::Rate && a[0].note == 60);
        a = l.keyUp(60, 30, 1e9);
        a = l.keyDown(65, 40, 1e9);      // not overlapped: a new attack
        CHECK(a.size() == 2 && a[0].kind == Action::Cut && a[1].kind == Action::On);

        VoiceMode mm; mm.mode = 'm';
        MonoPlan mo(mm);
        mo.keyDown(60, 0, 1e9);
        a = mo.keyDown(62, 10, 1e9);
        CHECK(a.size() == 2 && a[0].kind == Action::Cut && a[1].kind == Action::On && a[1].note == 62);

        VoiceMode hm; hm.mode = 'l'; hm.prio = 'h';
        MonoPlan hi(hm);
        hi.keyDown(70, 0, 1e9);
        a = hi.keyDown(60, 10, 1e9);     // high-note priority keeps 70
        CHECK(a.empty() && hi.sounding() == 70);
    }

    // ---- the mine grid: a 9 x 9 board as the guest would report it
    {
        Grid g;
        std::string cells =
            "........."
            "....1...."
            "..2.11..."
            ".F...?..."
            "1....2..."
            "..3..?..."
            ".....?..."
            "11.....*."
            "01x....1.";
        CHECK(g.parse("grid 9 9 l " + cells));
        CHECK(!g.parse("grid 9 9 p 123"));
        Seq x; x.kind = 0; x.octaves = 2;
        // column 0, field mode, C minor (q1), no notes held, K = 60: rows 1 and 4 hold '1' -> degrees 1 and 4
        auto s0 = stepNotes(g, 0, x, 1, -1, {}, 60);
        CHECK(s0.size() == 2 && s0[0].note == 62 && s0[1].note == 67);
        // column 2 has a wrong flag ('x'): a rest
        CHECK(stepNotes(g, 2, x, 1, -1, {}, 60).empty());
        // column 5: '2' at row 4 tied by '?' at column 6? no: the ties are in column 5 itself, below; a note at
        // row 4 of column 5 ('2'), and column 7 has a shown mine: octave up for that column
        auto s5 = stepNotes(g, 5, x, 1, -1, {}, 60);
        CHECK(s5.size() == 2);
        auto s7 = stepNotes(g, 7, x, 1, -1, {}, 60);
        CHECK(s7.size() == 1 && s7[0].note == 60 + 12);
        // arp mode: the number picks the held note
        Seq ax; ax.kind = 2; ax.octaves = 1;
        auto a0 = stepNotes(g, 0, ax, 1, -1, {48, 55, 63}, 60);
        CHECK(a0.size() == 1 && a0[0].note == 48);
        auto a2 = stepNotes(g, 4, ax, 1, -1, {48, 55, 63}, 60);   // column 4: '1' at row 7 ('1' in "....1....")
        CHECK(a2.size() == 1);
        // tie: column 4 row 5 ("..2.11...", col 4 = '1') and column 5 row 5 = '1': no tie. Row 5 col 1 is 'F' in
        // "..." -- use a direct case instead:
        Grid t;
        CHECK(t.parse("grid 9 9 p ........."
                      "........."
                      "........."
                      "........."
                      "........."
                      "........."
                      "........."
                      "........."
                      "3??F....."));
        auto tn = stepNotes(t, 0, x, 0, -1, {}, 60);
        CHECK(tn.size() == 1 && tn[0].lengthSteps == 3 && tn[0].vel == 73);
        auto fn = stepNotes(t, 3, x, 0, -1, {}, 60);
        CHECK(fn.size() == 1 && fn[0].vel == 127);
    }

    std::printf(fails ? "FAILED %d\n" : "ok\n", fails);
    return fails ? 1 : 0;
}

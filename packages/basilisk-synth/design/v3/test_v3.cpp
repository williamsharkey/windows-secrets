// DNA v3 tests. They use a core/dna.cpp READ-ONLY (compiled in, not changed). Build and run with test_v3.sh:
// it runs them against this branch's core (v2 without DNA.md 5.7) and against the main checkout's core (with 5.7,
// "unknown tokens are kept"), defining CORE_KEEPS for the second.
#include "dna3.h"
#include "engine3.h"
#include "dna.h"
#include <cstdio>
#include <map>
using namespace bsynth3;

static int fails = 0, checks = 0;
#define CHECK(c) do { checks++; if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)
#ifndef CORE_KEEPS
#define CORE_KEEPS 0
#endif

// The v2 meaning of a v3 string equals the v2 meaning of its v2 subset, with this core:
//   core(v3) and core(v2) agree once v3 tokens are taken out of core(v3)'s canonical form;
//   with a 5.7 core, the v3 part also survives a v2 save (the v3 canonical form is unchanged).
static void degrade(const std::string &v3, const std::string &v2)
{
    std::string c3 = bsynth::parse(v3).canonical, c2 = bsynth::parse(v2).canonical, s = strip3(v3);
    bool ok = s == v2 && bsynth::canonical(strip3(c3)) == c2;
    if (CORE_KEEPS) ok = ok && canonical3(c3) == canonical3(v3);    // a v2 save keeps every v3 token
    else ok = ok && c3 == c2;                                        // an old v2 save drops them (the known loss)
    // and v3 itself: canonical form idempotent, same v2 part, same v3 tokens
    std::string k = canonical3(v3);
    ok = ok && canonical3(k) == k && bsynth::canonical(strip3(k)) == c2;
    if (!ok) {
        std::printf("FAIL degrade\n  v3    %s\n  strip %s\n  want  %s\n  core(v3) %s\n  core(v2) %s\n  canon3 %s\n  canon3(core(v3)) %s\n",
                    v3.c_str(), s.c_str(), v2.c_str(), c3.c_str(), c2.c_str(), k.c_str(), canonical3(c3).c_str());
        fails++;
    }
    checks++;
}

int main()
{
    // ---- fractions
    size_t p = 0; CHECK(readFrac(".25", p) == 2500);
    p = 0; CHECK(readFrac("0.2", p) == 2000);
    p = 0; CHECK(readFrac("1", p) == kOne);
    CHECK(fracText(2500) == ".25" && fracText(0) == "0" && fracText(kOne) == "1" && fracText(15000) == "1.5");

    // ---- scales
    CHECK(degreeToSemis(0, 7) == 12 && degreeToSemis(0, -1) == -1 && degreeToSemis(12, 13) == 13 && degreeToSemis(9, 5) == 12);

    // ---- the owner's example: a pad starts at a random point 0.2..0.4 and plays a random 0.1..0.3 of the length
    Dna3 d = parse3("logon<#8Ws.2~.4l.1~.3NpYd6k;A400R900");
    CHECK(d.layers.size() == 1);
    CHECK(d.layers[0].w.s.lo == 2000 && d.layers[0].w.s.hi == 4000 && d.layers[0].w.l.lo == 1000 && d.layers[0].w.l.hi == 3000);
    CHECK(d.layers[0].tokens() == "Ws.2~.4l.1~.3NpYd6k");
    CHECK(canonical3("logon<#8Ws.2~.4l.1~.3NpYd6k;A400R900") == "logon<#8Ws.2~.4l.1~.3NpYd6k;A400R900");
    {
        Rng rng(7);
        uint32_t frames = 47546;
        for (int i = 0; i < 2000; i++) {
            Span s = window(d.layers[0].w, frames, 22050, 100, rng);
            CHECK(s.from >= frames * 2 / 10 && s.from <= frames * 4 / 10);
            uint32_t len = s.to - s.from;
            CHECK(len >= frames / 10 - 1 && len <= frames * 3 / 10 + 1);
            CHECK(s.to <= frames);
        }
    }
    // velocity moves the start toward 0
    {
        Dna3 v = parse3("dingWs.4v1");
        Rng rng(1);
        CHECK(window(v.layers[0].w, 10000, 22050, 0, rng).from == 4000);
        CHECK(window(v.layers[0].w, 10000, 22050, 127, rng).from == 0);
    }
    // a fixed window bakes into Sound Recorder steps; a random one does not
    {
        Dna3 f = parse3("dingWs.25e.75");
        CHECK(bakeSteps(f.layers[0].w, 22050, 22050) == "@t750]@t250[");
        CHECK(bakeSteps(d.layers[0].w, 22050, 22050).empty());
        CHECK(bakeSteps(parse3("dingWs.25").layers[0].w, 22050, 22050) == "@t250[");
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
        std::string t = "chord#6NlYd4l6kSs25rVw6,7f2,11s20,60Z36,60,48Gp.3j.1z60~120n40c25e2s1v4/ding;A2R300q1r9xd16g70s12n2p3a4";
        Dna3 a = parse3(t);
        std::string l0 = a.layers[0].tokens(), g = a.g.tokens();
        CHECK(l0 == "NlSrs25Yd4l6kVw6,7f2,11s20,60Z36,60,48Gp.3j.1z60~120n40c25s1");
        CHECK(g == "q1r9xg70s12n2p3a4");
        CHECK(a.layers[0].n.mode == 'l' && a.layers[0].s.strumMs == 25 && a.layers[0].s.roundRobin);
        CHECK(a.layers[0].v.wowCents == 6 && a.layers[0].v.wowDeciHz == 7 && a.layers[0].v.scoopMs == 60);
        CHECK(a.layers[0].z.lo == 36 && a.layers[0].z.hi == 60 && a.layers[0].z.root == 48);
        CHECK(a.layers[0].grains() && a.layers[0].g.sizeMs == 60 && a.layers[0].g.sizeHiMs == 120 && a.layers[0].g.scan == kOne);
        CHECK(a.g.scale == 1 && a.g.rootPc == 9 && a.g.x.on && a.g.x.kind == 2 && a.g.x.swing == 12);
        Dna3 b = parse3("ding" + l0 + ";" + g);
        CHECK(b.layers[0].tokens() == l0 && b.g.tokens() == g);
        degrade(t, "chord#6/ding;A2R300");
        CHECK(canonical3(t) == "chord#6" + l0 + "/ding;A2R300" + g);
    }
    // the last value of a subkey wins; one token per letter in canonical order
    CHECK(canonical3("dingYd3Ws.1Yd9Ws.2") == "dingWs.2Yd9");
    CHECK(canonical3("dingG") == "dingG" && parse3("dingG").layers[0].grains());
    CHECK(parse3("dingNlkh").layers[0].n.prio == 'h' && parse3("dingSg2x").layers[0].s.groupRandom && parse3("dingSxg2").layers[0].s.randomPick);
    CHECK(parse3(";xd8t").g.x.triplet && parse3(";xd8t").g.x.div == 8);

    // ---- forward compatibility (DNA.md 5.7, PRESET-ENGINE-2 2.1 rule 4): v4 parts survive a v3 save
    CHECK(canonical3("dingWs.2q9e.8") == "dingWs.2e.8q9");                 // an unknown subkey stays in its token
    CHECK(canonical3("ding;xg50z3") == "ding;xg50z3");
    CHECK(canonical3("ding;q2r4u7") == "ding;q2r4u7");
    CHECK(strip3("dingDl3Ws.5") == "dingDl3");                            // a v4 layer token is not v3: left to core
    if (CORE_KEEPS) {
        CHECK(canonical3("dingDl3Ws.5") == "dingDl3Ws.5");                // ... and core keeps it
        CHECK(canonical3("ding;A5E7q1") == "ding;A5E7q1");                 // a v4 global token, then q
    }
    // a v2 macro right after a v3 global token is not read as part of it (the 'm' boundary)
    {
        Dna3 g = parse3("ding;q0m21L0,200x");
        CHECK(g.g.scale == 0 && g.g.qExtra.empty() && g.g.x.on);
        CHECK(bsynth::parse(strip3("ding;q0m21L0,200x")).g.maps.size() == 1);
    }

    // ---- v3 macro parameters
    {
        std::string t = "ding/chordGp.1;m11W200,400m12P100,900m22P0,100m1=50m2=100";
        Dna3 a = parse3(t);
        CHECK(a.g.maps.size() == 3 && a.g.maps[0].param == 'W' && a.g.maps[0].layer == 1 && a.g.maps[0].hi == 400);
        CHECK(strip3(t) == "ding/chord;m1=50m2=100");
        bsynth::Dna v2 = bsynth::parse(t);
        CHECK(v2.g.macro[0] == 50 && v2.g.sustain == 100);                // the v3 maps never touch v2 globals
        Dna3 e = applyMacros3(a, v2.g.macro);
        CHECK(e.layers[0].w.s.lo == 3000);                                // 200..400 at 50 % = 300/1000
        CHECK(e.layers[1].g.pos == 5000 + 1000);                          // 100..900 at 50 % = 500, + (100 - 0) at 100 %
        CHECK(canonical3(t) == "ding/chordGp.1;m1=50m2=100m11W200,400m12P100,900m22P0,100");
        // on a v2 machine a v3 macro is never read as a global (core 5.7; the old core misreads some letters)
        if (CORE_KEEPS) CHECK(bsynth::parse("ding;m11S50").g.sustain == 100);
    }

    // ---- v1/v2 parsers hear the v2 subset: hand-made cases with every v2 token next to v3 tokens
    degrade("dingWs.2~.4>E#4Ws.1", "ding>E#4");
    degrade("tada@t300MdingWl.5@t900Ichimes>#4O120Q-40Ja0,0.30,100.400,60Jp0,-50.500,50NcSgxYk/dingGf;m1=50m11Z50,300xh",
            "tada@t300Mding@t900Ichimes>#4O120Q-40Ja0,0.30,100.400,60Jp0,-50.500,50/ding;m1=50m11Z50,300");
    degrade("ringout@30[@40]#3U1~0Vw4,6/recycle>>@8]#2FWm40;A15D400S70R250V80q8",
            "ringout@30[@40]#3U1~0/recycle>>@8]#2F;A15D400S70R250V80");
    degrade("chimesH0,7,12Sr/chordU3~12Sw.8Yq30", "chimesH0,7,12/chordU3~12");
    degrade("ding;A5m11W200,400R300", "ding;A5R300");

    // ---- v1 and v2 strings: v3 changes nothing (canonical3 == core canonical, no v3 tokens found)
    {
        const char *v12[] = {"ding>E/tada<<R+#4H0,12U2~9;A5R350", "chord#8/ding>E#8O120Q40;m1=0m11Z50,300m12Q-100,100",
                             "tada@t300Mding@t900Ichimes>", "logoff@30[<<E#12U3~10Ja0,0.900,100.4000,85Jp0,-60.6000,60;R3500K39",
                             "", ";A5", "ding//chord", "dingT-12L400F#16;B12V0K48G-6"};
        for (auto s : v12) {
            CHECK(canonical3(s) == bsynth::canonical(s));
            Dna3 x = parse3(s);
            bool none = x.g.tokens().empty();
            for (auto &L : x.layers) none = none && L.tokens().empty();
            CHECK(none);
        }
    }

    // ---- fuzz: random v2 strings with random v3 tokens inserted at token boundaries; plus pure v2 strings
    {
        const char *v2tok[] = {"+", "-", ">", "<", "E", "R", "[", "]", "C", "P", "X", "@30", "@t250", "Iding", "Mchimes",
                               "#4", "T-12", "H0,4,7", "U3~9", "F", "L80", "O120", "Q-40", "Ja0,0.30,100", "Jp0,-50.500,50"};
        const char *v3tok[] = {"Ws.2~.4l.1~.3", "We.9", "Wv.5m8000", "Np4", "Nm", "Nlg80", "Ncg200kh", "Sr", "Sx", "Sp",
                               "Sg2x", "Ss30", "Sd3", "Sw.5", "Yd8l6t12q20kr", "Vw8,6", "Vf2,12s30,80", "Z0,59,48",
                               "Gp.5j.2z40~90n60c30o20e3s.5bv6w.7y", "Gf", "Ws.1u5", "G", "Z40,70"};
        const char *v2glob[] = {"A10", "D300", "S70", "R250", "B12", "V80", "K48", "G-6", "m1=40", "m21L0,200", "m30Z50,200"};
        const char *v3glob[] = {"q0", "q9r4", "x", "xd8tg60s20n1p6a5o3l12b96fh", "k36", "k42l3j2e.5c1f15", "k46l3j2s.5c1", "k60,72l2p100w5t20h40y1,90g", "kd", "k38u1,2z", "m11W200,400", "m40J10,300", "xz2"};
        const char *src[] = {"ding", "chord", "tada", "logon", "ringout"};
        const int N3 = sizeof v3tok / sizeof *v3tok, NG3 = sizeof v3glob / sizeof *v3glob;
        Rng r(12345);
        int pure = 0;
        for (int n = 0; n < 20000; n++) {
            std::string v3, v2;
            bool only2 = r.in(0, 9) == 0;
            int layers = r.in(1, 4);
            for (int l = 0; l < layers; l++) {
                if (l) { v3 += "/"; v2 += "/"; }
                std::string s = src[r.in(0, 4)];
                v3 += s; v2 += s;
                int k = r.in(0, 8);
                for (int i = 0; i < k; i++) {
                    if (!only2 && r.in(0, 2) == 0) v3 += v3tok[r.in(0, N3 - 1)];
                    else { std::string t = v2tok[r.in(0, 24)]; v3 += t; v2 += t; }
                }
            }
            if (r.in(0, 1)) {
                v3 += ";"; v2 += ";";
                int k = r.in(0, 6);
                for (int i = 0; i < k; i++) {
                    if (!only2 && r.in(0, 2) == 0) v3 += v3glob[r.in(0, NG3 - 1)];
                    else { std::string t = v2glob[r.in(0, 10)]; v3 += t; v2 += t; }
                }
            }
            if (v3 == v2) {   // a pure v1/v2 string: v3 must not change a thing
                pure++;
                CHECK(canonical3(v2) == bsynth::canonical(v2) && strip3(v2) == v2);
            }
            int before = fails;
            degrade(v3, v2);
            if (fails > before + 3) break;
        }
        std::printf("fuzz: 20000 mixed DNAs checked (%d pure v1/v2), core keeps unknown tokens: %s\n", pure, CORE_KEEPS ? "yes" : "no");
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
        a = c.keyDown(67, 350, 1e9);   // overlapped: continue, no regate
        CHECK(a.size() == 1 && a[0].kind == Action::Rate && a[0].note == 67 && !a[0].regate);
        a = c.keyUp(67, 360, 1e9);     // back to 64, still held
        CHECK(a.size() == 1 && a[0].kind == Action::Rate && a[0].note == 64);
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
        CHECK(a.size() == 1 && a[0].kind == Action::Off);
        a = l.keyDown(65, 40, 1e9);      // not overlapped: a new attack
        CHECK(a.size() == 2 && a[0].kind == Action::Cut && a[1].kind == Action::On);

        VoiceMode mm; mm.mode = 'm';
        MonoPlan mo(mm);
        mo.keyDown(60, 0, 1e9);
        a = mo.keyDown(62, 10, 1e9);
        CHECK(a.size() == 2 && a[0].kind == Action::Cut && a[1].kind == Action::On && a[1].note == 62);
        a = mo.keyUp(62, 20, 1e9);       // mono: back to 60 with a new attack
        CHECK(a.size() == 2 && a[0].kind == Action::Cut && a[1].kind == Action::On && a[1].note == 60);
        a = mo.keyDown(60, 30, 1e9);     // a repeated note-on of a held key: one held entry, a re-attack
        a = mo.keyUp(60, 40, 1e9);
        CHECK(a.size() == 1 && a[0].kind == Action::Off);

        VoiceMode pm; pm.mode = 'm'; pm.glideMs = 60;     // mono with portamento: start at the old pitch, slide
        MonoPlan po(pm);
        po.keyDown(60, 0, 1e9);
        a = po.keyDown(67, 10, 1e9);
        CHECK(a.size() == 3 && a[0].kind == Action::Cut && a[1].kind == Action::On && a[1].note == 60 && a[2].kind == Action::Rate && a[2].note == 67);
        a = po.keyUp(67, 20, 1e9);       // and back, the same way
        CHECK(a.size() == 3 && a[1].note == 67 && a[2].note == 60);

        VoiceMode hm; hm.mode = 'l'; hm.prio = 'h';
        MonoPlan hi(hm);
        hi.keyDown(70, 0, 1e9);
        a = hi.keyDown(60, 10, 1e9);     // high-note priority keeps 70
        CHECK(a.empty() && hi.sounding() == 70);
        a = hi.keyUp(60, 20, 1e9);       // releasing the unheard note changes nothing
        CHECK(a.empty() && hi.sounding() == 70);
        a = hi.keyDown(72, 30, 1e9);     // a higher note takes over, legato
        CHECK(a.size() == 1 && a[0].kind == Action::Rate && a[0].note == 72);
    }

    // ---- stacking, groups, humanize, seeds
    {
        Stack rr; rr.roundRobin = true;
        Rng rng(3);
        std::vector<int> H{0, 12, 7};
        CHECK(noteIntervals(rr, H, 0, rng, 0, -1, 60) == std::vector<int>{0});
        CHECK(noteIntervals(rr, H, 1, rng, 0, -1, 60) == std::vector<int>{12});
        CHECK(noteIntervals(rr, H, 5, rng, 0, -1, 60) == std::vector<int>{7});
        Stack rx; rx.randomPick = true;
        for (int i = 0; i < 50; i++) { auto v = noteIntervals(rx, H, i, rng, 0, -1, 60); CHECK(v.size() == 1 && (v[0] == 0 || v[0] == 12 || v[0] == 7)); }
        Stack dia; dia.diatonic = 3;
        CHECK(noteIntervals(dia, H, 0, rng, 0, 0, 60) == (std::vector<int>{0, 4, 7}));     // C in C major: C E G
        CHECK(noteIntervals(dia, H, 0, rng, 0, 0, 62) == (std::vector<int>{0, 3, 7}));     // D: D F A
        CHECK(noteIntervals(dia, H, 0, rng, 0, 0, 71) == (std::vector<int>{0, 3, 6}));     // B: B D F
        dia.diatonic = 4;
        CHECK(noteIntervals(dia, H, 0, rng, 1, 9, 69) == (std::vector<int>{0, 3, 7, 10})); // A minor: Am7
        CHECK(noteIntervals(Stack(), H, 0, rng, 0, -1, 60) == H);
        Stack sw; sw.width = 6000;
        CHECK(unisonPan(sw, 0, 3) == -60 && unisonPan(sw, 1, 3) == 0 && unisonPan(sw, 2, 3) == 60 && unisonPan(sw, 0, 1) == 0);
        Stack st; st.strumMs = 30;
        CHECK(strumDelayMs(st, 2) == 60);
        CHECK(groupPick({1, 3}, false, 0, rng) == 1 && groupPick({1, 3}, false, 1, rng) == 3 && groupPick({}, false, 0, rng) == -1);
        Human y; y.detune = 6; y.level = 10; y.timeMs = 12; y.pan = 30;
        for (int i = 0; i < 200; i++) {
            HumanDraw h = humanize(y, rng);
            CHECK(h.cents >= -6 && h.cents <= 6 && h.levelPct >= 90 && h.levelPct <= 100 && h.lateMs >= 0 && h.lateMs <= 12 && h.pan >= -30 && h.pan <= 30);
        }
        Human k; k.perKey = true;
        CHECK(voiceSeed(k, 60, 1, 1, 9) == voiceSeed(k, 60, 5, 77, 9) && voiceSeed(k, 60, 1, 1, 9) != voiceSeed(k, 61, 1, 1, 9));
        Human n0;
        CHECK(voiceSeed(n0, 60, 1, 1, 9) != voiceSeed(n0, 60, 1, 2, 9));
    }

    // ---- zones and rate modulation
    {
        Dna3 z = parse3("aZ0,54,48/bZ55,127");
        CHECK(inZone(z.layers[0].z, 54) && !inZone(z.layers[0].z, 55) && inZone(z.layers[1].z, 55));
        CHECK(zoneRoot(z.layers[0].z, 60) == 48 && zoneRoot(z.layers[1].z, 60) == 60);
        Mod m; m.scoopCents = 20; m.scoopMs = 80;
        CHECK(modCents(m, 0, 0) == -20 && modCents(m, 40, 0) == -10 && modCents(m, 80, 0) == 0);
        Mod w; w.wowCents = 6; w.wowDeciHz = 6;
        double mx = 0;
        for (int t = 0; t < 3000; t += 5) mx = std::max(mx, std::abs(modCents(w, t, 0.1)));
        CHECK(mx > 5.9 && mx <= 6.0);
        auto st = xpStaircase(w, 5000, 0, 40, 2);
        CHECK(!st.empty() && st.size() < 125);                 // at most one swap per 40 ms
        for (size_t i = 1; i < st.size(); i++) CHECK(st[i].tMs - st[i - 1].tMs >= 40 && std::abs(st[i].cents) <= 6 && st[i].cents % 2 == 0);
        std::printf("wow 6 c / 0.6 Hz as XP swaps: %zu swaps in 5 s\n", st.size());
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
        CHECK(!g.parse("grid 9 9 p " + std::string(81, '#')));
        Seq x; x.kind = 0; x.octaves = 2;
        auto s0 = stepNotes(g, 0, x, 1, -1, {}, 60);           // C minor, no notes held, K = 60
        CHECK(s0.size() == 2 && s0[0].note == 62 && s0[1].note == 67);
        CHECK(stepNotes(g, 2, x, 1, -1, {}, 60).empty());       // a wrong flag: a rest
        auto s5 = stepNotes(g, 5, x, 1, -1, {}, 60);
        CHECK(s5.size() == 2);
        auto s7 = stepNotes(g, 7, x, 1, -1, {}, 60);            // a shown mine: the column plays an octave up
        CHECK(s7.size() == 1 && s7[0].note == 60 + 12);
        Seq ax; ax.kind = 2; ax.octaves = 1;
        auto a0 = stepNotes(g, 0, ax, 1, -1, {48, 55, 63}, 60);
        CHECK(a0.size() == 1 && a0[0].note == 48);
        Grid t;
        CHECK(t.parse("grid 9 9 p " + std::string(72, '.') + "3??F....."));
        auto tn = stepNotes(t, 0, x, 0, -1, {}, 60);
        CHECK(tn.size() == 1 && tn[0].lengthSteps == 3 && tn[0].vel == 73);
        auto fn = stepNotes(t, 3, x, 0, -1, {}, 60);
        CHECK(fn.size() == 1 && fn[0].vel == 127);
        // poly limit: accents first
        Grid many;
        CHECK(many.parse("grid 9 9 p " + std::string("F........1........2........F........8........3........4........5........6........")));
        Seq p2; p2.poly = 2;
        auto pn = stepNotes(many, 0, p2, 0, -1, {}, 60);
        CHECK(pn.size() == 2 && pn[0].vel == 127 && pn[1].vel == 127);
        // swing
        Seq sw; sw.div = 16; sw.swing = 50;
        CHECK(stepPpq(sw, 0) == 0 && stepPpq(sw, 1) == 0.25 + 0.125 && stepPpq(sw, 2) == 0.5);
    }

    // ---- kit mode (section 15)
    {
        std::string t = "kick#2/snare#4/hats@t30000Iclosedhat@t30000Iopenhat#6/tom#4;A0R300V90"
                        "k36k38l2y1,90k38l2y91,127i120k42l3j1e.9c1k44l3j2c1f20k46l3j3c1k47,53l4p100w3r50b15h70";
        Dna3 a = parse3(t);
        CHECK(a.g.kit() && a.g.pads.size() == 7);
        CHECK(a.g.pads[2].velLo == 91 && a.g.pads[2].level == 120);
        std::printf("kit canonical: %s\n", canonical3(t).c_str());
        CHECK(canonical3(canonical3(t)) == canonical3(t));
        degrade(t, "kick#2/snare#4/hats@t30000Iclosedhat@t30000Iopenhat#6/tom#4;A0R300V90");
        Rng rng(5);
        CHECK(pickPad(a.g.pads, 36, 100, 0, rng) == 0 && pickPad(a.g.pads, 37, 100, 0, rng) == -1);
        CHECK(pickPad(a.g.pads, 38, 60, 0, rng) == 1 && pickPad(a.g.pads, 38, 120, 0, rng) == 2);   // velocity layers
        CHECK(chokeTargets(a.g.pads, 4) == (std::vector<int>{3, 4, 5}));   // pedal hat chokes the hats, itself too
        Pad tom = a.g.pads[6];
        CHECK(padCents(tom, 50) == -15 && padCents(tom, 53) == 300 - 15 && padCents(tom, 47) == -300 - 15);   // range +-3
        CHECK(tom.pan == -30 && padCents(a.g.pads[0], 36) == 0);
        CHECK(std::abs(padGain(a.g.pads[0], 127, 90) - 1.0) < 1e-9 && std::abs(padGain(a.g.pads[0], 0, 90) - 0.1) < 1e-9);
        Pad fixed; fixed.curve = 3;
        CHECK(padGain(fixed, 1, 100) == 1.0);
        std::vector<uint32_t> seg{0, 5000, 8000};
        Span hs = padWindow(a.g.pads[3], seg, 12000, 22050, rng);   // closed hat: segment 1, end .9
        CHECK(hs.from == 0 && hs.to == 4500);
        Span os = padWindow(a.g.pads[5], seg, 12000, 22050, rng);   // open hat: segment 3 to the end
        CHECK(os.from == 8000 && os.to == 12000);
        // round-robin and random among pads on one note
        std::vector<Pad> rr = parse3(";k40l1k40l2k40l3").g.pads;
        CHECK(pickPad(rr, 40, 64, 0, rng) == 0 && pickPad(rr, 40, 64, 1, rng) == 1 && pickPad(rr, 40, 64, 5, rng) == 2);
        CHECK(!parse3(";k36kd").g.kit() && parse3(";k36kd").g.pads.size() == 1);
        CHECK(canonical3("a;k36u3,4,5") == "a;k36u3,4,5" && parse3("a;k36u3,4,5").g.pads[0].mutes.size() == 3);
        CHECK(canonical3("a;k36q1") == "a;q1k36");     // q starts its own token; canonical order q, x, k
        CHECK(canonical3("a;k60h100") == "a;k60" && parse3("a;k60b30").g.pads[0].tuneCents == -30);
    }

    // ---- the wire
    {
        auto caps = parseHi3("hi 3 xp ready win,rate,swap4,grid");
        CHECK(hasCap(caps, "rate") && hasCap(caps, "grid") && !hasCap(caps, "grain"));
        CHECK(parseHi3("hi 2 xp ready").empty() && !parseHi3("hi 3 311 wait").empty());
        Span w; w.from = 100; w.to = 2000;
        CHECK(onLine(3, 44100, 30000, -20, 0, 1, w) == "on 3 44100 30000 -20 0 1 100 2000");
        CHECK(rateLine(3, 33075, 80, true) == "rate 3 33075 80 1");
        Dna3 a = parse3("dingVw6,6s15,80Gp.5bv6");
        CHECK(lmodLine(0, a.layers[0].v) == "lmod 0 6 6 0 0 15 80");
        CHECK(lgrainLine(0, a.layers[0].g) == "lgrain 0 5000 0 80 80 20 0 0 2 0 b 6 0");
    }

    std::printf("%d checks: %s\n", checks, fails ? "FAILED" : "ok");
    if (fails) std::printf("FAILED %d\n", fails);
    return fails ? 1 : 0;
}

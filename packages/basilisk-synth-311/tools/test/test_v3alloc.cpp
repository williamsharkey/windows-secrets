// V3Alloc checks (no emulator): mono/legato/continue actions, poly limit, strum, groups, live bend.
#include "../../plugin/V3Alloc.h"
#include <cstdio>
#include <string>
using namespace b16v3;
static int fails = 0, checks = 0;
#define CHECK(c) do { checks++; if (!(c)) { fails++; std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
static std::string show(const std::vector<Out> &o)
{
    std::string s;
    for (auto &x : o) {
        char b[96];
        if (x.kind == Out::Rate) std::snprintf(b, sizeof b, "rate %d %u g%d%s; ", x.rec, x.hz, x.glideMs, x.regate ? " regate" : "");
        else std::snprintf(b, sizeof b, "%s %d n%d %u d%d; ", x.c.kind == bsynth::Cmd::On ? "on" : x.c.kind == bsynth::Cmd::Off ? "off" : "cut", x.c.rec, x.c.note, x.c.rateHz, x.c.delayMs);
        s += b;
    }
    return s;
}
static V3Alloc make(const char *dna)
{
    bsynth::Dna d = bsynth::parse(dna);
    bsynth3::Dna3 d3 = bsynth3::parse3(dna);
    V3Alloc a; a.setDna(d, d3);
    for (size_t i = 0; i < d.layers.size(); i++) a.setLayerInfo((int)i, d.layers[i].first, d.layers[i].count, 22050, 22050 * 2);
    return a;
}
static int count(const std::vector<Out> &o, bsynth::Cmd::Kind k) { int n = 0; for (auto &x : o) if (x.kind == Out::Cmd && x.c.kind == k) n++; return n; }
static int rates(const std::vector<Out> &o) { int n = 0; for (auto &x : o) if (x.kind == Out::Rate) n++; return n; }
int main()
{
    {   // legato: overlapping notes glide (Rate), detached notes re-attack
        V3Alloc a = make("ding#4Nlg80");
        CHECK(a.owns(0));
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); CHECK(count(o, bsynth::Cmd::On) == 1); o.clear();
        a.noteOn(64, 100, 2000, o); CHECK(rates(o) == 1 && count(o, bsynth::Cmd::On) == 0 && o[0].glideMs == 80); std::printf("legato: %s\n", show(o).c_str()); o.clear();
        a.noteOff(64, 3000, o); CHECK(rates(o) == 1); o.clear();   // back to 60, still held
        a.noteOff(60, 4000, o); CHECK(count(o, bsynth::Cmd::Off) == 1); o.clear();
        a.noteOn(67, 100, 200000, o); CHECK(count(o, bsynth::Cmd::On) == 1); o.clear();
    }
    {   // continue: a key during the release takes the voice back (regate)
        V3Alloc a = make("ding#4Nc");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); o.clear();
        a.noteOff(60, 2000, o); CHECK(count(o, bsynth::Cmd::Off) == 1); o.clear();
        a.noteOn(62, 100, 3000, o); CHECK(rates(o) == 1 && o[0].regate); std::printf("continue: %s\n", show(o).c_str()); o.clear();
    }
    {   // mono: a new attack each note, the old one cut
        V3Alloc a = make("ding#4Nm");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); o.clear();
        a.noteOn(64, 100, 2000, o); CHECK(count(o, bsynth::Cmd::Cut) == 1 && count(o, bsynth::Cmd::On) == 1); o.clear();
    }
    {   // poly limit 2: the third note cuts the oldest
        V3Alloc a = make("ding#8Np2");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); a.noteOn(62, 100, 2000, o); o.clear();
        a.noteOn(64, 100, 3000, o); CHECK(count(o, bsynth::Cmd::Cut) == 1 && o[0].c.note == 60); o.clear();
    }
    {   // strum: harmony voice k starts k * 30 ms later; unison width spreads the pan
        V3Alloc a = make("ding#8H0,4,7Ss30");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o);
        CHECK(count(o, bsynth::Cmd::On) == 3 && o[0].c.delayMs == 0 && o[1].c.delayMs == 30 && o[2].c.delayMs == 60);
        std::printf("strum: %s\n", show(o).c_str());
    }
    {   // round-robin intervals
        V3Alloc a = make("ding#8H0,12Sr");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); CHECK(count(o, bsynth::Cmd::On) == 1); uint32_t r1 = o[0].c.rateHz; o.clear();
        a.noteOn(60, 100, 2000, o); CHECK(count(o, bsynth::Cmd::On) == 1 && o[0].c.rateHz != r1); o.clear();
    }
    {   // layer groups: two layers take turns
        V3Alloc a = make("ding#4Sg1/chord#4Sg1");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); CHECK(count(o, bsynth::Cmd::On) == 1); int l1 = o[0].c.layer; o.clear();
        a.noteOn(62, 100, 2000, o); CHECK(count(o, bsynth::Cmd::On) == 1 && o[0].c.layer != l1); o.clear();
    }
    {   // degree harmony in C major: 1 3 5 on E (64) = E G B
        V3Alloc a = make("ding#8Dh1,3,5");
        std::vector<Out> o;
        a.noteOn(64, 100, 1000, o); CHECK(count(o, bsynth::Cmd::On) == 3);
        uint32_t e = bsynth::Voices::rateFor(22050, 4, 0), g = bsynth::Voices::rateFor(22050, 7, 0), b = bsynth::Voices::rateFor(22050, 11, 0);
        CHECK(o.size() == 3 && o[0].c.rateHz == e && o[1].c.rateHz == g && o[2].c.rateHz == b);
        std::printf("degrees: %s\n", show(o).c_str());
    }
    {   // live bend: a sounding voice gets a rate line; a fixed layer does not
        V3Alloc a = make("ding#4Nm");
        std::vector<Out> o;
        a.noteOn(60, 100, 1000, o); uint32_t hz = o[0].c.rateHz; o.clear();
        a.bend(1.0, 2000, o); CHECK(rates(o) == 1 && std::abs((double)o[0].hz / hz - std::pow(2.0, 2 / 12.0)) < 1e-3); o.clear();
        bsynth::Cmd c{bsynth::Cmd::On, 9, 60, 30000, 65535};
        a.follow(c, true);
        a.bend(0.0, 3000, o); CHECK(rates(o) == 1 && o[0].rec != 9); o.clear();
    }
    {   // the key: a plain layer stays chromatic in a 12-note scale, walks the scale with remap, snaps a 16-TET tuning
        V3Alloc a = make("ding#4");
        std::vector<Out> o;
        b16v3::KeyParams kp; kp.scale = 8;   // major pentatonic, no remap: core plays it (chromatic, as before)
        a.setKey(b16v3::effectiveKey(kp, bsynth3::parse3("ding#4")));
        CHECK(!a.owns(0));
        kp.remap = 1; kp.anchor = 60;        // remap: 60 61 62 63 64 65 = C D E G A C'
        a.setKey(b16v3::effectiveKey(kp, bsynth3::parse3("ding#4")));
        CHECK(a.owns(0));
        const int want[6] = {0, 2, 4, 7, 9, 12};
        for (int k = 0; k < 6; k++) {
            o.clear(); a.noteOn(60 + k, 100, 1000 + k * 100000, o);
            CHECK(count(o, bsynth::Cmd::On) == 1 && o.back().c.rateHz == bsynth::Voices::rateFor(22050, want[k], 0));
            a.allOff();
        }
        b16v3::KeyParams k16; k16.scale = 30;   // 16-TET, no remap: each key snaps to the nearest step (75 cents)
        a.setKey(b16v3::effectiveKey(k16, bsynth3::parse3("ding#4")));
        CHECK(a.owns(0));
        o.clear(); a.noteOn(61, 100, 1000, o);   // 100 cents -> 75
        CHECK(count(o, bsynth::Cmd::On) == 1 && o.back().c.rateHz == bsynth::Voices::rateFor(22050, 0.75, 0));
        std::printf("16-TET C#: %s\n", show(o).c_str());
    }
    {   // the preset's suggestion: D dorian (q2r2) with use-preset; degree chord on E = E G B (dorian 2nd degree: minor)
        bsynth::Dna d = bsynth::parse("ding#8Dh1,3,5;q2r2"); bsynth3::Dna3 d3 = bsynth3::parse3("ding#8Dh1,3,5;q2r2");
        V3Alloc a; a.setDna(d, d3); a.setLayerInfo(0, 0, 8, 22050, 44100);
        b16v3::KeyParams kp; kp.usePreset = 1;
        a.setKey(b16v3::effectiveKey(kp, d3));
        std::vector<Out> o; a.noteOn(64, 100, 1000, o);
        CHECK(o.size() == 3 && o[0].c.rateHz == bsynth::Voices::rateFor(22050, 4, 0) && o[1].c.rateHz == bsynth::Voices::rateFor(22050, 7, 0) && o[2].c.rateHz == bsynth::Voices::rateFor(22050, 11, 0));
        o.clear(); a.allOff(); a.noteOn(62, 100, 2000, o);   // D: D F A (the tonic, minor)
        CHECK(o.size() == 3 && o[1].c.rateHz == bsynth::Voices::rateFor(22050, 5, 0) && o[2].c.rateHz == bsynth::Voices::rateFor(22050, 9, 0));
        b16v3::KeyParams s; s.root = 3; s.scale = 7;
        CHECK(b16v3::KeyParams().lines() == "key 0 0\nkeyopt 0 1 0 0 60\n");
        b16v3::KeyParams r; CHECK(r.readLine("key 3 7") && r.root == 3 && r.scale == 7 && r.readLine("keyopt 1 3 1 2 48") && r.usePreset == 1 && r.snap == 3 && r.remap == 1 && r.labels == 2 && r.anchor == 48);
        (void)s;
    }
    std::printf("%d checks: %s\n", checks, fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}

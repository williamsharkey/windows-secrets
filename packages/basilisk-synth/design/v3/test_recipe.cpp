// DNA recipe tests (design/PRESET-ENGINE-2.md section 17). Built and run by test_v3.sh.
//   test_recipe [presets.txt]   presets.txt: from collect_presets.py (source TAB name TAB dna), optional
// Checks: every real preset and 20,000 random DNAs go DNA -> recipe -> DNA to the identical canonical form
// (canonical3), in all three forms; lenient input; error positions; and the length distribution of the one-line
// and short forms over the real presets.
#include "recipe.h"
#include "dna3.h"
#include "engine3.h"
#include "dna.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
using namespace bsynth3;

static int fails = 0, checks = 0;
#define CHECK(c) do { checks++; if (!(c)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

static bool roundTrip(const std::string &dna, bool verbose = true)
{
    std::string want = canonical3(dna);
    bool ok = true;
    for (RecipeForm f : {RecipeForm::Lines, RecipeForm::OneLine, RecipeForm::Short}) {
        std::string r = toRecipe(dna, f, 0), got;
        RecipeError e;
        bool parsed = fromRecipe(r, got, &e);
        checks++;
        if (!parsed || got != want) {
            ok = false;
            fails++;
            if (verbose && fails < 30)
                std::printf("FAIL round trip (form %d)\n  dna    %s\n  canon  %s\n  recipe %s\n  back   %s\n  error  %s at %zu: %s\n", (int)f, dna.c_str(), want.c_str(), r.c_str(),
                            got.c_str(), e.word.c_str(), e.pos, e.message.c_str());
        }
    }
    return ok;
}

static void stats(const char *what, std::vector<size_t> v)
{
    if (v.empty()) return;
    std::sort(v.begin(), v.end());
    auto q = [&](double f) { return v[std::min(v.size() - 1, (size_t)(f * (v.size() - 1) + 0.5))]; };
    size_t fit = std::count_if(v.begin(), v.end(), [](size_t x) { return x <= 60; });
    std::printf("  %-34s n %4zu  median %3zu  p90 %3zu  max %4zu  <=60: %zu (%.0f %%)\n", what, v.size(), q(0.5), q(0.9), v.back(), fit, 100.0 * fit / v.size());
}

// characters, not bytes (the symbols are 2-3 bytes in UTF-8)
static size_t chars(const std::string &s) { size_t n = 0; for (unsigned char c : s) if ((c & 0xC0) != 0x80) n++; return n; }

int main(int argc, char **argv)
{
    // ---- the coordinator's examples
    {
        std::string d = "ding>E/tada<<R+#4H0,12U2~9;A5R350";
        std::printf("multi-line:\n%s\none-line: %s\nshort:    %s\n", toRecipe(d, RecipeForm::Lines).c_str(), toRecipe(d, RecipeForm::OneLine).c_str(),
                    toRecipe(d, RecipeForm::Short).c_str());
        roundTrip(d);
        std::string got;
        // lenient: case, ASCII, spacing, either spelling
        CHECK(fromRecipe("DING Faster Echo / tada slower x2, reverse, LOUDER 4 recorders notes +0 +12 unison 2 +-9c | attack 5ms rel 0.35s", got) &&
              got == canonical3(d));
        CHECK(fromRecipe("ding fast echo / tada slow x2 rev loud 4r h+0+12 u2+-9c | a5 r350", got) && got == canonical3(d));
        CHECK(fromRecipe("tada trim 5-45%", got) && got == "tada@45]@11[");
        CHECK(fromRecipe("tada trim 250..750ms", got) && got == "tada@t750]@t250[");
        CHECK(fromRecipe("startup double x2", got) && got == "startup@0CP@0CP");
        CHECK(fromRecipe("logon cut before 20%", got) && got == "logon@20[");
        std::printf("trim: %s | %s\n", toRecipe("tada@45]@11[", RecipeForm::OneLine).c_str(), toRecipe("tada@t750]@t250[", RecipeForm::OneLine).c_str());
        CHECK(toRecipe("tada@45]@11[", RecipeForm::OneLine) == "tada trim 5\xE2\x80\x93" "45%");
        CHECK(toRecipe("tada@t750]@t250[", RecipeForm::OneLine) == "tada trim 250\xE2\x80\x93" "750ms");
        CHECK(toRecipe("startup@0CP@0CP", RecipeForm::OneLine) == "startup double\xC3\x97" "2");
    }
    // ---- errors point at the word
    {
        std::string got;
        RecipeError e;
        CHECK(!fromRecipe("ding faster wobble echo", got, &e) && e.word == "wobble" && e.pos == 12);
        CHECK(!fromRecipe("ding at 120%", got, &e) && e.word == "120%");
        CHECK(!fromRecipe("ding / tada | attack fast", got, &e) && e.word == "fast");
        CHECK(!fromRecipe("ding faster echo / tada slower\xE2\x80\xA6", got, &e) && e.message.find("shortened") != std::string::npos);
        std::printf("error example: '%s' at %zu: %s\n", e.word.c_str(), e.pos, e.message.c_str());
    }
    // ---- every token family once
    {
        const char *all[] = {
            "ding+-><ERCPX[]@30@t250IchimesMtada#4T-12H0,4,-12U3~9FL80O120Q-40Ja0,0.30,100.400,60Jp0,-50.500,50;A10D300S70R1500B12V80K48G-6m1=40m21L0,200m30Z50,200",
            "logon<#8Ws.2~.4l.1~.3v.5m8000NcGp.3j.1z60~120n40c25o20e3s.5bfv6w.7yYd8l6t12q20krSrxpg2xs30d3w.5Vw6,7f2,11s20,60Z36,60,48",
            "aNlg80kh/bNp4/cNm/dSg3/eZ0,127;q9r4xd8tg60s20n2p3a5o3l12b96fhkdk36k38l2y1,90k38l2i120y91,127k42l3j1e.9c1f20k47,53l4r50p100w3b15h70u2,3n1o2zm11W200,400m40J10,300",
            "dingDl3Ws.2q9;A5E7z2",      // unknown tokens and subkeys (v4), kept verbatim
            "", ";A5", "ding//chord", "-", "dingWs0", "a;x", "a;q0", "a;k36", "dingG", "dingNp",
        };
        for (auto s : all) roundTrip(s);
        std::printf("%s\n", toRecipe(all[1], RecipeForm::Lines).c_str());
        std::printf("%s\n", toRecipe(all[2], RecipeForm::OneLine).c_str());
    }
    // ---- the real presets
    std::map<std::string, std::vector<size_t>> one, sht;
    std::vector<size_t> oneAll, shtAll;
    int truncated = 0, n = 0, bad = 0;
    std::set<std::string> seen;
    if (argc > 1) {
        std::ifstream in(argv[1]);
        std::string line;
        std::vector<std::tuple<std::string, std::string, std::string>> rows;
        std::vector<std::string> names;
        while (std::getline(in, line)) {
            size_t a = line.find('\t'), b = line.find('\t', a + 1);
            if (a == std::string::npos || b == std::string::npos) continue;
            rows.emplace_back(line.substr(0, a), line.substr(a + 1, b - a - 1), line.substr(b + 1));
        }
        // the library NAMEs the presets use (core drops an Insert/Mix of an unknown NAME, so it must know them)
        for (auto &r : rows) {
            const std::string &d = std::get<2>(r);
            for (size_t i = 0; i < d.size(); i++) {
                bool start = i == 0 || d[i - 1] == '/' || d[i - 1] == 'I' || d[i - 1] == 'M';
                if (!start) continue;
                size_t j = i; while (j < d.size() && (islower((unsigned char)d[j]) || isdigit((unsigned char)d[j]) || d[j] == '_')) j++;
                if (j > i) names.push_back(d.substr(i, j - i));
            }
        }
        bsynth::setLibrary(names);
        for (auto &r : rows) {
            const std::string &tag = std::get<0>(r), &dna = std::get<2>(r);
            n++;
            if (!roundTrip(dna)) { bad++; continue; }
            if (!seen.insert(canonical3(dna)).second) continue;   // length statistics over distinct presets
            std::string o = toRecipe(dna, RecipeForm::OneLine), s0 = toRecipe(dna, RecipeForm::Short, 0), s = toRecipe(dna, RecipeForm::Short, 60);
            if (s != s0) truncated++;
            one[tag].push_back(chars(o)); sht[tag].push_back(chars(s0));
            oneAll.push_back(chars(o)); shtAll.push_back(chars(s0));
        }
        std::printf("real presets: %d checked in 3 forms, %d failed; %zu distinct\n", n, bad, seen.size());
        std::printf("lengths in characters (distinct presets):\n");
        stats("one-line, all", oneAll);
        stats("short (uncut), all", shtAll);
        for (auto &kv : one) { stats(("one-line, " + kv.first).c_str(), kv.second); stats(("short, " + kv.first).c_str(), sht[kv.first]); }
        std::printf("  short forms cut to 60 with \xE2\x80\xA6: %d of %zu\n", truncated, seen.size());
        // a few examples
        int shown = 0;
        for (auto &r : rows) {
            if (shown++ % 97) continue;
            std::printf("  %s\n    one-line: %s\n    short:    %s\n", std::get<2>(r).c_str(), toRecipe(std::get<2>(r), RecipeForm::OneLine).c_str(), toRecipe(std::get<2>(r), RecipeForm::Short).c_str());
        }
    }
    // ---- fuzz: the same 20,000-string generator as test_v3 (v1/v2 tokens, v3 tokens, globals, pads)
    {
        const char *v2tok[] = {"+", "-", ">", "<", "E", "R", "[", "]", "C", "P", "X", "@30", "@t250", "@t1500", "Iding", "Mchimes",
                               "#4", "T-12", "H0,4,7", "U3~9", "U2", "F", "L80", "O120", "Q-40", "Q0", "Ja0,0.30,100", "Jp0,-50.500,50", "@0CP", "@45]@11[", "@t750]@t250["};
        const char *v3tok[] = {"Ws.2~.4l.1~.3", "We.9", "Wv.5m8000", "Np4", "Nm", "Nlg80", "Ncg200kh", "Sr", "Sx", "Sp",
                               "Sg2x", "Ss30", "Sd3", "Sw.5", "Yd8l6t12q20kr", "Vw8,6", "Vf2,12s30,80", "Z0,59,48",
                               "Gp.5j.2z40~90n60c30o20e3s.5bv6w.7y", "Gf", "Ws.1u5", "G", "Z40,70", "Dl3"};
        const char *v2glob[] = {"A10", "D300", "S70", "R250", "B12", "V80", "K48", "G-6", "m1=40", "m21L0,200", "m30Z50,200", "R1500"};
        const char *v3glob[] = {"q0", "q9r4", "x", "xd8tg60s20n1p6a5o3l12b96fh", "m11W200,400", "m40J10,300", "xz2", "k36", "k42l3j2e.5c1f15",
                                "k46l3j2s.5c1", "k60,72l2p100w5t20h40y1,90g", "kd", "k38u1,2z", "E7"};
        const char *src[] = {"ding", "chord", "tada", "logon", "ringout", ""};
        Rng r(4242);
        int bad0 = fails;
        for (int k = 0; k < 20000; k++) {
            std::string v3;
            int layers = r.in(1, 4);
            for (int l = 0; l < layers; l++) {
                if (l) v3 += "/";
                v3 += src[r.in(0, 5)];
                int m = r.in(0, 8);
                for (int i = 0; i < m; i++) v3 += r.in(0, 2) == 0 ? v3tok[r.in(0, 23)] : v2tok[r.in(0, 30)];
            }
            if (r.in(0, 1)) {
                v3 += ";";
                int m = r.in(0, 6);
                for (int i = 0; i < m; i++) v3 += r.in(0, 2) == 0 ? v3glob[r.in(0, 13)] : v2glob[r.in(0, 11)];
            }
            roundTrip(v3);
            if (fails > bad0 + 10) break;
        }
        std::printf("fuzz: 20000 random DNAs x 3 forms, %d failures\n", fails - bad0);
    }
    std::printf("%d checks: %s\n", checks, fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}

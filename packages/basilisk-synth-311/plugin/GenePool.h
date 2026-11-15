// SNDWAVE2000: GENEPOOL.EXE, a table of sounds dealt as playing cards (1.5). Every card is a DNA. Draw deals new
// cards from the deck (pack presets, and raw sounds of the library and the inserted discs with random genes); Breed
// crosses two or more cards into a new generation (layers and gene families from either parent, then mutation);
// Keep saves a card (the kept row, and a .BSP file in Documents/SNDWAVE2000/Kept Sounds); Discard removes it. A click
// loads the card into this instance's own recorders and plays it: every audition is Sound Recorder.
//
// All DNA stays typable ASCII and passes the parser (dna.h): a child that does not parse back to valid layers is drawn
// again. Everything follows from one seed (SplitMix64), kept in the project with the table.
//
// Windows -> host: pool open | pool draw <n> | pool breed <id,id,...> | pool keep <id> | pool discard <id>
//                  pool play <id> | pool rate <0-100> | pool clear
// host -> Windows: pool clear | pool card <id>|<name>|<suit 0-3>|<rank 1-13>|<generation>|<kept>|<parents>|<code>
//                  pool end | pool status <text>
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#include "../../basilisk-synth/core/dna.h"
#include "../../basilisk-synth/core/userstore.h"

namespace b16pool {

struct Card { int id = 0, gen = 0, suit = 0, rank = 1; bool kept = false; std::string name, dna; std::vector<int> parents; };

class Pool {
public:
    uint64_t seed = 0x5EED3110ull;
    int rate = 25;   // mutation, percent
    int nextId = 1;
    std::vector<Card> cards;          // on the table, in deal order
    std::vector<Card> kept;           // the kept row
    std::vector<std::pair<std::string, std::string>> deck;   // (name, DNA): every pack preset of the machine
    std::vector<std::string> sounds;  // raw sound NAMEs: the six of C:\WINDOWS, the library disc, the pack discs
    std::map<std::string, std::string> soundPack;   // a pack disc's sound NAME -> its pack id (the disc goes in to play it)

    void loadDeck(const std::string &machine)
    {
        if (!deck.empty()) return;
        std::ifstream pk(machine + "/packs/PACKS.TSV"); std::string l;
        while (std::getline(pk, l)) {
            if (!l.empty() && l.back() == '\r') l.pop_back();
            const size_t a = l.find('\t'); if (a == std::string::npos) continue;
            {   // the disc's sounds
                const size_t b2 = l.find('\t', a + 1); const std::string id = l.substr(a + 1, b2 == std::string::npos ? std::string::npos : b2 - a - 1);
                std::ifstream lt(machine + "/packs/" + l.substr(0, a) + "/LIBRARY.TSV"); std::string r2;
                while (std::getline(lt, r2)) { if (r2.empty() || r2[0] == '#') continue; const size_t t2 = r2.find('\t'); soundPack[r2.substr(0, t2)] = id; }
            }
            std::ifstream t(machine + "/packs/" + l.substr(0, a) + "/PRESETS.TSV"); std::string r;
            while (std::getline(t, r)) {
                if (!r.empty() && r.back() == '\r') r.pop_back();
                if (r.empty() || r[0] == '#') continue;
                std::vector<std::string> c; std::stringstream ss(r); std::string x; while (std::getline(ss, x, '\t')) c.push_back(x);
                if (c.size() >= 3 && (c.size() < 5 || c[4].find("3.11") != std::string::npos)) deck.push_back({c[1], c[2]});
            }
        }
        for (const char *s : {"chimes", "ding", "ringin", "ringout", "chord", "tada"}) sounds.push_back(s);
        for (const char *f : {"/library.names.txt", "/packs/packs.names.txt"}) {
            std::ifstream n(machine + f);
            while (std::getline(n, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) sounds.push_back(l); }
        }
    }

    // ---- the deck: n new cards, generation 0
    std::vector<int> draw(int n)
    {
        std::vector<int> ids;
        for (int k = 0; k < n; k++) {
            Card c; c.id = nextId++; c.gen = 0;
            if (!deck.empty() && (sounds.empty() || next() % 100 < 70)) {   // a pack preset, as it is
                const auto &p = deck[next() % deck.size()];
                c.name = p.first; c.dna = bsynth::canonical(p.second);
            } else {   // a raw sound with random genes
                c.dna = randomSound(); c.name = rawName(c.dna);
            }
            face(c);
            cards.push_back(c); ids.push_back(c.id);
        }
        return ids;
    }
    // ---- a new generation: n children of the parents
    std::vector<int> breed(const std::vector<int> &pids, int n)
    {
        std::vector<Card> pc;   // (copies: the table grows while the children are dealt)
        for (int id : pids) if (const Card *c = find(id)) pc.push_back(*c);
        std::vector<const Card *> ps; for (auto &c : pc) ps.push_back(&c);
        std::vector<int> ids;
        if (ps.size() < 2) return ids;
        int gen = 0; for (auto *p : ps) gen = std::max(gen, p->gen);
        for (int k = 0; k < n; k++) {
            const Card *a = ps[next() % ps.size()], *b = ps[next() % ps.size()];
            if (a == b) b = ps[(std::find(ps.begin(), ps.end(), a) - ps.begin() + 1) % ps.size()];
            Card c; c.id = nextId++; c.gen = gen + 1; c.parents = {a->id, b->id};
            c.dna = cross(a->dna, b->dna);
            c.dna = mutate(c.dna);
            c.name = childName(*a, *b);
            face(c);
            cards.push_back(c); ids.push_back(c.id);   // (at once: the next child's name sees this one)
        }
        return ids;
    }
    bool keep(int id)
    {
        auto it = std::find_if(cards.begin(), cards.end(), [&](const Card &c) { return c.id == id; });
        if (it == cards.end()) return false;
        it->kept = true; kept.push_back(*it); cards.erase(it);
        return true;
    }
    bool discard(int id)
    {
        auto it = std::find_if(cards.begin(), cards.end(), [&](const Card &c) { return c.id == id; });
        if (it == cards.end()) return false;
        cards.erase(it); return true;
    }
    std::vector<std::string> packsFor(const std::string &dna) const   // the pack discs a DNA's sounds are on
    {
        std::vector<std::string> v; const bsynth::Dna d = bsynth::parse(dna);
        for (auto &L : d.layers) {
            auto it = soundPack.find(L.sourceName);
            if (it != soundPack.end() && std::find(v.begin(), v.end(), it->second) == v.end()) v.push_back(it->second);
        }
        return v;
    }
    const Card *find(int id) const
    {
        for (auto &c : cards) if (c.id == id) return &c;
        for (auto &c : kept) if (c.id == id) return &c;
        return nullptr;
    }

    // ---- the table in the project state: one text, base64 in the state line
    std::string save() const
    {
        std::ostringstream o; o << "genepool 1\nseed " << seed << "\nrate " << rate << "\nnext " << nextId << "\n";
        auto put = [&](const Card &c) {
            o << "card " << c.id << "\t" << c.gen << "\t" << (c.kept ? 1 : 0) << "\t";
            for (size_t k = 0; k < c.parents.size(); k++) o << (k ? "," : "") << c.parents[k];
            o << "\t" << c.name << "\t" << c.dna << "\n";
        };
        for (auto &c : cards) put(c);
        for (auto &c : kept) put(c);
        return o.str();
    }
    void load(const std::string &text)
    {
        cards.clear(); kept.clear();
        std::istringstream in(text); std::string l;
        while (std::getline(in, l)) {
            if (l.rfind("seed ", 0) == 0) seed = std::stoull(l.substr(5));
            else if (l.rfind("rate ", 0) == 0) rate = std::atoi(l.c_str() + 5);
            else if (l.rfind("next ", 0) == 0) nextId = std::atoi(l.c_str() + 5);
            else if (l.rfind("card ", 0) == 0) {
                std::vector<std::string> f; std::stringstream ss(l.substr(5)); std::string x; while (std::getline(ss, x, '\t')) f.push_back(x);
                if (f.size() < 6) continue;
                Card c; c.id = std::atoi(f[0].c_str()); c.gen = std::atoi(f[1].c_str()); c.kept = f[2] == "1";
                std::stringstream ps(f[3]); while (std::getline(ps, x, ',')) if (!x.empty()) c.parents.push_back(std::atoi(x.c_str()));
                c.name = f[4]; c.dna = f[5]; face(c);
                (c.kept ? kept : cards).push_back(c);
            }
        }
    }

private:
    uint64_t next() { uint64_t z = (seed += 0x9E3779B97F4A7C15ull); z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull; z = (z ^ (z >> 27)) * 0x94D049BB133111EBull; return z ^ (z >> 31); }
    int range(int lo, int hi) { return lo + (int)(next() % (uint64_t)(hi - lo + 1)); }

    static void face(Card &c)   // a playing card for it: the suit from its sound families, the rank from its DNA
    {
        const std::string h = bsynth::sha1Hex(c.dna.data(), c.dna.size());
        const bsynth::Dna d = bsynth::parse(c.dna);
        const std::string &src = d.layers.empty() ? c.dna : d.layers[0].sourceName;
        unsigned v = 0; for (char ch : src) v = v * 31 + (unsigned char)ch;
        c.suit = (int)(v % 4);
        c.rank = 1 + (int)(std::stoul(h.substr(0, 6), nullptr, 16) % 13);
    }
    static bool valid(const std::string &dna)
    {
        const bsynth::Dna d = bsynth::parse(dna);
        if (d.layers.empty() || d.layers.size() > 8 || dna.size() > 1000) return false;
        for (auto &L : d.layers) if (!L.valid()) return false;
        for (char ch : dna) if ((unsigned char)ch < 32 || (unsigned char)ch > 126) return false;
        return true;
    }
    static void split(const std::string &dna, std::vector<std::string> &layers, std::string &globals)
    {
        const std::string c = bsynth::canonical(dna);
        const size_t s = c.find(';');
        const std::string ls = c.substr(0, s); globals = s == std::string::npos ? "" : c.substr(s + 1);
        layers.clear(); size_t p = 0;
        while (true) { const size_t q = ls.find('/', p); layers.push_back(ls.substr(p, q == std::string::npos ? std::string::npos : q - p)); if (q == std::string::npos) break; p = q + 1; }
    }
    static bool isKit(const std::string &globals)   // kits and the sequencer: layers and pads belong together
    {
        for (size_t i = 0; i + 1 < globals.size(); i++)
            if ((globals[i] == 'k' || globals[i] == 'x') && (std::isdigit((unsigned char)globals[i + 1]) || globals[i + 1] == 's' || globals[i + 1] == 'd')) return true;
        return false;
    }
    // global tokens by family: a capital letter and what follows it up to the next capital
    static std::vector<std::string> tokens(const std::string &g)
    {
        std::vector<std::string> t; std::string cur;
        for (char ch : g) { if (std::isupper((unsigned char)ch) && !cur.empty()) { t.push_back(cur); cur.clear(); } cur += ch; }
        if (!cur.empty()) t.push_back(cur);
        return t;
    }
    std::string cross(const std::string &a, const std::string &b)
    {
        std::vector<std::string> la, lb; std::string ga, gb;
        split(a, la, ga); split(b, lb, gb);
        for (int tries = 0; tries < 12; tries++) {
            const bool aDom = next() & 1;
            const auto &ld = aDom ? la : lb, &lo = aDom ? lb : la; const std::string &gd = aDom ? ga : gb, &go = aDom ? gb : ga;
            std::vector<std::string> L;
            if (isKit(gd)) L = ld;   // a kit's layers are its pads: they stay with its globals
            else {
                const size_t n = std::max<size_t>(1, std::min<size_t>(4, next() & 1 ? ld.size() : (ld.size() + lo.size() + 1) / 2));
                for (size_t i = 0; i < n; i++) {
                    const bool fromD = (next() % 100) < 60 || isKit(go);
                    const auto &src = fromD || lo.empty() ? ld : lo;
                    L.push_back(src[i % src.size()]);
                }
            }
            // globals: the dominant parent's, with each classic gene (A D S R V G) from either parent
            std::vector<std::string> td = tokens(gd), to = tokens(go);
            for (auto &t : td) {
                if (t.size() < 2 || std::string("ADSRVG").find(t[0]) == std::string::npos || !std::isdigit((unsigned char)t[1]) && t[1] != '-') continue;
                if (next() & 1) for (auto &u : to) if (u[0] == t[0] && u.size() > 1 && (std::isdigit((unsigned char)u[1]) || u[1] == '-')) { t = u; break; }
            }
            std::string out;
            for (size_t i = 0; i < L.size(); i++) out += (i ? "/" : "") + L[i];
            std::string g; for (auto &t : td) g += t;
            if (!g.empty()) out += ";" + g;
            const std::string c = bsynth::canonical(out);
            if (valid(c)) return c;
        }
        return bsynth::canonical(a);
    }
    std::string mutate(const std::string &dna)
    {
        std::string d = bsynth::canonical(dna);
        const bsynth::Dna p = bsynth::parse(d);
        auto chance = [&](int scale) { return (int)(next() % 1000) < rate * scale; };
        for (int i = 0; i < (int)p.layers.size(); i++) {
            const auto &L = p.layers[i];
            std::string t = d;
            if (chance(4)) t = bsynth::setLayerGene(t, i, 'T', std::max(-24, std::min(24, L.transpose + range(-7, 7))));
            if (chance(5)) t = bsynth::setLayerGene(t, i, 'L', std::max(10, std::min(200, L.level + range(-35, 35))));
            if (chance(2) && !sounds.empty()) t = bsynth::setLayerSource(t, i, sounds[next() % sounds.size()]);   // a new sound in the old genes
            if (chance(2)) {   // one of Sound Recorder's effects, appended
                static const char ops[] = {'+', '-', '>', '<', 'E', 'R'};
                t = bsynth::appendStep(t, i, ops[next() % 6]);
            }
            if (valid(t)) d = t;
        }
        const auto &g = p.g;
        auto nudge = [&](char letter, int v, int lo, int hi, int pct) {
            if (!chance(5)) return;
            const int span = std::max(10, v * pct / 100);
            const std::string t = bsynth::setGlobal(d, letter, std::max(lo, std::min(hi, v + range(-span, span))));
            if (valid(t)) d = t;
        };
        nudge('A', g.attack, 0, 3000, 60); nudge('D', g.decay, 0, 5000, 60); nudge('S', g.sustain, 0, 100, 40);
        nudge('R', g.release, 10, 4000, 60); nudge('G', g.gainDb, -12, 6, 0);
        return bsynth::canonical(d);
    }
    std::string randomSound()
    {
        for (int tries = 0; tries < 12; tries++) {
            std::string out;
            const int n = range(1, 2);
            for (int k = 0; k < n; k++) {
                const std::string &s = sounds[next() % sounds.size()];
                char b[160]; std::snprintf(b, sizeof b, "%s%s#%d", k ? "/" : "", s.c_str(), range(2, 8)); out += b;
                if (next() & 1) { char t[16]; std::snprintf(t, sizeof t, "T%d", range(-12, 12)); out += t; }
            }
            char g[96]; std::snprintf(g, sizeof g, ";A%dD%dS%dR%d", range(0, 400), range(100, 3000), range(0, 100), range(80, 1500));
            out += g;
            const std::string c = bsynth::canonical(out);
            if (valid(c)) return c;
        }
        return bsynth::canonical("ding#8;R300");
    }
    static std::string rawName(const std::string &dna)   // "em_tape_recorder_a" -> "Tape Recorder"
    {
        const bsynth::Dna d = bsynth::parse(dna);
        const std::string src = d.layers.empty() ? "sound" : d.layers[0].sourceName;
        std::vector<std::string> w; std::string cur;
        for (char ch : src + "_") { if (ch == '_' || ch == '-' || ch == ' ') { if (!cur.empty()) w.push_back(cur); cur.clear(); } else cur += ch; }
        while (w.size() > 1 && w[0].size() <= 2) w.erase(w.begin());   // (a pack's prefix: em, gd, pw ...)
        std::string n;
        for (size_t k = 0; k < w.size() && k < 2; k++) {
            std::string x = w[k]; if (x.size() <= 1 || std::isdigit((unsigned char)x[0])) continue;
            x[0] = (char)std::toupper((unsigned char)x[0]); n += (n.empty() ? "" : " ") + x;
        }
        return n.empty() ? "Raw Sound" : n;
    }
    std::string childName(const Card &a, const Card &b)
    {
        auto words = [](const std::string &s) { std::vector<std::string> w; std::stringstream ss(s); std::string x; while (ss >> x) if (x != "Raw" && x != "II" && x != "III" && x != "IV" && x != "V") w.push_back(x); return w; };
        auto wa = words(a.name), wb = words(b.name);
        std::string n = (wa.empty() ? "New" : wa.front()) + " " + (wb.empty() ? "Sound" : wb.back());
        if (n.size() > 28) n.resize(28);
        int same = 0; for (auto &c : cards) if (c.name.rfind(n, 0) == 0) same++;
        for (auto &c : kept) if (c.name.rfind(n, 0) == 0) same++;
        if (same) { static const char *rom[] = {"II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}; n += std::string(" ") + rom[std::min(same - 1, 8)]; }
        return n;
    }
};

}  // namespace b16pool

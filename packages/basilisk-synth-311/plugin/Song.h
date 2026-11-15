// SNDWAVE1993: songs (design/SONG-TAB.md). The .song text (tools/songrender/README.md: the exact format
// songrender.py reads), Standard MIDI Files, and the split of a file into one track's events, done exactly as
// songrender.py + render311 do it, so a track rendered here and a stem rendered there are the same bytes.
#pragma once
#include <algorithm>
#include <cctype>
#include <fstream>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "PackAlias.h"
#include "SongEngine.h"

namespace b16song {

// ---------------------------------------------------------------------------------------------- MIDI files
struct SmfEvent { uint64_t tick; std::vector<uint8_t> b; };   // the whole event, status first; meta as FF type len data
struct Smf {
    int division = 480;
    std::vector<std::vector<SmfEvent>> tracks;

    bool parse(const std::vector<uint8_t> &d, std::string *err = nullptr)
    {
        auto fail = [&](const char *m) { if (err) *err = m; return false; };
        if (d.size() < 14 || std::memcmp(d.data(), "MThd", 4)) return fail("not a MIDI file");
        const uint32_t hl = be32(&d[4]); const int ntrk = be16(&d[10]), div = be16(&d[12]);
        if (div & 0x8000) return fail("SMPTE timing is not supported");
        division = div; tracks.clear();
        size_t p = 8 + hl;
        for (int t = 0; t < ntrk; t++) {
            if (p + 8 > d.size() || std::memcmp(&d[p], "MTrk", 4)) return fail("bad track chunk");
            const size_t end = std::min(d.size(), p + 8 + be32(&d[p + 4])); p += 8;
            uint64_t tick = 0; uint8_t run = 0; std::vector<SmfEvent> evs;
            auto vlq = [&]() { uint32_t v = 0; uint8_t c; do { if (p >= end) return v; c = d[p++]; v = (v << 7) | (c & 0x7F); } while (c & 0x80); return v; };
            while (p < end) {
                tick += vlq();
                if (p >= end) break;
                uint8_t st = d[p];
                if (st & 0x80) p++; else st = run;
                SmfEvent e; e.tick = tick;
                if (st == 0xFF) {
                    const uint8_t ty = d[p++]; const size_t q = p; const uint32_t ln = vlq();
                    e.b = {0xFF, ty}; e.b.insert(e.b.end(), d.begin() + (long)q, d.begin() + (long)std::min(end, p + ln));
                    p += ln;
                } else if (st == 0xF0 || st == 0xF7) {
                    const size_t q = p; const uint32_t ln = vlq();
                    e.b = {st}; e.b.insert(e.b.end(), d.begin() + (long)q, d.begin() + (long)std::min(end, p + ln));
                    p += ln;
                } else {
                    run = st;
                    const int n = ((st & 0xF0) == 0xC0 || (st & 0xF0) == 0xD0) ? 1 : 2;
                    e.b = {st}; for (int k = 0; k < n && p < end; k++) e.b.push_back(d[p++]);
                }
                evs.push_back(e);
            }
            tracks.push_back(evs);
            p = end;
        }
        return true;
    }
    std::vector<std::pair<uint64_t, uint32_t>> tempoMap() const   // (tick, microseconds per quarter), by tick
    {
        std::vector<std::pair<uint64_t, uint32_t>> tm;
        for (const auto &tr : tracks) for (const auto &e : tr)
            if (e.b.size() >= 6 && e.b[0] == 0xFF && e.b[1] == 0x51) tm.push_back({e.tick, (uint32_t)(e.b[3] << 16 | e.b[4] << 8 | e.b[5])});
        std::stable_sort(tm.begin(), tm.end(), [](const auto &a, const auto &b) { return a.first < b.first; });
        return tm;
    }
    double seconds(uint64_t tick) const   // smf.py Smf.seconds
    {
        double sec = 0; uint64_t last = 0; double uspq = 500000;
        for (const auto &t : tempoMap()) {
            if (t.first >= tick) break;
            sec += (double)(t.first - last) * uspq / 1e6 / division; last = t.first; uspq = t.second;
        }
        return sec + (double)(tick - last) * uspq / 1e6 / division;
    }
    std::vector<uint8_t> write() const   // smf.py Smf.write: format 1 (0 with one track), events stable by tick, end of track
    {
        auto vlq = [](std::vector<uint8_t> &o, uint64_t v) { uint8_t b[10]; int n = 0; b[n++] = v & 0x7F; v >>= 7; while (v) { b[n++] = 0x80 | (v & 0x7F); v >>= 7; } while (n) o.push_back(b[--n]); };
        auto be = [](std::vector<uint8_t> &o, uint32_t v, int n) { for (int k = n - 1; k >= 0; k--) o.push_back((uint8_t)(v >> (8 * k))); };
        std::vector<uint8_t> o = {'M', 'T', 'h', 'd'}; be(o, 6, 4); be(o, tracks.size() == 1 ? 0 : 1, 2); be(o, (uint32_t)tracks.size(), 2); be(o, (uint32_t)division, 2);
        for (const auto &tr : tracks) {
            std::vector<SmfEvent> ev = tr;
            std::stable_sort(ev.begin(), ev.end(), [](const SmfEvent &a, const SmfEvent &b) { return a.tick < b.tick; });
            std::vector<uint8_t> body; uint64_t last = 0, end = 0;
            for (const auto &e : ev) {
                end = std::max(end, e.tick);
                if (e.b.size() >= 2 && e.b[0] == 0xFF && e.b[1] == 0x2F) continue;
                vlq(body, e.tick - last); body.insert(body.end(), e.b.begin(), e.b.end()); last = e.tick;
            }
            vlq(body, end - last); body.insert(body.end(), {0xFF, 0x2F, 0x00});
            o.insert(o.end(), {'M', 'T', 'r', 'k'}); be(o, (uint32_t)body.size(), 4); o.insert(o.end(), body.begin(), body.end());
        }
        return o;
    }
    uint64_t lastTick() const { uint64_t m = 0; for (const auto &tr : tracks) for (const auto &e : tr) m = std::max(m, e.tick); return m; }
    double firstTempoBpm() const { auto tm = tempoMap(); return tm.empty() ? 120.0 : 60e6 / tm[0].second; }
    std::vector<int> channels() const
    {
        std::vector<int> c;
        for (const auto &tr : tracks) for (const auto &e : tr) if (!e.b.empty() && e.b[0] < 0xF0) { const int ch = e.b[0] & 15; if (std::find(c.begin(), c.end(), ch) == c.end()) c.push_back(ch); }
        std::sort(c.begin(), c.end());
        return c;
    }
};

// a track's source: chN, trN, joined by +, or all (README "SOURCE")
struct Source {
    bool all = false; std::vector<int> chans, trks;
    bool parse(const std::string &s)
    {
        all = s == "all"; chans.clear(); trks.clear();
        if (all) return true;
        size_t p = 0;
        while (p < s.size()) {
            size_t q = s.find('+', p); if (q == std::string::npos) q = s.size();
            const std::string part = s.substr(p, q - p);
            if (part.size() < 3) return false;
            const int v = std::atoi(part.c_str() + 2);
            if (part.compare(0, 2, "ch") == 0 && v >= 1 && v <= 16) chans.push_back(v - 1);
            else if (part.compare(0, 2, "tr") == 0 && v >= 0) trks.push_back(v);
            else return false;
            p = q + 1;
        }
        return !chans.empty() || !trks.empty();
    }
    bool match(int ti, int ch) const
    {
        if (all) return true;
        const bool c = chans.empty() || std::find(chans.begin(), chans.end(), ch) != chans.end();
        const bool t = trks.empty() || std::find(trks.begin(), trks.end(), ti) != trks.end();
        return c && t;
    }
};

inline int prioOf(const std::vector<uint8_t> &e)   // smf.py _prio: tempo, note-offs, the rest, note-ons
{
    if (e[0] == 0xFF) return 0;
    const int st = e[0] & 0xF0;
    if (st == 0x80 || (st == 0x90 && e.size() > 2 && e[2] == 0)) return 1;
    return st == 0x90 ? 3 : 2;
}
inline long pyRound(double x) { return std::lrint(x); }   // Python's round(): halves to even (the default rounding mode)

// One track's events in seconds: Smf.extract (tempo map + selected events on channel 1, transposed, velocity
// scaled), the tune bend inserted first, written and read back as render311 reads a file. `notes` counts note-ons.
inline std::vector<MidiEv> extractTrack(const Smf &smf, const Source &src, int transpose, double velScale, double tuneCents,
                                        int bendRange, int *notes = nullptr)
{
    std::vector<SmfEvent> evs;
    for (size_t ti = 0; ti < smf.tracks.size(); ti++)
        for (const auto &e : smf.tracks[ti]) {
            if (e.b.size() >= 2 && e.b[0] == 0xFF && e.b[1] == 0x51) { evs.push_back(e); continue; }
            if (e.b.empty() || e.b[0] >= 0xF0 || !src.match((int)ti, e.b[0] & 15)) continue;
            SmfEvent x = e; const int st = x.b[0] & 0xF0; x.b[0] = (uint8_t)st;
            if ((st == 0x80 || st == 0x90 || st == 0xA0) && x.b.size() >= 2) {
                const int n = x.b[1] + transpose;
                if (n < 0 || n > 127) continue;
                x.b[1] = (uint8_t)n;
                if (st == 0x90 && x.b.size() > 2 && x.b[2] > 0 && velScale != 1.0)
                    x.b[2] = (uint8_t)std::max(1L, std::min(127L, pyRound(x.b[2] * velScale)));
            }
            evs.push_back(x);
        }
    std::stable_sort(evs.begin(), evs.end(), [](const SmfEvent &a, const SmfEvent &b) {
        return a.tick != b.tick ? a.tick < b.tick : prioOf(a.b) < prioOf(b.b); });
    if (tuneCents != 0) {   // cents, through the plugin's own pitch bend (the DNA's B range)
        const int v = (int)pyRound(8192 + tuneCents / (bendRange * 100.0) * 8191);
        evs.insert(evs.begin(), SmfEvent{0, {0xE0, (uint8_t)(v & 0x7F), (uint8_t)(v >> 7)}});
    }
    // render311's readMidi on the written file: tempo and channel events, stable by tick, seconds piecewise
    std::vector<MidiEv> out; double sec = 0; uint64_t last = 0; double spt = 0.5 / smf.division; int nn = 0;
    for (const auto &e : evs) {
        sec += (double)(e.tick - last) * spt; last = e.tick;
        if (e.b[0] == 0xFF) { if (e.b.size() >= 6 && e.b[1] == 0x51) spt = (double)(e.b[3] << 16 | e.b[4] << 8 | e.b[5]) / 1e6 / smf.division; continue; }
        if ((e.b[0] & 0xF0) == 0x90 && e.b.size() > 2 && e.b[2] > 0) nn++;
        out.push_back({sec, e.b[0], e.b.size() > 1 ? e.b[1] : (uint8_t)0, e.b.size() > 2 ? e.b[2] : (uint8_t)0});
    }
    if (notes) *notes = nn;
    return out;
}

// ---------------------------------------------------------------------------------------------- the .song text
struct SongTrack {
    std::string name, src = "all", preset, dna;   // preset: "Name", "Category/Name" or "pack:Name"; dna: 'dna:...'
    double vol = 0, pan = 0, echo = 0, verb = 0, vel = 1, width = 1, hp = 0, lp = 0, tune = 0, lufs = 0;
    bool hasLufs = false, mute = false, solo = false;
    int tr = 0;
};
struct SongText {
    std::vector<std::pair<std::string, std::string>> meta;   // in written order
    std::map<std::string, std::map<std::string, std::string>> sec;   // master, echo, reverb
    std::vector<std::pair<std::string, std::string>> pinned;  // [dna] "pack:Name" = DNA
    std::vector<SongTrack> tracks;

    std::string get(const std::string &k, const std::string &def = "") const { for (const auto &m : meta) if (m.first == k) return m.second; return def; }
    void set(const std::string &k, const std::string &v) { for (auto &m : meta) if (m.first == k) { m.second = v; return; } meta.push_back({k, v}); }
    static std::string trim(std::string s) { while (!s.empty() && (s.back() == ' ' || s.back() == '\t' || s.back() == '\r')) s.pop_back(); size_t i = 0; while (i < s.size() && (s[i] == ' ' || s[i] == '\t')) i++; return s.substr(i); }
    static std::vector<std::string> shlexSplit(const std::string &s, std::string *err)   // Python shlex.split(comments=True)
    {
        std::vector<std::string> out; std::string cur; bool in = false; char q = 0; bool any = false;
        for (size_t i = 0; i < s.size(); i++) {
            const char c = s[i];
            if (q) { if (c == q) q = 0; else if (c == '\\' && q == '"' && i + 1 < s.size() && (s[i + 1] == '"' || s[i + 1] == '\\')) cur += s[++i]; else cur += c; continue; }
            if (c == '"' || c == '\'') { q = c; in = true; any = true; continue; }
            if (c == '#' && !in) break;
            if (c == ' ' || c == '\t') { if (in) { out.push_back(cur); cur.clear(); in = false; } continue; }
            if (c == '\\' && i + 1 < s.size()) { cur += s[++i]; in = true; continue; }
            cur += c; in = true; (void)any;
        }
        if (q) { if (err) *err = "No closing quotation"; return {}; }
        if (in) out.push_back(cur);
        return out;
    }
    bool parse(const std::string &text, std::string *err)
    {
        meta.clear(); sec.clear(); pinned.clear(); tracks.clear();
        std::string section; int ln = 0; size_t p = 0;
        auto fail = [&](const std::string &m) { if (err) *err = "line " + std::to_string(ln) + ": " + m; return false; };
        while (p <= text.size()) {
            size_t q = text.find('\n', p); if (q == std::string::npos) q = text.size();
            std::string s = trim(text.substr(p, q - p)); p = q + 1; ln++;
            if (s.empty() || s[0] == '#') { if (q == text.size()) break; continue; }
            if (s.front() == '[' && s.back() == ']') {
                section = s.substr(1, s.size() - 2); for (auto &c : section) c = (char)std::tolower((unsigned char)c);
                if (section != "master" && section != "echo" && section != "reverb" && section != "tracks" && section != "dna") return fail("unknown section [" + section + "]");
                continue;
            }
            if (section == "tracks") {
                std::string e; auto parts = shlexSplit(s, &e);
                if (!e.empty()) return fail(e);
                if (parts.size() < 3) return fail("a track is: NAME SOURCE PRESET [key=value ...]");
                SongTrack t; t.name = parts[0]; t.src = parts[1];
                if (parts[2].rfind("dna:", 0) == 0) t.dna = parts[2].substr(4); else t.preset = parts[2];
                for (size_t k = 3; k < parts.size(); k++) {
                    const std::string &kv = parts[k];
                    if (kv == "mute") { t.mute = true; continue; }
                    if (kv == "solo") { t.solo = true; continue; }
                    const size_t eq = kv.find('=');
                    if (eq == std::string::npos) return fail("\"" + kv + "\": expected key=value, mute or solo");
                    const std::string key = kv.substr(0, eq); const double v = std::atof(kv.c_str() + eq + 1);
                    if (key == "vol") t.vol = v; else if (key == "pan") t.pan = v; else if (key == "echo") t.echo = v; else if (key == "verb") t.verb = v;
                    else if (key == "vel") t.vel = v; else if (key == "width") t.width = v; else if (key == "hp") t.hp = v; else if (key == "lp") t.lp = v;
                    else if (key == "tune") t.tune = v; else if (key == "lufs") { t.lufs = v; t.hasLufs = true; }
                    else if (key == "tr" || key == "transpose") t.tr = std::atoi(kv.c_str() + eq + 1);
                    else return fail("unknown track key \"" + key + "\"");
                }
                Source sc; if (!sc.parse(t.src)) return fail("source \"" + t.src + "\": chN, trN joined by +, or all");
                tracks.push_back(t);
                continue;
            }
            if (section == "dna") {
                const size_t a = s.find('"'), b = a == std::string::npos ? a : s.find('"', a + 1), eq = b == std::string::npos ? b : s.find('=', b);
                if (eq == std::string::npos) return fail("[dna] lines are: \"pack:Name\" = DNA");
                pinned.push_back({s.substr(a + 1, b - a - 1), trim(s.substr(eq + 1))});
                continue;
            }
            size_t i = 0; while (i < s.size() && (std::isalnum((unsigned char)s[i]) || s[i] == '_' || s[i] == '-')) i++;
            size_t j = i; while (j < s.size() && (s[j] == ' ' || s[j] == '\t')) j++;
            if (i == 0 || j >= s.size() || (s[j] != '=' && s[j] != ':')) return fail("expected \"key = value\"");
            std::string k = s.substr(0, i); for (auto &c : k) c = (char)std::tolower((unsigned char)c);
            std::string v = trim(s.substr(j + 1));
            if (section.empty()) {
                bool had = false;
                for (auto &m : meta) if (m.first == k && (k == "credit" || k == "note")) { m.second += "\n" + v; had = true; }
                if (!had) set(k, v);
            } else sec[section][k] = v;
            if (q == text.size()) break;
        }
        if (get("title").empty()) return fail("missing \"title =\"");
        return true;
    }
    std::string write() const   // the same format back (comments are not kept)
    {
        std::string o;
        for (const auto &m : meta) {
            size_t p = 0; const std::string &v = m.second;
            do { size_t q = v.find('\n', p); if (q == std::string::npos) q = v.size(); o += m.first + " = " + v.substr(p, q - p) + "\n"; p = q + 1; } while (p <= v.size() && v.find('\n', p - 1) != std::string::npos && p < v.size());
        }
        for (const char *s : {"master", "echo", "reverb"}) {
            auto it = sec.find(s); if (it == sec.end() || it->second.empty()) continue;
            o += std::string("\n[") + s + "]\n";
            for (const auto &kv : it->second) o += kv.first + " = " + kv.second + "\n";
        }
        o += "\n[tracks]\n";
        auto quote = [](const std::string &x) { if (x.find_first_of(" \t#\"'") == std::string::npos && !x.empty()) return x; std::string r = "\""; for (char c : x) { if (c == '"' || c == '\\') r += '\\'; r += c; } return r + "\""; };
        auto num = [](double v) { char b[32]; std::snprintf(b, sizeof b, "%g", v); return std::string(b); };
        for (const auto &t : tracks) {
            o += quote(t.name) + " " + t.src + " " + (t.dna.empty() ? quote(t.preset) : "'dna:" + t.dna + "'");
            if (t.vol) o += " vol=" + num(t.vol);
            if (t.pan) o += " pan=" + num(t.pan);
            if (t.echo) o += " echo=" + num(t.echo);
            if (t.verb) o += " verb=" + num(t.verb);
            if (t.tr) o += " tr=" + std::to_string(t.tr);
            if (t.tune) o += " tune=" + num(t.tune);
            if (t.vel != 1) o += " vel=" + num(t.vel);
            if (t.hp) o += " hp=" + num(t.hp);
            if (t.lp) o += " lp=" + num(t.lp);
            if (t.width != 1) o += " width=" + num(t.width);
            if (t.hasLufs) o += " lufs=" + num(t.lufs);
            if (t.mute) o += " mute";
            if (t.solo) o += " solo";
            o += "\n";
        }
        if (!pinned.empty()) { o += "\n[dna]\n"; for (const auto &p : pinned) o += "\"" + p.first + "\" = " + p.second + "\n"; }
        return o;
    }
};

// presets of the machine's pack discs: pack id -> (name or Category/Name -> DNA)
inline std::map<std::string, std::map<std::string, std::string>> loadPresets(const std::string &machine)
{
    std::map<std::string, std::map<std::string, std::string>> P;
    std::ifstream in(machine + "/packs/PACKS.TSV"); std::string l;
    while (std::getline(in, l)) {
        if (!l.empty() && l.back() == '\r') l.pop_back();
        const size_t a = l.find('\t'); if (a == std::string::npos) continue;
        const size_t b = l.find('\t', a + 1);
        const std::string dir = l.substr(0, a), id = l.substr(a + 1, b == std::string::npos ? std::string::npos : b - a - 1);
        std::ifstream t(machine + "/packs/" + dir + "/PRESETS.TSV"); std::string r;
        auto &m = P[id];
        while (std::getline(t, r)) {
            if (!r.empty() && r.back() == '\r') r.pop_back();
            if (r.empty() || r[0] == '#') continue;
            std::vector<std::string> c; size_t p = 0;
            while (true) { size_t q = r.find('\t', p); c.push_back(r.substr(p, q == std::string::npos ? std::string::npos : q - p)); if (q == std::string::npos) break; p = q + 1; }
            if (c.size() >= 3) { m.emplace(c[1], c[2]); m.emplace(c[0] + "/" + c[1], c[2]); }
        }
    }
    return P;
}
// a track's DNA and its label (songrender.py resolve): the DNA as given, the pinned DNA, or the pack's preset
inline bool resolveTrack(const SongText &s, const SongTrack &t, const std::map<std::string, std::map<std::string, std::string>> &P,
                         std::string &dna, std::string &label, std::string &err)
{
    if (!t.dna.empty()) { dna = t.dna; label = "(DNA)"; return true; }
    std::string pk = s.get("pack"), name = t.preset;
    const size_t c = name.find(':'); if (c != std::string::npos) { pk = name.substr(0, c); name = name.substr(c + 1); }
    for (const auto &p : s.pinned) if (p.first == pk + ":" + name) { dna = p.second; label = p.first; return true; }
    pk = b16pack::packIdNow(pk);   // (a renamed pack, and its renamed presets: old songs keep playing)
    auto it = P.find(pk);
    if (it == P.end()) { err = "no pack \"" + pk + "\""; return false; }
    auto jt = it->second.find(name);
    if (jt == it->second.end()) { name = b16pack::presetNameNow(pk, name); jt = it->second.find(name); }
    if (jt == it->second.end()) { err = "track " + t.name + ": no preset \"" + name + "\" in " + pk; return false; }
    dna = jt->second; label = pk + ":" + name; return true;
}
inline int bendRangeOf(const std::string &dna)   // the DNA's B (2 by default): `;...B<n>` in the globals
{
    const size_t g = dna.find(';'); if (g == std::string::npos) return 2;
    for (size_t i = g; i + 1 < dna.size(); i++) if (dna[i] == 'B' && std::isdigit((unsigned char)dna[i + 1])) return std::max(1, std::atoi(dna.c_str() + i + 1));
    return 2;
}


// songrender plan(): each track's DNA and events, the song's tempo, tail and length. render311 is given the tempo
// as "%.6f" and the tail as "%g" on its command line, so the engines get those values (the stems stay identical).
struct PlanTrack { const SongTrack *t = nullptr; std::string dna, label; std::vector<MidiEv> ev; int notes = 0; };
struct SongPlan { double bpm = 120, engineBpm = 120, tail = 4, engineTail = 4, lengthSec = 0; std::vector<PlanTrack> tracks; };
inline bool planSong(const SongText &s, const Smf &smf, const std::map<std::string, std::map<std::string, std::string>> &P, SongPlan &out,
                     std::string &err)
{
    out = SongPlan();
    const std::string b = s.get("bpm"), t = s.get("tail");
    out.bpm = b.empty() ? smf.firstTempoBpm() : std::atof(b.c_str());
    out.tail = t.empty() ? 4.0 : std::atof(t.c_str());
    char buf[64];
    std::snprintf(buf, sizeof buf, "%.6f", out.bpm); out.engineBpm = std::atof(buf);
    std::snprintf(buf, sizeof buf, "%g", out.tail); out.engineTail = std::atof(buf);
    out.lengthSec = smf.seconds(smf.lastTick()) + out.tail;
    for (const auto &tr : s.tracks) {
        PlanTrack pt; pt.t = &tr;
        if (!resolveTrack(s, tr, P, pt.dna, pt.label, err)) return false;
        const int rng = bendRangeOf(pt.dna);
        if (std::fabs(tr.tune) > rng * 100) { err = "track " + tr.name + ": tune is past the bend range"; return false; }
        Source src; src.parse(tr.src);
        pt.ev = extractTrack(smf, src, tr.tr, tr.vel, tr.tune, rng, &pt.notes);
        if (!pt.notes) { err = "track " + tr.name + " (" + tr.src + ") has no notes"; return false; }
        out.tracks.push_back(std::move(pt));
    }
    return true;
}

}  // namespace b16song

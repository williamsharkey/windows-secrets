// SNDWAVE2000: the Song tab's host side (design/SONG-TAB.md). The song (the .song text and its MIDI file), the
// render (one engine per track on worker threads, render311's loop), the stems kept between renders, the mix
// (SongMix.h) and its playback through the plugin's output. Windows shows it and edits it with `song ...` lines.
//
// Windows -> host                                  host -> Windows
//   song get                                         song clear
//   song set <i> <key> <value>                       song meta <title>|<info>|<loudness>|<ceiling>|<engines>
//     (name, src, preset pack:Name, dna, tr, tune    song trk <i> <name>|<src>|<preset>|<tr>|<tune>|<vol10>|<pan>|
//      cents, vol10 tenths of a dB, pan, echo %,                <echo>|<verb>|<mute>|<solo>|<notes>|<lo>|<hi>
//      verb %, mute, solo)                           song end (the rows are in) | song status <text>
//   song master <loudness|ceiling> <value>           song pos <ms> <length ms> <playing>
//   song title <text> | song add | song del <i>
//   song render | song stop | song play <ms>
//   song import | song open | song save | song export | song engines <n>
#pragma once
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <functional>
#include <mutex>
#include <thread>
#include "SongMix.h"
#include "tuning_gen.h"
#include "../../basilisk-synth/core/userstore.h"
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/resource.h>
#include <unistd.h>
#if defined(__linux__)
#include <sys/syscall.h>
#endif
#endif

namespace b16song {

inline uint64_t fnv1a64(const std::string &s) { uint64_t h = 0xcbf29ce484222325ull; for (unsigned char c : s) { h ^= c; h *= 0x100000001b3ull; } return h; }
// a preset's measured tuning (cents to apply; tools/make_tuning311.py), 0 when it was not measured or is in tune
inline int measuredTune(const std::string &dna)
{
    const uint64_t h = fnv1a64(dna); unsigned lo = 0, hi = kTuningCount;
    while (lo < hi) { const unsigned m = (lo + hi) / 2; if (kTuning[m].dna < h) lo = m + 1; else hi = m; }
    return lo < kTuningCount && kTuning[lo].dna == h ? kTuning[lo].cents : 0;
}

inline void lowerThreadPriority()   // the engines give way to the host (and to the instance's own Windows)
{
#ifdef _WIN32
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_BELOW_NORMAL);
#elif defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
#elif defined(__linux__)
    setpriority(PRIO_PROCESS, (id_t)syscall(SYS_gettid), 10);
#endif
}

// ---- .sng: a zip (stored) holding song.song and song.mid
namespace sngzip {
inline uint32_t crc(const std::vector<uint8_t> &d) { return bsynth::crc32(d.data(), d.size()); }
inline std::vector<uint8_t> write(const std::vector<std::pair<std::string, std::vector<uint8_t>>> &files)
{
    std::vector<uint8_t> o, cd;
    auto u16 = [](std::vector<uint8_t> &v, uint32_t x) { v.push_back((uint8_t)x); v.push_back((uint8_t)(x >> 8)); };
    auto u32 = [&](std::vector<uint8_t> &v, uint32_t x) { u16(v, x & 0xFFFF); u16(v, x >> 16); };
    for (const auto &f : files) {
        const uint32_t off = (uint32_t)o.size(), c = crc(f.second), n = (uint32_t)f.second.size();
        u32(o, 0x04034b50); u16(o, 20); u16(o, 0); u16(o, 0); u16(o, 0); u16(o, 0x21); u32(o, c); u32(o, n); u32(o, n);
        u16(o, (uint32_t)f.first.size()); u16(o, 0); o.insert(o.end(), f.first.begin(), f.first.end()); o.insert(o.end(), f.second.begin(), f.second.end());
        u32(cd, 0x02014b50); u16(cd, 20); u16(cd, 20); u16(cd, 0); u16(cd, 0); u16(cd, 0); u16(cd, 0x21); u32(cd, c); u32(cd, n); u32(cd, n);
        u16(cd, (uint32_t)f.first.size()); u16(cd, 0); u16(cd, 0); u16(cd, 0); u16(cd, 0); u32(cd, 0); u32(cd, off);
        cd.insert(cd.end(), f.first.begin(), f.first.end());
    }
    const uint32_t cdo = (uint32_t)o.size(); o.insert(o.end(), cd.begin(), cd.end());
    u32(o, 0x06054b50); u16(o, 0); u16(o, 0); u16(o, (uint32_t)files.size()); u16(o, (uint32_t)files.size()); u32(o, (uint32_t)cd.size()); u32(o, cdo); u16(o, 0);
    return o;
}
inline bool read(const std::vector<uint8_t> &z, std::map<std::string, std::vector<uint8_t>> &out)   // stored entries (as written here)
{
    auto r16 = [&](size_t p) { return (uint32_t)(z[p] | z[p + 1] << 8); };
    auto r32 = [&](size_t p) { return r16(p) | r16(p + 2) << 16; };
    size_t e = z.size() >= 22 ? z.size() - 22 : 0;
    for (; e > 0 && r32(e) != 0x06054b50; e--) {}
    if (z.size() < 22 || r32(e) != 0x06054b50) return false;
    size_t p = r32(e + 16); const uint32_t n = r16(e + 10);
    for (uint32_t i = 0; i < n && p + 46 <= z.size() && r32(p) == 0x02014b50; i++) {
        const uint32_t meth = r16(p + 10), csz = r32(p + 20), usz = r32(p + 24), nl = r16(p + 28), xl = r16(p + 30), cl = r16(p + 32), lo = r32(p + 42);
        const std::string name(z.begin() + (long)p + 46, z.begin() + (long)std::min(z.size(), p + 46 + nl));
        p += 46 + nl + xl + cl;
        if (lo + 30 > z.size()) return false;
        const size_t d = lo + 30 + r16(lo + 26) + r16(lo + 28);
        if (d + csz > z.size()) return false;
        std::vector<uint8_t> raw(z.begin() + (long)d, z.begin() + (long)(d + csz)), v;
        if (meth == 0) v = raw;
        else continue;
        (void)usz;
        out[name] = v;
    }
    return true;
}
}  // namespace sngzip

class Session {
public:
    // set by the plugin
    std::string machine, core, userDir, tmpDir;
    std::function<void(const std::string &)> send;   // a line to Windows

    Session()
    {
        const unsigned hc = std::thread::hardware_concurrency();
        engines_ = (int)std::max(1u, std::min(4u, hc > 2 ? hc - 2 : 1u));
        if (const char *e = std::getenv("BASILISK16_SONG_ENGINES")) if (std::atoi(e) > 0) engines_ = std::min(8, std::atoi(e));   // (tests)
    }
    ~Session() { cancel_ = true; if (th_.joinable()) th_.join(); for (auto &s : stems_) std::remove(s.second.c_str()); }

    // ---- the state lines (design/SONG-TAB.md 5)
    bool empty() const { std::lock_guard<std::mutex> l(m_); return song_.tracks.empty() && midi_.empty(); }
    void stateLines(std::map<std::string, std::string> &extra) const
    {
        std::lock_guard<std::mutex> l(m_);
        if (song_.tracks.empty() && midi_.empty()) return;
        const std::string t = song_.write();
        extra["song"] = "1";
        extra["songtext"] = bsynth::base64(t.data(), t.size());
        if (!midi_.empty()) extra["songmidi"] = bsynth::base64(midi_.data(), midi_.size());
        if (!mixKey_.empty()) extra["songmix"] = mixKey_;
    }
    void loadState(const std::map<std::string, std::string> &extra)
    {
        stop();
        std::lock_guard<std::mutex> l(m_);
        song_ = SongText(); midi_.clear(); smf_ = Smf(); mix_.clear(); mixKey_.clear(); playPos_ = 0;
        auto it = extra.find("songtext");
        if (it != extra.end()) { std::vector<uint8_t> b; std::string err; if (bsynth::unbase64(it->second, b)) song_.parse(std::string(b.begin(), b.end()), &err); }
        it = extra.find("songmidi");
        if (it != extra.end() && bsynth::unbase64(it->second, midi_)) { std::string err; if (!smf_.parse(midi_, &err)) midi_.clear(); }
        it = extra.find("songmix");
        if (it != extra.end()) wantKey_ = it->second;
        dirty_ = true;
    }

    // ---- files
    std::string loadFile(const std::string &path, const std::vector<uint8_t> &bytes)   // .mid, .song (its MIDI beside it) or .sng; "" or an error
    {
        std::string ext = path.size() > 4 ? path.substr(path.size() - 4) : ""; for (auto &c : ext) c = (char)std::tolower((unsigned char)c);
        std::string err;
        if (bytes.size() >= 4 && std::memcmp(bytes.data(), "MThd", 4) == 0) return importMidi(bytes, path);
        std::string text; std::vector<uint8_t> mid;
        if (bytes.size() >= 4 && std::memcmp(bytes.data(), "PK\3\4", 4) == 0) {
            std::map<std::string, std::vector<uint8_t>> f;
            if (!sngzip::read(bytes, f) || !f.count("song.song")) return "not a song file";
            text.assign(f["song.song"].begin(), f["song.song"].end());
            if (f.count("song.mid")) mid = f["song.mid"];
        } else {
            text.assign(bytes.begin(), bytes.end());
            SongText probe; if (!probe.parse(text, &err)) return err;
            const size_t sl = path.find_last_of("/\\");
            std::ifstream in((sl == std::string::npos ? std::string() : path.substr(0, sl + 1)) + probe.get("midi"), std::ios::binary);
            mid.assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
            if (mid.empty()) return "the song's MIDI file (" + probe.get("midi") + ") is not beside it";
        }
        SongText s; Smf smf;
        if (!s.parse(text, &err)) return err;
        if (!mid.empty() && !smf.parse(mid, &err)) return err;
        stop();
        std::lock_guard<std::mutex> l(m_);
        song_ = s; midi_ = mid; smf_ = smf; mix_.clear(); mixKey_.clear(); playPos_ = 0;
        song_.set("midi", "song.mid");
        dirty_ = true;
        return "";
    }
    std::vector<uint8_t> sngBytes() const
    {
        std::lock_guard<std::mutex> l(m_);
        SongText s = song_; s.set("midi", "song.mid");
        const std::string t = s.write();
        return sngzip::write({{"song.song", std::vector<uint8_t>(t.begin(), t.end())}, {"song.mid", midi_}});
    }
    std::string fileStem() const
    {
        std::lock_guard<std::mutex> l(m_);
        std::string t = song_.get("title", "song"), o;
        for (char c : t) o += (std::isalnum((unsigned char)c) || c == '-' || c == '_') ? c : (c == ' ' ? '-' : '\0');
        o.erase(std::remove(o.begin(), o.end(), '\0'), o.end());
        return o.empty() ? "song" : o;
    }
    bool mixWav(std::vector<uint8_t> &out) const   // the mix as songrender writes it (24-bit)
    {
        std::lock_guard<std::mutex> l(m_);
        if (mix_.empty()) return false;
        const uint32_t data = (uint32_t)(mix_.size() * 3);
        out.clear(); out.reserve(44 + data);
        auto u32 = [&](uint32_t v) { for (int k = 0; k < 4; k++) out.push_back((uint8_t)(v >> (8 * k))); };
        auto u16 = [&](uint16_t v) { out.push_back((uint8_t)v); out.push_back((uint8_t)(v >> 8)); };
        out.insert(out.end(), {'R', 'I', 'F', 'F'}); u32(36 + data); out.insert(out.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
        u32(16); u16(1); u16(2); u32(48000); u32(48000 * 6); u16(6); u16(24); out.insert(out.end(), {'d', 'a', 't', 'a'}); u32(data);
        for (int32_t s : mix_) { out.push_back((uint8_t)s); out.push_back((uint8_t)(s >> 8)); out.push_back((uint8_t)(s >> 16)); }
        return true;
    }

    // ---- Windows' lines; returns false if the line is not the Song tab's. `fileReq` is set for a dialog: 6 import
    // MIDI or open a song, 7 save the song, 8 export the mix
    bool line(const std::string &ln, int &fileReq, std::string &defName)
    {
        if (ln.rfind("song ", 0) != 0) return false;
        const std::string r = ln.substr(5);
        auto arg = [&](const char *k) { const size_t n = std::strlen(k); return r.compare(0, n, k) == 0 && (r.size() == n || r[n] == ' '); };
        auto after = [&](const char *k) { const size_t n = std::strlen(k); return r.size() > n + 1 ? r.substr(n + 1) : std::string(); };
        if (arg("get")) { sendAll(); return true; }
        if (arg("import") || arg("open")) { fileReq = 6; return true; }
        if (arg("save")) { fileReq = 7; defName = fileStem() + ".sng"; return true; }
        if (arg("export")) { bool none; { std::lock_guard<std::mutex> l(m_); none = mix_.empty(); } if (none) { status("Render the song first."); return true; } fileReq = 8; defName = fileStem() + ".wav"; return true; }
        if (arg("render")) { render(); return true; }
        if (arg("stop")) { if (busy_) { cancel_ = true; status("Stopping the render..."); } playing_ = false; sendPos(); return true; }
        if (arg("play")) { play(std::atof(after("play").c_str()) / 1000.0); return true; }
        if (arg("engines")) { engines_ = std::max(1, std::min(8, std::atoi(after("engines").c_str()))); return true; }
        if (busy_) { status("Rendering: stop the render to change the song."); sendAll(); return true; }
        if (arg("notes")) { std::istringstream in(after("notes")); int i = 0; long first = 0; in >> i >> first; sendNotes(i, first); return true; }
        if (arg("noteadd") || arg("noteset") || arg("notedel")) { noteEdit(r); return true; }
        {
            std::lock_guard<std::mutex> l(m_);
            if (arg("title")) song_.set("title", after("title"));
            else if (arg("add")) {
                SongTrack t; t.name = "Track " + std::to_string(song_.tracks.size() + 1);
                t.src = "ch" + std::to_string(std::min<size_t>(16, song_.tracks.size() + 1)); t.dna = defaultDna;
                song_.tracks.push_back(t);
            } else if (arg("del")) {
                const int i = std::atoi(after("del").c_str());
                if (i >= 0 && i < (int)song_.tracks.size()) song_.tracks.erase(song_.tracks.begin() + i);
            } else if (arg("master")) {
                const std::string kv = after("master"); const size_t sp = kv.find(' ');
                if (sp != std::string::npos) song_.sec["master"][kv.substr(0, sp)] = kv.substr(sp + 1);
            } else if (arg("set")) {
                std::istringstream in(after("set")); int i = -1; std::string k, v; in >> i >> k; std::getline(in, v); v = SongText::trim(v);
                if (i < 0 || i >= (int)song_.tracks.size()) return true;
                SongTrack &t = song_.tracks[i]; const double x = std::atof(v.c_str());
                if (k == "name") t.name = v.empty() ? t.name : v;
                else if (k == "src") { Source s; if (s.parse(v)) t.src = v; }
                else if (k == "preset") {   // a pack preset: its measured tuning comes with it (the Tune column; the user may change it)
                    t.dna.clear(); t.preset = v;
                    std::string dna, label, err;
                    if (resolveTrack(song_, t, loadPresets(machine), dna, label, err)) t.tune = measuredTune(dna);
                }
                else if (k == "dna") { t.preset.clear(); t.dna = v; }
                else if (k == "usedna") { t.preset.clear(); t.dna = defaultDna; }   // the instance's sound
                else if (k == "tr") t.tr = std::max(-48, std::min(48, std::atoi(v.c_str())));
                else if (k == "tune") t.tune = std::max(-200.0, std::min(200.0, x));
                else if (k == "vol10") t.vol = std::max(-60.0, std::min(12.0, x / 10));
                else if (k == "pan") t.pan = std::max(-100.0, std::min(100.0, x));
                else if (k == "echo") t.echo = std::max(0.0, std::min(1.0, x / 100));
                else if (k == "verb") t.verb = std::max(0.0, std::min(1.0, x / 100));
                else if (k == "mute") t.mute = x != 0;
                else if (k == "solo") t.solo = x != 0;
            }
        }
        sendAll();
        return true;
    }

    // ---- the plugin's output: the mix, at the host's rate (linear), added to the instance's own sound
    void play(double sec)
    {
        std::lock_guard<std::mutex> l(m_);
        if (mix_.empty()) { statusLocked(wantKey_.empty() ? "Render the song to hear it." : "The render is not in this project: Render to hear it again."); return; }
        playPos_ = std::max(0.0, std::min(sec, (double)(mix_.size() / 2) / 48000.0)) * 48000.0;
        playing_ = true;
        sendPosLocked();
    }
    void process(float *L, float *R, uint32_t frames, double sr)
    {
        if (!playing_) return;
        std::unique_lock<std::mutex> l(m_, std::try_to_lock);
        if (!l.owns_lock()) return;
        const double step = 48000.0 / sr; const size_t n = mix_.size() / 2;
        double p = playPos_;
        for (uint32_t i = 0; i < frames; i++, p += step) {
            const size_t k = (size_t)p; if (k + 1 >= n) { playing_ = false; break; }
            const float f = (float)(p - (double)k);
            const float s = 1.f / 8388607.f;
            L[i] += ((float)mix_[2 * k] + (float)(mix_[2 * k + 2] - mix_[2 * k]) * f) * s;
            R[i] += ((float)mix_[2 * k + 1] + (float)(mix_[2 * k + 3] - mix_[2 * k + 1]) * f) * s;
        }
        playPos_ = p;
    }
    // the worker's housekeeping: rows to Windows after a change, the playhead now and then
    void poll()
    {
        if (dirty_.exchange(false)) sendAll();
        const double t = nowSec();
        if ((playing_ || wasPlaying_) && t - lastPos_ > 0.25) { lastPos_ = t; wasPlaying_ = playing_.load(); sendPos(); }
        std::string st; { std::lock_guard<std::mutex> l(m_); st.swap(pendStatus_); }
        if (!st.empty()) status(st);
    }
    void setDefaultDna(const std::string &d) { std::lock_guard<std::mutex> l(m_); defaultDna = d; }
    void shutdown() { stop(); send = nullptr; }
    void loadLater(const std::string &path, std::vector<uint8_t> bytes) { const std::string e = loadFile(path, bytes); if (!e.empty()) status("Not loaded: " + e + "."); }

private:
    // ---- the Notes... event list: a track's notes (its source's note-ons paired with their note-offs), paged
    struct NoteRef { size_t ti, on, off; uint64_t tick, dur; int key, vel, ch; };
    std::vector<NoteRef> notesOf(const SongTrack &t) const   // (m_ held)
    {
        std::vector<NoteRef> out; Source src; src.parse(t.src);
        for (size_t ti = 0; ti < smf_.tracks.size(); ti++) {
            const auto &ev = smf_.tracks[ti];
            std::map<int, std::vector<size_t>> open;   // ch*128+key -> note-ons waiting, first in first out
            for (size_t k = 0; k < ev.size(); k++) {
                const auto &e = ev[k]; if (e.b.size() < 3 || e.b[0] >= 0xF0) continue;
                const int st = e.b[0] & 0xF0, ch = e.b[0] & 15;
                if (!src.match((int)ti, ch)) continue;
                const int id = ch * 128 + e.b[1];
                if (st == 0x90 && e.b[2] > 0) open[id].push_back(k);
                else if ((st == 0x80 || st == 0x90) && !open[id].empty()) {
                    const size_t on = open[id].front(); open[id].erase(open[id].begin());
                    out.push_back({ti, on, k, ev[on].tick, e.tick - ev[on].tick, ev[on].b[1], ev[on].b[2], ch});
                }
            }
        }
        std::stable_sort(out.begin(), out.end(), [](const NoteRef &a, const NoteRef &b) { return a.tick != b.tick ? a.tick < b.tick : a.key < b.key; });
        return out;
    }
    void sendNotes(int i, long first)
    {
        if (!send) return;
        std::vector<std::string> out;
        {
            std::lock_guard<std::mutex> l(m_);
            if (i < 0 || i >= (int)song_.tracks.size()) return;
            const auto n = notesOf(song_.tracks[i]);
            const long total = (long)n.size(), page = 150;
            first = std::max(0L, std::min(first, std::max(0L, total - 1)));
            char b[120];
            std::snprintf(b, sizeof b, "song notes %d %d %ld %ld", i, smf_.division, first, total); out.push_back(b);
            for (long k = first; k < std::min(total, first + page); k++) {
                std::snprintf(b, sizeof b, "song note %ld %llu|%d|%d|%llu", k, (unsigned long long)n[k].tick, n[k].key, n[k].vel, (unsigned long long)n[k].dur);
                out.push_back(b);
            }
            out.push_back("song notes end");
        }
        for (auto &x : out) send(x);
    }
    // noteadd <i> <tick> <key> <vel> <dur> | noteset <i> <k> <tick> <key> <vel> <dur> | notedel <i> <k>
    void noteEdit(const std::string &r)
    {
        std::istringstream in(r); std::string op; int i = -1; long k = -1; long long tick = 0, dur = 0; int key = 60, vel = 100;
        in >> op >> i;
        if (op != "noteadd") in >> k;
        if (op != "notedel") in >> tick >> key >> vel >> dur;
        long show = 0;
        {
            std::lock_guard<std::mutex> l(m_);
            if (i < 0 || i >= (int)song_.tracks.size()) return;
            if (midi_.empty()) {   // a song without a file yet: one of its own (120 bpm unless the song says)
                const std::string b = song_.get("bpm"); const double bpm = b.empty() ? 120.0 : std::atof(b.c_str());
                const uint32_t us = (uint32_t)std::lround(60e6 / std::max(1.0, bpm));
                smf_ = Smf(); smf_.division = 480; smf_.tracks = {{SmfEvent{0, {0xFF, 0x51, 0x03, (uint8_t)(us >> 16), (uint8_t)(us >> 8), (uint8_t)us}}}};
                song_.set("midi", "song.mid");
            }
            const SongTrack &t = song_.tracks[i];
            auto n = notesOf(t);
            if (op != "noteadd") {
                if (k < 0 || k >= (long)n.size()) return;
                auto &ev = smf_.tracks[n[k].ti];
                const size_t a = std::max(n[k].on, n[k].off), b = std::min(n[k].on, n[k].off);
                ev.erase(ev.begin() + (long)a); ev.erase(ev.begin() + (long)b);
                show = k;
            }
            if (op != "notedel") {
                key = std::max(0, std::min(127, key)); vel = std::max(1, std::min(127, vel)); tick = std::max(0LL, tick); dur = std::max(1LL, dur);
                Source src; src.parse(t.src);
                int ch = !src.chans.empty() ? src.chans[0] : (op == "noteset" ? n[k].ch : 0);
                size_t ti;
                if (op == "noteset") ti = n[k].ti;
                else if (!src.trks.empty()) { ti = (size_t)src.trks[0]; while (smf_.tracks.size() <= ti) smf_.tracks.push_back({}); }
                else {   // the first file track with this source's events, else a new one
                    ti = smf_.tracks.size();
                    for (size_t x = 0; x < smf_.tracks.size() && ti == smf_.tracks.size(); x++)
                        for (const auto &e : smf_.tracks[x]) if (e.b.size() >= 2 && e.b[0] < 0xF0 && src.match((int)x, e.b[0] & 15)) { ti = x; break; }
                    if (ti == smf_.tracks.size()) smf_.tracks.push_back({});
                }
                if (src.all && op == "noteadd") ch = 0;
                auto &ev = smf_.tracks[ti];
                ev.push_back(SmfEvent{(uint64_t)tick, {(uint8_t)(0x90 | ch), (uint8_t)key, (uint8_t)vel}});
                ev.push_back(SmfEvent{(uint64_t)(tick + dur), {(uint8_t)(0x80 | ch), (uint8_t)key, 0}});
                std::stable_sort(ev.begin(), ev.end(), [](const SmfEvent &a, const SmfEvent &b) { return a.tick < b.tick; });
                const auto n2 = notesOf(t);
                for (size_t q = 0; q < n2.size(); q++) if (n2[q].tick == (uint64_t)tick && n2[q].key == key) { show = (long)q; break; }
            }
            midi_ = smf_.write();
            std::string err; Smf re; if (re.parse(midi_, &err)) smf_ = re;
        }
        sendNotes(i, std::max(0L, show - 20));
        { char b[48]; std::snprintf(b, sizeof b, "song notesel %ld", show); if (send) send(b); }
        dirty_ = true;   // (the rows: their note counts and ranges)
    }
    mutable std::mutex m_;
    SongText song_; std::vector<uint8_t> midi_; Smf smf_;
    std::vector<int32_t> mix_; std::string mixKey_, wantKey_;   // the mix as its WAV holds it: 24-bit, rounded half to even
    std::map<std::string, std::string> stems_;   // stem key -> its file (24-bit, in the instance's temp folder)
    std::thread th_; std::atomic<bool> busy_{false}, cancel_{false}, playing_{false}, dirty_{false};
    bool wasPlaying_ = false; double lastPos_ = 0, playPos_ = 0;
    std::string pendStatus_;
    int engines_ = 2;
    std::string defaultDna = "ding#16;R120";   // a new track's sound: the instance's DNA

    void status(const std::string &s) { if (send) send("song status " + s); }
    void statusLocked(const std::string &s) { pendStatus_ = s; }
    void sendPos() { std::lock_guard<std::mutex> l(m_); sendPosLocked(); }
    void sendPosLocked()
    {
        if (!send) return;
        char b[80]; std::snprintf(b, sizeof b, "song pos %ld %ld %d", (long)(playPos_ / 48.0), (long)(mix_.size() / 96), playing_ ? 1 : 0);
        send(b);
    }
    std::string importMidi(const std::vector<uint8_t> &bytes, const std::string &path)
    {
        Smf smf; std::string err;
        if (!smf.parse(bytes, &err)) return err;
        SongText s;
        std::string nm = path; const size_t sl = nm.find_last_of("/\\"); if (sl != std::string::npos) nm = nm.substr(sl + 1);
        if (nm.size() > 4) nm.resize(nm.size() - 4);
        s.set("title", nm.empty() ? "Untitled" : nm); s.set("midi", "song.mid");
        for (int ch : smf.channels()) {   // a track per channel with notes, in the instance's sound until a preset is chosen
            Source src; src.parse("ch" + std::to_string(ch + 1)); int notes = 0;
            extractTrack(smf, src, 0, 1.0, 0, 2, &notes);
            if (!notes) continue;
            SongTrack t; t.name = ch == 9 ? "Drums" : "Ch " + std::to_string(ch + 1); t.src = "ch" + std::to_string(ch + 1); t.dna = defaultDna;
            s.tracks.push_back(t);
        }
        if (s.tracks.empty()) return "the MIDI file has no notes";
        stop();
        std::lock_guard<std::mutex> l(m_);
        song_ = s; midi_ = bytes; smf_ = smf; mix_.clear(); mixKey_.clear(); playPos_ = 0;
        dirty_ = true;
        return "";
    }
    void stop() { cancel_ = true; if (th_.joinable()) th_.join(); cancel_ = false; playing_ = false; }
    void sendAll()
    {
        if (!send) return;
        std::vector<std::string> out;
        {
            std::lock_guard<std::mutex> l(m_);
            const double bpm = song_.get("bpm").empty() ? smf_.firstTempoBpm() : std::atof(song_.get("bpm").c_str());
            const double len = midi_.empty() ? 0 : smf_.seconds(smf_.lastTick());
            auto ms = song_.sec.count("master") ? song_.sec.at("master") : std::map<std::string, std::string>();
            char b[400], info[120];
            if (midi_.empty()) std::snprintf(info, sizeof info, "No MIDI file: Import MIDI...");
            else std::snprintf(info, sizeof info, "%.1f bpm, %d:%02d, %zu tracks", bpm, (int)(len / 60), (int)len % 60, song_.tracks.size());
            std::snprintf(b, sizeof b, "song meta %s|%s|%s|%s|%d", song_.get("title", "Untitled").c_str(), info, ms.count("loudness") ? ms["loudness"].c_str() : "-16",
                          ms.count("ceiling") ? ms["ceiling"].c_str() : "-1", engines_);
            out.push_back("song clear"); out.push_back(b);
            const std::string pk = song_.get("pack");
            for (size_t i = 0; i < song_.tracks.size(); i++) {
                const SongTrack &t = song_.tracks[i];
                int notes = 0, lo = 127, hi = 0;
                if (!midi_.empty()) {
                    Source src; src.parse(t.src);
                    for (const auto &e : extractTrack(smf_, src, t.tr, 1.0, 0, 2, &notes)) if ((e.st & 0xF0) == 0x90 && e.b) { lo = std::min<int>(lo, e.a); hi = std::max<int>(hi, e.a); }
                }
                std::string pre = t.dna.empty() ? (t.preset.find(':') == std::string::npos && !pk.empty() ? pk + ":" + t.preset : t.preset) : "DNA " + t.dna.substr(0, 40);
                for (auto &c : pre) if (c == '|') c = '/';
                std::string nm = t.name; for (auto &c : nm) if (c == '|') c = '/';
                std::snprintf(b, sizeof b, "song trk %zu %s|%s|%s|%d|%ld|%ld|%ld|%ld|%ld|%d|%d|%d|%d|%d", i, nm.c_str(), t.src.c_str(), pre.c_str(), t.tr, std::lrint(t.tune),
                              std::lrint(t.vol * 10), std::lrint(t.pan), std::lrint(t.echo * 100), std::lrint(t.verb * 100), t.mute, t.solo, notes, notes ? lo : 0, notes ? hi : 0);
                out.push_back(b);
            }
            out.push_back("song end");
        }
        for (auto &l : out) send(l);
        sendPos();
    }

    static std::string stemKey(const std::string &dna, const SongPlan &p, const std::vector<MidiEv> &ev)
    {
        std::string k = dna + "\n" + std::to_string(p.engineTail) + "\n" + std::to_string(p.engineBpm) + "\n";
        for (const auto &e : ev) { char b[48]; std::snprintf(b, sizeof b, "%.17g %u %u %u\n", e.t, e.st, e.a, e.b); k += b; }
        return bsynth::sha1Hex(k.data(), k.size());
    }
    static bool saveStem(const std::string &path, const std::vector<float> &lr)   // 24-bit, as the mixer reads it
    {
        FILE *f = std::fopen(path.c_str(), "wb"); if (!f) return false;
        std::vector<uint8_t> b; b.reserve(lr.size() * 3);
        for (float x : lr) { const double v = x < -1 ? -1 : x > 1 ? 1 : x; const int32_t s = (int32_t)std::lround(v * 8388607.0); b.push_back((uint8_t)s); b.push_back((uint8_t)(s >> 8)); b.push_back((uint8_t)(s >> 16)); }
        const bool ok = std::fwrite(b.data(), 1, b.size(), f) == b.size();
        std::fclose(f); return ok;
    }
    static bool loadStem(const std::string &path, std::vector<float> &lr)   // back to floats that stemSample() takes to the same 24 bits
    {
        std::ifstream in(path, std::ios::binary); std::vector<uint8_t> b((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        if (b.empty() || b.size() % 3) return false;
        lr.resize(b.size() / 3);
        for (size_t i = 0; i < lr.size(); i++) { const int32_t s = (int32_t)((uint32_t)(b[3 * i] | b[3 * i + 1] << 8 | b[3 * i + 2] << 16) << 8) >> 8; lr[i] = (float)((double)s / 8388607.0); }
        return true;
    }

    void render()
    {
        if (busy_) return;
        if (th_.joinable()) th_.join();
        playing_ = false;
        busy_ = true; cancel_ = false;
        th_ = std::thread([this]() { lowerThreadPriority(); renderNow(); busy_ = false; });
    }
    void renderNow()
    {
        SongText song; Smf smf; std::string err;
        { std::lock_guard<std::mutex> l(m_); song = song_; smf = smf_; if (midi_.empty()) err = "Import a MIDI file first (Import MIDI...)."; }
        if (song.tracks.empty() && err.empty()) err = "The song has no tracks.";
        SongPlan plan;
        if (err.empty() && !planSong(song, smf, loadPresets(machine), plan, err)) err = "Cannot render: " + err;
        if (!err.empty()) { status(err); return; }
        const size_t N = plan.tracks.size();
        std::vector<std::string> keys(N);
        std::vector<size_t> todo;
        {
            std::lock_guard<std::mutex> l(m_);
            for (size_t i = 0; i < N; i++) { keys[i] = stemKey(plan.tracks[i].dna, plan, plan.tracks[i].ev); if (!stems_.count(keys[i])) todo.push_back(i); }
        }
        std::vector<double> prog(N, 0.0); std::mutex pm; double lastRep = 0;
        const double t0 = nowSec();
        std::vector<TrackJob> jobs;
        for (size_t i : todo) {
            TrackJob J; J.machine = machine; J.core = core; J.userDir = userDir; J.dna = plan.tracks[i].dna; J.ev = plan.tracks[i].ev;
            J.tail = plan.engineTail; J.bpm = plan.engineBpm; J.lookahead48 = 150 * 48;
            jobs.push_back(std::move(J));
        }
        auto progress = [&](size_t q, double f) {
            double sum = 0; bool rep = false;
            { std::lock_guard<std::mutex> l(pm); prog[q] = f; for (double v : prog) sum += v; const double t = nowSec(); if (t - lastRep > 0.5) { lastRep = t; rep = true; } }
            if (!rep) return;
            char b[120]; std::snprintf(b, sizeof b, "Rendering %zu of %zu tracks on %d engines: %d%%", todo.size(), N, std::min<int>(engines_, (int)todo.size()),
                                       (int)(100 * sum / (double)std::max<size_t>(1, todo.size())));
            status(b);
        };
        std::string firstErr;
        auto done = [&](size_t q, TrackOut &R) {
            const size_t i = todo[q];
            const std::string path = tmpDir + "/song-" + keys[i] + ".s24";
            if (!saveStem(path, R.lr)) { R.err = "cannot write a stem in " + tmpDir; return false; }
            std::lock_guard<std::mutex> l(m_); stems_[keys[i]] = path;
            return true;
        };
        const bool ok = renderStems(jobs, engines_, &cancel_, progress, done, firstErr, lowerThreadPriority);
        const bool failed = !ok && !cancel_;
        if (cancel_) { status("Render stopped."); return; }
        if (failed) { status("The render failed (" + firstErr + ")."); return; }
        status("Mixing...");
        const double t1 = nowSec();
        std::vector<std::vector<float>> st(N); std::vector<MixIn> mi;
        for (size_t i = 0; i < N; i++) {
            std::string p; { std::lock_guard<std::mutex> l(m_); p = stems_[keys[i]]; }
            if (!loadStem(p, st[i])) { status("A stem went missing: Render again."); std::lock_guard<std::mutex> l(m_); stems_.erase(keys[i]); return; }
            mi.push_back({plan.tracks[i].t, &st[i]});
        }
        MixStats ms;
        const std::vector<double> y = mixSong(song, plan.bpm, plan.lengthSec, mi, &ms, &cancel_);
        if (cancel_ || y.empty()) { status("Render stopped."); return; }
        std::string mk; { std::string t = song.write(); for (auto &k : keys) t += k; mk = bsynth::sha1Hex(t.data(), t.size()); }
        {
            std::lock_guard<std::mutex> l(m_);
            mix_.resize(y.size()); for (size_t k = 0; k < y.size(); k++) mix_[k] = (int32_t)std::lrint(std::clamp(y[k], -1.0, 1.0) * 8388607.0);
            mixKey_ = mk; wantKey_ = mk; playPos_ = 0;
        }
        char b[200];
        std::snprintf(b, sizeof b, "Rendered %d:%02d in %.0f s (%zu of %zu tracks new, mix %.0f s): %.1f LUFS, peak %.1f dBFS. Play, or Export...",
                      (int)(plan.lengthSec / 60), (int)plan.lengthSec % 60, nowSec() - t0, todo.size(), N, nowSec() - t1, ms.lufs, ms.peakDb);
        status(b);
        sendPos();
    }
};

}  // namespace b16song

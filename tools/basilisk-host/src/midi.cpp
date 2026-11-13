// BasiliskHost - MIDI (see midi.h)
#include "midi.h"
#include <windows.h>
#include <mmsystem.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <cstdio>
#include <fstream>
#include <map>

void finish_score(Score &s)
{
    std::stable_sort(s.msgs.begin(), s.msgs.end(), [](const MidiMsg &a, const MidiMsg &b) {
        if (a.t != b.t) return a.t < b.t;
        // at the same instant: note-offs before note-ons, controllers first
        auto rank = [](const MidiMsg &m) { int t = m.st & 0xF0; return (t == 0x80 || (t == 0x90 && m.d2 == 0)) ? 0 : t == 0x90 ? 2 : 1; };
        return rank(a) < rank(b);
    });
    s.length = s.msgs.empty() ? 0 : s.msgs.back().t;
    if (s.notes.empty()) {   // derive the notes from the messages
        std::map<int, std::pair<double, int>> on;
        for (auto &m : s.msgs) {
            int ty = m.st & 0xF0, key = (m.st & 15) * 128 + m.d1;
            if (ty == 0x90 && m.d2 > 0) on[key] = {m.t, m.d2};
            else if (ty == 0x80 || (ty == 0x90 && m.d2 == 0)) {
                auto it = on.find(key);
                if (it != on.end()) { s.notes.push_back({it->second.first, m.t - it->second.first, m.d1, it->second.second, "file"}); on.erase(it); }
            }
        }
        for (auto &kv : on) s.notes.push_back({kv.second.first, s.length - kv.second.first, kv.first % 128, kv.second.second, "file"});
        std::sort(s.notes.begin(), s.notes.end(), [](const NoteRec &a, const NoteRec &b) { return a.t < b.t; });
    }
    for (auto &n : s.notes) {
        int same = 0;
        for (auto &o : s.notes) if (std::fabs(o.t - n.t) < 0.02) same++;
        n.single = same == 1;
    }
}

static void add_note(Score &s, double t, int note, int vel, double dur, const char *sec)
{
    s.msgs.push_back({t, 0x90, (uint8_t)note, (uint8_t)vel});
    s.msgs.push_back({t + dur, 0x80, (uint8_t)note, 0});
    s.notes.push_back({t, dur, note, vel, sec});
}

Score test_pattern(const std::string &sections)
{
    Score s;
    auto has = [&](const char *k) { return sections == "all" || sections.find(k) != std::string::npos; };
    double t = 0;
    if (has("scale")) {   // C major scale, C4..C5, then C3 and C6 for the pitch range
        int sc[] = {60, 62, 64, 65, 67, 69, 71, 72, 48, 84};
        for (int k = 0; k < 10; k++) add_note(s, t + 0.6 * k, sc[k], 100, 0.4, "scale");
        t += 6.5;
    }
    if (has("chords")) {  // I IV V I triads
        int ch[4][3] = {{60, 64, 67}, {65, 69, 72}, {67, 71, 74}, {60, 64, 67}};
        for (int k = 0; k < 4; k++)
            for (int j = 0; j < 3; j++) add_note(s, t + 1.0 * k, ch[k][j], 96, 0.8, "chords");
        t += 4.5;
    }
    if (has("repeats")) { // the same note, 8 per second, then 16 per second
        for (int k = 0; k < 12; k++) add_note(s, t + 0.125 * k, 67, 100, 0.06, "repeats");
        t += 12 * 0.125 + 0.4;
        for (int k = 0; k < 12; k++) add_note(s, t + 0.0625 * k, 72, 100, 0.03, "repeats");
        t += 12 * 0.0625 + 0.8;
    }
    if (has("sustain")) { // short notes held by the pedal
        s.msgs.push_back({t, 0xB0, 64, 127});
        add_note(s, t + 0.1, 60, 100, 0.1, "sustain");
        add_note(s, t + 0.6, 64, 100, 0.1, "sustain");
        s.msgs.push_back({t + 1.4, 0xB0, 64, 0});
        t += 2.2;
    }
    if (has("bend")) {    // bend up, play, bend back, play (the plugins apply bend when a note starts)
        s.msgs.push_back({t, 0xE0, 0x7F, 0x7F});
        add_note(s, t + 0.1, 60, 100, 0.4, "bend");
        s.msgs.push_back({t + 0.8, 0xE0, 0x00, 0x40});
        add_note(s, t + 0.9, 60, 100, 0.4, "bend");
        t += 1.8;
    }
    finish_score(s);
    return s;
}

Score parse_score(const std::string &spec)
{
    Score s;
    size_t p = 0;
    while (p < spec.size()) {
        size_t q = spec.find(',', p);
        std::string it = spec.substr(p, q == std::string::npos ? std::string::npos : q - p);
        double t, dur;
        int note, vel;
        if (sscanf(it.c_str(), "%lf:%d:%d:%lf", &t, &note, &vel, &dur) == 4) add_note(s, t, note, vel, dur, "score");
        if (q == std::string::npos) break;
        p = q + 1;
    }
    finish_score(s);
    return s;
}

// ------------------------------------------------------------------ SMF
static uint32_t be32(const uint8_t *p) { return (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]; }
static uint16_t be16(const uint8_t *p) { return (uint16_t)((p[0] << 8) | p[1]); }

bool read_midi_file(const std::string &path, Score &out, std::string &err)
{
    std::ifstream f(path, std::ios::binary);
    if (!f) { err = "cannot open " + path; return false; }
    std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
    if (d.size() < 14 || memcmp(d.data(), "MThd", 4)) { err = "not a MIDI file"; return false; }
    int ntrk = be16(&d[10]), div = be16(&d[12]);
    if (div & 0x8000) { err = "SMPTE time division is not supported"; return false; }
    struct Raw { uint64_t tick; int order; MidiMsg m; bool tempo; uint32_t usq; };
    std::vector<Raw> raw;
    size_t p = 8 + be32(&d[4]);
    int order = 0;
    for (int tr = 0; tr < ntrk && p + 8 <= d.size(); tr++) {
        if (memcmp(&d[p], "MTrk", 4)) { err = "bad track chunk"; return false; }
        size_t len = be32(&d[p + 4]), q = p + 8, end = std::min(d.size(), q + len);
        uint64_t tick = 0;
        uint8_t run = 0;
        auto vlq = [&]() { uint32_t v = 0; while (q < end) { uint8_t b = d[q++]; v = (v << 7) | (b & 0x7F); if (!(b & 0x80)) break; } return v; };
        while (q < end) {
            tick += vlq();
            if (q >= end) break;
            uint8_t st = d[q];
            if (st == 0xFF) {
                q++;
                uint8_t type = d[q++];
                uint32_t l = vlq();
                if (type == 0x51 && l == 3) raw.push_back({tick, order++, {}, true, (uint32_t)((d[q] << 16) | (d[q + 1] << 8) | d[q + 2])});
                q += l;
                if (type == 0x2F) break;
                continue;
            }
            if (st == 0xF0 || st == 0xF7) { q++; q += vlq(); continue; }
            if (st & 0x80) { run = st; q++; }
            else st = run;
            int nd = ((st & 0xF0) == 0xC0 || (st & 0xF0) == 0xD0) ? 1 : 2;
            MidiMsg m;
            m.st = st;
            m.d1 = q < end ? d[q] : 0;
            m.d2 = nd == 2 && q + 1 < end ? d[q + 1] : 0;
            q += nd;
            raw.push_back({tick, order++, m, false, 0});
        }
        p = 8 + p + len;
    }
    std::stable_sort(raw.begin(), raw.end(), [](const Raw &a, const Raw &b) { return a.tick < b.tick; });
    double usq = 500000, t = 0;
    uint64_t last = 0;
    for (auto &r : raw) {
        t += (double)(r.tick - last) * usq / 1e6 / div;
        last = r.tick;
        if (r.tempo) { usq = r.usq; continue; }
        MidiMsg m = r.m;
        m.t = t;
        out.msgs.push_back(m);
    }
    finish_score(out);
    return true;
}

bool write_midi_file(const std::string &path, const Score &s)
{
    const int div = 960;   // 120 bpm: 1920 ticks per second
    std::vector<uint8_t> trk;
    auto vlq = [&](uint32_t v) {
        uint8_t b[5];
        int n = 0;
        b[n++] = v & 0x7F;
        while (v >>= 7) b[n++] = (v & 0x7F) | 0x80;
        while (n) trk.push_back(b[--n]);
    };
    vlq(0);
    trk.insert(trk.end(), {0xFF, 0x51, 3, 0x07, 0xA1, 0x20});   // 500000 us per quarter
    uint64_t last = 0;
    for (auto &m : s.msgs) {
        uint64_t tick = (uint64_t)std::llround(m.t * 1920);
        vlq((uint32_t)(tick - last));
        last = tick;
        trk.push_back(m.st);
        trk.push_back(m.d1);
        if ((m.st & 0xF0) != 0xC0 && (m.st & 0xF0) != 0xD0) trk.push_back(m.d2);
    }
    vlq(0);
    trk.insert(trk.end(), {0xFF, 0x2F, 0});
    std::ofstream f(path, std::ios::binary);
    auto w32 = [&](uint32_t v) { uint8_t b[4] = {(uint8_t)(v >> 24), (uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v}; f.write((char *)b, 4); };
    auto w16 = [&](uint16_t v) { uint8_t b[2] = {(uint8_t)(v >> 8), (uint8_t)v}; f.write((char *)b, 2); };
    f.write("MThd", 4); w32(6); w16(0); w16(1); w16(div);
    f.write("MTrk", 4); w32((uint32_t)trk.size());
    f.write((char *)trk.data(), trk.size());
    return (bool)f;
}

// ------------------------------------------------------------------ winmm input
std::vector<std::string> midi_in_devices()
{
    std::vector<std::string> v;
    UINT n = midiInGetNumDevs();
    for (UINT i = 0; i < n; i++) {
        MIDIINCAPSW c = {};
        if (midiInGetDevCapsW(i, &c, sizeof c) == MMSYSERR_NOERROR) v.push_back(narrow(c.szPname));
        else v.push_back("MIDI in " + std::to_string(i));
    }
    return v;
}

static void CALLBACK midi_proc(HMIDIIN, UINT msg, DWORD_PTR inst, DWORD_PTR p1, DWORD_PTR)
{
    if (msg != MIM_DATA) return;
    MidiIn *self = (MidiIn *)inst;
    MidiMsg m;
    m.st = (uint8_t)(p1 & 0xFF);
    m.d1 = (uint8_t)((p1 >> 8) & 0x7F);
    m.d2 = (uint8_t)((p1 >> 16) & 0x7F);
    if (m.st < 0x80 || m.st >= 0xF0) return;   // no system messages (clock, active sensing)
    if (self->cb) self->cb(m);
}

bool MidiIn::open(int dev, std::function<void(const MidiMsg &)> f, std::string &err)
{
    close();
    cb = std::move(f);
    HMIDIIN hi = NULL;
    MMRESULT r = midiInOpen(&hi, (UINT)dev, (DWORD_PTR)&midi_proc, (DWORD_PTR)this, CALLBACK_FUNCTION);
    if (r != MMSYSERR_NOERROR) {
        wchar_t b[256] = {};
        midiInGetErrorTextW(r, b, 256);
        err = narrow(b);
        return false;
    }
    midiInStart(hi);
    h = hi;
    device = dev;
    return true;
}

void MidiIn::close()
{
    if (!h) return;
    midiInStop((HMIDIIN)h);
    midiInReset((HMIDIIN)h);
    midiInClose((HMIDIIN)h);
    h = nullptr;
    device = -1;
}

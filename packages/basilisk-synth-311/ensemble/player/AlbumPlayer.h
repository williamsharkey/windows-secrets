// SNDWAVE2000 Ensemble: an album on one instance (design/CITYPOP-ENS.md). A schedule (tools/album_ens.py: tracks,
// segments, notes) plays through one Windows: every lane switches preset when its schedule says, as early as its
// previous part has rung out, and its notes go to Windows a lookahead before they sound, stamped with their DAC
// sample. Shared by the native harness (tools/albumrender.cpp) and the web edition's worker (citypop-ens-web).
//
// A switch: the lane's build lines go to Windows when the DAC (Windows' own time) reaches the segment's build time.
// The new part's notes wait until Windows says `built`; then they go, and any whose time has passed play late (they
// are counted). Notes of the old part sent while its recorders are being rebuilt are counted too: those are the ones
// that may sound half old, half new.
#pragma once
#include "../../plugin/V3Voice.h"
#include "../../plugin/V3Alloc.h"
#include "../../plugin/V3Host.h"
#include "../../../basilisk-synth/core/dna.h"
#include "../../../basilisk-synth/core/proto.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

namespace ensalbum {

struct Track { int i; double start, end; std::string title; };
struct Seg {
    int id, lane, track; double tBuild, tFirst, tEnd; int cap, level, pan; std::string pack, name, dna;
    // run time
    int state = 0;                 // 0 waiting, 1 build sent, 2 built (adopted), 3 no build needed (same preset)
    double sentAt = -1, builtAt = -1;   // album seconds (by the DAC) when its build went and when it was built
    int lateNotes = 0, underBuild = 0;  // its notes sent after their time; the previous part's notes while it was built
    bsynth::Dna eff; bsynth3::Dna3 d3; uint32_t salt = 0;
};
struct Note { double t; int seg; uint8_t st, a, b; };

class Player {
public:
    using Send = std::function<void(const std::string &line, uint32_t id, uint64_t at)>;
    std::vector<Track> tracks; std::vector<Seg> segs; std::vector<Note> notes;
    static constexpr int NB = 10;
    double lookahead = 0.4;          // seconds: notes go this far ahead of Windows' time
    uint32_t kLat = 2880;            // DAC samples between a note's album time and its stamp (Windows' time to play it)
    double bpm = 120;

    bool load(const std::string &text)
    {
        std::istringstream in(text); std::string l;
        while (std::getline(in, l)) {
            if (l.size() < 2) continue;
            if (l[0] == 'T') { Track t; char b[256] = ""; std::sscanf(l.c_str() + 2, "%d %lf %lf %255[^\n]", &t.i, &t.start, &t.end, b); t.title = b; tracks.push_back(t); }
            else if (l[0] == 'S') {
                Seg s; int n = 0;
                std::sscanf(l.c_str() + 2, "%d %d %d %lf %lf %lf %d %d %d %n", &s.id, &s.lane, &s.track, &s.tBuild, &s.tFirst, &s.tEnd, &s.cap, &s.level, &s.pan, &n);
                std::string rest = l.substr(2 + n);
                size_t a = rest.find('\t'), b = rest.find('\t', a + 1);
                s.pack = rest.substr(0, a); s.name = rest.substr(a + 1, b - a - 1); s.dna = rest.substr(b + 1);
                segs.push_back(s);
            } else if (l[0] == 'N') {
                Note n; int st, a, b; std::sscanf(l.c_str() + 2, "%lf %d %d %d %d", &n.t, &n.seg, &st, &a, &b);
                n.st = (uint8_t)st; n.a = (uint8_t)a; n.b = (uint8_t)b; notes.push_back(n);
            }
        }
        for (auto &s : segs) {   // parsed once: the DNA as Windows builds it and as the notes use it
            const bsynth::Dna w = bsynth::parse(s.dna);
            s.eff = bsynth::applyMacros(w);
            s.d3 = bsynth3::applyMacros3(bsynth3::parse3(w.canonical), w.g.macro);
            s.salt = b16v3::salt(w.canonical);
            s.dna = w.canonical;
        }
        laneSegs.assign(NB, {});
        for (auto &s : segs) if (s.lane >= 0 && s.lane < NB) laneSegs[s.lane].push_back(s.id);
        return !segs.empty() && !notes.empty();
    }

    // before the album: track `t`'s first segments of every lane are built (their build lines go now); the clock
    // starts with begin() once ready() says so
    void prepare(int t, const Send &send)
    {
        trackFrom = t; ni = 0;
        while (ni < notes.size() && notes[ni].t < tracks[t].start) ni++;
        offset = tracks[t].start;
        for (int k = 0; k < NB; k++) {
            int cur = -1;
            for (int id : laneSegs[k]) if (segs[id].track <= t) cur = id; else break;
            for (int id : laneSegs[k]) if (segs[id].track == t) { cur = id; break; }
            if (cur < 0) continue;
            laneCur[k] = -1; laneNext[k] = 0;
            while (laneNext[k] < (int)laneSegs[k].size() && laneSegs[k][laneNext[k]] != cur) laneNext[k]++;
            build(segs[cur], send, offset);   // (before the clock: its build time is not counted)
            laneNext[k]++;
        }
        send("title " + under(tracks[t].title), 0, 0);
        curTrack = t;
    }
    bool ready() const { for (int k = 0; k < NB; k++) for (auto &s : segs) if (s.lane == k && s.state == 1) return false; return true; }
    void begin(uint64_t dac0) { this->dac0 = dac0; started = true; }
    double albumTime(uint64_t dac) const { return started ? offset + ((double)dac - (double)dac0) / 48000.0 : offset; }
    uint64_t stamp(double t) const { return dac0 + (uint64_t)((t - offset) * 48000.0 + 0.5) + kLat; }
    bool done() const { return started && ni >= notes.size() && albumTime(dacSeen) > tracks.back().end; }
    int track() const { return curTrack; }

    // every host tick, with Windows' DAC position now
    void tick(uint64_t dacNow, const Send &send)
    {
        dacSeen = dacNow;
        if (!started) return;
        const double now = albumTime(dacNow);
        while (curTrack + 1 < (int)tracks.size() && now >= tracks[curTrack + 1].start - 0.5) { curTrack++; send("title " + under(tracks[curTrack].title), 0, 0); }
        // switches due: a lane's next segment, once Windows' time passes its build time (one lane's builds in order)
        for (int k = 0; k < NB; k++) {
            if (laneNext[k] >= (int)laneSegs[k].size()) continue;
            Seg &s = segs[laneSegs[k][laneNext[k]]];
            const int prev = laneCur[k];
            if (building[k] >= 0) continue;                      // the lane's previous switch is still building
            if (now + 1e-9 < std::max(s.tBuild, 0.0)) continue;
            if (prev >= 0 && segs[prev].dna == s.dna) { s.state = 3; s.sentAt = s.builtAt = now; laneCur[k] = s.id; mixTo(s, send); laneNext[k]++; continue; }
            build(s, send, now);
            laneNext[k]++;
        }
        // notes due: a lookahead ahead of Windows' time; a note whose part is not built yet waits
        const double horizon = now + lookahead;
        while (ni < notes.size() && notes[ni].t < horizon) {
            const Note &n = notes[ni];
            Seg &s = segs[n.seg];
            if (s.state == 0 || s.state == 1) { held[s.lane].push_back(ni); ni++; continue; }
            play(n, now, send);
            ni++;
        }
        for (int k = 0; k < NB; k++) {   // held notes go once their part is built
            while (!held[k].empty()) {
                const Note &n = notes[held[k].front()];
                const Seg &s = segs[n.seg];
                if (s.state == 0 || s.state == 1) break;
                play(n, now, send);
                held[k].pop_front();
            }
        }
        for (int k = 0; k < NB; k++) if (laneCur[k] >= 0 && hostHas[k]) {
            const std::string pre = "@" + std::to_string(k) + " ";
            host[k].tick(stamp(horizon), [&](const char *line, uint64_t when) { send(pre + line, ++id, when); });
        }
    }

    // Windows' replies (lines)
    void reply(const std::string &l)
    {
        if (l.size() < 3 || l[0] != '@') return;
        const int k = std::atoi(l.c_str() + 1); const size_t sp = l.find(' ');
        if (k < 0 || k >= NB || sp == std::string::npos) return;
        const std::string r = l.substr(sp + 1);
        if (r.rfind("seg ", 0) == 0) { std::istringstream in(r.substr(4)); int L = -1; in >> L; std::vector<uint32_t> v; uint32_t f; while (in >> f) v.push_back(f); pendSegs[k].push_back({L, v}); return; }
        bsynth::proto::Reply rp = bsynth::proto::parse(r);
        if (rp.kind == bsynth::proto::Reply::Layer) pendLayers[k].push_back({rp.layer, rp.first, rp.count, rp.rate, rp.frames});
        else if (rp.kind == bsynth::proto::Reply::End) { if (hostHas[k]) host[k].end(rp.rec); }
        else if (rp.kind == bsynth::proto::Reply::Built) {
            if (building[k] < 0) return;
            Seg &s = segs[building[k]];
            host[k] = b16v3::NoteHost();
            host[k].bpm = bpm; host[k].capWin = host[k].capRate = host[k].capTape = true;
            host[k].adopt(s.eff, s.d3, s.salt);
            if (getenv("ALBUM_DEBUG")) std::fprintf(stderr, "built lane %d seg %d layers %zu at %.2f\n", k, s.id, pendLayers[k].size(), albumTime(dacSeen));
            for (auto &v : pendLayers[k]) host[k].layerInfo(v[0], v[1], v[2], v[3], v[4]);
            for (auto &g : pendSegs[k]) host[k].segments(g.first, g.second);
            pendLayers[k].clear(); pendSegs[k].clear();
            hostHas[k] = true;
            s.state = 2; s.builtAt = albumTime(dacSeen);
            laneCur[k] = s.id; building[k] = -1;
        }
    }

    // per track: switches, notes that played late because their part was still building, notes of a part being replaced
    struct Stat { int switches = 0, builds = 0, late = 0, underBuild = 0; double buildSecs = 0; };
    std::vector<Stat> stats() const
    {
        std::vector<Stat> r(tracks.size());
        for (auto &s : segs) {
            if (s.track < 0 || s.track >= (int)r.size() || s.state == 0) continue;
            Stat &x = r[s.track];
            x.switches++;
            if (s.state != 3) { x.builds++; x.buildSecs += std::max(0.0, s.builtAt - s.sentAt); }
            x.late += s.lateNotes; x.underBuild += s.underBuild;
        }
        return r;
    }

private:
    std::vector<std::vector<int>> laneSegs;
    int laneCur[NB] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1}, laneNext[NB] = {}, building[NB] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
    b16v3::NoteHost host[NB]; bool hostHas[NB] = {};
    std::vector<std::vector<int>> pendLayers[NB]; std::vector<std::pair<int, std::vector<uint32_t>>> pendSegs[NB];
    std::deque<size_t> held[NB];
    size_t ni = 0; uint64_t dac0 = 0, dacSeen = 0; bool started = false; double offset = 0; int curTrack = 0, trackFrom = 0;
    uint32_t id = 0;
public:
    uint64_t played = 0, dropped = 0;
private:

    static std::string under(std::string s) { for (auto &c : s) if (c == ' ') c = '_'; return s; }
    void mixTo(const Seg &s, const Send &send)
    {
        const std::string pre = "@" + std::to_string(s.lane) + " ";
        send(pre + "name " + under(s.name), 0, 0);
        char b[64]; std::snprintf(b, sizeof b, "mix %d %d 0 0", s.level, s.pan); send(pre + b, 0, 0);
    }
    void build(Seg &s, const Send &send, double now)
    {
        const int k = s.lane; const std::string pre = "@" + std::to_string(k) + " ";
        if (laneCur[k] >= 0) {   // the part being replaced: its notes still to go are counted while this builds
            const Seg &p = segs[laneCur[k]];
            for (size_t j = ni; j < notes.size() && notes[j].t < p.tEnd + 2; j++) if (notes[j].seg == p.id && (notes[j].st & 0xF0) == 0x90 && notes[j].b) s.underBuild++;
        }
        mixTo(s, send);
        send(pre + "cap " + std::to_string(s.cap), 0, 0);
        send(pre + "dna " + s.dna, 0, 0);
        char b[160]; bsynth::proto::env(b, sizeof b, s.eff.g); b[std::strlen(b) - 1] = 0; send(pre + b, 0, 0);
        for (int i = 0; i < bsynth::kMaxLayers; i++) {
            static const bsynth::Env none;
            const bsynth::Layer *Ly = i < (int)s.eff.layers.size() ? &s.eff.layers[i] : nullptr;
            send(pre + b16v3::lenvLine(i, 'a', Ly ? Ly->envA : none, s.d3, bpm, true), 0, 0);
            send(pre + b16v3::lenvLine(i, 'p', Ly ? Ly->envP : none, s.d3, bpm, true), 0, 0);
        }
        pendLayers[k].clear(); pendSegs[k].clear();
        s.state = 1; s.sentAt = now; building[k] = s.id;
    }
    void play(const Note &n, double now, const Send &send)
    {
        Seg &s = segs[n.seg]; const int k = s.lane;
        if (!hostHas[k] || laneCur[k] != s.id) { dropped++; if (getenv("ALBUM_DEBUG") && dropped < 5) std::fprintf(stderr, "drop note seg %d lane %d cur %d has %d state %d\n", s.id, k, laneCur[k], hostHas[k], s.state); return; }   // (a part already replaced)
        played++;
        if ((n.st & 0xF0) == 0x90 && n.b && n.t < now) s.lateNotes++;
        if (building[k] >= 0 && (n.st & 0xF0) == 0x90 && n.b) {}   // (counted at the switch)
        const std::string pre = "@" + std::to_string(k) + " ";
        const uint64_t at = stamp(std::max(n.t, now));
        host[k].midi(n.st | (uint8_t)k, n.a, n.b, at, [&](const char *line, uint64_t when) { send(pre + line, ++id, when); });
        if ((n.st & 0xF0) == 0x90 && n.b) { char b[32]; std::snprintf(b, sizeof b, "note %d %d", n.a, n.b); send(pre + b, 0, 0); }
    }
};

}  // namespace ensalbum

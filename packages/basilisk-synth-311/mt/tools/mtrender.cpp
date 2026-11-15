// mtrender: the multitimbral experiment's offline renderer (design/MULTITIMBRAL-EXPERIMENT.md). One Windows 3.11
// (MTSYNTH.EXE, cold-booted), many lanes: each lane builds its own DNA on its own Sound Recorders and plays its own
// track; the card keeps each lane's output apart (bsyn_host_read_lane), so every lane comes out as its own stem.
//
//   mtrender --machine DIR --core FILE --job JOB.txt --out-dir DIR [--lookahead MS] [--log FILE] [--tail S]
// JOB.txt: "bpm <bpm>", "tail <s>", then one "lane <midi path> <DNA>" per lane, in lane order.
// The track loop is render311's (plugin/SongEngine.h), extended to many NoteHosts on one machine.
#include "../../plugin/SongEngine.h"
#include <dlfcn.h>
#include <map>
#include <sys/resource.h>
using namespace b16song;

struct Lane {
    std::string dna, midi; std::vector<MidiEv> ev;
    b16v3::NoteHost host; bsynth::Dna eff; bsynth3::Dna3 d3; double gain = 1;
    uint32_t used = 0; int cap = 0;   // the recorders its notes used (bit per recorder)
    std::vector<float> out; double buildWall = 0; long buildGuestMs = -1; size_t ei = 0;
};
static double cpuSec() { struct rusage u; getrusage(RUSAGE_SELF, &u); return u.ru_utime.tv_sec + u.ru_stime.tv_sec + (u.ru_utime.tv_usec + u.ru_stime.tv_usec) * 1e-6; }

int main(int argc, char **argv)
{
    std::map<std::string, std::string> a;
    for (int i = 1; i + 1 < argc; i += 2) a[argv[i]] = argv[i + 1];
    if (!a.count("--machine") || !a.count("--core") || !a.count("--job") || !a.count("--out-dir")) { std::fprintf(stderr, "mtrender --machine DIR --core FILE --job JOB --out-dir DIR\n"); return 2; }
    const std::string machine = a["--machine"], core = a["--core"], outDir = a["--out-dir"];
    double bpm = 120, tail = a.count("--tail") ? std::atof(a["--tail"].c_str()) : 3.0;
    const uint64_t look48 = a.count("--lookahead") ? (uint64_t)(std::atof(a["--lookahead"].c_str()) * 48) : 0;
    std::vector<Lane> L;
    {
        std::ifstream in(a["--job"]); std::string l;
        while (std::getline(in, l)) {
            if (l.rfind("bpm ", 0) == 0) bpm = std::atof(l.c_str() + 4);
            else if (l.rfind("tail ", 0) == 0) tail = std::atof(l.c_str() + 5);
            else if (l.rfind("lane ", 0) == 0) {
                size_t s = l.find(' ', 5); Lane x; x.midi = l.substr(5, s - 5); x.dna = l.substr(s + 1);
                if (!readMidi(x.midi, x.ev)) { std::fprintf(stderr, "mtrender: cannot read %s\n", x.midi.c_str()); return 2; }
                if (a.count("--until")) {   // only the first seconds (profiling); the notes still sounding then get their offs
                    const double u = std::atof(a["--until"].c_str()); std::vector<MidiEv> k;
                    for (auto &m : x.ev) if (m.t < u || (m.st & 0xF0) == 0x80 || ((m.st & 0xF0) == 0x90 && m.b == 0)) k.push_back(m.t < u ? m : MidiEv{u, m.st, m.a, m.b});
                    x.ev = k;
                }
                L.push_back(std::move(x));
            }
        }
    }
    const double t0 = nowSec(), c0 = cpuSec();
    std::vector<std::string> libNames;
    {   std::ifstream in(machine + "/library.names.txt"); std::string l;
        while (std::getline(in, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) libNames.push_back(l); }
        std::ifstream pn(machine + "/packs/packs.names.txt");
        while (std::getline(pn, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) libNames.push_back(l); }
        setLibrary(libNames); }
    const std::string conf = tempConf(), recDir = conf + ".rec";
    b16rec::makeDir(recDir);
    {   std::ifstream in(machine + "/w31.conf"); std::string s((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>()); size_t p;
        while ((p = s.find("@MACHINE@")) != std::string::npos) s.replace(p, 9, "\"" + machine + "\"");
        while ((p = s.find("@DRIVE@")) != std::string::npos) s.replace(p, 7, "\"" + machine + "/drive\"");
        while ((p = s.find("@RECDIR@")) != std::string::npos) s.replace(p, 8, "\"" + recDir + "\"");
        while ((p = s.find("@PACKS@")) != std::string::npos) s.replace(p, 7, "\"" + machine + "/packs\"");
        std::ofstream o(conf); o << s; }
    Machine M; bshm *S = M.S = (bshm *)std::calloc(1, sizeof(bshm));
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING; S->lead = 1024; S->offline = 1; S->vid_want = 0;
    M.e = bs_engine_start(S, core.c_str(), conf.c_str(), "", nullptr, a.count("--log") ? a["--log"].c_str() : nullptr);
    std::vector<std::string> pending;   // replies, by lane
    auto lane_of = [](std::string &l) -> int { if (l.empty() || l[0] != '@') return -1; int k = std::atoi(l.c_str() + 1); size_t s = l.find(' '); l = s == std::string::npos ? "" : l.substr(s + 1); return k; };
    bool ready = false; std::string readyLine;
    while (!ready && S->state != BS_FAILED) {
        M.step(48000);
        std::vector<std::string> ls; M.lines(ls);
        for (auto &l : ls) { if (l.rfind("mt ready", 0) == 0) { ready = true; readyLine = l; } if (l.rfind("launch failed", 0) == 0) std::fprintf(stderr, "windows: %s\n", l.c_str()); }
        if (nowSec() - t0 > 300) { std::fprintf(stderr, "mtrender: no 'mt ready'\n"); return 3; }
    }
    if (S->state == BS_FAILED) { std::fprintf(stderr, "mtrender: %s\n", S->error); return 3; }
    void *core_h = dlopen(core.c_str(), RTLD_NOW | RTLD_NOLOAD);
    auto readLane = core_h ? (int (*)(int, uint64_t, float *, int))dlsym(core_h, "bsyn_host_read_lane") : nullptr;
    if (!readLane) { std::fprintf(stderr, "mtrender: the core has no lane buses\n"); return 3; }
    if (!a.count("--video") || a["--video"] != "1") { auto vid = (void (*)(int))dlsym(core_h, "bsyn_host_video"); if (vid) vid(0); }
    const double tBoot = nowSec(), cBoot = cpuSec();
    std::fprintf(stderr, "mtrender: %s (boot %.2f s wall)\n", readyLine.c_str(), tBoot - t0);
    {   std::ifstream in(machine + "/packs/PACKS.TSV"); std::string l, ids;
        while (std::getline(in, l)) { const size_t a1 = l.find('\t'), a2 = a1 == std::string::npos ? a1 : l.find('\t', a1 + 1); if (a2 != std::string::npos) ids += (ids.empty() ? "" : ",") + l.substr(a1 + 1, a2 - a1 - 1); }
        if (!ids.empty()) M.send("packs " + ids); }
    for (size_t k = 0; k < L.size(); k++) {   // build each lane, one after another (one Windows)
        Lane &ln = L[k]; const double tb = nowSec();
        const bsynth::Dna written = bsynth::parse(ln.dna);
        ln.eff = bsynth::applyMacros(written);
        ln.d3 = bsynth3::applyMacros3(bsynth3::parse3(written.canonical), written.g.macro);
        ln.host.bpm = bpm; ln.host.adopt(ln.eff, ln.d3, b16v3::salt(written.canonical));
        ln.host.capWin = ln.host.capRate = ln.host.capTape = true;
        ln.gain = std::pow(10.0, ln.eff.g.gainDb / 20.0);
        const std::string pre = "@" + std::to_string(k) + " ";
        if (a.count("--cap") && a["--cap"] == "1") {   // reclaim: a lane gets the recorders its track can use, no more
            const double rel = ln.eff.g.release / 1000.0 + 0.05; std::vector<std::pair<double, int>> edges; std::map<int, double> on;
            for (auto &m : ln.ev) {
                const int st = m.st & 0xF0;
                if (st == 0x90 && m.b) on[m.a] = m.t;
                else if ((st == 0x80 || st == 0x90) && on.count(m.a)) { edges.push_back({on[m.a], 1}); edges.push_back({m.t + rel, -1}); on.erase(m.a); }
            }
            for (auto &o : on) { edges.push_back({o.second, 1}); }
            std::sort(edges.begin(), edges.end()); int cur = 0, peak = 0; for (auto &e : edges) { cur += e.second; peak = std::max(peak, cur); }
            int need = 0;
            for (auto &Ly : ln.eff.layers) need += std::min(16, std::max(1, peak) * (int)Ly.harmony.size() * std::max(1, Ly.unison));
            ln.cap = std::max((int)ln.eff.layers.size(), std::min(16, need));
            M.send(pre + "cap " + std::to_string(ln.cap));
        }
        M.send(pre + "dna " + written.canonical);
        char b[160]; bsynth::proto::env(b, sizeof b, ln.eff.g); b[std::strlen(b) - 1] = 0; M.send(pre + b);
        for (bool built = false; !built;) {
            M.step(48000);
            std::vector<std::string> ls; M.lines(ls);
            for (auto l : ls) {
                const int lk = lane_of(l);
                if (lk != (int)k) { if (lk < 0 && getenv("MT_VERBOSE")) std::fprintf(stderr, "windows: %s\n", l.c_str()); continue; }
                if (l.rfind("seg ", 0) == 0) { std::istringstream in(l.substr(4)); int Ly = -1; in >> Ly; std::vector<uint32_t> v; uint32_t f; while (in >> f) v.push_back(f); ln.host.segments(Ly, v); }
                bsynth::proto::Reply r = bsynth::proto::parse(l);
                if (r.kind == bsynth::proto::Reply::Layer) ln.host.layerInfo(r.layer, r.first, r.count, r.rate, r.frames);
                if (r.kind == bsynth::proto::Reply::Built) { built = true; ln.buildGuestMs = std::atol(l.c_str() + 6); }
            }
            if (S->state == BS_FAILED || nowSec() - tb > 600) { std::fprintf(stderr, "mtrender: lane %zu did not build\n", k); return 3; }
        }
        for (int i = 0; i < bsynth::kMaxLayers; i++) {
            static const bsynth::Env none;
            const bsynth::Layer *Ly = i < (int)ln.eff.layers.size() ? &ln.eff.layers[i] : nullptr;
            M.send(pre + b16v3::lenvLine(i, 'a', Ly ? Ly->envA : none, ln.d3, bpm, true));
            M.send(pre + b16v3::lenvLine(i, 'p', Ly ? Ly->envP : none, ln.d3, bpm, true));
        }
        ln.buildWall = nowSec() - tb;
    }
    const double tBuilt = nowSec(), cBuilt = cpuSec();
    const uint32_t kLat = 2880, kBlock = 512;
    const uint64_t anchor = S->dac_w + 1;
    double endSec = 0; for (auto &ln : L) if (!ln.ev.empty()) endSec = std::max(endSec, ln.ev.back().t);
    endSec += tail;
    const uint64_t total = (uint64_t)(endSec * 48000) + kLat;
    std::vector<float> master; master.reserve(total * 2);
    for (auto &ln : L) ln.out.reserve(total * 2);
    std::vector<float> buf(kBlock * 2);
    uint64_t lines = 0;
    // --realtime 1: the host's blocks come at the wall clock's pace, as a DAW's would; a block whose samples are not
    // ready by its deadline (its time plus the plugin's fixed latency, kLat) is a dropout
    const bool rt = a.count("--realtime") && a["--realtime"] == "1";
    uint64_t misses = 0; double worst = 0; const double tp0 = nowSec();
    for (uint64_t h = 0; h < total; h += kBlock) {
        const uint64_t blockEnd = h + kBlock;
        if (rt) { const double due = tp0 + (double)h / 48000.0; while (nowSec() < due) std::this_thread::sleep_for(std::chrono::microseconds(300)); }
        for (size_t k = 0; k < L.size(); k++) {
            Lane &ln = L[k]; const std::string pre = "@" + std::to_string(k) + " ";
            auto sink = [&](const char *line, uint64_t when) { M.send(pre + line, ++M.nextId, when); lines++; if (!std::strncmp(line, "on ", 3)) ln.used |= 1u << (std::atoi(line + 3) & 31); };
            while (ln.ei < ln.ev.size() && (uint64_t)(ln.ev[ln.ei].t * 48000) < blockEnd + look48) {
                const MidiEv &m = ln.ev[ln.ei++];
                ln.host.midi(m.st, m.a, m.b, anchor + (uint64_t)(m.t * 48000) + kLat, sink);
            }
            ln.host.tick(anchor + blockEnd + kLat, sink);
        }
        std::vector<std::string> ls; M.lines(ls);
        for (auto l : ls) { const int lk = lane_of(l); if (lk < 0 || lk >= (int)L.size()) continue; bsynth::proto::Reply r = bsynth::proto::parse(l); if (r.kind == bsynth::proto::Reply::End) L[lk].host.end(r.rec); }
        const uint64_t need = anchor + blockEnd;
        S->host_r = anchor + h;
        while (S->dac_w < need && S->state != BS_FAILED) { M.runTo(need); nap(); }
        if (rt) { const double over = nowSec() - (tp0 + (double)(h + kBlock + kLat) / 48000.0); if (over > 0) misses++; if (over > worst) worst = over; }
        for (uint64_t k = anchor + h; k < need; k++) { const uint32_t j = (uint32_t)(k % BSHM_RING); master.push_back(S->ring[j * 2]); master.push_back(S->ring[j * 2 + 1]); }
        for (size_t k = 0; k < L.size(); k++) {
            const int got = readLane((int)k, anchor + h, buf.data(), kBlock);
            if (got != (int)kBlock) { std::fprintf(stderr, "mtrender: lane %zu bus short (%d)\n", k, got); return 4; }
            L[k].out.insert(L[k].out.end(), buf.begin(), buf.end());
        }
    }
    const double tPlay = nowSec(), cPlay = cpuSec();
    const uint32_t late = S->sched_late, ontime = S->sched_ontime, latemax = S->sched_latemax;
    M.send("stats"); M.send("mem"); M.step(4800);
    { std::vector<std::string> ls; M.lines(ls); for (auto &l : ls) if (l.rfind("stats", 0) == 0 || l.rfind("mem", 0) == 0) std::fprintf(stderr, "windows: %s\n", l.c_str()); }
    {   auto bst = (void (*)(uint64_t *, uint64_t *, uint32_t *))dlsym(core_h, "bsyn_host_bufstats");
        if (bst) { uint64_t t = 0, u = 0; uint32_t n = 0; bst(&t, &u, &n); std::fprintf(stderr, "buffers: %u recorders played; their buffers %.2f MB, distinct %.2f MB (%.0f%% duplicate)\n", n, t / 1048576.0, u / 1048576.0, t ? 100.0 * (t - u) / t : 0.0); } }
    bs_engine_stop(M.e); std::free(S); std::remove(conf.c_str()); b16rec::clearDir(recDir);
    std::vector<float> mix(master.size() - 2 * kLat, 0.f);
    for (size_t k = 0; k < L.size(); k++) {
        Lane &ln = L[k];
        ln.out.erase(ln.out.begin(), ln.out.begin() + 2 * kLat);
        for (float &x : ln.out) x *= (float)ln.gain;
        if (!a.count("--stems") || a["--stems"] != "0") writeWavFloat(outDir + "/lane" + std::to_string(k) + ".wav", ln.out);
        for (size_t i = 0; i < mix.size() && i < ln.out.size(); i++) mix[i] += ln.out[i];
        std::fprintf(stderr, "lane %zu: build %.2f s wall (%ld ms on Windows' clock), %zu events, %d recorders used (cap %d)\n", k, ln.buildWall, ln.buildGuestMs, ln.ev.size(), __builtin_popcount(ln.used), ln.cap);
    }
    writeWavFloat(outDir + "/mix.wav", mix);
    master.erase(master.begin(), master.begin() + 2 * kLat);
    if (!a.count("--stems") || a["--stems"] != "0") writeWavFloat(outDir + "/dac.wav", master);
    std::fprintf(stderr, "mtrender: %zu lanes, %.2f s of audio; boot %.2f s, build %.2f s, play %.2f s wall (%.2fx real time); cpu boot %.2f build %.2f play %.2f s; lines %llu; late %u of %u (max %u samples)\n",
                 L.size(), endSec, tBoot - t0, tBuilt - tBoot, tPlay - tBuilt, endSec / (tPlay - tBuilt), cBoot - c0, cBuilt - cBoot, cPlay - cBuilt,
                 (unsigned long long)lines, late, late + ontime, latemax);
    if (rt) std::fprintf(stderr, "realtime: %llu of %llu blocks missed their deadline (worst %.1f ms late)\n", (unsigned long long)misses, (unsigned long long)(total / kBlock), worst * 1000);
    { struct rusage u; getrusage(RUSAGE_SELF, &u); std::fprintf(stderr, "mtrender: peak RSS %ld MB\n", u.ru_maxrss / 1024); }
    return 0;
}

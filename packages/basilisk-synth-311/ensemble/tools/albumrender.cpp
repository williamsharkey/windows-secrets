// albumrender: a whole album through one SNDWAVE2000 Ensemble (ENSEMBLE.EXE in the Ensemble machine), offline, with
// the album player of the web edition (player/AlbumPlayer.h). It reports every track's switches, the notes that
// played late because their preset was still building, and how fast the machine ran.
//
//   albumrender --machine DIR --core FILE --album album.ens [--out mix.wav] [--from TRACK] [--to TRACK] [--log FILE]
#include "../../plugin/SongEngine.h"
#include "../player/AlbumPlayer.h"
#include <sys/resource.h>
#include <map>
using namespace b16song;

static double cpuSec() { struct rusage u; getrusage(RUSAGE_SELF, &u); return u.ru_utime.tv_sec + u.ru_stime.tv_sec + (u.ru_utime.tv_usec + u.ru_stime.tv_usec) * 1e-6; }

int main(int argc, char **argv)
{
    std::map<std::string, std::string> a;
    for (int i = 1; i + 1 < argc; i += 2) a[argv[i]] = argv[i + 1];
    const std::string machine = a["--machine"], core = a["--core"];
    {   std::vector<std::string> names; std::string l;
        std::ifstream x(machine + "/library.names.txt"); while (std::getline(x, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
        std::ifstream y(machine + "/packs/packs.names.txt"); while (std::getline(y, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
        setLibrary(names); }
    ensalbum::Player P;
    { std::ifstream in(a["--album"]); std::string t((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>()); if (!P.load(t)) { std::fprintf(stderr, "albumrender: no album\n"); return 2; } }
    const int from = a.count("--from") ? std::atoi(a["--from"].c_str()) : 0, to = a.count("--to") ? std::atoi(a["--to"].c_str()) : (int)P.tracks.size() - 1;

    const std::string conf = tempConf(), recDir = conf + ".rec"; b16rec::makeDir(recDir);
    {   std::ifstream in(machine + "/w31.conf"); std::string s((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>()); size_t p;
        while ((p = s.find("@MACHINE@")) != std::string::npos) s.replace(p, 9, "\"" + machine + "\"");
        while ((p = s.find("@DRIVE@")) != std::string::npos) s.replace(p, 7, "\"" + machine + "/drive\"");
        while ((p = s.find("@RECDIR@")) != std::string::npos) s.replace(p, 8, "\"" + recDir + "\"");
        while ((p = s.find("@PACKS@")) != std::string::npos) s.replace(p, 7, "\"" + machine + "/packs\"");
        std::ofstream o(conf); o << s; }
    const double t0 = nowSec(), c0 = cpuSec();
    Machine M; bshm *S = M.S = (bshm *)std::calloc(1, sizeof(bshm));
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING; S->lead = 1024; S->offline = 1; S->vid_want = 0;
    M.e = bs_engine_start(S, core.c_str(), conf.c_str(), (machine + "/w31.state").c_str(), nullptr, a.count("--log") ? a["--log"].c_str() : nullptr);
    while (S->state < BS_RUNNING && S->state != BS_FAILED) M.step(4800);
    if (S->state == BS_FAILED) { std::fprintf(stderr, "albumrender: %s\n", S->error); return 3; }
    uint64_t nOn = 0, nLines = 0;
    auto send = [&](const std::string &l, uint32_t id, uint64_t at) { M.send(l, id, at); nLines++; if (l.find(" on ") != std::string::npos) nOn++; };
    std::vector<std::string> ls;
    auto pump = [&]() { ls.clear(); M.lines(ls); for (auto &l : ls) { if (getenv("ALBUM_VERBOSE")) std::fprintf(stderr, "windows: %s\n", l.c_str()); P.reply(l); } };
    {   std::ifstream in(machine + "/packs/PACKS.TSV"); std::string l, ids;
        while (std::getline(in, l)) { const size_t a1 = l.find('\t'), a2 = a1 == std::string::npos ? a1 : l.find('\t', a1 + 1); if (a2 != std::string::npos) ids += (ids.empty() ? "" : ",") + l.substr(a1 + 1, a2 - a1 - 1); }
        M.send("packs " + ids); }
    if (a.count("--colors")) M.send("colors " + a["--colors"]);
    M.send("go");
    for (bool ready = false; !ready;) { M.step(4800); ls.clear(); M.lines(ls); for (auto &l : ls) if (l == "ready") ready = true; }
    const double tReady = nowSec();
    P.prepare(from, send);
    uint64_t steps = 0;
    while (!P.ready()) { M.step(4800); pump(); if (++steps > 20000) { std::fprintf(stderr, "albumrender: the first presets did not build\n"); return 3; } }
    const double tPrepared = nowSec(), cPrepared = cpuSec();
    const uint64_t dac0 = S->dac_w + 4800;
    P.begin(dac0);
    const double endT = P.tracks[to].end;
    FILE *wav = nullptr; uint64_t frames = 0;
    if (a.count("--out")) { wav = std::fopen(a["--out"].c_str(), "wb"); std::fseek(wav, 44, SEEK_SET); }
    const uint32_t kBlock = 512; uint64_t h = dac0;
    double lastShow = 0;
    while (P.albumTime(h) < endT) {
        P.tick(S->dac_w, send);
        pump();
        const uint64_t need = h + kBlock;
        S->host_r = h;
        while (S->dac_w < need && S->state != BS_FAILED) { M.runTo(need); nap(); }
        if (wav) for (uint64_t k = h; k < need; k++) { const uint32_t j = (uint32_t)(k % BSHM_RING); for (int c = 0; c < 2; c++) { float v = S->ring[j * 2 + c]; v = v > 1 ? 1 : v < -1 ? -1 : v; int16_t s16 = (int16_t)std::lround(v * 32767); std::fwrite(&s16, 2, 1, wav); } frames++; }
        h = need;
        if (P.albumTime(h) - lastShow > 30) { lastShow = P.albumTime(h); std::fprintf(stderr, "  %.0f s of album, %.1f s wall, track %d\n", lastShow, nowSec() - tPrepared, P.track() + 1); }
        if (S->state == BS_FAILED) break;
    }
    const double tEnd = nowSec(), cEnd = cpuSec();
    const uint32_t late = S->sched_late, ontime = S->sched_ontime, latemax = S->sched_latemax;
    bs_engine_stop(M.e); std::free(S); std::remove(conf.c_str()); b16rec::clearDir(recDir);
    if (wav) {
        const uint32_t data = (uint32_t)(frames * 4); std::fseek(wav, 0, SEEK_SET);
        auto u32 = [&](uint32_t v) { std::fwrite(&v, 4, 1, wav); }; auto u16 = [&](uint16_t v) { std::fwrite(&v, 2, 1, wav); };
        std::fwrite("RIFF", 1, 4, wav); u32(36 + data); std::fwrite("WAVEfmt ", 1, 8, wav); u32(16); u16(1); u16(2); u32(48000); u32(192000); u16(4); u16(16);
        std::fwrite("data", 1, 4, wav); u32(data); std::fclose(wav);
    }
    const double audio = endT - P.tracks[from].start;
    std::printf("albumrender: %llu lines to Windows, %llu notes (on); player played %llu, dropped %llu\n", (unsigned long long)nLines, (unsigned long long)nOn, (unsigned long long)P.played, (unsigned long long)P.dropped);
    std::printf("albumrender: tracks %d-%d, %.1f s of album; ready %.1f s, first presets %.1f s, play %.1f s wall (%.2fx real time), cpu %.1f s (%.2f of a core per real-time second); card late %u of %u (max %u samples)\n",
                from + 1, to + 1, audio, tReady - t0, tPrepared - tReady, tEnd - tPrepared, audio / (tEnd - tPrepared), cEnd - cPrepared, (cEnd - cPrepared) / audio, late, late + ontime, latemax);
    auto st = P.stats();
    for (int t = from; t <= to; t++)
        std::printf("  track %2d %-38.38s switches %2d (builds %2d, %.1f s building), notes late for a switch %d, notes of a part being replaced %d\n",
                    t + 1, P.tracks[t].title.c_str(), st[t].switches, st[t].builds, st[t].buildSecs, st[t].late, st[t].underBuild);
    return 0;
}

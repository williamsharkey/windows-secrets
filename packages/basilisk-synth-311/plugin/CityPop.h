// SNDWAVE1993: CITYPOP.EXE, the album CITYPOP1993 played on this instance (packages/basilisk-synth/library/
// albums/citypop-deprogrammed). The album's twelve .song files and their MIDI files are in the machine folder
// (machine/citypop/); every part is played by Sound Recorder through the Song tab's engines (one Windows 3.11 per
// part, renderStems), mixed by SongMix.h, and played through the plugin's output. A track is rendered before it plays;
// the next one renders while it plays. Renders are kept in My Recordings/CITYPOP1993, so a replay is at once.
//
// Track 1 comes prepared at the factory (machine/citypop/factory-01.wav, tools/make_citypop_factory.py: the same engines,
// 16-bit) so the album starts at once; `citypop clear` discards the renders, and from then on track 1 renders here too.
//
// Windows -> host: citypop list | citypop play <i> | citypop stop | citypop next | citypop prev | citypop clear
// host -> Windows: citypop trk <i> <title>|<seconds> | citypop end | citypop now <i> <playing> <ms> <length ms>
//                  citypop status <text>
#pragma once
#include <atomic>
#include <condition_variable>
#include <cstdio>
#include <functional>
#include <mutex>
#include <set>
#include <thread>
#include "SongMix.h"
#include "../../basilisk-synth/core/userstore.h"
#ifdef _WIN32
#include <windows.h>
#else
#include <dirent.h>
#include <sys/stat.h>
#endif

namespace b16song {

class CityPop {
public:
    std::string machine, core, userDir, tmpDir, cacheDir;   // set by the plugin (cacheDir: My Recordings/CITYPOP1993)
    std::function<void(const std::string &)> send;
    std::function<void()> lowerPriority;
    int engines = 4;

    ~CityPop() { shutdown(); }
    void shutdown()
    {
        { std::lock_guard<std::mutex> l(m_); quit_ = true; cancel_ = true; }
        cv_.notify_all();
        if (th_.joinable()) th_.join();
        send = nullptr;
    }

    bool line(const std::string &ln)
    {
        if (ln.rfind("citypop", 0) != 0) return false;
        const std::string r = ln.size() > 8 ? ln.substr(8) : "";
        load();
        if (r == "list" || r.empty()) { sendList(); sendNow(); return true; }
        if (r == "stop") { playing_ = false; sendNow(); return true; }
        if (r.rfind("play", 0) == 0) { const int i = r.size() > 5 ? std::atoi(r.c_str() + 5) : std::max(0, cur_.load()); play(i); return true; }
        if (r == "next") { play(std::min((int)titles_.size() - 1, cur_ + 1)); return true; }
        if (r == "prev") { play(std::max(0, cur_ - 1)); return true; }
        if (r == "clear") { clear(); return true; }
        return true;
    }
    void process(float *L, float *R, uint32_t frames, double sr)
    {
        if (!playing_) return;
        std::unique_lock<std::mutex> l(pm_, std::try_to_lock);
        if (!l.owns_lock() || mix_.empty()) return;
        const double step = 48000.0 / sr; const size_t n = mix_.size() / 2; const float s = 1.f / 8388607.f;
        double p = pos_;
        for (uint32_t i = 0; i < frames; i++, p += step) {
            const size_t k = (size_t)p;
            if (k + 1 >= n) { ended_ = true; playing_ = false; break; }
            const float f = (float)(p - (double)k);
            L[i] += ((float)mix_[2 * k] + (float)(mix_[2 * k + 2] - mix_[2 * k]) * f) * s;
            R[i] += ((float)mix_[2 * k + 1] + (float)(mix_[2 * k + 3] - mix_[2 * k + 1]) * f) * s;
        }
        pos_ = p;
    }
    void poll()   // the worker's housekeeping: the next track at the end of one, the playhead now and then
    {
        if (ended_.exchange(false)) {
            const int nx = cur_ + 1;
            if (nx < (int)titles_.size()) play(nx); else { cur_ = -1; status("End of the album."); sendNow(); }
        }
        const double t = nowSec();
        if (playing_ && t - lastNow_ > 0.5) { lastNow_ = t; sendNow(); }
        std::string st, pa; { std::lock_guard<std::mutex> l(m_); st.swap(pendStatus_); pa.swap(pendParts_); }
        if (!st.empty()) status(st);
        if (!pa.empty() && send) send("citypop parts " + pa);   // name pct|name pct|...
    }

private:
    std::mutex m_, pm_; std::condition_variable cv_;
    std::thread th_;
    bool loaded_ = false, quit_ = false;
    std::atomic<bool> cancel_{false}, playing_{false}, ended_{false};
    std::atomic<int> cur_{-1}, want_{-1};
    std::vector<std::string> files_, titles_; std::vector<double> lengths_;
    std::vector<int32_t> mix_; double pos_ = 0, lastNow_ = 0;
    std::set<int> ready_;            // tracks with a render in the cache
    std::string pendStatus_, pendParts_;

    void status(const std::string &s) { if (send) send("citypop status " + s); }
    void statusLater(const std::string &s) { std::lock_guard<std::mutex> l(m_); pendStatus_ = s; }
    std::string dir() const { return machine + "/citypop"; }
    static std::string slurp(const std::string &p) { std::ifstream in(p, std::ios::binary); return std::string((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>()); }

    void load()
    {
        if (loaded_) return;
        loaded_ = true;
        for (int k = 1; k <= 99; k++) {   // NN-*.song in order
            char pre[8]; std::snprintf(pre, sizeof pre, "%02d-", k);
            std::string f = findFile(dir(), pre, ".song");
            if (f.empty()) break;
            SongText s; std::string err;
            if (!s.parse(slurp(dir() + "/" + f), &err)) continue;
            Smf smf; const std::string mb = slurp(dir() + "/" + s.get("midi"));
            if (!smf.parse(std::vector<uint8_t>(mb.begin(), mb.end()), &err)) continue;
            const std::string t = s.get("tail");
            files_.push_back(f); titles_.push_back(s.get("title", f));
            lengths_.push_back(smf.seconds(smf.lastTick()) + (t.empty() ? 4.0 : std::atof(t.c_str())));
        }
        seedFactory();
        for (size_t i = 0; i < files_.size(); i++) if (fileExists(cachePath((int)i))) ready_.insert((int)i);
        th_ = std::thread([this] { if (lowerPriority) lowerPriority(); worker(); });
    }
    static std::string findFile(const std::string &d, const std::string &pre, const std::string &ext)
    {
#ifdef _WIN32
        WIN32_FIND_DATAA fd; HANDLE h = FindFirstFileA((d + "\\" + pre + "*" + ext).c_str(), &fd);
        if (h == INVALID_HANDLE_VALUE) return "";
        std::string n = fd.cFileName; FindClose(h); return n;
#else
        DIR *dp = opendir(d.c_str()); if (!dp) return "";
        std::string best;
        while (dirent *e = readdir(dp)) { std::string n = e->d_name; if (n.rfind(pre, 0) == 0 && n.size() > ext.size() && n.compare(n.size() - ext.size(), ext.size(), ext) == 0) best = n; }
        closedir(dp); return best;
#endif
    }
    static bool fileExists(const std::string &p) { FILE *f = std::fopen(p.c_str(), "rb"); if (f) std::fclose(f); return f != nullptr; }
    std::string cachePath(int i) const
    {
        const std::string s = slurp(dir() + "/" + files_[i]); SongText t; std::string err; t.parse(s, &err);
        const std::string k = s + slurp(dir() + "/" + t.get("midi")) + "SNDWAVE1993 1.5 render";
        std::string name = files_[i].substr(0, files_[i].size() - 5);
        return cacheDir + "/" + name + "-" + bsynth::sha1Hex(k.data(), k.size()).substr(0, 8) + ".wav";
    }
    void sendList()
    {
        if (!send) return;
        for (size_t i = 0; i < titles_.size(); i++) {
            char b[200]; std::snprintf(b, sizeof b, "citypop trk %zu %s|%d", i, titles_[i].c_str(), (int)lengths_[i]);
            send(b);
        }
        send("citypop end");
    }
    void sendNow()
    {
        if (!send) return;
        long len = 0; { std::lock_guard<std::mutex> l(pm_); len = (long)(mix_.size() / 96); }
        char b[96]; std::snprintf(b, sizeof b, "citypop now %d %d %ld %ld", cur_.load(), playing_ ? 1 : 0, (long)(pos_ / 48.0), len);
        send(b);
    }
    void play(int i)
    {
        if (i < 0 || i >= (int)titles_.size()) return;
        playing_ = false;
        { std::lock_guard<std::mutex> l(pm_); mix_.clear(); pos_ = 0; }
        cur_ = i; want_ = i;
        cancel_ = true;   // a render of another track gives way
        cv_.notify_all();
        sendNow();
    }

    // the worker: the wanted track first (then it plays), then the one after it, ahead of time
    void worker()
    {
        while (true) {
            int job = -1; bool forPlay = false;
            {
                std::unique_lock<std::mutex> l(m_);
                cv_.wait_for(l, std::chrono::milliseconds(200));
                if (quit_) return;
                const int w = want_;
                if (w >= 0) { job = w; forPlay = true; }
                else if (cur_ >= 0 && cur_ + 1 < (int)titles_.size() && !ready_.count(cur_ + 1)) job = cur_ + 1;
            }
            if (job < 0) continue;
            cancel_ = false;
            if (!ready_.count(job)) {
                if (forPlay) statusLater(prepText(job, 0));
                const bool ok = renderToCache(job, forPlay);
                if (!ok) { if (!cancel_ && forPlay) { statusLater("Track " + std::to_string(job + 1) + " could not be prepared."); want_ = -1; } continue; }
                std::lock_guard<std::mutex> l(m_); ready_.insert(job);
            }
            if (forPlay && want_ == job) {
                std::vector<int32_t> m;
                if (!loadWav(cachePath(job), m)) { std::lock_guard<std::mutex> l(m_); ready_.erase(job); continue; }
                { std::lock_guard<std::mutex> l(pm_); mix_.swap(m); pos_ = 0; }
                want_ = -1; playing_ = true;
                { std::lock_guard<std::mutex> l2(m_); pendParts_ = "-"; }
                char b[240]; std::snprintf(b, sizeof b, "Now playing: %d. %s%s", job + 1, titles_[job].c_str(),
                                            job == 0 && fileExists(cacheDir + "/FACTORY-01") ? "  (Track 1 was prepared at the factory.)" : ""); statusLater(b);
            }
        }
    }
    std::string prepText(int job, int pct) const
    {
        char b[160]; std::snprintf(b, sizeof b, "Preparing track %d of %zu (%s)... %d%%", job + 1, titles_.size(), titles_[job].c_str(), pct);
        return b;
    }
    bool renderToCache(int i, bool forPlay)
    {
        SongText song; Smf smf; std::string err;
        if (!song.parse(slurp(dir() + "/" + files_[i]), &err)) return false;
        const std::string mb = slurp(dir() + "/" + song.get("midi"));
        if (!smf.parse(std::vector<uint8_t>(mb.begin(), mb.end()), &err)) return false;
        SongPlan plan;
        if (!planSong(song, smf, loadPresets(machine), plan, err)) return false;
        const size_t N = plan.tracks.size();
        std::vector<TrackJob> jobs;
        std::vector<size_t> order(N);   // the busiest parts first: with an engine each, the slowest one sets the wait
        for (size_t k = 0; k < N; k++) order[k] = k;
        std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) { return plan.tracks[a].ev.size() > plan.tracks[b].ev.size(); });
        for (size_t q = 0; q < N; q++) {
            const size_t k = order[q];
            TrackJob J; J.machine = machine; J.core = core; J.userDir = userDir; J.dna = plan.tracks[k].dna; J.ev = plan.tracks[k].ev;
            J.tail = plan.engineTail; J.bpm = plan.engineBpm; J.lookahead48 = 150 * 48;
            jobs.push_back(std::move(J));
        }
        std::vector<std::string> stems(N); std::vector<double> prog(N, 0.0); std::mutex pm; double last = 0;
        auto progress = [&](size_t q, double f) {   // the status line, and each part's own progress (the player shows them)
            double sum = 0; bool rep = false; std::string parts;
            {
                std::lock_guard<std::mutex> l(pm); prog[q] = f; const double t = nowSec();
                for (double v : prog) sum += v;
                if (t - last > 1.0) {
                    last = t; rep = true;
                    for (size_t k = 0; k < N; k++) { char b[64]; std::snprintf(b, sizeof b, "%s%s %d", k ? "|" : "", plan.tracks[k].t->name.c_str(), (int)(100 * prog[k])); parts += b; }
                }
            }
            if (rep && forPlay) { statusLater(prepText(i, (int)(95 * sum / (double)N))); std::lock_guard<std::mutex> l(m_); pendParts_ = parts; }
        };
        auto done = [&](size_t q, TrackOut &R) {
            const std::string p = tmpDir + "/citypop-" + std::to_string(i) + "-" + std::to_string(order[q]) + ".s24";
            FILE *f = std::fopen(p.c_str(), "wb"); if (!f) return false;
            std::vector<uint8_t> b; b.reserve(R.lr.size() * 3);
            for (float x : R.lr) { const double v = x < -1 ? -1 : x > 1 ? 1 : x; const int32_t s = (int32_t)std::lround(v * 8388607.0); b.push_back((uint8_t)s); b.push_back((uint8_t)(s >> 8)); b.push_back((uint8_t)(s >> 16)); }
            const bool ok = std::fwrite(b.data(), 1, b.size(), f) == b.size(); std::fclose(f);
            stems[order[q]] = p; return ok;
        };
        auto cleanup = [&]() { for (auto &p : stems) if (!p.empty()) std::remove(p.c_str()); };
        if (!renderStems(jobs, engines, &cancel_, progress, done, err, lowerPriority)) { cleanup(); return false; }
        if (forPlay) statusLater(prepText(i, 97));
        std::vector<std::vector<float>> st(N); std::vector<MixIn> mi;
        for (size_t k = 0; k < N; k++) {
            const std::string b = slurp(stems[k]); st[k].resize(b.size() / 3);
            for (size_t j = 0; j < st[k].size(); j++) { const int32_t s = (int32_t)((uint32_t)((uint8_t)b[3 * j] | (uint8_t)b[3 * j + 1] << 8 | (uint8_t)b[3 * j + 2] << 16) << 8) >> 8; st[k][j] = (float)((double)s / 8388607.0); }
            mi.push_back({plan.tracks[k].t, &st[k]});
        }
        cleanup();
        const std::vector<double> y = mixSong(song, plan.bpm, plan.lengthSec, mi, nullptr, &cancel_);
        if (y.empty() || cancel_) return false;
        makeDir(cacheDir);
        const std::string out = cachePath(i), part = out + ".part";
        writeMixWav(part, y);
        std::remove(out.c_str());
        return std::rename(part.c_str(), out.c_str()) == 0;
    }
    // the factory's track 1 into the cache, once (not after `clear`: then every track is prepared here)
    void seedFactory()
    {
        if (files_.empty() || fileExists(cacheDir + "/NOFACTORY") || fileExists(cachePath(0))) return;
        const std::string b = slurp(dir() + "/factory-01.wav");
        if (b.size() < 44 || b.compare(0, 4, "RIFF") || (uint8_t)b[34] != 16) return;
        std::vector<double> y((b.size() - 44) / 2);
        for (size_t j = 0; j < y.size(); j++) y[j] = (double)(int16_t)((uint8_t)b[44 + 2 * j] | (uint8_t)b[45 + 2 * j] << 8) / 32768.0;
        makeDir(cacheDir);
        writeMixWav(cachePath(0), y);
        if (FILE *f = std::fopen((cacheDir + "/FACTORY-01").c_str(), "wb")) { std::fputs("Track 1 was prepared at the factory.\n", f); std::fclose(f); }
    }
    void clear()   // every render discarded; track 1 is prepared here from now on
    {
        { std::lock_guard<std::mutex> l(m_); cancel_ = true; }
        for (size_t i = 0; i < files_.size(); i++) std::remove(cachePath((int)i).c_str());
        std::remove((cacheDir + "/FACTORY-01").c_str());
        makeDir(cacheDir);
        if (FILE *f = std::fopen((cacheDir + "/NOFACTORY").c_str(), "wb")) { std::fputs("Every track is prepared on this computer.\n", f); std::fclose(f); }
        { std::lock_guard<std::mutex> l(m_); ready_.clear(); }
        status("The renders are discarded. Every track will be prepared on this computer.");
    }
    static void makeDir(const std::string &d)
    {
#ifdef _WIN32
        CreateDirectoryA(d.c_str(), nullptr);
#else
        mkdir(d.c_str(), 0755);
#endif
    }
    static bool loadWav(const std::string &p, std::vector<int32_t> &m)   // writeMixWav's 24-bit stereo
    {
        const std::string b = slurp(p);
        if (b.size() < 44 || b.compare(0, 4, "RIFF")) return false;
        const size_t n = (b.size() - 44) / 3; m.resize(n);
        for (size_t j = 0; j < n; j++) { const size_t o = 44 + 3 * j; m[j] = (int32_t)((uint32_t)((uint8_t)b[o] | (uint8_t)b[o + 1] << 8 | (uint8_t)b[o + 2] << 16) << 8) >> 8; }
        return n > 0;
    }
};

}  // namespace b16song

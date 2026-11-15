// SNDWAVE2000: the Song tab as the plugin sees it (the session itself is SongTab.h, built in SongTab.cpp).
// SongTab.cpp is compiled without -ffast-math (DPF's default): the song's timing, the engines' event stamps and
// the mix must come out exactly as render311 and songrender compute them.
#pragma once
#include <cstdint>
#include <functional>
#include <map>
#include <string>
#include <vector>

namespace b16song {
class Session;
class CityPop;
class SongTab {
public:
    SongTab();
    ~SongTab();
    void configure(const std::string &machine, const std::string &core, const std::string &userDir, const std::string &tmpDir,
                   std::function<void(const std::string &)> send);
    void stateLines(std::map<std::string, std::string> &extra) const;
    void loadState(const std::map<std::string, std::string> &extra);
    std::vector<uint8_t> sngBytes() const;
    bool mixWav(std::vector<uint8_t> &out) const;
    bool line(const std::string &ln, int &fileReq, std::string &defName);
    void process(float *L, float *R, uint32_t frames, double sr);
    void poll();
    void setDefaultDna(const std::string &d);
    void loadLater(const std::string &path, std::vector<uint8_t> bytes);
    void shutdown();
private:
    Session *s_;
    CityPop *c_;   // CITYPOP.EXE (CityPop.h)
};
}  // namespace b16song

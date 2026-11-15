// SNDWAVE1993: the Song tab's session, in a translation unit of its own (see SongSession.h).
#include "SongSession.h"
#include "SongTab.h"
#include "CityPop.h"

namespace b16song {
SongTab::SongTab() : s_(new Session()), c_(new CityPop()) {}
SongTab::~SongTab() { delete c_; delete s_; }
void SongTab::configure(const std::string &machine, const std::string &core, const std::string &userDir, const std::string &tmpDir,
                        std::function<void(const std::string &)> send)
{
    s_->machine = machine; s_->core = core; s_->userDir = userDir; s_->tmpDir = tmpDir; s_->send = send;
    c_->machine = machine; c_->core = core; c_->userDir = userDir; c_->tmpDir = tmpDir; c_->cacheDir = userDir + "/CITYPOP1993";
    c_->send = std::move(send); c_->lowerPriority = lowerThreadPriority;
    { const unsigned hc = std::thread::hardware_concurrency(); c_->engines = (int)std::max(1u, std::min(8u, hc > 2 ? hc - 2 : 1u)); }   // (a user's explicit request: cores - 2, up to 8, below normal priority)
    if (const char *e = std::getenv("BASILISK16_CITYPOP_ENGINES")) if (std::atoi(e) > 0) c_->engines = std::min(8, std::atoi(e));
}
void SongTab::stateLines(std::map<std::string, std::string> &extra) const { s_->stateLines(extra); }
void SongTab::loadState(const std::map<std::string, std::string> &extra) { s_->loadState(extra); }
std::vector<uint8_t> SongTab::sngBytes() const { return s_->sngBytes(); }
bool SongTab::mixWav(std::vector<uint8_t> &out) const { return s_->mixWav(out); }
bool SongTab::line(const std::string &ln, int &fileReq, std::string &defName) { return c_->line(ln) || s_->line(ln, fileReq, defName); }
void SongTab::process(float *L, float *R, uint32_t frames, double sr) { s_->process(L, R, frames, sr); c_->process(L, R, frames, sr); }
void SongTab::poll() { s_->poll(); c_->poll(); }
void SongTab::setDefaultDna(const std::string &d) { s_->setDefaultDna(d); }
void SongTab::loadLater(const std::string &path, std::vector<uint8_t> bytes) { s_->loadLater(path, std::move(bytes)); }
void SongTab::shutdown() { c_->shutdown(); s_->shutdown(); }
}  // namespace b16song

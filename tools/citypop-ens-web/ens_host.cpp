// SNDWAVE2000 Ensemble in the browser (/citypop-ens/): the host. One Windows 3.11 (the engine thread and DOSBox Pure
// with the 128-voice lane card, as the plugin), ENSEMBLE.EXE in it, and the album player (ensemble/player/
// AlbumPlayer.h, the same code as the native albumrender): every lane switches preset as its schedule says, and its
// notes go to Windows a lookahead before they sound, stamped with their DAC sample.
//
// Everything here runs on the worker's own thread (worker-main.js): the tick, the pointer, the keys.
#include "engine.h"
#include "AlbumPlayer.h"
#include <emscripten.h>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

extern "C" volatile int web_snapshot_request;
extern "C" volatile int web_mouse_dx, web_mouse_dy;

namespace {
bshm *S = nullptr;
bs_engine *E = nullptr;
std::unique_ptr<ensalbum::Player> P;
std::string albumText;
bool hello = false, ready = false, wantGo = false;
int playFrom = -1, phase = 0;          // phase: 0 idle, 1 building the first presets, 2 playing
uint64_t dac0 = 0;
std::vector<uint16_t> words; std::string frag;
std::vector<std::string> guestLog;
uint32_t notesSent = 0, linesSent = 0;
float outGain = 1.f;
uint32_t *frameBuf = nullptr; uint32_t frameSeq = 0xFFFFFFFF, frameW = 0, frameH = 0;
int scheme = 0;

void sendLine(const char *text, uint32_t id = 0, uint64_t at = 0)
{
    const int len = (int)std::strlen(text);
    int pos = 0;
    do {
        const int m = len - pos > 240 ? 240 : len - pos;
        const bool last = pos + m >= len;
        const int nw = 3 + (m + 1) / 2;
        uint16_t w[136];
        w[0] = (uint16_t)(((last ? 4 : 8) << 8) | nw);
        w[1] = (uint16_t)(last ? id : 0); w[2] = (uint16_t)((last ? id : 0) >> 16);
        for (int k = 0; k < (m + 1) / 2; k++) {
            const uint8_t a = (uint8_t)text[pos + 2 * k], b = 2 * k + 1 < m ? (uint8_t)text[pos + 2 * k + 1] : 0;
            w[3 + k] = (uint16_t)(a | (b << 8));
        }
        if (!(S->ev_w == S->ev_r && bs_engine_event(E, w, nw, last ? id : 0, last ? at : 0))) {
            if (S->ev_w - S->ev_r >= BSHM_EV) break;
            bshm_ev &e = S->ev[S->ev_w % BSHM_EV];
            std::memcpy(e.w, w, sizeof(uint16_t) * nw);
            e.n = (uint32_t)nw; e.id = last ? id : 0; e.at = last ? at : 0;
            __sync_synchronize();
            S->ev_w++;
        }
        pos += m;
    } while (pos < len);
    linesSent++;
}
void sendStr(const std::string &l, uint32_t id, uint64_t at)
{
    sendLine(l.c_str(), id, at);
    if (l.find(" on ") != std::string::npos) notesSent++;
}
std::string jsonEsc(const std::string &s)
{
    std::string o;
    for (char c : s) { if (c == '"' || c == '\\') { o += '\\'; o += c; } else if ((unsigned char)c < 32) o += ' '; else o += c; }
    return o;
}
void onLine(const std::string &l)
{
    if (guestLog.size() < 200) guestLog.push_back(l);
    if (l == "ready") { ready = true; if (scheme) sendLine("colors 1"); return; }   // (again: assembling repaints in the stock colours)
    if (P) P->reply(l);
}
}  // namespace

extern "C" {

EMSCRIPTEN_KEEPALIVE int ens_start(const char *conf, const char *state, const char *makeState, const char *logPath, int leadFrames, const char *libNames)
{
    if (S) return 0;
    {   std::vector<std::string> names; std::string cur;
        for (const char *p = libNames ? libNames : ""; ; p++) {
            if (!*p || *p == '\n') { while (!cur.empty() && (cur.back() == '\r' || cur.back() == ' ')) cur.pop_back(); if (!cur.empty()) names.push_back(cur); cur.clear(); if (!*p) break; }
            else cur += *p;
        }
        bsynth::setLibrary(names); }
    S = (bshm *)std::calloc(1, sizeof(bshm));
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
    S->lead = leadFrames > 0 ? (uint32_t)leadFrames : 2048; S->realtime = 0; S->vid_want = 1;
    E = bs_engine_start(S, "static", conf, state && *state ? state : nullptr, makeState && *makeState ? makeState : nullptr, logPath && *logPath ? logPath : nullptr);
    return E ? 1 : 0;
}
EMSCRIPTEN_KEEPALIVE bshm *ens_shm() { return S; }
EMSCRIPTEN_KEEPALIVE const int *ens_layout()
{
    static int o[29];
    o[0] = offsetof(bshm, state); o[1] = offsetof(bshm, quit); o[2] = offsetof(bshm, host_beat); o[3] = offsetof(bshm, engine_beat);
    o[4] = offsetof(bshm, dac_w); o[5] = offsetof(bshm, host_r); o[6] = offsetof(bshm, realtime); o[7] = offsetof(bshm, vid_seq);
    o[8] = offsetof(bshm, vid_w); o[9] = offsetof(bshm, vid_h); o[10] = offsetof(bshm, vid_want); o[11] = offsetof(bshm, mouse_x);
    o[12] = offsetof(bshm, mouse_y); o[13] = offsetof(bshm, mouse_btn); o[14] = offsetof(bshm, mouse_seq); o[15] = offsetof(bshm, ring);
    o[16] = offsetof(bshm, vid); o[17] = BSHM_RING; o[18] = offsetof(bshm, underruns); o[19] = offsetof(bshm, emu_load);
    o[20] = offsetof(bshm, offline); o[21] = offsetof(bshm, grant_until); o[22] = offsetof(bshm, sched_late); o[23] = offsetof(bshm, error);
    o[24] = (int)(intptr_t)&outGain; o[25] = sizeof(bshm); o[26] = BSHM_W; o[27] = BSHM_H; o[28] = offsetof(bshm, lead);
    return o;
}
// the album (album_ens.py's schedule text)
EMSCRIPTEN_KEEPALIVE int ens_album(const char *text) { albumText = text ? text : ""; return (int)albumText.size(); }
// play the album from track t (0-based): Windows builds that track's presets, then the clock starts
EMSCRIPTEN_KEEPALIVE void ens_play(int t) { playFrom = t; }
EMSCRIPTEN_KEEPALIVE void ens_stop() { if (P) sendLine("panic"); P.reset(); phase = 0; }
EMSCRIPTEN_KEEPALIVE void ens_colors(int which) { scheme = which; if (hello) sendLine(which ? "colors 1" : "colors 0"); }

static bool quiet = false;   // the snapshot maker: Windows is listened to, but told nothing (no hello, no go)
EMSCRIPTEN_KEEPALIVE void ens_quiet(int q) { quiet = q != 0; }
EMSCRIPTEN_KEEPALIVE void ens_tick()
{
    if (!S) return;
    if (!quiet && !hello && S->state >= BS_RUNNING && S->state != BS_FAILED) {
        hello = true;
        sendLine("packs rainy-loft");
        if (scheme) sendLine("colors 1");
        sendLine("go");
    }
    const auto send = [](const std::string &l, uint32_t id, uint64_t at) { sendStr(l, id, at); };
    if (hello && ready && playFrom >= 0) {   // a new start: a fresh player from that track
        P.reset(new ensalbum::Player());
        P->lookahead = 0.6;
        if (!P->load(albumText)) P.reset();
        else { if (playFrom >= (int)P->tracks.size()) playFrom = 0; P->prepare(playFrom, send); phase = 1; }
        playFrom = -1;
    }
    // Windows' replies
    while (S->rep_r != S->rep_w) { words.push_back((uint16_t)S->rep[S->rep_r % BSHM_REP]); __sync_synchronize(); S->rep_r++; }
    size_t i = 0;
    while (i < words.size()) {
        const int n = words[i] & 0xFF ? words[i] & 0xFF : 1;
        if (i + n > words.size()) break;
        const int ty = words[i] >> 8;
        if (ty == 3 || ty == 7) {
            for (int k = 1; k < n; k++) { const char a = (char)(words[i + k] & 0xFF), b = (char)(words[i + k] >> 8); if (a) frag += a; if (a && b) frag += b; }
            if (ty == 3) { onLine(frag); frag.clear(); }
        }
        i += n;
    }
    words.erase(words.begin(), words.begin() + i);
    if (P && phase == 1 && P->ready()) {   // the first presets are built: the clock starts a moment after Windows' now
        dac0 = S->dac_w + 9600;
        P->begin(dac0);
        phase = 2;
    }
    if (P && phase == 2) P->tick(S->dac_w, send);
}

// where playback is: the album's time at the AudioWorklet's position (host_r), and the track there
EMSCRIPTEN_KEEPALIVE double ens_pos() { return (P && phase == 2) ? P->albumTime(S->host_r) : -1; }
EMSCRIPTEN_KEEPALIVE double ens_emutime() { return (P && phase == 2) ? P->albumTime(S->dac_w) : -1; }

EMSCRIPTEN_KEEPALIVE void ens_mouse(int x, int y)
{
    if (!S) return;
    if (x < 0) x = 0; if (y < 0) y = 0; if (x >= BSHM_W) x = BSHM_W - 1; if (y >= BSHM_H) y = BSHM_H - 1;
    if (x == S->mouse_x && y == S->mouse_y) return;
    if (S->mouse_btn & 1) { __sync_fetch_and_add(&web_mouse_dx, x - S->mouse_x); __sync_fetch_and_add(&web_mouse_dy, y - S->mouse_y); }
    S->mouse_x = x; S->mouse_y = y; S->mouse_seq++;
}
EMSCRIPTEN_KEEPALIVE void ens_button(int bit, int down)
{
    if (!S) return;
    uint32_t btn = S->mouse_btn;
    if (down) btn |= (uint32_t)bit; else btn &= ~(uint32_t)bit;
    if (down && bit == 1) { const uint32_t w = S->click_w; S->click_x[w % 4] = S->mouse_x; S->click_y[w % 4] = S->mouse_y; __sync_synchronize(); S->click_w = w + 1; }
    S->mouse_btn = btn; S->mouse_seq++;
}
EMSCRIPTEN_KEEPALIVE void ens_key(int down, int rk)
{
    if (!S || S->key_w - S->key_r >= BSHM_KEYS) return;
    S->keys[S->key_w % BSHM_KEYS] = (down ? 0x80000000u : 0u) | (uint32_t)rk;
    __sync_synchronize(); S->key_w++;
}
EMSCRIPTEN_KEEPALIVE void ens_pause(int p) { if (S) { S->grant_until = 0; S->offline = p ? 1 : 0; } }
EMSCRIPTEN_KEEPALIVE void ens_grant(int frames) { if (S) { S->offline = 1; S->grant_until = S->dac_w + (uint64_t)frames; S->host_beat++; } }
EMSCRIPTEN_KEEPALIVE void ens_snapshot() { web_snapshot_request = 1; }

EMSCRIPTEN_KEEPALIVE uint32_t *ens_frame()
{
    if (!S) return nullptr;
    if (!frameBuf) frameBuf = (uint32_t *)std::calloc(2 + BSHM_W * BSHM_H, 4);
    const uint32_t seq = S->vid_seq;
    if ((seq & 1) || seq == frameSeq || !S->vid_w) return nullptr;
    const uint32_t w = S->vid_w, h = S->vid_h, n = w * h;
    uint32_t *d = frameBuf + 2; const volatile uint32_t *v = S->vid;
    static bool dirty = false;
    bool changed = dirty || w != frameW || h != frameH;
    for (uint32_t k = 0; k < n; k++) {
        const uint32_t x = v[k];
        const uint32_t y = 0xFF000000u | (x & 0x0000FF00u) | ((x >> 16) & 0xFFu) | ((x & 0xFFu) << 16);
        if (y != d[k]) { d[k] = y; changed = true; }
    }
    __sync_synchronize();
    if (S->vid_seq != seq) { dirty = changed; return nullptr; }
    frameSeq = seq; dirty = false;
    if (!changed) return nullptr;
    frameW = w; frameH = h; frameBuf[0] = w; frameBuf[1] = h;
    return frameBuf;
}

EMSCRIPTEN_KEEPALIVE const char *ens_info(int withLog)
{
    static std::string s;
    char b[640];
    int track = -1, sw = 0, builds = 0, late = 0;
    if (P && phase == 2) {
        const double t = P->albumTime(S->host_r);
        for (auto &tr : P->tracks) if (t >= tr.start - 0.5) track = tr.i;
        for (auto &st : P->stats()) { sw += st.switches; builds += st.builds; late += st.late; }
    }
    std::snprintf(b, sizeof b, "{\"state\":%u,\"ready\":%d,\"phase\":%d,\"dac\":%llu,\"host\":%llu,\"load\":%u,\"late\":%u,\"ontime\":%u,"
                  "\"notes\":%u,\"lines\":%u,\"pos\":%.3f,\"emu\":%.3f,\"track\":%d,\"switches\":%d,\"builds\":%d,\"switchLate\":%d,\"lead\":%u,\"under\":%u,",
                  S ? S->state : 0, ready, phase, S ? (unsigned long long)S->dac_w : 0ull, S ? (unsigned long long)S->host_r : 0ull,
                  S ? S->emu_load : 0, S ? S->sched_late : 0, S ? S->sched_ontime : 0, notesSent, linesSent, ens_pos(), ens_emutime(),
                  track, sw, builds, late, S ? S->lead : 0, S ? S->underruns : 0);
    s = b;
    s += "\"error\":\"" + jsonEsc(S ? std::string(S->error) : "") + "\",\"log\":[";
    if (withLog) for (size_t k = 0; k < guestLog.size(); k++) s += (k ? ",\"" : "\"") + jsonEsc(guestLog[k]) + "\"";
    s += "]}";
    if (withLog) guestLog.clear();
    return s.c_str();
}
// per track: switches, builds, seconds building, notes late for a switch (JSON array), for the page's report
EMSCRIPTEN_KEEPALIVE const char *ens_stats()
{
    static std::string s; s = "[";
    if (P) { auto st = P->stats(); for (size_t k = 0; k < st.size(); k++) { char b[160]; std::snprintf(b, sizeof b, "%s[%d,%d,%.2f,%d,%d]", k ? "," : "", st[k].switches, st[k].builds, st[k].buildSecs, st[k].late, st[k].underBuild); s += b; } }
    s += "]";
    return s.c_str();
}

}  // extern "C"

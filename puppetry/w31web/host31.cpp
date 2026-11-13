// BASILISK 3.11 in the browser on the DOSBox Pure web engine: the host side. The engine thread (web_engine.c, a
// copy of tools/basilisk16-web's, which runs packages/basilisk-synth-311/engine/engine.c) runs Windows for
// Workgroups 3.11; this file is the page's link to it. BASILISK.EXE talks to the page through the BSYN card's
// packets: its lines come out as reports (type 7 = more, 3 = the line ends) and the page's lines go in as events
// (type 8 = more, 4 = the line ends). There is no sound: the engine paces itself by its own clock.
#include "engine.h"
#include <emscripten.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <string>
#include <vector>

extern "C" volatile int web_snapshot_request;
extern "C" volatile int web_mouse_dx, web_mouse_dy;

namespace {
bshm *S = nullptr;
bs_engine *E = nullptr;
std::vector<uint16_t> words;
std::string frag, lines;             // lines from Windows, each ended by \x04, until the worker takes them
std::deque<std::vector<uint16_t>> outq;   // packets for Windows that did not fit the event ring yet
uint32_t *frameBuf = nullptr; uint32_t frameSeq = 0xFFFFFFFF, frameW = 0, frameH = 0;
uint32_t linesIn = 0, linesOut = 0;
float relScale = 1.f, relAccX = 0, relAccY = 0; double relDownT = 0;

void relFlush()
{
    if (emscripten_get_now() - relDownT < 120) return;
    const int dx = (int)relAccX, dy = (int)relAccY;
    relAccX -= dx; relAccY -= dy;
    if (dx) __sync_fetch_and_add(&web_mouse_dx, dx);
    if (dy) __sync_fetch_and_add(&web_mouse_dy, dy);
}
void pump()
{
    while (!outq.empty() && S->ev_w - S->ev_r < BSHM_EV) {
        const std::vector<uint16_t> &w = outq.front();
        bshm_ev &e = S->ev[S->ev_w % BSHM_EV];
        std::memcpy(e.w, w.data(), sizeof(uint16_t) * w.size());
        e.n = (uint32_t)w.size(); e.id = 0; e.at = 0;
        __sync_synchronize();
        S->ev_w++;
        outq.pop_front();
    }
}
}  // namespace

extern "C" {

EMSCRIPTEN_KEEPALIVE int b31_start(const char *conf, const char *state, const char *makeState, const char *logPath)
{
    if (S) return 0;
    S = (bshm *)std::calloc(1, sizeof(bshm));
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
    S->lead = 2048; S->realtime = 0; S->vid_want = 1;
    E = bs_engine_start(S, "static", conf, state && *state ? state : nullptr, makeState && *makeState ? makeState : nullptr,
                        logPath && *logPath ? logPath : nullptr);
    return E ? 1 : 0;
}
EMSCRIPTEN_KEEPALIVE bshm *b31_shm() { return S; }
EMSCRIPTEN_KEEPALIVE int b31_dac_off() { return (int)offsetof(bshm, dac_w); }

// one line to BASILISK.EXE (bytes 1..255, no NUL), in packets of up to 240 bytes
EMSCRIPTEN_KEEPALIVE void b31_send(const char *text)
{
    if (!S) return;
    const int len = (int)std::strlen(text);
    int pos = 0;
    do {
        const int m = len - pos > 240 ? 240 : len - pos;
        const bool last = pos + m >= len;
        std::vector<uint16_t> w(3 + (m + 1) / 2);
        w[0] = (uint16_t)(((last ? 4 : 8) << 8) | w.size()); w[1] = w[2] = 0;
        for (int k = 0; k < (m + 1) / 2; k++) {
            const uint8_t a = (uint8_t)text[pos + 2 * k], b = 2 * k + 1 < m ? (uint8_t)text[pos + 2 * k + 1] : 0;
            w[3 + k] = (uint16_t)(a | (b << 8));
        }
        outq.push_back(w);
        pos += m;
    } while (pos < len);
    linesOut++;
    pump();
}

// the periodic work: packets in and out. Returns the lines Windows sent since the last call ("" if none).
EMSCRIPTEN_KEEPALIVE const char *b31_tick()
{
    static std::string out;
    out.clear();
    if (!S) return "";
    if (S->mouse_btn & 1) relFlush();
    pump();
    while (S->rep_r != S->rep_w) { words.push_back((uint16_t)S->rep[S->rep_r % BSHM_REP]); __sync_synchronize(); S->rep_r++; }
    size_t i = 0;
    while (i < words.size()) {
        const int n = words[i] & 0xFF ? words[i] & 0xFF : 1;
        if (i + n > words.size()) break;
        const int ty = words[i] >> 8;
        if (ty == 3 || ty == 7) {
            for (int k = 1; k < n; k++) {
                const char a = (char)(words[i + k] & 0xFF), b = (char)(words[i + k] >> 8);
                if (a) frag += a; if (a && b) frag += b;
            }
            if (ty == 3) { lines += frag; lines += '\x04'; frag.clear(); linesIn++; }
        }
        i += n;
    }
    words.erase(words.begin(), words.begin() + i);
    out.swap(lines);
    return out.c_str();
}

EMSCRIPTEN_KEEPALIVE void b31_mouse(int x, int y)
{
    if (!S) return;
    if (x < 0) x = 0; if (y < 0) y = 0; if (x >= BSHM_W) x = BSHM_W - 1; if (y >= BSHM_H) y = BSHM_H - 1;
    if (x == S->mouse_x && y == S->mouse_y) return;
    if (S->mouse_btn & 1) { relAccX += (x - S->mouse_x) * relScale; relAccY += (y - S->mouse_y) * relScale; relFlush(); }
    S->mouse_x = x; S->mouse_y = y; S->mouse_seq++;
}
EMSCRIPTEN_KEEPALIVE void b31_button(int bit, int down)
{
    if (!S) return;
    uint32_t btn = S->mouse_btn;
    if (down) btn |= (uint32_t)bit; else btn &= ~(uint32_t)bit;
    if (bit == 1) { relAccX = relAccY = 0; relDownT = emscripten_get_now(); }
    if (down && bit == 1) {
        const uint32_t w = S->click_w;
        S->click_x[w % 4] = S->mouse_x; S->click_y[w % 4] = S->mouse_y;
        __sync_synchronize();
        S->click_w = w + 1;
    }
    S->mouse_btn = btn; S->mouse_seq++;
}
EMSCRIPTEN_KEEPALIVE void b31_relscale(float f) { relScale = f; }
EMSCRIPTEN_KEEPALIVE void b31_key(int down, int rk)
{
    if (!S || S->key_w - S->key_r >= BSHM_KEYS) return;
    S->keys[S->key_w % BSHM_KEYS] = (down ? 0x80000000u : 0u) | (uint32_t)rk;
    __sync_synchronize();
    S->key_w++;
}
// build time: run without a clock up to `frames` further; paused: the engine waits
EMSCRIPTEN_KEEPALIVE void b31_grant(int frames) { if (S) { S->offline = 1; S->grant_until = S->dac_w + (uint64_t)frames; S->host_beat++; } }
EMSCRIPTEN_KEEPALIVE void b31_pause(int p) { if (S) { S->grant_until = 0; S->offline = p ? 1 : 0; S->host_r = S->dac_w > 2048 ? S->dac_w - 2048 : 0; } }
EMSCRIPTEN_KEEPALIVE void b31_snapshot() { web_snapshot_request = 1; }
EMSCRIPTEN_KEEPALIVE void b31_stop() { if (E) { bs_engine_stop(E); E = nullptr; } }

// the screen as RGBA, if Windows drew a new frame since the last call (else 0). [0] = w, [1] = h, then pixels.
EMSCRIPTEN_KEEPALIVE uint32_t *b31_frame()
{
    if (!S) return nullptr;
    if (!frameBuf) frameBuf = (uint32_t *)std::calloc(2 + BSHM_W * BSHM_H, 4);
    const uint32_t seq = S->vid_seq;
    if ((seq & 1) || seq == frameSeq || !S->vid_w) return nullptr;
    const uint32_t w = S->vid_w, h = S->vid_h, n = w * h;
    uint32_t *d = frameBuf + 2;
    const volatile uint32_t *v = S->vid;
    static bool dirty = false;
    bool changed = dirty || w != frameW || h != frameH;
    for (uint32_t i = 0; i < n; i++) {
        const uint32_t x = v[i];
        const uint32_t y = 0xFF000000u | (x & 0x0000FF00u) | ((x >> 16) & 0xFFu) | ((x & 0xFFu) << 16);
        if (y != d[i]) { d[i] = y; changed = true; }
    }
    __sync_synchronize();
    if (S->vid_seq != seq) { dirty = changed; return nullptr; }
    frameSeq = seq; dirty = false;
    if (!changed) return nullptr;
    frameW = w; frameH = h; frameBuf[0] = w; frameBuf[1] = h;
    return frameBuf;
}

EMSCRIPTEN_KEEPALIVE const char *b31_info()
{
    static char b[400];
    std::snprintf(b, sizeof b, "{\"state\":%u,\"dac\":%llu,\"beat\":%llu,\"load\":%u,\"in\":%u,\"out\":%u,\"queued\":%u,\"error\":\"%s\"}",
                  S ? S->state : 0, S ? (unsigned long long)S->dac_w : 0ull, S ? (unsigned long long)S->engine_beat : 0ull,
                  S ? S->emu_load : 0, linesIn, linesOut, (unsigned)outq.size(), S ? S->error : "");
    for (char *p = b; *p; p++) if (*p == '\\') *p = '/';
    return b;
}
}  // extern "C"

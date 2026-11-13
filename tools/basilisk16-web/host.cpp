// BASILISK 16 in the browser: the host side. It is the plugin's host logic (packages/basilisk-synth-311/plugin/
// Basilisk16Plugin.cpp, run() and work()) on one thread: the shared core's voice allocator picks the recorder,
// Windows is told the rate and volume, and every note is stamped with the DAC sample it must start on. The engine
// thread (web_engine.c) runs Windows 3.11 exactly as in the plugin; the AudioWorklet reads the card's DAC ring
// straight out of the shared WebAssembly memory and writes back how far it has played (host_r).
//
// Everything here is called from the worker's own thread (b16-worker.js): the tick, the MIDI, the DNA.
#include "engine.h"
#include "dna.h"
#include "voices.h"
#include "proto.h"
#include "state.h"

#include <emscripten.h>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

using namespace bsynth;

extern "C" volatile int web_snapshot_request;
// the card's ADC (RECORDING.md R1, STATE.md 4): the microphone goes in stamped on the DAC clock
extern "C" void bsyn_host_input(uint64_t at, const float *lr, int n);
extern "C" void bsyn_host_insrc(int src);
extern "C" int bsyn_host_instate(uint64_t *start, uint32_t *bytes, uint32_t *overruns);
extern "C" uint64_t bsyn_host_dac(void);
static uint64_t micAt = 0;
extern "C" volatile int web_mouse_dx, web_mouse_dy;   // web_engine.c: relative motion for the emulated mouse
static float relScale = 1.f, relAccX = 0, relAccY = 0;
static double relDownT = 0;
// the drag's motion goes to the emulated mouse only once the press has reached Windows at its own place (the
// engine moves the pointer there first and holds the button for 3 frames): until then it is kept
static void relFlush()
{
    if (emscripten_get_now() - relDownT < 120) return;
    const int dx = (int)relAccX, dy = (int)relAccY;
    relAccX -= dx; relAccY -= dy;
    if (dx) __sync_fetch_and_add(&web_mouse_dx, dx);
    if (dy) __sync_fetch_and_add(&web_mouse_dy, dy);
}

namespace {

bshm *S = nullptr;
bs_engine *E = nullptr;
uint32_t lead = 2048, kLat = 2048 + 1536;

std::string dnaText;
Dna dnaNow;                         // what the voices play
bool hello = false, ready = false, building = false, inFlight = false, dnaToGuest = false, lenvDirty = false;
std::string cacheSig;
LayerInfo layerCache[kMaxLayers];
Dna stagedDna; std::string stagedSig; LayerInfo stagedLayers[kMaxLayers];
Voices voices{48000};
int cc1 = 0, cc1Applied = 0;
uint32_t nextId = 0;
std::vector<uint16_t> words; std::string frag;
std::vector<std::string> guestLog;      // the guest's lines, for the page (tests)
uint32_t notesSent = 0, keysFromWindows = 0, builtCount = 0;
std::string lastBuiltDna;
float outGain = 1.f;               // the DNA's G, read by the AudioWorklet (as the plugin applies it to its output)
uint32_t *frameBuf = nullptr; uint32_t frameSeq = 0xFFFFFFFF, frameW = 0, frameH = 0;

std::string sigOf(const Dna &d)
{
    std::string s;
    for (auto &L : d.layers) {
        s += std::to_string(L.source) + L.sourceName + ":" + std::to_string(L.first) + ":" + std::to_string(L.count) + ":";
        for (auto &st : L.steps) { s += st.op; s += std::to_string(st.arg) + "." + std::to_string(st.ms) + "." + std::to_string(st.sound) + st.name; }
        s += "|";
    }
    return s;
}

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
}
void trimSend(char *b) { size_t n = std::strlen(b); if (n && b[n - 1] == '\n') b[n - 1] = 0; sendLine(b); }

// the DNA as it sounds: macros applied, the mod wheel added to Macro 1 (as the plugin)
Dna effective(const Dna &written)
{
    const Dna base = applyMacros(written);
    cc1Applied = cc1;
    if (!cc1) return base;
    Dna w = written;
    w.g.macro[0] = std::min(100, std::max(0, written.g.macro[0] + (cc1 * 100 + 63) / 127));
    Dna d = applyMacros(w);
    return sigOf(d) == sigOf(base) ? d : base;
}

void adopt(const Dna &d)
{
    Cmd c[1];
    voices.setDna(d, c);
    for (int i = 0; i < kMaxLayers; i++)
        if (layerCache[i].known) voices.setLayerInfo(i, layerCache[i].first, layerCache[i].count, layerCache[i].rate, layerCache[i].frames);
    dnaNow = d;
    outGain = (float)std::pow(10.0, d.g.gainDb / 20.0);
}

void setDna(const std::string &text, bool toGuest, bool fromGuest = false)
{
    const Dna written = parse(text);
    Dna d = effective(written);
    dnaText = written.canonical;
    lenvDirty = true;
    if (toGuest && !fromGuest) dnaToGuest = true;
    const std::string sig = sigOf(d);
    if (sig == cacheSig || (cacheSig.empty() && sig == sigOf(parse(kDefaultDna)))) {
        if (cacheSig.empty()) layerCache[0] = LayerInfo{0, 16, 22050, 11466, true};   // the snapshot's recorders hold DING
        cacheSig = sig;
        adopt(d);
    } else {
        stagedDna = d; stagedSig = sig;
        for (auto &c : stagedLayers) c = LayerInfo();
        if (fromGuest) inFlight = true;
    }
}

uint64_t nowStamp()
{
    // the AudioWorklet's play position plus the latency; never behind what the engine has already made
    // (the AudioWorklet raises the lead after a gap: the latency follows it)
    const uint64_t a = S->host_r + S->lead + 1536, b = S->dac_w + 768;
    return a > b ? a : b;
}

void playMidi(uint8_t st0, uint8_t d1, uint8_t d2, bool fromWindows)
{
    const uint64_t at = nowStamp();
    const uint8_t st = st0 & 0xF0;
    Cmd c[kMaxCmds]; int n = 0;
    char t[48];
    if (st == 0x90 && d2 > 0) { n = voices.noteOn(d1, d2, at, c); if (!fromWindows && hello) { std::snprintf(t, sizeof t, "show %u %u", d1, d2); sendLine(t); } }
    else if (st == 0x80 || st == 0x90) { n = voices.noteOff(d1, at, c); if (!fromWindows && hello) { std::snprintf(t, sizeof t, "show %u 0", d1); sendLine(t); } }
    else if (st == 0xB0) {
        if (d1 == 64) n = voices.sustain(d2 >= 64, at, c);
        else if (d1 == 120 || d1 == 123) n = voices.allOff(c);
        else if (d1 == 1) {
            cc1 = d2;
            if (!fromWindows && hello) { std::snprintf(t, sizeof t, "cc 1 %u", d2); sendLine(t); }
            setDna(dnaText, false);   // the mod wheel moved: the sound follows (no DNA to Windows)
        }
    } else if (st == 0xE0) {
        const int v = (d1 | (d2 << 7)) - 8192;
        voices.bend(v / 8192.0);
        if (!fromWindows && hello) { std::snprintf(t, sizeof t, "bend %d", v); sendLine(t); }
    }
    for (int k = 0; k < n; k++) {
        char line[64];
        uint64_t when = at;
        if (c[k].kind == Cmd::On && c[k].delayMs) { when += (uint64_t)c[k].delayMs * 48; c[k].delayMs = 0; }
        proto::cmd(line, sizeof line, c[k]);
        line[std::strlen(line) - 1] = 0;
        sendLine(line, ++nextId, when);
        notesSent++;
    }
}

void onLine(const std::string &line)
{
    if (guestLog.size() < 4000) guestLog.push_back(line);
    proto::Reply r = proto::parse(line);
    switch (r.kind) {
    case proto::Reply::Ready: ready = true; break;
    case proto::Reply::Built:
        if (inFlight) {
            cacheSig = stagedSig;
            for (int i = 0; i < kMaxLayers; i++) layerCache[i] = stagedLayers[i];
            adopt(stagedDna);
            inFlight = false;
        }
        building = false; builtCount++; lastBuiltDna = dnaText;
        break;
    case proto::Reply::Layer:
        if (r.layer >= 0 && r.layer < kMaxLayers) {
            LayerInfo li{r.first, r.count, r.rate, r.frames, true};
            if (inFlight) stagedLayers[r.layer] = li;
            else { layerCache[r.layer] = li; voices.setLayerInfo(r.layer, li.first, li.count, li.rate, li.frames); }
        }
        break;
    case proto::Reply::End: voices.end(r.rec); break;
    case proto::Reply::Edit: setDna(r.text, false, true); break;
    default: {   // the keyboard strip in Windows (DNA.md 5.4)
        int a = 0, b = 0;
        if (std::sscanf(line.c_str(), "key %d %d", &a, &b) == 2) { keysFromWindows++; playMidi(b > 0 ? 0x90 : 0x80, (uint8_t)(a & 0x7F), (uint8_t)(b & 0x7F), true); }
        else if (std::sscanf(line.c_str(), "cc %d %d", &a, &b) == 2) playMidi(0xB0, (uint8_t)(a & 0x7F), (uint8_t)(b & 0x7F), true);
        else if (std::sscanf(line.c_str(), "bend %d", &a) == 1) { a += 8192; a = a < 0 ? 0 : a > 16383 ? 16383 : a; playMidi(0xE0, (uint8_t)(a & 0x7F), (uint8_t)(a >> 7), true); }
        break; }
    }
}

std::string jsonEsc(const std::string &s)
{
    std::string o;
    for (char ch : s) { if (ch == '"' || ch == '\\') o += '\\'; if ((unsigned char)ch >= 32) o += ch; }
    return o;
}

}  // namespace

extern "C" {

// the machine: conf (with its folder filled in), the snapshot to resume (or "" to boot), a snapshot to write ("")
EMSCRIPTEN_KEEPALIVE int b16_start(const char *conf, const char *state, const char *makeState, const char *logPath, int leadFrames, const char *libNames)
{
    if (S) return 0;
    {
        std::vector<std::string> names; std::string cur;
        for (const char *p = libNames ? libNames : ""; ; p++) {
            if (!*p || *p == '\n') { while (!cur.empty() && (cur.back() == '\r' || cur.back() == ' ')) cur.pop_back(); if (!cur.empty()) names.push_back(cur); cur.clear(); if (!*p) break; }
            else cur += *p;
        }
        setLibrary(names);
    }
    S = (bshm *)std::calloc(1, sizeof(bshm));
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
    lead = leadFrames > 0 ? (uint32_t)leadFrames : 2048; kLat = lead + 1536;
    S->lead = lead; S->realtime = 0; S->vid_want = 1;
    setDna(kDefaultDna, false);
    E = bs_engine_start(S, "static", conf, state && *state ? state : nullptr, makeState && *makeState ? makeState : nullptr,
                        logPath && *logPath ? logPath : nullptr);
    return E ? 1 : 0;
}

EMSCRIPTEN_KEEPALIVE bshm *b16_shm() { return S; }

// where the worker and the AudioWorklet find the fields they touch (byte offsets into the bshm block)
EMSCRIPTEN_KEEPALIVE const int *b16_layout()
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

// the host's periodic work (the plugin's worker loop, and the parts of its audio block that are not the audio)
EMSCRIPTEN_KEEPALIVE void b16_tick()
{
    if (!S) return;
    if (S->mouse_btn & 1) relFlush();
    if (!hello && S->state >= BS_RUNNING && S->state != BS_FAILED) {
        hello = true;
        char b[128];
        std::time_t t = std::time(nullptr); std::tm lt; localtime_r(&t, &lt);
        proto::hi(b, sizeof b); trimSend(b);
        proto::time(b, sizeof b, lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec); trimSend(b);
        proto::go(b, sizeof b); trimSend(b);
        dnaToGuest = true;
    }
    if (hello && dnaToGuest && !inFlight) {
        dnaToGuest = false;
        const Dna d = parse(dnaText);
        const bool rebuild = sigOf(applyMacros(d)) != cacheSig;
        if (rebuild) { inFlight = true; for (auto &c : stagedLayers) c = LayerInfo(); }
        building = rebuild;
        std::string line = "dna " + dnaText;
        sendLine(line.c_str());
        char b[96]; proto::env(b, sizeof b, d.g); trimSend(b);
        lenvDirty = true;
    } else if (hello && lenvDirty && !inFlight) {
        lenvDirty = false;
        const Dna eff = effective(parse(dnaText));
        for (int i = 0; i < kMaxLayers; i++) {
            static const Env none;
            char b[160];
            const Layer *L = i < (int)eff.layers.size() ? &eff.layers[i] : nullptr;
            proto::lenv(b, sizeof b, i, 'a', L ? L->envA : none); trimSend(b);
            proto::lenv(b, sizeof b, i, 'p', L ? L->envP : none); trimSend(b);
        }
    }
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
            if (ty == 3) { onLine(frag); frag.clear(); }
        }
        i += n;
    }
    words.erase(words.begin(), words.begin() + i);
}

EMSCRIPTEN_KEEPALIVE void b16_midi(int st, int a, int b) { if (S && S->state >= BS_RUNNING) playMidi((uint8_t)st, (uint8_t)a, (uint8_t)b, false); }
EMSCRIPTEN_KEEPALIVE void b16_dna(const char *text) { if (S) setDna(text, true); }

// the pointer and keys, exactly as the plugin's editor hands them to the engine
EMSCRIPTEN_KEEPALIVE void b16_mouse(int x, int y)
{
    if (!S) return;
    if (x < 0) x = 0; if (y < 0) y = 0; if (x >= BSHM_W) x = BSHM_W - 1; if (y >= BSHM_H) y = BSHM_H - 1;
    if (x == S->mouse_x && y == S->mouse_y) return;
    if (S->mouse_btn & 1) {   // a drag: the emulated mouse moves too (see web_engine.c), so Windows' modal loops follow
        relAccX += (x - S->mouse_x) * relScale; relAccY += (y - S->mouse_y) * relScale;
        relFlush();
    }
    S->mouse_x = x; S->mouse_y = y; S->mouse_seq++;
}
EMSCRIPTEN_KEEPALIVE void b16_button(int bit, int down)
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
// the microphone: n stereo frames at 48 kHz (lr interleaved), contiguous with the previous block; the first block
// (or one after a gap the card has already passed) goes 50 ms ahead of the card's DAC, as STATE.md 4 says
EMSCRIPTEN_KEEPALIVE void b16_mic(const float *lr, int n)
{
    if (!S || S->state < BS_RUNNING) return;
    const uint64_t dac = bsyn_host_dac();
    if (!micAt || micAt < dac + 256) micAt = dac + 2400;
    bsyn_host_input(micAt, lr, n);
    micAt += (uint64_t)n;
}
// (the input is the host's, not the synth's own output: what is not fed is silence)
EMSCRIPTEN_KEEPALIVE void b16_mic_on(int on) { bsyn_host_insrc(0); micAt = 0; (void)on; }
EMSCRIPTEN_KEEPALIVE int b16_recording() { uint64_t st = 0; uint32_t b = 0, o = 0; return bsyn_host_instate(&st, &b, &o); }

// tests and calibration: relative motion straight to the emulated mouse; the scale of drag motion
EMSCRIPTEN_KEEPALIVE void b16_rel(int dx, int dy) { __sync_fetch_and_add(&web_mouse_dx, dx); __sync_fetch_and_add(&web_mouse_dy, dy); }
EMSCRIPTEN_KEEPALIVE void b16_relscale(float f) { relScale = f; }
EMSCRIPTEN_KEEPALIVE void b16_key(int down, int rk)
{
    if (!S || S->key_w - S->key_r >= BSHM_KEYS) return;
    S->keys[S->key_w % BSHM_KEYS] = (down ? 0x80000000u : 0u) | (uint32_t)rk;
    __sync_synchronize();
    S->key_w++;
}

// paused: the engine stops where the AudioWorklet stopped (it only runs to host_r + lead)
EMSCRIPTEN_KEEPALIVE void b16_pause(int p) { if (S) { S->grant_until = 0; S->offline = p ? 1 : 0; } }
// build time: run without a clock up to `frames` DAC samples further (the node snapshot maker)
EMSCRIPTEN_KEEPALIVE void b16_grant(int frames) { if (S) { S->offline = 1; S->grant_until = S->dac_w + (uint64_t)frames; S->host_beat++; } }
EMSCRIPTEN_KEEPALIVE void b16_snapshot() { web_snapshot_request = 1; }
EMSCRIPTEN_KEEPALIVE void b16_stop() { if (E) { bs_engine_stop(E); E = nullptr; } }
EMSCRIPTEN_KEEPALIVE void b16_layer(int i, int first, int count, int rate, int frames)
{
    if (i < 0 || i >= kMaxLayers) return;
    layerCache[i] = LayerInfo{first, count, rate, frames, true};
    voices.setLayerInfo(i, first, count, rate, frames);
}

// the screen as RGBA for a canvas, if Windows drew a new frame since the last call (else 0). [0] = w, [1] = h, then pixels.
EMSCRIPTEN_KEEPALIVE uint32_t *b16_frame()
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
    for (uint32_t i = 0; i < n; i++) {   // XRGB (little endian B G R X) -> R G B A
        const uint32_t x = v[i];
        const uint32_t y = 0xFF000000u | (x & 0x0000FF00u) | ((x >> 16) & 0xFFu) | ((x & 0xFFu) << 16);
        if (y != d[i]) { d[i] = y; changed = true; }
    }
    __sync_synchronize();
    if (S->vid_seq != seq) { dirty = changed; return nullptr; }   // the engine wrote meanwhile: take the next one
    frameSeq = seq;
    dirty = false;
    if (!changed) return nullptr;
    frameW = w; frameH = h; frameBuf[0] = w; frameBuf[1] = h;
    return frameBuf;
}

// state for the page and the tests, as JSON
EMSCRIPTEN_KEEPALIVE const char *b16_info(int withLog)
{
    static std::string s;
    char b[512];
    std::snprintf(b, sizeof b, "{\"state\":%u,\"ready\":%d,\"building\":%d,\"inFlight\":%d,\"dac\":%llu,\"host\":%llu,\"load\":%u,"
                  "\"late\":%u,\"ontime\":%u,\"notes\":%u,\"keys\":%u,\"built\":%u,\"beat\":%llu,",
                  S ? S->state : 0, ready, building, inFlight, S ? (unsigned long long)S->dac_w : 0ull, S ? (unsigned long long)S->host_r : 0ull,
                  S ? S->emu_load : 0, S ? S->sched_late : 0, S ? S->sched_ontime : 0, notesSent, keysFromWindows, builtCount,
                  S ? (unsigned long long)S->engine_beat : 0ull);
    s = b;
    s += "\"dna\":\"" + jsonEsc(dnaText) + "\",\"error\":\"" + jsonEsc(S ? std::string(S->error) : "") + "\",\"layers\":[";
    for (int i = 0; i < kMaxLayers; i++) {
        std::snprintf(b, sizeof b, "%s[%d,%d,%d,%d,%d]", i ? "," : "", layerCache[i].known, layerCache[i].first, layerCache[i].count, layerCache[i].rate, layerCache[i].frames);
        s += b;
    }
    s += "],\"log\":[";
    if (withLog) for (size_t k = 0; k < guestLog.size(); k++) s += (k ? ",\"" : "\"") + jsonEsc(guestLog[k]) + "\"";
    s += "]}";
    if (withLog) guestLog.clear();
    return s.c_str();
}

}  // extern "C"

// SNDWAVE1993: the song mixer, a port of tools/songrender/songrender.py mix() (design/SONG-TAB.md §5). The same
// steps in the same order on the same 24-bit stems: DC, track filters, width, pan, volume, loudness, the echo and
// reverb sends (FFT convolution), the 25 Hz high-pass, the fade, the master loudness and the 4x true-peak limiter.
// The result matches songrender's WAV to within 1 LSB at 24 bits (FFT and summation order differ, nothing else).
#pragma once
#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <atomic>
#include <deque>
#include <string>
#include <vector>
#include "Song.h"

namespace b16song {
namespace mixd {

constexpr int SR = 48000;
constexpr double kPi = 3.14159265358979323846;   // (M_PI is not standard C++)
using Buf = std::vector<double>;
struct St { Buf l, r; size_t size() const { return l.size(); } void resize(size_t n) { l.assign(n, 0); r.assign(n, 0); } };

inline double num(const std::map<std::string, std::string> &m, const char *k, double def)   // songrender num()
{
    auto it = m.find(k); if (it == m.end()) return def;
    std::string v = it->second, o;
    for (size_t i = 0; i < v.size(); i++) {
        if (v.compare(i, 2, "ms") == 0 || v.compare(i, 2, "dB") == 0) { i++; continue; }
        o += v[i];
    }
    return std::atof(o.c_str());
}
inline std::string str(const std::map<std::string, std::string> &m, const char *k, const char *def)
{
    auto it = m.find(k); return it == m.end() ? def : it->second;
}

inline void onepole(Buf &x, double fc)   // lfilter([1-a], [1, -a])
{
    if (fc <= 0 || fc >= SR / 2) return;
    const double a = std::exp(-2 * kPi * fc / SR), b = 1 - a; double y = 0;
    for (double &v : x) { y = b * v + a * y; v = y; }
}
struct Biquad { double b0, b1, b2, a1, a2; };
inline Biquad butter2(double fc, bool hp)   // scipy butter(2, fc, fs=SR): bilinear with prewarping
{
    const double K = std::tan(kPi * fc / SR), q = std::sqrt(2.0), D = 1 + q * K + K * K;
    Biquad f;
    if (hp) { f.b0 = 1 / D; f.b1 = -2 / D; f.b2 = 1 / D; }
    else { f.b0 = K * K / D; f.b1 = 2 * K * K / D; f.b2 = K * K / D; }
    f.a1 = 2 * (K * K - 1) / D; f.a2 = (1 - q * K + K * K) / D;
    return f;
}
inline void biquad(Buf &x, const Biquad &f)   // direct form II transposed, as lfilter/sosfilt
{
    double z0 = 0, z1 = 0;
    for (double &v : x) { const double in = v, y = f.b0 * in + z0; z0 = f.b1 * in - f.a1 * y + z1; z1 = f.b2 * in - f.a2 * y; v = y; }
}

// ---- FFT convolution (overlap-add); full length x.size() + h.size() - 1, truncated to n
struct Fft {
    size_t n; std::vector<std::complex<double>> w; std::vector<size_t> rev;
    explicit Fft(size_t N) : n(N), w(N / 2), rev(N)
    {
        for (size_t k = 0; k < N / 2; k++) w[k] = std::polar(1.0, -2 * kPi * (double)k / (double)N);   // exact twiddles
        for (size_t i = 1, j = 0; i < N; i++) { size_t bit = N >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; rev[i] = j; }
    }
    void run(std::vector<std::complex<double>> &a, bool inv) const
    {
        for (size_t i = 1; i < n; i++) if (i < rev[i]) std::swap(a[i], a[rev[i]]);
        for (size_t len = 2; len <= n; len <<= 1) {
            const size_t h = len / 2, st = n / len;
            for (size_t i = 0; i < n; i += len)
                for (size_t k = 0; k < h; k++) {
                    const auto t = inv ? std::conj(w[k * st]) : w[k * st];
                    const auto u = a[i + k], v = a[i + k + h] * t; a[i + k] = u + v; a[i + k + h] = u - v;
                }
        }
        if (inv) { const double s = 1.0 / (double)n; for (auto &v : a) v *= s; }
    }
};
inline Buf convolve(const Buf &x, const Buf &h, size_t n)
{
    Buf out(n, 0.0);
    if (h.empty() || x.empty()) return out;
    size_t N = 1; while (N < 2 * h.size()) N <<= 1;
    N = std::max<size_t>(N, 1 << 16);
    const size_t B = N - h.size() + 1;
    const Fft F(N);
    std::vector<std::complex<double>> H(N), X(N);
    for (size_t i = 0; i < h.size(); i++) H[i] = h[i];
    F.run(H, false);
    const size_t len = std::min(x.size(), n);
    for (size_t s = 0; s < len; s += 2 * B) {   // two blocks at once: one in the real part, the next in the imaginary (h is real)
        std::fill(X.begin(), X.end(), 0.0);
        bool any = false;
        for (size_t i = 0; i < B && s + i < len; i++) { X[i].real(x[s + i]); any |= x[s + i] != 0; }
        for (size_t i = 0; i < B && s + B + i < len; i++) { X[i].imag(x[s + B + i]); any |= x[s + B + i] != 0; }
        if (!any) continue;
        F.run(X, false);
        for (size_t i = 0; i < N; i++) X[i] *= H[i];
        F.run(X, true);
        for (size_t i = 0; i < N && s + i < n; i++) out[s + i] += X[i].real();
        for (size_t i = 0; i < N && s + B + i < n; i++) out[s + B + i] += X[i].imag();
    }
    return out;
}

// ---- BS.1770 loudness (K-weighting, 400 ms blocks, 100 ms hop, gated)
inline double lufs(const Buf &L, const Buf &R)
{
    const Biquad s1{1.53512485958697, -2.69169618940638, 1.19839281085285, -1.69065929318241, 0.73248077421585};
    const Biquad s2{1.0, -2.0, 1.0, -1.99004745483398, 0.99007225036621};
    Buf yl = L, yr = R; biquad(yl, s1); biquad(yl, s2); biquad(yr, s1); biquad(yr, s2);
    const size_t blk = SR * 4 / 10, hop = SR / 10, n = yl.size();
    std::vector<double> ms, hs;   // energy per 100 ms hop; a block is four of them
    for (size_t i = 0; i < n; i += hop) { double s = 0; for (size_t k = i; k < i + hop && k < n; k++) s += yl[k] * yl[k] + yr[k] * yr[k]; hs.push_back(s); }
    for (size_t i = 0; i < std::max<size_t>(1, n > blk ? n - blk : 0); i += hop) {
        const size_t c = std::min(blk, n - std::min(n, i)); double s = 0;
        for (size_t k = i / hop; k < i / hop + 4 && k < hs.size(); k++) s += hs[k];
        ms.push_back(c ? s / (double)c : NAN);
    }
    if (ms.empty()) return -70;
    double g = 0; size_t gn = 0;
    for (double m : ms) if (-0.691 + 10 * std::log10(m + 1e-12) > -70) { g += m; gn++; }
    if (!gn) return -70;
    const double rel = -0.691 + 10 * std::log10(g / (double)gn) - 10;
    g = 0; gn = 0;
    for (double m : ms) { const double l = -0.691 + 10 * std::log10(m + 1e-12); if (l > -70 && l > rel) { g += m; gn++; } }
    return -0.691 + 10 * std::log10(g / (double)gn);
}

// ---- sends
inline void echoIr(const std::map<std::string, std::string> &sec, double bpm, Buf &hl, Buf &hr)
{
    const std::string t = str(sec, "time", "3/16");
    double dsec;
    if (t.find('/') != std::string::npos) dsec = 240.0 / bpm * std::atof(t.c_str()) / std::atof(t.c_str() + t.find('/') + 1);
    else dsec = num(sec, "time", 375) / 1000.0;
    const size_t D = (size_t)std::max(1L, pyRound(dsec * SR));
    const double fb = std::min(0.9, num(sec, "feedback", 0.35)), tone = num(sec, "tone", 3500);
    std::string pp = str(sec, "pingpong", "yes"); for (auto &c : pp) c = (char)std::tolower((unsigned char)c);
    const bool ping = pp == "yes" || pp == "on" || pp == "1" || pp == "true";
    int n = 1; while (std::pow(fb, n) > 0.001 && n < 64) n++;
    const size_t L = n * D + 4096;
    hl.assign(L, 0); hr.assign(L, 0);
    Buf imp(4096, 0.0); imp[0] = 1;
    for (int k = 1; k <= n; k++) {
        onepole(imp, tone);
        const double g = std::pow(fb, k - 1);
        for (size_t i = 0; i < 4096; i++) {
            if (ping) ((k - 1) % 2 ? hr : hl)[k * D + i] += g * imp[i];
            else { hl[k * D + i] += g * imp[i] * 0.7071; hr[k * D + i] += g * imp[i] * 0.7071; }
        }
    }
}
inline Buf splitmixGauss(uint64_t seed, size_t n)   // songrender splitmix_gauss: SplitMix64, Irwin-Hall of 4
{
    Buf o(n); uint64_t x = seed;
    for (size_t i = 0; i < n; i++) {
        double s = 0;
        for (int k = 0; k < 4; k++) {
            x += 0x9E3779B97F4A7C15ull; uint64_t z = x;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull; z = (z ^ (z >> 27)) * 0x94D049BB133111EBull; z ^= z >> 31;
            s += (double)(z >> 11) * 0x1p-53;
        }
        o[i] = (s - 2.0) * std::sqrt(3.0);
    }
    return o;
}
inline void reverbIr(const std::map<std::string, std::string> &sec, Buf &hl, Buf &hr)
{
    const double rt = num(sec, "size", 2.0), pre = num(sec, "predelay", 18) / 1000.0, tone = num(sec, "tone", 5500);
    const int64_t seed = (int64_t)num(sec, "seed", 3110);
    const size_t L = (size_t)((rt * 1.2 + pre) * SR), P = (size_t)(pre * SR), F = (size_t)(0.004 * SR);
    double e2 = 0;
    for (int c = 0; c < 2; c++) {
        Buf nz = splitmixGauss((uint64_t)(seed * 2 + c), L), lo = nz; onepole(lo, tone);
        Buf hi(L); for (size_t i = 0; i < L; i++) hi[i] = nz[i] - lo[i];
        onepole(lo, tone);
        Buf &h = c ? hr : hl; h.assign(L, 0);
        for (size_t i = 0; i + P < L; i++) {
            const double t = (double)i / SR;
            double v = lo[i] * std::exp(-6.9078 * t / rt) + 0.35 * hi[i] * std::exp(-6.9078 * t / (rt * 0.45));
            if (i < F) v *= F > 1 ? (double)i / (double)(F - 1) : 0;   // np.linspace(0, 1, F)
            h[P + i] = v;
        }
        for (double v : h) e2 += v * v;
    }
    const double k = std::sqrt(e2 / 2);
    for (auto &v : hl) v /= k;
    for (auto &v : hr) v /= k;
}

// ---- the limiter: 4x oversampled peaks (resample_poly's Kaiser 5.0 FIR, 81 taps), look-ahead min, release, smoothing
inline std::vector<double> upFir()
{
    auto i0 = [](double x) { double s = 1, t = 1; for (int k = 1; k < 200; k++) { t *= (x / 2) / k; s += t * t; if (t * t < 1e-17 * s) break; } return s; };
    std::vector<double> h(81); double sum = 0;
    for (int n = 0; n < 81; n++) {
        const double m = n - 40.0, a = 0.25 * m;
        const double sinc = a == 0 ? 1.0 : std::sin(kPi * a) / (kPi * a);
        const double r = 2.0 * n / 80.0 - 1.0;
        h[n] = 0.25 * sinc * i0(5.0 * std::sqrt(std::max(0.0, 1 - r * r))) / i0(5.0);
        sum += h[n];
    }
    for (auto &v : h) v = v / sum * 4;
    return h;
}
inline double limit(const St &x, double gain, double ceilingDb, St &y)   // returns the largest reduction (1 - min gain)
{
    const double c = std::pow(10.0, ceilingDb / 20);
    const size_t n = x.size();
    static const std::vector<double> h = upFir();
    Buf need(n);
    for (size_t i = 0; i < n; i++) {
        double pk = 0;
        for (int ph = 0; ph < 4; ph++) {   // up[4i+ph] = sum_q h[q] xup[4i+ph+40-q]; xup[4j] = x[j]
            const int64_t m = 4 * (int64_t)i + ph;
            double al = 0, ar = 0;
            for (int q = (int)((m + 40) % 4); q <= 80; q += 4) {
                const int64_t j = (m + 40 - q) / 4;
                if (j < 0 || j >= (int64_t)n) continue;
                al += h[q] * x.l[j] * gain; ar += h[q] * x.r[j] * gain;
            }
            pk = std::max(pk, std::max(std::fabs(al), std::fabs(ar)));
        }
        need[i] = std::min(1.0, c / std::max(pk, 1e-9));
    }
    const size_t L = std::max<size_t>(1, (size_t)(3.0 / 1000 * SR));
    Buf g(n);
    {   // minimum_filter1d(size 2L+1, nearest): the min over [i-L, i+L] clipped to the line
        std::deque<size_t> dq; size_t next = 0;
        for (size_t i = 0; i < n; i++) {
            const size_t hi = std::min(n - 1, i + L);
            while (next <= hi) { while (!dq.empty() && need[dq.back()] >= need[next]) dq.pop_back(); dq.push_back(next++); }
            while (dq.front() + L < i) dq.pop_front();
            g[i] = need[dq.front()];
        }
    }
    {   // _release: y = min(g, a*y + (1-a)*g), resting at 1 while nothing is reduced
        const double a = std::exp(-1.0 / (120.0 / 1000 * SR)); double yv = 1.0;
        for (size_t i = 0; i < n; i++) {
            if (yv >= 0.999999 && g[i] >= 0.999999) { yv = 1.0; continue; }
            const double v = a * yv + (1 - a) * g[i];
            yv = g[i] < v ? g[i] : v; g[i] = yv;
        }
    }
    {   // uniform_filter1d(size L+1, nearest): window [i - (L+1)/2, i + L/2], running sum as scipy does
        const size_t S = L + 1, s2 = S / 2; const int64_t s1 = (int64_t)S - (int64_t)s2 - 1;
        auto at = [&](int64_t k) { return g[(size_t)std::min<int64_t>((int64_t)n - 1, std::max<int64_t>(0, k))]; };
        Buf o(n); double t = 0;
        for (int64_t k = -(int64_t)s2; k <= s1; k++) t += at(k);
        o[0] = t / (double)S;
        for (size_t i = 1; i < n; i++) { t += at((int64_t)i + s1) - at((int64_t)i - (int64_t)s2 - 1); o[i] = t / (double)S; }
        g.swap(o);
    }
    double gmin = 1; y.resize(n);
    for (size_t i = 0; i < n; i++) {
        gmin = std::min(gmin, g[i]);
        y.l[i] = std::clamp(x.l[i] * gain * g[i], -c, c); y.r[i] = std::clamp(x.r[i] * gain * g[i], -c, c);
    }
    return n ? 1 - gmin : 0;
}

}  // namespace mixd

// a render's samples as songrender reads its stem: 24-bit (render311's WAV), back through FLAC s32 to float
inline double stemSample(float x) { const double v = x < -1 ? -1 : x > 1 ? 1 : x; return (double)std::lround(v * 8388607.0) / 8388608.0; }

struct MixIn { const SongTrack *t; const std::vector<float> *lr; };   // the track and its render (48 kHz stereo)
struct MixStats { std::vector<std::pair<std::string, double>> trackLufs; double pre = 0, lufs = 0, gainDb = 0, reductionDb = 0, peakDb = 0; };

// songrender mix(): `lengthSec` = the MIDI's last tick in seconds + tail. Returns 48 kHz stereo, interleaved.
inline std::vector<double> mixSong(const SongText &song, double bpm, double lengthSec, const std::vector<MixIn> &in, MixStats *stats = nullptr,
                                   const std::atomic<bool> *cancel = nullptr)
{
    using namespace mixd;
    const size_t n = (size_t)std::max(0.0, lengthSec * SR);
    St dry, eb, rb; dry.resize(n); eb.resize(n); rb.resize(n);
    bool anySolo = false; for (const auto &m : in) anySolo |= m.t->solo;
    bool anyE = false, anyR = false;
    auto secOf = [&](const char *s) { auto it = song.sec.find(s); static const std::map<std::string, std::string> none; return it == song.sec.end() ? none : it->second; };
    for (const auto &m : in) {
        const SongTrack &t = *m.t;
        if (anySolo ? !t.solo : t.mute) continue;
        if (cancel && *cancel) return {};
        Buf xl(n, 0.0), xr(n, 0.0);
        const size_t have = std::min(n, m.lr->size() / 2);
        for (size_t i = 0; i < have; i++) { xl[i] = stemSample((*m.lr)[2 * i]); xr[i] = stemSample((*m.lr)[2 * i + 1]); }
        double ml = 0, mr = 0; for (size_t i = 0; i < n; i++) { ml += xl[i]; mr += xr[i]; }
        if (n) { ml /= (double)n; mr /= (double)n; for (size_t i = 0; i < n; i++) { xl[i] -= ml; xr[i] -= mr; } }
        if (t.hp > 0) { const auto f = butter2(t.hp, true); biquad(xl, f); biquad(xr, f); }
        if (t.lp > 0) { const auto f = butter2(t.lp, false); biquad(xl, f); biquad(xr, f); }
        if (t.width != 1.0)
            for (size_t i = 0; i < n; i++) { const double mm = (xl[i] + xr[i]) / 2, s = (xl[i] - xr[i]) / 2 * t.width; xl[i] = mm + s; xr[i] = mm - s; }
        const double th = (std::max(-100.0, std::min(100.0, t.pan)) + 100.0) / 200.0 * kPi / 2;
        const double gl = std::sqrt(2.0) * std::cos(th), gr = std::sqrt(2.0) * std::sin(th);
        double g = std::pow(10.0, t.vol / 20);
        const double own = lufs(xl, xr);
        if (t.hasLufs && own > -69) g *= std::pow(10.0, (t.lufs - own) / 20);
        if (stats) stats->trackLufs.push_back({t.name, own});
        for (size_t i = 0; i < n; i++) {
            const double yl = xl[i] * gl * g, yr = xr[i] * gr * g;
            dry.l[i] += yl; dry.r[i] += yr;
            if (t.echo > 0) { eb.l[i] += yl * t.echo; eb.r[i] += yr * t.echo; anyE |= yl != 0 || yr != 0; }
            if (t.verb > 0) { rb.l[i] += yl * t.verb; rb.r[i] += yr * t.verb; anyR |= yl != 0 || yr != 0; }
        }
    }
    St out = dry;
    if (anyE) {
        const auto &es = secOf("echo"); Buf hl, hr; echoIr(es, bpm, hl, hr);
        const double lc = num(es, "lowcut", 180), lv = std::pow(10.0, num(es, "level", 0) / 20);
        for (int c = 0; c < 2; c++) {
            Buf e = convolve(c ? eb.r : eb.l, c ? hr : hl, n), lo = e; onepole(lo, lc);
            for (size_t i = 0; i < n; i++) e[i] -= lo[i];
            onepole(e, 20000);
            Buf &o = c ? out.r : out.l; for (size_t i = 0; i < n; i++) o[i] += e[i] * lv;
        }
    }
    if (cancel && *cancel) return {};
    if (anyR) {
        const auto &rs = secOf("reverb"); Buf hl, hr; reverbIr(rs, hl, hr);
        const double lc = num(rs, "lowcut", 150), lv = std::pow(10.0, num(rs, "level", -6) / 20);
        for (int c = 0; c < 2; c++) {
            Buf r = convolve(c ? rb.r : rb.l, c ? hr : hl, n), lo = r; onepole(lo, lc);
            Buf &o = c ? out.r : out.l; for (size_t i = 0; i < n; i++) o[i] += (r[i] - lo[i]) * lv;
        }
    }
    { const auto f = butter2(25, true); biquad(out.l, f); biquad(out.r, f); }
    const auto &ms = secOf("master");
    const size_t fo = std::min(n, (size_t)std::max(0.0, num(ms, "fadeout", 1.5) * SR));
    for (size_t k = 0; k < fo; k++) {
        const double v = fo > 1 ? 1.0 + (double)k * (-1.0 / (double)(fo - 1)) : 1.0, w = v * v;
        out.l[n - fo + k] *= w; out.r[n - fo + k] *= w;
    }
    const double target = num(ms, "loudness", -16.0), ceiling = num(ms, "ceiling", -1.0);
    const double pre = lufs(out.l, out.r);
    const double gain = std::pow(10.0, (target - pre) / 20) * std::pow(10.0, num(ms, "gain", 0) / 20);
    if (cancel && *cancel) return {};
    St y; double red = limit(out, gain, ceiling, y);
    double post = lufs(y.l, y.r);
    if (post < target - 0.3) { red = limit(out, gain * std::pow(10.0, (target - post) / 20), ceiling, y); post = lufs(y.l, y.r); }
    std::vector<double> lr(2 * n); double pk = 0;
    for (size_t i = 0; i < n; i++) { lr[2 * i] = y.l[i]; lr[2 * i + 1] = y.r[i]; pk = std::max(pk, std::max(std::fabs(y.l[i]), std::fabs(y.r[i]))); }
    if (stats) { stats->pre = pre; stats->lufs = post; stats->gainDb = 20 * std::log10(gain); stats->reductionDb = -20 * std::log10(std::max(1e-6, 1 - red)); stats->peakDb = 20 * std::log10(pk + 1e-12); }
    return lr;
}

// the mix as songrender writes it: 24-bit, rounded half to even
inline void writeMixWav(const std::string &path, const std::vector<double> &lr)
{
    FILE *f = std::fopen(path.c_str(), "wb"); if (!f) return;
    const uint32_t data = (uint32_t)(lr.size() * 3);
    auto u32 = [&](uint32_t v) { std::fwrite(&v, 4, 1, f); };
    auto u16 = [&](uint16_t v) { std::fwrite(&v, 2, 1, f); };
    std::fwrite("RIFF", 1, 4, f); u32(36 + data); std::fwrite("WAVEfmt ", 1, 8, f);
    u32(16); u16(1); u16(2); u32(48000); u32(48000 * 6); u16(6); u16(24);
    std::fwrite("data", 1, 4, f); u32(data);
    for (double x : lr) {
        const int32_t s = (int32_t)std::lrint(std::clamp(x, -1.0, 1.0) * 8388607.0);
        const uint8_t b[3] = {(uint8_t)s, (uint8_t)(s >> 8), (uint8_t)(s >> 16)};
        std::fwrite(b, 1, 3, f);
    }
    std::fclose(f);
}

}  // namespace b16song

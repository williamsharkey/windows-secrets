// BasiliskHost - analysis (see analysis.h). Methods follow packages/basilisk-synth/tools/run_tests.py.
#include "analysis.h"
#include <algorithm>
#include <cmath>
#include <complex>
#include <map>
#include <numeric>

static double db(double v) { return v > 1e-10 ? 20 * std::log10(v) : -200; }

Level level(const std::vector<float> &lr, size_t from, size_t to)
{
    Level L;
    size_t n = lr.size() / 2;
    to = std::min(to, n);
    double s = 0;
    size_t c = 0;
    for (size_t i = from; i < to; i++)
        for (int k = 0; k < 2; k++) {
            double v = lr[2 * i + k];
            L.peak = std::max(L.peak, std::fabs(v));
            s += v * v;
            c++;
        }
    L.rms = c ? std::sqrt(s / c) : 0;
    L.peakDb = db(L.peak);
    L.rmsDb = db(L.rms);
    return L;
}

static std::vector<float> mono(const std::vector<float> &lr)
{
    std::vector<float> m(lr.size() / 2);
    for (size_t i = 0; i < m.size(); i++) m[i] = 0.5f * (lr[2 * i] + lr[2 * i + 1]);
    return m;
}

static void fft(std::vector<std::complex<double>> &a)
{
    size_t n = a.size();
    for (size_t i = 1, j = 0; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (size_t len = 2; len <= n; len <<= 1) {
        double ang = -2 * M_PI / len;
        std::complex<double> wl(std::cos(ang), std::sin(ang));
        for (size_t i = 0; i < n; i += len) {
            std::complex<double> w(1);
            for (size_t j = 0; j < len / 2; j++) {
                auto u = a[i + j], v = a[i + j + len / 2] * w;
                a[i + j] = u + v;
                a[i + j + len / 2] = u - v;
                w *= wl;
            }
        }
    }
}

// magnitude spectrum of up to 8192 samples from `from`, Hann window, zero-padded to 65536
static std::vector<double> spectrum(const std::vector<float> &m, size_t from, size_t len)
{
    const size_t N = 65536;
    len = std::min<size_t>(std::min<size_t>(len, 8192), from < m.size() ? m.size() - from : 0);
    std::vector<std::complex<double>> a(N);
    for (size_t i = 0; i < len; i++) a[i] = m[from + i] * (0.5 - 0.5 * std::cos(2 * M_PI * i / std::max<size_t>(len - 1, 1)));
    fft(a);
    std::vector<double> mag(N / 2);
    for (size_t i = 0; i < N / 2; i++) mag[i] = std::abs(a[i]);
    return mag;
}

double peak_hz(const std::vector<float> &m, size_t from, size_t len, int sr)
{
    auto f = spectrum(m, from, len);
    size_t k = 20;
    for (size_t i = 20; i + 1 < f.size(); i++) if (f[i] > f[k]) k = i;
    double al = std::log(f[k - 1] + 1e-12), be = std::log(f[k] + 1e-12), ga = std::log(f[k + 1] + 1e-12);
    double den = al - 2 * be + ga;
    double off = std::fabs(den) > 1e-12 ? 0.5 * (al - ga) / den : 0;
    return (k + off) * sr / 65536.0;
}

// the spectrum on a log-frequency axis (5-cent bins from 40 Hz), compressed, for measuring pitch shifts
static const double LS_F0 = 40, LS_STEP = 5;
static std::vector<double> logspec(const std::vector<float> &m, size_t from, size_t len, int sr)
{
    auto f = spectrum(m, from, len);
    double fmax = std::min(sr * 0.45, 16000.0);
    int nb = (int)(1200 / LS_STEP * std::log2(fmax / LS_F0));
    std::vector<double> v(nb);
    for (int b = 0; b < nb; b++) {
        double hz = LS_F0 * std::pow(2.0, b * LS_STEP / 1200), x = hz * 65536 / sr;
        size_t k = (size_t)x;
        double u = x - k;
        double a = k + 1 < f.size() ? f[k] * (1 - u) + f[k + 1] * u : 0;
        v[b] = std::sqrt(a);
    }
    double mean = std::accumulate(v.begin(), v.end(), 0.0) / std::max<size_t>(v.size(), 1);
    for (auto &x : v) x -= mean;
    return v;
}

// shift of b against a, in cents, searched within [lo, hi]
static double logspec_shift(const std::vector<double> &a, const std::vector<double> &b, double lo, double hi)
{
    int s0 = (int)std::floor(lo / LS_STEP), s1 = (int)std::ceil(hi / LS_STEP);
    std::vector<double> c;
    for (int s = s0; s <= s1; s++) {
        double acc = 0, na = 0, nb = 0;
        for (int i = 0; i < (int)a.size(); i++) {
            int j = i + s;
            if (j < 0 || j >= (int)b.size()) continue;
            acc += a[i] * b[j];
            na += a[i] * a[i];
            nb += b[j] * b[j];
        }
        c.push_back(na > 0 && nb > 0 ? acc / std::sqrt(na * nb) : -1);
    }
    int k = (int)(std::max_element(c.begin(), c.end()) - c.begin());
    double off = 0;
    if (k > 0 && k + 1 < (int)c.size()) {
        double den = c[k - 1] - 2 * c[k] + c[k + 1];
        if (std::fabs(den) > 1e-12) off = 0.5 * (c[k - 1] - c[k + 1]) / den;
    }
    return (s0 + k + off) * LS_STEP;
}

// first rise of the envelope inside [a, b) (samples), as run_tests.py's onset()
static long onset(const std::vector<float> &env, long a, long b, int sr)
{
    a = std::max(0L, a);
    b = std::min((long)env.size(), b);
    int D = std::max(1, sr / 200);   // 5 ms
    if (b - a < 600 || b - a <= D) return -1;
    double best = -1;
    long k = 0;
    for (long i = a; i + D < b; i++) {
        double d = env[i + D] - env[i];
        if (d > best) { best = d; k = i; }
    }
    if (best < 2e-3) return -1;
    // walk back to 10% of the rise's top, or to the valley before it when the previous note still rings
    double pk = env[k + D], mn = env[k];
    long kmin = k;
    while (k > a && env[k] > 0.1 * pk) {
        k--;
        if (env[k] < mn) { mn = env[k]; kmin = k; }
        else if (env[k] > mn * 1.5 + 1e-4) return kmin;
    }
    return k;
}

std::vector<NoteResult> analyze_notes(const std::vector<float> &lr, int sr, double warmup, const Score &s, double lat,
                                      NotesSummary &sum)
{
    std::vector<NoteResult> out;
    auto m = mono(lr);
    std::vector<float> env(m.size());
    {
        double acc = 0;
        const int W = 64;
        for (size_t i = 0; i < m.size(); i++) {
            acc += std::fabs(m[i]);
            if (i >= W) acc -= std::fabs(m[i - W]);
            env[i >= W / 2 ? i - W / 2 : 0] = (float)(acc / W);
        }
    }
    // one onset per distinct start time
    std::vector<double> starts;
    for (auto &n : s.notes) if (starts.empty() || std::fabs(n.t - starts.back()) > 0.02) starts.push_back(n.t);
    std::map<long, long> onsetOf;   // start (ms) -> onset sample
    for (size_t i = 0; i < starts.size(); i++) {
        double exp = warmup + starts[i] + lat;
        double gp = i ? starts[i] - starts[i - 1] : 1, gn = i + 1 < starts.size() ? starts[i + 1] - starts[i] : 1;
        long a = (long)((exp - std::min(0.2, 0.45 * gp)) * sr), b = (long)((exp + std::min(0.5, 0.9 * gn)) * sr);
        onsetOf[std::lround(starts[i] * 1000)] = onset(env, a, b, sr);
    }
    // the pitch reference: the first single note of the scale (or of anything)
    const NoteRec *ref = nullptr;
    for (auto &n : s.notes) if (n.single && n.section == "scale") { ref = &n; break; }
    if (!ref) for (auto &n : s.notes) if (n.single && n.section != "bend") { ref = &n; break; }
    std::vector<double> refSpec;
    long refOn = -1;
    if (ref) {
        refOn = onsetOf[std::lround(ref->t * 1000)];
        if (refOn >= 0) refSpec = logspec(m, refOn + sr / 100, (size_t)(std::min(ref->dur, 0.35) * sr), sr);
        sum.refNote = ref->note;
    }
    std::vector<double> errs, cents;
    for (auto &n : s.notes) {
        NoteResult r;
        r.n = n;
        r.expectedS = warmup + n.t + lat;
        long on = onsetOf[std::lround(n.t * 1000)];
        sum.notes++;
        if (on >= 0) {
            r.heard = true;
            sum.heard++;
            r.onsetErrMs = (on / (double)sr - r.expectedS) * 1000;
            r.onsetRawMs = (on / (double)sr - warmup - n.t) * 1000;
            errs.push_back(r.onsetErrMs);
            size_t from = on + sr / 100, len = (size_t)(std::min(n.dur, 0.35) * sr);
            Level L = level(lr, on, on + (size_t)(std::max(n.dur, 0.05) * sr));
            r.peak = L.peak;
            r.rmsDb = L.rmsDb;
            if (n.single && n.section != "bend" && len > (size_t)(0.025 * sr)) {
                r.hz = peak_hz(m, from, len, sr);
                if (!refSpec.empty()) {
                    double expc = 100.0 * (n.note - ref->note);
                    r.intervalCents = logspec_shift(refSpec, logspec(m, from, len, sr), expc - 150, expc + 150);
                    r.centsOff = r.intervalCents - expc;
                    r.pitched = true;
                    sum.pitched++;
                    cents.push_back(std::fabs(r.centsOff));
                }
            }
        }
        out.push_back(r);
    }
    sum.timed = (int)errs.size();
    if (!errs.empty()) {
        auto e = errs;
        std::sort(e.begin(), e.end());
        sum.medianErrMs = e[e.size() / 2];
        sum.minErrMs = e.front();
        sum.maxErrMs = e.back();
        sum.meanErrMs = std::accumulate(e.begin(), e.end(), 0.0) / e.size();
        double v = 0;
        for (double x : e) v += (x - sum.meanErrMs) * (x - sum.meanErrMs);
        sum.stdErrMs = std::sqrt(v / e.size());
    }
    if (!cents.empty()) {
        sum.maxAbsCents = *std::max_element(cents.begin(), cents.end());
        sum.meanAbsCents = std::accumulate(cents.begin(), cents.end(), 0.0) / cents.size();
    }
    return out;
}

static std::vector<double> envelope(const std::vector<float> &lr, int sr)
{
    auto m = mono(lr);
    size_t hop = sr / 100;
    std::vector<double> e;
    for (size_t i = 0; i + hop <= m.size(); i += hop) {
        double a = 0;
        for (size_t k = 0; k < hop; k++) a += std::fabs(m[i + k]);
        e.push_back(a / hop);
    }
    return e;
}

static double corr(const double *u, const double *v, size_t n)
{
    double mu = 0, mv = 0;
    for (size_t i = 0; i < n; i++) { mu += u[i]; mv += v[i]; }
    mu /= n; mv /= n;
    double a = 0, b = 0, c = 0;
    for (size_t i = 0; i < n; i++) { a += (u[i] - mu) * (v[i] - mv); b += (u[i] - mu) * (u[i] - mu); c += (v[i] - mv) * (v[i] - mv); }
    return b > 0 && c > 0 ? a / std::sqrt(b * c) : (b == 0 && c == 0 ? 1 : 0);
}

Compare compare(const std::vector<float> &a, const std::vector<float> &b, int sr)
{
    Compare c;
    size_t n = std::min(a.size(), b.size());
    c.identical = a.size() == b.size();
    double sd = 0;
    std::vector<double> u(n), v(n);
    for (size_t i = 0; i < n; i++) {
        double d = std::fabs((double)a[i] - b[i]);
        if (d > 0) c.identical = false;
        c.maxAbsDiff = std::max(c.maxAbsDiff, d);
        sd += d * d;
        u[i] = a[i];
        v[i] = b[i];
    }
    c.diffRmsDb = n ? db(std::sqrt(sd / n)) : -200;
    c.sampleCorr = n ? corr(u.data(), v.data(), n) : 0;
    // loudness envelopes, best correlation over a +-300 ms shift
    auto ea = envelope(a, sr), eb = envelope(b, sr);
    double best = -1;
    for (int s = -30; s <= 30; s++) {
        const double *p, *q;
        size_t m;
        if (s >= 0) { if ((size_t)s >= ea.size()) continue; p = ea.data() + s; q = eb.data(); m = std::min(ea.size() - s, eb.size()); }
        else { if ((size_t)-s >= eb.size()) continue; p = ea.data(); q = eb.data() - s; m = std::min(ea.size(), eb.size() + s); }
        if (m < 10) continue;
        double r = corr(p, q, m);
        if (r > best) { best = r; c.envShiftMs = s * 10; }
    }
    c.envCorr = best;
    return c;
}

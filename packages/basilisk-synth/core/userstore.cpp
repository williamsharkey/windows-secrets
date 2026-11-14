// User recordings and the .b16 state file: see userstore.h.
#include "userstore.h"
#include <cstring>
#include <sstream>

namespace bsynth {

// ------------------------------------------------------------------------------------------------ names
std::string userName(const std::string &stem)
{
    std::string o;
    for (unsigned char c : stem) {
        char x = (char)std::tolower(c);
        if (!((x >= 'a' && x <= 'z') || (x >= '0' && x <= '9'))) x = '_';
        if (x == '_' && (o.empty() || o.back() == '_')) continue;   // runs collapse; no leading _
        o += x;
    }
    while (!o.empty() && o.back() == '_') o.pop_back();
    if (o.size() > 24) { o.resize(24); while (!o.empty() && o.back() == '_') o.pop_back(); }
    return o.empty() ? std::string() : kUserPrefix + o;
}
bool isUserName(const std::string &n)
{
    if (n.size() <= 2 || n.compare(0, 2, kUserPrefix) != 0) return false;
    for (unsigned char c : n) if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return false;
    return true;
}
std::string userDisplay(const std::string &n) { return isUserName(n) ? n.substr(2) : n; }

// ------------------------------------------------------------------------------------------------ sha1
std::string sha1Hex(const void *data, size_t n)
{
    uint32_t h[5] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0};
    const uint8_t *p = (const uint8_t *)data;
    std::vector<uint8_t> m(p, p + n);
    uint64_t bits = (uint64_t)n * 8;
    m.push_back(0x80);
    while (m.size() % 64 != 56) m.push_back(0);
    for (int i = 7; i >= 0; i--) m.push_back((uint8_t)(bits >> (8 * i)));
    auto rol = [](uint32_t x, int k) { return (x << k) | (x >> (32 - k)); };
    for (size_t c = 0; c < m.size(); c += 64) {
        uint32_t w[80];
        for (int i = 0; i < 16; i++) w[i] = (uint32_t)m[c + 4 * i] << 24 | (uint32_t)m[c + 4 * i + 1] << 16 | (uint32_t)m[c + 4 * i + 2] << 8 | m[c + 4 * i + 3];
        for (int i = 16; i < 80; i++) w[i] = rol(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
        uint32_t a = h[0], b = h[1], cc = h[2], d = h[3], e = h[4];
        for (int i = 0; i < 80; i++) {
            uint32_t f, k;
            if (i < 20) { f = (b & cc) | (~b & d); k = 0x5A827999; }
            else if (i < 40) { f = b ^ cc ^ d; k = 0x6ED9EBA1; }
            else if (i < 60) { f = (b & cc) | (b & d) | (cc & d); k = 0x8F1BBCDC; }
            else { f = b ^ cc ^ d; k = 0xCA62C1D6; }
            uint32_t t = rol(a, 5) + f + e + k + w[i];
            e = d; d = cc; cc = rol(b, 30); b = a; a = t;
        }
        h[0] += a; h[1] += b; h[2] += cc; h[3] += d; h[4] += e;
    }
    char o[41];
    for (int i = 0; i < 5; i++) std::snprintf(o + 8 * i, 9, "%08x", h[i]);
    return o;
}

// ------------------------------------------------------------------------------------------------ base64
static const char *kB64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
std::string base64(const void *data, size_t n)
{
    const uint8_t *p = (const uint8_t *)data;
    std::string o;
    for (size_t i = 0; i < n; i += 3) {
        uint32_t v = (uint32_t)p[i] << 16 | (i + 1 < n ? (uint32_t)p[i + 1] << 8 : 0) | (i + 2 < n ? p[i + 2] : 0);
        o += kB64[v >> 18 & 63]; o += kB64[v >> 12 & 63];
        o += i + 1 < n ? kB64[v >> 6 & 63] : '='; o += i + 2 < n ? kB64[v & 63] : '=';
    }
    return o;
}
bool unbase64(const std::string &s, std::vector<uint8_t> &out)
{
    out.clear();
    uint32_t v = 0; int k = 0;
    for (char c : s) {
        if (c == '=') break;
        const char *q = std::strchr(kB64, c);
        if (!q || !c) return false;
        v = v << 6 | (uint32_t)(q - kB64);
        if (++k == 4) { out.push_back((uint8_t)(v >> 16)); out.push_back((uint8_t)(v >> 8)); out.push_back((uint8_t)v); v = 0; k = 0; }
    }
    if (k == 2) out.push_back((uint8_t)(v >> 4));
    else if (k == 3) { out.push_back((uint8_t)(v >> 10)); out.push_back((uint8_t)(v >> 2)); }
    else if (k == 1) return false;
    return true;
}

// ------------------------------------------------------------------------------------------------ crc32, adler32
uint32_t crc32(const void *data, size_t n, uint32_t crc)
{
    static uint32_t t[256]; static bool made;
    if (!made) { for (uint32_t i = 0; i < 256; i++) { uint32_t c = i; for (int k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320u ^ (c >> 1) : c >> 1; t[i] = c; } made = true; }
    const uint8_t *p = (const uint8_t *)data;
    crc = ~crc;
    for (size_t i = 0; i < n; i++) crc = t[(crc ^ p[i]) & 255] ^ (crc >> 8);
    return ~crc;
}
static uint32_t adler32(const uint8_t *p, size_t n)
{
    uint32_t a = 1, b = 0;
    for (size_t i = 0; i < n; i++) { a = (a + p[i]) % 65521; b = (b + a) % 65521; }
    return b << 16 | a;
}

// ------------------------------------------------------------------------------------------------ deflate (fixed Huffman)
namespace {
struct BitOut {
    std::vector<uint8_t> &o; uint32_t acc = 0; int n = 0;
    explicit BitOut(std::vector<uint8_t> &v) : o(v) {}
    void put(uint32_t bits, int k) { acc |= bits << n; n += k; while (n >= 8) { o.push_back((uint8_t)acc); acc >>= 8; n -= 8; } }
    void putRev(uint32_t code, int k) { uint32_t r = 0; for (int i = 0; i < k; i++) r |= ((code >> i) & 1) << (k - 1 - i); put(r, k); }   // Huffman codes go MSB first
    void flush() { if (n) { o.push_back((uint8_t)acc); acc = 0; n = 0; } }
};
const int kLenBase[29] = {3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258};
const int kLenExtra[29] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0};
const int kDistBase[30] = {1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577};
const int kDistExtra[30] = {0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13};
void fixedLit(BitOut &b, int sym)   // the fixed literal/length code (RFC 1951 3.2.6)
{
    if (sym < 144) b.putRev(0x30 + sym, 8);
    else if (sym < 256) b.putRev(0x190 + sym - 144, 9);
    else if (sym < 280) b.putRev(sym - 256, 7);
    else b.putRev(0xC0 + sym - 280, 8);
}
}  // namespace

std::vector<uint8_t> zlibCompress(const void *data, size_t n)
{
    const uint8_t *p = (const uint8_t *)data;
    std::vector<uint8_t> o{0x78, 0x01};   // deflate, 32 KiB window, fastest
    BitOut b(o);
    b.put(1, 1); b.put(1, 2);              // the last block, fixed Huffman
    const int H = 1 << 15; std::vector<int32_t> head(H, -1), prev(n ? n : 1, -1);
    auto hash = [&](size_t i) { return (int)(((uint32_t)p[i] << 10 ^ (uint32_t)p[i + 1] << 5 ^ p[i + 2]) & (H - 1)); };
    size_t i = 0;
    while (i < n) {
        int bestLen = 0, bestDist = 0;
        if (i + 2 < n) {
            int h = hash(i), chain = 32;
            for (int32_t j = head[(size_t)h]; j >= 0 && chain-- > 0 && i - (size_t)j <= 32768; j = prev[(size_t)j]) {
                int L = 0; while (L < 258 && i + L < n && p[(size_t)j + L] == p[i + L]) L++;
                if (L > bestLen) { bestLen = L; bestDist = (int)(i - (size_t)j); if (L == 258) break; }
            }
        }
        if (bestLen >= 3) {
            int li = 0; while (li < 28 && kLenBase[li + 1] <= bestLen) li++;
            fixedLit(b, 257 + li); if (kLenExtra[li]) b.put((uint32_t)(bestLen - kLenBase[li]), kLenExtra[li]);
            int di = 0; while (di < 29 && kDistBase[di + 1] <= bestDist) di++;
            b.putRev((uint32_t)di, 5); if (kDistExtra[di]) b.put((uint32_t)(bestDist - kDistBase[di]), kDistExtra[di]);
            for (int k = 0; k < bestLen; k++, i++) if (i + 2 < n) { int h = hash(i); prev[i] = head[(size_t)h]; head[(size_t)h] = (int32_t)i; }
        } else {
            fixedLit(b, p[i]);
            if (i + 2 < n) { int h = hash(i); prev[i] = head[(size_t)h]; head[(size_t)h] = (int32_t)i; }
            i++;
        }
    }
    fixedLit(b, 256);
    b.flush();
    uint32_t a = adler32(p, n);
    for (int k = 3; k >= 0; k--) o.push_back((uint8_t)(a >> (8 * k)));
    return o;
}

// ------------------------------------------------------------------------------------------------ inflate
namespace {
struct BitIn {
    const uint8_t *p; size_t n, i = 0; uint32_t acc = 0; int k = 0; bool bad = false;
    uint32_t get(int c) { while (k < c) { if (i >= n) { bad = true; return 0; } acc |= (uint32_t)p[i++] << k; k += 8; } uint32_t v = acc & ((1u << c) - 1); acc >>= c; k -= c; return v; }
    void align() { acc = 0; k = 0; }
};
struct Huff { std::vector<int> count = std::vector<int>(16, 0), sym; };
bool build(Huff &h, const int *len, int n)
{
    h.count.assign(16, 0); h.sym.assign((size_t)n, 0);
    for (int i = 0; i < n; i++) h.count[(size_t)len[i]]++;
    h.count[0] = 0;
    std::vector<int> offs(16, 0);
    for (int i = 1; i < 16; i++) offs[(size_t)i] = offs[(size_t)i - 1] + h.count[(size_t)i - 1];
    for (int i = 0; i < n; i++) if (len[i]) h.sym[(size_t)offs[(size_t)len[i]]++] = i;
    return true;
}
int decode(BitIn &b, const Huff &h)
{
    int code = 0, first = 0, index = 0;
    for (int len = 1; len < 16; len++) {
        code |= (int)b.get(1); if (b.bad) return -1;
        int c = h.count[(size_t)len];
        if (code - c < first) return h.sym[(size_t)(index + (code - first))];
        index += c; first += c; first <<= 1; code <<= 1;
    }
    return -1;
}
}  // namespace

bool zlibDecompress(const void *data, size_t n, std::vector<uint8_t> &out, size_t maxOut)
{
    const uint8_t *p = (const uint8_t *)data;
    out.clear();
    if (n < 6 || (p[0] & 15) != 8 || ((p[0] << 8 | p[1]) % 31) || (p[1] & 0x20)) return false;
    BitIn b{p + 2, n - 6};
    for (int last = 0; !last;) {
        last = (int)b.get(1);
        int type = (int)b.get(2);
        if (b.bad) return false;
        if (type == 0) {
            b.align();
            if (b.i + 4 > b.n) return false;
            unsigned len = b.p[b.i] | b.p[b.i + 1] << 8; b.i += 4;
            if (b.i + len > b.n || out.size() + len > maxOut) return false;
            out.insert(out.end(), b.p + b.i, b.p + b.i + len); b.i += len;
            continue;
        }
        Huff lit, dist;
        if (type == 1) {
            int l[288], d[30];
            for (int i = 0; i < 288; i++) l[i] = i < 144 ? 8 : i < 256 ? 9 : i < 280 ? 7 : 8;
            for (int i = 0; i < 30; i++) d[i] = 5;
            build(lit, l, 288); build(dist, d, 30);
        } else if (type == 2) {
            int nl = (int)b.get(5) + 257, nd = (int)b.get(5) + 1, nc = (int)b.get(4) + 4;
            static const int ord[19] = {16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15};
            int cl[19] = {0}, lens[320] = {0};
            for (int i = 0; i < nc; i++) cl[ord[i]] = (int)b.get(3);
            Huff ch; build(ch, cl, 19);
            for (int i = 0; i < nl + nd;) {
                int s = decode(b, ch); if (s < 0) return false;
                if (s < 16) lens[i++] = s;
                else {
                    int rep = 0, v = 0;
                    if (s == 16) { if (!i) return false; v = lens[i - 1]; rep = 3 + (int)b.get(2); }
                    else if (s == 17) rep = 3 + (int)b.get(3);
                    else rep = 11 + (int)b.get(7);
                    if (i + rep > nl + nd) return false;
                    while (rep--) lens[i++] = v;
                }
            }
            build(lit, lens, nl); build(dist, lens + nl, nd);
        } else return false;
        for (;;) {
            int s = decode(b, lit); if (s < 0) return false;
            if (s < 256) { if (out.size() >= maxOut) return false; out.push_back((uint8_t)s); continue; }
            if (s == 256) break;
            s -= 257; if (s >= 29) return false;
            int len = kLenBase[s] + (int)b.get(kLenExtra[s]);
            int ds = decode(b, dist); if (ds < 0 || ds >= 30) return false;
            size_t d = (size_t)kDistBase[ds] + b.get(kDistExtra[ds]);
            if (b.bad || d > out.size() || out.size() + (size_t)len > maxOut) return false;
            for (int k = 0; k < len; k++) out.push_back(out[out.size() - d]);
        }
    }
    b.align();
    if (b.i + 4 > b.n + 4) return false;
    const uint8_t *t = p + 2 + b.i;
    if (t + 4 > p + n) return false;
    uint32_t a = (uint32_t)t[0] << 24 | (uint32_t)t[1] << 16 | (uint32_t)t[2] << 8 | t[3];
    return a == adler32(out.data(), out.size());
}

// ------------------------------------------------------------------------------------------------ .b16
std::vector<uint8_t> b16Write(const std::string &text, bool compress)
{
    std::vector<uint8_t> payload = compress ? zlibCompress(text.data(), text.size()) : std::vector<uint8_t>(text.begin(), text.end());
    std::vector<uint8_t> o{'B', '1', '6', 'S', 1, 0, (uint8_t)(compress ? 1 : 0), 0};
    uint32_t len = (uint32_t)text.size(), c = crc32(text.data(), text.size());
    for (int k = 0; k < 4; k++) o.push_back((uint8_t)(len >> (8 * k)));
    for (int k = 0; k < 4; k++) o.push_back((uint8_t)(c >> (8 * k)));
    o.insert(o.end(), payload.begin(), payload.end());
    return o;
}
bool b16Read(const void *data, size_t n, std::string &text, std::string *err)
{
    const uint8_t *p = (const uint8_t *)data;
    auto fail = [&](const char *m) { if (err) *err = m; return false; };
    if (n < 16 || std::memcmp(p, "B16S", 4)) return fail("not a BASILISK 16 state file (no B16S)");
    unsigned ver = p[4] | p[5] << 8, flags = p[6] | p[7] << 8;
    if (ver != 1) return fail("a state file of a later version");
    uint32_t len = p[8] | p[9] << 8 | p[10] << 16 | (uint32_t)p[11] << 24, c = p[12] | p[13] << 8 | p[14] << 16 | (uint32_t)p[15] << 24;
    std::vector<uint8_t> out;
    if (flags & 1) { if (!zlibDecompress(p + 16, n - 16, out, (size_t)len + 1)) return fail("the state file is damaged (inflate)"); }
    else out.assign(p + 16, p + n);
    if (out.size() != len || crc32(out.data(), out.size()) != c) return fail("the state file is damaged (length or CRC)");
    text.assign(out.begin(), out.end());
    return true;
}

// ------------------------------------------------------------------------------------------------ the index
std::vector<UserEntry> readIndex(const std::string &tsv)
{
    std::vector<UserEntry> v;
    std::istringstream in(tsv); std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty() || line[0] == '#') continue;
        std::vector<std::string> f; size_t a = 0, b;
        while ((b = line.find('\t', a)) != std::string::npos) { f.push_back(line.substr(a, b - a)); a = b + 1; }
        f.push_back(line.substr(a));
        if (f.size() < 3 || !isUserName(f[0])) continue;
        UserEntry e; e.name = f[0]; e.sha1 = f[1]; e.file = f[2];
        if (f.size() > 3) e.ms = std::atol(f[3].c_str());
        if (f.size() > 4) e.format = f[4];
        if (f.size() > 5) e.saved = f[5];
        if (f.size() > 6) e.edition = f[6];
        v.push_back(e);
    }
    return v;
}
std::string writeIndex(const std::vector<UserEntry> &v)
{
    std::string o = "# name\tsha1\tfile\tms\tformat\tsaved\tedition\n";
    for (const auto &e : v) o += e.name + "\t" + e.sha1 + "\t" + e.file + "\t" + std::to_string(e.ms) + "\t" + e.format + "\t" + e.saved + "\t" + e.edition + "\n";
    return o;
}
std::string freeName(const std::vector<UserEntry> &idx, const std::string &name, const std::string &sha1)
{
    auto taken = [&](const std::string &n, bool &same) { for (const auto &e : idx) if (e.name == n) { same = e.sha1 == sha1; return true; } return false; };
    bool same = false;
    if (!taken(name, same) || same) return name;
    for (int k = 2; k < 10000; k++) {
        std::string n = name + "_" + std::to_string(k);
        if (n.size() > 26) n = name.substr(0, 26 - std::to_string(k).size() - 1) + "_" + std::to_string(k);
        if (!taken(n, same) || same) return n;
    }
    return name;
}

Resolve resolveUser(bool inFolder, bool inVersions, bool embedded)
{
    if (inFolder) return Resolve::Folder;
    if (inVersions) return Resolve::Version;
    if (embedded) return Resolve::Embedded;
    return Resolve::Missing;
}

std::string userLine(const std::string &name, const std::vector<uint8_t> &wav, bool embed)
{
    std::string o = name + " " + sha1Hex(wav.data(), wav.size()) + " " + std::to_string(wav.size());
    if (embed) { std::vector<uint8_t> z = zlibCompress(wav.data(), wav.size()); o += " " + base64(z.data(), z.size()); }
    return o;
}
bool parseUserLine(const std::string &v, std::string &name, std::string &sha1, size_t &bytes, std::vector<uint8_t> *wav)
{
    std::istringstream in(v); std::string b64;
    if (!(in >> name >> sha1 >> bytes) || !isUserName(name) || sha1.size() != 40) return false;
    if (wav) {
        wav->clear();
        if (in >> b64) {
            std::vector<uint8_t> z;
            if (!unbase64(b64, z) || !zlibDecompress(z.data(), z.size(), *wav, bytes + 1) || wav->size() != bytes || sha1Hex(wav->data(), wav->size()) != sha1) { wav->clear(); return false; }
        }
    }
    return true;
}

}  // namespace bsynth

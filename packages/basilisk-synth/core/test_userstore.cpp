// userstore checks: names, sha1, base64, zlib both ways (and against Python's zlib), .b16, the index, user lines
#include "userstore.h"
#include <cstdio>
#include <cstdlib>
#include <string>
using namespace bsynth;
static int fails = 0, checks = 0;
#define CHECK(c) do { checks++; if (!(c)) { fails++; std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
int main(int argc, char **argv)
{
    CHECK(userName("My Vox (2)") == "u_my_vox_2");
    CHECK(userName("__A--b__") == "u_a_b");
    CHECK(userName("***") == "");
    CHECK(userName("abcdefghijklmnopqrstuvwxyz0123") == "u_abcdefghijklmnopqrstuvwx");
    CHECK(isUserName("u_vox") && !isUserName("vox") && !isUserName("u_Vox") && userDisplay("u_vox") == "vox");
    CHECK(sha1Hex("abc", 3) == "a9993e364706816aba3e25717850c26c9cd0d89d");
    CHECK(sha1Hex("", 0) == "da39a3ee5e6b4b0d3255bfef95601890afd80709");
    { std::string m(1000000, 'a'); CHECK(sha1Hex(m.data(), m.size()) == "34aa973cd4c4daa4f61eeb2bdbad27316534016f"); }
    CHECK(base64("Man", 3) == "TWFu" && base64("Ma", 2) == "TWE=" && base64("M", 1) == "TQ==");
    { std::vector<uint8_t> o; CHECK(unbase64("TWFu", o) && o.size() == 3 && o[2] == 'n'); CHECK(unbase64("TQ==", o) && o.size() == 1); }
    CHECK(crc32("123456789", 9) == 0xCBF43926u);
    {   // Python's zlib.compress(level 9): dynamic Huffman blocks
        const unsigned char py[] = {120,218,115,114,12,246,244,241,12,246,214,13,142,244,11,241,80,48,228,74,201,75,84,72,201,204,75,87,54,52,179,14,50,52,50,224,42,74,77,75,45,74,205,75,78,85,48,224,114,26,85,61,170,122,84,53,29,84,3,0,115,248,6,184};
        std::vector<uint8_t> out;
        std::string want; for (int i = 0; i < 20; i++) want += "BASILISK-SYNTH 1\ndna ding#16;R120\nreference 0\n";
        CHECK(zlibDecompress(py, sizeof py, out) && std::string(out.begin(), out.end()) == want);
    }
    {   // ours both ways, on text, noise and silence
        srand(7);
        for (int t = 0; t < 40; t++) {
            std::vector<uint8_t> d((size_t)(rand() % 70000));
            for (auto &x : d) x = (uint8_t)(t % 3 == 0 ? rand() : t % 3 == 1 ? 128 : "ding#16;R120 "[rand() % 13]);
            std::vector<uint8_t> z = zlibCompress(d.data(), d.size()), back;
            CHECK(zlibDecompress(z.data(), z.size(), back) && back == d);
            if (t % 3 == 1 && d.size() > 1000) CHECK(z.size() < d.size() / 20);
        }
    }
    {   // .b16
        std::string s = "BASILISK-SYNTH 1\ndna ding#16;R120\nreference 0\nkey 2 7\n", r, err;
        std::vector<uint8_t> f = b16Write(s);
        CHECK(f.size() > 16 && f[0] == 'B' && f[6] == 1 && b16Read(f.data(), f.size(), r) && r == s);
        std::vector<uint8_t> g = b16Write(s, false);
        CHECK(g[6] == 0 && b16Read(g.data(), g.size(), r) && r == s);
        f[f.size() - 3] ^= 1; CHECK(!b16Read(f.data(), f.size(), r, &err) && !err.empty());
        if (argc > 1) { FILE *o = std::fopen(argv[1], "wb"); std::vector<uint8_t> h = b16Write(s); std::fwrite(h.data(), 1, h.size(), o); std::fclose(o); }
    }
    {   // the index and new names
        std::vector<UserEntry> idx = readIndex("# name\tsha1\tfile\n" "u_vox\taaa\tvox.wav\t2400\tpcm16\t2026-11-13\tw31\n" "bad\tx\ty\n");
        CHECK(idx.size() == 1 && idx[0].ms == 2400 && readIndex(writeIndex(idx)).size() == 1);
        CHECK(freeName(idx, "u_vox", "aaa") == "u_vox" && freeName(idx, "u_vox", "bbb") == "u_vox_2" && freeName(idx, "u_kick", "c") == "u_kick");
        CHECK(resolveUser(false, false, true) == Resolve::Embedded && resolveUser(true, true, true) == Resolve::Folder && resolveUser(false, false, false) == Resolve::Missing);
    }
    {   // a user line, embedded and not
        std::vector<uint8_t> wav(4000); for (size_t i = 0; i < wav.size(); i++) wav[i] = (uint8_t)(128 + 60 * ((i / 25) % 2));
        std::string l = userLine("u_vox", wav, true), n, h; size_t b; std::vector<uint8_t> back;
        CHECK(parseUserLine(l, n, h, b, &back) && n == "u_vox" && b == wav.size() && back == wav);
        CHECK(parseUserLine(userLine("u_vox", wav, false), n, h, b, &back) && back.empty() && b == 4000);
    }
    std::printf("userstore: %d checks: %s\n", checks, fails ? "FAILED" : "ok");
    return fails ? 1 : 0;
}

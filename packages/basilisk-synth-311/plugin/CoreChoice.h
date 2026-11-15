// SNDWAVE2000: the emulated CPU core a machine runs with. The machine's w31.conf (and its snapshots) say core=normal;
// where the dynamic core works it is used instead: the same machine, bit-identical renders, faster (the multitimbral
// experiment). It does not start on macOS arm64, which keeps normal. SNDWAVE2000_CORE=normal|dynamic overrides.
#pragma once
#include <cstdlib>
#include <string>

inline void chooseCore(std::string &conf)
{
#if defined(__aarch64__) || defined(_M_ARM64)
    std::string want = "normal";
#else
    std::string want = "dynamic";
#endif
    if (const char *e = std::getenv("SNDWAVE2000_CORE")) if (*e) want = e;
    const size_t p = conf.find("core=normal");
    if (p != std::string::npos) conf.replace(p, 11, "core=" + want);
}

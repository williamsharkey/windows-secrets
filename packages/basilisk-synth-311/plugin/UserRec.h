// SNDWAVE1993 (BASILISK 16 in the code): My Recordings on the host (design/RECORDING.md sections 2.4, 3.1, 3.2), for the plugin and render311.
//   - the shared folder Documents/SNDWAVE1993/My Recordings: <name>.wav, index.tsv, .versions/<sha1>.wav; the plugin
//     process is its only writer (a lock file, a temporary file renamed into place)
//   - the instance's R: drive (a folder DOSBox mounts): the recordings copied in as U0001.WAV ..., and Windows' own
//     Save As writes there; `rec saved R:\NAME.WAV` makes the host check the file and publish it
// The names, hashes and the index format are core/userstore.
#pragma once
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <ctime>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <cmath>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#else
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#endif
#include "../../basilisk-synth/core/userstore.h"

namespace b16rec {

inline bool readFile(const std::string &p, std::vector<uint8_t> &d)
{
    FILE *f = std::fopen(p.c_str(), "rb"); if (!f) return false;
    d.clear(); uint8_t b[65536]; size_t n;
    while ((n = std::fread(b, 1, sizeof b, f)) > 0) d.insert(d.end(), b, b + n);
    std::fclose(f); return true;
}
inline bool writeFile(const std::string &p, const void *data, size_t n)   // a temporary file, renamed into place
{
    const std::string t = p + ".tmp";
    FILE *f = std::fopen(t.c_str(), "wb"); if (!f) return false;
    bool ok = std::fwrite(data, 1, n, f) == n; ok = std::fclose(f) == 0 && ok;
    if (!ok) { std::remove(t.c_str()); return false; }
#ifdef _WIN32
    return MoveFileExA(t.c_str(), p.c_str(), MOVEFILE_REPLACE_EXISTING) != 0;
#else
    return std::rename(t.c_str(), p.c_str()) == 0;
#endif
}
inline void makeDir(const std::string &p)
{
#ifdef _WIN32
    CreateDirectoryA(p.c_str(), nullptr);
#else
    mkdir(p.c_str(), 0755);
#endif
}
inline std::string myRecordingsDir()   // Documents/SNDWAVE1993/My Recordings (made if missing; SNDWAVE2000's if only that one exists); BASILISK16_MYREC overrides
{
    if (const char *e = std::getenv("BASILISK16_MYREC")) if (*e) { makeDir(e); return e; }
#ifdef _WIN32
    const char *home = std::getenv("USERPROFILE"); std::string d = std::string(home ? home : "C:") + "\\Documents"; const char *sep = "\\";
#else
    const char *home = std::getenv("HOME"); std::string d = std::string(home ? home : "/tmp") + "/Documents"; const char *sep = "/";
#endif
    makeDir(d);
    // SNDWAVE1993 was SNDWAVE2000 until 1.4: a machine that has only the old folder keeps using it (its recordings stay)
    auto isDir = [](const std::string &p) { FILE *f = std::fopen((p + "/index.tsv").c_str(), "rb"); if (f) std::fclose(f); return f != nullptr; };
    const std::string fresh = d + sep + "SNDWAVE1993", old = d + sep + "SNDWAVE2000";
    d = (!isDir(fresh + sep + "My Recordings") && isDir(old + sep + "My Recordings")) ? old : fresh;
    makeDir(d); d += sep; d += "My Recordings"; makeDir(d); makeDir(d + sep + ".versions");
    return d;
}
struct Lock {   // index.lock, made exclusively: one writer at a time, across instances and editions
    std::string path; bool held = false;
    explicit Lock(const std::string &dir) : path(dir + "/index.lock")
    {
        for (int k = 0; k < 100 && !held; k++) {
#ifdef _WIN32
            HANDLE h = CreateFileA(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
            if (h != INVALID_HANDLE_VALUE) { CloseHandle(h); held = true; }
#else
            int fd = open(path.c_str(), O_CREAT | O_EXCL | O_WRONLY, 0644);
            if (fd >= 0) { close(fd); held = true; }
#endif
            if (!held) std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
    }
    ~Lock() { if (held) std::remove(path.c_str()); }
};
struct Wav { bool ok = false; int rate = 0, bits = 0, ch = 0; long ms = 0; std::string fmt; };
inline Wav wavInfo(const std::vector<uint8_t> &d)   // a PCM WAV Sound Recorder opens (RECORDING.md 2.4)
{
    Wav w;
    if (d.size() < 44 || std::string(d.begin(), d.begin() + 4) != "RIFF" || std::string(d.begin() + 8, d.begin() + 12) != "WAVE") return w;
    size_t p = 12; long dataLen = -1;
    while (p + 8 <= d.size()) {
        const std::string id(d.begin() + (long)p, d.begin() + (long)p + 4);
        const uint32_t n = d[p + 4] | d[p + 5] << 8 | d[p + 6] << 16 | (uint32_t)d[p + 7] << 24;
        if (id == "fmt " && p + 24 <= d.size()) {
            if ((d[p + 8] | d[p + 9] << 8) != 1) return w;   // PCM only
            w.ch = d[p + 10] | d[p + 11] << 8; w.rate = (int)(d[p + 12] | d[p + 13] << 8 | d[p + 14] << 16 | (uint32_t)d[p + 15] << 24); w.bits = d[p + 22] | d[p + 23] << 8;
        } else if (id == "data") { dataLen = (long)std::min<size_t>(n, d.size() - p - 8); break; }
        p += 8 + n + (n & 1);
    }
    if (dataLen < 0 || !w.rate || (w.bits != 8 && w.bits != 16) || (w.ch != 1 && w.ch != 2)) return w;
    w.ms = (long)((double)dataLen / (w.rate * w.ch * (w.bits / 8)) * 1000.0);
    w.fmt = "pcm" + std::to_string(w.bits) + "-" + std::to_string(w.rate) + (w.ch == 2 ? "-stereo" : "-mono");
    w.ok = true;
    return w;
}
inline void clearDir(const std::string &dir)   // the instance's R: at the end: its files, then the folder
{
    if (dir.empty()) return;
#ifdef _WIN32
    WIN32_FIND_DATAA fd; HANDLE h = FindFirstFileA((dir + "\\*").c_str(), &fd);
    if (h != INVALID_HANDLE_VALUE) {
        do { if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) DeleteFileA((dir + "\\" + fd.cFileName).c_str()); } while (FindNextFileA(h, &fd));
        FindClose(h);
    }
    RemoveDirectoryA(dir.c_str());
#else
    if (DIR *d = opendir(dir.c_str())) {
        while (dirent *e = readdir(d)) if (e->d_name[0] != '.') std::remove((dir + "/" + e->d_name).c_str());
        closedir(d);
    }
    rmdir(dir.c_str());
#endif
}
inline std::string guestPath(int k) { char b[16]; std::snprintf(b, sizeof b, "R:\\U%04d.WAV", k + 1); return b; }
inline std::string hostName(int k) { char b[16]; std::snprintf(b, sizeof b, "U%04d.WAV", k + 1); return b; }

// The instance's R: drive from My Recordings: each recording copied in as U0001.WAV ...; returns the `user` lines
// for Windows and the names (for the core's name table)
inline std::vector<std::string> populate(const std::string &myDir, const std::string &recDir, std::vector<std::string> &names)
{
    std::vector<std::string> lines; std::vector<uint8_t> idx, wav;
    if (!readFile(myDir + "/index.tsv", idx)) return lines;
    const std::vector<bsynth::UserEntry> e = bsynth::readIndex(std::string(idx.begin(), idx.end()));
    for (size_t k = 0; k < e.size() && k < 60; k++) {
        if (!readFile(myDir + "/" + e[k].file, wav)) continue;
        if (!writeFile(recDir + "/" + hostName((int)k), wav.data(), wav.size())) continue;
        lines.push_back("user " + e[k].name + " " + guestPath((int)k) + " " + std::to_string(e[k].ms) + " " + e[k].format);
        names.push_back(e[k].name);
    }
    return lines;
}
// Windows saved `path` (R:\NAME.WAV): check it (PCM, at most 30 s), name it (u_ + the stem), publish it in My
// Recordings (a new name if another recording has it, the old version kept by hash). Returns the `user` line.
// (`stemFrom`: the path whose stem names it; a U0001.WAV the host copied in keeps its recording's name)
// The name taken by a different recording (RECORDING.md 2.4): mode 0 asks (returns false, `ask` = "<name> <ms>
// <date>"), 1 replaces it (the old one stays in .versions), 2 keeps both (name_2 ...).
inline bool publish(const std::string &myDir, const std::string &recDir, const std::string &path, const std::string &stemFrom,
                    const std::string &edition, std::string &line, std::string &name, std::string &err, int mode = 0,
                    std::string *ask = nullptr)
{
    std::string file = path;
    { const size_t s = file.find_last_of("\\/:"); if (s != std::string::npos) file = file.substr(s + 1); }
    std::string stem = stemFrom;
    { const size_t s = stem.find_last_of("\\/:"); if (s != std::string::npos) stem = stem.substr(s + 1); }
    const size_t dot = stem.rfind('.'); if (dot != std::string::npos) stem.resize(dot);
    if (!(path.size() > 2 && (path[0] == 'R' || path[0] == 'r') && path[1] == ':')) { err = "name Save it on R:, My Recordings"; return false; }
    std::vector<uint8_t> wav;
    if (!readFile(recDir + "/" + file, wav)) { err = "name the file is not on R:"; return false; }
    const Wav w = wavInfo(wav);
    if (!w.ok) { err = "format Only PCM WAV (8 or 16 bit) can be used."; return false; }
    if (w.ms > 30000) { err = "long Over 30 seconds. Trim it with Edit > Delete After Current Position."; return false; }
    std::string n = bsynth::userName(stem);
    if (n.empty()) { err = "name A name of letters and digits, please"; return false; }
    const std::string sha = bsynth::sha1Hex(wav.data(), wav.size());
    makeDir(myDir + "/.versions");
    Lock lock(myDir);
    if (!lock.held) { err = "full My Recordings is busy (index.lock)"; return false; }
    std::vector<uint8_t> idxText; readFile(myDir + "/index.tsv", idxText);
    std::vector<bsynth::UserEntry> idx = bsynth::readIndex(std::string(idxText.begin(), idxText.end()));
    int at = -1;
    for (size_t k = 0; k < idx.size(); k++) if (idx[k].name == n) at = (int)k;
    if (at >= 0 && idx[at].sha1 != sha) {
        if (mode == 0) {
            if (ask) *ask = n + " " + std::to_string(idx[at].ms) + " " + (idx[at].saved.empty() ? "-" : idx[at].saved);
            err = "ask"; return false;
        }
        if (mode == 1) idx.erase(idx.begin() + at);   // replaced (its bytes are in .versions under its hash)
        else n = bsynth::freeName(idx, n, sha);
    }
    bool known = false;
    for (auto &e : idx) if (e.name == n) { known = true; break; }
    const std::string out = n.substr(2) + ".wav";
    if (!known) {
        if (!writeFile(myDir + "/" + out, wav.data(), wav.size())) { err = "full cannot write to My Recordings"; return false; }
        writeFile(myDir + "/.versions/" + sha + ".wav", wav.data(), wav.size());
        bsynth::UserEntry e; e.name = n; e.sha1 = sha; e.file = out; e.ms = w.ms; e.format = w.fmt; e.edition = edition;
        char when[32]; std::time_t t = std::time(nullptr); std::strftime(when, sizeof when, "%Y-%m-%d", std::localtime(&t)); e.saved = when;
        idx.push_back(e);
        const std::string text = bsynth::writeIndex(idx);
        if (!writeFile(myDir + "/index.tsv", text.data(), text.size())) { err = "full cannot write the index"; return false; }
    }
    name = n;
    line = "user " + n + " " + path + " " + std::to_string(w.ms) + " " + w.fmt;
    return true;
}

// ---- recall (RECORDING.md 3.3)
inline std::vector<std::string> usedNames(const std::string &dna)   // the u_ names a DNA uses
{
    std::vector<std::string> v;
    auto isn = [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_'; };
    for (size_t i = 0; i + 2 < dna.size(); i++) {
        if (dna[i] != 'u' || dna[i + 1] != '_' || (i && isn(dna[i - 1]))) continue;
        size_t e = i + 2; while (e < dna.size() && isn(dna[e])) e++;
        const std::string n = dna.substr(i, e - i);
        if (std::find(v.begin(), v.end(), n) == v.end()) v.push_back(n);
        i = e;
    }
    return v;
}
inline std::vector<bsynth::UserEntry> index(const std::string &myDir)
{
    std::vector<uint8_t> t; readFile(myDir + "/index.tsv", t);
    return bsynth::readIndex(std::string(t.begin(), t.end()));
}
// the bytes of a recording: the pinned version if there is one, else the folder's current file
inline bool findWav(const std::string &myDir, const std::string &name, const std::string &pinnedSha, std::vector<uint8_t> &wav)
{
    if (!pinnedSha.empty() && readFile(myDir + "/.versions/" + pinnedSha + ".wav", wav)) return true;
    for (const auto &e : index(myDir)) if (e.name == name) return readFile(myDir + "/" + e.file, wav);
    return false;
}
// A state's `user` line: find that exact recording (the folder, .versions, else the embedded copy, which is then
// saved: under its name if the name is free, else in .versions only). If it is not the folder's current file, a copy
// goes onto R: and `line` is the `user` line for Windows. Returns false if the recording is missing.
inline bool recall(const std::string &myDir, const std::string &recDir, const std::string &value, std::string &name,
                   std::string &sha, std::string &line, bool &pinned)
{
    size_t bytes = 0; std::vector<uint8_t> emb;
    line.clear(); pinned = false;
    if (!bsynth::parseUserLine(value, name, sha, bytes, &emb)) return false;
    std::vector<bsynth::UserEntry> idx = index(myDir);
    for (const auto &e : idx) if (e.name == name && e.sha1 == sha) return true;   // the folder's current file
    std::vector<uint8_t> wav;
    const std::string ver = myDir + "/.versions/" + sha + ".wav";
    if (!readFile(ver, wav)) {
        if (emb.empty()) return false;
        wav = emb;
        makeDir(myDir + "/.versions");
        Lock lock(myDir);
        writeFile(ver, wav.data(), wav.size());
        bool taken = false; for (const auto &e : idx) if (e.name == name) taken = true;
        const Wav w = wavInfo(wav);
        if (!taken && w.ok && lock.held) {   // the name is free here: it is a recording of this machine's now
            const std::string out = name.substr(2) + ".wav";
            writeFile(myDir + "/" + out, wav.data(), wav.size());
            bsynth::UserEntry e; e.name = name; e.sha1 = sha; e.file = out; e.ms = w.ms; e.format = w.fmt; e.edition = "w31";
            char when[32]; std::time_t t = std::time(nullptr); std::strftime(when, sizeof when, "%Y-%m-%d", std::localtime(&t)); e.saved = when;
            idx.push_back(e);
            const std::string text = bsynth::writeIndex(idx);
            writeFile(myDir + "/index.tsv", text.data(), text.size());
        }
    }
    const Wav w = wavInfo(wav);
    if (!w.ok) return false;
    std::string f = "V" + sha.substr(0, 7) + ".WAV";   // 8.3
    for (auto &c : f) if (c >= 'a' && c <= 'z') c = (char)(c - 32);
    if (!writeFile(recDir + "/" + f, wav.data(), wav.size())) return false;
    line = "user " + name + " R:\\" + f + " " + std::to_string(w.ms) + " " + w.fmt;
    pinned = true;
    return true;
}

// ---- import (RECORDING.md 2.6): a WAV made fit for Sound Recorder. PCM 8/16 at 11, 22 or 44 kHz goes as it is;
// anything else (float, 24 or 32 bit, other rates, more channels) becomes 16-bit PCM at 44.1 kHz.
inline bool importWav(const std::vector<uint8_t> &in, std::vector<uint8_t> &out, std::string &err)
{
    if (in.size() < 44 || std::memcmp(in.data(), "RIFF", 4) || std::memcmp(in.data() + 8, "WAVE", 4)) { err = "not a WAV file"; return false; }
    int fmt = 0, ch = 0, rate = 0, bits = 0; size_t p = 12, data = 0, len = 0;
    auto u16 = [&](size_t o) { return (int)(in[o] | in[o + 1] << 8); };
    auto u32 = [&](size_t o) { return (uint32_t)(in[o] | in[o + 1] << 8 | in[o + 2] << 16 | (uint32_t)in[o + 3] << 24); };
    while (p + 8 <= in.size()) {
        const uint32_t n = u32(p + 4);
        if (!std::memcmp(in.data() + p, "fmt ", 4) && p + 24 <= in.size()) {
            fmt = u16(p + 8); ch = u16(p + 10); rate = (int)u32(p + 12); bits = u16(p + 22);
            if (fmt == 0xFFFE && p + 34 <= in.size()) fmt = u16(p + 32);   // WAVE_FORMAT_EXTENSIBLE: the sub-format
        } else if (!std::memcmp(in.data() + p, "data", 4)) { data = p + 8; len = std::min<size_t>(n, in.size() - data); break; }
        p += 8 + n + (n & 1);
    }
    if (!data || !ch || !rate || !(fmt == 1 || fmt == 3)) { err = "only PCM or float WAV files"; return false; }
    const bool native = fmt == 1 && (bits == 8 || bits == 16) && ch <= 2 && (rate == 11025 || rate == 22050 || rate == 44100);
    if (native) { out = in; return true; }
    const int bps = bits / 8; const size_t frames = len / ((size_t)bps * ch);
    if (!bps || frames == 0) { err = "empty"; return false; }
    auto sample = [&](size_t f, int c) -> float {
        const size_t o = data + (f * ch + c) * bps;
        if (fmt == 3 && bits == 32) { float x; std::memcpy(&x, &in[o], 4); return x; }
        if (fmt == 3 && bits == 64) { double x; std::memcpy(&x, &in[o], 8); return (float)x; }
        switch (bits) {
        case 8: return (in[o] - 128) / 128.f;
        case 16: return (int16_t)(in[o] | in[o + 1] << 8) / 32768.f;
        case 24: return (float)((int32_t)((uint32_t)in[o] << 8 | (uint32_t)in[o + 1] << 16 | (uint32_t)in[o + 2] << 24) >> 8) / 8388608.f;
        case 32: return (float)(int32_t)u32(o) / 2147483648.f;
        }
        return 0.f;
    };
    const int och = ch >= 2 ? 2 : 1;
    const double step = (double)rate / 44100.0;
    const size_t on = (size_t)((double)frames / step);
    std::vector<int16_t> pcm(on * och);
    for (size_t i = 0; i < on; i++) {
        const double t = i * step; const size_t f = (size_t)t; const float fr = (float)(t - f);
        for (int c = 0; c < och; c++) {
            const float a = sample(std::min(f, frames - 1), c), b = sample(std::min(f + 1, frames - 1), c);
            float x = a + (b - a) * fr; x = x > 1.f ? 1.f : x < -1.f ? -1.f : x;
            pcm[i * och + c] = (int16_t)std::lrint(x * 32767.f);
        }
    }
    const uint32_t db = (uint32_t)(pcm.size() * 2);
    out.assign(44, 0);
    auto w32 = [&](size_t o, uint32_t v) { for (int k = 0; k < 4; k++) out[o + k] = (uint8_t)(v >> (8 * k)); };
    auto w16 = [&](size_t o, int v) { out[o] = (uint8_t)v; out[o + 1] = (uint8_t)(v >> 8); };
    std::memcpy(&out[0], "RIFF", 4); w32(4, 36 + db); std::memcpy(&out[8], "WAVEfmt ", 8); w32(16, 16);
    w16(20, 1); w16(22, och); w32(24, 44100); w32(28, 44100 * 2 * och); w16(32, 2 * och); w16(34, 16);
    std::memcpy(&out[36], "data", 4); w32(40, db);
    out.insert(out.end(), (const uint8_t *)pcm.data(), (const uint8_t *)pcm.data() + db);
    return true;
}
inline std::string dosStem(const std::string &file)   // "My Loop (final).wav" -> "MYLOOPFI"
{
    std::string st = file; const size_t d = st.rfind('.'); if (d != std::string::npos) st.resize(d);
    std::string o;
    for (char c : st) { if (c >= 'a' && c <= 'z') c = (char)(c - 32); if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_') o += c; if (o.size() == 8) break; }
    return o.empty() ? "IMPORT" : o;
}

}  // namespace b16rec

// BASILISK SYNTH - the Windows XP machine behind one plugin instance (see Machine.hpp)
#include "Machine.hpp"
#include "machine_info.h"
#define BSYNTH_QEMU_TAG "11.1-1"   // the QEMU zipped into the Windows bundle (Stefan Weil's build, as packages/basilisk-xp)
#include "../core/proto.h"

#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cmath>
#include <cstring>
#include <ctime>
#include <fstream>
#include <sstream>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <shlobj.h>
#include <mmsystem.h>
typedef int socklen_t;
#define CLOSESOCK closesocket
#else
#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
extern char **environ;
#define CLOSESOCK ::close
#endif

namespace bsynth {

// ------------------------------------------------------------------ small helpers
double Machine::now()
{
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

static void sleep_ms(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

static bool exists(const std::string &p)
{
#ifdef _WIN32
    return GetFileAttributesA(p.c_str()) != INVALID_FILE_ATTRIBUTES;
#else
    struct stat st;
    return ::stat(p.c_str(), &st) == 0;
#endif
}
static long long file_size(const std::string &p)
{
#ifdef _WIN32
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExA(p.c_str(), GetFileExInfoStandard, &a)) return -1;
    return ((long long)a.nFileSizeHigh << 32) | a.nFileSizeLow;
#else
    struct stat st;
    return ::stat(p.c_str(), &st) == 0 ? (long long)st.st_size : -1;
#endif
}
static void mkdirs(const std::string &p)
{
    for (size_t i = 1; i <= p.size(); i++) {
        if (i == p.size() || p[i] == '/' || p[i] == '\\') {
            std::string d = p.substr(0, i);
#ifdef _WIN32
            CreateDirectoryA(d.c_str(), NULL);
#else
            ::mkdir(d.c_str(), 0755);
#endif
        }
    }
}
static void remove_file(const std::string &p)
{
#ifdef _WIN32
    DeleteFileA(p.c_str());
#else
    ::unlink(p.c_str());
#endif
}
static void remove_tree(const std::string &dir)
{
#ifdef _WIN32
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA((dir + "\\*").c_str(), &fd);
    if (h != INVALID_HANDLE_VALUE) {
        do {
            std::string n = fd.cFileName;
            if (n == "." || n == "..") continue;
            if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) remove_tree(dir + "\\" + n);
            else DeleteFileA((dir + "\\" + n).c_str());
        } while (FindNextFileA(h, &fd));
        FindClose(h);
    }
    RemoveDirectoryA(dir.c_str());
#else
    std::string cmd = "/bin/rm -rf '" + dir + "'";
    if (dir.size() > 8) { int r = system(cmd.c_str()); (void)r; }
#endif
}
#ifdef _WIN32
static const char SEP = '\\';
#else
static const char SEP = '/';
#endif

std::string Machine::machineDir()
{
    if (const char *e = getenv("BSYNTH_MACHINE_DIR")) return e;
#ifdef _WIN32
    char p[MAX_PATH];
    if (SHGetFolderPathA(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, p) != S_OK) GetTempPathA(MAX_PATH, p);
    return std::string(p) + "\\BASILISK SYNTH\\" BSYNTH_MACHINE_NAME;
#else
    const char *h = getenv("HOME");
    return std::string(h ? h : "/tmp") + "/Library/Application Support/BASILISK SYNTH/" BSYNTH_MACHINE_NAME;
#endif
}

// where this plugin binary lives: QEMU sits beside it in the bundle's Resources
static std::string resources_dir()
{
    std::string p;
#ifdef _WIN32
    HMODULE m = NULL;
    char b[MAX_PATH];
    GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)&resources_dir, &m);
    GetModuleFileNameA(m, b, MAX_PATH);
    p = b;
#else
    Dl_info info;
    if (dladdr((void *)&resources_dir, &info) && info.dli_fname) p = info.dli_fname;
#endif
    // .../Contents/<arch dir>/<binary>  ->  .../Contents/Resources
    for (int i = 0; i < 2; i++) { size_t k = p.find_last_of("/\\"); if (k != std::string::npos) p = p.substr(0, k); }
    if (const char *e = getenv("BSYNTH_RESOURCES")) return e;
    return p + SEP + "Resources";
}

// ------------------------------------------------------------------ SHA-256 (to check the machine download)
namespace {
struct Sha256 {
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    uint8_t buf[64];
    uint64_t len = 0;
    size_t n = 0;
    static uint32_t ror(uint32_t x, int r) { return (x >> r) | (x << (32 - r)); }
    void block(const uint8_t *p)
    {
        static const uint32_t k[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
            0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
            0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
            0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
            0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
            0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
        uint32_t w[64], a, b, c, d, e, f, g, hh;
        for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = ror(w[i - 15], 7) ^ ror(w[i - 15], 18) ^ (w[i - 15] >> 3), s1 = ror(w[i - 2], 17) ^ ror(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        a = h[0]; b = h[1]; c = h[2]; d = h[3]; e = h[4]; f = h[5]; g = h[6]; hh = h[7];
        for (int i = 0; i < 64; i++) {
            uint32_t t1 = hh + (ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)) + ((e & f) ^ (~e & g)) + k[i] + w[i];
            uint32_t t2 = (ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
            hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }
    void add(const uint8_t *p, size_t m)
    {
        len += m;
        while (m) {
            size_t t = 64 - n < m ? 64 - n : m;
            memcpy(buf + n, p, t); n += t; p += t; m -= t;
            if (n == 64) { block(buf); n = 0; }
        }
    }
    std::string hex()
    {
        uint64_t bits = len * 8;
        uint8_t pad = 0x80, z = 0, lb[8];
        add(&pad, 1);
        while (n != 56) add(&z, 1);
        for (int i = 0; i < 8; i++) lb[i] = (uint8_t)(bits >> (56 - 8 * i));
        add(lb, 8);
        char s[65];
        for (int i = 0; i < 8; i++) snprintf(s + 8 * i, 9, "%08x", h[i]);
        return s;
    }
};
}  // namespace

// ------------------------------------------------------------------ sockets
static bool net_init()
{
#ifdef _WIN32
    static bool done = false;
    if (!done) { WSADATA w; WSAStartup(MAKEWORD(2, 2), &w); done = true; }
#endif
    return true;
}
static int free_port(int lo = 0)
{
    net_init();
    for (int tries = 0; tries < 400; tries++) {
        intptr_t s = socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in a = {};
        a.sin_family = AF_INET;
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        a.sin_port = htons(lo ? (uint16_t)(lo + (rand() % 900)) : 0);
        if (bind(s, (sockaddr *)&a, sizeof a) == 0) {
            socklen_t l = sizeof a;
            getsockname(s, (sockaddr *)&a, &l);
            CLOSESOCK(s);
            return ntohs(a.sin_port);
        }
        CLOSESOCK(s);
    }
    return 0;
}
static intptr_t tcp_connect(int port, int timeout_ms, std::atomic<bool> *stop = nullptr)
{
    net_init();
    double end = Machine::now() + timeout_ms / 1000.0;
    while (Machine::now() < end && !(stop && *stop)) {
        intptr_t s = socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in a = {};
        a.sin_family = AF_INET;
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        a.sin_port = htons((uint16_t)port);
        if (connect(s, (sockaddr *)&a, sizeof a) == 0) {
            int one = 1;
            setsockopt(s, IPPROTO_TCP, TCP_NODELAY, (const char *)&one, sizeof one);
            return s;
        }
        CLOSESOCK(s);
        sleep_ms(20);
    }
    return -1;
}
static bool send_all(intptr_t s, const void *p, size_t n)
{
    const char *c = (const char *)p;
    while (n) {
        int k = (int)::send(s, c, (int)(n > (1 << 20) ? (1 << 20) : n), 0);
        if (k <= 0) return false;
        c += k; n -= (size_t)k;
    }
    return true;
}
static bool recv_all(intptr_t s, void *p, size_t n)
{
    char *c = (char *)p;
    while (n) {
        int k = (int)::recv(s, c, (int)n, 0);
        if (k <= 0) return false;
        c += k; n -= (size_t)k;
    }
    return true;
}
// wait up to ms for s to be readable
static bool readable(intptr_t s, int ms)
{
    fd_set f;
    FD_ZERO(&f);
#ifdef _WIN32
    FD_SET((SOCKET)s, &f);
#else
    FD_SET((int)s, &f);
#endif
    timeval tv = {ms / 1000, (ms % 1000) * 1000};
    return select((int)s + 1, &f, NULL, NULL, &tv) > 0;
}

// QMP: one short connection per command
static std::string qmp(int port, const std::string &cmd, int timeout_ms = 5000)
{
    intptr_t s = tcp_connect(port, timeout_ms);
    if (s < 0) return "";
    std::string all, line;
    auto read_line = [&](std::string &out) {
        out.clear();
        double end = Machine::now() + timeout_ms / 1000.0;
        char c;
        while (Machine::now() < end) {
            if (!readable(s, 50)) continue;
            if (::recv(s, &c, 1, 0) != 1) return false;
            if (c == '\n') return true;
            out += c;
        }
        return false;
    };
    read_line(line);   // greeting
    std::string caps = "{\"execute\":\"qmp_capabilities\"}\n";
    send_all(s, caps.data(), caps.size());
    read_line(line);
    std::string c = cmd + "\n";
    send_all(s, c.data(), c.size());
    while (read_line(line)) {
        if (line.find("\"return\"") != std::string::npos || line.find("\"error\"") != std::string::npos) { all = line; break; }
    }
    CLOSESOCK(s);
    return all;
}

// ------------------------------------------------------------------ processes
#ifdef _WIN32
static std::wstring widen(const std::string &s)
{
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, NULL, 0);
    std::wstring w(n ? n - 1 : 0, 0);
    if (n > 1) MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &w[0], n);
    return w;
}
static std::string quote(const std::string &a)
{
    if (!a.empty() && a.find_first_of(" \t\"") == std::string::npos) return a;
    std::string q = "\"";
    for (char c : a) { if (c == '"') q += '\\'; q += c; }
    return q + "\"";
}
// run and wait (hidden); returns exit code, or -1
static int run_wait(const std::vector<std::string> &argv, int timeout_ms, const std::string &log = "", std::atomic<bool> *stop = nullptr)
{
    std::string cl;
    for (auto &a : argv) cl += (cl.empty() ? "" : " ") + quote(a);
    std::wstring w = widen(cl);
    STARTUPINFOW si = {};
    PROCESS_INFORMATION pi = {};
    si.cb = sizeof si;
    HANDLE lf = INVALID_HANDLE_VALUE;
    if (!log.empty()) {
        SECURITY_ATTRIBUTES sa = {sizeof sa, NULL, TRUE};
        lf = CreateFileA(log.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, OPEN_ALWAYS, 0, NULL);
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = lf;
        si.hStdInput = NULL;
    }
    if (!CreateProcessW(NULL, &w[0], NULL, NULL, lf != INVALID_HANDLE_VALUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        if (lf != INVALID_HANDLE_VALUE) CloseHandle(lf);
        return -1;
    }
    DWORD code = (DWORD)-1;
    double end = Machine::now() + timeout_ms / 1000.0;
    for (;;) {
        if (WaitForSingleObject(pi.hProcess, 100) == WAIT_OBJECT_0) { GetExitCodeProcess(pi.hProcess, &code); break; }
        if (Machine::now() > end || (stop && *stop)) { TerminateProcess(pi.hProcess, 1); WaitForSingleObject(pi.hProcess, 2000); break; }
    }
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    if (lf != INVALID_HANDLE_VALUE) CloseHandle(lf);
    return (int)code;
}
#else
static int run_wait(const std::vector<std::string> &argv, int timeout_ms, const std::string &log = "", std::atomic<bool> *stop = nullptr)
{
    std::vector<char *> av;
    for (auto &a : argv) av.push_back((char *)a.c_str());
    av.push_back(nullptr);
    posix_spawn_file_actions_t fa;
    posix_spawn_file_actions_init(&fa);
    if (!log.empty()) {
        posix_spawn_file_actions_addopen(&fa, 1, log.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644);
        posix_spawn_file_actions_adddup2(&fa, 1, 2);
    }
    pid_t pid;
    int r = posix_spawn(&pid, av[0], &fa, NULL, av.data(), environ);
    posix_spawn_file_actions_destroy(&fa);
    if (r) return -1;
    double end = Machine::now() + timeout_ms / 1000.0;
    int st = 0;
    while (Machine::now() < end && !(stop && *stop)) {
        pid_t w = waitpid(pid, &st, WNOHANG);
        if (w == pid) return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
        sleep_ms(20);
    }
    ::kill(pid, SIGKILL);
    waitpid(pid, &st, 0);
    return -1;
}
#endif

// ------------------------------------------------------------------ the machine
static std::atomic<int> instance_counter{0};

Machine::Machine() : fb_((size_t)kW * kH * 4, 0)
{
    for (size_t i = 3; i < fb_.size(); i += 4) fb_[i] = 255;
}

Machine::~Machine() { stop(); }

// a log beside the machine (one per instance, the last few kept)
void Machine::log(const char *fmt, ...)
{
    static std::mutex m;
    std::lock_guard<std::mutex> g(m);
    std::string dir = Machine::machineDir();
    mkdirs(dir);
    FILE *f = fopen((dir + SEP + "plugin.log").c_str(), "a");
    if (!f) return;
    time_t t = time(NULL);
    char ts[32];
    strftime(ts, sizeof ts, "%H:%M:%S", localtime(&t));
    fprintf(f, "%s %.3f ", ts, fmod(Machine::now(), 1000.0));
    va_list a;
    va_start(a, fmt);
    vfprintf(f, fmt, a);
    va_end(a);
    fputc('\n', f);
    fclose(f);
}

void Machine::fail(const std::string &e)
{
    { std::lock_guard<std::mutex> g(mu_); error_ = e; }
    Machine::log("failed: %s", e.c_str());
    phase = Failed;
}
void Machine::setStatus(const std::string &s) { std::lock_guard<std::mutex> g(mu_); status_ = s; if (!s.empty()) Machine::log("%s", s.c_str()); }

void Machine::start()
{
    if (main_.joinable() || stopping_) return;
    main_ = std::thread([this] { run(); });
}

void Machine::send(const char *line)
{
    touch();
    Line l;
    snprintf(l.s, sizeof l.s, "%s", line);
    out_.push(l);
}

void Machine::sendLong(const std::string &line)
{
    touch();
    std::lock_guard<std::mutex> g(longMu_);
    long_.push_back(line);
}

bool Machine::popReply(std::string &line)
{
    std::lock_guard<std::mutex> g(inMu_);
    if (in_.empty()) return false;
    line = in_.front();
    in_.erase(in_.begin());
    return true;
}

bool Machine::ensureMachine()
{
    std::string dir = machineDir(), ok = dir + SEP + "machine.ok";
    if (exists(ok)) return true;
    mkdirs(dir);
    std::string lock = dir + SEP + "fetch.lock", arc = dir + SEP + "machine.tar.xz";
    // one instance fetches; the others wait for it
    for (;;) {
        if (stopping_) return false;
        if (exists(ok)) return true;
#ifdef _WIN32
        HANDLE h = CreateFileA(lock.c_str(), GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_FLAG_DELETE_ON_CLOSE, NULL);
        bool mine = h != INVALID_HANDLE_VALUE;
#else
        int fd = ::open(lock.c_str(), O_CREAT | O_EXCL | O_WRONLY, 0644);
        bool mine = fd >= 0;
        if (!mine) {   // a lock older than an hour belongs to a crashed fetch
            struct stat st;
            if (::stat(lock.c_str(), &st) == 0 && time(NULL) - st.st_mtime > 3600) { remove_file(lock); continue; }
        }
#endif
        if (!mine) {
            phase = Fetching;
            setStatus("Another BASILISK SYNTH is fetching the Windows XP machine...");
            long long sz = file_size(arc);
            progress = sz > 0 ? (float)((double)sz / BSYNTH_MACHINE_BYTES) : 0.f;
            sleep_ms(500);
            continue;
        }
        bool good = false;
        // download (curl ships with Windows 10+ and macOS), watching the file grow
        phase = Fetching;
        setStatus("Fetching the Windows XP machine (once): " + std::to_string(BSYNTH_MACHINE_BYTES / 1000000) + " MB");
        remove_file(arc);
        {
#ifdef _WIN32
            char sys[MAX_PATH];
            GetSystemDirectoryA(sys, MAX_PATH);
            std::string curl = std::string(sys) + "\\curl.exe";
#else
            std::string curl = "/usr/bin/curl";
#endif
            std::atomic<bool> done{false};
            int rc = -1;
            std::thread t([&] { rc = run_wait({curl, "-L", "-f", "-s", "-S", "--retry", "3", "-o", arc, getenv("BSYNTH_MACHINE_URL") ? getenv("BSYNTH_MACHINE_URL") : BSYNTH_MACHINE_URL}, 4 * 3600 * 1000, dir + SEP + "fetch.log", &stopping_); done = true; });
            while (!done) {
                long long sz = file_size(arc);
                progress = sz > 0 ? (float)((double)sz / BSYNTH_MACHINE_BYTES) : 0.f;
                sleep_ms(200);
                if (stopping_) break;
            }
            t.join();
            if (rc != 0) { fail("Could not download the Windows XP machine (see " + dir + SEP + "fetch.log)."); goto out; }
        }
        {
            phase = Unpacking;
            setStatus("Checking the download...");
            std::ifstream f(arc, std::ios::binary);
            Sha256 h;
            std::vector<char> b(1 << 20);
            long long tot = 0;
            while (f) {
                f.read(b.data(), (std::streamsize)b.size());
                std::streamsize n = f.gcount();
                if (n <= 0) break;
                h.add((const uint8_t *)b.data(), (size_t)n);
                tot += n;
                progress = (float)(0.3 * tot / BSYNTH_MACHINE_BYTES);
            }
            if (h.hex() != BSYNTH_MACHINE_SHA256) { remove_file(arc); fail("The Windows XP machine download was damaged; it will be fetched again next time."); goto out; }
        }
        {
            setStatus("Unpacking the Windows XP machine...");
            progress = 0.35f;
#ifdef _WIN32
            char sys[MAX_PATH];
            GetSystemDirectoryA(sys, MAX_PATH);
            std::string tar = std::string(sys) + "\\tar.exe";
#else
            std::string tar = "/usr/bin/tar";
#endif
            std::atomic<bool> done{false};
            int rc = -1;
            std::thread t([&] { rc = run_wait({tar, "-x", "-f", arc, "-C", dir}, 3600 * 1000, dir + SEP + "fetch.log", &stopping_); done = true; });
            while (!done) {
                long long sz = file_size(dir + SEP + "base.qcow2");
                if (sz > 0) progress = 0.35f + 0.65f * (float)((double)sz / BSYNTH_MACHINE_UNPACKED);
                sleep_ms(200);
            }
            t.join();
            if (rc != 0 || !exists(dir + SEP + "base.qcow2") || !exists(dir + SEP + "state.mig")) { fail("Could not unpack the Windows XP machine."); goto out; }
            remove_file(arc);
            std::ofstream(ok) << BSYNTH_MACHINE_NAME << "\n";
            good = true;
        }
    out:
#ifdef _WIN32
        CloseHandle(h);
#else
        ::close(fd);
        remove_file(lock);
#endif
        return good;
    }
}

bool Machine::launch()
{
    std::string res = resources_dir(), mdir = machineDir();
    char tag[64];
#ifdef _WIN32
    char tp[MAX_PATH];
    GetTempPathA(MAX_PATH, tp);
    snprintf(tag, sizeof tag, "bsynth-%lu-%d", (unsigned long)GetCurrentProcessId(), instance_counter++);
    tmp_ = std::string(tp) + tag;
    // QEMU is shipped zipped inside the bundle and unpacked beside the machine on first use: hosts that scan VST
    // folders for .dll files must never find QEMU's libraries in there
    std::string qbase = mdir.substr(0, mdir.find_last_of('\\')) + "\\qemu-" BSYNTH_QEMU_TAG;
    std::string qdir = qbase + "\\qemu", qemu = qdir + "\\qemu-system-i386w.exe", img = qdir + "\\qemu-img.exe", share = qdir + "\\share";
    if (!exists(qemu) && exists(res + "\\qemu-win64.zip")) {
        setStatus("Unpacking QEMU (once)...");
        char sys[MAX_PATH];
        GetSystemDirectoryA(sys, MAX_PATH);
        // each instance unpacks into its own folder and renames it into place; the loser of a race throws its copy away
        std::string mine = qbase + ".tmp-" + tag;
        mkdirs(mine);
        if (run_wait({std::string(sys) + "\\tar.exe", "-x", "-f", res + "\\qemu-win64.zip", "-C", mine}, 600000) != 0 ||
            !MoveFileA(mine.c_str(), qbase.c_str()))
            remove_tree(mine);
    }
#else
    snprintf(tag, sizeof tag, "bsynth-%d-%d", (int)getpid(), instance_counter++);
    tmp_ = std::string("/tmp/") + tag;
    // one bundle for both Macs: each slice of the universal binary runs the QEMU built for it
#if defined(__aarch64__) || defined(__arm64__)
    std::string qdir = res + "/qemu-arm64";
#else
    std::string qdir = res + "/qemu-x86_64";
#endif
    std::string qemu = qdir + "/bin/qemu-system-i386", img = qdir + "/bin/qemu-img", share = qdir + "/share/qemu";
#endif
    mkdirs(tmp_);
    std::string log = tmp_ + SEP + "qemu.log";
    if (!exists(qemu)) { fail("QEMU is missing from this copy of BASILISK SYNTH (" + qemu + ")."); return false; }
    overlay_ = tmp_ + SEP + "disk.qcow2";
    if (run_wait({img, "create", "-q", "-f", "qcow2", "-b", mdir + SEP + "base.qcow2", "-F", "qcow2", overlay_}, 30000, log) != 0) {
        fail("Could not prepare this instance's disk (qemu-img).");
        return false;
    }
    portQmp_ = free_port(); portCom_ = free_port(); portMig_ = free_port(); portVnc_ = free_port(5900);
    // the sound: QEMU writes a wav "file" that is really a pipe this instance reads
#ifdef _WIN32
    pipePath_ = std::string("\\\\.\\pipe\\") + tag + "-audio";
    pipe_ = CreateNamedPipeA(pipePath_.c_str(), PIPE_ACCESS_INBOUND, PIPE_TYPE_BYTE | PIPE_WAIT, 1, 0, 1 << 16, 0, NULL);
    if (pipe_ == INVALID_HANDLE_VALUE) { pipe_ = nullptr; fail("Could not create the sound pipe."); return false; }
#else
    pipePath_ = tmp_ + "/audio";
    if (mkfifo(pipePath_.c_str(), 0600) != 0) { fail("Could not create the sound pipe."); return false; }
    fifo_ = ::open(pipePath_.c_str(), O_RDONLY | O_NONBLOCK);
#endif
    auto esc = [](std::string s) { std::string o; for (char c : s) { o += c; if (c == ',') o += ','; } return o; };
    std::vector<std::string> a = {qemu, "-name", "BASILISK SYNTH", "-nodefaults", "-no-user-config", "-M", "pc-i440fx-6.2",
        "-m", "512", "-smp", "2", "-cpu", "qemu32",
        "-drive", "file=" + esc(overlay_) + ",format=qcow2,if=ide,index=0,cache=writeback",
        "-vga", "cirrus", "-device", "rtl8139,netdev=n0,mac=52:54:00:12:34:56",
        "-netdev", "user,id=n0,restrict=on,net=10.0.2.0/24",
        "-usb", "-device", "usb-tablet", "-rtc", "base=localtime", "-display", "none", "-boot", "menu=off",
        "-L", mdir + SEP + "fw", "-L", share,
        "-accel", "tcg,thread=multi,tb-size=256",
        "-audiodev", "wav,id=snd0,path=" + esc(pipePath_) + ",out.frequency=44100,out.channels=2,out.format=s16",
        "-device", "AC97,audiodev=snd0",
        "-chardev", "socket,id=ser0,host=127.0.0.1,port=" + std::to_string(portCom_) + ",server=on,wait=off",
        "-serial", "chardev:ser0",
        "-vnc", "127.0.0.1:" + std::to_string(portVnc_ - 5900),
        "-qmp", "tcp:127.0.0.1:" + std::to_string(portQmp_) + ",server=on,wait=off",
        "-incoming", "tcp:127.0.0.1:" + std::to_string(portMig_)};
    {
        std::ofstream l(log, std::ios::app);
        for (auto &x : a) l << x << " ";
        l << "\n";
    }
#ifdef _WIN32
    std::string cl;
    for (auto &x : a) cl += (cl.empty() ? "" : " ") + quote(x);
    std::wstring w = widen(cl);
    SECURITY_ATTRIBUTES sa = {sizeof sa, NULL, TRUE};
    HANDLE lf = CreateFileA(log.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, OPEN_ALWAYS, 0, NULL);
    STARTUPINFOW si = {};
    PROCESS_INFORMATION pi = {};
    si.cb = sizeof si;
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = si.hStdError = lf;
    // the job dies with this process, and takes QEMU with it: no orphan survives a crashed DAW
    job_ = CreateJobObjectA(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
    li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(job_, JobObjectExtendedLimitInformation, &li, sizeof li);
    BOOL ok = CreateProcessW(NULL, &w[0], NULL, NULL, TRUE, CREATE_NO_WINDOW | CREATE_SUSPENDED, NULL, NULL, &si, &pi);
    CloseHandle(lf);
    if (!ok) { fail("Could not start QEMU."); return false; }
    AssignProcessToJobObject(job_, pi.hProcess);
    ResumeThread(pi.hThread);
    CloseHandle(pi.hThread);
    proc_ = pi.hProcess;
#else
    std::vector<char *> av;
    for (auto &x : a) av.push_back((char *)x.c_str());
    av.push_back(nullptr);
    posix_spawn_file_actions_t fa;
    posix_spawn_file_actions_init(&fa);
    posix_spawn_file_actions_addopen(&fa, 1, log.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644);
    posix_spawn_file_actions_adddup2(&fa, 1, 2);
    posix_spawn_file_actions_addopen(&fa, 0, "/dev/null", O_RDONLY, 0);
    pid_t pid;
    int r = posix_spawn(&pid, av[0], &fa, NULL, av.data(), environ);
    posix_spawn_file_actions_destroy(&fa);
    if (r) { fail("Could not start QEMU."); return false; }
    pid_ = pid;
    // a watchdog: if the DAW dies without unloading us, QEMU goes too
    {
        std::string sh = "p=" + std::to_string(getpid()) + "; q=" + std::to_string(pid) +
                         "; while kill -0 $p 2>/dev/null && kill -0 $q 2>/dev/null; do sleep 1; done; kill -9 $q 2>/dev/null; rm -rf '" + tmp_ + "'";
        const char *wa[] = {"/bin/sh", "-c", sh.c_str(), nullptr};
        pid_t w;
        if (posix_spawn(&w, "/bin/sh", NULL, NULL, (char *const *)wa, environ) == 0) watchdog_ = w;
    }
#endif
    return true;
}

bool Machine::resume()
{
    // the machine state goes in over loopback; QEMU loads it as it arrives
    std::string st = machineDir() + SEP + "state.mig";
    std::ifstream f(st, std::ios::binary);
    if (!f) { fail("The machine state is missing."); return false; }
    intptr_t s = tcp_connect(portMig_, 15000, &stopping_);
    if (s < 0) { fail("QEMU did not start (see its log in " + tmp_ + ")."); return false; }
    std::vector<char> b(1 << 20);
    while (f && !stopping_) {
        f.read(b.data(), (std::streamsize)b.size());
        std::streamsize n = f.gcount();
        if (n <= 0) break;
        if (!send_all(s, b.data(), (size_t)n)) break;
    }
    CLOSESOCK(s);
    // wait until it has loaded, then run
    double end = now() + 30;
    while (now() < end && !stopping_) {
        std::string r = qmp(portQmp_, "{\"execute\":\"query-status\"}", 2000);
        if (r.find("\"paused\"") != std::string::npos || r.find("\"postmigrate\"") != std::string::npos) break;
        if (r.find("\"running\"") != std::string::npos) return true;
        if (r.find("inmigrate") == std::string::npos && !r.empty() && r.find("\"error\"") != std::string::npos) { fail("QEMU refused the machine state."); return false; }
        sleep_ms(30);
    }
    qmp(portQmp_, "{\"execute\":\"cont\"}");
    return true;
}

void Machine::run()
{
#ifdef _WIN32
    // 1 ms timers while a machine runs: the link thread's waits are otherwise 15.6 ms long
    timeBeginPeriod(1);
    struct End { ~End() { timeEndPeriod(1); } } end;
#endif
    phase = Starting;
    setStatus("Waking Windows XP...");
    if (!ensureMachine() || stopping_) return;
    phase = Starting;
    setStatus("Waking Windows XP...");
    if (!launch() || stopping_) return;
    audio_ = std::thread([this] { audioLoop(); });
    phase = Resuming;
    if (!resume() || stopping_) return;
    resumedAt = now();
    Machine::log("running (qemu in %s)", tmp_.c_str());
    phase = Running;
    setStatus("");
    vnc_ = std::thread([this] { vncLoop(); });
    linkLoop();
}

// ------------------------------------------------------------------ COM1: the guest link
void Machine::linkLoop()
{
    com_ = tcp_connect(portCom_, 10000, &stopping_);
    if (com_ < 0) { fail("Could not reach the guest's COM1."); return; }
    {
        time_t t = time(NULL);
        struct tm lt;
#ifdef _WIN32
        localtime_s(&lt, &t);
#else
        localtime_r(&t, &lt);
#endif
        char b[96];
        proto::time(b, sizeof b, lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec);
        send_all(com_, b, strlen(b));
        proto::hi(b, sizeof b);
        send_all(com_, b, strlen(b));
        send_all(com_, "\n", 1);
    }
    std::string acc;
    double lastHi = now();
    char buf[4096];
    bool building = false;
    double lastPing = 0;
    touch();
    auto timeLine = []() {
        time_t t = time(NULL);
        struct tm lt;
#ifdef _WIN32
        localtime_s(&lt, &t);
#else
        localtime_r(&t, &lt);
#endif
        char b[96];
        proto::time(b, sizeof b, lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec);
        return std::string(b);
    };
    while (!stopping_) {
        // out: everything queued, straight away (waking the machine first if it sleeps)
        Line l;
        std::string out;
        while (out_.pop(l)) out += l.s;
        { std::lock_guard<std::mutex> g(longMu_); for (auto &x : long_) out += x; long_.clear(); }
        if (out.find("dna ") != std::string::npos) building = true;   // stays awake until the guest says built
        bool wake = !out.empty() || now() - lastTouch_.load() < 0.5;
        if (asleep && wake) {
            qmp(portQmp_, "{\"execute\":\"cont\"}", 2000);
            asleep = false;
            out = timeLine() + out;       // its clock stood still while it slept
            log("woke");
        }
        if (out.size() > 24 || (out.size() > 1 && getenv("BSYNTH_LOG_LINES"))) log("sent: %.80s", out.c_str());
        // after a resume XP's serial driver has lost the UART's transmit interrupt: it sends only when a byte comes
        // in. So while awake the link sends an empty line (ignored by the guest) every 15 ms; each one carries
        // XP's waiting output out, and a trailing one carries each real line in at once
        if (!out.empty()) out += "\n";
        else if (!asleep && now() - lastPing > 0.015) { out = "\n"; }
        if (!out.empty()) lastPing = now();
        if (!out.empty() && !send_all(com_, out.data(), out.size())) break;
        if (!asleep && linked && !building && now() - lastTouch_.load() > kSleepAfter) {
            qmp(portQmp_, "{\"execute\":\"stop\"}", 2000);
            asleep = true;
            log("asleep");
        }
        if (!linked && !asleep && now() - lastHi > 1.0) {   // the guest may still be waking from the state: ask again
            char b[16];
            proto::hi(b, sizeof b);
            send_all(com_, b, strlen(b));
            send_all(com_, "\n", 1);
            lastHi = now();
        }
        if (readable(com_, 1)) {
            int n = (int)::recv(com_, buf, sizeof buf, 0);
            if (n <= 0) break;
            acc.append(buf, (size_t)n);
            size_t k;
            while ((k = acc.find('\n')) != std::string::npos) {
                std::string line = acc.substr(0, k);
                acc.erase(0, k + 1);
                if (!line.empty() && line.back() == '\r') line.pop_back();
                proto::Reply r = proto::parse(line);
                if (r.kind == proto::Reply::Hi && !linked) Machine::log("guest: %s", line.c_str());
                if (r.kind == proto::Reply::Hi) linked = true;
                if (r.kind != proto::Reply::Hi) Machine::log("guest: %s", line.c_str());
                if (r.kind == proto::Reply::Ready) ready = true;
                if (r.kind == proto::Reply::Built) { building = false; touch(); }
                std::lock_guard<std::mutex> g(inMu_);
                if (in_.size() < 4096) in_.push_back(line);
            }
        }
    }
}

// ------------------------------------------------------------------ the sound
void Machine::audioLoop()
{
    std::vector<uint8_t> raw(1 << 15);
    std::vector<float> f(1 << 15);
    size_t skip = 44;   // the wav header QEMU writes first
    size_t have = 0;    // carried-over bytes (a frame split across reads)
    uint8_t carry[4];
#ifdef _WIN32
    if (!ConnectNamedPipe((HANDLE)pipe_, NULL) && GetLastError() != ERROR_PIPE_CONNECTED) return;
#endif
    while (!stopping_) {
        int n = 0;
#ifdef _WIN32
        DWORD got = 0;
        if (!ReadFile((HANDLE)pipe_, raw.data(), (DWORD)raw.size(), &got, NULL)) break;
        n = (int)got;
#else
        pollfd p = {fifo_, POLLIN, 0};
        if (poll(&p, 1, 100) <= 0) continue;
        n = (int)::read(fifo_, raw.data(), raw.size());
        if (n == 0) { sleep_ms(5); continue; }   // no writer yet
        if (n < 0) { if (errno == EAGAIN || errno == EINTR) continue; break; }
#endif
        uint8_t *p8 = raw.data();
        size_t m = (size_t)n;
        if (skip) { size_t s = skip < m ? skip : m; p8 += s; m -= s; skip -= s; }
        size_t frames = 0;
        while (m) {
            carry[have++] = *p8++;
            m--;
            if (have == 4) {
                int16_t L = (int16_t)(carry[0] | carry[1] << 8), R = (int16_t)(carry[2] | carry[3] << 8);
                f[2 * frames] = L / 32768.f;
                f[2 * frames + 1] = R / 32768.f;
                frames++;
                have = 0;
                if (frames * 2 >= f.size()) { audio.write(f.data(), frames); frames = 0; }
            }
        }
        if (frames) audio.write(f.data(), frames);
    }
}

// ------------------------------------------------------------------ the screen (RFB 3.8, Raw + CopyRect)
void Machine::vncLoop()
{
    intptr_t s = tcp_connect(portVnc_, 10000, &stopping_);
    if (s < 0) return;
    char ver[12];
    uint8_t n8, t8;
    uint32_t res;
    if (!recv_all(s, ver, 12)) goto done;
    send_all(s, "RFB 003.008\n", 12);
    if (!recv_all(s, &n8, 1) || n8 == 0) goto done;
    {
        std::vector<uint8_t> types(n8);
        recv_all(s, types.data(), n8);
    }
    t8 = 1;
    send_all(s, &t8, 1);
    if (!recv_all(s, &res, 4) || res != 0) goto done;
    t8 = 1;   // shared
    send_all(s, &t8, 1);
    {
        uint8_t si[24];
        if (!recv_all(s, si, 24)) goto done;
        uint32_t nl = (uint32_t)si[20] << 24 | si[21] << 16 | si[22] << 8 | si[23];
        std::vector<char> name(nl);
        if (nl) recv_all(s, name.data(), nl);
    }
    {
        // 32 bpp, little endian, bytes R G B x
        uint8_t pf[20] = {0, 0, 0, 0, 32, 24, 0, 1, 0, 255, 0, 255, 0, 255, 0, 8, 16, 0, 0, 0};
        send_all(s, pf, 20);
        uint8_t enc[4 + 3 * 4] = {2, 0, 0, 3, 0, 0, 0, 1 /*CopyRect*/, 0, 0, 0, 0 /*Raw*/, 0xff, 0xff, 0xff, 0x21 /*DesktopSize -223*/};
        send_all(s, enc, sizeof enc);
    }
    { std::lock_guard<std::mutex> g(vncSendMu_); vncSock_ = s; }
    {
        bool incremental = false;
        std::vector<uint8_t> row;
        while (!stopping_) {
            uint8_t req[10] = {3, (uint8_t)incremental, 0, 0, 0, 0, (uint8_t)(kW >> 8), (uint8_t)(kW & 255), (uint8_t)(kH >> 8), (uint8_t)(kH & 255)};
            { std::lock_guard<std::mutex> g(vncSendMu_); if (!send_all(s, req, 10)) break; }
            incremental = true;
            uint8_t type;
            for (;;) {
                if (!recv_all(s, &type, 1)) goto done;
                if (type == 0) break;
                if (type == 2) continue;                     // bell
                if (type == 3) {                             // cut text
                    uint8_t h[7];
                    recv_all(s, h, 7);
                    uint32_t l = (uint32_t)h[3] << 24 | h[4] << 16 | h[5] << 8 | h[6];
                    std::vector<char> t(l);
                    if (l) recv_all(s, t.data(), l);
                    continue;
                }
                if (type == 1) {                             // colour map
                    uint8_t h[5];
                    recv_all(s, h, 5);
                    int nc = h[3] << 8 | h[4];
                    std::vector<uint8_t> c(6 * nc);
                    recv_all(s, c.data(), c.size());
                    continue;
                }
                goto done;
            }
            uint8_t h[3];
            if (!recv_all(s, h, 3)) break;
            int nr = h[1] << 8 | h[2];
            for (int i = 0; i < nr; i++) {
                uint8_t rh[12];
                if (!recv_all(s, rh, 12)) goto done;
                int x = rh[0] << 8 | rh[1], y = rh[2] << 8 | rh[3], w = rh[4] << 8 | rh[5], hh = rh[6] << 8 | rh[7];
                int32_t enc = (int32_t)((uint32_t)rh[8] << 24 | rh[9] << 16 | rh[10] << 8 | rh[11]);
                if (enc == 0) {
                    row.resize((size_t)w * 4);
                    for (int yy = 0; yy < hh; yy++) {
                        if (!recv_all(s, row.data(), row.size())) goto done;
                        if (y + yy >= kH) continue;
                        std::lock_guard<std::mutex> g(fbMu_);
                        uint8_t *d = &fb_[((size_t)(y + yy) * kW + x) * 4];
                        int ww = x + w > kW ? kW - x : w;
                        for (int k = 0; k < ww; k++) { d[4 * k] = row[4 * k]; d[4 * k + 1] = row[4 * k + 1]; d[4 * k + 2] = row[4 * k + 2]; d[4 * k + 3] = 255; }
                    }
                } else if (enc == 1) {
                    uint8_t sp[4];
                    if (!recv_all(s, sp, 4)) goto done;
                    int sx = sp[0] << 8 | sp[1], sy = sp[2] << 8 | sp[3];
                    std::lock_guard<std::mutex> g(fbMu_);
                    std::vector<uint8_t> tmp((size_t)w * hh * 4);
                    for (int yy = 0; yy < hh && sy + yy < kH; yy++) memcpy(&tmp[(size_t)yy * w * 4], &fb_[((size_t)(sy + yy) * kW + sx) * 4], (size_t)w * 4);
                    for (int yy = 0; yy < hh && y + yy < kH; yy++) memcpy(&fb_[((size_t)(y + yy) * kW + x) * 4], &tmp[(size_t)yy * w * 4], (size_t)w * 4);
                } else if (enc == -223) {
                    // XP never changes its size here
                } else goto done;
                std::lock_guard<std::mutex> g(fbMu_);
                if (x < dx0_) dx0_ = x;
                if (y < dy0_) dy0_ = y;
                if (x + w > dx1_) dx1_ = x + w > kW ? kW : x + w;
                if (y + hh > dy1_) dy1_ = y + hh > kH ? kH : y + hh;
            }
        }
    }
done:
    { std::lock_guard<std::mutex> g(vncSendMu_); vncSock_ = -1; }
    CLOSESOCK(s);
}

bool Machine::frame(std::vector<uint8_t> &rgba, int &x0, int &y0, int &x1, int &y1)
{
    std::lock_guard<std::mutex> g(fbMu_);
    if (dx1_ <= dx0_ || dy1_ <= dy0_) return false;
    if (rgba.size() != fb_.size()) rgba = fb_;
    else for (int y = dy0_; y < dy1_; y++) memcpy(&rgba[((size_t)y * kW + dx0_) * 4], &fb_[((size_t)y * kW + dx0_) * 4], (size_t)(dx1_ - dx0_) * 4);
    x0 = dx0_; y0 = dy0_; x1 = dx1_; y1 = dy1_;
    dx0_ = kW; dy0_ = kH; dx1_ = 0; dy1_ = 0;
    return true;
}

void Machine::pointer(int x, int y, int buttons)
{
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x >= kW) x = kW - 1;
    if (y >= kH) y = kH - 1;
    uint8_t m[6] = {5, (uint8_t)buttons, (uint8_t)(x >> 8), (uint8_t)x, (uint8_t)(y >> 8), (uint8_t)y};
    std::lock_guard<std::mutex> g(vncSendMu_);
    if (vncSock_ >= 0) send_all(vncSock_, m, 6);
}

void Machine::key(uint32_t keysym, bool down)
{
    uint8_t m[8] = {4, (uint8_t)down, 0, 0, (uint8_t)(keysym >> 24), (uint8_t)(keysym >> 16), (uint8_t)(keysym >> 8), (uint8_t)keysym};
    std::lock_guard<std::mutex> g(vncSendMu_);
    if (vncSock_ >= 0) send_all(vncSock_, m, 8);
}

// ------------------------------------------------------------------ stopping
void Machine::kill()
{
#ifdef _WIN32
    if (proc_) {
        if (portQmp_) qmp(portQmp_, "{\"execute\":\"quit\"}", 500);
        if (WaitForSingleObject((HANDLE)proc_, 1500) != WAIT_OBJECT_0) TerminateProcess((HANDLE)proc_, 1);
        WaitForSingleObject((HANDLE)proc_, 3000);
        CloseHandle((HANDLE)proc_);
        proc_ = nullptr;
    }
    if (job_) { CloseHandle((HANDLE)job_); job_ = nullptr; }
    if (pipe_) {
        // a reader may still be waiting for QEMU to connect: connect to it ourselves so it lets go
        HANDLE c = CreateFileA(pipePath_.c_str(), GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
        if (c != INVALID_HANDLE_VALUE) CloseHandle(c);
    }
#else
    if (pid_ > 0) {
        ::kill(pid_, SIGKILL);
        int st;
        waitpid(pid_, &st, 0);
        pid_ = -1;
    }
    if (watchdog_ > 0) { ::kill(watchdog_, SIGKILL); int st; waitpid(watchdog_, &st, 0); watchdog_ = -1; }
    if (fifo_ >= 0) { ::close(fifo_); fifo_ = -1; }
#endif
}

void Machine::stop()
{
    stopping_ = true;
    if (com_ >= 0) { CLOSESOCK(com_); }
    {
        std::lock_guard<std::mutex> g(vncSendMu_);
        if (vncSock_ >= 0) { shutdown(vncSock_, 2); }
    }
    kill();
    if (main_.joinable()) main_.join();
    if (audio_.joinable()) audio_.join();
#ifdef _WIN32
    if (pipe_) { CloseHandle((HANDLE)pipe_); pipe_ = nullptr; }
#endif
    if (vnc_.joinable()) vnc_.join();
    com_ = -1;
    if (!tmp_.empty() && !getenv("BSYNTH_KEEP")) { remove_tree(tmp_); tmp_.clear(); }
    phase = Off;
}

}  // namespace bsynth

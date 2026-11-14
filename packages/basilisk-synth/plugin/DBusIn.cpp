// BASILISK SYNTH - recording input over QEMU's peer-to-peer D-Bus (see DBusIn.hpp). A minimal D-Bus: SASL as the
// client, little-endian messages, the few types QEMU's AudioInListener calls use (t y b u ay).
#include "DBusIn.hpp"

#include <chrono>
#include <cstdio>
#include <cstring>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
typedef SOCKET sock_t;
#define CLOSESOCK closesocket
#else
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/mman.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <unistd.h>
typedef int sock_t;
#define CLOSESOCK ::close
#endif

namespace bsynth {

// ------------------------------------------------------------------ the ring
void InputRing::write(const int16_t *lr, size_t frames)
{
    const size_t cap = buf_.size() / 2;
    size_t w = w_.load(std::memory_order_relaxed);
    for (size_t i = 0; i < frames; i++) {
        size_t k = (w + i) % cap;
        buf_[2 * k] = lr[2 * i]; buf_[2 * k + 1] = lr[2 * i + 1];
    }
    w += frames;
    w_.store(w, std::memory_order_release);
    // overrun: the reader fell behind by more than the ring; it skips to the newest audio
    size_t r = r_.load(std::memory_order_acquire);
    if (w - r > cap) r_.store(w - cap / 2, std::memory_order_release);
}

size_t InputRing::read(int16_t *lr, size_t frames)
{
    const size_t cap = buf_.size() / 2;
    size_t r = r_.load(std::memory_order_acquire), w = w_.load(std::memory_order_acquire);
    // QEMU's dbus audio input does not pace itself (11.1: its rate limit is commented out): the card takes what a
    // Read returns, so only frames really in hand are returned and the DAW's own clock paces XP's recording. First a
    // cushion is let in (nothing returned), so short gaps in the host's blocks do not reach the recording
    if (!primed_) {
        if (w - r < cushion_) return 0;
        primed_ = true;
    }
    if (w - r == 0) { primed_ = false; under_++; return 0; }   // ran dry: prime again
    size_t n = w - r < frames ? w - r : frames;
    for (size_t i = 0; i < n; i++) {
        size_t k = (r + i) % cap;
        lr[2 * i] = buf_[2 * k]; lr[2 * i + 1] = buf_[2 * k + 1];
    }
    r_.store(r + n, std::memory_order_release);
    return n;
}

// ------------------------------------------------------------------ sockets
namespace {
bool sendAll(sock_t s, const void *p, size_t n)
{
    const char *c = (const char *)p;
    while (n) {
        int k = ::send(s, c, (int)n, 0);
        if (k <= 0) return false;
        c += k; n -= (size_t)k;
    }
    return true;
}
// 1: data, 0: nothing within the timeout, -1: closed
int recvSome(sock_t s, std::string &buf, int timeoutMs)
{
    fd_set rf; FD_ZERO(&rf); FD_SET(s, &rf);
    timeval tv{timeoutMs / 1000, (timeoutMs % 1000) * 1000};
    int n = select((int)s + 1, &rf, nullptr, nullptr, &tv);
    if (n < 0) return -1;
    if (n == 0) return 0;
    char b[65536];
    int k = ::recv(s, b, sizeof b, 0);
    if (k <= 0) return -1;
    buf.append(b, (size_t)k);
    return 1;
}
bool readLine(sock_t s, std::string &buf, std::string &line, int timeoutMs)
{
    for (int i = 0; i < 100; i++) {
        size_t e = buf.find("\r\n");
        if (e != std::string::npos) { line = buf.substr(0, e); buf.erase(0, e + 2); return true; }
        if (recvSome(s, buf, timeoutMs) <= 0) return false;
    }
    return false;
}
void noDelay(sock_t s) { int one = 1; setsockopt(s, IPPROTO_TCP, TCP_NODELAY, (const char *)&one, sizeof one); }

#ifdef _WIN32
// a connected pair over loopback TCP (Windows has no socketpair)
bool socketPair(sock_t sv[2])
{
    sock_t l = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sockaddr_in a{}; a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK); a.sin_port = 0;
    int len = sizeof a;
    if (bind(l, (sockaddr *)&a, sizeof a) || listen(l, 1) || getsockname(l, (sockaddr *)&a, &len)) { closesocket(l); return false; }
    sv[0] = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (connect(sv[0], (sockaddr *)&a, sizeof a)) { closesocket(l); closesocket(sv[0]); return false; }
    sv[1] = accept(l, nullptr, nullptr);
    closesocket(l);
    if (sv[1] == INVALID_SOCKET) { closesocket(sv[0]); return false; }
    noDelay(sv[0]); noDelay(sv[1]);
    return true;
}
std::string base64(const unsigned char *p, size_t n)
{
    static const char t[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string o;
    for (size_t i = 0; i < n; i += 3) {
        unsigned v = p[i] << 16 | (i + 1 < n ? p[i + 1] << 8 : 0) | (i + 2 < n ? p[i + 2] : 0);
        o += t[v >> 18 & 63]; o += t[v >> 12 & 63];
        o += i + 1 < n ? t[v >> 6 & 63] : '='; o += i + 2 < n ? t[v & 63] : '=';
    }
    return o;
}
#else
bool socketPair(sock_t sv[2]) { return ::socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == 0; }
bool sendWithFd(sock_t s, const void *p, size_t n, int fd)
{
    iovec io{(void *)p, n};
    char cbuf[CMSG_SPACE(sizeof(int))] = {0};
    msghdr m{}; m.msg_iov = &io; m.msg_iovlen = 1; m.msg_control = cbuf; m.msg_controllen = sizeof cbuf;
    cmsghdr *c = CMSG_FIRSTHDR(&m);
    c->cmsg_level = SOL_SOCKET; c->cmsg_type = SCM_RIGHTS; c->cmsg_len = CMSG_LEN(sizeof(int));
    std::memcpy(CMSG_DATA(c), &fd, sizeof fd);
    return sendmsg(s, &m, 0) == (ssize_t)n;
}
// like recvSome, and any file descriptors passed with the data (SCM_RIGHTS) are appended to fds
int recvSomeFds(sock_t s, std::string &buf, std::vector<int> &fds, int timeoutMs)
{
    fd_set rf; FD_ZERO(&rf); FD_SET(s, &rf);
    timeval tv{timeoutMs / 1000, (timeoutMs % 1000) * 1000};
    int n = select((int)s + 1, &rf, nullptr, nullptr, &tv);
    if (n < 0) return -1;
    if (n == 0) return 0;
    static thread_local char b[262144];
    char cbuf[CMSG_SPACE(sizeof(int) * 8)];
    iovec io{b, sizeof b};
    msghdr m{}; m.msg_iov = &io; m.msg_iovlen = 1; m.msg_control = cbuf; m.msg_controllen = sizeof cbuf;
    ssize_t k = recvmsg(s, &m, 0);
    if (k <= 0) return -1;
    for (cmsghdr *c = CMSG_FIRSTHDR(&m); c; c = CMSG_NXTHDR(&m, c))
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_RIGHTS)
            for (size_t i = 0; i < (c->cmsg_len - CMSG_LEN(0)) / sizeof(int); i++) { int fd; std::memcpy(&fd, CMSG_DATA(c) + i * sizeof(int), sizeof fd); fds.push_back(fd); }
    buf.append(b, (size_t)k);
    return 1;
}
#endif

// QMP: one command on a fresh connection (TCP port, or a Unix socket path for fd passing)
std::string qmpOnce(const std::string &unixPath, int tcpPort, const std::string &cmd, int passFd = -1)
{
    sock_t s;
#ifdef _WIN32
    (void)unixPath; (void)passFd;
    s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sockaddr_in a{}; a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK); a.sin_port = htons((u_short)tcpPort);
    if (connect(s, (sockaddr *)&a, sizeof a)) { closesocket(s); return ""; }
#else
    (void)tcpPort;
    s = socket(AF_UNIX, SOCK_STREAM, 0);
    sockaddr_un a{}; a.sun_family = AF_UNIX; std::snprintf(a.sun_path, sizeof a.sun_path, "%s", unixPath.c_str());
    if (connect(s, (sockaddr *)&a, sizeof a)) { ::close(s); return ""; }
#endif
    std::string buf, line, out;
    auto readJson = [&](std::string &l) {
        for (int i = 0; i < 200; i++) {
            size_t e = buf.find('\n');
            if (e != std::string::npos) { l = buf.substr(0, e); buf.erase(0, e + 1); return true; }
            if (recvSome(s, buf, 50) < 0) return false;
        }
        return false;
    };
    readJson(line);
    std::string caps = "{\"execute\":\"qmp_capabilities\"}\n";
    sendAll(s, caps.data(), caps.size());
    readJson(line);
    std::string c = cmd + "\n";
#ifndef _WIN32
    if (passFd >= 0) sendWithFd(s, c.data(), c.size(), passFd); else
#endif
    sendAll(s, c.data(), c.size());
    while (readJson(line)) if (line.find("\"return\"") != std::string::npos || line.find("\"error\"") != std::string::npos) { out = line; break; }
    CLOSESOCK(s);
    return out;
}

// ------------------------------------------------------------------ D-Bus marshalling
struct W {
    std::string b;
    void pad(size_t n) { while (b.size() % n) b.push_back('\0'); }
    void y(uint8_t v) { b.push_back((char)v); }
    void u(uint32_t v) { pad(4); b.append((const char *)&v, 4); }
    void s(const std::string &v) { u((uint32_t)v.size()); b += v; b.push_back('\0'); }
    void g(const std::string &v) { y((uint8_t)v.size()); b += v; b.push_back('\0'); }
    void ay(const void *p, size_t n) { u((uint32_t)n); b.append((const char *)p, n); }
};
struct R {
    const std::string &b; size_t p;
    R(const std::string &bb, size_t pp) : b(bb), p(pp) {}
    void pad(size_t n) { while (p % n) p++; }
    uint8_t y() { return (uint8_t)b[p++]; }
    uint32_t u() { pad(4); uint32_t v; std::memcpy(&v, b.data() + p, 4); p += 4; return v; }
    int32_t i() { return (int32_t)u(); }
    uint64_t t() { pad(8); uint64_t v; std::memcpy(&v, b.data() + p, 8); p += 8; return v; }
    std::string s() { uint32_t n = u(); std::string v = b.substr(p, n); p += n + 1; return v; }
    std::string g() { uint8_t n = y(); std::string v = b.substr(p, n); p += n + 1; return v; }
};
enum { CALL = 1, RETURN = 2 };
struct Field { uint8_t code; char type; std::string sval; uint32_t uval; };

std::string message(uint8_t type, uint32_t serial, const std::vector<Field> &fields, const std::string &body, uint32_t flags = 0)
{
    W m;
    m.y('l'); m.y(type); m.y((uint8_t)flags); m.y(1);
    m.u((uint32_t)body.size()); m.u(serial);
    m.u(0);   // field array length, patched below
    size_t start = m.b.size();
    for (auto &f : fields) {
        m.pad(8); m.y(f.code);
        char sig[2] = {f.type, 0}; m.g(sig);
        if (f.type == 's' || f.type == 'o') m.s(f.sval);
        else if (f.type == 'g') m.g(f.sval);
        else m.u(f.uval);
    }
    uint32_t flen = (uint32_t)(m.b.size() - start);
    std::memcpy(&m.b[start - 4], &flen, 4);
    m.pad(8);
    return m.b + body;
}

// one complete message in buf -> its parts (false: incomplete)
bool parse(std::string &buf, uint8_t &type, uint8_t &flags, uint32_t &serial, std::string &member, std::string &iface, std::string &body)
{
    if (buf.size() < 16) return false;
    uint32_t blen, flen;
    std::memcpy(&blen, buf.data() + 4, 4); std::memcpy(&serial, buf.data() + 8, 4); std::memcpy(&flen, buf.data() + 12, 4);
    size_t hdrEnd = 16 + flen, bodyOff = hdrEnd + ((8 - hdrEnd % 8) % 8), total = bodyOff + blen;
    if (buf.size() < total) return false;
    type = (uint8_t)buf[1]; flags = (uint8_t)buf[2];
    R r(buf, 16);
    member.clear(); iface.clear();
    while (r.p < hdrEnd) {
        r.pad(8);
        if (r.p >= hdrEnd) break;
        uint8_t code = r.y();
        std::string sig = r.g();
        char c = sig.empty() ? 'u' : sig[0];
        if (c == 's' || c == 'o') { std::string v = r.s(); if (code == 3) member = v; if (code == 2) iface = v; }
        else if (c == 'g') r.g();
        else r.u();
    }
    body = buf.substr(bodyOff, blen);
    buf.erase(0, total);
    return true;
}

std::string authLine()
{
#ifdef _WIN32
    return std::string("\0", 1) + "AUTH ANONYMOUS 627363796e7468\r\n";   // QEMU offers ANONYMOUS to a duplicated socket
#else
    char uid[32], hex[80] = {0};
    std::snprintf(uid, sizeof uid, "%u", (unsigned)getuid());
    for (size_t i = 0; uid[i]; i++) std::snprintf(hex + 2 * i, 3, "%02x", (unsigned char)uid[i]);
    return std::string("\0", 1) + "AUTH EXTERNAL " + hex + "\r\n";
#endif
}
}  // namespace

// ------------------------------------------------------------------ the peer
bool DBusIn::start(const std::string &qmpUnixPath, int qmpTcpPort, unsigned long qemuPid)
{
    stop_ = false; error.clear(); enabled_ = false; rate_ = 0;
#ifdef _WIN32
    WSADATA wd; WSAStartup(MAKEWORD(2, 2), &wd);
#else
    (void)qemuPid;
#endif
    sock_t a[2], l[2];
    if (!socketPair(a) || !socketPair(l)) { error = "socketpair"; return false; }
    // 1. the p2p display connection: one end to QEMU
    std::string r;
#ifdef _WIN32
    WSAPROTOCOL_INFOW info;
    if (WSADuplicateSocketW(a[0], (DWORD)qemuPid, &info)) { error = "WSADuplicateSocket"; return false; }
    r = qmpOnce("", qmpTcpPort, "{\"execute\":\"get-win32-socket\",\"arguments\":{\"info\":\"" +
                base64((const unsigned char *)&info, sizeof info) + "\",\"fdname\":\"bsin\"}}");
#else
    r = qmpOnce(qmpUnixPath, 0, "{\"execute\":\"getfd\",\"arguments\":{\"fdname\":\"bsin\"}}", a[0]);
#endif
    CLOSESOCK(a[0]);
    if (r.find("\"return\"") == std::string::npos) { error = "fd to QEMU: " + r; return false; }
    r = qmpOnce(qmpUnixPath, qmpTcpPort, "{\"execute\":\"add_client\",\"arguments\":{\"protocol\":\"@dbus-display\",\"fdname\":\"bsin\"}}");
    if (r.find("\"return\"") == std::string::npos) { error = "add_client: " + r; return false; }
    sock_t c = a[1];
    std::string buf, line, al = authLine();
    sendAll(c, al.data(), al.size());
    if (!readLine(c, buf, line, 2000) || line.rfind("OK", 0) != 0) { error = "auth: " + line; return false; }
#ifndef _WIN32
    sendAll(c, "NEGOTIATE_UNIX_FD\r\n", 19);
    readLine(c, buf, line, 2000);
#endif
    sendAll(c, "BEGIN\r\n", 7);
    // the listener side is served from now on: QEMU authenticates on it while it handles the call below, and only
    // answers the call after that (waiting for the answer first would deadlock)
    listener_ = (intptr_t)l[1];
    th_ = std::thread([this] { serve(listener_); });
    // 2. RegisterInListener: the listener connection's other end goes to QEMU
    std::vector<Field> f = {{1, 'o', "/org/qemu/Display1/Audio", 0}, {2, 's', "org.qemu.Display1.Audio", 0},
                            {3, 's', "RegisterInListener", 0}};
    W body;
#ifdef _WIN32
    WSAPROTOCOL_INFOW li;
    if (WSADuplicateSocketW(l[0], (DWORD)qemuPid, &li)) { error = "WSADuplicateSocket 2"; return false; }
    body.ay(&li, sizeof li);
    f.push_back({8, 'g', "ay", 0});
    std::string m = message(CALL, 1, f, body.b);
    sendAll(c, m.data(), m.size());
#else
    body.u(0);
    f.push_back({8, 'g', "h", 0});
    f.push_back({9, 'u', "", 1});
    std::string m = message(CALL, 1, f, body.b);
    sendWithFd(c, m.data(), m.size(), l[0]);
#endif
    CLOSESOCK(l[0]);
    // the reply
    uint8_t type = 0, flags; uint32_t serial; std::string member, iface, rb;
    for (int i = 0; i < 100 && !parse(buf, type, flags, serial, member, iface, rb); i++) recvSome(c, buf, 100);
    if (type != RETURN) {
        // an ERROR (3) carries its name in the header and its message as the body's first string
        error = "RegisterInListener refused (reply type " + std::to_string(type) + ")";
        if (type == 3 && rb.size() >= 4) { R e(rb, 0); error += ": " + e.s(); }
        stop_ = true; CLOSESOCK(l[1]); listener_ = -1; if (th_.joinable()) th_.join(); stop_ = false;
        CLOSESOCK(c);
        return false;
    }
    connBuf_ = buf;
    conn_ = (intptr_t)c;
    connected_ = true;
    return true;
}

void DBusIn::serve(intptr_t ls)
{
    sock_t s = (sock_t)ls;
    std::string buf, line, al = authLine();
    // QEMU authenticates as the server here too: we are the SASL client, then we answer its calls
    sendAll(s, al.data(), al.size());
    if (!readLine(s, buf, line, 2000)) { error = "listener auth"; connected_ = false; return; }
    sendAll(s, "BEGIN\r\n", 7);
    uint32_t out = 1000;
    std::vector<int16_t> pcm;
    while (!stop_) {
        uint8_t type, flags; uint32_t serial; std::string member, iface, body;
        if (!parse(buf, type, flags, serial, member, iface, body)) {
            if (recvSome(s, buf, 100) < 0) break;   // QEMU went away
            continue;
        }
        if (type != CALL) continue;
        W reply; std::string sig;
        R r(body, 0);
        if (member == "Init") {
            r.t(); r.y(); r.u(); r.u(); rate_ = r.u();
        } else if (member == "SetEnabled") {
            r.t(); enabled_ = r.u() != 0;
            if (enabled_) ring.clear();
        } else if (member == "Read") {
            r.t(); uint64_t size = r.t();
            size_t frames = (size_t)(size / 4);
            pcm.resize(frames * 2);
            const size_t got = ring.read(pcm.data(), frames);   // only what is in hand: the DAW paces the card
            reply.ay(pcm.data(), got * 4); sig = "ay";
            reads_++;
        } else if (iface == "org.freedesktop.DBus.Properties" && member == "Get") {
            reply.g("as"); reply.u(0); sig = "v";
        } else if (iface == "org.freedesktop.DBus.Properties" && member == "GetAll") {
            reply.u(0); sig = "a{sv}";
        }
        if (flags & 1) continue;   // no reply expected
        std::vector<Field> f = {{5, 'u', "", serial}};
        if (!sig.empty()) f.push_back({8, 'g', sig, 0});
        std::string m = message(RETURN, ++out, f, reply.b);
        if (!sendAll(s, m.data(), m.size())) break;
    }
    connected_ = false;
}

// ------------------------------------------------------------------ the screen
bool DBusIn::startDisplay(RectFn fn, unsigned long qemuPid)
{
    displayError.clear();
    if (conn_ < 0) { displayError = "no connection"; return false; }
#ifndef _WIN32
    (void)qemuPid;
#endif
    rect_ = std::move(fn);
    sock_t c = (sock_t)conn_, l[2];
    if (!socketPair(l)) { displayError = "socketpair"; return false; }
    dlistener_ = (intptr_t)l[1];
    dth_ = std::thread([this] { serveDisplay(dlistener_); });   // served before the call (see start)
    std::vector<Field> f = {{1, 'o', "/org/qemu/Display1/Console_0", 0}, {2, 's', "org.qemu.Display1.Console", 0},
                            {3, 's', "RegisterListener", 0}};
    W body;
#ifdef _WIN32
    WSAPROTOCOL_INFOW li;
    if (WSADuplicateSocketW(l[0], (DWORD)qemuPid, &li)) { displayError = "WSADuplicateSocket"; return false; }
    body.ay(&li, sizeof li);
    f.push_back({8, 'g', "ay", 0});
    std::string m = message(CALL, 2, f, body.b);
    sendAll(c, m.data(), m.size());
#else
    body.u(0);
    f.push_back({8, 'g', "h", 0});
    f.push_back({9, 'u', "", 1});
    std::string m = message(CALL, 2, f, body.b);
    sendWithFd(c, m.data(), m.size(), l[0]);
#endif
    CLOSESOCK(l[0]);
    uint8_t type = 0, flags; uint32_t serial = 0; std::string member, iface, rb;
    for (int i = 0; i < 100; i++) {
        while (parse(connBuf_, type, flags, serial, member, iface, rb)) if (type == RETURN || type == 3) break;
        if (type == RETURN || type == 3) break;
        recvSome(c, connBuf_, 100);
    }
    if (type != RETURN) {
        displayError = type == 3 ? "RegisterListener: error" : "RegisterListener: no reply";
        if (type == 3 && rb.size() >= 4) { R e(rb, 0); displayError += ": " + e.s(); }
        CLOSESOCK(l[1]); dlistener_ = -1; if (dth_.joinable()) dth_.join();
        return false;
    }
    return true;
}

void DBusIn::serveDisplay(intptr_t ls)
{
    sock_t s = (sock_t)ls;
    std::string buf, line, al = authLine();
    std::vector<int> fds;
    sendAll(s, al.data(), al.size());
    if (!readLine(s, buf, line, 2000)) { displayError = "listener auth"; return; }
#ifndef _WIN32
    sendAll(s, "NEGOTIATE_UNIX_FD\r\n", 19);
    bool unixFd = readLine(s, buf, line, 2000) && line.rfind("AGREE_UNIX_FD", 0) == 0;
#else
    bool unixFd = false;
#endif
    sendAll(s, "BEGIN\r\n", 7);
    displayOn_ = true;
    uint32_t out = 5000;
    // the mapped framebuffer (Unix.Map)
    const uint8_t *map = nullptr; size_t mapLen = 0; int mapFd = -1;
    uint32_t mw = 0, mh = 0, mstride = 0, mfmt = 0, moff = 0;
    auto unmap = [&] {
#ifndef _WIN32
        if (map) munmap((void *)map, mapLen);
        if (mapFd >= 0) ::close(mapFd);
#endif
        map = nullptr; mapLen = 0; mapFd = -1;
    };
    while (!stop_) {
        uint8_t type, flags; uint32_t serial; std::string member, iface, body;
        if (!parse(buf, type, flags, serial, member, iface, body)) {
#ifndef _WIN32
            int k = unixFd ? recvSomeFds(s, buf, fds, 100) : recvSome(s, buf, 100);
#else
            int k = recvSome(s, buf, 100);
#endif
            if (k < 0) break;
            continue;
        }
        if (type != CALL) continue;
        W reply; std::string sig;
        R r(body, 0);
        if (member == "Scanout") {
            uint32_t w = r.u(), h = r.u(), stride = r.u(), fmt = r.u(), n = r.u();
            if (n >= (uint64_t)stride * (h ? h - 1 : 0) + (uint64_t)w * ((fmt >> 24) / 8)) rect_(0, 0, (int)w, (int)h, (const uint8_t *)body.data() + r.p, stride, fmt);
            mapped_ = false; updates_++;
        } else if (member == "Update") {
            int x = r.i(), y = r.i(), w = r.i(), h = r.i();
            uint32_t stride = r.u(), fmt = r.u(), n = r.u();
            if (w > 0 && h > 0 && n >= (uint64_t)stride * (h - 1) + (uint64_t)w * ((fmt >> 24) / 8)) rect_(x, y, w, h, (const uint8_t *)body.data() + r.p, stride, fmt);
            updates_++;
#ifndef _WIN32
        } else if (member == "ScanoutMap") {
            uint32_t idx = r.u(); moff = r.u(); mw = r.u(); mh = r.u(); mstride = r.u(); mfmt = r.u();
            unmap();
            if (idx < fds.size()) {
                mapFd = fds[idx]; fds.erase(fds.begin() + idx);
                mapLen = (size_t)moff + (size_t)mstride * mh;
                void *p = mmap(nullptr, mapLen, PROT_READ, MAP_SHARED, mapFd, 0);
                if (p == MAP_FAILED) { map = nullptr; ::close(mapFd); mapFd = -1; } else map = (const uint8_t *)p;
            }
            if (map) { rect_(0, 0, (int)mw, (int)mh, map + moff, mstride, mfmt); mapped_ = true; }
            for (int fd : fds) ::close(fd);
            fds.clear();
            updates_++;
        } else if (member == "UpdateMap") {
            int x = r.i(), y = r.i(), w = r.i(), h = r.i();
            if (map && w > 0 && h > 0 && x >= 0 && y >= 0 && (uint32_t)(x + w) <= mw && (uint32_t)(y + h) <= mh)
                rect_(x, y, w, h, map + moff + (size_t)y * mstride + (size_t)x * ((mfmt >> 24) / 8), mstride, mfmt);
            updates_++;
#endif
        } else if (iface == "org.freedesktop.DBus.Properties" && (member == "Get" || member == "GetAll")) {
            // which optional listener interfaces we implement: the shared-memory map where fds can be passed
            W v;
            v.g("as");
            v.u(unixFd ? 1u : 0u);
            size_t lenAt = v.b.size() - 4, start = v.b.size();
            if (unixFd) v.s("org.qemu.Display1.Listener.Unix.Map");
            uint32_t alen = (uint32_t)(v.b.size() - start);
            std::memcpy(&v.b[lenAt], &alen, 4);
            if (member == "Get") { reply.b = v.b; sig = "v"; }
            else {
                // a{sv} with one entry: Interfaces
                reply.u(0); size_t at = reply.b.size() - 4;
                reply.pad(8); size_t st = reply.b.size();
                reply.s("Interfaces");
                // the variant: signature then value, aligned within this message's body
                reply.g("as"); reply.u(0); size_t la = reply.b.size() - 4, sa = reply.b.size();
                if (unixFd) reply.s("org.qemu.Display1.Listener.Unix.Map");
                uint32_t al2 = (uint32_t)(reply.b.size() - sa); std::memcpy(&reply.b[la], &al2, 4);
                uint32_t tot = (uint32_t)(reply.b.size() - st); std::memcpy(&reply.b[at], &tot, 4);
                sig = "a{sv}";
            }
        }
        // Disable, MouseSet, CursorDefine and anything else: an empty reply
        if (flags & 1) continue;
        std::vector<Field> f = {{5, 'u', "", serial}};
        if (!sig.empty()) f.push_back({8, 'g', sig, 0});
        std::string m = message(RETURN, ++out, f, reply.b);
        if (!sendAll(s, m.data(), m.size())) break;
    }
    unmap();
    displayOn_ = false;
}

void DBusIn::stopDisplay()
{
    if (dlistener_ >= 0) { CLOSESOCK((sock_t)dlistener_); dlistener_ = -1; }
    if (dth_.joinable()) dth_.join();
    displayOn_ = false; mapped_ = false;
}

void DBusIn::stop()
{
    stop_ = true;
    if (dlistener_ >= 0) { CLOSESOCK((sock_t)dlistener_); dlistener_ = -1; }
    if (dth_.joinable()) dth_.join();
    if (listener_ >= 0) { CLOSESOCK((sock_t)listener_); listener_ = -1; }
    if (conn_ >= 0) { CLOSESOCK((sock_t)conn_); conn_ = -1; }
    if (th_.joinable()) th_.join();
    connected_ = false;
}

}  // namespace bsynth

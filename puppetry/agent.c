/*
 * agent - tiny remote runner for a Windows XP guest.
 * Polls http://HOST:PORT/next for a command line, runs it, and POSTs the
 * output to /out.  Two built-ins:  "get <url-path> <local-file>" downloads
 * from the same server, and "spawn <cmdline>" starts without waiting.
 * Build: i686-w64-mingw32-gcc -O2 -o agent.exe agent.c -lws2_32
 */
#include <winsock2.h>
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *HOST = "10.0.2.2";
static int PORT = 8765;

/* one HTTP request; returns malloc'd body (NUL-terminated), sets *len */
static char *http(const char *method, const char *path, const char *body, int blen, int *len)
{
    SOCKET s;
    struct sockaddr_in a;
    char hdr[512], *buf = NULL, *p;
    int cap = 0, n = 0, r;
    *len = 0;
    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) return NULL;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons((u_short)PORT);
    a.sin_addr.s_addr = inet_addr(HOST);
    {   /* never hang forever: a loadvm can strand a half-open connection */
        int to = 8000;
        setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char *)&to, sizeof to);
        setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, (const char *)&to, sizeof to);
    }
    if (connect(s, (struct sockaddr *)&a, sizeof a)) { closesocket(s); return NULL; }
    sprintf(hdr, "%s %s HTTP/1.0\r\nHost: x\r\nContent-Length: %d\r\n\r\n", method, path, blen);
    send(s, hdr, (int)strlen(hdr), 0);
    if (blen) send(s, body, blen, 0);
    for (;;) {
        if (n + 65536 > cap) { cap = cap * 2 + 65536; buf = (char *)realloc(buf, cap + 1); }
        r = recv(s, buf + n, cap - n, 0);
        if (r <= 0) break;
        n += r;
    }
    closesocket(s);
    if (!buf) return NULL;
    buf[n] = 0;
    p = strstr(buf, "\r\n\r\n");
    if (!p) { free(buf); return NULL; }
    p += 4;
    *len = n - (int)(p - buf);
    memmove(buf, p, *len + 1);
    return buf;
}

static void post_out(const char *text, int len)
{
    int l;
    char *r = http("POST", "/out", text, len, &l);
    free(r);
}

static void run(const char *cmd)
{
    char line[4096], *out = NULL;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    FILE *f;
    long sz;
    if (!strncmp(cmd, "get ", 4)) {
        char url[1024], file[1024];
        int l;
        char *data;
        if (sscanf(cmd + 4, "%1023s %1023[^\r\n]", url, file) == 2 && (data = http("GET", url, NULL, 0, &l))) {
            f = fopen(file, "wb");
            if (f) { fwrite(data, 1, l, f); fclose(f); sprintf(line, "saved %s %d bytes\n", file, l); }
            else sprintf(line, "cannot write %s\n", file);
            free(data);
        } else sprintf(line, "get failed\n");
        post_out(line, (int)strlen(line));
        return;
    }
    memset(&si, 0, sizeof si);
    si.cb = sizeof si;
    if (!strncmp(cmd, "spawn ", 6)) {
        snprintf(line, sizeof line, "%s", cmd + 6);
        if (CreateProcessA(NULL, line, NULL, NULL, FALSE, 0, NULL, "C:\\p", &si, &pi)) {
            CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
            post_out("spawned\n", 8);
        } else post_out("spawn failed\n", 13);
        return;
    }
    snprintf(line, sizeof line, "cmd.exe /c %s > C:\\p\\agent.out 2>&1", cmd);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    if (!CreateProcessA(NULL, line, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, "C:\\p", &si, &pi)) {
        post_out("start failed\n", 13);
        return;
    }
    WaitForSingleObject(pi.hProcess, 120000);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    f = fopen("C:\\p\\agent.out", "rb");
    if (!f) { post_out("(no output)\n", 12); return; }
    fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET);
    out = (char *)malloc(sz + 1);
    sz = (long)fread(out, 1, sz, f);
    fclose(f);
    post_out(out, (int)sz);
    free(out);
}

int WINAPI WinMain(HINSTANCE a, HINSTANCE b, LPSTR c, int d)
{
    WSADATA w;
    (void)a; (void)b; (void)c; (void)d;
    WSAStartup(MAKEWORD(2, 0), &w);
    CreateDirectoryA("C:\\p", NULL);
    for (;;) {
        int l;
        char *cmd = http("GET", "/next", NULL, 0, &l);
        if (cmd && l > 0) { while (l && (cmd[l - 1] == '\n' || cmd[l - 1] == '\r')) cmd[--l] = 0; run(cmd); }
        else Sleep(300);
        free(cmd);
    }
}

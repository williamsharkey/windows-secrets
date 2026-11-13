/* PRESET ENGINE 2, measurements on XP's real Sound Recorder (sndrec32.exe), run in a dev VM of our own:
     t1    the position trackbar: range, line and page size, and where a seek really lands (Delete After at the seek
           point, then Save: the saved length is the position, exact to one frame)
     fx    the AESTHETIC-PRESETS open questions: Add Echo's delay, repeats and decay (an impulse through E and EE);
           whether Add Echo, Paste Mix and Mix with File lengthen the buffer; and Decrease/Increase Speed round
           trips on white noise (a low-pass?). The edited files are printed as base64 ("FILE name size" + lines),
           so the host can analyse them (design/proto/sr_analyze.py).
   The sources are synthetic (made here). Nothing from Windows leaves the VM except these measurements.
   Build: i686-w64-mingw32-gcc -O2 -o sr_probe.exe sr_probe.c -luser32 -lwinmm -static */
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define SR_POS 201
#define SR_LEN 202
#define SR_TRACK 204
#define SR_SAVE 13
#define SR_COPY 20
#define SR_PASTE_MIX 25
#define SR_MIXFILE 23
#define SR_DEL_AFTER 32
#define SR_SPEED_UP 35
#define SR_SPEED_DOWN 36
#define SR_ECHO 37
#define RATE 22050

static void wav(const char *path, int frames, int kind)    /* 0 sine 440, 1 impulse at 100 ms, 2 white noise, 3 sine 1 kHz */
{
    FILE *f = fopen(path, "wb");
    int i, n = frames * 2, v;
    unsigned seed = 777;
    long hdr[] = {0x46464952, 36 + n, 0x45564157, 0x20746D66, 16, 0x00010001, RATE, RATE * 2, 0x00100002, 0x61746164, n};
    fwrite(hdr, 4, 11, f);
    for (i = 0; i < frames; i++) {
        short s = 0;
        if (kind == 0) s = (short)(12000 * sin(2 * 3.14159265358979 * 440.0 * i / RATE));
        if (kind == 3) s = (short)(12000 * sin(2 * 3.14159265358979 * 1000.0 * i / RATE));
        if (kind == 1) s = i == RATE / 10 ? 24000 : 0;
        if (kind == 2) { seed = seed * 1103515245u + 12345u; v = (int)((seed >> 16) & 0x7FFF) - 16384; s = (short)(v * 0.6); }
        fwrite(&s, 2, 1, f);
    }
    fclose(f);
}
static PROCESS_INFORMATION pi;
static HWND srw;
static BOOL CALLBACK findw(HWND w, LPARAM l)
{
    DWORD pid = 0;
    GetWindowThreadProcessId(w, &pid);
    if (pid == pi.dwProcessId && IsWindowVisible(w) && GetDlgItem(w, SR_TRACK)) { srw = w; return FALSE; }
    return TRUE;
}
static HWND open_sr(const char *path)
{
    char cmd[512];
    STARTUPINFOA si;
    int i;
    memset(&si, 0, sizeof si); si.cb = sizeof si;
    sprintf(cmd, "sndrec32.exe \"%s\"", path);
    srw = NULL;
    if (!CreateProcessA(NULL, cmd, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) { printf("log cannot start sndrec32\n"); return NULL; }
    WaitForInputIdle(pi.hProcess, 10000);
    for (i = 0; i < 100 && !srw; i++) { EnumWindows(findw, 0); if (!srw) Sleep(100); }
    Sleep(300);
    return srw;
}
static void close_sr(void) { TerminateProcess(pi.hProcess, 0); WaitForSingleObject(pi.hProcess, 5000); CloseHandle(pi.hProcess); CloseHandle(pi.hThread); Sleep(200); }
static void cmd(int id) { SendMessageA(srw, WM_COMMAND, MAKEWPARAM(id, 0), (LPARAM)GetDlgItem(srw, id)); Sleep(150); }
static void text(int id, char *t) { GetDlgItemTextA(srw, id, t, 64); }
static void seek_permille(LONG pm)    /* exactly as srhook's seek() */
{
    HWND tb = GetDlgItem(srw, SR_TRACK);
    LONG mx = (LONG)SendMessageA(tb, TBM_GETRANGEMAX, 0, 0), p = (LONG)((double)mx * pm / 1000);
    SendMessageA(tb, TBM_SETPOS, TRUE, p);
    SendMessageA(srw, WM_HSCROLL, MAKEWPARAM(TB_THUMBPOSITION, p), (LPARAM)tb);
    SendMessageA(srw, WM_HSCROLL, MAKEWPARAM(TB_ENDTRACK, 0), (LPARAM)tb);
    Sleep(100);
}
static long datalen(const char *path)     /* the data chunk's size in bytes */
{
    FILE *f = fopen(path, "rb");
    unsigned char b[4096];
    long n, i;
    if (!f) return -1;
    n = (long)fread(b, 1, sizeof b, f);
    fclose(f);
    for (i = 12; i + 8 <= n; ) {
        long sz = b[i + 4] | b[i + 5] << 8 | b[i + 6] << 16 | (long)b[i + 7] << 24;
        if (!memcmp(b + i, "data", 4)) return sz;
        i += 8 + sz + (sz & 1);
    }
    return -1;
}
static void dump(const char *path)
{
    static const char *b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    FILE *f = fopen(path, "rb");
    unsigned char in[57];
    char out[80];
    size_t n, i, k;
    long total = 0;
    if (!f) return;
    fseek(f, 0, SEEK_END); total = ftell(f); fseek(f, 0, SEEK_SET);
    printf("FILE %s %ld\n", path, total);
    while ((n = fread(in, 1, 57, f)) > 0) {
        for (i = 0, k = 0; i < n; i += 3) {
            unsigned v = in[i] << 16 | (i + 1 < n ? in[i + 1] << 8 : 0) | (i + 2 < n ? in[i + 2] : 0);
            out[k++] = b64[v >> 18 & 63]; out[k++] = b64[v >> 12 & 63];
            out[k++] = i + 1 < n ? b64[v >> 6 & 63] : '='; out[k++] = i + 2 < n ? b64[v & 63] : '=';
        }
        out[k] = 0;
        printf("%s\n", out);
    }
    printf("END\n");
    fclose(f);
}
/* Sound Recorder's dialogs, answered the way srhook answers them: the Open dialog of Mix with File gets the file
   name; a message box ("All data after the position ... will be deleted. Continue?") gets OK. */
static const char *mixName = "C:\\p\\sine2s.wav";
static HWND dlgFound;
static BOOL CALLBACK findDlg(HWND w, LPARAM l)
{
    char cls[16];
    DWORD pid = 0;
    GetWindowThreadProcessId(w, &pid);
    GetClassNameA(w, cls, sizeof cls);
    if (pid == pi.dwProcessId && IsWindowVisible(w) && !strcmp(cls, "#32770")) { dlgFound = w; return FALSE; }
    return TRUE;
}
static DWORD WINAPI answer(LPVOID unused)
{
    for (;;) {
        dlgFound = NULL;
        if (pi.dwProcessId) EnumWindows(findDlg, 0);
        if (dlgFound) {
            HWND d = dlgFound, e;
            Sleep(300);
            e = GetDlgItem(d, 0x47C);              /* the file name combo (cmb13); its edit is the child */
            if (e) { HWND ed = FindWindowExA(e, NULL, "Edit", NULL); SendMessageA(ed ? ed : e, WM_SETTEXT, 0, (LPARAM)mixName); }
            if ((e = GetDlgItem(d, 0x480))) SendMessageA(e, WM_SETTEXT, 0, (LPARAM)mixName);
            PostMessageA(d, WM_COMMAND, IDOK, 0);
            Sleep(500);
        }
        Sleep(50);
    }
    return 0;
}
static void step(const char *src, const char *dst, const char *ops)   /* copy src to dst, run ops on it, save */
{
    const char *o;
    char t[64];
    CopyFileA(src, dst, FALSE);
    if (!open_sr(dst)) return;
    text(SR_LEN, t);
    printf("ops %s on %s: before %ld bytes (%s)", ops, dst, datalen(dst), t);
    for (o = ops; *o; o++) {
        if (*o == '<') cmd(SR_SPEED_DOWN);
        if (*o == '>') cmd(SR_SPEED_UP);
        if (*o == 'E') cmd(SR_ECHO);
        if (*o == 'C') cmd(SR_COPY);
        if (*o == 'X') cmd(SR_PASTE_MIX);
        if (*o == 'h') seek_permille(500);
        if (*o == 'z') seek_permille(0);
        if (*o == 'M') { cmd(SR_MIXFILE); Sleep(1500); }
    }
    text(SR_LEN, t);
    cmd(SR_SAVE);
    Sleep(500);
    close_sr();
    printf(" after %ld bytes (%s)\n", datalen(dst), t);
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "t1";
    char t[64];
    CreateThread(NULL, 0, answer, NULL, 0, NULL);
    wav("C:\\p\\t1s.wav", RATE, 0);
    wav("C:\\p\\t8s.wav", RATE * 8, 0);
    wav("C:\\p\\imp.wav", RATE, 1);
    wav("C:\\p\\noise.wav", RATE * 2, 2);
    wav("C:\\p\\sine1s.wav", RATE, 3);
    wav("C:\\p\\sine2s.wav", RATE * 2, 3);
    if (!strcmp(mode, "t1")) {
        const char *files[] = {"C:\\p\\t1s.wav", "C:\\p\\t8s.wav"};
        LONG pms[] = {0, 1, 2, 3, 5, 10, 123, 250, 500, 777, 999, 1000};
        int f, k;
        for (f = 0; f < 2; f++) {
            HWND tb;
            if (!open_sr(files[f])) return 1;
            tb = GetDlgItem(srw, SR_TRACK);
            text(SR_LEN, t);
            printf("t1 %s length %s frames %ld: trackbar range %ld..%ld line %ld page %ld\n", files[f], t, datalen(files[f]) / 2,
                   (long)SendMessageA(tb, TBM_GETRANGEMIN, 0, 0), (long)SendMessageA(tb, TBM_GETRANGEMAX, 0, 0),
                   (long)SendMessageA(tb, TBM_GETLINESIZE, 0, 0), (long)SendMessageA(tb, TBM_GETPAGESIZE, 0, 0));
            close_sr();
            for (k = 0; k < (int)(sizeof pms / sizeof pms[0]); k++) {
                char tmp[64], pos[64];
                long mx;
                sprintf(tmp, "C:\\p\\seek%d.wav", f);
                CopyFileA(files[f], tmp, FALSE);
                if (!open_sr(tmp)) return 1;
                mx = (long)SendMessageA(GetDlgItem(srw, SR_TRACK), TBM_GETRANGEMAX, 0, 0);
                seek_permille(pms[k]);
                text(SR_POS, pos);
                cmd(SR_DEL_AFTER);
                cmd(SR_SAVE);
                Sleep(400);
                close_sr();
                printf("t1 %s seek %ld permille (trackbar %ld of %ld): Position shows %s, Delete After keeps %ld frames (asked %.1f)\n",
                       files[f], pms[k], (long)(mx * pms[k] / 1000), mx, pos, datalen(tmp) / 2, (double)pms[k] * datalen(files[f]) / 2 / 1000);
            }
        }
    } else if (!strcmp(mode, "fx")) {
        step("C:\\p\\imp.wav", "C:\\p\\e1.wav", "E");
        step("C:\\p\\imp.wav", "C:\\p\\e2.wav", "EE");
        step("C:\\p\\sine1s.wav", "C:\\p\\px.wav", "CzhX");       /* copy, seek 50 %, paste mix */
        step("C:\\p\\sine1s.wav", "C:\\p\\mf.wav", "hM");         /* seek 50 %, mix with a 2 s file */
        step("C:\\p\\noise.wav", "C:\\p\\du.wav", "<>");
        step("C:\\p\\noise.wav", "C:\\p\\ud.wav", "><");
        step("C:\\p\\noise.wav", "C:\\p\\dduu.wav", "<<>>");
        step("C:\\p\\noise.wav", "C:\\p\\uudd.wav", ">><<");
        step("C:\\p\\noise.wav", "C:\\p\\d.wav", "<");
        step("C:\\p\\noise.wav", "C:\\p\\u.wav", ">");
        dump("C:\\p\\noise.wav");
        dump("C:\\p\\e1.wav"); dump("C:\\p\\e2.wav"); dump("C:\\p\\px.wav"); dump("C:\\p\\mf.wav");
        dump("C:\\p\\du.wav"); dump("C:\\p\\ud.wav"); dump("C:\\p\\dduu.wav"); dump("C:\\p\\uudd.wav");
        dump("C:\\p\\d.wav"); dump("C:\\p\\u.wav");
    }
    return 0;
}

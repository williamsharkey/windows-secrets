/* PRESET ENGINE 2 prototype: read the XP mine game's board from its memory and print the `grid` line of
   design/PRESET-ENGINE-2.md section 7.4.  STATUS: NOT RUN YET. It is the first probe to run in a dev VM of our
   own (never in a machine another session runs). It prints what it finds, so a wrong address shows at once.

   Build (in XP): tcc -o winmine_probe.exe winmine_probe.c -luser32
   Run: start winmine.exe, then winmine_probe.exe (it also accepts "--dump" to print the raw bytes).

   Addresses: the community-documented layout of the English XP SP2/SP3 winmine.exe (image base 0x01000000):
     0x01005330 mine count, 0x01005334 width, 0x01005338 height, 0x01005340 board: rows of 32 bytes, row 0 and
     row h+1 are border (0x10), column 0 and column w+1 are border too.
   Cell bytes (bit 0x80 = a mine is under it):
     0x0F hidden, 0x8F hidden mine, 0x40+n revealed with n neighbors, 0x0E flag, 0x8E flag on a mine,
     0x0D question mark, 0x8D question mark on a mine, 0x8A mine shown at the end, 0xCC the mine that was hit,
     0x0B a wrong flag shown at the end.
   If the border check fails, the probe scans the image's data pages for a 32-byte-stride grid framed by 0x10. */
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define BASE_MINES 0x01005330
#define BASE_W     0x01005334
#define BASE_H     0x01005338
#define BASE_BOARD 0x01005340
#define ROWB 32

static HANDLE proc;
static int rd(DWORD addr, void *buf, DWORD n) { SIZE_T got = 0; return ReadProcessMemory(proc, (LPCVOID)addr, buf, n, &got) && got == n; }

static int framed(const BYTE *b, int w, int h)
{
    int x, y;
    for (x = 0; x < w + 2; x++) if (b[x] != 0x10 || b[(h + 1) * ROWB + x] != 0x10) return 0;
    for (y = 0; y < h + 2; y++) if (b[y * ROWB] != 0x10 || b[y * ROWB + w + 1] != 0x10) return 0;
    return 1;
}

static char cell(BYTE c)
{
    if ((c & 0xF0) == 0x40 && (c & 0x0F) <= 8) return (char)('0' + (c & 0x0F));
    switch (c) {
    case 0x0F: case 0x8F: return '.';
    case 0x0E: case 0x8E: return 'F';
    case 0x0D: case 0x8D: return '?';
    case 0x8A: return '*';
    case 0xCC: return 'X';
    case 0x0B: return 'x';
    }
    return '#';   /* unknown: the probe shows it so the table can be corrected */
}

int main(int argc, char **argv)
{
    HWND w = FindWindowA("Minesweeper", NULL);
    DWORD pid = 0, board = BASE_BOARD;
    int W = 0, H = 0, M = 0, x, y, hidden = 0, open = 0, mines = 0, hit = 0;
    static BYTE b[ROWB * 27];
    char cells[30 * 24 + 1], st;
    char *q = cells;
    if (!w) { printf("log no mine game window (class Minesweeper)\n"); return 1; }
    GetWindowThreadProcessId(w, &pid);
    proc = OpenProcess(PROCESS_VM_READ, FALSE, pid);
    if (!proc) { printf("log OpenProcess failed %lu\n", GetLastError()); return 1; }
    rd(BASE_MINES, &M, 4); rd(BASE_W, &W, 4); rd(BASE_H, &H, 4);
    printf("log mines %d width %d height %d\n", M, W, H);
    if (W < 1 || W > 30 || H < 1 || H > 24 || !rd(board, b, sizeof b) || !framed(b, W, H)) {
        DWORD a;
        printf("log the documented address does not hold the board: scanning\n");
        for (a = 0x01005000; a < 0x01007000; a += 4) {
            if (!rd(a, b, sizeof b)) continue;
            if (b[0] == 0x10 && b[1] == 0x10 && W >= 1 && W <= 30 && H >= 1 && H <= 24 && framed(b, W, H)) { board = a; break; }
        }
        if (a >= 0x01007000) { printf("log board not found\n"); return 1; }
        printf("log board at 0x%08lX\n", board);
    }
    if (argc > 1 && !strcmp(argv[1], "--dump"))
        for (y = 0; y < H + 2; y++) { for (x = 0; x < W + 2; x++) printf("%02X ", b[y * ROWB + x]); printf("\n"); }
    for (y = 1; y <= H; y++)
        for (x = 1; x <= W; x++) {
            BYTE c = b[y * ROWB + x];
            char k = cell(c);
            *q++ = k;
            if (k == '.') hidden++;
            if (k >= '0' && k <= '8') open++;
            if (c & 0x80) mines++;
            if (k == 'X') hit = 1;
        }
    *q = 0;
    /* the game state from the cells: lost (a mine was hit), won (every safe cell open), new (all hidden), playing */
    st = hit ? 'l' : open == W * H - mines ? 'w' : open == 0 ? 'n' : 'p';
    printf("grid %d %d %c %s\n", W, H, st, cells);
    CloseHandle(proc);
    return 0;
}

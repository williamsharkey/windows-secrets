/* PRESET ENGINE 2 prototype: read the XP mine game's board from its memory and print the `grid` line of
   design/PRESET-ENGINE-2.md section 7.4.  STATUS: NOT RUN YET. It is the first probe to run in a dev VM of our
   own (never in a machine another session runs). It prints what it finds, so a wrong address shows at once.

   Build: tcc -o winmine_probe.exe winmine_probe.c -luser32   (or i686-w64-mingw32-gcc -O2 ... -luser32)
   Run: start winmine.exe, then winmine_probe.exe (it also accepts "--dump" to print the raw bytes).
   T7: winmine_probe.exe --scenario starts the game itself and walks every state (section 12, results in the spec):
   levels, flag, question mark, dig, a loss (mines shown, the hit mine, a wrong flag) and a win, printing the grid
   line after each step. Clicks are posted mouse messages, as the synth's auto-dig would post them.

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

static int W, H, M;
static BYTE b[ROWB * 27];
static int probe(int dump, int quiet)
{
    DWORD board = BASE_BOARD;
    int x, y, hidden = 0, open = 0, mines = 0, hit = 0;
    char cells[30 * 24 + 1], st;
    char *q = cells;
    rd(BASE_MINES, &M, 4); rd(BASE_W, &W, 4); rd(BASE_H, &H, 4);
    printf("log mines %d width %d height %d\n", M, W, H);
    if (W < 1 || W > 30 || H < 1 || H > 24 || !rd(board, b, sizeof b) || !framed(b, W, H)) {
        DWORD a;
        printf("log the documented address does not hold the board: scanning\n");
        for (a = 0x01005000; a < 0x01007000; a += 4) {
            if (!rd(a, b, sizeof b)) continue;
            if (b[0] == 0x10 && b[1] == 0x10 && W >= 1 && W <= 30 && H >= 1 && H <= 24 && framed(b, W, H)) { board = a; break; }
        }
        if (a >= 0x01007000) { printf("log board not found\n"); return 0; }
        printf("log board at 0x%08lX\n", board);
    }
    if (dump)
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
    if (!quiet) printf("grid %d %d %c %s\n", W, H, st, cells);
    { int k; for (k = 0; cells[k]; k++) if (cells[k] == '#') { printf("log unknown cell byte %02X\n", b[(k / W + 1) * ROWB + k % W + 1]); break; } }
    return st;
}

static HWND game;
static void click(int col, int row, int right)
{
    LPARAM lp = MAKELPARAM(12 + 16 * col + 8, 55 + 16 * row + 8);
    PostMessageA(game, right ? WM_RBUTTONDOWN : WM_LBUTTONDOWN, right ? MK_RBUTTON : MK_LBUTTON, lp);
    PostMessageA(game, right ? WM_RBUTTONUP : WM_LBUTTONUP, 0, lp);
    Sleep(300);
}
static int menuId(const char *name)    /* the Game menu item with this text (Beginner, Intermediate, Expert, New) */
{
    HMENU m = GetSubMenu(GetMenu(game), 0);
    int i, n = GetMenuItemCount(m);
    char t[64];
    for (i = 0; i < n; i++) { GetMenuStringA(m, i, t, sizeof t, MF_BYPOSITION); if (!strncmp(t[0] == '&' ? t + 1 : t, name, strlen(name))) return GetMenuItemID(m, i); }
    return -1;
}
static void level(const char *name) { PostMessageA(game, WM_COMMAND, menuId(name), 0); Sleep(600); }
static int at(int col, int row) { return b[(row + 1) * ROWB + col + 1]; }
static int findCell(int mine, int skip)  /* index of the skip-th hidden cell with (mine) or without a mine */
{
    int x, y;
    for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
        int c = at(x, y);
        if (c == 0x0F || c == 0x8F) if (((c & 0x80) != 0) == mine && skip-- == 0) return y * 32 + x;
    }
    return -1;
}
static void scenario(void)
{
    int c, k, t0, n;
    printf("log menu ids: Beginner %d Intermediate %d Expert %d New %d\n", menuId("Beginner"), menuId("Intermediate"), menuId("Expert"), menuId("New"));
    level("Beginner"); printf("step beginner new\n"); probe(0, 0);
    printf("step right-click (0,0) once, twice, three times\n");
    for (k = 0; k < 3; k++) { click(0, 0, 1); probe(0, 0); }
    c = findCell(0, 0); printf("step dig a safe cell (%d,%d)\n", c % 32, c / 32); click(c % 32, c / 32, 0); probe(0, 0);
    c = findCell(0, 0); printf("step flag a safe cell (%d,%d) (a wrong flag)\n", c % 32, c / 32); click(c % 32, c / 32, 1); probe(0, 0);
    c = findCell(1, 0); printf("step flag a mine (%d,%d)\n", c % 32, c / 32); click(c % 32, c / 32, 1); probe(1, 0);
    c = findCell(1, 0); printf("step dig a mine (%d,%d): loss\n", c % 32, c / 32); click(c % 32, c / 32, 0); probe(1, 0);
    c = findCell(0, 0); printf("step click after the loss (%d,%d)\n", c % 32, c / 32); click(c % 32, c / 32, 0); probe(0, 0);
    level("New"); printf("step New after loss\n"); probe(0, 0);
    printf("step win: dig every safe cell\n");
    for (n = 0; n < 200 && (c = findCell(0, 0)) >= 0; n++) { click(c % 32, c / 32, 0); probe(0, 1); }
    probe(0, 0);
    level("Intermediate"); printf("step intermediate\n"); probe(0, 0);
    for (k = 0; k < 3; k++) { c = findCell(0, 7 * k); click(c % 32, c / 32, 0); } probe(0, 0);
    level("Expert"); printf("step expert\n"); probe(0, 0);
    for (k = 0; k < 3; k++) { c = findCell(0, 31 * k); click(c % 32, c / 32, 0); } probe(0, 0);
    t0 = GetTickCount(); for (k = 0; k < 100; k++) probe(0, 1); printf("log 100 reads of the expert board: %lu ms\n", GetTickCount() - t0);
    level("Beginner");
}

int main(int argc, char **argv)
{
    DWORD pid = 0;
    int i;
    game = FindWindowA("Minesweeper", NULL);
    if (!game && argc > 1 && !strcmp(argv[1], "--scenario")) {
        WinExec("winmine.exe", SW_SHOWNORMAL);
        for (i = 0; i < 100 && !(game = FindWindowA("Minesweeper", NULL)); i++) Sleep(100);
    }
    if (!game) { printf("log no mine game window (class Minesweeper)\n"); return 1; }
    GetWindowThreadProcessId(game, &pid);
    proc = OpenProcess(PROCESS_VM_READ, FALSE, pid);
    if (!proc) { printf("log OpenProcess failed %lu\n", GetLastError()); return 1; }
    if (argc > 1 && !strcmp(argv[1], "--scenario")) scenario();
    else probe(argc > 1 && !strcmp(argv[1], "--dump"), 0);
    CloseHandle(proc);
    return 0;
}

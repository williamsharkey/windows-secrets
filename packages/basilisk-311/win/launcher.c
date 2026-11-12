/* BASILISK 3.11.exe - starts the local edition with no console window.
   Runs runtime\python\pythonw.exe -I app\basilisk.py from the folder this .exe is in.
   zig cc -target x86_64-windows-gnu -mwindows -Os launcher.c launcher.rc -o "BASILISK 3.11.exe" */
#include <windows.h>

int WINAPI wWinMain(HINSTANCE hi, HINSTANCE prev, LPWSTR args, int show)
{
    WCHAR dir[MAX_PATH], cmd[3 * MAX_PATH + 512], *p;
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    GetModuleFileNameW(NULL, dir, MAX_PATH);
    p = wcsrchr(dir, L'\\');
    if (p) *p = 0;
    wsprintfW(cmd, L"\"%s\\runtime\\python\\pythonw.exe\" -I \"%s\\app\\basilisk.py\" %s", dir, dir, args ? args : L"");
    ZeroMemory(&si, sizeof si);
    si.cb = sizeof si;
    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        MessageBoxW(NULL, L"BASILISK 3.11 could not start its runtime. Is the folder complete?", L"BASILISK 3.11", MB_ICONERROR);
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}

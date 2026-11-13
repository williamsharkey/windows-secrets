/* BASILISK.exe - the Windows face of BASILISK: our name and icon, no console. It runs the bundled
 * Python in this very process (python312.dll) on app\basilisk.py.
 *   x86_64-w64-mingw32-windres basilisk-win.rc -O coff -o res.o
 *   x86_64-w64-mingw32-gcc -O2 -municode -mwindows basilisk-win.c res.o -o BASILISK.exe
 */
#include <windows.h>
#include <wchar.h>

typedef int (*PyMainFn)(int, wchar_t **);

static void fail(const wchar_t *what)
{
    wchar_t m[700];
    swprintf(m, 700, L"BASILISK XP could not start: %ls\n\nThe folder may be incomplete; unzip BASILISK XP again.", what);
    MessageBoxW(NULL, m, L"BASILISK XP", MB_ICONERROR);
}

int WINAPI wWinMain(HINSTANCE hi, HINSTANCE hp, LPWSTR cmd, int show)
{
    wchar_t dir[MAX_PATH], py[MAX_PATH], dll[MAX_PATH], path[MAX_PATH * 3], script[MAX_PATH];
    wchar_t *argv[3];
    HMODULE h;
    PyMainFn py_main;
    (void)hi; (void)hp; (void)cmd; (void)show;
    GetModuleFileNameW(NULL, dir, MAX_PATH);
    *wcsrchr(dir, L'\\') = 0;
    swprintf(py, MAX_PATH, L"%ls\\runtime\\python", dir);
    swprintf(dll, MAX_PATH, L"%ls\\python312.dll", py);
    swprintf(path, MAX_PATH * 3, L"%ls\\runtime\\site;%ls\\app", dir, dir);
    swprintf(script, MAX_PATH, L"%ls\\app\\basilisk.py", dir);
    SetEnvironmentVariableW(L"PYTHONHOME", py);
    SetEnvironmentVariableW(L"PYTHONPATH", path);
    SetEnvironmentVariableW(L"PYTHONNOUSERSITE", L"1");
    SetEnvironmentVariableW(L"BASILISK_BUNDLE", dir);
    SetDllDirectoryW(py);
    /* one taskbar identity for the app (pins and groups as BASILISK, not as Python) */
    {
        typedef HRESULT (WINAPI *SetId)(PCWSTR);
        HMODULE sh = LoadLibraryW(L"shell32.dll");
        SetId f = sh ? (SetId)GetProcAddress(sh, "SetCurrentProcessExplicitAppUserModelID") : NULL;
        if (f) f(L"Basilisk.BASILISK-XP");
    }
    h = LoadLibraryW(dll);
    if (!h) { fail(L"runtime\\python\\python312.dll is missing."); return 1; }
    py_main = (PyMainFn)GetProcAddress(h, "Py_Main");
    if (!py_main) { fail(L"python312.dll has no Py_Main."); return 1; }
    argv[0] = L"BASILISK XP";
    argv[1] = script;
    argv[2] = NULL;
    return py_main(2, argv);
}

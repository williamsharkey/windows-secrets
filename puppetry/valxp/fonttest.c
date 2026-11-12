/* draw a ♥ sample in candidate fonts, to see which XP fonts carry the glyph */
#include <windows.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(h, &ps); int i;
        static const WCHAR *f[] = {L"Palatino Linotype", L"Comic Sans MS", L"Lucida Console", L"Georgia", L"Trebuchet MS", L"Tahoma", L"Arial", L"Lucida Sans Unicode", L"Times New Roman", L"Franklin Gothic Medium", L"Sylfaen", L"Verdana"};
        for (i = 0; i < 12; i++) {
            HFONT fo = CreateFontW(-26, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, CLEARTYPE_QUALITY, 0, f[i]);
            HGDIOBJ o = SelectObject(dc, fo); WCHAR b[128];
            wsprintfW(b, L"%s: \x2665 \x2764 caf\x00E9 \x00BFQu\x00E9? \x041F\x0440\x0438 Be mine", f[i]);
            TextOutW(dc, 10, 10 + i * 40, b, lstrlenW(b));
            SelectObject(dc, o); DeleteObject(fo);
        }
        EndPaint(h, &ps); return 0;
    }
    if (m == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProcW(h, m, w, l);
}
int WINAPI WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR c, int s)
{
    WNDCLASSW wc = {0}; MSG m; (void)hp; (void)c; (void)s;
    wc.lpfnWndProc = wp; wc.hInstance = hi; wc.lpszClassName = L"ft"; wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    RegisterClassW(&wc);
    CreateWindowW(L"ft", L"fonts", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 1000, 540, 0, 0, hi, 0);
    while (GetMessageW(&m, 0, 0, 0) > 0) DispatchMessageW(&m);
    return 0;
}

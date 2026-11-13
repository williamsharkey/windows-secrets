/* SYNHOOK.DLL - while BASILISK 16 rebuilds its recorders, Sound Recorder's own dialogs (Insert File, Mix with
   File, "save changes?", "delete before ... ?") are answered for it, off screen: a system CBT hook. */
#include <windows.h>
#include <string.h>

static HHOOK hook;
static HINSTANCE self;
static BOOL active;
static char pending[128];      /* the file name for the next Open-style dialog */
static int answered;

static BOOL has_button(HWND d, int id) { return GetDlgItem(d, id) != NULL; }

LRESULT FAR PASCAL __loadds __export CbtProc(int code, WPARAM w, LPARAM l)
{
    if (active && code == HCBT_CREATEWND) {
        CBT_CREATEWND FAR *c = (CBT_CREATEWND FAR *)l;
        char cls[16];
        GetClassName((HWND)w, cls, sizeof cls);
        if (!lstrcmp(cls, "#32770")) { c->lpcs->x = -3000; c->lpcs->y = -3000; }
    }
    if (active && code == HCBT_ACTIVATE) {
        HWND d = (HWND)w;
        char cls[16];
        GetClassName(d, cls, sizeof cls);
        if (!lstrcmp(cls, "#32770")) {
            SetWindowPos(d, NULL, -3000, -3000, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
            if (GetDlgItem(d, 1152)) {                          /* a file dialog: our file, OK */
                SetDlgItemText(d, 1152, pending);
                PostMessage(d, WM_COMMAND, IDOK, MAKELPARAM(GetDlgItem(d, IDOK), BN_CLICKED));
            } else if (has_button(d, IDNO)) {                   /* "save changes?" -> No; "delete ...?" -> Yes */
                char t[200]; HWND s;
                t[0] = 0;
                for (s = GetWindow(d, GW_CHILD); s; s = GetWindow(s, GW_HWNDNEXT)) {
                    GetClassName(s, cls, sizeof cls);
                    if (!lstrcmpi(cls, "Static")) { GetWindowText(s, t, sizeof t); if (lstrlen(t) > 8) break; }
                }
                PostMessage(d, WM_COMMAND, (_fstrstr(t, "save") || _fstrstr(t, "lose")) ? (_fstrstr(t, "lose") ? IDYES : IDNO) : IDYES, 0L);
            } else if (has_button(d, IDOK)) {
                PostMessage(d, WM_COMMAND, IDOK, 0L);           /* an error box: OK (the step is skipped) */
            } else if (has_button(d, IDYES)) PostMessage(d, WM_COMMAND, IDYES, 0L);
            answered++;
        }
    }
    return CallNextHookEx(hook, code, w, l);
}

void FAR PASCAL __loadds __export HookActive(BOOL on) { active = on; }
void FAR PASCAL __loadds __export HookPending(LPCSTR path) { lstrcpyn(pending, path, sizeof pending); }
int FAR PASCAL __loadds __export HookAnswered(void) { return answered; }
BOOL FAR PASCAL __loadds __export HookInstall(BOOL on)
{
    if (on && !hook) hook = SetWindowsHookEx(WH_CBT, (HOOKPROC)CbtProc, self, NULL);
    if (!on && hook) { UnhookWindowsHookEx(hook); hook = NULL; }
    return hook != NULL;
}

int FAR PASCAL LibMain(HINSTANCE hi, WORD ds, WORD heap, LPSTR cmd) { self = hi; return 1; }
int FAR PASCAL __export WEP(int x) { return 1; }

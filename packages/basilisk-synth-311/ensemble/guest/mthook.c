/* MTHOOK.DLL - the multitimbral experiment: strips Sound Recorders of what a lane does not need, in their own task.
   Windows 3.11's DestroyWindow refuses another task's windows, so the strip runs inside Sound Recorder: a system
   WH_GETMESSAGE hook sees our registered message posted to its window and destroys the children there.
   A CBT hook can also veto the creation of controls as the dialog is made (MtVeto). */
#include <windows.h>

static HHOOK hMsg, hCbt;
static HINSTANCE self;
static UINT msgStrip;
static WORD vetoMask;   /* bit k: veto control id 200+k of a "SoundRec" window */
static int nDestroyed, nVetoed;

static void strip_in_task(HWND w, WORD mask)
{
    HWND c, nx;
    if (mask & 0x8000) {   /* keep mode: bit k keeps control 200+k; the menu, the frames and the title go */
        HMENU m = GetMenu(w); if (m) { SetMenu(w, NULL); DestroyMenu(m); }
        SetWindowText(w, "");
        {   /* its OLE server window (SrvrWndClass) is shown at 0, 0 when the recorder starts shown: hidden here, in its task */
            HWND x; WORD hi = GetWindowWord(w, GWW_HINSTANCE); char cls[16];
            for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT))
                if (x != w && GetWindowWord(x, GWW_HINSTANCE) == hi) { GetClassName(x, cls, sizeof cls); if (!lstrcmp(cls, "SrvrWndClass")) ShowWindow(x, SW_HIDE); }
        }
        for (c = GetWindow(w, GW_CHILD); c; c = nx) {
            int id = GetDlgCtrlID(c);
            nx = GetWindow(c, GW_HWNDNEXT);
            if (id >= 200 && id < 215 && (mask >> (id - 200)) & 1) continue;
            DestroyWindow(c); nDestroyed++;
        }
        return;
    }
    if (mask & 2) { HMENU m = GetMenu(w); if (m) { SetMenu(w, NULL); DestroyMenu(m); } }
    for (c = GetWindow(w, GW_CHILD); c; c = nx) {
        int id = GetDlgCtrlID(c);
        nx = GetWindow(c, GW_HWNDNEXT);
        if (id == 203 && !(mask & 4)) continue;            /* the wave display (one per lane is shown) */
        if ((id == 200 || id == 202) && !(mask & 32)) continue;   /* status and length: read by the synth program (32: those too) */
        if (id == 204 && (mask & 16)) continue;            /* the seek bar: v3 W windows seek with it */
        if (!(mask & 1) && id != 203) continue;
        DestroyWindow(c); nDestroyed++;
    }
}
LRESULT FAR PASCAL __loadds __export MsgProc(int code, WPARAM w, LPARAM l)
{
    if (code >= 0 && msgStrip) {
        MSG FAR *m = (MSG FAR *)l;
        if (m->message == msgStrip) { strip_in_task(m->hwnd, (WORD)m->wParam); m->message = WM_NULL; }
    }
    return CallNextHookEx(hMsg, code, w, l);
}
LRESULT FAR PASCAL __loadds __export CbtProc(int code, WPARAM w, LPARAM l)
{
    if (code == HCBT_CREATEWND && vetoMask) {
        CBT_CREATEWND FAR *c = (CBT_CREATEWND FAR *)l;
        HWND parent = c->lpcs->hwndParent; char cls[16];
        int id = (int)(UINT)c->lpcs->hMenu;
        if (parent && (c->lpcs->style & WS_CHILD) && id >= 200 && id < 216 && (vetoMask >> (id - 200)) & 1) {
            GetClassName(parent, cls, sizeof cls);
            if (!lstrcmp(cls, "SoundRec")) { nVetoed++; return 1; }
        }
    }
    return CallNextHookEx(hCbt, code, w, l);
}
void FAR PASCAL __loadds __export MtVeto(WORD mask) { vetoMask = mask; }
int FAR PASCAL __loadds __export MtCount(int which) { return which ? nVetoed : nDestroyed; }
UINT FAR PASCAL __loadds __export MtInstall(void)
{
    if (!msgStrip) msgStrip = RegisterWindowMessage("MtStrip");
    if (!hMsg) hMsg = SetWindowsHookEx(WH_GETMESSAGE, (HOOKPROC)MsgProc, self, NULL);
    if (!hCbt) hCbt = SetWindowsHookEx(WH_CBT, (HOOKPROC)CbtProc, self, NULL);
    return hMsg && hCbt ? msgStrip : 0;
}
int FAR PASCAL LibMain(HINSTANCE hi, WORD ds, WORD heap, LPSTR cmd) { self = hi; return 1; }
int FAR PASCAL __export WEP(int x) { if (hMsg) UnhookWindowsHookEx(hMsg); if (hCbt) UnhookWindowsHookEx(hCbt); return 1; }

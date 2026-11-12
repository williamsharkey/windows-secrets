/* link.h - BASILISK 3.11 in the browser: the cable to the page is two files on C:
     C:\B3\TOJS.TXT    Windows appends <type><a>[\x1f<b>[\x1f<c>]]\x04 ; the page reads what's new
     C:\B3\TOWIN.TXT   the page rewrites it with everything it has ever sent; Windows reads from where it
                       stopped last time
   (js-dos's DOSBox-X has serial ports but no way to feed one from the page; files on its C: drive are
   shared with the page directly, so the "cable" is a pair of files, polled every 40 ms.) */
#define EOT 4
#define SEP 0x1F

static long linkIn;                      /* how much of TOWIN.TXT has been handled */
static char linkBuf[8200];
static int linkN;

static void LinkPut(char type, LPCSTR a, LPCSTR b, LPCSTR c)
{
    OFSTRUCT of;
    HFILE f;
    static char sep[2] = { SEP, 0 }, t[2], e[2] = { EOT, 0 };
    f = OpenFile("C:\\B3\\TOJS.TXT", &of, OF_WRITE | OF_SHARE_DENY_NONE);
    if (f == HFILE_ERROR) f = OpenFile("C:\\B3\\TOJS.TXT", &of, OF_CREATE | OF_WRITE);
    if (f == HFILE_ERROR) return;
    _llseek(f, 0L, 2);
    t[0] = type;
    _lwrite(f, t, 1);
    if (a) _lwrite(f, a, lstrlen(a));
    if (b) { _lwrite(f, sep, 1); _lwrite(f, b, lstrlen(b)); }
    if (c) { _lwrite(f, sep, 1); _lwrite(f, c, lstrlen(c)); }
    _lwrite(f, e, 1);
    _lclose(f);
}

/* read what's new in TOWIN.TXT and hand each complete message to h */
static void LinkPoll(void (*h)(char, LPSTR))
{
    OFSTRUCT of;
    HFILE f = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_READ | OF_SHARE_DENY_NONE);
    int n, i;
    if (f == HFILE_ERROR) return;
    _llseek(f, linkIn + linkN, 0);
    n = _lread(f, linkBuf + linkN, sizeof linkBuf - 1 - linkN);
    _lclose(f);
    if (n <= 0) return;
    linkN += n;
    for (;;) {
        for (i = 0; i < linkN && linkBuf[i] != EOT; i++) ;
        if (i >= linkN) break;
        linkBuf[i] = 0;
        {
            static char msg[8200];
            char t = linkBuf[0];
            memcpy(msg, linkBuf + 1, i);
            memmove(linkBuf, linkBuf + i + 1, linkN - i - 1);
            linkN -= i + 1;
            linkIn += i + 1;
            h(t, msg);
        }
    }
    if (linkN >= (int)sizeof linkBuf - 1) { linkIn += linkN; linkN = 0; }    /* a runaway message: drop it */
}

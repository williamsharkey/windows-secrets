# BASILISK 3.11, the suite

One Win16 client for both 3.11 stages:

- https://williamsharkey.com/basilisk-31.html (server: DOSBox-X on sharkey-server, `puppetry/w31`)
- https://williamsharkey.com/basilisk-31-browser.html (js-dos in the visitor's browser, `puppetry/w31b`)

`BASILISK.C` + `PARTS.C` (two files because Notepad holds about 45 KB and the build pours the source into
Notepad) and `B3BOOT.C` (the build: pour, Save As, `wcl`, run). Both pick their link at run time: if
`C:\B3\TOWIN.TXT` exists it's the browser's file mailbox, otherwise COM2 at 19200 baud.

## The cards

Windows 3.1 has no tab control, so Cardfile is the tab strip. BASILISK writes `C:\B3\TABS.CRD` (Cardfile's MGC
format: index lines "1 Chat" ... "5 Settings", sorted, then the bodies), opens it in Cardfile, and adopts the
`Card` window into a box in the right-hand column. A click on a header (or Alt+1..5, sent as `J n`, which posts
PgDn to Cardfile until the right card is in front) changes card; the front card is recognised by its body's first
line, and the left pane shows that card's part:

| Card | Part | Notes |
|---|---|---|
| 1 Chat | Notepad's edit (browser) / Terminal (server); Notepad's Find dialog as the input bar (browser) | as before |
| 2 Plan | a second Notepad's edit | `L` text from the `todo_write` tool; permission prompts are a real `MessageBox` (Yes once, No always, Cancel deny) |
| 3 Files | File Manager's MDIClient + status bar, opened on `C:\B3\WORK` | Ins (`@`) reads the selection from File Manager's own Copy dialog ("From:", id 102) |
| 4 Usage | our window: three gauges drawn like 3.1 Setup's (blue fill, inverted percentage) | `N ctx|max|day|daycap|month|monthcap|text` ($ in 1e-5) |
| 5 Settings | Control Panel's Mouse dialog (`CONTROL.EXE MAIN.CPL Mouse`), its controls moved onto our pane | tracking speed = effort (low..max), double-click speed = answer length, Swap = ask before commands, Mouse Trails (enabled) = Sonnet 5.5; sends `E effort|length|ask|model` |

Clock (analog, menu removed) and Calculator's display (id 414, the bill) stay in the column.

## Link messages added for the suite

host -> Windows: `J n` card, `L text` plan, `N ...` gauges, `I id<SEP>what` ask, `! once|always|deny` answer the
open box, `M x|y|b|down` mouse, `w n` wheel, `@` mention, `Q` window-tree dump to `C:\B3\SPY.TXT`.
Windows -> host: `J name` card in front, `E effort|length|ask|model`, `I id<SEP>asking|once|always|deny`,
`@ @NAME ` (server version; the browser client inserts it into the Find box itself), `S step ms` assembly steps.

## The mouse

Neither stage has an absolute-pointer driver in Windows 3.11 (xdotool into DOSBox-X's X window moves nothing; js-dos
would need relative motion). So the pages send the pointer over the link and BASILISK.EXE does it:
`SetCursorPos`, then `WM_LBUTTONDOWN/UP/DBLCLK`, `WM_RBUTTON*` posted to `WindowFromPoint`'s client area
(capture kept between down and up). Scroll bars are driven by their messages (`WM_HSCROLL`/`WM_VSCROLL` with
LINE/PAGE/THUMBTRACK/THUMBPOSITION computed from the click), since a scroll bar's tracking loop polls the real
button state. Non-client clicks (captions, menus) are not forwarded.

## The overture

About 6 s, one change at a time (measured in the lab: host 0.8 s, Find 1.3, Clock 1.8, Calculator 0.9,
Cardfile 0.9, Plan 0.7, File Manager 1.3, Control Panel 0.8): Notepad/Terminal glides to full screen; Find sheds
its controls one by one and glides to the bottom; Clock glides to the column; Calculator's display is lifted out and
glides under it; Cardfile opens the five cards and glides so its front card lands in the column, then gives up the
cards; Notepad, File Manager and the Mouse dialog appear, shrink toward the cards and go behind them. Each move
repaints what it uncovers (`UpdateWindow` on the desktop and host every frame), and keys are posted with `Pump` so
no Win16 queue (8 messages) overflows.

## Lab

`lab.sh prog.c [wait]` builds and runs a program in a lab copy of the 3.11 machine on sharkey (display :61,
`/root/snap/dosbox-x/common/w31s`, transient units `w31lab-x`/`w31lab-dbx`), screenshots it and fetches `SPY.TXT`;
`/root/w31/labsend MSG...` appends link messages to the lab's mailbox (fields separated by `^`). `labboot.sh` runs
the whole in-Windows build there; `mkbrowser.sh` makes the browser bundle (`/root/w31b/suite/www/w31.jsdos`).

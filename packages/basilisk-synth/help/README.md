BASILISK SYNTH / BASILISK 16 Help
=================================

Vintage Windows Help files for both instruments, opened by each guest's own viewer: WINHELP.EXE on Windows 3.11
and winhlp32.exe on Windows XP. No Microsoft tool is used to build them.

| File | What it is |
|---|---|
| `help.txt` | The one source for both help files. Lines starting `:xp ` or `:311 ` are only in that edition. The format is described at the top of `mkrtf.py`. |
| `mkrtf.py` | Turns help.txt into `bsynth.rtf` / `basil16.rtf` (WinHelp authoring RTF, as HC31 reads it), `helpmap.txt` ([MAP]) and `helpids.h`. |
| `hlpc.py` | A WinHelp 3.1 compiler (format 1.21, LZ77 topic blocks): topics, jumps, popups, keywords (Search), browse sequence, [CONFIG] macros and [MAP] context numbers. `hlpc.py --dump FILE.HLP` prints a help file as text. |
| `bsynth.hpj`, `basil16.hpj` | The help projects. |
| `build.sh` | Builds `out/BSYNTH.HLP` (XP) and `out/BASIL16.HLP` (3.11). `out/` is git-ignored. |
| `helpids.h` | Context numbers for `WinHelp(hwnd, file, HELP_CONTEXT, HELPID_...)`, the same in both files. |
| `install/install311.py` | Installs BASIL16.HLP on a WfW 3.11 C: drive folder, with a Program Manager group. |
| `install/helpinst.bat`, `install/helpicon.vbs` | Install BSYNTH.HLP inside XP, with a desktop shortcut. |

Build: `sh build.sh` (Python 3 only). The same sources give the same bytes (SOURCE_DATE_EPOCH is the last commit).

What was checked
----------------
In the real viewers, on private copies of both machines:
- **WINHELP.EXE (WfW 3.11):** every topic, with Page Down on the long ones. Also the Contents, Search (keyword list,
  Show Topics, Go To), glossary popups, the browse buttons and Back. The help was opened from the Program Manager item
  that `install311.py` made.
- **winhlp32.exe (XP):** the same, opened through the desktop shortcut that `helpinst.bat` made.

hlpc fix from this round: paragraphs with the same formatting now share one topic record, separated by 0x82, as
HC31 does. This is smaller and is what WINHELP.EXE expects.

Integration (for the plugin lanes)
==================================
The help topics already describe the items below, so the help is only true once these exist.

1. Build the help files
-----------------------
Run `sh packages/basilisk-synth/help/build.sh` before making the machine. It needs only Python 3.

2. Windows 3.11 (BASILISK 16)
-----------------------------
In `packages/basilisk-synth-311/tools/make_machine.py`, after the drive is copied and `BS\SYNTH.EXE` is in place,
and before `drive.zip` is written:

    python3 packages/basilisk-synth/help/install/install311.py <drive folder> packages/basilisk-synth/help/out/BASIL16.HLP

This does three things:
- copies the help to `C:\BS\BASIL16.HLP`;
- writes `C:\WINDOWS\BASIL16.GRP`, a "BASILISK 16" group whose item "BASILISK 16 Help" runs
  `WINHELP.EXE C:\BS\BASIL16.HLP`. Program Manager draws WINHELP.EXE's own icon;
- adds the group to `PROGMAN.INI` (`[Groups]` and `Order=`).

Running it again on the same drive is safe.

In `guest/synth.c`:
- **Minimize:** give hMain a Minimize button. Change `WS_POPUP | WS_CAPTION | WS_CLIPCHILDREN` to add
  `WS_SYSMENU | WS_MINIMIZEBOX`, and give the class an icon. While the synth is iconic, the recorders it owns must stay
  hidden; on restore, put them back. Program Manager is minimized at start, so the person double-clicks it to reach
  the group.
- **F1:** on WM_KEYDOWN VK_F1 (or via a message hook, because the recorders have focus), call
  `WinHelp(hMain, "C:\\BS\\BASIL16.HLP", HELP_CONTENTS, 0L)`. For a topic, use `HELP_CONTEXT, HELPID_KEYBOARD` and so on
  from `help/helpids.h`. On exit, call `WinHelp(hMain, "C:\\BS\\BASIL16.HLP", HELP_QUIT, 0L)`.

3. Windows XP (BASILISK SYNTH)
------------------------------
When the XP disk is prepared (the same session in which `guest/prep.bat` runs, before the machine state is saved),
put `out/BSYNTH.HLP`, `install/helpinst.bat` and `install/helpicon.vbs` in one folder the guest can read. Then run
`HELPINST.BAT` from that folder. It:
- copies `BSYNTH.HLP` to `C:\synth\BSYNTH.HLP`;
- creates `%USERPROFILE%\Desktop\BASILISK SYNTH Help.lnk`, which runs `%SystemRoot%\winhlp32.exe C:\synth\BSYNTH.HLP`
  with winhlp32's icon. It uses Windows Script Host, which comes with XP.

It prints `help installed`, or `help NOT installed` on failure. Running it again is safe.

In `guest/synth.c`:
- **Help menu:** add "Help &Contents\tF1" above "About BASILISK SYNTH". It calls
  `WinHelpA(win, "C:\\synth\\BSYNTH.HLP", HELP_FINDER, 0)`. HELP_CONTENTS works too; the file has no .CNT, so both
  open the Contents topic.
- **F1:** the same call. For a topic, use `HELP_CONTEXT, HELPID_...` from `help/helpids.h`.
- **File > Minimize:** the window is `WS_POPUP` with no caption, so it needs a menu command: `ShowWindow(win, SW_MINIMIZE)`
  and `ShowWindow(FindWindowA("Shell_TrayWnd", NULL), SW_SHOW)`. On restore (WM_SIZE SIZE_RESTORED or WM_ACTIVATE),
  hide the taskbar again, as EV_TRAY does. The window needs `WS_EX_APPWINDOW` (or a caption) so the taskbar shows a
  button for it. While minimized, the sixteen sndrec32 windows must be hidden too, or they cover the desktop.
- **The host:** while the person uses Windows, the plugin keeps playing. The machine already sleeps after 4 quiet
  seconds only when the editor is closed, so nothing changes there.

4. Wording the help relies on
-----------------------------
If a lane names these differently, change `help.txt` and rebuild:

- XP:
  - File > Minimize
  - Help > Help Contents (F1)
  - desktop icon "BASILISK SYNTH Help"
  - taskbar button "BASILISK SYNTH"
- 3.11:
  - the title bar's Minimize button
  - F1
  - group "BASILISK 16", item "BASILISK 16 Help"
- Both: keyboard Hold, PC keys / Keys, Bend, Mod, the four macros, and the preset counts (39 XP, 71 on 3.11), all as
  in the main READMEs on 2026-11-13.

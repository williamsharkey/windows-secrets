BASILISK 3.11, local edition
============================

Windows for Workgroups 3.11, in a window of its own, with Claude Code built into it: Terminal, Clock, Cardfile
and Calculator assembled into one program by a 16-bit C file that Windows compiled itself. Claude answers with
YOUR Anthropic account, at whatever model and effort you like. Everything runs on this computer.

START
  Windows  Unzip, open the "BASILISK 3.11" folder, double-click "BASILISK 3.11.exe". (SmartScreen may say
           "Windows protected your PC": More info > Run anyway.) It adds itself to the Start menu.
  macOS    Open the .dmg, drag BASILISK 3.11 to Applications. The first time: right-click it > Open > Open
           (macOS 15+: System Settings > Privacy & Security > Open Anyway). It is not notarized.
  Linux    chmod +x BASILISK-3.11-linux-x64.AppImage and run it. Needs a desktop (X11 or Wayland) and
           glibc 2.35+ (Ubuntu 22.04, Debian 12, Fedora 36 or newer).

The first start shows the build: Windows boots, pours BASILISK.C into Notepad, saves it, compiles it with
Open Watcom and assembles the client (about half a minute). Later starts open straight into BASILISK.

SIGN IN
  Copy your Anthropic API key (https://console.anthropic.com > API keys), then type  /login  in BASILISK.
  The key is read from your clipboard (never typed, never shown), checked with a free call, and saved on
  this computer, readable only by your account. Or sign in with the Anthropic CLI (ant auth login) or set
  ANTHROPIC_API_KEY, then /login.

WHO PAYS
  You do: every request goes from this computer to api.anthropic.com and is billed to your Anthropic API
  account at the published prices. A Claude.ai Pro/Max plan does not cover API use. BASILISK has no caps;
  the bill so far is on the Calculator and in /cost. Set a spend limit in the Console if you want one.
    haiku  claude-haiku-5-5    $0.10 / $0.50 per million tokens in / out  (default; a small C program < 1 cent)
    sonnet claude-sonnet-5-5   $2 / $10
    opus   claude-opus-5-5     $4 / $20
    fable  claude-fable-5-2    $8 / $40

INSIDE
  Type in the line at the bottom; Enter sends, Esc interrupts, Up/Down recall, PgUp/PgDn scroll, Alt+Enter full screen.
  /model haiku|sonnet|opus|fable   /effort low|medium|high|xhigh|max   /cost  /clear
  /login  /logout  /settings  /intro on|off  /size auto|1x|1.5x|2x|fullscreen  /files  /reset  /help
  D: is a folder on your computer (Documents/BASILISK 3.11), shared both ways. C:\B3\WORK is kept too.
  Closing the window quits.

WHERE THINGS LIVE
  Settings, key, C: and logs: %APPDATA%\BASILISK311 (Windows), ~/Library/Application Support/BASILISK311
  (macOS), ~/.config/basilisk311 (Linux). Delete that folder to forget everything.

CREDITS AND LICENCES
  Windows for Workgroups 3.11 (c) 1993 Microsoft, included as part of an art project.
  The engine is DOSBox-X (GPLv2; engine/COPYING.txt), an official build whose window-title format string is
  byte-patched so the title reads BASILISK 3.11 (engine/SOURCE.txt). Source: https://github.com/joncampbell123/dosbox-x
  (the matching source tarball is attached to this release). Open Watcom (Sybase Open Watcom Public License).
  Python from python-build-standalone (PSF), with anthropic (MIT), aiohttp (Apache 2.0) and their dependencies.
  Everything else: https://github.com/williamsharkey/windows-secrets (packages/basilisk-311, puppetry/w31).

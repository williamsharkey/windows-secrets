BASILISK - Claude Code in Windows XP, as a program on your computer
===================================================================

BASILISK III is a Claude Code client that lives in Windows XP: it was built from Notepad, Find, Date and
Time and Calculator parts, and it reads and writes files in C:\b3\work, runs commands, compiles C with tcc,
keeps a plan and shows what everything costs. This is the same suite as on williamsharkey.com, as one
program for Windows 11, macOS and Linux, on your own Claude account: no queue, no time limit, any model,
any effort.

It opens in its own window, ready in a couple of seconds: XP is resumed from a snapshot taken just after
BASILISK built itself. (Turn on "Intro" in settings to watch the build every time.)

Download
--------
https://github.com/williamsharkey/windows-secrets/releases/tag/basilisk-xp-v1.0.0

  BASILISK-XP-windows-x64.zip       Windows 10/11 (64-bit). Unzip anywhere, run BASILISK XP.exe.
  BASILISK-XP-macos-arm64.dmg       macOS 11+ on Apple Silicon. Drag BASILISK XP to Applications.
  BASILISK-XP-macos-x86_64.dmg      macOS 10.15+ on Intel (tested under Rosetta only).
  BASILISK-XP-linux-x64.AppImage    Linux x86-64. chmod +x, run.

The Windows XP machine (about 790 MB) is downloaded once on the first start, checked against its SHA-256
and unpacked (about 930 MB on disk). After that BASILISK starts in 2-3 seconds.

Unsigned builds: none of these are signed by Microsoft or Apple.
  Windows   SmartScreen may say "Windows protected your PC": click "More info", then "Run anyway".
  macOS     the first time, right-click BASILISK in Applications and choose Open, then Open again (or run
            xattr -dr com.apple.quarantine /Applications/BASILISK XP.app in Terminal).
  Linux     AppImages need FUSE 2 (Ubuntu 22.04+: sudo apt install libfuse2), or run it with
            --appimage-extract-and-run.

Signing in
----------
BASILISK uses your own Claude API access. The first time, its settings open by themselves:
  - paste an Anthropic API key (platform.claude.com > API keys) and press Save key. It is checked with
    one tiny request and stored only on this computer, readable by your user alone, or
  - run `ant auth login` (the Anthropic CLI) and start BASILISK again, or set ANTHROPIC_API_KEY.

Billing: every turn is a real Claude API call, billed by Anthropic to that account at API prices. The
dollar figures BASILISK shows are its own estimate from list prices (Haiku $0.10/$0.50, Sonnet $2/$10,
Opus $4/$20, Fable $8/$40 per million input/output tokens); your Anthropic console has the bill. There is
no spending cap, so watch the meter with Opus or Fable at high effort.

Using it
--------
  Settings      Ctrl+Alt+S (macOS: Cmd+,), or the "BASILISK XP.app settings..." button on the Settings tab
  Full screen   F11 (macOS: Ctrl+Cmd+F)
  Model/effort  the Settings tab in XP, /model haiku|sonnet|opus|fable and /effort low...max in Chat, or
                the app's settings. Sonnet, Opus and Fable use Anthropic's server-side fallback.
  Quit          close the window: keep the machine as it is for next time (windows, files, the
                conversation), or start fresh. "On quit" in settings remembers your choice.
  Reset machine back to the freshly built BASILISK.
  Display       "Fit window" (smooth) or "Sharp pixels" (whole-number scaling).

Settings, logs and the machine:
  Windows  %APPDATA%\BASILISK (settings, key)  and  %LOCALAPPDATA%\BASILISK (machine, logs)
  macOS    ~/Library/Application Support/BASILISK
  Linux    ~/.config/basilisk  and  ~/.local/share/basilisk
Uninstall: delete the app and those folders (Windows: also the Start menu entry BASILISK).

Speed
-----
XP is emulated by QEMU (TCG) on all three systems: a Mac's or Windows PC's hardware virtualization cannot
resume a snapshot taken under emulation, and on Apple Silicon there is no x86 hardware at all. It is
quick enough for BASILISK. On Linux with KVM, a machine you keep resumes with KVM, and Intro boots with KVM.

Networking and safety
---------------------
Claude runs commands inside XP, not on your computer. XP reaches BASILISK at 10.0.2.2:8765 through QEMU's
user networking. On macOS and Linux that is all it can reach. On Windows QEMU cannot restrict it that way,
so XP has ordinary NAT: it can reach the internet and services listening on your computer's 127.0.0.1, like
any QEMU virtual machine. BASILISK's port listens on 127.0.0.1 only and refuses requests made by web pages.
XP has no sound card (its AC97 driver hangs when resumed from a snapshot).

What's inside
-------------
  app/basilisk.py      the program: first-run download, snapshots, start and quit
  app/ui.py            the window (pygame-ce / SDL2): XP's screen, settings, loading and quit cards
  app/vnc.py           reads QEMU's screen over a private local socket, sends keys (PC scancodes) and mouse
  app/machine.py       QEMU's command line, QMP control, snapshots
  app/server_local.py  the host side of the client: the Claude tool loop (made from puppetry/b3/server.py)
  runtime/             Python 3.12 (python-build-standalone) with aiohttp, anthropic, pygame-ce
  qemu/                QEMU, trimmed to the i386 PC: Windows 11.1 (Stefan Weil's build), macOS 11.1
                       (Homebrew bottles, relocated), Linux 6.2 (Ubuntu 22.04, with its own C library)

Windows XP is Microsoft's; the machine is the one that runs BASILISK III on williamsharkey.com. QEMU is GPL
v2 (source: qemu.org). Python is PSF-licensed; pygame-ce and SDL are LGPL/zlib; Inter is OFL.

Building (maintainers)
----------------------
  tools/make_local.py     regenerate app/server_local.py and guest/basilisk3.c from puppetry/b3
  guest image             term.qcow2 with guest/basilisk3.c in C:\p and a Startup entry running
                          `C:\p\puppet.exe b3`, shut down cleanly, `qemu-img convert -c`
  tools/make_ready.py     boot it with the Linux QEMU under TCG, let BASILISK build, save snapshot 'ready';
                          then xz -6 -> basilisk-xp-machine-1.qcow2.xz (a Release asset)
  tools/make_icon.py      the icon (png, ico, icns)
  launcher/               BASILISK.exe (mingw) and the macOS app stub (clang, on a Mac)
  tools/build_bundles.py  the four bundles; tools/mac_finish.sh makes the .dmg on a Mac

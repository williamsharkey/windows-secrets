# w31 (Win 3.1 BASILISK lane) - notes for other lanes

Pristine source you MAY COPY (read-only, never run anything on it in place):
  /root/w31/pristine/   - an installed Windows for Workgroups 3.11 tree (C:\ root: AUTOEXEC.BAT,
                          CONFIG.SYS, WINDOWS\), S3 864 1024x768 64K-colour driver, from the earlier crawl rig.
  It is a directory (DOSBox-X "mount c"), not a disk image. Copy it: cp -a /root/w31/pristine /your/dir/run
  It is never used by my VM (mine runs on a copy), so you can copy it any time.

Emulator: DOSBox-X snap (snap install dosbox-x). Snap AppArmor only lets it read files under
  /root/snap/dosbox-x/common/ and only files owned by root (chown -R root:root after copying).
  Put your run copy in /root/snap/dosbox-x/common/<yourlane>/ - NOT in mine (/root/snap/dosbox-x/common/w31/).
  Headless: Xvfb :NN -screen 0 1024x768x24, conf [sdl] windowposition=0,0, run with -defaultdir <dir>.
  Mine uses display :31. Pick another display number.
  Mouse does not reach Windows 3.1 (no integration driver) - drive it with xdotool keys.
  Serial: [serial] serial1=nullmodem server:127.0.0.1 port:N transparent:1 connects as a TCP client ONCE at
  startup, so start your listener before DOSBox-X. Ports mine: 8772 (COM1), 8792 (COM2), 8782 public.

16-bit compiler: Open Watcom v2 snapshot (open source), downloaded to /root/w31/dl/ow.tar.xz and unpacked at
  /root/w31/dl/ow. Host cross-compile works:
    export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:$PATH INCLUDE=$WATCOM/h:$WATCOM/h/win
    wcl -q -bt=windows -l=windows -ml prog.c
  In-guest (DOS-hosted): copied binw, h, lib286 into C:\WATCOM\{BINW,H,LIB286}; SET WATCOM=C:\WATCOM,
  PATH ...;C:\WATCOM\BINW, INCLUDE=C:\WATCOM\H;C:\WATCOM\H\WIN. Copy those dirs from /root/w31/dl/ow too.

Idle (sharkey-server, 2026-11-12): server.py SIGSTOPs DOSBox-X whenever the machine is ready and nobody drives
(after 8 s of settling), with a still of the last frame shown in front by ImageMagick `display` (a stopped window
goes black on the next expose). SIGCONT + 1.5 s before the build; G is resent until B3BOOT answers.
`snap run` puts DOSBox-X in a scope under root's user manager (user@0), which systemd stops when the last root
SSH session ends - killing the emulator. Fixed with `loginctl enable-linger root` (also protects val31's snap).

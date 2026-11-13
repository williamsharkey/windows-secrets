#!/usr/bin/env python3
"""Answer files for an unattended install from the person's own media.

    answers.py xp  --key-file KEYFILE [--name NAME] > WINNT.SIF
    answers.py 311 [--name NAME] > SETUP.SHH

XP: WINNT.SIF for a clean install from the CD (Microsoft: Deploying Windows XP Part II; Unattend.txt reference in
DEPLOY.CAB on the XP CD, SUPPORT\\TOOLS). The product key is the person's own; it is read from a file (or stdin)
so that it never appears in a command line or log, and the plugin deletes the floppy after the build.

3.11: SETUP.SHH for "setup /h:a:\\setup.shh" (Microsoft KB Q120884 and the Windows 3.1 Resource Kit, Automated
Setup). DOSBox Pure provides DOS, so no MS-DOS media is needed.

The display, sound and start-up settings match what the shipped machines have (guest/prep.bat for XP,
tools/make_machine.py for 3.11): 1024x768, no event sounds, no screen saver, the synth program in Run.
"""
import argparse
import sys

XP_SIF = r"""[Data]
AutoPartition=1
MsDosInitiated="0"
UnattendedInstall="Yes"

[Unattended]
UnattendMode=FullUnattended
OemSkipEula=Yes
OemPreinstall=No
TargetPath=\WINDOWS
Repartition=Yes
FileSystem=*
UnattendSwitch="Yes"
WaitForReboot="No"
DriverSigningPolicy=Ignore
Hibernation=No

[GuiUnattended]
AdminPassword="*"
EncryptedAdminPassword=NO
AutoLogon=Yes
AutoLogonCount=9999
OEMSkipRegional=1
TimeZone=35
OemSkipWelcome=1

[UserData]
ProductKey="{key}"
FullName="{name}"
OrgName=""
ComputerName=BASILISK

[Display]
BitsPerPel=16
Xresolution=1024
Yresolution=768
Vrefresh=60

[RegionalSettings]
LanguageGroup=1
SystemLocale=00000409
UserLocale=00000409
InputLocale=0409:00000409

[Identification]
JoinWorkgroup=WORKGROUP

[Networking]
InstallDefaultComponents=Yes

[Components]
msmsgs=Off
msnexplr=Off
zonegames=Off
freecell=Off
hearts=Off
minesweeper=Off
pinball=Off
solitaire=Off
spider=Off

[Shell]
DefaultStartPanelOff=Yes
DefaultThemesOff=Yes

[GuiRunOnce]
Command0="A:\BSYNTH.CMD"
"""

# Section names and keys follow the SETUP.SHH template on WfW 3.11 disk 1. Tested in DOSBox Pure (install.py):
#  - display = vga for Setup itself: Setup's Windows part cannot start with SVGA256.DRV ("An error occurred while
#    trying to initialize the video adapter"). install.py then expands Microsoft's SVGA256.DRV/VDDSVGA.386/VGADIB.3GR
#    from the same disks and sets 1024x768, 256 colors, small fonts (SETUP.INF [svga768s]), which runs in 386
#    enhanced mode.
#  - network = nonet (WINNET.INF), and Setup is run with /i: its network-card detection hangs DOSBox otherwise.
#  - Accessories (Sound Recorder, Clock) must stay installed, and so must "bitmaps": SETUP.INF [win.bmps] holds the
#    wallpapers and also CHIMES, DING, RINGIN and RINGOUT.WAV, the sounds the DNA starts from.
W311_SHH = r"""[sysinfo]
showsysinfo=no

[configuration]
machine = ibm_compatible
display = vga
mouse = ps2mouse
keyboard = t4s0enha
language = enu
kblayout = nodll
network = nonet

[windir]
C:\WINDOWS

[userinfo]
"{name}"
""

[dontinstall]
readmes
games
screensavers

[endinstall]
configfiles = dontsave
endopt = exit
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edition', choices=['xp', '311'])
    ap.add_argument('--key-file', help='file holding the product key (XP only); "-" reads stdin')
    ap.add_argument('--name', default='BASILISK')
    a = ap.parse_args()
    if a.edition == 'xp':
        if not a.key_file:
            sys.exit('XP needs the person\'s product key (--key-file)')
        key = (sys.stdin.read() if a.key_file == '-' else open(a.key_file).read()).strip().upper()
        parts = key.split('-')
        if len(parts) != 5 or any(len(p) != 5 or not p.isalnum() for p in parts):
            sys.exit('a product key is five groups of five letters and digits')
        sys.stdout.write(XP_SIF.format(key=key, name=a.name).replace('\n', '\r\n'))
    else:
        sys.stdout.write(W311_SHH.format(name=a.name).replace('\n', '\r\n'))


if __name__ == '__main__':
    main()

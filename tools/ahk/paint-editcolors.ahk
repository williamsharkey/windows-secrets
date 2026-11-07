; Open Windows 7 Paint's "Edit colors" (ChooseColor) and reveal its hidden button.
#NoTrayIcon
SetTitleMatchMode, 2
Run, mspaint.exe
WinWait, - Paint,, 10
WinActivate
WinWaitActive, - Paint,, 5
IfWinNotActive, - Paint
    ExitApp
Sleep, 800
Send, {Alt}
Sleep, 400
Send, h
Sleep, 400
Send, ec
WinWait, Edit Colors,, 5
Sleep, 500
RunWait, C:\winsecrets\winprobe.exe shot "Edit Colors" C:\winsecrets\cc-before.bmp,, Hide
RunWait, %ComSpec% /c C:\winsecrets\winprobe.exe probe "Edit Colors" > C:\winsecrets\cc-probe.txt,, Hide
RunWait, %ComSpec% /c C:\winsecrets\winprobe.exe tab "Edit Colors" >> C:\winsecrets\cc-probe.txt,, Hide
RunWait, %ComSpec% /c C:\winsecrets\winprobe.exe reveal "Edit Colors" >> C:\winsecrets\cc-probe.txt,, Hide
Sleep, 400
RunWait, C:\winsecrets\winprobe.exe shot "Edit Colors" C:\winsecrets\cc-after.bmp,, Hide
WinClose, Edit Colors
Sleep, 300
WinClose, - Paint
Sleep, 500
IfWinExist, Paint ahk_class #32770
    ControlClick, Do&n't Save, Paint ahk_class #32770

; Resurrect Notepad's hidden "Match whole word only" checkbox and test it.
#NoTrayIcon
SetTitleMatchMode, 2
FileDelete, C:\winsecrets\cat.txt
FileAppend, concatenate the cat, C:\winsecrets\cat.txt
Run, notepad.exe C:\winsecrets\cat.txt
WinWait, cat.txt - Notepad,, 10
WinActivate
WinWaitActive, cat.txt - Notepad,, 5
IfWinNotActive, cat.txt - Notepad
    ExitApp
Send, ^{Home}
Send, ^f
WinWait, Find ahk_class #32770,, 5
ControlSetText, Edit1, cat, Find ahk_class #32770
RunWait, C:\winsecrets\winprobe.exe shot Find C:\winsecrets\np-find-before.bmp,, Hide
; the ghost: present, hidden, disabled
Control, Show,, Match &whole word only, Find ahk_class #32770
Control, Enable,, Match &whole word only, Find ahk_class #32770
Control, Check,, Match &whole word only, Find ahk_class #32770
Sleep, 300
RunWait, %ComSpec% /c C:\winsecrets\winprobe.exe probe Find > C:\winsecrets\np-find-probe.txt,, Hide
RunWait, C:\winsecrets\winprobe.exe shot Find C:\winsecrets\np-find-after.bmp,, Hide
ControlClick, &Find Next, Find ahk_class #32770
Sleep, 700
ControlGet, np, Hwnd,, Edit1, cat.txt - Notepad
SendMessage, 0xB0, 0, 0,, ahk_id %np%   ; EM_GETSEL
sel := ErrorLevel
start := sel & 0xFFFF
end := (sel >> 16) & 0xFFFF
FileAppend, whole-word-ticked selection=%start%-%end%`n, C:\winsecrets\np-result.txt
RunWait, C:\winsecrets\winprobe.exe shot screen C:\winsecrets\np-screen.bmp,, Hide
; control run: untick and search again from the top
Control, Uncheck,, Match &whole word only, Find ahk_class #32770
ControlSend,, ^{Home}, ahk_id %np%
SendMessage, 0xB1, 0, 0,, ahk_id %np%   ; EM_SETSEL 0,0
ControlClick, &Find Next, Find ahk_class #32770
Sleep, 700
SendMessage, 0xB0, 0, 0,, ahk_id %np%
sel := ErrorLevel
start := sel & 0xFFFF
end := (sel >> 16) & 0xFFFF
FileAppend, unticked selection=%start%-%end%`n, C:\winsecrets\np-result.txt
WinClose, Find ahk_class #32770
WinClose, cat.txt - Notepad

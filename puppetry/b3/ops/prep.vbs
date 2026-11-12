' BASILISK III desktop: the programs the build needs, as icons
Set sh = CreateObject("WScript.Shell")
d = sh.SpecialFolders("Desktop")
Sub L(name, target, args, icon)
  Set s = sh.CreateShortcut(d & "\" & name & ".lnk")
  s.TargetPath = target
  s.Arguments = args
  s.WorkingDirectory = sh.ExpandEnvironmentStrings("%USERPROFILE%")
  If icon <> "" Then s.IconLocation = icon
  s.Save
End Sub
L "Notepad", "%SystemRoot%\system32\notepad.exe", "", ""
L "Command Prompt", "%SystemRoot%\system32\cmd.exe", "", ""
L "tcc", "C:\tcc", "", "%SystemRoot%\system32\shell32.dll,4"
L "Calculator", "%SystemRoot%\system32\calc.exe", "", ""
L "Date and Time", "%SystemRoot%\system32\rundll32.exe", "shell32.dll,Control_RunDLL timedate.cpl", "%SystemRoot%\system32\timedate.cpl,0"
sh.RegWrite "HKCU\Software\Microsoft\Notepad\fWrap", 0, "REG_DWORD"
sh.RegWrite "HKCU\Software\Microsoft\Notepad\lfFaceName", "Lucida Console", "REG_SZ"
sh.RegWrite "HKCU\Software\Microsoft\Notepad\iPointSize", 100, "REG_DWORD"
sh.RegWrite "HKCU\Software\Microsoft\Notepad\StatusBar", 0, "REG_DWORD"
WScript.Echo "ok"

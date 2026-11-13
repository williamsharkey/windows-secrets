' BASILISK SYNTH Help: the desktop shortcut (called by HELPINST.BAT; Windows Script Host comes with Windows XP)
Set sh = CreateObject("WScript.Shell")
win = sh.ExpandEnvironmentStrings("%SystemRoot%")
Set lnk = sh.CreateShortcut(sh.SpecialFolders("Desktop") & "\BASILISK SYNTH Help.lnk")
lnk.TargetPath = win & "\winhlp32.exe"
lnk.Arguments = "C:\synth\BSYNTH.HLP"
lnk.WorkingDirectory = "C:\synth"
lnk.IconLocation = win & "\winhlp32.exe,0"
lnk.Description = "BASILISK SYNTH Help"
lnk.Save

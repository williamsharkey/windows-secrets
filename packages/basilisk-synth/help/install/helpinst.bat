@echo off
rem BASILISK SYNTH Help for Windows XP: run once inside XP while the machine is prepared (beside guest\prep.bat),
rem from a folder that holds BSYNTH.HLP, HELPINST.BAT and HELPICON.VBS (for example the build's share drive).
rem   - copies BSYNTH.HLP to C:\synth (beside synth.exe, which opens it with F1 / Help Contents)
rem   - puts a "BASILISK SYNTH Help" shortcut on the desktop (winhlp32.exe C:\synth\BSYNTH.HLP)
rem Running it again replaces both.
if not exist C:\synth mkdir C:\synth
copy /y "%~dp0BSYNTH.HLP" C:\synth\BSYNTH.HLP > nul
if errorlevel 1 goto fail
cscript //nologo "%~dp0HELPICON.VBS"
if errorlevel 1 goto fail
echo help installed
goto end
:fail
echo help NOT installed
:end

@echo off
rem BASILISK SYNTH machine: XP's own event sounds must never play into the instrument
reg add "HKCU\AppEvents\Schemes" /ve /d ".None" /f
for /f "delims=" %%k in ('reg query "HKCU\AppEvents\Schemes\Apps" /s ^| find "\.Current"') do reg add "%%k" /ve /d "" /f > nul
rem no screen saver, no power saving: it sits in a DAW for hours
reg add "HKCU\Control Panel\Desktop" /v ScreenSaveActive /d 0 /f
reg delete "HKCU\Control Panel\Desktop" /v SCRNSAVE.EXE /f
powercfg /change "Home/Office Desk" /monitor-timeout-ac 0 /disk-timeout-ac 0 /standby-timeout-ac 0 /hibernate-timeout-ac 0
powercfg /change "Always On" /monitor-timeout-ac 0 /disk-timeout-ac 0 /standby-timeout-ac 0 /hibernate-timeout-ac 0
powercfg /hibernate off
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v EnableBalloonTips /t REG_DWORD /d 0 /f
del "%USERPROFILE%\Desktop\basilisk.c" "%USERPROFILE%\Desktop\basilisk.exe"
del "%USERPROFILE%\Start Menu\Programs\Startup\basilisk.bat"
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v BasiliskSynth /d "C:\synth\synth.exe" /f
del C:\synth\synth.log C:\synth\*.exe.bak 2> nul
rem COM1 without its FIFO: one interrupt per byte (after a resume, XP's serial driver otherwise sits on the last bytes)
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Serial\Parameters" /v ForceFifoEnable /t REG_DWORD /d 0 /f
echo prepared

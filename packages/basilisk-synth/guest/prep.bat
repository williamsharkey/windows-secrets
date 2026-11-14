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
rem the library disc goes in while the synth runs: nothing may pop up for it
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Cdrom" /v AutoRun /t REG_DWORD /d 0 /f
rem a small shipped disk: the page file is zeroed at this shutdown and not used again (512 MB is plenty)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v ClearPageFileAtShutdown /t REG_DWORD /d 1 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v PagingFiles /t REG_MULTI_SZ /d "" /f
rem nothing unneeded on the shipped disk: Windows File Protection's spare copies, the driver archive (this machine's
rem hardware never changes), hotfix uninstall folders, temp files
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v SFCQuota /t REG_DWORD /d 0 /f
del /f /q "%windir%\system32\dllcache\*.*" > nul 2>&1
del /f /q "%windir%\Driver Cache\i386\*.cab" > nul 2>&1
for /d %%d in ("%windir%\$NtUninstall*") do rd /s /q "%%d"
for /d %%d in ("%windir%\$hf_mig$") do rd /s /q "%%d"
rd /s /q "%windir%\SoftwareDistribution\Download" > nul 2>&1
del /f /s /q "%TEMP%\*.*" > nul 2>&1
del /f /q "%windir%\Temp\*.*" > nul 2>&1
rem X1: the second AC97 is the recording card (the plugin feeds it the DAW's input); playback stays on the first
reg add "HKCU\Software\Microsoft\Multimedia\Sound Mapper" /v Playback /d "Intel(r) Integrated Audio" /f
reg add "HKCU\Software\Microsoft\Multimedia\Sound Mapper" /v Record /d "Intel(r) Integrated Audio (2)" /f
reg add "HKCU\Software\Microsoft\Multimedia\Sound Mapper" /v PreferredOnly /t REG_DWORD /d 1 /f
rem X1: new recordings default to CD Quality (44.1 kHz 16-bit stereo; XP ships "Radio Quality", 22 kHz 8-bit mono)
reg add "HKCU\Software\Microsoft\Multimedia\Audio" /v DefaultFormat /d "CD Quality" /f
echo prepared

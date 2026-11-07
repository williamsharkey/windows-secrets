@echo off
rem BASILISK V2 stage: launch-week desktop, no stranger yet - it gets written.
set D=%USERPROFILE%\Desktop
call C:\p\basilisk-setup.bat
copy /y "%USERPROFILE%\Start Menu\Programs\Accessories\Notepad.lnk" "%D%\" >nul
del /q "%D%\basilisk.exe" "%D%\basilisk.com" 2>nul
if not exist C:\basilisk mkdir C:\basilisk
del /q C:\basilisk\*.* 2>nul
rem Notepad in MS Gothic (copied from Windows 7), Japanese script
reg add HKCU\Software\Microsoft\Notepad /v lfFaceName /d "MS Gothic" /f >nul
reg add HKCU\Software\Microsoft\Notepad /v lfCharSet /t REG_DWORD /d 128 /f >nul
reg add HKCU\Software\Microsoft\Notepad /v iPointSize /t REG_DWORD /d 120 /f >nul
echo v2 set

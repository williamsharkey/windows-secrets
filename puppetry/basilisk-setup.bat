@echo off
rem Set the stage for BASILISK: an ordinary XP desktop in launch week, plus one stranger.
set D=%USERPROFILE%\Desktop
set A=%ALLUSERSPROFILE%\Start Menu\Programs
reg add "HKCU\Control Panel\Desktop" /v Wallpaper /d "C:\WINDOWS\Web\Wallpaper\Bliss.bmp" /f >nul
reg add "HKCU\Control Panel\Desktop" /v WallpaperStyle /d 2 /f >nul
reg add "HKCU\Control Panel\Desktop" /v TileWallpaper /d 0 /f >nul
RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters
copy /y "%A%\Accessories\Paint.lnk" "%D%\" >nul
copy /y "%A%\Accessories\Notepad.lnk" "%D%\" >nul
copy /y "%A%\Accessories\Calculator.lnk" "%D%\" >nul
copy /y "%A%\Accessories\System Tools\Character Map.lnk" "%D%\" >nul
copy /y "%A%\Accessories\Entertainment\Sound Recorder.lnk" "%D%\" >nul
copy /y "%A%\Games\Minesweeper.lnk" "%D%\" >nul
copy /y "%A%\Games\Solitaire.lnk" "%D%\" >nul
copy /y C:\p\puppet.exe "%D%\basilisk.exe" >nul
C:\p\puppet.exe test stamp %D%\basilisk.exe
w32tm /config /syncfromflags:NO >nul 2>&1
date 10-25-2001
time 10:21:00
echo set

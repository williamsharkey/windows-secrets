@echo off
rem Crawl classic Windows XP programs.  Run from the data disk (E:).
set C=%~d0\crawl
mkdir %C% 2>nul
for %%A in (notepad calc mspaint wordpad charmap sol freecell winmine mshearts spider sndrec32 sndvol32 regedit taskmgr dxdiag clipbrd eudcedit iexpress odbcad32 packager magnify osk sigverif winchat mplay32 hypertrm dialer fontview drwtsn32 cliconfg winver) do (
  echo == %%A
  %~d0\winprobe.exe crawl %C%\%%A %%A.exe
  taskkill /im %%A.exe /f >nul 2>&1
)
for %%A in (timedate mmsys main desk intl inetcpl sysdm powercfg joy appwiz telephon firewall hdwwiz ncpa access wscui nusrmgr) do (
  echo == %%A.cpl
  %~d0\winprobe.exe crawl %C%\cpl-%%A control.exe %%A.cpl
  taskkill /im rundll32.exe /f >nul 2>&1
)
"C:\Program Files\Windows NT\Pinball\pinball.exe" >nul 2>&1 & taskkill /im pinball.exe /f >nul 2>&1
echo ALLDONE > %~d0\done.txt

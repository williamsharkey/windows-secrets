@echo off
rem Crawl every classic Windows 7 program: menus, dialogs, tabs, expanders.
set C=C:\winsecrets\crawl
mkdir %C% 2>nul
for %%A in (notepad calc charmap regedit eudcedit iexpress odbcad32 dxdiag winver sigverif rasphone sndvol stikynot tabcal wfs xpsrchvw cliconfg dialer fxscover mstsc magnify osk soundrecorder mobsync msinfo32 taskmgr write mspaint dfrgui recdisc rekeywiz cttune dpiscaling credwiz fsquirt) do (
  echo == %%A
  winprobe crawl %C%\%%A %%A.exe
  taskkill /im %%A.exe /f >nul 2>&1
)
for %%A in (timedate mmsys main desk intl inetcpl sysdm powercfg joy appwiz telephon Firewall hdwwiz ncpa wscui TabletPC collab irprops bthprops infocardcpl) do (
  echo == %%A.cpl
  winprobe crawl %C%\cpl-%%A control.exe %%A.cpl
  taskkill /im rundll32.exe /f >nul 2>&1
)
echo ALLDONE

@echo off
rem Clip: the 6-pixel "&o" button in the colour picker, widened and pressed.
set W=C:\p\wp.exe
%W% move class:tooltips_class32 -3000 -3000 1 1
%W% move class:MSPaintApp 120 90 300 460
%W% cursor 990 700 0
%W% wait 1500
%W% post class:MSPaintApp 0x111 6869 0
%W% wait 1200
%W% move "Edit Colors" 300 150 453 331
for /f %%h in ('%W% find "Edit Colors" 719') do %W% click %%h
%W% wait 900
for /f %%h in ('%W% find "Edit Colors" 706') do set R=%%h
for /f %%h in ('%W% find "Edit Colors" 707') do set G=%%h
for /f %%h in ('%W% find "Edit Colors" 708') do set B=%%h
%W% settext %R% 2
%W% wait 150
%W% settext %R% 20
%W% wait 150
%W% settext %R% 200
%W% wait 300
%W% settext %G% 1
%W% wait 150
%W% settext %G% 12
%W% wait 150
%W% settext %G% 120
%W% wait 300
%W% settext %B% 6
%W% wait 150
%W% settext %B% 60
%W% wait 2500
%W% shake "Edit Colors" 900
%W% wait 500
%W% tween "Edit Colors" 300 150 476 420 1800
%W% wait 1800
for /f %%h in ('%W% find "Edit Colors" 713') do set O=%%h
%W% tween %O% 300 332 141 26 2200
%W% wait 1600
for /f "tokens=1-4" %%a in ('%W% screenpos %O%') do set /a CX=%%a+70 & set /a CY=%%b+13
%W% cursor %CX% %CY% 1400
%W% wait 700
%W% click %O%
%W% wait 3500

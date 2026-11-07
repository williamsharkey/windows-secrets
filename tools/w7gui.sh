#!/bin/bash
# Run a batch script in the interactive console session (session 1) of the
# W7 box and print its output.  Usage: w7gui.sh script.bat [timeout_s]
# The batch runs with cwd C:\winsecrets; its stdout/stderr come back here.
set -e
HOST=${W7HOST:-w7-lan}
BAT=$1; TMO=${2:-120}
scp -q "$BAT" $HOST:/C:/winsecrets/job.bat
ssh $HOST 'del /q C:\winsecrets\job.out C:\winsecrets\job.done 2>nul & (echo @echo off& echo cd /d C:\winsecrets& echo call job.bat ^> job.out 2^>^&1& echo echo done^> job.done) > C:\winsecrets\wrap.bat & (echo CreateObject^("WScript.Shell"^).Run "C:\winsecrets\wrap.bat", 0, True) > C:\winsecrets\wrap.vbs & schtasks /create /tn winsecrets-job /tr "wscript.exe C:\winsecrets\wrap.vbs" /sc once /st 23:59 /it /f >nul & schtasks /run /tn winsecrets-job >nul'
for i in $(seq 1 $TMO); do
  if ssh $HOST 'if exist C:\winsecrets\job.done (echo y)' 2>/dev/null | grep -q y; then break; fi
  sleep 1
done
ssh $HOST 'type C:\winsecrets\job.out'

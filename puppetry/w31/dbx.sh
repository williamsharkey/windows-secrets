#!/bin/bash
# w31 DOSBox-X control: dbx.sh start|stop|restart|shot FILE|xstop
C=/root/snap/dosbox-x/common/w31
case "$1" in
start)
  pgrep -f "[X]vfb :31" >/dev/null || { setsid nohup Xvfb :31 -screen 0 1024x768x24 -nolisten tcp >/dev/null 2>&1 </dev/null & sleep 1; }
  cd $C; setsid nohup env DISPLAY=:31 nice -n 5 /snap/bin/dosbox-x -defaultdir $C -conf $C/w31.conf >/root/w31/dosbox.log 2>&1 </dev/null & ;;
stop) pkill -f "[d]osbox-x -defaultdir $C"; pkill -x yad; sleep 0.5 ;;
xstop) pkill -f "[X]vfb :31" ;;
restart) $0 stop; $0 start ;;
shot) DISPLAY=:31 import -window root "$2" ;;
esac

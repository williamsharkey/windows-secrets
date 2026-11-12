#!/bin/bash
# val31 DOSBox-X control: dbx.sh start|stop|restart|shot FILE  (uses systemd when val31.target is installed)
C=/root/snap/dosbox-x/common/val31
if systemctl is-enabled val31.target >/dev/null 2>&1; then
  case "$1" in
  start) systemctl start val31-dosbox ;;
  stop) systemctl stop val31-dosbox ;;
  restart) systemctl restart val31-dosbox ;;
  shot) DISPLAY=:41 import -window root "$2" ;;
  esac
  exit 0
fi
case "$1" in
start)
  [ -S /tmp/.X11-unix/X41 ] || { setsid nohup Xvfb :41 -screen 0 1024x768x24 -nolisten tcp >/dev/null 2>&1 </dev/null & sleep 1; }
  cd $C; setsid nohup env DISPLAY=:41 nice -n 5 /snap/bin/dosbox-x -defaultdir $C -conf $C/val31.conf >/root/val31/dosbox.log 2>&1 </dev/null & ;;
stop) pkill -f "[d]osbox-x -defaultdir $C"; sleep 0.5 ;;
restart) $0 stop; $0 start ;;
shot) DISPLAY=:41 import -window root "$2" ;;
esac

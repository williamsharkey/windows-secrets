#!/bin/bash
# Recording studio: Windows XP in QEMU/KVM, rendered with SDL into a virtual
# X display that ffmpeg records.   studio.sh boot | rec NAME | stoprec | key ... | shot f.png | stop
D=:9; MON=/tmp/studio-mon.sock; ROOT=/root/xp
export DISPLAY=$D
mon() { echo "$1" | socat - UNIX-CONNECT:$MON >/dev/null 2>&1; }
case "$1" in
boot)
  pkill -f "Xvfb $D" ; pkill -f "name studio-xp"; sleep 1
  (Xvfb $D -screen 0 1024x768x24 -nocursor >/dev/null 2>&1 &); sleep 1
  qemu-system-i386 -name studio-xp -m 1024 -enable-kvm -cpu host -smp 2 \
    -drive file=$ROOT/winxp.qcow2,format=qcow2,snapshot=on,if=ide,index=0 \
    -drive file=$ROOT/data.img,format=raw,if=ide,index=1 \
    -vga cirrus -display sdl,show-cursor=off -full-screen \
    -netdev user,id=n0 -device rtl8139,netdev=n0 \
    -usb -device usb-tablet \
    -monitor unix:$MON,server,nowait -daemonize ;;
rec)   rm -f /root/rec-$2.mp4; (ffmpeg -loglevel error -y -f x11grab -draw_mouse 0 -framerate 30 -video_size 1024x768 -i $D.0+0,0 -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p /root/rec-$2.mp4 </dev/null >/root/rec-$2.log 2>&1 &) ;;
stoprec) pkill -INT -f "x11grab" ; sleep 3 ;;
key)   shift; for k in "$@"; do mon "sendkey $k"; sleep 0.12; done ;;
shot)  import -window root -display $D "$2" ;;
stop)  mon quit; sleep 1; pkill -f "Xvfb $D" ;;
esac

#!/bin/bash
# XP VALENTINE - the valentine VM. Network: only 10.0.2.2:8765 -> 127.0.0.1:8773 (valentine server guest side).
V=/root/valxp
MON=/tmp/valxp-mon.sock; QMP=/tmp/valxp-qmp.sock; VNC=/tmp/valxp-vnc.sock
GUESTPORT=${GUESTPORT:-8773}
ARGS=(-name valxp -m 512 -enable-kvm -cpu host -smp 2
  -drive file=$V/valxp.qcow2,format=qcow2,if=ide,index=0
  -vga cirrus -display none -vnc unix:$VNC,share=force-shared
  -netdev "user,id=n0,restrict=on,net=10.0.2.0/24,host=10.0.2.100,guestfwd=tcp:10.0.2.2:8765-cmd:socat STDIO TCP:127.0.0.1:$GUESTPORT"
  -device rtl8139,netdev=n0 -usb -device usb-tablet
  -monitor unix:$MON,server,nowait
  -qmp unix:$QMP,server,nowait)
qemu-img snapshot -U -l $V/valxp.qcow2 2>/dev/null | grep -q val-ready && ARGS+=(-loadvm val-ready)
case "$1" in
run)  exec qemu-system-i386 "${ARGS[@]}" ;;
boot) qemu-system-i386 "${ARGS[@]}" -daemonize ;;
stop) python3 -c "import socket,time;s=socket.socket(socket.AF_UNIX);s.connect(\"$QMP\");s.recv(4096);s.sendall(b\"{\\\"execute\\\":\\\"qmp_capabilities\\\"}{\\\"execute\\\":\\\"quit\\\"}\");time.sleep(1)" ;;
esac

#!/bin/bash
# BASILISK III - the term VM (Windows XP in QEMU). View: VNC on a unix socket (proxied view-only by server.py);
# keys: QMP input-send-event from server.py.  Network: only 10.0.2.2:8765 -> server.py guest side.
T=/root/term
MON=/tmp/term-mon.sock; QMP=/tmp/term-qmp.sock; VNC=/tmp/term-vnc.sock
GUESTPORT=${GUESTPORT:-8771}
ARGS=(-name term -machine pc-i440fx-jammy -m 512 -enable-kvm -cpu host -smp 2
  -drive file=$T/term.qcow2,format=qcow2,if=ide,index=0
  -vga cirrus -display none -vnc unix:$VNC,share=force-shared
  -netdev "user,id=n0,restrict=on,net=10.0.2.0/24,host=10.0.2.100,guestfwd=tcp:10.0.2.2:8765-cmd:socat STDIO TCP:127.0.0.1:$GUESTPORT"
  -device rtl8139,netdev=n0 -usb -device usb-tablet -k en-us
  -monitor unix:$MON,server,nowait
  -qmp unix:$QMP,server,nowait
  -qmp unix:/tmp/term-qmpk.sock,server,nowait)
qemu-img snapshot -U -l $T/term.qcow2 2>/dev/null | grep -q term-desk && ARGS+=(-loadvm term-desk)
case "$1" in
run)  exec qemu-system-i386 "${ARGS[@]}" ;;
boot) qemu-system-i386 "${ARGS[@]}" -daemonize ;;
stop) python3 -c "import socket,time;s=socket.socket(socket.AF_UNIX);s.connect(\"$QMP\");s.recv(4096);s.sendall(b\"{\\\"execute\\\":\\\"qmp_capabilities\\\"}{\\\"execute\\\":\\\"quit\\\"}\");time.sleep(1)" ;;
esac

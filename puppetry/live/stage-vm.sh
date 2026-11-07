#!/bin/bash
# BASILISK LIVE - the stage VM and its sound.
#   stage-vm.sh pulse     run the private PulseAudio (null sink "stage"), foreground
#   stage-vm.sh run       run the stage VM in the foreground (systemd: Type=simple)
#   stage-vm.sh boot      same, daemonized (manual use)
#   stage-vm.sh stop      quit the VM through its own monitor
# Nothing here touches the studio-xp / xp2 VMs or their sockets.
ST=/root/stage
MON=/tmp/stage-mon.sock      # HMP: owned by streamer.py (screendumps)
QMP=/tmp/stage-qmp.sock      # QMP: owned by server.py (loadvm, sendkey)
PULSE=$ST/pulse
GUESTPORT=${GUESTPORT:-8770} # guest's 10.0.2.2:8765 lands here (server.py guest side)
# guestfwd with a plain tcp: target is ONE chardev connection for the VM's lifetime;
# cmd: spawns socat per guest connection, which is what HTTP polling needs.
# restrict=on: the guest reaches nothing but this forward (no internet, no host ports).
ARGS=(-name stage -m 512 -enable-kvm -cpu host -smp 2
  -drive file=$ST/stage.qcow2,format=qcow2,if=ide,index=0
  -vga cirrus -display none
  -netdev "user,id=n0,restrict=on,net=10.0.2.0/24,host=10.0.2.100,guestfwd=tcp:10.0.2.2:8765-cmd:socat STDIO TCP:127.0.0.1:$GUESTPORT"
  -device rtl8139,netdev=n0 -usb -device usb-tablet
  -audiodev pa,id=snd0,server=unix:$PULSE/native,out.name=stage,out.frequency=44100,timer-period=10000
  -device AC97,audiodev=snd0
  -monitor unix:$MON,server,nowait
  -qmp unix:$QMP,server,nowait)
# start straight from the staged desktop (no cold boot) once the snapshot exists
qemu-img snapshot -U -l $ST/stage.qcow2 2>/dev/null | grep -q stage-ready && ARGS+=(-loadvm stage-ready)
case "$1" in
pulse)
  mkdir -p $PULSE
  cat > $PULSE/stage.pa <<PA
load-module module-native-protocol-unix socket=$PULSE/native auth-anonymous=1
load-module module-null-sink sink_name=stage rate=44100 channels=2 sink_properties=device.description=stage
set-default-sink stage
PA
  export PULSE_RUNTIME_PATH=$PULSE HOME=$PULSE XDG_RUNTIME_DIR=$PULSE
  exec pulseaudio -n --daemonize=no --exit-idle-time=-1 --disallow-exit=yes --use-pid-file=no \
       --system=no --log-target=stderr -F $PULSE/stage.pa ;;
run)
  for i in $(seq 50); do [ -S $PULSE/native ] && break; sleep 0.2; done
  exec qemu-system-i386 "${ARGS[@]}" ;;
boot)
  qemu-system-i386 "${ARGS[@]}" -daemonize ;;
stop)
  python3 -c "import socket;s=socket.socket(socket.AF_UNIX);s.connect('$QMP');s.recv(4096);s.sendall(b'{\"execute\":\"qmp_capabilities\"}{\"execute\":\"quit\"}');import time;time.sleep(1)" ;;
esac

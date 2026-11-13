X0 probes (RECORDING.md TR1): audio into Windows XP through QEMU's dbus audiodev, on a second AC97 card that is
input-only (playback stays on the wav pipe).

- `dbuspeer.py QMP [--pid QEMU_PID]` - a standard-library D-Bus peer: p2p connection (QMP getfd/add_client on
  Unix, get-win32-socket on Windows), RegisterInListener, answers Read with a 1 kHz sine (or `--clicks`).
  Windows needs `AUTH ANONYMOUS` and TCP_NODELAY on the socketpairs.
- `wavrec.c` - built in XP with tcc: `wavrec list`, `wavrec DEV SECONDS OUT.WAV` (waveIn through XP's own
  waveIn/kmixer/driver), `wavrec stat OUT.WAV` (frequency by zero crossings, glitches, silent runs).
- `agentsrv_std.py` - the guest agent's host side with the standard library (for the Mac).

QEMU: `-display dbus,p2p=yes,audiodev=a2 -audiodev dbus,id=a2[,nsamples=2048] -device AC97,audiodev=a2`.
Results are in PROGRESS.md (X0).

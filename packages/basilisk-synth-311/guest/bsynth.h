/* BSYN card: shared definitions for the Windows 3.11 side (driver and synth program) */
#define BS_BASE  0x2C0
#define BS_ARG   (BS_BASE + 0)
#define BS_CMD   (BS_BASE + 2)
#define BS_MAGIC (BS_BASE + 4)
#define BSC_OPEN 1
#define BSC_CLOSE 2
#define BSC_WRITE 3
#define BSC_RESET 4
#define BSC_POLLDONE 5
#define BSC_GETPOS 6
#define BSC_PAUSE 7
#define BSC_RESTART 8
#define BSC_SETVOL 9
#define BSC_SETRATE 10
#define BSC_GETVOL 11
#define BSC_GETRATE 12
#define BSC_EVPOLL 20
#define BSC_ARM 21
#define BSC_REPORT 22
#define BSC_ARMSTOP 23
#define BSC_MASTER 24
#define BSC_DACNOW 25
#define BSC_VOICES 26

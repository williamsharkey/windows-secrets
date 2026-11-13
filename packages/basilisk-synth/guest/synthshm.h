/* BASILISK SYNTH - what synth.exe and srhook.dll (inside every Sound Recorder) share.
   One named file mapping; everything is a LONG so either side can read it at any time. */
#define SY_NREC 16
#define SY_MAGIC 0x53594E31
#define SY_SHM "BasiliskSynthShm1"
#define SY_MSG "BasiliskSynthOp1"        /* registered message posted to a Sound Recorder: wParam op, lParam arg */
#define SY_DONE "BasiliskSynthDone1"     /* posted to synth.exe: wParam slot, lParam op (or SYE_END) */

/* ops, run by srhook.dll on the Sound Recorder's own thread */
#define SYO_PLAY 1     /* from the start, at s[i].rate (0 = the file's own rate) */
#define SYO_OFF 2      /* release: ramp to 0 over env_r, then Stop */
#define SYO_CUT 3      /* stop after a 5 ms ramp */
#define SYO_CMD 4      /* lParam: a Sound Recorder menu command id (WM_COMMAND), answering its message boxes */
#define SYO_SEEK 5     /* lParam: position in 1/1000 of the length */
#define SYO_STOP 6     /* Stop now */
#define SYO_NOMENU 7   /* take the menu bar away (the strip has the synth's menus instead) */
#define SYO_STRIP 8    /* lose the title bar and frame and become a child of the synth window, staying where it is */
#define SYO_DROP 9     /* the buttons a strip does not need (<<, >>, Record) drop away one at a time */
#define SYO_FLY 10     /* glide to s[i].fly (synth client coords) over lParam ms, parts sliding into a row */
#define SYE_END 100    /* the recorder stopped (end of sound or Stop) */
#define SYE_OPEN 101   /* the sound card was opened (lParam: ms since the play request) */

/* Sound Recorder (XP sndrec32.exe) ids */
#define SR_POS 201
#define SR_LEN 202
#define SR_WAVE 203
#define SR_TRACK 204
#define SR_REW 205
#define SR_FWD 206
#define SR_PLAY 207
#define SR_STOP 208
#define SR_REC 209
#define SR_NEW 1000
#define SR_OPEN 12
#define SR_SAVE 13
#define SR_SAVEAS 14
#define SR_COPY 20
#define SR_PASTE_INS 24
#define SR_PASTE_MIX 25
#define SR_INSFILE 22
#define SR_MIXFILE 23
#define SR_DEL_BEFORE 31
#define SR_DEL_AFTER 32
#define SR_VOL_UP 33
#define SR_VOL_DOWN 34
#define SR_SPEED_UP 35
#define SR_SPEED_DOWN 36
#define SR_ECHO 37
#define SR_REVERSE 38

typedef struct {
    volatile LONG pid;        /* the Sound Recorder process */
    volatile LONG hwnd;       /* its main window */
    volatile LONG rate;       /* Hz to open the sound card at for the next play; 0 = the file's own */
    volatile LONG vol;        /* this note's peak volume, 0..65535 */
    volatile LONG gate;       /* 1 while the note is held */
    volatile LONG level;      /* the envelope now, 0..65535 (for the display) */
    volatile LONG playing;    /* the sound card is open */
    volatile LONG answer;     /* 1: answer Sound Recorder's message boxes (Yes, or No to "save changes?") */
    volatile LONG t_req;      /* GetTickCount() of the last play request */
    volatile LONG t_open;     /* GetTickCount() at waveOutOpen */
    volatile LONG opens;      /* how many times the card was opened */
    volatile LONG fly[4];     /* SYO_FLY target: x, y, w, h */
    volatile LONG t_post;     /* GetTickCount() when synth.exe posted the last play */
    WCHAR file[260];          /* the next Open/Save/Insert/Mix dialog answers with this file */
} SySlot;

typedef struct {
    LONG magic, synth_hwnd;
    volatile LONG env_a, env_d, env_s, env_r;   /* ms, ms, %, ms */
    volatile LONG pad[10];
    RECT kid_final[16];       /* where a strip's controls end up, in this order: Play, Stop, Position frame,
                                 "Position:", position, wave, Length frame, "Length:", length, slider */
    SySlot s[SY_NREC];
} SyShm;

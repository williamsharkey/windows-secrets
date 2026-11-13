/* the few winmm declarations tcc lacks (no mmsystem.h, no winmm.def): call through GetProcAddress */
typedef UINT MMRESULT;
typedef HANDLE HWAVEOUT, *LPHWAVEOUT;
#define WAVE_MAPPER ((UINT)-1)
#define WAVECAPS_PITCH 1
#define WAVECAPS_PLAYBACKRATE 2
#define WAVECAPS_VOLUME 4
#define WAVECAPS_LRVOLUME 8
#define WAVECAPS_SYNC 16
#define WAVECAPS_SAMPLEACCURATE 32
#define CALLBACK_FUNCTION 0x30000
#define WOM_DONE 0x3BD
#pragma pack(push,1)
typedef struct { WORD wFormatTag, nChannels; DWORD nSamplesPerSec, nAvgBytesPerSec; WORD nBlockAlign, wBitsPerSample, cbSize; } WAVEFORMATEX, *LPWAVEFORMATEX;
#pragma pack(pop)
typedef const WAVEFORMATEX *LPCWAVEFORMATEX;
typedef struct { WORD wMid, wPid; UINT vDriverVersion; CHAR szPname[32]; DWORD dwFormats; WORD wChannels, wReserved1; DWORD dwSupport; } WAVEOUTCAPSA, *LPWAVEOUTCAPSA;
typedef struct wavehdr_tag { LPSTR lpData; DWORD dwBufferLength, dwBytesRecorded; DWORD_PTR dwUser; DWORD dwFlags, dwLoops; struct wavehdr_tag *lpNext; DWORD_PTR reserved; } WAVEHDR, *LPWAVEHDR;
typedef UINT (WINAPI *NUMDEVS)(void);

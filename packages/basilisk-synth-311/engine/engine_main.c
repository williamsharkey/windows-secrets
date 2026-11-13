/* engine as a process, for the test rigs: engine <shm-name> <core> <conf> <state|-> <host-pid> [--make-state OUT]
   It exits when the host says quit or the host process is gone. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "engine.h"
#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <signal.h>
#include <sys/mman.h>
#include <unistd.h>
#endif

static bshm *map_shm(const char *name)
{
#ifdef _WIN32
  HANDLE h = OpenFileMappingA(FILE_MAP_ALL_ACCESS, FALSE, name);
  if (!h) return NULL;
  return (bshm *)MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(bshm));
#else
  int fd = shm_open(name, O_RDWR, 0600); void *p;
  if (fd < 0) return NULL;
  p = mmap(NULL, sizeof(bshm), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  close(fd);
  return p == MAP_FAILED ? NULL : (bshm *)p;
#endif
}

static bshm *S; static long hostpid;
#ifdef _WIN32
static DWORD WINAPI watch(LPVOID p)
{
  HANDLE h = OpenProcess(SYNCHRONIZE, FALSE, (DWORD)hostpid);
  (void)p;
  if (h) WaitForSingleObject(h, INFINITE);
  else while (!S->quit) Sleep(250);
  S->quit = 1; return 0;
}
#endif

int main(int argc, char **argv)
{
  bs_engine *e;
  if (argc < 6) { fprintf(stderr, "engine <shm> <core> <conf> <state|-> <host-pid> [--make-state OUT]\n"); return 2; }
  hostpid = atol(argv[5]);
  S = map_shm(argv[1]);
  if (!S || S->magic != BSHM_MAGIC || S->version != BSHM_VERSION) { fprintf(stderr, "engine: no shared block %s\n", argv[1]); return 3; }
  e = bs_engine_new(S, argv[2], argv[3], strcmp(argv[4], "-") ? argv[4] : NULL,
                    (argc > 7 && !strcmp(argv[6], "--make-state")) ? argv[7] : NULL, getenv("BS311_LOG"));
#ifdef _WIN32
  CreateThread(NULL, 0, watch, NULL, 0, NULL);
#else
  if (fork() == 0) {          /* a watcher: when the host is gone, tell the engine to quit */
    while (kill((pid_t)hostpid, 0) == 0 && getppid() != 1 && !S->quit) usleep(250000);
    S->quit = 1; _exit(0);
  }
#endif
  return bs_engine_run(e);
}

/* zerofill.exe: fill C:'s free space with zeros, then give it back, so the shipped disk image compresses to what is
   really on it (tools/make_machine.py converts with zero clusters dropped). Run once before the machine is saved. */
#include <windows.h>
#include <stdio.h>
int main(void)
{
    static char z[1 << 20];
    HANDLE f = CreateFileA("C:\\zerofill.tmp", GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
    DWORD w;
    unsigned long mb = 0;
    if (f == INVALID_HANDLE_VALUE) { printf("cannot create\n"); return 1; }
    /* the disk is 64 GB but only its first few GB were ever used: 3 GB of zeros covers what was freed */
    while (mb < 3072 && WriteFile(f, z, sizeof z, &w, NULL) && w == sizeof z) mb++;
    FlushFileBuffers(f);
    CloseHandle(f);
    DeleteFileA("C:\\zerofill.tmp");
    printf("zeroed %lu MB\n", mb);
    return 0;
}

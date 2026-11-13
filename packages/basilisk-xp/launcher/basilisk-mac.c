/* BASILISK.app/Contents/MacOS/BASILISK - runs the bundled Python in this process, so macOS sees one app
 * named BASILISK with our icon (not "Python").
 *   clang -O2 -arch arm64 -mmacosx-version-min=11.0 basilisk-mac.c -o BASILISK
 */
#include <dlfcn.h>
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (*PyBytesMainFn)(int, char **);

int main(int argc, char **argv)
{
    char exe[PATH_MAX], real[PATH_MAX], res[PATH_MAX], lib[PATH_MAX], home[PATH_MAX], path[PATH_MAX * 2],
         script[PATH_MAX];
    uint32_t n = sizeof exe;
    void *h;
    PyBytesMainFn py_main;
    char *args[3];
    (void)argc; (void)argv;
    if (_NSGetExecutablePath(exe, &n) != 0 || !realpath(exe, real)) return 1;
    snprintf(res, sizeof res, "%s/../Resources", dirname(real));
    snprintf(home, sizeof home, "%s/runtime/python", res);
    snprintf(lib, sizeof lib, "%s/lib/libpython3.12.dylib", home);
    snprintf(path, sizeof path, "%s/runtime/site:%s/app", res, res);
    snprintf(script, sizeof script, "%s/app/basilisk.py", res);
    setenv("PYTHONHOME", home, 1);
    setenv("PYTHONPATH", path, 1);
    setenv("PYTHONNOUSERSITE", "1", 1);
    setenv("BASILISK_BUNDLE", res, 1);
    h = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "BASILISK: %s\n", dlerror()); return 1; }
    py_main = (PyBytesMainFn)dlsym(h, "Py_BytesMain");
    if (!py_main) return 1;
    args[0] = "BASILISK XP";
    args[1] = script;
    args[2] = NULL;
    return py_main(2, args);
}

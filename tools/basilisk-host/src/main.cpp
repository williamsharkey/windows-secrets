// BasiliskHost - a small Windows VST3 host for testing BASILISK SYNTH and BASILISK 16 without a DAW.
//
//   BasiliskHost.exe [PLUGIN.vst3 ...] [--sr HZ] [--block N] [--device NAME] [--env NAME=VALUE]   the GUI
//   BasiliskHost.exe --test PLUGIN.vst3 [harness options]                                         the test harness
//   BasiliskHost.exe --selftest DIR PLUGIN.vst3 [PLUGIN2.vst3]                                     a scripted GUI run
//   BasiliskHost.exe --write-pattern FILE.mid                                                     the test pattern as MIDI
// See README.md.
#include "host.h"
#include "midi.h"
#include <windows.h>
#include <shellapi.h>
#include <objbase.h>
#include <cstdio>
#include <io.h>
#include <fcntl.h>
#include <string>
#include <vector>

#include "audio.h"
#include <cmath>
int run_harness(const std::vector<std::string> &args);
int run_gui(const std::vector<std::string> &plugins, const std::string &selftestDir, const std::string &device, int sr, int block);

static void attach_console()
{
    // a GUI-subsystem program: use the caller's console or pipe when there is one
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    if (h && h != INVALID_HANDLE_VALUE && GetFileType(h) != FILE_TYPE_UNKNOWN) return;
    if (AttachConsole(ATTACH_PARENT_PROCESS)) {
        freopen("CONOUT$", "w", stdout);
        freopen("CONOUT$", "w", stderr);
    }
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int)
{
    // never a modal "cannot load DLL" or "insert disk" box: failures are logged instead
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX | SEM_NOGPFAULTERRORBOX);
    int argc = 0;
    wchar_t **wv = CommandLineToArgvW(GetCommandLineW(), &argc);
    std::vector<std::string> args;
    for (int i = 1; i < argc; i++) args.push_back(narrow(wv[i]));
    LocalFree(wv);

    std::vector<std::string> plugins;
    std::string selftest, device, pattern;
    bool test = false, probe = false;
    int sr = 48000, block = 512;
    for (size_t i = 0; i < args.size(); i++) {
        const std::string &a = args[i];
        auto next = [&]() { return i + 1 < args.size() ? args[++i] : std::string(); };
        if (a == "--env") {   // NAME=VALUE, set before any plugin loads (e.g. BSYNTH_MACHINE_DIR)
            std::string kv = next();
            size_t e = kv.find('=');
            if (e != std::string::npos) {
                // both the Win32 block and the C runtime's copy: a plugin's getenv() reads the latter
                std::wstring k = widen(kv.substr(0, e)), v = widen(kv.substr(e + 1));
                SetEnvironmentVariableW(k.c_str(), v.c_str());
                _wputenv_s(k.c_str(), v.c_str());
            }
        } else if (a == "--test") test = true;
        else if (a == "--selftest") selftest = next();
        else if (a == "--device") device = next();
        else if (a == "--sr") sr = atoi(next().c_str());
        else if (a == "--block") block = atoi(next().c_str());
        else if (a == "--write-pattern") pattern = next();
        else if (a == "--audio-probe") probe = true;
        else if (a == "--help" || a == "-h" || a == "/?") {
            attach_console();
            printf("BasiliskHost 1.0.0 - see README.md\n"
                   "  BasiliskHost.exe [PLUGIN.vst3 ...] [--sr HZ] [--block N] [--device NAME] [--env NAME=VALUE]\n"
                   "  BasiliskHost.exe --test PLUGIN.vst3 [--out-dir DIR] [--report FILE] [--midi FILE | --pattern LIST | --score SPEC]\n"
                   "                   [--tests offline,realtime,repeat,state,preset,progchange,multi,orphans,editor] [--repeat N] [--instances K]\n"
                   "                   [--sr HZ] [--block N] [--warmup S] [--tail S] [--program N] [--state-program N]\n"
                   "                   [--load-state FILE] [--automate NAME:t=v;t=v] [--multi-programs 0,2] [--change-at S] [--change-program N]\n"
                   "                   [--editor-script \"wait 8|click X Y|type TEXT|key enter|shot NAME\"] [--state-contains TEXT] [--kill-orphans] [--env NAME=VALUE]\n"
                   "  BasiliskHost.exe --selftest DIR PLUGIN.vst3 [PLUGIN2.vst3 ...]\n"
                   "  BasiliskHost.exe --write-pattern FILE.mid\n");
            return 0;
        } else if (a.size() > 2 && a[0] == '-' && a[1] == '-') {
            // harness options with a value
            static const char *withValue[] = {"--report", "--out-dir", "--midi", "--pattern", "--score", "--warmup", "--tail", "--repeat",
                                              "--instances", "--program", "--state-program", "--load-state", "--automate", "--tests", "--multi-programs", "--change-at", "--change-program", "--state-contains",
                                              "--editor-script", "--editor-script-file", "--render-timeout"};
            for (auto w : withValue) if (a == w) { i++; break; }
        } else if (!test) plugins.push_back(a);
    }
    if (probe) {   // play 5 s of a quiet 440 Hz tone; report what the device really took
        attach_console();
        CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
        for (auto &d : audio_devices()) printf("device: %s%s\n", d.name.c_str(), d.isDefault ? " (default)" : "");
        AudioOut out;
        std::string err;
        double ph = 0;
        int r = sr;
        if (!out.start(L"", sr, block, [&](float *L, float *R, int n) {
                for (int k = 0; k < n; k++) { L[k] = R[k] = 0.05f * (float)std::sin(ph); ph += 2 * M_PI * 440 / r; }
            }, err)) { printf("audio: %s\n", err.c_str()); return 1; }
        double t0 = now_s();
        Sleep(5000);
        double el = now_s() - t0;
        uint64_t f = out.framesOut;
        out.stop();
        printf("mix format %d Hz, %d ch, %d bit\n", out.mixRate, out.mixChannels, out.mixBits);
        printf("%s: asked %d Hz block %d, buffer %d frames, period %.1f ms; %llu frames in %.2f s = %.0f frames/s, underruns %llu\n",
               out.deviceName.c_str(), sr, block, out.bufferFrames, out.periodMs, (unsigned long long)f, el, f / el,
               (unsigned long long)out.underruns);
        return 0;
    }
    if (!pattern.empty()) {
        attach_console();
        bool ok = write_midi_file(pattern, test_pattern());
        printf("%s %s\n", ok ? "wrote" : "could not write", pattern.c_str());
        return ok ? 0 : 1;
    }
    if (test) {
        attach_console();
        CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
        return run_harness(args);
    }
    block = block < 64 ? 64 : block > 2048 ? 2048 : block;
    return run_gui(plugins, selftest, device, sr, block);
}

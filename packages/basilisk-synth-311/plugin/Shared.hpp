// What the editor needs from the plugin instance (DISTRHO_PLUGIN_WANT_DIRECT_ACCESS).
#pragma once
#include "../engine/bshm.h"
#include <atomic>
struct Basilisk16Shared {
    bshm *S = nullptr;
    std::atomic<int> editors{0};
    std::atomic_flag shmLock = ATOMIC_FLAG_INIT;   // the event ring has two writers: the audio thread and the worker
    char status[160] = "";                         // shown by the editor until Windows has drawn its first frame
};

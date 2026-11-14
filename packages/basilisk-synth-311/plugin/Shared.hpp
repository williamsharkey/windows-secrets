// What the editor needs from the plugin instance (DISTRHO_PLUGIN_WANT_DIRECT_ACCESS).
#pragma once
#include "../engine/bshm.h"
#include <atomic>
#include <mutex>
#include <string>
#include <vector>
#include <cstdint>
struct Basilisk16Shared {
    bshm *S = nullptr;
    std::atomic<int> editors{0};
    std::atomic_flag shmLock = ATOMIC_FLAG_INIT;   // the event ring has two writers: the audio thread and the worker
    char status[160] = "";                         // shown by the editor until Windows has drawn its first frame
    // Save state / Load state (design/STATE.md): Windows asks (`state save` / `state load`), the plugin hands the
    // editor the state text and the request; the editor opens the host's file dialog and writes or reads the .b16
    std::atomic<int> fileReq{0};                   // 1 save, 2 load, 3 export a recording, 4 import a WAV
    std::vector<uint8_t> fileBytes;                // (3) the recording's bytes, exactly as Sound Recorder saved them
    std::string fileName;                          // (3) its default file name
    std::atomic<bool> importReady{false};          // (4) the editor read a WAV: fileBytes, fileName (the plugin takes them)
    std::mutex fileMtx; std::string stateText;     // the state to save
    std::string fileMsg;                           // a message back to Windows (`state saved <name>` / `state error ...`)
};

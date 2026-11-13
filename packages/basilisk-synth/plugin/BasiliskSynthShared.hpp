// What the UI needs from the plugin (same process: DISTRHO_PLUGIN_WANT_DIRECT_ACCESS)
#pragma once
#include <string>
#include "Machine.hpp"
#include "../core/dna.h"
#include "../core/voices.h"
#include "../core/proto.h"
#include "../core/state.h"

class SynthHost {
public:
    virtual ~SynthHost() {}
    virtual bsynth::Machine &machine() = 0;
    virtual void uiOpened() = 0;                       // the editor is showing: time for the assembly
    virtual bool takeEdit(std::string &dna) = 0;       // a DNA changed inside XP, for the UI to hand to the host
    virtual std::string dnaText() = 0;
    virtual int latencyMs() const = 0;
};

// the plugin instance pointer DPF hands the UI, as the SynthHost it is (defined beside the plugin class)
SynthHost *synthHostOf(void *pluginInstance);

#ifndef DISTRHO_PLUGIN_INFO_H_INCLUDED
#define DISTRHO_PLUGIN_INFO_H_INCLUDED

#define DISTRHO_PLUGIN_BRAND   "williamsharkey.com"
#define DISTRHO_PLUGIN_NAME    "BASILISK SYNTH"
#define DISTRHO_PLUGIN_URI     "https://williamsharkey.com/basilisk-synth"
#define DISTRHO_PLUGIN_CLAP_ID "com.williamsharkey.basilisk-synth"

#define DISTRHO_PLUGIN_BRAND_ID  Wshk
#define DISTRHO_PLUGIN_UNIQUE_ID Bsyn

#define DISTRHO_PLUGIN_HAS_UI          1
#define DISTRHO_PLUGIN_IS_RT_SAFE      1
#define DISTRHO_PLUGIN_IS_SYNTH        1
#define DISTRHO_PLUGIN_NUM_INPUTS      2   // a stereo sidechain: the recording input (RECORDING.md 1.1)
#define DISTRHO_PLUGIN_AU_TYPE         aumu   // an instrument: DPF would call a synth with inputs a music effect (aumf),
                                              // and DAWs would list it among effects. AU instruments take side chains
#define DISTRHO_PLUGIN_NUM_OUTPUTS     2
#define DISTRHO_PLUGIN_WANT_LATENCY    1
#define DISTRHO_PLUGIN_WANT_MIDI_INPUT 1
#define DISTRHO_PLUGIN_WANT_PROGRAMS   1
#define DISTRHO_PLUGIN_WANT_STATE      1
#define DISTRHO_PLUGIN_WANT_FULL_STATE 1
#define DISTRHO_PLUGIN_WANT_DIRECT_ACCESS 1
#define DISTRHO_PLUGIN_WANT_TIMEPOS    1

#define DISTRHO_UI_USE_NANOVG      1
#define DISTRHO_UI_USER_RESIZABLE  1
#define DISTRHO_UI_DEFAULT_WIDTH   1024
#define DISTRHO_UI_DEFAULT_HEIGHT  768
#define DISTRHO_UI_FILE_BROWSER    0

#define DISTRHO_PLUGIN_VST3_CATEGORIES "Instrument|Sampler"
#define DISTRHO_PLUGIN_CLAP_FEATURES   "instrument", "sampler", "stereo"

#endif

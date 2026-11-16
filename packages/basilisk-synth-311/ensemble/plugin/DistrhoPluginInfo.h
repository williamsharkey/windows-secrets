// SNDWAVE1993 Ensemble (beta, design/ENSEMBLE.md): one Windows 3.11, sixteen lanes, one MIDI channel each.
#ifndef DISTRHO_PLUGIN_INFO_H_INCLUDED
#define DISTRHO_PLUGIN_INFO_H_INCLUDED

#define DISTRHO_PLUGIN_BRAND   "Algorithmic Industries"
#define DISTRHO_PLUGIN_NAME    "SNDWAVE1993 Ensemble"
#define DISTRHO_PLUGIN_URI     "https://williamsharkey.com/sndwave2000/ensemble"
#define DISTRHO_PLUGIN_CLAP_ID "com.williamsharkey.sndwave2000-ensemble"
#define DISTRHO_PLUGIN_BRAND_ID  Wshk
#define DISTRHO_PLUGIN_UNIQUE_ID B3En

#define DISTRHO_PLUGIN_HAS_UI 1
#define DISTRHO_PLUGIN_IS_RT_SAFE 1
#define DISTRHO_PLUGIN_IS_SYNTH 1
#define DISTRHO_PLUGIN_NUM_INPUTS 0
#define DISTRHO_PLUGIN_NUM_OUTPUTS 34   /* the mix, then each lane's own pair (post-fader) */
#define DISTRHO_PLUGIN_WANT_LATENCY 1
#define DISTRHO_PLUGIN_WANT_PROGRAMS 0
#define DISTRHO_PLUGIN_WANT_STATE 1
#define DISTRHO_PLUGIN_WANT_FULL_STATE 1
#define DISTRHO_PLUGIN_WANT_DIRECT_ACCESS 1
#define DISTRHO_PLUGIN_WANT_MIDI_INPUT 1
#define DISTRHO_PLUGIN_WANT_TIMEPOS 1
#define DISTRHO_UI_USE_NANOVG 0
#define DISTRHO_UI_USER_RESIZABLE 1
#define DISTRHO_UI_DEFAULT_WIDTH 1024
#define DISTRHO_UI_DEFAULT_HEIGHT 768
#define DISTRHO_PLUGIN_VST3_CATEGORIES "Instrument|Synth|Sampler"
#define DISTRHO_PLUGIN_CLAP_FEATURES "instrument", "synthesizer", "sampler", "stereo"
#define DISTRHO_PLUGIN_AU_TYPE aumu
// VST3: the controllers the lanes use, on every channel (sustain, all off, pitch bend: the songs' tuning bends)
#define DPF_VST3_FEW_MIDI_CC 1, 64, 120, 123, 129

#endif

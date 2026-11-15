// render311: DNA + MIDI -> WAV through the real Windows 3.11 machine (DOSBox Pure with the BSYN card), headless.
//
//   render311 --machine DIR --core FILE --dna "DNA" (--midi in.mid | --score "t:note:vel:dur,...") --out out.wav
//             [--tail SECONDS] [--log FILE] [--bits 24|32] [--bpm BPM]   (BPM: the tempo for v3 Wt, Wb, Wg; 120)
//             [--key 0-11] [--scale ID] [--use-preset-scale 0|1] [--snap 1-4] [--remap 0|1] [--anchor NOTE]   (the plugin's
//             Key, Scale, Use Preset Scale, Snap, Remap Keys and Remap Anchor parameters: PRESET-ENGINE-2 18.2)
//             [--scala FILE.scl]   (an imported tuning, as the Scales page's Scala... button)
//             [--grid "<w> <h> <state> <cells>"]   (a Minesweeper board for a DNA with x tokens: the sequencer)
//             [--lookahead MS]   (send each event this long before its block: dense chords arm on time; 0 default)
//             [--user-dir DIR]   (My Recordings: index.tsv and the WAVs; their u_ names play, RECORDING.md 4.4)
//   render311 --machine DIR --core FILE --song SONG.song --out mix.wav [--jobs N] [--stems DIR] [--lookahead MS]
//             (a whole song, as the Song tab renders it: one engine per track, N at once (4), each with a copy of the
//             core, then the mix; --stems writes each track's render as DIR/<n>.<name>.wav; --lookahead 150 default)
//
// --score: notes as t:note:velocity:duration in seconds (the format of packages/basilisk-synth/tools/batch_render.py).
// DNA v2 (DNA.md 5): library NAMEs come from DIR/library.names.txt; macros are applied as the plugin applies them.
//
// The machine resumes from its snapshot, skips the assembly animation (no screen), builds the DNA with Sound
// Recorder's own commands, and plays the MIDI file note by note through the recorders, exactly as the plugin does
// offline: every note is stamped with the DAC sample it must start on. It runs as fast as the emulator can (no real
// time pacing). Output: 48 kHz stereo WAV (24-bit, or 32-bit float with --bits 32), aligned to the notes (the latency
// is already removed).
#include "../plugin/SongMix.h"
#include <map>
#include <thread>

static int renderSongFile(std::map<std::string, std::string> &a)
{
    using namespace b16song;
    const std::string path = a["--song"];
    std::ifstream in(path, std::ios::binary); std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    SongText song; std::string err;
    if (!song.parse(text, &err)) { std::fprintf(stderr, "render311: %s: %s\n", path.c_str(), err.c_str()); return 2; }
    const size_t sl = path.find_last_of("/\\");
    const std::string mpath = (sl == std::string::npos ? std::string() : path.substr(0, sl + 1)) + song.get("midi");
    std::ifstream mf(mpath, std::ios::binary); std::vector<uint8_t> md((std::istreambuf_iterator<char>(mf)), std::istreambuf_iterator<char>());
    Smf smf;
    if (!smf.parse(md, &err)) { std::fprintf(stderr, "render311: %s: %s\n", mpath.c_str(), err.c_str()); return 2; }
    SongPlan plan;
    if (!planSong(song, smf, loadPresets(a["--machine"]), plan, err)) { std::fprintf(stderr, "render311: %s: %s\n", path.c_str(), err.c_str()); return 2; }
    {   // the name table once, before the engines start (it is process-wide)
        std::vector<std::string> names; std::string l;
        std::ifstream n1(a["--machine"] + "/library.names.txt"), n2(a["--machine"] + "/packs/packs.names.txt");
        for (std::ifstream *f : {&n1, &n2}) while (std::getline(*f, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
        setLibrary(names);
    }
    const int jobs = std::max(1, a.count("--jobs") ? std::atoi(a["--jobs"].c_str()) : 4);
    const uint64_t look = (uint64_t)((a.count("--lookahead") ? std::atof(a["--lookahead"].c_str()) : 150.0) * 48.0);
    const size_t N = plan.tracks.size();
    std::vector<TrackOut> outs(N);
    std::atomic<size_t> next{0};
    const double t0 = nowSec();
    auto worker = [&]() {
        for (size_t i; (i = next++) < N;) {
            TrackJob J; J.machine = a["--machine"]; J.core = a["--core"]; J.dna = plan.tracks[i].dna; J.ev = plan.tracks[i].ev;
            J.tail = plan.engineTail; J.bpm = plan.engineBpm; J.lookahead48 = look; J.setLibrary = false; J.privateCore = true;
            if (!renderTrack(J, outs[i]) && outs[i].err.empty()) outs[i].err = "failed";
            std::fprintf(stderr, "render311: track %zu %s (%s): %.1f s in %.1f s, late %u of %u%s%s\n", i + 1, plan.tracks[i].t->name.c_str(),
                         plan.tracks[i].label.c_str(), outs[i].endSec, outs[i].buildSec + outs[i].playSec, outs[i].late, outs[i].total,
                         outs[i].err.empty() ? "" : ": ", outs[i].err.c_str());
        }
    };
    std::vector<std::thread> th;
    for (int k = 0; k < std::min<int>(jobs, (int)N); k++) th.emplace_back(worker);
    for (auto &t : th) t.join();
    for (auto &o : outs) if (!o.err.empty()) return 3;
    const double t1 = nowSec();
    if (a.count("--stems"))
        for (size_t i = 0; i < N; i++) writeWav(a["--stems"] + "/" + std::to_string(i) + "." + plan.tracks[i].t->name + ".wav", outs[i].lr);
    std::vector<MixIn> mi;
    for (size_t i = 0; i < N; i++) mi.push_back({plan.tracks[i].t, &outs[i].lr});
    MixStats st;
    const std::vector<double> y = mixSong(song, plan.bpm, plan.lengthSec, mi, &st);
    writeMixWav(a["--out"], y);
    std::fprintf(stderr, "render311: %s: %.2f s, %zu tracks, %d engines: tracks %.1f s, mix %.1f s; %.2f LUFS, peak %.2f dBFS, limiter %.2f dB\n",
                 path.c_str(), y.size() / 96000.0, N, std::min<int>(jobs, (int)N), t1 - t0, nowSec() - t1, st.lufs, st.peakDb, st.reductionDb);
    return 0;
}

int main(int argc, char **argv)
{
    std::map<std::string, std::string> a;
    for (int i = 1; i + 1 < argc; i += 2) a[argv[i]] = argv[i + 1];
    if (a.count("--song") && a.count("--machine") && a.count("--core") && a.count("--out")) return renderSongFile(a);
    if (!a.count("--machine") || !a.count("--core") || !a.count("--dna") || (!a.count("--midi") && !a.count("--score")) || !a.count("--out")) {
        std::fprintf(stderr, "render311 --machine DIR --core FILE --dna DNA (--midi IN.mid | --score t:note:vel:dur,...) --out OUT.wav [--tail SECONDS] [--log FILE] [--bits 24|32]\n");
        return 2;
    }
    std::vector<b16song::MidiEv> ev;
    if (a.count("--score")) { if (!b16song::readScore(a["--score"], ev)) { std::fprintf(stderr, "render311: bad --score\n"); return 2; } }
    else if (!b16song::readMidi(a["--midi"], ev)) { std::fprintf(stderr, "render311: cannot read %s\n", a["--midi"].c_str()); return 2; }
    const double tail = a.count("--tail") ? std::atof(a["--tail"].c_str()) : 3.0;
    const double bpm = a.count("--bpm") ? std::atof(a["--bpm"].c_str()) : 120.0;   // v3 Wt, Wb, Wg
    b16song::TrackJob J;
    J.machine = a["--machine"]; J.core = a["--core"]; J.dna = a["--dna"]; J.ev = ev; J.tail = tail; J.bpm = bpm;
    if (a.count("--log")) J.log = a["--log"];
    if (a.count("--user-dir")) J.userDir = a["--user-dir"];
    if (a.count("--grid")) J.grid = a["--grid"];
    J.verbose = std::getenv("RENDER311_VERBOSE") != nullptr;
    if (a.count("--lookahead")) J.lookahead48 = (uint64_t)(std::atof(a["--lookahead"].c_str()) * 48.0);   // ms
    {   // the key and scale parameters (PRESET-ENGINE-2 18.2), as the plugin's
        auto num = [&](const char *k, int &v) { if (a.count(k)) v = std::atoi(a[k].c_str()); };
        num("--key", J.kp.root); num("--scale", J.kp.scale); num("--use-preset-scale", J.kp.usePreset); num("--snap", J.kp.snap);
        num("--remap", J.kp.remap); num("--anchor", J.kp.anchor);
        if (a.count("--scala")) {   // a Scala .scl (the plugin's Scala... import)
            std::ifstream in(a["--scala"]); std::string t((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>()), err;
            bsynth3::Tuning tu;
            if (!bsynth3::parseScl(t, tu, &err)) { std::fprintf(stderr, "render311: --scala: %s\n", err.c_str()); return 2; }
            J.kp.tuning = bsynth3::tuningText(tu);
        }
    }
    b16song::TrackOut R;
    if (!b16song::renderTrack(J, R)) { std::fprintf(stderr, "render311: %s\n", R.err.c_str()); return 3; }
    if (a.count("--bits") && a["--bits"] == "32") b16song::writeWavFloat(a["--out"], R.lr); else b16song::writeWav(a["--out"], R.lr);
    std::fprintf(stderr, "render311: %.2f s of audio in %.2f s (resume+build %.2f s, play %.2f s: %.1fx real time); late notes %u of %u\n",
                 R.endSec, R.buildSec + R.playSec, R.buildSec, R.playSec, R.endSec / (R.playSec > 0 ? R.playSec : 1), R.late, R.total);
    return 0;
}

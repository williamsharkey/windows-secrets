# BASILISK 16: status

Released as basilisk-synth-311-v1.0.0. See README.md for what it is, how it was tested, and how to build it.

Open items:
- Mac universal builds use a folder C: drive. DOSBox Pure's zip drive crashes in its x86_64 macOS build; seen under
  Rosetta. Windows uses drive.zip, because plugin hosts scan folders for .dll files and must not find Windows 3.11's.
- Reloading a saved REAPER project renders the same envelope, but one stretch differs by up to about 20 % of the
  signal (4.5–5.7 s in the test project): probably a release-time difference while the host restores parameters.
  Not chased.
- VST3 hosts list DPF's MIDI-CC parameters (2048 of them) next to the real ones.
- The factory programs are the "Current Program" parameter, not a VST3 program list.

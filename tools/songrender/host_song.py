"""songrender --engine host: each track rendered through the real SNDWAVE1993 VST3 in BasiliskHost (Windows), offline.

    songrender.py SONG.song --engine host --host C:/.../BasiliskHost.exe --plugin C:/.../SNDWAVE1993.vst3

Per track: a raw VST3 component state (DPF's "__dpf_state_begin__" block) holding the plugin's own state text, the
track's DNA and every pack disc inserted (the Library tab's discs, as render311 inserts them all), then
`BasiliskHost --test PLUGIN --tests offline --midi TRACK.mid --load-state STATE`. The host renders warmup + score +
tail; the warmup and the plugin's reported latency are cut off, so the stem lines up with render311's.
Runs from WSL (Windows interop) or on Windows.
"""
import json, os, subprocess, tempfile, hashlib, shutil

WARMUP = 8.0


def winpath(p):
    if os.name == 'nt':
        return p
    return subprocess.run(['wslpath', '-w', p], capture_output=True, text=True, check=True).stdout.strip()


class HostArgs:
    def __init__(self, host, plugin):
        if not host or not plugin:
            raise SystemExit('--engine host needs --host BasiliskHost.exe and --plugin SNDWAVE1993.vst3')
        self.host, self.plugin = host, plugin
        self.packs = ''
        m = os.path.join(plugin, 'Contents', 'Resources', 'machine', 'packs', 'PACKS.TSV')
        if os.path.exists(m):
            self.packs = ','.join(l.split('\t')[1] for l in open(m, encoding='utf-8') if l.count('\t') >= 2)
        # a scratch folder Windows can write fast (the C: temp folder when running from WSL)
        if os.name == 'nt':
            self.scratch = tempfile.gettempdir()
        else:
            w = subprocess.run(['cmd.exe', '/c', 'echo %TEMP%'], capture_output=True, text=True, cwd='/mnt/c').stdout.strip()
            self.scratch = subprocess.run(['wslpath', '-u', w], capture_output=True, text=True).stdout.strip()

    def ident(self):
        h = hashlib.sha256()
        win = os.path.join(self.plugin, 'Contents', 'x86_64-win')
        dll = next((os.path.join(win, n) for n in ('SNDWAVE1993.vst3', 'SNDWAVE2000.vst3')
                    if os.path.exists(os.path.join(win, n))), os.path.join(win, 'SNDWAVE1993.vst3'))   # 1.5 renamed it
        for p in (dll, os.path.join(self.plugin, 'Contents', 'Resources', 'machine', 'w31.state')):
            if os.path.exists(p):
                with open(p, 'rb') as f:
                    h.update(f.read())
        return h.hexdigest()[:16]


def state_blob(dna, packs):
    text = 'BASILISK-SYNTH 1\ndna ' + dna + '\nreference 0\n' + (f'packs {packs}\n' if packs else '')
    # DPF's VST3 state stream: NUL-separated keys and values between the state markers, 0xFE at the end
    return b'__dpf_state_begin__\0state\0' + text.encode() + b'\0__dpf_state_end__\0\xfe'


def render_track(ha, dna, mid, wav_out, tail):
    import songrender as sr
    work = tempfile.mkdtemp(prefix='songhost-', dir=ha.scratch)
    try:
        shutil.copy(mid, os.path.join(work, 'track.mid'))
        with open(os.path.join(work, 'track.state'), 'wb') as f:
            f.write(state_blob(dna, ha.packs))
        out = os.path.join(work, 'out')
        cmd = [ha.host, '--test', winpath(ha.plugin) if ha.plugin.startswith('/') else ha.plugin,
               '--tests', 'offline', '--midi', winpath(os.path.join(work, 'track.mid')),
               '--load-state', winpath(os.path.join(work, 'track.state')), '--out-dir', winpath(out),
               '--warmup', f'{WARMUP:g}', '--tail', f'{tail:g}', '--sr', '48000', '--block', '512']
        r = subprocess.run(cmd, capture_output=True, text=True)
        rep = json.load(open(os.path.join(out, 'report.json')))
        lat = int(rep['renders']['offline'].get('latency_samples', 2880))
        x = sr.read_f32_wav(os.path.join(out, 'offline.wav'))
        x = x[int(WARMUP * sr.SR) + lat:]
        # as render311 writes it: 32-bit float
        import numpy as np
        lr = x.astype('<f4').reshape(-1)
        with open(wav_out, 'wb') as f:
            data = lr.tobytes()
            f.write(b'RIFF' + (36 + len(data)).to_bytes(4, 'little') + b'WAVEfmt ' + (16).to_bytes(4, 'little'))
            f.write((3).to_bytes(2, 'little') + (2).to_bytes(2, 'little') + (48000).to_bytes(4, 'little') + (48000 * 8).to_bytes(4, 'little'))
            f.write((8).to_bytes(2, 'little') + (32).to_bytes(2, 'little') + b'data' + len(data).to_bytes(4, 'little') + data)
        return f'host: latency {lat}, render {rep["renders"]["offline"].get("render_s", "?")} s'
    finally:
        shutil.rmtree(work, ignore_errors=True)

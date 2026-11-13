import sys, os, subprocess, tempfile
sys.path.insert(0, os.path.expanduser('~/windows-secrets-sound-arch/packages/basilisk-synth/sound-archaeology'))
import sound_archaeology as sa
Z = os.path.expanduser('~/sound-arch/root/usr/lib/7zip/7z')
for e in sa.walk_source(sys.argv[1]):
    l = e.path.lower()
    if l.endswith(('.chm', '.msi', '.wmz', '.zip', '.swf', '.hlp', '.col')):
        d = e.read()
        if l.endswith('.swf'):
            print('SWF', e.path, d[:3], len(d)); continue
        with tempfile.NamedTemporaryFile(dir=os.path.expanduser('~/sound-arch/tmp'), suffix='.bin') as t:
            t.write(d); t.flush()
            out = subprocess.run([Z, 'l', t.name], capture_output=True, text=True).stdout
        hits = [x for x in out.splitlines() if x.lower().rstrip().endswith(('.wav', '.mid', '.rmi', '.wma', '.mp3', '.au', '.snd'))]
        if hits: print('HIT', e.path, hits[:10])

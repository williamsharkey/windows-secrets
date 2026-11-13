import rig, time
e = rig.start()
try:
    e.wait_packet(2, 60) if False else None
    print(rig.pr(e, 'hi 2', 'hi', 60))
    for f in ('NOIS1', 'NOIS8', 'SINE', 'CLICK', 'STEPS'):
        print(rig.pr(e, 'pr load 0 C:\\PE2\\%s.WAV' % f, 'pr load'))
    e.shot('/home/wm/pe2-311/work/t0.png')
finally: e.close()

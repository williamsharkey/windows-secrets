import sys, os, struct, zlib
sys.path.insert(0, os.path.expanduser('~/windows-secrets-sound-arch/packages/basilisk-synth/sound-archaeology'))
import sound_archaeology as sa
def tags(d):
    if d[:3]==b'CWS': d=d[:8]+zlib.decompress(d[8:])
    nb=d[8]>>3; p=8+((5+4*nb+7)//8)+4
    while p+2<=len(d):
        cl=struct.unpack('<H',d[p:p+2])[0]; p+=2; code=cl>>6; ln=cl&63
        if ln==63: ln=struct.unpack('<I',d[p:p+4])[0]; p+=4
        yield code,d[p:p+ln]; p+=ln
        if code==0: break
for e in sa.walk_source(sys.argv[1]):
    if e.path.lower().endswith('.swf'):
        d=e.read(); import collections; c=collections.Counter(); info=[]
        for code,b in tags(d):
            c[code]+=1
            if code==14:
                sid,fl,n=struct.unpack('<HBI',b[:7]); info.append(('DS',sid,fl>>4,[5512,11025,22050,44100][(fl>>2)&3],(fl>>1)&1,fl&1,n,len(b)))
            if code in (18,45):
                info.append(('SH',b[1]>>4,[5512,11025,22050,44100][(b[1]>>2)&3],b[1]&1))
        print(e.path, {k:v for k,v in c.items() if k in (14,15,18,19,45)}, info[:40])

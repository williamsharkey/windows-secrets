import sys,struct
from dissect.hypervisor.disk import qcow2
from dissect.ntfs import NTFS
def open_ntfs(p):
    q=qcow2.QCow2(open(p,'rb')); s=q.open()
    s.seek(0); mbr=s.read(512)
    start=struct.unpack('<I',mbr[446+8:446+12])[0]*512
    class Sub:
        def __init__(s2): s2.pos=0
        def seek(s2,o,w=0):
            if w==0: s2.pos=o
            elif w==1: s2.pos+=o
            else: s2.pos=q.size-start+o
            return s2.pos
        def tell(s2): return s2.pos
        def read(s2,n=-1):
            s.seek(start+s2.pos); d=s.read(n); s2.pos+=len(d); return d
    return NTFS(Sub())
def walk(fs):
    stack=[('',fs.mft.get('\\'))]; seen=set()
    while stack:
        path,d=stack.pop()
        for name,e in d.listdir().items():
            if name in ('.','..') or name.startswith('$'): continue
            try:
                if e.attribute.file_name.flags==2: continue  # DOS 8.3 alias
            except Exception: pass
            try:
                r=e.dereference()
                if r.segment in seen: continue
                seen.add(r.segment)
                if r.is_dir(): stack.append((path+'\\'+name,r))
                else: yield path+'\\'+name, r.size()
            except Exception as ex: print('ERR',path,name,ex,file=sys.stderr)
if __name__=='__main__':
    fs=open_ntfs(sys.argv[1])
    for p,sz in walk(fs): print(f"{sz}\t{p}")

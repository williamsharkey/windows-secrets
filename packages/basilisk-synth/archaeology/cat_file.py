import sys, walk, shutil
fs=walk.open_ntfs(sys.argv[1])
r=fs.mft.get(sys.argv[2])
with open(sys.argv[3],'wb') as o: shutil.copyfileobj(r.open(),o)

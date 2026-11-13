import csv, json, sys, collections, re
prior = json.load(open('/mnt/c/Users/willi/github/williamsharkey/windows-secrets/packages/basilisk-synth/library/research/windows-sounds.json'))['sounds']
files, conts = set(), set()
for s in prior:
    for p in [s.get('path')] + (s.get('also_at') or []):
        if not p: continue
        p = p.lower().replace('c:', '')
        if ' (' in p: conts.add(p.split(' (')[0])
        else: files.add(p)
rows = []
for f in sys.argv[2:]:
    rows += list(csv.DictReader(open(f)))
out = []
for r in rows:
    p = r['path'].split('|')[0].lower()
    if p.startswith('\\synth\\') or (p.endswith('sndrec.wav') and r['duration'] in ('0.0', '0')):
        continue   # BASILISK's own working files and the empty "New Sound" template
    if r['kind'] == 'dls-wave':
        st = 'new (inside gm.dls, which the prior list holds as one entry)'
    elif r['where'] == 'file' and p in files:
        st = 'prior'
    elif r['path'].split('|')[0].lower() in conts or p in conts:
        st = 'prior'
    elif '|' in r['path'] and r['path'].split('|')[1].lower() in {x.split('\\')[-1] for x in files}:
        st = 'new location (prior lists the name, not in our image)'
    else:
        st = 'new'
    # dllcache / duplicate copies point at the first copy
    r['in_prior_research'] = st
    out.append(r)
# propagate: a dup inherits its original's status
byid = {r['id']: r for r in out}
for r in out:
    if r['dup_of'] and r['dup_of'] in byid and byid[r['dup_of']]['in_prior_research'] == 'prior':
        r['in_prior_research'] = 'prior'
    if r['dup_of'] and r['in_prior_research'] == 'prior' and r['dup_of'] in byid:
        byid[r['dup_of']]['in_prior_research'] = 'prior'
cols = list(rows[0].keys())
with open(sys.argv[1], 'w', newline='') as o:
    w = csv.DictWriter(o, cols, extrasaction='ignore'); w.writeheader(); w.writerows(out)
c = collections.Counter((r['source'], r['kind'], r['in_prior_research'][:12], 'dup' if r['dup_of'] else 'uniq') for r in out)
for k, v in sorted(c.items()): print(v, k)
c = collections.Counter((r['source'], r['path'].split('\\')[-1]) for r in out if not r['dup_of'] and r['in_prior_research'] != 'prior')
for k, v in sorted(c.items()): print(v, k)

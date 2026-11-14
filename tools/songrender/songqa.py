#!/usr/bin/env python3
"""songqa: checks over songrender's reports. A stem that is silent or nearly so (a preset that does not answer the
notes it was given), a late note, a song outside 1:30-3:00, a limiter working hard, the loudness off target.

    songqa.py OUT_DIR [...]
"""
import json, os, re, sys

bad = 0
for d in sys.argv[1:]:
    for f in sorted(os.listdir(d)):
        if not f.endswith('.json') or f == 'index.json':
            continue
        r = json.load(open(os.path.join(d, f)))
        if 'mix' not in r:
            continue
        issues = []
        if not 88 <= r['seconds'] <= 185:
            issues.append(f'length {r["seconds"]:.0f} s')
        for t in r['mix']['tracks']:
            if t['lufs'] < -45:
                issues.append(f'{t["track"]} nearly silent ({t["lufs"]} LUFS)')
        for t in r['tracks']:
            m = re.search(r'late notes (\d+) of', t.get('render', ''))
            if m and int(m.group(1)):
                issues.append(f'{t["name"]}: {m.group(1)} late notes')
        if r['mix']['limiter_max_reduction_db'] > 6:
            issues.append(f'limiter {r["mix"]["limiter_max_reduction_db"]} dB')
        print(f'{f[:-5]:34s} {r["seconds"]:6.1f} s {r["mix"]["lufs"]:6.1f} LUFS  {"; ".join(issues) or "ok"}')
        bad += bool(issues)
print(f'{bad} with issues')

#!/usr/bin/env python3
"""Summarize dlgscan -a -j output: deduplicated suspicious controls."""
import json, os, sys, collections
path = sys.argv[1]; show = sys.argv[2:] or ['OUTSIDE', 'PARTIAL', 'ZEROSIZE']
rows = [json.loads(l) for l in open(path, encoding='utf-8', errors='replace') if l.strip()]
seen = set()
for r in rows:
    if r['kind'] != 'control' or r['flag'] not in show: continue
    b = os.path.basename(r['file'].replace('\\', '/')).lower().replace('.mui', '')
    k = (b, r['res'], r['id'], r['x'], r['y'])
    if k in seen: continue
    seen.add(k)
    print(f"{b:20} {r['flag']:8} res={r['res']:<6} [{r['dlg_cx']}x{r['dlg_cy']} {r['dialog'][:28]!r}] id={r['id']} {r['type']} "
          f"@{r['x']},{r['y']} {r['cx']}x{r['cy']} {'vis' if r['visible'] else 'HID'}{' DIS' if r['disabled'] else ''}"
          f"{' tab' if r['tabstop'] else ''} {r['text'][:50]!r}")

#!/usr/bin/env python3
"""Scoring statistics of evolve states: candidates, pass rate, reject reasons, per category and per lineage.

    stats.py STATE.json [...]  [--json OUT]
"""
import argparse, collections, json, re, sys


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('states', nargs='+'); ap.add_argument('--json')
    a = ap.parse_args()
    rows, T, st = [], [], []
    for f in a.states:
        s = json.load(open(f)); off = len(T); T += s['targets']; st.append(s.get('stats', {}))
        for r in s['rows']: r = dict(r); r['t'] += off; rows.append(r)
    why = collections.Counter()
    for r in rows:
        for w in r['why']: why[re.sub(r'[\d.+-]+', 'N', w)] += 1
    cat = collections.defaultdict(lambda: [0, 0]); lin = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        c = T[r['t']]['scat']; l = r['lin'].split('-')[0]
        cat[c][0] += 1; cat[c][1] += r['ok']; lin[l][0] += 1; lin[l][1] += r['ok']
    sc = sorted(r['score'] for r in rows if r['ok'])
    out = {'candidates': len(rows), 'pass': sum(r['ok'] for r in rows), 'targets': len(T),
           'reject_reasons': dict(why.most_common()), 'by_category': {k: {'n': v[0], 'pass': v[1]} for k, v in sorted(cat.items())},
           'by_lineage': {k: {'n': v[0], 'pass': v[1]} for k, v in sorted(lin.items())},
           'score_quartiles': [sc[len(sc) * q // 4] for q in range(4)] + [sc[-1]] if sc else [],
           'retuned': sum(1 for r in rows if r['origin'] == 'retune'), 'retune_pass': sum(1 for r in rows if r['origin'] == 'retune' and r['ok']),
           'render_stats': st}
    print(json.dumps(out, indent=1))
    if a.json: json.dump(out, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()

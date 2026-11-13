#!/usr/bin/env python3
"""Put the "Try it online" block (section.html) into sndrec.html's Download section, or replace the one already there.
  insert_section.py SITE/sndrec.html VERSION
Only the lines between the b16-try markers are this tool's; the rest of the page is left as it is."""
import re, sys
page, ver = sys.argv[1], sys.argv[2]
import os
block = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'section.html')).read().replace('@V@', ver).rstrip('\n') + '\n'
s = open(page, encoding='utf-8').read()
m = re.search(r'[ \t]*<!-- b16-try: begin.*?<!-- b16-try: end -->\n', s, re.S)
if m: s = s[:m.start()] + block + s[m.end():]
else:
    d = s.index('<div class="win" id="download">')
    a = s.index('<p><a class="btn" href="sndrec-download.html"', d)
    a = s.rindex('\n', 0, a) + 1
    s = s[:a] + block + s[a:]
open(page, 'w', encoding='utf-8').write(s)
print('sndrec.html: b16-try block', 'replaced' if m else 'inserted')

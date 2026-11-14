#!/usr/bin/env python3
"""The play page, /sndwave2000/play/index.html: play.html (the site's frame) around the "Try it online" block
(section.html), with the block's files next to it.
  make_play.py OUT/index.html VERSION"""
import os, sys
out, ver = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
block = open(os.path.join(here, 'section.html')).read().replace('@V@', ver).replace('@BASE@', '').rstrip('\n')
block = block.replace('<h2>Try it online</h2>\n', '', 1)   # the page's own h1 says it
page = open(os.path.join(here, 'play.html')).read().replace('@SECTION@', block)
assert '@' + 'BASE@' not in page and '@SECTION@' not in page
open(out, 'w', encoding='utf-8').write(page)
print('play page', out, 'version', ver)

#!/bin/bash
# deploy-ui.sh: the UI lane's half of site/citypop -> williamsharkey.com/citypop/ (docroot ~/html/live on the web host, via sharkey-server).
# Sends the page itself (index.html, style.css, app.js, fonts/, art/, .htaccess, and scene/ + life/ with --modules).
# Never sends album.json, audio/, data/ or SOURCES.TXT: those are the album lane's (deploy.sh).
# Dry run shows what differs from the live copy; --go copies only new or changed files, then checks every URL over HTTPS.
set -e
REPO=$(cd "$(dirname "$0")/../../../../../.." && pwd)
SRC=$REPO/site/citypop
SSH="ssh -o BatchMode=yes -J root@165.227.95.55 williamsharkey.com@williamsharkey.com"
DST=html/live/citypop
MODS=0; GO=0
for a in "$@"; do case $a in --go) GO=1;; --modules) MODS=1;; esac; done
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mine() {   # the files this script owns, relative, ./-prefixed
  (cd "$SRC" && find . -type f ! -name .gitignore ! -name '*.md' ! -name 'test*.html' ! -path './audio/*' ! -path './data/*' \
     ! -name album.json ! -name SOURCES.TXT | sort | grep -Ev '^\./(scene|life)/|^\./art/scene2' || true)
  [ $MODS = 1 ] && (cd "$SRC" && find ./scene ./life ./art -type f \( -path './art/scene2*' -o ! -path './art/*' \) ! -path './scene/gen/*' ! -name .gitignore ! -name '*.md' ! -name 'test*.html' ! -name '*.py' 2>/dev/null | sort) || true
}
mine | sort -u > "$TMP/files"
(cd "$SRC" && xargs md5sum < "$TMP/files") > "$TMP/local.md5"
$SSH "cd $DST 2>/dev/null && find . -type f | sort | xargs md5sum" > "$TMP/live.md5" || true
echo "== local vs live (UI files only)"
grep -Ff <(awk '{print $2}' "$TMP/local.md5") "$TMP/live.md5" > "$TMP/live-mine.md5" || true
diff "$TMP/live-mine.md5" "$TMP/local.md5" | grep '^[<>]' | sed 's/^</live: /; s/^>/new:  /' || echo "(no differences)"
CH=$(diff "$TMP/live-mine.md5" "$TMP/local.md5" | grep '^>' | awk '{print $3}' || true)
if [ $GO = 1 ] && [ -n "$CH" ]; then
  (cd "$SRC" && tar czf - $CH) | $SSH "mkdir -p $DST && tar xzf - -C $DST"
  echo "== sent: $(echo $CH | wc -w) files"
  $SSH "cd $DST && find . -type f | sort | xargs md5sum" > "$TMP/live.md5"
elif [ $GO = 0 ]; then echo "dry run: add --go to copy (and --modules to include scene/ and life/)"; fi
echo "== check over HTTPS"
bad=0
while read -r f; do
  f=${f#./}; u="https://williamsharkey.com/citypop/$f"; [ "$f" = index.html ] && u="https://williamsharkey.com/citypop/"
  case $f in *.htaccess) grep -q "$(md5sum < "$SRC/$f" | cut -c1-32)  ./$f" "$TMP/live.md5" && st=ok || { st=DIFF; bad=1; }; echo "$st   (md5 over ssh)  $f"; continue;; esac
  r=$(curl -s -o "$TMP/got" -w '%{http_code} %{content_type}' "$u")
  a=$(md5sum < "$SRC/$f" | cut -c1-32); b=$(md5sum < "$TMP/got" | cut -c1-32)
  st=ok; [ "$a" = "$b" ] || st=DIFF; [ "${r%% *}" = 200 ] || st=FAIL
  [ $st = ok ] || bad=1
  printf '%-5s %s  %s\n' "$st" "$r" "$f"
done < "$TMP/files"
[ $bad = 0 ] && echo "all ok" || { echo "some files differ (run with --go?)"; exit 1; }

#!/bin/bash
# deploy.sh: put site/citypop-deprogrammed on williamsharkey.com/citypop-deprogrammed/ (docroot ~/html/live on the web
# host, reached through sharkey-server). Shows what differs from the live copy first; --go to copy.
set -e
REPO=$(cd "$(dirname "$0")/../../../../../.." && pwd)
SRC=$REPO/site/citypop-deprogrammed
SSH="ssh -o BatchMode=yes -J root@165.227.95.55 williamsharkey.com@williamsharkey.com"
DST=html/live/citypop-deprogrammed
echo "== local vs live (md5)"
(cd "$SRC" && find . -type f ! -name .gitignore | sort | xargs md5sum) > /tmp/cpd_local.md5
$SSH "cd $DST 2>/dev/null && find . -type f | sort | xargs md5sum" > /tmp/cpd_live.md5 || true
diff /tmp/cpd_live.md5 /tmp/cpd_local.md5 | grep '^[<>]' | sed 's/^</live: /; s/^>/new:  /' || echo "(no differences)"
[ "$1" = "--go" ] || { echo "dry run: add --go to copy"; exit 0; }
(cd "$SRC" && tar czf - --exclude=.gitignore .) | $SSH "mkdir -p $DST && tar xzf - -C $DST"
echo "== check over HTTPS"
for f in index.html app.js album.json; do
  a=$(md5sum < "$SRC/$f" | cut -c1-32); b=$(curl -s "https://williamsharkey.com/citypop-deprogrammed/$f" | md5sum | cut -c1-32)
  [ "$a" = "$b" ] && echo "ok   $f" || echo "DIFF $f"
done

#!/bin/bash
# resnap.sh : put the current /root/term/www/basilisk3.c into the clean desktop snapshot (term-desk).
# Takes the server's maintenance lock first: it refuses (409) while a visitor drives or a session is
# starting, and holds new sessions off until the snapshot is saved. (A session that started in the middle
# of a loadvm/savevm once timed out with no explanation; this is why.)
TOK=$(cat /root/term/data/admin.token)
A() { curl -s -o /dev/stderr -w '%{http_code}' -X POST "http://127.0.0.1:8771/admin/maint?on=$1&token=$TOK"; }
H() { curl -s -X POST "http://127.0.0.1:8771/admin/hmp?token=$TOK" --data-binary "$1"; }
code=$(A 1)
if [ "$code" != 200 ]; then echo "resnap: the machine is in use (HTTP $code); try again when it is idle" >&2; exit 1; fi
trap 'A 0 >/dev/null 2>&1' EXIT
H "loadvm term-desk" && H "cont" >/dev/null
sleep 3
tadm "get /basilisk3.c C:\\p\\basilisk3.c"
sleep 1
H "savevm term-desk"
H "stop" >/dev/null
qemu-img snapshot -U -l /root/term/term.qcow2 | tail -1

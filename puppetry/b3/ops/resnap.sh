#!/bin/bash
# resnap.sh : put the current /root/term/www/basilisk3.c and puppet.exe into the clean desktop snapshot
TOK=$(cat /root/term/data/admin.token)
H() { curl -s -X POST "http://127.0.0.1:8771/admin/hmp?token=$TOK" --data-binary "$1"; }
H "loadvm term-desk" && H "cont" >/dev/null
sleep 3
tadm "get /basilisk3.c C:\\p\\basilisk3.c"
sleep 1
H "savevm term-desk"
qemu-img snapshot -U -l /root/term/term.qcow2 | tail -1

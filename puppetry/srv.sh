#!/bin/bash
pkill -f "studio_server.py serv[e]"
sleep 0.5
setsid python3 /root/xp/studio_server.py serve >/root/xp/server.log 2>&1 < /dev/null &

#!/bin/bash
# full-res still from the live HLS (use while streamer.py owns the monitor)
cd /dev/shm/stage-hls && cat init.mp4 $(ls -t seg*.m4s | sed -n 2p) > /tmp/stage-frame.mp4 && ffmpeg -loglevel error -y -i /tmp/stage-frame.mp4 -update 1 -frames:v 1 $1

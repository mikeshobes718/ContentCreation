#!/usr/bin/env bash
# Render every plate to build/plates/<name>.mp4 (720p24, upscaled later).
set -euo pipefail
cd "$(dirname "$0")/.."
for n in ${PLATES:-vault eight codered datacenter crowd crowd2}; do
  [ -f "plates/$n.mp4" ] && { echo "skip $n"; continue; }
  xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --python blender/plates.py -- "$n" build/plates >/dev/null 2>&1
  mkdir -p plates
  ffmpeg -loglevel error -y -framerate 24 -i "build/plates/$n/f_%04d.png" -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p "plates/$n.mp4"
  echo "plate $n done"
done

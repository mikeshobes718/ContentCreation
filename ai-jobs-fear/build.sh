#!/usr/bin/env bash
# Build the full video: narration -> visuals -> score/mix -> final mux.
# Needs: ffmpeg, python3 with kokoro-onnx soundfile skia-python numpy,
# and the Kokoro model files in ./models (see README).
set -euo pipefail
cd "$(dirname "$0")"
B=build

python3 pipeline/tts.py
python3 pipeline/render.py --jobs "${JOBS:-4}" ${ONLY:+--only "$ONLY"}
python3 pipeline/mix.py
python3 pipeline/render.py --thumbnail out/thumbnail.png

ls $B/segments/seg_*.mp4 | sort | sed "s|^$B/segments/|file '|; s|$|'|" > $B/segments/list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i $B/segments/list.txt -c copy $B/video.mp4
ffmpeg -loglevel error -y -i $B/video.mp4 -i $B/mix.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -shortest -movflags +faststart \
  out/the-machine-is-coming-for-your-job.mp4
cp $B/subtitles.srt out/the-machine-is-coming-for-your-job.srt
echo "done: out/the-machine-is-coming-for-your-job.mp4"

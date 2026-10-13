#!/usr/bin/env bash
# Build "Google Invented Modern AI" end to end.
#   VOICE_BACKEND=elevenlabs ./build.sh   (needs ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID)
#   VOICE_BACKEND=files ./build.sh        (your own WAVs in build/lines/, see build/lines_manifest.tsv)
#   ./build.sh                            (offline Kokoro preview voice)
set -euo pipefail
cd "$(dirname "$0")"
B=build
NAME=google-invented-modern-ai

# one-time deps for a fresh cloud session
python3 -c "import skia, soundfile" 2>/dev/null || pip install -q skia-python soundfile numpy
python3 -c "import skia" 2>/dev/null || apt-get install -y -q libegl1 libgl1 >/dev/null

# 3D plates are committed in plates/; only re-render them if one is missing
for n in vault eight codered datacenter crowd crowd2; do
  [ -f "plates/$n.mp4" ] || { command -v blender >/dev/null || apt-get install -y -q blender xvfb >/dev/null; PLATES="$n" blender/render_all.sh; }
done

python3 pipeline/tts.py
rm -f $B/segments/seg_*.mp4
python3 pipeline/render.py --jobs "${JOBS:-4}"
python3 pipeline/mix.py
mkdir -p out
python3 pipeline/render.py --thumbnail out/thumbnail.png

ls $B/segments/seg_*.mp4 | sort | sed "s|^$B/segments/|file '|; s|$|'|" > $B/segments/list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i $B/segments/list.txt -c copy $B/video.mp4
ffmpeg -loglevel error -y -i $B/video.mp4 -i $B/mix.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -shortest -movflags +faststart out/$NAME.mp4
cp $B/subtitles.srt out/$NAME.srt
echo "done: out/$NAME.mp4 ($(python3 -c "import json;print(json.load(open('$B/timeline.json'))['voice'])"))"
# YouTube chapter list from the real timeline
python3 - <<'PY' > out/chapters.txt
import json, sys
sys.path.insert(0, ".")
from script import SCENES
tl = json.load(open("build/timeline.json"))
print("0:00 Thirteen days")
for s in tl["scenes"]:
    p = SCENES[s["index"]]["p"]
    if s["visual"] == "title" and p.get("num"):
        m, sec = divmod(int(s["start"]), 60)
        print(f"{m}:{sec:02} {p['title']}")
PY
cat out/chapters.txt

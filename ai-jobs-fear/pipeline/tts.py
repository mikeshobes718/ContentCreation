"""Narrate every line with Kokoro (offline) and lay out the master timeline.

Writes into build/:
  narration.wav   the full voice track
  timeline.json   per-scene start/duration and per-line cue times
  subtitles.srt   sentence-level captions
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")
MODELS = os.environ.get("KOKORO_DIR", os.path.join(HERE, "..", "models"))
VOICE = os.environ.get("VOICE", "bm_george")
SPEED = float(os.environ.get("SPEED", "1.0"))

LEAD_IN = 0.55      # silence before the first line of a scene
GAP = 0.42          # between lines
TAIL = 0.85         # after the last line of a scene


def trim(sig, sr, thresh=0.01):
    idx = np.where(np.abs(sig) > thresh)[0]
    if len(idx) == 0:
        return sig
    a = max(0, idx[0] - int(0.03 * sr))
    b = min(len(sig), idx[-1] + int(0.08 * sr))
    return sig[a:b]


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    os.makedirs(os.path.join(BUILD, "lines"), exist_ok=True)
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    lang = "en-gb" if VOICE.startswith("b") else "en-us"

    sr = 24000
    track = []
    t = 0.0
    timeline, subs = [], []
    for si, sc in enumerate(SCENES):
        lines = sc["lines"]
        start = t
        cues = []
        if not lines:
            dur = sc.get("hold", 3.0)
            track.append(np.zeros(int(dur * sr), np.float32))
            t += dur
        else:
            track.append(np.zeros(int(LEAD_IN * sr), np.float32))
            t += LEAD_IN
            for li, line in enumerate(lines):
                spoken, shown = line if isinstance(line, tuple) else (line, line)
                cache = os.path.join(BUILD, "lines", f"s{si:02}_l{li:02}.wav")
                key = cache + ".txt"
                if os.path.exists(cache) and open(key).read() == f"{VOICE}|{SPEED}|{spoken}":
                    sig, _ = sf.read(cache, dtype="float32")
                else:
                    sig, sr = k.create(spoken, voice=VOICE, speed=SPEED, lang=lang)
                    sig = trim(sig.astype(np.float32), sr)
                    sf.write(cache, sig, sr)
                    open(key, "w").write(f"{VOICE}|{SPEED}|{spoken}")
                cues.append(t - start)
                subs.append((t, t + len(sig) / sr, shown))
                track.append(sig)
                t += len(sig) / sr
                gap = GAP if li < len(lines) - 1 else sc.get("tail", TAIL)
                track.append(np.zeros(int(gap * sr), np.float32))
                t += gap
            dur = t - start
        timeline.append(dict(index=si, visual=sc["visual"], start=start, dur=dur, cues=cues))
        print(f"scene {si:02} {sc['visual']:<10} {start:7.2f}s  +{dur:5.2f}s", file=sys.stderr)

    audio = np.concatenate(track)
    sf.write(os.path.join(BUILD, "narration.wav"), audio, sr)
    json.dump(dict(total=len(audio) / sr, scenes=timeline), open(os.path.join(BUILD, "timeline.json"), "w"), indent=1)
    with open(os.path.join(BUILD, "subtitles.srt"), "w") as f:
        for i, (a, b, s) in enumerate(subs, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n")
    print(f"total {len(audio) / sr / 60:.2f} min", file=sys.stderr)


if __name__ == "__main__":
    main()

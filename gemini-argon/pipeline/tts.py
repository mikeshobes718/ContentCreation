"""Narrate every line and lay out the master timeline.

Voice backends (VOICE_BACKEND):
  kokoro      offline Kokoro (default; needs models/ next to this project)
  elevenlabs  ElevenLabs API: ELEVENLABS_VOICE_ID (or ElevenLabsMyVoiceID), and the key either
              as a network secret on api.elevenlabs.io or in ELEVENLABS_API_KEY
  files       use WAVs you made elsewhere (your own recording, Qwen3-TTS on
              your Mac, ...). Put them in build/lines/ named as in
              build/lines_manifest.tsv, which this script always writes.

Writes into build/: narration.wav, timeline.json, subtitles.srt, lines_manifest.tsv
"""
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from script import SCENES  # noqa: E402

BUILD = os.path.join(HERE, "..", "build")
BACKEND = os.environ.get("VOICE_BACKEND", "kokoro")
SR = 24000

LEAD_IN = 0.5
GAP = 0.38
TAIL = 0.8


def trim(sig, thresh=0.01):
    idx = np.where(np.abs(sig) > thresh)[0]
    if len(idx) == 0:
        return sig
    a = max(0, idx[0] - int(0.03 * SR))
    b = min(len(sig), idx[-1] + int(0.08 * SR))
    return sig[a:b]


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


class Kokoro:
    def __init__(self):
        from kokoro_onnx import Kokoro as K
        models = os.environ.get("KOKORO_DIR", os.path.join(HERE, "..", "..", "ai-jobs-fear", "models"))
        self.k = K(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))
        self.voice = os.environ.get("VOICE", "bm_george")
        self.tag = f"kokoro:{self.voice}"

    def say(self, text, prev, nxt):
        sig, sr = self.k.create(text, voice=self.voice, speed=1.0, lang="en-gb" if self.voice.startswith("b") else "en-us")
        assert sr == SR
        return sig.astype(np.float32)


class ElevenLabs:
    def __init__(self):
        # The key is optional: with a network secret, the egress proxy adds xi-api-key itself.
        self.key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ElevenLabsAPIKey")
        self.voice = os.environ.get("ELEVENLABS_VOICE_ID") or os.environ["ElevenLabsMyVoiceID"]
        self.model = os.environ.get("ELEVENLABS_MODEL", "eleven_v4")
        self.settings = dict(stability=float(os.environ.get("EL_STABILITY", "0.45")),
                             similarity_boost=float(os.environ.get("EL_SIMILARITY", "0.85")),
                             style=float(os.environ.get("EL_STYLE", "0.15")),
                             use_speaker_boost=True)
        self.tag = f"elevenlabs:{self.voice}:{self.model}:{sorted(self.settings.items())}"

    def say(self, text, prev, nxt):
        body = dict(text=text, model_id=self.model, voice_settings=self.settings)
        # neighbouring lines keep intonation consistent across separate requests
        if prev:
            body["previous_text"] = prev
        if nxt:
            body["next_text"] = nxt
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}?output_format=mp3_44100_128",
            data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "Accept": "audio/mpeg", **({"xi-api-key": self.key} if self.key else {})})
        mp3 = urllib.request.urlopen(req, timeout=120).read()
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "-", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                             input=mp3, stdout=subprocess.PIPE, check=True).stdout
        return np.frombuffer(pcm, np.float32).copy()


class Files:
    tag = "files"

    def say(self, text, prev, nxt):
        raise FileNotFoundError("missing recording; see build/lines_manifest.tsv")


def spoken_and_shown(line):
    return line if isinstance(line, tuple) else (line, line)


def main():
    lines_dir = os.path.join(BUILD, "lines")
    os.makedirs(lines_dir, exist_ok=True)
    flat = [(si, li, *spoken_and_shown(l)) for si, sc in enumerate(SCENES) for li, l in enumerate(sc["lines"])]
    with open(os.path.join(BUILD, "lines_manifest.tsv"), "w") as f:
        for si, li, spoken, shown in flat:
            f.write(f"s{si:02}_l{li:02}.wav\t{shown}\n")

    voice = dict(kokoro=Kokoro, elevenlabs=ElevenLabs, files=Files)[BACKEND]()
    track, timeline, subs = [], [], []
    t = 0.0
    k = 0
    for si, sc in enumerate(SCENES):
        start, cues = t, []
        if not sc["lines"]:
            dur = sc.get("hold", 3.0)
            track.append(np.zeros(int(dur * SR), np.float32))
            t += dur
        else:
            track.append(np.zeros(int(LEAD_IN * SR), np.float32))
            t += LEAD_IN
            for li, line in enumerate(sc["lines"]):
                spoken, shown = spoken_and_shown(line)
                wav = os.path.join(lines_dir, f"s{si:02}_l{li:02}.wav")
                stamp = wav + ".txt"
                tag = f"{voice.tag}|{spoken}"
                fresh = os.path.exists(wav) and (BACKEND == "files" or (os.path.exists(stamp) and open(stamp).read() == tag))
                if fresh:
                    sig, sr = sf.read(wav, dtype="float32", always_2d=True)
                    sig = sig.mean(1)
                    if sr != SR:
                        sig = np.interp(np.arange(int(len(sig) * SR / sr)) * sr / SR, np.arange(len(sig)), sig).astype(np.float32)
                else:
                    prev = flat[k - 1][2] if k > 0 else None
                    nxt = flat[k + 1][2] if k + 1 < len(flat) else None
                    sig = voice.say(spoken, prev, nxt)
                    sf.write(wav, sig, SR)
                    open(stamp, "w").write(tag)
                    print(f"  voiced s{si:02}_l{li:02}", file=sys.stderr)
                sig = trim(sig)
                cues.append(t - start)
                subs.append((t, t + len(sig) / SR, shown))
                track.append(sig)
                t += len(sig) / SR
                gap = GAP if li < len(sc["lines"]) - 1 else sc.get("tail", TAIL)
                track.append(np.zeros(int(gap * SR), np.float32))
                t += gap
                k += 1
            dur = t - start
        timeline.append(dict(index=si, visual=sc["visual"], start=start, dur=dur, cues=cues))
        print(f"scene {si:02} {sc['visual']:<12} {start:7.2f}s  +{dur:5.2f}s", file=sys.stderr)

    audio = np.concatenate(track)
    sf.write(os.path.join(BUILD, "narration.wav"), audio, SR)
    json.dump(dict(total=len(audio) / SR, voice=voice.tag.split("|")[0], scenes=timeline),
              open(os.path.join(BUILD, "timeline.json"), "w"), indent=1)
    with open(os.path.join(BUILD, "subtitles.srt"), "w") as f:
        for i, (a, b, s) in enumerate(subs, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n")
    print(f"total {len(audio) / SR / 60:.2f} min ({voice.tag})", file=sys.stderr)


if __name__ == "__main__":
    main()

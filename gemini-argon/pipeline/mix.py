"""Synthesize an ambient score, duck it under the narration, and mix.

Writes build/music.wav and build/mix.wav (48 kHz stereo).
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")
SR = 48000

# A minor-ish drift: Am(add9) - Fmaj7 - Cmaj7 - Em7, 8 bars of slow pads
CHORDS = [
    [50, 57, 60, 64],   # D3 A3 C4 E4  (Dm9)
    [46, 53, 57, 62],   # Bb2 F3 A3 D4 (Bbmaj7)
    [53, 57, 60, 67],   # F3 A3 C4 G4  (Fadd9)
    [48, 55, 58, 62],   # C3 G3 Bb3 D4 (C7sus)
]
CHORD_LEN = 9.0


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad_voice(f, n, rng):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.12, 0.0, 0.11):
        ff = f * 2 ** (det / 12)
        ph = rng.uniform(0, 2 * np.pi)
        # soft, mostly-fundamental tone with a few quiet harmonics
        for h, amp in ((1, 1.0), (2, 0.28), (3, 0.1), (4, 0.05)):
            out += amp * np.sin(2 * np.pi * ff * h * t + ph * h)
    return out / 3


def reverb(x, secs=3.2, mix=0.35, seed=1):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 6.5 / secs)
    ir[: int(0.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return (1 - mix) * x + mix * wet * 0.6


def boom(n_len=3.5):
    n = int(n_len * SR)
    t = np.arange(n) / SR
    f = 30 + 55 * np.exp(-t * 3)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 1.4)
    noise = np.random.default_rng(3).normal(0, 1, n) * np.exp(-t * 9) * 0.12
    return (body + noise) * 0.9


def swell(n_len=1.6):
    n = int(n_len * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(5).normal(0, 1, n)
    # crude lowpass by moving average, rising envelope
    k = 40
    noise = np.convolve(noise, np.ones(k) / k, mode="same")
    return noise * (t / n_len) ** 3 * 0.5


def music(total, title_times):
    rng = np.random.default_rng(42)
    n = int((total + 2) * SR)
    out = np.zeros(n)
    t_all = np.arange(n) / SR
    step = int(CHORD_LEN * SR)
    xf = int(3.0 * SR)
    k = 0
    pos = 0
    while pos < n:
        seg_n = min(step + xf, n - pos)
        chord = CHORDS[k % len(CHORDS)]
        seg = sum(pad_voice(hz(m), seg_n, rng) for m in chord) / len(chord)
        env = np.ones(seg_n)
        a = min(xf, seg_n)
        env[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
        r = min(xf, seg_n)
        env[-r:] *= np.cos(np.linspace(0, np.pi / 2, r)) ** 2
        out[pos:pos + seg_n] += seg * env
        pos += step
        k += 1
    # slow breathing
    out *= 0.75 + 0.25 * np.sin(2 * np.pi * t_all / 13.0)
    # sparse high plucks (pentatonic over A minor)
    notes = [62, 65, 67, 69, 72, 74]
    pl = np.zeros(n)
    tt = 2.0
    while tt < total:
        m = notes[rng.integers(len(notes))] + 12 * rng.integers(0, 2)
        ln = int(2.5 * SR)
        i0 = int(tt * SR)
        if i0 + ln < n:
            tp = np.arange(ln) / SR
            pl[i0:i0 + ln] += np.sin(2 * np.pi * hz(m) * tp) * np.exp(-tp * 2.2) * 0.22
        tt += rng.choice([1.5, 2.25, 3.0, 4.5])
    out += pl
    # low sub drone
    out += 0.25 * np.sin(2 * np.pi * hz(38) * t_all) * (0.6 + 0.4 * np.sin(2 * np.pi * t_all / 17))
    # chapter hits
    for tt in title_times:
        i0 = int(tt * SR)
        b = boom()
        s = swell()
        e = min(n, i0 + len(b))
        out[i0:e] += b[: e - i0] * 1.6
        j0 = max(0, i0 - len(s))
        out[j0:i0] += s[len(s) - (i0 - j0):]
    out = reverb(out)
    out /= np.max(np.abs(out)) + 1e-9
    # tiny stereo spread via short delay
    d = int(0.011 * SR)
    left = out
    right = np.concatenate([np.zeros(d), out[:-d]])
    return np.stack([left, right], 1)


def main():
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    total = tl["total"]
    titles = [s["start"] for s in tl["scenes"] if s["visual"] == "title"]
    mus = music(total, titles)
    sf.write(os.path.join(BUILD, "music.wav"), mus.astype(np.float32), SR)

    # narration at 48k (high-quality resample via ffmpeg/soxr)
    n48 = os.path.join(BUILD, "narration48.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(BUILD, "narration.wav"),
                    "-af", "aresample=48000:resampler=soxr,highpass=f=70", "-ac", "1", n48], check=True)
    voice, _ = sf.read(n48, dtype="float64")
    n = len(mus)
    voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    voice /= np.max(np.abs(voice)) + 1e-9

    # ducking envelope from voice RMS
    win = int(0.05 * SR)
    rms = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, mode="same"))
    active = (rms > 0.02).astype(float)
    # smooth: fast attack, slow release
    env = np.zeros(n)
    a_att, a_rel = 1 - np.exp(-1 / (0.15 * SR)), 1 - np.exp(-1 / (0.9 * SR))
    # vectorized-ish one-pole on downsampled control signal
    hop = 480
    ctl = active[::hop]
    sm = np.zeros_like(ctl)
    v = 0.0
    for i, x in enumerate(ctl):
        coef = 1 - np.exp(-hop / ((0.15 if x > v else 0.9) * SR))
        v += (x - v) * coef
        sm[i] = v
    env = np.interp(np.arange(n), np.arange(len(sm)) * hop, sm)
    music_gain = 0.20 - 0.11 * env          # ~-14 dB under voice, -8 dB in the gaps
    mix = mus * music_gain[:, None] + voice[:, None] * 0.85
    # fade out the tail
    fo = int(3 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mix /= max(1.0, np.max(np.abs(mix)) / 0.98)
    sf.write(os.path.join(BUILD, "mix.wav"), mix.astype(np.float32), SR)
    print("mix written", mix.shape[0] / SR, "s")


if __name__ == "__main__":
    main()

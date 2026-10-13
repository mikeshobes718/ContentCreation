"""Render the visuals for every scene (Gemini Argon video) with Skia and encode them with ffmpeg.

Each scene is drawn by a function named after its `visual` key. Draw functions
get (canvas, t, S, p): t is seconds into the scene, S holds dur/cues, p the
scene params from script.py. Everything is drawn in a 1920x1080 space.

usage: python3 render.py [--preview SECONDS] [--only N,N] [--stills]
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import skia

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from script import SCENES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")
W, H, FPS = 1920, 1080, 24
PLATES = os.path.join(HERE, "..", "plates")
FONT_DIR = "/usr/share/fonts/opentype/inter"

# palette
BG = (6, 10, 18)
INK = (232, 237, 245)
MUTED = (125, 138, 163)
DIM = (52, 66, 92)
LINE = (24, 36, 58)
PANEL = (13, 20, 36)
GREEN = (43, 255, 136)
RED = (255, 72, 92)
BLUE = (110, 168, 255)


def col(rgb, a=1.0):
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), *rgb)


def paint(rgb=INK, a=1.0, stroke=None, blur=None, **kw):
    p = skia.Paint(Color=col(rgb, a), AntiAlias=True, **kw)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def inout(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ap(t, t0, d=0.6):
    """eased 0..1 progress of an animation starting at t0 lasting d."""
    return ease((t - t0) / d)


def cue(S, i, default=0.0):
    c = S["cues"]
    if not c:
        return default
    return c[min(i, len(c) - 1)]


def lerp(a, b, x):
    return a + (b - a) * x


# ------------------------------------------------------------------ text
_FONTS = {}


def font(name, size):
    key = (name, size)
    if key not in _FONTS:
        files = dict(reg="Inter-Regular", med="Inter-Medium", semi="Inter-SemiBold", bold="Inter-Bold",
                     light="Inter-Light", disp="InterDisplay-Bold", dispx="InterDisplay-ExtraBold",
                     displ="InterDisplay-Light", dispm="InterDisplay-Medium", dispi="InterDisplay-LightItalic",
                     ital="Inter-Italic")
        tf = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, files[name] + ".otf"))
        f = skia.Font(tf, size)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        _FONTS[key] = f
    return _FONTS[key]


def measure(s, f, track=0):
    return f.measureText(s) + track * max(0, len(s) - 1)


def txt(c, s, x, y, size=40, rgb=INK, a=1.0, face="reg", align="left", track=0, glow=0):
    f = font(face, size)
    w = measure(s, f, track)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if a <= 0.003:
        return w
    pts = [paint(rgb, a)]
    if glow:
        pts.insert(0, paint(rgb, a * 0.55, blur=glow))
    for pt in pts:
        if track:
            cx = x
            for ch in s:
                c.drawString(ch, cx, y, f, pt)
                cx += f.measureText(ch) + track
        else:
            c.drawString(s, x, y, f, pt)
    return w


def wrap(s, size, width, face="reg"):
    f = font(face, size)
    out, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if measure(trial, f) > width and cur:
            out.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


def para(c, s, x, y, size, width, rgb=INK, a=1.0, face="reg", lh=1.3, align="left"):
    lines = wrap(s, size, width, face)
    for i, ln in enumerate(lines):
        txt(c, ln, x, y + i * size * lh, size, rgb, a, face, align)
    return len(lines) * size * lh


def label(c, s, x, y, a=1.0, rgb=GREEN, size=22, align="left"):
    """small tracked uppercase label with a dot, Fern-style"""
    if align == "left":
        c.drawCircle(x + 5, y - size * 0.36, 5, paint(rgb, a))
        c.drawCircle(x + 5, y - size * 0.36, 10, paint(rgb, a * 0.5, blur=6))
        txt(c, s.upper(), x + 22, y, size, rgb, a, "semi", track=size * 0.14)
    else:
        txt(c, s.upper(), x, y, size, rgb, a, "semi", align=align, track=size * 0.14)


def source(c, s, a=1.0):
    txt(c, s, 96, H - 64, 20, MUTED, a * 0.85, "reg")


# ------------------------------------------------------------------ background / post
_GRAIN = None


def grain_images():
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(7)
        _GRAIN = []
        for _ in range(6):
            n = rng.normal(128, 40, (540, 960)).clip(0, 255).astype(np.uint8)
            rgba = np.dstack([n, n, n, np.full_like(n, 255)])
            _GRAIN.append(skia.Image.fromarray(np.ascontiguousarray(rgba)))
    return _GRAIN


def background(c, T):
    c.clear(col(BG))
    # slow drifting radial glows
    for (cx, cy, r, rgb, a, sp) in ((500, 300, 900, (14, 40, 70), 0.55, 0.05), (1500, 820, 800, (8, 60, 46), 0.35, 0.037)):
        x = cx + 140 * math.sin(T * sp)
        y = cy + 90 * math.cos(T * sp * 1.3)
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeRadial((x, y), r, [col(rgb, a), col(rgb, 0)]))
        c.drawRect(skia.Rect.MakeWH(W, H), p)
    # faint grid
    off = (T * 6) % 120
    gp = paint(LINE, 0.55, stroke=1)
    for gx in range(-120, W + 120, 120):
        c.drawLine(gx + off, 0, gx + off, H, gp)
    for gy in range(-120, H + 120, 120):
        c.drawLine(0, gy + off * 0.5, W, gy + off * 0.5, gp)


_VIG = None


def vignette():
    global _VIG
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.hypot(xx - W / 2, yy - H / 2) / 1150
        a = (np.clip((d - 0.55) / 0.45, 0, 1) ** 1.2 * 0.75 * 255).astype(np.uint8)
        z = np.zeros_like(a)
        _VIG = skia.Image.fromarray(np.ascontiguousarray(np.dstack([z, z, z, a])), colorType=skia.kRGBA_8888_ColorType,
                                    alphaType=skia.kUnpremul_AlphaType)
    return _VIG


def post(c, T, fi):
    c.drawImage(vignette(), 0, 0)
    # film grain
    g = grain_images()[fi % 6]
    gp = skia.Paint(Alphaf=0.07, BlendMode=skia.BlendMode.kOverlay)
    c.drawImageRect(g, skia.Rect.MakeWH(W, H), skia.SamplingOptions(), gp)


# ------------------------------------------------------------------ shared drawing bits
def poly(pts):
    path = skia.Path()
    path.moveTo(*pts[0])
    for q in pts[1:]:
        path.lineTo(*q)
    path.close()
    return path


def polyline(pts):
    path = skia.Path()
    if not pts:
        return path
    path.moveTo(*pts[0])
    for q in pts[1:]:
        path.lineTo(*q)
    return path


def partial(pts, frac):
    """first `frac` of a polyline (by point count, interpolated)"""
    if frac <= 0:
        return []
    n = (len(pts) - 1) * clamp(frac)
    i = int(n)
    out = pts[: i + 1]
    if i < len(pts) - 1:
        f = n - i
        a, b = pts[i], pts[i + 1]
        out = out + [(lerp(a[0], b[0], f), lerp(a[1], b[1], f))]
    return out


def glow_dot(c, x, y, r, rgb=GREEN, a=1.0):
    c.drawCircle(x, y, r * 3.2, paint(rgb, a * 0.35, blur=r * 2))
    c.drawCircle(x, y, r, paint(rgb, a))


def glow_line(c, path, rgb=GREEN, w=4, a=1.0):
    c.drawPath(path, paint(rgb, a * 0.45, stroke=w * 3, blur=w * 2))
    c.drawPath(path, paint(rgb, a, stroke=w))


def panel(c, x, y, w, h, a=1.0, border=LINE, r=18):
    rect = skia.Rect.MakeXYWH(x, y, w, h)
    c.drawRoundRect(rect, r, r, paint(PANEL, 0.92 * a))
    c.drawRoundRect(rect, r, r, paint(border, a, stroke=2))


def iso_box(c, cx, cy, a, b, h, top=(27, 39, 64), left=(17, 26, 44), right=(13, 21, 36), edge=(42, 58, 92), alpha=1.0):
    T = [(cx, cy - b - h), (cx + a, cy - h), (cx, cy + b - h), (cx - a, cy - h)]
    L = [(cx - a, cy - h), (cx, cy + b - h), (cx, cy + b), (cx - a, cy)]
    R = [(cx, cy + b - h), (cx + a, cy - h), (cx + a, cy), (cx, cy + b)]
    for pts, rgb in ((L, left), (R, right), (T, top)):
        c.drawPath(poly(pts), paint(rgb, alpha))
    c.drawPath(poly(T), paint(edge, alpha * 0.8, stroke=1.2))


# ================================================================== visuals
def v_title(c, t, S, p):
    dur = S["dur"]
    out = 1 - ap(t, dur - 0.6, 0.5)
    # orb
    oa = ap(t, 0, 1.4) * out
    orb = skia.Paint(AntiAlias=True)
    orb.setShader(skia.GradientShader.MakeRadial((960, 540), 520, [col(GREEN, 0.16 * oa), col(GREEN, 0)]))
    c.drawRect(skia.Rect.MakeWH(W, H), orb)
    if p.get("main"):
        la = ap(t, 0.3, 0.9) * out
        txt(c, p["title"], 960, 470 + (1 - la) * 24, 118, INK, la, "dispx", align="center")
        sa = ap(t, 1.1, 0.9) * out
        txt(c, p["sub"], 960, 600 + (1 - sa) * 20, 66, GREEN, sa, "disp", align="center", glow=14)
        lw = 900 * ap(t, 1.6, 1.2)
        c.drawLine(960 - lw / 2, 668, 960 + lw / 2, 668, paint(GREEN, out, stroke=3))
        c.drawLine(960 - lw / 2, 668, 960 + lw / 2, 668, paint(GREEN, 0.5 * out, stroke=8, blur=6))
        glow_dot(c, 960 + lw / 2, 668, 6, GREEN, out * (lw > 1))
    else:
        na = ap(t, 0.15, 0.6) * out
        txt(c, p["num"], 960, 430, 46, GREEN, na, "semi", align="center", track=10, glow=10)
        ta = ap(t, 0.45, 0.8) * out
        txt(c, p["title"], 960, 590 + (1 - ta) * 20, 120, INK, ta, "dispx", align="center")
        lw = 160 * ap(t, 0.8, 0.8)
        c.drawLine(960 - lw / 2, 470, 960 + lw / 2, 470, paint(GREEN, out, stroke=2))


def v_timeline(c, t, S, p):
    ev = p["events"]
    spacing = 560
    axis_y = 600
    active = 0
    for k, (_, _, ci) in enumerate(ev):
        if t >= cue(S, ci):
            active = k
    # camera follows the active event
    cam = 0.0
    for k, (_, _, ci) in enumerate(ev):
        cam += spacing * ap(t, cue(S, ci) - 0.2, 1.4) if k > 0 else 0
    base_x = 1060
    end_x = base_x + spacing * (len(ev) - 1) + 600
    ax = paint(LINE, 1, stroke=3)
    c.drawLine(-200, axis_y, end_x - cam, axis_y, paint(DIM, 1, stroke=2))
    for k, (year, lbl, ci) in enumerate(ev):
        x = base_x + k * spacing - cam
        a = ap(t, cue(S, ci), 0.7)
        if a <= 0:
            c.drawCircle(x, axis_y, 6, paint(DIM, 1))
            continue
        is_active = (k == active)
        rgb = GREEN if is_active else MUTED
        glow_dot(c, x, axis_y, 9 if is_active else 6, rgb, a)
        txt(c, year, x, axis_y - 70 - (1 - a) * 20, 110 if is_active else 80, INK if is_active else MUTED,
            a * (1 if is_active else 0.7), "disp", align="center")
        for li, ln in enumerate(wrap(lbl, 32, 460, "med")):
            txt(c, ln, x, axis_y + 80 + li * 44, 32, INK if is_active else MUTED, a * (1 if is_active else 0.6), "med", align="center")
    label(c, p.get("label", ""), 96, 120, ap(t, 0.2))


def v_bignum(c, t, S, p):
    t0 = 0.3
    v = p["value"] * ease((t - t0) / 1.8)
    s = f"{int(round(v)):,}{p['suffix']}"
    a = ap(t, t0, 0.5)
    txt(c, s, 96, 560, 280, GREEN, a, "dispx", glow=34)
    c.drawLine(104, 620, 104 + 700 * ap(t, 0.8, 1.2), 620, paint(GREEN, a, stroke=3))
    para(c, p["caption"], 104, 700, 46, 1300, INK, ap(t, 1.0, 0.8), "med")
    source(c, p["source"], ap(t, 1.4))


def v_quote(c, t, S, p):
    qa = ap(t, 0.2, 0.6)
    txt(c, "“", 120, 400, 300, GREEN, qa, "disp", glow=20)
    words = p["text"].split()
    lines = wrap(p["text"], 78, 1500, "displ")
    k = 0
    for li, ln in enumerate(lines):
        x = 260
        for wd in ln.split():
            wa = ap(t, 0.6 + k * 0.17, 0.5)
            w = txt(c, wd + " ", x, 400 + li * 104 + (1 - wa) * 12, 78, INK, wa, "displ")
            x += w
            k += 1
    aa = ap(t, 0.8 + len(words) * 0.17, 0.7)
    yb = 400 + len(lines) * 104 + 40
    c.drawLine(262, yb, 262 + 80 * aa, yb, paint(GREEN, aa, stroke=3))
    txt(c, p["who"], 262, yb + 60, 36, INK, aa, "semi")
    txt(c, p["src"], 262, yb + 106, 26, MUTED, aa, "reg")
    if p.get("extra"):
        ea = ap(t, cue(S, p["extra_cue"]) + 0.4, 0.7)
        txt(c, "…" + p["extra"], 1824, yb + 80, 54, GREEN, ea, "disp", align="right", glow=16)


def v_statement(c, t, S, p):
    a = ap(t, 0.3, 0.8)
    word = p["word"]
    f = font("dispx", 190)
    w = measure(word, f)
    txt(c, word, 960, 520, 190, INK, a, "dispx", align="center")
    # sweep highlight
    sw = (t - 0.8) / 1.6
    if 0 < sw < 1:
        sx = 960 - w / 2 + (w + 400) * sw - 200
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(sx - 120, 300, 240, 300))
        txt(c, word, 960, 520, 190, GREEN, a, "dispx", align="center", glow=20)
        c.restore()
    d = p["defn"]
    c1 = cue(S, 1) + 1.6
    n = int(len(d) * clamp((t - c1) / 2.0))
    if n > 0:
        txt(c, d[:n], 960, 660, 44, GREEN, 1, "med", align="center")
    c.drawLine(960 - w / 2, 572, 960 - w / 2 + w * ap(t, 0.9, 1.0), 572, paint(GREEN, a, stroke=3))


def v_cards(c, t, S, p):
    cards = p["cards"]
    n = len(cards)
    cw, ch, gap = 400, 440, 28
    x0 = (W - (n * cw + (n - 1) * gap)) / 2
    y0 = 330
    active = 0
    for k, cd in enumerate(cards):
        if t >= cue(S, cd[3]):
            active = k
    label(c, "Exhibits for the defence", 96, 140, ap(t, 0.2))
    for k, (head, l1, l2, ci) in enumerate(cards):
        a = ap(t, cue(S, ci), 0.6)
        if a <= 0:
            panel(c, x0 + k * (cw + gap), y0, cw, ch, 0.25)
            continue
        is_a = k == active
        x = x0 + k * (cw + gap)
        y = y0 + (1 - a) * 30 - (12 if is_a else 0)
        panel(c, x, y, cw, ch, a * (1 if is_a else 0.75), border=GREEN if is_a else LINE)
        txt(c, head, x + 34, y + 70, 30, GREEN if is_a else MUTED, a, "semi", track=6)
        para(c, l1, x + 34, y + 150, 34, cw - 68, INK, a * (1 if is_a else 0.7), "semi")
        para(c, l2, x + 34, y + 300, 28, cw - 68, MUTED, a * (1 if is_a else 0.7), "reg")


# ------------------------------------------------------------------ Blender plates


class PlateReader:
    """Sequential decoder for a Blender plate, upscaled to 1080p."""

    def __init__(self, name):
        path = os.path.join(PLATES, f"{name}.mp4")
        self.ok = os.path.exists(path)
        self.idx = -1
        self.img = None
        self.seconds = 1.0
        if self.ok:
            n = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0",
                                "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout.strip()
            self.seconds = int(n) / FPS
            self.proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={W}:{H}:flags=lanczos",
                 "-f", "rawvideo", "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)

    def frame(self, i):
        if not self.ok:
            return None
        while self.idx < i:
            buf = self.proc.stdout.read(W * H * 4)
            if len(buf) < W * H * 4:
                break
            self.idx += 1
            arr = np.frombuffer(buf, np.uint8).reshape(H, W, 4)
            self.img = skia.Image.fromarray(arr.copy())
        return self.img


_READERS = {}


def plate_image(name, S, t):
    key = (name, S["start"])
    if key not in _READERS:
        _READERS.clear()
        _READERS[key] = PlateReader(name)
    r = _READERS[key]
    speed = min(1.0, r.seconds / max(S["dur"], 0.1))
    return r.frame(int(t * FPS * speed))


def v_plate(c, t, S, p):
    img = plate_image(p["plate"], S, t)
    if img is not None:
        c.drawImage(img, 0, 0)
    else:
        txt(c, f"[plate: {p['plate']}]", 960, 540, 40, MUTED, 1, "med", align="center")
    # readability gradient for captions
    g = skia.Paint(AntiAlias=True)
    g.setShader(skia.GradientShader.MakeLinear([(0, H - 380), (0, H)], [col(BG, 0), col(BG, 0.85)]))
    c.drawRect(skia.Rect.MakeXYWH(0, H - 380, W, 380), g)
    label(c, p.get("label", ""), 96, 120, ap(t, 0.3))
    caps = p.get("caption", [])
    for k, (ci, text) in enumerate(caps):
        a = ap(t, cue(S, ci) + 0.3, 0.6)
        if k + 1 < len(caps):
            a *= 1 - ap(t, cue(S, caps[k + 1][0]) + 0.1, 0.4)
        txt(c, text, 96, H - 120 + (1 - a) * 16, 60, INK, a, "disp")


# ------------------------------------------------------------------ 2D visuals
def v_countdown(c, t, S, p):
    a = ap(t, 0.2)
    label(c, p["date"], 96, 120, a)
    n = p["days"]
    shown = int(n * clamp((t - 0.4) / 2.0))
    txt(c, f"{shown}", 96, 520, 300, GREEN, a, "dispx", glow=36)
    txt(c, "days later", 110, 610, 52, INK, a, "disp")
    for k in range(n):
        x = 110 + k * 46
        on = ap(t, 0.4 + 2.0 * k / n, 0.2)
        c.drawRoundRect(skia.Rect.MakeXYWH(x, 660, 30, 30), 6, 6, paint(GREEN if on > 0.5 else DIM, a))
    txt(c, "SEPT 30", 110, 730, 22, MUTED, a, "semi", track=3)
    txt(c, "OCT 13", 110 + (n - 1) * 46 + 30, 730, 22, GREEN, a, "semi", align="right", track=3)
    pa = ap(t, cue(S, 1) + 0.2, 0.7)
    x0, y0 = 1060, 240
    panel(c, x0, y0, 760, 600, pa, border=GREEN)
    txt(c, "NOW OPEN TO", x0 + 50, y0 + 80, 24, GREEN, pa, "semi", track=5)
    rows = [("Gemini app", "Pro & Ultra subscribers"), ("Gemini API", "paid tier developers"), ("Antigravity", "Ultra subscribers")]
    for k, (h, sub) in enumerate(rows):
        ra = ap(t, cue(S, 1) + 0.6 + k * 0.5, 0.5)
        yy = y0 + 160 + k * 92
        txt(c, h, x0 + 50, yy, 40, INK, ra, "semi")
        txt(c, sub, x0 + 710, yy, 28, MUTED, ra, "reg", align="right")
        c.drawLine(x0 + 50, yy + 28, x0 + 710, yy + 28, paint(LINE, ra, stroke=2))
    qa = ap(t, cue(S, 1) + 2.4, 0.6)
    txt(c, p["price"], x0 + 50, y0 + 520, 76, GREEN, qa, "dispx", glow=16)
    txt(c, p["unit"], x0 + 50, y0 + 566, 24, MUTED, qa, "reg")


def v_paper(c, t, S, p):
    a = ap(t, 0.2, 0.8)
    c.save()
    c.rotate(-3, 470, 560)
    x0, y0, w, h = 190, 150 + (1 - a) * 40, 560, 780
    c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 14, y0 + 18, w, h), 6, 6, paint((0, 0, 0), 0.5 * a, blur=18))
    c.drawRoundRect(skia.Rect.MakeXYWH(x0, y0, w, h), 6, 6, paint((236, 238, 242), a))
    dark = (30, 34, 44)
    txt(c, "Attention Is All You Need", x0 + w / 2, y0 + 90, 36, dark, a, "bold", align="center")
    for k in range(8):
        bx = x0 + 60 + (k % 4) * 115
        by = y0 + 140 + (k // 4) * 50
        c.drawRoundRect(skia.Rect.MakeXYWH(bx, by, 90, 12), 4, 4, paint((120, 126, 140), a))
        c.drawRoundRect(skia.Rect.MakeXYWH(bx + 10, by + 20, 70, 8), 3, 3, paint((180, 184, 194), a))
    txt(c, "Abstract", x0 + w / 2, y0 + 290, 22, dark, a, "semi", align="center")
    rng = random.Random(2)
    for k in range(18):
        lw = w - 120 - (rng.random() * 140 if k % 6 == 5 else 0)
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 60, y0 + 320 + k * 24, lw, 9), 3, 3, paint((190, 194, 202), a))
    c.restore()
    txt(c, "2017", 900, 260, 40, MUTED, a, "disp")
    txt(c, "8 researchers · Google", 900, 310, 30, MUTED, a, "med")
    # the Transformer
    ta = ap(t, cue(S, 1) + 0.3, 0.7)
    for k, (lbl, rgb) in enumerate((("Feed forward", BLUE), ("Attention", GREEN), ("Embeddings", MUTED))):
        yy = 400 + k * 110 + (1 - ta) * 20
        panel(c, 900, yy, 420, 86, ta, border=rgb, r=14)
        txt(c, lbl, 1110, yy + 56, 34, INK, ta, "semi", align="center")
    txt(c, "THE TRANSFORMER", 900, 760, 24, GREEN, ta, "semi", track=5)
    ga = ap(t, cue(S, 2) + 0.4, 0.7)
    x = 1420
    for ch, hl in (("Chat", False), ("G", False), ("P", False), ("T", True)):
        w_ = txt(c, ch, x, 560, 96, GREEN if hl else INK, ga, "dispx", glow=24 if hl else 0)
        x += w_ + (6 if ch != "Chat" else 14)
    txt(c, "Generative Pre-trained Transformer", 1420, 620, 26, MUTED, ga, "med")
    sa = ap(t, cue(S, 3) + 0.5, 0.4)
    if sa > 0:
        c.save()
        c.rotate(-10, 470, 900)
        rr = skia.Rect.MakeXYWH(250, 850, 440, 90)
        c.drawRoundRect(rr, 10, 10, paint(GREEN, sa, stroke=5))
        txt(c, "PUBLISHED OPENLY", 470, 912, 40, GREEN, sa, "bold", align="center", track=4)
        c.restore()


def v_search_money(c, t, S, p):
    a = ap(t, 0.2)
    x0, y0 = 120, 200
    c.drawRoundRect(skia.Rect.MakeXYWH(x0, y0, 900, 84), 42, 42, paint(PANEL, a))
    c.drawRoundRect(skia.Rect.MakeXYWH(x0, y0, 900, 84), 42, 42, paint(DIM, a, stroke=2))
    txt(c, "best running shoes for flat feet", x0 + 50, y0 + 54, 30, INK, a, "reg")
    ans = ap(t, cue(S, 1) + 0.4, 0.8)
    for k in range(5):
        yy = y0 + 140 + k * 118
        is_ad = k < 3
        ra = a * (1 - 0.75 * ans)
        if is_ad:
            panel(c, x0, yy, 72, 34, ra, border=GREEN, r=8)
            txt(c, "Ad", x0 + 36, yy + 25, 20, GREEN, ra, "semi", align="center")
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 90, yy + 6, 520 - k * 30, 18), 6, 6, paint(BLUE if is_ad else MUTED, ra * 0.8))
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 90, yy + 42, 760, 12), 5, 5, paint(DIM, ra))
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 90, yy + 66, 640, 12), 5, 5, paint(DIM, ra))
    if ans > 0:
        yy = y0 + 130 + (1 - ans) * 30
        panel(c, x0 - 10, yy, 920, 300, ans, border=GREEN)
        txt(c, "✨ AI answer", x0 + 30, yy + 60, 28, GREEN, ans, "semi")
        for k in range(4):
            c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 30, yy + 100 + k * 42, 820 - k * 90, 14), 6, 6, paint(INK, ans * 0.6))
        txt(c, "No click. No ad.", x0 + 30, yy + 280, 30, RED, ap(t, cue(S, 1) + 1.6), "semi")
    ma = ap(t, cue(S, 2) + 0.2, 0.5)
    v = p["value"] * ease((t - cue(S, 2) - 0.2) / 1.6)
    txt(c, f"${int(v)}B", 1150, 560, 200, GREEN, ma, "dispx", glow=30)
    para(c, p["label"], 1160, 640, 36, 650, INK, ma, "med")
    source(c, "Alphabet annual report: Google Search & other revenue, FY2022", ma)


def v_bard(c, t, S, p):
    a = ap(t, 0.2)
    x0 = 120
    panel(c, x0 + 260, 150, 860, 120, a, border=DIM, r=28)
    para(c, "What new discoveries from the James Webb Space Telescope can I tell my 9-year-old about?",
         x0 + 300, 200, 30, 780, INK, a, "reg")
    ba = ap(t, cue(S, 1) + 0.3, 0.6)
    panel(c, x0, 320, 1000, 200, ba, border=BLUE, r=28)
    txt(c, "Bard", x0 + 40, 372, 26, BLUE, ba, "semi")
    para(c, "JWST took the very first pictures of a planet outside of our own solar system.",
         x0 + 40, 425, 36, 920, INK, ba, "med")
    xa = ap(t, cue(S, 2) + 0.2, 0.4)
    if xa > 0:
        c.drawLine(x0 + 30, 470, x0 + 30 + 940 * xa, 410, paint(RED, 1, stroke=6))
        txt(c, "First exoplanet image: 2004, ESO’s Very Large Telescope", x0 + 40, 580, 30, RED, xa, "semi")
    # the stock
    sa = ap(t, cue(S, 3) + 0.1, 0.5)
    if sa > 0:
        gx0, gx1, gy = 1220, 1800, 360
        pts = []
        rng = random.Random(8)
        v = 0
        for k in range(41):
            v += rng.uniform(-6, 6)
            if k > 30:
                v += 22
            pts.append((lerp(gx0, gx1, k / 40), gy + 60 + v))
        seg = partial(pts, ap(t, cue(S, 3) + 0.1, 2.0))
        glow_line(c, polyline(seg), RED, 4, sa)
        txt(c, "ALPHABET (GOOGL)", gx0, gy - 40, 22, MUTED, sa, "semi", track=3)
        ka = ap(t, cue(S, 3) + 1.6, 0.6)
        txt(c, "−$100B", 1800, 760, 120, RED, ka, "dispx", align="right", glow=24)
        txt(c, "market value, in one day", 1800, 810, 30, MUTED, ka, "med", align="right")
    label(c, "FEB 2023", 96, 100, a)
    source(c, "NPR, Reuters, Feb 8, 2023", ap(t, cue(S, 3) + 1.6))


def v_merge(c, t, S, p):
    a = ap(t, 0.2)
    m = ap(t, 2.2, 1.6)
    r = 200
    lx = lerp(560, 960, m)
    rx = lerp(1360, 960, m)
    for x, name, rgb in ((lx, p["left"], BLUE), (rx, p["right"], GREEN)):
        c.drawCircle(x, 480, r, paint(rgb, 0.12 * a))
        c.drawCircle(x, 480, r, paint(rgb, a * (1 - m * 0.6), stroke=3))
        txt(c, name, x, 494, 44, INK, a * (1 - m), "disp", align="center")
    ma = ap(t, 3.4, 0.8)
    c.drawCircle(960, 480, r + 20, paint(GREEN, 0.3 * ma, blur=24))
    c.drawCircle(960, 480, r + 20, paint(GREEN, ma, stroke=4))
    txt(c, p["merged"], 960, 494, 48, INK, ma, "dispx", align="center")
    txt(c, p["lead"], 960, 780, 34, MUTED, ap(t, 4.0), "med", align="center")
    na = ap(t, cue(S, 1) + 0.3, 0.7)
    if na > 0:
        gold = (232, 190, 92)
        c.drawCircle(1620, 300, 90, paint(gold, 0.3 * na, blur=20))
        c.drawCircle(1620, 300, 80, paint(gold, na))
        c.drawCircle(1620, 300, 64, paint((180, 140, 60), na, stroke=3))
        txt(c, "NOBEL", 1620, 312, 30, (60, 44, 10), na, "bold", align="center", track=3)
        txt(c, "Chemistry, 2024", 1620, 440, 30, INK, na, "semi", align="center")
        txt(c, "protein structure prediction", 1620, 480, 24, MUTED, na, "reg", align="center")
    label(c, "The reorganisation", 96, 120, a)


def v_missed(c, t, S, p):
    a = ap(t, 0.2)
    wins = p["windows"]
    n = len(wins)
    x0, y = 260, 620
    bw = 300
    # which window the card is aiming at
    fails = [cue(S, 2) + 0.5, cue(S, 3) + 0.6, cue(S, 4) + 0.2, cue(S, 4) + 1.4]
    for k, mname in enumerate(wins):
        x = x0 + k * (bw + 40)
        fa = ap(t, fails[k], 0.35)
        panel(c, x, y, bw, 200, a, border=RED if fa > 0.5 else LINE)
        txt(c, mname, x + bw / 2, y + 120, 64, MUTED if fa < 0.5 else RED, a, "dispx", align="center")
        if fa > 0:
            c.drawLine(x + 40, y + 30, x + 40 + (bw - 80) * fa, y + 30 + 140 * fa, paint(RED, fa, stroke=6))
            c.drawLine(x + bw - 40, y + 30, x + bw - 40 - (bw - 80) * fa, y + 30 + 140 * fa, paint(RED, fa, stroke=6))
    # the promised model hopping between windows
    tgt = 0
    for k in range(n):
        if t > fails[k] + 0.4:
            tgt = min(n - 1, k + 1)
    cx = x0 + bw / 2 + tgt * (bw + 40)
    gone = ap(t, fails[-1] + 0.5, 0.6)
    ca = ap(t, cue(S, 1), 0.6) * (1 - gone)
    panel(c, cx - 230, 330, 460, 150, ca, border=BLUE)
    txt(c, p["promise"], cx, 410, 46, INK, ca, "disp", align="center")
    txt(c, p["said"], cx, 452, 24, MUTED, ca, "reg", align="center")
    if gone > 0:
        panel(c, 960 - 300, 330, 600, 150, gone, border=GREEN)
        txt(c, "Gemini 4 Argon", 960, 420, 60, GREEN, gone, "dispx", align="center", glow=14)
    label(c, "Google I/O, May 2026 →", 96, 120, a)
    source(c, "Bloomberg, Reuters (Jul–Aug 2026)", a)


def v_bench(c, t, S, p):
    a = ap(t, 0.2)
    label(c, p["title"], 96, 140, a)
    hl = p.get("hl", 0)
    maxv = max(v for _, v in p["bars"]) * 1.12
    for k, (name, val) in enumerate(p["bars"]):
        y = 300 + k * 190
        f = ap(t, 0.6 + k * 0.35, 1.4)
        w = 1150 * val / maxv * f
        rgb = GREEN if k == hl else DIM
        txt(c, name, 96, y + 20, 40, INK if k == hl else MUTED, a, "semi")
        r = skia.Rect.MakeXYWH(560, y - 30, w, 76)
        if k == hl:
            c.drawRoundRect(r, 10, 10, paint(GREEN, 0.3 * f, blur=18))
        c.drawRoundRect(r, 10, 10, paint(rgb, a))
        txt(c, f"{val * f:.1f}" if val % 1 else f"{int(round(val * f))}", 560 + w + 24, y + 26, 56,
            INK if k == hl else MUTED, f, "disp")
    source(c, p["src"], a)


def v_price(c, t, S, p):
    a = ap(t, 0.2)
    label(c, "Gemini 4 Argon API pricing", 96, 140, a)
    cards = [("LAUNCH PRICE", p["now"], "until " + p["until"], GREEN, cue(S, 1)), ("AFTER", p["later"], "standard price", MUTED, cue(S, 1) + 3.5)]
    for k, (head, (i, o), sub, rgb, t0) in enumerate(cards):
        ca = ap(t, t0, 0.7)
        x = 160 + k * 820
        panel(c, x, 260, 760, 470, ca, border=rgb)
        txt(c, head, x + 50, 340, 26, rgb, ca, "semi", track=5)
        txt(c, i, x + 50, 500, 150, INK, ca, "dispx")
        txt(c, "in", x + 50 + measure(i, font("dispx", 150)) + 16, 500, 36, MUTED, ca, "med")
        txt(c, o, x + 380, 500, 150, rgb if k == 0 else INK, ca, "dispx", glow=20 if k == 0 else 0)
        txt(c, "out", x + 380 + measure(o, font("dispx", 150)) + 16, 500, 36, MUTED, ca, "med")
        txt(c, "per million tokens · " + sub, x + 50, 580, 28, MUTED, ca, "reg")
    qa = ap(t, cue(S, 2) + 0.4, 0.7)
    txt(c, "Jefferies: rivals may be forced to cut prices", 960, 850, 50, INK, qa, "disp", align="center")
    txt(c, "Analyst comment, via Benzinga, October 2026", 960, 905, 26, MUTED, qa, "reg", align="center")


def v_end(c, t, S, p):
    l1, l2 = p["lines"]
    a1 = ap(t, cue(S, 0) + 0.5, 0.8)
    a2 = ap(t, cue(S, 1) + 0.4, 0.8)
    fin = ap(t, cue(S, 2) + 0.6, 0.8)
    dim = 1 - 0.6 * fin
    txt(c, l1, 960, 420, 84, INK, a1 * dim, "disp", align="center")
    txt(c, l2, 960, 560, 84, GREEN, a2 * dim, "disp", align="center", glow=16)
    out = 1 - ap(t, S["dur"] - 1.6, 1.2)
    txt(c, "Comeback, or very expensive catch-up?", 960, 760, 50, MUTED, fin * out, "dispi", align="center")


VISUALS = {k[2:]: v for k, v in globals().items() if k.startswith("v_")}


# ------------------------------------------------------------------ frame loop
def draw_frame(c, sc, S, fi, T):
    t = T - S["start"]
    background(c, T)
    fade = ap(t, 0, 0.45) * (1 - ap(t, S["dur"] - 0.4, 0.4))
    c.save()
    # slow camera push-in
    z = 1 + 0.035 * inout(t / max(S["dur"], 0.1))
    c.translate(W / 2, H / 2)
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    c.saveLayer(None, skia.Paint(Alphaf=fade))
    VISUALS[sc["visual"]](c, t, S, sc["p"])
    c.restore()
    c.restore()
    post(c, T, fi)


def render_scene(args):
    si, S, out, limit = args
    sc = SCENES[si]
    f0 = round(S["start"] * FPS)
    f1 = round((S["start"] + S["dur"]) * FPS)
    if limit:
        f1 = min(f1, f0 + int(limit * FPS))
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    enc = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-threads", "2", out], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        draw_frame(c, sc, S, fi, fi / FPS)
        enc.stdin.write(arr.tobytes())
    enc.stdin.close()
    enc.wait()
    return si, f1 - f0


def stills(timeline):
    os.makedirs(os.path.join(BUILD, "stills"), exist_ok=True)
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    for S in timeline["scenes"]:
        sc = SCENES[S["index"]]
        T = S["start"] + S["dur"] * 0.8
        draw_frame(c, sc, S, int(T * FPS), T)
        img = surf.makeImageSnapshot()
        img.save(os.path.join(BUILD, "stills", f"{S['index']:02}_{sc['visual']}.png"), skia.kPNG)


def thumbnail(path):
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    background(c, 3.0)
    S = dict(start=-1.0, dur=5.0, cues=[])
    img = plate_image("vault", S, 5.0)
    if img is not None:
        c.save()
        c.translate(380, 0)
        c.drawImage(img, 0, 0)
        c.restore()
    g = skia.Paint(AntiAlias=True)
    g.setShader(skia.GradientShader.MakeLinear([(0, 0), (1200, 0)], [col(BG, 0.95), col(BG, 0)]))
    c.drawRect(skia.Rect.MakeWH(W, H), g)
    txt(c, "GOOGLE", 90, 330, 150, INK, 1, "dispx")
    txt(c, "INVENTED IT.", 90, 490, 150, INK, 1, "dispx")
    txt(c, "THEN FELL", 90, 680, 150, GREEN, 1, "dispx", glow=30)
    txt(c, "BEHIND.", 90, 840, 150, GREEN, 1, "dispx", glow=30)
    post(c, 3.0, 0)
    surf.makeImageSnapshot().save(path, skia.kPNG)


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--thumbnail", default="")
    ap_.add_argument("--only", default="")
    ap_.add_argument("--preview", type=float, default=0)
    ap_.add_argument("--stills", action="store_true")
    ap_.add_argument("--jobs", type=int, default=4)
    args = ap_.parse_args()
    if args.thumbnail:
        thumbnail(args.thumbnail)
        return
    timeline = json.load(open(os.path.join(BUILD, "timeline.json")))
    if args.stills:
        stills(timeline)
        return
    only = {int(x) for x in args.only.split(",") if x}
    os.makedirs(os.path.join(BUILD, "segments"), exist_ok=True)
    jobs = []
    for S in timeline["scenes"]:
        if only and S["index"] not in only:
            continue
        out = os.path.join(BUILD, "segments", f"seg_{S['index']:02}.mp4")
        jobs.append((S["index"], S, out, args.preview))
    # longest first keeps the pool busy
    jobs.sort(key=lambda j: -j[1]["dur"])
    with Pool(args.jobs) as pool:
        for si, n in pool.imap_unordered(render_scene, jobs):
            print(f"scene {si:02} done ({n} frames)", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

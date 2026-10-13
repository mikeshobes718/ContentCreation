"""Render the visuals for every scene with Skia and encode them with ffmpeg.

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

from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")
W, H, FPS = 1920, 1080, 30
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
def v_office(c, t, S, p):
    cols, rows = 10, 8
    a, b = 92, 46
    ox, oy = 960, 250
    rng = random.Random(3)
    desks = [(i, j) for i in range(cols) for j in range(rows)]
    order = desks[:]
    rng.shuffle(order)
    n_off = int(len(desks) * p["off_frac"])
    t0 = cue(S, p["off_from"])
    span = max(1.0, (S["dur"] - t0) * 0.75)
    off_at = {d: t0 + span * (k / n_off) ** 0.8 for k, d in enumerate(order[:n_off])}
    pan = inout(t / S["dur"]) * 60
    for (i, j) in sorted(desks, key=lambda d: d[0] + d[1]):
        cx = ox + (i - j) * a + pan
        cy = oy + (i + j) * b
        intro = ap(t, 0.05 * (i + j) * 0.5, 0.8)
        if intro <= 0:
            continue
        cy += (1 - intro) * 40
        iso_box(c, cx, cy, a * 0.62, b * 0.62, 22, alpha=intro)
        # monitor on the back edge
        exv, eyv = (a, b), (-a, b)
        mx, my = cx - 0.18 * eyv[0], cy - 22 - 0.18 * eyv[1] - 4
        hw = 0.26
        mh = 34
        q = [(mx - hw * exv[0], my - hw * exv[1]), (mx + hw * exv[0], my + hw * exv[1]),
             (mx + hw * exv[0], my + hw * exv[1] - mh), (mx - hw * exv[0], my - hw * exv[1] - mh)]
        d = (i, j)
        on = 1.0
        if d in off_at:
            dt = t - off_at[d]
            if dt > 0:
                flick = 0.0 if dt > 0.35 else (0.6 if int(dt * 30) % 2 else 0.15)
                on = flick
        scr = tuple(int(lerp(26, v, on)) for v in (160, 255, 205)) if on > 0 else (26, 34, 51)
        if on > 0.2:
            c.drawPath(poly(q), paint(GREEN, 0.28 * on * intro, blur=14))
        c.drawPath(poly(q), paint(scr, intro))
        c.drawPath(poly(q), paint((60, 80, 110), intro * 0.7, stroke=1.2))
    la = ap(t, 0.3)
    label(c, p["label"], 96, 120, la)
    if S["cues"]:
        ba = ap(t, cue(S, 1), 0.8)
        txt(c, "Block, Inc.", 96, 980, 54, INK, ba, "disp")
        txt(c, "Square · Cash App · Afterpay · TIDAL", 96, 1020, 24, MUTED, ba, "reg")
        ra = ap(t, cue(S, 3), 0.8)
        txt(c, "Reason given:", 1824, 960, 26, MUTED, ra, "reg", align="right")
        txt(c, "AI", 1824, 1030, 72, GREEN, ra, "disp", align="right", glow=18)


def _walk(n, seed, vol=0.012):
    rng = random.Random(seed)
    v, out = 1.0, []
    for _ in range(n):
        v *= 1 + rng.uniform(-vol, vol)
        out.append(v)
    return out


def v_stock(c, t, S, p):
    x0, x1, y0, y1 = 140, 1780, 300, 900
    panel(c, x0 - 40, y0 - 120, x1 - x0 + 80, y1 - y0 + 200, ap(t, 0, 0.5))
    pre = _walk(70, 11 if not p.get("again") else 5)
    lo, hi = 0.85, 1.35
    def X(k):
        return x0 + 40 + (x1 - x0 - 120) * k / 90
    def Y(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)
    jump_cue = cue(S, 1)
    pts = [(X(k), Y(v)) for k, v in enumerate(pre)]
    last = pre[-1]
    post_pts = []
    rng = random.Random(4)
    v = last
    for k in range(70, 90):
        target = last * 1.21
        f = ease((k - 70) / 6)
        v = lerp(last, target, f) * (1 + rng.uniform(-0.006, 0.006))
        post_pts.append((X(k), Y(v)))
    draw_pre = partial(pts, ap(t, 0.2, 2.2))
    if len(draw_pre) > 1:
        # area fill
        area = polyline(draw_pre)
        area.lineTo(draw_pre[-1][0], y1)
        area.lineTo(draw_pre[0][0], y1)
        area.close()
        fp = skia.Paint(AntiAlias=True)
        fp.setShader(skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [col(BLUE, 0.18), col(BLUE, 0)]))
        c.drawPath(area, fp)
        glow_line(c, polyline(draw_pre), BLUE, 3)
    # market close marker
    ma = ap(t, 1.6, 0.6)
    dash = paint(MUTED, 0.6 * ma, stroke=2)
    dash.setPathEffect(skia.DashPathEffect.Make([10, 10], 0))
    c.drawLine(X(69.5), y0 - 20, X(69.5), y1, dash)
    txt(c, "MARKET CLOSE", X(69.5) - 14, y0 - 30, 18, MUTED, ma, "semi", align="right", track=3)
    txt(c, "AFTER HOURS", X(69.5) + 14, y0 - 30, 18, GREEN, ma, "semi", track=3)
    jf = ap(t, jump_cue, 1.4)
    if jf > 0:
        seg = partial([pts[-1]] + post_pts, jf)
        glow_line(c, polyline(seg), GREEN, 4)
        glow_dot(c, *seg[-1], 7)
        ja = ap(t, jump_cue + 0.6, 0.6)
        txt(c, "+20%", X(84), Y(last * 1.21) - 50, 110, GREEN, ja, "disp", align="right", glow=24)
    # headers
    ha = ap(t, 0.1)
    txt(c, p["name"], x0, y0 - 50, 40, INK, ha, "disp")
    if p.get("ticker"):
        txt(c, p["ticker"], x0 + measure(p["name"], font("disp", 40)) + 22, y0 - 50, 30, MUTED, ha, "med", track=4)
    if p.get("again"):
        ca = ap(t, cue(S, 0) + 1.2, 0.6)
        chip_x, chip_y = X(66) - 520, Y(last) + 110
        panel(c, chip_x, chip_y - 52, 500, 76, ca, border=GREEN, r=38)
        txt(c, "“… because of AI.”", chip_x + 250, chip_y - 2, 34, INK, ca, "ital", align="center")
        txt(c, "Illustrative", x1, y0 - 50, 22, MUTED, ha, "reg", align="right")
    if p.get("headcount") is not None:
        hc = ap(t, cue(S, 0) + 0.3, 0.7)
        bx = x0 + 10
        txt(c, "EMPLOYEES", bx, 1035 - 120 + 120, 20, MUTED, hc, "semi", track=4)
        txt(c, "10,000+", bx + 200, 1040, 44, INK, hc, "disp")
        txt(c, "→", bx + 390, 1040, 44, MUTED, ap(t, cue(S, 0) + 0.9), "disp")
        txt(c, "<6,000", bx + 460, 1040, 44, RED, ap(t, cue(S, 0) + 1.2), "disp", glow=10)


def person(c, x, y, s, rgb, a):
    c.drawCircle(x, y - s * 0.55, s * 0.36, paint(rgb, a))
    r = skia.Rect.MakeXYWH(x - s * 0.55, y - s * 0.1, s * 1.1, s * 0.8)
    c.drawRoundRect(r, s * 0.45, s * 0.45, paint(rgb, a))


def v_dots(c, t, S, p):
    cols, rows = 20, 10
    sx, sy, gap = 900, 260, 46
    rng = random.Random(9)
    idx = list(range(cols * rows))
    rng.shuffle(idx)
    lit = set(idx[: int(round(p["frac"] * cols * rows))])
    t0 = cue(S, p["cue"]) + 0.8
    for k in range(cols * rows):
        i, j = k % cols, k // cols
        x, y = sx + i * gap, sy + j * gap * 1.25
        ia = ap(t, 0.02 * (i + j) * 0.6, 0.6)
        rank = sorted(lit).index(k) if k in lit else 0
        on = ap(t, t0 + 2.2 * (idx.index(k) / len(idx)), 0.4) if k in lit else 0
        rgb = tuple(int(lerp(d, g, on)) for d, g in zip(DIM, GREEN))
        if on > 0.5:
            c.drawCircle(x, y - 4, 18, paint(GREEN, 0.18 * on, blur=10))
        person(c, x, y, 22, rgb, ia)
    na = ap(t, t0, 0.6)
    shown = int(round(p["frac"] * 100 * ease((t - t0) / 2.2))) if t > t0 else 0
    txt(c, f"{shown}%", 96, 520, 220, GREEN, na, "disp", glow=30)
    para(c, p["caption"], 104, 610, 38, 700, INK, na, "med")
    source(c, p["source"], na)


def v_title(c, t, S, p):
    dur = S["dur"]
    out = 1 - ap(t, dur - 0.6, 0.5)
    # orb
    oa = ap(t, 0, 1.4) * out
    orb = skia.Paint(AntiAlias=True)
    orb.setShader(skia.GradientShader.MakeRadial((960, 540), 520, [col(GREEN, 0.16 * oa), col(GREEN, 0)]))
    c.drawRect(skia.Rect.MakeWH(W, H), orb)
    if p.get("main"):
        title = p["title"]
        words = title.split()
        lines = [" ".join(words[:3]), " ".join(words[3:])]
        for li, ln in enumerate(lines):
            la = ap(t, 0.3 + li * 0.45, 0.9) * out
            txt(c, ln, 960, 480 + li * 130 + (1 - la) * 24, 124, INK, la, "dispx", align="center")
        lw = 900 * ap(t, 1.2, 1.2)
        c.drawLine(960 - lw / 2, 650, 960 + lw / 2, 650, paint(GREEN, out, stroke=3))
        c.drawLine(960 - lw / 2, 650, 960 + lw / 2, 650, paint(GREEN, 0.5 * out, stroke=8, blur=6))
        txt(c, p["sub"], 960, 720, 36, MUTED, ap(t, 1.8, 0.8) * out, "reg", align="center")
        glow_dot(c, 960 + lw / 2, 650, 6, GREEN, out * (lw > 1))
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
    label(c, "Two centuries of the same fear", 96, 120, ap(t, 0.2))


def v_atm(c, t, S, p):
    x0, x1, y0, y1 = 200, 1720, 260, 860
    ga = ap(t, 0, 0.6)
    c.drawLine(x0, y1, x1, y1, paint(DIM, ga, stroke=2))
    c.drawLine(x0, y0, x0, y1, paint(DIM, ga, stroke=2))
    txt(c, "1980", x0, y1 + 50, 26, MUTED, ga, "med")
    txt(c, "2010", x1, y1 + 50, 26, MUTED, ga, "med", align="right")
    N = 60
    atm = [(lerp(x0, x1, k / N), y1 - 30 - (y1 - y0 - 60) * (k / N) ** 1.6) for k in range(N + 1)]
    tell = [(lerp(x0, x1, k / N), y1 - 300 - 90 * math.sin(k / N * math.pi * 0.55) - 6 * math.sin(k * 0.7)) for k in range(N + 1)]
    fear = [(lerp(x0, x1, k / N), y1 - 300 + 260 * (k / N) ** 1.3) for k in range(N + 1)]
    c0, c1 = cue(S, 0), cue(S, 1)
    af = ap(t, c0 + 0.6, 3.0)
    if af > 0:
        seg = partial(atm, af)
        glow_line(c, polyline(seg), BLUE, 4)
        txt(c, "ATMs", seg[-1][0] - 10, seg[-1][1] - 24, 34, BLUE, ap(t, c0 + 2.6), "semi", align="right")
    # the assumption: tellers collapse (dashed red), fades when the truth arrives
    ff = ap(t, c0 + 2.2, 2.5) * (1 - ap(t, c1 + 0.4, 0.8))
    if ff > 0:
        seg = partial(fear, ap(t, c0 + 2.2, 2.5))
        dp = paint(RED, ff, stroke=4)
        dp.setPathEffect(skia.DashPathEffect.Make([14, 12], 0))
        c.drawPath(polyline(seg), dp)
        txt(c, "What everyone expected", seg[-1][0] - 10, seg[-1][1] + 50, 28, RED, ff, "med", align="right")
    tf = ap(t, c1 + 0.6, 3.0)
    if tf > 0:
        seg = partial(tell, tf)
        glow_line(c, polyline(seg), GREEN, 5)
        glow_dot(c, *seg[-1], 7)
        txt(c, "Bank tellers", seg[-1][0] - 10, seg[-1][1] - 30, 34, GREEN, ap(t, c1 + 2.8), "semi", align="right")
    label(c, "The ATM paradox", 96, 120, ap(t, 0.2))
    txt(c, "US, stylized", x0 + 20, y0 - 10, 22, MUTED, ga, "reg")
    source(c, "Shape stylized from James Bessen, “Toil and Technology” (IMF, 2015)", ga)


def v_bignum(c, t, S, p):
    t0 = 0.3
    v = p["value"] * ease((t - t0) / 1.8)
    s = f"{int(round(v)):,}{p['suffix']}"
    a = ap(t, t0, 0.5)
    txt(c, s, 96, 560, 280, GREEN, a, "dispx", glow=34)
    c.drawLine(104, 620, 104 + 700 * ap(t, 0.8, 1.2), 620, paint(GREEN, a, stroke=3))
    para(c, p["caption"], 104, 700, 46, 1300, INK, ap(t, 1.0, 0.8), "med")
    source(c, p["source"], ap(t, 1.4))


def v_muscle(c, t, S, p):
    a0 = ap(t, 0.3)
    txt(c, "MUSCLE", 560, 420, 150, MUTED, a0 * 0.8, "dispx", align="center")
    st = ap(t, 2.5, 0.6)
    w = measure("MUSCLE", font("dispx", 150))
    c.drawLine(560 - w / 2 - 20, 370, 560 - w / 2 - 20 + (w + 40) * st, 370, paint(RED, a0, stroke=8))
    ma = ap(t, 4.6, 0.8)
    txt(c, "MIND", 1360, 420, 150, GREEN, ma, "dispx", align="center", glow=30)
    txt(c, "then", 560, 220, 30, MUTED, a0, "semi", align="center", track=6)
    txt(c, "now", 1360, 220, 30, GREEN, ma, "semi", align="center", track=6)
    c1 = cue(S, 1)
    y = 560
    for k, wd in enumerate(p["words"]):
        wa = ap(t, c1 + 0.15 + k * 0.75, 0.5)
        fw = measure(wd, font("semi", 40)) + 70
        x = 1360 - fw / 2
        yy = y + k * 96 + (1 - wa) * 16
        panel(c, x, yy, fw, 72, wa, border=GREEN, r=36)
        txt(c, wd, 1360, yy + 50, 40, INK, wa, "semi", align="center")


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


def v_compare(c, t, S, p):
    side = 640
    bx, by = 1160, 220
    ga = ap(t, 0.2, 1.0)
    s = side * ga
    rect = skia.Rect.MakeXYWH(bx, by + side - s, s, s)
    c.drawRect(rect, paint(DIM, 0.35 * ga))
    c.drawRect(rect, paint(MUTED, ga, stroke=2))
    ratio = p["small"] / p["big"]
    ss = side * math.sqrt(ratio)
    sa = ap(t, cue(S, 1) + 0.3, 0.6)
    if sa > 0:
        r2 = skia.Rect.MakeXYWH(bx, by + side - ss, ss, ss)
        c.drawRect(r2, paint(GREEN, 0.5 * sa, blur=12))
        c.drawRect(r2, paint(GREEN, sa))
        # leader line to the label
        c.drawLine(bx + ss + 6, by + side - ss / 2, bx - 60, by + side - ss / 2 - 120, paint(GREEN, sa, stroke=2))
    txt(c, p["period"].upper(), 96, 200, 22, MUTED, ga, "semi", track=4)
    txt(c, "≈ 13.6 million", 96, 330, 92, INK, ga, "disp")
    txt(c, p["big_label"], 96, 384, 32, MUTED, ga, "med")
    txt(c, f"{p['small']:,}", 96, 640, 92, GREEN, sa, "disp", glow=16)
    txt(c, p["small_label"], 96, 694, 32, MUTED, sa, "med")
    pa = ap(t, cue(S, 1) + 1.6, 0.7)
    txt(c, f"≈ {ratio * 100:.1f}%", 96, 860, 120, GREEN, pa, "dispx", glow=24)
    source(c, p["source"], ga)


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


def v_canary(c, t, S, p):
    x0, x1, y0, y1 = 220, 1500, 250, 860
    ga = ap(t, cue(S, 1), 0.8)
    c.drawLine(x0, y1, x1, y1, paint(DIM, ga, stroke=2))
    c.drawLine(x0, y0, x0, y1, paint(DIM, ga, stroke=2))
    def Y(v):
        return y1 - (v - 80) / 30 * (y1 - y0)
    base = paint(MUTED, 0.5 * ga, stroke=2)
    base.setPathEffect(skia.DashPathEffect.Make([8, 10], 0))
    c.drawLine(x0, Y(100), x1, Y(100), base)
    txt(c, "100", x0 - 20, Y(100) + 10, 24, MUTED, ga, "med", align="right")
    for k, yr in enumerate(["2022", "2023", "2024", "2025"]):
        txt(c, yr, lerp(x0, x1, k / 3), y1 + 46, 24, MUTED, ga, "med", align="center")
    txt(c, "Employment in the most AI-exposed occupations (indexed, late 2022 = 100)", x0, y0 - 40, 26, MUTED, ga, "reg")
    N = 48
    def series(endv, wob, seed):
        rng = random.Random(seed)
        out = []
        for k in range(N + 1):
            f = k / N
            v = 100 + (endv - 100) * (max(0, f - 0.15) / 0.85) ** 1.3 + rng.uniform(-wob, wob)
            out.append((lerp(x0, x1, f), Y(v)))
        return out
    young = series(87, 0.5, 1)
    old = series(106, 0.5, 2)
    yf = ap(t, cue(S, 2) + 0.4, 3.5)
    if yf > 0:
        seg = partial(young, yf)
        glow_line(c, polyline(seg), RED, 5)
        glow_dot(c, *seg[-1], 7, RED)
        la = ap(t, cue(S, 2) + 3.0)
        txt(c, "Ages 22–25", x1 + 30, young[-1][1] - 6, 34, RED, la, "semi")
        txt(c, "≈ −13% relative", x1 + 30, young[-1][1] + 36, 28, RED, la, "reg")
    of = ap(t, cue(S, 3) + 0.2, 2.5)
    if of > 0:
        seg = partial(old, of)
        glow_line(c, polyline(seg), GREEN, 4)
        glow_dot(c, *seg[-1], 6)
        txt(c, "Older workers", x1 + 30, old[-1][1] + 10, 34, GREEN, ap(t, cue(S, 3) + 2.2), "semi")
    ta = ap(t, cue(S, 4) + 0.2, 0.8)
    txt(c, "“Canaries in the Coal Mine”", 960, 160, 54, INK, ta, "dispi", align="center")
    label(c, "The signal", 96, 120, ap(t, 0.2) * (1 - ta))
    source(c, p["src"], ga)


def v_split(c, t, S, p):
    for side, (h1, h2, bullets), t0 in (("L", p["left"], 0.2), ("R", p["right"], cue(S, p["right_cue"]))):
        a = ap(t, t0, 0.7)
        x = 96 if side == "L" else 1000
        rgb = RED if side == "L" else BLUE
        panel(c, x, 220, 824, 640, a, border=rgb)
        txt(c, h1, x + 50, 320, 36, MUTED, a, "semi", track=4)
        txt(c, h2, x + 50, 390, 60, rgb, a, "dispx", glow=12)
        for k, b in enumerate(bullets):
            ba = ap(t, t0 + 1.0 + k * 1.2, 0.6)
            yy = 500 + k * 160
            c.drawCircle(x + 62, yy - 12, 6, paint(rgb, ba))
            para(c, b, x + 90, yy, 32, 680, INK, ba, "med")
    va = ap(t, cue(S, p["right_cue"]) - 0.2, 0.5)
    c.drawCircle(960, 540, 44, paint(BG, va))
    c.drawCircle(960, 540, 44, paint(MUTED, va, stroke=2))
    txt(c, "vs", 960, 552, 30, INK, va, "semi", align="center")


def v_ladder(c, t, S, p):
    rungs = p["rungs"]
    n = len(rungs)
    cx, top, bot = 760, 150, 960
    railw = 220
    sp = (bot - top) / (n - 0.3)
    a = ap(t, 0.1, 0.8)
    gone_t = cue(S, p["cue"]) + 3.2
    # rails stop where the missing rungs begin
    g = ap(t, gone_t, 1.4)
    rail_bot = lerp(bot, top + sp * (n - p["gone"] - 0.5), g)
    for rx in (cx - railw / 2, cx + railw / 2):
        c.drawLine(rx, top, rx, rail_bot, paint(MUTED, a, stroke=8))
    for k, name in enumerate(rungs):
        y = top + sp * (k + 0.4)
        missing = k >= n - p["gone"]
        ra = a
        rgb = MUTED
        if missing:
            fl = ap(t, gone_t - 1.2, 0.5)
            rgb = tuple(int(lerp(m, r, fl)) for m, r in zip(MUTED, RED))
            ra = a * (1 - g)
            y += g * 40
        c.drawLine(cx - railw / 2, y, cx + railw / 2, y, paint(rgb, ra, stroke=10))
        txt(c, name, cx + railw / 2 + 50, y + 12, 36, INK if not missing else rgb, ra if missing else a * 0.9, "med")
        if missing and g > 0:
            dp = paint(RED, a * g * 0.7, stroke=2)
            dp.setPathEffect(skia.DashPathEffect.Make([8, 10], 0))
            c.drawLine(cx - railw / 2, y - 40 * g, cx + railw / 2, y - 40 * g, dp)
    label(c, "The first rung", 96, 120, a)
    # ghost job posting
    ja = ap(t, cue(S, 1) + 0.2, 0.7)
    if ja > 0:
        x, y = 1260, 640
        panel(c, x, y, 520, 220, ja * (1 - 0.5 * ap(t, cue(S, 1) + 2.2, 1.2)), border=LINE)
        txt(c, "Junior Analyst", x + 36, y + 70, 40, INK, ja * 0.6, "semi")
        txt(c, "Entry level · 0–2 yrs", x + 36, y + 116, 26, MUTED, ja * 0.6, "reg")
        st = ap(t, cue(S, 1) + 1.0, 0.4)
        c.save()
        c.rotate(-8, x + 260, y + 160)
        rr = skia.Rect.MakeXYWH(x + 120, y + 128, 280, 64)
        c.drawRoundRect(rr, 8, 8, paint(RED, st, stroke=4))
        txt(c, "NEVER POSTED", x + 260, y + 172, 30, RED, st, "bold", align="center", track=3)
        c.restore()


def v_megaphone(c, t, S, p):
    qa = ap(t, 0.2, 0.7)
    txt(c, "Fear", 300, 400, 150, INK, qa, "dispx", align="center")
    txt(c, ">", 560, 400, 150, GREEN, ap(t, 1.0), "dispx", align="center", glow=20)
    txt(c, "Data", 820, 400, 150, MUTED, ap(t, 1.4), "dispx", align="center")
    for k, item in enumerate(p["items"]):
        ia = ap(t, cue(S, k + 1), 0.6)
        is_a = all(t < cue(S, j + 1) for j in range(k + 1, len(p["items"])))
        y = 300 + k * 200
        x = 1100
        txt(c, f"0{k + 1}", x, y + 30 + (1 - ia) * 14, 36, GREEN if is_a else MUTED, ia, "semi", track=4)
        txt(c, item, x + 90, y + 34 + (1 - ia) * 14, 56, INK if is_a else MUTED, ia, "disp")
        c.drawLine(x, y + 80, x + 720 * ia, y + 80, paint(LINE, ia, stroke=2))


def v_bars(c, t, S, p):
    bars = p["bars"]
    base = 860
    maxv = 40
    label(c, p["title"], 96, 140, ap(t, 0.2))
    for k, (name, val) in enumerate(bars):
        x = 640 + k * 420
        f = ap(t, 0.5 + k * 0.6, 1.4)
        h = 560 * val / maxv * f
        rgb = GREEN if k == len(bars) - 1 else DIM
        r = skia.Rect.MakeXYWH(x, base - h, 240, h)
        if k == len(bars) - 1:
            c.drawRect(r, paint(GREEN, 0.35 * f, blur=20))
        c.drawRect(r, paint(rgb, 1))
        txt(c, f"{int(round(val * f))}%", x + 120, base - h - 30, 84, INK if k else MUTED, f, "disp", align="center")
        txt(c, name, x + 120, base + 56, 32, MUTED, ap(t, 0.3), "med", align="center")
    c.drawLine(560, base, 1440, base, paint(DIM, ap(t, 0.2), stroke=2))
    source(c, p["source"], ap(t, 0.5))


def gear_path(cx, cy, r, teeth, rot):
    path = skia.Path()
    n = teeth * 4
    for k in range(n + 1):
        ang = rot + 2 * math.pi * k / n
        rr = r * (1.0 if (k % 4) in (1, 2) else 0.84)
        pt = (cx + rr * math.cos(ang), cy + rr * math.sin(ang))
        if k == 0:
            path.moveTo(*pt)
        else:
            path.lineTo(*pt)
    path.close()
    path.addCircle(cx, cy, r * 0.35)
    return path


def v_hammer(c, t, S, p):
    a = ap(t, 0.2, 1.0)
    glow_line(c, gear_path(1250, 520, 260, 14, t * 0.25), GREEN, 3, a)
    glow_line(c, gear_path(1570, 300, 150, 9, -t * 0.25 * 14 / 9 + 0.1), GREEN, 3, a * 0.8)
    # hammer, mid-swing, frozen
    c.save()
    c.rotate(-28 + 6 * math.sin(t * 0.6), 700, 820)
    hp = paint(INK, a * 0.9, stroke=4)
    c.drawRoundRect(skia.Rect.MakeXYWH(684, 360, 32, 470), 10, 10, hp)
    c.drawRoundRect(skia.Rect.MakeXYWH(560, 300, 280, 110), 14, 14, hp)
    c.restore()
    txt(c, "1811", 96, 220, 60, MUTED, a, "disp")
    c1 = cue(S, 1)
    ea = ap(t, c1 + 4.5, 0.8)
    txt(c, "Hanged or transported.", 96, 980, 44, RED, ea, "semi")


def v_end(c, t, S, p):
    fa = ap(t, cue(S, 2) + 2.6, 0.8)
    for k, ln in enumerate(p["lines"]):
        a = ap(t, cue(S, k) + (0.6 if k == 0 else 0.2), 0.7) * (1 - fa)
        past = 1 - 0.55 * ap(t, cue(S, k + 1) if k + 1 < len(S["cues"]) else 1e9, 0.8)
        rgb = GREEN if k == 1 else INK
        if k == 0:
            # struck out: it's not the question
            txt(c, ln, 960, 380, 70, MUTED, a * past, "disp", align="center")
            w = measure(ln, font("disp", 70))
            c.drawLine(960 - w / 2, 356, 960 - w / 2 + w * ap(t, cue(S, 0) + 3.6, 0.6), 356, paint(RED, a, stroke=5))
        else:
            txt(c, ln, 960, 380 + k * 140, 70, rgb, a * past, "disp", align="center", glow=14 if k == 1 else 0)
    txt(c, "Not really.", 960, 560, 110, INK, ap(t, cue(S, 2) + 3.3, 0.8) * (1 - ap(t, S["dur"] - 1.6, 1.2)), "dispx", align="center")


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
    c.save()
    c.translate(420, 150)
    S = dict(dur=20.0, cues=[0.0, 1.0, 2.0, 3.0])
    v_office(c, 19.0, S, dict(off_from=0, off_frac=0.45, label=""))
    c.restore()
    c.drawRect(skia.Rect.MakeWH(W, H), paint(BG, 0.25))
    txt(c, "1 IN 5", 90, 470, 300, GREEN, 1, "dispx", glow=40)
    txt(c, "LAYOFFS NOW", 100, 600, 104, INK, 1, "dispx")
    txt(c, "BLAME AI", 100, 710, 104, INK, 1, "dispx")
    txt(c, "...but is it true?", 104, 800, 52, MUTED, 1, "ital")
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

"""Measure how much a reel looks and sounds like a phone video rather than an AI render.

Each number has a plain meaning (all measured on a 540 px wide copy, so reels of any size compare):
- shake_px: the camera's small hand wobble, frame to frame, after smoothing out deliberate moves. A tripod or an AI render is ~0.
- grain: sensor noise left in flat areas (Immerkaer's estimate). AI renders are unnaturally clean.
- sharpness: how crisp edges are (variance of the Laplacian). AI renders tend to be over-sharp and too even.
- saturation / contrast: colour strength and spread. AI renders tend to be punchier than a phone.
- room_tone_db: the quietest moments' level (dBFS). Real rooms hum; AI audio and clean edits fall to near silence.
"""
from __future__ import annotations

import subprocess

import cv2
import numpy as np

_K = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)


def _noise(gray: np.ndarray) -> float:
    """Immerkaer (1996) noise sigma, on the flattest half of the picture (edges excluded)."""
    h, w = gray.shape
    conv = np.abs(cv2.filter2D(gray, -1, _K))
    edges = cv2.Canny(gray.astype(np.uint8), 40, 120)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8))
    flat = conv[edges == 0]
    if flat.size < 1000:
        return 0.0
    return float(np.sqrt(np.pi / 2) * flat.mean() / 6)


def video(path: str, fps: float = 10, start: float = 0, length: float | None = None) -> dict:
    cap = cv2.VideoCapture(path)
    vfps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    step = max(1, round(vfps / fps))
    prev, moves, noise, sharp, sat, con = None, [], [], [], [], []
    i, end = 0, (start + length) * vfps if length else None
    while True:
        ok, fr = cap.read()
        if not ok or (end and i + start * vfps > end):
            break
        if i % step == 0:
            sc = 540 / fr.shape[1]
            small = cv2.resize(fr, (540, int(fr.shape[0] * sc)), interpolation=cv2.INTER_AREA)
            small = small[int(small.shape[0] * 0.08):int(small.shape[0] * 0.62)]   # skip caption bands and the corner mark
            g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
            noise.append(_noise(g)); sharp.append(float(cv2.Laplacian(g, cv2.CV_32F).var()))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            sat.append(float(hsv[..., 1].mean())); con.append(float(g.std()))
            if prev is not None:
                (dx, dy), resp = cv2.phaseCorrelate(prev, g, cv2.createHanningWindow(g.shape[::-1], cv2.CV_32F))
                moves.append((dx, dy) if resp > 0.2 and abs(dx) < 40 and abs(dy) < 40 else (np.nan, np.nan))   # a cut is not shake
            prev = g
        i += 1
    m = np.array(moves) if moves else np.zeros((1, 2))
    # wobble = how much each frame-to-frame move differs from its neighbours' average (pans and zooms cancel out)
    ok = ~np.isnan(m).any(1)
    jit = []
    for i in range(1, len(m) - 1):
        if ok[i - 1] and ok[i] and ok[i + 1]:
            jit.append(float(np.hypot(*(m[i] - (m[i - 1] + m[i + 1]) / 2))))
    return {"shake_px": round(float(np.median(jit)), 3) if jit else 0.0,
            "grain": round(float(np.median(noise)), 2) if noise else None,
            "sharpness": round(float(np.median(sharp)), 1) if sharp else None,
            "saturation": round(float(np.median(sat)), 1) if sat else None,
            "contrast": round(float(np.median(con)), 1) if con else None}


def room_tone_db(path: str) -> float | None:
    """Level of the quietest 10 % of 50 ms windows, in dBFS (None when there is no audio)."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True)
    a = np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768
    if a.size < 16000:
        return None
    n = 800
    rms = np.sqrt((a[: a.size // n * n].reshape(-1, n) ** 2).mean(1) + 1e-12)
    return round(float(20 * np.log10(np.percentile(rms, 10))), 1)


def measure(path: str, **kw) -> dict:
    return {**video(path, **kw), "room_tone_db": room_tone_db(path)}


# Phone footage ranges (DTJ's measurements, 21 Oct 2026: real phone reels and Harsh's AI winners).
PHONE = {"shake_px": (0.5, 1.6), "sharpness": (40, 650)}   # a handheld selfie wobbles more than a phone on a stand

if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("python scripts/realism.py <video.mp4> [...]  -> wobble, sharpness, grain, colour, room tone; flags what is outside phone range")
        raise SystemExit(1)
    for f in sys.argv[1:]:
        r = measure(f)
        off = {k: r[k] for k, (lo, hi) in PHONE.items() if r.get(k) is None or not lo <= r[k] <= hi}
        print(json.dumps({"file": f, **r, "reads_as_phone_footage": not off, "outside": off}, ensure_ascii=False))

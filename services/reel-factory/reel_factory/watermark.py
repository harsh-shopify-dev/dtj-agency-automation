"""Remove Google Flow's visible two-star sparkle from a raw 720x1280 Flow clip.

Harsh's decision (21 Oct 2026): remove it on every reel, with this exact method (senso-01 v5).
- The upper star never moves (573,1133, 54 px). The lower star drifts up to ~25 px; it is found per frame by shape match.
- LaMa (big-lama, Apache-2.0) repaints a 7 px-dilated star mask inside a 256 px window, feathered back. Run on raw clips,
  BEFORE any zoom, so the mark is always where we expect it.
- delogo (blurry box) and four formula methods (reverse alpha blend, temporal fill, per-frame alpha estimate) were tried and
  rejected: visible outlines or smears. Invisible SynthID is not touched.
"""
from __future__ import annotations

import subprocess

import cv2
import numpy as np

STATIC = (573, 1133, 54)                 # upper star: x, y, size (720x1280)
SEARCH = (500, 1060, 720, 1280)          # x0, y0, x1, y1 where the stars live
SIZES = range(48, 60, 2)
WINDOW = (464, 1024, 256)                # repaint window x0, y0, size


def _star(size: int, soft: bool, ss: int = 4, p: float = 0.62) -> np.ndarray:
    n = size * ss; c = (n - 1) / 2
    y, x = np.mgrid[0:n, 0:n]; u, v = np.abs(x - c) / (n / 2), np.abs(y - c) / (n / 2)
    m = cv2.resize(((u ** p + v ** p) <= 1).astype(np.float32), (size, size), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(m, (0, 0), 0.7) if soft else m


SHARP = {s: _star(s, False) for s in SIZES}
SOFT = {s: _star(s, True) for s in (*SIZES, STATIC[2])}


def find_moving(gray: np.ndarray, min_score: float = 0.45) -> tuple[int, int, int] | None:
    """The lower (moving) star: best shape match in the corner that is not the static star."""
    x0, y0, x1, y1 = SEARCH
    r = gray[y0:y1, x0:x1]
    hp = r - cv2.GaussianBlur(r, (0, 0), 8)
    cands = []
    for s, M in SHARP.items():
        m = cv2.matchTemplate(hp, M - M.mean(), cv2.TM_CCOEFF_NORMED)
        for _ in range(3):
            _, v, _, p = cv2.minMaxLoc(m)
            cands.append((v, p[0] + x0, p[1] + y0, s))
            m[max(0, p[1] - s // 2):p[1] + s // 2, max(0, p[0] - s // 2):p[0] + s // 2] = -1
    for v, x, y, s in sorted(cands, reverse=True):
        if v < min_score:
            return None
        if np.hypot(x - STATIC[0], y - STATIC[1]) > 20:
            return x, y, s
    return None


def star_mask(shape: tuple[int, int], stars: list[tuple[int, int, int]], grow: int = 7) -> np.ndarray:
    H, W = shape; P = 100
    mp = np.zeros((H + 2 * P, W + 2 * P), np.uint8)
    for x, y, s in stars:
        st = (SOFT.get(s, _star(s, True)) > 0.02).astype(np.uint8) * 255
        sh, sw = st.shape
        mp[y + P:y + P + sh, x + P:x + P + sw] |= st
    return cv2.dilate(mp[P:P + H, P:P + W], np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))


class Remover:
    def __init__(self):
        from simple_lama_inpainting import SimpleLama   # downloads big-lama.pt once (~196 MB) to the torch cache
        self.lama = SimpleLama()

    def frame(self, img: np.ndarray, stars: list[tuple[int, int, int]]) -> np.ndarray:
        x0, y0, S = WINDOW
        m = star_mask(img.shape[:2], stars)
        crop, mc = img[y0:y0 + S, x0:x0 + S], m[y0:y0 + S, x0:x0 + S]
        res = np.array(self.lama(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), mc))[:S, :S]
        res = cv2.cvtColor(res, cv2.COLOR_RGB2BGR).astype(np.float32)
        soft = cv2.GaussianBlur(mc.astype(np.float32) / 255, (0, 0), 2)[..., None]
        out = img.copy()
        out[y0:y0 + S, x0:x0 + S] = np.clip(crop * (1 - soft) + res * soft, 0, 255).astype(np.uint8)
        return out

    def clip(self, src: str, dst: str) -> dict:
        cap = cv2.VideoCapture(src)
        fps = cap.get(cv2.CAP_PROP_FPS); W, H = int(cap.get(3)), int(cap.get(4))
        if (W, H) != (720, 1280):
            raise ValueError(f"{src}: expected a raw 720x1280 Flow clip, got {W}x{H}")
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
                                "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "12", "-preset", "medium",
                                "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", dst], stdin=subprocess.PIPE)
        prev, found, n = None, 0, 0
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            mv = find_moving(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32))
            if mv:
                prev, found = mv, found + 1
            stars = [STATIC] + ([mv or prev] if (mv or prev) else [])
            enc.stdin.write(self.frame(fr, stars).tobytes()); n += 1
        enc.stdin.close(); enc.wait()
        if enc.returncode:
            raise RuntimeError(f"ffmpeg failed writing {dst}")
        return {"frames": n, "moving_star_found": found}


def corner_visible(path: str, every_s: float = 0.5) -> list[float]:
    """Times (s) where a sparkle still shows in the final 1080x1920 reel's bottom-right corner (shape match >= 0.55)."""
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step, i, hits = max(1, int(round(fps * every_s))), 0, []
    big = {s: cv2.resize(SHARP[s], (int(s * 1.5), int(s * 1.5))) for s in SIZES}
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % step == 0:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)[1500:1920, 680:1080]
            hp = g - cv2.GaussianBlur(g, (0, 0), 10)
            best = max(cv2.minMaxLoc(cv2.matchTemplate(hp, M - M.mean(), cv2.TM_CCOEFF_NORMED))[1] for M in big.values())
            if best >= 0.55:
                hits.append(round(i / fps, 2))
        i += 1
    return hits

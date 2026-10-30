"""Take checks: every scripted word spoken, the product stays in frame (no drops, floats, jumps), caption placement.

Lessons (book-01 v2, 20 Oct 2026): review takes at 4+ fps; a product that leaves the frame mid-clip, jumps, or is
swung fast is a REJECT. Motion peaks alone cannot reject a take (real handheld footage trips them too): report them for a look.
"""
from __future__ import annotations

import re

import cv2
import numpy as np

from .captions import bare


def words_check(heard: list[tuple[str, float, float]], line: str) -> dict:
    """Missing scripted words (digits count as their words: '10' = 'ten')."""
    nums = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
            "9": "nine", "10": "ten", "12": "twelve", "20": "twenty"}
    said = [nums.get(bare(w), bare(w)) for w, _, _ in heard]
    want = [bare(t) for t in line.split() if bare(t)]
    missing = [w for w in want if w not in said]
    span = (heard[0][1], heard[-1][2]) if heard else None
    return {"said": " ".join(w for w, _, _ in heard), "missing": missing, "speech": span,
            "ok": not missing and (bool(heard) or not want)}   # a silent shot (no line) has nothing to hear


class ProductTracker:
    """SIFT match of the product's front (a cut-out photo) in each frame."""

    def __init__(self, product_png: str):
        t = cv2.imread(product_png, cv2.IMREAD_GRAYSCALE)
        if t is None:
            raise FileNotFoundError(product_png)
        self.sift = cv2.SIFT_create(nfeatures=1500)
        self.k, self.d = self.sift.detectAndCompute(t, None)
        self.h, self.w = t.shape
        self.flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=40))

    def find(self, frame_bgr: np.ndarray) -> tuple[float, float, float] | None:
        g = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        sc = 540 / g.shape[1]; g = cv2.resize(g, (540, int(g.shape[0] * sc)))
        k, d = self.sift.detectAndCompute(g, None)
        if d is None or len(k) < 10:
            return None
        m = [a for a, b in self.flann.knnMatch(self.d, d, k=2) if a.distance < 0.75 * b.distance]
        if len(m) < 10:
            return None
        M, mask = cv2.findHomography(np.float32([self.k[a.queryIdx].pt for a in m]).reshape(-1, 1, 2),
                                     np.float32([k[a.trainIdx].pt for a in m]).reshape(-1, 1, 2), cv2.RANSAC, 6.0)
        if M is None or mask.sum() < 12:
            return None
        c = cv2.perspectiveTransform(np.float32([[0, 0], [self.w, 0], [self.w, self.h], [0, self.h]]).reshape(-1, 1, 2), M).reshape(-1, 2)
        gh, gw = g.shape
        if not cv2.isContourConvex(c.astype(np.int32)) or not 0.003 < cv2.contourArea(c) / (gw * gh) < 0.6:
            return None
        return float(c[:, 0].mean() / gw), float(c[:, 1].mean() / gh), float(c[:, 1].max() / gh)

    def take(self, path: str, fps: float = 8, expect_product: bool = True) -> dict:
        cap = cv2.VideoCapture(path); vfps = cap.get(cv2.CAP_PROP_FPS) or 24
        step, i, rows = max(1, round(vfps / fps)), 0, []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            if i % step == 0:
                rows.append((i / vfps, self.find(fr)))
            i += 1
        seen = [r[1] is not None for r in rows]
        issues = []
        first = next((j for j, s in enumerate(seen) if s), None)
        if expect_product and first is None:
            issues.append("product never visible")
        if first is not None:
            lost, run0 = [], None
            for j in range(first, len(seen)):
                if not seen[j] and run0 is None:
                    run0 = j
                if seen[j] and run0 is not None:
                    if j - run0 >= 2:
                        lost.append(round(rows[run0][0], 2))
                    run0 = None
            if run0 is not None and len(seen) - run0 >= 2:
                lost.append(round(rows[run0][0], 2))
            if lost:
                issues.append(f"product lost mid-clip at {lost}")
        jumps = [round(rows[j][0], 2) for j in range(1, len(rows)) if rows[j][1] and rows[j - 1][1]
                 and np.hypot(rows[j][1][0] - rows[j - 1][1][0], rows[j][1][1] - rows[j - 1][1][1]) > 0.12]
        if jumps:
            issues.append(f"product jumps at {jumps}")
        return {"visible_pct": round(100 * sum(seen) / max(len(seen), 1)), "issues": issues, "ok": not issues,
                "lowest_edge": max((r[1][2] for r in rows if r[1]), default=None)}


def caption_place(path: str, tracker: ProductTracker | None, bottom: float = 0.69, top: float = 0.14, half: float = 0.035) -> str:
    """'bottom' (Harsh's default) or 'top' only when the top band is empty AND the bottom band would cover the product."""
    cap = cv2.VideoCapture(path); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    covers, busy = 0, []
    for f in np.linspace(0, max(n - 1, 0), 8).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f)); ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (540, 960)); H, W = g.shape
        if tracker:
            hit = tracker.find(fr)
            if hit and abs(hit[1] - bottom) < 0.2:
                covers += 1
        band = g[int((top - half) * H):int((top + half) * H), int(0.2 * W):int(0.8 * W)]
        busy.append(float(cv2.Canny(band, 60, 150).mean() / 255))
    return "top" if covers >= 3 and busy and float(np.median(busy)) < 0.04 else "bottom"


def claims_in(text: str) -> list[str]:
    """Every number (with the word after it), big-number words, and result words in a line: each must be in the client's facts."""
    pats = [r"\d[\d,.]*\s*(%|[a-z]+)?",
            r"\b(hundred|thousand|lakh|crore|million)s?\b",
            r"\b(guarantee\w*|clinically|proven|cure\w*|best[- ]selling|bestseller|no\.?\s*1|number one|doctors?|dermatologists?)\b"]
    found, taken = [], []
    for p in pats:
        for m in re.finditer(p, text, re.I):
            if not any(a < m.end() and m.start() < b for a, b in taken):   # a part of a number already found is not a new claim
                taken.append(m.span()); found.append(m.group(0).strip())
    return found

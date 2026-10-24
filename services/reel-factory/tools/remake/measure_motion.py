"""Measure a reference edit's camera move on every frame of every shot: measure_motion.py <reference.mp4> <cut.json> <anchors> <out.json>

anchors = comma list of the time (s) inside each shot whose frame our picture was made from.
Per frame: the similarity transform from the anchor frame (scale, angle, dx, dy as fractions of the frame), how many SIFT
matches held (low = blurred or covered), the blur sigma that best turns the warped anchor into that frame, the leftover
change after the move (= animated things: smoke, embers, a flash) and the mean brightness (flash frames).
"""
import json
import sys

import cv2
import numpy as np

ref, cut_p, anchors_s, out_p = sys.argv[1:5]
cut = json.load(open(cut_p, encoding="utf-8"))
anchors = [float(a) for a in anchors_s.split(",")]
cap = cv2.VideoCapture(ref)
FPS = cap.get(cv2.CAP_PROP_FPS)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(cv2.resize(f, (360, 640), interpolation=cv2.INTER_AREA))
H, W = frames[0].shape[:2]
sift = cv2.SIFT_create(1500)
bf = cv2.BFMatcher(cv2.NORM_L2)


def feats(img):
    return sift.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)


def similarity(fa, fb):
    ka, da = fa
    kb, db = fb
    if da is None or db is None or len(ka) < 8 or len(kb) < 8:
        return None, 0
    good = [m for m, n in (p for p in bf.knnMatch(da, db, k=2) if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 8:
        return None, len(good)
    pa = np.float32([ka[m.queryIdx].pt for m in good])
    pb = np.float32([kb[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=4000)
    return M, int(inl.sum()) if inl is not None else 0


def decompose(M):
    s = float(np.hypot(M[0, 0], M[1, 0]))
    ang = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    # express as: zoom by s about the frame centre, then shift (dx, dy) in frame fractions
    c = np.array([W / 2, H / 2])
    moved = M[:, :2] @ c + M[:, 2]
    return s, ang, float((moved[0] - c[0]) / W), float((moved[1] - c[1]) / H)


def blur_sigma(pred, real):
    g_real = cv2.cvtColor(real, cv2.COLOR_BGR2GRAY).astype(np.float32)
    best, err0 = 0.0, None
    for s in (0, 0.7, 1.2, 2, 3, 4.5, 6.5, 9, 13):
        p = pred if s == 0 else cv2.GaussianBlur(pred, (0, 0), s)
        e = float(np.mean(np.abs(cv2.cvtColor(p, cv2.COLOR_BGR2GRAY).astype(np.float32) - g_real)))
        if err0 is None or e < err0:
            best, err0 = s, e
    return best, err0


shots = []
for k, s in enumerate(cut["segments"][:len(anchors)]):
    i0, i1 = int(round(s["t0"] * FPS)), int(round(s["t1"] * FPS))
    ia = min(max(int(round(anchors[k] * FPS)), i0), i1 - 1)
    fa = feats(frames[ia])
    rows, last = [], None
    for i in range(i0, i1):
        M, n = similarity(fa, feats(frames[i]))
        if M is None or n < 12:
            M = last                          # too blurred to match: keep the last good move (filled in below)
        row = {"t": round(i / FPS, 3), "matches": n, "lum": round(float(frames[i].mean()), 1)}
        if M is not None:
            sc, ang, dx, dy = decompose(M)
            pred = cv2.warpAffine(frames[ia], M, (W, H), borderMode=cv2.BORDER_REFLECT)
            sig, err = blur_sigma(pred, frames[i])
            row.update(scale=round(sc, 4), angle=round(ang, 3), dx=round(dx, 4), dy=round(dy, 4), blur=sig, residual=round(err, 1))
            last = M if n >= 12 else last
        rows.append(row)
    shots.append({"shot": k + 1, "anchor": anchors[k], "frames": rows})
    sc = [r.get("scale") for r in rows if "scale" in r]
    print(f"shot {k + 1:2d}: {len(rows)} frames, scale {min(sc) if sc else 0:.3f}-{max(sc) if sc else 0:.3f}, "
          f"weak matches {sum(r['matches'] < 12 for r in rows)}, max blur {max(r.get('blur', 0) for r in rows)}, "
          f"lum {min(r['lum'] for r in rows)}-{max(r['lum'] for r in rows)}")
json.dump({"fps": FPS, "shots": shots}, open(out_p, "w", encoding="utf-8"), indent=0)

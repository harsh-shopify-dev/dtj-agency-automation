"""Measure a reference edit's camera move on every frame of every shot: measure_motion.py <reference.mp4> <cut.json> <anchors> <out.json>

anchors = comma list of the time (s) inside each shot whose frame our picture was made from.
Per frame: the similarity transform from the anchor frame (scale, angle, dx, dy as fractions of the frame), how many SIFT
matches held (low = blurred or covered), the blur sigma that best turns the warped anchor into that frame, the leftover
change after the move (= animated things: smoke, embers, a flash) and the mean brightness (flash frames).
Also importable: measure(video, segments, anchors) -> {"fps", "shots"} (the watcher measures our own reel the same way).
"""
import json
import subprocess
import sys

import cv2
import numpy as np

W, H = 360, 640
sift = cv2.SIFT_create(1500)
bf = cv2.BFMatcher(cv2.NORM_L2)


def read_frames(path: str) -> tuple[list, float]:
    """Every frame at 360x640 (ffmpeg scales while decoding: fast on a 1080x1920 reel too)."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    return [np.frombuffer(raw, np.uint8, W * H * 3, i * W * H * 3).reshape(H, W, 3) for i in range(n)], fps


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


def measure(video: str, segments: list[dict], anchors: list[float], out=print) -> dict:
    frames, fps = read_frames(video)
    shots = []
    for k, s in enumerate(segments[:len(anchors)]):
        i0, i1 = int(round(s["t0"] * fps)), min(int(round(s["t1"] * fps)), len(frames))
        if i1 <= i0:
            break
        ia = min(max(int(round(anchors[k] * fps)), i0), i1 - 1)
        fa = feats(frames[ia])
        rows, last = [], None
        for i in range(i0, i1):
            M, n = similarity(fa, feats(frames[i]))
            if M is None or n < 12:
                M = last                          # too blurred to match: keep the last good move
            row = {"t": round(i / fps, 3), "matches": n, "lum": round(float(frames[i].mean()), 1)}
            if M is not None:
                sc, ang, dx, dy = decompose(M)
                pred = cv2.warpAffine(frames[ia], M, (W, H), borderMode=cv2.BORDER_REFLECT)
                sig, err = blur_sigma(pred, frames[i])
                row.update(scale=round(sc, 4), angle=round(ang, 3), dx=round(dx, 4), dy=round(dy, 4), blur=sig, residual=round(err, 1))
                last = M if n >= 12 else last
            rows.append(row)
        shots.append({"shot": k + 1, "anchor": anchors[k], "frames": rows})
        sc = [r.get("scale") for r in rows if "scale" in r]
        out(f"shot {k + 1:2d}: {len(rows)} frames, scale {min(sc) if sc else 0:.3f}-{max(sc) if sc else 0:.3f}, "
            f"weak matches {sum(r['matches'] < 12 for r in rows)}, max blur {max(r.get('blur', 0) for r in rows)}, "
            f"lum {min(r['lum'] for r in rows)}-{max(r['lum'] for r in rows)}")
    return {"fps": fps, "shots": shots}


if __name__ == "__main__":
    ref, cut_p, anchors_s, out_p = sys.argv[1:5]
    cut = json.load(open(cut_p, encoding="utf-8"))
    res = measure(ref, cut["segments"], [float(a) for a in anchors_s.split(",")])
    json.dump(res, open(out_p, "w", encoding="utf-8"), indent=0)

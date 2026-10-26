"""Paste the real pack artwork over small front-facing boxes an AI picture or clip garbled: fixpack.py <pack.png> <in> <out> [--show]

Each box front is found as a large red rectangle (the Mahalaxmi box is red with a blue band). The real front is resized onto it,
then relit with the generated box's own low-frequency light so it sits in the scene, and feathered at the edge.
A clip is done frame by frame; box positions are smoothed over time so the paste never jitters.
"""
import subprocess
import sys

import cv2
import numpy as np


def red_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = (((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 140) & (hsv[..., 2] > 90)).astype(np.uint8) * 255
    blue = ((hsv[..., 0] > 95) & (hsv[..., 0] < 115) & (hsv[..., 1] > 120) & (hsv[..., 2] > 120)).astype(np.uint8) * 255
    return m, blue


def boxes(img, ratio, min_h=60):
    m, blue = red_mask(img)
    k = max(3, img.shape[1] // 120)
    closed = cv2.morphologyEx(m | blue, cv2.MORPH_CLOSE, np.ones((k * 3, k * 3), np.uint8))
    cs, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    closed = cv2.drawContours(np.zeros_like(closed), cs, -1, 255, -1)      # fill the food photo inside the box
    n, lab, st, _ = cv2.connectedComponentsWithStats(closed)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if h < min_h or a < 0.6 * w * h:
            continue
        r = w / h
        if 0.75 * ratio < r < 1.3 * ratio and blue[y:y + h, x:x + w].mean() > 20:
            out.append((x, y, w, h))
    return sorted(out)


def bands(img, min_w):
    _, blue = red_mask(img)
    blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(blue)
    return sorted([tuple(st[i][:4]) for i in range(1, n) if st[i][2] >= min_w and 1.4 < st[i][2] / st[i][3] < 4.5])


def front_of(pack):
    b = boxes(pack, 0.75, 200)
    if not b:
        raise SystemExit("pack front not found")
    x, y, w, h = max(b, key=lambda t: t[2] * t[3])
    bx, by, bw, bh = max(bands(pack, 200), key=lambda t: t[2])
    rel = ((x - bx) / bw, (y - by) / bw, w / bw, h / bw)       # the box front measured in blue-band widths
    return pack[y:y + h, x:x + w], rel


def boxes_from_bands(img, rel, min_w=25):
    """Seed each box from its blue band, then measure its real edges: the bright pack red around the band."""
    H, W = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    pack = ((((hsv[..., 0] < 8) | (hsv[..., 0] > 172)) & (hsv[..., 1] > 150) & (hsv[..., 2] > 150))
            | ((hsv[..., 0] > 95) & (hsv[..., 0] < 115) & (hsv[..., 1] > 120) & (hsv[..., 2] > 120))).astype(np.uint8) * 255
    out = []
    for bx, by, bw, bh in bands(img, min_w):
        ex, ey, ew, eh = bx + rel[0] * bw, by + rel[1] * bw, rel[2] * bw, rel[3] * bw
        x0, y0 = int(max(0, ex - 0.25 * ew)), int(max(0, ey - 0.25 * eh))
        x1, y1 = int(min(W, ex + 1.25 * ew)), int(min(H, ey + 1.25 * eh))
        win = pack[y0:y1, x0:x1] > 0
        cx, cy = bx + bw // 2 - x0, by + bh // 2 - y0
        # rows/columns that are mostly pack colour, as a run outward from the band: the first gap is the box edge
        band_rows = slice(max(0, int(ey - y0)), int(ey - y0 + eh))
        colf = win[band_rows].mean(0)
        def run(f, c, thr):
            lo = hi = c
            while lo > 0 and f[lo - 1] > thr:
                lo -= 1
            while hi < len(f) - 1 and f[hi + 1] > thr:
                hi += 1
            return lo, hi
        l, r = run(colf, min(max(cx, 0), len(colf) - 1), 0.45)
        rowf = win[:, l:r + 1].mean(1)
        t, btm = run(rowf, min(max(cy, 0), len(rowf) - 1), 0.30)
        out.append((x0 + l, y0 + t, r - l + 1, btm - t + 1))
    return out


def paste(img, front, box):
    x, y, w, h = box
    src = cv2.resize(front, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
    gen = img[y:y + h, x:x + w].astype(np.float32)
    s = max(3, w // 6) | 1
    light = cv2.GaussianBlur(gen.mean(2), (s, s), 0) / np.maximum(cv2.GaussianBlur(src.mean(2), (s, s), 0), 8)
    out = np.clip(src * np.clip(light, 0.4, 1.6)[..., None], 0, 255)
    soft = np.zeros((h, w), np.float32)
    e = max(1, w // 60)
    soft[e:h - e, e:w - e] = 1
    soft = cv2.GaussianBlur(soft, (0, 0), e)[..., None]
    img[y:y + h, x:x + w] = (gen * (1 - soft) + out * soft).astype(np.uint8)
    return img


def main():
    pack_p, src, dst = sys.argv[1:4]
    front, rel = front_of(cv2.imread(pack_p))
    print("pack front", front.shape[1], "x", front.shape[0])
    manual = [tuple(int(v) for v in a.split(",")) for a in sys.argv[4:]]     # optional x,y,w,h per box, measured by a person
    if not src.lower().endswith((".mp4", ".mov")):
        img = cv2.imread(src)
        b = manual or boxes_from_bands(img, rel)
        print("boxes", b)
        for bx in b:
            paste(img, front, bx)
        cv2.imwrite(dst, img)
        return
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    found = [boxes_from_bands(f, rel) for f in frames]
    n = max(len(b) for b in found)
    tracks = []                                        # per box: median-smoothed position over a 9-frame window
    for j in range(n):
        seq = [b[j] if len(b) == n else None for b in found]
        tracks.append(seq)
    H, W = frames[0].shape[:2]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                            "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
    for i, f in enumerate(frames):
        for seq in tracks:
            win = [s for s in seq[max(0, i - 4):i + 5] if s]
            if not win:
                continue
            bx = tuple(int(np.median([s[k] for s in win])) for k in range(4))
            paste(f, front, bx)
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    enc.wait()
    print("boxes per frame", [len(b) for b in found[::24]])


if __name__ == "__main__":
    main()

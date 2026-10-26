"""Rebuild a reference reel's cut list with our own shots: recut.py <job>/cut.json

cut.json: {"size": [1080, 1920], "fps": 30, "music": "...", "out": "...", "corner": "...png", "corner_xy": [x, y],
           "label": "Video created using AI", "segments": [
             {"t0": 0, "t1": 1.93, "src": "images/p01.png", "move": "push"|"pull"|"rotate"|"none",
              "zoom": 0.06, "start": 0.0, "speed": 1.0, "in": "whip"|"zoom"|"blurin"|"cut",
              "out": "whip"|"zoom"|"mirror"|"punch"|"cut", "punch_at": [cx, cy], "corner": true}, ...]}
A still gets a slow camera move; a clip plays from "start" at "speed". "whip" = a fast horizontal slide with motion blur over
the cut (the reference's transition), "zoom" = a radial zoom blur over the cut. Effects: "mirror" = the frame shrinks with
mirrored edges, "punch" = a fast zoom into punch_at with radial blur, "blurin" = starts soft and closer, snaps sharp.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

job = Path(sys.argv[1]).parent
cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
W, H = cfg.get("size", [1080, 1920])
FPS = cfg.get("fps", 30)
TR = 6                                   # frames each side of a cut that carry a transition
FX = 9                                   # frames an in/out effect (mirror, punch, blur-in) takes, as in the reference


def cover(img, w=W, h=H):
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    img = cv2.resize(img, (round(iw * s), round(ih * s)), interpolation=cv2.INTER_LANCZOS4)
    y, x = (img.shape[0] - h) // 2, (img.shape[1] - w) // 2
    return img[y:y + h, x:x + w]


def zoom_at(img, z, cx=0.5, cy=0.5, ang=0.0):
    m = cv2.getRotationMatrix2D((W * cx, H * cy), ang, z)
    return cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


REF = json.loads((job / cfg["ref_motion"]).read_text(encoding="utf-8")) if cfg.get("ref_motion") else None


def ref_track(shot):
    """The reference's measured move for one shot (measure_motion.py), every frame filled: frames too blurred to match take the
    nearest measured move and the strongest blur."""
    rows = REF["shots"][shot - 1]["frames"]
    good = [i for i, r in enumerate(rows) if "scale" in r and r["scale"] > 0.3]
    out = []
    for i, r in enumerate(rows):
        if i in good:
            out.append(dict(r))
        else:
            j = min(good, key=lambda g: abs(g - i))
            out.append(dict(rows[j], blur=13))
    return out


def ref_matrix(r):
    m = cv2.getRotationMatrix2D((W / 2, H / 2), r.get("angle", 0.0), r["scale"])
    m[0, 2] += r["dx"] * W
    m[1, 2] += r["dy"] * H
    return m


def lerp_row(a, b, u):
    return {k: a[k] + (b[k] - a[k]) * u for k in ("scale", "angle", "dx", "dy")}


def ref_frame(img, track, t):
    """Replay the reference's camera move on our picture: same zoom, shift, turn and blur on the same frame. Fast moves are
    motion-blurred by averaging the in-between positions (a real shutter), slow ones get the measured softness."""
    fps = REF["fps"]
    k = min(max(int(round(t * fps)), 0), len(track) - 1)
    r, pa, na = track[k], track[max(k - 1, 0)], track[min(k + 1, len(track) - 1)]
    speed = max(abs(na["scale"] - pa["scale"]), abs(na["dx"] - pa["dx"]) * 4, abs(na["dy"] - pa["dy"]) * 4)
    if speed > 0.03:
        acc = np.zeros(img.shape, np.float32)
        n = 9
        for i in range(n):
            u = i / (n - 1)
            q = lerp_row(pa, r, 0.5 + 0.5 * u) if u < 0.5 else lerp_row(r, na, (u - 0.5))
            acc += cv2.warpAffine(img, ref_matrix(q), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        out = (acc / n).astype(np.uint8)
    else:
        out = cv2.warpAffine(img, ref_matrix(r), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    sig = r.get("blur", 0) * W / 360            # measured on a 360 px wide copy of the reference
    if speed > 0.03:
        sig *= 0.3                               # on a fast move the shutter blur above is the blur; a soft blur would hide the zoom
    return cv2.GaussianBlur(out, (0, 0), sig) if sig > 0.8 else out


class Source:
    def __init__(self, seg):
        self.seg = seg
        p = job / seg["src"]
        self.still = p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        if self.still:
            self.img = cover(cv2.imread(str(p)), int(W * 1.0), int(H * 1.0))
        else:
            cap = cv2.VideoCapture(str(p))
            self.vfps = cap.get(cv2.CAP_PROP_FPS) or 24
            self.frames = []
            while True:
                ok, f = cap.read()
                if not ok:
                    break
                self.frames.append(f)
            cap.release()

    def frame(self, t):                   # t = seconds into the segment (may be <0 or > length for transitions)
        s = self.seg
        dur = s["t1"] - s["t0"]
        u = min(max(t / dur, -0.3), 1.3)
        if self.still:
            img = self.img
        else:
            k = int((s.get("start", 0) + t * s.get("speed", 1.0)) * self.vfps)
            img = cover(self.frames[min(max(k, 0), len(self.frames) - 1)])
        mv, z = s.get("move", "push"), s.get("zoom", 0.06)
        if mv == "ref":
            if not hasattr(self, "track"):
                self.track = ref_track(s["shot"])
            return ref_frame(img if img.shape[:2] == (H, W) else cover(img), self.track, t)
        if mv == "push":
            return zoom_at(img, 1.0 + z * u, s.get("cx", 0.5), s.get("cy", 0.5))
        if mv == "pull":
            return zoom_at(img, 1.0 + z * (1 - u), s.get("cx", 0.5), s.get("cy", 0.5))
        if mv == "rotate":
            return zoom_at(img, 1.06 + z * u, 0.5, 0.5, ang=-4 * u)
        return img if img.shape[:2] == (H, W) else cover(img)


def hblur(img, r):
    r = int(r)
    if r < 2:
        return img
    k = np.zeros((1, r), np.float32)
    k[0, :] = 1.0 / r
    return cv2.filter2D(img, -1, k)


def whip_pair(a_img, b_img, p):            # p 0..1 across the cut: [outgoing | incoming] slides left, blurred by speed
    e = 0.5 - 0.5 * np.cos(np.pi * p)
    v = np.sin(np.pi * p)                 # speed, peaks at the cut
    strip = np.concatenate([a_img, b_img], axis=1)
    x = int(e * W)
    return hblur(strip[:, x:x + W].copy(), 4 + 220 * v)


def zoomblur(img, a, cx=0.5, cy=0.5, base=1.0):
    acc = np.zeros_like(img, np.float32)
    n = 8
    for i in range(n):
        acc += zoom_at(img, base * (1.0 + 0.35 * a * i / n), cx, cy)
    return (acc / n).astype(np.uint8)


# Effects measured on the reference's red "king" shots (24 Oct 2026):
def mirror_out(img, a):                    # the frame shrinks and mirrored copies fill the edges (shots 3, 7, 11)
    return zoom_at(img, 1.0 - 0.28 * a * a)


def zoom_punch(img, a, cx, cy):            # fast zoom into a point with radial blur, into the cut (shots 5, 9)
    return zoomblur(img, a, cx, cy, base=1.0 + 0.9 * a * a)


def blur_in(img, a):                       # starts soft and a little closer, snaps sharp (shots 13, 15)
    img = zoom_at(img, 1.0 + 0.12 * a)
    return cv2.GaussianBlur(img, (0, 0), 0.1 + 16 * a) if a > 0.02 else img


def overlay(dst, rgba, x, y):
    h, w = rgba.shape[:2]
    a = rgba[:, :, 3:4] / 255.0
    roi = dst[y:y + h, x:x + w]
    roi[:] = (roi * (1 - a) + rgba[:, :, :3] * a).astype(np.uint8)


def _font(size):
    """Arial on Windows, Noto/DejaVu on the VPS (Linux has no arial.ttf); Pillow's own font as the last resort."""
    for name in ("arial.ttf", "NotoSans-Regular.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def label_img(text, dark):
    if not text:
        return np.zeros((44, 520, 4), np.uint8)        # no label (the default since 25 Oct 2026: the AI label is added at posting)
    font = _font(26)
    im = Image.new("RGBA", (520, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if not dark:
        d.text((2, 8), text, font=font, fill=(0, 0, 0, 140))
    d.text((0, 6), text, font=font, fill=(90, 90, 90, 230) if dark else (255, 255, 255, 235))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGRA)


segs = cfg["segments"]
srcs = [Source(s) for s in segs]
corner = cv2.imread(str(job / cfg["corner"]), cv2.IMREAD_UNCHANGED) if cfg.get("corner") else None
lab_light, lab_dark = label_img(cfg.get("label", ""), False), label_img(cfg.get("label", ""), True)
total = segs[-1]["t1"]
out = job / cfg["out"]
raw = out.with_suffix(".video.mp4")
ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                       str(raw)], stdin=subprocess.PIPE)
nfr = round(total * FPS)
for n in range(nfr):
    t = n / FPS
    i = next(k for k, s in enumerate(segs) if t < s["t1"] or k == len(segs) - 1)
    s = segs[i]
    f = srcs[i].frame(t - s["t0"])
    to_end = round((s["t1"] - t) * FPS)          # frames left in this segment
    from_start = round((t - s["t0"]) * FPS)
    nxt = segs[i + 1] if i + 1 < len(segs) else None
    prv = segs[i - 1] if i > 0 else None
    if s.get("out", "cut") == "whip" and to_end <= TR and nxt:
        p = 0.5 * (1 - to_end / TR)                     # 0 -> 0.5 up to the cut
        f = whip_pair(f, srcs[i + 1].frame(0), p)
    elif s.get("out", "cut") == "zoom" and to_end <= TR:
        f = zoomblur(f, 1 - to_end / TR)
    elif s.get("out", "cut") == "mirror" and to_end <= FX:
        f = mirror_out(f, 1 - to_end / FX)
    elif s.get("out", "cut") == "punch" and to_end <= FX:
        f = zoom_punch(f, 1 - to_end / FX, *s.get("punch_at", (0.5, 0.5)))
    if s.get("in", "cut") == "whip" and from_start < TR and prv:
        p = 0.5 + 0.5 * from_start / TR                 # 0.5 -> 1 after the cut
        f = whip_pair(srcs[i - 1].frame(prv["t1"] - prv["t0"]), f, p)
    elif s.get("in", "cut") == "zoom" and from_start < TR:
        f = zoomblur(f, 1 - from_start / TR)
    elif s.get("in", "cut") == "blurin" and from_start < FX:
        f = blur_in(f, (1 - from_start / FX) ** 2)
    if s.get("pop") and from_start < 9:                  # end card logo pop
        f = zoom_at(f, 0.85 + 0.15 * min(1, from_start / 8) ** 0.5)
    if corner is not None and s.get("corner", True):
        overlay(f, corner, *cfg["corner_xy"])
    if cfg.get("label"):
        lab = lab_dark if s.get("light_bg") else lab_light
        overlay(f, lab, 48, H - 150)
    ff.stdin.write(f.tobytes())
ff.stdin.close()
ff.wait()
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-i", str(job / cfg["music"]), "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
               check=True)
raw.unlink()
print("wrote", out, f"{nfr / FPS:.2f}s")

"""Give a finished, caption-free edit the measured phone-camera look: edge-keeping soften + a slow hand wobble.

    python scripts/phone_look.py in.mp4 out.mp4            (1080x1920 in, 1080x1920 out, audio copied)
    python scripts/phone_look.py in.mp4 out.mp4 --wobble 1.5 --no-soften     force the settings instead of measuring first

Why: raw Omni Flash takes are tripod-steady (wobble 0.20-0.26 px) and hyper-detailed (sharpness 1,058-1,517), while real phone
reels and Harsh's AI winners measure 0.73-0.86 px and 47-614 (scripts/realism.py). Wobble 1.5 + this soften lands at ~0.73-0.94 px
and ~270, with eyes, glasses and the book's title still crisp. Run it BEFORE burning captions, so the captions stay still.
By default it measures the clip first and adds only what is missing: a clip prompted as a handheld selfie already wobbles
(book-01 g4: 1.36 px), so it gets no extra wobble; a clip already under sharpness 650 gets no soften.
"""
from __future__ import annotations

import argparse
import subprocess

SOFTEN = "smartblur=lr=2.0:ls=0.8:lt=-3"


def wobble(a: float, seed: int = 0) -> str:
    ph = [(seed * 1.7 + k * 0.9) % 6.28 for k in range(6)]
    x = f"(iw-ow)/2+{a}*(sin(2*PI*t*0.47+{ph[0]:.2f})+0.7*sin(2*PI*t*1.13+{ph[1]:.2f})+0.2*sin(2*PI*t*3.1+{ph[2]:.2f}))"
    y = f"(ih-oh)/2+{a}*(sin(2*PI*t*0.39+{ph[3]:.2f})+0.7*sin(2*PI*t*0.97+{ph[4]:.2f})+0.2*sin(2*PI*t*2.7+{ph[5]:.2f}))"
    return f"scale=iw*1.03:-2,crop=1080:1920:'{x}':'{y}'"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--wobble", type=float, help="force this wobble (px); 0 = none")
    ap.add_argument("--no-soften", action="store_true")
    a = ap.parse_args(argv)
    soften, wob = not a.no_soften, a.wobble
    if wob is None:
        from realism import video
        m = video(a.src, length=8)
        wob = 1.5 if m["shake_px"] < 0.5 else 0
        soften = soften and (m["sharpness"] or 0) > 650
        print(f"measured: wobble {m['shake_px']} px, sharpness {m['sharpness']} -> add wobble {wob}, soften {soften}")
    vf = "scale=1080:1920:flags=bicubic" + (f",{SOFTEN}" if soften else "") + (f",{wobble(wob)}" if wob else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-vf", vf + ",format=yuv420p", "-c:v", "libx264", "-crf", "18",
                    "-preset", "medium", "-c:a", "copy", "-movflags", "+faststart", a.dst], check=True)
    print(f"wrote {a.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

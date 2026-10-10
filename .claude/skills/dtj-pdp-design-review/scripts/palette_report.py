"""Measure the colours of a product page from its screenshots and check them against a vibe profile.

    python palette_report.py SHOT.png [SHOT2.png ...] --profile electric [--out DIR] [--skip-top 120] [--mask page-audit.json]
    python palette_report.py --contrast "#082A45:#12BEE9" "#FFFFFF:#082A45"

Blank padding under a short page (a tall headless window) is trimmed automatically: it would count as "white" and hide a dull
page's real numbers. With --mask (the JSON from page_audit.js, whose `images` list has each picture's page box and the page
width), pictures are blanked out and a second set of metrics, `ui_only`, measures OUR design without the client's photos: judge
the vibe on `ui_only` when the photos are loud (a bright pack banner can make a pale page look colourful).

Prints a JSON report (dominant colours with their share of the page, the vibe metrics, each target pass/fail, a fit score) and,
with --out, writes palette.json and palette.png (a swatch strip). Deterministic: the same screenshots give the same numbers.
Needs Pillow and numpy only. Photos count as page colour: read the numbers together with the screenshots, not instead of them.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PROFILES = json.loads((HERE / "vibe_profiles.json").read_text(encoding="utf-8"))["profiles"]


def drop_blank_runs(im: Image.Image, keep: np.ndarray | None = None, min_run: int = 300):
    """Remove every fully blank horizontal stretch taller than min_run px: a short page in a tall window gets empty space (often
    between the content and a footer pushed to the bottom), which would count as page white. Real white sections have content
    more often than every 300 px. Returns the image (and the mask rows, kept in step)."""
    a = np.asarray(im.convert("L"))
    blank = ~(a < 250).any(axis=1)
    rows = np.ones(len(blank), dtype=bool)
    start = None
    for i, b in enumerate(np.append(blank, False)):
        if b and start is None:
            start = i
        elif not b and start is not None:
            if i - start > min_run:
                rows[start + 12:i - 12] = False  # keep a little margin on each side
            start = None
    arr = np.asarray(im)[rows]
    return Image.fromarray(arr), (keep[rows] if keep is not None else None)


def load_pixels(paths: list[str], skip_top: int = 0, width: int = 360, mask: dict | None = None) -> np.ndarray:
    """Pixels of all shots, downscaled. With a mask, picture boxes are dropped (only the first shot is masked: the full page)."""
    chunks = []
    for n, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        keep = np.ones((im.height, im.width), dtype=bool)
        if mask and n == 0:  # boxes are in page coordinates: mask BEFORE removing blank stretches
            scale = im.width / float(mask.get("page_width") or im.width)
            for box in mask.get("images", []):
                x, y, w, h = (int(round(v * scale)) for v in (box["x"], box["y"], box["w"], box["h"]))
                keep[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = False
        im, keep = drop_blank_runs(im, keep)
        if skip_top:
            im = im.crop((0, min(skip_top, im.height - 1), im.width, im.height))
            keep = keep[min(skip_top, keep.shape[0] - 1):]
        h = max(1, round(im.height * width / im.width))
        px = np.asarray(im.resize((width, h), Image.BILINEAR), dtype=np.float64) / 255.0
        k = np.asarray(Image.fromarray(keep.astype(np.uint8) * 255).resize((width, h), Image.NEAREST)) > 127
        chunks.append(px[k] if mask and n == 0 else px.reshape(-1, 3))
    return np.concatenate(chunks)


def hls(px: np.ndarray) -> np.ndarray:
    mx, mn = px.max(1), px.min(1)
    light = (mx + mn) / 2
    d = mx - mn
    denom = np.where(light > 0.5, 2 - mx - mn, mx + mn)
    sat = np.divide(d, denom, out=np.zeros_like(d), where=(d > 0) & (denom > 0))
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    hue = np.zeros_like(mx)
    m = d > 0
    rc = np.where(m, (mx - r) / (d + 1e-9), 0)
    gc = np.where(m, (mx - g) / (d + 1e-9), 0)
    bc = np.where(m, (mx - b) / (d + 1e-9), 0)
    hue = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
    hue = np.where(m, (hue / 6.0) % 1.0, 0) * 360
    return np.stack([hue, light, sat], 1)


def colourfulness(px: np.ndarray) -> float:
    r, g, b = px[:, 0] * 255, px[:, 1] * 255, px[:, 2] * 255
    rg, yb = r - g, 0.5 * (r + g) - b
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def kmeans(px: np.ndarray, k: int = 8, iters: int = 12) -> tuple[np.ndarray, np.ndarray]:
    sample = px[:: max(1, len(px) // 40000)]
    order = np.argsort(sample @ np.array([0.2126, 0.7152, 0.0722]))
    centres = sample[order[np.linspace(0, len(order) - 1, k).astype(int)]]  # spread by lightness: deterministic start
    for _ in range(iters):
        labels = np.argmin(((sample[:, None, :] - centres[None]) ** 2).sum(2), 1)
        for j in range(k):
            if (labels == j).any():
                centres[j] = sample[labels == j].mean(0)
    labels = np.argmin(((px[:, None, :] - centres[None]) ** 2).sum(2), 1)
    shares = np.bincount(labels, minlength=k) / len(px)
    return centres, shares


def to_hex(c) -> str:
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in c)


def luminance(hexcol: str) -> float:
    c = [int(hexcol.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def metrics(px: np.ndarray) -> dict:
    h = hls(px)
    hue, light, sat = h[:, 0], h[:, 1], h[:, 2]
    neutral = (sat < 0.12) | (light > 0.94) | (light < 0.08)
    chroma = ~neutral
    fam = np.bincount((hue[chroma] // 30).astype(int), minlength=12) / max(1, chroma.sum())
    warm = ((hue[chroma] < 60) | (hue[chroma] >= 330)).mean() if chroma.any() else 0.0
    return {
        "white_share": round(float(((light > 0.92) & (sat < 0.10)).mean()), 3),
        "dark_share": round(float((light < 0.22).mean()), 3),
        "vivid_share": round(float(((sat > 0.45) & (light > 0.25) & (light < 0.85)).mean()), 3),
        "colourfulness": round(colourfulness(px), 1),
        "chroma_saturation": round(float(sat[chroma].mean()) if chroma.any() else 0.0, 3),
        "hue_families": int((fam >= 0.04).sum()),
        "warm_share": round(float(warm), 3),
    }


def check(m: dict, profile: str) -> dict:
    targets = PROFILES[profile]["targets"]
    rows, passed = [], 0
    for key, (lo, hi) in targets.items():
        ok = (lo is None or m[key] >= lo) and (hi is None or m[key] <= hi)
        passed += ok
        rows.append({"metric": key, "value": m[key], "target": [lo, hi], "pass": ok})
    return {"profile": profile, "for": PROFILES[profile]["for"], "checks": rows, "fit_score": round(100 * passed / len(rows))}


def swatch(colours: list[dict], path: Path) -> None:
    im = Image.new("RGB", (800, 120), "white")
    d = ImageDraw.Draw(im)
    x = 0
    for c in colours:
        w = max(1, round(800 * c["share"]))
        d.rectangle([x, 0, x + w, 90], fill=c["hex"])
        d.text((x + 4, 96), f"{c['hex']} {c['share']:.0%}", fill="black")
        x += w
    im.save(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*")
    ap.add_argument("--profile", choices=sorted(PROFILES))
    ap.add_argument("--out")
    ap.add_argument("--skip-top", type=int, default=0, help="pixels to ignore at the top of each shot (store header)")
    ap.add_argument("--contrast", nargs="*", help="colour pairs 'FG:BG' to measure")
    ap.add_argument("--mask", help="page_audit.js JSON (images + page_width): adds ui_only metrics without the pictures")
    args = ap.parse_args(argv)
    report: dict = {}
    if args.contrast:
        report["contrast"] = [{"pair": p, "ratio": contrast(*p.split(":"))} for p in args.contrast]
    if args.images:
        px = load_pixels(args.images, args.skip_top)
        centres, shares = kmeans(px)
        colours = sorted(({"hex": to_hex(c), "share": round(float(s), 3),
                           "hls": [round(v, 2) for v in colorsys.rgb_to_hls(*c)]} for c, s in zip(centres, shares) if s > 0.004),
                         key=lambda c: -c["share"])
        m = metrics(px)
        report.update({"images": args.images, "dominant_colours": colours, "metrics": m})
        if args.profile:
            report["vibe"] = check(m, args.profile)
        if args.mask:
            audit = json.loads(Path(args.mask).read_text(encoding="utf-8"))
            ui = metrics(load_pixels(args.images[:1], args.skip_top, mask=audit))
            report["ui_only"] = {"metrics": ui, **({"vibe": check(ui, args.profile)} if args.profile else {})}
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / "palette.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
            swatch(colours, out / "palette.png")
    if not report:
        ap.error("give screenshots and/or --contrast pairs")
    json.dump(report, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

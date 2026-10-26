"""Erase another brand's marks (corner logo, "Available on" strip, website) from reference frames with LaMa:

    clean_brand.py <out_dir> <img>... [--box x0,y0,x1,y1 ...]

Boxes are given on a 720x1280 frame (scaled to each picture). Without --box the mahalaxmi-02 (Ramdev Kitchen King) boxes are used.
Run it BEFORE a frame goes to ChatGPT/Codex: it copies every mark it sees (24 Oct 2026).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from reel_factory.watermark import lama  # noqa: E402

DEFAULT_BOXES = [(520, 118, 675, 210), (40, 1058, 475, 1135)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--box", action="append", default=[], help="x0,y0,x1,y1 on a 720x1280 frame")
    a = ap.parse_args(argv)
    boxes = [tuple(int(v) for v in b.split(",")) for b in a.box] or DEFAULT_BOXES
    model = lama()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for p in a.images:
        im = Image.open(p).convert("RGB")
        w, h = im.size
        k = w / 720
        m = np.zeros((h, w), np.uint8)
        for x0, y0, x1, y1 in boxes:
            m[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)] = 255
        res = model(im, Image.fromarray(m)).crop((0, 0, w, h))
        res.save(a.out_dir / (Path(p).stem + ".png"))
        print("cleaned", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

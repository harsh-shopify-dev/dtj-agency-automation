"""Turns the header / footer capture (.work/chrome-reference/<site>/{desktop,phone}.json, made by study_capture.py) into the study table and
counts in references/study.md. Numbers only from the files; colour words from the measured colours (dark / light / colour)."""
from __future__ import annotations

import colorsys
import json
import re
import statistics as st
import sys
from pathlib import Path

REF = Path(__file__).resolve().parents[4] / ".work" / "chrome-reference"
OUT = Path(__file__).resolve().parents[1] / "references" / "study.md"


def rgb(s: str | None):
    m = re.search(r"(\d+)\D+(\d+)\D+(\d+)", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def kind(s: str | None) -> str:
    c = rgb(s)
    if not c:
        return "-"
    h, l, sat = colorsys.rgb_to_hls(*(v / 255 for v in c))
    if l > 0.93:
        return "white"
    if l < 0.22:
        return "dark"
    if sat > 0.35 and 0.2 < l < 0.8:
        return "colour"
    return "light" if l > 0.6 else "dark"


def pixels(png: Path, xs, ys):
    """The most common colour in an area of a screenshot: the page's real paint (a page often colours a layer the DOM reader misses)."""
    from collections import Counter
    from PIL import Image
    im = Image.open(png).convert("RGB")
    cnt = Counter(im.getpixel((x, y)) for x in xs for y in ys if 0 <= y < im.size[1] and 0 <= x < im.size[0])
    return "rgb({},{},{})".format(*cnt.most_common(1)[0][0]) if cnt else None


def main() -> None:
    rows, stats = [], {"ann": 0, "ann_dark_or_colour": 0, "hdr_white": 0, "sticky": 0, "logo_left": 0, "logo_center": 0, "ftr_dark_or_colour": 0,
                       "ftr_light": 0, "newsletter": 0, "social": 0, "payment": 0, "sites": 0}
    hd, hp, ad, fcols, fh = [], [], [], [], []
    for d in sorted(p for p in REF.iterdir() if p.is_dir()):
        dk = d / "desktop.json"
        ph = d / "phone.json"
        if not dk.exists():
            continue
        m = json.loads(dk.read_text(encoding="utf-8"))
        mp = json.loads(ph.read_text(encoding="utf-8")) if ph.exists() else {}
        a, h, f = m.get("announcement"), m.get("header"), m.get("footer")
        if not h:
            continue
        stats["sites"] += 1
        hk = kind(h["bg"])
        top, bottom = d / "desktop-top.png", d / "desktop-bottom.png"
        a_bg = pixels(top, range(2, 30, 3), range(a["top"] + 4, a["top"] + a["h"] - 4)) if a and top.exists() else (a or {}).get("bg")
        ak = kind(a_bg) if a else "none"
        f_bg = None
        if f and bottom.exists():
            from PIL import Image
            hgt = Image.open(bottom).size[1]
            f_bg = pixels(bottom, range(2, 40, 4), range(hgt - 260, hgt - 20, 6))  # the footer's own paint, read from the page's bottom
        fk = kind(f_bg or (f or {}).get("bg")) if f else "-"
        if a:
            stats["ann"] += 1
            ad.append(a["h"])
            if ak in ("dark", "colour") and ak != hk:
                stats["ann_dark_or_colour"] += 1
        stats["hdr_white"] += hk == "white"
        stats["sticky"] += bool(h.get("sticky"))
        lx = h.get("logo_x")
        if lx is not None:
            stats["logo_left"] += lx < 30
            stats["logo_center"] += 40 <= lx <= 60
        hd.append(h["h"])
        if mp.get("header"):
            hp.append(mp["header"]["h"])
        if f:
            stats["ftr_dark_or_colour"] += fk in ("dark", "colour")
            stats["ftr_light"] += fk in ("white", "light")
            stats["newsletter"] += bool(f["newsletter"])
            stats["social"] += f["social_links"] > 0
            stats["payment"] += bool(f["payment"])
            fcols.append(f["columns"])
            fh.append(f["h"])
        rows.append(f"| {d.name} | {ak}{(' ' + str(a['h']) + ' px') if a else ''} | {hk}, {h['h']} px{(' / ' + str(mp['header']['h']) + ' px phone') if mp.get('header') else ''} "
                    f"| {'left' if lx is not None and lx < 30 else 'centre' if lx is not None and 40 <= lx <= 60 else lx} | {'yes' if h.get('sticky') else 'no'} "
                    f"| {fk} | {f['columns'] if f else '-'} | {'yes' if f and f['newsletter'] else 'no'} | {f['social_links'] if f else '-'} "
                    f"| {'yes' if f and f['payment'] else 'no'} |")
    n = stats["sites"]
    med = lambda xs: int(st.median(xs)) if xs else None  # noqa: E731
    text = ["# Header and footer study (21 Oct 2026)", "",
            f"{n} public home pages of strong D2C brands (the 19 Oct home-page study's list plus Proeffex), opened in a clean headless Edge at 1280 and",
            "390 px (`scripts/study_capture.py`, raw files private in `.work/chrome-reference/`). Colours are read from the page (computed styles);",
            "\"colour\" = a saturated brand colour, \"dark\" = near black / deep brand colour; bar and footer colours are read from the screenshots' pixels",
            "(the page reader alone took a white wrapper for the footer on several sites). A site whose parts the reader could not find is left out.", "",
            "| Site | Announcement bar | Header (laptop / phone height) | Logo | Sticky | Footer | Footer columns | Sign-up | Social links | Payment icons |",
            "|---|---|---|---|---|---|---|---|---|---|", *rows, "",
            "## Counts", "",
            f"- Announcement bar at the very top: {stats['ann']} of {n}; in a dark or brand colour that differs from the header: {stats['ann_dark_or_colour']}"
            f" (bar height median {med(ad)} px).",
            f"- Header on white: {stats['hdr_white']} of {n}; sticky: {stats['sticky']} of {n}; logo on the left: {stats['logo_left']}, centred: {stats['logo_center']}"
            f" (header height median {med(hd)} px on a laptop, {med(hp)} px on a phone).",
            f"- Footer in a dark or brand colour: {stats['ftr_dark_or_colour']} of {n}; light or white: {stats['ftr_light']}.",
            f"- Footer sign-up: {stats['newsletter']} of {n}; social links: {stats['social']} of {n}; payment icons: {stats['payment']} of {n};"
            f" link columns median {med(fcols)}.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text[-6:]))
    print("written", OUT)


if __name__ == "__main__":
    sys.exit(main())

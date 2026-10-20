"""Reads a home page study folder (private, under .work/, never committed) and turns each brand's saved captures into numbers, so every figure
in references/study/ comes from code (CLAUDE.md rule 4). Nothing is fetched: it reads only what capture.py and remeasure.py saved.

    python .claude/skills/dtj-home-page/scripts/study_numbers.py .work/home-page-reference --out <file.json> [--sheets <folder>]

Per brand (folder <category>/<brand>/ with desktop-metrics.json, desktop-spacing.json, phone-spacing.json, desktop.png):
- pad: the empty space between a section's edge and its first / last text or button (remeasure.py, full-width photo sections left out),
  median and quartiles of all top and bottom gaps, desktop 1440 and phone 390 px. Same definition as ratings.md, so the numbers match it.
- sections, page length (desktop and phone), heading sizes (H1 and the section headings), button corners, body font.
- colour bands, read from the desktop screenshot (the section list in the saved files is nested on several sites, so it cannot place
  sections on the picture): every row's colour comes from the page's side margins (32 px at each edge; the right strip stops 26 px short
  of the edge, where the capture keeps a white scroll-bar gutter). A row is FLAT when both edges show one exact colour (no channel
  varies by more than 2 across the strip: a CSS fill; a photo's smooth wall still carries noise), EDGE when only one
  does (a carousel or a half-width photo touches the other edge), else PICTURE. Rows of one colour form a band; bands under 40 px are
  folded into the band above (lines, text touching the edge), an EDGE band under 120 px counts as picture. Rows are chained to the row
  above, so a vertical gradient stays one band (read at its middle, `gradient: true`). The top 140 px (announcement
  and header) and the last band when it runs to the page's end (the footer, at most 1,600 px) are left out. A capture wider than the
  1440 px viewport is read in its first 1440 px.
  Classes (OKLCH): white = L >= 0.985 and chroma <= 0.02; offwhite = L >= 0.955 and chroma <= 0.015 (a barely-there cream, grey or
  blue that reads as the ground); tint = any other L >= 0.78; dark = L < 0.32; solid = the rest; picture = no flat colour at the edges.
  A band counts as a BAND from 150 px; shorter ones are strips.
--sheets writes, per brand, the desktop page with the band edges and their class drawn on it, and the phone page in strips, for a
person (or an agent) to read the layout next to the numbers. Those pictures stay in the private folder you name."""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "services" / "store-builder"))
from page_builder.palette import oklch  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SKIP = {"section-store-home-1", "wakefit"}  # not part of the study / desktop capture blocked (403)
EDGE = 32  # px of side margin read at each edge
FLAT = 2  # a row is one colour when no channel varies by more than this across a strip
PAGE_W = 1440  # the capture's viewport: anything wider in the picture is not the page


def _hex(c) -> str:
    return "#%02X%02X%02X" % tuple(int(v) for v in c[:3])


def classify(c) -> str:
    L, C, _ = oklch(_hex(c))
    if L >= 0.985 and C <= 0.02:
        return "white"
    if L >= 0.955 and C <= 0.015:
        return "offwhite"
    if L >= 0.78:
        return "tint"
    if L < 0.32:
        return "dark"
    return "solid"


def _rows(im: Image.Image):
    """Per row: (left mean, right mean, flat?) from the side margins."""
    w, h = im.size
    w = min(w, PAGE_W)  # G FUEL's capture is 1800 px wide with the page in the left 1440 px and blank white beyond
    left = im.crop((2, 0, 2 + EDGE, h)).convert("RGB")
    right = im.crop((w - 26 - EDGE, 0, w - 26, h)).convert("RGB")  # the capture's white scroll-bar gutter is the last ~15 px
    lp, rp = left.load(), right.load()
    out = []
    for y in range(h):
        row = []
        for px, n in ((lp, EDGE), (rp, EDGE)):
            vals = [px[x, y] for x in range(0, n, 4)]
            mean = tuple(sum(v[i] for v in vals) / len(vals) for i in range(3))
            spread = max(max(v[i] for v in vals) - min(v[i] for v in vals) for i in range(3))
            row.append((mean, spread))
        (lm, ls), (rm, rs) = row
        # the colour of the row: both edges flat and alike, else whichever edge is flat (a carousel or a half photo touches one edge)
        # FLAT = the CSS fill of the band: the same value across the strip (spread <= 2). A photo's smooth wall or sky still carries noise.
        colour = lm if ls <= FLAT else (rm if rs <= FLAT else None)
        out.append((lm, rm, ls <= FLAT and rs <= FLAT and max(abs(lm[i] - rm[i]) for i in range(3)) < 8, colour))
    return out


HEADER_PX = 140
FOOTER_MAX = 1600  # AG1's footer is 1471 px
MIN_RUN, MIN_EDGE_RUN, MIN_BAND = 40, 120, 150


def _same(c1, c2, tol: int = 7) -> bool:
    return c1 is not None and c2 is not None and max(abs(c1[i] - c2[i]) for i in range(3)) <= tol


def _close(h1, h2) -> bool:
    if not (h1 and h2):
        return False
    a, b = oklch(h1), oklch(h2)
    return abs(a[0] - b[0]) < 0.015 and abs(a[1] - b[1]) < 0.012


def bands(rows) -> list[dict]:
    """Rows -> colour bands [{top, height, class, colour}] over the whole page (header and footer included; see content())."""
    runs: list[dict] = []
    for y, (lm, _rm, strong, colour) in enumerate(rows):
        kind = "flat" if strong else ("edge" if colour is not None else "picture")
        col = lm if strong else colour
        last = runs[-1] if runs else None
        if last and last["kind"] == kind and (kind == "picture" or _same(last["prev"], col, 3)):
            last["height"] += 1
            last["prev"] = col
            last["rows"].append(col)
            continue
        runs.append({"top": y, "height": 1, "kind": kind, "colour": col, "prev": col, "rows": [col]})
    for r in runs:  # a gradient band is read at its middle
        if r["kind"] != "picture":
            r["colour"] = r["rows"][len(r["rows"]) // 2]
            r["gradient"] = not _same(r["rows"][0], r["rows"][-1], 12)
    merged: list[dict] = []  # fold short runs into the band above them
    for r in runs:
        if merged and r["height"] < MIN_RUN:
            merged[-1]["height"] += r["height"]
            continue
        merged.append({k: v for k, v in r.items() if k not in ("prev", "rows")})
    out: list[dict] = []
    for r in merged:
        cls = "picture" if r["kind"] == "picture" or (r["kind"] == "edge" and r["height"] < MIN_EDGE_RUN) else classify(r["colour"])
        col = None if cls == "picture" else _hex(r["colour"])
        last = out[-1] if out else None
        if last and last["class"] == cls and (cls == "picture" or _close(last["colour"], col)):
            last["height"] += r["height"]
            continue
        out.append({"top": r["top"], "height": r["height"], "class": cls, "colour": col, "gradient": bool(r.get("gradient")) and cls != "picture"})
    return out


def content(all_bands: list[dict], page_h: int) -> tuple[list[dict], dict]:
    """The bands between the header (top HEADER_PX) and the footer (the last band, when it runs to the page's end)."""
    footer = all_bands[-1] if all_bands else None
    end = page_h
    if footer and footer["top"] + footer["height"] >= page_h - 2 and footer["height"] <= FOOTER_MAX and footer["top"] > page_h * 0.5:
        end = footer["top"]
    out = []
    for b in all_bands:
        top, bot = max(b["top"], HEADER_PX), min(b["top"] + b["height"], end)
        if bot - top > 0:
            out.append({**b, "top": top, "height": bot - top})
    return out, {"header_px": HEADER_PX, "footer_top": end if end < page_h else None, "content_px": sum(b["height"] for b in out)}


def _q(vals: list[float]) -> dict:
    if not vals:
        return {"median": None}
    qs = st.quantiles(vals, n=4) if len(vals) >= 2 else [vals[0]] * 3
    lo, hi = min(vals), max(vals)  # with very few values the quartiles can fall outside the data (Whole Truth: two values): kept inside
    return {"median": round(st.median(vals)), "p25": round(min(max(qs[0], lo), hi)), "p75": round(min(max(qs[2], lo), hi)), "min": lo, "max": hi,
            "n": len(vals)}


NAV_PX = 130  # a leading entry this short, with no heading and no full-width photo, is the store's nav or category bar, not a section


def clean(spacing: list[dict]) -> tuple[list[dict], int]:
    """The spacing list without the nav bar some captures start with (found by reading the screenshots: Method's phone list and Cooking
    Guild's desktop list began with it, which pulled their pad down); returns (sections, how many leading entries were dropped)."""
    dropped = 0
    while spacing and spacing[0]["height"] < NAV_PX and not spacing[0].get("heading") and not spacing[0].get("full_bleed_picture"):
        spacing = spacing[1:]
        dropped += 1
    return spacing, dropped


def pads(spacing: list[dict]) -> list[float]:
    """Every top and bottom gap of the sections that are not a full-width photo. A negative gap is impossible (text measured outside its
    own section box, e.g. KittySpout's review widget at -5113 px) and is left out."""
    out = []
    for s in spacing:
        if s.get("full_bleed_picture"):
            continue
        for k in ("text_gap_top", "text_gap_bottom"):
            if s.get(k) is not None and s[k] >= 0:
                out.append(s[k])
    return out


def brand(d: Path) -> dict | None:
    need = ["desktop-metrics.json", "desktop-spacing.json", "phone-spacing.json", "desktop.png"]
    if not all((d / f).is_file() for f in need):
        return None
    m = json.loads((d / "desktop-metrics.json").read_text(encoding="utf-8"))
    pm = json.loads((d / "phone-metrics.json").read_text(encoding="utf-8")) if (d / "phone-metrics.json").is_file() else {}
    ds, nav_d = clean(json.loads((d / "desktop-spacing.json").read_text(encoding="utf-8")))
    ps, nav_p = clean(json.loads((d / "phone-spacing.json").read_text(encoding="utf-8")))
    im = Image.open(d / "desktop.png")
    all_bands = bands(_rows(im))
    body, frame = content(all_bands, im.height)
    total = frame["content_px"] or 1
    classes = ("white", "offwhite", "tint", "solid", "dark", "picture")
    share = {c: round(sum(b["height"] for b in body if b["class"] == c) / total, 2) for c in classes}
    real = [b for b in body if b["height"] >= MIN_BAND]
    counts = {c: sum(1 for b in real if b["class"] == c) for c in classes}
    runs = {c: max([b["height"] for b in body if b["class"] == c] or [0]) for c in ("white", "offwhite")}
    hues = [{"class": b["class"], "colour": b["colour"], "hue": round(oklch(b["colour"])[2]), "height": b["height"]}
            for b in real if b["class"] in ("tint", "solid", "dark")]
    heads = [s["heading_px"] for s in ds[1:] if s.get("heading_px")]
    pheads = [s["heading_px"] for s in ps[1:] if s.get("heading_px")]
    return {
        "source": (d / "source.txt").read_text(encoding="utf-8").splitlines()[0] if (d / "source.txt").is_file() else None,
        "sections_spacing": {"desktop": len(ds), "phone": len(ps)},
        "nav_bar_dropped": {"desktop": nav_d, "phone": nav_p},
        "page_px": {"desktop": m.get("page_height"), "phone": pm.get("page_height")},
        "pad_desktop": _q(pads(ds)), "pad_phone": _q(pads(ps)),
        "pad_by_section_desktop": [[s.get("text_gap_top"), s.get("text_gap_bottom"), bool(s.get("full_bleed_picture")), s.get("heading", "")[:40]] for s in ds],
        "pad_by_section_phone": [[s.get("text_gap_top"), s.get("text_gap_bottom"), bool(s.get("full_bleed_picture"))] for s in ps],
        "h1_px": {"desktop": m.get("h1_px"), "phone": pm.get("h1_px")},
        "hero_heading_px": {"desktop": ds[0].get("heading_px") if ds else None, "phone": ps[0].get("heading_px") if ps else None},
        "section_heading_px": {"desktop": _q(heads), "phone": _q(pheads)},
        "button": {"radius": m.get("button_radius"), "bg": m.get("button_bg")},
        "font": (m.get("body_font") or "").split(",")[0].strip('" '),
        "frame": frame,
        "bands": {"share": share, "counts_150px": counts, "colour_bands": hues, "longest_ground_run_px": runs,
                  "colour_changes": sum(1 for x, y in zip(real, real[1:]) if x["class"] != y["class"] or not _close(x["colour"], y["colour"])),
                  "sequence": [f"{b['class']}:{b['colour'] or ''}:{b['height']}" for b in real]},
        "all_bands": [{k: b[k] for k in ("top", "height", "class", "colour", "gradient")} for b in all_bands],
        "gradient_bands": sum(1 for b in real if b.get("gradient")),
    }


def sheets(d: Path, data: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(d / "desktop.png").convert("RGB")
    dr = ImageDraw.Draw(im)
    for i, r in enumerate(data["all_bands"], 1):
        if r["height"] < MIN_BAND and r["class"] != "picture":
            continue
        y = r["top"]
        dr.line([(0, y), (im.width, y)], fill=(255, 0, 0), width=3)
        dr.rectangle([0, y, 360, y + 26], fill=(255, 0, 0))
        dr.text((6, y + 6), f"B{i} {r['class']} {r['colour'] or ''} h{r['height']}", fill=(255, 255, 255))
    small = im.resize((720, round(im.height * 720 / im.width)))
    tall = 1400
    parts = [small.crop((0, y, 720, min(small.height, y + tall))) for y in range(0, small.height, tall)]
    for n in range(0, len(parts), 2):
        pair = parts[n:n + 2]
        sheet = Image.new("RGB", (1460, tall), "white")
        for k, p in enumerate(pair):
            sheet.paste(p, (k * 740, 0))
        sheet.save(out / f"desktop-{n // 2 + 1}.png")
    ph = Image.open(d / "phone.png").convert("RGB")
    strips = [ph.crop((0, y, ph.width, min(ph.height, y + tall))) for y in range(0, ph.height, tall)]
    for n in range(0, len(strips), 4):
        group = strips[n:n + 4]
        sheet = Image.new("RGB", (4 * 410, tall), "white")
        for k, p in enumerate(group):
            sheet.paste(p, (k * 410, 0))
        sheet.save(out / f"phone-{n // 4 + 1}.png")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("study")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheets", help="folder for the annotated pictures (keep it private)")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    root = Path(a.study)
    result = {}
    for cat in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP):
        for d in sorted(p for p in cat.iterdir() if p.is_dir() and p.name not in SKIP):
            if a.only and d.name not in a.only:
                continue
            r = brand(d)
            if r is None:
                print(f"{d.name}: files missing, not measured")
                continue
            r["category_folder"] = cat.name
            result[d.name] = r
            if a.sheets:
                sheets(d, r, Path(a.sheets) / d.name)
            b = r["bands"]
            sh = b["share"]
            seq = " ".join("p" if x.startswith("picture") else x.split(":")[0][0].upper() for x in b["sequence"])
            print(f"{d.name:<16} pad {r['pad_desktop']['median']}/{r['pad_phone']['median']}  secs {r['sections_spacing']['desktop']}  "
                  f"page {r['page_px']['desktop']}  ground {sh['white'] + sh['offwhite']:.2f} tint {sh['tint']} solid {sh['solid']} "
                  f"dark {sh['dark']} pic {sh['picture']}  bands {seq}", flush=True)
    Path(a.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

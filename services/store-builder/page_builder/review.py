"""The screenshot review loop: render the page, look at it in a real browser on a phone (390 px) and a desktop (1280 px), measure what a
model cannot be trusted to judge, and fix what the loop is allowed to fix by itself.

Checks (a model's eye is not trusted with any of these; they are measured):
  R01 error  the page is wider than the screen (sideways scrolling on a phone)
  R02 error  an element sticks out past the screen edge
  R03 error  rendered text fails WCAG AA contrast (4.5:1; 3:1 for large text) against what is really behind it. This catches what the
             planned colours (lint L01) cannot: theme CSS overriding a colour, a semi-transparent layer, a colour that never got applied
  R04 warn   text sits on a picture or gradient: contrast cannot be measured, a person checks it in the screenshot
  R05 warn   text is cut off (ellipsis, line clamp or hidden overflow)
  R06 error  a DTJ block renders empty (an empty band on the page)
  R07 warn   a tap target is smaller than 24 x 24 px on the phone (WCAG 2.2, 2.5.8 minimum)
  R08 error  a picture fails to load

What the loop may change by itself: ONLY lines the Claude copy step wrote. If a section with a rewritten line fails an error check, those
lines go back to the template wording and the page is checked again. Anything else is reported as "needs human" with the screenshots;
the loop never edits design decisions, facts or settings on its own.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from . import render
from .assemble import build_pdp

WIDTHS = (390, 1280)
MIN_TAP = 24
CHECKS = {
    "R01": "error", "R02": "error", "R03": "error", "R04": "warn", "R05": "warn", "R06": "error", "R07": "warn", "R08": "error",
}


@dataclass
class Finding:
    check: str
    severity: str
    width: int
    section: str | None
    block: str | None
    message: str


# ---------------------------------------------------------------- colour maths (WCAG 2.x)
_RGBA = re.compile(r"rgba?\(([^)]+)\)")
_SRGB = re.compile(r"color\(srgb\s+([^)]+)\)")  # what browsers report for color-mix() results, channels 0..1


class UnmeasurableColour(ValueError):
    pass


def parse_colour(css: str) -> tuple[float, float, float, float]:
    """rgb()/rgba() (0..255) or color(srgb r g b / a) (0..1). Other spaces (oklch, lab...) raise UnmeasurableColour."""
    css = css or ""
    m = _RGBA.search(css)
    if m:
        parts = [p.strip() for p in m.group(1).replace("/", ",").replace(" ", ",").split(",") if p.strip()]
        r, g, b = (float(x) for x in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return r, g, b, a
    m = _SRGB.search(css)
    if m:
        parts = m.group(1).replace("/", " ").split()
        r, g, b = (min(max(float(x), 0.0), 1.0) * 255 for x in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return r, g, b, a
    raise UnmeasurableColour(f"colour format not measured: {css!r}")


def blend(top: tuple, below: tuple) -> tuple:
    a = top[3]
    return tuple(top[i] * a + below[i] * (1 - a) for i in range(3)) + (1.0,)


def effective_background(layers: list[str]) -> tuple:
    """layers run from the element outwards; the last one is opaque. Composite them from the outside in."""
    colours = [parse_colour(c) for c in layers]
    base = colours[-1][:3] + (1.0,)
    for c in reversed(colours[:-1]):
        base = blend(c, base)
    return base


def luminance(c: tuple) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(fg: tuple, bg: tuple) -> float:
    a, b = luminance(fg) + 0.05, luminance(bg) + 0.05
    return round(max(a, b) / min(a, b), 2)


def large_text(size: float, weight: int) -> bool:
    return size >= 24 or (size >= 18.66 and weight >= 700)


def _hex(c: tuple) -> str:
    return "#%02X%02X%02X" % tuple(round(v) for v in c[:3])


# ---------------------------------------------------------------- probe -> findings
def analyse(probe: dict, width: int) -> list[Finding]:
    out: list[Finding] = []

    def add(check, section, block, message):
        out.append(Finding(check, CHECKS[check], width, section, block, message))

    extra = probe["page_width"] - probe["width"]
    if extra > 1:
        add("R01", None, None, f"the page is {extra} px wider than the {probe['width']} px screen, so it scrolls sideways")
    for o in probe.get("offenders", [])[:5]:
        add("R02", o["section"], o["block"], f"{o['dtj']} <{o['tag']}> reaches {o['left']}..{o['right']} px on a {probe['width']} px screen")

    on_picture: dict[tuple, int] = {}
    seen: set[tuple] = set()
    for t in probe.get("texts", []):
        if t["image"]:
            on_picture[(t["section"], t["block"])] = on_picture.get((t["section"], t["block"]), 0) + 1
            continue
        try:
            bg = effective_background(t["layers"])
            fg = parse_colour(t["color"])
        except UnmeasurableColour:  # a colour space we do not convert: a person checks it in the screenshot
            on_picture[(t["section"], t["block"])] = on_picture.get((t["section"], t["block"]), 0) + 1
            continue
        fg = blend(fg, bg) if fg[3] < 1 else fg
        ratio = contrast(fg, bg)
        symbol = not re.search(r"[^\W_]", t["text"])  # only symbols (stars, ticks, arrows): an icon, WCAG 1.4.11 asks 3:1
        need = 3.0 if symbol or large_text(t["size"], t["weight"]) else 4.5
        key = (t["block"], _hex(fg), _hex(bg))
        if ratio < need and key not in seen:  # one finding per colour pair per block, not one per word
            seen.add(key)
            add("R03", t["section"], t["block"], f"\"{t['text'][:40]}\" is {_hex(fg)} on {_hex(bg)} = {ratio}:1, needs {need}:1 ({t['dtj']})")
    for (section, block), n in on_picture.items():
        add("R04", section, block, f"{n} text element(s) sit on a picture or gradient, or use a colour format that is not measured: "
                                   "check readability by eye in the screenshot")
    for c in probe.get("clipped", [])[:8]:
        add("R05", c["section"], c["block"], f"text is cut off: \"{c['text'][:40]}\"")
    for b in probe.get("blocks", []):
        if b["height"] < 8 or (b["text_len"] == 0 and b["images"] == 0):
            add("R06", b["section"], b["block"], f"{b['dtj']} renders empty ({b['height']} px, no text, no picture)")
    if probe["width"] < 750:
        for t in probe.get("taps", []):
            if 0 < min(t["w"], t["h"]) < MIN_TAP:
                add("R07", t["section"], t["block"], f"tap target \"{t['label'][:30]}\" is {t['w']} x {t['h']} px (minimum {MIN_TAP} x {MIN_TAP})")
    for i in probe.get("broken_images", []):
        add("R08", i["section"], i["block"], f"picture failed to load: {i['src']}")
    return out


# ---------------------------------------------------------------- the loop
def _copy_slots_by_section(overrides: dict) -> dict[str, list[str]]:
    by: dict[str, list[str]] = {}
    for slot in overrides:
        by.setdefault(slot.split(".", 1)[0], []).append(slot)
    return by


def review_page(brand: dict, facts: dict, *, out_dir: Path, browser, copy_overrides: dict | None = None, widths=WIDTHS,
                max_rounds: int = 2, media_dir: Path | None = None, screenshots: bool = True, **build_kw) -> dict:
    """Render, measure, (maybe) revert Claude-written lines, measure again. Returns the review report; writes the screenshots, the
    preview HTML and the final template into out_dir. Never talks to a store."""
    out_dir.mkdir(parents=True, exist_ok=True)
    overrides = dict(copy_overrides or {})
    rounds, reverted = [], {}
    result = None
    for n in range(1, max_rounds + 1):
        result = build_pdp(brand, facts, copy_overrides=overrides or None, **build_kw)
        doc, notes = render.page_html(result, media_dir=media_dir)
        findings, probes = [], {}
        for w in widths:
            probes[w] = browser.measure(doc, w)
            findings += analyse(probes[w], w)
        errors = [f for f in findings if f.severity == "error"]
        rounds.append({"round": n, "copy_lines": sorted(overrides), "errors": len(errors),
                       "warnings": len(findings) - len(errors), "findings": [asdict(f) for f in findings]})
        if not errors:
            break
        by_section = _copy_slots_by_section(overrides)
        to_revert = sorted({s for f in errors if f.section in by_section for s in by_section[f.section]})
        if not to_revert or n == max_rounds:
            break
        for slot in to_revert:
            reverted[slot] = "its section failed " + ", ".join(sorted({f.check for f in errors if f.section == slot.split('.', 1)[0]}))
            overrides.pop(slot)

    final_findings = rounds[-1]["findings"]
    final_errors = [f for f in final_findings if f["severity"] == "error"]
    shots = {}
    (out_dir / "preview.html").write_text(doc, encoding="utf-8")
    if screenshots:
        for w in widths:
            png = out_dir / f"page-{w}.png"
            browser.screenshot(doc, w, probes[w]["page_height"], png, scale=2 if w < 750 else 1)
            shots[str(w)] = png.name
    lint_errors = [f for f in result.report["lint"] if f["severity"] == "error"]
    verdict = "pass" if not final_errors and not lint_errors and not result.report["problems"] else "needs human"
    report = {
        "verdict": verdict,
        "widths": list(widths),
        "rounds": rounds,
        "reverted_copy": reverted,
        "copy_lines_kept": sorted(overrides),
        "screenshots": shots,
        "preview_notes": notes,
        "page_height": {str(w): probes[w]["page_height"] for w in widths},
        "lint_errors": lint_errors,
        "build_problems": result.report["problems"],
        "checks": {k: v for k, v in CHECKS.items()},
        "not_checked_here": ["the theme's own parts (gallery, title, variant picker, buy buttons) are stand-ins",
                             "pictures are placeholders unless --media points at the real files",
                             "live price, stock and picker products use preview samples",
                             "the real store preview after an approved push is the final check"],
    }
    (out_dir / "review.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    report["_result"] = result  # the final page object, for the caller (not written to disk)
    return report

"""Harsh's design checks (H01-H11): the things his review of Go Mints v2 caught that lint, the palette score and the CRO rubric missed
(10 Oct 2026). Each check is measured from a built template.json, so any model reaches the same verdict on the same page.

    python design_checks.py <run dir or template.json> [--compare <older run dir or template.json>]

Prints JSON: every check with its measured values, a pass/fail and the findings. With --compare it also prints the older page's
results and a one-line before/after per check. Standard library only; contrast is the WCAG 2 formula.

Background colours are read from the blocks' own settings (`background`, card and panel colours); a section with no background
setting sits on the page colour (white unless --page is given).
"""
from __future__ import annotations

import colorsys
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from template_audit import load, walk_blocks  # noqa: E402

WHITE = "#FFFFFF"
MUDDY = (1.05, 1.5)  # a card this close to its section reads as a smudge, neither a card nor flat (v2: #213F58 on #082A45 = 1.34)
STORY_WORDS, STORY_POINT = 20, 32
SPEC = re.compile(r"\d\s*(mg|mcg|µg|g|kg|ml|l|iu|kcal|cal|%)(?![a-z])", re.I)
BUTTON_KEYS = ("button_label", "button_label_1", "cta_text")
DARK_LUMINANCE = 0.08
THEME_TEXT = "#000000"  # Horizon's default text colour (measured on the Test Store, 10 Oct 2026)
SAME = 1.5  # two colours closer than this read as one


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return round((max(la, lb) + 0.05) / (min(la, lb) + 0.05), 2)


def hue_of(hex_colour: str) -> float | None:
    """The hue in degrees, or None for a neutral (white, cream, grey, near-black): neutrals give the eye a rest."""
    h = hex_colour.lstrip("#")
    hh, light, sat = colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    return None if sat < 0.25 or light > 0.92 or light < 0.06 else hh * 360


def same_family(a: float, b: float) -> bool:
    d = abs(a - b) % 360
    return min(d, 360 - d) < 25


def _hls(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    hh, light, sat = colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    return hh * 360, light, sat


def vivid_warm(hex_colour: str) -> bool:
    """A bright orange, amber or yellow (Hope N Skin #FF8C11): darkened for white words or a dark band, it turns brown."""
    hue, light, sat = _hls(hex_colour)
    return 15 <= hue <= 65 and sat >= 0.7 and light >= 0.45


def brownish(hex_colour: str) -> bool:
    hue, light, sat = _hls(hex_colour)
    return 10 <= hue <= 70 and sat >= 0.3 and 0.05 <= light <= 0.40


SURFACE_KEYS = ("panel_bg", "card_bg", "card_bg_color", "item_bg")
DETAIL_KEYS = ("accent_color", "icon_color", "icon_bg", "highlight_color", "number_color", "tile_color", "tile_star_color",
               "toggle_color", "tick_color", "button_bg", "cta_bg")
LIGHT_TEXT_KEYS = ("text_color", "heading_color", "body_color", "card_text_color", "q_color", "a_color")


def _hex(v) -> str | None:
    return v.upper() if isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v) else None


def blocks_of(template: dict) -> list[tuple[str, str, dict]]:
    out: list = []
    for sid in template.get("order") or list(template["sections"]):
        walk_blocks(template["sections"][sid], out, sid)
    return out


def check(template: dict, page: str = WHITE) -> dict:
    blocks = blocks_of(template)
    section_bg: dict[str, str] = {}
    for sid, _, s in blocks:
        if _hex(s.get("background")) and sid not in section_bg:
            section_bg[sid] = _hex(s["background"])
    bg = lambda sid: section_bg.get(sid, page)  # noqa: E731
    by_type = lambda t: [(sid, s) for sid, b, s in blocks if b == t]  # noqa: E731
    res: dict[str, dict] = {}

    # H01 cards stand apart from their section (or are clearly the same colour with an outline)
    cards = []
    for sid, s in by_type("dtj-testimonials-slider") + by_type("dtj-stat-cards") + by_type("dtj-stories"):
        if _hex(s.get("card_bg")):
            cards.append((sid, s["card_bg"].upper(), bg(sid)))
    for sid, s in by_type("dtj-science-stats"):
        if _hex(s.get("card_bg_color")):
            cards.append((sid, s["card_bg_color"].upper(), bg(sid)))
    for sid, s in by_type("dtj-split-story"):
        if _hex(s.get("panel_bg")):
            cards.append((sid, s["panel_bg"].upper(), bg(sid)))
    rows = [{"section": sid, "card": c, "section_bg": b, "ratio": contrast(c, b)} for sid, c, b in cards]
    # light greys on a light section are a deliberate soft panel, not a smudge (Harsh, 10 Oct 2026: "grey like Minimalist", whose
    # near-white #F6F6F6 sits on white at 1.08:1); the smudge is a tinted or dark card a shade off its section (Go Mints v2 navy on navy)
    soft_panel = lambda c, b: hue_of(c) is None and hue_of(b) is None and min(luminance(c), luminance(b)) > 0.6  # noqa: E731
    bad = [r for r in rows if MUDDY[0] < r["ratio"] < MUDDY[1] and not soft_panel(r["card"], r["section_bg"])]
    res["H01_card_separation"] = {"why": "A card a shade off its section reads as a smudge (Harsh: white review cards, white numbers section).",
                                  "cards": rows, "findings": [f"{r['section']}: card {r['card']} on {r['section_bg']} is {r['ratio']}:1" for r in bad],
                                  "pass": not bad}

    # H02 words on cards, panels and question boxes read at 4.5:1
    pairs = []
    for sid, s in by_type("dtj-testimonials-slider"):
        card = _hex(s.get("card_bg")) or WHITE
        words = _hex(s.get("card_text_color")) or _hex(s.get("text_color")) or "#000000"
        pairs.append((f"{sid} review cards", words, card))
    for sid, s in by_type("dtj-split-story"):
        panel = _hex(s.get("panel_bg")) or bg(sid)
        pairs.append((f"{sid} story points", _hex(s.get("body_color")) or _hex(s.get("text_color")) or "#000000", panel))
    for sid, s in by_type("dtj-faq"):
        box = _hex(s.get("item_bg")) or bg(sid)
        pairs.append((f"{sid} FAQ answers", _hex(s.get("a_color")) or _hex(s.get("text_color")) or "#000000", box))
    for sid, s in by_type("dtj-stat-cards"):
        card = _hex(s.get("card_bg")) or WHITE
        pairs.append((f"{sid} number labels", _hex(s.get("label_color")) or "#000000", card))
    rows = [{"where": w, "fg": f, "bg": b, "ratio": contrast(f, b)} for w, f, b in pairs]
    bad = [r for r in rows if r["ratio"] < 4.5]
    res["H02_words_on_cards"] = {"why": "White on the bright brand colour was 2.2:1; words go on a box where they read (Harsh chose navy boxes).",
                                 "pairs": rows, "findings": [f"{r['where']}: {r['fg']} on {r['bg']} is {r['ratio']}:1" for r in bad], "pass": not bad}

    # H03 icons stand apart from the words next to them
    # "the same colour" = under 1.5:1 apart; an unset word colour is the theme's text colour (black on Horizon)
    found = []
    for sid, s in by_type("dtj-feature-showcase"):
        title = _hex(s.get("title_color")) or _hex(s.get("text_color")) or THEME_TEXT
        icon = _hex(s.get("icon_color")) or title
        if not _hex(s.get("icon_bg")) and contrast(icon, title) < SAME:
            found.append(f"{sid}: icons in the title colour with no badge")
    for sid, s in by_type("dtj-marquee"):
        words = _hex(s.get("text_color")) or THEME_TEXT
        tick, b = _hex(s.get("accent_color")) or words, bg(sid)
        # only on a band where a white tick would show (white on the brand cyan 2.2:1 shows; on volt yellow 1.1:1 it vanishes)
        if b != page and contrast(WHITE, b) >= 2 and contrast(tick, words) < SAME:
            found.append(f"{sid}: strip ticks in the word colour on a coloured band")
    res["H03_icon_separation"] = {"why": "Icons the same colour as the text blend into it (Harsh: white badges, white strip ticks).",
                                  "findings": found, "pass": not found}

    # H04 every button named after its section
    labels = [(f"{sid}.{k}", str(s[k]).strip()) for sid, _, s in blocks for k in BUTTON_KEYS if s.get(k)]
    distinct = {lab.lower() for _, lab in labels}
    res["H04_button_labels"] = {"why": "Twelve identical labels read as one repeated ad; each label continues its section (Harsh).",
                                "buttons": len(labels), "distinct_labels": len(distinct), "labels": [lab for _, lab in labels],
                                "findings": [] if len(distinct) == len(labels) else [f"{len(labels)} buttons, {len(distinct)} labels"],
                                "pass": len(distinct) == len(labels)}

    # H05 story cards short
    found, words = [], []
    for sid, s in by_type("dtj-split-story"):
        n = len(str(s.get("body") or "").split())
        pts = [str(v) for k, v in s.items() if re.fullmatch(r"bullet_\d+", k) and v]
        words.append({"section": sid, "paragraph_words": n, "point_chars": [len(p) for p in pts]})
        if n > STORY_WORDS:
            found.append(f"{sid}: paragraph {n} words (max {STORY_WORDS})")
        found += [f"{sid}: point '{p}' {len(p)} characters (max {STORY_POINT})" for p in pts if len(p) > STORY_POINT]
    res["H05_story_length"] = {"why": "A story card under a full-width picture must be read in one glance (Harsh: short and to the point).",
                               "cards": words, "findings": found, "pass": not found}

    # H06 buy-box points are benefits
    pts = [line.strip() for _, b, s in blocks if b == "dtj-hero-points" for line in str(s.get("benefits") or "").splitlines() if line.strip()]
    specs = [p for p in pts if SPEC.search(p)]
    res["H06_buybox_benefits"] = {"why": "The buy box answers 'what do I get'; doses and measures belong in the proof sections (Harsh).",
                                  "points": pts, "findings": [f"'{p}' is a spec" for p in specs], "pass": not specs}

    # H07 pictures keep their own shape
    found = []
    for sid, s in by_type("dtj-slideshow-pro"):
        for k in ("ratio_mobile", "ratio_desktop"):
            if s.get(k, "adapt") != "adapt":
                found.append(f"{sid}.{k} = {s[k]} (crops a picture of another shape)")
    for sid, s in by_type("dtj-split-story"):
        if s.get("image") and s.get("image_fit", "fill") != "adapt":
            found.append(f"{sid}.image_fit = {s.get('image_fit', 'fill')}")
    for sid, s in by_type("dtj-science-stats"):
        if s.get("card_image_aspect_ratio", "4 / 5") != "adapt":
            found.append(f"{sid}.card_image_aspect_ratio = {s.get('card_image_aspect_ratio', '4 / 5')}")
    res["H07_picture_shape"] = {"why": "A 4:5 crop of a square pack shot cut its printed claims (Harsh: the section adapts to the picture).",
                                "findings": found, "pass": not found}

    # H08 dark weight: dark sections are emphasis, not the default
    order = [sid for sid in (template.get("order") or []) if sid != "main"]
    dark = [sid for sid in order if luminance(bg(sid)) < DARK_LUMINANCE]
    res["H08_dark_sections"] = {"why": "Four navy sections made the page heavy; content with its own colour (photos, number cards) sits on white (Harsh).",
                                "dark_sections": dark, "count": len(dark), "findings": [f"{len(dark)} dark sections (max 2)"] if len(dark) > 2 else [],
                                "pass": len(dark) <= 2}

    # H10 one colour everywhere: a coloured card or band whose accents, ticks, icons and button are all the same colour family, with
    # nothing white to rest on (Harsh twice: Go Mints "white review cards / white icons", Hope N Skin "everything is orangish")
    found, families = [], []
    for sid in order:
        blocks = [(b, st) for s_id, b, st in blocks_of(template) if s_id == sid]
        surfaces = [_hex(st.get(k)) for _, st in blocks for k in SURFACE_KEYS if _hex(st.get(k))]
        surfaces = [c for c in surfaces if hue_of(c) is not None] or ([bg(sid)] if hue_of(bg(sid)) is not None else [])
        details = [_hex(st.get(k)) for _, st in blocks for k in DETAIL_KEYS if _hex(st.get(k))]
        families += [hue_of(c) for c in surfaces + details if hue_of(c) is not None]
        if not surfaces:
            continue
        hues = [hue_of(c) for c in details]
        relief = any(h is None and luminance(c) > 0.6 for c, h in zip(details, hues)) or any(
            _hex(st.get(k)) and luminance(_hex(st[k])) > 0.6 for _, st in blocks for k in LIGHT_TEXT_KEYS) or any(
            b == "dtj-slideshow-pro" and not st.get("text_color") for b, st in blocks)  # older banners: white words by default
        tinted = [h for h in hues if h is not None]
        base = hue_of(surfaces[0])
        if len(tinted) >= 2 and all(same_family(h, base) for h in tinted) and not relief:
            found.append(f"{sid}: {surfaces[0]} surface with {len(tinted)} accents in the same colour family and nothing white")
    top = max(({round(h / 30) * 30 % 360 for h in families}), key=lambda f: sum(same_family(h, f) for h in families), default=None)
    share = round(sum(same_family(h, top) for h in families) / len(families), 2) if families else 0
    res["H10_colour_monotony"] = {"why": "One colour on the card, the words, the ticks and the button reads as a smear; give every coloured surface "
                                  "a white or contrasting detail (Harsh: Go Mints, Hope N Skin).",
                                  "dominant_family_share": share, "findings": found, "pass": not found}

    # H11 a bright warm brand colour darkened into brown: the Hope N Skin story card #B2620C and closing banner #402305 were both orange
    # #FF8C11 deepened (for white words, for a dark band). Harsh rejected both ("that dark brown"; the banner "didnt got updated").
    # A bright orange, amber or yellow keeps its character only as a FILL (button, tick, star tile) or as a light tint, never darkened.
    every = blocks_of(template)  # (H10 above reuses the name `blocks` for one section)
    vivid = sorted({c for _, _, st in every for k in DETAIL_KEYS if (c := _hex(st.get(k))) and vivid_warm(c)})
    found = []
    for sid, b, st in every:
        for k in SURFACE_KEYS + ("background", "overlay_color"):
            c = _hex(st.get(k))
            if c and brownish(c) and any(same_family(_hls(c)[0], _hls(v)[0]) for v in vivid):
                found.append(f"{sid}.{k} = {c}: the brand's {vivid[0]} darkened into brown")
    res["H11_no_brown"] = {"why": "A bright orange or yellow darkened for white words or a dark band turns brown and heavy (Harsh, Hope N Skin): "
                           "use a light card with dark words and keep the brand colour for fills and marks.",
                           "vivid_brand_colours": vivid, "findings": sorted(set(found)), "pass": not found}

    # H09 the background sequence (for the report: what a shopper scrolls through)
    res["H09_background_sequence"] = {"why": "Read the rhythm at a glance: never two equal neighbours, no long run of one colour.",
                                      "sequence": [{"section": sid, "bg": bg(sid), "dark": luminance(bg(sid)) < DARK_LUMINANCE} for sid in order],
                                      "findings": [], "pass": True}
    passed = sum(1 for r in res.values() if r["pass"])
    # the palette inventory: every area colour and where it is used. After ANY colour change, read it: an old colour still listed is a
    # section the change missed (the brown closing banner stayed through 10 card-colour pushes on Hope N Skin, 10 Oct 2026)
    palette: dict[str, list[str]] = {}
    for sid, b, st in every:
        for k in SURFACE_KEYS + ("background", "overlay_color", "tile_color", "button_bg"):
            if _hex(st.get(k)):
                palette.setdefault(_hex(st[k]), []).append(f"{sid}.{k}")
    return {"passed": passed, "of": len(res), "checks": res, "palette": {c: sorted(set(v)) for c, v in sorted(palette.items())}}


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print(__doc__)
        return 1
    page = WHITE
    if "--page" in argv:
        i = argv.index("--page")
        page = argv[i + 1].upper()
        del argv[i:i + 2]
    older = None
    if "--compare" in argv:
        i = argv.index("--compare")
        older = argv[i + 1]
        del argv[i:i + 2]
    now = check(load(Path(argv[0])), page)
    out = {"page": now}
    if older:
        before = check(load(Path(older)), page)
        out["before"] = before
        out["before_after"] = {k: f"{'pass' if before['checks'][k]['pass'] else 'FAIL'} -> {'pass' if v['pass'] else 'FAIL'}"
                               for k, v in now["checks"].items()}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

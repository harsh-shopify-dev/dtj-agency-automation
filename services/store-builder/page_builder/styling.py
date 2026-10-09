"""Styling: puts the design direction onto each section's block settings (colours by band role, one radius family, type treatment, rhythm).
Only settings the block really has are written (checked against the catalog), so a block that lacks a control is simply left alone."""
from __future__ import annotations

from .catalog import Catalog
from .direction import Direction
from .sections import Section


def apply(sec: Section, role: str, d: Direction, cat: Catalog, first: bool = False) -> None:
    r, s = d.roles, sec.settings

    def put(key, value):
        if value is not None and cat.has(sec.app, sec.block, key):
            s[key] = value

    dark, band = role == "dark", role == "band"
    acc = r["accent_on_dark"] if dark else r["accent"]
    head = r["on_dark"] if dark else r["text"]
    pad = d.density["band"] if (dark or band) else d.density["section"]

    # rhythm and side space (same for every block)
    if sec.block != "marquee":
        put("padding_top", pad if not first else max(pad - 8, 16))
        put("padding_bottom", pad)
    else:
        put("padding_top", 0)
        put("padding_bottom", 0)
    put("side_padding", d.density["side"])
    if dark:
        put("background", r["dark"])
        put("text_color", r["on_dark"])
    elif band:
        put("background", r["band"])
    # one radius family
    for key in ("corner_radius", "card_radius", "panel_radius", "border_radius", "item_radius"):
        put(key, d.shape["card"] if key != "item_radius" else min(d.shape["card"], 16))

    b = sec.block
    if b == "marquee":
        put("accent_color", acc)
    elif b == "feature-showcase":
        put("heading_color", head)
        put("title_color", head)
        put("icon_color", acc)
    elif b == "science-stats":
        put("heading_text_color", head)
        put("heading_font_style", "normal")
        put("heading_font_weight", "700")
        put("card_bg_color", r["dark"])
        put("card_text_color", r["on_dark"])
        put("number_color", r["accent_on_dark"])
        put("card_shadow_enable", True)
    elif b == "split-story":
        put("heading_color", head)
        put("accent_color", acc)
        put("panel_bg", r["band"])
    elif b == "measured-results":
        put("accent_color", r["accent_on_dark"])
        put("card_text_color", r["text"])
        put("card_accent_color", r["accent"])
        put("card_bg", r["tint_card"])
    elif b == "stat-cards":
        put("heading_color", head)
        put("accent_color", acc)
        put("card_bg", r["tint_card"])
    elif b == "whats-inside":
        put("accent_color", acc)
        put("highlight_color", acc)
    elif b == "whats-not-inside":
        put("highlight_color", r["accent_on_dark"] if dark else acc)
    elif b == "comparison-table":
        put("heading_color", head)
        put("our_bg_color", r["band"])
    elif b == "testimonials-slider":
        put("button_color", r["button_bg"])
        if not dark:
            # the cards default to white: on a dark brand that put #F2F2F2 text on white (1.12:1, review loop 9 Oct 2026).
            # The direction's card colours are a checked pair for any brand, light or dark.
            put("card_bg", r["tint_card"])
            put("text_color", r["on_card"])
        if d.dark_mode:
            put("tile_color", r["rating_tile"])  # the white star needs a tile it shows on (direction.py)
    elif b == "faq":
        put("heading_color_1", head)
        put("accent_color", acc)
    elif b == "price":
        put("text_color", r["text"])
        # the struck-through price: the block's default "softer shade" measured 3.57:1 on white in the review loop (9 Oct 2026), below AA.
        # The direction's muted colour is pushed to 4.5:1 on the page background, where the buy box sits.
        put("compare_color", r["muted"])
        put("badge_bg", r["button_bg"])
        put("badge_color", r["button_text"])
        put("price_size", 28)
    elif b == "social-proof":
        put("star_color", r["rating_star"])  # rating gold, darkened only as far as 3:1 on the page needs (direction.py)
        put("badge_bg", r["band"])
        put("badge_color", r["text"])
        put("badge_icon_color", acc)
        put("text_size", 13)
        put("item_gap", 8)
    elif b in ("hero-points", "shade-picker", "addons", "testimonials"):
        put("accent_color", acc)
        if b == "hero-points":
            put("eyebrow_color", head)
        if b == "testimonials":
            put("star_color", r["rating_star"])
    elif b == "slideshow-pro":
        put("accent_color", r["accent_on_dark"])
        put("overlay_color", r["dark"])
        put("button_bg", r["button_bg"])
        put("button_color", r["button_text"])
        put("button_style", d.shape["button"])
        put("chip_style", d.shape["chips"])
        put("accent_font", d.type["accent_font"])
        put("heading_font", d.type["heading_font"])
        put("eyebrow_style", d.type["eyebrow_style"])
        put("transition", d.motion["transition"])
        put("autoplay_seconds", d.motion["seconds"])
        put("background", r["dark"])

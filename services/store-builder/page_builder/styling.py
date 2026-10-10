"""Styling: puts the design direction onto each section's block settings (colours by band role, one radius family, type treatment, rhythm).
Only settings the block really has are written (checked against the catalog), so a block that lacks a control is simply left alone."""
from __future__ import annotations

from provision import style

from .catalog import Catalog
from .direction import BOLD_VIBES, Direction
from .direction import _best_text_on as best_text_on
from .sections import Section


# the trust strip under the buy box: big and calm (Harsh, 9 Oct 2026: "more padding, more height, more gigantic")
MARQUEE = {"padding": 24, "text": 24, "icon": 30, "gap": 72}


def apply(sec: Section, role: str, d: Direction, cat: Catalog, first: bool = False) -> None:
    r, s = d.roles, sec.settings

    def put(key, value):
        if value is not None and cat.has(sec.app, sec.block, key):
            s[key] = value

    dark, band, accent_band = role == "dark", role == "band", role == "accent"
    bold = d.vibe in BOLD_VIBES and not d.dark_mode  # electric / playful: brand-colour bands, ink boxes with white words
    if dark:
        acc, head = r["accent_on_dark"], r["on_dark"]
    elif accent_band:  # a band in the accent colour (electric / playful pages): everything on it is the ink colour
        acc, head = r["on_accent"], r["on_accent"]
    elif band:
        acc, head = r["accent_on_band"], r["on_band"]
    else:
        acc, head = r["accent"], r["text"]
    pad = d.density["band"] if (dark or band or accent_band) else d.density["section"]

    # rhythm and side space (same for every block)
    if sec.block != "marquee":
        put("padding_top", pad if not first else max(pad - 8, 16))
        put("padding_bottom", pad)
    else:  # the strip is a bold band of its own: clear space above and below so it never touches the pictures (Harsh, 9 Oct 2026)
        put("padding_top", MARQUEE["padding"])
        put("padding_bottom", MARQUEE["padding"])
    put("side_padding", d.density["side"])
    if dark:
        put("background", r["dark"])
        put("text_color", r["on_dark"])
    elif accent_band:
        put("background", r["accent_fill"])
        put("text_color", r["on_accent"])
    elif band:
        put("background", r["band"])
        if r["on_band"] != r["text"]:  # a bold band (the brand colour itself) carries its own text colour
            put("text_color", r["on_band"])
    # one radius family
    for key in ("corner_radius", "card_radius", "panel_radius", "border_radius", "item_radius"):
        put(key, d.shape["card"] if key != "item_radius" else min(d.shape["card"], 16))

    b = sec.block
    if b == "marquee":
        # on a brand-colour band the ticks are white (Harsh, 10 Oct 2026); they are decoration, the words carry the meaning
        put("accent_color", r["tint_card"] if band and bold else acc)
        put("text_size", MARQUEE["text"])
        put("icon_size", MARQUEE["icon"])
        put("gap", MARQUEE["gap"])
    elif b == "feature-showcase":
        put("heading_color", head)
        put("title_color", head)
        # every icon sits in a round badge so it stands apart from the words: icons in the text colour blended into the brand band
        # (Harsh, 10 Oct 2026: "white color for the icons to separate them out"). On a band: a white badge; on white: a brand badge.
        if dark or band or accent_band:
            put("icon_bg", r["tint_card"])
            put("icon_color", r["on_card"])
        else:
            put("icon_bg", r["band"])
            put("icon_color", r["accent_on_band"])
        if dark or band or accent_band:  # the block fades secondary text to 72 %: on a strong band that fails 4.5:1 (review loop, 10 Oct 2026)
            put("desc_color", head)
    elif b == "science-stats":
        put("heading_text_color", head)
        put("heading_font_style", "normal")
        put("heading_font_weight", "700")
        put("card_bg_color", r["dark"])
        put("card_text_color", r["on_dark"])
        put("number_color", r["accent_on_dark"])
        put("card_shadow_enable", True)
        put("card_image_aspect_ratio", "adapt")  # pictures keep their own shape: never trimmed
    elif b == "split-story":
        # the card's panel must stand out from what is behind it, and its words must read on the panel itself (review loop, 10 Oct 2026:
        # a deep-cyan accent on a cyan panel was 2.2:1)
        if dark:
            put("panel_bg", style.mix(r["dark"], "#FFFFFF", 0.10).upper())
            panel_head, panel_acc = r["on_dark"], r["accent_on_dark"]
        elif bold and (band or accent_band):  # a white card on the brand-colour band
            put("panel_bg", r["tint_card"])
            panel_head, panel_acc = r["text"], r["accent"]
        elif bold:  # on white: an ink card with white words and accent ticks (Harsh, 10 Oct 2026: white points; white on the
            # brand cyan was 2.2:1, so the card turns ink instead)
            put("panel_bg", r["dark"])
            panel_head, panel_acc = r["on_dark"], r["accent_on_dark"]
        else:  # calm pages: the brand-colour card with white accent words and white ticks (H01: it stands apart from page and band)
            put("panel_bg", r["panel"].upper())
            panel_head, panel_acc = r["panel_head"], r["accent_on_panel"]
            if r.get("panel_tick"):
                put("tick_color", r["panel_tick"].upper())  # the check inside the white tick takes the card's colour
        put("heading_color", panel_head)
        put("accent_color", panel_acc)
        put("body_color", r["on_panel"] if not (dark or bold) else panel_head)  # calm cards: white words on the deep brand colour
        if style.contrast("#FFFFFF", panel_acc) < 3 and "tick_color" not in s:  # a light marker's check: the card's colour, else black/white
            # (a tick colour chosen above, e.g. the brand colour on a grey card, is kept)
            panel = s.get("panel_bg") or r["bg"]
            put("tick_color", panel if style.contrast(panel, panel_acc) >= 3 else best_text_on(panel_acc))
        put("image_fit", "adapt")  # the whole picture at its own shape (it was trimmed on the live book page, 9 Oct 2026)
    elif b == "measured-results":
        put("accent_color", r["accent_on_dark"])
        put("card_text_color", r["text"])
        put("card_accent_color", r["accent"])
        put("card_bg", r["tint_card"])
    elif b == "stat-cards":
        put("heading_color", head)
        put("accent_color", acc)
        bold_on_white = role == "plain" and bold
        if dark or bold_on_white:  # dark cards, the figures in the accent colour (volt on white was 1.25:1, review loop 10 Oct 2026);
            # on an electric / playful page the section itself is white and the cards are the ink colour (Harsh, 10 Oct 2026)
            put("card_bg", style.mix(r["dark"], "#FFFFFF", 0.10).upper() if dark else r["dark"])
            put("number_color", r["accent_on_dark"])
            put("label_color", r["on_dark"])
            put("note_color", r["on_dark"])
        else:
            put("card_bg", r["tint_card"])
            put("number_color", r["accent"])
            put("label_color", r["on_card"])
            put("note_color", r["muted_on_card"])
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
        # the cards are always the light card colour with their own text colour, so a dark band gets white cards with dark words
        # while its heading stays light (Harsh, 10 Oct 2026: "use the white for the review cards"). The direction's card colours are
        # a checked pair for any brand (a dark brand's white cards once carried #F2F2F2 text, 1.12:1, review loop 9 Oct 2026).
        put("card_bg", r["tint_card"])
        put("card_text_color", r["on_card"])
        if not dark:
            put("text_color", r["on_card"])
        tile = r["rating_tile"] if d.dark_mode else r["on_card"]  # a light text colour would leave the star nothing to show on
        put("tile_color", tile)
        star = r["accent_on_dark"] if style.contrast(r["accent_on_dark"], tile) >= 3 else best_text_on(tile)
        put("tile_star_color", star)  # the accent star when it reads on the tile, else black or white (the block's default is Canvas)
    elif b == "faq":
        put("heading_color_1", head)
        put("accent_color", acc)
        if band and bold:  # questions in ink boxes with white words on the brand band (Harsh, 10 Oct 2026: white answers;
            # white on the brand cyan was 2.2:1); the open / close button in the accent colour, its x in the box colour
            put("item_bg", r["dark"])
            put("item_border", r["dark"])
            put("q_color", r["on_dark"])
            put("a_color", r["on_dark"])
            put("toggle_color", r["accent_on_dark"])
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
        put("avatar_size", 24)  # five photos (rule L14) + badge + stars must fit one phone line without cutting the badge (9 Oct 2026)
    elif b in ("hero-points", "shade-picker", "addons", "testimonials"):
        put("accent_color", acc)
        if b == "hero-points":
            put("eyebrow_color", head)
        if b == "testimonials":
            put("star_color", r["rating_star"])
            put("avatar_text_color", best_text_on(acc))  # the initial on the accent circle: black or white by contrast, not Canvas
    elif b == "shoppable-reels":
        put("price_color", acc)
        put("padding_left", d.density["side"])  # its heading sat on the screen edge on phones (review screenshot, 10 Oct 2026)
        put("padding_right", d.density["side"])
    elif b == "stories":
        put("heading_color", head)
        put("card_bg", r["tint_card"])
        put("card_border", r["border"])
        put("name_color", r["on_card"])
        put("quote_color", r["on_card"])
        put("tag_bg", r["band"] if not band else r["tint_card"])
        put("tag_color", r["on_band"] if not band else r["on_card"])
        put("verified_color", r["accent"])
        put("star_color", r["rating_star"])
        put("cta_bg", r["button_bg"] if not accent_band else r["on_accent"])
        put("cta_text_color", r["button_text"] if not accent_band else r["accent_fill"])
        put("cta_full_width", False)  # the page's buttons all share one shape (the DTJ CTA blocks are pills on round brands)
        put("cta_radius", 60 if d.shape["button"] == "pill" else (10 if d.shape["button"] == "rounded" else 0))
    elif b == "cta":
        put("heading_color", head)
        put("seal_color", head)
        if accent_band:  # the accent colour is the background here: the button turns ink with accent text
            put("button_bg", r["on_accent"])
            put("button_color", r["accent_fill"])
        else:
            put("button_bg", r["button_bg"])
            put("button_color", r["button_text"])
        put("button_style", d.shape["button"] if d.shape["button"] in ("pill", "rounded", "square") else "pill")
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

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

# ---- the HOME page's vertical rhythm and type scale (Harsh, 19 Oct 2026: our home page "looks cramped and flat"). Measured on 23 reference
# home pages (.claude/skills/dtj-home-page/references/study/, page_builder/home_profiles.json): the pages rated 85 and up keep 80-112 px
# between a section's edge and its first or last words on a laptop and 32-66 px on a phone; ours kept 20-32 on both. ONE number per step,
# written on the theme's own section wrapper (Horizon's `padding-block-start` / `-end`), which the theme scales to 0.7 below 990 px
# (snippets/spacing-style.liquid, never under 20 px), so one value is the laptop AND the phone rhythm. The block's own padding is then 0
# and the wrapper carries the band colour, so a band is one colour from edge to edge.
HOME_SPACE = {"section": 80, "related": 48}  # related: the 85+ pages' smallest usual gap (10th percentile, 48 px; 34 on a phone)
# Thin strips carry their own height (no section padding): the top announcement, the trust strip under the hero, the wave.
HOME_STRIPS = ("announcement_bar", "trust_band_home", "wave_home")
# Related neighbours (above, below) sit closer, so the pair reads as one idea: the shop row right under its categories, and the
# shop-by-concern band the wave flows into. Every other join keeps the full step.
HOME_RELATED = {("categories_home", "best_sellers_home"), ("wave_home", "concerns_home")}
# One heading scale (laptop, phone px): the reference pages rated 85+ use 32-56 px section headings (median 42) and 48-66 px hero
# headings. The categories ring stays small: it is a way to move around, not a headline (Harsh, 14 Oct 2026).
HOME_TYPE = {"hero": (56, 36), "section": (40, 30), "nav": (28, 22)}
NAV_BLOCKS = ("circle-menu",)


def home_rhythm(kinds: list[str]) -> list[tuple[int, int] | None]:
    """(top, bottom) section padding for each section of a home page, in page order: thin strips 0, related neighbours the tighter step
    on the side they share, everything else the full step. The hero is None: it keeps its own look (a picture banner runs edge to edge,
    a one-product split hero keeps its panel's own space)."""
    out: list[tuple[int, int] | None] = []
    for i, kind in enumerate(kinds):
        if kind == "hero_home":
            out.append(None)
            continue
        if kind in HOME_STRIPS:
            out.append((0, 0))
            continue
        above = kinds[i - 1] if i else None
        below = kinds[i + 1] if i + 1 < len(kinds) else None
        top = HOME_SPACE["related"] if (above, kind) in HOME_RELATED else HOME_SPACE["section"]
        bottom = HOME_SPACE["related"] if (kind, below) in HOME_RELATED else HOME_SPACE["section"]
        out.append((top, bottom))
    return out


def apply_home_type(sec: Section, cat: Catalog) -> None:
    """The home type scale onto a section's heading-size settings (only the settings its block really has)."""
    def put(key, value):
        if cat.has(sec.app, sec.block, key):
            sec.settings[key] = value

    step = HOME_TYPE["hero" if sec.kind == "hero_home" else "nav" if sec.block in NAV_BLOCKS else "section"]
    put("heading_size_desktop", step[0])
    put("heading_size_mobile", step[1])
    if sec.block == "faq":  # one size for both: the block takes 6 px off it on phones (faq.css), so the phone lands on the scale
        put("heading_size", step[1] + 6)
    elif sec.block == "stories":
        put("heading_size", step[1])


def apply(sec: Section, role: str, d: Direction, cat: Catalog, first: bool = False) -> None:
    r, s = d.roles, sec.settings

    def put(key, value):
        if value is not None and cat.has(sec.app, sec.block, key):
            s[key] = value

    mint = role == "mint"  # the palette method's second soft band (the accent family's tint): treated like a band everywhere
    dark, band, accent_band = role == "dark", role in ("band", "mint"), role == "accent"
    band_bg = r["mint"] if mint else r["band"]
    bold = d.vibe in BOLD_VIBES and not d.dark_mode  # electric / playful: brand-colour bands, ink boxes with white words
    if dark:
        acc, head = r["accent_on_dark"], r["on_dark"]
    elif accent_band:  # a band in the accent colour (electric / playful pages): everything on it is the ink colour
        acc, head = r["on_accent"], r["on_accent"]
    elif band:
        acc, head = (r["accent_on_mint"] if mint else r["accent_on_band"]), r["on_band"]
    else:
        acc, head = r["accent"], r["text"]
    pad = d.density["band"] if (dark or band or accent_band) else d.density["section"]

    # rhythm and side space (same for every block)
    if sec.block == "marquee-band":  # each version of the moving strip sets its own height and lines: no section padding around it
        put("padding_top", 0)
        put("padding_bottom", 0)
    elif sec.block != "marquee":
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
        put("background", band_bg)
        if r["on_band"] != r["text"]:  # a bold band (the brand colour itself) carries its own text colour
            put("text_color", r["on_band"])
    # one radius family
    for key in ("corner_radius", "card_radius", "panel_radius", "border_radius", "item_radius"):
        put(key, d.shape["card"] if key != "item_radius" else min(d.shape["card"], 16))

    b = sec.block
    if b == "marquee":
        # on a brand-colour band the ticks are white (Harsh, 10 Oct 2026); they are decoration, the words carry the meaning. When the
        # words on the band are white too, white ticks blend in (24 Oct 2026, NoCheat's maroon band: design check H03): then the
        # accent, as long as it shows on the band.
        tick = r["tint_card"] if band and bold else acc
        words = r["on_band"] if band else head
        if band and bold and style.contrast(tick, words) < 1.5 and style.contrast(r["accent"], band_bg) >= 3:
            tick = r["accent"]
        put("accent_color", tick)
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
        else:  # calm pages: the brand-colour card with white accent words and white ticks (H01: it stands apart from page and band),
            # or with card_tone "neutral" Minimalist's light grey with dark words (direction.py)
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
        if d.ramps and sec.kind == "compare_home":  # the home table: a tall white column on the soft band, brand-blue hairlines, dark words (the reference table)
            put("our_bg_color", r["tint_card"])
            put("our_text_color", r["text"])
            put("other_text_color", r["text"])
            put("line_color", d.ramps["brand"][5])
            put("muted_color", r["muted"])
        else:
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
        if not d.dark_mode and not bold:  # calm pages: brand-colour tiles with white stars (Harsh, Hope N Skin, 10 Oct 2026)
            put("tile_color", r["review_tile"])
            put("tile_star_color", "#FFFFFF")
        else:
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
        # the ink only when it reads on the band (24 Oct 2026, NoCheat: ink #24090B on the maroon band was 2.35:1, the review's R03)
        put("badge_color", r["text"] if style.contrast(r["text"], r["band"]) >= 4.5 else best_text_on(r["band"]))
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
    elif b == "hero-banner":
        put("corner_radius", 0)  # the container itself is never rounded; a split layout rounds its own panel
        layout = s.get("layout", "banner")
        if layout in ("banner", "cover"):  # a picture hero: always light words on a dark overlay, whatever band the page alternates
            put("side_padding", 0)  # edge to edge: the text has its own inner space (lint L02 exempts it)
            put("padding_top", 0)
            put("padding_bottom", 0)
            put("background", r["dark"])
            put("text_color", r["on_dark"])
            put("accent_color", r["accent_on_dark"])
            put("star_color", r["accent_on_dark"])
            if sec.kind == "hero_home" and r.get("dark_button_bg"):
                put("button_bg", r["dark_button_bg"])
                put("button_color", r["dark_button_text"])
        else:  # split: a story panel on the page's own band. This block falls back to light words on black (it is made for pictures), so
            # the split sets both: the section's own colour, and words that follow the PANEL they sit on (13 Oct 2026: white words on a pale
            # panel on the Elevate home page)
            on_band_role = band or dark or accent_band
            put("background", r["dark"] if dark else r["accent_fill"] if accent_band else band_bg if band else r["bg"])
            if sec.kind == "hero_home":  # the first screen: a bold dark panel, never the pale one the story uses further down
                put("panel_bg", r["dark"])
                put("text_color", r["on_dark"])
                acc = r["accent_on_dark"]
            else:
                put("panel_bg", r["tint_card"] if on_band_role else r["band"])
                put("text_color", r["on_card"] if on_band_role else r["on_band"])
                acc = r["accent"] if on_band_role else r["accent_on_band"]
            put("accent_color", acc)
            put("star_color", r["rating_star"])
            put("card_bg", r["bg"])
        put("point_icon_color", r["accent_on_dark"] if layout in ("banner", "cover") else (r.get("mark") or acc))
        put("button_bg", r["button_bg"])
        put("button_color", r["button_text"])
        put("button_style", "square" if d.shape["button"] == "square" else "rounded")  # a regular rectangle, never an oval (Harsh, 12 Oct 2026)
        put("heading_font", d.type["heading_font"])
        put("accent_font", d.type["accent_font"] if d.type["accent_font"] in ("italic", "serif", "bold", "plain") else "auto")
    elif b in ("feature-cards", "feature-tiles"):
        put("accent_color", acc)
        put("heading_color", head)
        put("title_color", head)
        put("label_color", head)
        put("desc_color", head)
        put("card_bg" if b == "feature-cards" else "tile_bg", r["tint_card"] if band else r["band"])
        put("icon_bg", acc)
        put("icon_color", best_text_on(acc))
        put("badge_bg", acc)
        put("badge_color", best_text_on(acc))
        put("image_radius", d.shape["card"])
        put("tile_radius", min(d.shape["card"], 24))
        put("button_style", "solid")
        put("button_bg", r["button_bg"])
        put("button_color", r["button_text"])
        put("button_shape", "square" if d.shape["button"] == "square" else "rounded")  # a regular rectangle, never an oval (Harsh, 12 Oct 2026)
        if accent_band and r.get("fill_button_bg"):  # the palette method's solid brand band: white tiles carry dark words and brand icons
            put("heading_color", r["on_accent"])
            put("accent_color", r["accent_on_fill"])
            for key in ("title_color", "label_color", "desc_color"):
                put(key, r["on_card"])
            put("card_bg" if b == "feature-cards" else "tile_bg", r["tint_card"])
            put("icon_bg", r["accent_fill"])
            put("icon_color", r["on_accent"])
            put("button_bg", r["fill_button_bg"])
            put("button_color", r["fill_button_text"])
    elif b == "video-reviews":
        put("link_color", r["accent_on_dark"])
        put("verified_color", r["accent_on_dark"])
        put("arrow_bg", r["tint_card"])
        put("arrow_color", r["on_card"])
    # ---- the DTJ Commerce / DTJ Shop home blocks and the comparison showcase (13 Oct 2026). Buttons are regular rectangles, never ovals
    # (Harsh, 12 Oct 2026); every colour pair below is one the direction already checked (button, accent on its band, card text).
    elif b == "marquee-band":
        if s.get("variation") == "bold" and d.ramps:  # the palette method: the top strip is the deep ink colour, icons in the fresh accent
            put("background", r["dark"])
            put("text_color", r["on_dark"])
            put("icon_color", r["accent_on_dark"])
        elif s.get("variation") == "bold":  # the top strip: the brand's accent colour with its own checked text colour
            put("background", r["accent_fill"])
            put("text_color", r["on_accent"])
            put("icon_color", r["on_accent"])
        else:  # the calm strip under the hero: the page colour, brand-coloured icons (the accent's fresh mark with the palette method)
            put("icon_color", r.get("mark") or r["accent"])
            put("line_color", r["border"])
    elif b == "press-strip":
        put("logo_tone", "gray")  # a mixed set of logos reads as one even row
    elif b == "circle-menu":
        put("ring_color_1", r["accent"])  # the story ring in the brand's own colours instead of the block's orange-pink-purple
        put("ring_color_2", r["button_bg"])
        put("ring_color_3", r["accent_on_band"])
        put("frame_color", r["border"])
    elif b == "category-grid":
        put("button_bg", r["button_bg"])
        put("button_color", r["button_text"])
        put("button_shape", "square" if d.shape["button"] == "square" else "rounded")
        put("tile_radius", d.shape["card"])
    elif b == "category-slider":
        put("arrow_bg", r["button_bg"])
        put("arrow_color", r["button_text"])
        put("arrows", "square" if d.shape["button"] == "square" else "circle")
    elif b == "best-sellers":
        put("accent_color", r["button_bg"])  # the active tab, the cart button, the badge: the page's button pair
        put("accent_text", r["button_text"])
        put("card_bg", r["tint_card"] if band else r["band"])
        put("button_shape", "square" if d.shape["button"] == "square" else "rounded")
        put("tab_style", "pill")
        if sec.kind == "best_sellers_home":  # Harsh set it to 0 in the theme editor (19 Oct 2026): the cards sit close to the categories
            put("padding_top", 0)
            put("padding_bottom", 0)  # filled pills read as finished navigation; the block's dashed boxes looked unfinished (14 Oct 2026)
    elif b == "concern-slider":
        put("accent_color", acc)
        put("card_bg", r["tint_card"])
        put("button_color", r["button_bg"])
        put("button_text", r["button_text"])
        put("button_shape", "square" if d.shape["button"] == "square" else "rounded")
    elif b == "before-after":
        put("accent_color", acc)
        put("button_color", r["button_bg"])
        put("button_text", r["button_text"])
        if band or dark:
            put("panel_color", r["tint_card"])
    elif b == "compare-showcase":
        put("accent_color", acc)
        put("button_bg", r["button_bg"])
        put("button_color", r["button_text"])
        put("button_shape", "square" if d.shape["button"] == "square" else "rounded")
        put("card_bg", r["tint_card"])
        put("col_from", r["button_bg"])  # our column: the button colour with its own checked text and tick colour
        put("col_text", r["button_text"])
        put("check_color", r["button_text"])
        put("heading_font", d.type["heading_font"] if d.type["heading_font"] in ("theme", "serif", "sans") else "auto")
    elif b == "slideshow-pro":
        # the closing banner: the dark band, or the light card colour with dark words on a "neutral" page (direction.py)
        put("accent_color", r["accent_on_banner"])
        put("overlay_color", r["banner"])
        put("text_color", r["on_banner"])
        put("button_bg", r["button_bg"])
        put("button_color", r["button_text"])
        put("button_style", d.shape["button"])
        put("chip_style", d.shape["chips"])
        put("accent_font", d.type["accent_font"])
        put("heading_font", d.type["heading_font"])
        put("eyebrow_style", d.type["eyebrow_style"])
        put("transition", d.motion["transition"])
        put("autoplay_seconds", d.motion["seconds"])
        put("background", r["banner"])
        if sec.kind == "hero_home":  # the home hero: edge to edge like the full-image banner, its words keep their own inner space
            for key, value in (("padding_top", 0), ("padding_bottom", 0), ("side_padding", 0), ("corner_radius", 0), ("container_width", 1920)):
                put(key, value)
            if r.get("dark_button_bg"):  # the palette method: a button that stands out on the dark shade over the photo
                put("button_bg", r["dark_button_bg"])
                put("button_color", r["dark_button_text"])

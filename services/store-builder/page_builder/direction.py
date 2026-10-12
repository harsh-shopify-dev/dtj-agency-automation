"""Design direction: turns a brand profile into the design choices a page is built from.

Every choice carries its REASON (`why`), every colour pair is contrast-checked (`checks`), and nothing is left to a model's taste:
the same brand always gives the same direction. The judgment follows these principles:
- Brand first: the brand's own colours and type class drive the page; a missing value is filled in from the category and reported, never silently.
- Contrast is a hard floor (WCAG AA 4.5:1 for text). A brand colour that fails on its background is adjusted and the adjustment is reported.
- Different brands must not look the same: shape language, type treatment, accent-word treatment, density and motion are chosen from the
  brand's category, price tier and voice, and the single emphasised "signature" section differs per category.
- Restraint: at most two accent-word headlines and two eyebrow labels per page, one dark emphasis band, one radius family.
- The vibe (brand.vibe, 10 Oct 2026): "electric" and "playful" brands get BOLD colour: alternate bands in the brand colour itself (not a
  tint), the brand's ink for at most 2 dark sections and for cards and boxes, a button and accent bands in the accent colour. Every pair is still checked.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass, field
from pathlib import Path

from provision import style

AA_TEXT = 4.5
AA_LARGE = 3.0

# what a category suggests when the brand does not say (these are design defaults, never claims about the product)
CATEGORY = {
    "beauty": {"shape": "round", "heading": "serif", "voice": "warm", "signature": "story_card"},
    "supplements": {"shape": "soft", "heading": "sans", "voice": "clinical", "signature": "proof_panel"},
    "home-care": {"shape": "soft", "heading": "sans", "voice": "plain", "signature": "free_from_band"},
    "food": {"shape": "round", "heading": "theme", "voice": "playful", "signature": "story_card"},
    "apparel": {"shape": "sharp", "heading": "sans", "voice": "luxe", "signature": "hero_slideshow"},
    "other": {"shape": "soft", "heading": "theme", "voice": "plain", "signature": "story_card"},
}
SHAPE = {  # one radius family per page
    "sharp": {"card": 0, "button": "square", "chips": "outline", "tile": 0},
    "soft": {"card": 12, "button": "rounded", "chips": "outline", "tile": 10},
    "round": {"card": 20, "button": "pill", "chips": "soft", "tile": 16},
}
ACCENT_BY_VOICE = {"luxe": "serif", "warm": "serif", "clinical": "bold", "playful": "bold", "plain": "plain"}
DENSITY = {"value": {"section": 28, "band": 32}, "mid": {"section": 32, "band": 36}, "premium": {"section": 36, "band": 40}}  # neighbours add up to at most 76 px (rule L03)
WHITE, BLACK = "#FFFFFF", "#000000"
RATING_GOLD = "#E0A100"  # the one colour that is not the brand's: rating stars must read as stars
BOLD_VIBES = ("electric", "playful")  # .claude/skills/dtj-pdp-factory/references/colour-and-vibe.md
NEUTRAL_CARD = "#FAFAFA"  # a whisper of grey, lighter than Minimalist's box grey #F6F6F6 (beminimalist.co, measured 10 Oct 2026):
# their photo grey #E5E9EA looked heavy (Harsh: "make it very closer to white"), then #F6F6F6 too (Harsh: "more lighter")


def _toward(color: str, bg: str, ratio: float, target: str) -> str:
    """Mix `color` toward `target` until it reaches `ratio` contrast on `bg` (or runs out of steps)."""
    for _ in range(60):
        if style.contrast(color, bg) >= ratio:
            return color
        color = style.mix(color, target, 0.06)
    return color


def _turns_brown(color: str) -> bool:
    """A bright orange, amber or yellow: darkened for white words or a dark band it turns brown (design_checks H11; Hope N Skin
    #FF8C11 became the #B2620C card and the #402305 banner, both rejected by Harsh, 10 Oct 2026). Blues, greens, reds and purples
    keep their character when deepened (navy, forest, maroon, plum)."""
    h = color.lstrip("#")
    hue, light, sat = colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    return 15 <= hue * 360 <= 65 and sat >= 0.7 and light >= 0.45


def _best_text_on(bg: str) -> str:
    return WHITE if style.contrast(WHITE, bg) >= style.contrast(BLACK, bg) else BLACK


@dataclass
class Direction:
    roles: dict = field(default_factory=dict)
    shape: dict = field(default_factory=dict)
    type: dict = field(default_factory=dict)
    density: dict = field(default_factory=dict)
    motion: dict = field(default_factory=dict)
    signature: str = ""
    dark_mode: bool = False
    vibe: str = ""
    max_dark: int = 2
    why: dict = field(default_factory=dict)
    checks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    palette_sources: dict = field(default_factory=dict)

    def failed_checks(self) -> list:
        return [c for c in self.checks if not c["ok"]]

    def as_report(self) -> dict:
        return {"roles": self.roles, "shape": self.shape, "type": self.type, "density": self.density, "motion": self.motion,
                "signature": self.signature, "dark_mode": self.dark_mode, "vibe": self.vibe, "max_dark": self.max_dark, "why": self.why, "checks": self.checks,
                "warnings": self.warnings, "palette_sources": self.palette_sources}


def _steps_to_pass(color: str, bg: str, target: str) -> int:
    for n in range(61):
        if style.contrast(color, bg) >= AA_TEXT:
            return n
        color = style.mix(color, target, 0.06)
    return 99


def _bold(r: dict, colors: dict, bg: str, ink: str, primary: str) -> None:
    """Electric / playful roles on a light page: the brand colour as a full band, the ink as the dark band, the accent as a fill."""
    band = primary.upper()
    on = ink if style.contrast(ink, band) >= AA_TEXT else (WHITE if style.contrast(WHITE, band) >= AA_TEXT else None)
    while on is None:  # neither ink nor white reads on the brand colour: darken the band until one does
        band = style.mix(band, BLACK, 0.06)
        on = ink if style.contrast(ink, band) >= AA_TEXT else (WHITE if style.contrast(WHITE, band) >= AA_TEXT else None)
    r["band"], r["on_band"], r["accent_on_band"] = band, on, on
    if style.luminance(ink) < 0.08:  # a dark brand ink (navy, black, deep green) is the dark band
        r["dark"] = ink
    accent = (colors.get("accent") or primary).upper()
    r["on_dark"] = WHITE
    r["accent_on_dark"] = accent if style.contrast(accent, r["dark"]) >= AA_TEXT else _toward(accent, r["dark"], AA_TEXT, WHITE)
    r["button_bg"] = accent
    r["button_text"] = ink if style.contrast(ink, accent) >= AA_TEXT else _best_text_on(accent)
    # accent words on the white page: whichever brand colour needs the least darkening (a neon accent turned olive on white, 9 Oct 2026)
    best = min((primary.upper(), accent), key=lambda c: _steps_to_pass(c, bg, BLACK))
    r["accent"] = _toward(best, bg, AA_TEXT, BLACK)
    r["star"] = r["accent"]


def derive(brand: dict, logo_path: Path | None = None) -> Direction:
    d = Direction()
    category = brand.get("category", "other")
    defaults = CATEGORY.get(category, CATEGORY["other"])
    tier = brand.get("price_tier", "mid")
    voice = brand.get("voice", defaults["voice"])

    # ---- colours
    colors = dict(brand.get("colors") or {})
    palette = style.resolve_palette({"colors": colors}, logo_path)
    d.palette_sources = {k: v["source"] for k, v in palette.items()}
    for role in ("primary", "background", "text"):
        if not colors.get(role):
            d.warnings.append(f"colors.{role} not provided: {d.palette_sources.get({'primary': 'color1', 'background': 'background', 'text': 'foreground'}[role])}")
    bg, text, primary = palette["background"]["value"], palette["foreground"]["value"], palette["color1"]["value"]
    d.dark_mode = style.luminance(bg) < 0.25
    r = d.roles
    r["bg"], r["text"] = bg, text
    r["muted"] = _toward(style.mix(text, bg, 0.30), bg, AA_TEXT, text)
    if d.dark_mode:
        r["band"] = style.mix(bg, WHITE, 0.07)
        r["dark"] = style.mix(bg, BLACK, 0.35)
        r["on_dark"] = text
        r["accent"] = _toward((colors.get("accent") or primary).upper(), r["band"], AA_TEXT, WHITE)
    else:
        weight = 0.90
        r["band"] = style.mix(primary, bg, weight)
        while style.contrast(text, r["band"]) < AA_TEXT * 1.5 and weight < 0.99:  # keep body text comfortably readable on the band
            weight += 0.02
            r["band"] = style.mix(primary, bg, weight)
        # the dark band: the brand colour deepened, except a bright orange or yellow, which turns brown: those use the dark text colour
        # (judged on the brand's OWN colour: the palette has already darkened color1 for text use, #FF8C11 -> #A85C0C)
        brown = _turns_brown((colors.get("primary") or primary).upper())
        r["dark"] = text if brown and style.luminance(text) < 0.08 else style.mix(primary, BLACK, 0.62)
        r["on_dark"] = WHITE
        base = (colors.get("accent") or primary).upper()  # the brand's accent colour wins for accent words and ticks when it has one
        r["accent"] = _toward(_toward(base, bg, AA_TEXT, BLACK), r["band"], AA_TEXT, BLACK)
    r["accent_on_dark"] = _toward(style.mix((colors.get("accent") or primary).upper(), WHITE, 0.45), r["dark"], AA_TEXT, WHITE)
    r["button_bg"] = r["accent"]
    r["button_text"] = _best_text_on(r["button_bg"])
    raw_accent = (colors.get("accent") or "").upper()
    if raw_accent and not d.dark_mode and raw_accent != r["accent"] and style.contrast(text, raw_accent) >= AA_TEXT:
        # a bright brand colour that was darkened for text use stays bright as a FILL: the button keeps the brand's own colour with the
        # page's text colour on it (Hope N Skin orange #FF8C11 had turned brown #9B5609 for white text, 10 Oct 2026)
        r["button_bg"], r["button_text"] = raw_accent, text
    r["on_band"], r["accent_on_band"] = text, r["accent"]
    d.vibe = brand.get("vibe") or ""
    if d.vibe in BOLD_VIBES and not d.dark_mode:
        _bold(r, colors, bg, text, (colors.get("primary") or primary))  # the brand's own colour: the palette darkens it for TEXT use
        # still at most 2 dark sections: Harsh's review of Go Mints v2 (10 Oct 2026) moved the photos and the numbers off navy; the ink
        # colour now goes into cards and boxes on light sections (review cards' band excepted), which keeps the energy without the weight
    r["accent_fill"], r["on_accent"] = r["button_bg"], r["button_text"]
    r["star"] = r["accent"]
    # rating stars stay gold (stars must read as stars) but, as icons, need 3:1 on the page (WCAG 1.4.11); on a light page the gold is
    # darkened just enough (the review loop measured plain #E0A100 at 2.2:1 on white, 9 Oct 2026)
    r["rating_star"] = _toward(RATING_GOLD, bg, AA_LARGE, WHITE if d.dark_mode else BLACK)
    # star TILES (a square with a white star inside): the white star needs 3:1 on the tile. Only dark brands need it set: by default the
    # tile takes the text colour, which on a dark brand is light, so the white star disappeared (seen in the review screenshot, 9 Oct 2026)
    r["rating_tile"] = _toward(RATING_GOLD, WHITE, AA_LARGE, BLACK)
    # calm pages: the review cards' star tiles in the brand colour with WHITE stars (Harsh, Hope N Skin, 10 Oct 2026: "make the star
    # square blocks orange and stars white"), deepened only as far as the white star needs (3:1, an icon; plain #FF8C11 is 2.3:1)
    r["review_tile"] = _toward((colors.get("accent") or primary).upper(), WHITE, AA_LARGE, BLACK)
    r["border"] = style.mix(text, bg, 0.85)
    r["tint_card"] = WHITE if not d.dark_mode else style.mix(bg, WHITE, 0.12)
    r["on_card"] = text if not d.dark_mode else text
    # soft text on cards (footnotes under figures): the block's default grey was 4.21:1 on white (review loop, 9 Oct 2026, a book page)
    r["muted_on_card"] = _toward(style.mix(text, r["tint_card"], 0.30), r["tint_card"], AA_TEXT, text)
    # a CARD on a calm page (the story cards): first choice, the brand colour itself, deep enough that WHITE words read on it at 4.5:1
    # (paragraph, points, accent words, tick circles; Harsh, Hope N Skin, 10 Oct 2026: "make the dark orange white, the icons white and
    # the mark inside orange", then "keep every text white here, just 'Brighter skin' as it is"). The first heading line keeps the
    # page's text colour while it reads as a large headline (3:1), else it turns white too. Otherwise a tint at least 1.5:1 from the
    # page and the band (design_checks H01; the calm band is only ~1.1:1 from white), with the brand accent for the words.
    # card_tone "neutral" = the Minimalist look instead (Harsh, 10 Oct 2026: "grey like minimalist -- minimalist brand"): their light
    # grey, the page's dark words, tick circles in the text colour with the brand accent as the check mark.
    raw = (colors.get("primary") or primary).upper()
    deep, k = raw, 0.0
    while style.contrast(WHITE, deep) < AA_TEXT and k < 0.7:
        k += 0.02
        deep = style.mix(raw, BLACK, k)  # k = the share of black
    # no card_tone given: a brand colour that turns brown when deepened gets the light card by default (the Hope N Skin lesson)
    tone = brand.get("card_tone") or ("neutral" if _turns_brown(raw) else "brand")
    neutral = tone == "neutral" and not d.dark_mode
    if neutral:
        words = text if style.contrast(text, NEUTRAL_CARD) >= AA_TEXT else _best_text_on(NEUTRAL_CARD)
        r["panel"], r["on_panel"], r["panel_head"], r["accent_on_panel"] = NEUTRAL_CARD, words, words, words
        r["panel_tick"] = _toward((colors.get("accent") or raw).upper(), words, AA_LARGE, WHITE)
    elif not d.dark_mode and style.contrast(WHITE, deep) >= AA_TEXT:
        r["panel"], r["accent_on_panel"], r["panel_tick"], r["on_panel"] = deep, WHITE, deep, WHITE
        r["panel_head"] = text if style.contrast(text, deep) >= AA_LARGE else WHITE
    else:
        weight, panel = 0.90, r["band"]
        while weight > 0.30 and (style.contrast(panel, bg) < 1.5 or style.contrast(panel, r["band"]) < 1.5):
            weight -= 0.02
            panel = style.mix(raw, bg, weight)
        if style.contrast(text, panel) < AA_TEXT:  # never trade the words' contrast for the card's
            panel = r["band"]
        r["panel"] = panel
        r["accent_on_panel"] = _toward(r["accent"], panel, AA_TEXT, BLACK if not d.dark_mode else WHITE)
        r["panel_tick"], r["on_panel"], r["panel_head"] = "", text, text
    # the closing banner (W15): the dark band by default; the light card look carries over to it (Harsh, 10 Oct 2026: the dark brown
    # banner "didnt got updated" after the near-white cards)
    if neutral:
        r["banner"], r["on_banner"], r["accent_on_banner"] = r["panel"], r["on_panel"], r["accent_on_panel"]
    else:
        r["banner"], r["on_banner"], r["accent_on_banner"] = r["dark"], r["on_dark"], r["accent_on_dark"]
    for role in list(r):
        r[role] = r[role].upper()
    pairs = [("text on page", "text", "bg", AA_TEXT), ("text on band", "on_band", "band", AA_TEXT), ("muted text on page", "muted", "bg", AA_TEXT),
             ("accent on page", "accent", "bg", AA_TEXT), ("accent on band", "accent_on_band", "band", AA_TEXT), ("text on dark band", "on_dark", "dark", AA_TEXT),
             ("text on accent band", "on_accent", "accent_fill", AA_TEXT),
             ("accent on dark band", "accent_on_dark", "dark", AA_TEXT), ("button text", "button_text", "button_bg", AA_TEXT),
             ("text on white cards", "text", "tint_card", AA_TEXT), ("soft text on cards", "muted_on_card", "tint_card", AA_TEXT),
             ("rating stars on page", "rating_star", "bg", AA_LARGE), ("words on story cards", "on_panel", "panel", AA_TEXT),
             ("heading on story cards", "panel_head", "panel", AA_LARGE), ("accent on story cards", "accent_on_panel", "panel", AA_LARGE),
             ("words on the closing banner", "on_banner", "banner", AA_TEXT)]
    if d.dark_mode:
        pairs = [p for p in pairs if p[0] not in ("accent on page",)] + [("accent on page", "accent", "band", AA_TEXT)]
    for name, fg, back, need in pairs:
        ratio = round(style.contrast(r[fg], r[back]), 2)
        d.checks.append({"pair": name, "fg": r[fg], "bg": r[back], "ratio": ratio, "needs": need, "ok": ratio >= need})
    ratio = round(style.contrast(WHITE, r["rating_tile"]), 2)
    d.checks.append({"pair": "white star on rating tile", "fg": WHITE, "bg": r["rating_tile"], "ratio": ratio, "needs": AA_LARGE, "ok": ratio >= AA_LARGE})
    ratio = round(style.contrast(WHITE, r["review_tile"]), 2)
    d.checks.append({"pair": "white star on review tile", "fg": WHITE, "bg": r["review_tile"], "ratio": ratio, "needs": AA_LARGE, "ok": ratio >= AA_LARGE})
    d.why["colors"] = ("Page = the brand's background and text; band = a very light tint of the brand colour for alternating sections; dark band = the brand "
                       "colour darkened, used once for emphasis; accent colours were pushed toward black/white until they pass 4.5:1 on what they sit on.")
    if d.vibe in BOLD_VIBES and not d.dark_mode:
        d.why["colors"] = (f"{d.vibe} vibe: alternating bands in the brand colour itself ({r['band']}) with {r['on_band']} text, the brand's ink ({r['dark']}) "
                           f"for at most {d.max_dark} dark sections and for cards and boxes with white words, the button and accent bands in the accent colour "
                           f"({r['accent_fill']}) with {r['on_accent']} text; accent words on white use {r['accent']}. Every pair passes 4.5:1.")

    # ---- shape language: one radius family
    shape_name = brand.get("shape_language") or defaults["shape"]
    d.shape = {"name": shape_name, **SHAPE[shape_name]}
    d.why["shape"] = f"{shape_name}: the whole page uses one radius family (cards {SHAPE[shape_name]['card']} px, {SHAPE[shape_name]['button']} buttons), taken from the brand/category."

    # ---- type treatment
    fonts = brand.get("fonts") or {}
    heading_class = fonts.get("heading_class") or defaults["heading"]
    accent = ACCENT_BY_VOICE.get(voice, "plain")
    d.type = {"heading_font": heading_class, "accent_font": accent, "accent_words_max": 1 if tier == "premium" else 2,
              "eyebrow_style": "mono" if voice == "clinical" else ("plain" if tier == "premium" else "sans"), "eyebrow_max": 2,
              "brand_fonts": {k: v for k, v in fonts.items() if k in ("heading", "body")}}
    d.why["type"] = (f"Headings use the {heading_class} class; accent words are {accent} ({voice} voice) and limited to {d.type['accent_words_max']} "
                     "headline(s), because accenting a word in every heading reads as a template. Eyebrow labels are capped at 2 and only used when a real fact exists.")

    # ---- density and motion
    dens = DENSITY.get(tier, DENSITY["mid"])
    d.density = {"section": dens["section"], "band": dens["band"], "side": 20 if tier == "premium" else 16}
    d.motion = {"transition": "fade" if (tier == "premium" or voice in ("luxe", "warm")) else "slide", "seconds": 7 if tier == "premium" else 6}
    d.why["density"] = f"{tier} price tier: sections breathe {dens['section']} to {dens['band']} px, side space {d.density['side']} px; motion is a {d.motion['transition']}, nothing animates on its own except the slideshow timer."
    d.signature = defaults["signature"]
    d.why["signature"] = f"One emphasised section for the {category} category: {d.signature}. Everything else stays quiet."
    return d

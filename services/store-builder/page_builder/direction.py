"""Design direction: turns a brand profile into the design choices a page is built from.

Every choice carries its REASON (`why`), every colour pair is contrast-checked (`checks`), and nothing is left to a model's taste:
the same brand always gives the same direction. The judgment follows these principles:
- Brand first: the brand's own colours and type class drive the page; a missing value is filled in from the category and reported, never silently.
- Contrast is a hard floor (WCAG AA 4.5:1 for text). A brand colour that fails on its background is adjusted and the adjustment is reported.
- Different brands must not look the same: shape language, type treatment, accent-word treatment, density and motion are chosen from the
  brand's category, price tier and voice, and the single emphasised "signature" section differs per category.
- Restraint: at most two accent-word headlines and two eyebrow labels per page, one dark emphasis band, one radius family.
"""
from __future__ import annotations

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


def _toward(color: str, bg: str, ratio: float, target: str) -> str:
    """Mix `color` toward `target` until it reaches `ratio` contrast on `bg` (or runs out of steps)."""
    for _ in range(60):
        if style.contrast(color, bg) >= ratio:
            return color
        color = style.mix(color, target, 0.06)
    return color


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
    why: dict = field(default_factory=dict)
    checks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    palette_sources: dict = field(default_factory=dict)

    def failed_checks(self) -> list:
        return [c for c in self.checks if not c["ok"]]

    def as_report(self) -> dict:
        return {"roles": self.roles, "shape": self.shape, "type": self.type, "density": self.density, "motion": self.motion,
                "signature": self.signature, "dark_mode": self.dark_mode, "why": self.why, "checks": self.checks,
                "warnings": self.warnings, "palette_sources": self.palette_sources}


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
        r["dark"] = style.mix(primary, BLACK, 0.62)
        r["on_dark"] = WHITE
        base = (colors.get("accent") or primary).upper()  # the brand's accent colour wins for accent words and ticks when it has one
        r["accent"] = _toward(_toward(base, bg, AA_TEXT, BLACK), r["band"], AA_TEXT, BLACK)
    r["accent_on_dark"] = _toward(style.mix((colors.get("accent") or primary).upper(), WHITE, 0.45), r["dark"], AA_TEXT, WHITE)
    r["button_bg"] = r["accent"]
    r["button_text"] = _best_text_on(r["button_bg"])
    r["star"] = r["accent"]
    # rating stars stay gold (stars must read as stars) but, as icons, need 3:1 on the page (WCAG 1.4.11); on a light page the gold is
    # darkened just enough (the review loop measured plain #E0A100 at 2.2:1 on white, 9 Oct 2026)
    r["rating_star"] = _toward(RATING_GOLD, bg, AA_LARGE, WHITE if d.dark_mode else BLACK)
    # star TILES (a square with a white star inside): the white star needs 3:1 on the tile. Only dark brands need it set: by default the
    # tile takes the text colour, which on a dark brand is light, so the white star disappeared (seen in the review screenshot, 9 Oct 2026)
    r["rating_tile"] = _toward(RATING_GOLD, WHITE, AA_LARGE, BLACK)
    r["border"] = style.mix(text, bg, 0.85)
    r["tint_card"] = WHITE if not d.dark_mode else style.mix(bg, WHITE, 0.12)
    r["on_card"] = text if not d.dark_mode else text
    # soft text on cards (footnotes under figures): the block's default grey was 4.21:1 on white (review loop, 9 Oct 2026, a book page)
    r["muted_on_card"] = _toward(style.mix(text, r["tint_card"], 0.30), r["tint_card"], AA_TEXT, text)
    for role in list(r):
        r[role] = r[role].upper()
    pairs = [("text on page", "text", "bg", AA_TEXT), ("text on band", "text", "band", AA_TEXT), ("muted text on page", "muted", "bg", AA_TEXT),
             ("accent on page", "accent", "bg", AA_TEXT), ("accent on band", "accent", "band", AA_TEXT), ("text on dark band", "on_dark", "dark", AA_TEXT),
             ("accent on dark band", "accent_on_dark", "dark", AA_TEXT), ("button text", "button_text", "button_bg", AA_TEXT),
             ("text on white cards", "text", "tint_card", AA_TEXT), ("soft text on cards", "muted_on_card", "tint_card", AA_TEXT),
             ("rating stars on page", "rating_star", "bg", AA_LARGE)]
    if d.dark_mode:
        pairs = [p for p in pairs if p[0] not in ("accent on page",)] + [("accent on page", "accent", "band", AA_TEXT)]
    for name, fg, back, need in pairs:
        ratio = round(style.contrast(r[fg], r[back]), 2)
        d.checks.append({"pair": name, "fg": r[fg], "bg": r[back], "ratio": ratio, "needs": need, "ok": ratio >= need})
    ratio = round(style.contrast(WHITE, r["rating_tile"]), 2)
    d.checks.append({"pair": "white star on rating tile", "fg": WHITE, "bg": r["rating_tile"], "ratio": ratio, "needs": AA_LARGE, "ok": ratio >= AA_LARGE})
    d.why["colors"] = ("Page = the brand's background and text; band = a very light tint of the brand colour for alternating sections; dark band = the brand "
                       "colour darkened, used once for emphasis; accent colours were pushed toward black/white until they pass 4.5:1 on what they sit on.")

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

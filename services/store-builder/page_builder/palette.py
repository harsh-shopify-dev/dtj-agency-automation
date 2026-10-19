"""The palette method top product designers use, as code (researched 19 Oct 2026 for Harsh: "find how to apply a best color palette how top
figma designers think and decide the color palette").

    1. Start from the brand's own colour (pack or logo), plus a second colour the brand already uses (its accent).
    2. A 12-step scale per colour in OKLCH (even steps to the eye, unlike HSL), each step with one job (Radix Colors):
       1-2 page and soft bands, 3-5 cards / tiles / selected, 6-8 borders, 9 the solid colour (bands, buttons), 10 its hover, 11-12 text.
    3. Greys are never pure: 12 neutrals carry a little of the brand's hue (Refactoring UI: "saturate your greys").
    4. One accent for actions and highlights only, about 60 % light ground / 30 % brand family / 10 % accent (the 60-30-10 rule).
    5. Every pair is measured (WCAG 2): words 4.5:1, large words and icons 3:1, and a button's edge 3:1 against what it sits on, so the
       button colour is chosen PER background, never one colour everywhere.
    6. Colours mean things per category: a cleaning brand never gets yellow or brown as a main or button colour (Harsh, 19 Oct 2026:
       "yellow also represents stains ... a blue-green combination would be much more better").

Sources: refactoringui.com (building your colour palette), radix-ui.com (understanding the scale), Material 3 dynamic colour (HCT tonal
palettes), the 60-30-10 rule. Standard library only."""
from __future__ import annotations

import math

STEP_L = [0.985, 0.97, 0.94, 0.905, 0.87, 0.82, 0.75, 0.66, None, None, 0.45, 0.25]  # step 9 = the seed itself, 10 = its hover
NEUTRAL_L = [0.99, 0.975, 0.95, 0.925, 0.90, 0.86, 0.80, 0.70, 0.55, 0.48, 0.40, 0.20]
WHITE = "#FFFFFF"
AA_TEXT, AA_LARGE = 4.5, 3.0
# hues (OKLCH degrees) that read as dirt or stains on a cleaning brand: yellow, amber, brown
AVOID_HUES = {"cleaning": [(40.0, 115.0)]}
CLEANING_CATEGORIES = ("home-care", "cleaning", "hygiene", "laundry")


def _s2l(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _l2s(c: float) -> int:
    c = max(0.0, min(1.0, c))
    return round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))


def _rgb(h: str) -> list[int]:
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def oklch(h: str) -> tuple[float, float, float]:
    """Hex -> (lightness 0-1, chroma, hue in degrees)."""
    r, g, b = (_s2l(x) for x in _rgb(h))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def _linear(L: float, C: float, H: float) -> tuple[float, float, float]:
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)


def to_hex(L: float, C: float, H: float) -> str:
    """OKLCH -> hex, lowering the chroma until the colour exists on screens (sRGB)."""
    while C > 0 and not all(-1e-4 <= c <= 1 + 1e-4 for c in _linear(L, C, H)):
        C -= 0.002
    return "#" + "".join(f"{_l2s(c):02X}" for c in _linear(L, max(C, 0.0), H))


def luminance(h: str) -> float:
    r, g, b = (_s2l(x) for x in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    x, y = sorted((luminance(a), luminance(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def ramp(seed: str) -> list[str]:
    """12 steps from one colour: same hue, lightness in even visual steps, chroma highest near the seed (step 9)."""
    L9, C9, H = oklch(seed)
    out = []
    for i, L in enumerate(STEP_L, 1):
        if i == 9:
            out.append(seed.upper())
            continue
        if i == 10:
            L = L9 - 0.05
        C = C9 * (0.12 + 0.88 * min(1.0, (1 - L) / (1 - L9 + 1e-6))) if i < 9 else C9 * 0.95
        out.append(to_hex(L, C, H))
    return out


def neutrals(hue: float) -> list[str]:
    """12 greys with a little of the brand's hue (cool brands get cool greys, warm brands warm ones)."""
    return [to_hex(L, 0.012 if L > 0.5 else 0.02, hue) for L in NEUTRAL_L]


def hue_gap(a: str, b: str) -> float:
    return abs((oklch(a)[2] - oklch(b)[2] + 180) % 360 - 180)


def avoided(colour: str, category: str) -> bool:
    """True when the colour reads as dirt for this category (a cleaning brand's yellow or brown)."""
    if category not in CLEANING_CATEGORIES:
        return False
    L, C, H = oklch(colour)
    return C > 0.04 and any(lo <= H <= hi for lo, hi in AVOID_HUES["cleaning"])


def deepen_for(colour: str, words: str, need: float = AA_TEXT) -> str:
    """The colour, darkened in OKLCH (hue kept) until the words read on it."""
    L, C, H = oklch(colour)
    out = colour.upper()
    while contrast(words, out) < need and L > 0.05:
        L -= 0.01
        out = to_hex(L, C, H)
    return out


def button_for(background: str, options: list[tuple[str, str]]) -> tuple[str, str]:
    """The first (fill, words) pair whose words read at 4.5:1 AND whose edge stands 3:1 from the background (WCAG 1.4.11)."""
    for fill, words in options:
        if contrast(words, fill) >= AA_TEXT and contrast(fill, background) >= AA_LARGE:
            return fill, words
    return max(options, key=lambda o: contrast(o[0], background))


def roles(primary: str, accent: str, category: str) -> dict:
    """The page roles from the brand colour and its accent (both hex). Every pair is checked by direction.py like the other roles."""
    b, a = ramp(primary), ramp(accent)
    n = neutrals(oklch(primary)[2])
    text, muted = n[11], n[9]
    band = b[2] if contrast(text, b[2]) >= AA_TEXT * 1.5 else b[1]
    dark = b[11]
    # a second soft band from the ACCENT family (blue-green pages alternate blue tint, white and mint instead of one pale blue four times)
    mint = next((a[i] for i in (1, 0) if contrast(text, a[i]) >= AA_TEXT * 1.5), a[0])
    accent_on_mint = b[10] if contrast(b[10], mint) >= AA_TEXT else b[11]
    deep_accent = deepen_for(accent, WHITE)  # the action colour with white words (greens and blues keep their character when deepened)
    light_accent = next((s for s in a[:6][::-1] if contrast(s, dark) >= AA_TEXT and contrast(s, primary) >= AA_TEXT), a[2])
    page_button = button_for(WHITE, [(deep_accent, WHITE), (accent.upper(), text), (primary.upper(), WHITE)])
    band_button = button_for(band, [(deep_accent, WHITE), (primary.upper(), WHITE), (text, WHITE)])
    fill_button = button_for(primary.upper(), [(WHITE, deepen_for(primary, WHITE)), (light_accent, text)])
    dark_button = button_for(dark, [(accent.upper(), text), (light_accent, text), (WHITE, dark)])
    return {
        "bg": WHITE, "text": text, "muted": muted, "border": n[5],
        "band": band, "on_band": text, "mint": mint, "accent_on_mint": accent_on_mint,
        "accent": b[10], "accent_on_band": b[10] if contrast(b[10], band) >= AA_TEXT else b[11],
        "dark": dark, "on_dark": WHITE, "accent_on_dark": light_accent,
        "button_bg": page_button[0], "button_text": page_button[1],
        "band_button_bg": band_button[0], "band_button_text": band_button[1],
        "accent_fill": primary.upper(), "on_accent": WHITE if contrast(WHITE, primary) >= AA_TEXT else text,
        "accent_on_fill": light_accent, "fill_button_bg": fill_button[0], "fill_button_text": fill_button[1],
        "dark_button_bg": dark_button[0], "dark_button_text": dark_button[1],
        "mark": deepen_for(accent, WHITE, AA_LARGE),  # ticks and small icons in the accent family, 3:1 on white
        "tint_card": WHITE, "on_card": text, "muted_on_card": muted,
        "panel": b[1], "on_panel": text, "panel_head": text, "accent_on_panel": b[10], "panel_tick": "",
        "banner": dark, "on_banner": WHITE, "accent_on_banner": light_accent,
        "_ramps": {"brand": b, "accent": a, "neutral": n},
        "_warnings": [f"{c} reads as dirt or stains on a {category} page (yellow/brown family): pick another accent" for c in (primary, accent)
                      if avoided(c, category)],
    }

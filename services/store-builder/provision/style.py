"""Turn the optional brand `style` block into Horizon theme settings.

Horizon 4.2.0 (read from the master theme, 5 Oct 2026):
- colors live in `current.color_palette` of config/settings_data.json: background, foreground, color1, color2, color3
  (color1 = main brand color, color2 = soft surface, color3 = borders)
- fonts are handles like `inter_n7` (family, weight)
- the logo is the `logo` image setting (needs the file uploaded to the store first)

Missing colors are filled in, never silently: every value is reported with its source
("provided", "from_logo", "default", "derived" or "adjusted_for_contrast").
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from . import templates

DEFAULTS = {"background": "#FFFFFF", "foreground": "#000000", "primary": "#333333"}
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_FAMILY = re.compile(r"^[A-Za-z0-9 ]{2,40}$")
MIN_TEXT_CONTRAST = 4.5  # WCAG AA for normal text
MIN_BRAND_CONTRAST = 4.5  # primary is used for buttons with text on top, so hold it to the same bar


def _rgb(hex_: str) -> tuple[int, int, int]:
    return int(hex_[1:3], 16), int(hex_[3:5], 16), int(hex_[5:7], 16)


def _hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(c))) for c in rgb))


def luminance(hex_: str) -> float:
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, weight_b: float) -> str:
    return _hex(tuple(x * (1 - weight_b) + y * weight_b for x, y in zip(_rgb(a), _rgb(b))))


def dominant_color(path: Path) -> str | None:
    """Most common clearly-coloured pixel in the logo (ignores transparent, near-white, near-black and grey pixels)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as im:
        im = im.convert("RGBA")
        im.thumbnail((96, 96))
        counts: Counter = Counter()
        for r, g, b, a in im.getdata():
            if a < 200 or max(r, g, b) < 40 or min(r, g, b) > 225 or max(r, g, b) - min(r, g, b) < 24:
                continue
            counts[(r // 16 * 16 + 8, g // 16 * 16 + 8, b // 16 * 16 + 8)] += 1
    return _hex(counts.most_common(1)[0][0]) if counts else None


def _darken_until(color: str, background: str, target: float) -> str:
    for _ in range(40):
        if contrast(color, background) >= target:
            return color
        color = mix(color, "#000000", 0.08)
    return color


def resolve_palette(style: dict | None, logo_path: Path | None = None) -> dict:
    """Returns {role: {"value": "#RRGGBB", "source": ...}} for background, foreground, color1, color2, color3."""
    colors = dict((style or {}).get("colors") or {})
    for key, value in colors.items():
        if not _HEX.match(value):
            raise ValueError(f"colors.{key} must look like #1A2B3C, got {value!r}")
    out: dict[str, dict] = {}

    bg = colors.get("background")
    out["background"] = {"value": (bg or DEFAULTS["background"]).upper(), "source": "provided" if bg else "default"}

    fg = colors.get("text")
    fg_value, fg_source = (fg or DEFAULTS["foreground"]).upper(), "provided" if fg else "default"
    if contrast(fg_value, out["background"]["value"]) < MIN_TEXT_CONTRAST:
        fg_value = "#000000" if luminance(out["background"]["value"]) > 0.4 else "#FFFFFF"
        fg_source = "adjusted_for_contrast"
    out["foreground"] = {"value": fg_value, "source": fg_source}

    primary = colors.get("primary")
    source = "provided"
    if not primary:
        primary, source = (dominant_color(logo_path) if logo_path else None), "from_logo"
        if not primary:
            primary, source = DEFAULTS["primary"], "default"
    primary = primary.upper()
    fixed = _darken_until(primary, out["background"]["value"], MIN_BRAND_CONTRAST) if luminance(out["background"]["value"]) > 0.4 else primary
    if fixed != primary:
        primary, source = fixed, "adjusted_for_contrast"
    out["color1"] = {"value": primary, "source": source}

    accent = colors.get("accent")
    out["color2"] = {"value": accent.upper(), "source": "provided"} if accent else \
        {"value": mix(primary, out["background"]["value"], 0.88), "source": "derived"}
    out["color3"] = {"value": mix(out["foreground"]["value"], out["background"]["value"], 0.85), "source": "derived"}
    return out


def font_handle(family: str, weight: int = 4) -> str:
    """Shopify font handle, e.g. ('Playfair Display', 7) -> 'playfair_display_n7'. The family cannot be checked offline:
    the first push to a theme is the real test (see resolve_fonts)."""
    if not _FAMILY.match(family):
        raise ValueError(f"bad font family name: {family!r}")
    return f"{re.sub(r'[^a-z0-9]+', '_', family.lower()).strip('_')}_n{weight}"


def resolve_fonts(style: dict | None) -> dict:
    fonts = (style or {}).get("fonts") or {}
    out = {}
    if fonts.get("heading"):
        out["type_heading_font"] = font_handle(fonts["heading"], 7)
        out["type_accent_font"] = font_handle(fonts["heading"], 7)
    if fonts.get("body"):
        out["type_body_font"] = font_handle(fonts["body"], 4)
        out["type_subheading_font"] = font_handle(fonts["body"], 5)
    return out


def apply_to_settings(text: str, palette: dict, fonts: dict, logo_ref: str | None = None) -> tuple[str, list[dict]]:
    """Returns (new config/settings_data.json text, change list). Only `current` is edited, never `presets`."""
    header, data = templates.load(text)
    current = data.setdefault("current", {})
    changes: list[dict] = []

    def put(key, value):
        if current.get(key) != value:
            changes.append({"setting": key, "before": current.get(key), "after": value})
            current[key] = value

    pal = dict(current.get("color_palette") or {})
    for role, info in palette.items():
        if pal.get(role) != info["value"]:
            changes.append({"setting": f"color_palette.{role}", "before": pal.get(role), "after": info["value"], "source": info["source"]})
            pal[role] = info["value"]
    current["color_palette"] = pal
    for key, value in fonts.items():
        put(key, value)
    if logo_ref:
        put("logo", logo_ref)
    return templates.dump(header, data), changes

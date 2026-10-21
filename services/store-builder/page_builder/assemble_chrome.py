"""Header and footer (the store's "chrome", on every page) from the brand's palette (Harsh, 21 Oct 2026: "the header and footer will be designed
according to the color palette"). Works on the theme's own two group files, as they are now, and changes only settings and words:

    from page_builder.assemble_chrome import build_chrome
    res = build_chrome(brand, facts, chrome, header_group, footer_group)   # the current sections/header-group.json and footer-group.json
    res.header, res.footer   # the new files (every section, block and id kept; nothing deleted)
    res.report               # colours used, what changed, the words and their sources, problems

What it does (CHROME, CHROME_COLOURS; the numbers from the 21 Oct 2026 study of 24 strong D2C sites, `.claude/skills/dtj-header-footer/
references/study.md`):
- announcement bar: the brand's deep colour with light words; its lines come from the facts (store-wide promises with their source, or
  marked SAMPLE lines on a demo store). Without any line the bar is switched OFF: never Horizon's "Welcome to our store".
- header: the page colour with the text colour, a thin border, sticky; the cart count in the brand's button colours.
- footer: the brand's deep colour (the theme turns its words light by itself), the sign-up in the brand's button colours, a modest sign-up
  line instead of the theme's "exclusive deals" promise, social icons ONLY for the brand's real pages (Horizon's placeholder links to
  facebook.com, instagram.com... are emptied), "Powered by Shopify" off.
Deterministic, nothing talks to Shopify; every word has a recorded origin; every setting is checked against Horizon 4.2.0's schema."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import direction as direction_mod
from .assemble import InputError, _validate
from .palette import contrast

HERE = Path(__file__).resolve().parent
PARTS = json.loads((HERE / "base" / "horizon-chrome-parts.json").read_text(encoding="utf-8"))
HEADER_FILE, FOOTER_FILE = "sections/header-group.json", "sections/footer-group.json"
# Horizon's own placeholders: never left on a client's store
PLACEHOLDER_TEXT = ("welcome to our store", "shop our latest arrival", "get exclusive deals and early access to new products")
SOCIAL_KEYS = ("facebook", "instagram", "youtube", "tiktok", "twitter", "threads", "linkedin", "bluesky", "snapchat", "pinterest", "tumblr", "vimeo")
BARE_SOCIAL = re.compile(r"^https?://(www\.)?(facebook|instagram|youtube|tiktok|twitter|x|threads|linkedin|bsky|snapchat|pinterest|tumblr|vimeo)\.(com|app|net)/?$", re.I)

# The 21 Oct 2026 study of 23 strong D2C home pages (pixels read from their screenshots; .claude/skills/dtj-header-footer/references/study.md):
# an announcement bar on top on 17, 13 of them dark or in a brand colour, about 41 px tall; the header on white on 21, sticky on 17, the logo
# on the left on 12 (centred on 4); the footer dark or in a brand colour on 15 (white or light on 7); a sign-up on 16, social links on 21,
# payment icons on only 4.
# where each colour role goes (direction.roles names); a brand's palette decides the colours, this decides the placement
CHROME_COLOURS = {"announcement": "dark", "announcement_text": "on_dark", "header": "bg", "header_text": "text", "header_border": "border",
                  "bubble": "button_bg", "bubble_text": "button_text", "footer": "dark", "footer_text": "on_dark",
                  "signup_button": "button_bg", "signup_button_text": "button_text", "signup_input": "bg", "signup_input_text": "text"}
CHROME = {"announcement_padding": 10, "announcement_font_size": "0.875rem", "announcement_speed": 5, "header_height": "standard",
          "sticky": "always", "header_border": 1, "footer_padding": (48, 32), "utilities_padding": (16, 20), "footer_gap": 40}


@dataclass
class ChromeResult:
    header: dict
    footer: dict
    report: dict = field(default_factory=dict)


def check_parts(part: str, values: dict) -> list[str]:
    spec, problems = PARTS[part], []
    for key, value in values.items():
        s = spec.get(key)
        if s is None:
            problems.append(f"theme {part}: unknown setting {key!r}")
        elif s["type"] == "select" and value not in s["options"]:
            problems.append(f"theme {part}: {key}={value!r} is not one of {s['options']}")
        elif s["type"] == "range" and not (isinstance(value, (int, float)) and s["min"] <= value <= s["max"]):
            problems.append(f"theme {part}: {key}={value!r} is outside {s['min']}..{s['max']}")
        elif s["type"] == "checkbox" and not isinstance(value, bool):
            problems.append(f"theme {part}: {key} must be true or false")
        elif s["type"] == "color" and value and not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value)) and not str(value).startswith("{{"):
            problems.append(f"theme {part}: {key}={value!r} is not a colour")
    return problems


def _sections_of(group: dict, kind: str) -> list[tuple[str, dict]]:
    return [(sid, group["sections"][sid]) for sid in group.get("order", []) if group["sections"].get(sid, {}).get("type") == kind]


def _lines(chrome: dict, facts: dict) -> list[dict]:
    """The announcement lines: chrome.json first (store-wide promises with sources), else the home facts' announcements."""
    items = (chrome.get("announcements") or (facts.get("announcements") or {}).get("items") or [])
    out = []
    for it in items[:3]:
        text, source = str(it.get("text", "")).strip(), str(it.get("source", "")).strip()
        if not text or not source:
            raise InputError("every announcement line needs text and source")
        if text.lower().rstrip(".!") in PLACEHOLDER_TEXT:
            raise InputError(f"{text!r} is a theme placeholder, not an announcement")
        out.append({"text": text, "source": source, "link": str(it.get("link", "") or "")})
    return out


def build_chrome(brand: dict, facts: dict, chrome: dict | None, header_group: dict, footer_group: dict, *, logo_path: Path | None = None) -> ChromeResult:
    _validate(brand, "brand-profile")
    chrome = chrome or {}
    d = direction_mod.derive(brand, logo_path)
    r = d.roles
    col = {k: r[v] for k, v in CHROME_COLOURS.items()}
    header, footer = copy.deepcopy(header_group), copy.deepcopy(footer_group)
    changes, problems, prov, removed = [], [], {}, []

    # ---- announcement bar
    lines = _lines(chrome, facts)
    for sid, sec in _sections_of(header, "header-announcements"):
        if not lines:
            if not sec.get("disabled"):
                sec["disabled"] = True
                changes.append({"part": sid, "change": "switched off", "why": "no announcement line in the facts (never the theme's placeholder)"})
            continue
        sec.pop("disabled", None)
        pad = CHROME["announcement_padding"]
        sec.setdefault("settings", {}).update({"background_color": col["announcement"], "divider_width": 0, "speed": CHROME["announcement_speed"],
                                               "padding-block-start": pad, "padding-block-end": pad})
        problems += check_parts("header-announcements", sec["settings"])
        old = [sec["blocks"][b]["settings"].get("text", "") for b in sec.get("block_order", []) if b in sec.get("blocks", {})]
        removed += [t for t in old if t.lower().strip(" .!") in PLACEHOLDER_TEXT]
        sec["blocks"], sec["block_order"] = {}, []
        for i, ln in enumerate(lines, 1):
            bid = f"dtj_announcement_{i}"
            s = {"text": ln["text"], "link": ln["link"], "font": "var(--font-subheading--family)", "font_size": CHROME["announcement_font_size"],
                 "weight": "500", "letter_spacing": "normal", "case": "none", "text_color": col["announcement_text"]}
            problems += check_parts("_announcement", s)
            sec["blocks"][bid] = {"type": "_announcement", "settings": s}
            sec["block_order"].append(bid)
            prov[f"{sid}.{bid}"] = {"kind": "sample" if ln["source"].upper().startswith("SAMPLE") else "fact", "source": ln["source"], "text": ln["text"]}
        changes.append({"part": sid, "change": f"{len(lines)} line(s) on the brand's deep colour"})

    # ---- header
    for sid, sec in _sections_of(header, "header"):
        s = sec.setdefault("settings", {})
        s.update({"background_color_top": col["header"], "text_color_top": col["header_text"], "bubble_style": "custom",
                  "bubble_background_color": col["bubble"], "bubble_text_color": col["bubble_text"], "border_width": CHROME["header_border"],
                  "bottom_border_color": col["header_border"], "enable_sticky_header": CHROME["sticky"], "section_height": CHROME["header_height"]})
        problems += check_parts("header", {k: s[k] for k in ("background_color_top", "text_color_top", "bubble_style", "bubble_background_color",
                                                              "bubble_text_color", "border_width", "bottom_border_color", "enable_sticky_header",
                                                              "section_height")})
        changes.append({"part": sid, "change": "page colour with the text colour, thin border, cart count in the button colours"})

    # ---- footer
    brand_name = brand.get("brand_name") or "us"
    signup = chrome.get("newsletter") or {}
    for sid, sec in _sections_of(footer, "footer"):
        top, bottom = CHROME["footer_padding"]
        sec.setdefault("settings", {}).update({"background_color": col["footer"], "padding-block-start": top, "padding-block-end": bottom,
                                               "gap": CHROME["footer_gap"]})
        problems += check_parts("footer", sec["settings"])

        def walk(blocks: dict, path: str):
            for bid, b in (blocks or {}).items():
                bs = b.setdefault("settings", {})
                if b.get("type") == "email-signup":
                    bs.update({"input_style": "custom", "input_background_color": col["signup_input"], "input_text_color": col["signup_input_text"],
                               "style_class": "button-custom", "custom_button_background": col["signup_button"],
                               "custom_button_text": col["signup_button_text"], "custom_button_border": col["signup_button"]})
                    problems.extend(check_parts("email-signup", {k: bs[k] for k in ("input_style", "input_background_color", "input_text_color",
                                                                                     "style_class", "custom_button_background",
                                                                                     "custom_button_text", "custom_button_border")}))
                elif b.get("type") == "text":
                    t = str(bs.get("text", ""))
                    plain = re.sub(r"<[^>]+>", "", t).strip().lower().rstrip(".!")
                    if plain in PLACEHOLDER_TEXT:  # the theme's "exclusive deals" promise: a claim nobody made
                        line = signup.get("text") or f"News and new products from {brand_name}, now and then."
                        bs["text"] = f"<p>{line}</p>"
                        removed.append(re.sub(r"<[^>]+>", "", t).strip())
                        prov[f"{sid}.{path}{bid}"] = {"kind": "fact" if signup.get("text") else "structure",
                                                      "source": signup.get("source", "page structure (no promise, no offer)"), "text": line}
                walk(b.get("blocks"), f"{path}{bid}/")
        walk(sec.get("blocks"), "")
        changes.append({"part": sid, "change": "the brand's deep colour, sign-up in the button colours"})

    social = chrome.get("social") or {}
    for sid, sec in _sections_of(footer, "footer-utilities"):
        top, bottom = CHROME["utilities_padding"]
        sec.setdefault("settings", {}).update({"background_color": col["footer"], "padding-block-start": top, "padding-block-end": bottom,
                                               "divider_color": r.get("muted") or col["footer_text"]})
        problems += check_parts("footer-utilities", sec["settings"])
        for bid, b in (sec.get("blocks") or {}).items():
            bs = b.setdefault("settings", {})
            if b.get("type") == "footer-copyright":
                bs["show_powered_by"] = False
            if b.get("type") == "social-links":
                for key in SOCIAL_KEYS:
                    old = str(bs.get(f"{key}_url") or "")
                    real = social.get(key) or {}
                    if real.get("url"):
                        if not real.get("source"):
                            raise InputError(f"social link {key}: give where it was found (source)")
                        bs[f"{key}_url"] = real["url"]
                        prov[f"{sid}.{bid}.{key}"] = {"kind": "fact", "source": real["source"], "text": real["url"]}
                    elif old:
                        bs[f"{key}_url"] = ""
                        if BARE_SOCIAL.match(old):
                            removed.append(old)
                bs["icon_color"] = col["footer_text"]
                problems += check_parts("social-links", {k: v for k, v in bs.items()})
        changes.append({"part": sid, "change": "same deep colour, real social pages only, 'Powered by Shopify' off"})

    # ---- contrast: every pair a shopper reads
    pairs = {"announcement": (col["announcement_text"], col["announcement"]), "header": (col["header_text"], col["header"]),
             "cart count": (col["bubble_text"], col["bubble"]), "footer": (col["footer_text"], col["footer"]),
             "sign-up button": (col["signup_button_text"], col["signup_button"]), "sign-up field": (col["signup_input_text"], col["signup_input"])}
    ratios = {k: round(contrast(a, b), 2) for k, (a, b) in pairs.items()}
    for k, v in ratios.items():
        if v < 4.5:
            problems.append(f"contrast: {k} is {v}:1, under 4.5:1")
    report = {"files": [HEADER_FILE, FOOTER_FILE], "colours": col, "contrast": ratios, "changes": changes, "provenance": prov,
              "removed_placeholders": removed, "samples": sorted(k for k, v in prov.items() if v["kind"] == "sample"), "problems": problems,
              "category": brand.get("category", ""), "direction": d.as_report()}
    return ChromeResult(header, footer, report)

"""Lint rules: the design judgment as checks. A page that breaks an `error` rule must not be pushed; `warn` rules go into the report for a human.
Each rule says WHY it exists, because a rule nobody understands gets argued with or deleted."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

MAX_PAD = 56
MAX_JOIN = 80  # bottom padding of one section + top padding of the next
MIN_SIDE = 12
MAX_DARK = 2
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_STEP = re.compile(r"^Step \d+: ")


@dataclass
class Finding:
    rule: str
    severity: str  # error | warn
    message: str


RULES = {
    "L01": ("error", "Every text/background pair must pass WCAG AA (4.5:1). Unreadable text is the fastest way to lose a sale and a client."),
    "L02": ("error", "Every full-width section keeps at least 12 px of side space, so nothing touches a phone's screen edge."),
    "L03": ("error", "Section padding stays within 56 px and two neighbours together within 80 px, so there are no big empty holes between sections."),
    "L04": ("error", "Neighbouring sections never share the same background colour: bands alternate so each section reads as its own block."),
    "L05": ("error", "At most 2 dark bands: dark is for emphasis, and emphasis only works when it is rare."),
    "L06": ("error", "Reviews sit directly under the buy buttons, where the last doubt appears."),
    "L07": ("error", "Every text on the page has a recorded origin (a named fact, a structural template, or a labelled demo). Nothing is invented."),
    "L08": ("error", "Every number in generated or structural text exists in the facts (the price is live from Shopify, not typed)."),
    "L09": ("error", "Demo content is allowed only when the facts say demo: true (a dev store); each demo item is listed for replacement."),
    "L10": ("error", "At most the direction's number of accent-word headlines per page: accenting one word in every heading reads as a template."),
    "L11": ("warn", "Three or more neighbouring sections without a band change makes the page read as one long block."),
    "L12": ("error", "The buy box has the live price block, and the theme's own price line is removed so the price is not shown twice."),
}


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUM.findall(text or "")}


def _fact_numbers(facts: dict) -> set[str]:
    out: set[str] = set()

    def walk(x):
        if isinstance(x, str):
            out.update(_numbers(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk({k: v for k, v in facts.items() if k not in ("media",)})
    return out


def lint(model) -> list[Finding]:
    d, cat, facts = model.direction, model.catalog, model.facts
    out: list[Finding] = []

    def add(rule, msg):
        out.append(Finding(rule, RULES[rule][0], msg))

    # L01 contrast
    for c in d.failed_checks():
        add("L01", f"{c['pair']}: {c['fg']} on {c['bg']} is {c['ratio']}:1, needs {c['needs']}:1")
    for sec in model.sections:
        if sec.block == "slideshow-pro" and any(k.startswith(("heading_", "description_")) for k in sec.settings):
            if sec.settings.get("overlay_style", "side") == "none" or sec.settings.get("overlay_opacity", 60) < 40:
                add("L01", f"{sec.id}: text over a picture needs an overlay of at least 40 %")

    # L02 side space, L03 rhythm
    pads = []
    for sec in model.sections:
        if cat.has(sec.app, sec.block, "side_padding"):
            side = sec.settings.get("side_padding", cat.default(sec.app, sec.block, "side_padding"))
            if side is None or side < MIN_SIDE:
                add("L02", f"{sec.id}: side space {side} px is below {MIN_SIDE} px")
        top = sec.settings.get("padding_top", cat.default(sec.app, sec.block, "padding_top") or 0)
        bottom = sec.settings.get("padding_bottom", cat.default(sec.app, sec.block, "padding_bottom") or 0)
        pads.append((sec, top, bottom))
        if top > MAX_PAD or bottom > MAX_PAD:
            add("L03", f"{sec.id}: padding {top}/{bottom} px is above {MAX_PAD} px")
    for (a, _, a_bottom), (b, b_top, _) in zip(pads, pads[1:]):
        if a_bottom + b_top > MAX_JOIN:
            add("L03", f"{a.id} then {b.id}: {a_bottom + b_top} px between them is above {MAX_JOIN} px")

    # L04 bands, L05 dark, L11 monotony
    bgs = [sec.settings.get("background") for sec in model.sections if model.roles.get(sec.id) != "none"]
    for a, b in zip(bgs, bgs[1:]):
        if a and a == b:
            add("L04", f"two neighbouring sections share the background {a}")
    if sum(1 for sec in model.sections if model.roles.get(sec.id) == "dark") > MAX_DARK:
        add("L05", f"more than {MAX_DARK} dark bands")
    run = 0
    for bg in bgs:
        run = run + 1 if not bg else 0
        if run == 3:
            add("L11", "three neighbouring sections have no band background")
            break

    # L06 / L12 buy box
    details = model.template["sections"]["main"]["blocks"]["product-details"]
    order = details["block_order"]
    btn = "buy_buttons_eYQEYi"
    for key in order:
        blk = details["blocks"][key]
        if "/dtj-testimonials/" in blk["type"]:
            if order.index(key) != order.index(btn) + 1:
                add("L06", "the DTJ reviews block is not directly under the buy buttons")
    if not any("/dtj-price/" in details["blocks"][k]["type"] for k in order):
        add("L12", "the DTJ price block is missing from the buy box")
    group = details["blocks"].get("group_icgrde", {})
    if any(b.get("type") == "price" for b in group.get("blocks", {}).values()):
        add("L12", "the theme's own price line is still in the title group next to the DTJ price")

    # L07 provenance, L08 numbers, L09 demo
    allowed = _fact_numbers(facts)
    allowed |= _numbers(model.brand.get("brand_name", ""))
    demo_items = []
    for sec in model.sections + model.buybox_sections:
        for key in cat.text_settings(sec.app, sec.block):
            if key not in sec.settings:
                continue
            rec = model.prov.get((sec.id, key))
            if rec is None:
                add("L07", f"{sec.id}.{key} has no recorded origin")
                continue
            if rec["kind"] == "demo":
                demo_items.append(f"{sec.id}.{key}")
                if not model.demo:
                    add("L09", f"{sec.id}.{key} is demo content but the facts do not say demo: true")
                continue
            text = re.sub(r"<[^>]+>", " ", _STEP.sub("", rec["text"]))
            extra = _numbers(text) - allowed
            if extra:
                add("L08", f"{sec.id}.{key} contains {sorted(extra)} which is not in the facts")
    model.demo_items = demo_items

    # L10 accents
    accents = 0
    for sec in model.sections:
        accents += len(re.findall(r"\*[^*]+\*", " ".join(str(v) for k, v in sec.settings.items() if k.startswith("heading"))))
        accents += 1 if sec.settings.get("heading_accent") else 0
        accents += 1 if sec.settings.get("highlight_word") else 0
    if accents > d.type["accent_words_max"]:
        add("L10", f"{accents} accent-word headlines, the direction allows {d.type['accent_words_max']}")
    return out

"""Lint rules: the design judgment as checks. A page that breaks an `error` rule must not be pushed; `warn` rules go into the report for a human.
Each rule says WHY it exists, because a rule nobody understands gets argued with or deleted."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass

MAX_PAD = 56
MAX_JOIN = 80  # bottom padding of one section + top padding of the next
MIN_SIDE = 12
MAX_DARK = 2
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_STEP = re.compile(r"^Step \d+: ")
STORY_WORDS = 20  # a story card's paragraph
STORY_POINT = 32  # characters per story point
BUTTON_KEYS = ("button_label", "button_label_1", "cta_text")
# a dose or a measure in a buy-box point means it describes the product (a feature), not what the shopper gets (a benefit)
# DTJ-written copy (L19): never a health or body claim; a claim word only when the brand's OWN facts already use it
HEALTH_WORDS = ("lose weight", "weight loss", "burn fat", "fat burn", "detox", "cure", "heals", "immunity", "disease", "clinically",
                "doctor", "dermatologist", "prescription")
CLAIM_WORDS = ("best", "#1", "number one", "the only", "india's only", "100%", "guarantee", "proven", "award", "certified", "approved",
               "official", "natural", "no preservative", "preservative-free", "vegan", "sugar-free", "instantly", "miracle", "chef")
RISKY_JOKES = ("addict", "overdose", "side effect")  # fine on a sauce, a real worry on a supplement or a skincare product
_SPEC = re.compile(r"\d\s*(mg|mcg|µg|g|kg|ml|l|iu|kcal|cal|%)(?![a-z])", re.I)


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
    "L05": ("error", "At most 2 dark bands on every page: dark is for emphasis, and emphasis only works when it is rare. Electric / playful pages put the ink colour into cards and boxes instead (Harsh, 10 Oct 2026)."),
    "L06": ("error", "Reviews sit directly under the buy buttons, where the last doubt appears."),
    "L07": ("error", "Every text on the page has a recorded origin (a named fact, a structural template, or a labelled demo). Nothing is invented."),
    "L08": ("error", "Every number in generated or structural text exists in the facts (the price is live from Shopify, not typed)."),
    "L09": ("error", "Demo content is allowed only when the facts say demo: true (a dev store); each demo item is listed for replacement."),
    "L10": ("error", "At most the direction's number of accent-word headlines per page: accenting one word in every heading reads as a template."),
    "L11": ("warn", "Three or more neighbouring sections without a band change makes the page read as one long block."),
    "L12": ("error", "The buy box has the live price block, and the theme's own price line is removed so the price is not shown twice."),
    "L15": ("error", "A badge is 2 or 3 short words, at most 20 characters (a milestone or a promise at a glance); a longer one gets cut on phones (Harsh, 9 Oct 2026)."),
    "L14": ("error", "The rating line shows exactly 5 round photos or none: a short row looks unfinished (Harsh, 9 Oct 2026)."),
    "L13": ("error", "Every tick-mark list (the buy box points, the story points) has exactly 4 points: fewer looks thin, more is not read (Harsh, 9 Oct 2026)."),
    "L16": ("error", "Every button on the page has its own label, named after what its section says; twelve identical labels read as one repeated ad (Harsh, 10 Oct 2026)."),
    "L17": ("error", "A story card is short and to the point: a paragraph of at most 20 words and points of at most 32 characters, or it reads as a wall of text on a phone (Harsh, 10 Oct 2026)."),
    "L19": ("error", "Copy DTJ writes (source 'DTJ COPY ...') makes the shopper feel the product but adds no claim: no health or body words, no claim word the brand's own facts do not use, no dependency jokes on supplements or skincare (references/copywriting.md; Harsh, 10 Oct 2026)."),
    "L18": ("error", "The buy box points are benefits (what the shopper gets: energy in minutes, easy to carry), not specs: doses and measures belong in the ingredients and numbers sections (Harsh, 10 Oct 2026)."),
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


def _brand_text(facts: dict) -> str:
    """The brand's own words: every fact except our copy lines and samples (neither may license a claim)."""
    out: list[str] = []

    def walk(x):
        if isinstance(x, dict):
            if str(x.get("source", "")).upper().startswith(("DTJ COPY", "SAMPLE")):
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            out.append(x.lower())
    walk({k: v for k, v in facts.items() if k not in ("media",)})
    return " | ".join(out)


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
    max_dark = getattr(d, "max_dark", MAX_DARK)
    if sum(1 for sec in model.sections if model.roles.get(sec.id) == "dark") > max_dark:
        add("L05", f"more than {max_dark} dark bands")
    run = 0
    for bg in bgs:
        run = run + 1 if not bg else 0
        if run == 3:
            add("L11", "three neighbouring sections have no band background")
            break

    # L06 / L12 buy box
    from .assemble import BUY_BUTTON_TYPES, product_column  # the buy box's column, whatever the theme (Horizon or Dawn)
    details = product_column(model.template)
    order = details["block_order"]
    btn = next((k for k in order if details["blocks"][k]["type"] in BUY_BUTTON_TYPES), None)
    for key in order:
        blk = details["blocks"][key]
        if "/dtj-testimonials/" in blk["type"]:
            if btn is None or order.index(key) != order.index(btn) + 1:
                add("L06", "the DTJ reviews block is not directly under the buy buttons")
    if not any("/dtj-price/" in details["blocks"][k]["type"] for k in order):
        add("L12", "the DTJ price block is missing from the buy box")
    theme_prices = [k for k in order if details["blocks"][k].get("type") == "price"]
    for k in order:
        theme_prices += [s for s, b in (details["blocks"][k].get("blocks") or {}).items() if b.get("type") == "price"]
    if theme_prices:
        add("L12", f"the theme's own price line is still in the buy box next to the DTJ price ({', '.join(theme_prices)})")

    # L13 exactly four ticks wherever a tick list is shown
    for sec in model.sections + model.buybox_sections:
        if sec.kind == "hero_points" and sec.settings.get("benefits"):
            n = len([x for x in str(sec.settings["benefits"]).splitlines() if x.strip()])
        elif sec.kind in ("story_split", "story_split_2"):
            n = len([k for k in sec.settings if re.fullmatch(r"bullet_\d+", k) and sec.settings[k]])
        else:
            continue
        if n and n != 4:
            add("L13", f"{sec.id} shows {n} tick points; it needs exactly 4 (add real points to the facts, never invented ones)")
    # L16 one label per button, L17 short story cards, L18 benefits in the buy box
    labels: dict[str, list[str]] = {}
    for sec in model.sections + list(getattr(model, "extras", {}).values()):
        for key in BUTTON_KEYS:
            if sec.settings.get(key):
                labels.setdefault(str(sec.settings[key]).strip().lower(), []).append(f"{sec.id}.{key}")
    for label, where in labels.items():
        if len(where) > 1:
            add("L16", f"{len(where)} buttons say '{label}' ({', '.join(where)}); name each after its section")
    for sec in model.sections:
        if sec.kind not in ("story_split", "story_split_2"):
            continue
        words = len(str(sec.settings.get("body") or "").split())
        if words > STORY_WORDS:
            add("L17", f"{sec.id} paragraph has {words} words; keep it to {STORY_WORDS} or fewer")
        for k in sorted(k for k in sec.settings if re.fullmatch(r"bullet_\d+", k)):
            if len(str(sec.settings[k])) > STORY_POINT:
                add("L17", f"{sec.id}.{k} '{sec.settings[k]}' is {len(str(sec.settings[k]))} characters; keep points to {STORY_POINT}")
    for sec in model.buybox_sections:
        if sec.kind == "hero_points":
            for line in str(sec.settings.get("benefits") or "").splitlines():
                if _SPEC.search(line):
                    add("L18", f"buy box point '{line.strip()}' is a spec (a dose or measure); write what the shopper gets instead")
    for sec in model.buybox_sections:
        if sec.block == "social-proof":
            photos = len([k for k in sec.settings if re.fullmatch(r"avatar_\d+", k) and sec.settings[k]])
            if photos and photos != 5:
                add("L14", f"{sec.id} shows {photos} round photos; it needs exactly 5 (or none)")
            badge = str(sec.settings.get("badge_text") or "").split()
            if badge and (not 2 <= len(badge) <= 3 or len(" ".join(badge)) > 20):
                add("L15", f"{sec.id} badge '{' '.join(badge)}' is {len(badge)} words / {len(' '.join(badge))} characters; use 2-3 words, at most 20")

    # L19 our own copy adds no claim
    brand_text = _brand_text(facts)
    for (sid, key), rec in model.prov.items():
        if rec["kind"] != "dtj_copy":
            continue
        low = html.unescape(str(rec["text"])).lower()
        bad = [w for w in HEALTH_WORDS if w in low] + [w for w in CLAIM_WORDS if w in low and w not in brand_text]
        if model.brand.get("category") in ("supplements", "beauty"):
            bad += [w for w in RISKY_JOKES if w in low]
        if bad:
            add("L19", f"{sid}.{key} (DTJ copy) uses {sorted(set(bad))}: say it with a sourced fact, or cut it")

    # L07 provenance, L08 numbers, L09 demo
    allowed = _fact_numbers(facts)
    allowed |= _numbers(model.brand.get("brand_name", ""))
    demo_items = []
    for sec in model.sections + model.buybox_sections + list(getattr(model, "extras", {}).values()):
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
            # rich text stores characters as entities ("Malar's" -> "Malar&#x27;s"): read the words, not the entity's digits
            text = html.unescape(re.sub(r"<[^>]+>", " ", _STEP.sub("", rec["text"])))
            extra = _numbers(text) - allowed
            if extra:
                add("L08", f"{sec.id}.{key} contains {sorted(extra)} which is not in the facts")
    model.demo_items = demo_items
    if getattr(model, "demo_pictures", None) and not model.demo:
        add("L09", f"{len(model.demo_pictures)} test pictures on the page but the facts do not say demo: true")

    # L10 accents
    accents = 0
    for sec in model.sections:
        accents += len(re.findall(r"\*[^*]+\*", " ".join(str(v) for k, v in sec.settings.items() if k.startswith("heading"))))
        accents += 1 if sec.settings.get("heading_accent") else 0
        accents += 1 if sec.settings.get("highlight_word") else 0
    if accents > d.type["accent_words_max"]:
        add("L10", f"{accents} accent-word headlines, the direction allows {d.type['accent_words_max']}")
    return out

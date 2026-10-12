"""The contract for the ONE thing a Claude API step may do: rewrite the page's STRUCTURAL copy (signpost headings such as "Why choose X?",
"How it works", "Questions, answered", and the label of the button after each section) in the brand's voice.

It may NOT touch fact text (benefits, steps, FAQ answers, reviews, figures): those come from the facts, verbatim, with their source.
Everything the model returns is validated here by code before it reaches the page, and a rejected line simply keeps the template wording.

Flow (the API call itself lives in the service that runs this, with the key from the vault, never in this module):
    first = build_pdp(brand, facts)
    request = build_request(first)                       # JSON for the model: voice, rules, the slots and their current text
    response = <Claude API, structured output against RESPONSE_SCHEMA>
    accepted, rejected = validate_response(first, response)
    final = build_pdp(brand, facts, copy_overrides=accepted)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .rules import _fact_numbers, _numbers

HERE = Path(__file__).resolve().parent
MAX_LEN = 48
MAX_BUTTON = 24  # a button label fits one line of a phone-width pill
BUTTON_KEYS = ("button_label", "button_label_1", "cta_text")
# a button here always buys (it adds to the cart or goes to the buy box): a reading label would mislead the shopper
NOT_BUYING = ("learn more", "read more", "see more", "find out", "discover", "explore", "view more", "know more")
# words that make a claim, an offer or urgency: never allowed in structural copy unless the facts already use the word
RISKY = ("best", "#1", "number one", "guarantee", "clinically", "proven", "doctor", "cure", "heal", "100%", "free shipping", "sale", "discount",
         "limited", "only today", "hurry", "miracle", "instantly", "award", "official", "certified", "approved", "lowest price")

RESPONSE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["slots"],
    "properties": {"slots": {"type": "object", "additionalProperties": {"type": "string", "maxLength": MAX_LEN}}},
}


def is_button(slot: str) -> bool:
    return slot.rsplit(".", 1)[-1] in BUTTON_KEYS


def _section_heading(prov: dict, sid: str) -> str | None:
    """The heading of the section a button belongs to (the button block `<section>_cta`, or a button inside the section itself)."""
    parent = sid[:-4] if sid.endswith("_cta") else sid
    for key in ("heading", "heading_1"):
        rec = prov.get((parent, key))
        if rec:
            accent = prov.get((parent, f"{key}_accent"))
            return " ".join(x for x in (rec["text"], accent["text"] if accent else None) if x)
    return None


def list_slots(result) -> list[dict]:
    """The structural strings of a built page: the only text a model may rewrite. A button label carries its section's heading, so it
    can be named after what that section says (Harsh, 10 Oct 2026)."""
    out = []
    prov = result.model.prov
    for (sid, key), rec in sorted(prov.items()):
        if rec["kind"] in ("structure", "copy"):
            slot = f"{sid}.{key}"
            if is_button(slot):
                out.append({"slot": slot, "current": rec["text"], "max_length": MAX_BUTTON, "button": True,
                            "section_heading": _section_heading(prov, sid)})
            else:
                out.append({"slot": slot, "current": rec["text"], "max_length": MAX_LEN})
    return out


def build_request(result) -> dict:
    d = result.model.direction
    return {
        "task": "Rewrite each slot's text in the brand's voice. Keep its job (a signpost or a button), keep it short, keep any {brand} name exactly as given.",
        "brand": {"name": result.model.brand["brand_name"], "category": result.model.brand["category"],
                  "voice": result.model.brand.get("voice") or "plain", "price_tier": result.model.brand.get("price_tier", "mid")},
        "design_notes": {"type_treatment": d.type["accent_font"], "shape": d.shape["name"]},
        "rules": [
            "Signposts only: say what the section is, never promise or claim anything.",
            "No numbers, no percentages, no prices, no offers, no urgency, no superlatives, no medical or performance claims.",
            "Plain words, sentence case, active voice, under 48 characters, no emoji, no HTML, no asterisks.",
            "Do not repeat the same phrasing in two slots.",
            "If you cannot improve a slot, return its current text unchanged.",
            "Button slots (button: true): every button buys (adds the product to the cart or goes to the buy box). Name it after its section "
            "(section_heading) as a buying action: 2 to 5 words, at most 24 characters, starting with a verb (Get, Try, Grab, Start, Join, Make...). "
            "Never a reading label (Learn more, Read more, Discover). Every button label on the page is different.",
        ],
        "slots": list_slots(result),
        "response_schema": RESPONSE_SCHEMA,
    }


def validate_response(result, response: dict) -> tuple[dict, dict]:
    """Returns (accepted, rejected): accepted = {slot: text} safe to apply, rejected = {slot: reason}."""
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(RESPONSE_SCHEMA).iter_errors(response))
    if errors:
        return {}, {"(response)": "; ".join(e.message for e in errors[:3])}
    known = {s["slot"]: s for s in list_slots(result)}
    allowed_numbers = _fact_numbers(result.model.facts)
    fact_text = json.dumps(result.model.facts, ensure_ascii=False).lower()
    accepted, rejected = {}, {}
    seen: set[str] = set()
    brand = result.model.brand["brand_name"].lower()
    for slot, text in response["slots"].items():
        if slot not in known:
            rejected[slot] = "not a structural slot (fact text can never be rewritten)"
            continue
        text = text.strip()
        low = text.lower()
        button = is_button(slot)
        if not text:
            rejected[slot] = "empty"
        elif button and len(text) > MAX_BUTTON:
            rejected[slot] = f"a button label has at most {MAX_BUTTON} characters"
        elif button and not 2 <= len(text.split()) <= 5:
            rejected[slot] = "a button label has 2 to 5 words"
        elif button and any(w in low for w in NOT_BUYING):
            rejected[slot] = "a button here buys: a reading label (learn more, discover...) would mislead"
        elif re.search(r"[<>*{}]|https?://", text):
            rejected[slot] = "contains markup, braces, asterisks or a link"
        elif _numbers(text) - allowed_numbers:
            rejected[slot] = f"contains numbers {sorted(_numbers(text) - allowed_numbers)} that are not in the facts"
        elif any(w in low and w not in fact_text for w in RISKY):
            rejected[slot] = "contains a claim, offer or urgency word"
        elif low in seen:
            rejected[slot] = "duplicates another slot"
        elif brand in known[slot]["current"].lower() and brand not in low:
            rejected[slot] = "dropped the brand name that this slot must keep"
        else:
            accepted[slot] = text
            seen.add(low)
    return accepted, rejected

"""Synthetic TEST fixtures for three very different brands (not real clients, not real claims; every source says 'demo fixture').
They exist to prove the page adapts: palette, shape, type treatment, density, motion and the emphasised section all differ per brand."""
from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def toilova() -> tuple[dict, dict]:
    data = json.loads((HERE / "toilova.json").read_text(encoding="utf-8"))
    return copy.deepcopy(data["brand"]), copy.deepcopy(data["facts"])


def _facts(title: str, with_reviews: bool = True) -> dict:
    src = "demo fixture"
    media = [{"role": r, "file": f"{r}.webp"} for r in ("pack", "hand", "steps", "shelf", "acid", "fumes")]
    facts = {
        "demo": True, "product": {"title": title, "handle": "demo-product"}, "media": media,
        "trust_points": [{"text": t, "source": src} for t in ("First point", "Second point", "Third point", "Fourth point")],
        "benefits": [{"title": f"Benefit {i}", "text": f"Benefit {i} text", "source": src} for i in range(1, 5)],
        "story": {"heading": "Story heading", "accent": "accent words", "body": "Story body", "bullets": ["Tick one", "Tick two", "Tick three", "Tick four"], "image_role": "hand", "source": src},
        "steps": {"intro": "Steps intro", "items": ["First step", "Second step", "Third step"], "image_role": "steps", "source": src},
        "key_facts": [{"value": "10 g", "label": "Fact one", "note": "Note one", "image_role": "pack", "source": src},
                      {"value": "2x", "label": "Fact two", "note": "Note two", "image_role": "shelf", "source": src},
                      {"value": "30 ml", "label": "Fact three", "note": "Note three", "image_role": "hand", "source": src}],
        "pack_contents": [{"name": "Item one", "detail": "Detail", "image_role": "pack", "source": src}, {"name": "Item two", "image_role": "shelf", "source": src}],
        "free_from": [{"name": "Not one", "source": src}, {"name": "Not two", "source": src}],
        "faqs": [{"q": f"Question {i}?", "a": f"Answer {i}.", "source": src} for i in range(1, 4)],
    }
    if with_reviews:
        facts["reviews"] = [{"quote": f"Demo review {i}", "name": f"Demo customer {i}", "rating": 5, "source": "demo fixture"} for i in range(1, 4)]
        facts["rating"] = {"value": "4.8", "source": "demo fixture"}
    return facts


BRANDS = {
    "aurelia": ({"brand_name": "Aurelia", "category": "beauty", "price_tier": "premium", "voice": "luxe",
                 "colors": {"primary": "#7A2E4A", "background": "#FFFAF7", "text": "#2A1620"}}, _facts("Aurelia Glow Serum")),
    "voltra": ({"brand_name": "Voltra", "category": "supplements", "price_tier": "mid", "voice": "clinical",
                "colors": {"primary": "#1C6EA4", "background": "#FFFFFF", "text": "#10202D"}}, _facts("Voltra Daily Powder")),
    "nocturne": ({"brand_name": "Nocturne", "category": "apparel", "price_tier": "premium", "voice": "luxe", "shape_language": "sharp",
                  "colors": {"primary": "#C9A24A", "background": "#0F0F12", "text": "#F2F2F2"}}, _facts("Nocturne Wool Coat")),
    "zestly": ({"brand_name": "Zestly", "category": "food", "price_tier": "value", "voice": "playful",
                "colors": {"primary": "#E4572E", "background": "#FFF9F0", "text": "#2B2118"}}, _facts("Zestly Chilli Crunch", with_reviews=False)),
}

"""Home page section builders (Harsh, 13 Oct 2026): the DTJ Heroes blocks, chosen niche-first. Same contract as sections.py: a builder returns a
Section or Omit(reason) when its facts are missing, and every text goes through ctx.put so its origin is recorded (lint L07). Nothing here
writes marketing copy: words come from the home facts (verbatim, with their source) or from a short structural signpost."""
from __future__ import annotations

import json
from pathlib import Path

from . import niches
from .catalog import VIDEO_PREFIX
from .sections import STRUCTURE, Ctx, Omit, Section, _slots, faq, trust_marquee

HERE = Path(__file__).resolve().parent
STRUCTURE.update({
    "home_why": "Why {brand}",
    "home_video": "{brand} in real life",
    "video_link": "See the product",
})
DEFAULT_ICONS = ["sparkle", "shield", "leaf", "heart", "bolt", "award"]  # exist in the icon lists of both feature blocks
VALUE_BLOCKS = ["dtj-heroes/feature-cards", "dtj-heroes/feature-tiles"]  # tried in niche order (niches.order_blocks); the first one the facts can fill wins


def hero_layouts() -> dict:
    return json.loads((HERE / "recipes" / "home.json").read_text(encoding="utf-8"))["hero_layout"]


def hero_home(ctx: Ctx):
    h = ctx.facts.get("hero")
    if not h:
        return Omit("hero_home", "needs the hero facts (a headline, a button label, a picture and their source)")
    image = ctx.media(h["image_role"])
    if not image:
        return Omit("hero_home", f"the media list has no picture with the role {h['image_role']!r}")
    layout = hero_layouts().get(niches.niche_of(ctx.brand["category"]), "banner")
    s = Section("home_hero", "dtj-heroes", "hero-banner", role="none", kind="hero_home")
    s.settings.update({"layout": layout, "image": image, "priority": True})
    mobile = ctx.media(h.get("image_mobile_role"))
    if mobile:
        s.settings["image_mobile"] = mobile
    headline = h["headline"]
    if "*" in headline and not ctx.take_accent():  # the page's accent-word budget is spent: the words stay plain
        headline = headline.replace("*", "")
    ctx.put(s, "heading", headline, "fact", h["source"])
    ctx.put(s, "subheading", h.get("sub"), "fact", h["source"])
    ctx.put(s, "badge_text", h.get("badge"), "fact", h["source"])
    if h.get("points"):
        ctx.put(s, "points", "\n".join(h["points"][:4]), "fact", h["source"])
    ctx.put(s, "button_label", h["cta_label"], "fact", h["source"])
    s.settings["button_url"] = h.get("cta_url") or "/collections/all"
    rating = ctx.facts.get("rating")
    if rating:  # only a real, sourced rating is ever shown
        s.settings["rating_value"] = float(rating["value"])
        ctx.put(s, "rating_text", rating.get("text"), "fact", rating["source"])
    return s


def _icon(ctx: Ctx, block: str, wanted: str | None, k: int) -> str:
    key = "f1_icon" if block == "feature-cards" else "t1_icon"
    valid = {o["value"] for o in ctx.catalog.settings("dtj-heroes", block)[key]["options"]} - {"none"}
    return wanted if wanted in valid else DEFAULT_ICONS[k % len(DEFAULT_ICONS)]


def _cards(ctx: Ctx, vp: dict):
    image = ctx.media(vp.get("image_role"))
    if not image:
        return Omit("value_props_home", "the soft-card layout needs a centre picture (value_props.image_role)")
    s = Section("home_values", "dtj-heroes", "feature-cards", role="plain", kind="value_props_home")
    s.settings["image"] = image
    if vp.get("badge") and ctx.eyebrow_allowed():
        ctx.put(s, "badge_text", vp["badge"], "fact", vp["source"])
    if vp.get("heading"):
        ctx.put(s, "heading", vp["heading"], "fact", vp["source"])
    else:
        ctx.put(s, "heading", ctx.structure("home_why"))
    ctx.put(s, "subheading", vp.get("intro"), "fact", vp["source"])
    slot_for = ["f1", "f4", "f2", "f5", "f3", "f6"]  # alternate left / right so the two sides stay balanced
    for k, item in enumerate(vp["items"][:6]):
        f = slot_for[k]
        ctx.put(s, f"{f}_title", item["title"], "fact", item["source"])
        ctx.put(s, f"{f}_text", item.get("text"), "fact", item["source"])
        s.settings[f"{f}_icon"] = _icon(ctx, "feature-cards", item.get("icon"), k)
    return s


def _tiles(ctx: Ctx, vp: dict):
    items = vp["items"]
    n = 6 if len(items) >= 6 else (4 if len(items) in (4, 5) else 3)  # full rows only: 3 or 6 in three columns, 4 in two
    s = Section("home_values", "dtj-heroes", "feature-tiles", role="plain", kind="value_props_home")
    s.settings["tile_columns"] = "2" if n == 4 else "3"
    image = ctx.media(vp.get("image_role"))
    if image:
        s.settings["image"] = image
    if vp.get("heading"):
        ctx.put(s, "heading", vp["heading"], "fact", vp["source"])
    else:
        ctx.put(s, "heading", ctx.structure("home_why"))
    ctx.put(s, "text", vp.get("intro"), "fact", vp["source"])
    for k, item in enumerate(items[:n]):
        ctx.put(s, f"t{k + 1}_label", item["title"], "fact", item["source"])
        s.settings[f"t{k + 1}_icon"] = _icon(ctx, "feature-tiles", item.get("icon"), k)
    return s


def value_props_home(ctx: Ctx):
    vp = ctx.facts.get("value_props")
    if not vp:
        return Omit("value_props_home", "needs 3 to 6 reasons to choose the brand, each with its source")
    reasons = []
    for app_block in niches.order_blocks(VALUE_BLOCKS, ctx.brand["category"]):  # niche first, then the other layout
        res = _cards(ctx, vp) if app_block.endswith("feature-cards") else _tiles(ctx, vp)
        if not isinstance(res, Omit):
            return res
        reasons.append(res.reason)
        ctx.prov = {k: v for k, v in ctx.prov.items() if k[0] != "home_values"}  # forget the half-built attempt's texts
    return Omit("value_props_home", "; ".join(reasons))


def story_home(ctx: Ctx):
    st = ctx.facts.get("story")
    if not st:
        return Omit("story_home", "needs the brand story (a heading, a short paragraph and their source)")
    image = ctx.media(st.get("image_role"))
    if not image:
        return Omit("story_home", "the story needs a picture (story.image_role)")
    s = Section("home_story", "dtj-heroes", "hero-banner", role="plain", kind="story_home")
    s.settings.update({"layout": "split", "image": image, "priority": False})
    ctx.put(s, "heading", st["heading"], "fact", st["source"])
    ctx.put(s, "subheading", st["body"], "fact", st["source"])
    if st.get("bullets"):
        ctx.put(s, "points", "\n".join(st["bullets"][:4]), "fact", st["source"])
    review = st.get("review")
    if review:  # only a real, sourced review ever appears
        ctx.put(s, "review_quote", review["quote"], "fact", review["source"])
        ctx.put(s, "review_name", review["name"], "fact", review["source"])
        if review.get("rating"):
            s.settings["review_stars"] = float(review["rating"])
    if st.get("cta_label"):
        ctx.put(s, "button_label", st["cta_label"], "fact", st["source"])
        s.settings["button_url"] = st.get("cta_url") or "/collections/all"
    return s


def video_reviews_home(ctx: Ctx):
    vr = ctx.facts.get("video_reviews")
    if not vr:
        return Omit("video_reviews_home", "needs 3 to 6 real customer cards (with permission), each with a picture and its source")
    cards = [it for it in vr["items"] if ctx.media(it["image_role"])]
    if len(cards) < 3:
        return Omit("video_reviews_home", "needs at least 3 cards whose picture role exists in the media list")
    s = Section("home_video", "dtj-heroes", "video-reviews", role="band", kind="video_reviews_home")
    if vr.get("heading"):
        ctx.put(s, "heading", vr["heading"], "fact", vr["source"])
    else:
        ctx.put(s, "heading", ctx.structure("home_video"))
    ctx.put(s, "subheading", vr.get("intro"), "fact", vr["source"])
    if any(c.get("url") for c in cards):
        ctx.put(s, "link_label", ctx.structure("video_link"))
    for i, it in _slots(6, cards):
        s.settings[f"image_{i}"] = ctx.media(it["image_role"])
        ctx.put(s, f"name_{i}", it["name"], "fact", it["source"])
        ctx.put(s, f"text_{i}", it.get("line"), "fact", it["source"])
        if it.get("url"):
            s.settings[f"url_{i}"] = it["url"]
        if it.get("video"):
            s.settings[f"video_{i}"] = f"{VIDEO_PREFIX}{it['video']}"
    return s


HOME_BUILDERS = {f.__name__: f for f in (hero_home, trust_marquee, value_props_home, story_home, video_reviews_home, faq)}

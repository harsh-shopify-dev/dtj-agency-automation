"""Home page section builders (Harsh, 13 Oct 2026): the DTJ Heroes blocks, chosen niche-first. Same contract as sections.py: a builder returns a
Section or Omit(reason) when its facts are missing, and every text goes through ctx.put so its origin is recorded (lint L07). Nothing here
writes marketing copy: words come from the home facts (verbatim, with their source) or from a short structural signpost."""
from __future__ import annotations

import html
import json
import re
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


# the hero on a phone: the words over the picture (the overlay look built 14 Oct 2026), LEFT-aligned. Harsh set these in the theme editor and
# made them the standard on 19 Oct 2026: "check the herobanners mobile settings we will keep the same for future and only copy and colors will
# be changed"
HERO_PHONE = {"mobile_layout": "overlay", "mobile_align": "left"}


def hero_layouts() -> dict:
    return json.loads((HERE / "recipes" / "home.json").read_text(encoding="utf-8"))["hero_layout"]


def hero_home(ctx: Ctx):
    h = ctx.facts.get("hero")
    if not h:
        return Omit("hero_home", "needs the hero facts (a headline, a button label, a picture and their source)")
    image = ctx.media(h["image_role"])
    if not image:
        return Omit("hero_home", f"the media list has no picture with the role {h['image_role']!r}")
    # the niche picks the full-image layout. A multi-product store ALWAYS gets it (Harsh, 14 Oct 2026: "for multi product page stores we will
    # never use this hero section we will use the full image banner"), so its hero picture must be a wide one with room for the words. Only a
    # one-product shop may ask for a split (its product shot beside the words, picture on the right so the story's split looks different).
    layout = hero_layouts().get(niches.niche_of(ctx.brand["category"]), "banner")
    if ctx.facts.get("store_type") == "single_product" and h.get("layout"):
        layout = h["layout"]
    extra = [sl for sl in h.get("slides", []) if ctx.media(sl["image_role"])]  # a banner without its picture is left out
    if extra and layout != "split":
        return _hero_slideshow(ctx, h, image, extra)
    s = Section("home_hero", "dtj-heroes", "hero-banner", role="none", kind="hero_home")
    s.settings.update({"layout": layout, "image": image, "priority": True})
    if layout == "split":
        s.settings["image_side"] = "right"
    else:
        s.settings.update(HERO_PHONE)
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


def _hero_slideshow(ctx: Ctx, h: dict, image: str, extra: list[dict]):
    """2 or 3 full-image banners in DTJ Slideshow Pro. Banner 1 = the hero's own facts (with its badge as the eyebrow, its points as chips
    and a real rating only); banners 2 and 3 = hero.slides. Only banner 1 may use the page's accent word."""
    s = Section("home_hero", "dtj-sections-2", "slideshow-pro", role="none", kind="hero_home")
    s.settings.update({"autoplay": True, "show_progress": True, "arrows_position": "right-bottom", "overlay_style": "side", "overlay_opacity": 70,
                       "overlay_size": 80, "content_position": "left", "content_align": "center",
                       # banner 1's own shape on desktop and phone (design check H07: a fixed 21:9 / 4:5 cut the pictures); the skill asks
                       # for banner photos of one shape, so banners 2 and 3 fit the same frame
                       "ratio_desktop": "adapt", "ratio_mobile": "adapt",
                       # phones (Harsh, 14 Oct 2026, three reference screenshots): a TALL picture with the words resting low on it over a fade,
                       # never the words above a short wide strip. A slide's own phone picture (image_mobile_role) is used when the facts have one.
                       **HERO_PHONE,
                       # desktop (Harsh, 15 Oct 2026: "the hero section looks way too big"): a tall collage made the slide fill the whole screen;
                       # cap it at about two thirds of the screen height (the picture is cropped to fit)
                       "desktop_max_height": 70})
    slides = [{"image": image, "image_mobile": ctx.media(h.get("image_mobile_role")), "headline": h["headline"], "sub": h.get("sub"),
               "eyebrow": h.get("badge"), "cta_label": h["cta_label"], "cta_url": h.get("cta_url"), "source": h["source"], "chips": h.get("points")}]
    slides += [{**sl, "image": ctx.media(sl["image_role"]), "image_mobile": ctx.media(sl.get("image_mobile_role"))} for sl in extra]
    for i, sl in enumerate(slides, 1):
        headline = sl["headline"]
        if "*" in headline and not (i == 1 and ctx.take_accent()):
            headline = headline.replace("*", "")
        s.settings[f"image_{i}"] = sl["image"]
        if sl.get("image_mobile"):
            s.settings[f"image_mobile_{i}"] = sl["image_mobile"]
        ctx.put(s, f"heading_{i}", headline, "fact", sl["source"])
        ctx.put(s, f"description_{i}", sl.get("sub"), "fact", sl["source"])
        ctx.put(s, f"eyebrow_{i}", sl.get("eyebrow"), "fact", sl["source"])
        if sl.get("chips"):
            ctx.put(s, f"chips_{i}", "\n".join(sl["chips"][:4]), "fact", sl["source"])
        ctx.put(s, f"button_label_{i}", sl["cta_label"], "fact", sl["source"])
        s.settings[f"button_url_{i}"] = sl.get("cta_url") or "/collections/all"
    rating = ctx.facts.get("rating")
    if rating and rating.get("text"):  # only a real, sourced rating, and only on banner 1
        ctx.put(s, "rating_1", rating["text"], "fact", rating["source"])
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
        ctx.put(s, "heading", vp["heading"].replace("*", ""), "fact", vp["source"])  # this block has no accent words: the marks would show
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
        ctx.put(s, "heading", vp["heading"].replace("*", ""), "fact", vp["source"])  # this block has no accent words: the marks would show
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
            if vp.get("cta_label"):  # its own button, named after the section (lint L16): no long stretch of page without one
                ctx.put(res, "button_label", vp["cta_label"], "fact", vp["source"])
                res.settings["button_url"] = vp.get("cta_url") or "/collections/all"
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
        return Omit("video_reviews_home", "needs 3 to 6 real customer cards (with permission), each with a picture or a video and its source")
    cards = [it for it in vr["items"] if it.get("video") or ctx.media(it.get("image_role"))]  # a video alone shows its own cover frame
    if len(cards) < 3:
        return Omit("video_reviews_home", "needs at least 3 cards with a video or a picture whose role exists in the media list")
    s = Section("home_video", "dtj-heroes", "video-reviews", role="band", kind="video_reviews_home")
    s.settings["arrows_mobile"] = True  # a swipe row needs a visible hint on a phone (Harsh, 20 Oct 2026: "give arrows in mobile version")
    if vr.get("heading"):
        ctx.put(s, "heading", vr["heading"], "fact", vr["source"])
    else:
        ctx.put(s, "heading", ctx.structure("home_video"))
    ctx.put(s, "subheading", vr.get("intro"), "fact", vr["source"])
    if any(c.get("url") for c in cards):
        ctx.put(s, "link_label", ctx.structure("video_link"))
    for i, it in _slots(6, cards):
        if ctx.media(it.get("image_role")):
            s.settings[f"image_{i}"] = ctx.media(it["image_role"])
        ctx.put(s, f"name_{i}", it["name"], "fact", it["source"])
        ctx.put(s, f"text_{i}", it.get("line"), "fact", it["source"])
        if it.get("url"):
            s.settings[f"url_{i}"] = it["url"]
        if it.get("video"):
            s.settings[f"video_{i}"] = f"{VIDEO_PREFIX}{it['video']}"
    return s


# ------------------------------------------------------------------------------------------------ the DTJ Commerce and DTJ Shop blocks
# (13 Oct 2026). Each one reads only the client's real facts; the collection blocks read the store's own collections (each tile takes its
# collection's name, link and picture unless the facts give their own), so nothing on them is typed by us.
STRUCTURE.update({
    "home_shop": "Shop {brand}",
    "home_add": "Add to cart",
    "home_categories": "Shop by category",
    "home_press": "As seen in",  # only ever shown when every logo has the article's address as proof (press_home)
    "home_concern_h": "Shop by", "home_concern_a": "concern",
})
STRIP_ICONS = [(r"cash on delivery|\bcod\b|secure|safe|\bpay", "shield"),  # payment first: "cash on delivery" is not about shipping
               (r"ship|deliver|dispatch|courier", "truck"), (r"return|refund|exchange|replace", "return"), (r"support|help|whatsapp|call|chat", "support"),
               (r"gift", "gift"), (r"offer|% ?off|\boff\b|sale|discount", "tag"), (r"fast|quick|same.day|hour", "clock"), (r"review|rated|star", "star")]
CATEGORY_BLOCKS = ["dtj-commerce/circle-menu", "dtj-commerce/category-grid", "dtj-commerce/category-slider"]
CATEGORY_TILES = {"circle-menu": (3, 8), "category-grid": (3, 5), "category-slider": (4, 8)}  # (fewest that looks finished, most the block has)
CIRCLE_VERSION = {"beauty": "ring", "fashion": "ring", "wellness": "circle", "food": "circle"}  # story rings for looks, plain circles for food and
# wellness, framed squares for the rest
SLIDER_SHAPE = {"fashion": "slant", "food": "round"}  # the rest: leaf


def _strip_icon(ctx: Ctx, s: Section, key: str, wanted: str | None, text: str) -> str:
    """The icon the facts name, else one that matches the words (a truck for shipping), else a plain tick: never a misleading picture."""
    valid = {o["value"] for o in ctx.catalog.settings(s.app, s.block)[key]["options"]}
    if wanted in valid:
        return wanted
    low = text.lower()
    return next((icon for pattern, icon in STRIP_ICONS if re.search(pattern, low)), "check")


def _strip(ctx: Ctx, s: Section, items: list[dict]) -> Section:
    for i, it in _slots(6, items):
        ctx.put(s, f"text_{i}", it["text"], "fact", it["source"])
        s.settings[f"icon_{i}"] = _strip_icon(ctx, s, f"icon_{i}", it.get("icon"), it["text"])
        if it.get("link"):
            s.settings[f"link_{i}"] = it["link"]
    return s


def announcement_bar(ctx: Ctx):
    a = ctx.facts.get("announcements")
    if not a:
        return Omit("announcement_bar", "needs 2 to 6 short store facts for the top strip (shipping, returns, payment, support), each with its source")
    s = Section("home_announce", "dtj-commerce", "marquee-band", role="none", kind="announcement_bar")
    s.settings["variation"] = "bold"
    return _strip(ctx, s, a["items"])


def trust_band_home(ctx: Ctx):
    pts = ctx.facts.get("trust_points", [])
    if len(pts) < 3:
        return Omit("trust_band_home", "needs at least 3 trust points (a short strip of one or two reads empty)")
    s = Section("home_trust", "dtj-commerce", "marquee-band", role="none", kind="trust_band_home")
    s.settings["variation"] = "line"  # the calm strip with a line above and below, right under the hero
    return _strip(ctx, s, pts)


def press_home(ctx: Ctx):
    pr = ctx.facts.get("press")
    if not pr:
        return Omit("press_home", "needs at least 3 REAL press mentions, each with its logo and the article's address (never invented)")
    items = [it for it in pr["items"] if ctx.media(it["logo_role"])]
    if len(items) < 3:
        return Omit("press_home", "needs at least 3 mentions whose logo picture exists in the media list")
    s = Section("home_press", "dtj-commerce", "press-strip", role="plain", kind="press_home")
    if pr.get("heading"):
        ctx.put(s, "heading", pr["heading"], "fact", pr["source"])
    else:
        ctx.put(s, "heading", ctx.structure("home_press"))
    s.settings["layout"] = "row" if len(items) <= 5 else "marquee"
    for i, it in _slots(8, items):
        s.settings[f"logo_{i}"] = ctx.media(it["logo_role"])
        ctx.put(s, f"name_{i}", it["name"], "fact", it["source"])
        s.settings[f"link_{i}"] = it["url"]
    s.evidence = [f"{it['name']}: {it['url']}" for it in items[:8]]
    return s


def categories_home(ctx: Ctx):
    c = ctx.facts.get("categories")
    if not c:
        return Omit("categories_home", "needs 3 or more of the store's real collections to show as categories")
    items, niche, reasons = c["items"], niches.niche_of(ctx.brand["category"]), []
    for app_block in niches.order_blocks(CATEGORY_BLOCKS, ctx.brand["category"]):  # niche first, then the other layouts
        block = app_block.split("/")[1]
        fewest, most = CATEGORY_TILES[block]
        if len(items) < fewest:
            reasons.append(f"{block} needs at least {fewest} categories")
            continue
        tiles = items[:most]
        if block == "category-grid" and len(tiles) == 4:  # its even grid has 3 tiles a row on desktop: the 4th would sit alone (14 Oct 2026)
            reasons.append("category-grid would leave the 4th tile alone on its own row")
            continue
        s = Section("home_categories", "dtj-commerce", block, role="plain", kind="categories_home")
        s.settings["collections"] = [it["collection"] for it in tiles]
        if c.get("heading"):
            ctx.put(s, "heading", c["heading"], "fact", c["source"])
        else:
            ctx.put(s, "heading", ctx.structure("home_categories"))
        for i, it in _slots(most, tiles):
            image = ctx.media(it.get("image_role"))
            if image:
                s.settings[f"image_{i}"] = image
            ctx.put(s, f"title_{i}", it.get("title"), "fact", it["source"])
            if block == "category-grid":
                ctx.put(s, f"button_{i}", it.get("button"), "fact", it["source"])
        if block == "circle-menu":
            s.settings["variation"] = CIRCLE_VERSION.get(niche, "square")
            # a row of small tiles is a way to move around, not a headline section: a quiet heading (Harsh, 14 Oct 2026: "this section is
            # way too big" with the block's own 44 px heading above 100 px tiles)
            s.settings.update({"heading_size_desktop": 28, "heading_size_mobile": 22})
            if len(tiles) >= 4:  # phones: one row to swipe (centred when it fits); wrapping 3 a row leaves a tile alone (14 Oct 2026)
                s.settings["mobile_layout"] = "scroll"
        elif block == "category-grid":
            s.settings["layout"] = "bento_left" if len(tiles) == 5 else "even"  # the big layouts need exactly 5 tiles
            s.settings["overlay"] = 30  # white titles stay readable on a bright picture
        else:
            s.settings["shape"] = SLIDER_SHAPE.get(niche, "leaf")
        return s
    return Omit("categories_home", "; ".join(reasons))


def best_sellers_home(ctx: Ctx):
    b = ctx.facts.get("best_sellers")
    if not b:
        return Omit("best_sellers_home", "needs at least one of the store's real collections to show its products")
    s = Section("home_bestsellers", "dtj-commerce", "best-sellers", role="plain", kind="best_sellers_home")
    s.settings["collections"] = [x["collection"] for x in b["collections"][:5]]
    if b.get("heading"):
        ctx.put(s, "heading", b["heading"], "fact", b["source"])
    else:
        ctx.put(s, "heading", ctx.structure("home_shop"))  # "best sellers" would be a sales claim: only the facts may say it
    for i, x in _slots(5, b["collections"]):
        ctx.put(s, f"tab_{i}", x.get("tab"), "fact", b["source"])
    if b.get("badge_tags"):
        ctx.put(s, "badge_tags", ", ".join(b["badge_tags"]), "fact", b["source"])
    s.settings.update({"show_rating": True, "quick_add": "button", "card_style": "soft"})  # ratings come only from real reviews (Judge.me)
    ctx.put(s, "add_label", ctx.structure("home_add"))  # a buying action in plain words, not the block's "Quick add" (14 Oct 2026)
    return s


def concerns_home(ctx: Ctx):
    c = ctx.facts.get("concerns")
    if not c:
        return Omit("concerns_home", "needs 2 to 6 concerns, each matched to one of the store's real collections")
    s = Section("home_concerns", "dtj-shop", "concern-slider", role="band", kind="concerns_home")
    s.settings["collections"] = [it["collection"] for it in c["items"][:6]]
    # a browse row: picture, name, price, button. The product description under the name (the first lines of the store's own text) made every card
    # taller and noisier (Harsh, 20 Oct 2026: "the section is way too huge for a desktop screen")
    s.settings["show_blurb"] = False
    if c.get("heading"):
        ctx.accent_pair(s, "heading", "heading_accent", c["heading"], c.get("heading_accent"), "fact", c["source"])
    else:
        ctx.accent_pair(s, "heading", "heading_accent", ctx.structure("home_concern_h"), ctx.structure("home_concern_a"), "structure", "page structure")
    ctx.put(s, "subtext", c.get("intro"), "fact", c["source"])
    for i, it in _slots(6, c["items"]):
        ctx.put(s, f"concern_{i}", it["label"], "fact", it["source"])
    return s


def _compare_table(ctx: Ctx, c: dict):
    """DTJ Sections comparison-table: a port of the Super Senior pack's comparison (our tall column tinted with the brand name and picture on top, the
    other column plain, a sentence in each cell, thin divider lines, the heading beside it on desktop). The star line under the heading is the pack's
    own and only ever carries a REAL rating: it is not built here."""
    s = Section("home_compare", "dtj-sections", "comparison-table", role="plain", kind="compare_home")
    if c.get("heading"):
        ctx.put(s, "heading", c["heading"], "fact", c["source"])
    else:
        ctx.put(s, "heading", ctx.structure("compare_why", other=c["them_title"]))
    ctx.put(s, "brand_label", c.get("us_title") or ctx.brand["brand_name"], "fact", c["source"])
    ctx.put(s, "other_label", c["them_title"], "fact", c["source"])
    s.settings["header_layout"] = "side"
    for key, role in (("our_brand_image", c.get("image_role")), ("other_brand_image", c.get("them_image_role"))):
        image = ctx.media(role)
        if image:
            s.settings[key] = image
    for i, row in _slots(10, c["rows"]):
        ctx.put(s, f"our_text_{i}", row["us"], "fact", c["source"])
        ctx.put(s, f"other_text_{i}", row["them"], "fact", c["source"])
    s.evidence = [f"comparison approved by the owner ({c['source']})"]
    return s


def compare_home(ctx: Ctx):
    c = ctx.facts.get("compare")
    if not c:
        return Omit("compare_home", "no comparison facts")
    if not c.get("claims_approved"):
        return Omit("compare_home", "needs the owner's approval first: an empty cell shows a tick or a cross, a claim about other products")
    if all("label" not in row for row in c["rows"]):  # two columns of sentences: Harsh's reference table (20 Oct 2026: "i need exact replica of it")
        return _compare_table(ctx, c)
    s = Section("home_compare", "dtj-heroes", "compare-showcase", role="plain", kind="compare_home")
    s.settings["variation"] = "spotlight"
    if c.get("heading"):
        ctx.put(s, "heading", c["heading"], "fact", c["source"])
    else:
        ctx.put(s, "heading", ctx.structure("compare", other=c["them_title"]))
    if c.get("eyebrow") and ctx.eyebrow_allowed():
        ctx.put(s, "eyebrow", c["eyebrow"], "fact", c["source"])
    ctx.put(s, "text", c.get("text"), "fact", c["source"])
    if c.get("points"):
        ctx.put(s, "points", "\n".join(c["points"][:4]), "fact", c["source"])
    ctx.put(s, "us_title", c.get("us_title") or ctx.brand["brand_name"], "fact", c["source"])
    ctx.put(s, "us_sub", c.get("us_sub"), "fact", c["source"])
    ctx.put(s, "them_title", c["them_title"], "fact", c["source"])
    for i, row in _slots(7, c["rows"]):
        ctx.put(s, f"r{i}_label", row["label"], "fact", c["source"])
        ctx.put(s, f"r{i}_us", row.get("us"), "fact", c["source"])  # empty = a tick
        ctx.put(s, f"r{i}_them", row.get("them"), "fact", c["source"])  # empty = a cross
    image = ctx.media(c.get("image_role"))
    if image:
        s.settings["image"] = image
    if c.get("cta_label"):
        ctx.put(s, "button_label", c["cta_label"], "fact", c["source"])
        s.settings["button_url"] = c.get("cta_url") or "/collections/all"
    s.evidence = [f"comparison approved by the owner ({c['source']})"]
    return s


def before_after_home(ctx: Ctx):
    ba = ctx.facts.get("before_after")
    if not ba:
        return Omit("before_after_home", "needs a REAL before / after photo pair with the person's permission (never staged or invented)")
    before, after = ctx.media(ba["before_role"]), ctx.media(ba["after_role"])
    if not (before and after):
        return Omit("before_after_home", "the media list has no picture for the before or the after role")
    s = Section("home_before_after", "dtj-shop", "before-after", role="band", kind="before_after_home")
    s.settings.update({"before_image": before, "after_image": after, "show_stars": False,  # five stars would claim reviews: never on by default
                       "variation": "circle" if niches.niche_of(ctx.brand["category"]) == "beauty" else "card"})
    if ba.get("eyebrow") and ctx.eyebrow_allowed():
        ctx.put(s, "eyebrow_bold", ba["eyebrow"], "fact", ba["source"])
    ctx.accent_pair(s, "heading", "heading_accent", ba["heading"], ba.get("heading_accent"), "fact", ba["source"])
    if ba.get("body"):
        ctx.put(s, "body", f"<p>{html.escape(ba['body'])}</p>", "fact", ba["source"])
    for i, pt in _slots(3, ba.get("points", [])):
        ctx.put(s, f"point_{i}_bold", pt["bold"], "fact", ba["source"])
        ctx.put(s, f"point_{i}_rest", pt.get("rest"), "fact", ba["source"])
    if ba.get("cta_label"):
        ctx.put(s, "button_label", ba["cta_label"], "fact", ba["source"])
        s.settings["button_link"] = ba.get("cta_url") or "/collections/all"
    s.evidence = [f"photos shown with permission: {ba['consent']}"]
    return s


def wave_home(ctx: Ctx):
    """A soft wave into the next band. Its colours are set by the assembler from the sections around it (the colour above and the colour
    below); when both are the same there is no edge to soften and the wave is left out."""
    s = Section("home_wave", "dtj-commerce", "wave-divider", role="none", kind="wave_home")
    s.settings.update({"style": "layered", "layers": 3, "wave_height": 100, "wave_height_mobile": 60,
                       "animate": False})  # the direction lets nothing move on its own except the slideshow timer (direction.py)
    return s


HOME_BUILDERS = {f.__name__: f for f in (hero_home, trust_marquee, trust_band_home, announcement_bar, value_props_home, story_home, video_reviews_home,
                                         faq, press_home, categories_home, best_sellers_home, concerns_home, compare_home, before_after_home, wave_home)}

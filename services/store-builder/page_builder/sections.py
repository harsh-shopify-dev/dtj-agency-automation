"""Section builders: product facts -> block settings. A builder returns a Section, or Omit(reason) when its facts are missing.
Nothing here writes marketing copy: text comes from facts (verbatim, with its source) or from a short structural template
("Why choose {brand}?"), and both are recorded in the provenance table so the lint rules can prove it."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from .catalog import IMAGE_PREFIX, VIDEO_PREFIX, Catalog

FEATURE_ICONS = ["sparkles", "check", "shield_plus", "wind_calm", "leaf", "flask", "pill", "microscope", "heart_pulse", "shield_focus", "brain", "eye"]
SLIDE_ICONS = {"leaf", "shield", "check", "globe", "heart", "bolt", "snowflake", "bulb", "brain", "drop", "sparkle", "star", "truck", "clock", "award", "atom"}
MAX_TEXT = 250  # a single-line text setting stays short; longer copy belongs in a textarea setting

# structural copy: the page's signposts. A Claude step may rewrite these in the brand's voice inside copy_contract.py; they never contain claims.
STRUCTURE = {
    "why": "Why choose {brand}?",
    "how_h": "How it", "how_a": "works.",
    "inside": "What's in the box", "inside_hl": "box",
    "notinside": "What's not inside", "notinside_hl": "not inside",
    "compare": "{brand} vs. {other}",
    "compare_why": "Why {brand} outperforms {other}",
    "faq_h": "Questions,", "faq_a": "answered",
    "reviews": "What customers say",
    "numbers": "{brand} in numbers",
    "glance": "{brand} at a glance",
    "footnote": "From {sources}.",
    "ugc": "{brand} in real life",
    "why_us": "Why {brand}",
    "stories": "In their own words",
    "cta": "Shop now",
    # one button label per section, named after what that section says (Harsh, 10 Oct 2026: "every CTAs have the same text, they should be
    # named accordingly with what the section says"). Generic buying actions; the copy step rewrites them in the section's own words.
    "cta_ugc_strip": "Get yours",
    "cta_story_split": "Try it yourself",
    "cta_story_split_2": "Make it yours",
    "cta_reviews_slider": "Join them",
    "cta_why_us": "Make the switch",
    "cta_why_features": "Get started",
    "cta_guarantee": "Order with confidence",
    "cta_facts_glance": "Choose yours",
    "cta_faq": "Ready? Order now",
    "cta_stories": "Start your story",
}
MAIN = "#MainContent"  # Horizon's main content anchor: the top of the product (buy box) section


@dataclass
class Section:
    id: str
    app: str
    block: str
    settings: dict = field(default_factory=dict)
    role: str = "auto"  # auto | plain | band | dark | accent | none (none = no band, no alternation)
    kind: str = ""
    cta: bool = False  # a DTJ CTA button follows this section (DTJ Standard Product Page v1)


@dataclass
class Omit:
    kind: str
    reason: str


class Ctx:
    """Everything a builder needs, plus the provenance table every text value is recorded in."""

    def __init__(self, brand: dict, facts: dict, direction, catalog: Catalog, copy: dict | None = None):
        self.brand, self.facts, self.direction, self.catalog = brand, facts, direction, catalog
        self.copy = copy or {}  # accepted rewrites of STRUCTURAL copy only, keyed "<section id>.<setting>" (see copy_contract.py)
        self.demo = bool(facts.get("demo"))
        self.prov: dict[tuple[str, str], dict] = {}
        self.accents_used = 0
        self.eyebrows_used = 0
        self._media = {m["role"]: m for m in facts.get("media", [])}

    @property
    def title(self) -> str:
        return self.facts["product"]["title"]

    def media(self, role: str | None) -> str | None:
        item = self._media.get(role) if role else None
        return f"{IMAGE_PREFIX}{item['file']}" if item else None

    def structure(self, key: str, **kw) -> str:
        return STRUCTURE[key].format(brand=kw.pop("brand", self.brand["brand_name"]), **kw)

    def put(self, section: Section, key: str, value, kind: str = "structure", source: str = "page structure"):
        """Set a text setting and record where the words came from."""
        if value in (None, ""):
            return
        value = str(value)
        if len(value) > MAX_TEXT and key in self.catalog.text_settings(section.app, section.block) and \
                self.catalog.settings(section.app, section.block)[key]["type"] == "text":
            raise ValueError(f"{section.id}.{key}: {len(value)} characters is too long for a text setting")
        if kind == "fact" and str(source).lower().startswith("demo"):
            kind = "demo"
        if kind == "fact" and str(source).upper().startswith("SAMPLE"):
            kind = "sample"  # sample content (Harsh, 10 Oct 2026): listed in the report, draft themes only, replaced before live
        if kind == "fact" and str(source).upper().startswith("DTJ COPY"):
            kind = "dtj_copy"  # a line WE wrote on a sourced fact (references/copywriting.md): listed for the client's sign-off, lint L19
        if kind == "structure" and f"{section.id}.{key}" in self.copy:
            value, kind, source = self.copy[f"{section.id}.{key}"], "copy", "claude copy step (validated)"
        section.settings[key] = value
        self.prov[(section.id, key)] = {"kind": kind, "source": source, "text": value}

    def take_accent(self) -> bool:
        """The page may accent at most direction.type.accent_words_max headlines (accenting a word in every heading reads as a template)."""
        if self.accents_used < self.direction.type["accent_words_max"]:
            self.accents_used += 1
            return True
        return False

    def accent_pair(self, section: Section, key_heading: str, key_accent: str, before: str, accent: str | None, kind: str, source: str):
        """Heading + accent words: the accent field is used while the page's accent budget lasts, otherwise the words join the plain heading."""
        if accent and self.take_accent():
            self.put(section, key_heading, before, kind, source)
            self.put(section, key_accent, accent, kind, source)
        else:
            self.put(section, key_heading, f"{before} {accent or ''}".strip(), kind, source)

    def eyebrow_allowed(self) -> bool:
        if self.eyebrows_used < self.direction.type["eyebrow_max"]:
            self.eyebrows_used += 1
            return True
        return False


TICKS = 4  # every tick-mark list on a page has exactly this many points (rule L13)
AVATARS = 5  # the rating line shows exactly this many round photos, or none (rule L14; Harsh, 9 Oct 2026)


SHIELD_WORDS = re.compile(r"\b(tested|guarantee[ds]?|warranty|returns?|refunds?|safe|secure|trusted|licensed|certified|verified|genuine|authentic)\b", re.I)

def _slots(n_max, items):
    return list(enumerate(items[:n_max], 1))


# ------------------------------------------------------------------------------------------------ page sections
def trust_marquee(ctx: Ctx):
    pts = ctx.facts.get("trust_points", [])
    if len(pts) < 3:
        return Omit("trust_marquee", "needs at least 3 trust points (a short strip of one or two reads empty)")
    s = Section("dtj_marquee", "dtj-sections", "marquee", role="none", kind="trust_marquee")
    for i, p in _slots(10, pts):
        ctx.put(s, f"text_{i}", p["text"], "fact", p["source"])
    return s


def why_features(ctx: Ctx):
    items = ctx.facts.get("benefits", [])
    n = len(items) if len(items) in (4, 6) else (4 if len(items) >= 4 and len(items) != 5 else 0)
    if len(items) == 5:
        n = 4
    if n == 0:
        return Omit("why_features", "needs 4 or 6 benefits so both sides of the layout are filled")
    s = Section("dtj_why", "dtj-sections-2", "feature-showcase", role="plain", kind="why_features")
    intro = ctx.facts.get("feature_intro")
    if intro:  # W10 of the standard page: a benefit headline and two sentences above the four benefits
        ctx.put(s, "heading", intro["heading"], "fact", intro["source"])
        ctx.put(s, "subheading", intro.get("text"), "fact", intro["source"])
    else:
        ctx.put(s, "heading", ctx.structure("why"))
    image = ctx.media("pack")
    if image:
        s.settings["image"] = image
    slot_for = ["f1", "f4", "f2", "f5", "f3", "f6"]  # alternate left / right so any even number stays balanced
    for k, b in enumerate(items[:n]):
        f = slot_for[k]
        ctx.put(s, f"{f}_title", b["title"], "fact", b["source"])
        ctx.put(s, f"{f}_text", b.get("text"), "fact", b["source"])
        icon = b.get("icon") if b.get("icon") in FEATURE_ICONS else FEATURE_ICONS[k % len(FEATURE_ICONS)]
        s.settings[f"{f}_icon"] = icon
    return s


def facts_glance(ctx: Ctx):
    kf = ctx.facts.get("key_facts", [])
    if len(kf) < 2:
        return Omit("facts_glance", "needs at least 2 key facts (a figure, what it counts and where it comes from)")
    with_images = [f for f in kf if ctx.media(f.get("image_role"))]
    if len(with_images) == len(kf) and len(kf) >= 3:
        s = Section("dtj_stats", "dtj-sections", "science-stats", role="band", kind="facts_glance")
        ctx.put(s, "heading", ctx.structure("glance"))
        for i, f in _slots(6, kf):
            ctx.put(s, f"number_{i}", f["value"], "fact", f["source"])
            ctx.put(s, f"description_{i}", f["label"], "fact", f["source"])
            s.settings[f"image_{i}"] = ctx.media(f["image_role"])
        return s
    s = Section("dtj_numbers", "dtj-sections-2", "stat-cards", role="band", kind="facts_glance")
    ctx.put(s, "heading", ctx.structure("numbers"))
    if len(kf) == 4 and max(len(f["value"]) for f in kf) >= 7:
        s.settings["columns"] = "2"  # a long figure ("2,00,000+") broke across two lines in a row of four (book page, 10 Oct 2026)
    for i, f in _slots(6, kf):
        ctx.put(s, f"number_{i}", f["value"], "fact", f["source"])
        ctx.put(s, f"label_{i}", f["label"], "fact", f["source"])
        # only a real note is shown: a source is bookkeeping ("product description ... confirmed by Harsh"), not words for shoppers
        ctx.put(s, f"note_{i}", f.get("note"), "fact", f["source"])
    return s


def story_split(ctx: Ctx):
    st = ctx.facts.get("story")
    if not st:
        return Omit("story_split", "needs a story (a heading, a short paragraph and its source)")
    s = Section("dtj_story", "dtj-sections-2", "split-story", role="plain", kind="story_split")
    ctx.accent_pair(s, "heading", "heading_accent", st["heading"], st.get("accent"), "fact", st["source"])
    ctx.put(s, "body", st.get("body"), "fact", st["source"])
    for i, b in _slots(TICKS, st.get("bullets", [])):
        ctx.put(s, f"bullet_{i}", b, "fact", st["source"])
    image = ctx.media(st.get("image_role"))
    if image:
        s.settings["image"] = image
    s.settings["image_side"] = "start"
    return s


def how_split(ctx: Ctx):
    st = ctx.facts.get("steps")
    if not st:
        return Omit("how_split", "needs 2 to 5 steps and their source")
    s = Section("dtj_how", "dtj-sections-2", "split-story", role="plain", kind="how_split")
    ctx.accent_pair(s, "heading", "heading_accent", ctx.structure("how_h"), ctx.structure("how_a"), "structure", "page structure")
    ctx.put(s, "body", st.get("intro"), "fact", st["source"])
    for i, step in _slots(5, st["items"]):
        ctx.put(s, f"bullet_{i}", f"Step {i}: {step}", "fact", st["source"])
    image = ctx.media(st.get("image_role"))
    if image:
        s.settings["image"] = image
    s.settings["image_side"] = "end"
    return s


def proof_panel(ctx: Ctx):
    kf = ctx.facts.get("key_facts", [])
    if len(kf) < 3:
        return Omit("proof_panel", "needs at least 3 key facts: one for the card and two rows")
    s = Section("dtj_proof", "dtj-sections-2", "measured-results", role="dark", kind="proof_panel")
    st = ctx.facts.get("story")
    if st:
        ctx.put(s, "card_heading", st["heading"], "fact", st["source"])
        ctx.put(s, "card_heading_accent", st.get("accent"), "fact", st["source"])
    ctx.put(s, "card_figure", kf[0]["value"], "fact", kf[0]["source"])
    ctx.put(s, "card_figure_label", kf[0]["label"], "fact", kf[0]["source"])
    image = ctx.media("pack")
    if image:
        s.settings["image"] = image
    ctx.put(s, "heading", ctx.structure("numbers"))
    for i, f in _slots(5, kf[1:]):
        ctx.put(s, f"figure_{i}", f["value"], "fact", f["source"])
        ctx.put(s, f"title_{i}", f["label"], "fact", f["source"])
        ctx.put(s, f"text_{i}", f.get("note"), "fact", f["source"])
    sources = sorted({f["source"] for f in kf})
    ctx.put(s, "footnote", ctx.structure("footnote", sources=" and ".join(sources)))
    return s


def pack_inside(ctx: Ctx):
    items = ctx.facts.get("pack_contents", [])
    if len(items) < 2:
        return Omit("pack_inside", "needs at least 2 items (one item sits alone at the edge of the grid)")
    s = Section("dtj_inside", "dtj-sections", "whats-inside", role="plain", kind="pack_inside")
    ctx.put(s, "heading", ctx.structure("inside"))
    if ctx.take_accent():
        ctx.put(s, "highlight_word", ctx.structure("inside_hl"))
    s.settings["columns"] = {2: "2", 4: "4"}.get(len(items), "3")  # 4 items in 3 columns left one alone on a row (Go Mints, 9 Oct 2026)
    for i, it in _slots(6, items):
        ctx.put(s, f"name_{i}", it["name"], "fact", it["source"])
        ctx.put(s, f"description_{i}", it.get("detail"), "fact", it["source"])
        ctx.put(s, f"dose_{i}", it.get("dose"), "fact", it["source"])
        ctx.put(s, f"benefits_{i}", "\n".join(it.get("benefits", [])), "fact", it["source"])
        image = ctx.media(it.get("image_role"))
        if image:
            s.settings[f"image_{i}"] = image
    return s


def free_from(ctx: Ctx):
    items = ctx.facts.get("free_from", [])
    if len(items) < 2:
        return Omit("free_from", "needs at least 2 'not inside' items and their source")
    s = Section("dtj_notinside", "dtj-sections", "whats-not-inside", role="dark", kind="free_from")
    ctx.put(s, "heading", ctx.structure("notinside"))
    if ctx.take_accent():
        ctx.put(s, "highlight_word", ctx.structure("notinside_hl"))
    any_image = False
    for i, it in _slots(12, items):
        ctx.put(s, f"name_{i}", it["name"], "fact", it["source"])
        image = ctx.media(it.get("image_role"))
        if image:
            s.settings[f"image_{i}"] = image
            any_image = True
    if not any_image:
        s.settings["image_size"] = 60
    return s


def comparison(ctx: Ctx):
    c = ctx.facts.get("comparison")
    if not c:
        return Omit("comparison", "no comparison facts")
    if not c.get("claims_approved"):
        return Omit("comparison", "needs the owner's approval first: it makes claims about other products")
    s = Section("dtj_compare", "dtj-sections", "comparison-table", role="plain", kind="comparison")
    ctx.put(s, "heading", ctx.structure("compare", other=c.get("other_label", "others")))
    ctx.put(s, "brand_label", c.get("ours_label") or ctx.brand["brand_name"], "fact", c["source"])
    ctx.put(s, "other_label", c.get("other_label"), "fact", c["source"])
    s.settings["header_layout"] = "top"
    image = ctx.media(c.get("image_role") or "pack")
    if image:
        s.settings["our_brand_image"] = image
    for i, row in _slots(10, c["rows"]):
        ctx.put(s, f"our_text_{i}", row["ours"], "fact", c["source"])
        ctx.put(s, f"other_text_{i}", row["other"], "fact", c["source"])
    return s


def reviews_slider(ctx: Ctx):
    rv = ctx.facts.get("reviews", [])
    if len(rv) < 3:
        return Omit("reviews_slider", "needs at least 3 REAL reviews with a source (none are ever invented)")
    s = Section("dtj_reviews", "dtj-sections", "testimonials-slider", role="band", kind="reviews_slider")
    ctx.put(s, "heading", ctx.structure("reviews"))
    for i, r in _slots(8, rv):
        ctx.put(s, f"text_{i}", r["quote"], "fact", r["source"])
        ctx.put(s, f"author_{i}", ", ".join(x for x in (r["name"], r.get("location")) if x), "fact", r["source"])
        if r.get("rating"):
            s.settings[f"stars_{i}"] = str(r["rating"])
        image = ctx.media(r.get("image_role"))
        if image:
            s.settings[f"image_{i}"] = image
    return s


def faq(ctx: Ctx):
    qs = ctx.facts.get("faqs", [])
    if len(qs) < 3:
        return Omit("faq", "needs at least 3 questions with answers and their source")
    s = Section("dtj_faq", "dtj-sections", "faq", role="plain", kind="faq")
    ctx.accent_pair(s, "heading", "heading_accent", ctx.structure("faq_h"), ctx.structure("faq_a"), "structure", "page structure")
    s.settings["show_filters"] = False
    for i, q in _slots(12, qs):
        ctx.put(s, f"question_{i}", q["q"], "fact", q["source"])
        ctx.put(s, f"answer_{i}", f"<p>{html.escape(q['a'])}</p>", "fact", q["source"])
    return s


# ------------------------------------------------------------------------------------------------ DTJ Standard Product Page v1 (10 Oct 2026)
def cta_label(ctx: Ctx) -> tuple[str, str, str]:
    """The brand's main call-to-action label (the page's last button): (label, kind, source)."""
    c = ctx.facts.get("cta")
    return (c["label"], "fact", c["source"]) if c else (ctx.structure("cta"), "structure", "page structure")


def section_cta_label(ctx: Ctx, kind: str) -> tuple[str, str, str]:
    """The label of the button after a section: a buying action in that section's words. Every button does the same thing (the page's
    one action), but each is named after its section (Harsh, 10 Oct 2026). A structural default the copy step may rewrite; a section
    without one gets the main label."""
    key = f"cta_{kind}"
    return (ctx.structure(key), "structure", "page structure") if key in STRUCTURE else cta_label(ctx)


def ugc_strip(ctx: Ctx):
    items = ctx.facts.get("ugc", [])
    if len(items) < 3:
        return Omit("ugc_strip", "needs 3-6 customer photos or videos (with permission), or SAMPLE pictures on our own store")
    s = Section("dtj_ugc", "dtj-blocks", "shoppable-reels", role="dark", kind="ugc_strip")
    ctx.put(s, "heading", ctx.structure("ugc"))
    handle = ctx.facts.get("product", {}).get("handle")
    if handle:
        s.settings["products"] = [handle] * min(6, len(items))
    for i, it in _slots(6, items):
        s.settings[f"media_type_{i}"] = "image"
        if it.get("video"):  # a reader's or creator's video (Harsh, 10 Oct 2026: videos for the testimonials); the picture stays as fallback
            s.settings[f"media_type_{i}"] = "video"
            s.settings[f"video_{i}"] = f"{VIDEO_PREFIX}{it['video']}"
        image = ctx.media(it["image_role"])
        if image:
            s.settings[f"image_{i}"] = image
    return s


def story_split_2(ctx: Ctx):
    st = ctx.facts.get("story_2")
    if not st:
        return Omit("story_split_2", "needs the second big benefit (a heading, a short paragraph, 4 points and their source)")
    s = Section("dtj_story_2", "dtj-sections-2", "split-story", role="band", kind="story_split_2")
    ctx.accent_pair(s, "heading", "heading_accent", st["heading"], st.get("accent"), "fact", st["source"])
    ctx.put(s, "body", st.get("body"), "fact", st["source"])
    for i, b in _slots(TICKS, st.get("bullets", [])):
        ctx.put(s, f"bullet_{i}", b, "fact", st["source"])
    image = ctx.media(st.get("image_role"))
    if image:
        s.settings["image"] = image
    s.settings["image_side"] = "end"
    return s


def why_us(ctx: Ctx):
    d = ctx.facts.get("differentiators")
    if not d or len(d.get("items", [])) < 4:
        return Omit("why_us", "needs 4 or 6 differentiators (title + one line each) and their source")
    items = d["items"][:6] if len(d["items"]) >= 6 else d["items"][:4]
    s = Section("dtj_why_us", "dtj-sections", "whats-inside", role="plain", kind="why_us")
    ctx.put(s, "heading", d["heading"], "fact", d["source"])
    if d.get("highlight") and d["highlight"] in d["heading"] and ctx.take_accent():
        ctx.put(s, "highlight_word", d["highlight"], "fact", d["source"])
    s.settings["columns"] = "3" if len(items) == 6 else "2"
    for i, it in _slots(6, items):
        ctx.put(s, f"name_{i}", it["title"], "fact", it["source"])
        ctx.put(s, f"description_{i}", it.get("text"), "fact", it["source"])
        image = ctx.media(it.get("image_role"))
        if image:
            s.settings[f"image_{i}"] = image
    return s


def benefit_strip_2(ctx: Ctx):
    pts = ctx.facts.get("strip_2", [])
    if len(pts) < 3:
        return Omit("benefit_strip_2", "needs at least 3 points that are not in the first strip")
    s = Section("dtj_marquee_2", "dtj-sections", "marquee", role="none", kind="benefit_strip_2")
    for i, p in _slots(10, pts):
        ctx.put(s, f"text_{i}", p["text"], "fact", p["source"])
    return s


def guarantee(ctx: Ctx):
    g = ctx.facts.get("guarantee")
    if not g:
        return Omit("guarantee", "needs the brand's guarantee or return promise with its terms (or SAMPLE terms)")
    s = Section("dtj_guarantee", "dtj-sections-2", "cta", role="accent", kind="guarantee")
    s.settings["style"] = "banner"
    ctx.put(s, "heading", g["heading"], "fact", g["source"])
    ctx.put(s, "text", g.get("text"), "fact", g["source"])
    ctx.put(s, "seal_text", g.get("seal"), "fact", g["source"])
    label, kind, source = section_cta_label(ctx, "guarantee")
    ctx.put(s, "button_label", label, kind, source)
    s.settings["action"] = (ctx.facts.get("cta") or {}).get("action", "scroll")
    return s


def stories(ctx: Ctx):
    items = ctx.facts.get("stories", [])
    if len(items) < 3:
        return Omit("stories", "needs 3-6 customer stories (photo, name, quote) or SAMPLE ones")
    s = Section("dtj_stories", "dtj-sections", "stories", role="band", kind="stories")
    ctx.put(s, "heading", ctx.structure("stories"))
    for i, it in _slots(6, items):
        ctx.put(s, f"name_{i}", it["name"], "fact", it["source"])
        ctx.put(s, f"quote_{i}", it["quote"], "fact", it["source"])
        ctx.put(s, f"tags_{i}", it.get("tags"), "fact", it["source"])
        image = ctx.media(it.get("image_role"))
        if image:
            s.settings[f"photo_{i}"] = image
    label, kind, source = section_cta_label(ctx, "stories")
    ctx.put(s, "cta_text", label, kind, source)
    s.settings["cta_link"] = MAIN
    return s


def final_push(ctx: Ctx):
    f = ctx.facts.get("final_push")
    if not f:
        return Omit("final_push", "needs the final value proposition (a heading, one sentence, a picture)")
    s = Section("dtj_final", "dtj-sections-2", "slideshow-pro", role="none", kind="final_push")
    ctx.put(s, "heading_1", f["heading"], "fact", f["source"])
    ctx.put(s, "description_1", f.get("text"), "fact", f["source"])
    label, kind, source = cta_label(ctx)
    ctx.put(s, "button_label_1", label, kind, source)
    s.settings["button_url_1"] = MAIN
    image = ctx.media(f.get("image_role")) or ctx.media("pack")
    if image:
        s.settings["image_1"] = image
    s.settings.update({"autoplay": False, "show_progress": False, "arrows_position": "none", "overlay_style": "solid",
                       "overlay_opacity": 60, "content_position": "center",
                       # the slide takes the picture's own shape, so nothing is cut off (Harsh, 10 Oct 2026: "the section should adapt to
                       # image size"; a 4:5 crop of a square pack shot cut its printed claims at both edges)
                       "ratio_desktop": "adapt", "ratio_mobile": "adapt"})
    return s


BUILDERS = {f.__name__: f for f in (trust_marquee, why_features, facts_glance, story_split, how_split, proof_panel, pack_inside, free_from, comparison, reviews_slider, faq,
                                    ugc_strip, story_split_2, why_us, benefit_strip_2, guarantee, stories, final_push)}


# ------------------------------------------------------------------------------------------------ buy box blocks
def buybox_blocks(ctx: Ctx) -> dict:
    """The DTJ blocks of the buy box, keyed by position: before_title, after_title, before_picker, before_buttons, after_buttons."""
    f, out = ctx.facts, {"before_title": [], "after_title": [], "before_picker": [], "before_buttons": [], "after_buttons": []}
    d = ctx.direction
    sp = f.get("social_proof") or {}
    if f.get("rating") or sp:
        # the line above the title: [badge] [stars + number] [real customer photos] [proof lines], every part from a sourced fact
        s = Section("dtj_stars", "dtj-blocks", "social-proof", kind="rating")
        rich = bool(sp) or ctx.demo  # a full line (badge, photos) gets the five-star style
        s.settings.update({"show_stars": bool(f.get("rating")), "show_rating_number": True, "show_stock": False,
                           "rating_style": "five" if rich else "single"})
        if f.get("rating"):
            ctx.put(s, "rating_value", f["rating"]["value"], "fact", f["rating"]["source"])
        if sp.get("badge"):
            ctx.put(s, "badge_text", sp["badge"]["text"], "fact", sp["badge"]["source"])
            # the block's only icon is a shield: it fits a promise ("Lab tested", "7-day returns"), not a label like "High protein"
            # (Harsh, 24 Oct 2026: "the shield is totally unrelated with the badge saying high protein")
            s.settings["badge_icon"] = bool(SHIELD_WORDS.search(sp["badge"]["text"]))
        for i, line in _slots(2, sp.get("lines", [])):
            ctx.put(s, f"proof_text_{i}", line["text"], "fact", line["source"])
        n = 0
        for av in sp.get("avatars", []):  # the schema requires a consent note for every customer photo
            image = ctx.media(av["role"])
            if image and n < AVATARS:
                n += 1
                s.settings[f"avatar_{n}"] = image
        out["before_title"].append(s)
    price = Section("dtj_price", "dtj-blocks", "price", kind="price")
    out["after_title"].append(price)
    bb = f.get("buybox") or {}
    # always exactly 4 points (Harsh, 9 Oct 2026): the buy box's own, topped up from the benefit titles, never invented (rule L13)
    bullets = list(bb.get("bullets") or [])
    bullets += [b["title"] for b in f.get("benefits", []) if b["title"] not in bullets]
    bullets = bullets[:TICKS]
    if bullets:
        s = Section("dtj_points", "dtj-blocks", "hero-points", kind="hero_points")
        src = bb.get("source") or "product benefits"
        if bb.get("tagline") and ctx.eyebrow_allowed():
            ctx.put(s, "eyebrow", bb["tagline"], "fact", src)
        ctx.put(s, "subheading", bb.get("intro"), "fact", src)
        ctx.put(s, "benefits", "\n".join(bullets[:4]), "fact", src)
        s.settings.update({"columns": "2", "show_star": False})
        out["after_title"].append(s)
    bundles = f.get("bundles") or {}
    if len(bundles.get("variant_handles", [])) >= 2:
        s = Section("dtj_picker", "dtj-blocks", "shade-picker", kind="picker")
        s.settings.update({"products": bundles["variant_handles"], "style": "pill"})
        out["before_picker"].append(s)
    if bundles.get("addon_handles"):
        s = Section("dtj_addons", "dtj-blocks", "addons", kind="addons")
        s.settings["products"] = bundles["addon_handles"]
        out["before_buttons"].append(s)
    rv = f.get("reviews", [])
    if rv:
        s = Section("dtj_reviews_buy", "dtj-blocks", "testimonials", kind="reviews_buybox")
        for i, r in _slots(5, rv):
            ctx.put(s, f"quote_{i}", r["quote"], "fact", r["source"])
            ctx.put(s, f"name_{i}", r["name"], "fact", r["source"])
            ctx.put(s, f"location_{i}", r.get("location"), "fact", r["source"])
            if r.get("rating"):
                s.settings[f"rating_{i}"] = str(r["rating"])
        out["after_buttons"].append(s)
    return out

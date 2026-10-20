"""The home page recipe: niche-aware order, hero layout and block choice; omission instead of invention; the same lint rules as the product page."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jsonschema import Draft202012Validator  # noqa: E402
from page_builder import niches  # noqa: E402
from page_builder.assemble import InputError  # noqa: E402
from page_builder.assemble_home import build_home  # noqa: E402
from page_builder.examples.fixtures import BRANDS  # noqa: E402

SRC = "demo fixture"
ROLES = ("hero", "hero_m", "values", "story", "c1", "c2", "c3", "c4")


def home_facts() -> dict:
    return {
        "demo": True,
        "media": [{"role": r, "file": f"{r}.webp"} for r in ROLES],
        "hero": {"headline": "Sample headline for *the brand.*", "sub": "Sample sub line.", "badge": "Sample badge", "points": ["Point one", "Point two"],
                 "cta_label": "Shop all", "cta_url": "/collections/all", "image_role": "hero", "image_mobile_role": "hero_m", "source": SRC},
        "trust_points": [{"text": t, "source": SRC} for t in ("First point", "Second point", "Third point", "Fourth point")],
        "value_props": {"heading": "Sample reasons", "image_role": "values", "source": SRC,
                        "items": [{"title": f"Reason {i}", "text": f"Reason {i} text", "source": SRC} for i in range(1, 5)]},
        "story": {"heading": "Sample story", "body": "A short sample paragraph.", "bullets": ["Tick one", "Tick two", "Tick three", "Tick four"], "image_role": "story",
                  "source": SRC},
        "video_reviews": {"heading": "Sample customers", "source": SRC,
                          "items": [{"name": f"Customer {i}", "line": "Sample line", "image_role": f"c{i}", "url": "/collections/all", "source": SRC} for i in range(1, 5)]},
        "faqs": [{"q": f"Question {i}?", "a": f"Answer {i}.", "source": SRC} for i in range(1, 4)],
    }


def full_facts() -> dict:
    """home_facts plus the facts of every block wired on 13 Oct 2026, so that no section is left out."""
    f = home_facts()
    f["media"] += [{"role": r, "file": f"{r}.webp"} for r in ("p1", "p2", "p3", "before", "after", "cmp")]
    f["announcements"] = {"source": SRC, "items": [{"text": "Free shipping on prepaid orders", "source": SRC}, {"text": "Easy 7-day returns", "source": SRC},
                                                   {"text": "Cash on delivery available", "source": SRC}]}
    f["categories"] = {"source": SRC, "items": [{"collection": c, "source": SRC} for c in ("face", "body", "hair", "kits")]}
    f["best_sellers"] = {"source": SRC, "collections": [{"collection": "face", "tab": "Face"}, {"collection": "body", "tab": "Body"}]}
    f["concerns"] = {"source": SRC, "items": [{"collection": "acne", "label": "Acne", "source": SRC}, {"collection": "dry-skin", "label": "Dry skin", "source": SRC}]}
    f["press"] = {"source": SRC, "items": [{"name": f"Paper {i}", "logo_role": f"p{i}", "url": f"https://example.com/a{i}", "source": SRC} for i in (1, 2, 3)]}
    f["compare"] = {"source": SRC, "claims_approved": True, "them_title": "Others", "cta_label": "See the difference", "image_role": "cmp",
                    "rows": [{"label": f"Row {i}"} for i in (1, 2, 3)]}
    f["before_after"] = {"source": SRC, "before_role": "before", "after_role": "after", "heading": "Real results", "heading_accent": "in 4 weeks",
                         "consent": "Signed consent from the customer, 1 Oct 2026", "cta_label": "Start yours"}
    return f


def brand(category: str) -> dict:
    by_cat = {b["category"]: b for b, _ in BRANDS.values()}
    if category in by_cat:
        return copy.deepcopy(by_cat[category])
    return {"brand_name": "Hearth", "category": category, "price_tier": "mid", "voice": "plain",
            "colors": {"primary": "#2F6B4F", "background": "#FFFFFF", "text": "#1B2B22"}}


def blocks(result) -> list[str]:
    return [s["block"] for s in result.report["sections_built"]]


class NicheTests(unittest.TestCase):
    def test_every_category_builds_a_clean_page(self):
        for category in ("beauty", "supplements", "home-care", "food", "apparel", "other"):
            for facts in (home_facts(), full_facts()):
                res = build_home(brand(category), facts)
                self.assertEqual(res.report["problems"], [], category)
                self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [], category)
            # with every fact present nothing is left out, except the theme's product row that the DTJ product rows replace
            self.assertEqual([o["section"] for o in res.report["sections_omitted"]], ["theme:product_list"], category)
            self.assertEqual(len(res.report["sections_built"]), 14, category)

    def test_the_order_and_the_hero_layout_follow_the_niche(self):
        beauty = build_home(brand("beauty"), home_facts())
        fashion = build_home(brand("apparel"), home_facts())
        self.assertEqual(beauty.report["niche"], "beauty")
        self.assertEqual(fashion.report["niche"], "fashion")
        kinds = lambda r: [s["kind"] for s in r.report["sections_built"]]  # noqa: E731
        self.assertEqual(kinds(beauty)[:3], ["hero_home", "trust_band_home", "value_props_home"])  # beauty: trust and reasons first
        self.assertTrue(fashion.report["page_order"][1].startswith("product_list"))  # fashion shows products right after the hero
        layouts = {c: next(b["settings"]["layout"] for sec in build_home(brand(c), home_facts()).template["sections"].values() for b in sec["blocks"].values()
                           if "dtj-hero-banner" in b["type"]) for c in ("beauty", "apparel", "food")}
        self.assertEqual(layouts, {"beauty": "banner", "apparel": "cover", "food": "cover"})

    def test_each_niche_picks_its_own_block_for_the_reasons_section(self):
        want = {"beauty": "feature-cards", "supplements": "feature-cards", "food": "feature-cards", "home-care": "feature-tiles", "apparel": "feature-tiles",
                "other": "feature-cards"}
        for category, block in want.items():
            res = build_home(brand(category), home_facts())
            self.assertIn(f"dtj-heroes/{block}", blocks(res), category)
            other = "feature-tiles" if block == "feature-cards" else "feature-cards"
            self.assertNotIn(f"dtj-heroes/{other}", blocks(res), category)

    def test_when_the_niche_block_cannot_be_filled_the_next_one_is_used(self):
        facts = home_facts()
        del facts["value_props"]["image_role"]  # the soft-card layout needs a centre picture
        res = build_home(brand("beauty"), facts)
        self.assertIn("dtj-heroes/feature-tiles", blocks(res))
        self.assertNotIn("dtj-heroes/feature-cards", blocks(res))
        self.assertEqual(res.report["problems"], [])

    def test_the_niche_fit_is_reported_for_every_section(self):
        res = build_home(brand("beauty"), home_facts())
        fits = {s["block"]: s["niche_fit"] for s in res.report["sections_built"]}
        self.assertEqual(fits["dtj-heroes/feature-cards"], "made for this niche")
        self.assertEqual(fits["dtj-heroes/video-reviews"], "made for this niche")
        self.assertEqual(fits["dtj-heroes/hero-banner"], "suits every niche")


class OmissionTests(unittest.TestCase):
    def test_a_section_without_its_facts_is_left_out_with_a_reason_and_nothing_is_invented(self):
        facts = home_facts()
        for key in ("video_reviews", "story", "value_props", "faqs", "trust_points"):
            del facts[key]
        res = build_home(brand("beauty"), facts)
        self.assertEqual([s["kind"] for s in res.report["sections_built"]], ["hero_home"])
        self.assertEqual({o["section"] for o in res.report["sections_omitted"]},
                         {"trust_band_home", "value_props_home", "video_reviews_home", "story_home", "faq", "announcement_bar", "press_home", "categories_home",
                          "best_sellers_home", "before_after_home", "compare_home", "concerns_home", "wave_home"})
        self.assertTrue(all(o["reason"] for o in res.report["sections_omitted"]))
        self.assertEqual(res.report["problems"], [])

    def test_too_few_customer_cards_means_no_video_section(self):
        facts = home_facts()
        facts["video_reviews"]["items"] = facts["video_reviews"]["items"][:3]
        facts["media"] = [m for m in facts["media"] if m["role"] != "c3"]
        res = build_home(brand("beauty"), facts)
        self.assertNotIn("dtj-heroes/video-reviews", blocks(res))
        self.assertIn("video_reviews_home", {o["section"] for o in res.report["sections_omitted"]})

    def test_a_review_appears_in_the_story_only_when_the_facts_have_one(self):
        res = build_home(brand("beauty"), home_facts())
        story = next(b["settings"] for s in res.template["sections"].values() for b in s["blocks"].values() if b["settings"].get("layout") == "split")
        self.assertNotIn("review_quote", story)
        facts = home_facts()
        facts["story"]["review"] = {"quote": "Sample quote", "name": "Sample name", "rating": 4.5, "source": SRC}
        story = next(b["settings"] for s in build_home(brand("beauty"), facts).template["sections"].values() for b in s["blocks"].values() if b["settings"].get("layout") == "split")
        self.assertEqual((story["review_quote"], story["review_stars"]), ("Sample quote", 4.5))

    def test_a_rating_is_shown_only_when_the_facts_have_one(self):
        res = build_home(brand("beauty"), home_facts())
        hero = next(b["settings"] for s in res.template["sections"].values() for b in s["blocks"].values() if b["settings"].get("priority"))
        self.assertEqual(hero["rating_value"] if "rating_value" in hero else 0, 0)
        facts = home_facts()
        facts["rating"] = {"value": "4.5", "text": "Sample rating text", "source": SRC}
        hero = next(b["settings"] for s in build_home(brand("beauty"), facts).template["sections"].values() for b in s["blocks"].values() if b["settings"].get("priority"))
        self.assertEqual(hero["rating_value"], 4.5)

    def test_bad_facts_are_refused_before_anything_is_built(self):
        facts = home_facts()
        facts["hero"]["cta_label"] = ""
        with self.assertRaises(InputError):
            build_home(brand("beauty"), facts)
        with self.assertRaises(InputError):
            build_home(brand("beauty"), {"demo": True})


class PageTests(unittest.TestCase):
    def test_the_template_keeps_the_themes_featured_products_and_ends_with_the_faq(self):
        res = build_home(brand("home-care"), home_facts())
        self.assertIn("product_list_fa6P9H", res.template["sections"])
        self.assertEqual(res.template["order"][-1], "dtj_faq")
        self.assertEqual(set(res.template["order"]), set(res.template["sections"]))
        for sid, sec in res.template["sections"].items():
            if sec["type"] == "_blocks":
                self.assertEqual(sec["settings"]["section_width"], "full-width", sid)  # a band reaches both screen edges

    def test_the_hero_runs_edge_to_edge_and_is_the_first_picture(self):
        res = build_home(brand("beauty"), home_facts())
        first = res.template["sections"][res.template["order"][0]]
        hero = next(iter(first["blocks"].values()))
        self.assertIn("dtj-hero-banner", hero["type"])
        self.assertEqual((hero["settings"]["priority"], hero["settings"]["corner_radius"], hero["settings"]["padding_top"], hero["settings"]["side_padding"]), (True, 0, 0, 0))

    def test_no_button_on_the_home_page_is_an_oval(self):
        for category in ("beauty", "apparel", "food", "home-care"):
            res = build_home(brand(category), home_facts())
            for sec in res.template["sections"].values():
                for b in sec["blocks"].values():
                    self.assertNotEqual(b["settings"].get("button_style"), "pill", category)

    def test_every_block_reference_uses_the_registered_extension_id(self):
        res = build_home(brand("beauty"), home_facts())
        refs = [b["type"] for s in res.template["sections"].values() for b in s["blocks"].values() if str(b["type"]).startswith("shopify://apps/")]
        self.assertTrue(refs)
        self.assertTrue(all(r.startswith("shopify://apps/") and r.count("/") >= 5 for r in refs))
        self.assertTrue(any("dtj-heroes" in r and "01a1304c-d26f-7ac9-aad2-dd5d41d7a942" in r for r in refs))

    def test_it_is_deterministic(self):
        a = build_home(brand("food"), home_facts())
        b = build_home(brand("food"), home_facts())
        self.assertEqual(json.dumps(a.template, sort_keys=True), json.dumps(b.template, sort_keys=True))

    def test_the_accent_words_stay_within_the_pages_budget(self):
        res = build_home(brand("beauty"), home_facts())
        self.assertEqual([f for f in res.report["lint"] if f["rule"] == "L10"], [])

    def test_every_text_has_a_recorded_origin(self):
        res = build_home(brand("beauty"), home_facts())
        self.assertEqual([f for f in res.report["lint"] if f["rule"] in ("L07", "L08", "L09")], [])
        self.assertTrue(res.report["provenance"])

    def test_the_facts_schema_is_a_valid_schema_and_the_recipe_covers_every_niche(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / "page_builder" / "schemas" / "home-facts.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        recipe = json.loads((Path(__file__).resolve().parents[1] / "page_builder" / "recipes" / "home.json").read_text(encoding="utf-8"))
        known = set(niches._tags()["niche_of_category"].values())
        self.assertEqual(set(recipe["hero_layout"]), known)
        self.assertTrue(set(recipe["overrides"]) <= known)



def settings_of(res, block: str) -> dict:
    return next(b["settings"] for s in res.template["sections"].values() for b in s.get("blocks", {}).values() if f"/dtj-{block}/" in str(b["type"]))


def built_kinds(res) -> list[str]:
    return [s["kind"] for s in res.report["sections_built"]]


def omitted(res) -> dict[str, str]:
    return {o["section"]: o["reason"] for o in res.report["sections_omitted"]}


class StoryColourTests(unittest.TestCase):
    def test_the_story_panel_always_has_readable_words_on_either_band(self):
        # 13 Oct 2026: the split story fell back to the block's white words on a pale panel (and a black section) on the Elevate home page
        from provision import style
        for category in ("beauty", "supplements", "home-care", "food", "apparel", "other"):
            for only in (None, {"hero_home", "story_home", "faq"}, {"hero_home", "value_props_home", "story_home", "faq"}):
                res = build_home(brand(category), home_facts(), only=only)
                story = next(s for s in res.model.sections if s.kind == "story_home")
                st = story.settings
                self.assertTrue(st.get("background") and st.get("text_color") and st.get("panel_bg"), (category, only, st))
                self.assertGreaterEqual(style.contrast(st["text_color"], st["panel_bg"]), 4.5, (category, only))
                self.assertEqual([f for f in res.report["lint"] if f["rule"] == "L01"], [], (category, only))


class HeroLayoutTests(unittest.TestCase):
    def test_a_product_shot_hero_can_be_a_split_with_a_dark_readable_panel(self):
        # 14 Oct 2026: a square product photo in a banner put the headline on the pack; the facts can ask for a split instead
        from provision import style
        facts = home_facts()
        facts["hero"]["layout"] = "split"
        multi = next(s for s in build_home(brand("home-care"), facts).model.sections if s.kind == "hero_home")
        self.assertEqual(multi.settings["layout"], "banner")  # Harsh, 14 Oct 2026: a multi-product store always gets the full-image banner
        facts["store_type"] = "single_product"
        res = build_home(brand("home-care"), facts)
        hero = next(s for s in res.model.sections if s.kind == "hero_home")
        story = next(s for s in res.model.sections if s.kind == "story_home")
        self.assertEqual((hero.settings["layout"], hero.settings["image_side"]), ("split", "right"))
        self.assertGreaterEqual(style.contrast(hero.settings["text_color"], hero.settings["panel_bg"]), 4.5)
        self.assertNotEqual(hero.settings["panel_bg"], story.settings["panel_bg"])  # the first screen never looks like the story
        self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [])
        default = next(s for s in build_home(brand("home-care"), home_facts()).model.sections if s.kind == "hero_home")
        self.assertEqual(default.settings["layout"], "banner")  # without the fact the niche decides, as before
        self.assertNotIn("image_side", default.settings)


class VideoCardTests(unittest.TestCase):
    def test_a_customer_card_can_be_a_video_alone(self):
        facts = home_facts()
        for k, it in enumerate(facts["video_reviews"]["items"], 1):
            del it["image_role"]
            it["video"] = f"customer-{k}.mp4"
        res = build_home(brand("home-care"), facts)
        st = next(s for s in res.model.sections if s.kind == "video_reviews_home").settings
        self.assertEqual(st["video_1"], "shopify://files/videos/customer-1.mp4")
        self.assertNotIn("image_1", st)  # the block shows the video's own cover frame
        self.assertEqual(res.report["problems"], [])
        del facts["video_reviews"]["items"][0]["video"]  # neither a picture nor a video: the facts are refused
        with self.assertRaises(InputError):
            build_home(brand("home-care"), facts)


class HeroSlideshowTests(unittest.TestCase):
    def slides_facts(self, n=2):
        facts = home_facts()
        facts["media"] += [{"role": f"banner{k}", "file": f"banner{k}.webp"} for k in (2, 3)]
        facts["hero"]["slides"] = [{"image_role": f"banner{k}", "headline": f"Banner {k} *headline*", "sub": f"Banner {k} line.",
                                    "cta_label": f"Shop banner {k}", "cta_url": f"/collections/c{k}", "source": SRC} for k in (2, 3)][:n - 1]  # n banners in all: the hero's own + n - 1 more
        return facts

    def test_two_or_three_banners_make_the_hero_a_slideshow_with_banner_one_as_the_main_message(self):
        res = build_home(brand("home-care"), self.slides_facts(2))
        hero = next(s for s in res.model.sections if s.kind == "hero_home")
        st = hero.settings
        self.assertEqual(f"{hero.app}/{hero.block}", "dtj-sections-2/slideshow-pro")
        self.assertEqual(st["image_1"], "shopify://shop_images/hero.webp")  # banner 1 = the hero's own picture and words
        self.assertEqual(st["heading_1"], home_facts()["hero"]["headline"])
        self.assertEqual(st["heading_3"] if "heading_3" in st else None, None)
        self.assertEqual((st["heading_2"], st["button_label_2"], st["button_url_2"]), ("Banner 2 headline", "Shop banner 2", "/collections/c2"))
        self.assertNotIn("*", st["heading_2"])  # only banner 1 may use the accent word
        self.assertEqual((st["side_padding"], st["padding_top"], st["corner_radius"]), (0, 0, 0))  # edge to edge
        self.assertGreaterEqual(st["overlay_opacity"], 40)
        self.assertTrue(st["autoplay"])
        self.assertEqual(res.report["problems"], [])
        self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [])
        self.assertEqual(len([k for k in build_home(brand("home-care"), self.slides_facts(3)).model.sections[0].settings if k.startswith("image_") and not k.startswith("image_mobile")]), 3)

    def test_one_banner_or_missing_banner_pictures_keep_the_single_full_image_banner(self):
        self.assertEqual(next(s for s in build_home(brand("home-care"), home_facts()).model.sections if s.kind == "hero_home").block, "hero-banner")
        facts = self.slides_facts(2)
        facts["media"] = [m for m in facts["media"] if m["role"] != "banner2"]  # banner 2 has no picture: left out
        hero = next(s for s in build_home(brand("home-care"), facts).model.sections if s.kind == "hero_home")
        self.assertEqual(hero.block, "hero-banner")


class MethodTests(unittest.TestCase):
    """The product-page method applied to the home page (14 Oct 2026)."""

    def test_the_reasons_section_carries_its_own_button_and_the_tabs_are_pills(self):
        facts = home_facts()
        facts["value_props"].update(cta_label="Shop no-scrub cleaning", cta_url="/collections/bathroom-care")
        res = build_home(brand("home-care"), facts)
        st = next(s for s in res.model.sections if s.kind == "value_props_home").settings
        self.assertEqual((st["button_label"], st["button_url"]), ("Shop no-scrub cleaning", "/collections/bathroom-care"))
        self.assertEqual(settings_of(build_home(brand("beauty"), full_facts()), "best-sellers")["tab_style"], "pill")
        self.assertEqual(settings_of(build_home(brand("beauty"), full_facts()), "best-sellers")["add_label"], "Add to cart")

    def test_a_block_without_accent_words_never_shows_the_asterisks(self):
        facts = home_facts()
        facts["value_props"]["heading"] = "All of the foam. *None of the scrubbing.*"  # 14 Oct 2026: the tiles printed the marks
        for category in ("home-care", "beauty"):  # feature-tiles and feature-cards
            res = build_home(brand(category), facts)
            st = next(s for s in res.model.sections if s.kind == "value_props_home").settings
            self.assertEqual(st["heading"], "All of the foam. None of the scrubbing.", category)

    def test_the_slideshow_hero_keeps_its_pictures_whole(self):
        facts = home_facts()
        facts["media"].append({"role": "banner2", "file": "banner2.webp"})
        facts["hero"]["slides"] = [{"image_role": "banner2", "headline": "Banner two", "cta_label": "Shop banner two", "source": SRC}]
        st = next(s for s in build_home(brand("home-care"), facts).model.sections if s.kind == "hero_home").settings
        self.assertEqual((st["ratio_desktop"], st["ratio_mobile"]), ("adapt", "adapt"))

    def test_the_slideshow_hero_puts_the_words_on_a_tall_phone_picture_and_uses_a_phone_picture_when_given(self):
        facts = home_facts()
        facts["media"] += [{"role": "hero_phone", "file": "hero_phone.webp"}, {"role": "banner2", "file": "banner2.webp"},
                           {"role": "banner2_phone", "file": "banner2_phone.webp"}]
        facts["hero"]["image_mobile_role"] = "hero_phone"
        facts["hero"]["slides"] = [{"image_role": "banner2", "image_mobile_role": "banner2_phone", "headline": "Banner two",
                                    "cta_label": "Shop banner two", "source": SRC}]
        res = build_home(brand("home-care"), facts)
        st = next(s for s in res.model.sections if s.kind == "hero_home").settings
        self.assertEqual(st["mobile_layout"], "overlay")
        self.assertEqual(st["desktop_max_height"], 70)  # a tall collage must not fill the whole desktop screen
        self.assertEqual(st["image_mobile_1"], "shopify://shop_images/hero_phone.webp")
        self.assertEqual(st["image_mobile_2"], "shopify://shop_images/banner2_phone.webp")
        self.assertEqual(res.report["problems"], [])
        facts["hero"].pop("image_mobile_role")
        facts["hero"]["slides"][0].pop("image_mobile_role")
        st = next(s for s in build_home(brand("home-care"), facts).model.sections if s.kind == "hero_home").settings
        self.assertEqual(st["mobile_layout"], "overlay")
        self.assertNotIn("image_mobile_1", st)  # no phone picture: the main one is cropped tall by the block


class PaletteMethodTests(unittest.TestCase):
    """The researched palette method (palette.py, 19 Oct 2026): opt-in with brand.palette = "ramps"."""

    def test_every_role_pair_reads_and_every_button_stands_apart_from_its_background(self):
        from page_builder import palette
        r = palette.roles("#0B66B2", "#00B84C", "home-care")
        for fg, bg in (("text", "bg"), ("muted", "bg"), ("text", "band"), ("accent", "bg"), ("accent_on_band", "band"), ("on_dark", "dark"),
                       ("accent_on_dark", "dark"), ("button_text", "button_bg"), ("band_button_text", "band_button_bg"), ("on_accent", "accent_fill"),
                       ("accent_on_fill", "accent_fill"), ("fill_button_text", "fill_button_bg"), ("dark_button_text", "dark_button_bg")):
            self.assertGreaterEqual(palette.contrast(r[fg], r[bg]), 4.5, (fg, bg))
        for button, bg in (("button_bg", "bg"), ("band_button_bg", "band"), ("fill_button_bg", "accent_fill"), ("dark_button_bg", "dark")):
            self.assertGreaterEqual(palette.contrast(r[button], r[bg]), 3.0, (button, bg))
        self.assertEqual(len(r["_ramps"]["brand"]), 12)
        self.assertNotEqual(r["border"], "#DBDEE0")  # greys carry the brand's hue
        self.assertEqual(r["_warnings"], [])

    def test_a_cleaning_brand_is_warned_off_yellow(self):
        from page_builder import palette  # Harsh, 19 Oct 2026: "yellow also represents stains"
        self.assertTrue(palette.roles("#0B66B2", "#FFD23F", "home-care")["_warnings"])
        self.assertFalse(palette.roles("#0B66B2", "#FFD23F", "food")["_warnings"])

    def test_the_method_gives_one_solid_brand_band_with_readable_white_tiles_and_leaves_other_brands_alone(self):
        b = brand("home-care")
        b["colors"] = {"primary": "#0B66B2", "accent": "#00B84C", "background": "#FFFFFF", "text": "#10202D"}
        b["palette"] = "ramps"
        res = build_home(b, home_facts())
        self.assertTrue(res.model.direction.ramps)
        self.assertEqual(res.model.direction.failed_checks(), [])
        self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [])
        values = next(s for s in res.model.sections if s.kind == "value_props_home")
        self.assertEqual(res.model.roles[values.id], "accent")
        st = values.settings
        self.assertEqual((st["background"], st["tile_bg"], st["button_bg"]), ("#0B66B2", "#FFFFFF", "#FFFFFF"))
        plain = build_home(brand("home-care"), home_facts())  # no palette option: the approved looks stay exactly as they were
        self.assertFalse(plain.model.direction.ramps)
        self.assertNotEqual(plain.model.roles[next(s for s in plain.model.sections if s.kind == "value_props_home").id], "accent")

    def test_a_mint_band_from_the_accent_family_breaks_up_the_blue_and_every_pair_on_it_reads(self):
        from page_builder import palette  # Harsh, 19 Oct 2026: "apply better colors ... like a top level figma designer": not one pale blue four times
        r = palette.roles("#0B66B2", "#00B84C", "home-care")
        self.assertNotEqual(r["mint"], r["band"])
        self.assertGreaterEqual(palette.contrast(r["text"], r["mint"]), 4.5)
        self.assertGreaterEqual(palette.contrast(r["accent_on_mint"], r["mint"]), 4.5)
        self.assertGreater(palette.oklch(r["mint"])[0], 0.9)  # still a SOFT band: the white-share of the page stays high

    def test_the_method_paces_the_page_and_neighbours_never_share_a_colour(self):
        b = brand("home-care")
        b["colors"] = {"primary": "#0B66B2", "accent": "#00B84C", "background": "#FFFFFF", "text": "#10202D"}
        b["palette"] = "ramps"
        res = build_home(b, home_facts())
        by_kind = {s.kind: res.model.roles[s.id] for s in res.model.sections}
        for kind, want in (("categories_home", "plain"), ("best_sellers_home", "band"), ("value_props_home", "accent")):
            if kind in by_kind:
                self.assertEqual(by_kind[kind], want, kind)
        self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [])  # L04: neighbours never share a background
        self.assertLessEqual(sum(1 for v in by_kind.values() if v == "dark"), res.model.direction.max_dark)

    def test_the_hero_keeps_harshs_phone_settings_in_both_forms(self):
        banner = next(s for s in build_home(brand("home-care"), home_facts()).model.sections if s.kind == "hero_home").settings
        self.assertEqual((banner["mobile_layout"], banner["mobile_align"]), ("overlay", "left"))
        facts = home_facts()
        facts["media"].append({"role": "banner2", "file": "banner2.webp"})
        facts["hero"]["slides"] = [{"image_role": "banner2", "headline": "Banner two", "cta_label": "Shop banner two", "source": SRC}]
        slides = next(s for s in build_home(brand("home-care"), facts).model.sections if s.kind == "hero_home").settings
        self.assertEqual((slides["mobile_layout"], slides["mobile_align"]), ("overlay", "left"))


class NewBlockTests(unittest.TestCase):
    """The DTJ Commerce, DTJ Shop and comparison blocks wired on 13 Oct 2026: real facts in, nothing invented, every setting valid."""

    def test_the_category_layout_follows_the_niche_and_the_number_of_categories(self):
        want = {"beauty": ("circle-menu", "variation", "ring"), "supplements": ("circle-menu", "variation", "circle"),
                # 4 categories: the grid (3 a row on desktop) would leave one alone, so home and general take the next block
                "home-care": ("circle-menu", "variation", "square"), "other": ("circle-menu", "variation", "square"),
                "apparel": ("circle-menu", "variation", "ring"), "food": ("category-slider", "shape", "round")}
        for category, (block, key, value) in want.items():
            res = build_home(brand(category), full_facts())
            self.assertIn(f"dtj-commerce/{block}", blocks(res), category)
            self.assertEqual(settings_of(res, block)[key], value, category)
            self.assertEqual(settings_of(res, block)["collections"], ["face", "body", "hair", "kits"], category)
        facts = full_facts()
        facts["categories"]["items"] = facts["categories"]["items"][:3]
        self.assertIn("dtj-commerce/circle-menu", blocks(build_home(brand("food"), facts)))  # the slider needs 4: the next layout is used
        self.assertEqual(settings_of(build_home(brand("home-care"), facts), "category-grid")["layout"], "even")  # 3 fill one grid row
        self.assertEqual(settings_of(build_home(brand("home-care"), full_facts()), "circle-menu")["mobile_layout"], "scroll")  # 4: one row to swipe
        menu = settings_of(build_home(brand("home-care"), full_facts()), "circle-menu")
        self.assertLessEqual((menu["heading_size_desktop"], menu["heading_size_mobile"]), (28, 22))  # a quiet heading over small tiles
        facts = full_facts()
        facts["categories"]["items"].append({"collection": "gifts", "source": SRC})
        self.assertEqual(settings_of(build_home(brand("home-care"), facts), "category-grid")["layout"], "bento_left")  # the big layout needs exactly 5

    def test_the_collection_blocks_name_nothing_themselves(self):
        res = build_home(brand("beauty"), full_facts())
        best = settings_of(res, "best-sellers")
        self.assertEqual(best["collections"], ["face", "body"])
        self.assertEqual((best["tab_1"], best["tab_2"]), ("Face", "Body"))
        self.assertNotIn("best", best["heading"].lower())  # "best sellers" is a sales claim: only the facts may say it
        self.assertTrue(best["show_rating"])  # the block shows a rating only from real reviews
        self.assertEqual(omitted(res)["theme:product_list"], "best_sellers_home already shows the shop's products")
        rings = settings_of(res, "circle-menu")
        self.assertFalse([k for k in rings if k.startswith("title_")])  # each tile shows its collection's own name
        concern = settings_of(res, "concern-slider")
        self.assertEqual((concern["collections"], concern["concern_1"], concern["concern_2"]), (["acne", "dry-skin"], "Acne", "Dry skin"))

    def test_the_top_strip_uses_the_stores_own_facts_with_matching_icons(self):
        res = build_home(brand("beauty"), full_facts())
        strip = settings_of(res, "marquee-band")
        self.assertEqual(strip["variation"], "bold")
        self.assertEqual((strip["icon_1"], strip["icon_2"], strip["icon_3"]), ("truck", "return", "shield"))
        self.assertEqual(res.template["order"][0], "home_announce")
        facts = full_facts()
        facts["announcements"]["items"][0]["icon"] = "gift"
        self.assertEqual(settings_of(build_home(brand("beauty"), facts), "marquee-band")["icon_1"], "gift")

    def test_press_logos_need_their_pictures_and_every_mention_needs_its_article(self):
        res = build_home(brand("beauty"), full_facts())
        press = settings_of(res, "press-strip")
        self.assertEqual((press["link_1"], press["name_1"]), ("https://example.com/a1", "Paper 1"))
        self.assertEqual(len(res.report["evidence"]["home_press"]), 3)
        facts = full_facts()
        del facts["press"]["items"][0]["url"]
        with self.assertRaises(InputError):  # a mention without its article is refused before anything is built
            build_home(brand("beauty"), facts)
        facts = full_facts()
        facts["media"] = [m for m in facts["media"] if m["role"] != "p3"]
        self.assertIn("logo picture", omitted(build_home(brand("beauty"), facts))["press_home"])

    def test_a_comparison_is_built_only_with_the_owners_approval(self):
        facts = full_facts()
        facts["compare"]["claims_approved"] = False
        res = build_home(brand("home-care"), facts)
        self.assertNotIn("dtj-heroes/compare-showcase", blocks(res))
        self.assertIn("owner's approval", omitted(res)["compare_home"])
        res = build_home(brand("home-care"), full_facts())
        cmp = settings_of(res, "compare-showcase")
        self.assertEqual((cmp["r1_label"], cmp["us_title"], cmp["them_title"]), ("Row 1", brand("home-care")["brand_name"], "Others"))
        self.assertNotIn("r1_us", cmp)  # an empty cell shows the block's tick: nothing typed for it
        self.assertIn("approved by the owner", res.report["evidence"]["home_compare"][0])

    def test_two_columns_of_sentences_become_the_reference_comparison_table(self):
        # Harsh, 20 Oct 2026: the tick/cross comparison "looks very immature"; he wants the Super Senior pack's table as it is: a tall tinted column with the
        # brand name and picture, the other column beside it, a sentence in each cell, thin divider lines. Rows without a label are that table.
        facts = full_facts()
        facts["media"] += [{"role": "cmp_them", "file": "cmp_them.webp"}]
        facts["compare"]["them_image_role"] = "cmp_them"
        facts["compare"]["rows"] = [{"us": f"Our sentence {i}", "them": f"Their sentence {i}"} for i in range(1, 5)]
        res = build_home(brand("home-care"), facts)
        self.assertNotIn("dtj-heroes/compare-showcase", blocks(res))
        table = settings_of(res, "comparison-table")
        self.assertEqual((table["our_text_1"], table["other_text_1"], table["our_text_4"], table["other_text_4"]),
                         ("Our sentence 1", "Their sentence 1", "Our sentence 4", "Their sentence 4"))
        self.assertEqual((table["brand_label"], table["other_label"]), (brand("home-care")["brand_name"], "Others"))
        self.assertTrue(table["heading"].startswith("Why ") and "outperforms" in table["heading"])
        self.assertIn("our_brand_image", table)
        self.assertIn("other_brand_image", table)
        self.assertNotIn("review_text", table)  # the pack's star line carries only a REAL rating: never built here
        self.assertNotIn("show_stars", table)
        self.assertIn("approved by the owner", res.report["evidence"]["home_compare"][0])
        self.assertEqual(res.report["problems"], [])

    def test_a_before_and_after_needs_both_photos_and_the_persons_permission(self):
        facts = full_facts()
        del facts["before_after"]["consent"]
        with self.assertRaises(InputError):
            build_home(brand("beauty"), facts)
        facts = full_facts()
        facts["media"] = [m for m in facts["media"] if m["role"] != "after"]
        self.assertIn("before or the after", omitted(build_home(brand("beauty"), facts))["before_after_home"])
        res = build_home(brand("beauty"), full_facts())
        ba = settings_of(res, "before-after")
        self.assertFalse(ba["show_stars"])  # five stars would claim reviews
        self.assertEqual(ba["variation"], "circle")
        self.assertIn("permission", res.report["evidence"]["home_before_after"][0])

    def test_the_wave_takes_its_colours_from_its_neighbours_and_goes_when_there_is_no_edge(self):
        res = build_home(brand("beauty"), full_facts())
        order = res.template["order"]
        i = order.index("home_wave")
        wave = settings_of(res, "wave-divider")
        below = next(iter(res.template["sections"][order[i + 1]]["blocks"].values()))["settings"].get("background")
        self.assertEqual(wave["wave_color"], below or res.report["direction"]["roles"]["bg"])  # no band below: the page's own colour
        self.assertNotEqual(wave["background"].upper(), wave["wave_color"].upper())
        self.assertFalse(wave["animate"])
        facts = {"demo": True, "media": home_facts()["media"] + [{"role": "before", "file": "b.webp"}, {"role": "after", "file": "a.webp"}],
                 "hero": home_facts()["hero"], "before_after": full_facts()["before_after"]}
        res = build_home(brand("beauty"), facts)
        self.assertEqual(omitted(res)["wave_home"], "nothing follows it on this page")
        self.assertNotIn("home_wave", res.template["order"])

    def test_no_button_shape_is_an_oval_and_each_button_has_its_own_label(self):
        for category in ("beauty", "apparel", "home-care"):
            res = build_home(brand(category), full_facts())
            for sec in res.template["sections"].values():
                for b in sec.get("blocks", {}).values():
                    self.assertNotIn(b["settings"].get("button_shape"), ("pill",), category)
            self.assertEqual([f for f in res.report["lint"] if f["rule"] == "L16"], [], category)


if __name__ == "__main__":
    unittest.main()

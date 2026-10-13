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
            res = build_home(brand(category), home_facts())
            self.assertEqual(res.report["problems"], [], category)
            self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [], category)
            self.assertEqual(res.report["sections_omitted"], [], category)

    def test_the_order_and_the_hero_layout_follow_the_niche(self):
        beauty = build_home(brand("beauty"), home_facts())
        fashion = build_home(brand("apparel"), home_facts())
        self.assertEqual(beauty.report["niche"], "beauty")
        self.assertEqual(fashion.report["niche"], "fashion")
        kinds = lambda r: [s["kind"] for s in r.report["sections_built"]]  # noqa: E731
        self.assertEqual(kinds(beauty)[:3], ["hero_home", "trust_marquee", "value_props_home"])  # beauty: trust and reasons first
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
        self.assertEqual({o["section"] for o in res.report["sections_omitted"]}, {"trust_marquee", "value_props_home", "video_reviews_home", "story_home", "faq"})
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


if __name__ == "__main__":
    unittest.main()

"""Tests for the page builder: the design judgment as checks (adaptation to a brand, contrast, rhythm, provenance, omission instead of invention,
the copy contract)."""
import copy
import json
import unittest

from page_builder import copy_contract, rules, styling
from page_builder.assemble import InputError, build_pdp
from page_builder.catalog import Catalog
from page_builder.direction import derive
from provision.style import contrast as style_contrast
from page_builder.examples import fixtures


def build(name=None, **mods):
    brand, facts = fixtures.toilova() if name is None else (copy.deepcopy(fixtures.BRANDS[name][0]), copy.deepcopy(fixtures.BRANDS[name][1]))
    for path, value in mods.items():
        target = facts
        keys = path.split("__")
        for k in keys[:-1]:
            target = target[k]
        if value is None:
            target.pop(keys[-1], None)
        else:
            target[keys[-1]] = value
    return build_pdp(brand, facts)


def errors(result):
    return [f for f in result.report["lint"] if f["severity"] == "error"]


class ToilovaPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = build()

    def test_builds_clean_with_no_problem_and_no_error(self):
        self.assertEqual(self.r.report["problems"], [])
        self.assertEqual(errors(self.r), [])
        self.assertTrue(self.r.ok)

    def test_sections_follow_the_home_care_recipe_in_order(self):
        built = [s["kind"] for s in self.r.report["sections_built"]]
        self.assertEqual(built, ["trust_marquee", "why_features", "facts_glance", "story_split", "how_split", "free_from", "pack_inside", "faq"])

    def test_missing_facts_omit_a_section_with_a_reason_instead_of_inventing(self):
        omitted = {o["section"]: o["reason"] for o in self.r.report["sections_omitted"]}
        self.assertIn("reviews_slider", omitted)
        self.assertIn("REAL reviews", omitted["reviews_slider"])
        self.assertIn("approval", omitted["comparison"])
        self.assertNotIn("dtj-testimonials-slider", json.dumps(self.r.template))
        self.assertNotIn("dtj-social-proof", json.dumps(self.r.template))  # no real rating: no stars

    def test_every_text_has_a_recorded_origin(self):
        prov = self.r.report["provenance"]
        self.assertGreater(len(prov), 40)
        self.assertTrue(all(v["kind"] in ("fact", "structure", "demo", "copy") for v in prov.values()))
        self.assertEqual({v["kind"] for v in prov.values()} - {"fact", "structure"}, set())

    def test_the_buy_box_has_the_live_price_and_no_second_theme_price(self):
        details = self.r.template["sections"]["main"]["blocks"]["product-details"]
        types = [b["type"] for b in details["blocks"].values()]
        self.assertEqual(sum("/dtj-price/" in t for t in types), 1)
        self.assertNotIn("price_tVjtKg", details["blocks"]["group_icgrde"]["blocks"])
        order = details["block_order"]
        self.assertLess(order.index("group_icgrde"), order.index("dtj_blocks_price_dtj_price"))
        self.assertLess(order.index("dtj_blocks_price_dtj_price"), order.index("buy_buttons_eYQEYi"))

    def test_every_section_is_full_width_and_keeps_side_space(self):
        for sid in self.r.template["order"][1:]:
            self.assertEqual(self.r.template["sections"][sid]["settings"]["section_width"], "full-width")
        for sec in self.r.model.sections:
            if Catalog().has(sec.app, sec.block, "side_padding"):
                self.assertGreaterEqual(sec.settings["side_padding"], 12)

    def test_bands_alternate_and_only_the_signature_section_is_dark(self):
        roles = [self.r.model.roles[s.id] for s in self.r.model.sections]
        self.assertEqual([r for r in roles if r == "dark"], ["dark"])
        self.assertEqual([s.kind for s in self.r.model.sections if self.r.model.roles[s.id] == "dark"], ["free_from"])
        backgrounds = [s.settings.get("background") for s in self.r.model.sections if self.r.model.roles[s.id] != "none"]
        for a, b in zip(backgrounds, backgrounds[1:]):
            self.assertFalse(a and a == b)

    def test_the_same_input_always_gives_the_same_page(self):
        self.assertEqual(json.dumps(build().template, sort_keys=True), json.dumps(self.r.template, sort_keys=True))

    def test_every_setting_exists_in_the_real_block_definitions(self):
        cat = Catalog()
        for sec in self.r.model.sections + self.r.model.buybox_sections:
            self.assertEqual(cat.validate(sec.app, sec.block, sec.settings), [], sec.id)

    def test_accent_words_stay_within_the_budget(self):
        count = 0
        for sec in self.r.model.sections:
            count += sum(1 for k in ("heading_accent", "highlight_word") if sec.settings.get(k))
        self.assertLessEqual(count, self.r.model.direction.type["accent_words_max"])


class AdaptationTests(unittest.TestCase):
    def test_different_brands_get_different_directions(self):
        dirs = {name: build(name).report["direction"] for name in fixtures.BRANDS}
        self.assertEqual(len({d["shape"]["name"] for d in dirs.values()}), 3)   # sharp, soft, round all appear
        self.assertGreaterEqual(len({d["signature"] for d in dirs.values()}), 3)
        looks = {(d["type"]["heading_font"], d["type"]["accent_font"], d["type"]["eyebrow_style"], d["shape"]["name"]) for d in dirs.values()}
        self.assertEqual(len(looks), 4)  # no two brands share the same type-and-shape treatment
        self.assertEqual(len({d["roles"]["accent"] for d in dirs.values()}), 4)  # four brand colours, four accents
        self.assertEqual({dirs["aurelia"]["motion"]["transition"], dirs["zestly"]["motion"]["transition"]}, {"fade", "slide"})

    def test_every_brand_builds_a_valid_page_with_passing_contrast(self):
        for name in fixtures.BRANDS:
            r = build(name)
            self.assertEqual(r.report["problems"], [], name)
            self.assertEqual(errors(r), [], name)
            self.assertEqual(r.model.direction.failed_checks(), [], name)

    def test_a_dark_brand_gets_a_dark_page_with_readable_text(self):
        d = derive(fixtures.BRANDS["nocturne"][0])
        self.assertTrue(d.dark_mode)
        self.assertGreaterEqual(__import__("provision.style", fromlist=["x"]).contrast(d.roles["text"], d.roles["bg"]), 7)
        self.assertEqual(d.shape["name"], "sharp")

    def test_the_emphasised_section_follows_the_category(self):
        self.assertEqual(build("voltra").report["direction"]["signature"], "proof_panel")
        self.assertIn("proof_panel", [s["kind"] for s in build("voltra").report["sections_built"]])
        self.assertNotIn("facts_glance", [s["kind"] for s in build("voltra").report["sections_built"]])
        self.assertIn("facts_glance", [s["kind"] for s in build("aurelia").report["sections_built"]])

    def test_premium_brands_get_more_air_and_a_stricter_accent_budget(self):
        premium, value = derive(fixtures.BRANDS["aurelia"][0]), derive(fixtures.BRANDS["zestly"][0])
        self.assertGreater(premium.density["section"], value.density["section"])
        self.assertEqual(premium.type["accent_words_max"], 1)
        self.assertEqual(value.type["accent_words_max"], 2)

    def test_a_low_contrast_brand_colour_is_adjusted_and_reported(self):
        brand = {"brand_name": "Sunny", "category": "food", "colors": {"primary": "#FFE066", "background": "#FFFFFF", "text": "#222222"}}
        d = derive(brand)
        self.assertEqual(d.failed_checks(), [])
        self.assertNotEqual(d.roles["accent"], "#FFE066")

    def test_a_brand_with_no_colours_gets_defaults_and_a_warning(self):
        d = derive({"brand_name": "Plain", "category": "other"})
        self.assertTrue(any("not provided" in w for w in d.warnings))
        self.assertEqual(d.failed_checks(), [])


class FigureCardTests(unittest.TestCase):
    """Found 9 Oct 2026 on a book page: figure cards without notes printed the internal source as the caption, in a 4.21:1 grey."""

    KF = [{"value": "2,00,000+", "label": "Copies sold", "source": "product description (current figure confirmed by Harsh)"},
          {"value": "4.9", "label": "Rating", "source": "product description"},
          {"value": "2–3", "label": "Sittings to finish", "source": "product description", "note": "From the product description"}]

    def cards(self):
        r = build(key_facts=copy.deepcopy(self.KF))
        return r, next(s for s in r.model.sections if s.block == "stat-cards")

    def test_a_source_is_never_printed_as_a_caption(self):
        r, sec = self.cards()
        self.assertNotIn("note_1", sec.settings)
        self.assertNotIn("note_2", sec.settings)
        self.assertEqual(sec.settings["note_3"], "From the product description")
        page = json.dumps(r.template)
        self.assertNotIn("confirmed by Harsh", page)

    def test_card_captions_use_a_colour_checked_on_the_card(self):
        r, sec = self.cards()
        roles = r.model.direction.roles
        self.assertEqual(sec.settings["note_color"], roles["muted_on_card"])
        self.assertEqual(sec.settings["label_color"], roles["on_card"])
        for name in fixtures.BRANDS:
            check = next(c for c in derive(fixtures.BRANDS[name][0]).checks if c["pair"] == "soft text on cards")
            self.assertTrue(check["ok"], (name, check))


class SocialProofLineTests(unittest.TestCase):
    """The line above the title (Harsh, 9 Oct 2026: 'in the rating star add the images and the badges')."""

    SP = {"badge": {"text": "2 Lakh+ Sold", "source": "product description"},
          "lines": [{"text": "a short proof line", "source": "product description"}],
          "avatars": [{"role": f"reader_{i}", "consent": "reader agreed on Instagram DM, 9 Oct 2026"} for i in range(1, 6)]}

    def stars(self, result):
        return next(s for s in result.model.buybox_sections if s.kind == "rating")

    def facts(self):
        _, f = fixtures.toilova()
        f["media"] += [{"role": f"reader_{i}", "file": f"reader-{i}.webp"} for i in range(1, 6)]
        f["rating"] = {"value": "4.9", "source": "product description"}
        f["social_proof"] = copy.deepcopy(self.SP)
        return f

    def test_badge_lines_and_consented_photos_come_from_the_facts(self):
        b, _ = fixtures.toilova()
        r = build_pdp(b, self.facts())
        s = self.stars(r)
        self.assertEqual((s.settings["badge_text"], s.settings["proof_text_1"], s.settings["rating_style"]),
                         ("2 Lakh+ Sold", "a short proof line", "five"))
        self.assertTrue(s.settings["avatar_1"].endswith("reader-1.webp"))
        self.assertTrue(s.settings["avatar_5"].endswith("reader-5.webp"))
        self.assertEqual(r.model.prov[(s.id, "badge_text")]["kind"], "fact")
        self.assertEqual(errors(r), [])

    def test_the_rating_line_shows_five_photos_or_none(self):
        b, _ = fixtures.toilova()
        f = self.facts()
        f["social_proof"]["avatars"] = f["social_proof"]["avatars"][:3]
        self.assertIn("L14", [x["rule"] for x in errors(build_pdp(b, f))])  # three real photos: the page fails, nothing is padded
        f["social_proof"]["avatars"] = []
        self.assertNotIn("L14", [x["rule"] for x in errors(build_pdp(b, f))])

    def test_a_badge_is_two_or_three_words(self):
        b, _ = fixtures.toilova()
        for text, ok in (("2 Lakh+ Sold", True), ("Made in India", True), ("Bestseller", False), ("National Bestseller", True), ("2,00,000+ copies sold", False),
                         ("Over 2,00,000 copies sold", False)):
            f = self.facts()
            f["social_proof"]["badge"]["text"] = text
            self.assertEqual("L15" not in [x["rule"] for x in errors(build_pdp(b, f))], ok, text)

    def test_a_customer_photo_needs_a_consent_note(self):
        b, _ = fixtures.toilova()
        f = self.facts()
        del f["social_proof"]["avatars"][0]["consent"]
        with self.assertRaises(InputError):
            build_pdp(b, f)

    def test_without_social_proof_the_line_stays_a_compact_rating(self):
        b, _ = fixtures.toilova()
        f = self.facts()
        del f["social_proof"]
        s = self.stars(build_pdp(b, f))
        self.assertEqual(s.settings["rating_style"], "single")
        self.assertNotIn("badge_text", s.settings)
        f["social_proof"] = {"badge": {"text": "National Bestseller", "source": "product description"}}
        del f["rating"]
        s = self.stars(build_pdp(b, f))
        self.assertFalse(s.settings["show_stars"])  # no rating fact: no stars, only the badge
        self.assertNotIn("rating_value", s.settings)


class HarshFeedbackTests(unittest.TestCase):
    """Harsh's notes on the live book page, 9 Oct 2026."""

    def test_the_trust_strip_is_big_and_never_touches_the_pictures(self):
        s = next(x for x in build().model.sections if x.block == "marquee")
        self.assertEqual((s.settings["padding_top"], s.settings["padding_bottom"]), (styling.MARQUEE["padding"],) * 2)
        self.assertGreaterEqual(s.settings["padding_top"], 16)
        self.assertEqual((s.settings["text_size"], s.settings["icon_size"], s.settings["gap"]),
                         (styling.MARQUEE["text"], styling.MARQUEE["icon"], styling.MARQUEE["gap"]))
        self.assertGreater(s.settings["text_size"], 14)  # bigger than the block's default

    def test_pictures_keep_their_own_shape(self):
        r = build()
        story = next(x for x in r.model.sections if x.block == "split-story")
        self.assertEqual(story.settings["image_fit"], "adapt")
        stats = next(x for x in r.model.sections if x.block == "science-stats")  # TOILOVA's figures all have pictures
        self.assertEqual(stats.settings["card_image_aspect_ratio"], "adapt")

    def test_tick_lists_have_exactly_four_points(self):
        r = build(buybox__bullets=["One real point", "Two real points"])
        pts = next(x for x in r.model.buybox_sections if x.kind == "hero_points")
        lines = pts.settings["benefits"].splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[:2], ["One real point", "Two real points"])  # the buy box's own first, then benefit titles
        self.assertEqual(lines[2], "No scrubbing needed")
        self.assertNotIn("L13", [f["rule"] for f in errors(r)])
        _, f = fixtures.toilova()
        r = build(story__bullets=f["story"]["bullets"][:3])
        self.assertIn("L13", [x["rule"] for x in errors(r)])  # three real points: the page fails, nothing is invented
        r = build(story__bullets=f["story"]["bullets"] + ["Fifth point"])
        story = next(x for x in r.model.sections if x.block == "split-story")
        self.assertEqual(sorted(k for k in story.settings if k.startswith("bullet_")), ["bullet_1", "bullet_2", "bullet_3", "bullet_4"])


class DemoPictureTests(unittest.TestCase):
    """A dev-store test: every empty picture slot gets one of the product's own pictures, and each is listed for replacement."""

    def page(self, demo):
        b, f = fixtures.toilova()
        f["demo"] = demo
        f["rating"] = {"value": "4.9", "source": "test"}
        f["social_proof"] = {"lines": [{"text": "from 2,000+ readers", "source": "test"}]}
        for item in f["pack_contents"]:
            item.pop("image_role", None)
        return build_pdp(b, f)

    def test_empty_pictures_are_filled_and_listed_only_on_a_demo_page(self):
        r = self.page(True)
        pics = r.report["demo_pictures"]
        self.assertIn("dtj_inside.image_1", pics)
        self.assertIn("dtj_inside.image_2", pics)
        self.assertNotIn("dtj_inside.image_3", pics)  # TOILOVA's pack has 2 items: no third picture
        self.assertEqual([p for p in pics if p.startswith("dtj_stars.")], [f"dtj_stars.avatar_{i}" for i in range(1, 6)])
        self.assertFalse([p for p in pics if "icon" in p or p.startswith(("dtj_marquee.", "dtj_why.f"))])  # icon slots keep icons
        self.assertEqual(r.report["needs_replacement"][-len(pics):], pics)
        self.assertEqual(errors(r), [])
        self.assertEqual(self.page(False).report["demo_pictures"], [])

    def test_test_pictures_without_the_demo_flag_are_an_error(self):
        r = self.page(True)
        r.model.demo = False
        self.assertIn("L09", [f.rule for f in rules.lint(r.model)])


DAWN = {  # the shape of Harsh's Dawn 15.4.1 product.json (9 Oct 2026), including a custom block the page must keep
    "sections": {
        "main": {"type": "main-product", "settings": {}, "block_order": ["text", "title", "price", "variant_picker", "buy_buttons", "bundle_upsell", "description"],
                 "blocks": {k: {"type": k, "settings": {}} for k in ("text", "title", "price", "variant_picker", "buy_buttons", "bundle_upsell", "description")}},
        "related-products": {"type": "related-products", "settings": {}},
    },
    "order": ["main", "related-products"],
}


class DawnLayoutTests(unittest.TestCase):
    """Harsh, 9 Oct 2026: "create the same page ... in this theme" (a Dawn theme)."""

    def page(self):
        b, f = fixtures.toilova()
        f["rating"] = {"value": "4.9", "source": "test"}
        return build_pdp(b, f, theme="dawn", base_template=copy.deepcopy(DAWN))

    def test_the_buy_box_goes_into_dawns_product_section(self):
        r = self.page()
        main = r.template["sections"]["main"]
        order = main["block_order"]
        kinds = [main["blocks"][k]["type"].split("/blocks/")[-1].split("/")[0] if "/blocks/" in main["blocks"][k]["type"] else main["blocks"][k]["type"] for k in order]
        self.assertEqual(kinds, ["text", "dtj-social-proof", "title", "dtj-price", "dtj-hero-points", "variant_picker", "buy_buttons", "bundle_upsell", "description"])
        self.assertNotIn("price", main["blocks"])  # the DTJ price replaces the theme's
        self.assertEqual(errors(r), [])

    def test_sections_are_dawn_apps_sections_above_the_themes_own(self):
        r = self.page()
        t = r.template
        ours = [s["id"] for s in r.report["sections_built"]]
        self.assertEqual(t["order"], ["main", *ours, "related-products"])
        for sid in ours:
            self.assertEqual((t["sections"][sid]["type"], t["sections"][sid]["settings"]), ("apps", {"include_margins": False}))

    def test_the_preview_renders_a_dawn_page(self):
        from page_builder import render
        html, notes = render.page_html(self.page())
        self.assertIn('data-pb-dtj="dtj-blocks/price"', html)
        self.assertIn("theme title", notes["stand_ins"])

    def test_dawn_needs_its_own_product_template(self):
        b, f = fixtures.toilova()
        with self.assertRaises(InputError):
            build_pdp(b, f, theme="dawn")
        with self.assertRaises(InputError):
            build_pdp(b, f, theme="debut")


class ClientRegistryTests(unittest.TestCase):
    CLIENT = {"dtj-blocks": {"handle": "dtj-blocks-test-store", "uuid": "a" * 8 + "-0000-7000-8000-" + "b" * 12},
              "dtj-sections": {"handle": "dtj-sections-test-store", "uuid": "c" * 8 + "-0000-7000-8000-" + "d" * 12},
              "dtj-sections-2": {"handle": "dtj-sections-2-test-store", "uuid": "e" * 8 + "-0000-7000-8000-" + "f" * 12}}

    def test_every_dtj_block_points_at_the_clients_copy_and_nothing_else_changes(self):
        from page_builder.catalog import registry, to_client
        r = build()
        ours = json.dumps(r.template)
        moved = to_client(r.template, self.CLIENT)
        text = json.dumps(moved)
        for app, entry in registry().items():
            self.assertNotIn(entry["uuid"], text)  # no block left on our own app
            if entry["uuid"] in ours:
                self.assertIn(f"shopify://apps/{self.CLIENT[app]['handle']}/blocks/", text)
        back = text
        for app, entry in self.CLIENT.items():
            back = back.replace(f"apps/{entry['handle']}/", f"apps/{app}/").replace(entry["uuid"], registry()[app]["uuid"])
        self.assertEqual(json.loads(back), r.template)  # only the addresses changed

    def test_a_registry_written_before_the_install_is_refused(self):
        import tempfile
        from pathlib import Path
        from page_builder.catalog import load_client_registry
        apps = {k: dict(v) for k, v in self.CLIENT.items()}
        apps["dtj-blocks"]["handle"] = "pending"
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "c.json"
            f.write_text(json.dumps({"apps": apps}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_client_registry(f)

    def test_a_missing_copy_stops_the_page(self):
        from page_builder.catalog import to_client
        partial = {k: v for k, v in self.CLIENT.items() if k != "dtj-sections"}
        with self.assertRaises(ValueError):
            to_client(build().template, partial)


class OmissionTests(unittest.TestCase):
    def test_too_few_faqs_omit_the_faq(self):
        r = build(faqs=[{"q": "One?", "a": "A.", "source": "product description"}])
        self.assertNotIn("faq", [s["kind"] for s in r.report["sections_built"]])
        self.assertIn("faq", [o["section"] for o in r.report["sections_omitted"]])

    def test_a_single_pack_item_is_not_shown_alone(self):
        r = build(pack_contents=fixtures.toilova()[1]["pack_contents"][:1])
        self.assertIn("pack_inside", [o["section"] for o in r.report["sections_omitted"]])

    def test_a_brand_may_name_its_vibe(self):
        brand, facts = fixtures.toilova()
        brand["vibe"] = "electric"
        self.assertEqual(errors(build_pdp(brand, facts)), [])
        brand["vibe"] = "loud"
        with self.assertRaises((InputError, ValueError)):
            build_pdp(brand, facts)

    def test_pack_items_fill_whole_rows(self):
        base = fixtures.toilova()[1]["pack_contents"]
        items = (base * 4)[:6]
        for n, columns in ((2, "2"), (3, "3"), (4, "4"), (6, "3")):
            r = build(pack_contents=items[:n])
            inside = [s for s in r.model.sections if s.kind == "pack_inside"][0]
            self.assertEqual(inside.settings["columns"], columns, f"{n} items")

    def test_comparison_appears_only_with_the_owners_approval(self):
        brand, facts = fixtures.toilova()
        facts["comparison"]["claims_approved"] = True
        r = build_pdp(brand, facts)
        self.assertIn("comparison", [s["kind"] for s in r.report["sections_built"]])
        self.assertEqual(errors(r), [])

    def test_real_reviews_unlock_the_slider_the_stars_and_the_buy_box_reviews(self):
        brand, facts = fixtures.toilova()
        facts["reviews"] = [{"quote": f"Real quote {i}", "name": f"Name {i}", "rating": 5, "source": "client export"} for i in range(1, 4)]
        facts["rating"] = {"value": "4.6", "source": "client export"}
        r = build_pdp(brand, facts)
        self.assertEqual(errors(r), [])
        types = json.dumps(r.template)
        for block in ("dtj-testimonials-slider", "dtj-social-proof", "dtj-testimonials/"):
            self.assertIn(block, types)
        order = r.template["sections"]["main"]["blocks"]["product-details"]["block_order"]
        self.assertEqual(order.index("dtj_blocks_testimonials_dtj_reviews_buy"), order.index("buy_buttons_eYQEYi") + 1)

    def test_bad_input_is_refused_before_anything_is_built(self):
        brand, facts = fixtures.toilova()
        facts["benefits"][0].pop("source")
        with self.assertRaises(InputError):
            build_pdp(brand, facts)
        with self.assertRaises(InputError):
            build_pdp({"brand_name": "X", "category": "toys"}, facts)


class LintTests(unittest.TestCase):
    def relint(self, result, mutate):
        mutate(result.model)
        return [f.rule for f in rules.lint(result.model)]

    def test_big_padding_and_small_side_space_are_caught(self):
        r = build()
        found = self.relint(r, lambda m: (m.sections[2].settings.update({"padding_top": 90}), m.sections[1].settings.update({"side_padding": 2})))
        self.assertIn("L03", found)
        self.assertIn("L02", found)

    def test_two_neighbours_with_the_same_background_are_caught(self):
        r = build()
        found = self.relint(r, lambda m: [s.settings.update({"background": "#EEEEEE"}) for s in m.sections[2:4]])
        self.assertIn("L04", found)

    def test_an_invented_number_is_caught(self):
        r = build()
        def mutate(m):
            sec = next(s for s in m.sections if s.kind == "why_features")
            m.prov[(sec.id, "heading")]["text"] = "Trusted by 25,000 homes"
        self.assertIn("L08", self.relint(r, mutate))

    def test_an_apostrophe_stored_as_an_entity_is_not_a_number(self):
        # found 9 Oct 2026 on a real book page: rich text stores "Malar's" as "Malar&#x27;s" and L08 read the entity's 27 as a number
        r = build()
        def mutate(m, text):
            sec = next(s for s in m.sections if s.kind == "faq")
            m.prov[(sec.id, "answer_1")]["text"] = text
        self.assertNotIn("L08", self.relint(r, lambda m: mutate(m, "<p>Harsh and Malar&#x27;s love &amp; friends</p>")))
        self.assertIn("L08", self.relint(build(), lambda m: mutate(m, "<p>Malar&#x27;s 27 friends</p>")))

    def test_text_without_a_recorded_origin_is_caught(self):
        r = build()
        def mutate(m):
            sec = next(s for s in m.sections if s.kind == "why_features")
            sec.settings["subheading"] = "Quietly added"
        self.assertIn("L07", self.relint(r, mutate))

    def test_demo_content_needs_the_demo_flag(self):
        brand, facts = fixtures.toilova()
        facts["faqs"][0]["source"] = "demo sample"
        r = build_pdp(brand, facts)
        self.assertIn("L09", [f["rule"] for f in r.report["lint"]])
        facts["demo"] = True
        r2 = build_pdp(brand, facts)
        self.assertNotIn("L09", [f["rule"] for f in r2.report["lint"]])
        self.assertTrue(any("question_1" in x or "answer_1" in x for x in r2.report["needs_replacement"]))

    def test_too_many_dark_bands_are_caught(self):
        r = build()
        found = self.relint(r, lambda m: [m.roles.__setitem__(s.id, "dark") for s in m.sections])
        self.assertIn("L05", found)

    def test_a_failing_contrast_pair_is_caught(self):
        r = build()
        found = self.relint(r, lambda m: m.direction.checks.append({"pair": "x", "fg": "#777777", "bg": "#888888", "ratio": 1.1, "needs": 4.5, "ok": False}))
        self.assertIn("L01", found)

    def test_every_rule_has_a_reason(self):
        for rule, (severity, why) in rules.RULES.items():
            self.assertIn(severity, ("error", "warn"))
            self.assertGreater(len(why), 30, rule)


class CopyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = build()
        cls.slots = {s["slot"]: s["current"] for s in copy_contract.list_slots(cls.r)}

    def test_only_structural_text_is_offered_to_the_model(self):
        self.assertIn("dtj_why.heading", self.slots)
        self.assertNotIn("dtj_why.f1_title", self.slots)  # benefit titles are facts
        self.assertTrue(all(len(s) <= 60 for s in self.slots.values()))

    def test_the_request_carries_voice_rules_and_slots(self):
        req = copy_contract.build_request(self.r)
        self.assertEqual(req["brand"]["name"], "TOILOVA")
        self.assertGreaterEqual(len(req["rules"]), 4)
        self.assertEqual(len(req["slots"]), len(self.slots))

    def test_a_clean_rewrite_is_accepted_and_applied_with_its_origin_marked(self):
        accepted, rejected = copy_contract.validate_response(self.r, {"slots": {"dtj_why.heading": "Why TOILOVA works for you"}})
        self.assertEqual(rejected, {})
        brand, facts = fixtures.toilova()
        final = build_pdp(brand, facts, copy_overrides=accepted)
        self.assertEqual(final.model.prov[("dtj_why", "heading")]["kind"], "copy")
        self.assertEqual(final.model.sections[1].settings["heading"], "Why TOILOVA works for you")
        self.assertEqual(errors(final), [])

    def test_claims_numbers_markup_fact_slots_and_brand_loss_are_rejected(self):
        bad = {"dtj_why.heading": "The #1 cleaner",
               "dtj_faq.heading": "Questions answered in 5 minutes",
               "dtj_inside.heading": "<b>What is inside</b>",
               "dtj_why.f1_title": "Totally new benefit",
               "dtj_notinside.heading": "Free shipping today",
               "dtj_how.heading": ""}
        accepted, rejected = copy_contract.validate_response(self.r, {"slots": bad})
        self.assertEqual(accepted, {})
        self.assertEqual(set(rejected), set(bad))

    def test_dropping_the_brand_name_from_a_slot_that_has_it_is_rejected(self):
        accepted, rejected = copy_contract.validate_response(self.r, {"slots": {"dtj_why.heading": "Why choose this one?"}})
        self.assertIn("dtj_why.heading", rejected)

    def test_a_response_that_breaks_the_schema_is_rejected_whole(self):
        for bad in ({}, {"slots": {"dtj_why.heading": 5}}, {"slots": {"dtj_why.heading": "x" * 80}}):
            accepted, rejected = copy_contract.validate_response(self.r, bad)
            self.assertEqual(accepted, {})
            self.assertTrue(rejected)

    def test_two_slots_may_not_say_the_same_thing(self):
        accepted, rejected = copy_contract.validate_response(self.r, {"slots": {"dtj_how.heading": "Easy as that", "dtj_faq.heading": "Easy as that"}})
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 1)


if __name__ == "__main__":
    unittest.main()


def standard_facts():
    """The TOILOVA fixture filled out for every section of DTJ Standard Product Page v1, with marked samples where a client
    would not have sent content yet."""
    brand, facts = fixtures.toilova()
    S = "SAMPLE: replace before live"
    facts["ugc"] = [{"image_role": r, "source": S} for r in ("hand", "shelf", "steps")]
    facts["story_2"] = {"heading": "Clean without the fumes", "body": "A thick gel that clings to the bowl.",
                        "bullets": ["Clings under the rim", "No harsh smell", "Septic-safe", "Rinses in one flush"], "image_role": "fumes",
                        "source": "product description"}
    facts["differentiators"] = {"heading": "Why TOILOVA works harder", "items": [{"title": f"Point {i}", "text": f"Line {i}.", "source": "product description"} for i in range(1, 7)],
                                "source": "product description"}
    facts["strip_2"] = [{"text": t, "source": "pack print"} for t in ("Made in India", "Septic safe", "No harsh smell", "Cash on delivery")]
    facts["feature_intro"] = {"heading": "What you will notice", "text": "Every flush, cleaner.", "source": "product description"}
    facts["guarantee"] = {"heading": "Love it or your money back", "text": "Use it for 30 days.", "seal": "30-day promise", "source": S}
    facts["reviews"] = [{"quote": f"Review words {i}.", "name": n, "location": "Pune", "rating": 5, "source": S} for i, n in enumerate(("Asha", "Ravi", "Meera"), 1)]
    facts["stories"] = [{"name": n, "quote": f"Story words {i}.", "tags": "Daily use", "image_role": "hand", "source": S} for i, n in enumerate(("Kiran", "Neha", "Arjun"), 1)]
    facts["final_push"] = {"heading": "A cleaner bathroom, every day", "text": "Order today.", "image_role": "shelf", "source": "product description"}
    facts["cta"] = {"label": "Get my bottle", "source": "brand voice"}
    return brand, facts


STANDARD_ORDER = ["trust_marquee", "story_split", "story_split_2", "reviews_slider", "why_us", "benefit_strip_2", "why_features",
                  "guarantee", "facts_glance", "faq", "stories", "final_push"]


class PeopleAndPhotoStripTests(unittest.TestCase):
    """Harsh, 19 Oct 2026: DTJ's sample people photos in every human picture slot of a sample, and the customer-photo strip right
    under the buy buttons (not a section of its own on the left)."""

    def demo_page(self, **mods):
        brand, facts = standard_facts()
        facts["demo"] = True
        facts["rating"] = {"value": "4.6", "source": "SAMPLE: replace before live"}
        for r, who in zip(facts["reviews"], ("f", "m", "f")):
            r["person"] = who
        for st, who in zip(facts["stories"], ("m", "f", "m")):
            st["person"] = who
        facts.update(mods)
        return build_pdp(brand, facts, recipe="dtj-standard-v1")

    @staticmethod
    def person(value):
        from page_builder.assemble import load_people
        name = str(value or "").rsplit("/", 1)[-1]
        return next((p["person"] for p in load_people() if p["file"] == name), None)

    def test_sample_reviews_stories_and_the_rating_line_get_matching_people_never_twice(self):
        r = self.demo_page()
        reviews = next(s for s in r.model.sections if s.kind == "reviews_slider").settings
        stories = next(s for s in r.model.sections if s.kind == "stories").settings
        stars = next(s for s in r.model.buybox_sections if s.kind == "rating").settings
        self.assertEqual([self.person(reviews[f"image_{i}"]) for i in (1, 2, 3)], ["f", "m", "f"])
        self.assertEqual([self.person(stories[f"photo_{i}"]) for i in (1, 2, 3)], ["m", "f", "m"])  # a person replaces the product picture
        avatars = [stars[f"avatar_{i}"] for i in range(1, 6)]
        self.assertTrue(all(self.person(a) for a in avatars))
        used = r.report["people_photos"]
        self.assertEqual(len(used), 11)
        self.assertEqual(len(set(used)), 11)  # never the same face twice on a page
        self.assertTrue(all(f"shopify://shop_images/{u}" in json.dumps(r.template) for u in used))
        self.assertEqual(errors(r), [])

    def test_a_real_review_never_gets_a_strangers_face_and_a_page_that_is_not_a_demo_gets_none(self):
        brand, facts = standard_facts()
        facts["demo"] = True
        facts["reviews"][0]["source"] = "Judge.me review, 12 Oct 2026"
        r = build_pdp(brand, facts, recipe="dtj-standard-v1")
        reviews = next(s for s in r.model.sections if s.kind == "reviews_slider").settings
        self.assertFalse(reviews.get("image_1"))
        self.assertTrue(self.person(reviews["image_2"]))
        brand, facts = standard_facts()  # demo not set: no test pictures and no people at all
        self.assertEqual(build_pdp(brand, facts, recipe="dtj-standard-v1").report["people_photos"], [])

    def test_the_photo_strip_sits_right_under_the_buy_buttons(self):
        r = self.demo_page()
        self.assertNotIn("ugc_strip", [s.kind for s in r.model.sections])
        strip = next(s for s in r.model.buybox_sections if s.kind == "ugc_strip")
        column = r.template["sections"]["main"]["blocks"]["product-details"]
        order = column["block_order"]
        self.assertEqual(order.index(next(k for k in order if "dtj_ugc" in k)), order.index("buy_buttons_eYQEYi") + 1)
        self.assertEqual(strip.settings["card_width"], 170)
        self.assertNotIn("background", strip.settings)  # the column's own white, no band
        self.assertNotIn("dtj_ugc", r.model.extras)  # no button of its own: the buy buttons are right above
        self.assertNotIn("dtj_ugc", r.template["sections"])


class RangeStepTests(unittest.TestCase):
    def test_a_range_value_between_steps_is_a_problem_before_shopify_refuses_the_file(self):
        cat = Catalog()
        self.assertTrue(any("step" in p for p in cat.validate("dtj-sections-2", "slideshow-pro", {"overlay_opacity": 62})))
        self.assertEqual(cat.validate("dtj-sections-2", "slideshow-pro", {"overlay_opacity": 60}), [])


class StandardPageTests(unittest.TestCase):
    def build(self, vibe=None, **mods):
        brand, facts = standard_facts()
        if vibe:
            brand["vibe"] = vibe
        for k, v in mods.items():
            if v is None:
                facts.pop(k, None)  # the client has not sent this section's content
            else:
                facts[k] = v
        return build_pdp(brand, facts, recipe="dtj-standard-v1")

    def test_every_section_in_the_fixed_order_whatever_the_category(self):
        r = self.build()
        self.assertEqual([s.kind for s in r.model.sections], STANDARD_ORDER)
        self.assertEqual(r.report["chosen_by"], "fixed set")
        self.assertEqual(errors(r), [])
        brand, facts = standard_facts()
        brand["category"] = "beauty"  # categories reorder the old recipe, never the fixed set
        self.assertEqual([s.kind for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections], STANDARD_ORDER)

    def test_a_plan_cannot_reorder_or_drop_sections_of_the_fixed_set(self):
        brand, facts = standard_facts()
        r = build_pdp(brand, facts, recipe="dtj-standard-v1", plan={"order": ["faq"], "left_out": {}, "signature": ""})
        self.assertEqual([s.kind for s in r.model.sections], STANDARD_ORDER)

    def test_the_cta_button_follows_the_wireframe_sections_inside_the_same_band(self):
        r = self.build()
        with_cta = [s["kind"] for s in r.report["sections_built"] if s["cta"]]
        self.assertEqual(with_cta, ["story_split", "story_split_2", "reviews_slider", "why_us", "why_features", "facts_glance", "faq"])
        sec = r.template["sections"]["dtj_reviews"]
        self.assertEqual(len(sec["block_order"]), 2)
        cta = sec["blocks"][sec["block_order"][1]]
        self.assertIn("/blocks/dtj-cta/", cta["type"])
        self.assertEqual(cta["settings"]["button_label"], "Join them")  # named after its section (Harsh, 10 Oct 2026)
        self.assertEqual(cta["settings"].get("background"), r.model.sections[STANDARD_ORDER.index("reviews_slider")].settings.get("background"))

    def test_every_button_has_its_own_label_and_the_last_one_keeps_the_brands_main_label(self):
        r = self.build()
        labels = [x.settings["button_label"] for x in r.model.extras.values()]
        labels += [r.template["sections"][sid]["blocks"][k]["settings"][key] for sid, key in
                   (("dtj_guarantee", "button_label"), ("dtj_stories", "cta_text"), ("dtj_final", "button_label_1"))
                   for k in r.template["sections"][sid]["block_order"][:1]]
        self.assertEqual(len(labels), len(set(labels)), labels)
        self.assertEqual(labels[-1], "Get my bottle")
        self.assertEqual(r.model.prov[("dtj_reviews_cta", "button_label")]["kind"], "structure")  # the copy step may rename it

    def test_the_copy_step_names_a_button_after_its_section_within_the_limits(self):
        r = self.build()
        slots = {x["slot"]: x for x in copy_contract.list_slots(r)}
        self.assertTrue(slots["dtj_reviews_cta.button_label"]["button"])
        self.assertEqual(slots["dtj_reviews_cta.button_label"]["section_heading"], "What customers say")
        self.assertEqual(slots["dtj_reviews_cta.button_label"]["max_length"], 24)
        self.assertNotIn("dtj_final.button_label_1", slots)  # the brand's own main label is a fact
        accepted, rejected = copy_contract.validate_response(r, {"slots": {
            "dtj_reviews_cta.button_label": "Join the happy homes",
            "dtj_faq_cta.button_label": "Learn more about it",
            "dtj_why_us_cta.button_label": "Get the cleaner that works harder",
            "dtj_story_cta.button_label": "Go"}})
        self.assertEqual(set(accepted), {"dtj_reviews_cta.button_label"})
        self.assertEqual(set(rejected), {"dtj_faq_cta.button_label", "dtj_why_us_cta.button_label", "dtj_story_cta.button_label"})
        final = build_pdp(*standard_facts(), recipe="dtj-standard-v1", copy_overrides=accepted)
        self.assertEqual(final.model.extras["dtj_reviews"].settings["button_label"], "Join the happy homes")
        self.assertEqual(errors(final), [])

    def test_two_buttons_with_the_same_label_fail_the_page(self):
        r = build_pdp(*standard_facts(), recipe="dtj-standard-v1", copy_overrides={"dtj_faq_cta.button_label": "Join them"})
        self.assertIn("L16", [f["rule"] for f in errors(r)])

    def test_an_electric_brand_gets_bold_bands_and_every_pair_still_passes(self):
        r = self.build(vibe="electric")
        roles = {s.kind: r.model.roles[s.id] for s in r.model.sections}
        # Harsh, 10 Oct 2026: customer photos and numbers on white, reviews dark with white cards
        self.assertEqual((roles["trust_marquee"], roles["facts_glance"], roles["reviews_slider"]), ("band", "plain", "dark"))
        self.assertEqual(roles["guarantee"], "accent")
        d = r.model.direction
        self.assertEqual(d.roles["band"], "#0B4A6F")  # the brand colour itself, not a tint
        self.assertEqual(d.failed_checks(), [])
        self.assertEqual(errors(r), [])
        by_kind = {s.kind: s.settings for s in r.model.sections}
        reviews = by_kind["reviews_slider"]
        self.assertEqual((reviews["card_bg"], reviews["card_text_color"]), (d.roles["tint_card"], d.roles["on_card"]))
        self.assertEqual(reviews["text_color"], d.roles["on_dark"])  # the heading on the dark band stays light
        numbers = by_kind["facts_glance"]
        card = numbers.get("card_bg") or numbers.get("card_bg_color")  # stat cards, or science stats when every figure has a picture
        self.assertEqual((card, numbers["number_color"]), (d.roles["dark"], d.roles["accent_on_dark"]))
        self.assertNotIn("background", numbers)  # the section itself is white
        icons = by_kind["why_features"]
        self.assertEqual((icons["icon_bg"], icons["icon_color"]), (d.roles["tint_card"], d.roles["on_card"]))  # white badges on the band

    def test_the_shield_only_on_a_promise_badge(self):
        # Harsh, 24 Oct 2026: "the shield is totally unrelated with the badge saying high protein"
        from page_builder.sections import SHIELD_WORDS
        self.assertFalse(SHIELD_WORDS.search("High protein"))
        self.assertTrue(SHIELD_WORDS.search("Lab tested") and SHIELD_WORDS.search("7-day returns"))

    def test_the_badge_icon_shows_on_its_badge(self):
        # 24 Oct 2026, NoCheat: the icon was the maroon of the maroon badge ("NO ICON IN THE HIGH PROTEIN")
        for vibe in ("electric", "playful", None):
            r = self.build(vibe=vibe) if vibe else self.build()
            blocks = r.template["sections"]["main"]["blocks"]["product-details"]["blocks"]
            proof = next((b["settings"] for k, b in blocks.items() if "social_proof" in k), {})
            if "badge_icon_color" in proof:
                self.assertGreaterEqual(style_contrast(proof["badge_icon_color"], proof["badge_bg"]), 3, vibe)

    def test_the_faq_question_keeps_its_colour_on_hover(self):
        # Harsh, 25 Oct 2026: "on hover the text gets hidden": Horizon's summary:hover beat the block's question colour
        r = self.build(vibe="electric")
        faq = [s for s in r.template["sections"].values()
               if any("dtj-faq" in str(b.get("type", "")) for b in (s.get("blocks") or {}).values())]
        self.assertTrue(faq)
        self.assertIn(".dtj-faq__q:hover{color:var(--fq-q-color,inherit)}", faq[0]["custom_css"])

    def test_the_theme_buy_buttons_take_the_page_palette(self):
        # Harsh, 24 Oct 2026: "add to cart keep the yellow and buy it now red (the same color palette applied to the page)"
        r = self.build(vibe="electric")
        d, t = r.model.direction.roles, r.template
        cart = t["sections"]["main"]["blocks"]["product-details"]["blocks"]["buy_buttons_eYQEYi"]["blocks"]["add-to-cart"]["settings"]
        self.assertEqual((cart["style_class"], cart["custom_button_background"], cart["custom_button_text"]),
                         ("button-custom", d["button_bg"], d["button_text"]))
        css = " ".join(t["sections"]["main"]["custom_css"])
        self.assertIn("button.shopify-payment-button__button.shopify-payment-button__button--unbranded", css)
        now = css.split("background-color:")[1].split(" ")[0]
        self.assertGreaterEqual(style_contrast(now, css.split("color:")[2].split(" ")[0]), 4.5)  # Buy it now's words read on it
        self.assertGreaterEqual(style_contrast(now, d["button_bg"]), 1.5)  # and it is not the Add to cart colour

    def test_white_words_on_an_electric_page_sit_on_ink_never_on_the_brand_colour(self):
        # Harsh, 10 Oct 2026: white story points, white FAQ answers, white strip ticks; white on the brand cyan was 2.2:1
        r = self.build(vibe="electric")
        d = r.model.direction
        by_kind = {s.kind: s.settings for s in r.model.sections}
        story = by_kind["story_split"]
        self.assertEqual((story["panel_bg"], story["body_color"], story["accent_color"]), (d.roles["dark"], d.roles["on_dark"], d.roles["accent_on_dark"]))
        if style_contrast("#FFFFFF", d.roles["accent_on_dark"]) < 3:
            self.assertEqual(story["tick_color"], d.roles["dark"])  # a white check would vanish on a light marker
        faq = by_kind["faq"]
        self.assertEqual((faq["item_bg"], faq["q_color"], faq["a_color"], faq["toggle_color"]),
                         (d.roles["dark"], d.roles["on_dark"], d.roles["on_dark"], d.roles["accent_on_dark"]))
        # the strip's ticks stand apart from its words and show on the band (white ticks, unless the words are white too:
        # design check H03, 24 Oct 2026)
        tick = by_kind["trust_marquee"]["accent_color"]
        self.assertGreaterEqual(style_contrast(tick, by_kind["trust_marquee"].get("text_color") or d.roles["on_band"]), 1.5)
        self.assertGreaterEqual(style_contrast(tick, d.roles["band"]), 3)
        self.assertEqual(by_kind["benefit_strip_2"]["accent_color"], d.roles["on_accent"])  # the accent band keeps its own checked colour
        calm = {s.kind: s.settings for s in self.build().model.sections}
        self.assertNotIn("item_bg", calm["faq"])  # calm pages keep their soft look
        self.assertNotEqual(calm["story_split"]["panel_bg"], r.model.direction.roles["dark"])

    def our_copy(self, intro, category=None):
        brand, facts = standard_facts()
        if category:
            brand["category"] = category
        facts["buybox"] = {"tagline": "Foam first. Scrub never.", "intro": intro, "source": "DTJ COPY (basis: product description)",
                           "bullets": ["Zero scrubbing", "No harsh fumes", "Done in one flush", "Hands stay clean"]}
        return build_pdp(brand, facts, recipe="dtj-standard-v1")

    def test_copy_we_write_is_listed_for_the_clients_sign_off(self):
        # references/copywriting.md: voice lines stand on facts and are marked DTJ COPY (Harsh, 10 Oct 2026, the MojoVibe standard)
        r = self.our_copy("Made for the bathroom you dread: foam that does the scrubbing, so all you do is flush.")
        self.assertIn("dtj_points.subheading", r.report["dtj_copy"])
        self.assertEqual(r.model.prov[("dtj_points", "subheading")]["kind"], "dtj_copy")
        self.assertNotIn("dtj_points.subheading", r.report["samples"])
        self.assertEqual(errors(r), [])

    def test_copy_we_write_adds_no_claim(self):
        found = lambda r: [f["message"] for f in errors(r) if f["rule"] == "L19"]  # noqa: E731
        self.assertTrue(found(self.our_copy("The only cleaner you need, clinically tested.")))  # "the only", "clinically"
        self.assertTrue(found(self.our_copy("Lose weight? No. Lose the scrubbing.")))  # a body word, even as a joke
        self.assertTrue(found(self.our_copy("100% natural foam.")))  # claim words the brand's own facts do not use
        self.assertEqual(found(self.our_copy("Warning: may cause addiction to a clean bathroom.")), [])  # a joke on home care
        self.assertTrue(found(self.our_copy("Warning: may cause addiction to a clean bathroom.", category="supplements")))

    def test_number_cards_on_a_white_electric_section_are_ink_with_accent_figures(self):
        brand, facts = standard_facts()
        brand["vibe"] = "electric"
        for f in facts["key_facts"]:
            f.pop("image_role", None)  # without a picture per figure the numbers use the stat cards
        r = build_pdp(brand, facts, recipe="dtj-standard-v1")
        sec = next(s for s in r.model.sections if s.kind == "facts_glance")
        d = r.model.direction
        self.assertEqual(sec.block, "stat-cards")
        self.assertEqual((sec.settings["card_bg"], sec.settings["number_color"], sec.settings["label_color"]),
                         (d.roles["dark"], d.roles["accent_on_dark"], d.roles["on_dark"]))
        self.assertEqual(errors(r), [])

    def test_story_cards_on_a_calm_page_stand_apart_from_the_page_and_the_band(self):
        # design_checks H01 on the first editorial page (a book, 10 Oct 2026): the calm band is ~1.1:1 from white, so a band-coloured
        # card on white and a white card on the band both melted into their section
        r = self.build()
        d = r.model.direction
        for s in r.model.sections:
            if s.block == "split-story":
                behind = s.settings.get("background") or d.roles["bg"]
                self.assertEqual(s.settings["panel_bg"], d.roles["panel"].upper())
                self.assertGreaterEqual(style_contrast(s.settings["panel_bg"], behind), 1.5, s.kind)
                self.assertGreaterEqual(style_contrast(s.settings["body_color"], s.settings["panel_bg"]), 4.5)  # the card's own words
        self.assertEqual(d.failed_checks(), [])

    def test_four_long_figures_sit_two_by_two_so_none_breaks_across_lines(self):
        brand, facts = standard_facts()
        facts["key_facts"] = [{"value": v, "label": "Label", "source": "pack"} for v in ("2,00,000+", "4.9", "2-3", "2")]
        sec = next(s for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections if s.kind == "facts_glance")
        self.assertEqual(sec.settings.get("columns"), "2")
        facts["key_facts"] = [{"value": v, "label": "Label", "source": "pack"} for v in ("4.9", "50 mg", "75 mg", "4 min")]
        sec = next(s for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections if s.kind == "facts_glance")
        self.assertNotIn("columns", sec.settings)

    def test_reader_videos_play_in_the_photo_strip_with_the_picture_as_fallback(self):
        # Harsh, 10 Oct 2026: "I have added videos which you can use in the testimonials"
        brand, facts = standard_facts()
        facts["ugc"] = [{"image_role": "hand", "video": f"clip{i}.mp4", "source": "Harsh, 10 Oct 2026"} for i in (1, 2, 3)]
        r = build_pdp(brand, facts, recipe="dtj-standard-v1")
        sec = next(s for s in r.model.buybox_sections if s.kind == "ugc_strip")  # in the buy box column since 19 Oct 2026
        self.assertEqual([sec.settings[f"media_type_{i}"] for i in (1, 2, 3)], ["video"] * 3)
        self.assertEqual(sec.settings["video_2"], "shopify://files/videos/clip2.mp4")
        self.assertTrue(sec.settings["image_1"].startswith("shopify://shop_images/"))
        self.assertEqual(r.report["problems"], [])
        self.assertEqual(errors(r), [])
        self.assertTrue(Catalog().validate("dtj-blocks", "shoppable-reels", {"video_1": "https://cdn.shopify.com/x.mp4"}))  # not a Files reference

    def test_edits_made_in_the_theme_editor_are_kept_on_every_rebuild(self):
        from page_builder.run_client import apply_kept_edits
        t = build_pdp(*standard_facts(), recipe="dtj-standard-v1").template
        key = next(k for k in t["sections"]["main"]["blocks"]["product-details"]["blocks"] if "dtj_price" in k)
        done = apply_kept_edits(t, [{"section": "main", "block": key, "setting": "price_size", "value": 22, "why": "Harsh"}])
        self.assertEqual(t["sections"]["main"]["blocks"]["product-details"]["blocks"][key]["settings"]["price_size"], 22)
        self.assertEqual(len(done), 1)
        with self.assertRaises(ValueError):  # a typo never writes silently
            apply_kept_edits(t, [{"section": "main", "block": key, "setting": "price_sise", "value": 22}])
        with self.assertRaises(ValueError):
            apply_kept_edits(t, [{"section": "main", "block": "gone", "setting": "x", "value": 1}])

    def test_a_bright_brand_colour_stays_bright_on_the_buttons_of_a_calm_page(self):
        # Hope N Skin, 10 Oct 2026: orange #FF8C11 was darkened to brown for white text; near-black text on the real orange reads at 7.5:1
        d = derive({"brand_name": "Glow", "category": "beauty", "vibe": "fresh",
                    "colors": {"primary": "#FF8C11", "accent": "#FF8C11", "background": "#FFFFFF", "text": "#1A1A1A"}})
        self.assertEqual((d.roles["button_bg"], d.roles["button_text"]), ("#FF8C11", "#1A1A1A"))
        self.assertGreaterEqual(style_contrast(d.roles["button_text"], d.roles["button_bg"]), 4.5)
        self.assertNotEqual(d.roles["accent"], "#FF8C11")  # accent WORDS on white still use the darkened, readable shade
        dark_accent = derive({"brand_name": "Book", "category": "other", "vibe": "editorial",
                              "colors": {"primary": "#BF956C", "accent": "#993916", "background": "#FFFFFF", "text": "#2A1E16"}})
        self.assertEqual(dark_accent.roles["button_text"], "#FFFFFF")  # a dark accent keeps white text

    def test_calm_story_cards_are_the_brand_colour_with_white_accent_words_and_ticks(self):
        # Harsh, Hope N Skin, 10 Oct 2026: "make the dark orange white and make the icons white and the mark inside orange"; a colour
        # that keeps its character when deepened (a teal here; a bright orange turns brown and gets the light card, test below)
        d = derive({"brand_name": "Glow", "category": "beauty", "vibe": "fresh",
                    "colors": {"primary": "#1F9E8F", "accent": "#1F9E8F", "background": "#FFFFFF", "text": "#1A1A1A"}})
        panel = d.roles["panel"]
        self.assertEqual((d.roles["accent_on_panel"], d.roles["panel_tick"], d.roles["on_panel"]), ("#FFFFFF", panel, "#FFFFFF"))
        self.assertGreaterEqual(style_contrast("#FFFFFF", panel), 4.5)  # white paragraph and points (Harsh: "keep every text white here")
        self.assertGreaterEqual(style_contrast(d.roles["panel_head"], panel), 3.0)  # "Brighter skin," stays dark as a large headline
        self.assertEqual(d.failed_checks(), [])

    def test_a_neutral_card_tone_gives_minimalists_light_grey_with_dark_words_and_the_brand_colour_on_the_ticks(self):
        # Harsh, Hope N Skin, 10 Oct 2026: "use grey color like minimalist", then "i told to use grey like minimalist -- minimalist brand"
        d = derive({"brand_name": "Glow", "category": "beauty", "vibe": "fresh", "card_tone": "neutral",
                    "colors": {"primary": "#FF8C11", "accent": "#FF8C11", "background": "#FFFFFF", "text": "#1A1A1A"}})
        r = d.roles
        self.assertEqual(r["panel"], "#FAFAFA")  # almost white (Harsh: "make it very closer to white", then "more lighter")
        self.assertEqual((r["on_panel"], r["panel_head"], r["accent_on_panel"]), ("#1A1A1A",) * 3)  # their dark words on light grey
        self.assertGreaterEqual(style_contrast(r["on_panel"], r["panel"]), 4.5)
        self.assertEqual(r["panel_tick"], "#FF8C11")  # the orange check inside the dark tick circle
        self.assertGreaterEqual(style_contrast(r["panel_tick"], r["accent_on_panel"]), 3.0)
        self.assertEqual(d.failed_checks(), [])
        brand, facts = standard_facts()
        brand.update({"vibe": "fresh", "card_tone": "neutral"})
        built = {s.kind: s.settings for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections}
        story = built["story_split"]
        self.assertEqual(story["panel_bg"], "#FAFAFA")
        self.assertNotEqual(story["tick_color"], story["accent_color"])  # the brand colour survives on the built page
        # the closing banner follows the cards instead of staying dark brown (Harsh: "this section didnt got updated")
        final = built["final_push"]
        self.assertEqual((final["background"], final["overlay_color"], final["text_color"]), ("#FAFAFA", "#FAFAFA", derive(brand).roles["text"]))
        brand["card_tone"] = "brand"
        final = {s.kind: s.settings for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections}["final_push"]
        self.assertEqual((final["background"], final["text_color"]), (derive(brand).roles["dark"], "#FFFFFF"))  # default: the dark band

    def test_a_bright_orange_brand_never_turns_brown(self):
        # Hope N Skin, 10 Oct 2026: orange deepened into the #B2620C card and the #402305 banner; Harsh rejected both (design_checks H11)
        orange = {"brand_name": "Glow", "category": "beauty", "vibe": "fresh",
                  "colors": {"primary": "#FF8C11", "accent": "#FF8C11", "background": "#FFFFFF", "text": "#1A1A1A"}}
        r = derive(orange).roles
        self.assertEqual((r["panel"], r["banner"]), ("#FAFAFA", "#FAFAFA"))  # the light card look without being asked
        self.assertEqual(r["dark"], "#1A1A1A")  # the ink, not brown
        forced = derive({**orange, "card_tone": "brand"}).roles
        self.assertNotEqual(forced["panel"], "#FAFAFA")  # card_tone "brand" still gives the deepened brand card on request
        teal = derive({**orange, "colors": {**orange["colors"], "primary": "#1F9E8F", "accent": "#1F9E8F"}}).roles
        self.assertNotEqual(teal["panel"], "#FAFAFA")  # colours that stay themselves when deepened keep the brand card

    def test_calm_review_star_tiles_are_the_brand_colour_with_white_stars(self):
        # Harsh, Hope N Skin, 10 Oct 2026: "make the star square blocks orange and stars white"
        brand, facts = standard_facts()
        brand.update({"vibe": "fresh", "colors": {"primary": "#FF8C11", "accent": "#FF8C11", "background": "#FFFFFF", "text": "#1A1A1A"}})
        reviews = {s.kind: s.settings for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections}["reviews_slider"]
        tile = reviews["tile_color"]
        self.assertEqual(reviews["tile_star_color"], "#FFFFFF")
        self.assertGreaterEqual(style_contrast("#FFFFFF", tile), 3.0)  # the white star reads (plain #FF8C11 is 2.3:1)
        self.assertLess(style_contrast("#FFFFFF", tile), 3.6)  # darkened only as far as needed: still orange, not brown
        brand["vibe"] = "electric"  # bold pages keep the ink tiles Harsh approved on Go Mints
        reviews = {s.kind: s.settings for s in build_pdp(brand, facts, recipe="dtj-standard-v1").model.sections}["reviews_slider"]
        self.assertNotEqual(reviews["tile_star_color"], "#FFFFFF")

    def test_the_closing_banner_takes_the_pictures_own_shape(self):
        final = {s.kind: s.settings for s in self.build().model.sections}["final_push"]
        self.assertEqual((final["ratio_desktop"], final["ratio_mobile"]), ("adapt", "adapt"))

    def test_a_long_story_card_fails_the_page(self):
        brand, facts = standard_facts()
        facts["story"]["body"] = " ".join(["word"] * 21)
        facts["story_2"]["bullets"][0] = "A point that runs on far too long to read"
        found = [f["message"] for f in errors(build_pdp(brand, facts, recipe="dtj-standard-v1")) if f["rule"] == "L17"]
        self.assertEqual(len(found), 2, found)

    def test_buy_box_points_with_a_dose_or_measure_fail_the_page(self):
        brand, facts = standard_facts()
        facts["buybox"]["bullets"] = ["Natural caffeine 50 mg", "Energy in minutes", "100% vegan", "Easy to carry"]
        found = [f["message"] for f in errors(build_pdp(brand, facts, recipe="dtj-standard-v1")) if f["rule"] == "L18"]
        self.assertEqual(len(found), 2, found)

    def test_a_calm_brand_keeps_soft_bands_and_one_dark_at_most(self):
        r = self.build()
        self.assertNotIn("accent", set(r.model.roles.values()))
        self.assertNotIn("dark", set(r.model.roles.values()))
        self.assertNotEqual(r.model.direction.roles["band"], "#0B4A6F")

    def test_reviews_show_once_in_the_fixed_set_never_also_in_the_buy_box(self):
        r = self.build()
        self.assertNotIn("reviews_buybox", [s.kind for s in r.model.buybox_sections])
        self.assertIn("reviews_slider", [s.kind for s in r.model.sections])

    def test_samples_are_tracked_and_listed_for_replacement(self):
        r = self.build()
        self.assertIn("dtj_guarantee.heading", r.report["samples"])
        self.assertIn("dtj_reviews.text_1", r.report["samples"])
        self.assertTrue(set(r.report["samples"]) <= set(r.report["needs_replacement"]))
        self.assertNotIn("dtj_story.heading", r.report["samples"])  # a real fact is not a sample

    def test_a_section_without_content_is_left_out_and_never_glues_two_bands_together(self):
        r = self.build(vibe="electric", story=None)
        kinds = [s.kind for s in r.model.sections]
        self.assertNotIn("story_split", kinds)
        bgs = [s.settings.get("background") for s in r.model.sections if r.model.roles[s.id] != "none"]
        self.assertFalse(any(a and a == b for a, b in zip(bgs, bgs[1:])))

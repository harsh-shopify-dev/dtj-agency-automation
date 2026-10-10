"""Tests for the page builder: the design judgment as checks (adaptation to a brand, contrast, rhythm, provenance, omission instead of invention,
the copy contract)."""
import copy
import json
import unittest

from page_builder import copy_contract, rules, styling
from page_builder.assemble import InputError, build_pdp
from page_builder.catalog import Catalog
from page_builder.direction import derive
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


STANDARD_ORDER = ["ugc_strip", "trust_marquee", "story_split", "story_split_2", "reviews_slider", "why_us", "benefit_strip_2", "why_features",
                  "guarantee", "facts_glance", "faq", "stories", "final_push"]


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
        self.assertEqual(with_cta, ["ugc_strip", "story_split", "story_split_2", "reviews_slider", "why_us", "why_features", "facts_glance", "faq"])
        sec = r.template["sections"]["dtj_reviews"]
        self.assertEqual(len(sec["block_order"]), 2)
        cta = sec["blocks"][sec["block_order"][1]]
        self.assertIn("/blocks/dtj-cta/", cta["type"])
        self.assertEqual(cta["settings"]["button_label"], "Get my bottle")
        self.assertEqual(cta["settings"].get("background"), r.model.sections[STANDARD_ORDER.index("reviews_slider")].settings.get("background"))
        labels = {r.model.extras[k].settings["button_label"] for k in r.model.extras}
        self.assertEqual(labels, {"Get my bottle"})  # ONE label for the whole page

    def test_an_electric_brand_gets_bold_bands_and_every_pair_still_passes(self):
        r = self.build(vibe="electric")
        roles = {s.kind: r.model.roles[s.id] for s in r.model.sections}
        self.assertEqual(roles["ugc_strip"], "dark")
        self.assertEqual(roles["guarantee"], "accent")
        d = r.model.direction
        self.assertEqual(d.roles["band"], "#0B4A6F")  # the brand colour itself, not a tint
        self.assertEqual(d.failed_checks(), [])
        self.assertEqual(errors(r), [])

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

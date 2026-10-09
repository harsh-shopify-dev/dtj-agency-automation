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


class OmissionTests(unittest.TestCase):
    def test_too_few_faqs_omit_the_faq(self):
        r = build(faqs=[{"q": "One?", "a": "A.", "source": "product description"}])
        self.assertNotIn("faq", [s["kind"] for s in r.report["sections_built"]])
        self.assertIn("faq", [o["section"] for o in r.report["sections_omitted"]])

    def test_a_single_pack_item_is_not_shown_alone(self):
        r = build(pack_contents=fixtures.toilova()[1]["pack_contents"][:1])
        self.assertIn("pack_inside", [o["section"] for o in r.report["sections_omitted"]])

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

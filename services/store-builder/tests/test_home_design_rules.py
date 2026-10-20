"""The home page design rules from the 23-page study (Harsh, 19 Oct 2026: our home page "looks cramped and flat"): one vertical rhythm on the
theme's section wrapper, one heading scale, the lint gate L20, and the measurable checks in home_checks.py."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_builder import home_checks, render, rules, styling  # noqa: E402
from page_builder.assemble_home import build_home  # noqa: E402
from test_home_page import brand, full_facts  # noqa: E402


def ramps_brand() -> dict:
    b = brand("home-care")
    b["colors"] = {"primary": "#0B66B2", "accent": "#00B84C", "background": "#FFFFFF", "text": "#10202D"}
    b["palette"] = "ramps"
    return b


def built():
    return build_home(ramps_brand(), full_facts())


def kinds_of(res) -> dict[str, str]:
    return {s["id"]: s["kind"] for s in res.report["sections_built"]}


class RhythmTests(unittest.TestCase):
    def test_one_step_everywhere_a_tighter_one_between_related_neighbours_none_for_strips_and_the_hero_keeps_its_own(self):
        S, R = styling.HOME_SPACE["section"], styling.HOME_SPACE["related"]
        got = styling.home_rhythm(["announcement_bar", "hero_home", "trust_band_home", "categories_home", "best_sellers_home",
                                   "value_props_home", "wave_home", "concerns_home", "faq"])
        self.assertEqual(got, [(0, 0), None, (0, 0), (S, R), (R, S), (S, S), (0, 0), (R, S), (S, S)])
        self.assertLess(R, S)

    def test_the_steps_sit_inside_what_the_best_reference_pages_measure(self):
        prof = json.loads(home_checks.PROFILES.read_text(encoding="utf-8"))["profiles"]["default"]["targets"]
        lo, hi = prof["pad_desktop"]
        self.assertTrue(lo <= styling.HOME_SPACE["section"] <= hi)  # desktop: the wrapper's padding is the space itself
        self.assertGreaterEqual(styling.HOME_SPACE["related"], prof["pad_floor_desktop"])
        phone = round(styling.HOME_SPACE["section"] * render.PHONE_SPACING_SCALE)  # the theme makes it 0.7 on phones
        self.assertTrue(prof["pad_phone"][0] <= phone <= prof["pad_phone"][1])

    def test_the_space_sits_on_the_theme_wrapper_which_carries_the_band_colour(self):
        res = built()
        rhythm = dict(zip([s.id for s in res.model.sections if s.id in res.template["order"]],
                          styling.home_rhythm([s.kind for s in res.model.sections if s.id in res.template["order"]])))
        checked = 0
        for sec in res.model.sections:
            want = rhythm.get(sec.id)
            wrap = res.template["sections"][sec.id]["settings"]
            if not want or want == (0, 0):
                continue
            checked += 1
            self.assertEqual((wrap["padding-block-start"], wrap["padding-block-end"]), want, sec.id)
            self.assertEqual((sec.settings.get("padding_top", 0), sec.settings.get("padding_bottom", 0)), (0, 0), sec.id)
            self.assertEqual(wrap["background_color"], sec.settings.get("background") or "", sec.id)  # a band is one colour edge to edge
        self.assertGreaterEqual(checked, 8)
        self.assertEqual(res.report["category"], "home-care")
        self.assertIn("rhythm", res.report)

    def test_lint_l20_gates_the_rhythm_and_l03_stays_a_product_page_rule(self):
        res = built()
        self.assertEqual([f for f in res.report["lint"] if f["severity"] == "error"], [])
        model = copy.copy(res.model)
        model.template = copy.deepcopy(res.template)
        faq = next(s.id for s in res.model.sections if s.kind == "faq")
        model.template["sections"][faq]["settings"]["padding-block-start"] = 24  # someone squeezes one section
        found = [f for f in rules.lint(model) if f.rule == "L20"]
        self.assertEqual(len(found), 1)
        self.assertIn(faq, found[0].message)
        self.assertFalse([f for f in rules.lint(model) if f.rule == "L03"])  # the 56 px cap is for product pages only


class TypeScaleTests(unittest.TestCase):
    def test_every_heading_sits_on_the_scale(self):
        res = built()
        for sec in res.model.sections:
            step = styling.HOME_TYPE["hero" if sec.kind == "hero_home" else "nav" if sec.block in styling.NAV_BLOCKS else "section"]
            if "heading_size_desktop" in sec.settings:
                self.assertEqual((sec.settings["heading_size_desktop"], sec.settings.get("heading_size_mobile")), step, sec.id)
            if sec.block == "faq":  # one size: the block takes 6 px off it on phones
                self.assertEqual(sec.settings["heading_size"] - 6, styling.HOME_TYPE["section"][1])


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.res = built()
        self.rule = json.loads(home_checks.PROFILES.read_text(encoding="utf-8"))["order"]

    def findings(self, template=None, report=None, rule=None):
        return home_checks.check_template(template or self.res.template, report or self.res.report, rule or self.rule)

    def test_a_fresh_build_passes_and_strong_bands_are_only_reported(self):
        found, numbers = self.findings()
        self.assertEqual(found, [])
        self.assertTrue(all(b["kind"] not in home_checks.EXEMPT for b in numbers["strong_bands"]))  # reported, never a finding

    def test_two_neighbours_with_one_colour_fail(self):
        t = copy.deepcopy(self.res.template)
        ids = [s["id"] for s in self.res.report["sections_built"] if s["kind"] not in home_checks.EXEMPT]
        order = [i for i in t["order"] if i in ids]
        a, b = order[0], order[1]
        bg = (t["sections"][a]["blocks"][t["sections"][a]["block_order"][0]]["settings"].get("background") or "#FFFFFF")
        t["sections"][b]["blocks"][t["sections"][b]["block_order"][0]]["settings"]["background"] = bg
        found, _ = self.findings(template=t)
        self.assertIn("HC2", [f["check"] for f in found])

    def test_the_order_rule(self):
        t = copy.deepcopy(self.res.template)
        ids = {s["kind"]: s["id"] for s in self.res.report["sections_built"]}
        t["order"].remove(ids["faq"])
        t["order"].insert(t["order"].index(ids["value_props_home"]), ids["faq"])  # the FAQ in the middle
        t["order"].remove(ids["story_home"])
        t["order"].insert(t["order"].index(ids["hero_home"]) + 1, ids["story_home"])  # the story before any way to shop
        found, _ = self.findings(template=t)
        msgs = " ".join(f["message"] for f in found if f["check"] == "HC4")
        self.assertIn("FAQ", msgs)
        self.assertIn("story", msgs)
        t2 = copy.deepcopy(self.res.template)
        for k in ("categories_home", "best_sellers_home"):
            t2["order"].remove(ids[k])
            t2["order"].insert(len(t2["order"]) - 1, ids[k])  # shopping pushed down the page
        self.assertIn("shop", " ".join(f["section"] for f in self.findings(template=t2)[0] if f["check"] == "HC4"))

    def test_a_heading_off_the_scale_is_found(self):
        t = copy.deepcopy(self.res.template)
        sid = next(s["id"] for s in self.res.report["sections_built"] if s["kind"] == "compare_home")
        t["sections"][sid]["blocks"][t["sections"][sid]["block_order"][0]]["settings"]["heading_size_desktop"] = 64
        self.assertIn(("HC5", sid), [(f["check"], f["section"]) for f in self.findings(template=t)[0]])

    def test_the_measured_spacing_against_the_profile(self):
        kinds = kinds_of(self.res)
        sid = next(k for k, v in kinds.items() if v == "faq")
        targets = {"pad_desktop": [80, 112], "pad_phone": [40, 66], "pad_floor_desktop": 48, "pad_floor_phone": 24}

        class Fake:
            def __init__(self, gaps):
                self.gaps = gaps

            def measure(self, doc, width, probe=None, height=None):
                top, bottom = self.gaps[width]
                return {"page_height": 6000, "sections": [{"section": sid, "text_gap_top": top, "text_gap_bottom": bottom, "full_bleed_picture": False}]}

        found, numbers = home_checks.check_rendered("<html></html>", kinds, targets, Fake({1280: (96, 100), 390: (56, 60)}))
        self.assertEqual(found, [])
        self.assertEqual(numbers["desktop"]["median"], 98)
        found, _ = home_checks.check_rendered("<html></html>", kinds, targets, Fake({1280: (28, 32), 390: (20, 22)}))
        self.assertEqual({f["check"] for f in found}, {"HC6"})
        self.assertEqual(len(found), 4)  # both medians out of range, and the section under the floor on both screens

    def test_the_cli_writes_its_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "template.json").write_text(json.dumps(self.res.template), encoding="utf-8")
            (run / "home-report.json").write_text(json.dumps(self.res.report), encoding="utf-8")
            self.assertEqual(home_checks.main(["--run", str(run)]), 0)
            out = json.loads((run / "home-checks.json").read_text(encoding="utf-8"))
            self.assertEqual((out["pass"], out["profile"]), (True, "home-care"))


class ProfileAndRenderTests(unittest.TestCase):
    def test_every_profile_has_the_spacing_targets_and_unknown_categories_get_the_default(self):
        data = json.loads(home_checks.PROFILES.read_text(encoding="utf-8"))
        for name, prof in data["profiles"].items():
            for key in ("pad_desktop", "pad_phone", "pad_floor_desktop", "pad_floor_phone"):
                self.assertIn(key, prof["targets"], name)
            self.assertTrue(prof["references"], name)
        self.assertEqual(home_checks.load_profile("home-care")[0], "home-care")
        self.assertEqual(home_checks.load_profile("garden tools")[0], "default")
        for key in ("shop_within", "first_proof_by", "faq_within_last", "proof_kinds"):
            self.assertIn(key, data["order"])

    def test_the_local_render_scales_the_wrapper_like_the_theme(self):
        self.assertEqual(render.wrapper_style({"padding-block-start": 80, "padding-block-end": 16, "background_color": "#DEEDFE"}),
                         "padding-top:max(20px,calc(var(--pb-spacing-scale) * 80px));padding-bottom:16px;background:#DEEDFE")
        doc = render.home_page_html(built().template)
        self.assertIn("--pb-spacing-scale:0.7", doc)
        self.assertIn("min-width:990px", doc)


if __name__ == "__main__":
    unittest.main()

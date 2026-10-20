"""The home page plan (Harsh, 13 Oct 2026): "the AI will decide itself according to the brand what's needed and what not", with must
sections, add-ons only when they add impact, nothing repetitive, for multi-product (99%) and single-product stores."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_home_page import brand, full_facts, home_facts  # noqa: E402
from test_home_ship import STORE, THEME, FakeTheme, Workspace, quiet  # noqa: E402

from page_builder import assemble_home, home_plan, push_page, run_home, ship_home  # noqa: E402
from page_builder.assemble_home import build_home  # noqa: E402


def plan_of(facts: dict, category: str = "beauty") -> dict[str, dict]:
    rows = home_plan.plan(build_home(brand(category), facts).report, facts)
    return {r["option"]: r for r in rows}


def decided(rows: dict, decision: str) -> set[str]:
    return {o for o, r in rows.items() if r["decision"] == decision}


class PlanTests(unittest.TestCase):
    def test_a_multi_product_store_gets_its_musts_then_the_strongest_add_ons_within_the_length_budget(self):
        rows = plan_of(full_facts())
        self.assertEqual(decided(rows, "must"), {"hero", "trust", "categories", "best-sellers", "reasons", "faq"})
        self.assertEqual(decided(rows, "add"), {"press", "before-after", "videos", "concerns", "announcement", "compare", "wave"})
        self.assertEqual(decided(rows, "skip"), {"story"})  # the weakest add-on gives way when the page is long enough
        self.assertIn("long enough", rows["story"]["reason"])
        self.assertEqual(set(rows), set(assemble_home.OPTIONS))  # every section gets exactly one decision, each with its reason
        self.assertTrue(all(r["reason"] for r in rows.values()))

    def test_the_plan_lists_the_sections_in_the_page_order(self):
        facts = full_facts()
        res = build_home(brand("beauty"), facts)
        ids = {s["kind"]: s["id"] for s in res.report["sections_built"]}
        planned = [ids[b] for b in home_plan.chosen(home_plan.plan(res.report, facts))]
        self.assertEqual(planned, [sid for sid in res.report["page_order"] if sid in planned])

    def test_a_must_section_without_its_facts_is_a_gap_to_fill_never_invented(self):
        rows = plan_of(home_facts())  # no categories, best sellers, press...
        self.assertEqual(rows["categories"]["decision"], "must_missing")
        self.assertIn("the page needs it, but", rows["categories"]["reason"])
        self.assertNotIn("categories_home", home_plan.chosen(list(rows.values())))
        self.assertEqual(rows["press"]["decision"], "skip")
        self.assertIn("press mentions", rows["press"]["reason"])

    def test_more_room_for_add_ons_when_a_must_is_missing(self):
        facts = full_facts()
        del facts["categories"]
        rows = plan_of(facts)
        self.assertEqual(rows["categories"]["decision"], "must_missing")
        self.assertEqual(rows["story"]["decision"], "add")  # the missing must leaves room

    def test_concerns_that_repeat_the_categories_are_left_out_and_the_wave_with_them(self):
        facts = full_facts()
        facts["concerns"]["items"] = [{"collection": c, "label": c.title(), "source": "demo fixture"} for c in ("face", "body")]
        rows = plan_of(facts)
        self.assertEqual(rows["concerns"]["decision"], "skip")
        self.assertIn("same collections", rows["concerns"]["reason"])
        self.assertEqual(rows["wave"]["decision"], "skip")
        self.assertIn("not on this page", rows["wave"]["reason"])

    def test_a_top_strip_that_says_what_the_trust_strip_says_is_left_out(self):
        facts = full_facts()
        facts["announcements"]["items"] = [{"text": t["text"], "source": "demo fixture"} for t in facts["trust_points"][:3]]
        rows = plan_of(facts)
        self.assertEqual(rows["announcement"]["decision"], "skip")
        self.assertIn("trust strip", rows["announcement"]["reason"])

    def test_a_single_product_store_never_gets_shop_sections_or_the_theme_product_row(self):
        facts = full_facts()
        facts["store_type"] = "single_product"
        rows = plan_of(facts)
        self.assertEqual(decided(rows, "must"), {"hero", "trust", "reasons", "faq"})
        for option in ("categories", "best-sellers", "concerns", "wave"):
            self.assertEqual(rows[option]["decision"], "skip", option)
        self.assertIn("no categories", rows["categories"]["reason"])
        page = build_home(brand("beauty"), facts, only=set(home_plan.chosen(list(rows.values()))))
        self.assertFalse(any(sid.startswith("product_list") for sid in page.report["page_order"]))
        self.assertIn("one product", " ".join(o["reason"] for o in page.report["sections_omitted"]))

    def test_the_store_type_defaults_to_multi_product(self):
        self.assertEqual(home_plan.store_type(home_facts()), "multi_product")


class AutoRunTests(Workspace):
    def test_the_list_shows_the_plan_and_writes_nothing(self):
        (self.tmp / "home-facts.json").write_text(json.dumps(home_facts()), encoding="utf-8")
        code, text = self.run_home("--list")
        self.assertEqual(code, 0)
        self.assertIn("multi-product store", text)
        self.assertRegex(text, r"MUST +hero +the first screen")
        self.assertRegex(text, r"NEEDS FACTS +categories +the page needs it, but")
        self.assertRegex(text, r"SKIP +press +needs at least 3 REAL press mentions")
        self.assertFalse(self.out.exists())

    def test_auto_builds_exactly_the_plan(self):
        code, text = self.run_home("--sections", "auto")
        self.assertEqual(code, 0, text)
        report = json.loads((self.out / "home-report.json").read_text(encoding="utf-8"))
        planned = [r["option"] for r in report["plan"] if r["decision"] in ("must", "add")]
        self.assertTrue(report["plan_used"])
        self.assertEqual(sorted(report["chosen"]), sorted(planned))
        self.assertNotIn("story", report["chosen"])

    def test_names_override_the_plan(self):
        code, text = self.run_home("--sections", "story", "--store", STORE, "--theme", THEME, access=FakeTheme())
        self.assertEqual(code, 0, text)
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        self.assertEqual(approval["sections"], ["story"])  # the plan skipped it; the person's pick wins
        self.assertFalse(json.loads((self.out / "home-report.json").read_text(encoding="utf-8"))["plan_used"])

    def test_a_fresh_auto_page_is_written_to_the_draft_with_the_plans_gaps_recorded(self):
        facts = full_facts()
        del facts["categories"]
        (self.tmp / "home-facts.json").write_text(json.dumps(facts), encoding="utf-8")
        fake = FakeTheme()
        code, text = quiet(ship_home.main, ["--client", str(self.tmp), "--sections", "auto", "--fresh", "--store", STORE, "--theme", THEME],
                           design=lambda argv: run_home.main(argv, access=fake), push=lambda argv: push_page.main(argv, access=fake))
        self.assertEqual(code, 0, text)
        written = json.loads(fake.files["templates/index.json"])
        self.assertNotIn("custom_banner", written["sections"])  # fresh: the old page is replaced (and backed up)
        result = json.loads((self.out / "ship-result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["gaps"][0]["option"], "categories")
        self.assertIn("needs facts for: categories", result["summary"])


if __name__ == "__main__":
    unittest.main()

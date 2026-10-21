"""Home pages only on request, only the chosen sections (Harsh, 13 Oct 2026): the options list, the merge into the home page as it is, and the
draft write (a stand-in theme: nothing reaches Shopify)."""
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_home_page import brand, full_facts, home_facts  # noqa: E402

from page_builder import assemble_home, push_page, run_home, ship_home  # noqa: E402
from page_builder import theme_target as tt  # noqa: E402
from page_builder.assemble import InputError  # noqa: E402
from page_builder.assemble_home import build_home  # noqa: E402
from provision.theme import ThemeError  # noqa: E402

STORE, THEME = "test-store.myshopify.com", "123456"
# the home page as it is on the store: one of OUR sections from an earlier run (edited by hand since) and one the person added themselves
CURRENT = {"sections": {"home_hero": {"type": "_blocks", "blocks": {}, "block_order": [], "settings": {"note": "edited by hand"}},
                        "custom_banner": {"type": "image-banner", "settings": {"heading": "Our own banner"}}},
           "order": ["home_hero", "custom_banner"]}


class FakeTheme:
    """Stands in for ThemeAccess: a draft theme held in memory."""

    def __init__(self, role="unpublished", base="Horizon", index=CURRENT):
        self.store, self.role, self.commands, self.pushed = STORE, role, [], []
        self.files = {"config/settings_schema.json": json.dumps([{"name": "theme_info", "theme_name": base, "theme_version": "4.2.0"}]),
                      "templates/product.json": "{}", "templates/index.json": json.dumps(index)}

    def themes(self, theme_id):
        return [{"id": int(theme_id), "name": "Draft copy", "role": self.role}]

    def pull(self, theme_id, files, dest):
        self.commands.append(["pull", *files])
        for f in files:
            if f in self.files:
                (dest / f).parent.mkdir(parents=True, exist_ok=True)
                (dest / f).write_text(self.files[f], encoding="utf-8")
        return dest

    def push_product_template(self, theme_id, staging, file):
        self.pushed.append(file)
        self.files[file] = (staging / file).read_text(encoding="utf-8")
        return {"role": self.role, "name": "Draft copy"}


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        code = fn(*a, **k)
    return code, out.getvalue() + err.getvalue()


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "brand.json").write_text(json.dumps(brand("beauty")), encoding="utf-8")
        (self.tmp / "home-facts.json").write_text(json.dumps(full_facts()), encoding="utf-8")
        self.out = self.tmp / "home-run"

    def run_home(self, *extra, access=None):
        argv = ["--brand", str(self.tmp / "brand.json"), "--facts", str(self.tmp / "home-facts.json"), "--out", str(self.out), *extra]
        return quiet(run_home.main, argv, access=access)


class OptionsTests(Workspace):
    def test_the_options_show_every_section_ready_or_with_the_facts_it_misses(self):
        opts = assemble_home.options(build_home(brand("beauty"), home_facts()))
        self.assertTrue(next(o for o in opts if o["option"] == "hero")["ready"])
        self.assertIn("press mentions", next(o for o in opts if o["option"] == "press")["reason"])
        self.assertEqual({o["option"] for o in opts}, set(assemble_home.OPTIONS))

    def test_names_are_picked_by_their_short_names_and_an_unknown_name_stops(self):
        self.assertEqual(assemble_home.pick("hero, best-sellers"), ["hero_home", "best_sellers_home"])
        self.assertEqual(len(assemble_home.pick("all")), len(assemble_home.OPTIONS))
        with self.assertRaises(InputError):
            assemble_home.pick("hero,banner")

    def test_a_store_run_needs_the_chosen_sections(self):
        code, text = self.run_home("--store", STORE, "--theme", THEME, access=FakeTheme())
        self.assertEqual(code, 1)
        self.assertIn("--sections", text)


class MergeTests(unittest.TestCase):
    def test_only_the_chosen_sections_change_and_everything_else_stays_exactly_as_it_was(self):
        page = build_home(brand("beauty"), full_facts()).template
        merged, changes = assemble_home.merge(CURRENT, page, ["home_bestsellers"])
        self.assertEqual(merged["sections"]["home_hero"], CURRENT["sections"]["home_hero"])  # not chosen: the hand edit stays
        self.assertEqual(merged["sections"]["custom_banner"], CURRENT["sections"]["custom_banner"])
        self.assertEqual(merged["order"], ["home_hero", "home_bestsellers", "custom_banner"])  # next to its neighbour from the built page
        self.assertEqual(changes, [{"section": "home_bestsellers", "change": "added", "after": "home_hero"}])
        merged, changes = assemble_home.merge(CURRENT, page, ["home_hero"])
        self.assertEqual(merged["sections"]["home_hero"], page["sections"]["home_hero"])  # chosen: replaced where it stands
        self.assertEqual(merged["order"], CURRENT["order"])
        self.assertEqual(changes, [{"section": "home_hero", "change": "replaced"}])
        self.assertEqual(CURRENT["sections"]["home_hero"]["settings"], {"note": "edited by hand"})  # the input is never changed

    def test_a_first_section_on_an_empty_page_goes_to_the_top(self):
        page = build_home(brand("beauty"), full_facts()).template
        merged, _ = assemble_home.merge({"sections": {}, "order": []}, page, ["home_announce", "home_hero"])
        self.assertEqual(merged["order"], ["home_announce", "home_hero"])


class StoreRunTests(Workspace):
    def test_a_store_run_merges_into_the_draft_home_page_and_prepares_a_guarded_write(self):
        fake = FakeTheme()
        code, text = self.run_home("--sections", "best-sellers,hero", "--store", STORE, "--theme", THEME, access=fake)
        self.assertEqual(code, 0, text)
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        self.assertTrue(approval["pushable"])
        self.assertEqual(approval["file"], "templates/index.json")
        self.assertEqual(approval["base_sha256"], tt.sha256(fake.files["templates/index.json"].encode("utf-8")))
        self.assertEqual(approval["sections"], ["hero", "best-sellers"])
        merged = json.loads((self.out / "template.json").read_text(encoding="utf-8"))
        self.assertEqual(merged["sections"]["custom_banner"], CURRENT["sections"]["custom_banner"])
        self.assertEqual(merged["order"], ["home_hero", "home_bestsellers", "custom_banner"])
        self.assertEqual(fake.pushed, [])  # run_home never writes

    def test_a_section_is_switched_off_where_it_stands_and_kept_in_the_file(self):
        # Harsh, 21 Oct 2026: the theme's announcement bar now carries the lines on every page, so the home page's own strip goes
        page = {"sections": {**copy.deepcopy(CURRENT["sections"]), "home_announce": {"type": "_blocks", "blocks": {}, "settings": {}}},
                "order": ["home_announce"] + CURRENT["order"]}
        fake = FakeTheme(index=page)
        code, text = self.run_home("--remove", "announcement", "--store", STORE, "--theme", THEME, access=fake)
        self.assertEqual(code, 0, text)
        merged = json.loads((self.out / "template.json").read_text(encoding="utf-8"))
        self.assertTrue(merged["sections"]["home_announce"]["disabled"])
        self.assertEqual(merged["order"], page["order"])  # nothing moved, nothing deleted
        self.assertEqual(merged["sections"]["home_hero"], CURRENT["sections"]["home_hero"])  # every other section exactly as it was
        self.assertEqual(json.loads((self.out / "approval.json").read_text(encoding="utf-8"))["changes"],
                         [{"section": "home_announce", "change": "switched off"}])

    def test_a_fresh_page_holds_only_the_chosen_sections_and_the_old_page_is_backed_up(self):
        fake = FakeTheme()
        code, text = self.run_home("--sections", "hero,faq", "--fresh", "--store", STORE, "--theme", THEME, access=fake)
        self.assertEqual(code, 0, text)
        page = json.loads((self.out / "template.json").read_text(encoding="utf-8"))
        # only the chosen sections, plus the theme's own product row: no DTJ product rows were chosen, and a shop's home shows products
        self.assertEqual([page["order"][0], page["order"][-1]], ["home_hero", "dtj_faq"])
        self.assertEqual([page["sections"][s]["type"] for s in page["order"][1:-1]], ["product-list"])
        self.assertNotIn("custom_banner", page["sections"])
        backups = list(self.out.glob("backup-*/templates/index.json"))
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), CURRENT)
        self.assertTrue(json.loads((self.out / "approval.json").read_text(encoding="utf-8"))["base_sha256"])

    def test_a_live_theme_or_a_non_horizon_theme_is_refused(self):
        for fake, why in ((FakeTheme(role="main"), "live"), (FakeTheme(base="Dawn"), "Horizon")):
            code, text = self.run_home("--sections", "hero", "--store", STORE, "--theme", THEME, access=fake)
            self.assertEqual(code, 1, why)
            self.assertFalse((self.out / "approval.json").exists(), why)

    def test_a_chosen_section_without_its_facts_is_named_and_the_rest_still_builds(self):
        facts = full_facts()
        del facts["press"]
        (self.tmp / "home-facts.json").write_text(json.dumps(facts), encoding="utf-8")
        code, text = self.run_home("--sections", "press,hero", "--store", STORE, "--theme", THEME, access=FakeTheme())
        self.assertEqual(code, 0)
        self.assertIn("not built press", text)
        self.assertEqual(json.loads((self.out / "approval.json").read_text(encoding="utf-8"))["sections"], ["hero"])


class WriteTests(Workspace):
    def test_ship_home_writes_only_the_home_page_of_the_draft_and_reads_it_back(self):
        fake = FakeTheme()
        design = lambda argv: run_home.main(argv, access=fake)  # noqa: E731
        push = lambda argv: push_page.main(argv, access=fake)  # noqa: E731
        code, text = quiet(ship_home.main, ["--client", str(self.tmp), "--sections", "hero,best-sellers", "--store", STORE, "--theme", THEME],
                           design=design, push=push)
        self.assertEqual(code, 0, text)
        self.assertEqual(fake.pushed, ["templates/index.json"])
        written = json.loads(fake.files["templates/index.json"])
        self.assertEqual(written["sections"]["custom_banner"], CURRENT["sections"]["custom_banner"])
        result = json.loads((self.out / "ship-result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["page_status"], "written to draft")
        self.assertEqual(result["preview_url"], f"https://{STORE}/?preview_theme_id={THEME}")
        log = (self.out / "action-log.jsonl").read_text(encoding="utf-8")
        self.assertIn("home pages included", log)
        self.assertIn("write templates/index.json to draft theme", log)

    def test_a_home_page_changed_in_the_editor_after_the_merge_is_never_overwritten(self):
        fake = FakeTheme()
        code, _ = self.run_home("--sections", "hero", "--store", STORE, "--theme", THEME, access=fake)
        self.assertEqual(code, 0)
        edited = copy.deepcopy(CURRENT)
        edited["sections"]["custom_banner"]["settings"]["heading"] = "Changed in the editor a minute ago"
        fake.files["templates/index.json"] = json.dumps(edited)
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        code, text = quiet(push_page.main, ["--out", str(self.out), "--approve", approval["approve_code"], "--approved-by", "Test",
                                            "--allow-demo", "--allow-samples"], access=fake)
        self.assertEqual(code, 1)
        self.assertIn("changed in the theme since this update was prepared", text)
        self.assertEqual(fake.pushed, [])

    def test_ship_home_without_chosen_sections_changes_nothing(self):
        fake = FakeTheme()
        with self.assertRaises(SystemExit):
            quiet(ship_home.main, ["--client", str(self.tmp), "--store", STORE, "--theme", THEME],
                  design=lambda argv: run_home.main(argv, access=fake), push=lambda argv: push_page.main(argv, access=fake))
        self.assertEqual(fake.pushed, [])

    def test_the_theme_tool_writes_page_templates_only(self):
        fake_cli = lambda cmd, env: __import__("subprocess").CompletedProcess(cmd, 0, '{"theme": {"id": 1, "role": "unpublished"}}', "")  # noqa: E731
        access = tt.ThemeAccess(STORE, "shptka_test", runner=fake_cli)
        for ok in ("templates/index.json", "templates/product.json", "templates/product.dtj-x.json"):
            access.push_product_template(THEME, self.tmp, ok)
        # the header and footer groups joined on 21 Oct 2026 (run_chrome, a person's yes every time); every other section file stays out
        for bad in ("templates/page.json", "sections/main-product.json", "sections/header.liquid", "layout/theme.liquid", "templates/index.alt.json"):
            with self.assertRaises(ThemeError, msg=bad):
                access.push_product_template(THEME, self.tmp, bad)


if __name__ == "__main__":
    unittest.main()

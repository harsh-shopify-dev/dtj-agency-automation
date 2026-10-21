"""Collection page (Harsh, 20 Oct 2026: "design the collection page adding that section and ensure all the ratings and everything appears
perfectly"): the builder, the merge into the theme's collection template as it is, the template checks, learning the app's address from a
placed block, and the Tier 2 write (a stand-in theme: nothing reaches Shopify)."""
import contextlib
import copy
import fnmatch
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_home_page import brand as _brand  # noqa: E402
from test_home_page import full_facts, home_facts  # noqa: E402

from page_builder import assemble_collection as ac  # noqa: E402
from page_builder import catalog, collection_checks, push_page, run_collection  # noqa: E402
from page_builder import theme_target as tt  # noqa: E402
from page_builder.assemble import InputError  # noqa: E402
from page_builder.catalog import Catalog  # noqa: E402
from provision.theme import ThemeError  # noqa: E402

STORE, THEME = "test-store.myshopify.com", "123456"


def brand():
    return _brand("beauty")  # the block's own category (Proeffex)

UUID = "01a1aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee"
KNOWN = {**catalog.registry(), ac.LIST_APP: {"uuid": UUID, "folder": catalog.registry()[ac.LIST_APP]["folder"]}}
POINTS = [{"text": "Free shipping above Rs. 499", "source": "shipping policy page"}, {"text": "Cash on delivery", "source": "checkout settings"},
          {"text": "7-day returns", "source": "refund policy page"}]
# the theme's collection template as Horizon 4.2.0 ships it (title section + main-collection grid) plus a list placed by hand in the editor
PLACED = f"shopify://apps/dtj-collection/blocks/dtj-product-list/{UUID}"
CURRENT = {"sections": {
    "section": {"type": "section", "blocks": {"t": {"type": "text", "settings": {"text": "<h1>{{ closest.collection.title }}</h1>"}}}, "settings": {}},
    "main": {"type": "main-collection", "blocks": {}, "settings": {}},
    "placed_list": {"type": "_blocks", "blocks": {"b": {"type": PLACED, "settings": {"collection": "{{ closest.collection }}"}}}, "settings": {}},
    "you_may_like": {"type": "product-list", "blocks": {}, "settings": {"note": "kept"}}},
    "order": ["section", "main", "placed_list", "you_may_like"]}


def build(**kw):
    return ac.build_collection(brand(), home_facts(), kw.pop("page", {}), catalog=kw.pop("catalog", Catalog(KNOWN)), **kw)


class FakeTheme:
    def __init__(self, role="unpublished", base="Horizon", collection=CURRENT):
        self.store, self.role, self.commands, self.pushed = STORE, role, [], []
        self.files = {"config/settings_schema.json": json.dumps([{"name": "theme_info", "theme_name": base, "theme_version": "4.2.0"}]),
                      "templates/product.json": "{}", "templates/collection.json": json.dumps(collection)}

    def themes(self, theme_id):
        return [{"id": int(theme_id), "name": "Draft copy", "role": self.role}]

    def pull(self, theme_id, files, dest):
        self.commands.append(["pull", *files])
        for name, text in self.files.items():
            if any(fnmatch.fnmatch(name, f) for f in files):
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                (dest / name).write_text(text, encoding="utf-8")
        return dest

    def push_product_template(self, theme_id, staging, file):
        if not tt.PAGE_FILES.fullmatch(file):
            raise ThemeError("not a page file")
        self.pushed.append(file)
        self.files[file] = (staging / file).read_text(encoding="utf-8")
        return {"role": self.role, "name": "Draft copy"}


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        code = fn(*a, **k)
    return code, out.getvalue() + err.getvalue()


class BuildTests(unittest.TestCase):
    def test_the_page_is_the_collections_own_title_then_every_product_of_that_collection(self):
        r = build()
        self.assertEqual(r.template["order"], ["dtj_collection_header", "dtj_collection_products"])
        head = r.template["sections"]["dtj_collection_header"]
        self.assertEqual(head["blocks"]["title"]["settings"]["text"], "<h1>{{ closest.collection.title }}</h1>")  # one template, every collection
        self.assertEqual(head["blocks"]["description"]["settings"]["text"], "{{ closest.collection.description }}")
        block = next(iter(r.template["sections"]["dtj_collection_products"]["blocks"].values()))
        self.assertEqual(block["type"], f"shopify://apps/dtj-collection/blocks/dtj-product-list/{UUID}")
        s = block["settings"]
        self.assertNotIn("collection", s)  # left empty: the block shows the page's own collection, never a fixed one
        self.assertEqual((s["max_products"], s["show_sort"], s["show_heading"], s["pf_hide_no_reviews"]), (50, True, False, True))
        self.assertEqual(r.report["problems"], [])
        self.assertFalse(r.report["pending_address"])

    def test_the_card_look_is_left_exactly_as_the_original(self):
        s = next(iter(build().template["sections"]["dtj_collection_products"]["blocks"].values()))["settings"]
        for key in [k for k in s if k.startswith("pf_")]:
            self.assertEqual(key, "pf_hide_no_reviews", "only the 0-review rule is set; every card style setting keeps the original's default")

    def test_colour_is_placed_title_on_the_page_colour_products_on_the_brands_soft_tint_and_valid_for_the_theme(self):
        from page_builder import direction
        roles = direction.derive(brand(), None).roles
        r = build()
        head = r.template["sections"]["dtj_collection_header"]
        self.assertEqual(head["settings"]["background_color"], roles["bg"])
        self.assertEqual(r.template["sections"]["dtj_collection_products"]["settings"]["background_color"], roles["panel"])  # white cards stand out
        self.assertEqual((head["settings"]["padding-block-start"], head["settings"]["padding-block-end"]), ac.COLLECTION_SPACE["header"])
        self.assertEqual(ac.check_theme_settings("section", head["settings"]), [])
        bad = dict(head["settings"], section_width="wide")
        self.assertTrue(ac.check_theme_settings("section", bad))  # a value Horizon does not know is caught before Shopify refuses the file

    def test_the_links_row_shows_the_stores_own_collections_between_the_title_and_the_products(self):
        self.assertNotIn("collection_nav", build().template["order"])  # no categories in the facts: left out, with the reason
        r = ac.build_collection(brand(), full_facts(), {}, catalog=Catalog(KNOWN))
        self.assertEqual(r.template["order"], ["dtj_collection_header", "collection_nav", "dtj_collection_products"])
        nav = next(iter(r.template["sections"]["collection_nav"]["blocks"].values()))
        self.assertTrue(nav["type"].startswith("shopify://apps/dtj-commerce/blocks/dtj-circle-menu/"))
        self.assertEqual(nav["settings"]["collections"], ["face", "body", "hair", "kits"])  # the store's real collections, their own pictures and names
        self.assertEqual(nav["settings"]["heading"], "")  # navigation, not a headline: the H1 above is the heading
        self.assertEqual(r.report["problems"], [])
        head = r.template["sections"]["dtj_collection_header"]["settings"]
        self.assertEqual((head["padding-block-start"], head["padding-block-end"]), ac.COLLECTION_SPACE["header_with_nav"])
        final, _ = ac.merge(CURRENT, r.template)
        self.assertEqual(collection_checks.check_template(final), [])

    def test_a_trust_strip_needs_three_store_wide_points_with_sources(self):
        r = build()
        self.assertNotIn("collection_trust", r.template["order"])
        self.assertTrue(any("STORE-WIDE" in o["reason"] for o in r.report["sections_omitted"] if o["section"] == "collection_trust"))
        r = build(page={"store_points": POINTS})
        self.assertIn("collection_trust", r.template["order"])
        self.assertEqual(r.report["provenance"]["collection_trust.text_1"]["kind"], "fact")
        with self.assertRaises(InputError):
            build(page={"store_points": POINTS[:2] + [{"text": "No source"}]})

    def test_products_are_always_on_the_page_and_names_are_checked(self):
        with self.assertRaises(InputError):
            build(chosen=("header",))
        with self.assertRaises(InputError):
            build(chosen=("products", "banner"))
        self.assertEqual(build(chosen=("products",)).template["order"], ["dtj_collection_products"])

    def test_an_unknown_app_address_lets_the_page_be_looked_at_never_written(self):
        r = ac.build_collection(brand(), home_facts(), {}, catalog=Catalog({**catalog.registry()}))
        if catalog.registry()[ac.LIST_APP]["uuid"] != "pending":
            self.skipTest("the real registry already knows the address")
        self.assertTrue(r.report["pending_address"])
        self.assertTrue(any("PENDING ADDRESS" in p for p in r.report["problems"]))
        self.assertIn("CC6", [f["check"] for f in collection_checks.check_template(r.template)])


class MergeTests(unittest.TestCase):
    def test_the_theme_grid_and_the_old_title_and_a_hand_placed_list_are_switched_off_and_kept(self):
        final, changes = ac.merge(CURRENT, build().template)
        self.assertEqual(final["order"][:2], ["dtj_collection_header", "dtj_collection_products"])
        for sid in ("section", "main", "placed_list"):
            self.assertTrue(final["sections"][sid]["disabled"], sid)  # still in the file: undo = switch it on
        self.assertNotIn("disabled", final["sections"]["you_may_like"])  # another product row of the theme is not this collection's grid
        self.assertEqual(final["sections"]["you_may_like"], CURRENT["sections"]["you_may_like"])
        self.assertEqual({c["section"] for c in changes if c["change"] == "switched off"}, {"section", "main", "placed_list"})
        self.assertEqual(collection_checks.check_template(final), [])

    def test_a_second_run_replaces_our_sections_where_they_stand(self):
        once, _ = ac.merge(CURRENT, build().template)
        twice, changes = ac.merge(once, build().template)
        self.assertEqual(once["order"], twice["order"])
        self.assertEqual({c["change"] for c in changes}, {"replaced"})


class CheckTests(unittest.TestCase):
    def final(self):
        return ac.merge(CURRENT, build().template)[0]

    def test_each_check_catches_its_fault(self):
        t = self.final()
        list_block = next(iter(t["sections"]["dtj_collection_products"]["blocks"].values()))
        list_block["settings"]["collection"] = "summer-sale"
        self.assertIn("CC2", [f["check"] for f in collection_checks.check_template(t)])
        t = self.final()
        t["sections"]["main"].pop("disabled")
        self.assertIn("CC3", [f["check"] for f in collection_checks.check_template(t)])
        t = self.final()
        t["sections"]["section"].pop("disabled")
        self.assertIn("CC4", [f["check"] for f in collection_checks.check_template(t)])
        t = self.final()
        t["sections"]["placed_list"].pop("disabled")
        self.assertIn("CC1", [f["check"] for f in collection_checks.check_template(t)])
        t = self.final()
        next(iter(t["sections"]["dtj_collection_products"]["blocks"].values()))["settings"]["max_products"] = 16
        self.assertIn("CC5", [f["check"] for f in collection_checks.check_template(t)])


class RunAndWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.client = self.tmp / "client"
        self.client.mkdir()
        (self.client / "brand.json").write_text(json.dumps(brand()), encoding="utf-8")
        (self.client / "home-facts.json").write_text(json.dumps(home_facts()), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_store(self, fake):
        with mock.patch.object(catalog, "registry", lambda path=None: KNOWN):
            return quiet(run_collection.main, ["--client", str(self.client), "--store", STORE, "--theme", THEME], access=fake)

    def test_design_merge_and_the_tier2_write_of_templates_collection_json(self):
        fake = FakeTheme()
        code, out = self.run_store(fake)
        self.assertEqual(code, 0, out)
        approval = json.loads((self.client / "collection-run" / "approval.json").read_text(encoding="utf-8"))
        self.assertEqual(approval["file"], "templates/collection.json")
        self.assertTrue(approval["pushable"])
        self.assertFalse(approval["standing_rule"])  # a collection page is not covered by Harsh's standing draft rule
        code, out = quiet(push_page.main, ["--out", str(self.client / "collection-run"), "--approve", approval["approve_code"],
                                           "--approved-by", "Harsh"], access=fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(fake.pushed, ["templates/collection.json"])
        written = json.loads(fake.files["templates/collection.json"])
        self.assertTrue(written["sections"]["main"]["disabled"])
        self.assertEqual(collection_checks.check_template(written), [])

    def test_a_live_theme_or_a_changed_page_is_never_written(self):
        code, out = self.run_store(FakeTheme(role="main"))
        self.assertEqual(code, 1)
        fake = FakeTheme()
        self.run_store(fake)
        approval = json.loads((self.client / "collection-run" / "approval.json").read_text(encoding="utf-8"))
        fake.files["templates/collection.json"] = json.dumps({"sections": {}, "order": []})  # someone edited the page in the editor since
        code, out = quiet(push_page.main, ["--out", str(self.client / "collection-run"), "--approve", approval["approve_code"],
                                           "--approved-by", "Harsh"], access=fake)
        self.assertEqual(code, 1)
        self.assertEqual(fake.pushed, [])

    def test_the_page_builder_writes_collection_templates_and_nothing_else_new(self):
        for ok in ("templates/collection.json", "templates/collection.sale.json", "templates/index.json", "templates/product.x.json"):
            self.assertTrue(tt.PAGE_FILES.fullmatch(ok), ok)
        for bad in ("templates/page.json", "templates/collection.json.bak", "sections/header-group.json.bak", "sections/overlay-group.json",
                    "config/settings_data.json"):
            self.assertFalse(tt.PAGE_FILES.fullmatch(bad), bad)

    def test_learning_the_apps_address_from_a_block_placed_in_the_editor(self):
        reg_path = self.tmp / "registry.json"
        reg = copy.deepcopy(json.loads((Path(catalog.__file__).parent / "registry.json").read_text(encoding="utf-8")))
        reg["apps"][ac.LIST_APP]["uuid"] = "pending"
        reg_path.write_text(json.dumps(reg), encoding="utf-8")
        found = run_collection.learn_uuid(FakeTheme(), THEME, self.tmp / "pull", registry_path=reg_path, clients_dir=self.tmp)
        self.assertEqual((found["handle"], found["uuid"], found["collection_setting"]), ("dtj-collection", UUID, "{{ closest.collection }}"))
        self.assertEqual(json.loads(reg_path.read_text(encoding="utf-8"))["apps"][ac.LIST_APP]["uuid"], UUID)
        with self.assertRaises(ThemeError):
            run_collection.learn_uuid(FakeTheme(collection={"sections": {}, "order": []}), THEME, self.tmp / "pull2", registry_path=reg_path,
                                      clients_dir=self.tmp)


if __name__ == "__main__":
    unittest.main()

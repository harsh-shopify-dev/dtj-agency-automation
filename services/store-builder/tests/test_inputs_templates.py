import json
import tempfile
import unittest
from pathlib import Path

from provision import apps, products, run, templates

BRAND = {"client_id": "test-brand", "brand_name": "Test Brand", "store_domain": "test-brand.myshopify.com",
         "home": {"product_list_collection": "all", "hero_image": "hero.jpg"}}
SHEET = {"products": [{"handle": "sample-one", "title": "Sample One", "price": "499.00", "sku": "S-1",
                       "images": [{"file": "one.jpg", "alt": "Sample one front"}]}]}

INDEX = """/*
 * auto-generated header
 */
{
  "sections": {
    "hero_abc": {"type": "hero", "settings": {"media_type_1": "image"}},
    "product_list_xyz": {"type": "product-list", "settings": {"collection": "all", "max_products": 8}}
  },
  "order": ["hero_abc", "product_list_xyz"]
}
"""


def images_dir(names):
    d = tempfile.TemporaryDirectory()
    for n in names:
        (Path(d.name) / n).write_bytes(b"x" * 10)
    return d


class InputTests(unittest.TestCase):
    def test_valid_inputs_plan(self):
        with images_dir(["hero.jpg", "one.jpg"]) as d:
            out = run.plan(BRAND, SHEET, Path(d))
        self.assertEqual(out["stage_3_products"][0]["create"]["product"]["status"], "DRAFT")
        self.assertIn("--unpublished", out["stage_2_theme"])
        self.assertEqual(out["needs_human_input"], [])

    def test_missing_price_is_rejected_not_guessed(self):
        bad = {"products": [{"handle": "a", "title": "A"}]}
        with images_dir([]) as d, self.assertRaises(run.InputError):
            run.plan(BRAND, bad, Path(d))

    def test_bad_handle_and_duplicate_handles(self):
        with images_dir(["hero.jpg", "one.jpg"]) as d:
            with self.assertRaises(run.InputError):
                run.plan(BRAND, {"products": [{**SHEET["products"][0], "handle": "Bad Handle"}]}, Path(d))
            with self.assertRaises(run.InputError):
                run.plan(BRAND, {"products": SHEET["products"] * 2}, Path(d))

    def test_image_path_cannot_escape_the_folder(self):
        with images_dir([]) as d, self.assertRaises(ValueError):
            products.staged_upload_variables(Path(d), ["../secret.png"])

    def test_missing_image_is_an_error(self):
        with images_dir(["hero.jpg"]) as d, self.assertRaises(FileNotFoundError):
            run.plan(BRAND, SHEET, Path(d))

    def test_unknown_facts_are_listed_for_a_human(self):
        sheet = {"products": [{**SHEET["products"][0], "description_html": "[[TODO]]"}]}
        with images_dir(["hero.jpg", "one.jpg"]) as d:
            self.assertEqual(run.plan(BRAND, sheet, Path(d))["needs_human_input"], ["sample-one"])

    def test_live_store_domain_pattern_is_enforced(self):
        with images_dir([]) as d, self.assertRaises(run.InputError):
            run.plan({**BRAND, "store_domain": "shop.example.com"}, SHEET, Path(d))

    def test_variant_variables(self):
        v = products.variant_variables("gid://p/1", "gid://v/1", {**SHEET["products"][0], "compare_at_price": "599.00"})
        self.assertEqual(v["variants"][0]["compareAtPrice"], "599.00")
        self.assertEqual(v["variants"][0]["inventoryItem"], {"sku": "S-1"})

    def test_circuit_breaker_opens_on_third_failure(self):
        b = run.CircuitBreaker()
        self.assertFalse(b.failed("push"))
        self.assertFalse(b.failed("push"))
        self.assertTrue(b.failed("push"))
        b.ok("push")
        self.assertFalse(b.failed("push"))

    def test_app_checklist_never_invents_apps(self):
        text = apps.checklist_markdown(BRAND)
        self.assertIn("[[TODO: choose app]]", text)


class TemplateTests(unittest.TestCase):
    def test_bindings_fill_collection_and_hero_and_keep_header(self):
        out, changes = templates.apply_bindings({"templates/index.json": INDEX}, [
            {"file": "templates/index.json", "section_type": "product-list", "setting": "collection", "value": "featured"},
            {"file": "templates/index.json", "section_type": "hero", "setting": "image_1", "value": "shopify://shop_images/hero.jpg"}])
        text = out["templates/index.json"]
        self.assertTrue(text.startswith("/*\n * auto-generated header"))
        _, data = templates.load(text)
        self.assertEqual(data["sections"]["product_list_xyz"]["settings"]["collection"], "featured")
        self.assertEqual(data["sections"]["hero_abc"]["settings"]["image_1"], "shopify://shop_images/hero.jpg")
        self.assertEqual(data["sections"]["product_list_xyz"]["settings"]["max_products"], 8)  # untouched
        self.assertEqual({c["setting"] for c in changes}, {"collection", "image_1"})

    def test_unchanged_value_means_no_file_to_push(self):
        out, changes = templates.apply_bindings({"templates/index.json": INDEX}, [
            {"file": "templates/index.json", "section_type": "product-list", "setting": "collection", "value": "all"}])
        self.assertEqual((out, changes), ({}, []))

    def test_missing_section_type_fails_loudly(self):
        with self.assertRaises(templates.TemplateError):
            templates.apply_bindings({"templates/index.json": INDEX}, [
                {"file": "templates/index.json", "section_type": "nope", "setting": "x", "value": 1}])

    def test_bindings_from_brand_validate_values(self):
        self.assertEqual(len(templates.bindings_from_brand(BRAND)), 2)
        with self.assertRaises(templates.TemplateError):
            templates.bindings_from_brand({"home": {"product_list_collection": "Bad Handle!"}})
        with self.assertRaises(templates.TemplateError):
            templates.bindings_from_brand({"home": {"hero_image": "../x.jpg"}})


class CliTests(unittest.TestCase):
    def test_dry_run_writes_plan_log_and_checklist_and_sends_nothing(self):
        with images_dir(["hero.jpg", "one.jpg"]) as imgs, tempfile.TemporaryDirectory() as work:
            w = Path(work)
            (w / "b.json").write_text(json.dumps(BRAND))
            (w / "p.json").write_text(json.dumps(SHEET))
            code = run.main(["--brand", str(w / "b.json"), "--products", str(w / "p.json"), "--images", imgs, "--out", str(w / "out")])
            self.assertEqual(code, 0)
            self.assertTrue((w / "out" / "dry-run-plan.json").is_file())
            self.assertTrue((w / "out" / "app-checklist.md").is_file())
            rows = [json.loads(l) for l in (w / "out" / "action-log.jsonl").read_text().splitlines()]
            self.assertTrue(rows and all(r["result"] == "dry_run" for r in rows))

    def test_bad_input_exits_2_and_logs_blocked(self):
        with images_dir([]) as imgs, tempfile.TemporaryDirectory() as work:
            w = Path(work)
            (w / "b.json").write_text(json.dumps(BRAND))
            (w / "p.json").write_text(json.dumps({"products": []}))
            code = run.main(["--brand", str(w / "b.json"), "--products", str(w / "p.json"), "--images", imgs, "--out", str(w / "out")])
            self.assertEqual(code, 2)
            self.assertIn('"blocked"', (w / "out" / "action-log.jsonl").read_text())


if __name__ == "__main__":
    unittest.main()

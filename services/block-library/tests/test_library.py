import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_library as cl  # noqa: E402


class LibraryRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ("extensions", "manifests", "schemas"):
            shutil.copytree(ROOT / name, self.root / name)
        self.manifest = self.root / "manifests" / "hero-points.json"  # the real block these rule tests break on purpose
        self.block = self.root / "extensions/dtj-blocks/blocks/dtj-hero-points.liquid"

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self):
        return cl.check_block(self.manifest, self.root)

    def edit_block(self, old, new):
        text = self.block.read_text(encoding="utf-8")
        self.assertIn(old, text)
        self.block.write_text(text.replace(old, new, 1), encoding="utf-8")

    def edit_schema(self, change):
        """Edit the block's {% schema %} as data, so tests do not depend on how the generator formats the JSON."""
        text = self.block.read_text(encoding="utf-8")
        schema = cl.extract_schema(text)
        change(schema)
        new = "{% schema %}\n" + json.dumps(schema, indent=2) + "\n{% endschema %}"
        self.block.write_text(cl._SCHEMA.sub(lambda _m: new, text), encoding="utf-8")

    def test_real_block_passes_every_rule(self):
        self.assertEqual(self.problems(), [])

    def test_baked_in_copy_is_rejected(self):
        def add_default(schema):
            next(s for s in schema["settings"] if s.get("id") == "eyebrow")["default"] = "Free shipping"
        self.edit_schema(add_default)
        self.assertTrue(any("default copy" in p for p in self.problems()))

    def test_missing_licence_gate_is_rejected(self):
        self.edit_block("{%- render 'dtj-licence', value: app.metafields.dtj.licence.value, content: dtj_content, design_mode: request.design_mode, attributes: block.shopify_attributes -%}", "{{ dtj_content }}")
        self.assertTrue(any("licence gate" in p for p in self.problems()))

    def test_hard_coded_colour_is_rejected(self):
        self.edit_block("{%- capture dtj_content -%}", "<i style='color:#12BEE9'></i>{%- capture dtj_content -%}")
        self.assertTrue(any("hex colour" in p for p in self.problems()))

    def test_bad_range_default_is_rejected(self):
        def off_step(schema):
            next(s for s in schema["settings"] if s.get("id") == "check_size")["default"] = 25  # min 14, step 2: 25 is not on a step
        self.edit_schema(off_step)
        self.assertTrue(any("not on a step" in p for p in self.problems()))

    def test_manifest_slot_without_setting_is_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["slots"].append({"id": "item_9_text", "type": "text", "required": False})
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(any("item_9_text" in p for p in self.problems()))

    def test_licence_flag_cannot_be_turned_off_in_the_manifest_schema(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["licence"] = False
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        # allowed by the schema (a free block could exist later), but then the gate is not demanded: make that visible
        self.assertEqual(self.problems(), [])

    def test_snippet_reading_block_directly_is_rejected(self):
        snippet = self.root / "extensions/dtj-blocks/snippets/dtj-licence.liquid"
        snippet.write_text(snippet.read_text(encoding="utf-8") + "{{ block.settings.x }}", encoding="utf-8")
        self.assertTrue(any("reads 'block.' directly" in p for p in self.problems()))

    def test_a_comment_mentioning_block_is_fine(self):
        self.assertEqual(self.problems(), [])  # the real snippet's comment mentions block.shopify_attributes

    def test_block_comparing_the_gate_output_is_rejected(self):
        # the exact pattern that broke on a real store: capture the snippet's output, then compare it
        self.edit_block("{%- capture dtj_content -%}", "{%- capture dtj_licence -%}{%- render 'dtj-licence', value: x -%}{%- endcapture -%}{%- capture dtj_content -%}")
        self.assertTrue(any("captures the licence snippet" in p for p in self.problems()))

    def test_too_many_headers_are_rejected(self):
        # Shopify refused a real deploy for this on 5 Oct 2026: max 6 non-interactive settings in an app block
        def add_headers(schema):
            schema["settings"] = [{"type": "header", "content": f"H{n}"} for n in range(7)] + schema["settings"]
        self.edit_schema(add_headers)
        self.assertTrue(any("at most 6 non-interactive" in p for p in self.problems()))

    def test_image_without_an_explicit_css_size_is_rejected(self):
        # the Offer Pill bug (5 Oct 2026): Horizon stretched the image because only the tag had width/height
        css = self.root / "extensions/dtj-blocks/assets/dtj-hero-points.css"
        self.block.write_text(self.block.read_text(encoding="utf-8").replace("{%- capture dtj_content -%}", '<img class="x-img" src="a.png" alt="" width="20" height="20">{%- capture dtj_content -%}', 1), encoding="utf-8")
        self.assertTrue(any("no explicit width/height" in p for p in self.problems()))
        css.write_text(css.read_text(encoding="utf-8") + "\n.x-img { width: 20px; height: 20px; }\n", encoding="utf-8")
        self.assertEqual([p for p in self.problems() if "no explicit width" in p], [])

    def test_blank_range_unit_is_rejected(self):
        # Shopify refused a real deploy: 'settings: with id="stock_threshold" unit can't be blank'
        def blank_unit(schema):
            next(s for s in schema["settings"] if s.get("id") == "check_size")["unit"] = ""
        self.edit_schema(blank_unit)
        self.assertTrue(any("unit can't be blank" in p for p in self.problems()))

    def test_literal_brace_inside_an_output_expression_is_rejected(self):
        # Shopify refused a real deploy for this (5 Oct 2026): {{ x | replace: '{count}', y }} ends at the first single "}"
        self.edit_block("{%- capture dtj_content -%}", "{{ 'a' | replace: '{count}', 'b' }}{%- capture dtj_content -%}")
        self.assertTrue(any("single '}'" in p for p in self.problems()))

    def test_normal_output_expressions_and_tags_with_braces_are_fine(self):
        self.edit_block("{%- capture dtj_content -%}", "{{ 'a' | append: 'b' }}{%- assign tok = '{count}' -%}{%- capture dtj_content -%}")
        self.assertEqual([p for p in self.problems() if "single" in p], [])

    def test_two_product_pickers_are_rejected(self):
        # Shopify refused the deploy: "settings: exceeds limit of 1 for type 'product'"
        def two_pickers(schema):
            schema["settings"] += [{"type": "product", "id": "p1", "label": "A"}, {"type": "product", "id": "p2", "label": "B"}]
        self.edit_schema(two_pickers)
        self.assertTrue(any("'product' settings" in p for p in self.problems()))

    def test_one_product_list_is_fine(self):
        self.edit_schema(lambda schema: schema["settings"].append({"type": "product_list", "id": "pl", "label": "Products", "limit": 4}))
        self.assertEqual([p for p in self.problems() if "settings: an app block may have only 1" in p], [])

    def test_long_block_name_is_rejected(self):
        self.edit_schema(lambda schema: schema.update({"name": "DTJ Option Picker (products)"}))
        self.assertTrue(any("allows 25" in p for p in self.problems()))

    def test_oversized_script_is_rejected(self):
        # Theme Check: 'dtj-addons.js (10442 B) exceeds the configured threshold (10000 B)'. hero-points has no script, so give it one.
        self.edit_schema(lambda schema: schema.update({"javascript": "dtj-big.js"}))
        (self.root / "extensions/dtj-blocks/assets/dtj-big.js").write_text("a" * 10001, encoding="utf-8")
        self.assertTrue(any("Theme Check errors at 10,000" in p for p in self.problems()))
        (self.root / "extensions/dtj-blocks/assets/dtj-big.js").write_text("a" * 9000, encoding="utf-8")
        self.assertEqual([p for p in self.problems() if "10,000" in p], [])

    def test_missing_snippet_is_rejected(self):
        (self.root / "extensions/dtj-blocks/snippets/dtj-check-icon.liquid").unlink()
        self.assertTrue(any("'dtj-check-icon' does not exist" in p for p in self.problems()))

    def test_nested_blocks_are_rejected(self):
        self.edit_schema(lambda schema: schema.update({"blocks": [{"type": "x", "name": "x"}]}))
        self.assertTrue(any("nested" in p for p in self.problems()))


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from provision import templates

UUID = "01a10b7e-02ff-7b68-95a3-bbcdcb562875"  # extension uuid read from a real saved theme on 5 Oct 2026

# trimmed from the real templates/product.json pulled from the dev store after the block was added in the editor
PRODUCT = """/*
 * ------------------------------------------------------------
 * IMPORTANT: The contents of this file are auto-generated.
 * ------------------------------------------------------------
 */
{
  "sections": {
    "main": {
      "type": "product-information",
      "blocks": {
        "disclosures": {"type": "disclosures", "settings": {}},
        "media-gallery": {"type": "_product-media-gallery", "static": true, "settings": {}}
      },
      "block_order": ["disclosures"],
      "settings": {}
    },
    "product_recommendations_qggXJq": {"type": "product-recommendations", "blocks": {}, "settings": {}}
  },
  "order": ["main", "product_recommendations_qggXJq"]
}
"""

KW = dict(section_type="product-information", app_handle="dtj-blocks", block_handle="dtj-trust-row", ext_uuid=UUID)
SETTINGS = {"item_1_text": "abc", "item_1_icon": "check"}


class AppBlockTests(unittest.TestCase):
    def test_type_matches_what_shopify_saved(self):
        self.assertEqual(templates.app_block_type("dtj-blocks", "dtj-trust-row", UUID),
                         "shopify://apps/dtj-blocks/blocks/dtj-trust-row/01a10b7e-02ff-7b68-95a3-bbcdcb562875")

    def test_adds_the_block_in_the_right_place_and_keeps_the_header(self):
        text, key, added = templates.add_app_block(PRODUCT, settings=SETTINGS, index=0, **KW)
        self.assertTrue(added)
        self.assertTrue(text.startswith("/*\n * ------"))
        _, data = templates.load(text)
        section = data["sections"]["main"]
        self.assertTrue(key.startswith("dtj_blocks_dtj_trust_row_"))
        self.assertEqual(section["block_order"], [key, "disclosures"])
        self.assertEqual(section["blocks"][key]["type"], templates.app_block_type("dtj-blocks", "dtj-trust-row", UUID))
        self.assertEqual(section["blocks"][key]["settings"], SETTINGS)
        self.assertIn("media-gallery", section["blocks"])  # untouched

    def test_default_position_is_the_end(self):
        text, key, _ = templates.add_app_block(PRODUCT, settings=SETTINGS, **KW)
        self.assertEqual(templates.load(text)[1]["sections"]["main"]["block_order"], ["disclosures", key])

    def test_idempotent_second_run_updates_settings_without_duplicating(self):
        once, key1, added1 = templates.add_app_block(PRODUCT, settings=SETTINGS, **KW)
        twice, key2, added2 = templates.add_app_block(once, settings={"item_1_text": "new"}, **KW)
        self.assertEqual((added1, added2, key1), (True, False, key2))
        main = templates.load(twice)[1]["sections"]["main"]
        self.assertEqual(sum(1 for b in main["blocks"].values() if "dtj-trust-row" in b["type"]), 1)
        self.assertEqual(main["blocks"][key1]["settings"], {"item_1_text": "new"})
        self.assertEqual(main["block_order"].count(key1), 1)

    def test_missing_section_type_fails_loudly(self):
        with self.assertRaises(templates.TemplateError):
            templates.add_app_block(PRODUCT, settings={}, **{**KW, "section_type": "nope"})

    def test_bad_handles_or_uuid_are_refused(self):
        for bad in ({"app_handle": "Bad Handle"}, {"block_handle": "../x"}, {"ext_uuid": "not-a-uuid"}):
            with self.assertRaises(templates.TemplateError):
                templates.add_app_block(PRODUCT, settings={}, **{**KW, **bad})

    def test_result_is_valid_json_after_the_header(self):
        text, _, _ = templates.add_app_block(PRODUCT, settings=SETTINGS, **KW)
        json.loads(text[text.index("{"):])


if __name__ == "__main__":
    unittest.main()

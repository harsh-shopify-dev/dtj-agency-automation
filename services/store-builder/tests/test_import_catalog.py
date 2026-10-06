import json
import tempfile
import unittest
from pathlib import Path

from provision import import_catalog as ic
from provision.run import validate

PRODUCTS = [
    {"id": 1, "handle": "good-book", "title": "Good Book", "body_html": "<p>Hi</p><script>x()</script>", "vendor": "V",
     "product_type": "Book", "tags": ["a", "b"], "variants": [{"price": "299.00", "compare_at_price": "399.00", "sku": "S1"}],
     "images": [{"src": "https://cdn.example/a.jpg?v=1", "alt": None}, {"src": "https://cdn.example/b.PNG", "alt": "Back"}]},
    {"id": 2, "handle": "वी-आर", "title": "Hindi", "variants": [{"price": "349.00", "compare_at_price": None}],
     "images": [{"src": "https://cdn.example/c.gif"}]},
    {"id": 3, "handle": "no-price", "title": "No price", "variants": [{"price": None}], "images": []},
]


def fake_get(url):
    if "products.json" in url:
        return json.dumps({"products": PRODUCTS if "page=1" in url else []}).encode(), "application/json"
    if url.endswith("a.jpg?v=1") or url.endswith("b.PNG"):
        return b"IMG", "image/jpeg"
    return b"<html>", "text/html"


class ImportTests(unittest.TestCase):
    def test_import_writes_files_and_a_valid_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            result = ic.run("shop.example", Path(d), get=fake_get, sleep=lambda s: None)
            sheet = json.loads((Path(d) / "product-sheet.json").read_text(encoding="utf-8"))
            validate(sheet, "product-sheet.schema.json")
            self.assertEqual(result["products"], 2)  # the one without a price is dropped, not guessed
            self.assertEqual(result["images"], 2)
            self.assertEqual(len(result["skipped_images"]), 1)  # the .gif
            self.assertEqual(result["renamed_handles"], ["imported-2"])
            first = sheet["products"][0]
            self.assertNotIn("script", first["description_html"])
            self.assertEqual(first["images"][0]["alt"], "Good Book")  # alt falls back to the title
            self.assertEqual(first["images"][1]["alt"], "Back")
            self.assertEqual(first["compare_at_price"], "399.00")
            self.assertEqual({p.name for p in (Path(d) / "images").iterdir()}, {"good-book-1.jpg", "good-book-2.png"})
            self.assertIn("Do not publish", (Path(d) / "SOURCE.md").read_text(encoding="utf-8"))

    def test_compare_at_price_below_price_is_dropped(self):
        sheet = ic.build_sheet([{**PRODUCTS[0], "variants": [{"price": "500.00", "compare_at_price": "400.00"}]}], {})
        self.assertNotIn("compare_at_price", sheet["products"][0])


if __name__ == "__main__":
    unittest.main()

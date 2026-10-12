"""fetch_product: the public product and its pictures under their STORE file names (the names facts.media[].file must use)."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from page_builder import fetch_product as fp

PRODUCT = {
    "handle": "serum", "title": "Radiance Serum", "price": 44900, "compare_at_price": 72900, "available": True, "vendor": "Hope N Skin",
    "type": "Serum", "tags": ["skin"], "options": [{"name": "Title"}], "variants": [{"title": "30 ml", "price": 44900, "available": True}],
    "description": "<p>Brightens &amp; hydrates.</p><ul><li>10% vitamin C</li></ul>",
    "media": [
        {"media_type": "image", "src": "//qaxv3r-8g.myshopify.com/cdn/shop/files/Hope%20Front_1.webp?v=17", "alt": "front", "width": 1000, "height": 1000},
        {"media_type": "image", "src": "https://cdn.shopify.com/s/files/1/0/files/back.jpg?v=2", "alt": "", "width": 800, "height": 1000},
        {"media_type": "video", "preview_image": {"src": "https://cdn.shopify.com/s/files/1/0/files/preview_images/clip.jpg", "width": 720, "height": 1080},
         "sources": [{"url": "https://cdn.shopify.com/videos/c/o/v/abc.mp4"}]},
    ],
}


class FetchProduct(unittest.TestCase):
    def setUp(self):
        self.client = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.client)
        self.fetched = []

    def get(self, url):
        self.fetched.append(url)
        if url.endswith("/products/serum.js"):
            return 200, url, json.dumps(PRODUCT).encode()
        return 200, url, b"picture-bytes:" + url.encode()

    def run_main(self, get=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return fp.main(["--store", "qaxv3r-8g.myshopify.com", "--handle", "serum", "--client", str(self.client)], get=get or self.get)

    def test_pictures_are_saved_under_their_store_file_names(self):
        self.assertEqual(self.run_main(), 0)
        product = json.loads((self.client / "store-product.json").read_text(encoding="utf-8"))
        self.assertEqual([m["file"] for m in product["media"]], ["Hope Front_1.webp", "back.jpg", "clip.jpg"])
        self.assertTrue((self.client / "media" / "Hope Front_1.webp").read_bytes().startswith(b"picture-bytes:"))
        self.assertFalse((self.client / "media" / "clip.jpg").exists())  # a video is listed, never downloaded
        self.assertEqual(product["media"][2]["sources"], ["https://cdn.shopify.com/videos/c/o/v/abc.mp4"])
        self.assertTrue(product["media"][0]["url"].startswith("https://"))

    def test_prices_are_rupees_and_the_description_is_plain_text(self):
        self.run_main()
        product = json.loads((self.client / "store-product.json").read_text(encoding="utf-8"))
        self.assertEqual((product["price_rupees"], product["compare_at_price_rupees"]), (449.0, 729.0))
        self.assertEqual(product["description_text"], "Brightens & hydrates.\n10% vitamin C")
        self.assertIn("public product data", product["source"])

    def test_a_password_page_or_a_missing_product_stops_without_files(self):
        for answer in ((200, "https://qaxv3r-8g.myshopify.com/password", b"<html>"), (404, "x", b"")):
            self.assertEqual(self.run_main(get=lambda url, a=answer: a), 1)
        self.assertFalse((self.client / "store-product.json").exists())

    def test_it_only_reads(self):
        self.run_main()
        self.assertTrue(all(u.startswith("https://") for u in self.fetched))
        self.assertTrue(self.fetched[0].endswith("/products/serum.js"))


if __name__ == "__main__":
    unittest.main()

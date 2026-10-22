"""The niche reader (provision/niche_assets.py, 22 Oct 2026): 5 D2C competitors' banners, top products, prices and pictures, for
study before our pictures are planned, and realistic sample prices from their price range. A stand-in plays the competitors'
websites: nothing here reaches the internet."""
import io
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from provision import niche_assets as na


def picture(colour="red", size=(40, 30), fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, fmt)
    return buf.getvalue()


JPG, PNG = picture(), picture("blue", fmt="PNG")
CDN = "//teaco.in/cdn/shop/files"

SHOP_HOME = f"""<html><head><title>TeaCo | Calm teas</title><meta property="og:site_name" content="TeaCo">
<meta property="og:image" content="https://teaco.in/cdn/shop/files/share.jpg">
<style>:root {{ --color-base-background-1: 255, 250, 240; --color-accent: #1F3A2D; --color-text: #333; --color-bad: 300, 1, 1; }}</style>
<script>var x = '<img src="{CDN}/in-script.jpg" width="3000">';</script></head><body>
<div id="shopify-section-header" class="shopify-section"><img class="header__logo" src="{CDN}/logo.png" width="1600" alt="TeaCo logo"></div>
<div id="shopify-section-template--1__slideshow" class="shopify-section"><div class="slideshow">
  <img srcset="{CDN}/hero-1.jpg?v=1&amp;width=375 375w, {CDN}/hero-1.jpg?v=1&amp;width=3840 3840w" src="{CDN}/hero-1.jpg?v=1&amp;width=375">
  <img srcset="{CDN}/hero-2.jpg?v=2&amp;width=750 750w, {CDN}/hero-2.jpg?v=2&amp;width=1500 1500w">
  <img srcset="{CDN}/hero-1.jpg?v=1&amp;width=750 750w">
</div></div>
<div id="shopify-section-template--1__featured_collection" class="shopify-section"><div class="card__media">
  <img srcset="{CDN}/card.jpg?width=533 533w, {CDN}/card.jpg?width=1946 1946w"></div></div>
<div id="shopify-section-template--1__image_banner" class="shopify-section">
  <div class="banner__media" style="background-image: url('{CDN}/wide-bg.jpg?v=3')"></div></div>
</body></html>"""

PRODUCTS = {"products": [
    {"handle": h, "title": t, "product_type": "Tea", "variants": [{"price": p, "compare_at_price": c}],
     "images": [{"src": f"https://cdn.shopify.com/s/files/1/{h}-{i}.jpg?v=1"} for i in range(1, 5)]}
    for h, t, p, c in (("chamomile", "Chamomile Calm", "349.00", "449.00"), ("mint", "Mint Fresh", "299.00", None),
                       ("rose", "Rose Petal", "499.00", "499.00"), ("hibiscus", "Hibiscus Glow", "399.00", "599.00"))]}
BEST = '<a href="/products/hibiscus">x</a><a href="/collections/all/products/chamomile?v=1">y</a><a href="/products/unknown">z</a>'


def shop_site(requests=None, broken=()):
    def get(url):
        if requests is not None:
            requests.append(url)
        if url in ("https://teaco.in/", "https://www.teaco.in/"):
            return 200, "https://teaco.in/", SHOP_HOME.encode()
        if url.startswith("https://teaco.in/products.json"):
            return 200, url, json.dumps(PRODUCTS).encode()
        if url == "https://teaco.in/collections/all?sort_by=best-selling":
            return 200, url, BEST.encode()
        if any(b in url for b in broken):
            return 200, url, b"<html>not a picture</html>"
        if url.startswith("https://teaco.in/cdn/shop/files/") or url.startswith("https://cdn.shopify.com/"):
            return 200, url, PNG if "hero-2" in url else JPG
        return 404, url, b""
    return get


SITE_HOME = '<html><head><meta property="og:site_name" content="Leafy"></head><body><img src="/wp/banner-wide.jpg" width="1920"></body></html>'
SITEMAP = "<urlset>" + "".join(f"<url><loc>https://leafy.in/product/tea-{n}/</loc></url>" for n in range(1, 40)) + "</urlset>"


def product_page(n, price=True):
    offer = f',"offers":{{"price":"{200 + n}"}}' if price else ""
    return (f'<html><head><script type="application/ld+json">{{"@type":"Product","name":"Leaf Tea {n}"{offer}}}</script></head>'
            f'<body><h1>Leaf Tea {n}</h1><img src="https://leafy.in/wp/tea-{n}-a.jpg"><img src="https://leafy.in/wp/tea-{n}-b.jpg">'
            f'</body></html>')


def website(requests=None):
    def get(url):
        if requests is not None:
            requests.append(url)
        if url == "https://leafy.in/":
            return 200, url, SITE_HOME.encode()
        if url == "https://leafy.in/sitemap.xml":
            return 200, url, SITEMAP.encode()
        if url.startswith("https://leafy.in/product/tea-"):
            n = int(url.rstrip("/").rsplit("-", 1)[1])
            return 200, url, product_page(n, price=n != 2).encode()
        if url.startswith("https://leafy.in/wp/"):
            return 200, url, JPG
        return 404, url, b""
    return get


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)


class Shopify(Base):
    def test_banners_best_sellers_prices_and_pictures(self):
        asked = []
        c = na.read_competitor("teaco.in", self.tmp, shop_site(asked), pause=lambda: None)
        self.assertEqual((c["name"], c["host"], c["platform"]), ("TeaCo", "teaco.in", "shopify"))
        self.assertEqual(c["colours"], ["#fffaf0", "#1f3a2d", "#333333"])  # 300,1,1 is not a colour
        names = [Path(b).name for b in c["banners"]]
        self.assertEqual(names, ["1.jpg", "2.png", "3.jpg"])  # hero 1, hero 2 (a png), the background banner; no logo, card, script
        banner_asks = [u for u in asked if "/cdn/shop/files/" in u]
        self.assertTrue(all("width=1600" in u for u in banner_asks))
        self.assertTrue(any("hero-1.jpg" in u and "v=1" in u for u in banner_asks))
        self.assertFalse(any(x in u for u in banner_asks for x in ("logo", "card", "in-script", "share")))
        self.assertEqual([p["handle"] for p in c["products"]], ["hibiscus", "chamomile", "mint"])  # best sellers first
        hib, cham, mint = c["products"]
        self.assertEqual((hib["price"], hib["compare_at_price"], hib["url"]), (399.0, 599.0, "https://teaco.in/products/hibiscus"))
        self.assertEqual(mint["compare_at_price"], None)
        self.assertEqual(len(cham["pictures"]), 3)  # 2-3 pictures, never all 4
        self.assertTrue(all(Path(x).exists() for p in c["products"] for x in p["pictures"]))
        self.assertTrue(cham["pictures"][0].endswith(str(Path("teaco.in", "products", "chamomile", "1.jpg"))))
        self.assertTrue(any("width=1200" in u for u in asked if "cdn.shopify.com" in u))
        self.assertLessEqual(c["requests"], na.MAX_REQUESTS)
        self.assertEqual(c["problems"], [])

    def test_a_page_instead_of_a_picture_is_not_saved_and_is_said(self):
        c = na.read_competitor("https://teaco.in", self.tmp, shop_site(broken=("hero-2",)), pause=lambda: None)
        self.assertEqual(len(c["banners"]), 2)
        self.assertTrue(any("could not be downloaded" in x for x in c["problems"]))

    def test_a_site_that_does_not_answer_is_refused(self):
        with self.assertRaises(na.CompetitorError):
            na.read_competitor("https://gone.in", self.tmp, lambda url: (0, url, b""), pause=lambda: None)

    def test_no_banner_falls_back_to_og_image_and_rate_rules(self):
        page = '<html><head><meta property="og:image" content="https://x.in/cdn/shop/files/share.jpg?v=9"></head><body></body></html>'
        self.assertEqual(na.banners_of(page, "https://x.in"), ["https://x.in/cdn/shop/files/share.jpg?v=9&width=1600"])
        self.assertEqual(na.sized("https://cdn.shopify.com/s/files/a_1200x.jpg?v=1&width=300&crop=center", 1600),
                         "https://cdn.shopify.com/s/files/a.jpg?v=1&width=1600")
        self.assertEqual(na.sized("https://leafy.in/wp/a.jpg", 1600), "https://leafy.in/wp/a.jpg")


class Website(Base):
    def test_a_site_that_is_not_shopify_is_read_from_its_product_pages_within_the_limit(self):
        asked = []
        c = na.read_competitor("https://leafy.in", self.tmp, website(asked), pause=lambda: None)
        self.assertEqual((c["name"], c["platform"]), ("Leafy", "website"))
        self.assertEqual(len(c["banners"]), 1)  # a picture offered 1920 wide outside a product grid
        self.assertEqual([p["title"] for p in c["products"]], ["Leaf Tea 1", "Leaf Tea 2", "Leaf Tea 3"])
        self.assertEqual([p["price"] for p in c["products"]], [201.0, None, 203.0])  # no price shown = none, never a guess
        self.assertEqual([len(p["pictures"]) for p in c["products"]], [2, 2, 2])
        self.assertLessEqual(len(asked), na.MAX_REQUESTS)

    def test_the_request_limit_stops_a_big_site_and_says_so(self):
        asked = []
        c = na.read_competitor("https://leafy.in", self.tmp, website(asked), pause=lambda: None, limit=6)
        self.assertEqual(len(asked), 6)
        self.assertIn("stopped at 6 requests (this competitor's limit)", c["problems"])


class Niche(Base):
    def test_research_goes_on_past_a_failure_and_writes_the_range_sheets_and_the_rule(self):
        def get(url):
            if "teaco.in" in url:
                return shop_site()(url)
            if "leafy.in" in url:
                return website()(url)
            return 0, url, b""
        data = na.research(["https://teaco.in", "https://gone.in", "https://leafy.in"], self.tmp, get, "calm herbal teas",
                           pause=lambda: None, now=lambda: datetime(2026, 10, 22, tzinfo=timezone.utc))
        self.assertEqual([c["host"] for c in data["competitors"]], ["teaco.in", "leafy.in"])
        self.assertEqual(len(data["problems"]), 1)
        self.assertIn("gone.in", data["problems"][0])
        pr = data["prices"]
        self.assertEqual((pr["min"], pr["max"], pr["count"]), (201.0, 399.0, 5))
        self.assertEqual(pr["median"], 299.0)  # 201, 203, 299, 349, 399
        self.assertEqual(pr["compare_ratio_median"], round((599 / 399 + 449 / 349) / 2, 3))
        self.assertIn("never uploaded to the picture maker", data["note"])
        saved = json.loads((self.tmp / "niche.json").read_text(encoding="utf-8"))
        self.assertEqual((saved["niche"], saved["made_at"]), ("calm herbal teas", "2026-10-22T00:00:00Z"))
        sheet = Path(data["competitors"][0]["sheet"])
        self.assertTrue(sheet.exists())
        with Image.open(sheet) as im:
            self.assertLessEqual(im.width, na.SHEET_WIDTH)

    def test_the_command_line_needs_three_competitors(self):
        out = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(out):
            code = na.main(["https://teaco.in", "--out", str(self.tmp), "--niche", "tea"], get=shop_site())
        self.assertEqual(code, 1)
        self.assertIn("TeaCo (teaco.in, shopify): 3 banners, 3 products", out.getvalue())


class SamplePrices(unittest.TestCase):
    PRICES = {"min": 249.0, "median": 449.0, "max": 899.0, "compare_ratio_median": 1.4, "count": 12}

    def test_retail_endings(self):
        self.assertEqual([na.retail(v) for v in (10, 60, 315, 330, 1000, 1530)], [49, 49, 299, 349, 999, 1549])

    def test_spread_from_the_lowest_to_the_median_with_a_compare_price_above(self):
        got = [na.sample_price(self.PRICES, r, 5) for r in range(1, 6)]
        self.assertEqual([p for p, _ in got], ["249.00", "299.00", "349.00", "399.00", "449.00"])
        for p, c in got:
            self.assertGreater(float(c), float(p))
            self.assertIn(c[-5:-3], ("49", "99"))
        self.assertEqual(na.sample_price(self.PRICES, 1, 5)[1], "349.00")  # 249 x 1.4 = 348.6

    def test_no_compare_ratio_uses_a_quarter_more_and_no_prices_is_refused(self):
        self.assertEqual(na.sample_price(dict(self.PRICES, compare_ratio_median=None), 1, 1), ("349.00", "449.00"))
        with self.assertRaises(ValueError):
            na.sample_price({"min": None, "median": None}, 1, 3)


class Retries(unittest.TestCase):
    def test_429_and_5xx_and_no_answer_are_tried_again_three_times(self):
        answers = [(429, "u", b""), (503, "u", b""), (0, "u", b""), (200, "u", b"ok")]
        slept = []
        get = na.retrying(lambda url: answers.pop(0), sleep=slept.append)
        self.assertEqual(get("u"), (200, "u", b"ok"))
        self.assertEqual(slept, [2, 4, 6])
        always = na.retrying(lambda url: (500, url, b""), sleep=lambda s: None)
        self.assertEqual(always("u")[0], 500)
        self.assertEqual(na.retrying(lambda url: (404, url, b""), sleep=slept.append)("u")[0], 404)
        self.assertEqual(len(slept), 3)  # a 404 is not tried again


if __name__ == "__main__":
    unittest.main()

"""Brand intake (Harsh, 19 Oct 2026): a client's public store in one folder before a redesign, at most 20 products. A stand-in store:
nothing here touches the internet."""
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from page_builder import brand_intake  # noqa: E402
from page_builder.assemble import _validate  # noqa: E402

BASE = "https://toilova.example"


def png(colour: tuple[int, int, int], size=(60, 60), frame=True) -> bytes:
    im = Image.new("RGB", size, "white")  # a pack on a white studio background
    Image.Image.paste(im, Image.new("RGB", (size[0] - 20, size[1] - 20), colour), (10, 10))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


HOME = f"""<html><head><title>Toilova | Home care</title>
<meta property="og:site_name" content="Toilova"><meta name="description" content="Foam that does the scrubbing.">
<meta property="og:image" content="//cdn.shopify.com/s/files/1/share.png">
<style>:root {{ --color-background: 255,255,255; --color-foreground: 16,32,45; --color-button: 11,102,178; --color-badge: 220,40,40;
--color-badge-2: 220,40,40; --color-error: 139,0,0; --color-highlight: 220,40,40; --color-highlight-2: 220,40,40; --font-heading-family: "Poppins", sans-serif; --font-body-family: Inter, sans-serif; }}</style>
<script>Shopify.theme = {{"name":"Horizon","id":1}}; Shopify.currency = {{"active":"INR","rate":"1.0"}};</script></head>
<body><a href="/"><img class="header__logo" src="//cdn.shopify.com/s/files/1/logo.png" alt="Toilova"></a>
<a href="https://instagram.com/toilova">ig</a><a href="mailto:owner@toilova.example">mail</a></body></html>"""


def products(n: int) -> dict:
    return {"products": [{"title": f"Toilet cleaner foam {k}", "handle": f"foam-{k}", "product_type": "Toilet cleaner", "vendor": "Toilova",
                          "tags": ["bathroom", "cleaning"], "body_html": "<p>No scrubbing needed.</p>",
                          "options": [{"name": "Pack"}], "variants": [{"price": "699.00", "compare_at_price": "1400.00"}],
                          "images": [{"src": f"https://cdn.shopify.com/s/files/1/foam-{k}-1.png?v=1"},
                                     {"src": f"https://cdn.shopify.com/s/files/1/foam-{k}-2.png?v=1"}]} for k in range(n)]}


def store(n_products: int = 25, shopify: bool = True):
    pages = {
        BASE + "/": HOME.encode(),
        BASE + "/collections.json?limit=250": json.dumps({"collections": [{"title": "Bathroom care", "handle": "bathroom-care", "products_count": 3,
                                                                            "image": {"src": "https://cdn.shopify.com/s/files/1/bath.png"}}]}).encode(),
        BASE + "/policies/shipping-policy": b"<p>We ship to [INSERT CITY] within 5 days.</p>",
        BASE + "/policies/privacy-policy": b"<p>Our privacy policy.</p>",
    }
    if shopify:
        pages[BASE + "/products.json?limit=250"] = json.dumps(products(n_products)).encode()
    calls = []

    def get(url):
        calls.append(url)
        if url in pages:
            return 200, url, pages[url]
        if "cdn.shopify.com" in url:
            if "logo" in url:
                return 200, url, png((0, 184, 76))  # the logo carries the brand's green
            return 200, url, png((11, 102, 178))  # blue packs
        return 404, url, b""
    return get, calls


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp()) / "intake"
        self.addCleanup(shutil.rmtree, self.out.parent, ignore_errors=True)

    def run_intake(self, **kw):
        get, calls = store(**kw)
        return brand_intake.intake(BASE, self.out, get=get, delay=0), calls

    def test_at_most_20_products_are_read_with_every_picture_and_the_rest_only_counted(self):
        r, calls = self.run_intake(n_products=25)
        self.assertEqual((r["counts"]["products_listed"], r["counts"]["products_read"]), (25, 20))
        self.assertTrue(any("only the first 20" in n for n in r["notes"]))
        self.assertEqual(len(list((self.out / "images" / "products").rglob("*.png"))), 40)
        self.assertFalse(any("foam-20" in u for u in calls))  # products after the 20th: not even their pictures are requested
        self.assertTrue(all("width=2048" in u for u in calls if "cdn.shopify.com" in u))

    def test_the_brand_facts_fonts_and_policies_are_read_and_no_personal_data_is_kept(self):
        r, _ = self.run_intake()
        self.assertEqual((r["shop"]["name"], r["shop"]["theme"], r["shop"]["currency"]), ("Toilova", "Horizon", "INR"))
        self.assertEqual(r["shop"]["fonts"], {"heading": "Poppins", "body": "Inter"})
        self.assertEqual(r["shop"]["socials"], ["https://instagram.com/toilova"])
        self.assertNotIn("owner@toilova.example", (self.out / "brand-intake.json").read_text(encoding="utf-8"))
        self.assertTrue(r["policies"]["shipping-policy"]["looks_like_a_template"])
        self.assertFalse(r["policies"]["refund-policy"]["found"])
        self.assertTrue((self.out / "images" / "logo.png").is_file())

    def test_the_palette_comes_from_the_theme_button_and_the_logo_and_the_draft_brand_file_is_valid(self):
        r, _ = self.run_intake()
        chosen = r["colours"]["chosen"]
        self.assertEqual(chosen["primary"], "#0B66B2")  # the theme's button colour, not the more used badge red
        self.assertNotIn("#8B0000", [c["hex"] for c in r["colours"]["candidates"]])  # the error colour is a signal, not the brand
        self.assertEqual(chosen["accent_from"], "the logo")
        self.assertGreaterEqual(brand_intake.palette.hue_gap(chosen["primary"], chosen["accent"]), 40)
        self.assertEqual((chosen["text"], chosen["background"]), ("#10202D", "#FFFFFF"))
        self.assertEqual(len(r["palette"]["ramps"]["brand"]), 12)
        brand = json.loads((self.out / "brand.json").read_text(encoding="utf-8"))
        _validate(brand, "brand-profile")  # the page builder can use it as it is
        self.assertEqual((brand["category"], brand["price_tier"], brand["palette"]), ("home-care", "mid", "ramps"))
        for f in ("BRAND.md", "palette.png", "products.png"):
            self.assertTrue((self.out / f).is_file(), f)
        self.assertIn("Guesses (check them", (self.out / "BRAND.md").read_text(encoding="utf-8"))

    def test_a_store_that_is_not_shopify_still_gives_the_brand_and_colours(self):
        r, _ = self.run_intake(shopify=False)
        self.assertEqual((r["platform"], r["counts"]["products_read"]), ("other", 0))
        self.assertTrue(any("not a Shopify store" in n for n in r["notes"]))
        self.assertEqual(r["colours"]["chosen"]["primary"], "#0B66B2")

    def test_the_colour_most_products_share_wins_and_the_description_tells_the_category(self):
        # 19 Oct 2026, the test store: a book cover listed first won the brand colour over six blue packs, and "TOILOVA" said nothing
        feed = {"products": [{"title": "A book", "handle": "book", "body_html": "<p>A workbook.</p>", "variants": [{"price": "299"}],
                              "images": [{"src": "https://cdn.shopify.com/s/files/1/book.png"}]}] +
                            [{"title": "TOILOVA", "handle": f"t{k}", "body_html": "<p>Toilet cleaning foam powder.</p>", "variants": [{"price": "699"}],
                              "images": [{"src": f"https://cdn.shopify.com/s/files/1/t{k}.png"}]} for k in range(4)]}
        pages = {BASE + "/": b"<html><title>Shop</title></html>", BASE + "/products.json?limit=250": json.dumps(feed).encode()}

        def get(url):
            if url in pages:
                return 200, url, pages[url]
            if "book" in url:
                return 200, url, png((232, 120, 120))
            if "cdn.shopify.com" in url:
                return 200, url, png((11, 102, 178))
            return 404, url, b""
        r = brand_intake.intake(BASE, self.out, get=get, delay=0)
        self.assertEqual(r["colours"]["chosen"]["primary_from"], "product pictures (4 of 5 products)")
        self.assertEqual(r["guesses"]["category"], "home-care")

    def test_horizon_font_names_are_read_and_a_slow_picture_is_retried_once(self):
        shop = brand_intake.read_home(BASE, "<style>--font-heading--family: Inter, sans-serif; --font-body--family: Lato, sans-serif;</style>")
        self.assertEqual(shop["fonts"], {"heading": "Inter", "body": "Lato"})
        get, calls = store(n_products=1)
        first = {"failed": False}

        def flaky(url):
            if "foam-0-1" in url and not first["failed"]:
                first["failed"] = True
                raise TimeoutError("slow CDN")
            return get(url)
        r = brand_intake.intake(BASE, self.out, get=flaky, delay=0)
        self.assertEqual(r["products"][0]["pictures"], ["foam-0-1.png", "foam-0-2.png"])
        self.assertFalse(any("not downloaded" in n for n in r["notes"]))

    def test_videos_are_downloaded_at_720p_and_youtube_links_are_listed(self):
        # Harsh, 19 Oct 2026: "it should also download videos if available"
        get, calls = store(n_products=2)
        media = {"media": [{"media_type": "image"},
                           {"media_type": "video", "sources": [
                               {"format": "mp4", "mime_type": "video/mp4", "height": 1080, "url": "https://cdn.shopify.com/videos/c/vp/a/demo.HD-1080p.mp4"},
                               {"format": "mp4", "mime_type": "video/mp4", "height": 720, "url": "https://cdn.shopify.com/videos/c/vp/a/demo.HD-720p.mp4"},
                               {"format": "m3u8", "mime_type": "application/x-mpegURL", "url": "https://cdn.shopify.com/videos/c/vp/a/demo.m3u8"}]},
                           {"media_type": "external_video", "host": "youtube", "external_id": "abc123"}]}
        home = HOME.replace("</body>", '<video autoplay><source src="//cdn.shopify.com/videos/c/o/v/hero.mp4" type="video/mp4"></video></body>')

        def get2(url):
            if url == BASE + "/products/foam-0.js":
                return 200, url, json.dumps(media).encode()
            if url == BASE + "/":
                return 200, url, home.encode()
            if url.endswith(".mp4"):
                calls.append(url)
                return 200, url, b"MP4-STAND-IN-ftypmp42" + b"0" * 100
            return get(url)
        r = brand_intake.intake(BASE, self.out, get=get2, delay=0)
        foam = r["products"][0]
        self.assertEqual(foam["videos"], ["demo.HD-720p.mp4"])
        self.assertEqual(foam["external_videos"], ["https://www.youtube.com/watch?v=abc123"])
        self.assertTrue((self.out / "videos" / "products" / "foam-0" / "demo.HD-720p.mp4").is_file())
        self.assertEqual(r["site_videos"], ["hero.mp4"])
        self.assertEqual(r["counts"]["videos"], 2)
        self.assertFalse(any("width=2048" in u for u in calls if u.endswith(".mp4") or "videos" in u))  # videos are never resized
        self.assertIn("| 1 + 1 linked |", (self.out / "BRAND.md").read_text(encoding="utf-8"))

    def test_a_dark_logo_colour_beats_one_products_colour_and_app_code_is_not_a_template_policy(self):
        # Freesoul, 19 Oct 2026: the maroon logo (#39000B) lost to a purple on one product, and "{{" in an app's script flagged 3 policies
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><path fill="#39000B"/></svg>'
        page = (HOME.replace("--color-button: 11,102,178;", "").replace('src="//cdn.shopify.com/s/files/1/logo.png"', 'src="//cdn.shopify.com/s/files/1/logo.svg"'))
        feed = {"products": [{"title": "Protein blend", "handle": f"p{k}", "variants": [{"price": "30"}],
                              "images": [{"src": f"https://cdn.shopify.com/s/files/1/p{k}.png"}]} for k in range(3)]}
        policy = b'<script>{"mix_item_header":"mix item {{itemIndex}}"}</script><div class="shopify-policy__body"><p>Returns within 14 days.</p></div>'

        def get(url):
            if url == BASE + "/":
                return 200, url, page.encode()
            if url == BASE + "/products.json?limit=250":
                return 200, url, json.dumps(feed).encode()
            if url.startswith(BASE + "/policies/"):
                return 200, url, policy
            if "logo.svg" in url:
                return 200, url, svg
            if url.endswith("p0.png?width=2048"):
                return 200, url, png((120, 88, 152))  # one purple product
            if "cdn.shopify.com" in url:
                return 200, url, png((240, 228, 216), frame=False)
            return 404, url, b""
        r = brand_intake.intake(BASE, self.out, get=get, delay=0)
        self.assertEqual((r["colours"]["chosen"]["primary"], r["colours"]["chosen"]["primary_from"]), ("#39000B", "the logo"))
        self.assertFalse(any(p["looks_like_a_template"] for p in r["policies"].values()))

    def test_a_custom_themes_stylesheet_gives_its_colours_and_font(self):
        css = ".btn{background-color:#5B2A86;color:#fff}.hero{background:#5B2A86}h1{font-family:'ESPark',serif}body{font-family:ESPark}"
        page = '<html><head><link rel="stylesheet" href="//shop.example/cdn/shop/t/373/assets/output.css?v=1"></head></html>'
        colours = brand_intake.theme_colours(page, css)
        self.assertEqual(colours[0]["hex"], "#5B2A86")
        self.assertEqual(colours[0]["source"], "the theme's stylesheet")
        self.assertEqual(brand_intake.read_home(BASE, page, css)["fonts"]["heading"], "ESPark")
        chosen = brand_intake.choose_colours([{"hex": "#39000B", "source": "the logo"}, {"hex": "#D83B9E", "source": "the theme's stylesheet"}], "supplements")
        self.assertEqual((chosen["primary"], chosen["accent"]), ("#39000B", "#D83B9E"))  # close hues, far apart in lightness: two colours

    def test_the_command_never_reads_more_than_20_even_when_asked(self):
        get, _ = store(n_products=30)
        from unittest import mock
        with mock.patch.object(brand_intake, "POLITE_DELAY", 0):
            code = brand_intake.main([BASE, "--client", str(self.out.parent), "--max-products", "50"], get=get)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.out / "brand-intake.json").read_text(encoding="utf-8"))["counts"]["products_read"], 20)


if __name__ == "__main__":
    unittest.main()

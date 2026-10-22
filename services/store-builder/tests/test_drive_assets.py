"""The Drive reader (provision/drive_assets.py, 22 Oct 2026): a client's public Drive folder for a NEW store into the brand shape
brand_copy.make_plan takes. A stand-in plays Drive's public pages (the listing markup is copied from a real public folder, saved in
fixtures/drive): nothing here reaches Google or Shopify."""
import json
import shutil
import tempfile
import unittest
import zipfile
import io
from pathlib import Path

from provision import brand_copy as bc
from provision import drive_assets as da

FIXTURES = Path(__file__).parent / "fixtures" / "drive"
ROOT_ID = "1RootFolderAAAAAAAAAAAAAAAAAAAAAA"


def entry_html(eid, name, kind, mime=""):
    href = {"folder": f"https://drive.google.com/drive/folders/{eid}",
            "doc": f"https://docs.google.com/document/d/{eid}/edit?usp=drive_web",
            "file": f"https://drive.google.com/file/d/{eid}/view?usp=drive_web"}[kind]
    icon = ('<div aria-label="Folder" class="icon-color-1 drive-sprite-folder-list-shared-icon"></div>' if kind == "folder" else
            f'<img src="https://drive-thirdparty.googleusercontent.com/16/type/{mime or "application/vnd.google-apps.document"}" alt=""/>')
    return (f'<div class="flip-entry" id="entry-{eid}" tabindex="0" role="link"><div class="flip-entry-info"><a href="{href}" '
            f'target="_blank"><div class="flip-entry-visual"></div><div class="flip-entry-list-icon">{icon}</div>'
            f'<div class="flip-entry-title">{name}</div></a></div><div class="flip-entry-last-modified"><div>Oct 22</div></div></div>')


def listing(title, entries):
    return (f'<!DOCTYPE html><html><head><title>{title}</title></head><body class="flip-embedded"><div id="flip-contents" '
            f'class="flip-contents flip-list-view"><div class="flip-entries">'
            + "".join(entry_html(*e) for e in entries) + "</div></div></body></html>").encode()


JPEG = b"\xff\xd8\xff\xe0fakejpeg"


class FakeDrive:
    """folders: id -> (title, [(id, name, kind, mime)]); docs: id -> text; files: id -> bytes."""

    def __init__(self, folders, docs=None, files=None):
        self.folders, self.docs, self.files = folders, docs or {}, files or {}
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if "embeddedfolderview" in url:
            fid = url.split("id=")[1]
            if fid not in self.folders:
                return 404, url, b""
            return 200, url, listing(*self.folders[fid])
        if "/export?format=txt" in url:
            did = url.split("/document/d/")[1].split("/")[0]
            return (200, "https://doc-10-docstext.googleusercontent.com/export/x", self.docs[did].encode("utf-8-sig")) if did in self.docs \
                else (200, "https://accounts.google.com/ServiceLogin", b"<html>sign in</html>")
        if "usercontent.google.com/download" in url:
            fid = url.split("id=")[1].split("&")[0]
            if fid in self.files:
                return 200, url, self.files[fid]
            return 200, url, b"<!DOCTYPE html><html>Google Drive - Virus scan warning</html>"
        return 404, url, b""


def senso_like():
    folders = {
        ROOT_ID: ("Masala &amp; Co", [("F_brand", "1 Brand", "folder"), ("F_products", "2 Products", "folder"),
                                      ("F_banners", "3 Banners", "folder"), ("F_pol", "4 Policies", "folder")]),
        "F_brand": ("1 Brand", [("D_brand", "Brand details", "doc"), ("I_logo", "logo.png", "file", "image/png"),
                                ("I_logow", "logo-white.png", "file", "image/png")]),
        "F_products": ("2 Products", [("P2", "2. Garam Masala", "folder"), ("P1", "1. Kitchen King", "folder"),
                                      ("P3", "3 in 1 Tea Mix", "folder"), ("P4", "Kitchen King", "folder")]),
        "P1": ("1. Kitchen King", [("D_p1", "Details", "doc"), ("I_p1_10", "10.jpg", "file", "image/jpeg"),
                                    ("I_p1_2", "2.jpg", "file", "image/jpeg"), ("I_p1_1", "1.jpg", "file", "image/jpeg"),
                                    ("V_p1", "how-to.mp4", "file", "video/mp4")]),
        "P2": ("2. Garam Masala", [("T_p2", "details.txt", "file", "text/plain"), ("I_p2_1", "1.jpg", "file", "image/jpeg")]),
        "P3": ("3 in 1 Tea Mix", [("I_p3_1", "front.webp", "file", "image/webp")]),
        "P4": ("Kitchen King", [("D_p4", "Details", "doc")]),
        "F_banners": ("3 Banners", [("I_b2", "2.jpg", "file", "image/jpeg"), ("I_b1", "1.jpg", "file", "image/jpeg")]),
        "F_pol": ("4 Policies", [("D_ref", "Refund policy", "doc"), ("D_short", "Shipping", "doc"), ("D_misc", "Notes", "doc")]),
    }
    docs = {
        "D_brand": "Name: Masala & Co\r\nTagline: Spice it right\r\nColours: #C0392B, 1a1a1a, #fff, bad\r\nFonts: Poppins, Lora\r\n"
                   "About: Family spice makers from Rajkot.\r\nSince 1982.\r\nEmail: care@masala.co\r\nPhone: +91 98765 43210\r\n"
                   "Instagram: https://instagram.com/masalaco\r\n",
        "D_p1": "Price: Rs. 1,299/-\nMRP: 1,499\nSizes: 100 g = 199, 250 g = 449, 100 g = 199\nCollection: Masalas, Best sellers\n"
                "SKU: KK-1\nTags: veg\nWeight: 250 g\nDescription: A blend for every sabzi.\nNote: keep it dry.\n\nMade in Rajkot <fresh>.",
        "D_p4": "Price: 99\nCollection: masalas\nDescription: The small pack.",
        "D_ref": "Refunds within 7 days of delivery for unopened packs. Write to care@masala.co with your order number.",
        "D_short": "Soon.",
        "D_misc": "Nothing about policies here, just notes for the team that are long enough to count.",
    }
    files = {k: JPEG for k in ("I_logo", "I_logow", "I_p1_10", "I_p1_2", "I_p1_1", "I_p2_1", "I_p3_1", "I_b1", "I_b2")}
    files["T_p2"] = b"Price: about 300\nSize = S, M, L\nDescription: Strong.\n"
    return FakeDrive(folders, docs, files)


class Links(unittest.TestCase):
    def test_folder_links(self):
        for link in (f"https://drive.google.com/drive/folders/{ROOT_ID}?usp=sharing", f"https://drive.google.com/drive/u/0/folders/{ROOT_ID}",
                     f"https://drive.google.com/open?id={ROOT_ID}", ROOT_ID):
            self.assertEqual(da.folder_id(link), ROOT_ID)

    def test_not_a_folder(self):
        for link in ("https://drive.google.com/file/d/1abcdefghijklmnop/view", "https://brand.com/products", "hello"):
            with self.assertRaises(da.DriveError):
                da.folder_id(link)


class RealListing(unittest.TestCase):
    def test_parses_the_real_markup(self):
        page = (FIXTURES / "embeddedfolderview-gdown.html").read_bytes()
        title, entries = da.list_folder("x", lambda url: (200, url, page))
        self.assertEqual(title, "gdown")
        self.assertEqual(len(entries), 16)
        kinds = {e["name"]: e["kind"] for e in entries}
        self.assertEqual(kinds["deep_folder"], "folder")
        self.assertEqual(kinds["gdown.docx"], "doc")  # a Google Doc keeps the .docx name it was uploaded with
        self.assertEqual(kinds["gdown.xlsx"], "sheet")
        self.assertEqual(kinds["spam.txt"], "file")
        spam = next(e for e in entries if e["name"] == "spam.txt")
        self.assertEqual(spam["id"], "1cKSdgtWrPgvEsBGmjWALOH33taGyVXKb")
        self.assertEqual(spam["mime"], "text/plain")

    def test_not_shared(self):
        with self.assertRaisesRegex(da.DriveError, "Anyone with the link"):
            da.list_folder("x", lambda url: (404, url, b""))
        with self.assertRaisesRegex(da.DriveError, "Anyone with the link"):
            da.list_folder("x", lambda url: (200, "https://accounts.google.com/ServiceLogin?x", b"<html></html>"))
        with self.assertRaisesRegex(da.DriveError, "did not answer"):
            da.list_folder("x", lambda url: (0, url, b""))


class ReadFolder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def read(self, drive=None, **kw):
        return da.read_folder(f"https://drive.google.com/drive/folders/{ROOT_ID}?usp=sharing", self.tmp, get=drive or senso_like(),
                              pause=lambda: None, **kw)

    def test_brand(self):
        data = self.read()
        b = data["brand"]
        self.assertEqual(data["name"], "Masala & Co")
        self.assertEqual(b["tagline"], "Spice it right")
        self.assertEqual(b["colours"], ["#c0392b", "#1a1a1a", "#ffffff"])
        self.assertEqual(b["fonts"], ["Poppins", "Lora"])
        self.assertEqual(b["about"], "Family spice makers from Rajkot.\nSince 1982.")
        self.assertEqual(b["email"], "care@masala.co")
        self.assertEqual(b["social"], {"instagram": "https://instagram.com/masalaco"})
        self.assertTrue(b["logo"].endswith("logo.png") and Path(b["logo"]).read_bytes() == JPEG)
        self.assertTrue(b["logo_white"].endswith("logo-white.png"))
        self.assertEqual(data["source"], "drive")
        self.assertIsNone(data["myshopify_domain"])

    def test_products(self):
        data = self.read()
        by = {p["handle"]: p for p in data["products"]}
        self.assertEqual([p["handle"] for p in data["products"]], ["kitchen-king", "garam-masala", "3-in-1-tea-mix", "kitchen-king-2"])
        kk = by["kitchen-king"]
        self.assertEqual(kk["title"], "Kitchen King")
        self.assertEqual(kk["options"], [{"name": "Size", "position": 1, "values": ["100 g", "250 g"]}])
        self.assertEqual([(v["option1"], v["price"]) for v in kk["variants"]], [("100 g", "199"), ("250 g", "449")])
        self.assertFalse(kk["price_needed"])
        self.assertEqual(kk["tags"], ["veg"])
        self.assertEqual([Path(i["path"]).name for i in kk["images"]], ["1.jpg", "2.jpg", "10.jpg"])  # natural order: 1 is the main one
        self.assertEqual(kk["videos"][0]["name"], "how-to.mp4")
        self.assertIn("<p>A blend for every sabzi.<br>Note: keep it dry.</p><p>Made in Rajkot &lt;fresh&gt;.</p>", kk["body_html"])
        self.assertEqual(kk["source"], "https://drive.google.com/drive/folders/P1")
        gm = by["garam-masala"]  # a .txt Details, a price that is not a number, one price for S, M, L
        self.assertTrue(gm["price_needed"])
        self.assertEqual([(v["option1"], v["price"]) for v in gm["variants"]], [("S", "0.00"), ("M", "0.00"), ("L", "0.00")])
        self.assertIn(bc.PRICE_TAG, gm["tags"])
        tea = by["3-in-1-tea-mix"]  # no Details doc: no price, never guessed
        self.assertEqual(tea["title"], "3 in 1 Tea Mix")
        self.assertEqual(tea["variants"], [{"option1": "Default Title", "price": "0.00", "compare_at_price": None, "sku": ""}])
        self.assertEqual(by["kitchen-king-2"]["variants"][0]["price"], "99")
        self.assertEqual(data["best_sellers"][0], {"handle": "kitchen-king", "title": "Kitchen King",
                                                   "url": "https://drive.google.com/drive/folders/P1"})

    def test_single_price_and_mrp(self):
        p, problems = da.product_from("Chai", da.parse_fields("Price: ₹ 250 only\nMRP: Rs.300\nSKU: C1", da.PRODUCT_KEYS, "description"), "B")
        self.assertEqual(p["variants"], [{"option1": "Default Title", "price": "250", "compare_at_price": "300", "sku": "C1"}])
        self.assertEqual(problems, [])
        p, _ = da.product_from("Chai", da.parse_fields("Price: 300\nMRP: 250", da.PRODUCT_KEYS, "description"), "B")
        self.assertIsNone(p["variants"][0]["compare_at_price"])  # a "compare at" below the price is dropped
        p, _ = da.product_from("Chai", da.parse_fields("Sizes:\n250 g = 499\n500 g = 899\nDescription: x", da.PRODUCT_KEYS, "description"), "B")
        self.assertEqual([(v["option1"], v["price"]) for v in p["variants"]], [("250 g", "499"), ("500 g", "899")])

    def test_collections_banners_policies(self):
        data = self.read()
        self.assertEqual(data["collections"], [
            {"handle": "masalas", "title": "Masalas", "description_html": "", "products": ["kitchen-king", "kitchen-king-2"]},
            {"handle": "best-sellers", "title": "Best sellers", "description_html": "", "products": ["kitchen-king"]}])
        self.assertEqual([Path(b).name for b in data["banners"]], ["1.jpg", "2.jpg"])
        self.assertEqual(list(data["policies"]), ["REFUND_POLICY"])
        self.assertTrue(data["policies"]["REFUND_POLICY"]["body"].startswith("<p>Refunds within 7 days"))
        self.assertTrue(any("Shipping" in x and "empty" in x for x in data["problems"]))

    def test_problems_and_file(self):
        data = self.read()
        problems = "\n".join(data["problems"])
        self.assertIn("Garam Masala: the price \"about 300\" is not a number", problems)
        self.assertIn("3 in 1 Tea Mix: no Details doc", problems)
        self.assertIn("Kitchen King: no pictures", problems)
        saved = json.loads((self.tmp / "drive.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["product_count"], 4)
        self.assertIn("4 products (5 pictures, 2 without a price)", da.summary(data))

    def test_a_warning_page_is_not_a_picture(self):
        drive = senso_like()
        del drive.files["I_p2_1"]
        data = self.read(drive)
        gm = next(p for p in data["products"] if p["handle"] == "garam-masala")
        self.assertEqual(gm["images"], [])
        self.assertIn("Garam Masala: the picture 1.jpg could not be downloaded", data["problems"])

    def test_rerun_keeps_what_it_has(self):
        self.read()
        drive = senso_like()
        self.read(drive)
        self.assertFalse([u for u in drive.calls if "usercontent" in u and "I_p1_1" in u])

    def test_max_products(self):
        data = self.read(max_products=2)
        self.assertEqual(len(data["products"]), 2)
        self.assertIn("2 more product folders left out (the first 2 are read)", data["problems"])

    def test_folder_errors(self):
        empty = FakeDrive({ROOT_ID: ("Empty", [])})
        with self.assertRaisesRegex(da.DriveError, "empty"):
            self.read(empty)
        no_products = FakeDrive({ROOT_ID: ("B", [("F1", "Pictures", "folder")])})
        with self.assertRaisesRegex(da.DriveError, "No \"2 Products\" folder"):
            self.read(no_products)
        with self.assertRaisesRegex(da.DriveError, "Anyone with the link"):
            self.read(FakeDrive({}))

    def test_docx_details(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", '<w:document><w:body><w:p><w:r><w:t>Price: 150</w:t></w:r></w:p>'
                                            '<w:p><w:r><w:t xml:space="preserve">Description: </w:t></w:r><w:r><w:t>Tasty &amp; fresh</w:t></w:r></w:p>'
                                            '</w:body></w:document>')
        text = da.read_text({"id": "X", "name": "Details.docx", "kind": "file"}, lambda url: (200, url, buf.getvalue()))
        self.assertEqual(text, "Price: 150\nDescription: Tasty & fresh")


class FitsTheCopyPlan(unittest.TestCase):
    def test_make_plan_takes_it(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        data = da.read_folder(ROOT_ID, tmp, get=senso_like(), pause=lambda: None)
        for p in data["products"]:  # the store job uploads the pictures and fills src
            for i in p["images"]:
                i["src"] = f"https://shopify-staged-uploads.storage.googleapis.com/tmp/{Path(i['path']).name}"
        target = {"store": "dtj-testing.myshopify.com", "name": "dtj-testing", "currency": "INR", "password": True,
                  "online_store": "gid://shopify/Publication/1", "empty_policies": ["REFUND_POLICY"], "products": ["kitchen-king-2"],
                  "collections": []}
        plan = bc.make_plan(data, target)
        handles = [p["handle"] for p in plan["products"]]
        self.assertEqual(handles, ["kitchen-king", "garam-masala", "3-in-1-tea-mix"])
        kk = plan["products"][0]
        self.assertEqual([v["price"] for v in kk["variants"]], ["199", "449"])
        self.assertEqual(len(kk["files"]), 3)
        self.assertEqual(plan["policies"][0]["type"], "REFUND_POLICY")
        self.assertEqual(plan["collections"][0]["products"], ["kitchen-king"])


class Retries(unittest.TestCase):
    def test_429_and_5xx_are_tried_again(self):
        answers = [(429, "u", b""), (503, "u", b""), (200, "u", b"ok")]
        waits = []
        orig = da._once
        da._once = lambda url: answers.pop(0)
        try:
            self.assertEqual(da.http_get("u", sleep=waits.append), (200, "u", b"ok"))
        finally:
            da._once = orig
        self.assertEqual(waits, [2, 4])

    def test_gives_up_after_three(self):
        calls = []
        orig = da._once
        da._once = lambda url: calls.append(url) or (500, url, b"")
        try:
            self.assertEqual(da.http_get("u", sleep=lambda s: None)[0], 500)
        finally:
            da._once = orig
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()

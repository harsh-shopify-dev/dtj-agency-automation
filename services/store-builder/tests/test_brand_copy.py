"""The brand copy (provision/brand_copy.py, 21 Oct 2026): what is read from the brand's public store, what the plan creates and never
touches, and the order and safety of the writes. Stand-ins play the brand's website and the target store's Admin API: nothing here
reaches Shopify."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from provision import brand_copy as bc
from provision import gql
from provision.gql import GraphQLError

BASE = "https://glowco.com"
SERUM = {"id": 1, "handle": "glow-serum", "title": "Glow Serum &amp; Co", "body_html": "<p>Bright.</p><script>x()</script>", "vendor": "GlowCo",
         "product_type": "Serum", "tags": ["face", "vitamin c"],
         "options": [{"name": "Size", "position": 1, "values": ["30 ml", "50 ml"]}],
         "variants": [{"option1": "30 ml", "price": "899.00", "compare_at_price": "999.00", "sku": "GS30"},
                      {"option1": "50 ml", "price": "1299.00", "compare_at_price": None, "sku": ""}],
         "images": [{"src": "https://cdn.shopify.com/s/files/1/0001/files/Glow_Serum%201.jpg?v=17", "alt": ""}]}
PLAIN = {"id": 2, "handle": "night-cream", "title": "Night Cream", "body_html": "", "tags": "night, cream",
         "options": [{"name": "Title", "position": 1, "values": ["Default Title"]}],
         "variants": [{"option1": "Default Title", "price": "499.00"}], "images": []}
NO_PRICE = {"id": 3, "handle": "gift", "title": "Gift", "variants": [{"option1": "Default Title", "price": ""}], "options": []}
POLICY_PAGE = ('<html><body><div class="shopify-policy__body">\n<div class="rte"><p>Returns within 7 days of delivery, unopened only. '
               'Write to us at care@glowco.com.</p><script>t()</script></div>\n</div></body></html>')


def brand_site(extra=None):
    pages = {
        f"{BASE}/products.json?limit=250&page=1": json.dumps({"products": [SERUM, PLAIN, NO_PRICE]}),
        f"{BASE}/collections.json?limit=250": json.dumps({"collections": [
            {"handle": "frontpage", "title": "Home"}, {"handle": "skin", "title": "Skin &amp; Care", "body_html": "<p>All skin</p>"},
            {"handle": "empty", "title": "Empty"}]}),
        f"{BASE}/collections/skin/products.json?limit=250&page=1": json.dumps({"products": [{"handle": "glow-serum"}, {"handle": "night-cream"}]}),
        f"{BASE}/collections/empty/products.json?limit=250&page=1": json.dumps({"products": []}),
        f"{BASE}/policies/refund-policy": POLICY_PAGE,
        **(extra or {}),
    }

    def get(url):
        body = pages.get(url)
        return (200, url, body.encode()) if body is not None else (404, url, b"")
    return get


TARGET = {"store": "royal-demo.myshopify.com", "name": "Royal Demo", "currency": "INR", "password": True, "storefront_status": 200,
          "online_store": "gid://shopify/Publication/9", "empty_policies": ["REFUND_POLICY", "SHIPPING_POLICY"],
          "products": ["night-cream"], "collections": []}


class Read(unittest.TestCase):
    def test_the_brands_catalogue_collections_and_policies(self):
        brand = bc.read_brand("glowco.com/collections/all", brand_site(), pause=lambda: None)
        self.assertEqual(brand["base"], BASE)
        self.assertEqual(len(brand["products"]), 3)
        self.assertEqual([c["handle"] for c in brand["collections"]], ["skin"])  # frontpage skipped, an empty one left out
        self.assertEqual(brand["collections"][0]["title"], "Skin & Care")
        pol = brand["policies"]["REFUND_POLICY"]
        self.assertIn("Returns within 7 days", pol["body"])
        self.assertNotIn("<script", pol["body"])
        self.assertEqual(pol["source"], f"{BASE}/policies/refund-policy")

    def test_a_site_without_a_public_catalogue_is_refused(self):
        with self.assertRaises(ValueError):
            bc.read_brand(BASE, lambda url: (404, url, b""), pause=lambda: None)


class Plan(unittest.TestCase):
    def test_a_product_with_its_options_variants_prices_and_pictures(self):
        inp = bc.product_input(SERUM, "ACTIVE")
        self.assertEqual((inp["title"], inp["handle"], inp["status"], inp["vendor"], inp["productType"], inp["tags"]),
                         ("Glow Serum & Co", "glow-serum", "ACTIVE", "GlowCo", "Serum", ["face", "vitamin c"]))
        self.assertEqual(inp["descriptionHtml"], "<p>Bright.</p>")
        self.assertEqual(inp["productOptions"], [{"name": "Size", "position": 1, "values": [{"name": "30 ml"}, {"name": "50 ml"}]}])
        self.assertEqual(inp["variants"][0], {"optionValues": [{"optionName": "Size", "name": "30 ml"}], "price": "899.00",
                                              "inventoryItem": {"tracked": False}, "compareAtPrice": "999.00", "sku": "GS30"})
        self.assertNotIn("compareAtPrice", inp["variants"][1])
        self.assertEqual(inp["files"], [{"originalSource": "https://cdn.shopify.com/s/files/1/0001/files/Glow_Serum%201.jpg?v=17",
                                         "contentType": "IMAGE", "alt": "Glow Serum & Co", "filename": "Glow_Serum 1.jpg"}])
        self.assertEqual(bc.product_input(PLAIN, "DRAFT")["tags"], ["night", "cream"])
        self.assertIsNone(bc.product_input(NO_PRICE, "ACTIVE"))  # never a guessed price

    def test_what_the_target_has_is_left_alone(self):
        brand = bc.read_brand(BASE, brand_site(), pause=lambda: None)
        plan = bc.make_plan(brand, TARGET, "USD")
        self.assertEqual([p["handle"] for p in plan["products"]], ["glow-serum"])
        self.assertEqual(plan["skipped"], {"products_on_target": ["night-cream"], "no_price": ["gift"], "collections_on_target": [],
                                           "policies_not_empty": []})
        self.assertEqual(plan["collections"][0]["products"], ["glow-serum"])  # only products this copy makes
        self.assertEqual([p["type"] for p in plan["policies"]], ["REFUND_POLICY"])
        self.assertEqual(plan["status"], "ACTIVE")
        self.assertIn("prices are the brand's numbers in USD; royal-demo.myshopify.com sells in INR (not converted)", plan["notes"])
        self.assertEqual(bc.summary(plan), "1 products (1 pictures, 2 variants), 1 collections, 1 policy pages, as ACTIVE")

    def test_an_open_store_gets_drafts_and_unreadable_policies_are_said(self):
        brand = bc.read_brand(BASE, brand_site(), pause=lambda: None)
        plan = bc.make_plan(brand, dict(TARGET, password=False, empty_policies=None), None)
        self.assertEqual(plan["status"], "DRAFT")
        self.assertTrue(all(p["status"] == "DRAFT" for p in plan["products"]))
        self.assertEqual(plan["policies"], [])
        self.assertTrue(any("open to the public" in n for n in plan["notes"]))
        self.assertTrue(any("cannot read policies yet" in n and bc.SCOPES in n for n in plan["notes"]))

    def test_every_operation_is_on_the_allowlist_and_none_deletes(self):
        for q in (bc.SET_PRODUCT, bc.CREATE_COLLECTION, bc.PUBLISH, bc.SET_POLICY):
            self.assertEqual(gql.check_operation(q), "mutation")
        for q in (bc.TARGET, bc.TARGET_POLICIES, bc.PRODUCT_HANDLES, bc.COLLECTION_HANDLES):
            self.assertEqual(gql.check_operation(q), "query")
        self.assertFalse([m for m in gql.ALLOWED_MUTATIONS if "delete" in m.lower()])


class FakeAdmin:
    """execute(query, variables) like GraphQLClient; fails the products named in `fail`."""

    def __init__(self, fail=()):
        self.calls, self.fail, self.n = [], set(fail), 0

    def execute(self, query, variables=None):
        self.calls.append((query.split("(")[0].split()[-1], variables))
        self.n += 1
        if "productSet" in query:
            if variables["input"]["handle"] in self.fail:
                raise GraphQLError("Internal error")
            return {"data": {"productSet": {"product": {"id": f"gid://shopify/Product/{self.n}", "handle": variables["input"]["handle"]},
                                            "userErrors": []}}}
        if "collectionCreate" in query:
            return {"data": {"collectionCreate": {"collection": {"id": f"gid://shopify/Collection/{self.n}"}, "userErrors": []}}}
        if "publishablePublish" in query:
            return {"data": {"publishablePublish": {"userErrors": []}}}
        if "shopPolicyUpdate" in query:
            return {"data": {"shopPolicyUpdate": {"shopPolicy": {"type": variables["shopPolicy"]["type"]}, "userErrors": []}}}
        raise AssertionError(query)


class Log:
    def __init__(self):
        self.rows = []

    def record(self, **row):
        self.rows.append(row)


class Apply(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.plan = bc.make_plan(bc.read_brand(BASE, brand_site(), pause=lambda: None), dict(TARGET, products=[]), None)

    def test_collections_first_then_products_in_them_then_empty_policies_each_logged_with_the_approver(self):
        admin, log = FakeAdmin(), Log()
        done = bc.apply(self.plan, admin, self.tmp / "applied.json", log, "Riya (Telegram Approve)", out=lambda *_: None)
        self.assertEqual([c[0] for c in admin.calls], ["CopyCollection", "Publish", "CopyProduct", "Publish", "CopyProduct", "Publish",
                                                       "SetPolicy"])
        first = next(v for name, v in admin.calls if name == "CopyProduct")
        self.assertEqual(first["input"]["collections"], ["gid://shopify/Collection/1"])
        self.assertEqual(next(v for name, v in admin.calls if name == "Publish")["input"], [{"publicationId": "gid://shopify/Publication/9"}])
        self.assertEqual((done["products"], done["collections"], done["policies"], done["failed"]), (2, 1, 1, {}))
        self.assertEqual({r["approver"] for r in log.rows}, {"Riya (Telegram Approve)"})
        again = FakeAdmin()  # a rerun makes nothing twice
        bc.apply(self.plan, again, self.tmp / "applied.json", log, "Riya (Telegram Approve)", out=lambda *_: None)
        self.assertEqual(again.calls, [])

    def test_drafts_are_not_published(self):
        plan = bc.make_plan(bc.read_brand(BASE, brand_site(), pause=lambda: None), dict(TARGET, products=[], password=False), None)
        admin = FakeAdmin()
        bc.apply(plan, admin, self.tmp / "applied.json", Log(), "Harsh", out=lambda *_: None)
        self.assertNotIn("Publish", [c[0] for c in admin.calls])

    def test_a_failed_product_is_kept_for_the_next_run_and_three_in_a_row_stop(self):
        admin = FakeAdmin(fail={"glow-serum"})
        done = bc.apply(self.plan, admin, self.tmp / "applied.json", Log(), "Harsh", out=lambda *_: None)
        self.assertEqual(list(done["failed"]), ["product:glow-serum"])
        self.assertEqual(done["products"], 1)
        many = dict(self.plan, products=[dict(self.plan["products"][0], handle=f"p{i}") for i in range(5)])
        with self.assertRaises(SystemExit):
            bc.apply(many, FakeAdmin(fail={f"p{i}" for i in range(5)}), self.tmp / "other.json", Log(), "Harsh", out=lambda *_: None)

    def test_no_approver_no_import(self):
        with self.assertRaises(ValueError):
            bc.apply(self.plan, FakeAdmin(), self.tmp / "applied.json", Log(), "  ")


if __name__ == "__main__":
    unittest.main()

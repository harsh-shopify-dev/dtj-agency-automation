"""The code nodes of "Store Factory: New Page" run in Node exactly as n8n runs them (node_harness.py): a product link is matched to a
shop in dtj_stores and becomes a brief row; anything else is refused with a plain sentence and nothing is saved.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import unittest

from node_harness import HAS_NODE, run_node

TEST_STORE = {"id": 1, "store_name": "DTJ Test Store", "myshopify_domain": "qaxv3r-8g.myshopify.com",
              "other_domains": "test-store-harsh-dtj.myshopify.com", "draft_theme_id": "167627423941",
              "client_registry": "page_builder/clients/test-store-harsh-dtj.json", "brand_name": "", "brand_website": "",
              "reference_brands": "", "store_notes": "Several brands: take the brand from the product.", "active": True}
CLIENT = {"id": 2, "store_name": "Hope N Skin", "myshopify_domain": "hopenskin-store.myshopify.com", "other_domains": "hopenskin.com, www.hopenskin.com",
          "draft_theme_id": "123456789012", "client_registry": "page_builder/clients/hopenskin.json", "brand_name": "Hope N Skin",
          "brand_website": "https://hopenskin.com", "reference_brands": "Minimalist", "store_notes": "", "active": True}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class NewPage(unittest.TestCase):
    def match(self, link, note="", stores=(TEST_STORE, CLIENT), requested_by="Riya (Telegram)", chat_id="555"):
        req = run_node("take_request.js", {"product_link": link, "note": note, "requested_by": requested_by, "chat_id": chat_id})["out"][0]["json"]
        res = run_node("match_store.js", list(stores) or [{}], {"Take the Request": req})
        self.assertTrue(res["ok"], res)
        return res["out"][0]["json"]

    def test_the_edit_box_as_shipped_asks_for_a_link(self):
        out = run_node("what_to_design.js", {})["out"][0]["json"]
        self.assertEqual((out["product_link"], out["requested_by"]), ("", "n8n (run by hand)"))
        self.assertIn("Please send the product link", self.match(out["product_link"])["message"])

    def test_a_product_link_finds_its_shop_and_becomes_a_brief(self):
        got = self.match("https://test-store-harsh-dtj.myshopify.com/collections/all/products/Pore-Clarifying-Serum?variant=1", note="lead with acne marks")
        self.assertTrue(got["ok"])
        row = got["row"]
        self.assertEqual((row["store_domain"], row["theme_id"], row["client_registry"], row["template_suffix"]),
                         ("qaxv3r-8g.myshopify.com", "167627423941", "page_builder/clients/test-store-harsh-dtj.json", "dtj-pore-clarifying-serum"))
        self.assertEqual(row["product_url"], "https://test-store-harsh-dtj.myshopify.com/products/pore-clarifying-serum")
        self.assertEqual((row["requested_by"], row["telegram_chat_id"], row["status"]), ("Riya (Telegram)", "555", "new"))
        self.assertIn("lead with acne marks", row["notes"])
        self.assertIn("About this shop: Several brands", row["notes"])

    def test_the_shops_own_address_works_and_brings_its_brand(self):
        row = self.match("www.hopenskin.com/products/radiance-serum")["row"]
        self.assertEqual((row["store_domain"], row["brand_name"], row["reference_brands"]), ("hopenskin-store.myshopify.com", "Hope N Skin", "Minimalist"))

    def test_wrong_links_get_a_plain_reason_and_no_brief(self):
        cases = {
            "https://admin.shopify.com/store/qaxv3r-8g/products/10351302934725": "admin link",
            "https://test-store-harsh-dtj.myshopify.com/collections/all": "not a product page",
            "https://unknown-shop.com/products/x": "not set up for page design",
            "not a link at all %%": "does not look like a link",
        }
        for link, words in cases.items():
            got = self.match(link)
            self.assertFalse(got["ok"], link)
            self.assertIn(words, got["message"], link)
            self.assertNotIn("row", got)

    def test_a_paused_or_half_set_up_shop_is_refused(self):
        self.assertIn("paused", self.match("https://hopenskin.com/products/x", stores=({**CLIENT, "active": False},))["message"])
        self.assertIn("no draft theme", self.match("https://hopenskin.com/products/x", stores=({**CLIENT, "draft_theme_id": ""},))["message"])
        self.assertIn("no app copies", self.match("https://hopenskin.com/products/x", stores=({**CLIENT, "client_registry": "../x"},))["message"])
        self.assertIn("not set up", self.match("https://hopenskin.com/products/x", stores=())["message"])  # empty stores table

    def test_the_answers_say_what_happens_next(self):
        refs = {"Match the Store": {"handle": "pore-clarifying-serum", "store_name": "DTJ Test Store"}, "Save Brief": {"id": 7}}
        started = run_node("started.js", {}, refs)["out"][0]["json"]
        self.assertEqual((started["ok"], started["row_id"]), (True, 7))
        self.assertIn("handle the Claude Code trigger in n8n", started["message"])
        stopped = run_node("not_started.js", {"ok": False, "message": "The shop x is not set up"})["out"][0]["json"]
        self.assertEqual((stopped["ok"], stopped["message"]), (False, "The shop x is not set up"))


if __name__ == "__main__":
    unittest.main()

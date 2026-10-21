"""reply.py refuses an answer n8n's reply node would not understand, before anything is sent (no network in these tests).

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import unittest

import reply

PREVIEW = "https://qaxv3r-8g.myshopify.com/products/serum?preview_theme_id=167627423941&view=dtj-hns-vitc"


class Check(unittest.TestCase):
    def test_a_page_written_to_the_draft_carries_its_code_and_preview_link(self):
        body = {"page_status": "written to draft", "approve_code": "5ee449f5807e", "preview_url": PREVIEW, "design_checks": "11/11"}
        self.assertEqual(reply.check(body), "page_design")
        for broken in ({**body, "approve_code": "5ee449"}, {**body, "preview_url": ""},
                       {**body, "preview_url": "https://evil.example/products/x?preview_theme_id=1"}):
            with self.assertRaises(ValueError):
                reply.check(broken)

    def test_the_other_page_answers_and_the_older_flow_still_pass(self):
        for status in ("needs a look", "could not build", "designed (not written)"):
            self.assertEqual(reply.check({"page_status": status}), "page_design")
        self.assertEqual(reply.check({"page_status": "ready for approval", "approve_code": "0123456789ab"}), "page_design")
        self.assertEqual(reply.check({"result": "written to draft", "approved_by": "Harsh"}), "write_to_draft")

    def test_a_reel_answer_needs_its_file_when_ready(self):
        self.assertEqual(reply.check({"reel_status": "reel ready", "final_path": "/home/dtj/reels/n8n-3/final/reel_final.mp4"}), "reel")
        self.assertEqual(reply.check({"reel_status": "could not make", "note": "needs a person: Google sign-in"}), "reel")
        for body in ({"reel_status": "reel ready"}, {"reel_status": "done"}):
            with self.assertRaises(ValueError):
                reply.check(body)

    def test_an_add_shop_answer_is_done_only_with_all_seven_installed(self):
        shop = {"shop": "royal-dosa.myshopify.com", "label": "Royal Dosa", "note": ""}
        self.assertEqual(reply.check({**shop, "shop_status": "done", "installed": 7}), "add_shop")
        self.assertEqual(reply.check({**shop, "shop_status": "waiting for installs", "installed": 2}), "add_shop")
        self.assertEqual(reply.check({**shop, "shop_status": "could not add", "installed": 0, "note": "CLI not signed in"}), "add_shop")
        for body in ({**shop, "shop_status": "done", "installed": 6}, {**shop, "shop_status": "done"}, {**shop, "shop_status": "added"}):
            with self.assertRaises(ValueError):
                reply.check(body)

    def test_a_new_store_answer(self):
        for status in ("done", "partly done", "could not start"):
            self.assertEqual(reply.check({"store_status": status, "shop": "royal-dosa.myshopify.com", "pages": []}), "new_store")
        with self.assertRaises(ValueError):
            reply.check({"store_status": "finished"})

    def test_unknown_or_empty_answers_are_refused(self):
        for body in ({"page_status": "done"}, {}, {"result": "written to draft"}):
            with self.assertRaises(ValueError):
                reply.check(body)

    def test_only_dtj_n8n_resume_urls_are_accepted(self):
        self.assertEqual(reply.main(["--resume-url", "https://example.com/webhook-waiting/1", "--body", "x.json"]), 1)
        self.assertTrue(reply.RESUME.match("https://n8n.srv2048145.hstgr.cloud/webhook-waiting/301?signature=ab12"))
        self.assertFalse(reply.RESUME.match("https://n8n.srv1969859.hstgr.cloud/webhook-waiting/301?signature=ab12"))  # the old server
        self.assertFalse(reply.RESUME.match("https://n8n.srv2048145.hstgr.cloud.evil.example/webhook-waiting/301"))


if __name__ == "__main__":
    unittest.main()

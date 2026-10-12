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

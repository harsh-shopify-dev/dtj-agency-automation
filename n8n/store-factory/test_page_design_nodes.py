"""The code nodes of "Store Factory: Page Design" run in Node exactly as n8n runs them (node_harness.py). The .js files are the source
of truth: deploy_page_design.py sends them to n8n byte for byte.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import json
import unittest
from pathlib import Path

from node_harness import HAS_NODE
from node_harness import run_node as _run

RESUME = "https://n8n.srv2048145.hstgr.cloud/webhook-waiting/301?signature=ab12"


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Nodes(unittest.TestCase):
    def run_node(self, name, given, refs=None):
        return _run(name, given, {"__resume": RESUME, **(refs or {})})

    # ---- Request for Claude Code: Page Design
    def row(self, **extra):
        return {"id": 12, "status": "new", "store_domain": "qaxv3r-8g.myshopify.com", "theme_id": "167627423941", "brand_name": "Hope N Skin",
                "product_url": "https://test-store-harsh-dtj.myshopify.com/products/radiance-serum", "template_suffix": "dtj-radiance-serum",
                "client_registry": "page_builder/clients/test-store-harsh-dtj.json", "brand_website": "https://hopenskin.com",
                "reference_brands": "Minimalist", "notes": "", "brand_json": "{}", "facts_json": "{}", "picture_links_json": "[]", **extra}

    def test_the_request_is_a_complete_task_list_for_a_fresh_session(self):
        res = self.run_node("request_page_design.js", self.row())
        self.assertTrue(res["ok"], res)
        out = res["out"][0]["json"]
        text = out["instructions"]
        for must in ("dtj-pdp-factory", "page_builder.fetch_product --store qaxv3r-8g.myshopify.com --handle radiance-serum",
                     "page_builder.ship_draft --client ../../.work/clients/n8n-12-radiance-serum --store qaxv3r-8g.myshopify.com "
                     "--theme 167627423941 --template-suffix dtj-radiance-serum --client-registry page_builder/clients/test-store-harsh-dtj.json",
                     "--design-only", f'reply.py --resume-url "{RESUME}"', "never the live theme", "SAMPLE", "Minimalist",
                     "docs/HANDOFF.md", "could not build"):
            self.assertIn(must, text)
        self.assertEqual(out["resume_url"], RESUME)
        self.assertEqual(out["request"]["client_folder"], ".work/clients/n8n-12-radiance-serum")
        # the brand intake (19 Oct 2026): the choice is read when the designer starts; the data goes to one folder per website
        for must in ("Read the brief's brand_intake NOW (n8n tool get_data_table_rows, table dtj_client_intake, row id 12)",
                     "python -m page_builder.brand_intake https://hopenskin.com --client ../../.work/clients/intake-hopenskin.com",
                     '"no": do not collect it again', 'empty: ask the person at this laptop',
                     "../../.work/clients/intake-hopenskin.com/intake: start from BRAND.md"):
            self.assertIn(must, text)
        self.assertEqual(out["request"]["intake_folder"], ".work/clients/intake-hopenskin.com")
        site = self.run_node("request_page_design.js", self.row(brand_website="", brand_intake="yes"))["out"][0]["json"]
        self.assertIn("brand_intake https://test-store-harsh-dtj.myshopify.com --client ../../.work/clients/intake-test-store-harsh-dtj.myshopify.com",
                      site["instructions"])  # no brand site: the product link's own address
        self.assertIn("- Brand data first (brand_intake): yes", site["instructions"])
        self.assertIn("Read its brand_website too", site["instructions"])  # the requester may send the brand's own site later
        self.assertNotIn("token", json.dumps(out["request"]).lower())

    def test_a_form_brief_uses_the_client_answers_and_its_handle(self):
        res = self.run_node("request_page_design.js", self.row(product_url="", template_suffix="", client_registry="",
                                                                facts_json=json.dumps({"product": {"handle": "toilova-1"}}),
                                                                brand_json=json.dumps({"brand_name": "TOILOVA"})))
        out = res["out"][0]["json"]
        self.assertIn("--template-suffix dtj-toilova-1", out["instructions"])
        self.assertIn("request.brand and request.facts", out["instructions"])
        self.assertIn('whose "store" is qaxv3r-8g.myshopify.com', out["instructions"])  # find the registry, never guess it

    def test_a_brief_without_a_product_stops(self):
        res = self.run_node("request_page_design.js", self.row(product_url="", facts_json="{}"))
        self.assertFalse(res["ok"])

    # ---- Claude Code Reply: Page Design (the same rules as reply.py)
    def reply(self, body):
        refs = {"Request for Claude Code: Page Design": {"request": {"row_id": 12}}}
        given = {} if body is None else {"body": body}
        return self.run_node("reply_page_design.js", given, refs)["out"][0]["json"]

    def test_the_reply_records_a_written_page_and_refuses_half_answers(self):
        good = {"page_status": "written to draft", "approve_code": "5ee449f5807e", "design_checks": "11/11", "samples": 38,
                "preview_url": "https://qaxv3r-8g.myshopify.com/products/x?preview_theme_id=167627423941&view=dtj-x"}
        got = self.reply(good)
        self.assertEqual((got["row_id"], got["page_status"], got["design_checks"], got["samples"]), (12, "written to draft", "11/11", 38))
        self.assertEqual(got["approved_by"], "Harsh (standing: draft pushes without asking)")
        self.assertEqual(self.reply({**good, "preview_url": "https://evil.example/?preview_theme_id=1"})["page_status"],
                         "reply not understood (no code or preview link)")
        self.assertEqual(self.reply({"page_status": "could not build", "note": "no Theme Access password"})["approved_by"], "")
        self.assertEqual(self.reply(None)["page_status"], "timed out (no reply in 3 days)")

    def test_the_real_ship_result_is_understood(self):
        ship = Path(__file__).resolve().parents[2] / ".work/clients/test-store-hopenskin-vitc/run/ship-result.json"
        if not ship.exists():
            self.skipTest("no local ship-result.json")
        got = self.reply(json.loads(ship.read_text(encoding="utf-8")))
        self.assertEqual(got["page_status"], "written to draft")


if __name__ == "__main__":
    unittest.main()

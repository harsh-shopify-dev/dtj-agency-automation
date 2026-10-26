"""dtj (Hermes Agent -> the reel factory) with a stand-in n8n: the reel bot's own code nodes decide, New Reel is started like the bot.

    python -m unittest tools/hermes/test_dtj.py
"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "n8n" / "store-factory"))
import dtj  # noqa: E402
from node_harness import HAS_NODE  # noqa: E402

NOW = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
TEAM = [{"telegram_user_id": "7051933055", "name": "Harsh", "role": "admin", "active": True}]
IDS = {"dtj_bot_users": "U", "dtj_bot_answers": "A", "dtj_reel_jobs": "J", "dtj_reel_settings": "S"}


class FakeN8n:
    def __init__(self, team=TEAM, today=(), settings=()):
        self.data = {"U": list(team), "A": [], "J": list(today), "S": list(settings)}
        self.calls = []

    def __call__(self, tool, args):
        self.calls.append((tool, args))
        if tool == "get_workflow_details":
            raise RuntimeError("offline: use the repo's copy of the bot's nodes")
        if tool == "search_data_tables":
            return {"data": [{"name": k, "id": v} for k, v in IDS.items()]}
        if tool == "get_data_table_rows":
            return {"data": self.data[args["dataTableId"]]}
        if tool == "execute_workflow":
            return {"executionId": "1900", "status": "started"}
        raise AssertionError(tool)


@unittest.skipUnless(HAS_NODE, "Node.js runs the reel bot's code nodes")
class Dtj(unittest.TestCase):
    def run_dtj(self, sub, text, fake, user="7051933055"):
        return dtj.handle(user, "Harsh", sub, text, call=fake, now=NOW, code_dir=Path(tempfile.mkdtemp()))

    def test_remake_starts_new_reel_like_the_bot(self):
        fake = FakeN8n()
        res = self.run_dtj("remake", "https://www.instagram.com/reel/DZhYs5wu_n3/ https://shop.example/products/garam-masala "
                                     "Mahalaxmi Garam Masala for: Gujarati home cooks", fake)
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "reel")
        run = [a for t, a in fake.calls if t == "execute_workflow"][0]
        form = run["inputs"]["formData"]
        self.assertEqual((run["workflowId"], run["triggerNodeName"]), (dtj.NEW_REEL, "New UGC Reel"))
        self.assertEqual((form["reel_type"], form["chat_id"], form["requested_by"]), ("remake", "7051933055", "Harsh"))
        self.assertEqual(form["reference_reels"], "https://www.instagram.com/reel/DZhYs5wu_n3/")
        self.assertEqual(form["audience"], "Gujarati home cooks")
        self.assertIn("@dtj_reels_bot", res["say"])

    def test_refusals_are_the_bots(self):
        self.assertIn("only for the DTJ team", self.run_dtj("status", "", FakeN8n(team=[]))["say"])
        full = FakeN8n(today=[{"product_name": "x"}] * 3, settings=[{"key": "daily_limit", "value": "3"}])
        res = self.run_dtj("remake", "https://www.instagram.com/reel/A/ https://shop.example/p", full)
        self.assertIn("limit of 3", res["say"])
        self.assertFalse(any(t == "execute_workflow" for t, _ in full.calls))
        self.assertIn("ONE reference reel", self.run_dtj("remake", "https://shop.example/p", FakeN8n())["say"])

    def test_needs_the_telegram_sender(self):
        res = self.run_dtj("remake", "x", FakeN8n(), user="")
        self.assertFalse(res["ok"])
        self.assertIn("from Telegram", res["say"])

    def test_status_and_plain_text(self):
        res = self.run_dtj("status", "", FakeN8n(today=[{"product_name": "Senso", "reel_type": "ugc", "reel_status": "new"}]))
        self.assertIn("Today: 1 of 10 reels", res["say"])
        self.assertNotIn("<b>", res["say"])

    def test_unknown_sub_command(self):
        self.assertFalse(self.run_dtj("deploy", "", FakeN8n())["ok"])


if __name__ == "__main__":
    unittest.main()

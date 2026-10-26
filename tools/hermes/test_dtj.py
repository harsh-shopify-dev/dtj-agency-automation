"""dtj (Hermes Agent -> the reel factory) with a stand-in n8n: the reel bot's own code nodes decide, New Reel is started like the bot.

    python -m unittest tools/hermes/test_dtj.py
"""
import json
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
        if tool == "add_data_table_rows":
            self.data[args["dataTableId"]] += args["rows"]
            return {"inserted": len(args["rows"])}
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
        self.assertIn("tap Start", res["say"])

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

    def test_photo_then_remake_uses_it(self):
        import base64
        dtj.PHOTOS_ROOT[0] = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: dtj.PHOTOS_ROOT.__setitem__(0, None))
        jpg = base64.b64encode(bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * 64).decode()
        saved = dtj.handle("7051933055", "Harsh", "photo", jpg, call=FakeN8n(), now=datetime.now(timezone.utc))
        self.assertTrue(saved["ok"], saved)
        self.assertIn("Photo saved (1 ", saved["say"])
        fake = FakeN8n()
        res = dtj.handle("7051933055", "Harsh", "remake", "https://www.instagram.com/reel/DZhYs5wu_n3/ Mahalaxmi Garam Masala",
                         call=fake, now=datetime.now(timezone.utc), code_dir=Path(tempfile.mkdtemp()))
        self.assertEqual(res["action"], "reel", res)
        form = [a for t, a in fake.calls if t == "execute_workflow"][0]["inputs"]["formData"]
        self.assertEqual(form["product_images"], saved["path"])          # a VPS path, no tg: and no HP: mark
        self.assertEqual(form["product_name"], "Mahalaxmi Garam Masala")

    def test_photo_refusals(self):
        import base64
        dtj.PHOTOS_ROOT[0] = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: dtj.PHOTOS_ROOT.__setitem__(0, None))
        jpg = base64.b64encode(bytes([0xFF, 0xD8, 0xFF]) + b"x" * 10).decode()
        self.assertIn("only for the DTJ team", dtj.handle("4242424", "X", "photo", jpg, call=FakeN8n(team=[]), now=NOW)["say"])
        self.assertFalse(dtj.handle("7051933055", "Harsh", "photo", base64.b64encode(b"<html>").decode(), call=FakeN8n(), now=NOW)["ok"])


    def test_button_tap_is_saved_like_the_old_bot(self):
        fake = FakeN8n()
        tap = {"callback_query": {"id": "cb1", "from": {"id": 7051933055, "first_name": "Harsh", "is_bot": False}, "data": "a:r42:pictures1:0",
                                  "message": {"chat": {"id": 7051933055, "type": "private"},
                                              "reply_markup": {"inline_keyboard": [[{"text": "Approve", "callback_data": "a:r42:pictures1:0"}]]}}}}
        res = dtj.handle("7051933055", "Harsh", "tg", json.dumps(tap), call=fake, now=NOW, code_dir=Path(tempfile.mkdtemp()))
        self.assertEqual(res["action"], "answer", res)
        row = fake.data["A"][-1]
        self.assertEqual((row["job"], row["key"], row["value"], row["choice"], row["by"], row["chat_id"]),
                         ("r42", "pictures1", "Approve", "0", "Harsh", "7051933055"))
        self.assertIn("Approved by Harsh", res["say"])

    def test_reply_to_a_question_and_forged_sender(self):
        fake = FakeN8n()
        reply = {"message": {"chat": {"id": 7051933055, "type": "private"}, "from": {"id": 7051933055, "first_name": "Harsh", "is_bot": False},
                             "text": "make the box bigger", "reply_to_message": {"from": {"id": 1, "is_bot": True},
                                                                                "text": "What should change?\n\n(job r42, answer pictures1n)"}}}
        res = dtj.handle("7051933055", "Harsh", "tg", json.dumps(reply), call=fake, now=NOW, code_dir=Path(tempfile.mkdtemp()))
        self.assertEqual((res["action"], fake.data["A"][-1]["value"], fake.data["A"][-1]["key"]), ("answer", "make the box bigger", "pictures1n"))
        res = dtj.handle("4242424", "X", "tg", json.dumps(reply), call=FakeN8n(), now=NOW, code_dir=Path(tempfile.mkdtemp()))
        self.assertFalse(res["ok"])
        self.assertIn("sender did not match", res["say"])


    def test_plain_text_never_answers_a_store_question(self):
        fake = FakeN8n()
        fake.data["A"] = [{"job": "page-12", "key": "chat", "value": "", "choice": "open", "chat_id": "7051933055", "at": "2026-10-24T09:52:36Z"}]
        res = self.run_dtj("say", "Start, and the reel is for diwali", fake)
        self.assertNotEqual(res["action"], "answer")
        self.assertEqual(len(fake.data["A"]), 1)
        fake.data["A"].append({"job": "r42", "key": "plan1n", "value": "", "choice": "open", "chat_id": "7051933055", "at": "2026-10-26T09:00:00Z"})
        res = self.run_dtj("say", "show all four flavours", fake)
        self.assertEqual((res["action"], fake.data["A"][-1]["job"]), ("answer", "r42"))


if __name__ == "__main__":
    unittest.main()

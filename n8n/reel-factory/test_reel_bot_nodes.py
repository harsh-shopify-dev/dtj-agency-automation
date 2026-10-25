"""The code nodes of "Reel Factory: Telegram Bot" run in Node exactly as n8n runs them (../store-factory/node_harness.py).

    python -m unittest n8n/reel-factory/test_reel_bot_nodes.py
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))
from node_harness import HAS_NODE, run_node  # noqa: E402

CHAT = {"id": 70, "type": "private"}
HARSH = {"id": 7051933055, "first_name": "Harsh", "is_bot": False}
USERS = [{"telegram_user_id": "7051933055", "name": "Harsh", "role": "admin", "active": True},
         {"telegram_user_id": "42", "name": "Asha", "role": "requester", "active": True}]


def msg(text="", **extra):
    return {"message": {"chat": CHAT, "from": HARSH, "text": text, **extra}}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class ReelBot(unittest.TestCase):
    def read(self, update):
        return run_node(HERE / "reel_bot_read.js", update)["out"][0]["json"]

    def route(self, update, users=USERS, today=(), settings=(), photos=(), marks=()):
        refs = {"Read the Message": self.read(update), "Load Bot Users": list(users), "Load Open Questions": list(marks),
                "Load Today's Reels": list(today), "Load Settings": list(settings), "Load Recent Photos": list(photos)}
        out = run_node(HERE / "reel_bot_route.js", {}, refs)["out"]
        return out[0]["json"] if out else None

    def test_kinds(self):
        self.assertEqual(self.read(msg("/remake https://www.instagram.com/reel/X/"))["kind"], "remake")
        self.assertEqual(self.read(msg("/reels 12"))["kind"], "limit")
        self.assertEqual(self.read(msg("123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"))["kind"], "secret")
        photo = self.read({"message": {"chat": CHAT, "from": HARSH, "photo": [{"file_id": "small"}, {"file_id": "BIGfileid1234"}]}})
        self.assertEqual((photo["kind"], photo["photo_id"]), ("photo", "BIGfileid1234"))
        tap = {"callback_query": {"id": "cb1", "from": HARSH, "data": "a:r42:pictures1:0",
                                  "message": {"chat": CHAT, "reply_markup": {"inline_keyboard": [[{"text": "Approve", "callback_data": "a:r42:pictures1:0"}]]}}}}
        t = self.read(tap)
        self.assertEqual((t["kind"], t["job"], t["key"], t["arg"]), ("answer", "r42", "pictures1", "Approve"))
        self.assertEqual(self.read({"message": {"chat": {"id": -5, "type": "group"}, "from": HARSH, "text": "/help"}})["kind"], "ignore")

    def test_remake_from_photos_and_links(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        got = self.route(msg("/remake https://www.instagram.com/reel/DZhYs5wu_n3/ Mahalaxmi Garam Masala for: Gujarati home cooks 30-50"),
                         photos=[{"value": "PHOTO1abcdefgh", "at": now}, {"value": "OLDphoto", "at": "2020-01-01T00:00:00Z"}])
        self.assertEqual(got["action"], "reel")
        i = got["inputs"]
        self.assertEqual((i["reel_type"], i["product_name"], i["audience"]), ("remake", "Mahalaxmi Garam Masala", "Gujarati home cooks 30-50"))
        self.assertEqual(i["product_images"], "tg:PHOTO1abcdefgh")
        self.assertEqual(i["reference_reels"], "https://www.instagram.com/reel/DZhYs5wu_n3/")
        self.assertEqual(i["chat_id"], "70")

    def test_limits_access_and_open_questions(self):
        self.assertIn("only for the DTJ team", self.route(msg("/help"), users=[])["text"])
        full = self.route(msg("/remake https://www.instagram.com/reel/A/ https://shop.example/products/masala"),
                          today=[{"product_name": "x"}] * 3, settings=[{"key": "daily_limit", "value": "3"}])
        self.assertIn("limit of 3", full["text"])
        self.assertEqual(self.route(msg("/reels 5"))["value"], "5")
        asha = {"message": {"chat": CHAT, "from": {"id": 42, "first_name": "Asha"}, "text": "/reels 5"}}
        self.assertIn("Only an admin", self.route(asha)["text"])
        open_q = [{"job": "r42", "key": "pictures1n", "value": "", "choice": "open", "chat_id": "70", "at": "2026-10-25T10:00:00Z"}]
        ans = self.route(msg("3: the box is too small"), marks=open_q)
        self.assertEqual((ans["action"], ans["job"], ans["key"], ans["value"]), ("answer", "r42", "pictures1n", "3: the box is too small"))
        self.assertIn("ONE reference reel", self.route(msg("/remake https://shop.example/p"))["text"])

    def test_refs_and_audience(self):
        r = self.route(msg("/refs Blue Tea India meta"))
        self.assertEqual((r["action"], r["inputs"]["query"], r["inputs"]["sources"], r["inputs"]["mode"]), ("refs", "Blue Tea India", "meta", "refs"))
        a = self.route(msg("/audience Gen Z urban India #genz #mumbaifood @foodie.creator"))
        self.assertEqual((a["inputs"]["mode"], a["inputs"]["audience"], a["inputs"]["hashtags"], a["inputs"]["creators"]),
                         ("audience", "Gen Z urban India", "#genz #mumbaifood", "@foodie.creator"))

    def test_reply_texts(self):
        who = {"action": "answer", "chat_id": "70", "value": "Approve", "by": "Harsh"}
        out = run_node(HERE / "reel_bot_reply.js", {"id": 1}, {"Who Is It": who})["out"][0]["json"]
        self.assertIn("Approved by Harsh", out["text"])
        err = run_node(HERE / "reel_bot_reply.js", {"error": {"message": "table down"}}, {"Who Is It": who})["out"][0]["json"]
        self.assertIn("did not go through", err["text"])


if __name__ == "__main__":
    unittest.main()

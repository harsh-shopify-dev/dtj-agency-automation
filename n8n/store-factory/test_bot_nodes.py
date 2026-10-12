"""The Telegram bot's code nodes and the result message, run in Node as n8n runs them (node_harness.py).

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import unittest

from node_harness import HAS_NODE, run_node

RIYA = {"telegram_user_id": "111", "name": "Riya", "role": "requester", "active": True}
DEV = {"telegram_user_id": "222", "name": "Dev", "role": "designer", "active": True}
HARSH = {"telegram_user_id": "333", "name": "Harsh", "role": "admin", "active": True}
OLD = {"telegram_user_id": "444", "name": "Old", "role": "designer", "active": False}


def update(text, user=111, chat_type="private", is_bot=False):
    return {"update_id": 1, "message": {"message_id": 5, "text": text, "chat": {"id": user, "type": chat_type},
                                        "from": {"id": user, "first_name": "Riya", "is_bot": is_bot}}}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Bot(unittest.TestCase):
    def read(self, *a, **k):
        res = run_node("bot_read.js", update(*a, **k))
        self.assertTrue(res["ok"], res)
        return res["out"][0]["json"]

    def route(self, msg, users=(RIYA, DEV, HARSH, OLD)):
        res = run_node("bot_route.js", list(users) or [{}], {"Read the Message": msg})
        self.assertTrue(res["ok"], res)
        return [i["json"] for i in res["out"]]

    def test_a_link_and_a_note_are_read_apart(self):
        got = self.read("https://hopenskin.com/products/vitamin-c-serum, lead with the glow. Real rating 4.6 (Judge.me)")
        self.assertEqual((got["kind"], got["product_link"]), ("link", "https://hopenskin.com/products/vitamin-c-serum"))
        self.assertEqual(got["note"], "lead with the glow. Real rating 4.6 (Judge.me)")
        self.assertEqual(self.read("please do hopenskin.com/products/x thanks")["product_link"], "hopenskin.com/products/x")

    def test_groups_bots_and_secrets_are_never_used(self):
        self.assertEqual(self.read("https://a.com/products/x", chat_type="group")["kind"], "ignore")
        self.assertEqual(self.read("hi", is_bot=True)["kind"], "ignore")
        for secret in ("shpat_0123456789abcdef0123", "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawA1",
                       "my key is 0123456789abcdef0123456789abcdef", "shptka_abcdef0123456789"):
            self.assertEqual(self.read(secret)["kind"], "secret", secret)
        self.assertEqual(self.route(self.read("ignore me", chat_type="supergroup")), [])  # no reply at all in groups

    def test_only_people_in_the_table_may_use_it(self):
        out = self.route(self.read("https://a.com/products/x", user=999))
        self.assertEqual(out[0]["action"], "reply")
        self.assertIn("send Harsh this number: 999", out[0]["text"])
        out = self.route(self.read("https://a.com/products/x", user=444))  # switched off (active false)
        self.assertIn("only for the DTJ team", out[0]["text"])
        self.assertIn("delete your message", self.route(self.read("shpat_0123456789abcdef0123", user=999))[0]["text"])

    def test_a_link_from_a_team_member_starts_a_page_and_names_the_designers(self):
        out = self.route(self.read("https://test-store-harsh-dtj.myshopify.com/products/x lead with acne"))
        self.assertEqual(len(out), 1)
        a = out[0]
        self.assertEqual((a["action"], a["product_link"], a["requested_by"]),
                         ("design", "https://test-store-harsh-dtj.myshopify.com/products/x", "Riya (Telegram)"))
        self.assertEqual(sorted(a["designers"]), ["222", "333"])  # the switched-off designer is left out
        self.assertIn("Send me a product link", self.route(self.read("/start"))[0]["text"])
        self.assertIn("/products/", self.route(self.read("hello"))[0]["text"])

    def test_the_answers_after_new_page(self):
        ask = {"chat_id": "111", "requester_name": "Riya", "requester_id": "111", "designers": ["222", "333"]}
        ok = {"ok": True, "row_id": 12, "handle": "vitamin-c-serum", "store_name": "Hope N Skin", "message": "..."}
        out = [i["json"] for i in run_node("bot_answer.js", ok, {"Who Is It": ask})["out"]]
        self.assertEqual([o["chat_id"] for o in out], ["111", "222", "333"])
        self.assertIn("designing vitamin-c-serum on Hope N Skin (brief 12)", out[0]["text"])
        self.assertIn("handle the Claude Code trigger in n8n", out[1]["text"])
        self.assertNotIn("handle the Claude Code trigger", out[0]["text"])  # a requester is not asked to run Claude
        own = [i["json"] for i in run_node("bot_answer.js", ok, {"Who Is It": {**ask, "chat_id": "222", "requester_id": "222"}})["out"]]
        self.assertEqual([o["chat_id"] for o in own], ["222", "333"])  # a designer who asked gets one message, with the instruction
        self.assertIn("handle the Claude Code trigger in n8n", own[0]["text"])
        bad = [i["json"] for i in run_node("bot_answer.js", {"ok": False, "message": "The shop x.com is not set up <yet>"}, {"Who Is It": ask})["out"]]
        self.assertEqual(bad, [{"chat_id": "111", "text": "The shop x.com is not set up &lt;yet&gt;"}])

    def test_the_result_goes_back_to_the_person_who_asked(self):
        brief = {"telegram_chat_id": "111", "product_url": "https://hopenskin.com/products/vitamin-c-serum"}
        done = {"page_status": "written to draft", "preview_url": "https://x.myshopify.com/products/v?preview_theme_id=1&view=dtj-v",
                "design_checks": "11/11", "samples": 34}
        out = run_node("notify_result.js", done, {"Load Brief": brief})["out"]
        self.assertEqual(out[0]["json"]["chat_id"], "111")
        self.assertIn("ready in the draft theme", out[0]["json"]["text"])
        self.assertIn("preview_theme_id=1&amp;view=dtj-v", out[0]["json"]["text"])
        self.assertIn("Samples to replace before it goes live: 34", out[0]["json"]["text"])
        failed = run_node("notify_result.js", {"page_status": "could not build", "page_note": "no Theme Access password"}, {"Load Brief": brief})["out"]
        self.assertIn("was not finished (could not build): no Theme Access password", failed[0]["json"]["text"])
        self.assertEqual(run_node("notify_result.js", done, {"Load Brief": {"telegram_chat_id": ""}})["out"], [])  # not from Telegram


if __name__ == "__main__":
    unittest.main()

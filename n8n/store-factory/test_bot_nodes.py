"""The Telegram bot's code nodes and the result message, run in Node as n8n runs them (node_harness.py).

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import unittest

from node_harness import HAS_NODE, run_node

RIYA = {"telegram_user_id": "111", "name": "Riya", "role": "requester", "active": True}
DEV = {"telegram_user_id": "222", "name": "Dev", "role": "designer", "active": True}
HARSH = {"telegram_user_id": "333", "name": "Harsh", "role": "admin", "active": True}
OLD = {"telegram_user_id": "444", "name": "Old", "role": "designer", "active": False}


TEST_STORE = {"store_name": "DTJ Test Store", "myshopify_domain": "qaxv3r-8g.myshopify.com", "other_domains": "test-store-harsh-dtj.myshopify.com",
              "client_registry": "page_builder/clients/test-store-harsh-dtj.json", "active": True}
ELEVATE = {"store_name": "Elevate with Harsh", "myshopify_domain": "elevate-with-harsh.myshopify.com", "other_domains": "",
           "client_registry": "page_builder/clients/elevate-with-harsh.json", "active": True}
SHOPS = [TEST_STORE, ELEVATE]


def update(text, user=111, chat_type="private", is_bot=False):
    return {"update_id": 1, "message": {"message_id": 5, "text": text, "chat": {"id": user, "type": chat_type},
                                        "from": {"id": user, "first_name": "Riya", "is_bot": is_bot}}}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Bot(unittest.TestCase):
    def read(self, *a, **k):
        res = run_node("bot_read.js", update(*a, **k))
        self.assertTrue(res["ok"], res)
        return res["out"][0]["json"]

    def route(self, msg, users=(RIYA, DEV, HARSH, OLD), shops=None):
        shops = SHOPS if shops is None else shops
        res = run_node("bot_route.js", list(shops) or [{}], {"Read the Message": msg, "Load Bot Users": list(users) or [{}]})
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


def button(data, user=333):
    return {"update_id": 2, "callback_query": {"id": "cb1", "data": data, "from": {"id": user, "first_name": "Harsh", "is_bot": False},
                                               "message": {"message_id": 9, "chat": {"id": user, "type": "private"}}}}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class AppSwitch(unittest.TestCase):
    def read(self, upd):
        return run_node("bot_read.js", upd)["out"][0]["json"]

    def route(self, msg, users=(RIYA, DEV, HARSH, OLD)):
        res = run_node("bot_route.js", SHOPS, {"Read the Message": msg, "Load Bot Users": list(users)})
        self.assertTrue(res["ok"], res)
        return [i["json"] for i in res["out"]]

    def cmd(self, text, user=333):
        return self.route(self.read(update(text, user=user)))

    def test_commands_and_buttons_are_read(self):
        got = self.read(update("/off@DtjPageDesignerBot test store", user=333))
        self.assertEqual((got["kind"], got["command"], got["arg"]), ("command", "off", "test store"))
        tap = self.read(button("lic:off:test-store-harsh-dtj:1791790000"))
        self.assertEqual((tap["kind"], tap["data"], tap["callback_id"], tap["chat_id"]), ("button", "lic:off:test-store-harsh-dtj:1791790000", "cb1", "333"))
        self.assertEqual(self.read({"callback_query": {"id": "x", "data": "lic:cancel", "from": {"id": 1},
                                                       "message": {"chat": {"id": -5, "type": "group"}}}})["kind"], "ignore")

    def test_only_admins_may_see_or_switch(self):
        for text in ("/status test store", "/off test store", "/shops"):
            out = self.cmd(text, user=222)  # a designer
            self.assertEqual(out[0]["action"], "reply")
            self.assertIn("Only an admin", out[0]["text"])
        self.assertIn("Only an admin", self.route(self.read(button("lic:off:test-store-harsh-dtj:%d" % __import__("time").time(), user=111)))[0]["text"])

    def test_admin_commands_and_fresh_taps_go_to_the_switch_path(self):
        import time
        now = int(time.time())
        st = self.cmd("/status Test Store")[0]
        self.assertEqual((st["action"], st["command"], st["arg"]), ("switch", "status", "Test Store"))
        self.assertEqual(self.cmd("/shops")[0]["command"], "shops")
        go = self.route(self.read(button(f"lic:off:test-store-harsh-dtj:{now}")))[0]
        self.assertEqual((go["action"], go["command"], go["state"], go["client"], go["actor"], go["admins"]),
                         ("switch", "tap", "inactive", "test-store-harsh-dtj", "Harsh", []))
        self.assertIn("expired", self.route(self.read(button(f"lic:off:test-store-harsh-dtj:{now - 121}")))[0]["text"])
        self.assertIn("Cancelled", self.route(self.read(button("lic:cancel")))[0]["text"])
        self.assertIn("not valid", self.route(self.read(button("lic:off:../../x:1")))[0]["text"])
        self.assertIn("Which shop", self.cmd("/status")[0]["text"])
        two = self.route(self.read(button(f"lic:on:test-store-harsh-dtj:{now}")), users=(HARSH, {**DEV, "role": "admin"}))[0]
        self.assertEqual((two["state"], two["admins"]), ("active", ["222"]))  # the other admin is told afterwards


# the install catcher's list (worker.js listShops): client copies, DTJ's original apps on an organization store, an app-only client
def apps(client, label, parts=("blocks", "sections", "sections2")):
    names = {"blocks": "DTJ Blocks", "sections": "DTJ Sections", "sections2": "DTJ Sections 2"}
    return [{"app": f"{client}-{p}", "part": p, "label": f"{names[p]} - {label}"} for p in parts]


CATCHER_LIST = {"statusCode": 200, "body": {"shops": [
    {"client": "elevate-with-harsh", "shop": "elevate-with-harsh.myshopify.com", "name": "Elevate with Harsh", "kind": "dtj apps",
     "apps": apps("elevate-with-harsh", "Elevate with Harsh")},
    {"client": "rupa-divine-crystals", "shop": "rupa-divine-crystals.myshopify.com", "name": "Rupa Divine", "kind": "client copies",
     "apps": apps("rupa-divine-crystals", "Rupa Divine")},
    {"client": "test-store-harsh-dtj", "shop": "qaxv3r-8g.myshopify.com", "name": "Test Store", "kind": "client copies",
     "apps": apps("test-store-harsh-dtj", "Test Store")}]}}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class PickTheShop(unittest.TestCase):
    def pick(self, command, arg="", listing=CATCHER_LIST, shops=SHOPS, **ask):
        who = {"action": "switch", "chat_id": "333", "actor": "Harsh", "admins": ["222"], "command": command, "arg": arg,
               "state": "", "client": "", **ask}
        res = run_node("bot_switch.js", listing, {"Who Is It": who, "Load Shops": list(shops) or [{}]})
        self.assertTrue(res["ok"], res)
        return [i["json"] for i in res["out"]]

    def test_shops_lists_every_shop_the_catcher_knows_and_the_page_only_ones(self):
        out = self.pick("shops", shops=SHOPS + [{"store_name": "Hope N Skin", "myshopify_domain": "hopenskin.myshopify.com",
                                                 "client_registry": "", "active": True}])[0]
        self.assertEqual((out["action"], out["state"], out["listing"]), ("licence", "status", True))
        self.assertEqual([s["client"] for s in out["shops"]], ["elevate-with-harsh", "rupa-divine-crystals", "test-store-harsh-dtj"])
        self.assertEqual(out["shops"][2]["name"], "DTJ Test Store")  # the friendlier name from dtj_stores
        self.assertEqual(out["shops"][1]["name"], "Rupa Divine")  # an app-only client: not in dtj_stores, still on the switch
        self.assertEqual(out["missing"], ["Hope N Skin"])
        self.assertNotIn("names", out["shops"][0])

    def test_a_shop_is_found_by_any_of_its_names_and_off_asks_for_a_tap_first(self):
        for arg in ("rupa", "Rupa Divine", "rupa-divine-crystals.myshopify.com", "https://rupa-divine-crystals.myshopify.com/admin"):
            st = self.pick("status", arg)[0]
            self.assertEqual((st["action"], [s["client"] for s in st["shops"]]), ("licence", ["rupa-divine-crystals"]), arg)
        self.assertEqual(self.pick("status", "test-store-harsh-dtj.myshopify.com")[0]["shops"][0]["client"], "test-store-harsh-dtj")
        off = self.pick("off", "elevate")[0]
        self.assertEqual((off["action"], off["yes_text"]), ("confirm", "Yes, switch OFF"))  # nothing switches before the tap
        self.assertRegex(off["yes_data"], r"^lic:off:elevate-with-harsh:\d{10}$")
        self.assertIn("elevate-with-harsh.myshopify.com", off["text"])
        self.assertIn("More than one shop", self.pick("status", "harsh")[0]["text"])
        self.assertIn("No shop matches", self.pick("status", "royal dosa")[0]["text"])

    def test_a_tap_switches_only_a_shop_still_on_the_list(self):
        go = self.pick("tap", state="inactive", client="elevate-with-harsh")[0]
        self.assertEqual((go["action"], go["state"], go["approved_by"], go["reason"], go["admins"]),
                         ("licence", "inactive", "Harsh via Telegram", "Telegram /off", ["222"]))
        self.assertEqual([a["app"] for a in go["shops"][0]["apps"]],
                         ["elevate-with-harsh-blocks", "elevate-with-harsh-sections", "elevate-with-harsh-sections2"])
        self.assertIn("not on the switch any more", self.pick("tap", state="active", client="gone-shop")[0]["text"])

    def test_a_page_shop_without_the_switch_and_a_broken_list_are_explained(self):
        only_test = {"statusCode": 200, "body": {"shops": CATCHER_LIST["body"]["shops"][2:]}}
        self.assertIn("not on the switch yet", self.pick("status", "elevate", listing=only_test)[0]["text"])
        self.assertIn("refused the bot's key", self.pick("shops", listing={"statusCode": 401, "body": {"error": "bad signature"}})[0]["text"])
        self.assertIn("could not reach", self.pick("shops", listing={"error": {"message": "timeout"}})[0]["text"])

    def test_the_calls_and_the_reports(self):
        import json
        pick = self.pick("tap", state="inactive", client="test-store-harsh-dtj")[0]
        calls = [i["json"] for i in run_node("licence_calls.js", pick)["out"]]
        self.assertEqual([c["app"] for c in calls], ["test-store-harsh-dtj-blocks", "test-store-harsh-dtj-sections", "test-store-harsh-dtj-sections2"])
        self.assertEqual([c["label"] for c in calls], ["DTJ Blocks", "DTJ Sections", "DTJ Sections 2"])
        body = json.loads(calls[0]["body"])
        self.assertEqual((body["state"], body["approved_by"]), ("inactive", "Harsh via Telegram"))
        answers = [{"statusCode": 200, "body": {"before": "active", "after": "inactive", "verified": True}}] * 3
        out = [i["json"] for i in run_node("licence_report.js", answers, {"Pick the Shop": pick, "Licence Calls": calls})["out"]]
        self.assertEqual([o["chat_id"] for o in out], ["333", "222"])
        self.assertIn("Done: all DTJ apps on DTJ Test Store are OFF.", out[0]["text"])
        self.assertIn("DTJ Sections 2: ON -> OFF (checked)", out[0]["text"])
        self.assertIn("Harsh switched OFF", out[1]["text"])
        mixed = answers[:2] + [{"statusCode": 401, "body": {"error": "bad signature"}}]
        self.assertIn("Not everything switched", run_node("licence_report.js", mixed, {"Pick the Shop": pick, "Licence Calls": calls})["out"][0]["json"]["text"])

        listing = self.pick("shops")[0]
        calls = [i["json"] for i in run_node("licence_calls.js", listing)["out"]]
        self.assertEqual(len(calls), 9)
        self.assertNotIn("approved_by", json.loads(calls[0]["body"]))  # a status call changes nothing
        state = {"elevate-with-harsh": {"statusCode": 200, "body": {"licence": None}},
                 "rupa-divine-crystals": {"statusCode": 404, "body": {"error": "no store key for x: the store has not installed it (or uninstalled it)"}},
                 "test-store-harsh-dtj": {"statusCode": 200, "body": {"licence": "active"}}}
        txt = run_node("licence_report.js", [state[c["client"]] for c in calls], {"Pick the Shop": listing, "Licence Calls": calls})["out"][0]["json"]["text"]
        self.assertIn("Elevate with Harsh (elevate-with-harsh.myshopify.com, DTJ's own apps)\nDTJ Blocks: not set (blocks hidden)", txt)
        self.assertIn("Rupa Divine (rupa-divine-crystals.myshopify.com)\nDTJ Blocks: not installed on the shop", txt)
        self.assertIn("DTJ Test Store (qaxv3r-8g.myshopify.com)\nDTJ Blocks: ON\nDTJ Sections: ON\nDTJ Sections 2: ON", txt)
        self.assertIn("for example: /status Elevate with Harsh", txt)
        org = [{"statusCode": 404, "body": {"error": "DTJ's app is not installed on x, or the store is not in DTJ's Shopify organization (shop_not_permitted)"}}] * 3
        one = self.pick("status", "elevate")[0]
        calls = [i["json"] for i in run_node("licence_calls.js", one)["out"]]
        txt = run_node("licence_report.js", org, {"Pick the Shop": one, "Licence Calls": calls})["out"][0]["json"]["text"]
        self.assertIn("outside DTJ's Shopify organization", txt)

if __name__ == "__main__":
    unittest.main()

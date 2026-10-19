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


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Intake(unittest.TestCase):
    """/intake <store> (19 Oct 2026): the GitHub "Brand intake" run, answered in the chat with the Drive folder."""

    def ask(self, text, user=111):
        msg = run_node("bot_read.js", update(text, user=user))["out"][0]["json"]
        res = run_node("bot_route.js", list(SHOPS), {"Read the Message": msg, "Load Bot Users": [RIYA, DEV, HARSH, OLD]})
        self.assertTrue(res["ok"], res)
        return msg, [i["json"] for i in res["out"]]

    def test_anyone_on_the_bot_starts_an_intake_with_the_store_and_their_chat(self):
        msg, out = self.ask("/intake freesoul.com")
        self.assertEqual((msg["kind"], msg["arg"]), ("intake", "freesoul.com"))
        self.assertEqual(out[0]["action"], "intake")
        self.assertEqual(out[0]["body"], {"ref": "chore/initial-import",
                                          "inputs": {"store": "freesoul.com", "requested_by": "Riya", "telegram_chat_id": "111"}})

    def test_no_address_or_a_bad_one_gets_an_example_and_nothing_starts(self):
        for text in ("/intake", "/intake hello there", "/intake freesoul.com; rm -rf /"):
            _, out = self.ask(text)
            self.assertEqual(out[0]["action"], "reply", text)
            self.assertIn("/intake freesoul.com", out[0]["text"], text)

    def test_someone_not_on_the_bot_cannot_start_one(self):
        _, out = self.ask("/intake freesoul.com", user=999)
        self.assertEqual(out[0]["action"], "reply")
        self.assertIn("only for the DTJ team", out[0]["text"])

    def test_the_answer_says_started_or_why_not(self):
        who = {"chat_id": "111", "store": "freesoul.com"}
        ok = run_node("intake_started.js", {"statusCode": 204}, {"Who Is It": who})["out"][0]["json"]
        self.assertIn("Started the brand intake for freesoul.com", ok["text"])
        no = run_node("intake_started.js", {"statusCode": 404}, {"Who Is It": who})["out"][0]["json"]
        self.assertIn("cannot find the \"Brand intake\" workflow", no["text"])
        self.assertEqual(no["chat_id"], "111")


class IntakeDeploy(unittest.TestCase):
    def test_the_intake_branch_takes_the_third_output_and_the_reply_moves_to_the_fallback(self):
        import deploy_telegram_bot as d  # noqa: PLC0415
        ops = d.intake_ops("gh-key")
        rules = next(o for o in ops if o.get("path") == "/rules/values")["value"]
        self.assertEqual([r["outputKey"] for r in rules], ["design", "switch", "intake"])
        links = [(o.get("sourceIndex"), o["target"]) for o in ops if o["type"] == "addConnection" and o["source"] == "What to Do"]
        self.assertEqual(sorted(links), [(2, "Start Brand Intake"), (3, "Send")])
        start = next(o["node"] for o in ops if o["type"] == "addNode" and o["node"]["name"] == "Start Brand Intake")
        self.assertTrue(start["parameters"]["url"].endswith("/actions/workflows/brand-intake.yml/dispatches"))
        self.assertEqual(start["parameters"]["genericAuthType"], "httpBearerAuth")
        self.assertIn({"type": "setNodeCredential", "nodeName": "Start Brand Intake", "credentialKey": "httpBearerAuth",
                       "credentialId": "gh-key", "credentialName": "DTJ GitHub Actions"}, ops)


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


def run(i, status, store="freesoul.com", minutes=2):
    """One run in GitHub's list of the Brand intake workflow's runs."""
    return {"id": i, "status": status, "display_title": f"Brand intake: {store}", "run_started_at": "2026-10-19T10:18:47Z"}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Stop(unittest.TestCase):
    """/stop and the Stop button (19 Oct 2026, Harsh: "add a stop feature"; brand intakes only)."""

    def route(self, upd, users=(RIYA, DEV, HARSH, OLD)):
        msg = run_node("bot_read.js", upd)["out"][0]["json"]
        res = run_node("bot_route.js", list(SHOPS), {"Read the Message": msg, "Load Bot Users": list(users)})
        self.assertTrue(res["ok"], res)
        return msg, [i["json"] for i in res["out"]]

    def plan(self, ask, status, runs=None):
        body = {"total_count": len(runs or []), "workflow_runs": runs or []} if runs is not None else {"message": "Bad credentials"}
        res = run_node("stop_plan.js", {"statusCode": status, "body": body}, {"Who Is It": ask})
        self.assertTrue(res["ok"], res)
        return [i["json"] for i in res["out"]]

    def test_stop_and_a_stop_tap_are_read_and_anyone_on_the_bot_may_use_them(self):
        msg, out = self.route(update("/stop"))  # Riya, a requester
        self.assertEqual(msg["kind"], "stop")
        self.assertEqual(out, [{"action": "stop", "mode": "list", "chat_id": "111", "run_id": "", "by": "Riya"}])
        msg, out = self.route(button("stop:intake:39236551490", user=111))
        self.assertEqual((msg["kind"], msg["data"]), ("button", "stop:intake:39236551490"))
        self.assertEqual(out[0], {"action": "stop", "mode": "cancel", "chat_id": "111", "run_id": "39236551490", "by": "Riya"})

    def test_a_bad_stop_button_or_someone_not_on_the_bot_stops_nothing(self):
        for data in ("stop:intake:abc", "stop:page:12", "stop:intake:1;rm"):
            _, out = self.route(button(data, user=111))
            self.assertEqual(out[0]["action"], "reply", data)
        _, out = self.route(button("stop:intake:42", user=999))
        self.assertEqual(out[0]["action"], "reply")
        self.assertIn("only for the DTJ team", out[0]["text"])
        _, out = self.route(update("/stop", user=999))
        self.assertIn("only for the DTJ team", out[0]["text"])

    def test_the_list_shows_only_running_intakes_each_with_its_own_button(self):
        ask = {"chat_id": "111", "mode": "list", "run_id": "", "by": "Riya"}
        out = self.plan(ask, 200, [run(1, "in_progress"), run(2, "completed", "old.com"), run(3, "queued", "<b>x</b>.com")])
        self.assertEqual([o["action"] for o in out], ["choose", "choose"])
        self.assertEqual([o["stop_data"] for o in out], ["stop:intake:1", "stop:intake:3"])
        self.assertIn("Running: brand intake for freesoul.com, started", out[0]["text"])
        self.assertIn("&lt;b&gt;x&lt;/b&gt;.com", out[1]["text"])  # a store name is never read as HTML
        self.assertEqual(self.plan(ask, 200, [run(2, "completed")])[0]["text"], "No brand intake is running right now.")

    def test_only_a_brand_intake_that_is_still_going_is_cancelled(self):
        ask = {"chat_id": "111", "mode": "cancel", "run_id": "7", "by": "Riya"}
        out = self.plan(ask, 200, [run(7, "in_progress")])
        self.assertEqual(out, [{"action": "cancel", "chat_id": "111", "run_id": "7", "store": "freesoul.com", "by": "Riya"}])
        self.assertIn("already finished", self.plan(ask, 200, [run(7, "completed")])[0]["text"])
        gone = self.plan(ask, 200, [run(8, "in_progress")])[0]  # not a run of the Brand intake workflow (or too old): never cancelled
        self.assertEqual(gone["action"], "reply")
        self.assertIn("Nothing was stopped", gone["text"])
        self.assertIn("GitHub refused the bot's key", self.plan(ask, 401)[0]["text"])
        self.assertIn("could not reach GitHub (500)", self.plan(ask, 500)[0]["text"])

    def test_the_answer_after_the_cancel(self):
        plan = {"chat_id": "111", "store": "freesoul.com", "by": "Riya", "run_id": "7"}
        ok = run_node("stop_report.js", {"statusCode": 202}, {"Stop Plan": plan})["out"][0]["json"]
        self.assertEqual(ok["chat_id"], "111")
        self.assertIn("Stopping the brand intake for freesoul.com (asked by Riya)", ok["text"])
        self.assertIn("already finished", run_node("stop_report.js", {"statusCode": 409}, {"Stop Plan": plan})["out"][0]["json"]["text"])
        self.assertIn("Please tell Harsh", run_node("stop_report.js", {"statusCode": 403}, {"Stop Plan": plan})["out"][0]["json"]["text"])


class StopDeploy(unittest.TestCase):
    def test_the_stop_branch_takes_the_fourth_output_and_carries_the_keys(self):
        import deploy_telegram_bot as d  # noqa: PLC0415
        ops = d.stop_ops("gh-key", "tg-key")
        rules = next(o for o in ops if o.get("path") == "/rules/values")["value"]
        self.assertEqual([r["outputKey"] for r in rules], ["design", "switch", "intake", "stop"])
        links = [(o.get("sourceIndex"), o["target"]) for o in ops if o["type"] == "addConnection" and o["source"] == "What to Do"]
        self.assertEqual(sorted(links), [(3, "List Intakes"), (4, "Send")])
        self.assertIn({"type": "removeConnection", "source": "What to Do", "sourceIndex": 3, "target": "Send"}, ops)
        nodes = {o["node"]["name"]: o["node"] for o in ops if o["type"] == "addNode"}
        self.assertTrue(nodes["List Intakes"]["parameters"]["url"].endswith("/actions/workflows/brand-intake.yml/runs?per_page=30"))
        self.assertTrue(nodes["Cancel the Intake"]["parameters"]["url"].endswith("/actions/runs/{{ $json.run_id }}/cancel"))
        self.assertEqual(nodes["Cancel the Intake"]["parameters"]["method"], "POST")
        creds = {(o["nodeName"], o["credentialKey"], o["credentialId"]) for o in ops if o["type"] == "setNodeCredential"}
        self.assertEqual(creds, {("List Intakes", "httpBearerAuth", "gh-key"), ("Cancel the Intake", "httpBearerAuth", "gh-key"),
                                 ("Ask to Stop", "telegramApi", "tg-key")})


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class IntakeChoice(unittest.TestCase):
    """"Collect the brand's data first?" after a page starts (19 Oct 2026, Harsh: "it should ask me if it should run the scraper")."""

    def test_the_question_follows_a_started_page_with_its_brief_on_both_buttons(self):
        ask = {"chat_id": "111", "requester_name": "Riya", "requester_id": "111", "designers": ["333"]}
        ok = {"ok": True, "row_id": 12, "handle": "radiance-serum", "store_name": "Hope N Skin"}
        out = [i["json"] for i in run_node("intake_question.js", ok, {"Who Is It": ask})["out"]]
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["chat_id"], out[0]["yes_data"], out[0]["no_data"]), ("111", "brief:intake:12", "brief:skip:12"))
        self.assertIn("collect the brand's data first?", out[0]["text"])
        self.assertEqual(run_node("intake_question.js", {"ok": False, "message": "no"}, {"Who Is It": ask})["out"], [])

    def test_a_tap_is_read_and_becomes_a_choice_for_the_brief(self):
        def route(data, user=111):
            msg = run_node("bot_read.js", button(data, user=user))["out"][0]["json"]
            res = run_node("bot_route.js", list(SHOPS), {"Read the Message": msg, "Load Bot Users": [RIYA, DEV, HARSH, OLD]})
            return [i["json"] for i in res["out"]]
        self.assertEqual(route("brief:intake:12")[0], {"action": "brief", "chat_id": "111", "row_id": 12, "brand_intake": "yes", "by": "Riya"})
        self.assertEqual(route("brief:skip:12")[0]["brand_intake"], "no")
        for bad in ("brief:intake:x", "brief:maybe:12", "brief:intake:12;1"):
            self.assertEqual(route(bad)[0]["action"], "reply", bad)
        self.assertIn("only for the DTJ team", route("brief:intake:12", user=999)[0]["text"])

    def test_the_answer_after_saving_says_what_the_designer_will_do(self):
        def noted(choice, rows):
            who = {"chat_id": "111", "row_id": 12, "brand_intake": choice}
            return run_node("choice_noted.js", rows or [{}], {"Who Is It": who})["out"][0]["json"]["text"]
        self.assertIn("collect the brand's data first for Hope N Skin", noted("yes", [{"id": 12, "brand_name": "Hope N Skin", "page_status": ""}]))
        self.assertIn("with the data we already have", noted("no", [{"id": 12, "brand_name": "", "page_status": ""}]))
        self.assertIn('already marked "written to draft"', noted("yes", [{"id": 12, "page_status": "written to draft"}]))
        self.assertIn("not on the list any more", noted("yes", []))


class ChoiceDeploy(unittest.TestCase):
    def test_the_choice_takes_the_fifth_output_saves_on_the_brief_and_asks_after_a_new_page(self):
        import deploy_telegram_bot as d  # noqa: PLC0415
        ops = d.choice_ops("tg-key")
        rules = next(o for o in ops if o.get("path") == "/rules/values")["value"]
        self.assertEqual([r["outputKey"] for r in rules], ["design", "switch", "intake", "stop", "brief"])
        links = sorted((o["source"], o.get("sourceIndex"), o["target"]) for o in ops if o["type"] == "addConnection")
        self.assertIn(("What to Do", 4, "Note the Choice"), links)
        self.assertIn(("What to Do", 5, "Send"), links)
        self.assertIn(("Ask New Page", None, "Intake Question"), links)
        self.assertIn({"type": "removeConnection", "source": "What to Do", "sourceIndex": 4, "target": "Send"}, ops)
        note = next(o["node"] for o in ops if o["type"] == "addNode" and o["node"]["name"] == "Note the Choice")
        self.assertEqual(note["parameters"]["operation"], "update")
        self.assertEqual(note["parameters"]["dataTableId"]["value"], d.INTAKE)
        self.assertEqual(note["parameters"]["columns"]["value"], {"brand_intake": "={{ $json.brand_intake }}"})
        self.assertIn({"type": "setNodeCredential", "nodeName": "Ask About Intake", "credentialKey": "telegramApi", "credentialId": "tg-key",
                       "credentialName": "DTJ Page Bot"}, ops)


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Commands(unittest.TestCase):
    """/commands (19 Oct 2026, Harsh: "create a command so it can show all the commands in the bot available")."""

    def ask(self, text, user):
        msg = run_node("bot_read.js", update(text, user=user))["out"][0]["json"]
        res = run_node("bot_route.js", list(SHOPS), {"Read the Message": msg, "Load Bot Users": [RIYA, DEV, HARSH, OLD]})
        self.assertTrue(res["ok"], res)
        return msg, [i["json"] for i in res["out"]]

    def test_everyone_on_the_bot_gets_the_list_and_only_admins_see_the_admin_part(self):
        for text in ("/commands", "/menu", "/Commands@DtjPageDesignerBot"):
            msg, out = self.ask(text, 111)
            self.assertEqual(msg["kind"], "commands", text)
        riya = out[0]["text"]
        for must in ("a product link:", "/intake shop.com:", "/stop:", "/help:", "/commands:"):
            self.assertIn(must, riya)
        self.assertNotIn("/shops", riya)  # Riya is a requester
        admin = self.ask("/commands", 333)[1][0]["text"]
        for must in ("/shops:", "/status shop:", "/off shop and /on shop:"):
            self.assertIn(must, admin)
        self.assertIn("only for the DTJ team", self.ask("/commands", 999)[1][0]["text"])
        self.assertIn("/commands lists everything I can do.", self.ask("/help", 111)[1][0]["text"])

    def test_every_command_the_bot_reads_is_on_the_list(self):
        import re  # noqa: PLC0415
        from node_harness import HERE  # noqa: PLC0415
        code = (HERE / "bot_read.js").read_text(encoding="utf-8")
        known = set()
        for group in re.findall(r"\^\\/\(?([a-z|]+)", code):  # the commands: patterns that start a message with "/"
            known.update(c for c in group.split("|") if c)
        self.assertGreaterEqual(len(known), 9, sorted(known))
        known -= {"start", "menu"}  # /start = /help, /menu = /commands
        admin = self.ask("/commands", 333)[1][0]["text"]
        missing = [c for c in sorted(known) if "/" + c not in admin]
        self.assertEqual(missing, [], "a command the bot reads is missing from /commands")


def reply_to(text, asked, user=111, asked_by_bot=True):
    return {"update_id": 3, "message": {"message_id": 6, "text": text, "chat": {"id": user, "type": "private"},
                                        "from": {"id": user, "first_name": "Riya", "is_bot": False},
                                        "reply_to_message": {"message_id": 5, "text": asked, "from": {"id": 1, "is_bot": asked_by_bot}}}}


ASKED = ("Noted: the designer will collect the brand's data first, then design the page from it.\n\n"
         "Which website is the brand's own for brief 12? Reply to this message with its address, for example senso.in.")


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Website(unittest.TestCase):
    """The brand's own website after "Yes, collect it first" (19 Oct 2026, Harsh: "it didnt asked for the brand website link?")."""

    def route(self, upd, users=(RIYA, DEV, HARSH, OLD)):
        msg = run_node("bot_read.js", upd)["out"][0]["json"]
        res = run_node("bot_route.js", list(SHOPS), {"Read the Message": msg, "Load Bot Users": list(users)})
        self.assertTrue(res["ok"], res)
        return msg, [i["json"] for i in res["out"]]

    def test_a_reply_to_the_question_is_the_website_for_that_brief(self):
        msg, out = self.route(reply_to("https://www.Senso.in/pages/about", ASKED))
        self.assertEqual((msg["kind"], msg["row_id"], msg["arg"]), ("site", 12, "https://www.Senso.in/pages/about"))
        self.assertEqual(out[0], {"action": "site", "chat_id": "111", "row_id": 12, "website": "https://senso.in", "by": "Riya"})
        self.assertIn("read the shop itself", self.route(reply_to("same", ASKED))[1][0]["text"])
        self.assertIn("does not look like a website address", self.route(reply_to("the tea brand", ASKED))[1][0]["text"])
        self.assertIn("only for the DTJ team", self.route(reply_to("senso.in", ASKED, user=999))[1][0]["text"])

    def test_other_replies_and_commands_are_not_read_as_a_website(self):
        self.assertEqual(self.route(reply_to("senso.in", "Got it: designing x (brief 12)."))[0]["kind"], "nolink")
        self.assertNotEqual(self.route(reply_to("senso.in", ASKED, asked_by_bot=False))[0]["kind"], "site")
        self.assertEqual(self.route(reply_to("/help", ASKED))[0]["kind"], "help")

    def test_the_question_comes_only_after_a_yes(self):
        row = {"id": 12, "brand_name": "", "page_status": "", "brand_website": "",
               "product_url": "https://elevate-with-harsh.myshopify.com/products/senso-tea", "store_domain": "elevate-with-harsh.myshopify.com"}
        yes = run_node("choice_noted.js", [row], {"Who Is It": {"chat_id": "111", "row_id": 12, "brand_intake": "yes"}})["out"][0]["json"]
        self.assertTrue(yes["site_question"])
        self.assertIn("Which website is the brand's own for brief 12? Reply to this message", yes["text"])
        self.assertIn("If it is elevate-with-harsh.myshopify.com, reply: same", yes["text"])
        no = run_node("choice_noted.js", [row], {"Who Is It": {"chat_id": "111", "row_id": 12, "brand_intake": "no"}})["out"][0]["json"]
        self.assertNotIn("site_question", no)

    def test_the_saved_website_is_confirmed(self):
        who = {"chat_id": "111", "row_id": 12, "website": "https://senso.in"}
        ok = run_node("website_noted.js", [{"id": 12, "page_status": ""}], {"Who Is It": who})["out"][0]["json"]["text"]
        self.assertEqual(ok, "Got it: for brief 12 the designer will collect the brand's data from senso.in.")
        self.assertIn("not on the list any more", run_node("website_noted.js", [{}], {"Who Is It": who})["out"][0]["json"]["text"])


class SiteDeploy(unittest.TestCase):
    def test_the_website_takes_the_sixth_output_and_the_question_follows_a_yes(self):
        import deploy_telegram_bot as d  # noqa: PLC0415
        ops = d.site_ops("tg-key")
        rules = next(o for o in ops if o.get("path") == "/rules/values")["value"]
        self.assertEqual([r["outputKey"] for r in rules], ["design", "switch", "intake", "stop", "brief", "site"])
        links = {(o["source"], o.get("sourceIndex"), o["target"]) for o in ops if o["type"] == "addConnection"}
        for link in (("What to Do", 5, "Note the Website"), ("What to Do", 6, "Send"), ("Choice Noted", None, "Need the Website?"),
                     ("Need the Website?", 0, "Ask for the Website"), ("Need the Website?", 1, "Send")):
            self.assertIn(link, links)
        self.assertIn({"type": "removeConnection", "source": "Choice Noted", "target": "Send"}, ops)
        nodes = {o["node"]["name"]: o["node"] for o in ops if o["type"] == "addNode"}
        self.assertEqual(nodes["Ask for the Website"]["parameters"]["replyMarkup"], "forceReply")
        self.assertEqual(nodes["Note the Website"]["parameters"]["columns"]["value"], {"brand_website": "={{ $json.website }}"})

if __name__ == "__main__":
    unittest.main()

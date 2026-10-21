"""The store job (store_job.py) and its Telegram questions (bot_ask.py) against a stand-in Telegram and a stand-in answers table: what
is asked, in which order, what a tap means, and that a job picks up where it stopped. Nothing reaches Telegram, n8n or Shopify.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import bot_ask
import store_job

SCAN = {"link": "https://royaldosa.com", "base": "https://royaldosa.com", "myshopify_domain": "royal-dosa.myshopify.com",
        "name": "Royal Dosa", "currency": "INR", "live_theme": {"name": "Horizon", "id": "101", "schema_name": "Horizon"},
        "product_count": 4, "more_products": False, "collection_count": 2,
        "best_sellers_from": "the store's best-selling order (/collections/all?sort_by=best-selling)",
        "best_sellers": [{"handle": h, "title": t, "url": f"https://royaldosa.com/products/{h}"} for h, t in
                         (("podi", "Gunpowder Podi"), ("idli-mix", "Idli Mix"), ("masala-dosa-mix", "Masala Dosa Mix"),
                          ("sambar", "Sambar Powder"))]}
CHAT = "333"


class Telegram:
    def __init__(self):
        self.sent = []

    def __call__(self, method, data):
        self.sent.append((method, data))
        return {"message_id": len(self.sent)}

    def questions(self):
        return [d for m, d in self.sent if "reply_markup" in d]

    def last(self):
        return self.sent[-1][1]


class Answers:
    """dtj_bot_answers: a tap = the label and its index, a typed reply = the text (what the bot's n8n workflow saves)."""

    def __init__(self):
        self.rows = []

    def __call__(self, job):
        return [r for r in self.rows if r["job"] == job]

    def tap(self, tg, label, by="Harsh", chat=CHAT):
        for m in reversed(tg.questions()):
            for i, row in enumerate(m["reply_markup"].get("inline_keyboard", [])):
                if row[0]["text"] == label:
                    _, job, key, n = row[0]["callback_data"].split(":")
                    self.rows.append({"id": len(self.rows) + 1, "job": job, "key": key, "value": label, "choice": n, "by": by,
                                      "chat_id": chat, "at": f"2026-10-21T10:{len(self.rows):02d}:00Z"})
                    return
        raise AssertionError(f"no button {label!r}")

    def type(self, tg, text, by="Harsh"):
        asked = tg.questions()[-1]["text"]
        key = asked.rsplit("answer ", 1)[1].rstrip(")")
        job = asked.rsplit("(job ", 1)[1].split(",")[0]
        self.rows.append({"id": len(self.rows) + 1, "job": job, "key": key, "value": text, "choice": "", "by": by, "chat_id": CHAT,
                          "at": f"2026-10-21T10:{len(self.rows):02d}:00Z"})


class Clock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, s):
        self.now += s

    def __call__(self):
        return self.now


class Log:
    def __init__(self):
        self.rows = []

    def record(self, **row):
        self.rows.append(row)


class FakeAccess:
    def __init__(self, added=()):
        self.made, self.added, self.commands = [], list(added), [["shopify", "theme", "duplicate"]]

    def duplicate_live(self, name):
        self.made.append(name)
        return {"id": "555", "name": name, "role": "unpublished", "from_live": "101", "from_live_name": "Horizon"}

    def themes(self, role=None, **_):
        return [t for t in self.added if not role or t["role"] == role]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tg, self.answers, self.clock, self.log, self.printed = Telegram(), Answers(), Clock(), Log(), []

    def job(self, access=None, scan=SCAN):
        j = store_job.Job(store_job.job_id(scan["myshopify_domain"]), send=self.tg, rows=self.answers, access=access, log=self.log,
                          state_dir=self.tmp, out=self.printed.append, sleep=self.clock.sleep, clock=self.clock,
                          today=lambda: "21 Oct 2026")
        j.begin(scan, CHAT, "Harsh")
        return j


class Questions(Base):
    def test_a_client_store_is_planned_in_five_taps_and_a_typed_offer(self):
        j = self.job()
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)  # nobody tapped yet
        self.assertIn("Whose store is it?", self.tg.questions()[0]["text"])
        self.assertIn("4 products, 2 collections, live theme Horizon (Horizon)", self.tg.questions()[0]["text"])
        self.answers.tap(self.tg, "A client's store")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.answers.tap(self.tg, 'Use "Royal Dosa"')
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Everything")
        j.plan(minutes=1)
        products = self.tg.questions()[-1]
        self.assertIn("1. Gunpowder Podi", products["text"])
        self.assertEqual([r[0]["text"] for r in products["reply_markup"]["inline_keyboard"]],
                         ["All 4 products", "Top 3 best sellers", "I'll pick them"])
        self.answers.tap(self.tg, "Top 3 best sellers")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "I'll type it")
        j.plan(minutes=1)
        self.assertTrue(self.tg.questions()[-1]["reply_markup"]["force_reply"])
        self.answers.type(self.tg, "Flat 10% off on prepaid orders")
        self.assertEqual(j.plan(minutes=1), 0)
        p = j.s["plan"]
        self.assertEqual((p["whose"], p["label"], p["theme"], p["parts"], p["offer"]),
                         ("client", "Royal Dosa", "duplicate", ["chrome", "home", "collection", "products"], "Flat 10% off on prepaid orders"))
        self.assertEqual([x["handle"] for x in p["products"]], ["podi", "idli-mix", "masala-dosa-mix"])
        self.assertIn("Plan for <b>Royal Dosa</b>", self.tg.last()["text"])
        self.assertIn("Approve button", self.tg.last()["text"])
        asked = len(self.tg.questions())
        self.assertEqual(j.plan(minutes=1), 0)  # a rerun asks nothing again
        self.assertEqual(len(self.tg.questions()), asked)

    def test_every_button_fits_telegram_and_names_its_job(self):
        j = self.job()
        j.plan(minutes=1)
        data = self.tg.questions()[0]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
        self.assertEqual(data, "a:royal-dosa:whose:0")
        self.assertLessEqual(len(store_job.job_id("a" * 60 + ".myshopify.com")), 24)
        self.assertLessEqual(len(f"a:{store_job.job_id('a' * 60 + '.myshopify.com')}:{'x' * 20}:9".encode()), 64)

    def test_answers_from_another_chat_do_not_count_and_the_last_answer_wins(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "A client's store", chat="999")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.answers.tap(self.tg, "Wrong store: stop")
        self.answers.tap(self.tg, "A client's store")
        j.plan(minutes=1)
        self.assertEqual(j.s["plan"]["whose"], "client")

    def test_wrong_store_stops(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Wrong store: stop")
        self.assertEqual(j.plan(minutes=1), 1)
        self.assertIn("wrong store", j.s["stopped"])

    def test_a_theme_the_builder_does_not_know_asks_for_horizon_first(self):
        j = self.job(scan={**SCAN, "live_theme": {"name": "Impact", "schema_name": "Impact"}})
        j.plan(minutes=1)
        self.answers.tap(self.tg, "DTJ's own store")
        j.plan(minutes=1)
        self.assertIn("Add theme > Horizon (do NOT publish it)", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Stop")
        self.assertEqual(j.plan(minutes=1), 1)

    def test_a_dawn_store_gets_product_pages_only(self):
        j = self.job(scan={**SCAN, "live_theme": {"name": "Dawn", "schema_name": "Dawn"}})
        j.plan(minutes=1)
        self.answers.tap(self.tg, "DTJ's own store")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Product pages only, on Dawn")
        j.plan(minutes=1)
        self.assertIn("Which product pages?", self.tg.questions()[-1]["text"])  # no "what to design" question
        self.assertEqual(j.s["plan"]["parts"], ["products"])

    def test_picked_products_by_link_or_name_and_unknown_ones_are_said(self):
        j = self.job()
        j.plan(minutes=1)
        for label in ("DTJ's own store", "Choose one by one", "No", "No", "No", "Yes", "I'll pick them"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.type(self.tg, "https://royaldosa.com/products/sambar?variant=1\nidli mix\nchocolate cake")
        j.plan(minutes=1)
        self.assertIn("Not found in the store, left out: chocolate cake", [d["text"] for _, d in self.tg.sent][-2])
        self.assertEqual([x["handle"] for x in j.s["plan"]["products"]], ["sambar", "idli-mix"])
        self.assertEqual(j.s["plan"]["parts"], ["products"])


class Approvals(Base):
    def planned(self, access=None):
        j = self.job(access)
        j.plan(minutes=1)
        for label in ("A client's store", 'Use "Royal Dosa"', "Everything except product pages", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertTrue(j.s.get("planned"))
        return j

    def test_the_draft_copy_waits_for_an_approve_tap_and_logs_who_tapped(self):
        access = FakeAccess()
        j = self.planned(access)
        self.assertEqual(j.draft(minutes=1), store_job.WAITING)
        self.assertEqual(access.made, [])
        self.assertIn("duplicate the live theme <b>Horizon</b>", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Approve", by="Riya")
        self.assertEqual(j.draft(minutes=1), 0)
        self.assertEqual(access.made, ["DTJ Draft 21 Oct 2026"])
        self.assertEqual((j.s["draft"]["id"], j.s["draft"]["approved_by"]), ("555", "Riya (Telegram Approve)"))
        self.assertEqual(self.log.rows[-1]["approver"], "Riya (Telegram Approve)")
        self.assertEqual(self.log.rows[-1]["tier"], 2)
        self.assertEqual(j.draft(minutes=1), 0)  # made once
        self.assertEqual(len(access.made), 1)

    def test_skip_leaves_it_undone(self):
        access = FakeAccess()
        j = self.planned(access)
        j.draft(minutes=1)
        self.answers.tap(self.tg, "Skip")
        self.assertEqual(j.draft(minutes=1), store_job.SKIPPED)
        self.assertEqual(access.made, [])

    def test_an_added_horizon_is_used_as_the_draft_without_copying(self):
        access = FakeAccess(added=[{"id": 700, "name": "Horizon", "role": "unpublished"}])
        j = self.job(access, scan={**SCAN, "live_theme": {"name": "Impact", "schema_name": "Impact"}})
        j.plan(minutes=1)
        for label in ("DTJ's own store", "Done: Horizon is added", "Only product pages", "Top 3 best sellers", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertEqual(j.draft(minutes=1), 0)
        self.assertEqual((j.s["draft"]["id"], access.made), ("700", []))

    def test_the_apps_tap_gives_the_exact_add_shop_command(self):
        j = self.planned(FakeAccess())
        j.draft(minutes=1)
        self.answers.tap(self.tg, "Approve")
        j.draft(minutes=1)
        self.assertEqual(j.apps(minutes=1), store_job.WAITING)
        self.assertIn("7 DTJ app copies for <b>Royal Dosa</b>", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Approve", by="Harsh")
        self.assertEqual(j.apps(minutes=1), 0)
        self.assertEqual(self.printed[-1], 'python services/install-catcher/tools/add_shop.py --shop royal-dosa.myshopify.com '
                                           '--label "Royal Dosa" --chat 333 --approved-by "Harsh (Telegram Approve)" --theme 555')

    def test_one_write_one_tap_and_the_answer_for_n8n(self):
        j = self.planned()
        self.assertEqual(j.approve("ok_header", "Write the header: preview https://x", minutes=1), store_job.WAITING)
        self.answers.tap(self.tg, "Approve", by="Harsh")
        self.assertEqual(j.approve("ok_header", "Write the header: preview https://x", minutes=1), 0)
        self.assertEqual(self.printed[-1], "APPROVED_BY=Harsh (Telegram Approve)")
        self.assertEqual(j.approve("ok_footer", "Write the footer", minutes=1), store_job.WAITING)  # its own tap
        j.record("home", "https://royal-dosa.myshopify.com/?preview_theme_id=555")
        j.finish("partly done", "the owner has not installed 2 apps yet")
        body = json.loads((self.tmp / "royal-dosa" / "answer.json").read_text(encoding="utf-8"))
        self.assertEqual((body["store_status"], body["shop"], body["pages"][0]["part"]), ("partly done", "royal-dosa.myshopify.com", "home"))
        with self.assertRaises(SystemExit):
            j.finish("finished")

    def test_nothing_happens_before_the_plan(self):
        j = self.job(FakeAccess())
        with self.assertRaises(SystemExit):
            j.draft(minutes=1)


class Pieces(unittest.TestCase):
    def test_typed_products_match_by_link_or_unique_name(self):
        sellers = SCAN["best_sellers"]
        picked, unknown = store_job.match_products(["Mix", "PODI", "/products/sambar", "", "/products/none"], sellers)
        self.assertEqual([p["handle"] for p in picked], ["podi", "sambar"])  # "Mix" matches two products: not guessed
        self.assertEqual(unknown, ["Mix", "/products/none"])

    def test_theme_support(self):
        self.assertEqual([store_job.theme_support(x) for x in ("Horizon", "dawn", "Impact", None)], ["horizon", "dawn", "none", "none"])

    def test_bad_job_or_key_names_are_refused(self):
        with self.assertRaises(ValueError):
            bot_ask.Asker("Bad Job", CHAT, send=Telegram(), rows=Answers(), state={}, save=lambda: None)
        a = bot_ask.Asker("ok-job", CHAT, send=Telegram(), rows=Answers(), state={}, save=lambda: None)
        with self.assertRaises(ValueError):
            a.ask("Bad Key!", "x", [("a", "a")])


if __name__ == "__main__":
    unittest.main()

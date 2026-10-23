"""The store job (store_job.py) and its Telegram questions (bot_ask.py) against a stand-in Telegram and a stand-in answers table: what
is asked, in which order, what a tap means, and that a job picks up where it stopped. Nothing reaches Telegram, n8n or Shopify.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory
"""
import io
import json
import os
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
                                      "chat_id": chat, "at": f"2099-10-21T10:{len(self.rows):02d}:00Z"})
                    return
        raise AssertionError(f"no button {label!r}")

    def type(self, tg, text, by="Harsh"):
        asked = tg.questions()[-1]["text"]
        key = asked.rsplit("answer ", 1)[1].rstrip(")")
        job = asked.rsplit("(job ", 1)[1].split(",")[0]
        self.rows.append({"id": len(self.rows) + 1, "job": job, "key": key, "value": text, "choice": "", "by": by, "chat_id": CHAT,
                          "at": f"2099-10-21T10:{len(self.rows):02d}:00Z"})


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
        self.assertIn("What are we building in this store?", self.tg.questions()[0]["text"])
        self.assertIn("4 products, 2 collections, live theme Horizon (Horizon)", self.tg.questions()[0]["text"])
        self.answers.tap(self.tg, "Redesign an existing brand")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertIn("Where are the brand's products now?", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Already in this store")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        pictures = self.tg.questions()[-1]
        self.assertIn("Should ChatGPT make new pictures", pictures["text"])
        self.assertEqual([r[0]["text"] for r in pictures["reply_markup"]["inline_keyboard"]], ["Only banners", "No new pictures"])
        self.answers.tap(self.tg, "No new pictures")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.answers.tap(self.tg, "No study")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertIn("Whose store is <b>Royal Dosa</b>", self.tg.questions()[-1]["text"])
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
                         ("client", "Royal Dosa", "duplicate", ["chrome", "home", "collection", "products", "pages"],
                          "Flat 10% off on prepaid orders"))
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
        self.assertEqual(data, "a:royal-dosa:kind:0")
        self.assertLessEqual(len(store_job.job_id("a" * 60 + ".myshopify.com")), 24)
        self.assertLessEqual(len(f"a:{store_job.job_id('a' * 60 + '.myshopify.com')}:{'x' * 20}:9".encode()), 64)

    def test_answers_from_another_chat_do_not_count_and_the_last_answer_wins(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Redesign an existing brand", chat="999")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertNotIn("kind", j.s["answers"])
        self.answers.tap(self.tg, "Wrong store: stop")
        self.answers.tap(self.tg, "Redesign an existing brand")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Already in this store")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "No new pictures")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "No study")
        j.plan(minutes=1)
        self.assertFalse(j.s["plan"]["copy"])
        self.assertIn("Whose store is", self.tg.questions()[-1]["text"])

    def test_an_old_tap_left_in_the_table_does_not_answer_a_new_question(self):
        # the second run for elevate (21 Oct 2026): the table still held the first run's taps for the same job and keys
        self.answers.rows.append({"id": 1, "job": "royal-dosa", "key": "kind", "value": "Redesign an existing brand", "choice": "0",
                                  "by": "Harsh", "chat_id": CHAT, "at": "2020-01-01T10:00:00.000Z"})
        j = self.job()
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertNotIn("kind", j.s["answers"])
        self.assertIn("at", j.s["asked"]["kind"])

    def test_wrong_store_stops(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Wrong store: stop")
        self.assertEqual(j.plan(minutes=1), 1)
        self.assertIn("wrong store", j.s["stopped"])

    def test_a_theme_the_builder_does_not_know_asks_for_horizon_first(self):
        j = self.job(scan={**SCAN, "live_theme": {"name": "Impact", "schema_name": "Impact"}})
        j.plan(minutes=1)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "DTJ's own store"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertIn("Add theme > Horizon (do NOT publish it)", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Stop")
        self.assertEqual(j.plan(minutes=1), 1)

    def test_a_dawn_store_gets_product_pages_only(self):
        j = self.job(scan={**SCAN, "live_theme": {"name": "Dawn", "schema_name": "Dawn"}})
        j.plan(minutes=1)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "DTJ's own store"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.tap(self.tg, "Product pages only, on Dawn")
        j.plan(minutes=1)
        self.assertIn("Which product pages?", self.tg.questions()[-1]["text"])  # no "what to design" question
        self.assertEqual(j.s["plan"]["parts"], ["products"])

    def test_picked_products_by_link_or_name_and_unknown_ones_are_said(self):
        j = self.job()
        j.plan(minutes=1)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "DTJ's own store", "Choose one by one", "No", "No", "No", "Yes", "No", "I'll pick them"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.type(self.tg, "https://royaldosa.com/products/sambar?variant=1\nidli mix\nchocolate cake")
        j.plan(minutes=1)
        self.assertIn("chocolate cake: not found in the store", [d["text"] for _, d in self.tg.sent][-2])
        self.assertEqual([x["handle"] for x in j.s["plan"]["products"]], ["sambar", "idli-mix"])
        self.assertEqual(j.s["plan"]["parts"], ["products"])


class Approvals(Base):
    def planned(self, access=None):
        j = self.job(access)
        j.plan(minutes=1)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "A client's store", 'Use "Royal Dosa"', "Everything except product pages", "No offer"):
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
        self.assertEqual(self.log.rows[-1]["approved_by"], "Riya (Telegram Approve)")
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
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "DTJ's own store", "Done: Horizon is added", "Only product pages", "Top 3 best sellers",
                      "No offer"):
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


BRAND = {**SCAN, "link": "https://glowco.com", "base": "https://glowco.com", "myshopify_domain": "glowco.myshopify.com", "name": "GlowCo",
         "currency": "USD", "product_count": 2, "collection_count": 1,
         "best_sellers": [{"handle": "glow-serum", "title": "Glow Serum", "url": "https://glowco.com/products/glow-serum"},
                          {"handle": "night-cream", "title": "Night Cream", "url": "https://glowco.com/products/night-cream"}]}
PLAN = {"brand": "https://glowco.com", "status": "ACTIVE", "notes": ["prices are the brand's numbers in USD; royal-dosa.myshopify.com "
                                                                   "sells in INR (not converted)"],
        "products": [{"handle": "glow-serum", "files": [1, 2], "variants": [1]}, {"handle": "night-cream", "files": [1], "variants": [1, 2]}],
        "collections": [{"handle": "skin"}], "policies": [{"type": "REFUND_POLICY"}],
        "target": {"store": "royal-dosa.myshopify.com"}, "skipped": {}}


class BrandCopy(Base):
    """The link sent is the store to build in; the bot asks for the brand's own link and copies the brand into it (21 Oct 2026)."""

    def job(self, access=None, scan=SCAN, planner=None, scanner=None, statuses=None):
        self.planned_with, self.looked = [], 0
        self.statuses = list(statuses or [{"done": {"products": 1}, "total": {"products": 2}, "finished": False},
                                          {"done": {"products": 2, "collections": 1}, "total": {"products": 2}, "finished": True, "stopped": None}])

        def plan(link, store, currency, out, job, **_):
            self.planned_with.append((link, store, currency, job))
            return PLAN

        def status(job):
            self.looked += 1
            return self.statuses.pop(0) if self.statuses else {"finished": True}
        j = store_job.Job(store_job.job_id(scan["myshopify_domain"]), send=self.tg, rows=self.answers, access=access, log=self.log,
                          state_dir=self.tmp, out=self.printed.append, sleep=self.clock.sleep, clock=self.clock,
                          today=lambda: "21 Oct 2026", scanner=scanner or (lambda link: BRAND), planner=planner or plan, copy_status=status)
        j.begin(scan, CHAT, "Harsh")
        return j

    def planned(self, **kw):
        j = self.job(**kw)
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Redesign an existing brand")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "On its current website")
        j.plan(minutes=1)
        self.answers.type(self.tg, "https://glowco.com")
        j.plan(minutes=1)
        for label in ("No new pictures", "No study", "DTJ's own store", "Everything", "All 2 products", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        return j

    def test_the_bot_asks_for_the_brand_and_plans_from_the_brands_products(self):
        j = self.planned()
        told = [d["text"] for _, d in self.tg.sent]
        self.assertTrue(any("Brand: <b>GlowCo</b> (https://glowco.com): 2 products" in x for x in told))
        p = j.s["plan"]
        self.assertTrue(p["copy"])
        self.assertEqual((p["brand"]["store"], p["brand"]["currency"]), ("glowco.myshopify.com", "USD"))
        self.assertEqual([x["handle"] for x in p["products"]], ["glow-serum", "night-cream"])  # the BRAND's products
        self.assertIn("Copy <b>GlowCo</b> into it", self.tg.last()["text"])
        self.assertIn("the products (every one ACTIVE)", self.tg.last()["text"])

    def test_a_brand_that_cannot_be_read_is_asked_again_and_three_in_a_row_stop(self):
        def scanner(link):
            if "wordpress" in link:
                raise ValueError("no product pages to read")
            return BRAND
        j = self.job(scanner=scanner)
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Redesign an existing brand")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "On its current website")
        j.plan(minutes=1)
        self.answers.type(self.tg, "https://wordpress-brand.com")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)  # asked again: the refused link never counts twice
        told = [d["text"] for _, d in self.tg.sent]
        self.assertTrue(any("I could not read https://wordpress-brand.com as a brand" in x for x in told))
        self.assertIn("answer brand_link", self.tg.questions()[-1]["text"])
        self.answers.type(self.tg, "https://glowco.com")
        j.plan(minutes=1)
        self.assertEqual(j.s["brand"]["name"], "GlowCo")
        k = self.job(scan={**SCAN, "myshopify_domain": "other-store.myshopify.com"}, scanner=scanner)
        k.plan(minutes=1)
        self.answers.tap(self.tg, "Redesign an existing brand")
        k.plan(minutes=1)
        self.answers.tap(self.tg, "On its current website")
        k.plan(minutes=1)
        for _ in range(3):
            self.answers.type(self.tg, "https://wordpress-brand.com")
            code = k.plan(minutes=1)
        self.assertEqual(code, 1)
        self.assertIn("three brand links in a row", k.s["stopped"])

    def test_a_website_brand_without_prices_is_said_to_come_in_at_zero(self):
        site = {**BRAND, "platform": "website", "myshopify_domain": None, "collection_count": 0, "prices": 0}
        j = self.job(scanner=lambda link: site)
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Redesign an existing brand")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "On its current website")
        j.plan(minutes=1)
        self.answers.type(self.tg, "https://glowco.com")
        j.plan(minutes=1)
        told = next(d["text"] for _, d in self.tg.sent if d["text"].startswith("Brand: <b>GlowCo</b>"))
        self.assertIn("not a Shopify store and shows no price for some products", told)
        self.assertIn("go in at 0.00 (never guessed)", told)
        self.assertNotIn("collections", told)

    def test_the_copy_is_planned_read_only_then_waits_for_its_own_tap(self):
        j = self.planned()
        self.assertEqual(j.copy(minutes=1), store_job.WAITING)
        self.assertEqual(self.planned_with, [("https://glowco.com", "royal-dosa.myshopify.com", "USD", "royal-dosa")])
        self.assertEqual(self.looked, 0)  # nothing is copied before the tap
        ask = self.tg.questions()[-1]["text"]
        self.assertIn("Copy <b>GlowCo</b> into <b>Royal Dosa</b>: 2 products (3 pictures, 3 variants), 1 collections, 1 policy pages, "
                      "as ACTIVE", ask)
        self.assertIn("sells in INR (not converted)", ask)
        self.assertIn("Nothing the store has is changed or deleted", ask)
        self.answers.tap(self.tg, "Approve", by="Riya")
        self.assertEqual(j.copy(minutes=5), 0)  # the tap starts n8n's copy; this only waits until it says finished
        self.assertEqual(self.looked, 2)
        self.assertEqual(json.loads(self.printed[-1])["done"]["products"], 2)
        self.assertEqual(j.s["copy_approved_by"], "Riya (Telegram Approve)")
        self.assertEqual(self.log.rows[-1]["approved_by"], "Riya (Telegram Approve)")
        self.assertEqual(len(self.planned_with), 1)  # planned once
        self.assertEqual(j.copy(minutes=1), 0)
        self.assertEqual((len(self.planned_with), self.looked), (1, 2))  # finished: nothing asked again

    def test_a_second_copy_after_a_finished_one_needs_its_own_tap(self):
        j = self.planned()
        j.copy(minutes=1)
        self.answers.tap(self.tg, "Approve", by="Riya")
        self.assertEqual(j.copy(minutes=5), 0)
        self.statuses = [{"done": {"policies": 2}, "total": {"policies": 2}, "finished": True, "stopped": None}]
        self.assertEqual(j.copy(minutes=1, again=True), store_job.WAITING)  # planned again, waiting for a NEW tap
        self.assertEqual(len(self.planned_with), 2)
        self.assertNotIn("copy_approved_by", j.s)
        self.answers.tap(self.tg, "Approve", by="Harsh")
        self.assertEqual(j.copy(minutes=1), 0)
        self.assertEqual(j.s["copy_approved_by"], "Harsh (Telegram Approve)")

    def test_store_builder_not_installed_asks_once_then_goes_on(self):
        tries = []

        def plan(link, store, currency, out, job, **_):
            tries.append(1)
            if len(tries) < 3:
                raise store_job.NotInstalled("DTJ's app is not installed on royal-dosa.myshopify.com")
            return PLAN
        j = self.planned(planner=plan)
        self.assertEqual(j.copy(minutes=10), store_job.WAITING)  # planned on the third look, then waits for the tap
        asked = [d["text"] for _, d in self.tg.sent if "install <b>DTJ Store Builder</b>" in d["text"]]
        self.assertEqual(len(asked), 1)
        self.assertIn("Copy <b>GlowCo</b>", self.tg.questions()[-1]["text"])

    def test_a_copy_that_stops_in_n8n_says_so(self):
        j = self.planned(statuses=[{"done": {"products": 1, "failed": 3}, "total": {"products": 4}, "finished": True,
                                    "stopped": "3 product copies failed in a row"}])
        j.copy(minutes=1)
        self.answers.tap(self.tg, "Approve")
        self.assertEqual(j.copy(minutes=1), 1)
        self.assertIn("stopped", j.s["copy_result"])

    def test_skip_and_a_plan_that_fails(self):
        j = self.planned()
        j.copy(minutes=1)
        self.answers.tap(self.tg, "Skip")
        self.assertEqual(j.copy(minutes=1), store_job.SKIPPED)

        def no_scope(*_, **__):
            raise RuntimeError("ACCESS_DENIED: read_products")
        k = self.planned(scan={**SCAN, "myshopify_domain": "other.myshopify.com"}, planner=no_scope)
        self.assertEqual(k.copy(minutes=1), 1)
        self.assertIn("I could not plan the copy: ACCESS_DENIED", [d["text"] for _, d in self.tg.sent][-2])

    def test_nothing_to_copy_when_the_store_is_the_brand(self):
        j = self.job()
        j.plan(minutes=1)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "DTJ's own store", "Only product pages", "Top 3 best sellers", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertEqual(j.copy(minutes=1), 0)
        self.assertEqual(self.printed[-1], "nothing to copy: this store is the brand")
        self.assertEqual(self.planned_with, [])


DRIVE = "https://drive.google.com/drive/folders/abc"
DRIVE_BRAND = {"source": "drive", "link": DRIVE, "base": DRIVE, "name": "Senso Foods", "collections": [], "banners": [], "policies": {},
               "products": [{"handle": "masala-chai", "title": "Masala Chai", "body_html": "<p>Tea</p>", "tags": [],
                             "options": [{"name": "Title", "position": 1, "values": ["Default Title"]}],
                             "variants": [{"option1": "Default Title", "price": "249", "sku": ""}],
                             "images": [{"path": "x/1.jpg", "alt": "Masala Chai"}], "price_needed": False},
                            {"handle": "ginger-chai", "title": "Ginger Chai", "body_html": "<p>Tea</p>", "tags": ["dtj-price-needed"],
                             "options": [{"name": "Title", "position": 1, "values": ["Default Title"]}],
                             "variants": [{"option1": "Default Title", "price": "0.00", "sku": ""}], "images": [], "price_needed": True}],
               "product_count": 2, "collection_count": 0, "best_sellers_from": "the Drive folder's order",
               "best_sellers": [{"handle": "masala-chai", "title": "Masala Chai", "url": DRIVE}, {"handle": "ginger-chai", "title": "Ginger Chai", "url": DRIVE}],
               "problems": ["Ginger Chai has no pictures"]}
SAMPLES = {"products": [{"title": f"Chai Blend {n}", "description": "A warm, everyday blend of black tea and spices for the evening cup.",
                         "collection": "Tea" if n % 2 else "Tea, Gifts", "price": str(249 + 50 * n), "compare_at_price": str(349 + 50 * n),
                         "pictures": [f"a tin of loose tea number {n}", "the tin open, leaves"]}
                        for n in range(1, 7)],
           "banners": [{"prompt": "a calm kitchen counter with a tea tin and a steaming cup, morning light"}, "tea leaves on a wooden tray"],
           "style": "Blue Tea and its peers shoot one tin on warm beige or a wooden counter, soft morning light, loose leaves and a "
                    "steaming cup as the only props; ours follow that: warm, calm, one product, no text."}
NICHE = {"niche": "tea", "competitors": [{"name": f"Brand {n}", "banners": [f"b{n}.jpg"], "products": [{"pictures": [f"p{n}.jpg"]}]}
                                         for n in range(1, 6)]}


class NewStore(Base):
    """A new store (Harsh, 22 Oct 2026): the products from a Google Drive folder, or samples with ChatGPT pictures and sample prices;
    every one ACTIVE; pictures only when the person says so and after the niche research."""

    def job(self, drive=None):
        self.planned_with, self.pictures = [], []

        def plan(link, store, currency, out, job, brand=None, prices=None):
            self.planned_with.append((brand, prices))
            return PLAN

        def picture(kind, prompt, out, refs=()):
            self.pictures.append((kind, prompt, [Path(r).name for r in refs]))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"png")
            return {}
        j = store_job.Job("royal-dosa", send=self.tg, rows=self.answers, log=self.log, state_dir=self.tmp, out=self.printed.append,
                          sleep=self.clock.sleep, clock=self.clock, planner=plan, picture=picture,
                          drive=drive or (lambda link, out: json.loads(json.dumps(DRIVE_BRAND))),
                          copy_status=lambda job: {"finished": True, "done": {"products": 2, "collections": 1}},
                          today=lambda: "22 Oct 2026")
        j.begin(SCAN, CHAT, "Harsh")
        return j

    def told(self):
        return [d["text"] for _, d in self.tg.sent]

    def research(self, **kw):
        f = self.tmp / "niche.json"
        f.write_text(json.dumps(dict(NICHE, **kw)), encoding="utf-8")
        return str(f)

    def drive_job(self, pictures="No: the folder's pictures are enough"):
        j = self.job()
        j.plan(minutes=1)
        for label in ("New store from scratch", "Yes: I'll send a Google Drive folder"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.type(self.tg, DRIVE)
        j.plan(minutes=1)
        for label in (pictures, "No study", "DTJ's own store", "Everything", "All 2 products", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        return j

    def test_a_drive_folder_store_is_read_at_once_and_typed_prices_reach_the_plan(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "New store from scratch")
        j.plan(minutes=1)
        self.assertIn("Are the brand's products ready?", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Yes: I'll send a Google Drive folder")
        j.plan(minutes=1)
        self.assertIn("Anyone with the link", self.tg.questions()[-1]["text"])
        self.answers.type(self.tg, DRIVE)
        j.plan(minutes=1)
        self.assertEqual([r[0]["text"] for r in self.tg.questions()[-1]["reply_markup"]["inline_keyboard"]],
                         ["Banners and extra product pictures", "Only banners", "No: the folder's pictures are enough"])
        said = next(x for x in self.told() if x.startswith("Drive folder:"))
        self.assertIn("<b>Senso Foods</b>: 2 products", said)
        self.assertIn("1 products have no price", said)
        self.assertIn("- Ginger Chai has no pictures", said)
        for label in ("No: the folder's pictures are enough", "No study", "DTJ's own store", "Everything", "All 2 products", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        p = j.s["plan"]
        self.assertEqual((p["kind"], p["source"], p["copy"], p["pictures"]), ("new", "drive", True, "none"))
        self.assertEqual([x["handle"] for x in p["products"]], ["masala-chai", "ginger-chai"])
        self.assertIn("from the Drive folder", self.tg.last()["text"])
        self.assertEqual(j.copy(minutes=1), store_job.WAITING)
        ask = self.tg.questions()[-1]
        self.assertIn("1 products have no price", ask["text"])
        self.assertEqual([r[0]["text"] for r in ask["reply_markup"]["inline_keyboard"]], ["I'll type the prices", "Leave them at 0.00"])
        self.answers.tap(self.tg, "I'll type the prices")
        self.assertEqual(j.copy(minutes=1), store_job.WAITING)
        self.answers.type(self.tg, "Ginger chai = 199\nChocolate cake = 99\nhello")
        self.assertEqual(j.copy(minutes=1), store_job.WAITING)  # planned, waiting for the Approve tap
        brand, prices = self.planned_with[0]
        self.assertEqual((brand["name"], prices), ("Senso Foods", {"ginger-chai": {"price": "199", "compare_at_price": None, "sample": False}}))
        self.assertTrue(any("chocolate cake: not found" in x.lower() and 'hello: not "name = price"' in x for x in self.told()))
        self.assertIn("Add the Drive folder's products of <b>Senso Foods</b>", self.tg.questions()[-1]["text"])

    def test_drive_pictures_need_the_research_use_our_photos_and_sample_prices_are_offered(self):
        j = self.drive_job("Banners and extra product pictures")
        photo = self.tmp / "masala-1.jpg"
        photo.write_bytes(b"jpg")
        j.s["brand"]["products"][0]["images"] = [{"path": str(photo), "alt": "Masala Chai"}]
        j.s["brand"]["products"][1]["body_html"] = "<p> </p>"  # no description in the folder: a sample one is allowed
        f = self.tmp / "assets.json"
        body = {"pictures": [{"for": "masala-chai", "prompt": "the tin in the reference on a kitchen counter, morning light",
                              "refs": [str(photo)]}],
                "banners": [{"prompt": "a warm counter with the tin in the reference", "refs": [str(photo)]}],
                "sample_prices": {"ginger-chai": {"price": "299", "compare_at_price": "399"}, "masala-chai": {"price": "1"}},
                "descriptions": {"ginger-chai": "Ginger and black tea, cut fine, for a strong cup with milk."}}
        f.write_text(json.dumps(body), encoding="utf-8")
        with self.assertRaises(SystemExit) as no_research:
            j.assets(f)
        self.assertIn("no pictures before the niche research", str(no_research.exception))
        f.write_text(json.dumps(dict(body, research=self.research(competitors=NICHE["competitors"][:2]), style=SAMPLES["style"])), encoding="utf-8")
        with self.assertRaises(SystemExit):
            j.assets(f)  # 2 competitors are not enough
        f.write_text(json.dumps(dict(body, research=self.research(), style=SAMPLES["style"])), encoding="utf-8")
        self.assertEqual(j.assets(f), 0)
        self.assertEqual(self.pictures, [("lifestyle", body["pictures"][0]["prompt"], ["masala-1.jpg"]),
                                         ("banner", body["banners"][0]["prompt"], ["masala-1.jpg"])])
        masala, ginger = j.s["brand"]["products"]
        self.assertEqual([Path(x["path"]).name for x in masala["images"]], ["masala-1.jpg", "masala-chai-ai-1.png"])
        self.assertIn("dtj-sample-text", ginger["tags"])
        self.assertEqual(j.s["plan"]["sample_prices"], {"ginger-chai": {"price": "299", "compare_at_price": "399"}})  # masala has a price
        self.assertTrue(any("Sample prices refused for: masala-chai" in x for x in self.told()))
        self.assertEqual(j.copy(minutes=1), store_job.WAITING)
        self.assertEqual([r[0]["text"] for r in self.tg.questions()[-1]["reply_markup"]["inline_keyboard"]],
                         ["Use the sample prices", "I'll type the prices", "Leave them at 0.00"])
        self.answers.tap(self.tg, "Use the sample prices")
        j.copy(minutes=1)
        self.assertEqual(self.planned_with[0][1], {"ginger-chai": {"price": "299", "compare_at_price": "399", "sample": True}})
        priced = store_job.priced(j.s["brand"], self.planned_with[0][1])["products"][1]
        self.assertEqual((priced["variants"][0]["price"], priced["variants"][0]["compare_at_price"], priced["price_needed"]),
                         ("299", "399", False))
        self.assertEqual(priced["tags"], ["dtj-sample-text", "dtj-sample-price"])

    def test_no_pictures_answer_makes_none(self):
        j = self.drive_job()
        f = self.tmp / "assets.json"
        f.write_text(json.dumps({"pictures": [{"for": "masala-chai", "prompt": "x"}], "banners": ["a counter"]}), encoding="utf-8")
        self.assertEqual(j.assets(f), 0)  # the person said no: nothing made, no research needed
        self.assertEqual(self.pictures, [])

    def test_a_folder_that_cannot_be_read_is_asked_again(self):
        tries = []

        def drive(link, out):
            tries.append(link)
            if len(tries) == 1:
                raise ValueError("the folder is not shared with 'Anyone with the link'")
            return json.loads(json.dumps(DRIVE_BRAND))
        j = self.job(drive=drive)
        j.plan(minutes=1)
        for label in ("New store from scratch", "Yes: I'll send a Google Drive folder"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.type(self.tg, DRIVE)
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertTrue(any("not shared with 'Anyone with the link'" in x for x in self.told()))
        self.answers.type(self.tg, DRIVE)
        j.plan(minutes=1)
        self.assertEqual(j.s["brand"]["name"], "Senso Foods")

    def test_a_samples_store_makes_its_products_and_banners_once_then_adds_them_active(self):
        j = self.job()
        j.plan(minutes=1)
        for label in ("New store from scratch", "No: make sample products"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.type(self.tg, "Chai Ghar")
        j.plan(minutes=1)
        self.answers.type(self.tg, "masala tea and tea gifts")
        j.plan(minutes=1)
        self.assertIn("sample price", self.tg.questions()[-1]["text"])
        for label in ("6", "Product pictures and banners", "No study", "DTJ's own store", "Everything", "The first 3", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        p = j.s["plan"]
        self.assertEqual((p["source"], p["product_pages"], p["products"], j.s["brand"]["name"]), ("samples", 3, [], "Chai Ghar"))
        self.assertIn("Make 6 sample products for <b>Chai Ghar</b>", self.tg.last()["text"])
        with self.assertRaises(SystemExit):
            j.copy(minutes=1)  # the samples are made first
        f = self.tmp / "assets.json"
        f.write_text(json.dumps(dict(SAMPLES, research=self.research())), encoding="utf-8")
        self.assertEqual(j.assets(f), 0)
        self.assertEqual([k for k, _, _ in self.pictures], ["product"] * 12 + ["banner"] * 2)
        br = j.s["brand"]
        self.assertEqual(len(br["products"]), 6)
        self.assertEqual(br["products"][0]["tags"], ["dtj-sample", "dtj-sample-price"])
        self.assertEqual((br["products"][0]["variants"][0]["price"], br["products"][0]["variants"][0]["compare_at_price"]), ("299", "399"))
        self.assertEqual({c["handle"]: len(c["products"]) for c in br["collections"]}, {"tea": 6, "gifts": 3})
        self.assertEqual([x["handle"] for x in p["products"]], ["chai-blend-1", "chai-blend-2", "chai-blend-3"])
        self.assertEqual(len(br["banners"]), 2)
        self.assertEqual(j.assets(f), 0)
        self.assertEqual(len(self.pictures), 14)  # nothing made twice
        self.assertEqual(j.copy(minutes=1), store_job.WAITING)  # every sample has its price: straight to the Approve tap
        brand, prices = self.planned_with[0]
        self.assertEqual((len(brand["products"]), prices), (6, {}))
        self.assertIn("Add the sample products of <b>Chai Ghar</b>", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Approve")
        self.assertEqual(j.copy(minutes=1), 0)
        j.record("Home page", "https://royal-dosa.myshopify.com/?preview_theme_id=1")
        self.assertEqual(j.finish("partly done", "the apps wait for their installs"), 0)
        hand = (self.tmp / "royal-dosa" / "handover.md").read_text(encoding="utf-8")
        for part in ("Added: 2 products (every one ACTIVE), 1 collections", "- Home page: https://royal-dosa.myshopify.com/?preview_theme_id=1",
                     "- Sample products: 6 (Chai Blend 1", "- Sample prices (dtj-sample-price): 6", "- Pictures made by ChatGPT: 14",
                     "- Payments:", "- Launch: a test order in test mode"):
            self.assertIn(part, hand)
        self.assertIn("Samples to replace before launch", self.told()[-1])
        self.assertNotIn("Payments", self.told()[-1])  # Telegram gets the short part; the owner's list is in the file

    def test_a_samples_file_without_a_price_a_claim_or_the_wrong_count_is_refused(self):
        good = SAMPLES["products"][:3]
        self.assertEqual(store_job.sample_problems(good, 3), [])
        bad = [{k: v for k, v in good[0].items() if k != "price"}, dict(good[1], description="Clinically proven to calm you, rated 5 stars by 2,000 buyers."),
               dict(good[2], pictures=[], compare_at_price="10")]
        why = " | ".join(store_job.sample_problems(bad, 3))
        for part in ("product 1: a sample price", 'says "clinically"', "product 3: 1-3 picture prompts", "product 3: the compare-at price"):
            self.assertIn(part, why)
        self.assertIn("4 products, the person asked for 3", " ".join(store_job.sample_problems(good + good[:1], 3)))

    def test_local_pictures_go_through_the_staged_upload_and_typed_prices_drop_the_tag(self):
        pics = self.tmp / "pics"
        pics.mkdir()
        (pics / "1.jpg").write_bytes(b"jpg")
        (pics / "2.heic").write_bytes(b"heic")
        brand = json.loads(json.dumps(DRIVE_BRAND))
        brand["products"][0]["images"] = [{"path": str(pics / "1.jpg"), "alt": "Masala Chai"}, {"path": str(pics / "2.heic"), "alt": "x"}]
        sent = []

        def upload(paths, call, shop):
            sent.append((paths, shop))
            return {str(x): f"https://shopify-staged-uploads.storage.googleapis.com/tmp/{x.name}" for x in paths}
        out = store_job._local_pictures(brand, "royal-dosa.myshopify.com", upload=upload)
        self.assertEqual(sent, [([pics / "1.jpg"], "royal-dosa.myshopify.com")])
        self.assertEqual(out["products"][0]["images"], [{"src": "https://shopify-staged-uploads.storage.googleapis.com/tmp/1.jpg",
                                                        "alt": "Masala Chai"}])
        self.assertEqual(out["left_out_pictures"], 1)
        priced = store_job.priced(out, {"ginger-chai": "199"})
        g = priced["products"][1]
        self.assertEqual((g["variants"][0]["price"], g["tags"], g["price_needed"]), ("199", [], False))


class CompetitorStudy(Base):
    """Harsh, 23 Oct 2026: "an option for competitor website analysis and a block that asks what to focus on"."""

    def to_rivals(self, j):
        j.plan(minutes=1)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertIn("study competitor websites first", self.tg.questions()[-1]["text"])

    def test_links_sent_and_focus_picked_one_by_one(self):
        j = self.job()
        self.to_rivals(j)
        self.answers.tap(self.tg, "Yes: I'll send their links")
        j.plan(minutes=1)
        self.answers.type(self.tg, "no link here")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertTrue(any("found no website link" in d["text"] for _, d in self.tg.sent))
        self.answers.type(self.tg, "https://bluetea.co.in\nhttps://www.sleepyowl.co/ and https://bluetea.co.in, http://x.example).")
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Choose one by one")
        j.plan(minutes=1)
        self.assertIn("Study their pictures (banners", self.tg.questions()[-1]["text"])
        for answer in ("Yes", "Yes", "Yes", "No", "No", "No"):
            self.answers.tap(self.tg, answer)
            j.plan(minutes=1)
        self.assertIn("Anything specific you want me to look at as well?", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "I'll type it")
        j.plan(minutes=1)
        self.answers.type(self.tg, "How they   show the ingredients on the first phone screen")
        j.plan(minutes=1)
        rivals = j.s["plan"]["competitors"]
        self.assertEqual(rivals, {"how": "send", "links": ["https://bluetea.co.in", "https://www.sleepyowl.co/", "http://x.example"],
                                  "focus": ["pictures", "copy", "palette"],
                                  "note": "How they show the ingredients on the first phone screen"})
        self.assertIn("Whose store is", self.tg.questions()[-1]["text"])

    def test_find_them_and_everything_then_the_study_is_kept_and_sent(self):
        j = self.job()
        self.to_rivals(j)
        for label in ("Yes: find them yourself", "Everything", "No, that's all", "DTJ's own store", "Everything except product pages",
                      "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertEqual(j.s["plan"]["competitors"]["focus"], list(store_job.FOCUS))
        self.assertIn("Competitor study (I find them): pictures, copywriting, colour palette and fonts", self.tg.last()["text"])
        f = self.tmp / "study.md"
        f.write_text("# Pictures\nWarm beige backgrounds.\n# Copywriting\nShort lines.\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as short:
            j.study(f)  # a heading is missing for most of the focus
        self.assertIn("Colour palette and fonts", str(short.exception))
        body = "".join(f"## {store_job.FOCUS[k].split(' (')[0]}\nThey do this; we do that, in our own words and pictures.\n" for k in store_job.FOCUS)
        f.write_text(body, encoding="utf-8")
        self.assertEqual(j.study(f), 0)
        self.assertTrue((self.tmp / "royal-dosa" / "study.md").exists())
        self.assertIn("Competitor study for <b>Royal Dosa</b>", self.tg.last()["text"])
        self.assertIn("Competitor study:", j.handover())

    def test_only_what_i_type_and_the_study_must_answer_it(self):
        j = self.job()
        self.to_rivals(j)
        for label in ("Yes: find them yourself", "Only what I type"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.type(self.tg, "Their bundles and how they price a 3-pack")
        j.plan(minutes=1)
        for label in ("DTJ's own store", "Everything except product pages", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertEqual(j.s["plan"]["competitors"], {"how": "find", "focus": [], "note": "Their bundles and how they price a 3-pack"})
        self.assertIn("your request: Their bundles and how they price a 3-pack", self.tg.last()["text"])
        f = self.tmp / "study.md"
        f.write_text("# Pictures\n" + "Something about pictures that is long enough to pass the length check. " * 4, encoding="utf-8")
        with self.assertRaises(SystemExit) as no_answer:
            j.study(f)
        self.assertIn("Your request", str(no_answer.exception))
        f.write_text("# Your request\n" + "They sell 3-packs at a lower price per pack; we show our own pack sizes only. " * 4,
                     encoding="utf-8")
        self.assertEqual(j.study(f), 0)

    def test_no_study_skips_the_focus(self):
        j = self.job()
        self.to_rivals(j)
        self.answers.tap(self.tg, "No study")
        j.plan(minutes=1)
        self.assertEqual(j.s["plan"]["competitors"], {"how": "no", "links": [], "focus": []})
        self.assertIn("Whose store is", self.tg.questions()[-1]["text"])
        with self.assertRaises(SystemExit):
            j.study(self.tmp / "none.md")


class PagesAndMenus(Base):
    """About, Contact, FAQ and the menus (22 Oct 2026: a store handed over ready to sell), each with its own Approve tap."""

    def ready(self, catcher):
        j = store_job.Job("royal-dosa", send=self.tg, rows=self.answers, log=self.log, state_dir=self.tmp, out=self.printed.append,
                          sleep=self.clock.sleep, clock=self.clock, catcher=catcher)
        j.begin(SCAN, CHAT, "Harsh")
        j.s["planned"] = True
        j.s["brand"] = {"collections": [{"handle": "tea", "title": "Tea"}, {"handle": "gifts", "title": "Gifts"}]}
        return j

    def test_pages_wait_for_their_tap_then_go_through_store_builder_once(self):
        calls = []

        def catcher(body):
            calls.append(body)
            return {"created": ["about-us", "faq"], "skipped": ["contact"], "failed": []}
        j = self.ready(catcher)
        f = self.tmp / "pages.json"
        f.write_text(json.dumps({"pages": [
            {"handle": "about-us", "title": "About us", "body_html": "<p>Founded in Rajkot.</p>", "sample": True},
            {"handle": "contact", "title": "Contact", "body_html": "", "template_suffix": "contact"},
            {"handle": "faq", "title": "FAQ", "body_html": "<h3>How do I order?</h3><p>Add to cart.</p>", "sample": True}]}), encoding="utf-8")
        self.assertEqual(j.pages(f, minutes=1), store_job.WAITING)
        self.assertEqual(calls, [])  # nothing before the tap
        self.assertIn("Sample text, to replace before launch: About us, FAQ", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Approve", by="Riya")
        self.assertEqual(j.pages(f, minutes=1), 0)
        self.assertEqual((calls[0]["op"], calls[0]["approved_by"], calls[0]["pages"][1]["template_suffix"]),
                         ("pages", "Riya (Telegram Approve)", "contact"))
        self.assertEqual(j.s["sample_pages"], ["About us", "FAQ"])
        self.assertEqual(j.pages(f, minutes=1), 0)
        self.assertEqual(len(calls), 1)  # done once
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"pages": [{"handle": "About Us", "title": "x"},
                                             {"handle": "faq", "title": "FAQ", "body_html": "<p>Clinically proven</p>", "sample": True}]}))
        k = self.ready(catcher)
        k.s.pop("pages_result", None)
        with self.assertRaises(SystemExit) as refused:
            store_job.Job.pages(k, bad, minutes=1)
        self.assertIn("a claim word in sample text", str(refused.exception))

    def test_menus_use_the_real_collections_and_pages_one_tap_for_both(self):
        calls = []

        def catcher(body):
            calls.append(body)
            if body["handle"] == "footer":
                raise store_job.CatcherError("the install service said 502: Shopify refused it: Access denied")
            return {"menu": body["handle"], "items": [{"title": x["title"], "url": "/"} for x in body["items"]], "left_out": [], "before": []}
        j = self.ready(catcher)
        self.assertEqual(j.menus(minutes=1), store_job.WAITING)
        ask = self.tg.questions()[-1]["text"]
        self.assertIn("Main menu: Home, Shop all, Tea, Gifts, About us, Contact", ask)
        self.assertIn("Footer: About us, Contact, FAQ, Search, Refund policy, Shipping policy, Privacy policy, Terms of service", ask)
        self.answers.tap(self.tg, "Approve", by="Harsh")
        self.assertEqual(j.menus(minutes=1), 1)  # the footer was refused: said, the main menu is still set
        self.assertEqual([c["handle"] for c in calls], ["main-menu", "footer"])
        self.assertTrue(all(c["approved_by"] == "Harsh (Telegram Approve)" for c in calls))
        self.assertIn("footer: not set", self.tg.last()["text"])
        hand = j.handover()
        self.assertIn("- Menus set: main-menu", hand)
        self.assertIn("- Menus: the main menu and footer menu", hand)  # the footer is still the owner's


class ShopsList(Base):
    """A connected store (draft theme + apps) joins the shops list, so its product links work in the bot (23 Oct 2026)."""

    def test_added_once_with_the_draft_and_the_registry_and_never_twice(self):
        rows = []

        def stores_row(row):
            rows.append(row)
            return "added" if len(rows) == 1 else "exists"
        j = store_job.Job("dtj-testing", send=self.tg, rows=self.answers, log=self.log, state_dir=self.tmp, out=self.printed.append,
                          sleep=self.clock.sleep, clock=self.clock, stores_row=stores_row, today=lambda: "23 Oct 2026")
        j.begin({**SCAN, "myshopify_domain": "dtj-testing.myshopify.com", "name": "DTJ Testing"}, CHAT, "Harsh")
        j.shops_list()
        self.assertEqual(rows, [])  # no draft theme yet: not connected
        j.s["draft"] = {"id": "189402775703"}
        j.shops_list()
        self.assertEqual((rows[0]["draft_theme_id"], rows[0]["client_registry"], rows[0]["active"]),
                         ("189402775703", "page_builder/clients/dtj-testing.json", True))
        self.assertIn("is on the shops list now", self.tg.last()["text"])
        j.shops_list()
        self.assertEqual(len(rows), 1)  # done once


class FreshJob(unittest.TestCase):
    """A new n8n run for the same store starts with fresh questions; the old job is kept aside (23 Oct 2026)."""

    def test_a_new_run_moves_the_old_job_aside_and_the_same_run_keeps_it(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        folder = root / "dtj-testing"
        folder.mkdir()
        (folder / "job.json").write_text(json.dumps({"run": "988", "planned": True}), encoding="utf-8")
        self.assertIsNone(store_job.fresh_job(folder, ""))  # no run given: nothing moves
        self.assertIsNone(store_job.fresh_job(folder, "988"))  # the same run (a rerun after exit 3): kept
        moved = store_job.fresh_job(folder, "1201", stamp=lambda: "20261023-090000")
        self.assertEqual(moved, root / "dtj-testing-20261023-090000")
        self.assertTrue((moved / "job.json").exists())
        self.assertFalse(folder.exists())
        self.assertIsNone(store_job.fresh_job(folder, "1201"))  # nothing there any more: the new job starts from scratch
        legacy = root / "elevate"
        legacy.mkdir()
        (legacy / "job.json").write_text("{}", encoding="utf-8")  # a job from before runs were recorded
        self.assertIsNotNone(store_job.fresh_job(legacy, "1300", stamp=lambda: "x"))


class Activate(Base):
    def test_old_drafts_are_switched_on_in_rounds_and_logged_with_the_named_yes(self):
        calls = []

        def catcher(body):
            calls.append(body["handles"])
            hs = body["handles"]
            return {"activated": hs[:12], "left": hs[12:]} if hs != ["gone"] else {"not_found": ["gone"]}
        j = store_job.Job("royal-dosa", send=self.tg, rows=self.answers, log=self.log, state_dir=self.tmp, out=self.printed.append,
                          sleep=self.clock.sleep, clock=self.clock, catcher=catcher)
        j.begin(SCAN, CHAT, "Harsh")
        with self.assertRaises(SystemExit):
            j.activate("Harsh", ["a"])  # no plan yet
        j.s["planned"] = True
        handles = [f"p-{n}" for n in range(30)]
        self.assertEqual(j.activate("Harsh (chat, 22 Oct 2026)", handles + handles[:3]), 0)
        self.assertEqual([len(c) for c in calls], [30, 18, 6])
        self.assertEqual(json.loads(self.printed[-1])["activated"], 30)
        self.assertEqual(self.log.rows[-1]["approved_by"], "Harsh (chat, 22 Oct 2026)")
        with self.assertRaises(SystemExit):
            j.activate("  ", handles)


class PrivateScan(unittest.TestCase):
    """A store behind its password page, read with DTJ's own access (22 Oct 2026, dtj-testing)."""

    class Access:
        def __init__(self):
            self.pulled = []

        def themes(self, role=None, **_):
            return [{"id": 189402906775, "name": "test-data", "role": "live"}]

        def pull(self, theme_id, files, dest):
            self.pulled.append((theme_id, list(files)))
            (dest / "config").mkdir(parents=True, exist_ok=True)
            (dest / "config" / "settings_schema.json").write_text(json.dumps([{"name": "theme_info", "theme_name": "Horizon",
                                                                               "theme_version": "4.2.0"}]), encoding="utf-8")

    def test_its_live_theme_and_store_builders_view(self):
        access = self.Access()
        inside = {"name": "DTJ Testing", "currency": "USD", "products": ["a", "b"], "collections": ["c"]}
        sc = store_job._private_scan("dtj-testing.myshopify.com", "https://admin.shopify.com/store/dtj-testing", access=access,
                                     catcher=lambda body: inside)
        self.assertEqual((sc["name"], sc["currency"], sc["product_count"], sc["collection_count"], sc["password"]),
                         ("DTJ Testing", "USD", 2, 1, True))
        self.assertEqual(sc["live_theme"], {"name": "test-data", "id": "189402906775", "schema_name": "Horizon", "schema_version": "4.2.0"})
        self.assertEqual(access.pulled, [("189402906775", ["config/settings_schema.json"])])  # read only: one settings file
        self.assertEqual(sc["best_sellers"][0], {"handle": "a", "title": "a", "url": "https://dtj-testing.myshopify.com/products/a"})

    def test_without_store_builder_the_handle_names_it(self):
        def missing(body):
            raise store_job.NotInstalled("not installed")
        sc = store_job._private_scan("dtj-testing.myshopify.com", "x", access=self.Access(), catcher=missing)
        self.assertEqual((sc["name"], sc["product_count"]), ("dtj-testing", 0))


class Installs(Base):
    """DTJ's own store: 7 Install buttons in Telegram, each app switched on as soon as it is installed (Harsh, 22 Oct 2026)."""
    APPS = [("blocks", "DTJ Blocks", "a" * 32), ("sections", "DTJ Sections", "b" * 32), ("heroes", "DTJ Heroes", "c" * 32)]

    def setUp(self):
        super().setUp()
        self.installed, self.switched = {}, []

    def licence(self, key, state, approved_by):
        if state == "status":
            return (200, self.installed[key]) if key in self.installed else (404, {"error": "not installed"})
        self.switched.append((key, approved_by))
        self.installed[key] = {**self.installed[key], "licence": "active"}
        return 200, {"verified": True}

    def ready(self, whose="DTJ's own store"):
        j = store_job.Job("royal-dosa", send=self.tg, rows=self.answers, log=self.log, state_dir=self.tmp, out=self.printed.append,
                          sleep=self.clock.sleep, clock=self.clock, licence=self.licence, org_apps=lambda: self.APPS)
        j.begin(SCAN, CHAT, "Harsh")
        j.plan(minutes=1)
        names = ['Use "Royal Dosa"'] if whose == "A client's store" else []
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", whose, *names, "Everything except product pages", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        return j

    def test_buttons_once_then_each_install_is_switched_on_under_the_apps_tap(self):
        j = self.ready()
        with self.assertRaises(SystemExit):
            j.installs(minutes=1)  # no apps tap yet
        j.apps(minutes=1)
        self.assertIn("send you 7 Install buttons and switch each app on", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Approve", by="Harsh")
        j.apps(minutes=1)
        self.installed["royal-dosa-blocks"] = {"app_handle": "dtj-blocks", "licence": None}
        self.assertEqual(j.installs(minutes=1), store_job.WAITING)
        buttons = [r[0] for r in self.tg.questions()[-1]["reply_markup"]["inline_keyboard"]]
        self.assertEqual(buttons[0], {"text": "Install DTJ Blocks",
                                      "url": "https://admin.shopify.com/store/royal-dosa/oauth/install?client_id=" + "a" * 32})
        self.assertEqual(len(buttons), 3)
        self.assertEqual(self.switched, [("royal-dosa-blocks", "Harsh (Telegram Approve)")])
        self.installed["royal-dosa-sections"] = {"app_handle": "dtj-sections", "licence": "active"}  # already on: nothing to switch
        self.installed["royal-dosa-heroes"] = {"app_handle": "dtj-heroes", "licence": "inactive"}
        sent = len(self.tg.sent)
        self.assertEqual(j.installs(minutes=1), 0)
        self.assertEqual([k for k, _ in self.switched], ["royal-dosa-blocks", "royal-dosa-heroes"])
        self.assertEqual(len([d for m, d in self.tg.sent[sent:] if "reply_markup" in d]), 0)  # the buttons are sent once
        self.assertIn("All 3 DTJ apps are installed and switched on", self.tg.last()["text"])
        self.assertEqual(self.log.rows[-1]["approved_by"], "Harsh (Telegram Approve)")

    def test_a_client_store_gets_its_buttons_from_add_shop(self):
        j = self.ready(whose="A client's store")
        self.assertEqual(j.installs(minutes=1), 0)
        self.assertIn("add_shop.py sends its Install buttons", self.printed[-1])


class RealActionLog(unittest.TestCase):
    """The job's rows go through the real action log, whose schema refuses an unknown field or result (22 Oct 2026: "approver" and
    "skipped" crashed the live copy job after Harsh's tap)."""

    def test_every_kind_of_row_the_job_writes_is_valid(self):
        import sys as _sys  # noqa: PLC0415
        _sys.path.insert(0, str(store_job.ROOT / "services" / "store-builder"))
        from provision.actionlog import ActionLog  # noqa: PLC0415
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        tg, answers = Telegram(), Answers()
        j = store_job.Job("royal-dosa", send=tg, rows=answers, state_dir=tmp, out=lambda *_: None,
                          log=ActionLog(tmp / "action-log.jsonl", "royal-dosa", automation="store-job"), sleep=lambda s: None, clock=Clock())
        j.begin(SCAN, CHAT, "Harsh")
        j.plan(minutes=0)
        for label in ("Redesign an existing brand", "Already in this store", "No new pictures", "No study", "A client's store", 'Use "Royal Dosa"', "Everything except product pages", "No offer"):
            answers.tap(tg, label)
            j.plan(minutes=0)
        j.approve("ok_header", "Write the header", minutes=0)
        answers.tap(tg, "Approve")
        self.assertEqual(j.approve("ok_header", "Write the header", minutes=0), 0)
        j.approve("ok_footer", "Write the footer", minutes=0)
        answers.tap(tg, "Skip")
        self.assertEqual(j.approve("ok_footer", "Write the footer", minutes=0), store_job.SKIPPED)
        rows = [json.loads(x) for x in (tmp / "action-log.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(r["result"], r["approved_by"]) for r in rows], [("success", "Harsh"), ("blocked", "Harsh")])


class OpenMarks(unittest.TestCase):
    def test_a_typed_question_is_marked_open_then_closed_and_marks_are_never_answers(self):
        tg, answers, marks, state = Telegram(), Answers(), [], {}
        a = bot_ask.Asker("dtj-testing", CHAT, send=tg, rows=answers, state=state, save=lambda: None, add_row=marks.append,
                          sleep=lambda s: None, clock=Clock(), now=lambda: "2026-10-22T06:25:59Z")
        a.ask_text("brand_link", "Send the brand's link")
        self.assertEqual([(m["key"], m["choice"], m["value"]) for m in marks], [("brand_link", "open", "")])
        answers.rows.append({"id": 9, "job": "dtj-testing", "key": "brand_link", "value": "", "choice": "open", "by": "", "chat_id": CHAT,
                             "at": "2099-01-01T00:00:00Z"})  # the mark itself sits in the same table
        self.assertIsNone(a.answer("brand_link"))
        answers.type(tg, "https://sensofoods.com/")
        self.assertEqual(a.answer("brand_link")["value"], "https://sensofoods.com/")
        self.assertEqual([m["choice"] for m in marks], ["open", "closed"])
        a.ask("whose", "Whose store?", [("Ours", "dtj")])  # a button question gets no mark
        self.assertEqual(len(marks), 2)


class CatcherRetry(unittest.TestCase):
    """22 Oct 2026: a dropped connection stopped the Senso policy copy; the call is now tried again (max 3 more, CLAUDE.md)."""

    def test_a_dropped_connection_is_tried_again_and_a_4xx_is_final(self):
        import urllib.error  # noqa: PLC0415
        tries, pauses = [], []

        class Answer:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(self.data).encode()

        def flaky(req, timeout):
            tries.append(json.loads(req.data)["ts"])
            if len(tries) < 3:
                raise urllib.error.URLError(ConnectionResetError(10054, "closed by the remote host"))
            return Answer({"done": {}})
        old = os.environ.get("DTJ_CATCHER_CONTROL_KEY")
        os.environ["DTJ_CATCHER_CONTROL_KEY"] = "test-key"
        try:
            self.assertEqual(store_job._catcher({"op": "status", "job": "x"}, opener=flaky, sleep=pauses.append), {"done": {}})
            self.assertEqual((len(tries), pauses), (3, [2, 4]))

            def always_down(req, timeout):
                raise urllib.error.URLError("down")
            with self.assertRaises(store_job.CatcherError):
                store_job._catcher({"op": "status", "job": "x"}, opener=always_down, sleep=lambda s: None)

            def refused(req, timeout):
                raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b'{"error": "bad request"}'))
            calls = []
            with self.assertRaises(store_job.CatcherError):
                store_job._catcher({"op": "status", "job": "x"}, opener=lambda r, timeout: calls.append(1) or refused(r, timeout),
                                   sleep=lambda s: None)
            self.assertEqual(len(calls), 1)  # a 4xx is never repeated
        finally:
            if old is None:
                os.environ.pop("DTJ_CATCHER_CONTROL_KEY", None)
            else:
                os.environ["DTJ_CATCHER_CONTROL_KEY"] = old


class Pieces(unittest.TestCase):
    def test_typed_products_match_by_link_or_unique_name(self):
        sellers = SCAN["best_sellers"]
        picked, left, notes = store_job.match_products(["Mix", "PODI", "/products/sambar", "", "/products/none", "cake"], sellers)
        self.assertEqual([p["handle"] for p in picked], ["podi", "sambar"])  # "Mix" matches two products: not guessed
        self.assertEqual(left, ["Mix: matches 2 products (Idli Mix, Masala Dosa Mix): send its link",
                                "/products/none: not a product of this store", "cake: not found in the store"])
        self.assertEqual(notes, [])

    def test_an_exact_name_wins_and_same_name_products_take_the_best_seller(self):
        # the first live run (21 Oct 2026, elevate): "TOILOVA" next to three "TOILOVA (Copy)" products, and two products called
        # "We are there for each other"; the old matcher refused both and the job stopped
        sellers = [{"handle": h, "title": t, "url": f"https://x/products/{h}"} for h, t in (
            ("toilova-copy-copy", "TOILOVA (Copy) (Copy)"), ("we-are-there-for-each-other-2", "We are there for each other"),
            ("toilova", "TOILOVA"), ("toilova-copy", "TOILOVA (Copy)"), ("we-are-there-for-each-other", "We are there for each other"))]
        picked, left, notes = store_job.match_products(["TOILOVA", " We are there for each other"], sellers)
        self.assertEqual([p["handle"] for p in picked], ["toilova", "we-are-there-for-each-other-2"])
        self.assertEqual(left, [])
        self.assertEqual(notes, ['2 products are called "We are there for each other": took the best seller, '
                                 "https://x/products/we-are-there-for-each-other-2"])

    def test_a_stop_is_told_in_telegram(self):
        tg, answers = Telegram(), Answers()
        with tempfile.TemporaryDirectory() as tmp:
            j = store_job.Job("royal-dosa", send=tg, rows=answers, state_dir=Path(tmp), out=lambda *_: None)
            j.begin(SCAN, CHAT, "Harsh")
            j.plan(minutes=0)
            answers.tap(tg, "Wrong store: stop")
            self.assertEqual(j.plan(minutes=0), 1)
        self.assertEqual(tg.last()["text"], "Stopped: the person said it is the wrong store.")

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

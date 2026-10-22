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
        self.assertIn("Which brand should I build in this store?", self.tg.questions()[0]["text"])
        self.assertIn("4 products, 2 collections, live theme Horizon (Horizon)", self.tg.questions()[0]["text"])
        self.answers.tap(self.tg, "This store is the brand")
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
        self.assertEqual(data, "a:royal-dosa:brand_src:0")
        self.assertLessEqual(len(store_job.job_id("a" * 60 + ".myshopify.com")), 24)
        self.assertLessEqual(len(f"a:{store_job.job_id('a' * 60 + '.myshopify.com')}:{'x' * 20}:9".encode()), 64)

    def test_answers_from_another_chat_do_not_count_and_the_last_answer_wins(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "This store is the brand", chat="999")
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.answers.tap(self.tg, "Wrong store: stop")
        self.answers.tap(self.tg, "This store is the brand")
        j.plan(minutes=1)
        self.assertFalse(j.s["plan"]["copy"])
        self.assertIn("Whose store is", self.tg.questions()[-1]["text"])

    def test_an_old_tap_left_in_the_table_does_not_answer_a_new_question(self):
        # the second run for elevate (21 Oct 2026): the table still held the first run's taps for the same job and keys
        self.answers.rows.append({"id": 1, "job": "royal-dosa", "key": "brand_src", "value": "This store is the brand", "choice": "1",
                                  "by": "Harsh", "chat_id": CHAT, "at": "2020-01-01T10:00:00.000Z"})
        j = self.job()
        self.assertEqual(j.plan(minutes=1), store_job.WAITING)
        self.assertNotIn("brand_src", j.s["answers"])
        self.assertIn("at", j.s["asked"]["brand_src"])

    def test_wrong_store_stops(self):
        j = self.job()
        j.plan(minutes=1)
        self.answers.tap(self.tg, "Wrong store: stop")
        self.assertEqual(j.plan(minutes=1), 1)
        self.assertIn("wrong store", j.s["stopped"])

    def test_a_theme_the_builder_does_not_know_asks_for_horizon_first(self):
        j = self.job(scan={**SCAN, "live_theme": {"name": "Impact", "schema_name": "Impact"}})
        j.plan(minutes=1)
        for label in ("This store is the brand", "DTJ's own store"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertIn("Add theme > Horizon (do NOT publish it)", self.tg.questions()[-1]["text"])
        self.answers.tap(self.tg, "Stop")
        self.assertEqual(j.plan(minutes=1), 1)

    def test_a_dawn_store_gets_product_pages_only(self):
        j = self.job(scan={**SCAN, "live_theme": {"name": "Dawn", "schema_name": "Dawn"}})
        j.plan(minutes=1)
        for label in ("This store is the brand", "DTJ's own store"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.answers.tap(self.tg, "Product pages only, on Dawn")
        j.plan(minutes=1)
        self.assertIn("Which product pages?", self.tg.questions()[-1]["text"])  # no "what to design" question
        self.assertEqual(j.s["plan"]["parts"], ["products"])

    def test_picked_products_by_link_or_name_and_unknown_ones_are_said(self):
        j = self.job()
        j.plan(minutes=1)
        for label in ("This store is the brand", "DTJ's own store", "Choose one by one", "No", "No", "No", "Yes", "I'll pick them"):
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
        for label in ("This store is the brand", "A client's store", 'Use "Royal Dosa"', "Everything except product pages", "No offer"):
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
        for label in ("This store is the brand", "DTJ's own store", "Done: Horizon is added", "Only product pages", "Top 3 best sellers",
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

        def plan(link, store, currency, out, job):
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
        self.answers.tap(self.tg, "I'll send the brand's link")
        j.plan(minutes=1)
        self.answers.type(self.tg, "https://glowco.com")
        j.plan(minutes=1)
        for label in ("DTJ's own store", "Everything", "All 2 products", "No offer"):
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
        self.assertIn("the brand copy", self.tg.last()["text"])

    def test_a_brand_that_cannot_be_read_is_asked_again_and_three_in_a_row_stop(self):
        def scanner(link):
            if "wordpress" in link:
                raise ValueError("no product pages to read")
            return BRAND
        j = self.job(scanner=scanner)
        j.plan(minutes=1)
        self.answers.tap(self.tg, "I'll send the brand's link")
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
        self.answers.tap(self.tg, "I'll send the brand's link")
        k.plan(minutes=1)
        for _ in range(3):
            self.answers.type(self.tg, "https://wordpress-brand.com")
            code = k.plan(minutes=1)
        self.assertEqual(code, 1)
        self.assertIn("three brand links in a row", k.s["stopped"])

    def test_a_website_brand_is_said_to_come_in_as_hidden_drafts(self):
        site = {**BRAND, "platform": "website", "myshopify_domain": None, "collection_count": 0, "prices": 0}
        j = self.job(scanner=lambda link: site)
        j.plan(minutes=1)
        self.answers.tap(self.tg, "I'll send the brand's link")
        j.plan(minutes=1)
        self.answers.type(self.tg, "https://glowco.com")
        j.plan(minutes=1)
        told = next(d["text"] for _, d in self.tg.sent if d["text"].startswith("Brand: <b>GlowCo</b>"))
        self.assertIn("not a Shopify store and shows no prices", told)
        self.assertIn("hidden drafts", told)
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
        self.assertEqual(self.log.rows[-1]["approver"], "Riya (Telegram Approve)")
        self.assertEqual(len(self.planned_with), 1)  # planned once
        self.assertEqual(j.copy(minutes=1), 0)
        self.assertEqual((len(self.planned_with), self.looked), (1, 2))  # finished: nothing asked again

    def test_store_builder_not_installed_asks_once_then_goes_on(self):
        tries = []

        def plan(link, store, currency, out, job):
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
        for label in ("This store is the brand", "DTJ's own store", "Only product pages", "Top 3 best sellers", "No offer"):
            self.answers.tap(self.tg, label)
            j.plan(minutes=1)
        self.assertEqual(j.copy(minutes=1), 0)
        self.assertEqual(self.printed[-1], "nothing to copy: this store is the brand")
        self.assertEqual(self.planned_with, [])


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

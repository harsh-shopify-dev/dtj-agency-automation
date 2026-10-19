import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from seo_engine import aeo_probe, config, gates, run_weekly, site_scan, wordpress, writer

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)
SITE = "https://digitaltusharjoshi.com"

PAGE = """<html><head><title>Performance Marketing Agency in India | DTJ</title>
<meta name="description" content="DTJ is a Data-Driven Digital Marketing Services Agency in India, We Helping Brands Grow">
<link rel="canonical" href="https://digitaltusharjoshi.com/">
<script type="application/ld+json">{"@graph":[{"@type":"WebPage"},{"@type":"Organization"}]}</script>
<script>var x = "not words";</script></head>
<body><h1>Grow your D2C brand</h1><h2>Why are my ads not giving orders?</h2><p>Some words here.</p>
<img src="a.png"><img src="b.png" alt="dashboard"></body></html>"""


def fetcher(pages: dict):
    def fetch(url):
        if url in pages:
            status, ctype, body = pages[url]
            return site_scan.Response(status, url, ctype, body)
        return site_scan.Response(404, url, "", "")
    return fetch


def site_pages():
    index = f"<sitemapindex><sitemap><loc>{SITE}/page-sitemap.xml</loc></sitemap></sitemapindex>"
    urlset = (f"<urlset><url><loc>{SITE}/</loc><lastmod>2026-07-16T11:54:27+00:00</lastmod></url>"
              f"<url><loc>{SITE}/sample-page/</loc><lastmod>2025-07-24T09:06:17+00:00</lastmod></url></urlset>")
    return {f"{SITE}/sitemap_index.xml": (200, "text/xml", index), f"{SITE}/page-sitemap.xml": (200, "text/xml", urlset),
            f"{SITE}/": (200, "text/html", PAGE), f"{SITE}/sample-page/": (200, "text/html", PAGE),
            f"{SITE}/llms.txt": (200, "text/plain", "# Digital Tushar Joshi: India's #1 Performance Marketing Agency\n")}


PARA = ("Start with what a shopper sees after they tap your ad. If the page they land on is slow, confusing or different from the "
        "ad, they leave. Open your own ad on your phone and buy something from your own store, step by step, and write down every "
        "moment you felt unsure.")


def good_article(**over):
    a = {
        "title": "Ads running but no orders? What to check first",
        "slug": "ads-running-no-orders-what-to-check",
        "meta_description": ("Your Facebook ads get views but no orders. Here is what to check first on the ad, the page and the "
                             "checkout, in plain words, before you spend more."),
        "short_answer": ("When ads get views but no orders, the problem is usually after the click: the page does not match the ad, "
                         "the price or delivery is unclear, or checkout is hard on a phone. Check those before you change the ads."),
        "sections": [{"heading": f"What should I check {w}?", "paragraphs": [PARA, PARA]} for w in
                     ("first", "on the page", "at checkout", "in the ad", "next week", "with my team")],
        "faq": [{"question": "Should I stop my ads?", "answer": "Not before you have checked the page and the checkout."},
                {"question": "Is it the product?", "answer": "Sometimes, but check what a shopper sees first."},
                {"question": "Can DTJ look at it?", "answer": "Yes. DTJ offers a free growth audit. If we don't see a clear "
                                                              "opportunity, we'll tell you."}],
        "facts_used": ["offer-audit", "promise-honest", "proof-royal-dosa"],
        "internal_links": [{"url": f"{SITE}/performance-marketing-agency-in-india/", "anchor": "how we run ads"}],
    }
    a["sections"][0]["paragraphs"].append("The Royal Dosa Paper reached ₹5.28Cr in sales and 1.68L orders, from its own Shopify report.")
    a.update(over)
    return a


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        c = config.load({})
        self.assertEqual((c.automation_enabled, c.dry_run, c.mode, c.site), (False, True, "shadow", SITE))
        self.assertTrue(c.decide(0).allowed)
        self.assertFalse(c.decide(1).allowed)

    def test_only_drafts_ever_allowed(self):
        c = config.load({"AUTOMATION_ENABLED": "1", "SEO_DRY_RUN": "0", "SEO_MODE": "approve"})
        self.assertTrue(c.decide(1).allowed)
        self.assertFalse(c.decide(2).allowed)
        self.assertFalse(c.decide(2, "  ").allowed)
        self.assertTrue(c.decide(2, "Harsh").allowed)
        self.assertFalse(c.decide(3, "Harsh").allowed)
        self.assertFalse(config.load({}).decide(2, "Harsh").allowed)  # kill switch off
        self.assertFalse(config.load({"AUTOMATION_ENABLED": "1", "SEO_DRY_RUN": "0"}).decide(1).allowed)  # shadow

    def test_bad_values_refused(self):
        with self.assertRaises(config.ConfigError):
            config.load({"SEO_MODE": "auto"})
        with self.assertRaises(config.ConfigError):
            config.load({"SEO_SITE": "http://insecure.example"})


class ScanTests(unittest.TestCase):
    def test_parse_page(self):
        p = site_scan.parse_page(SITE + "/", PAGE)
        self.assertEqual(p.h1, ["Grow your D2C brand"])
        self.assertEqual(p.questions, ["Why are my ads not giving orders?"])
        self.assertEqual(p.schema_types, ["Organization", "WebPage"])
        self.assertEqual((p.img_total, p.img_no_alt), (2, 1))
        self.assertNotIn("not words", " ".join(p.questions))

    def test_scan_findings(self):
        res = site_scan.scan(SITE, fetcher(site_pages()), delay=0, now=NOW)
        rules = {(f["rule"], f["page"]) for f in res["findings"]}
        self.assertIn(("wordpress-default-page", f"{SITE}/sample-page/"), rules)
        self.assertIn(("description-grammar", f"{SITE}/"), rules)
        self.assertIn(("llms-txt-claim", f"{SITE}/llms.txt"), rules)
        self.assertIn(("stale", f"{SITE}/sample-page/"), rules)
        self.assertNotIn(("entity-schema-missing", f"{SITE}/"), rules)  # the home page has Organization data
        self.assertEqual(res["findings"][0]["severity"], "high")
        self.assertEqual(res["pages_in_sitemap"], 2)

    def test_templates_and_encoded_canonicals(self):
        tpl = site_scan.parse_page(SITE + "/elementor-hf/footer/", PAGE)
        self.assertEqual([f.rule for f in site_scan.page_findings(tpl, NOW)], ["template-in-sitemap"])
        url = SITE + "/from-%e2%82%b91-lakh/"
        p = site_scan.parse_page(url, f'<link rel="canonical" href="{SITE}/from-₹1-lakh/"><h1>x</h1>')
        self.assertNotIn("canonical-elsewhere", {f.rule for f in site_scan.page_findings(p, NOW)})

    def test_broken_json_ld_is_reported(self):
        p = site_scan.parse_page(SITE + "/x", '<script type="application/ld+json">{bad</script><h1>x</h1>')
        self.assertIn("schema-broken", {f.rule for f in site_scan.page_findings(p, NOW)})


class GateTests(unittest.TestCase):
    def test_good_article_passes(self):
        r = gates.check(good_article())
        self.assertTrue(r.ok, r.blocks)

    def test_invented_number_blocks(self):
        a = good_article()
        a["sections"][1]["paragraphs"].append("Most brands see a 3X return within 45 days.")
        r = gates.check(a)
        self.assertFalse(r.ok)
        self.assertTrue(any("3X" in b for b in r.blocks), r.blocks)
        self.assertTrue(any("45" in b for b in r.blocks), r.blocks)

    def test_unsourced_stat_is_named(self):
        a = good_article()
        a["sections"][1]["paragraphs"].append("We have managed ₹70Cr+ in ad spend.")
        self.assertTrue(any("stat-ad-spend" in b for b in gates.check(a).blocks))

    def test_claims_process_and_tushar_call_block(self):
        for line in ("DTJ is the best agency in Gujarat.", "Book a call with Tushar today.", "Our AI agents write this.",
                     "We guarantee orders.", "We reply within 2 hours.", "DTJ fixes your RTO problem."):
            a = good_article()
            a["sections"][2]["paragraphs"].append(line)
            self.assertFalse(gates.check(a).ok, line)

    def test_best_inside_a_question_is_fine(self):
        a = good_article()
        a["faq"].append({"question": "What is the best way to test a new ad?", "answer": "Change one thing at a time."})
        self.assertTrue(gates.check(a).ok, gates.check(a).blocks)

    def test_outside_link_and_shape_block(self):
        r = gates.check(good_article(internal_links=[{"url": "https://competitor.in/x", "anchor": "x"}], slug="Bad Slug", faq=[]))
        self.assertTrue(any("competitor.in" in b for b in r.blocks))
        self.assertTrue(any("slug" in b for b in r.blocks))
        self.assertTrue(any("FAQ" in b for b in r.blocks))

    def test_jargon_warns_only(self):
        a = good_article()
        a["sections"][3]["paragraphs"].append("Your ROAS is what you earn for each rupee spent on ads.")
        r = gates.check(a)
        self.assertTrue(r.ok)
        self.assertTrue(any("roas" in w for w in r.warnings))

    def test_numbers_in(self):
        self.assertEqual([c for _, c in gates.numbers_in("3 steps in 2026, ₹1.5L, 2.8%, 3,071 orders, 16X, 45 days")],
                         ["1.5", "2.8", "3071", "16", "45"])


class FakeClient:
    def __init__(self, resp):
        self.resp, self.calls = resp, []
        self.messages = self.beta = NS(create=self._create)
        self.beta.messages = NS(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return self.resp(kw) if callable(self.resp) else self.resp


class WriterTests(unittest.TestCase):
    TOPIC = {"id": "ads-no-orders", "slug": "facebook-ads-no-orders", "question": "Ads but no orders?", "pain": "p", "words_they_use": ["no sales"]}

    def test_dry_run_calls_nothing(self):
        d = writer.write_article(self.TOPIC, [])
        self.assertEqual((d.mode, d.status), ("dry-run", "not-run"))

    def test_request_holds_only_approved_facts(self):
        params = writer.request_params(self.TOPIC, [{"url": SITE + "/", "title": "Home", "status": 200}])
        body = json.loads(params["messages"][0]["content"])
        self.assertTrue(body["approved_facts"])
        self.assertNotIn("70Cr", params["messages"][0]["content"])
        self.assertEqual(params["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(params["fallbacks"], "default")

    def test_live_passed_and_blocked(self):
        ok = NS(stop_reason="end_turn", model="claude-opus-5-5", id="m1", usage=NS(input_tokens=1000, output_tokens=2000),
                content=[NS(type="text", text=json.dumps(good_article()))])
        d = writer.write_article(self.TOPIC, [], client=FakeClient(ok))
        self.assertEqual(d.status, "passed", d.gate)
        self.assertEqual(d.article["slug"], "facebook-ads-no-orders")
        self.assertAlmostEqual(d.cost_usd, 0.044)
        bad = good_article()
        bad["short_answer"] = "DTJ is the No. 1 agency."
        d2 = writer.write_article(self.TOPIC, [], client=FakeClient(NS(stop_reason="end_turn", model="x", usage=None,
                                                                         content=[NS(type="text", text=json.dumps(bad))])))
        self.assertEqual(d2.status, "blocked")

    def test_refusal_and_api_error(self):
        d = writer.write_article(self.TOPIC, [], client=FakeClient(NS(stop_reason="refusal", content=[], model="x", usage=None)))
        self.assertEqual(d.status, "refusal")

        def boom(_):
            raise RuntimeError("down")
        self.assertEqual(writer.write_article(self.TOPIC, [], client=FakeClient(boom)).status, "api-error")

    def test_html_has_answer_first_and_faq_data(self):
        h = writer.to_html(good_article())
        self.assertTrue(h.startswith('<p class="dtj-short-answer">'))
        self.assertIn('"@type": "FAQPage"', h)
        self.assertNotIn("<script>alert", writer.to_html(good_article(short_answer="<script>alert(1)</script>")))


class ProbeTests(unittest.TestCase):
    def test_reads_names_and_citations(self):
        content = [
            {"type": "server_tool_use", "name": "web_search"},
            {"type": "web_search_tool_result", "content": [{"url": "https://clutch.co/in/agencies"}, {"url": "https://digitaltusharjoshi.com/"}]},
            {"type": "text", "text": "Options include Digital Tushar Joshi in Rajkot.",
             "citations": [{"url": "https://www.clutch.co/in/agencies"}, {"url": "https://digitaltusharjoshi.com/about-us/"}]},
        ]
        r = aeo_probe.read_answer(content)
        self.assertTrue(r["dtj_named"] and r["dtj_cited"] and r["dtj_in_search_results"])
        self.assertEqual(r["cited_hosts"][0], "clutch.co")

    def test_not_named_and_search_error(self):
        r = aeo_probe.read_answer([{"type": "web_search_tool_result", "content": {"error_code": "max_uses_exceeded"}},
                                   {"type": "text", "text": "Try agency X."}])
        self.assertFalse(r["dtj_named"] or r["dtj_cited"])

    def test_pause_turn_resumes_and_place(self):
        replies = iter([NS(stop_reason="pause_turn", content=[{"type": "text", "text": ""}], model="m"),
                        NS(stop_reason="end_turn", content=[{"type": "text", "text": "DTJ"}], model="m")])
        client = FakeClient(lambda kw: next(replies))
        r = aeo_probe.ask("q", client, place="Rajkot")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["tools"][0]["user_location"]["city"], "Rajkot")
        self.assertTrue(r["dtj_named"])

    def test_dry_run(self):
        self.assertEqual(aeo_probe.probe([{"q": "a"}, {"q": "b"}], None, limit=1)["planned"], ["a"])


class WordPressTests(unittest.TestCase):
    ENV = {"WP_USER": "editor", "WP_APP_PASSWORD": "xxxx xxxx"}

    def cfg(self):
        return config.load({})

    def test_sends_draft_only(self):
        sent = []

        def opener(req):
            sent.append(req)
            if req.get_method() == "GET":
                return 200, []
            return 201, {"id": 7, "status": "draft"}
        with mock.patch.dict("os.environ", self.ENV):
            out = wordpress.create_draft(self.cfg(), title="t", slug="s", html="<p>x</p>", excerpt="e", opener=opener)
        self.assertEqual(json.loads(sent[1].data)["status"], "draft")
        self.assertIn("post=7", out["edit_url"])
        self.assertNotIn("xxxx", json.dumps(out))

    def test_existing_slug_changes_nothing(self):
        sent = []

        def opener(req):
            sent.append(req)
            return 200, [{"id": 1}]
        with mock.patch.dict("os.environ", self.ENV), self.assertRaises(wordpress.WordPressError):
            wordpress.create_draft(self.cfg(), title="t", slug="s", html="", excerpt="", opener=opener)
        self.assertEqual([r.get_method() for r in sent], ["GET"])

    def test_no_credentials(self):
        with self.assertRaises(config.ConfigError):
            config.load({}).wp_credentials({})


class RunTests(unittest.TestCase):
    def test_free_dry_run_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run_weekly.run(live=False, out_root=Path(tmp), max_pages=10, probe_limit=3, fetch=fetcher(site_pages()), env={})
            out = Path(res["out"])
            self.assertTrue((out / "scan.json").exists() and (out / "report.md").exists())
            self.assertIn("Not run this week", res["report"])
            rows = [json.loads(l) for l in (Path(tmp) / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["action"] for r in rows], ["site scan", "prepare fixes batch", "AEO check", "draft article"])
            self.assertEqual(rows[-1]["result"], "dry_run")

    def test_live_shadow_keeps_the_draft_as_a_file(self):
        ok = NS(stop_reason="end_turn", model="claude-opus-5-5", usage=None, content=[NS(type="text", text=json.dumps(good_article()))])
        with tempfile.TemporaryDirectory() as tmp:
            res = run_weekly.run(live=True, out_root=Path(tmp), max_pages=10, probe_limit=0, fetch=fetcher(site_pages()),
                                 client=FakeClient(ok), env={"AUTOMATION_ENABLED": "1", "SEO_DRY_RUN": "0"},
                                 wp_opener=lambda req: self.fail("WordPress must not be called in shadow mode"))
            self.assertTrue((Path(res["out"]) / "draft.html").exists())
            rows = [json.loads(l) for l in (Path(tmp) / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual((rows[-1]["tier"], rows[-1]["result"]), (1, "recommended"))
            self.assertEqual(json.loads((Path(tmp) / "state.json").read_text())["written"], ["ads-no-orders"])

    def test_approve_mode_skips_topics_already_in_wordpress(self):
        ok = NS(stop_reason="end_turn", model="claude-opus-5-5", usage=None, content=[NS(type="text", text=json.dumps(good_article()))])
        sent = []

        def wp(req):
            sent.append((req.get_method(), req.full_url))
            if req.get_method() == "GET":
                return 200, [{"id": 1}] if "slug=facebook-ads-no-orders" in req.full_url else []
            return 201, {"id": 9, "status": "draft"}
        env = {"AUTOMATION_ENABLED": "1", "SEO_DRY_RUN": "0", "SEO_MODE": "approve", "WP_USER": "u", "WP_APP_PASSWORD": "p"}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", env):
            res = run_weekly.run(live=True, out_root=Path(tmp), max_pages=10, probe_limit=0, fetch=fetcher(site_pages()),
                                 client=FakeClient(ok), env=env, wp_opener=wp)
            rows = [json.loads(l) for l in (Path(tmp) / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
            state = json.loads((Path(tmp) / "state.json").read_text())
        self.assertEqual(rows[-1]["target"], "wordpress post draft: add-to-cart-no-buy")
        self.assertEqual(rows[-1]["result"], "success")
        self.assertEqual(state["written"], ["ads-no-orders", "add-to-cart-no-buy"])
        posted = [u for m, u in sent if m == "POST"]
        self.assertEqual(len(posted), 1)
        self.assertIn("post=9", res["report"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the 14 Oct 2026 upgrades: DataForSEO, keyword plan, top-3 outline, city pages, fixes batch, applying a batch."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from seo_engine import aeo_probe, apply_batch, city_page, dataforseo, fixer, gates, keywords, run_weekly, serp_skeleton, site_scan
from test_seo_engine import SITE, FakeClient, fetcher, good_article, site_pages

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)
DFS_ENV = {"DATAFORSEO_LOGIN": "login", "DATAFORSEO_PASSWORD": "pw"}


def dfs_reply(result: dict, cost: float = 0.01, status: int = 20000) -> dict:
    return {"cost": cost, "tasks": [{"status_code": status, "status_message": "Ok.", "cost": cost, "result": [result]}]}


class FakeDFS(dataforseo.Client):
    """A real Client whose network is replaced by canned answers per endpoint."""

    def __init__(self, answers: dict, cap: float = 5.0):
        self.sent = []

        def opener(req):
            path = req.full_url.split("/v3/", 1)[1]
            self.sent.append((path, json.loads(req.data)[0]))
            ans = answers[next(k for k in answers if path.startswith(k))]
            return ans(json.loads(req.data)[0]) if callable(ans) else ans
        super().__init__(cap_usd=cap, opener=opener, env=DFS_ENV)


IDEAS = [
    {"keyword": "facebook ads not getting sales", "keyword_info": {"search_volume": 320, "cpc": 0.4}, "keyword_properties": {"keyword_difficulty": 12},
     "search_intent_info": {"main_intent": "informational"}},
    {"keyword": "facebook ads no sales", "keyword_info": {"search_volume": 140, "cpc": 0.3}, "keyword_properties": {"keyword_difficulty": 10},
     "search_intent_info": {"main_intent": "informational"}},
    {"keyword": "digital marketing agency in rajkot", "keyword_info": {"search_volume": 90, "cpc": 0.8}, "keyword_properties": {"keyword_difficulty": 8},
     "search_intent_info": {"main_intent": "commercial"}},
    {"keyword": "digital marketing course", "keyword_info": {"search_volume": 9000, "cpc": 1.0}, "keyword_properties": {"keyword_difficulty": 20},
     "search_intent_info": {"main_intent": "commercial"}},
    {"keyword": "seo agency in india", "keyword_info": {"search_volume": 2000, "cpc": 2.0}, "keyword_properties": {"keyword_difficulty": 55},
     "search_intent_info": {"main_intent": "commercial"}},
    {"keyword": "shopify store no sales", "keyword_info": {"search_volume": 70, "cpc": 0}, "keyword_properties": {"keyword_difficulty": 5},
     "search_intent_info": {"main_intent": "informational"}},
]
SHARED = [f"https://site{i}.com/a" for i in range(10)]


def serp_for(task):
    urls = SHARED if "facebook" in task["keyword"] else [f"https://other{i}.com" for i in range(10)]
    return dfs_reply({"items": [{"type": "organic", "rank_group": i + 1, "url": u, "title": "t", "domain": u} for i, u in enumerate(urls)]
                      + [{"type": "people_also_ask"}]})


class DataForSEOTests(unittest.TestCase):
    def test_parses_ideas_and_tracks_cost(self):
        c = FakeDFS({"dataforseo_labs": dfs_reply({"items": IDEAS}, cost=0.05)})
        ideas = c.keyword_ideas(["x"])
        self.assertEqual(ideas[0], {"keyword": "facebook ads not getting sales", "volume": 320, "cpc": 0.4, "kd": 12, "intent": "informational"})
        self.assertAlmostEqual(c.spent, 0.05)
        self.assertEqual(c.sent[0][1]["location_code"], 2356)

    def test_cap_stops_calls(self):
        c = FakeDFS({"serp": serp_for}, cap=0.02)
        c.serp("a"), c.serp("b")
        with self.assertRaises(dataforseo.BudgetExceeded):
            c.serp("c")

    def test_error_status_raises_and_no_login(self):
        with self.assertRaises(dataforseo.DataForSEOError):
            FakeDFS({"serp": dfs_reply({}, status=40501)}).serp("a")
        with self.assertRaises(dataforseo.DataForSEOError):
            dataforseo.Client(env={}).serp("a")

    def test_llm_answer(self):
        res = {"model_name": "gpt-4.1-2025", "items": [{"type": "message", "sections": [
            {"text": "Try Digital Tushar Joshi in Rajkot.", "annotations": [{"url": "https://digitaltusharjoshi.com/"}, {"url": "https://clutch.co/x"}]}]}]}
        c = FakeDFS({"ai_optimization": dfs_reply(res)})
        out = aeo_probe.ask_dfs("q", c, "chat_gpt", "Rajkot")
        self.assertTrue(out["dtj_named"] and out["dtj_cited"])
        self.assertEqual(c.sent[0][1]["web_search_city"], "Rajkot")
        self.assertTrue(c.sent[0][0].startswith("ai_optimization/chat_gpt/llm_responses/live"))


class KeywordTests(unittest.TestCase):
    def test_filters(self):
        seeds = gates.load_json("seeds.json")
        verdict = {k["keyword"]: keywords.keep({"keyword": k["keyword"], "volume": k["keyword_info"]["search_volume"], "cpc": k["keyword_info"]["cpc"],
                                                "kd": k["keyword_properties"]["keyword_difficulty"], "intent": k["search_intent_info"]["main_intent"]}, seeds)
                   for k in IDEAS}
        self.assertTrue(verdict["digital marketing agency in rajkot"][0])
        self.assertEqual(verdict["digital marketing course"][1], "off-topic word")
        self.assertIn("difficulty", verdict["seo agency in india"][1])
        self.assertEqual(verdict["shopify store no sales"][1], "nobody pays for this click")

    def test_city_floor_is_lower(self):
        seeds = gates.load_json("seeds.json")
        self.assertTrue(keywords.keep({"keyword": "meta ads agency in ahmedabad", "volume": 20, "cpc": 1, "kd": 5, "intent": "commercial"}, seeds)[0])
        self.assertFalse(keywords.keep({"keyword": "meta ads agency", "volume": 20, "cpc": 1, "kd": 5, "intent": "commercial"}, seeds)[0])

    def test_plan_groups_by_shared_results(self):
        c = FakeDFS({"dataforseo_labs": dfs_reply({"items": IDEAS}), "serp": serp_for})
        plan = keywords.build_plan(c, now=NOW)
        tide = [cl for cl in plan["clusters"] if cl["type"] == "tide"]
        self.assertEqual(len(tide), 1)
        self.assertEqual(tide[0]["keywords"], ["facebook ads not getting sales", "facebook ads no sales"])
        boat = next(cl for cl in plan["clusters"] if cl["type"] == "boat")
        self.assertEqual((boat["place"], boat["service"]), ("Rajkot", "performance-marketing"))
        self.assertEqual(plan["kept"], 3)
        self.assertGreater(plan["cost_usd"], 0)
        self.assertEqual(keywords.plan_age_days(plan, NOW), 0)


class SkeletonTests(unittest.TestCase):
    COMP = "<html><title>Why ads fail</title><h1>Why your ads get no orders</h1><h2>Is it the page?</h2><p>" + \
           "the quick brown fox jumps over the lazy dog near the river bank today " * 3 + "</p></html>"

    def test_outline_skips_directories_and_keeps_text_private(self):
        def serp(task):
            return dfs_reply({"items": [{"type": "organic", "rank_group": 1, "url": "https://www.quora.com/x"},
                                        {"type": "organic", "rank_group": 2, "url": "https://blog.example.com/a"}]})
        sk = serp_skeleton.build(FakeDFS({"serp": serp}), "ads no orders", "Rajkot",
                                 fetch=fetcher({"https://blog.example.com/a": (200, "text/html", self.COMP)}))
        self.assertEqual([p["url"] for p in sk["pages"]], ["https://blog.example.com/a"])
        self.assertIn("h2: Is it the page?", sk["pages"][0]["outline"])
        self.assertNotIn("_fingerprint", serp_skeleton.for_model(sk))
        self.assertNotIn("quick brown", json.dumps(serp_skeleton.for_model(sk)))

    def test_place_falls_back_to_india(self):
        calls = []

        def serp(task):
            calls.append(task)
            return dfs_reply({}, status=40501) if "location_name" in task else dfs_reply({"items": []})
        sk = serp_skeleton.build(FakeDFS({"serp": serp}), "k", "Rajkot", fetch=fetcher({}))
        self.assertEqual(calls[0]["location_name"], "Rajkot,Gujarat,India")
        self.assertIn("used India", sk["note"])

    def test_copy_check_blocks_copied_sentences(self):
        fp = serp_skeleton.shingles("the quick brown fox jumps over the lazy dog near the river bank today")
        a = good_article()
        a["sections"][0]["paragraphs"].append("The quick brown fox jumps over the lazy dog near the river bank today.")
        self.assertTrue(any("copied" in b for b in gates.check(a, fingerprint=fp).blocks))
        self.assertTrue(gates.check(good_article(), fingerprint=fp).ok)


def proof_with_client(city="Rajkot"):
    p = gates.load_json("local_proof.json")
    p["cities"][city]["clients"] = [{"name": "Brand R", "result": "₹12L → ₹48L in sales (the brand's own Shopify sales report)",
                                     "service": "performance-marketing", "consent": True, "source": "test"}]
    return p


class CityTests(unittest.TestCase):
    def test_no_proof_no_page(self):
        seeds, proof = gates.load_json("seeds.json"), gates.load_json("local_proof.json")
        rows = city_page.matrix(seeds, proof, None, set())
        self.assertEqual({r["status"] for r in rows}, {"needs proof"})
        self.assertIsNone(city_page.next_city_page(rows))
        self.assertFalse(city_page.proof_ok({"office": None, "clients": [{"result": "x", "consent": True}], "reviews": [], "photos": []})[0])
        self.assertFalse(city_page.proof_ok({"office": {"address": "a"}, "clients": [{"result": "x", "consent": False}]})[0])

    def test_ready_with_proof_and_plan_order(self):
        seeds = gates.load_json("seeds.json")
        plan = {"clusters": [{"type": "boat", "place": "Rajkot", "service": "shopify-development", "keywords": ["shopify developer in rajkot"],
                              "volume_sum": 40, "priority": 99.0}]}
        rows = city_page.matrix(seeds, proof_with_client(), plan, set())
        nxt = city_page.next_city_page(rows)
        self.assertEqual((nxt["city"], nxt["service"]), ("Rajkot", "shopify-development"))
        local = city_page.local_for_model("Rajkot", proof_with_client(), "performance-marketing")
        self.assertEqual(local["clients"][0]["name"], "Brand R")

    def test_local_numbers_allowed_only_on_that_page(self):
        local = city_page.local_for_model("Rajkot", proof_with_client(), "performance-marketing")
        a = good_article()
        a["sections"][1]["paragraphs"].append("Brand R went from ₹12L to ₹48L in sales.")
        self.assertFalse(gates.check(a).ok)
        from seo_engine import writer
        self.assertTrue(gates.check(a, kind="city", extra_facts=writer.local_lines(local)).ok, gates.check(a, kind="city", extra_facts=writer.local_lines(local)).blocks)

    def test_doorway_pages_blocked(self):
        text = gates.article_text(good_article())
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "seo-agency-in-rajkot.txt").write_text(text, encoding="utf-8")
            similar, score, other = city_page.too_similar(text.replace("first", "Ahmedabad"), Path(tmp))
        self.assertTrue(similar)
        self.assertEqual(other, "seo-agency-in-rajkot")
        self.assertLess(gates.similarity("one two three four five six seven", "alpha beta gamma delta epsilon zeta eta"), 0.01)


def scan_result():
    return site_scan.scan(SITE, fetcher(site_pages()), delay=0, now=NOW)


class FixerTests(unittest.TestCase):
    def test_dry_run_batch(self):
        b = fixer.propose(scan_result(), now=NOW)
        kinds = [c["kind"] for c in b["changes"]]
        self.assertIn("noindex", kinds)
        self.assertNotIn("meta_description", kinds)  # needs the API key
        self.assertTrue(any("need a new title or description" in n for n in b["notes"]))
        self.assertTrue(any(c["kind"] == "manual" and c.get("rule") == "llms-txt-claim" for c in b["changes"]))
        self.assertEqual(b["id"], "fix-2026-10-14")

    def test_ai_lines_are_checked(self):
        pages = [{"url": f"{SITE}/", "seo_title": "Performance marketing for D2C brands | DTJ",
                  "meta_description": "DTJ is the best agency in India and grows D2C brands with ads, Shopify stores and search. Get a free growth audit of your ads and store today."}]
        resp = NS(stop_reason="end_turn", content=[NS(type="text", text=json.dumps({"pages": pages}))])
        b = fixer.propose(scan_result(), client=FakeClient(resp), now=NOW)
        desc = next(c for c in b["changes"] if c["kind"] == "meta_description")
        self.assertEqual(desc["how"], "blocked")
        self.assertTrue(any("best" in x for x in desc["blocks"]))

    def test_business_details_from_real_offices(self):
        data = fixer.site_jsonld(gates.load_json("local_proof.json"))
        offices = [g for g in data["@graph"] if g["@type"] == "ProfessionalService"]
        self.assertEqual(sorted(o["address"]["addressLocality"] for o in offices), ["Ahmedabad", "Rajkot"])


class ApplyTests(unittest.TestCase):
    ENV = {"AUTOMATION_ENABLED": "1", "SEO_DRY_RUN": "0", "WP_USER": "u", "WP_APP_PASSWORD": "p"}

    def batch(self):
        return {"id": "fix-test", "site": SITE, "changes": [
            {"cid": "c001", "kind": "meta_description", "url": f"{SITE}/", "before": "Old description here", "after": "New plain description",
             "reason": "r", "how": "auto"},
            {"cid": "c002", "kind": "meta_description", "url": f"{SITE}/x/", "before": "Something else", "after": "Another",
             "reason": "r", "how": "auto"},
            {"cid": "c003", "kind": "manual", "url": "x", "before": None, "after": None, "reason": "r", "how": "manual"}]}

    def make_site(self):
        state = {"desc": "Old description here"}

        def fetch(url):
            u = url.split("?")[0]
            if u in (f"{SITE}/", f"{SITE}/x/"):
                d = state["desc"] if u == f"{SITE}/" else "Edited by a person"
                return site_scan.Response(200, url, "text/html", f'<title>T</title><meta name="description" content="{d}"><h1>h</h1>')
            return site_scan.Response(404, url, "", "")
        writes = []

        def wp(req):
            if "resolve" in req.full_url:
                return 200, {"post_id": 5, "post_type": "page", "metadesc": "Old description here", "title": "", "noindex": ""}
            if req.full_url.endswith("/meta"):
                body = json.loads(req.data)
                writes.append(body)
                state["desc"] = body["value"]
                return 200, {"post_id": 5, "field": body["field"], "after": body["value"]}
            return 404, {"code": "rest_no_route"}
        return fetch, wp, writes

    def test_needs_named_approver_and_kill_switch(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", self.ENV):
            with self.assertRaises(SystemExit):
                apply_batch.apply(self.batch(), approved_by=" ", out_dir=Path(tmp) / "b", env=self.ENV)
            with self.assertRaises(SystemExit):
                apply_batch.apply(self.batch(), approved_by="Harsh", out_dir=Path(tmp) / "b", env={**self.ENV, "AUTOMATION_ENABLED": "0"})

    def test_applies_verifies_skips_and_undoes(self):
        fetch, wp, writes = self.make_site()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", self.ENV):
            rec = apply_batch.apply(self.batch(), approved_by="Harsh", out_dir=Path(tmp) / "b", fetch=fetch, opener=wp, env=self.ENV, wait=0)
            self.assertEqual({r["cid"]: r["status"] for r in rec["results"]}, {"c001": "verified", "c002": "skipped"})
            self.assertEqual(writes, [{"post_id": 5, "field": "metadesc", "value": "New plain description"}])
            rows = [json.loads(l) for l in (Path(tmp) / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual((rows[0]["tier"], rows[0]["approved_by"], rows[0]["before"]), (2, "Harsh", "Old description here"))
            self.assertTrue((Path(tmp) / "b" / "applied-fix-test.json").exists())
            undone = apply_batch.undo(rec, approved_by="Harsh", out_dir=Path(tmp) / "b", opener=wp, env=self.ENV)
        self.assertEqual(undone["undone"][0]["status"], "undone")
        self.assertEqual(writes[-1]["value"], "Old description here")

    def test_missing_bridge_is_reported(self):
        fetch, _, _ = self.make_site()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", self.ENV):
            rec = apply_batch.apply(self.batch(), approved_by="Harsh", out_dir=Path(tmp) / "b", fetch=fetch,
                                    opener=lambda req: (404, {"code": "rest_no_route"}), env=self.ENV, wait=0)
        self.assertIn("Bridge plugin is not active", rec["results"][0]["why"])


class RunTests(unittest.TestCase):
    def test_city_week_when_proof_exists(self):
        ok = NS(stop_reason="end_turn", model="claude-opus-5-5", usage=None, content=[NS(type="text", text=json.dumps(good_article()))])
        proof = proof_with_client()
        real = gates.load_json
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(gates, "load_json", side_effect=lambda n: proof if n == "local_proof.json" else real(n)):
            Path(tmp, "state.json").write_text(json.dumps({"written": ["ads-no-orders"], "last_kind": "article"}))
            res = run_weekly.run(live=True, out_root=Path(tmp), max_pages=10, probe_limit=0, fetch=fetcher(site_pages()), client=FakeClient(ok), env={})
            draft = json.loads((Path(res["out"]) / "draft.json").read_text(encoding="utf-8"))
            state = json.loads(Path(tmp, "state.json").read_text())
            self.assertEqual(draft["kind"], "city")
            self.assertEqual(state["last_kind"], "city")
            self.assertTrue(any(Path(tmp, "city-pages").glob("*-in-rajkot.txt")))

    def test_falls_back_to_article_without_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "state.json").write_text(json.dumps({"written": [], "last_kind": "article"}))
            res = run_weekly.run(live=False, out_root=Path(tmp), max_pages=10, probe_limit=1, fetch=fetcher(site_pages()), env={})
        self.assertIn("No city page this week", res["report"])
        self.assertIn("Fixes waiting for one yes", res["report"])


if __name__ == "__main__":
    unittest.main()

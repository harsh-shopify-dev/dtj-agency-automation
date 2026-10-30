"""Tests for the 19 Oct 2026 fix: a child sitemap that fails to load is tried again, and if it still fails the report says the check
was incomplete (a test run that day read 9 of 24 pages without a word)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from seo_engine import report, run_weekly, site_scan
from test_seo_engine import PAGE, SITE, site_pages

NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)
POSTS = f"{SITE}/post-sitemap.xml"
POST = f"{SITE}/why-ads-no-orders/"


def two_sitemaps() -> dict:
    """The test site with a second child sitemap holding one blog post."""
    pages = site_pages()
    pages[f"{SITE}/sitemap_index.xml"] = (200, "text/xml", f"<sitemapindex><sitemap><loc>{SITE}/page-sitemap.xml</loc></sitemap>"
                                                            f"<sitemap><loc>{POSTS}</loc></sitemap></sitemapindex>")
    pages[POSTS] = (200, "text/xml", f"<urlset><url><loc>{POST}</loc><lastmod>2026-10-01T10:00:00+00:00</lastmod></url></urlset>")
    pages[POST] = (200, "text/html", PAGE)
    return pages


class ScriptedFetch:
    """A fake fetcher: each URL answers from its script in order (the last answer repeats); every call is counted."""

    def __init__(self, pages: dict, scripts: dict | None = None):
        self.pages, self.scripts, self.calls = pages, scripts or {}, {}

    def __call__(self, url):
        n = self.calls[url] = self.calls.get(url, 0) + 1
        if url in self.scripts:
            script = self.scripts[url]
            status, ctype, body = script[min(n, len(script)) - 1]
        else:
            status, ctype, body = self.pages.get(url, (404, "", ""))
        return site_scan.Response(status, url, ctype, body)


ERROR_500 = (500, "text/html", "")
TIMEOUT = (0, "", "fetch error: TimeoutError")


def rules(res: dict) -> dict:
    return {f["rule"]: f for f in res["findings"]}


class RetryTests(unittest.TestCase):
    def test_500_once_then_200_reads_every_page(self):
        pages = two_sitemaps()
        fetch = ScriptedFetch(pages, {POSTS: [ERROR_500, pages[POSTS]]})
        res = site_scan.scan(SITE, fetch, delay=0, now=NOW, retry_wait=0)
        self.assertEqual(fetch.calls[POSTS], 2)
        self.assertEqual(res["pages_in_sitemap"], 3)
        self.assertIn(POST, [p["url"] for p in res["pages"]])
        self.assertNotIn("sitemap-unreadable", rules(res))
        self.assertTrue(res["coverage"]["complete"])

    def test_waits_longer_each_time(self):
        fetch = ScriptedFetch(two_sitemaps(), {POSTS: [ERROR_500]})
        with mock.patch.object(site_scan.time, "sleep") as slept:
            site_scan.read_sitemaps(SITE, fetch, wait=2.0)
        self.assertEqual([c.args[0] for c in slept.call_args_list], [2.0, 4.0])  # 3 tries, so 2 waits

    def test_always_failing_sitemap_is_a_high_finding(self):
        fetch = ScriptedFetch(two_sitemaps(), {POSTS: [ERROR_500]})
        res = site_scan.scan(SITE, fetch, delay=0, now=NOW, retry_wait=0)
        self.assertEqual(fetch.calls[POSTS], site_scan.SITEMAP_TRIES)
        f = rules(res)["sitemap-unreadable"]
        self.assertEqual((f["severity"], f["page"]), ("high", POSTS))
        self.assertEqual(f["evidence"], "HTTP 500 after 3 tries")
        self.assertEqual(res["findings"][0]["severity"], "high")
        self.assertEqual(res["pages_in_sitemap"], 2)  # the other sitemap's pages are still checked
        self.assertFalse(res["coverage"]["complete"])
        self.assertEqual(res["coverage"]["unreadable_sitemaps"], [{"url": POSTS, "status": 500, "tries": 3, "why": "HTTP 500"}])

    def test_timeouts_and_rate_limits_are_retried_404_is_not(self):
        pages = two_sitemaps()
        fetch = ScriptedFetch(pages, {POSTS: [TIMEOUT, (429, "", ""), pages[POSTS]]})
        urls, problems = site_scan.read_sitemaps(SITE, fetch, wait=0)
        self.assertEqual((fetch.calls[POSTS], len(urls), problems), (3, 3, []))
        fetch = ScriptedFetch(pages, {POSTS: [(404, "", "")]})
        urls, problems = site_scan.read_sitemaps(SITE, fetch, wait=0)
        self.assertEqual((fetch.calls[POSTS], len(urls)), (1, 2))
        self.assertEqual(problems[0]["why"], "HTTP 404")

    def test_no_sitemap_at_all_is_reported(self):
        fetch = ScriptedFetch({}, {f"{SITE}/sitemap_index.xml": [ERROR_500]})
        urls, problems = site_scan.read_sitemaps(SITE, fetch, wait=0)
        self.assertEqual(urls, [])
        self.assertEqual([p["url"] for p in problems], [f"{SITE}/sitemap_index.xml"])
        urls, problems = site_scan.read_sitemaps(SITE, ScriptedFetch({}), wait=0)  # 404 everywhere
        self.assertEqual(len(problems), 1)


class CoverageTests(unittest.TestCase):
    def test_far_fewer_pages_than_last_time(self):
        res = site_scan.scan(SITE, ScriptedFetch(two_sitemaps()), delay=0, now=NOW, retry_wait=0, previous_pages=24)
        self.assertTrue(res["coverage"]["fewer_than_before"])
        self.assertFalse(res["coverage"]["complete"])
        text = "\n".join(report.coverage_warning(res["coverage"]))
        self.assertIn("Only 3 pages were read; the last complete check read 24", text)

    def test_a_small_change_is_not_flagged(self):
        res = site_scan.scan(SITE, ScriptedFetch(two_sitemaps()), delay=0, now=NOW, retry_wait=0, previous_pages=4)
        self.assertTrue(res["coverage"]["complete"])
        self.assertEqual(report.coverage_warning(res["coverage"]), [])

    def test_previous_pages_from_saved_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for day, pages, bad in (("2026-10-12", 24, []), ("2026-10-19", 9, [{"url": POSTS}])):
                (root / day).mkdir()
                (root / day / "scan.json").write_text(json.dumps({"pages_in_sitemap": pages, "coverage": {"unreadable_sitemaps": bad}}))
            self.assertEqual(run_weekly.previous_pages(root, {}), 24)  # the incomplete 9-page check is not the yardstick
            self.assertEqual(run_weekly.previous_pages(root, {"last_complete_pages": 22}), 22)
            self.assertIsNone(run_weekly.previous_pages(root / "empty", {}))


class WeeklyRunTests(unittest.TestCase):
    def test_lost_sitemap_shows_in_the_report_and_keeps_the_yardstick(self):
        pages = two_sitemaps()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(site_scan.time, "sleep"):
            run_weekly.run(live=False, out_root=Path(tmp), probe_limit=0, fetch=ScriptedFetch(pages), env={})
            state_path = Path(tmp) / "state.json"
            self.assertEqual(json.loads(state_path.read_text())["last_complete_pages"], 3)

            res = run_weekly.run(live=False, out_root=Path(tmp), probe_limit=0, fetch=ScriptedFetch(pages, {POSTS: [ERROR_500]}), env={})
            md = res["report"]
            self.assertIn("**This check is incomplete.**", md)
            self.assertIn(f"{POSTS}: HTTP 500 after 3 tries", md)
            self.assertIn("| Fix now | sitemap-unreadable |", md)
            self.assertEqual(json.loads(state_path.read_text())["last_complete_pages"], 3)  # not lowered by the broken check
            rows = [json.loads(l) for l in (Path(tmp) / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
            scan_row = [r for r in rows if r["action"] == "site scan"][-1]
            self.assertFalse(scan_row["evidence"]["complete"])
            self.assertEqual(scan_row["evidence"]["unreadable_sitemaps"], [POSTS])

    def test_complete_check_has_no_warning(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(site_scan.time, "sleep"):
            res = run_weekly.run(live=False, out_root=Path(tmp), probe_limit=0, fetch=ScriptedFetch(two_sitemaps()), env={})
        self.assertNotIn("incomplete", res["report"])


if __name__ == "__main__":
    unittest.main()

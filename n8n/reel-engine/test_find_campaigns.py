"""The campaign finder's code nodes in Node with a stand-in Apify answer, and its generated workflow.

    python -m unittest n8n/reel-engine/test_find_campaigns.py
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deploy_find_campaigns as dep  # noqa: E402


def run(js_file: str, item: dict, plan: dict | None = None):
    body = (HERE / js_file).read_text(encoding="utf-8")
    prog = ("const $input = { first: () => ({ json: " + json.dumps(item) + " }) };\n"
            "const $ = () => ({ first: () => ({ json: " + json.dumps(plan or {}) + " }) });\n"
            "const out = (() => {\n" + body + "\n})();\nconsole.log(JSON.stringify(out));")
    p = subprocess.run(["node", "-e", prog], capture_output=True, text=True, encoding="utf-8")
    return (None, p.stderr) if p.returncode else (json.loads(p.stdout)[0]["json"], "")


def reel(user, views, caption="Diwali gifting #diwali", days=5, **kw):
    t = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return {"url": f"https://www.instagram.com/reel/{user}{views}/", "videoUrl": f"https://cdn.example/{user}{views}.mp4", "caption": caption,
            "videoPlayCount": views, "likesCount": views // 10, "commentsCount": 3, "ownerUsername": user, "ownerFullName": user.title(),
            "timestamp": t, "productType": "clips", **kw}


PLAN = {"niche": "watches", "count": 3, "days": 60}


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Plan(unittest.TestCase):
    def test_searches_diwali_tags_for_the_niche(self):
        j, _ = run("find_plan.js", {"niche": "Watches", "count": "3"})
        self.assertEqual(j["actor"], "apify/instagram-hashtag-scraper")
        self.assertIn("diwaliwatches", j["input"]["hashtags"])
        self.assertEqual(j["input"]["resultsType"], "reels")
        self.assertEqual((j["count"], j["niche"]), (3, "watches"))
        self.assertEqual(run("find_plan.js", {"niche": "watches"})[0]["days"], 400)
        self.assertLessEqual(j["max_usd"], 0.30)
        self.assertLessEqual(j["max_items"], 100)

    def test_count_is_capped_and_defaults(self):
        self.assertEqual(run("find_plan.js", {"niche": "tea", "count": "99"})[0]["count"], 15)
        self.assertEqual(run("find_plan.js", {"niche": "tea"})[0]["count"], 10)

    def test_two_word_niche_makes_one_tag(self):
        self.assertIn("diwalidryfruits", run("find_plan.js", {"niche": "dry fruits"})[0]["input"]["hashtags"])

    def test_no_niche_is_refused(self):
        out, err = run("find_plan.js", {"niche": " "})
        self.assertIsNone(out)
        self.assertIn("niche", err)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Read(unittest.TestCase):
    def read(self, items, status=200, plan=PLAN):
        return run("find_read.js", {"statusCode": status, "body": items}, plan)[0]

    def test_top_by_views_one_per_account(self):
        j = self.read([reel("a", 100), reel("a", 900), reel("b", 500), reel("c", 700), reel("d", 50)])
        self.assertEqual([r["username"] for r in j["results"]], ["a", "c", "b"])
        self.assertEqual(j["results"][0]["views"], 900)
        self.assertTrue(j["results"][0]["video_url"].endswith(".mp4"))

    def test_only_recent_diwali_reels(self):
        j = self.read([reel("old", 900, days=200), reel("off", 800, caption="New watch drop"), reel("ok", 10, caption="दीवाली special"),
                       reel("img", 700, productType="feed", videoUrl=None)])
        self.assertEqual([r["username"] for r in j["results"]], ["ok"])

    def test_html_lists_results_and_escapes_captions(self):
        j = self.read([reel("a", 100, caption="Diwali <script>x</script> & more")])
        self.assertIn("&lt;script&gt;", j["html"])
        self.assertNotIn("<script>", j["html"])
        self.assertIn("https://www.instagram.com/reel/a100/", j["html"])

    def test_niche_and_brand_reels_beat_viral_comedy(self):
        j = self.read([reel("meme", 9000000, caption="Diwali comedy 😂"), reel("viral", 5000000, caption="Happy Diwali vibes"),
                       reel("adfilm", 900, caption="Our new Diwali campaign film"), reel("store", 50, caption="Diwali watches for you #watch"),
                       reel("big", 40000, caption="Diwali gift: a Titan watch")])
        self.assertEqual([r["username"] for r in j["results"]], ["big", "store", "adfilm"])

    def test_nothing_found_says_so(self):
        j = self.read([reel("off", 800, caption="no festival here")])
        self.assertEqual(j["results"], [])
        self.assertIn("Nothing", j["html"])

    def test_apify_error_says_so(self):
        j = self.read({"error": {"message": "token invalid"}}, status=401)
        self.assertEqual(j["results"], [])
        self.assertIn("401", j["html"])

    def test_a_missing_view_count_still_counts_as_zero(self):
        r = reel("a", 100)
        del r["videoPlayCount"]
        self.assertEqual(self.read([r])["results"][0]["views"], 0)


class Generated(unittest.TestCase):
    def test_has_the_apify_node_and_a_note_on_every_node(self):
        code = dep.workflow_code()
        self.assertIn('"Find on Instagram (Apify)"', code)
        self.assertIn("DTJ Apify", code)
        names = re.findall(r"config: \{ name: (\"[^\"]+\"|'[^']+')", code)
        notes = re.findall(r"notes: (\"(?:[^\"\\]|\\.)*\"|'[^']*')", code)
        self.assertEqual(len(notes), len(names), names)
        self.assertGreaterEqual(len(names), 4)


if __name__ == "__main__":
    unittest.main()

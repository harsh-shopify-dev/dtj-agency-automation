"""The code nodes of "WATFEO Ads: New Ad" run in Node exactly as n8n runs them (../store-factory/node_harness.py).

    python -m unittest discover -s n8n/watfeo-ads -t n8n/watfeo-ads
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))
from node_harness import HAS_NODE  # noqa: E402
from node_harness import run_node as _run  # noqa: E402

RESUME = "https://n8n.srv2048145.hstgr.cloud/webhook-waiting/700?signature=ef56"
FORM = {"kind": "Full reel", "language": "Hinglish", "count": "1", "angle": "", "reference": "", "notes": "", "requested_by": "Harsh"}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Nodes(unittest.TestCase):
    def run_node(self, name, given, refs=None):
        return _run(HERE / name, given, {"__resume": RESUME, **(refs or {})})

    def test_a_form_becomes_a_new_job(self):
        row = self.run_node("take_watfeo_request.js", FORM)["out"][0]["json"]["row"]
        self.assertEqual((row["status"], row["kind"], row["language"], row["count"], row["angle_asked"]), ("new", "reel", "hinglish", 1, None))

    def test_bad_requests_are_refused_with_reasons(self):
        out = self.run_node("take_watfeo_request.js", {**FORM, "kind": "Scripts only", "angle": "77", "count": "9",
                                                       "language": "French"})["out"][0]["json"]
        self.assertFalse(out["ok"])
        for why in ("language must be", "1 to 58", "between 1 and 5"):
            self.assertIn(why, out["problems"])
        self.assertIn("at most 2 full reels", self.run_node("take_watfeo_request.js", {**FORM, "count": "3"})["out"][0]["json"]["problems"])

    def test_the_request_lists_the_teams_used_angles_and_the_skill(self):
        job = {"id": 9, "kind": "scripts", "language": "en", "count": 3, "angle_asked": 13, "requested_by": "Harsh"}
        earlier = [{"id": 3, "angle_used": 46}, {"id": 5, "angle_used": 56}, {"id": 7, "angle_used": None}, job]
        out = self.run_node("request_watfeo.js", earlier, {"Save WATFEO Ad": job})["out"][0]["json"]
        t = out["instructions"]
        for must in ("watfeo-ugc-ads", "already used (count them as used): 46, 56", "#13 (asked for", ".work/watfeo/watfeo-9/",
                     f'reply.py --resume-url "{RESUME}" --body .work/watfeo/watfeo-9/result.json', '"kind": "scripts"', "the saved .md file",
                     "reserved", "Nothing is posted"):
            self.assertIn(must, t)
        self.assertEqual(out["request"]["angles_used"], [46, 56])

    def reply(self, body):
        refs = {"Request for Claude Code: WATFEO Ad": {"request": {"job_id": 9}}}
        return self.run_node("reply_watfeo.js", {} if body is None else {"body": body}, refs)["out"][0]["json"]

    def test_the_reply_records_the_angle_and_checks_the_file_type(self):
        got = self.reply({"reel_status": "reel ready", "kind": "scripts", "final_path": "D:\\x\\scripts.md", "angle": 13, "note": "3 scripts"})
        self.assertEqual((got["row_id"], got["ad_status"], got["angle_used"]), (9, "reel ready", 13))
        self.assertEqual(self.reply({"reel_status": "reel ready", "kind": "reel", "final_path": "x.md", "angle": 13})["ad_status"],
                         "reply not understood (no final file)")
        self.assertIsNone(self.reply({"reel_status": "could not make", "angle": 13, "note": "needs a person: Google sign-in"})["angle_used"])
        self.assertEqual(self.reply(None)["ad_status"], "timed out (no reply in 3 days)")

    def test_only_telegram_jobs_get_a_message(self):
        r = {"ad_status": "reel ready", "final_path": "a<b>.mp4", "angle_used": 13}
        self.assertEqual(self.run_node("tell_watfeo_requester.js", r, {"Save WATFEO Ad": {"kind": "reel"}})["out"], [])
        msg = self.run_node("tell_watfeo_requester.js", r, {"Save WATFEO Ad": {"kind": "reel", "telegram_chat_id": "5"}})["out"][0]["json"]
        self.assertIn("angle #13", msg["text"]); self.assertIn("a&lt;b&gt;.mp4", msg["text"])


if __name__ == "__main__":
    unittest.main()

"""The code nodes of "Reel Factory: New Reel" run in Node exactly as n8n runs them (../store-factory/node_harness.py). The .js files
are the source of truth: deploy_reel.py sends them to n8n byte for byte.

    python -m unittest discover -s n8n/reel-factory -t n8n/reel-factory
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))
from node_harness import HAS_NODE  # noqa: E402
from node_harness import run_node as _run  # noqa: E402

RESUME = "https://n8n.srv2048145.hstgr.cloud/webhook-waiting/412?signature=cd34"
FORM = {"product_name": "Senso Instant Detox Green Tea Kahwa", "brand_name": "Senso",
        "product_images": "https://cdn.shopify.com/s/files/senso-box.png\n", "reference_reels": "https://example.com/ref1.mp4\r\nhttps://example.com/ref2.mp4",
        "language": "English", "music": "", "facts": "Just add hot water. 3g x 10 Sachets.", "notes": "", "requested_by": "Harsh"}


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Nodes(unittest.TestCase):
    def run_node(self, name, given, refs=None):
        return _run(HERE / name, given, {"__resume": RESUME, **(refs or {})})

    # ---- Take the Reel Request
    def test_a_complete_form_becomes_a_new_job(self):
        out = self.run_node("take_reel_request.js", FORM)["out"][0]["json"]
        self.assertTrue(out["ok"], out)
        row = out["row"]
        self.assertEqual((row["status"], row["language"], row["requested_by"]), ("new", "en", "Harsh"))
        self.assertEqual(row["reference_reels"].split("\n"), ["https://example.com/ref1.mp4", "https://example.com/ref2.mp4"])
        self.assertIn("Senso", json.loads(row["raw_json"])["product_name"])   # the raw answers are kept

    def test_labels_work_too_and_bad_input_is_refused_with_reasons(self):
        out = self.run_node("take_reel_request.js", {"Product name": "X", "Language": "Klingon",
                                                     "Product pictures (links, one per line)": "http://insecure.example/a.png"})["out"][0]["json"]
        self.assertFalse(out["ok"])
        self.assertEqual(out["row"]["status"], "refused")
        for why in ("no reference reel", "language must be", "no approved facts", "not a https link"):
            self.assertIn(why, out["problems"])
        self.assertEqual(self.run_node("take_reel_request.js", {**FORM, "language": "Gujarati"})["out"][0]["json"]["row"]["language"], "gu")

    def test_a_remake_from_the_reel_bot(self):
        # /remake: one reference, a bot photo, no language and no facts (music only); the form default stays a UGC reel
        given = {"reel_type": "remake", "product_name": "Mahalaxmi Garam Masala", "product_images": "tg:AgACAgUAAxkBAAIB12345",
                 "reference_reels": "https://www.instagram.com/reel/DZhYs5wu_n3/", "requested_by": "Harsh", "chat_id": "7051933055",
                 "audience": "Gujarati home cooks 30-50"}
        out = self.run_node("take_reel_request.js", given)["out"][0]["json"]
        self.assertTrue(out["ok"], out)
        self.assertEqual((out["row"]["reel_type"], out["row"]["language"], out["row"]["audience"]), ("remake", "none", "Gujarati home cooks 30-50"))
        two = self.run_node("take_reel_request.js", {**given, "reference_reels": "https://a.com/1.mp4\nhttps://a.com/2.mp4"})["out"][0]["json"]
        self.assertIn("exactly one reference", two["problems"])
        self.assertEqual(self.run_node("take_reel_request.js", FORM)["out"][0]["json"]["row"]["reel_type"], "ugc")
        row = {**out["row"], "id": 9}
        text = self.run_node("request_reel.js", row)["out"][0]["json"]["instructions"]
        for must in ("REMAKE ONE REFERENCE EDIT", "remake-a-reference-edit.md", "reel.sh remake reference", "measure_motion",
                     "clean_brand", "codex_image.sh", "watcher.sh g1", "watcher.sh g2", "watcher.sh g3", "watcher.sh g4", "watcher.sh g5",
                     'plan --file', "--watch", "DTJ_WAIT:", "reel_job.py photos --job r9", '"move": "ref"', 'label ""',
                     "own soundtrack", "--chat \"7051933055\""):
            self.assertIn(must, text)

    # ---- Request for Claude Code: Reel
    def test_the_request_is_a_complete_task_list_for_a_fresh_session(self):
        row = {**self.run_node("take_reel_request.js", FORM)["out"][0]["json"]["row"], "id": 7}
        out = self.run_node("request_reel.js", row)["out"][0]["json"]
        text = out["instructions"]
        J = "/home/ai/dtj-agency-automation/.work/reels/n8n-7-senso-instant-detox-green-tea-kahwa"
        for must in ("dtj-ugc-reel", "dtj-reel-watcher", f"bash tools/vps/reel.sh job new --job {J}", "reel.sh job lint",
                     "reel.sh slop", "reel.sh job clips", "watcher.sh g1", "watcher.sh g4", "reel_job.py start --job r7",
                     f'reply.py --resume-url "{RESUME}" --body {J}/result.json',
                     "Just add hot water", "Never invent", "Nothing is posted", ".work/handoff/"):
            self.assertIn(must, text)
        self.assertEqual(out["request"]["reference_reels"], ["https://example.com/ref1.mp4", "https://example.com/ref2.mp4"])
        self.assertEqual(out["resume_url"], RESUME)
        self.assertEqual(out["job_folder"], J)

    def test_no_row_stops(self):
        self.assertFalse(self.run_node("request_reel.js", {})["ok"])

    # ---- Claude Code Reply: Reel (the same rules as reply.py's "reel" stage)
    def reply(self, body):
        refs = {"Request for Claude Code: Reel": {"request": {"job_id": 7}}}
        return self.run_node("reply_reel.js", {} if body is None else {"body": body}, refs)["out"][0]["json"]

    def test_the_reply_records_a_ready_reel_and_refuses_half_answers(self):
        good = {"reel_status": "reel ready", "final_path": "D:\\reels\\n8n-7\\final\\reel_final.mp4", "duration_s": 26.5, "lufs": -14.0,
                "generations": 8, "credits_used": 112, "note": ""}
        got = self.reply(good)
        self.assertEqual((got["row_id"], got["reel_status"], got["duration_s"], got["credits_used"]), (7, "reel ready", 26.5, 112))
        self.assertEqual(self.reply({**good, "final_path": ""})["reel_status"], "reply not understood (no final file)")
        self.assertEqual(self.reply({**good, "lufs": 5})["lufs"], None)
        self.assertEqual(self.reply({"reel_status": "could not make", "note": "needs a person: Google sign-in"})["reel_note"],
                         "needs a person: Google sign-in")
        self.assertEqual(self.reply(None)["reel_status"], "timed out (no reply in 3 days)")

    # ---- Tell the Requester
    def test_only_telegram_jobs_get_a_message(self):
        r = {"reel_status": "reel ready", "duration_s": 26.5, "final_path": "/r/a<b>.mp4"}
        self.assertEqual(self.run_node("tell_reel_requester.js", r, {"Save Reel Job": {"product_name": "X"}})["out"], [])
        msg = self.run_node("tell_reel_requester.js", r, {"Save Reel Job": {"product_name": "X", "telegram_chat_id": "55"}})["out"][0]["json"]
        self.assertEqual(msg["chat_id"], "55")
        self.assertIn("/r/a&lt;b&gt;.mp4", msg["text"])
        self.assertIn("Nothing was posted", msg["text"])


if __name__ == "__main__":
    unittest.main()

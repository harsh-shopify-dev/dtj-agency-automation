"""Tests for reel_job.py (the reel's Telegram approvals) with a fake Telegram and a fake answers table.

    python -m unittest n8n/reel-factory/test_reel_job.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reel_job  # noqa: E402


class FakeBot:
    def __init__(self):
        self.sent, self.rows, self.next_id = [], [], 1

    def send(self, method, data):
        self.sent.append((method, data))
        self.next_id += 1
        return {"message_id": self.next_id}

    def tap(self, job, key, choice, value, by="Harsh", at="2099-01-01T00:00:00"):
        self.rows.append({"id": len(self.rows) + 1, "job": job, "key": key, "choice": str(choice), "value": value, "by": by,
                          "chat_id": "100", "at": at})


class FakeMedia:
    def __init__(self):
        self.albums, self.videos = [], []

    def album(self, tok, chat, files, captions):
        self.albums.append([f.name for f in files])
        return [{}] * len(files)

    def video(self, tok, chat, path, caption=""):
        self.videos.append(path.name)
        return {"message_id": 9}


class Progress:
    def start(self, chat, title):
        return "progress bar: started"

    def step(self, *a):
        return "step"

    def finish(self, ok, note=""):
        return "done" if ok else "stopped"


def job(tmp, bot, media=None, out=None):
    return reel_job.ReelJob("r42", send=bot.send, rows=lambda j: [r for r in bot.rows if r["job"] == j], add_row=lambda r: None,
                            media=media or FakeMedia(), progress=Progress(), state_dir=Path(tmp), out=(out if out is not None else []).append,
                            sleep=lambda s: None, clock=iter(range(0, 10 ** 6, 1000)).__next__, log=lambda row: None)


class ReelJobTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bot = FakeBot()
        self.out = []
        j = job(self.tmp, self.bot, out=self.out)
        j.start("100", "Reel: Mahalaxmi")

    def j(self, media=None):
        return job(self.tmp, self.bot, media, self.out)

    def test_plan_waits_then_approves_once(self):
        plan = Path(self.tmp) / "plan.md"
        plan.write_text("1. two boxes\n2. one box", encoding="utf-8")
        self.assertEqual(self.j().plan(plan, 1, 0.1), reel_job.WAITING)
        texts = [d.get("text", "") for m, d in self.bot.sent]
        self.assertTrue(any("two boxes" in t for t in texts))
        self.assertEqual(self.j().plan(plan, 1, 0.1), reel_job.WAITING)        # asked again: nothing sent twice
        self.assertEqual(sum("two boxes" in d.get("text", "") for m, d in self.bot.sent), 1)
        self.bot.tap("r42", "plan1", 0, "Approve")
        self.assertEqual(self.j().plan(plan, 1, 0.1), 0)
        self.assertEqual(json.loads(self.out[-1]), {"ok": True, "by": "Harsh"})

    def test_change_something_asks_what(self):
        media = FakeMedia()
        d = Path(self.tmp) / "images"
        d.mkdir()
        for n in ("p01.png", "p02.png"):
            (d / n).write_bytes(b"x")
        self.assertEqual(self.j(media).pictures(d, [], 1, 0.1), reel_job.WAITING)
        self.assertEqual(media.albums, [["p01.png", "p02.png"]])
        self.bot.tap("r42", "pictures1", 1, "Change something")
        self.assertEqual(self.j(media).pictures(d, [], 1, 0.1), reel_job.WAITING)   # now waits for the typed note
        self.bot.tap("r42", "pictures1n", "", "2: the box is too small")
        self.assertEqual(self.j(media).pictures(d, [], 1, 0.1), 0)
        self.assertEqual(json.loads(self.out[-1])["note"], "2: the box is too small")
        self.assertEqual(len(media.albums), 1)                                      # shown once only

    def test_final_sends_the_video(self):
        media = FakeMedia()
        f = Path(self.tmp) / "reel.mp4"
        f.write_bytes(b"x")
        self.bot.tap("r42", "final2", 0, "Approve", by="Asha")
        self.assertEqual(self.j(media).final(f, 2, 0.1), 0)
        self.assertEqual(media.videos, ["reel.mp4"])
        self.assertEqual(json.loads(self.out[-1])["by"], "Asha")

    def test_old_taps_do_not_count(self):
        plan = Path(self.tmp) / "plan.md"
        plan.write_text("x", encoding="utf-8")
        self.bot.tap("r42", "plan1", 0, "Approve", at="2000-01-01T00:00:00")       # from before the question was sent
        self.assertEqual(self.j().plan(plan, 1, 0.1), reel_job.WAITING)


class WatcherTest(ReelJobTest):
    def verdict(self, v):
        p = Path(self.tmp) / "g2.verdict.json"
        p.write_text(json.dumps(v), encoding="utf-8")
        return p

    def test_card_comes_first_and_block_is_refused(self):
        d = Path(self.tmp) / "imgs"
        d.mkdir()
        (d / "p01.png").write_bytes(b"x")
        j = self.j()
        j.watch = self.verdict({"gate": "g2", "round": 1, "verdict": "block", "blocking": [{"item": "picture 1", "issue": "Ramdev logo"}]})
        self.assertEqual(j.pictures(d, [], 1, 0.1), 2)
        self.assertFalse(any("Watcher" in dd.get("text", "") for m, dd in self.bot.sent))   # nothing shown to the person
        j = self.j()
        j.watch = self.verdict({"gate": "g2", "round": 1, "verdict": "pass", "score": 91, "ideas": [{"idea": "add a pack close-up"}]})
        self.assertEqual(j.pictures(d, [], 1, 0.1), reel_job.WAITING)
        texts = [dd.get("text", "") for m, dd in self.bot.sent]
        self.assertTrue(any(t.startswith("Watcher (G2, round 1): PASS, 91/100") for t in texts))


class MediaTest(unittest.TestCase):
    def test_album_groups_of_ten(self):
        import tg_media
        calls = []

        def post(url, body, kind):
            calls.append(url.rsplit("/", 1)[-1])
            return 200, {"ok": True, "result": [{}] * 10}
        files = []
        tmp = Path(tempfile.mkdtemp())
        for i in range(12):
            p = tmp / f"p{i:02d}.png"
            p.write_bytes(b"x")
            files.append(p)
        tg_media.album("t", "1", files, post=post)
        self.assertEqual(calls, ["sendMediaGroup", "sendMediaGroup"])
        self.assertEqual(tg_media.upload("", "sendPhoto", {}, {}, post=post), {})   # no token: nothing sent


if __name__ == "__main__":
    unittest.main()

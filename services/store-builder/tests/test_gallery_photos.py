"""The whole picture plan made a few at a time (a session starts it in the background and writes the copy meanwhile), and the
see-through check of a cut-out. Nothing reaches Codex or OpenAI here."""
import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from provision import ai_images, gallery_photos

PLAN = {"refs": ["pack.jpg"], "photos": [
    {"name": "p-pack", "prompt": "The jar from the reference photo in the right half, flat sunshine-yellow backdrop", "ref": True},
    {"name": "f-toast", "prompt": "One slice of toast with the spread, flat yellow backdrop"},
    {"name": "c-jar", "prompt": "The jar from the reference photo, upright and centred", "ref": True, "transparent": True},
]}


class Photos(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "pack.jpg").write_bytes(b"\xff\xd8")
        self.calls, self.running, self.most = [], 0, 0
        self.lock = threading.Lock()

    def fake_make(self, kind, prompt, out, refs=(), transparent=False):
        with self.lock:
            self.calls.append({"kind": kind, "out": Path(out).name, "refs": [Path(r).name for r in refs], "transparent": transparent})
            self.running += 1
            self.most = max(self.most, self.running)
        time.sleep(0.05)
        with self.lock:
            self.running -= 1
        if "toast" in prompt and getattr(self, "fail_toast", False):
            raise ai_images.ImagesError("Codex could not make it: usage limit")
        Path(out).write_bytes(b"\x89PNG")
        return {"path": str(out), "transparent": 0.4 if transparent else None}

    def test_every_photo_is_made_at_once_with_its_refs_and_kind(self):
        rows = gallery_photos.make_all(PLAN, self.tmp / "out", self.tmp, make=self.fake_make)
        self.assertEqual([r["name"] for r in rows], ["p-pack", "f-toast", "c-jar"])
        self.assertEqual(self.most, 3)  # three at the same time, not one after the other
        by = {c["out"]: c for c in self.calls}
        self.assertEqual((by["p-pack.png"]["kind"], by["p-pack.png"]["refs"]), ("studio", ["pack.jpg"]))
        self.assertEqual(by["f-toast.png"]["refs"], [])
        self.assertTrue(by["c-jar.png"]["transparent"])
        record = json.loads((self.tmp / "out" / "photos.json").read_text(encoding="utf-8"))
        self.assertEqual(len(record), 3)

    def test_a_failure_is_recorded_and_only_it_is_made_again(self):
        self.fail_toast = True
        rows = gallery_photos.make_all(PLAN, self.tmp / "out", self.tmp, make=self.fake_make)
        self.assertIn("usage limit", next(r for r in rows if r["name"] == "f-toast")["error"])
        self.fail_toast, self.calls = False, []
        gallery_photos.make_all(PLAN, self.tmp / "out", self.tmp, only={"f-toast"}, make=self.fake_make)
        self.assertEqual([c["out"] for c in self.calls], ["f-toast.png"])
        record = {r["name"]: r for r in json.loads((self.tmp / "out" / "photos.json").read_text(encoding="utf-8"))}
        self.assertEqual(set(record), {"p-pack", "f-toast", "c-jar"})  # the earlier results are kept
        self.assertIn("path", record["f-toast"])

    def test_a_refused_prompt_or_a_bad_plan_makes_nothing(self):
        bad = {"photos": [*PLAN["photos"], {"name": "x", "prompt": "Jar with a 50% off sticker"}]}
        with self.assertRaises(ValueError) as e:
            gallery_photos.make_all(bad, self.tmp / "out", self.tmp, make=self.fake_make)
        self.assertIn("x:", str(e.exception))
        for plan in ({"photos": []}, {"photos": [{"name": "a", "prompt": "toast"}, {"name": "a", "prompt": "toast"}]}):
            with self.assertRaises(ValueError):
                gallery_photos.make_all(plan, self.tmp / "out", self.tmp, make=self.fake_make)
        self.assertEqual(self.calls, [])


class Background(unittest.TestCase):
    """--detach starts the plan in its own process; --wait reads photos.json until every photo is made or failed."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_detach_starts_the_same_command_in_its_own_session_and_returns(self):
        seen = {}

        class Proc:
            pid = 4242

        def popen(cmd, **kw):
            seen.update(cmd=cmd, **kw)
            return Proc()

        code = gallery_photos.detach(["--plan", "p.json", "--out", "o", "--detach", "--progress", "x.json"], self.tmp / "o", popen=popen)
        self.assertEqual(code, 0)
        self.assertEqual(seen["cmd"][1:], ["-m", "provision.gallery_photos", "--plan", "p.json", "--out", "o", "--progress", "x.json"])
        self.assertTrue(seen["start_new_session"])
        self.assertEqual(json.loads((self.tmp / "o" / "running.json").read_text(encoding="utf-8"))["pid"], 4242)

    def test_wait_reports_made_failed_and_unfinished(self):
        out = self.tmp / "o"
        out.mkdir()
        (out / "photos.json").write_text(json.dumps([{"name": "p-pack", "path": "x.png"}, {"name": "f-toast", "error": "limit"}]),
                                         encoding="utf-8")
        clock = iter(range(0, 10000, 600))
        code = gallery_photos.wait(PLAN, out, timeout=1200, sleep=lambda s: None, clock=lambda: next(clock), alive=lambda o: True)
        self.assertEqual(code, 1)  # c-jar never finished: the time ran out
        code = gallery_photos.wait(PLAN, out, timeout=1200, sleep=lambda s: None, clock=lambda: 0, alive=lambda o: False)
        self.assertEqual(code, 1)  # the maker stopped: no endless wait


class SeeThrough(unittest.TestCase):
    def test_a_cut_out_asks_for_no_backdrop_and_a_solid_one_is_refused(self):
        text = ai_images.guard("The jar from the reference photo, upright", "studio", refs=True, transparent=True)
        self.assertIn("TRANSPARENT background", text)
        self.assertNotIn("seamless paper backdrop", text)  # the studio backdrop words would fight the cut-out
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        clear = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        clear.paste((200, 30, 30, 255), (3, 3, 7, 7))
        clear.save(tmp / "cut.png")
        Image.new("RGB", (10, 10), (255, 255, 255)).save(tmp / "solid.png")
        self.assertAlmostEqual(ai_images.clear_share(tmp / "cut.png"), 0.84)
        self.assertEqual(ai_images.clear_share(tmp / "solid.png"), 0.0)

        def runner(argv, timeout, data=None):
            out = Path(argv[argv.index("--out") + 1])
            shutil.copy(tmp / data, out)
            return 0, json.dumps({"ok": True, "path": str(out)}), ""

        side = ai_images.make("studio", "The jar, upright", tmp / "a.webp", environ={}, read_var=lambda n: None, codex_ok=lambda: True,
                              runner=lambda a, t: runner(a, t, "cut.png"), transparent=True)
        self.assertTrue(side["path"].endswith("a.png"))  # a cut-out is always a png
        self.assertAlmostEqual(side["transparent"], 0.84)
        with self.assertRaises(ai_images.ImagesError) as e:
            ai_images.make("studio", "The jar, upright", tmp / "b.png", environ={}, read_var=lambda n: None, codex_ok=lambda: True,
                           runner=lambda a, t: runner(a, t, "solid.png"), transparent=True)
        self.assertIn("transparent background", str(e.exception))


if __name__ == "__main__":
    unittest.main()

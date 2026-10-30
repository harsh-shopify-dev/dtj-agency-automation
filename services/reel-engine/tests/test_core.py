"""Engine core: brand folders, run folders and the stage server (no models, no network)."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from engine import brands, runs, server


def make_brand(root: Path, name: str = "branda", own: int = 2, niche: str = "snacks", niche_refs: int = 3) -> brands.Brand:
    b = root / "brands" / name
    (b / "references" / "cinematic").mkdir(parents=True)
    (b / "products").mkdir()
    (b / "brand.json").write_text(json.dumps({"name": "Brand A", "niche": niche}), encoding="utf-8")
    (b / "brief.md").write_text("A crunchy snack brand.", encoding="utf-8")
    (b / "facts.md").write_text("Baked, not fried.", encoding="utf-8")
    (b / "products" / "pack.png").write_bytes(b"png")
    for i in range(own):
        (b / "references" / "cinematic" / f"own{i}.mp4").write_bytes(b"v")
    n = root / "Niches" / niche / "cinematic"
    n.mkdir(parents=True)
    for i in range(niche_refs):
        (n / f"niche{i}.mp4").write_bytes(b"v")
    return brands.Brand(root, name)


class BrandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_refs_fall_back_to_niche(self):
        b = make_brand(self.tmp, own=2)
        self.assertEqual(len(b.references("cinematic", self.tmp / "Niches")), 5)

    def test_own_refs_enough_no_niche(self):
        b = make_brand(self.tmp, own=3)
        refs = b.references("cinematic", self.tmp / "Niches")
        self.assertEqual(len(refs), 3)
        self.assertTrue(all("own" in r.name for r in refs))

    def test_refs_none_raises(self):
        b = make_brand(self.tmp, own=0, niche_refs=0)
        with self.assertRaises(brands.NoReferences):
            b.references("cinematic", self.tmp / "Niches")

    def test_brand_fields(self):
        b = make_brand(self.tmp)
        self.assertEqual(b.niche, "snacks")
        self.assertIn("Baked", b.facts)
        self.assertEqual([p.name for p in b.products], ["pack.png"])
        self.assertEqual(b.style_card_path("cinematic").name, "cinematic.json")

    def test_unknown_brand_raises(self):
        with self.assertRaises(brands.UnknownBrand):
            brands.Brand(self.tmp, "nobody")


class RunTests(unittest.TestCase):
    def test_record_and_done(self):
        tmp = Path(tempfile.mkdtemp())
        r = runs.Run(tmp, "branda", "r1")
        self.assertIsNone(r.done("script"))
        r.record("script", {"ok": True, "scenes": 4})
        again = runs.Run(tmp, "branda", "r1")
        self.assertEqual(again.done("script")["scenes"], 4)

    def test_bad_run_id_refused(self):
        with self.assertRaises(ValueError):
            runs.Run(Path(tempfile.mkdtemp()), "branda", "../x")


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        make_brand(self.tmp)
        self.calls = []

        def script(run, brand, body):
            self.calls.append(body)
            return {"ok": True, "scenes": 3}

        def take(run, brand, body):
            return {"ok": True, "run": run.run}

        self.ctx = server.Context(self.tmp, {"take": take, "script": script}, rerun={"review"})

    def post(self, body):
        return server.handle(body, self.ctx)

    def test_refuses_without_watcher(self):
        code, ans = self.post({"brand": "branda", "run": "r1", "stage": "take"})
        self.assertEqual(code, 400)
        self.assertIn("watcher", ans["error"])

    def test_take_then_stage_uses_saved_watcher(self):
        self.assertEqual(self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})[0], 200)
        code, ans = self.post({"brand": "branda", "run": "r1", "stage": "script"})
        self.assertEqual(code, 200)
        self.assertTrue(ans["ok"])

    def test_stage_retry_returns_saved(self):
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.post({"brand": "branda", "run": "r1", "stage": "script"})
        code, ans = self.post({"brand": "branda", "run": "r1", "stage": "script"})
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(ans["cached"])

    def test_same_stage_with_new_fields_runs_again(self):
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.post({"brand": "branda", "run": "r1", "stage": "script", "round": 1})
        code, ans = self.post({"brand": "branda", "run": "r1", "stage": "script", "round": 2, "note": "shorter"})
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn("cached", ans)

    def test_review_always_runs(self):
        self.ctx.stages["review"] = lambda run, brand, body: self.calls.append(body) or {"ok": True, "waiting": True}
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.post({"brand": "branda", "run": "r1", "stage": "review"})
        self.post({"brand": "branda", "run": "r1", "stage": "review"})
        self.assertEqual(len(self.calls), 2)

    def test_redo_runs_again(self):
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.post({"brand": "branda", "run": "r1", "stage": "script"})
        self.post({"brand": "branda", "run": "r1", "stage": "script", "redo": True})
        self.assertEqual(len(self.calls), 2)

    def test_busy_when_locked(self):
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.ctx.lock.acquire()
        try:
            code, ans = self.post({"brand": "branda", "run": "r1", "stage": "script"})
        finally:
            self.ctx.lock.release()
        self.assertEqual(code, 409)
        self.assertEqual(ans, {"ok": False, "busy": True})

    def test_review_is_not_blocked_by_the_lock(self):
        self.ctx.stages["review"] = lambda run, brand, body: {"ok": True, "waiting": True}
        self.ctx.rerun = {"review"}
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.ctx.lock.acquire()
        try:
            code, ans = self.post({"brand": "branda", "run": "r1", "stage": "review"})
        finally:
            self.ctx.lock.release()
        self.assertEqual((code, ans.get("waiting")), (200, True))

    def test_unknown_stage(self):
        self.post({"brand": "branda", "run": "r1", "stage": "take", "watcher": "Harsh"})
        code, ans = self.post({"brand": "branda", "run": "r1", "stage": "nope"})
        self.assertEqual(code, 400)

    def test_unknown_brand(self):
        code, ans = self.post({"brand": "zzz", "run": "r1", "stage": "take", "watcher": "Harsh"})
        self.assertEqual(code, 404)

    def test_files_path_cannot_escape(self):
        code, ans = server.save_file(self.ctx, "branda", "../x.mp4", b"v")
        self.assertEqual(code, 400)

    def test_files_saved_in_brand(self):
        code, ans = server.save_file(self.ctx, "branda", "references/ugc/a.mp4", b"v")
        self.assertEqual(code, 200)
        self.assertTrue((self.tmp / "brands" / "branda" / "references" / "ugc" / "a.mp4").is_file())

    def test_outputs_lists_finals(self):
        r = runs.Run(self.tmp, "branda", "r1")
        (r.dir / "final").mkdir()
        (r.dir / "final" / "reel.mp4").write_bytes(b"v")
        code, ans = server.outputs(self.ctx, "branda", "r1")
        self.assertEqual(code, 200)
        self.assertEqual([Path(p).name for p in ans["final"]], ["reel.mp4"])


if __name__ == "__main__":
    unittest.main()

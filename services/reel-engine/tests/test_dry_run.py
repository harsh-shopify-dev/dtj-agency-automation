"""A whole reel through the engine's HTTP handler, in the order n8n's Reel Engine calls it, with fake models, Telegram and Flow."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine import server, stages
from tests.test_core import make_brand
from tests.test_stages import FACTS, Fakes


class DryRun(unittest.TestCase):
    def test_whole_reel_with_one_change_round(self):
        tmp = Path(tempfile.mkdtemp())
        brand = make_brand(tmp, own=3)
        (brand.dir / "facts.md").write_text(FACTS, encoding="utf-8")
        f = Fakes(tmp)
        d = f.deps()
        ctx = server.Context(tmp, {n: (lambda r, b, body, n=n: stages.run_stage(n, r, b, body, deps=d)) for n in stages.STAGES},
                             stages.RERUN)

        def post(stage, **body):
            code, ans = server.handle({"brand": "branda", "run": "r20261030-1200-abcd", "stage": stage, **body}, ctx)
            self.assertEqual(code, 200, ans)
            return ans

        post("take", style="cinematic", request="Diwali reel", language="en", chat="123", watcher="Harsh")
        post("style_card")
        post("script", loop=0)
        pics = post("pictures", loop=0)
        self.assertEqual(len(pics["pictures"]), 4)
        self.assertTrue(post("review", gate="pictures", loop=0)["waiting"])
        f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "2: add a diya next to the pack"})]
        change = post("review", gate="pictures", loop=0)
        self.assertEqual((change["next"], change["loop"]), ("pictures", 1))
        drawn = len(f.codex_calls)
        post("pictures", loop=change["loop"])
        self.assertEqual(len(f.codex_calls), drawn + 1)
        again = post("pictures", loop=change["loop"])            # an n8n retry of the same call: nothing redrawn
        self.assertTrue(again["cached"])
        self.assertEqual(len(f.codex_calls), drawn + 1)
        f.person_answers = [(0, {"ok": True, "by": "Harsh"})]
        self.assertEqual(post("review", gate="pictures", loop=1)["next"], "clips")
        clips = post("clips", loop=1)
        self.assertEqual(clips["needs_look"], [])
        self.assertEqual(len(f.flow_calls), 4)
        post("clips", loop=1)                                     # retried: no second Flow spend
        self.assertEqual(len(f.flow_calls), 4)
        post("edit", loop=1)
        f.person_answers = [(0, {"ok": True, "by": "Harsh"})]
        self.assertEqual(post("review", gate="final", loop=1)["next"], "save")
        res = post("result", loop=1)
        self.assertEqual(res["reel_status"], "reel ready")
        self.assertTrue(Path(res["final_path"]).is_file())
        self.assertEqual(res["credits"], 24 * 4)
        self.assertEqual(res["watcher"], "Harsh")


if __name__ == "__main__":
    unittest.main()

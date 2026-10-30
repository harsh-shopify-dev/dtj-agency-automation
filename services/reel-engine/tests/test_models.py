"""Model wrappers with a fake subprocess.run: no login, no quota."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from engine import models
from engine.server import NeedsPerson


class Fake:
    def __init__(self, *outs, on_call=None):
        self.outs, self.calls, self.on_call = list(outs), [], on_call

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if self.on_call:
            self.on_call(cmd, kw)
        out = self.outs.pop(0) if len(self.outs) > 1 else self.outs[0]
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")


def agy(text: str, status: str = "SUCCESS") -> str:
    return json.dumps({"status": status, "response": text, "error": "" if status == "SUCCESS" else text})


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.vid = self.tmp / "ref.mp4"
        self.vid.write_bytes(b"v")

    def test_json_in_fences_parsed(self):
        run = Fake(agy('Here you go:\n```json\n{"scenes": 3}\n```\nDone.'))
        self.assertEqual(models.gemini_json("p", [self.vid], self.tmp, run=run), {"scenes": 3})

    def test_files_mentioned_with_at(self):
        run = Fake(agy('{"a": 1}'))
        models.gemini_json("watch", [self.vid], self.tmp, run=run)
        cmd = run.calls[0][0]
        self.assertIn("@ref.mp4", cmd[cmd.index("-p") + 1])

    def test_bad_json_retried_once_then_error(self):
        run = Fake(agy("no json here"))
        with self.assertRaises(models.ModelError):
            models.gemini_json("p", [], self.tmp, run=run)
        self.assertEqual(len(run.calls), 2)

    def test_bad_json_then_good(self):
        run = Fake(agy("nope"), agy('{"ok": 1}'))
        self.assertEqual(models.gemini_json("p", [], self.tmp, run=run), {"ok": 1})

    def test_signin_text_is_needs_person(self):
        run = Fake(agy("Error authenticating: please sign in again", status="ERROR"))
        with self.assertRaises(NeedsPerson):
            models.gemini_json("p", [], self.tmp, run=run)

    def test_quota_is_needs_person_for_claude(self):
        run = Fake(json.dumps({"is_error": True, "result": "You've hit your usage limit"}))
        with self.assertRaises(NeedsPerson):
            models.claude_json("p", [], self.tmp, run=run)

    def test_claude_json_parsed(self):
        run = Fake(json.dumps({"is_error": False, "result": 'Score: ```json\n{"score": 8}\n```'}))
        self.assertEqual(models.claude_json("p", [self.vid], self.tmp, run=run), {"score": 8})

    def test_codex_image_missing_file_is_error(self):
        run = Fake("session id: 0123456789abcdef0123456789\ndone")
        with self.assertRaises(models.ModelError):
            models.codex_image("draw", [self.vid], self.tmp / "out.png", run=run, codex_home=self.tmp / "codex")

    def test_codex_image_copied_and_no_api_key(self):
        home = self.tmp / "codex"
        sid = "0123456789abcdef0123456789"

        def draw(cmd, kw):
            d = home / "generated_images" / sid
            d.mkdir(parents=True)
            (d / "img.png").write_bytes(b"png")

        run = Fake(f"session id: {sid}\ndone", on_call=draw)
        out = models.codex_image("draw", [self.vid], self.tmp / "out.png", run=run, codex_home=home,
                                 env={"OPENAI_API_KEY": "x", "PATH": "/bin"})
        self.assertEqual(out.read_bytes(), b"png")
        cmd, kw = run.calls[0]
        self.assertNotIn("OPENAI_API_KEY", kw["env"])
        self.assertEqual(kw["env"]["CODEX_HOME"], str(home))
        self.assertIn(f"--image={self.vid}", cmd)

    def test_env_home_per_tool(self):
        run = Fake(agy('{"a": 1}'))
        models.gemini_json("p", [], self.tmp, run=run, env={"GEMINI_HOME": "/g", "PATH": "/bin"})
        self.assertEqual(run.calls[0][1]["env"]["HOME"], "/g")


if __name__ == "__main__":
    unittest.main()

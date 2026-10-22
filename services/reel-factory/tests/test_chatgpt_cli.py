"""The ChatGPT picture command for the VPS (reel_factory/chatgpt_cli.py): one JSON line and a clear exit code, with a stand-in
ChatGPT window. Nothing here opens Chrome or reaches ChatGPT.

    cd services/reel-factory && python -m unittest discover -s tests -t .
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reel_factory import chatgpt_cli
from reel_factory.flow import NeedsPerson

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


class FakeChatGPT:
    def __init__(self, fail=None):
        self.fail, self.calls, self.closed = fail, [], False

    def image(self, prompt, out, files=(), timeout_s=300):
        self.calls.append((prompt, list(files), timeout_s))
        if self.fail:
            raise self.fail
        Path(out).write_bytes(PNG)
        return Path(out)

    def close(self):
        self.closed = True


class ChatGPTCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.prompt = self.tmp / "prompt.txt"
        self.prompt.write_text("One amber bottle on a plain light background.\n", encoding="utf-8")
        self.ref = self.tmp / "ref-1.jpg"
        self.ref.write_bytes(b"\xff\xd8jpg")
        self.seen = []

    def run_cli(self, cg, *extra, attach=None):
        argv = ["image", "--prompt-file", str(self.prompt), "--out", str(self.tmp / "out.png"), *extra]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = chatgpt_cli.main(argv, attach=attach or (lambda cdp: self.seen.append(cdp) or cg))
        lines = buf.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 1)  # one JSON line, always
        return code, json.loads(lines[0])

    def test_a_fresh_chat_with_our_product_attached_makes_one_picture(self):
        cg = FakeChatGPT()
        code, got = self.run_cli(cg, "--ref", str(self.ref), "--timeout", "120", "--cdp", "http://127.0.0.1:9333")
        self.assertEqual(code, 0)
        self.assertEqual((got["ok"], got["refs"], Path(got["path"]).name), (True, 1, "out.png"))
        self.assertEqual(cg.calls, [("One amber bottle on a plain light background.", [str(self.ref)], 120)])
        self.assertEqual(self.seen, ["http://127.0.0.1:9333"])
        self.assertTrue(cg.closed)
        self.assertEqual((self.tmp / "out.png").read_bytes(), PNG)

    def test_chrome_not_answering_exits_2(self):
        def down(cdp):
            raise ConnectionRefusedError("connect ECONNREFUSED 127.0.0.1:9222")
        code, got = self.run_cli(None, attach=down)
        self.assertEqual(code, 2)
        self.assertIn("does not answer at http://127.0.0.1:9222", got["error"])

    def test_signed_out_says_a_person_is_needed(self):
        code, got = self.run_cli(FakeChatGPT(NeedsPerson("ChatGPT is signed out in the reel Chrome window")))
        self.assertEqual((code, got["ok"], got.get("needs_person")), (1, False, True))
        self.assertIn("signed out", got["error"])

    def test_a_refusal_or_a_missing_reference_is_exit_1(self):
        code, got = self.run_cli(FakeChatGPT(RuntimeError("ChatGPT refused the picture")))
        self.assertEqual((code, got["ok"]), (1, False))
        cg = FakeChatGPT()
        code, got = self.run_cli(cg, "--ref", str(self.tmp / "nope.jpg"))
        self.assertEqual(code, 1)
        self.assertIn("reference picture not found", got["error"])
        self.assertEqual(cg.calls, [])  # nothing sent to ChatGPT

    def test_an_empty_prompt_is_refused(self):
        self.prompt.write_text("  \n", encoding="utf-8")
        code, got = self.run_cli(FakeChatGPT())
        self.assertEqual((code, got["error"]), (1, "the prompt file is empty"))


if __name__ == "__main__":
    unittest.main()

"""The Flow clip command (reel_factory/flow_cli.py): one JSON line and a clear exit code, with a stand-in Flow window.
Nothing here opens Chrome or spends Flow credits.

    cd services/reel-factory && python -m unittest discover -s tests -t .
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reel_factory import flow_cli
from reel_factory.flow import NeedsPerson


class FakeFlow:
    def __init__(self, fail=None):
        self.fail, self.log, self.closed, self.attached_ids = fail, [], False, []
        self.uploads = {}

    def open_project(self, url=None):
        self.log.append(("open", url))
        return url or "https://flow.google.com/project/p1"

    def settings(self, mode, ratio="9:16", takes=2, model=None, seconds=None, **kw):
        self.log.append(("settings", mode, ratio, takes, model, seconds))

    def upload(self, path, timeout_s=120):
        aid = f"asset-{len(self.uploads) + 1}"
        self.uploads[aid] = str(path)
        self.attached_ids.append(aid)  # Flow also attaches an upload to the prompt
        return aid

    def clear_attached(self):
        self.attached_ids = []

    def attach(self, asset_id):
        self.log.append(("attach", asset_id))
        self.attached_ids.append(asset_id)

    def generate(self, prompt, expect, timeout_s=600):
        if self.fail:
            raise self.fail
        self.log.append(("generate", prompt, expect, list(self.attached_ids)))
        return [f"vid-{k}" for k in range(expect)]

    def video_url(self, asset_id):
        return f"https://signed/{asset_id}"

    def close(self):
        self.closed = True


class FlowCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.prompt = self.tmp / "p.txt"
        self.prompt.write_text("Slow push-in. The pack stays still on the table.\n", encoding="utf-8")
        self.image = self.tmp / "s3.png"
        self.image.write_bytes(b"png")
        self.pack = self.tmp / "pack.png"
        self.pack.write_bytes(b"png")
        self.downloads = []

    def fake_download(self, url, dest):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"mp4")
        self.downloads.append((url, str(dest)))
        return Path(dest)

    def run_cli(self, fl, *extra, attach=None):
        argv = ["clip", "--image", str(self.image), "--prompt-file", str(self.prompt), "--out", str(self.tmp / "clips"), *extra]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = flow_cli.main(argv, attach=attach or (lambda cdp: fl), download=self.fake_download)
        lines = buf.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 1)  # one JSON line, always
        return code, json.loads(lines[0])

    def test_ok_json(self):
        fl = FakeFlow()
        code, got = self.run_cli(fl, "--product", str(self.pack), "--seconds", "8")
        self.assertEqual(code, 0)
        self.assertTrue(got["ok"])
        self.assertEqual(len(got["files"]), 2)
        self.assertEqual(got["credits"], 24)
        self.assertEqual(got["project"], "https://flow.google.com/project/p1")
        self.assertIn(("settings", "Video", "9:16", 2, "Omni", 8), fl.log)
        self.assertTrue(fl.closed)

    def test_mode_set_before_attaching(self):
        fl = FakeFlow()
        self.run_cli(fl, "--product", str(self.pack))
        kinds = [e[0] for e in fl.log]
        self.assertLess(kinds.index("settings"), kinds.index("attach"))

    def test_attaches_by_asset_id_not_position(self):
        fl = FakeFlow()
        self.run_cli(fl, "--product", str(self.pack))
        gen = [e for e in fl.log if e[0] == "generate"][0]
        self.assertEqual(gen[3], ["asset-1", "asset-2"])  # exactly the start picture and the pack, by id
        self.assertEqual(fl.uploads["asset-1"], str(self.image))

    def test_bad_seconds_refused(self):
        fl = FakeFlow()
        code, got = self.run_cli(fl, "--seconds", "5")
        self.assertEqual(code, 1)
        self.assertIn("4, 6, 8 or 10", got["error"])
        self.assertEqual(fl.log, [])  # nothing sent to Flow

    def test_needs_person(self):
        code, got = self.run_cli(FakeFlow(NeedsPerson("Google asks for a sign-in")))
        self.assertEqual((code, got["ok"], got.get("needs_person")), (1, False, True))

    def test_chrome_down_exit_2(self):
        def down(cdp):
            raise ConnectionRefusedError("refused")
        code, got = self.run_cli(None, attach=down)
        self.assertEqual(code, 2)
        self.assertIn("does not answer", got["error"])

    def test_missing_image_refused(self):
        self.image.unlink()
        code, got = self.run_cli(FakeFlow())
        self.assertEqual(code, 1)
        self.assertIn("not found", got["error"])


if __name__ == "__main__":
    unittest.main()

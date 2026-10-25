"""A frozen Shopify CLI never hangs a write (20 and 21 Oct 2026: a theme pull sat idle for 10+ minutes; subprocess.run's own timeout could
not end it on Windows). Stand-in processes only: nothing reaches Shopify."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_chrome import FOOTER, FakeTheme, brand, facts  # noqa: E402

from page_builder import push_page, run_chrome  # noqa: E402
from page_builder import theme_target as tt  # noqa: E402
from provision.theme import ThemeError  # noqa: E402


class Frozen:
    """A process that never answers (communicate always times out), or one that answers at once."""
    started: list = []

    def __init__(self, args, freeze=True, **kw):
        self.args, self.pid, self.freeze, self.returncode = args, 4242, freeze, 0
        Frozen.started.append(args)

    def communicate(self, timeout=None):
        if self.freeze:
            raise subprocess.TimeoutExpired(self.args, timeout)
        return "ok", ""


class RunTests(unittest.TestCase):
    def setUp(self):
        Frozen.started = []

    def test_a_frozen_read_is_stopped_with_its_children_and_tried_once_more(self):
        with mock.patch.object(tt, "_kill_tree") as kill, mock.patch.object(tt, "LIMITS", {"pull": 0.01, "list": 0.01, "push": 0.01}):
            with self.assertRaises(ThemeError) as e:
                tt._run(["shopify", "theme", "pull", "--path", "x"], {}, popen=Frozen)
        self.assertEqual(len(Frozen.started), 2)
        self.assertEqual(kill.call_count, 2)  # the whole tree, each time
        self.assertIn("2 tries", str(e.exception))

    def test_a_frozen_write_is_never_repeated_and_says_to_read_the_theme_back(self):
        with mock.patch.object(tt, "_kill_tree"), mock.patch.object(tt, "LIMITS", {"pull": 0.01, "list": 0.01, "push": 0.01}):
            with self.assertRaises(ThemeError) as e:
                tt._run(["shopify", "theme", "push", "--path", "x"], {}, popen=Frozen)
        self.assertEqual(len(Frozen.started), 1)
        self.assertIn("read the theme back", str(e.exception))

    def test_an_answer_comes_back_as_before(self):
        done = tt._run(["shopify", "theme", "list"], {}, popen=lambda a, **k: Frozen(a, freeze=False))
        self.assertEqual((done.returncode, done.stdout), (0, "ok"))


class StoppedButLanded(FakeTheme):
    """The push lands, then the CLI is stopped before it says so (what happened to the footer on 21 Oct 2026)."""

    def push_product_template(self, theme_id, staging, file):
        super().push_product_template(theme_id, staging, file)
        raise ThemeError("shopify push did not answer within 300 s; it was stopped (a write may still have landed: read the theme back)")


class Refused(FakeTheme):
    def push_product_template(self, theme_id, staging, file):
        raise ThemeError("shopify theme push failed (1): refused")


class PushPageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.client = self.tmp / "client"
        self.client.mkdir()
        (self.client / "brand.json").write_text(json.dumps(brand()), encoding="utf-8")
        (self.client / "home-facts.json").write_text(json.dumps(facts()), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def push(self, fake):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_chrome.main(["--client", str(self.client), "--store", "test-store.myshopify.com", "--theme", "123456"], access=fake), 0)
            a = json.loads((self.client / "chrome-run" / "footer" / "approval.json").read_text(encoding="utf-8"))
            code = push_page.main(["--out", str(self.client / "chrome-run" / "footer"), "--approve", a["approve_code"], "--approved-by", "Harsh"], access=fake)
        log = [json.loads(x) for x in (self.client / "chrome-run" / "footer" / "action-log.jsonl").read_text(encoding="utf-8").splitlines()]
        return code, log[-1]

    def test_a_stopped_write_that_landed_is_reported_written_after_reading_it_back(self):
        code, row = self.push(StoppedButLanded())
        self.assertEqual(code, 0)
        self.assertEqual(row["result"], "success")

    def test_a_refused_write_is_reported_failed_with_its_reason(self):
        fake = Refused()
        code, row = self.push(fake)
        self.assertEqual(code, 1)
        self.assertEqual(row["result"], "failed")
        self.assertIn("refused", row["error"])
        self.assertEqual(json.loads(fake.files["sections/footer-group.json"]), FOOTER)  # the theme is unchanged


if __name__ == "__main__":
    unittest.main()

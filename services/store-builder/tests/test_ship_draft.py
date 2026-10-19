"""ship_draft: one command from a client folder to a page in the DRAFT theme, with every gate in front of the write (stand-in build,
checks and push: nothing here talks to a store)."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from page_builder import ship_draft

STORE, THEME = "qaxv3r-8g.myshopify.com", "167627423941"


def passing_checks(_out):
    return {"passed": 11, "of": 11, "checks": {"H01_card_separation": {"pass": True, "findings": []}}}


class ShipDraft(unittest.TestCase):
    def setUp(self):
        self.client = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.client)
        (self.client / "brand.json").write_text(json.dumps({"brand_name": "Glow"}), encoding="utf-8")
        (self.client / "facts.json").write_text(json.dumps({"product": {"handle": "radiance-serum"}}), encoding="utf-8")
        (self.client / "copy-answer.json").write_text("{}", encoding="utf-8")
        self.builds, self.pushes = [], []

    def design(self, code=0, lint=(), problems=(), samples=3, demo=True, message="", files=None, people=()):
        def fake(argv):
            self.builds.append(argv)
            out = Path(argv[argv.index("--out") + 1])
            if (code != 1) if files is None else files:
                (out / "template.json").write_text("{}", encoding="utf-8")
                (out / "build-report.json").write_text(json.dumps({"lint": list(lint), "problems": list(problems), "people_photos": list(people),
                                                                   "sections_built": [{"kind": "faq"}] * 13}), encoding="utf-8")
                (out / "approval.json").write_text(json.dumps({"approve_code": "0123456789ab", "store": STORE, "theme_id": THEME,
                                                               "file": "templates/product.dtj-glow.json", "samples": samples, "demo": demo,
                                                               "demo_pictures": 2, "dtj_copy": 5, "review": "pass" if code == 0 else "needs a look",
                                                               "kept_edits": []}), encoding="utf-8")
            print(message)
            return code
        return fake

    def push(self, rc=0):
        def fake(argv):
            self.pushes.append(argv)
            print("written and verified" if rc == 0 else "not written: the theme is live")
            return rc
        return fake

    def ship(self, *extra, design=None, push=None, checks=passing_checks, people=None):
        argv = ["--client", str(self.client), "--store", STORE, "--theme", THEME, "--template-suffix", "dtj-glow", *extra]
        self.uploads = []

        def fake_people(store, files, log_dir):
            self.uploads.append((store, list(files), self.pushes[:]))
            return (True, "") if people is None else people

        with contextlib.redirect_stdout(io.StringIO()):
            code = ship_draft.main(argv, design=design or self.design(), push=push or self.push(), checks=checks, sleep=lambda s: None,
                                   people=fake_people)
        return code, json.loads((self.client / "run" / "ship-result.json").read_text(encoding="utf-8"))

    def test_the_sample_people_photos_reach_the_stores_files_before_the_draft_is_written(self):
        files = ["dtj-sample-person-02.webp", "dtj-sample-person-03.webp"]
        code, res = self.ship(design=self.design(people=files))
        self.assertEqual((code, res["page_status"]), (0, "written to draft"))
        self.assertEqual(self.uploads, [(STORE, files, [])])  # uploaded first, while nothing was pushed yet
        self.assertEqual(len(self.pushes), 1)
        code, res = self.ship(design=self.design(people=files), people=(False, "access denied"))
        self.assertEqual((code, res["page_status"]), (2, "needs a look"))
        self.assertIn("could not be put in the store's Files (access denied)", res["note"])
        self.assertEqual(len(self.pushes), 1)  # nothing more was written
        code, _ = self.ship("--design-only", design=self.design(people=files))
        self.assertEqual(self.uploads, [])  # design only never touches the store
        code, _ = self.ship()
        self.assertEqual(self.uploads, [])  # a page without people photos uploads nothing

    def test_a_page_that_passes_every_gate_is_written_to_the_draft(self):
        code, res = self.ship()
        self.assertEqual((code, res["page_status"], res["design_checks"]), (0, "written to draft", "11/11"))
        flags = self.pushes[0]
        self.assertEqual(flags[flags.index("--approve") + 1], "0123456789ab")  # the build's own code, never a stale one
        self.assertEqual(flags[flags.index("--approved-by") + 1], ship_draft.STANDING)
        self.assertIn("--allow-samples", flags)  # a draft preview may hold samples; push_page still refuses the live theme
        self.assertIn("--allow-demo", flags)
        self.assertEqual(res["preview_url"], f"https://{STORE}/products/radiance-serum?preview_theme_id={THEME}&view=dtj-glow")
        build = self.builds[0]
        self.assertEqual(build[build.index("--plan") + 1], "off")  # the fixed sections, never a per-product plan
        self.assertEqual(build[build.index("--copy") + 1], "answer")

    def test_without_a_copy_answer_the_copy_step_runs_dry_and_writes_its_request(self):
        (self.client / "copy-answer.json").unlink()
        self.ship("--design-only")
        build = self.builds[0]
        self.assertEqual(build[build.index("--copy") + 1], "dry")  # never "live": no API call from this command
        self.assertNotIn("--copy-answer", build)

    def test_a_failed_design_check_writes_nothing(self):
        def failing(_out):
            return {"passed": 10, "of": 11, "checks": {"H11_no_brown": {"pass": False, "findings": ["dtj_final.background = #402305"]}}}
        code, res = self.ship(checks=failing)
        self.assertEqual((code, res["page_status"], self.pushes), (2, "needs a look", []))
        self.assertIn("H11_no_brown: dtj_final.background = #402305", res["failed_checks"])

    def test_lint_errors_or_a_failed_review_write_nothing(self):
        code, res = self.ship(design=self.design(code=2, lint=[{"severity": "error", "rule": "L17", "message": "story too long"}]))
        self.assertEqual((code, res["page_status"], self.pushes), (2, "needs a look", []))
        self.assertIn("L17", res["note"])

    def test_a_failed_build_never_pushes_an_older_approval(self):
        run = self.client / "run"
        run.mkdir()
        (run / "approval.json").write_text(json.dumps({"approve_code": "fedcba987654"}), encoding="utf-8")  # left by an earlier run
        code, res = self.ship(design=self.design(code=1, message="could not build the page: bad facts"))
        self.assertEqual((code, res["page_status"], self.pushes), (1, "could not build", []))
        self.assertEqual(len(self.builds), 1)  # not a browser failure: no retry
        code, res = self.ship(design=self.design(code=1, files=True, message="stopped after writing"))  # files written, then it failed
        self.assertEqual((code, res["page_status"], self.pushes), (1, "could not build", []))

    def test_a_browser_that_did_not_start_is_retried_at_most_three_times(self):
        code, res = self.ship(design=self.design(code=1, message="review loop could not run: no browser rendered"))
        self.assertEqual((code, len(self.builds), self.pushes), (1, 3, []))
        flaky = iter([self.design(code=1, message="review loop could not run"), self.design()])
        self.builds.clear()
        code, res = self.ship(design=lambda argv: next(flaky)(argv))
        self.assertEqual((code, res["page_status"], len(self.builds)), (0, "written to draft", 2))

    def test_a_refused_push_is_reported_not_hidden(self):
        code, res = self.ship(push=self.push(rc=1))
        self.assertEqual((code, res["page_status"], res["preview_url"]), (2, "needs a look", ""))
        self.assertIn("the theme is live", res["note"])

    def test_design_only_never_touches_the_store(self):
        argv = ["--client", str(self.client), "--design-only"]
        with contextlib.redirect_stdout(io.StringIO()):
            code = ship_draft.main(argv, design=self.design(), push=self.push(), checks=passing_checks, sleep=lambda s: None)
        res = json.loads((self.client / "run" / "ship-result.json").read_text(encoding="utf-8"))
        self.assertEqual((code, res["page_status"], self.pushes), (0, "designed (not written)", []))
        self.assertIn("--no-theme-check", self.builds[0])
        self.assertNotIn("--store", self.builds[0])

    def test_the_real_design_checks_script_is_where_the_runner_looks(self):
        self.assertTrue(ship_draft.DESIGN_CHECKS.is_file(), ship_draft.DESIGN_CHECKS)


if __name__ == "__main__":
    unittest.main()

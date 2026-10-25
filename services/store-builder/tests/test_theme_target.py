"""Tests for the draft-theme path: Theme Access password handling, the theme checks, run_client's approval file and push_page's gate.
A stand-in for the Shopify CLI plays the store, so nothing here reaches Shopify."""
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from page_builder import push_page, run_client
from page_builder import theme_target as tt
from page_builder.examples import fixtures
from provision.theme import ThemeError

TOKEN = "shptka_test_not_a_real_password_123"
STORE = "elevate-with-harsh.myshopify.com"
THEME = "150000000001"


class FakeShopify:
    """Answers `shopify theme list|pull|push` like the CLI does, holding the draft theme's files in memory."""

    def __init__(self, role="unpublished", base="Horizon", product='/* auto-generated */\n{"sections": {}, "order": []}\n'):
        self.role, self.base = role, base
        self.files = {tt.PRODUCT_TEMPLATE: product,
                      tt.SCHEMA_FILE: json.dumps([{"name": "theme_info", "theme_name": base, "theme_version": "4.2.0"}])}
        self.calls, self.pushed, self.fail_with, self.tamper = [], [], None, False

    def __call__(self, cmd, env):
        self.calls.append((list(cmd), dict(env)))
        if self.fail_with:
            return subprocess.CompletedProcess(cmd, 1, "", self.fail_with)
        verb = cmd[2]
        if verb == "list":
            theme_id = cmd[cmd.index("--id") + 1]
            found = [{"id": int(THEME), "name": "Horizon draft", "role": self.role}] if theme_id == THEME else []
            return subprocess.CompletedProcess(cmd, 0, json.dumps(found), "")
        path = Path(cmd[cmd.index("--path") + 1])
        only = [cmd[i + 1] for i, c in enumerate(cmd) if c == "--only"]
        if verb == "pull":
            for name in only:
                if name in self.files:
                    (path / name).parent.mkdir(parents=True, exist_ok=True)
                    (path / name).write_text(self.files[name], encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if verb == "push":
            for name in only:
                self.files[name] = (path / name).read_text(encoding="utf-8")
                if self.tamper:  # what Shopify keeps differs from what was sent
                    self.files[name] = '{"sections": {}, "order": []}'
                self.pushed.append(name)
            theme = {"id": int(THEME), "name": "Horizon draft", "role": self.role,
                     "editor_url": f"https://{STORE}/admin/themes/{THEME}/editor", "preview_url": f"https://{STORE}/?preview_theme_id={THEME}"}
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"theme": theme}), "")
        raise AssertionError(cmd)


def access(fake):
    return tt.ThemeAccess(STORE, TOKEN, runner=fake)


class Password(unittest.TestCase):
    def test_store_and_variable_names(self):
        self.assertEqual(tt.normalise_store("https://Elevate-With-Harsh.myshopify.com/admin"), STORE)
        self.assertEqual(tt.normalise_store("elevate-with-harsh"), STORE)
        self.assertEqual(tt.token_env_name(STORE), "DTJ_THEME_ACCESS_ELEVATE_WITH_HARSH")
        with self.assertRaises(ThemeError):
            tt.normalise_store("toilova.in/shop")
        self.assertEqual(tt.read_token(STORE, {"DTJ_THEME_ACCESS_ELEVATE_WITH_HARSH": TOKEN}, registry=False), TOKEN)
        self.assertIsNone(tt.read_token(STORE, {}, registry=False))

    def test_password_goes_only_through_the_child_environment(self):
        fake = FakeShopify()
        a = access(fake)
        a.themes(THEME)
        cmd, env = fake.calls[0]
        self.assertNotIn(TOKEN, " ".join(cmd))
        self.assertEqual(env["SHOPIFY_CLI_THEME_TOKEN"], TOKEN)
        self.assertNotIn(TOKEN, repr(a))
        self.assertNotIn(TOKEN, json.dumps(a.commands))

    def test_password_is_redacted_from_cli_errors(self):
        fake = FakeShopify()
        fake.fail_with = f"Invalid password {TOKEN}"
        with self.assertRaises(ThemeError) as caught:
            access(fake).themes(THEME)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertIn("[redacted]", str(caught.exception))


class TargetChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_a_horizon_draft_passes_and_its_product_page_is_backed_up(self):
        info = tt.check_target(access(FakeShopify()), THEME, self.tmp / "before")
        self.assertEqual((info["role"], info["base_theme"], info["base_version"]), ("unpublished", "Horizon", "4.2.0"))
        self.assertTrue(Path(info["backup"]).exists())
        self.assertEqual(info["current_product_template_sha256"], tt.sha256(Path(info["backup"]).read_bytes()))

    def test_refusals(self):
        cases = {
            "LIVE": (FakeShopify(role="live"), THEME),
            "not found": (FakeShopify(), "999"),
            "only a draft": (FakeShopify(role="development"), THEME),
            "supports Horizon, Dawn only": (FakeShopify(base="Debut"), THEME),
            "must be the number": (FakeShopify(), "live"),
        }
        for words, (fake, theme_id) in cases.items():
            with self.subTest(words):
                with self.assertRaises(ThemeError) as caught:
                    tt.check_target(access(fake), theme_id, self.tmp / words.replace(" ", "_"))
                self.assertIn(words, str(caught.exception))
                self.assertEqual(fake.pushed, [])

    def test_push_command_is_narrow(self):
        fake = FakeShopify()
        staging = tt.stage(self._template(), self.tmp / "stage")
        access(fake).push_product_template(THEME, staging)
        cmd = fake.calls[-1][0]
        self.assertEqual([cmd[i + 1] for i, c in enumerate(cmd) if c == "--only"], [tt.PRODUCT_TEMPLATE])
        for flag in ("--nodelete", "--json"):
            self.assertIn(flag, cmd)
        for flag in ("--allow-live", "--publish", "--live", "--unpublished"):
            self.assertNotIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--theme") + 1], THEME)

    def _template(self):
        p = self.tmp / "template.json"
        p.write_bytes(tt.template_bytes({"sections": {"a": {"type": "x"}}, "order": ["a"]}))
        return p

    def test_store_product_is_context_only_and_skipped_behind_a_password(self):
        body = json.dumps({"title": "TOILOVA", "price": 29900, "compare_at_price": 39900, "options": [{"name": "Size"}],
                           "variants": [{}, {}], "available": True, "images": ["a", "b", "c"]})
        got = tt.fetch_store_product(STORE, "toilova-1", get=lambda url: (200, url, body))
        self.assertEqual(got, {"title": "TOILOVA", "price_minor_units": 29900, "compare_at_price_minor_units": 39900, "options": ["Size"],
                               "variant_count": 2, "available": True, "image_count": 3})
        self.assertIsNone(tt.fetch_store_product(STORE, "toilova-1", get=lambda url: (200, f"https://{STORE}/password", "<html>")))


class ClientRunAndPush(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        b, f = fixtures.toilova()
        (self.tmp / "brand.json").write_text(json.dumps(b), encoding="utf-8")
        (self.tmp / "facts.json").write_text(json.dumps(f), encoding="utf-8")
        self.out = self.tmp / "out"
        self.fake = FakeShopify()
        self.original = self.fake.files[tt.PRODUCT_TEMPLATE]

    def design(self, *extra):
        argv = ["--brand", str(self.tmp / "brand.json"), "--facts", str(self.tmp / "facts.json"), "--store", STORE, "--theme", THEME,
                "--out", str(self.out), "--no-browser", *extra]
        with contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()):
            code = run_client.main(argv, access=access(self.fake), get=lambda url: (404, url, ""))
        return code, printed.getvalue()

    def push(self, code, *extra, fake=None):
        argv = ["--out", str(self.out), "--approve", code, "--approved-by", "Harsh", *extra]
        with contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()) as err:
            rc = push_page.main(argv, access=access(fake or self.fake))
        return rc, printed.getvalue() + err.getvalue()

    def log(self):
        return [json.loads(l) for l in (self.out / "action-log.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_design_reads_only_and_writes_an_approval(self):
        code, printed = self.design()
        self.assertEqual(code, 2)  # not screenshot-reviewed in this test, so it asks for a person's look
        self.assertEqual(self.fake.pushed, [])
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        body = (self.out / "template.json").read_bytes()
        self.assertEqual(approval["template_sha256"], tt.sha256(body))
        self.assertTrue(approval["pushable"])
        self.assertEqual((approval["store"], approval["theme_id"], approval["plan"]), (STORE, THEME, "not-run"))
        self.assertIn(f"--approve {approval['approve_code']}", printed)
        self.assertTrue((self.out / "theme-before" / tt.PRODUCT_TEMPLATE).exists())
        self.assertEqual([r["result"] for r in self.log()], ["success", "recommended"])
        self.assertTrue((self.out / "graphics-todo.json").exists())

    def test_design_stops_on_a_live_theme(self):
        self.fake.role = "live"
        code, _ = self.design()
        self.assertEqual(code, 1)
        self.assertFalse((self.out / "approval.json").exists())
        self.assertEqual(self.log()[0]["result"], "blocked")

    def test_push_writes_exactly_the_approved_page_and_verifies_it(self):
        self.design()
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        rc, printed = self.push(approval["approve_code"], "--accept-review-findings")
        self.assertEqual(rc, 0, printed)
        self.assertEqual(self.fake.pushed, [tt.PRODUCT_TEMPLATE])
        self.assertEqual(self.fake.files[tt.PRODUCT_TEMPLATE].encode("utf-8"), (self.out / "template.json").read_bytes())
        row = self.log()[-1]
        self.assertEqual((row["tier"], row["mode"], row["result"], row["approved_by"]), (2, "approve", "success", "Harsh"))
        self.assertEqual(row["after"]["sha256"], approval["template_sha256"])
        backups = list(self.out.glob("backup-*/templates/product.json"))
        self.assertEqual(backups[0].read_text(encoding="utf-8"), self.original)
        self.assertIn("written and verified", printed)

    def test_a_page_with_samples_needs_an_explicit_yes_for_a_draft_preview(self):
        self.design()
        approval_path = self.out / "approval.json"
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        approval["samples"] = 3  # as run_client records when facts carry SAMPLE sources
        approval_path.write_text(json.dumps(approval), encoding="utf-8")
        rc, printed = self.push(approval["approve_code"], "--accept-review-findings")
        self.assertEqual(rc, 1)
        self.assertIn("SAMPLE", printed)
        self.assertEqual(self.fake.pushed, [])
        rc, printed = self.push(approval["approve_code"], "--accept-review-findings", "--allow-samples")
        self.assertEqual(rc, 0, printed)

    def test_push_refusals_write_nothing(self):
        self.design()
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        good = approval["approve_code"]
        rc, msg = self.push("000000000000", "--accept-review-findings")
        self.assertEqual(rc, 1)
        self.assertIn("does not match", msg)
        rc, msg = self.push(good)
        self.assertEqual(rc, 1)
        self.assertIn("--accept-review-findings", msg)
        live = FakeShopify(role="live")
        rc, msg = self.push(good, "--accept-review-findings", fake=live)
        self.assertEqual(rc, 1)
        self.assertIn("LIVE", msg)
        self.assertEqual(live.pushed, [])
        (self.out / "template.json").write_bytes((self.out / "template.json").read_bytes() + b" ")
        rc, msg = self.push(good, "--accept-review-findings")
        self.assertEqual(rc, 1)
        self.assertIn("changed after the approval", msg)
        self.assertEqual(self.fake.pushed, [])
        self.assertEqual([r["result"] for r in self.log()[2:]], ["blocked", "blocked", "failed", "blocked"])

    def test_a_page_with_test_pictures_needs_allow_demo(self):
        b, f = fixtures.toilova()
        f["demo"] = True
        (self.tmp / "facts.json").write_text(json.dumps(f), encoding="utf-8")
        self.design()
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        self.assertTrue(approval["demo"])
        rc, msg = self.push(approval["approve_code"], "--accept-review-findings")
        self.assertEqual(rc, 1)
        self.assertIn("TEST pictures", msg)
        self.assertEqual(self.fake.pushed, [])
        rc, _ = self.push(approval["approve_code"], "--accept-review-findings", "--allow-demo")
        self.assertEqual(rc, 0)

    def test_a_write_that_does_not_read_back_the_same_is_reported_as_failed(self):
        self.design()
        self.fake.tamper = True
        code = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))["approve_code"]
        rc, msg = self.push(code, "--accept-review-findings")
        self.assertEqual(rc, 1)
        self.assertIn("does not match", msg)
        self.assertEqual(self.log()[-1]["result"], "failed")

    def test_design_only_run_cannot_be_pushed(self):
        argv = ["--brand", str(self.tmp / "brand.json"), "--facts", str(self.tmp / "facts.json"), "--out", str(self.out),
                "--no-browser", "--no-theme-check"]
        with contextlib.redirect_stdout(io.StringIO()):
            run_client.main(argv)
        code = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))["approve_code"]
        rc, msg = self.push(code, "--accept-review-findings")
        self.assertEqual(rc, 1)
        self.assertIn("design-only", msg)

    def test_claude_code_answers_drive_the_design(self):
        from tests.test_ai_plan import answer as plan_answer

        (self.tmp / "plan-answer.json").write_text(json.dumps(plan_answer(["trust_marquee", "free_from", "faq"])), encoding="utf-8")
        code, printed = self.design("--plan", "answer", "--plan-answer", str(self.tmp / "plan-answer.json"), "--recipe", "pdp")
        self.assertEqual(code, 2)
        plan = json.loads((self.out / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["decided_by"], "claude code session plan (checked by code)")
        self.assertTrue((self.out / "plan-request.json").exists())
        self.assertTrue((self.out / "copy-request.json").exists())
        built = json.loads((self.out / "build-report.json").read_text(encoding="utf-8"))["sections_built"]
        self.assertEqual([s["kind"] for s in built], ["trust_marquee", "free_from", "faq"])
        self.assertEqual(self.fake.pushed, [])
        code, _ = self.design("--plan", "answer")  # no answer file: refuse, do not fall back silently
        self.assertEqual(code, 1)

    def test_the_fixed_standard_set_ignores_a_plans_section_choice(self):
        from tests.test_ai_plan import answer as plan_answer

        (self.tmp / "plan-answer.json").write_text(json.dumps(plan_answer(["trust_marquee", "free_from", "faq"])), encoding="utf-8")
        self.design("--plan", "answer", "--plan-answer", str(self.tmp / "plan-answer.json"))  # default recipe: dtj-standard-v1
        report = json.loads((self.out / "build-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["recipe"], "dtj-standard-v1")
        self.assertEqual(report["chosen_by"], "fixed set")
        self.assertNotIn("free_from", [s["kind"] for s in report["sections_built"]])  # not part of the fixed set, whatever a plan says

    def test_the_n8n_request_drives_a_run(self):
        b, f = fixtures.toilova()
        req = self.tmp / "request.json"
        req.write_text(json.dumps({"claude_code_stage": "page_design", "resume_url": "https://x", "request": {
            "row_id": 7, "status": "new", "brand_name": "TOILOVA", "store_domain": STORE, "theme_id": THEME, "brand": b, "facts": f}}),
            encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = run_client.main(["--intake", str(req), "--out", str(self.out), "--no-browser"], access=access(self.fake),
                                   get=lambda url: (404, url, ""))
        self.assertEqual(code, 2)
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        self.assertEqual((approval["store"], approval["theme_id"], approval["client"]), (STORE, THEME, "TOILOVA"))

    def test_a_dawn_theme_gets_a_new_template_in_its_own_layout(self):
        from tests.test_page_builder import DAWN
        self.fake = FakeShopify(base="Dawn", product=json.dumps(DAWN))
        code, printed = self.design("--template-suffix", "dtj-book")
        approval = json.loads((self.out / "approval.json").read_text(encoding="utf-8"))
        self.assertEqual((approval["file"], approval["layout"]), ("templates/product.dtj-book.json", "dawn"))
        page = json.loads((self.out / "template.json").read_text(encoding="utf-8"))
        self.assertEqual(page["sections"]["main"]["type"], "main-product")
        rc, msg = self.push(approval["approve_code"], "--accept-review-findings")
        self.assertEqual(rc, 0, msg)
        self.assertEqual(self.fake.pushed, ["templates/product.dtj-book.json"])  # a new page: the theme's product.json is untouched
        self.assertEqual(self.fake.files[tt.PRODUCT_TEMPLATE], json.dumps(DAWN))
        with self.assertRaises(ThemeError):
            tt.template_file("Bad Name")

    def test_intake_row_that_needs_fixes_is_refused(self):
        row = self.tmp / "row.json"
        row.write_text(json.dumps({"status": "needs-fixes", "problems": "Brand name is missing."}), encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            run_client.main(["--intake", str(row), "--out", str(self.out)])
        self.assertIn("fix the brief first", str(caught.exception))


if __name__ == "__main__":
    unittest.main()


class PushRefusalTests(unittest.TestCase):
    def test_a_push_shopify_partly_refuses_is_an_error_even_when_the_cli_exits_0(self):
        import subprocess
        out = ("Theme upload complete ...\n╭─ error ─╮\n│ templates/product.x.json │\n"
               "│ Setting 'overlay_opacity' must be a step in the range │\nThe theme 'Copy' (#1) was pushed with errors")
        access = tt.ThemeAccess("x.myshopify.com", "shptka_test", runner=lambda cmd, env: subprocess.CompletedProcess(cmd, 0, out, ""))
        with self.assertRaises(tt.ThemeError) as caught:
            access.push_product_template("1", tt.Path("."), "templates/product.x.json")
        self.assertIn("overlay_opacity", str(caught.exception))

    def test_a_pull_folder_looks_like_a_theme_so_the_cli_runs_without_a_person(self):
        import subprocess
        import tempfile
        seen = []
        access = tt.ThemeAccess("x.myshopify.com", None, runner=lambda cmd, env: seen.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""),
                                login=True)
        with tempfile.TemporaryDirectory() as tmp:
            access.pull("1", ["templates/product.json"], tt.Path(tmp) / "pull")
            self.assertEqual(sorted(p.name for p in (tt.Path(tmp) / "pull").iterdir()), ["config", "layout", "sections", "templates"])
        self.assertNotIn("--force", seen[0])

    def test_a_failed_pull_says_the_cli_error_not_its_boxes(self):
        import subprocess
        import tempfile
        box, gap = "─" * 78, " " * 78
        err = ('<claude-code-hint v="1" type="plugin" value="shopify-ai-toolkit@claude-plugins-official" />\n'
               f"╭─ warning {box}╮\n│{gap}│\n│  It doesn't seem like you're running this command in a theme directory.      │\n│{gap}│\n╰{box}╯\n"
               f"╭─ error {box}╮\n│{gap}│\n│  Request timed out: the theme files could not be listed.                     │\n╰{box}╯")
        access = tt.ThemeAccess("x.myshopify.com", "shptka_test", runner=lambda cmd, env: subprocess.CompletedProcess(cmd, 1, "", err))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(tt.ThemeError) as caught:
            access.pull("1", ["templates/product.json"], tt.Path(tmp))
        text = str(caught.exception)
        self.assertIn("failed (1): error Request timed out: the theme files could not be listed.", text)
        self.assertNotIn("claude-code-hint", text)
        self.assertNotIn("theme directory", text)

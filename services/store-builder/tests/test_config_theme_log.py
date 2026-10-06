import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from provision import config, theme
from provision.actionlog import ActionLog, scrub


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        c = config.load({})
        self.assertFalse(c.automation_enabled)
        self.assertTrue(c.dry_run)
        self.assertEqual(c.mode, "shadow")
        self.assertFalse(c.decide(1).allowed)
        self.assertFalse(c.decide(2, "Harsh").allowed)

    def test_auto_mode_is_refused(self):
        with self.assertRaises(config.ConfigError):
            config.load({"AUTOMATION_MODE": "auto"})

    def test_bad_domain_is_refused(self):
        with self.assertRaises(config.ConfigError):
            config.load({"SHOPIFY_DOMAIN": "example.com; rm -rf"})

    def live(self, **extra):
        env = {"AUTOMATION_ENABLED": "true", "DRY_RUN": "false", "AUTOMATION_MODE": "approve", **extra}
        return config.load(env)

    def test_tier2_needs_a_named_approver(self):
        c = self.live()
        self.assertFalse(c.decide(2).allowed)
        self.assertTrue(c.decide(2, "Harsh").allowed)

    def test_tier3_is_never_allowed(self):
        self.assertFalse(self.live().decide(3, "Harsh").allowed)

    def test_shadow_never_acts_even_when_live(self):
        self.assertFalse(self.live(AUTOMATION_MODE="shadow").decide(1).allowed)

    def test_tier0_always_allowed(self):
        self.assertTrue(config.load({}).decide(0).allowed)

    def test_token_name_and_missing_report(self):
        c = config.load({"CLIENT_ID": "acme-co", "SHOPIFY_DOMAIN": "acme.myshopify.com"})
        self.assertEqual(c.token_env_name(), "SHOPIFY_ADMIN_TOKEN_ACME_CO")
        with self.assertRaises(config.ConfigError):
            c.admin_token({})
        self.assertEqual(c.admin_token({"SHOPIFY_ADMIN_TOKEN_ACME_CO": "t"}), "t")
        self.assertIn("SHOPIFY_API_VERSION is not pinned", c.missing_for_live({}))
        self.assertFalse(hasattr(c, "token"))  # the token is read at call time, never kept on the object


class ThemeTests(unittest.TestCase):
    def test_new_theme_command(self):
        cmd = theme.push_new_unpublished_cmd("a.myshopify.com", "d", "Draft")
        self.assertIn("--unpublished", cmd)
        self.assertEqual(cmd[cmd.index("--theme") + 1], "Draft")
        self.assertNotIn("--live", cmd)

    def test_narrow_push_needs_files_and_numeric_id(self):
        with self.assertRaises(theme.ThemeError):
            theme.push_files_cmd("a.myshopify.com", "d", "123", [])
        with self.assertRaises(theme.ThemeError):
            theme.push_files_cmd("a.myshopify.com", "d", "live", ["templates/index.json"])
        cmd = theme.push_files_cmd("a.myshopify.com", "d", "123", ["templates/index.json", "templates/product.json"])
        self.assertIn("--nodelete", cmd)
        self.assertEqual(cmd.count("--only"), 2)

    def test_live_theme_is_refused(self):
        themes = [{"id": 1, "role": "live"}, {"id": 2, "role": "unpublished"}]
        with self.assertRaises(theme.ThemeError):
            theme.assert_not_live(themes, "1")
        with self.assertRaises(theme.ThemeError):
            theme.assert_not_live(themes, "999")  # unknown is refused too
        theme.assert_not_live(themes, "2")

    def test_push_result_must_report_an_unpublished_theme(self):
        ok = json.dumps({"theme": {"id": 5, "name": "x", "role": "unpublished"}})
        self.assertEqual(theme.parse_pushed_theme(ok)["id"], 5)
        for bad in ("not json", "{}", json.dumps({"theme": {"id": 5, "role": "live"}})):
            with self.assertRaises(theme.ThemeError):
                theme.parse_pushed_theme(bad)


class ActionLogTests(unittest.TestCase):
    def test_secrets_are_scrubbed_and_row_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            log = ActionLog(Path(d) / "a.jsonl", "acme")
            log.record(tier=2, mode="approve", target="theme", action="push", reason="r", result="dry_run",
                       evidence={"cmd": "x", "X-Shopify-Access-Token": "SECRET", "nested": [{"api_key": "SECRET"}]})
            text = (Path(d) / "a.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("SECRET", text)
            self.assertEqual(json.loads(text)["evidence"]["cmd"], "x")

    def test_malformed_row_is_not_written(self):
        with tempfile.TemporaryDirectory() as d:
            log = ActionLog(Path(d) / "a.jsonl", "acme")
            with self.assertRaises(ValidationError):
                log.record(tier=9, mode="approve", target="t", action="a", reason="r", result="success")
            self.assertFalse((Path(d) / "a.jsonl").exists())

    def test_scrub_leaves_normal_values(self):
        self.assertEqual(scrub({"a": 1, "b": [1, 2]}), {"a": 1, "b": [1, 2]})


if __name__ == "__main__":
    unittest.main()

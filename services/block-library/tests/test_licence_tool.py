import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import licence  # noqa: E402

ENV = {licence.SECRET_ENV: "SUPERSECRET"}


class FakeShopify:
    def __init__(self, token_status=200, current=None, user_errors=None, gql_status=200):
        self.calls, self.current, self.user_errors, self.token_status, self.gql_status = [], current, user_errors or [], token_status, gql_status

    def __call__(self, url, payload, headers=None):
        self.calls.append((url, payload, headers))
        if url.endswith("/oauth/access_token"):
            if self.token_status != 200:
                return self.token_status, {"error": "shop_not_permitted", "error_description": "Client credentials cannot be performed on this shop."}
            return 200, {"access_token": "TOKEN123", "expires_in": 86399}
        if self.gql_status != 200:
            return self.gql_status, {}
        if "metafieldsSet" in payload["query"]:
            self.current = payload["variables"]["metafields"][0]["value"]
            return 200, {"data": {"metafieldsSet": {"metafields": [], "userErrors": self.user_errors}}}
        return 200, {"data": {"shop": {"id": "gid://shopify/Shop/1"},
                              "currentAppInstallation": {"id": "gid://shopify/AppInstallation/9", "app": {"handle": "dtj-blocks"},
                                                         "licence": {"value": self.current} if self.current else None}}}


def run(args, shop=None, env=ENV):
    shop = shop or FakeShopify()
    with tempfile.TemporaryDirectory() as d, mock.patch("sys.stdout", new_callable=StringIO) as out, mock.patch("sys.stderr", new_callable=StringIO) as err:
        code = licence.main([*args, "--log", str(Path(d, "log.jsonl"))], env=env, post=shop, ask=False)  # False: never wait for a typed secret in tests
        log = Path(d, "log.jsonl").read_text(encoding="utf-8") if Path(d, "log.jsonl").exists() else ""
    return code, out.getvalue(), err.getvalue(), log, shop


S = ["--shop", "t.myshopify.com"]


class LicenceToolTests(unittest.TestCase):
    def test_status_is_read_only(self):
        code, out, _, log, shop = run([*S, "--status"], FakeShopify(current="active"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["licence"], "active")
        self.assertEqual(log, "")
        self.assertFalse(any("metafieldsSet" in (c[1] or {}).get("query", "") for c in shop.calls))

    def test_set_needs_a_named_approver(self):
        code, _, err, _, shop = run([*S, "--set", "inactive"])
        self.assertEqual(code, 2)
        self.assertIn("approved-by", err)
        self.assertEqual(shop.calls, [])

    def test_set_flips_the_flag_and_logs_it(self):
        code, out, _, log, shop = run([*S, "--set", "inactive", "--approved-by", "Harsh"], FakeShopify(current="active"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"before": "active", "after": "inactive"})
        row = json.loads(log)
        self.assertEqual((row["approved_by"], row["result"], row["tier"]), ("Harsh", "success", 2))
        sent = [c for c in shop.calls if "metafieldsSet" in (c[1] or {}).get("query", "")][0]
        mf = sent[1]["variables"]["metafields"][0]
        self.assertEqual((mf["ownerId"], mf["namespace"], mf["key"], mf["value"]),
                         ("gid://shopify/AppInstallation/9", "dtj", "licence", "inactive"))  # on the installation, not the shop

    def test_secret_and_token_never_appear_in_output_or_log(self):
        code, out, err, log, _ = run([*S, "--set", "active", "--approved-by", "Harsh"])
        for text in (out, err, log):
            self.assertNotIn("SUPERSECRET", text)
            self.assertNotIn("TOKEN123", text)

    def test_missing_secret_stops_before_any_call(self):
        code, _, err, _, shop = run([*S, "--status"], env={})
        self.assertEqual(code, 2)
        self.assertIn(licence.SECRET_ENV, err)
        self.assertEqual(shop.calls, [])

    def test_store_outside_the_org_gives_a_clear_message(self):
        code, _, err, _, _ = run([*S, "--status"], FakeShopify(token_status=400))
        self.assertEqual(code, 1)
        self.assertIn("same Shopify organization", err)

    def test_user_errors_are_a_failure_and_are_logged(self):
        shop = FakeShopify(user_errors=[{"field": ["metafields", "0"], "message": "nope", "code": "X"}])
        code, _, err, log, _ = run([*S, "--set", "active", "--approved-by", "Harsh"], shop)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(log)["result"], "failed")

    def test_other_mutations_and_deletes_are_refused(self):
        for q in ("mutation {\n  productDelete(input: {id: \"1\"}) { deletedProductId }\n}", "mutation {\n  themePublish(id: \"1\") { theme { id } }\n}"):
            with self.assertRaises(licence.LicenceError):
                licence.graphql("t.myshopify.com", "tok", q, post=FakeShopify())

    def test_bad_shop_name_is_refused(self):
        code, _, err, _, shop = run(["--shop", "evil.example.com", "--status"])
        self.assertEqual(code, 2)
        self.assertEqual(shop.calls, [])

    def test_client_id_is_read_from_the_toml(self):
        self.assertRegex(licence.client_id(), r"^[0-9a-f]{32}$")

    def test_the_sections_app_uses_its_own_secret_variable_never_the_blocks_one(self):
        # only the blocks secret is set: asking for the sections app must stop before any call, naming ITS variable
        code, _, err, _, shop = run([*S, "--status", "--app", "sections"])
        self.assertEqual(code, 2)
        self.assertIn("DTJ_SECTIONS_CLIENT_SECRET", err)
        self.assertEqual(shop.calls, [])

    def test_the_sections_app_needs_to_be_linked_before_its_flag_can_be_touched(self):
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d, "shopify.app.toml")
            with mock.patch.dict(licence.APPS, {"sections": (missing, "DTJ_SECTIONS_CLIENT_SECRET")}):
                code, _, err, _, shop = run([*S, "--status", "--app", "sections"], env={"DTJ_SECTIONS_CLIENT_SECRET": "OTHERSECRET"})
        self.assertEqual(code, 1)
        self.assertIn("link the app first", err)
        self.assertEqual(shop.calls, [])

    def test_the_second_sections_app_has_its_own_secret_variable_and_needs_linking(self):
        code, _, err, _, shop = run([*S, "--status", "--app", "sections2"], env={"DTJ_SECTIONS_CLIENT_SECRET": "NOT_THE_RIGHT_ONE"})
        self.assertEqual(code, 2)
        self.assertIn("DTJ_SECTIONS2_CLIENT_SECRET", err)
        self.assertEqual(shop.calls, [])
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d, "shopify.app.toml")
            with mock.patch.dict(licence.APPS, {"sections2": (missing, "DTJ_SECTIONS2_CLIENT_SECRET")}):
                code, _, err, _, shop = run([*S, "--status", "--app", "sections2"], env={"DTJ_SECTIONS2_CLIENT_SECRET": "THIRD"})
        self.assertEqual(code, 1)
        self.assertIn("link the app first", err)
        self.assertEqual(shop.calls, [])

    def test_the_sections_app_uses_its_own_client_id_and_secret(self):
        with tempfile.TemporaryDirectory() as d:
            toml = Path(d, "shopify.app.toml")
            toml.write_text('client_id = "' + "ab" * 16 + '"\n', encoding="utf-8")
            with mock.patch.dict(licence.APPS, {"sections": (toml, "DTJ_SECTIONS_CLIENT_SECRET")}):
                code, out, err, log, shop = run([*S, "--status", "--app", "sections"], FakeShopify(current="active"), env={"DTJ_SECTIONS_CLIENT_SECRET": "OTHERSECRET"})
        self.assertEqual(code, 0)
        token_call = [c for c in shop.calls if c[0].endswith("/oauth/access_token")][0]
        self.assertIn("ab" * 16, json.dumps(token_call[1]))
        self.assertIn("OTHERSECRET", json.dumps(token_call[1]))
        self.assertNotIn("OTHERSECRET", out + err + log)

    def _three_apps(self, d):  # name kept: it now builds one temporary entry for EVERY registered app
        apps = {}
        for i, (name, (_, var)) in enumerate(dict(licence.APPS).items()):
            toml = Path(d, f"{name}.toml")
            toml.write_text('client_id = "' + f"{i + 1:02x}" * 16 + '"\n', encoding="utf-8")
            apps[name] = (toml, var)
        return apps

    def test_all_apps_in_one_go_each_with_its_own_secret(self):
        env = {licence.SECRET_ENV: "SECRET_ONE", "DTJ_SECTIONS_CLIENT_SECRET": "SECRET_TWO", "DTJ_SECTIONS2_CLIENT_SECRET": "SECRET_THREE", "DTJ_HEROES_CLIENT_SECRET": "SECRET_FOUR"}
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(licence.APPS, self._three_apps(d)):
            code, out, err, log, shop = run([*S, "--set", "inactive", "--approved-by", "Harsh", "--app", "all"], FakeShopify(current="active"), env=env)
        self.assertEqual(code, 0)
        tokens = [json.dumps(c[1]) for c in shop.calls if c[0].endswith("/oauth/access_token")]
        self.assertEqual(len(tokens), 4)
        for secret in ("SECRET_ONE", "SECRET_TWO", "SECRET_THREE", "SECRET_FOUR"):
            self.assertEqual(sum(secret in t for t in tokens), 1)  # every app used ITS secret, once
            self.assertNotIn(secret, out + err + log)
        self.assertEqual(len(log.strip().splitlines()), 4)  # one log row per app
        self.assertEqual({json.loads(line)["app_key"] for line in out.strip().splitlines()}, {"blocks", "sections", "sections2", "heroes"})

    def test_one_missing_secret_does_not_stop_the_other_apps_and_the_run_is_not_a_success(self):
        env = {licence.SECRET_ENV: "SECRET_ONE", "DTJ_SECTIONS2_CLIENT_SECRET": "SECRET_THREE", "DTJ_HEROES_CLIENT_SECRET": "SECRET_FOUR"}
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(licence.APPS, self._three_apps(d)):
            code, out, err, _, shop = run([*S, "--status", "--app", "all"], FakeShopify(current="active"), env=env)
        self.assertEqual(code, 2)
        self.assertIn("DTJ_SECTIONS_CLIENT_SECRET", err)
        self.assertEqual(len(out.strip().splitlines()), 3)

    def test_a_missing_secret_is_asked_for_hidden_and_never_saved(self):
        asked = []
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(licence.APPS, self._three_apps(d)),                 mock.patch("sys.stdout", new_callable=StringIO) as out, mock.patch("sys.stderr", new_callable=StringIO) as err:
            code = licence.main([*S, "--status", "--app", "all", "--log", str(Path(d, "log.jsonl"))], env={},
                                post=FakeShopify(current="active"), ask=lambda prompt: asked.append(prompt) or "TYPED_SECRET")
        self.assertEqual(code, 0)
        self.assertEqual(len(asked), 4)
        self.assertTrue(all("never saved" in a for a in asked))
        self.assertNotIn("TYPED_SECRET", out.getvalue() + err.getvalue())

    def test_all_still_needs_a_named_approver_to_change_anything(self):
        code, _, err, _, shop = run([*S, "--set", "inactive", "--app", "all"])
        self.assertEqual(code, 2)
        self.assertIn("--approved-by", err)
        self.assertEqual(shop.calls, [])


if __name__ == "__main__":
    unittest.main()

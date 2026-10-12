"""Tests for add_client.py (per-client app files) and deploy.py (secrets and deploy). A stand-in runs instead of wrangler: nothing reaches
Cloudflare or Shopify.  Run: python -m unittest discover -s services/install-catcher/test -p "test_*.py"
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
import add_client  # noqa: E402
import deploy  # noqa: E402
import client_registry  # noqa: E402
import licence_call  # noqa: E402

IDS = {"blocks": "a" * 32, "sections": "b" * 32, "sections2": "c" * 32}


def blank_wrangler() -> str:
    """The real wrangler.toml with no clients and no storage yet (the live file holds real clients: tests never depend on it)."""
    import re
    text = (HERE / "wrangler.toml").read_text(encoding="utf-8")
    text = re.sub(r'^id = "[0-9a-f]{32}"', 'id = "REPLACE_WITH_KV_ID"', text, flags=re.M)
    return add_client.set_apps(text, {})
WORKER = "https://dtj-install-catcher.dtj.workers.dev"
SHOP = "royal-dosa.myshopify.com"


class AddClient(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for folder, _ in add_client.APPS.values():
            (self.tmp / folder).mkdir()
            (self.tmp / folder / "shopify.app.toml").write_text("ours, untouched", encoding="utf-8")
        self.wrangler = self.tmp / "wrangler.toml"
        self.wrangler.write_text(blank_wrangler(), encoding="utf-8")

    def add(self, **over):
        args = {"--shop": SHOP, "--label": "Royal Dosa", "--worker": WORKER, **{f"--{p}-id": v for p, v in IDS.items()}, **over}
        return add_client.main([x for kv in args.items() for x in kv], services=self.tmp, wrangler=self.wrangler)

    def test_three_copies_point_at_the_catcher_and_ask_for_no_data(self):
        self.add()
        text = (self.tmp / "block-library" / "shopify.app.royal-dosa.toml").read_text(encoding="utf-8")
        for expected in (f'client_id = "{"a" * 32}"', 'name = "DTJ Blocks - Royal Dosa"', f'application_url = "{WORKER}/start/royal-dosa-blocks"',
                         "embedded = false", 'scopes = ""', f'redirect_urls = [ "{WORKER}/callback/royal-dosa-blocks" ]',
                         'topics = [ "app/uninstalled" ]', f'uri = "{WORKER}/webhooks/royal-dosa-blocks"'):
            self.assertIn(expected, text)
        self.assertIn("/start/royal-dosa-sections2", (self.tmp / "block-library-sections-2" / "shopify.app.royal-dosa.toml").read_text(encoding="utf-8"))
        for folder, _ in add_client.APPS.values():  # our current apps are never touched
            self.assertEqual((self.tmp / folder / "shopify.app.toml").read_text(encoding="utf-8"), "ours, untouched")
        apps = add_client.current_apps(self.wrangler.read_text(encoding="utf-8"))
        self.assertEqual(sorted(apps), ["royal-dosa-blocks", "royal-dosa-sections", "royal-dosa-sections2"])
        self.assertEqual(apps["royal-dosa-sections"], {"client_id": "b" * 32, "shop": SHOP, "label": "DTJ Sections - Royal Dosa"})

    def test_bad_inputs_are_refused(self):
        with self.assertRaises(SystemExit):
            self.add(**{"--blocks-id": "not-a-client-id"})
        with self.assertRaises(SystemExit):
            self.add(**{"--shop": "royaldosa.com"})
        with self.assertRaises(SystemExit):
            self.add(**{"--worker": "http://insecure.example"})

    def test_a_renamed_store_keeps_its_original_address_but_a_readable_name(self):
        self.add(**{"--shop": "qaxv3r-8g.myshopify.com", "--name": "royal-test"})
        text = (self.tmp / "block-library" / "shopify.app.royal-test.toml").read_text(encoding="utf-8")
        self.assertIn(f'application_url = "{WORKER}/start/royal-test-blocks"', text)
        apps = add_client.current_apps(self.wrangler.read_text(encoding="utf-8"))
        self.assertEqual(apps["royal-test-blocks"]["shop"], "qaxv3r-8g.myshopify.com")  # what Shopify sends, so what the catcher pins
        with self.assertRaises(SystemExit):
            self.add(**{"--name": "Royal Test"})

    def test_secret_variable_names_match_what_harsh_was_told(self):
        self.assertEqual(add_client.secret_env("royal-dosa", "blocks"), "DTJ_SECRET_ROYAL_DOSA_BLOCKS")
        self.assertEqual(add_client.secret_env("royal-dosa", "sections2"), "DTJ_SECRET_ROYAL_DOSA_SECTIONS2")


class FakeWrangler:
    def __init__(self, existing=(), new_worker=False):
        self.calls, self.existing, self.new_worker = [], list(existing), new_worker

    def __call__(self, cmd, env, stdin):
        self.calls.append((list(cmd), stdin, dict(env)))
        args = cmd[3:]
        out = ""
        if args[:3] == ["kv", "namespace", "create"]:
            out = 'Add the following to your configuration file:\n[[kv_namespaces]]\nbinding = "VAULT"\nid = "' + "f" * 32 + '"'
        elif args[:2] == ["secret", "list"]:
            if self.new_worker and not any(c[0][3:4] == ["deploy"] for c in self.calls):
                return subprocess.CompletedProcess(cmd, 1, "", 'X [ERROR] Worker "dtj-install-catcher" not found.')
            out = json.dumps([{"name": n, "type": "secret_text"} for n in self.existing])
        elif args[:1] == ["deploy"]:
            out = "Uploaded dtj-install-catcher\n  https://dtj-install-catcher.dtj.workers.dev\nCurrent Version ID: x"
        return subprocess.CompletedProcess(cmd, 0, out, "")


class Deployment(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.toml = self.tmp / "wrangler.toml"
        text = blank_wrangler()
        apps = {f"royal-dosa-{p}": {"client_id": IDS[p], "shop": SHOP, "label": p} for p in IDS}
        self.toml.write_text(add_client.set_apps(text, apps), encoding="utf-8")
        self.env = {"CLOUDFLARE_API_TOKEN": "cf-token-SECRET", "CLOUDFLARE_ACCOUNT_ID": "acc123",
                    **{add_client.secret_env("royal-dosa", p): f"shpss_client_secret_{p}" for p in IDS}}
        self.saved = {}

    def deployer(self, fake, env=None, dry=False):
        return deploy.Deploy(runner=fake, environ=env or self.env, save=self.saved.__setitem__, wrangler_toml=self.toml, dry_run=dry)

    def test_secrets_only_travel_through_stdin_and_the_catcher_keys_are_backed_up(self):
        fake = FakeWrangler()
        url = self.deployer(fake).run()
        self.assertEqual(url, "https://dtj-install-catcher.dtj.workers.dev")
        self.assertIn("f" * 32, self.toml.read_text(encoding="utf-8"))  # storage id written
        secret_values = list(self.env.values())[2:] + list(self.saved.values()) + ["cf-token-SECRET"]
        for cmd, stdin, env in fake.calls:
            for value in secret_values:
                self.assertNotIn(value, " ".join(cmd))
        puts = {cmd[5]: stdin for cmd, stdin, _ in fake.calls if cmd[3:5] == ["secret", "put"]}
        self.assertEqual(puts["SECRET_ROYAL_DOSA_BLOCKS"], "shpss_client_secret_blocks")
        self.assertEqual(set(puts), {"VAULT_KEY", "CONTROL_KEY", "BOT_KEY", "SECRET_ROYAL_DOSA_BLOCKS", "SECRET_ROYAL_DOSA_SECTIONS", "SECRET_ROYAL_DOSA_SECTIONS2"})
        self.assertEqual(puts["BOT_KEY"], self.saved["DTJ_CATCHER_BOT_KEY"])
        self.assertEqual(len(puts["BOT_KEY"]), 64)  # 32 random bytes as hex: the catcher wants 32+ characters
        self.assertEqual(puts["VAULT_KEY"], self.saved["DTJ_CATCHER_VAULT_KEY"])
        self.assertEqual(len(__import__("base64").b64decode(puts["VAULT_KEY"])), 32)
        self.assertEqual(fake.calls[-1][0][3], "deploy")
        self.assertEqual(fake.calls[0][2]["CLOUDFLARE_API_TOKEN"], "cf-token-SECRET")  # the login goes by environment only

    def test_a_new_worker_is_deployed_before_its_secrets_are_set(self):
        fake = FakeWrangler(new_worker=True)
        url = self.deployer(fake).run()
        self.assertEqual(url, "https://dtj-install-catcher.dtj.workers.dev")
        steps = [c[0][3] if c[0][3] != "secret" else f"secret {c[0][4]}" for c in fake.calls]
        self.assertEqual(steps[:3], ["kv", "secret list", "deploy"])  # first deploy creates the Worker
        self.assertEqual(steps[-1], "deploy")  # and the last one ships code and secrets together
        self.assertEqual(steps.count("secret put"), 6)

    def test_other_wrangler_errors_still_stop(self):
        class Broken(FakeWrangler):
            def __call__(self, cmd, env, stdin):
                if cmd[3:5] == ["secret", "list"]:
                    return subprocess.CompletedProcess(cmd, 1, "", "Authentication error [code: 10000]")
                return super().__call__(cmd, env, stdin)
        with self.assertRaises(SystemExit):
            self.deployer(Broken()).run()

    def test_existing_catcher_keys_are_reused_not_replaced(self):
        env = {**self.env, "DTJ_CATCHER_VAULT_KEY": "kept-vault", "DTJ_CATCHER_CONTROL_KEY": "kept-control", "DTJ_CATCHER_BOT_KEY": "k" * 64}
        fake = FakeWrangler(existing=["VAULT_KEY", "CONTROL_KEY", "BOT_KEY"])
        self.deployer(fake, env).run()
        names = [cmd[5] for cmd, _, _ in fake.calls if cmd[3:5] == ["secret", "put"]]
        self.assertNotIn("VAULT_KEY", names)  # replacing it would make every stored store key unreadable
        self.assertEqual(self.saved, {})

    def test_an_older_catcher_without_a_bot_key_gets_one_and_keeps_its_other_keys(self):
        env = {**self.env, "DTJ_CATCHER_VAULT_KEY": "kept-vault", "DTJ_CATCHER_CONTROL_KEY": "kept-control"}
        fake = FakeWrangler(existing=["VAULT_KEY", "CONTROL_KEY"])  # deployed on 9 Oct, before the bot existed
        self.deployer(fake, env).run()
        names = [cmd[5] for cmd, _, _ in fake.calls if cmd[3:5] == ["secret", "put"]]
        self.assertIn("BOT_KEY", names)
        self.assertNotIn("VAULT_KEY", names)
        self.assertNotIn("CONTROL_KEY", names)
        self.assertEqual(set(self.saved), {"DTJ_CATCHER_BOT_KEY"})  # only the new key gets a local backup

    def test_a_key_set_in_cloudflare_without_its_local_backup_stops_everything(self):
        fake = FakeWrangler(existing=["VAULT_KEY"])
        with self.assertRaises(SystemExit):
            self.deployer(fake).run()
        self.assertFalse([c for c in fake.calls if c[0][3] == "deploy"])

    def test_a_missing_client_secret_stops_before_anything_runs(self):
        env = dict(self.env)
        del env[add_client.secret_env("royal-dosa", "sections")]
        fake = FakeWrangler()
        with self.assertRaises(SystemExit):
            self.deployer(fake, env).run()
        self.assertEqual(fake.calls, [])

    def test_dry_run_runs_nothing(self):
        fake = FakeWrangler()
        d = self.deployer(fake, dry=True)
        d.run()
        self.assertEqual(fake.calls, [])
        self.assertTrue(any("deploy" in line for line in d.log))
        self.assertFalse(any("shpss_" in line or "cf-token" in line for line in d.log))


class FakeResponse:
    def __init__(self, status, body):
        self.status, self._body = status, json.dumps(body).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class LicenceCall(unittest.TestCase):
    def test_the_request_is_signed_with_the_control_key_and_never_carries_it(self):
        seen = []

        def opener(req, timeout):
            seen.append(req)
            return FakeResponse(200, {"licence": "active"})
        code, data = licence_call.call("royal-dosa-blocks", "status", key="k" * 64, opener=opener)
        self.assertEqual((code, data), (200, {"licence": "active"}))
        req = seen[0]
        expected = __import__("hmac").new(b"k" * 64, req.data, "sha256").hexdigest()
        self.assertEqual(req.get_header("X-dtj-signature"), expected)
        self.assertNotIn("k" * 64, req.data.decode())
        self.assertNotIn("Python-urllib", req.get_header("User-agent"))

    def test_a_change_needs_a_named_approver(self):
        with self.assertRaises(SystemExit):
            licence_call.call("royal-dosa-blocks", "inactive", key="k", opener=lambda *a, **k: None)

    def test_server_errors_are_retried_at_most_three_times(self):
        import urllib.error
        calls = []

        def opener(req, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, __import__("io").BytesIO(b"busy"))
        code, _ = licence_call.call("royal-dosa-blocks", "status", key="k", opener=opener, sleep=lambda s: None)
        self.assertEqual((code, len(calls)), (503, 4))


class ClientRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.wrangler = self.tmp / "wrangler.toml"
        apps = {f"royal-dosa-{p}": {"client_id": IDS[p], "shop": "qaxv3r-8g.myshopify.com", "label": f"{add_client.APPS[p][1]} - Royal Dosa"}
                for p in IDS}
        self.wrangler.write_text(add_client.set_apps(blank_wrangler(), apps), encoding="utf-8")
        for i, (part, (folder, display)) in enumerate(add_client.APPS.items()):
            d = self.tmp / folder / ".shopify" / "deploy-bundle"
            d.mkdir(parents=True)
            (d / "manifest.json").write_text(json.dumps({"name": f"{display} - Royal Dosa", "modules": [
                {"type": "app_access", "uuid": "x"}, {"type": "theme_app_extension", "handle": "dtj", "uuid": f"01a120c{i}-0000-7000-8000-000000000000"}]}))

    def build(self, status):
        return client_registry.build("royal-dosa", status, services=self.tmp, wrangler=self.wrangler, clients_dir=self.tmp / "clients")

    def test_uuids_come_from_the_release_record_and_handles_from_the_store(self):
        data = self.build(lambda key: {"app_handle": key.replace("royal-dosa-", "dtj-") + "-royal-dosa"})
        self.assertEqual(data["store"], "qaxv3r-8g.myshopify.com")
        self.assertEqual(data["apps"]["dtj-blocks"], {"handle": "dtj-blocks-royal-dosa", "uuid": "01a120c0-0000-7000-8000-000000000000"})
        self.assertEqual(data["apps"]["dtj-sections-2"]["uuid"], "01a120c2-0000-7000-8000-000000000000")
        self.assertTrue((self.tmp / "clients" / "royal-dosa.json").is_file())

    def test_before_the_install_the_handle_is_pending(self):
        data = self.build(lambda key: {})
        self.assertEqual({e["handle"] for e in data["apps"].values()}, {"pending"})

    def test_another_clients_release_record_is_refused(self):
        m = self.tmp / "block-library" / ".shopify" / "deploy-bundle" / "manifest.json"
        m.write_text(json.dumps({"name": "DTJ Blocks - Rupa Divine", "modules": []}))
        with self.assertRaises(SystemExit):
            self.build(lambda key: {})


if __name__ == "__main__":
    unittest.main()

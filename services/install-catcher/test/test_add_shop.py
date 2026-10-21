"""add_shop.py: a client shop end to end with one command (Harsh, 21 Oct 2026). Stand-ins for the Shopify CLI, Telegram, n8n and the
install service: nothing reaches Shopify or Cloudflare.

    python -m unittest discover -s services/install-catcher/test -p "test_*.py"
"""
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE / "test"))
import add_client  # noqa: E402
import add_shop  # noqa: E402
from test_tools import blank_wrangler  # noqa: E402

SHOP = "royal-dosa.myshopify.com"


class FakeCli:
    """The Shopify CLI: app init writes a new app's file, env show prints a secret, the rest answer 0. fail_on = a word that makes it fail."""

    def __init__(self, fail_on=None):
        self.calls, self.fail_on, self.n = [], fail_on, 0

    def __call__(self, cmd):
        self.calls.append(cmd)
        line = " ".join(cmd)
        if self.fail_on and self.fail_on in line:
            return subprocess.CompletedProcess(cmd, 1, "", f"Error: {self.fail_on} refused SHOPIFY_API_SECRET=shpss_leak")
        if cmd[1:3] == ["app", "init"]:
            self.n += 1
            folder = Path(cmd[cmd.index("--path") + 1]) / "new-app"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "shopify.app.toml").write_text(f'client_id = "{self.n:032x}"\nname = "x"\n', encoding="utf-8")
        if cmd[1:4] == ["app", "env", "show"]:
            folder = Path(cmd[cmd.index("--path") + 1]).name
            return subprocess.CompletedProcess(cmd, 0, f"SHOPIFY_API_KEY=abc\nSHOPIFY_API_SECRET=shpss_secret_{folder}\nSCOPES=\n", "")
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    def count(self, words):
        return sum(1 for c in self.calls if " ".join(c[1:]).startswith(words))


class Job(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for folder, _ in add_client.APPS.values():
            (self.tmp / folder).mkdir()
            (self.tmp / folder / "shopify.app.toml").write_text("ours, untouched", encoding="utf-8")
        self.wrangler = self.tmp / "wrangler.toml"
        self.wrangler.write_text(blank_wrangler(), encoding="utf-8")
        self.saved, self.sent, self.rows, self.deploys, self.installed, self.registries = {}, [], [], [], {}, []
        self.out = io.StringIO()

    def job(self, cli, **kw):
        return add_shop.AddShop(SHOP, "Royal Dosa", chat=kw.pop("chat", "555"), theme=kw.pop("theme", ""), approved_by="Harsh",
                                cli=cli, save=self.saved.__setitem__, status=lambda key: self.installed.get(key),
                                telegram=lambda m, d: self.sent.append((m, d)), n8n=self.rows.append, services=self.tmp,
                                wrangler=self.wrangler, state_dir=self.tmp / "state", deploy_catcher=lambda: self.deploys.append(1) or 0,
                                registry=self.registries.append, out=lambda *a: print(*a, file=self.out), sleep=lambda s: None, **kw)

    def links(self, job):
        return [f"{p}=https://admin.shopify.com/oauth/install_custom_app?client_id={job.s['ids'][p]}&no_redirect=true&signature=abc"
                for p in add_client.APPS]

    def test_one_command_does_everything_a_script_may_and_waits_for_the_install_links(self):
        cli = FakeCli()
        job = self.job(cli)
        self.assertEqual(job.run(), add_shop.WAITING)
        self.assertEqual(cli.count("app init"), 7)
        self.assertEqual(cli.count("app config link"), 7)
        self.assertEqual(cli.count("app env show"), 7)
        self.assertEqual(cli.count("app deploy"), 7)
        self.assertEqual(self.deploys, [1])  # the install service once, after the releases
        init = next(c for c in cli.calls if c[1:3] == ["app", "init"])
        self.assertEqual(init[init.index("--organization-id") + 1], add_shop.ORG_ID)
        self.assertIn("--no-input", init)
        self.assertEqual(init[init.index("--name") + 1], "DTJ Blocks - Royal Dosa")
        # the copies' settings are ours after the link (the link pulls Shopify's defaults first)
        text = (self.tmp / "block-library-collection" / "shopify.app.royal-dosa.toml").read_text(encoding="utf-8")
        self.assertIn(f"{add_shop.WORKER}/start/royal-dosa-collection", text)
        self.assertEqual(sorted(add_client.current_apps(self.wrangler.read_text(encoding="utf-8"))), sorted(f"royal-dosa-{p}" for p in add_client.APPS))
        self.assertEqual(set(self.saved), {add_client.secret_env("royal-dosa", p) for p in add_client.APPS})
        self.assertIn("waiting for the install links", self.out.getvalue())

    def test_secrets_go_only_into_the_windows_variables(self):
        cli = FakeCli()
        job = self.job(cli)
        job.run()
        secrets = list(self.saved.values())
        self.assertTrue(all(v.startswith("shpss_secret_") for v in secrets))
        state = (self.tmp / "state" / "royal-dosa.json").read_text(encoding="utf-8")
        for v in secrets:
            self.assertNotIn(v, state)
            self.assertNotIn(v, self.out.getvalue())

    def test_the_links_the_buttons_the_installs_and_the_shop_list(self):
        job = self.job(FakeCli())
        job.run()
        job.add_links(self.links(job))
        self.installed = {f"royal-dosa-{p}": {"app_handle": f"dtj-{p}-royal-dosa", "licence": "active"} for p in add_client.APPS}
        self.assertEqual(job.run(), 0)
        method, data = self.sent[0]
        self.assertEqual(method, "sendMessage")
        buttons = [row[0] for row in data["reply_markup"]["inline_keyboard"]]
        self.assertEqual([b["text"] for b in buttons], [f"Install {d}" for _f, d in add_client.APPS.values()])
        self.assertEqual(self.registries, ["royal-dosa"])
        row = self.rows[0]
        self.assertEqual((row["myshopify_domain"], row["client_registry"], row["active"]), (SHOP, "page_builder/clients/royal-dosa.json", False))
        self.assertEqual(job.run(), 0)  # a second run changes nothing and sends nothing again
        self.assertEqual((len(self.sent), len(self.rows)), (1, 1))

    def test_a_shop_with_its_draft_theme_is_active_on_the_list(self):
        job = self.job(FakeCli(), theme="1234567890")
        job.run()
        job.add_links(self.links(job))
        self.installed = {f"royal-dosa-{p}": {"app_handle": "h"} for p in add_client.APPS}
        job.run()
        self.assertEqual((self.rows[0]["draft_theme_id"], self.rows[0]["active"]), ("1234567890", True))

    def test_a_failure_stops_cleanly_and_the_next_run_continues_where_it_stopped(self):
        bad = FakeCli(fail_on="Royal Dosa copy")  # the release message: every release fails
        job = self.job(bad)
        self.assertEqual(job.run(), 1)
        self.assertIn("stopped:", self.out.getvalue())
        self.assertNotIn("shpss_leak", self.out.getvalue())  # a secret in the CLI's error text is hidden
        good = FakeCli()
        again = self.job(good)
        self.assertEqual(again.run(), add_shop.WAITING)
        self.assertEqual(good.count("app init"), 0)  # the copies are not made twice
        self.assertEqual(good.count("app deploy"), 7)

    def test_an_install_link_of_another_app_is_refused(self):
        job = self.job(FakeCli())
        job.run()
        wrong = f"blocks=https://admin.shopify.com/oauth/install_custom_app?client_id={job.s['ids']['heroes']}&signature=x"
        with self.assertRaises(add_shop.Failed):
            job.add_links([wrong])
        with self.assertRaises(add_shop.Failed):
            job.add_links(["banners=https://admin.shopify.com/x?client_id=" + "a" * 32])

    def test_installs_still_missing_after_the_wait_say_so_and_keep_the_state(self):
        job = self.job(FakeCli())
        job.run()
        job.add_links(self.links(job))
        self.installed = {"royal-dosa-blocks": {"app_handle": "h"}, "royal-dosa-heroes": {"app_handle": "h2"}}
        self.assertEqual(job.run(wait_minutes=0), add_shop.WAITING)
        self.assertIn("2 of 7 installed so far", self.out.getvalue())
        self.assertEqual(sorted(json.loads((self.tmp / "state" / "royal-dosa.json").read_text(encoding="utf-8"))["installed"]), ["blocks", "heroes"])

    def test_copies_already_in_the_repo_are_reused_when_the_state_is_lost(self):
        first = FakeCli()
        self.job(first).run()
        ids = json.loads((self.tmp / "state" / "royal-dosa.json").read_text(encoding="utf-8"))["ids"]
        (self.tmp / "state" / "royal-dosa.json").unlink()  # another laptop, or .work cleaned
        second = FakeCli()
        again = self.job(second)
        self.assertEqual(again.run(), add_shop.WAITING)
        self.assertEqual(second.count("app init"), 0)  # never a second set of apps in the Dev Dashboard
        self.assertEqual(again.s["ids"], ids)

    def test_every_run_leaves_the_answer_for_n8n(self):
        answer = self.tmp / "state" / "royal-dosa.answer.json"
        job = self.job(FakeCli())
        job.run()
        body = json.loads(answer.read_text(encoding="utf-8"))
        self.assertEqual((body["shop_status"], body["installed"], body["shop"]), ("waiting for installs", 0, SHOP))
        self.assertIn("install link", body["note"])
        job.add_links(self.links(job))
        self.installed = {f"royal-dosa-{p}": {"app_handle": "h"} for p in add_client.APPS}
        job.run()
        self.assertEqual(json.loads(answer.read_text(encoding="utf-8"))["shop_status"], "done")
        self.assertEqual(self.job(FakeCli(fail_on="Royal Dosa copy"), name="royal-dosa-2").run(), 1)
        failed = json.loads((self.tmp / "state" / "royal-dosa-2.answer.json").read_text(encoding="utf-8"))
        self.assertEqual(failed["shop_status"], "could not add")
        self.assertNotIn("shpss_leak", failed["note"])

    def test_only_an_original_store_address_is_taken(self):
        with self.assertRaises(add_shop.Failed):
            add_shop.AddShop("royaldosa.com", "Royal Dosa", state_dir=self.tmp / "state")


if __name__ == "__main__":
    unittest.main()

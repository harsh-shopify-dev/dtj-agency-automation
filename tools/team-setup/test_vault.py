"""vault.py against a stand-in Bitwarden command-line tool (no network, no real vault, no Windows settings touched).

    python -m unittest discover -s tools/team-setup -t tools/team-setup
"""
import base64
import contextlib
import io
import json
import subprocess
import unittest

import vault

VAULT_KEY = "VAULTKEY-must-never-be-printed-0123456789abcdef"
THEME = "shptka_THEME-must-never-be-printed-12345"
ORG = "org-1"
COLS = {vault.DESIGNERS: "col-designers", vault.DEVELOPERS: "col-developers"}


class FakeBw:
    """Answers the bw commands vault.py uses, from memory; refuses anything else."""

    def __init__(self, status="unlocked", visible=(vault.DESIGNERS, vault.DEVELOPERS), items=()):
        self.state, self.visible, self.items, self.calls, self.n = status, visible, list(items), [], 0

    def __call__(self, cmd, stdin, env):
        self.calls.append((cmd, stdin))
        args = cmd[1:]
        ok = lambda out: subprocess.CompletedProcess(cmd, 0, out, "")  # noqa: E731
        if args == ["status"]:
            return ok(json.dumps({"status": self.state}))
        if args == ["sync"]:
            return ok("Syncing complete.")
        if args == ["list", "organizations"]:
            return ok(json.dumps([{"id": ORG, "name": "DTJ"}]))
        if args[:2] == ["list", "org-collections"]:
            return ok(json.dumps([{"id": COLS[n], "name": n, "organizationId": ORG} for n in self.visible]))
        if args[:3] == ["list", "items", "--collectionid"]:
            return ok(json.dumps([i for i in self.items if args[3] in i["collectionIds"]]))
        if args == ["get", "template", "item"]:
            return ok(json.dumps({"organizationId": None, "collectionIds": None, "folderId": None, "type": 1, "name": "Item name",
                                  "notes": "Some notes", "favorite": False, "fields": [], "login": None, "reprompt": 0}))
        if args[:2] == ["create", "item"]:
            item = json.loads(base64.b64decode(stdin))
            self.n += 1
            self.items.append({**item, "id": f"item-{self.n}"})
            return ok(json.dumps({"id": f"item-{self.n}"}))
        if args[:2] == ["edit", "item"]:
            item = json.loads(base64.b64decode(stdin))
            self.items = [item if i["id"] == args[2] else i for i in self.items]
            return ok("{}")
        return subprocess.CompletedProcess(cmd, 1, "", f"unknown command {args}")


def item(name, value, col=vault.DEVELOPERS, iid=None):
    return {"id": iid or f"id-{name}", "name": name, "type": 1, "organizationId": ORG, "collectionIds": [COLS[col]],
            "login": {"password": value}}


class Vault(unittest.TestCase):
    def run_main(self, fake, local, *argv, unlock=None):
        saved, out, err = {}, io.StringIO(), io.StringIO()
        v = vault.Vault(runner=fake, unlock=unlock or (lambda env: "session-key-from-bitwarden"), environ={})
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vault.main(list(argv), vault=v, local=local, save=saved.__setitem__)
        text = out.getvalue() + err.getvalue()
        for secret in (VAULT_KEY, THEME, "session-key-from-bitwarden"):
            self.assertNotIn(secret, text)  # never on screen
        for cmd, _stdin in fake.calls:
            self.assertFalse(any(VAULT_KEY in a or THEME in a for a in cmd))  # never on a command line
        return code, text, saved, v

    def test_push_backs_up_the_irreplaceable_key_into_the_developers_collection_through_stdin(self):
        fake = FakeBw()
        code, text, _, _ = self.run_main(fake, {"DTJ_CATCHER_VAULT_KEY": VAULT_KEY, "DTJ_THEME_ACCESS_QAXV3R_8G": THEME}, "push", "--all")
        self.assertEqual(code, 0)
        made = {i["name"]: i for i in fake.items}
        self.assertEqual(made["DTJ_CATCHER_VAULT_KEY"]["login"]["password"], VAULT_KEY)
        self.assertEqual(made["DTJ_CATCHER_VAULT_KEY"]["collectionIds"], ["col-developers"])
        self.assertEqual(made["DTJ_THEME_ACCESS_QAXV3R_8G"]["collectionIds"], ["col-designers"])
        self.assertIn("IRREPLACEABLE", made["DTJ_CATCHER_VAULT_KEY"]["notes"])
        self.assertIn("added to 'DTJ Store Factory - Developers'", text)
        again = self.run_main(fake, {"DTJ_CATCHER_VAULT_KEY": VAULT_KEY}, "push", "DTJ_CATCHER_VAULT_KEY")[1]
        self.assertIn("already in the vault, same value", again)

    def test_personal_and_unknown_keys_never_go_into_the_vault(self):
        fake = FakeBw()
        code, text, _, _ = self.run_main(fake, {"N8N_MCP_TOKEN": "eyJpersonal", "PATH": "x"}, "push", "N8N_MCP_TOKEN", "PATH")
        self.assertEqual(code, 1)
        self.assertIn("personal one that never goes into the vault", text)
        self.assertEqual(fake.items, [])
        self.assertNotIn("N8N_MCP_TOKEN", [i["name"] for i in fake.items])
        all_code, _, _, _ = self.run_main(fake, {"N8N_MCP_TOKEN": "eyJpersonal"}, "push", "--all")
        self.assertEqual(all_code, 1)  # nothing known to copy

    def test_a_designer_pulls_only_what_their_collection_shows_and_keeps_their_own_values(self):
        fake = FakeBw(visible=(vault.DESIGNERS,), items=[item("DTJ_THEME_ACCESS_QAXV3R_8G", THEME, vault.DESIGNERS),
                                                          item("DTJ_THEME_ACCESS_HOPE", "shptka_other", vault.DESIGNERS),
                                                          item("DTJ_CATCHER_VAULT_KEY", VAULT_KEY)])
        code, text, saved, _ = self.run_main(fake, {"DTJ_THEME_ACCESS_HOPE": "mine"}, "pull")
        self.assertEqual(code, 0)
        self.assertEqual(saved, {"DTJ_THEME_ACCESS_QAXV3R_8G": THEME})  # the developer key is not visible; their own value is kept
        self.assertIn("left as they are", text)
        _, _, saved, _ = self.run_main(fake, {"DTJ_THEME_ACCESS_HOPE": "mine"}, "pull", "--replace")
        self.assertEqual(saved["DTJ_THEME_ACCESS_HOPE"], "shptka_other")

    def test_status_names_keys_only_and_warns_when_the_vault_key_lives_on_one_laptop(self):
        code, text, _, _ = self.run_main(FakeBw(), {"DTJ_CATCHER_VAULT_KEY": VAULT_KEY}, "status")
        self.assertEqual(code, 0)
        self.assertIn("DTJ_CATCHER_VAULT_KEY: NOT in the vault, on this laptop", text)
        self.assertIn("WARNING: DTJ_CATCHER_VAULT_KEY is only on this laptop", text)

    def test_signing_in_is_left_to_bitwarden_and_problems_stop_cleanly(self):
        code, text, _, _ = self.run_main(FakeBw(status="unauthenticated"), {}, "status")
        self.assertEqual(code, 2)
        self.assertIn("bw login", text)
        fake = FakeBw(status="locked")
        asked = []
        code, _, _, v = self.run_main(fake, {}, "status", unlock=lambda env: asked.append(1) or "session-key-from-bitwarden")
        self.assertEqual((code, asked, v.env["BW_SESSION"]), (0, [1], "session-key-from-bitwarden"))
        twins = FakeBw(items=[item("DTJ_CATCHER_BOT_KEY", "a" * 64, iid="x1"), item("DTJ_CATCHER_BOT_KEY", "b" * 64, iid="x2")])
        code, text, _, _ = self.run_main(twins, {}, "pull")
        self.assertEqual(code, 2)
        self.assertIn("two vault items are named DTJ_CATCHER_BOT_KEY", text)
        nocol = FakeBw(visible=())
        code, text, _, _ = self.run_main(nocol, {"DTJ_CATCHER_VAULT_KEY": VAULT_KEY}, "push", "DTJ_CATCHER_VAULT_KEY")
        self.assertEqual(code, 1)
        self.assertIn("Make these collections", text)


class EnvFile(unittest.TestCase):
    """The VPS (22 Oct 2026): keys go into the worker's env file, owner-only, never into a Windows setting."""

    def test_keys_round_trip_and_the_file_is_rewritten_whole(self):
        import os
        import tempfile
        from pathlib import Path
        path = Path(tempfile.mkdtemp()) / "dtj" / "worker.env"
        save = vault.env_file_saver(path)
        save("DTJ_CATCHER_CONTROL_KEY", 'a"b\\c')
        save("N8N_MCP_TOKEN", "plain")
        save("N8N_MCP_TOKEN", "newer")
        self.assertEqual(vault.env_file_vars(path), {"DTJ_CATCHER_CONTROL_KEY": 'a"b\\c', "N8N_MCP_TOKEN": "newer"})
        self.assertEqual(path.read_text(encoding="utf-8").count("\n"), 2)
        if os.name != "nt":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(vault.env_file_vars(path.parent / "missing.env"), {})


if __name__ == "__main__":
    unittest.main()

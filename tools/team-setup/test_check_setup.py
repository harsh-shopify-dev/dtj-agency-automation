"""check_setup never prints a secret, names what is missing, and refuses a theme that is not a draft (stand-ins: no store, no n8n).

    python -m unittest discover -s tools/team-setup -t tools/team-setup
"""
import contextlib
import io
import sys
import types
import unittest
from unittest import mock

import check_setup as cs

SECRET = "shptka_THIS-MUST-NEVER-BE-PRINTED-1234567890"
STORES = [{"store_name": "DTJ Test Store", "myshopify_domain": "qaxv3r-8g.myshopify.com", "draft_theme_id": "167627423941"},
          {"store_name": "Hope N Skin", "myshopify_domain": "hopenskin-store.myshopify.com", "draft_theme_id": "123456789012"}]


class FakeAccess:
    role = "unpublished"

    def __init__(self, store, token):
        self.store = store

    def themes(self, theme_id):
        return [{"id": int(theme_id), "role": FakeAccess.role}]


class Check(unittest.TestCase):
    def run_check(self, secrets: dict, *argv):
        n8n = types.ModuleType("n8n_mcp")
        n8n.call = lambda tool, args: {"data": []}
        n8n.STORES_TABLE, n8n.PROJECT = "t", "p"
        out = io.StringIO()
        with mock.patch.object(cs, "user_var", lambda name: secrets.get(name, "")), \
                mock.patch.object(cs, "stores_from_n8n", lambda: STORES), \
                mock.patch.object(cs, "_version", lambda cmd: "1.0"), \
                mock.patch("page_builder.theme_target.ThemeAccess", FakeAccess), \
                mock.patch.dict(sys.modules, {"n8n_mcp": n8n}), contextlib.redirect_stdout(out):
            code = cs.main(list(argv))
        return code, out.getvalue()

    def test_no_secret_value_is_ever_printed(self):
        secrets = {"N8N_MCP_TOKEN": SECRET, "DTJ_THEME_ACCESS_QAXV3R_8G": SECRET, "DTJ_THEME_ACCESS_HOPENSKIN_STORE": SECRET}
        for argv in ((), ("--missing-secrets",), ("--secret-names",)):
            _, printed = self.run_check(secrets, *argv)
            self.assertNotIn(SECRET, printed)
            self.assertNotIn(SECRET[:12], printed)
        _, printed = self.run_check(secrets)
        self.assertIn(f"{len(SECRET)} characters", printed)  # length only

    def test_missing_secrets_are_listed_by_name(self):
        _, printed = self.run_check({"N8N_MCP_TOKEN": SECRET}, "--missing-secrets")
        self.assertEqual(printed.split(), ["DTJ_THEME_ACCESS_QAXV3R_8G", "DTJ_THEME_ACCESS_HOPENSKIN_STORE"])
        _, printed = self.run_check({}, "--secret-names")
        self.assertEqual(printed.split()[0], "N8N_MCP_TOKEN")

    def test_a_live_theme_saved_as_the_draft_is_a_problem(self):
        secrets = {"N8N_MCP_TOKEN": SECRET, "DTJ_THEME_ACCESS_QAXV3R_8G": SECRET, "DTJ_THEME_ACCESS_HOPENSKIN_STORE": SECRET}
        FakeAccess.role = "live"
        self.addCleanup(setattr, FakeAccess, "role", "unpublished")
        code, printed = self.run_check(secrets)
        self.assertEqual(code, 1)
        self.assertIn("is live", printed)
        FakeAccess.role = "unpublished"
        code, printed = self.run_check(secrets)
        self.assertIn("draft theme 167627423941 is unpublished", printed)


if __name__ == "__main__":
    unittest.main()

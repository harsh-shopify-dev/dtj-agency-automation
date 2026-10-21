"""store_builder.py: DTJ Store Builder made, its secret saved and released, with a stand-in Shopify CLI (nothing reaches Shopify).

    python -m unittest discover -s services/install-catcher/test -p "test_*.py"
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE / "test"))
import store_builder as sb  # noqa: E402
from test_tools import blank_wrangler  # noqa: E402


class FakeCli:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[1:3] == ["app", "init"]:
            folder = Path(cmd[cmd.index("--path") + 1]) / "new"
            folder.mkdir(parents=True)
            (folder / "shopify.app.toml").write_text('client_id = "' + "c" * 32 + '"\n', encoding="utf-8")
        if cmd[1:4] == ["app", "env", "show"]:
            return subprocess.CompletedProcess(cmd, 0, "SHOPIFY_API_KEY=" + "c" * 32 + "\nSHOPIFY_API_SECRET=shpss_builder_secret\n", "")
        return subprocess.CompletedProcess(cmd, 0, "ok", "")


class StoreBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.wrangler = self.tmp / "wrangler.toml"
        self.wrangler.write_text(blank_wrangler(), encoding="utf-8")
        self.saved, self.printed = {}, []

    def make(self, cli):
        return sb.create("Harsh", cli=cli, save=self.saved.__setitem__, folder=self.tmp / "app", wrangler=self.wrangler,
                         out=self.printed.append)

    def test_made_once_with_only_the_brand_copys_permissions_secret_saved_and_released(self):
        cli = FakeCli()
        self.assertEqual(self.make(cli), "c" * 32)
        toml = (self.tmp / "app" / "shopify.app.toml").read_text(encoding="utf-8")
        self.assertIn('scopes = "read_products,write_products,read_publications,write_publications,read_legal_policies,write_legal_policies"', toml)
        self.assertIn('application_url = "https://dtj-install-catcher.ultimateecomwithharsh.workers.dev/builder"', toml)
        self.assertEqual(self.saved, {"DTJ_STORE_BUILDER_CLIENT_SECRET": "shpss_builder_secret"})
        self.assertNotIn("shpss_builder_secret", " ".join(self.printed) + toml + self.wrangler.read_text(encoding="utf-8"))
        self.assertIn('BUILDER_CLIENT_ID = "' + "c" * 32 + '"', self.wrangler.read_text(encoding="utf-8"))
        init = next(c for c in cli.calls if c[1:3] == ["app", "init"])
        self.assertEqual(init[init.index("--organization-id") + 1], "141167028")
        self.assertEqual([c[1:3] for c in cli.calls][-1], ["app", "deploy"])
        again = FakeCli()
        self.make(again)  # a second run reuses the app: never two Store Builders
        self.assertFalse([c for c in again.calls if c[1:3] == ["app", "init"]])
        self.assertEqual(self.wrangler.read_text(encoding="utf-8").count("BUILDER_CLIENT_ID"), 1)

    def test_no_yes_no_app(self):
        with self.assertRaises(sb.Failed):
            sb.create(" ", cli=FakeCli(), save=self.saved.__setitem__, folder=self.tmp / "app", wrangler=self.wrangler)


if __name__ == "__main__":
    unittest.main()

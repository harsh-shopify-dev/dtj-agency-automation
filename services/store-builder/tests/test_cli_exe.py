"""The Shopify CLI is found even when it lives only inside the Claude desktop app's npm folder (20 Oct 2026: ship_home stopped with
"The system cannot find the file specified" in Harsh's PowerShell, which does not see that folder)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provision import theme  # noqa: E402


class CliExeTests(unittest.TestCase):
    def test_on_path_wins_then_the_claude_app_folder_then_the_bare_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            npm = Path(tmp, "Packages", "Claude_abc123", "LocalCache", "Roaming", "npm")
            npm.mkdir(parents=True)
            (npm / "shopify.cmd").write_text("@echo off\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}), mock.patch.object(theme.shutil, "which", return_value=None):
                self.assertEqual(theme.cli_exe("shopify"), str(npm / "shopify.cmd"))
                self.assertEqual(theme.cli_exe("git"), "git")  # only the Shopify CLI is looked up there
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}), mock.patch.object(theme.shutil, "which", return_value=r"C:\x\shopify.cmd"):
                self.assertEqual(theme.cli_exe("shopify"), r"C:\x\shopify.cmd")
        with tempfile.TemporaryDirectory() as empty, mock.patch.dict(os.environ, {"LOCALAPPDATA": empty}), \
                mock.patch.object(theme.shutil, "which", return_value=None):
            self.assertEqual(theme.cli_exe("shopify"), "shopify")  # nothing found: the plain name, so the error names the program


class OutsideGitTests(unittest.TestCase):
    """20 Oct 2026: started next to a git project with uncommitted changes, the CLI asks "Do you want to proceed?" and, with no one to
    answer, ship_home's theme pull waited 10 minutes. Git must see no project at the theme folder nor at the folder the CLI runs in."""

    def test_paths_become_absolute_and_git_stops_above_the_theme_folder_and_the_run_folder(self):
        cmd, cwd, extra = theme.outside_git(["shopify", "theme", "pull", "--path", os.path.join("..", "work", "backup"), "--only", "a.json"])
        self.assertTrue(os.path.isabs(cmd[4]))
        self.assertEqual(cmd[:4] + cmd[5:], ["shopify", "theme", "pull", "--path", "--only", "a.json"])
        ceilings = extra["GIT_CEILING_DIRECTORIES"].split(os.pathsep)
        self.assertIn(os.path.dirname(cmd[4]), ceilings)
        self.assertIn(os.path.dirname(os.path.abspath(cwd)), ceilings)
        self.assertEqual(theme.outside_git(["shopify", "theme", "list", "--json"])[0], ["shopify", "theme", "list", "--json"])


if __name__ == "__main__":
    unittest.main()

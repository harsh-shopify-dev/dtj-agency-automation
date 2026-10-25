"""Where the page builder finds a browser: DTJ_BROWSER, the usual places, then Playwright's Chromium (the VPS, 23 Oct 2026)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from page_builder import browser


class Candidates(unittest.TestCase):
    def test_a_named_browser_comes_first_and_playwrights_chromium_last_newest_first(self):
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        for build in ("chromium-1140", "chromium-1200"):
            exe = home / ".cache" / "ms-playwright" / build / "chrome-linux" / "chrome"
            exe.parent.mkdir(parents=True)
            exe.write_text("")
        found = browser.candidates({"DTJ_BROWSER": "/opt/chrome/chrome"}, home)
        self.assertEqual(found[0], Path("/opt/chrome/chrome"))
        self.assertEqual(found[1:1 + len(browser.CANDIDATES)], [Path(p) for p in browser.CANDIDATES])
        self.assertEqual([p.parts[-3] for p in found[-2:]], ["chromium-1200", "chromium-1140"])
        self.assertEqual(browser.candidates({}, home)[0], Path(browser.CANDIDATES[0]))


if __name__ == "__main__":
    unittest.main()

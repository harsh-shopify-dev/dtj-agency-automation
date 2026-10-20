"""Drive Google Flow (flow.google.com) in a real, logged-in Chrome, the way a person does (Harsh's decision 20 Oct 2026:
no API; Flow and ChatGPT run in a browser on the VPS).

Chrome runs with its own DTJ profile and a debugging port; a person signs in to Google ONCE in that window:
    Windows: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\\dtj\\chrome-flow
    Linux (VPS desktop): google-chrome --remote-debugging-port=9222 --user-data-dir=$HOME/dtj/chrome-flow
This module attaches over CDP. It never types a password, never solves a captcha: if Google shows a sign-in or a challenge it
stops with NeedsPerson and the job waits for the person on duty.

What was learned driving Flow by hand (20-21 Oct 2026), now in code:
- Images: Nano Banana 2.1, 9:16, x2 (0 credits). Videos: Omni 1.1 Flash, Ingredients mode, 9:16, 720p, 4/6/8/10 s, x2.
- Switching Frames/Ingredients drops attached images; set the mode first, then attach.
- The picker lists items lazily and re-orders as new items finish: pick by asset id (the uuid in the image URL), never by position.
- A video tile's thumbnail uuid is the video's uuid; the signed video URL is only on the clip's own page (open, read, go back).
- Assets download with the signed URL alone (no cookies).
"""
from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

FLOW = "https://flow.google.com/"
IMG_RE = re.compile(r"flow-content\.google/image/([0-9a-f-]{36})")


class NeedsPerson(RuntimeError):
    """Google wants a sign-in, a verification or shows an error a person must look at."""


class FlowError(RuntimeError):
    pass


class Flow:
    def __init__(self, cdp: str = "http://127.0.0.1:9222", slow_ms: int = 250):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(cdp, slow_mo=slow_ms)
        ctx = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        self.page = ctx.new_page()
        self.page.set_default_timeout(30_000)

    def close(self):
        try:
            self.page.close()
        finally:
            self._pw.stop()

    # ---------- navigation ----------
    def _guard(self):
        url = self.page.url
        if "accounts.google.com" in url or "/signin" in url:
            raise NeedsPerson("Google asks for a sign-in in the Flow Chrome window: a person must sign in once")
        body = self.page.locator("body").inner_text(timeout=5_000)[:4000].lower()
        for bad in ("unusual traffic", "verify it's you", "captcha", "try again later"):
            if bad in body:
                raise NeedsPerson(f"Flow shows '{bad}': a person must look at the Flow Chrome window")

    def open_project(self, url: str | None = None) -> str:
        if url:
            self.page.goto(url, wait_until="domcontentloaded")
        else:
            self.page.goto(FLOW, wait_until="domcontentloaded")
            self.page.wait_for_timeout(2500)
            self._guard()
            self.page.get_by_text("New project", exact=True).first.click()
            self.page.wait_for_url(re.compile(r"/project/"), timeout=30_000)
        self.page.wait_for_timeout(2500)
        self._guard()
        return self.page.url.split("/edit/")[0]

    # ---------- settings ----------
    def _overlay_button(self, label: str):
        return self.page.locator(".cdk-overlay-container button").filter(has_text=re.compile(rf"(^|\s){re.escape(label)}$"))

    def _open_settings(self):
        btn = self.page.locator("button").filter(has_text=re.compile(r"Nano Banana|Video ·|Omni|Veo|Image ·")).last
        btn.click()
        self.page.wait_for_timeout(600)

    def settings(self, mode: str, ratio: str = "9:16", takes: int = 2, model: str | None = None, seconds: int | None = None,
                 video_mode: str = "Ingredients", resolution: str = "720p"):
        """mode 'Image' or 'Video'. Set BEFORE attaching ingredients (a mode change drops them)."""
        self._open_settings()
        self._overlay_button(mode).first.click()
        self.page.wait_for_timeout(400)
        if mode == "Video":
            self._overlay_button(video_mode).first.click()
            if resolution:
                self._overlay_button(resolution).first.click()
            if seconds:
                self._overlay_button(f"{seconds}s").first.click()
        self._overlay_button(ratio).first.click()
        if model:
            current = self.page.locator(".cdk-overlay-container button").filter(has_text="arrow_drop_down").first
            if model not in current.inner_text():
                current.click()
                self.page.get_by_role("option", name=re.compile(re.escape(model))).first.click()
        self._overlay_button(f"x{takes}").first.click()
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(400)

    # ---------- assets ----------
    def asset_ids(self) -> list[str]:
        srcs = self.page.eval_on_selector_all("img", "els => els.map(e => e.src)")
        seen, out = set(), []
        for s in srcs:
            m = IMG_RE.search(s or "")
            if m and m.group(1) not in seen:
                seen.add(m.group(1)); out.append(m.group(1))
        return out

    def _open_picker(self):
        self.page.locator("button").filter(has_text=re.compile(r"^add$")).first.click()
        self.page.wait_for_timeout(1200)

    def _close_picker(self):
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)

    def upload(self, path: str | Path, timeout_s: int = 120) -> str:
        """Upload a local image into the project; returns its asset id. (Flow also attaches it to the prompt.)"""
        before = set(self.asset_ids())
        self._open_picker()
        with self.page.expect_file_chooser() as fc:
            self.page.locator(".cdk-overlay-container button").filter(has_text=re.compile(r"^upload$")).first.click()
        fc.value.set_files(str(path))
        self._close_picker()
        end = time.time() + timeout_s
        while time.time() < end:
            new = [i for i in self.asset_ids() if i not in before]
            if new:
                return new[0]
            self.page.wait_for_timeout(2000)
        raise FlowError(f"upload of {path} did not appear in the project")

    def attached(self) -> list[str]:
        srcs = self.page.eval_on_selector_all("flow-ingredient-bar img, .prompt-ingredient-bar img", "els => els.map(e => e.src)")
        return [m.group(1) for s in srcs if (m := IMG_RE.search(s or ""))]

    def clear_attached(self):
        for _ in range(6):
            if not self.attached():
                return
            self.page.locator("flow-ingredient-bar button, .prompt-ingredient-bar button").filter(
                has_text=re.compile(r"close|cancel")).first.click()
            self.page.wait_for_timeout(400)

    def attach(self, asset_id: str):
        """Attach a project image as an ingredient, found by id (scrolls the lazy list)."""
        self._open_picker()
        found = self.page.evaluate("""async (id) => {
            const sc = [...document.querySelectorAll('.cdk-overlay-container *')].filter(e => e.scrollHeight > e.clientHeight + 20
                        && getComputedStyle(e).overflowY !== 'visible');
            for (let k = 0; k < 40; k++) {
              const img = [...document.querySelectorAll('.cdk-overlay-container img')].find(i => i.src.includes(id));
              if (img) { img.scrollIntoView({block: 'center', behavior: 'instant'}); await new Promise(r => setTimeout(r, 800));
                         const row = img.closest('button,[role=option],li') || img.parentElement; row.click(); return true; }
              sc.forEach(s => s.scrollTop += 300); await new Promise(r => setTimeout(r, 300));
            }
            return false; }""", asset_id)
        self.page.wait_for_timeout(1500)
        if not found or asset_id not in self.attached():
            self._close_picker()
            raise FlowError(f"could not attach asset {asset_id}")

    # ---------- generate ----------
    def generate(self, prompt: str, expect: int, timeout_s: int = 600) -> list[str]:
        """Type the prompt, submit, wait until `expect` new assets have finished. Returns their ids (newest first)."""
        before = set(self.asset_ids())
        box = self.page.get_by_role("textbox", name=re.compile("What do you want to create"))
        box.click(); box.fill(prompt)
        self.page.locator("button").filter(has_text=re.compile(r"^arrow_forward$")).last.click()
        end = time.time() + timeout_s
        while time.time() < end:
            self.page.wait_for_timeout(5000)
            self._guard()
            busy = self.page.evaluate("[...document.querySelectorAll('*')].filter(e => e.children.length === 0 && "
                                      "/^\\d{1,3}%$/.test(e.textContent.trim())).length")
            new = [i for i in self.asset_ids() if i not in before]
            if len(new) >= expect and not busy:
                return new[:expect]
            failed = self.page.locator("text=/couldn.t generate|policy|failed/i").count()
            if failed and not busy:
                raise FlowError(f"Flow could not generate ({len(new)} of {expect} came back): check the prompt for policy words")
        raise FlowError(f"timed out after {timeout_s}s waiting for {expect} results")

    def video_url(self, asset_id: str) -> str:
        """Open a video tile, read its signed URL, come back."""
        home = self.page.url.split("/edit/")[0]
        self.page.evaluate("""(id) => { const i = [...document.querySelectorAll('img')].find(i => i.src.includes(id));
                                        i.scrollIntoView({block: 'center'}); i.click(); }""", asset_id)
        self.page.wait_for_url(re.compile(r"/edit/"), timeout=20_000)
        url = None
        for _ in range(20):
            self.page.wait_for_timeout(500)
            url = self.page.evaluate("[...document.querySelectorAll('video')].map(v => v.currentSrc || v.src).find(Boolean)")
            if url:
                break
        self.page.goto(home, wait_until="domcontentloaded"); self.page.wait_for_timeout(2500)
        if not url or asset_id not in url:
            raise FlowError(f"no video URL for {asset_id}")
        return url

    def image_url(self, asset_id: str) -> str:
        srcs = self.page.eval_on_selector_all("img", "els => els.map(e => e.src)")
        for s in srcs:
            if asset_id in (s or ""):
                return s
        raise FlowError(f"no image URL for {asset_id}")


def download(url: str, dest: str | Path) -> Path:
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest
